"""Real RCAEval build (data/canonical) against known facts and against the Hugging Face copy.

Known HF-vs-Zenodo difference classes (docs/dataset_quality_audit.md): renamed batch cases,
one case missing logs, header-only traces, root_cause.txt files, omitted auxiliary files or
columns, one truncated inject_time, and log messages whose edge quotes HF dropped. Any other
difference fails.
"""
from __future__ import annotations

import random
from collections import Counter
from pathlib import Path

import numpy as np
import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest

from conftest import REAL_DATA
from rca.store import CanonicalStore

HF = REAL_DATA / "raw/rcaeval-hf/hf-afeacb11bcc9"
KNOWN = {"renamed_case", "hf_missing_logs", "header_only_traces", "root_cause_txt", "omitted_aux", "truncated_inject_time",
         "hf_log_quoting"}

pytestmark = [pytest.mark.realdata,
              pytest.mark.skipif(not (REAL_DATA / "canonical/v1/rcaeval/_build.json").is_file(), reason="no real RCAEval build")]


@pytest.fixture(scope="module")
def real():
    store = CanonicalStore(REAL_DATA)
    labels = store.labels("rcaeval")
    incs = {i["incident_uid"]: i for i in store.incidents("rcaeval", states=None)}
    return {"store": store, "labels": labels, "incs": incs, "q": store.quality("rcaeval"),
            "by_sid": {l["source_incident_id"]: u for u, l in labels.items()}}


def test_counts_and_duplicate(real):
    assert len(real["incs"]) == 736
    states = Counter(q["state"] for q in real["q"].values())
    assert states["REJECT"] == 1
    (rej,) = [u for u, q in real["q"].items() if q["state"] == "REJECT"]
    assert real["labels"][rej]["source_incident_id"].endswith("_multi-source-data")
    assert real["labels"][rej]["group"]["duplicate_of"] == real["by_sid"]["rcaeval:re2ob_checkoutservice_cpu_1"]
    assert not any(f["code"] == "ADAPTER_EXCEPTION" for q in real["q"].values() for f in q["findings"])


def test_batch_cell_labels(real):
    batch = [u for sid, u in real["by_sid"].items() if sid.startswith("rcaeval:re3tt_ts-route-service_f3_1_")]
    plain = [u for sid, u in real["by_sid"].items() if sid.startswith("rcaeval:re3tt_ts-route-service_f3_") and u not in batch]
    assert len(batch) == 3 and len(plain) == 3 and len(set(batch + plain)) == 6
    for u in batch + plain:
        lab = real["labels"][u]
        assert lab["root_cause"]["primary_root_service"] == "route" and lab["fault"]["type_raw"] == "f3"


def test_roots_are_candidates_or_explained(real):
    for u, lab in real["labels"].items():
        if lab["eval_tier"] != "A":
            continue
        if lab["root_cause"]["primary_root_service"] not in real["incs"][u]["candidates"]["services"]:
            assert any(f["code"] == "ROOT_NOT_CANDIDATE" for f in real["q"][u]["findings"]), u


def test_label_artifacts_recorded(real):
    assert sum(1 for l in real["labels"].values() if l["label_artifacts"]) == 8


def _canon_metric_frame(t, set_name):
    t = t.filter(pc.equal(t["metric_set"], set_name))
    names = [f"{e}_{m}" for e, m in zip(t["entity_raw"].to_pylist(), t["metric"].to_pylist())]
    return t["ts_ns"].to_numpy() // 10**9, np.asarray(names, dtype=object), t["value"].to_numpy(zero_copy_only=False).astype(float)


def _compare_case(real, hf_dir: Path, uid: str) -> set[str]:
    classes = set()
    store, inc = real["store"], real["incs"][uid]
    sid = real["labels"][uid]["source_incident_id"]
    if sid.split(":", 1)[1] != hf_dir.name:
        classes.add("renamed_case")
    if (hf_dir / "inject_time.txt").read_text(encoding="utf-8").strip() != inc["time"]["anchor_original"]["value"]:
        classes.add("truncated_inject_time")
    if real["labels"][uid]["label_artifacts"]:
        classes.add("root_cause_txt")
    # metrics: HF columns must be a subset of one canonical metric set, with equal values
    hm = pq.read_table(hf_dir / "metrics.parquet")
    t = store.telemetry(uid, "metrics")
    ok_set = None
    for ms in inc["telemetry"]["metrics"]["metric_sets"]:
        ts, names, vals = _canon_metric_frame(t, ms)
        if set(hm.column_names) - {"time"} <= set(names):
            ok_set = (ts, names, vals)
            if set(hm.column_names) - {"time"} != set(names):
                classes.add("omitted_aux")
            break
    if ok_set is None:
        return classes | {"metric_columns_differ"}
    ts, names, vals = ok_set
    hts = hm["time"].to_numpy()
    for col in [c for c in hm.column_names if c != "time"][:40]:
        sel = names == col
        canon = dict(zip(ts[sel].tolist(), vals[sel].tolist()))
        hv = hm[col].to_numpy(zero_copy_only=False).astype(float)
        for x, v in zip(hts.tolist(), hv.tolist()):
            c = canon.get(x)
            if c is None:
                if not np.isnan(v):
                    return classes | {f"metric_row_missing:{col}"}
                continue
            if not (np.isnan(c) and np.isnan(v)) and not np.isclose(c, v, rtol=1e-9, atol=0):
                return classes | {f"metric_value_differs:{col}"}
    # logs: (timestamp, container, message) in source order
    hl = hf_dir / "logs.parquet"
    st = inc["telemetry"]["logs"]["status"]
    if st == "present" and not hl.is_file():
        classes.add("hf_missing_logs")
    elif hl.is_file():
        # HF keeps log time in whole seconds (rounded) and drops quote characters (" and ') at the
        # edges of a message, e.g. raw CSV `..."""`; the canonical message keeps them as parsed
        h = pq.read_table(hl)
        c = store.telemetry(uid, "logs").sort_by([("src_file", "ascending"), ("src_row", "ascending")])
        hm, cm = h["message"].to_pylist(), c["message"].to_pylist()
        if h.num_rows != c.num_rows or any(abs(a * 10**9 - b) > 5 * 10**8
                                           for a, b in zip(h["timestamp"].to_pylist(), c["ts_ns"].to_pylist())):
            classes.add("logs_differ")
        elif hm != cm:
            if all(a == b or (a or "").strip("\"'") == (b or "").strip("\"'") for a, b in zip(hm, cm)):
                classes.add("hf_log_quoting")
            else:
                classes.add("logs_differ")
    # traces
    ht = hf_dir / "traces.parquet"
    st = inc["telemetry"]["traces"]["status"]
    if st == "empty" and not ht.is_file():
        classes.add("header_only_traces")
    elif st == "present" and ht.is_file():
        h = pq.read_table(ht, columns=["spanID", "startTime", "duration"])
        c = store.telemetry(uid, "traces", columns=["span_id", "ts_ns", "duration_ns", "src_row"]).sort_by("src_row")
        if h.num_rows != c.num_rows or h["spanID"].to_pylist() != c["span_id"].to_pylist() \
                or [int(float(x)) * 1000 for x in h["startTime"].to_pylist()[:5000]] != c["ts_ns"].to_pylist()[:5000]:
            classes.add("traces_differ")
    elif (st == "present") != ht.is_file():
        classes.add("traces_presence_differs")
    return classes


@pytest.mark.skipif(not HF.is_dir(), reason="HF copy not present")
def test_hf_parity_on_seeded_sample(real):
    by_time = {}
    for u, inc in real["incs"].items():
        if real["q"][u]["state"] != "REJECT":
            by_time.setdefault(inc["time"]["anchor_original"]["value"], []).append(u)
    by_name = {sid.split(":", 1)[1]: u for sid, u in real["by_sid"].items()}
    hf_cases = sorted(p for p in HF.iterdir() if p.is_dir() and (p / "inject_time.txt").is_file())
    assert len(hf_cases) == 735
    sample = random.Random(20261014).sample(hf_cases, 20)
    sample += [HF / "re3tt_ts-route-service_f3_4", HF / "re1ob_currencyservice_loss_1", HF / "re2tt_ts-auth-service_cpu_1"]
    seen = Counter()
    for d in sample:
        t = (d / "inject_time.txt").read_text(encoding="utf-8").strip()
        uids = by_time.get(t) or ([by_name[d.name]] if d.name in by_name else [])
        assert len(uids) == 1, d.name
        classes = _compare_case(real, d, uids[0])
        assert classes <= KNOWN, (d.name, classes - KNOWN)
        seen.update(classes)
    assert {"renamed_case", "truncated_inject_time", "hf_missing_logs"} <= set(seen)
