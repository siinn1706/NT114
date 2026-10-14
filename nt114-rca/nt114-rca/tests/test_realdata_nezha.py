"""Real-data checks on the canonical Nezha build against the raw `rca_data` tree: counts and states,
anchors from `inject_time`, the torn CSV row of 2023-01-29 10:06, the overflowed `TimeUnixNano` rows,
and row-level parity of a seeded sample of log, trace and metric members."""
from __future__ import annotations

import csv
import json
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.compute as pc
import pytest

from conftest import REAL_DATA
from rca.adapters.nezha import go_time_ns, iso_utc_ns
from rca.schema import TS_MAX_NS, TS_MIN_NS
from rca.store import CanonicalStore

RAW = REAL_DATA / "raw"
TORN = "nezha/git-d8140101fdb4/rca_data/2023-01-29/log/10_06_log.csv"

pytestmark = [pytest.mark.realdata,
              pytest.mark.skipif(not (REAL_DATA / "canonical/v1/nezha/_build.json").is_file(), reason="no real Nezha build")]


@pytest.fixture(scope="module")
def real():
    store = CanonicalStore(REAL_DATA)
    labels = store.labels("nezha")
    incs = {i["incident_uid"]: i for i in store.incidents("nezha", states=None)}
    src = {}
    with open(REAL_DATA / "canonical/v1/nezha/eval_only/source_index.jsonl", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            src[r["incident_uid"]] = r["members"]
    return {"store": store, "labels": labels, "incs": incs, "q": store.quality("nezha"), "src": src}


def _raw_rows(member: str) -> list[dict]:
    csv.field_size_limit(1 << 30)
    with open(RAW / member, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_counts_states_and_labels(real):
    assert len(real["incs"]) == 101
    assert Counter(i["system"] for i in real["incs"].values()) == {"online-boutique": 56, "train-ticket": 45}
    states = Counter(q["state"] for q in real["q"].values())
    assert states["REJECT"] == states["QUARANTINE"] == 0, states
    for u, q in real["q"].items():
        assert not [f for f in q["findings"] if f["code"] in ("SCHEMA_INVALID", "ADAPTER_EXCEPTION", "INVARIANT_VIOLATION")], u
    for u, lab in real["labels"].items():
        assert lab["label_validity"] == "valid" and lab["eval_tier"] == "A"
        assert lab["root_cause"]["primary_root_service"] in real["incs"][u]["candidates"]["services"]


def test_anchor_is_inject_time_utc(real):
    for u, lab in real["labels"].items():
        it = lab["root_cause"]["original"]["inject_time"]
        want = int(datetime.strptime(it, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()) * 10**9
        assert real["incs"][u]["time"]["anchor_ns"] == want


def test_torn_row_dropped_with_finding(real):
    users = [u for u, ms in real["src"].items() if any(m["member"] == TORN for m in ms)]
    assert users
    raw = _raw_rows(TORN)
    with_rows = 0
    for u in users:
        pe = [f for f in real["q"][u]["findings"] if f["code"] == "PARSE_ERROR" and "malformed CSV" in f["detail"]]
        assert pe and "10_06_log.csv data row 629 (10 fields, header 8)" in pe[0]["detail"]
        idx = [k for k, m in enumerate(real["src"][u]) if m["member"] == TORN][0]
        lg = real["store"].telemetry(u, "logs")
        rows = lg.filter(pc.equal(lg["src_file"], idx))
        kept = set(rows["src_row"].to_pylist())
        assert 629 not in kept
        if not kept:            # the file is a spare edge minute whose rows fall outside this window
            continue
        with_rows += 1
        # rows after the torn one keep their raw indices: check one against the raw file
        k = max(kept)
        assert k > 629
        r = rows.filter(pc.equal(rows["src_row"], k))
        assert r["ts_ns"][0].as_py() == int(raw[k]["TimeUnixNano"]) and r["entity_raw"][0].as_py() == raw[k]["PodName"]
    assert with_rows


def test_no_out_of_range_log_times_and_sentinel_rows_recovered(real):
    recovered = 0
    for u, inc in real["incs"].items():
        lg = real["store"].telemetry(u, "logs")
        mn, mx = pc.min(lg["ts_ns"]).as_py(), pc.max(lg["ts_ns"]).as_py()
        assert TS_MIN_NS <= mn and mx < TS_MAX_NS
        f = [x for x in real["q"][u]["findings"] if x["code"] == "TS_COLUMN_OFFSET" and x["modality"] == "logs"]
        recovered += int(f[0]["detail"].split()[0]) if f else 0
        assert not [x for x in real["q"][u]["findings"] if x["code"] == "TS_OUT_OF_RANGE"]
    assert recovered > 0
    # every sentinel row in one raw file is present with its Timestamp-derived time
    member = "nezha/git-d8140101fdb4/rca_data/2023-01-29/log/09_21_log.csv"
    raw = _raw_rows(member)
    sent = [k for k, r in enumerate(raw) if r["TimeUnixNano"].startswith("-")]
    assert sent
    u = next(u for u, ms in real["src"].items() if any(m["member"] == member for m in ms)
             and all(TS_MIN_NS <= iso_utc_ns(raw[k]["Timestamp"]) for k in sent))
    idx = [k for k, m in enumerate(real["src"][u]) if m["member"] == member][0]
    w = real["incs"][u]["time"]["window"]
    lg = real["store"].telemetry(u, "logs")
    rows = lg.filter(pc.equal(lg["src_file"], idx))
    got = dict(zip(rows["src_row"].to_pylist(), rows["ts_ns"].to_pylist()))
    for k in sent:
        want = iso_utc_ns(raw[k]["Timestamp"])
        if w["start_ns"] <= want <= w["end_ns"]:
            assert got.get(k) == want


@pytest.mark.parametrize("modality,role_prefix", [("logs", "logs"), ("traces", "traces"), ("metrics", "metrics:default")])
def test_seeded_row_parity(real, modality, role_prefix):
    rnd = random.Random(20261014)
    uids = rnd.sample(sorted(real["incs"]), 4)
    for u in uids:
        members = real["src"][u]
        cand = [k for k, m in enumerate(members) if m["role"] == role_prefix]
        k = rnd.choice(cand)
        raw = _raw_rows(members[k]["member"])
        t = real["store"].telemetry(u, modality)
        rows = t.filter(pc.equal(t["src_file"], k))
        assert rows.num_rows, (u, members[k]["member"])
        sample = rnd.sample(range(rows.num_rows), min(25, rows.num_rows))
        for j in sample:
            i = rows["src_row"][j].as_py()
            r = raw[i]
            if modality == "logs":
                assert rows["entity_raw"][j].as_py() == r["PodName"]
                want = int(r["TimeUnixNano"]) if not r["TimeUnixNano"].startswith("-") else iso_utc_ns(r["Timestamp"])
                assert rows["ts_ns"][j].as_py() == want
            elif modality == "traces":
                assert rows["span_id"][j].as_py() == r["SpanID"] and rows["entity_raw"][j].as_py() == r["PodName"]
                assert rows["ts_ns"][j].as_py() == int(r["StartTimeUnixNano"])
                assert rows["duration_ns"][j].as_py() == int(r["EndTimeUnixNano"]) - int(r["StartTimeUnixNano"])
            else:
                assert rows["ts_ns"][j].as_py() == go_time_ns(r["Time"]) and rows["entity_raw"][j].as_py() == r["PodName"]
                header = list(r.keys())
                col = header[rows["src_col"][j].as_py()]
                v = rows["value"][j].as_py()
                assert (v is None and r[col] == "") or v == pytest.approx(float(r[col]), nan_ok=True)


def test_lineage_matches_registry_one_to_one(real):
    from rca import audit
    lin = audit.lineage(real["store"], ["nezha"], REAL_DATA / "manifests")["datasets"]["nezha"]
    assert lin["matched_one_to_one"] == 101 and lin["unexplained"] == 0 and lin["registry_only_count"] == 0
    assert not lin["anchor_differences"] and not lin["label_differences"]
    assert lin["anchor_differences_explained"] == {"registry used inject_timestamp": 29}
