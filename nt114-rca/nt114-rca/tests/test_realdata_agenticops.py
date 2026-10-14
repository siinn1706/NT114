"""Real-data checks on the canonical AIOps2025 and RCA100 builds against the raw AgenticOpsEval tree:
counts, states and tiers; anchors and windows that never use label times; label-following metric
groups absent from stored telemetry; no label text in visible records; row parity of sampled members."""
from __future__ import annotations

import json
import random
from collections import Counter
from datetime import datetime
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest

from conftest import REAL_DATA
from rca.adapters.aiops2025 import iso_to_ns
from rca.store import CanonicalStore

RAW = REAL_DATA / "raw" / "agenticopseval" / "gitlab-69cf36430b43"

pytestmark = [pytest.mark.realdata,
              pytest.mark.skipif(not (REAL_DATA / "canonical/v1/aiops2025/_build.json").is_file()
                                 or not (REAL_DATA / "canonical/v1/rca100/_build.json").is_file(),
                                 reason="no real AIOps2025/RCA100 build")]


def _load(ds):
    store = CanonicalStore(REAL_DATA)
    return {"store": store, "labels": store.labels(ds), "q": store.quality(ds),
            "incs": {i["incident_uid"]: i for i in store.incidents(ds, states=None)}}


@pytest.fixture(scope="module")
def aiops():
    return _load("aiops2025")


@pytest.fixture(scope="module")
def rca():
    return _load("rca100")


def _no_bad_findings(h):
    for u, q in h["q"].items():
        assert not [f for f in q["findings"] if f["code"] in ("SCHEMA_INVALID", "ADAPTER_EXCEPTION", "INVARIANT_VIOLATION",
                                                              "SERVICE_ID_COLLISION")], u


# ---------------------------------------------------------------- AIOps2025
def test_aiops_counts_states_tiers(aiops):
    assert len(aiops["incs"]) == 400
    states = Counter(q["state"] for q in aiops["q"].values())
    assert states["REJECT"] == states["QUARANTINE"] == 0, states
    _no_bad_findings(aiops)
    tiers = Counter(l["eval_tier"] for l in aiops["labels"].values())
    assert tiers == {"A": 318, "B": 82}
    assert Counter(l["eval_tier_reason"] for l in aiops["labels"].values())["set-scoring-only"] == 73
    for u, lab in aiops["labels"].items():
        assert lab["label_validity"] == "valid"
        p = lab["root_cause"]["primary_root_service"]
        assert p is None or p in aiops["incs"][u]["candidates"]["services"]


def test_aiops_anchor_window_and_hidden_end(aiops):
    gt = {g["uuid"]: g for g in map(json.loads, open(RAW / "AIOps2025/groundtruth.jsonl", encoding="utf-8"))}
    for u, inc in aiops["incs"].items():
        g = gt[aiops["labels"][u]["source_incident_id"].split(":", 1)[1]]
        t = inc["time"]
        start = int(datetime.fromisoformat(g["start_time"].replace("Z", "+00:00")).timestamp())
        assert t["anchor_ns"] == start * 10**9 and t["end_ns"] is None and inc["context"]["visible_text"] is None
        assert t["window"]["start_ns"] == (start - 1200) * 10**9 and t["window"]["end_ns"] == (start + 600) * 10**9 + 999_999_999
        assert inc["dataset_subset"] == "AIOps2025"
        assert aiops["labels"][u]["truth_time"]["end_ns"] is not None


def test_aiops_visible_records_hold_no_label_text(aiops):
    gt = list(map(json.loads, open(RAW / "AIOps2025/groundtruth.jsonl", encoding="utf-8")))
    texts = {s for g in gt for s in g.get("fault_description", []) if len(s) >= 12}
    texts |= {g["fault_type"] for g in gt}
    vis = (REAL_DATA / "canonical/v1/aiops2025/visible/incidents.jsonl").read_text(encoding="utf-8")
    assert texts and not [t for t in texts if t in vis]


def test_aiops_log_rows_match_raw_members(aiops):
    """Seeded sample: stored log rows equal the raw hourly rows inside the window."""
    src = {r["incident_uid"]: r["members"] for r in map(json.loads, open(REAL_DATA / "canonical/v1/aiops2025/eval_only/source_index.jsonl", encoding="utf-8"))}
    rng = random.Random(7)
    uids = rng.sample(sorted(u for u, i in aiops["incs"].items() if i["telemetry"]["logs"]["status"] == "present"), 3)
    ex = REAL_DATA / "work/extract/agenticopseval/gitlab-69cf36430b43/AIOps2025"
    for u in uids:
        w = aiops["incs"][u]["time"]["window"]
        n = 0
        for m in src[u]:
            if "/log-parquet/" not in m["member"]:
                continue
            arc, rel = m["member"].split("!", 1)
            ts = iso_to_ns(pq.read_table(ex / Path(arc).name.split(".")[0] / rel, columns=["@timestamp"])["@timestamp"])
            ok = pc.and_(pc.greater_equal(ts, w["start_ns"]), pc.less_equal(ts, w["end_ns"]))
            n += pc.sum(pc.fill_null(ok, False).cast("int64")).as_py() or 0
        assert aiops["store"].telemetry(u, "logs").num_rows == n, u


# ---------------------------------------------------------------- RCA100
def test_rca100_counts_states_tiers(rca):
    assert len(rca["incs"]) == 103
    states = Counter(q["state"] for q in rca["q"].values())
    assert states["REJECT"] == states["QUARANTINE"] == 0, states
    _no_bad_findings(rca)
    assert Counter(l["eval_tier"] for l in rca["labels"].values()) == {"A": 86, "B": 17}
    assert Counter(l["root_cause"]["label_granularity"] for l in rca["labels"].values()) == {"service": 83, "node": 17, "pod": 3}
    # class imbalance, preserved as labelled: `inventory` is the raw root in 55 cases and the service
    # of one more pod root (tier-A majority baseline 56/86)
    assert Counter(r for l in rca["labels"].values() for r in l["root_cause"]["original"]["root_cause_entities"])["inventory"] == 55
    roots = Counter(l["root_cause"]["primary_root_service"] for l in rca["labels"].values() if l["eval_tier"] == "A")
    assert roots.most_common(1) == [("inventory", 56)]


def test_rca100_anchor_is_first_occurred_alert(rca):
    mapping = json.loads((RAW / "RCA100/answer_key/mapping.json").read_text(encoding="utf-8"))["task_to_case_id"]
    task_of = {f"rca100:{v}": k for k, v in mapping.items()}
    for u, inc in rca["incs"].items():
        t = task_of[rca["labels"][u]["source_incident_id"]]
        al = pq.read_table(RAW / "RCA100/cases" / t / "alerts.parquet", columns=["status", "time_s"]).to_pylist()
        first = min(a["time_s"] for a in al if a["status"] == "OCCURRED")
        tm = inc["time"]
        assert tm["anchor_kind"] == "alert" and tm["anchor_ns"] == first * 10**9 and tm["end_ns"] is None
        assert tm["window"]["start_ns"] == (first - 900) * 10**9 and tm["window"]["end_ns"] == (first + 120) * 10**9


def test_rca100_label_following_metrics_never_stored(rca):
    for u in rca["incs"]:
        m = rca["store"].telemetry(u, "metrics")
        names = set(pc.unique(m["metric"]).to_pylist())
        assert not names & {"pod_restart_count", "arms_exception_requests_error_count_raw"}, u
    dropped = sum(any(f["code"] == "METRIC_GROUP_DROPPED" for f in q["findings"]) for q in rca["q"].values())
    assert dropped == 6                                   # the 4 nullPointerException + 2 pod-restart cases


def test_rca100_visible_text_is_alert_only(rca):
    for u, inc in rca["incs"].items():
        text = inc["context"]["visible_text"]
        fault = rca["labels"][u]["fault"]["type_raw"]
        assert text and fault not in text and fault.split("-", 1)[1] not in text and "prompt" not in text


def test_rca100_low_coverage_matches_export_end(rca):
    """LOW_COVERAGE 'source export stops' is reported exactly where the raw log export ends > 30 s
    before the window end (paged exports also leave gaps inside the window; those are not this finding)."""
    mapping = json.loads((RAW / "RCA100/answer_key/mapping.json").read_text(encoding="utf-8"))["task_to_case_id"]
    task_of = {f"rca100:{v}": k for k, v in mapping.items()}
    n = 0
    for u, inc in rca["incs"].items():
        t = task_of[rca["labels"][u]["source_incident_id"]]
        end = pc.max(iso_to_ns(pq.read_table(RAW / "RCA100/cases" / t / "logs.parquet", columns=["_time_"])["_time_"])).as_py()
        short = inc["time"]["window"]["end_ns"] - end > 30 * 10**9
        flagged = any(f["code"] == "LOW_COVERAGE" and f.get("modality") == "logs" and "source export stops" in f["detail"]
                      for f in rca["q"][u]["findings"])
        assert short == flagged, u
        n += flagged
    assert n > 0
