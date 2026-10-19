"""Compatibility view: canonical records and telemetry in the shapes the legacy pipeline expects.

`visible_case` gives model-facing code a `VisibleCase` (no labels, `case_id = incident_uid`, so the
candidate shuffle seed carries no label). `truth` gives scoring and ablation a `Truth`.
`legacy_telemetry` rebuilds the `{"metrics", "logs", "traces"}` DataFrames the evidence builder reads
(the shapes of the retired direct RCAEval loader: same column names, units and row order) from the
canonical Parquet files. `tests/golden/canonical_synthetic_evidence.sha256` pins the resulting evidence.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pyarrow.compute as pc

from .data import Truth, VisibleCase
from .store import CanonicalStore


# Bump whenever `legacy_telemetry` can return different frames for the same canonical data: evidence
# fingerprints include it, so cached evidence built from an older view is rebuilt.
VIEW_VERSION = "2"
# Time bucket for metrics merged across entities (s); RCA100 samples every 30 s and keeps 120 s after
# the anchor, so 60 s buckets would leave too few post-anchor points to score.
METRIC_ALIGN_S = {"rca100": 30}


def visible_case(incident: dict) -> VisibleCase:
    return VisibleCase(case_id=incident["incident_uid"], dataset=incident["dataset_id"], system=incident["system"],
                       inject_time=incident["time"]["anchor_ns"] // 10**9, path=None,
                       services=list(incident["candidates"]["services"]))


def truth(label: dict) -> Truth:
    rc = label["root_cause"]
    return Truth(root_service=rc["primary_root_service"], fault=label["fault"]["type_raw"],
                 root_ids=tuple(rc["root_service_ids"]), granularity=rc["label_granularity"])


def evidence_kwargs(cfg: dict, dataset: str) -> dict:
    """Per-dataset `evidence.build` options from the prep config's `evidence` section."""
    gap = ((cfg.get("evidence") or {}).get("log_trace_segment_gap_s") or {}).get(dataset)
    return {"log_trace_segment_gap_s": float(gap)} if gap else {}


def default_metric_set(incident: dict) -> str | None:
    """Metric set the legacy loader would read: `simple` except RCAEval RE1 (it reads data.csv)."""
    sets = incident["telemetry"]["metrics"]["metric_sets"]
    if not sets:
        return None
    if incident["dataset_id"] == "rcaeval":
        from .adapters.rcaeval import legacy_metric_set
        return legacy_metric_set(incident["dataset_subset"], sets)
    for preferred in ("simple", "default"):
        if preferred in sets:
            return preferred
    return sets[0]


def _metrics_wide_bucketed(t, align_s: int) -> pd.DataFrame | None:
    """Several source members (one CSV per pod) or a long-format table (one value per source row): one
    column per `<service_id>_<metric>`, rows on `align_s` time buckets, entities of the same service
    averaged. Rows without a service id are skipped."""
    t = t.filter(pc.is_valid(t["service_id"]))
    if t.num_rows == 0:
        return None
    df = pd.DataFrame({"time": t["ts_ns"].to_numpy(zero_copy_only=False) // 10**9 // align_s * align_s,
                       "col": [f"{s}_{m.replace('_', '.')}" for s, m in zip(t["service_id"].to_pylist(), t["metric"].to_pylist())],
                       "value": t["value"].to_numpy(zero_copy_only=False).astype(float)})
    wide = df.pivot_table(index="time", columns="col", values="value", aggfunc="mean", dropna=False)
    wide = wide.sort_index().reset_index()
    wide.columns.name = None
    return wide[["time"] + sorted(c for c in wide.columns if c != "time")]


def _metrics_wide(t, metric_set: str, align_s: int = 60) -> pd.DataFrame | None:
    t = t.filter(pc.equal(t["metric_set"], metric_set))
    if t.num_rows == 0:
        return None
    # the cell-position rebuild below is for one wide CSV (RCAEval); long tables have a single value column
    if pc.count_distinct(t["src_file"]).as_py() != 1 or pc.count_distinct(t["src_col"]).as_py() == 1:
        return _metrics_wide_bucketed(t, align_s)
    rows = t["src_row"].to_numpy()
    cols = t["src_col"].to_numpy()
    ts = t["ts_ns"].to_numpy(zero_copy_only=False)
    vals = t["value"].to_numpy(zero_copy_only=False).astype(float)
    names = [f"{e}_{m.replace('_', '.')}" for e, m in zip(t["entity_raw"].to_pylist(), t["metric"].to_pylist())]
    u_rows, r_idx = np.unique(rows, return_inverse=True)
    u_cols, c_idx = np.unique(cols, return_inverse=True)
    mat = np.full((len(u_rows), len(u_cols)), np.nan)
    mat[r_idx, c_idx] = vals
    col_names = [None] * len(u_cols)
    for k, ci in enumerate(c_idx):
        if col_names[ci] is None:
            col_names[ci] = names[k]
    time_ns = np.zeros(len(u_rows), dtype=np.int64)
    time_ns[r_idx] = ts
    time = time_ns // 10**9 if np.all(time_ns % 10**9 == 0) else time_ns / 1e9
    df = pd.DataFrame(mat, columns=col_names)
    df.insert(0, "time", time)
    return df


def legacy_telemetry(store: CanonicalStore, uid: str, metric_set: str | None = None) -> dict:
    inc = store.incident(uid)
    out = {"metrics": None, "logs": None, "traces": None}
    ms = metric_set or default_metric_set(inc)
    t = store.telemetry(uid, "metrics")
    if t is not None and ms is not None:
        out["metrics"] = _metrics_wide(t, ms, METRIC_ALIGN_S.get(inc["dataset_id"], 60))
    t = store.telemetry(uid, "logs")
    if t is not None:
        df = t.sort_by([("src_file", "ascending"), ("src_row", "ascending")]).to_pandas()
        # pandas.read_csv reads an empty field as NaN; canonical keeps "" (the legacy loader saw NaN)
        logs = pd.DataFrame({"timestamp": df["ts_ns"].astype("int64"), "container_name": df["entity_raw"],
                             "message": df["message"].replace("", np.nan)})
        if df["level"].notna().any():
            logs["level"] = df["level"]
        logs["svc"] = df["service_id"]
        out["logs"] = logs
    t = store.telemetry(uid, "traces")
    if t is not None:
        df = t.sort_by([("src_file", "ascending"), ("src_row", "ascending")]).to_pandas()
        out["traces"] = pd.DataFrame({
            "traceID": df["trace_id"], "spanID": df["span_id"], "serviceName": df["entity_raw"],
            "operationName": df["operation"], "startTime": df["ts_ns"] // 1000, "duration": df["duration_ns"] // 1000,
            "statusCode": pd.to_numeric(df["status_code"], errors="coerce"), "parentSpanID": df["parent_span_id"],
            "svc": df["service_id"]})
    return out
