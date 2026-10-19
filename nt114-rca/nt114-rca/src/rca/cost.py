"""End-to-end cost per cell (evaluation-only): tokens, LLM latency, retrieval and preparation seconds.

Rows of `table_cost` are dataset x model x condition x retrieval x store mode (`kind == "cell"`), plus
one row per arm path of the selective evaluator (`kind == "path"`): `answer` pays the `none` arm,
`answer+retrieve` pays both arms of `selective.ARMS` for every incident (the upper bound of any
policy that retrieves after answering). Latency replayed from the LLM cache is the latency recorded
when the answer was first generated; `cached_share` says how much of a cell was replayed.
Preparation seconds come from `prepare_log.jsonl`: the telemetry read plus the build of that
condition, a measurement of the machine named in the manifest. GPU-seconds stay NaN until a GPU run
records them.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .selective import ARMS

KEYS = ["dataset", "model", "condition", "retrieval", "store_mode"]


def load_prepare_log(paths) -> pd.DataFrame:
    """Latest row per (incident, condition) of the query incidents; store rows are a retrieval set-up cost."""
    frames = [pd.read_json(p, lines=True) for p in paths or [] if Path(p).is_file() and Path(p).stat().st_size]
    if not frames:
        return pd.DataFrame(columns=["incident_uid", "condition", "prepare_s"])
    log = pd.concat(frames, ignore_index=True)
    if "kind" in log:
        log = log[log["kind"] == "query"]
    log = log.sort_values("ts").drop_duplicates(["incident_uid", "condition"], keep="last")
    return log.assign(prepare_s=log["wall_s"].astype(float))[["incident_uid", "condition", "prepare_s"]]


def _n_samples(df: pd.DataFrame) -> pd.Series:
    if "sampling" not in df:
        return pd.Series(np.nan, index=df.index)
    return df["sampling"].map(lambda s: s.get("n") if isinstance(s, dict) else np.nan).astype(float)


def _frame(df: pd.DataFrame, prep: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    for c in ("prompt_tokens", "completion_tokens", "latency_s", "retrieval_s"):
        d[c] = pd.to_numeric(d[c], errors="coerce") if c in d else np.nan
    d["total_tokens"] = d["prompt_tokens"] + d["completion_tokens"]
    d["n_samples"] = _n_samples(d)
    d["cached"] = d["cached"].astype(float) if "cached" in d else np.nan
    if "store_mode" not in d:
        d["store_mode"] = "-"
    uid = "incident_uid" if "incident_uid" in d and d["incident_uid"].notna().any() else "case_id"
    d = d.merge(prep.rename(columns={"incident_uid": uid}), on=[uid, "condition"], how="left")
    d["e2e_s"] = d["prepare_s"].fillna(0) + d["retrieval_s"].fillna(0) + d["latency_s"]
    return d


def _summary(g: pd.DataFrame) -> dict:
    return {"n_records": len(g), "n_incidents": g["incident_uid"].nunique() if "incident_uid" in g else len(g),
            "prompt_tokens": g["prompt_tokens"].mean(), "completion_tokens": g["completion_tokens"].mean(),
            "total_tokens": g["total_tokens"].mean(), "tokens_per_sample": (g["total_tokens"] / g["n_samples"]).mean(),
            "latency_s": g["latency_s"].mean(), "cached_share": g["cached"].mean(),
            "latency_replayed": bool((g["cached"] > 0).any()), "retrieval_s": g["retrieval_s"].mean(),
            "prepare_s": g["prepare_s"].mean(), "prepare_logged": float(g["prepare_s"].notna().mean()),
            "gpu_s": np.nan, "e2e_s": g["e2e_s"].mean()}


def table_cost(df: pd.DataFrame, prepare_logs=(), arms: dict = ARMS, store_mode: str = "precedent") -> pd.DataFrame:
    d = _frame(df, load_prepare_log(prepare_logs))
    rows = [{"kind": "cell", **dict(zip(KEYS, k)), **_summary(g)} for k, g in d.groupby(KEYS, dropna=False)]
    # arm paths: per incident, sum the cells each path pays (the `retrieve` arm in the non-oracle store)
    ans, ret = arms["answer"], arms["retrieve"]
    uid = "incident_uid" if "incident_uid" in d and d["incident_uid"].notna().any() else "case_id"
    a = d[(d.retrieval == ans)]
    r = d[(d.retrieval == ret) & (d.store_mode == store_mode)]
    num = ["prompt_tokens", "completion_tokens", "total_tokens", "latency_s", "retrieval_s"]
    for (ds, m, cond), ga in a.groupby(["dataset", "model", "condition"]):
        gr = r[(r.dataset == ds) & (r.model == m) & (r.condition == cond)]
        base = {"kind": "path", "dataset": ds, "model": m, "condition": cond, "store_mode": store_mode}
        rows.append({**base, "retrieval": ans, "path": "answer", **_summary(ga)})
        if len(gr):
            both = ga.set_index(uid)[num].add(gr.set_index(uid)[num]).dropna(subset=["total_tokens"])
            prep = ga.set_index(uid)["prepare_s"].reindex(both.index)
            # the incident is prepared once; both calls and the retrieval are paid
            both["e2e_s"] = prep.fillna(0) + both["retrieval_s"].fillna(0) + both["latency_s"]
            rows.append({**base, "retrieval": f"{ans}+{ret}", "path": "answer+retrieve", "n_records": len(both),
                         "n_incidents": len(both), **{c: both[c].mean() for c in num + ["e2e_s"]},
                         "prepare_s": prep.mean(), "gpu_s": np.nan})
    return pd.DataFrame(rows)
