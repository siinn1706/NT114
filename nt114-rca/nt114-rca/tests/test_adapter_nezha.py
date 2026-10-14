"""Nezha adapter on a Nezha-shaped fixture tree (two OB incidents 8 minutes apart, one clipped TT incident)."""
from __future__ import annotations

import pyarrow.compute as pc
import pytest

from fixtures.build_fixtures import NEZHA_OB_PODS, NEZHA_TT_PODS, nezha_tree
from rca import evidence, prep
from rca.adapters.nezha import go_time_ns, metric_name
from rca.legacy_view import legacy_telemetry, visible_case
from rca.store import CanonicalStore


def nezha_config(root_rel: str = "raw/nezha-test/rca_data") -> dict:
    cfg = prep.load_config()
    cfg["datasets"]["nezha"]["root"] = root_rel
    cfg["_hash"] = prep.config_hash(cfg)
    return cfg


@pytest.fixture(scope="module")
def nezha_home(tmp_path_factory):
    dh = tmp_path_factory.mktemp("nz")
    nezha_tree(dh / "raw" / "nezha-test")
    receipt = prep.build_dataset("nezha", nezha_config(), dh, max_workers=1, log=lambda *a: None)
    store = CanonicalStore(dh)
    labels = store.labels("nezha")
    by_sid = {l["source_incident_id"]: u for u, l in labels.items()}
    return {"dh": dh, "receipt": receipt, "store": store, "labels": labels, "q": store.quality("nezha"), "by_sid": by_sid}


def _findings(h, sid, code):
    return [f for f in h["q"][h["by_sid"][sid]]["findings"] if f["code"] == code]


def test_metric_name_and_go_time():
    assert metric_name("CpuUsageRate(%)") == ("cpu-usage-rate-pct", "%")
    assert metric_name("PodServerLatencyP90(s)") == ("pod-server-latency-p90-s", "s")
    assert metric_name("SyscallRead") == ("syscall-read", None)
    assert go_time_ns("2022-08-22 03:51:19.607158889 +0000 UTC m=+0.11") == 1661140279_607158889


def test_discovery_labels_and_systems(nezha_home):
    h = nezha_home
    assert h["receipt"]["counts"]["incidents"] == 3 and h["receipt"]["exceptions"] == 0
    a = h["labels"][h["by_sid"]["nezha:2022-08-22:03:0"]]
    assert a["root_cause"]["primary_root_service"] == "cart" and a["root_cause"]["label_granularity"] == "pod"
    assert a["fault"] == {"type_raw": "cpu_contention", "family": "cpu"} and a["eval_tier"] == "A"
    assert a["label_artifacts"] and a["label_artifacts"][0]["kind"] == "nezha:root_cause_hipster.json"
    t = h["labels"][h["by_sid"]["nezha:2023-01-30:11:0"]]
    assert t["root_cause"]["primary_root_service"] == "contacts" and t["fault"]["family"] == "network-delay"
    incs = {i["incident_uid"]: i for i in h["store"].incidents("nezha", states=None)}
    assert incs[h["by_sid"]["nezha:2023-01-30:11:0"]]["system"] == "train-ticket"
    for u, lab in h["labels"].items():
        assert lab["root_cause"]["primary_root_service"] in incs[u]["candidates"]["services"]


def test_anchor_from_inject_time_and_contamination(nezha_home):
    h = nezha_home
    b = h["by_sid"]["nezha:2022-08-22:04:0"]
    inc = h["store"].incident(b)
    assert inc["time"]["anchor_ns"] == 1661140914 * 10**9          # 2022-08-22 04:01:54 UTC
    assert _findings(h, "nezha:2022-08-22:04:0", "ANCHOR_FIELD_DISAGREE")
    assert not _findings(h, "nezha:2022-08-22:03:0", "ANCHOR_FIELD_DISAGREE")
    # B is 480 s after A: A falls in B's evidence window, B is outside A's (post 300 s)
    assert "03/0" in _findings(h, "nezha:2022-08-22:04:0", "BASELINE_CONTAMINATED")[0]["detail"]
    assert not _findings(h, "nezha:2022-08-22:03:0", "BASELINE_CONTAMINATED")


def test_clipped_window_at_stream_end(nezha_home):
    h = nezha_home
    inc = h["store"].incident(h["by_sid"]["nezha:2023-01-30:11:0"])
    assert inc["time"]["window"]["clipped_end"] and not inc["time"]["window"]["clipped_start"]
    assert _findings(h, "nezha:2023-01-30:11:0", "WINDOW_CLIPPED")


def test_metrics_use_time_string(nezha_home):
    h = nezha_home
    u = h["by_sid"]["nezha:2022-08-22:03:0"]
    t = h["store"].telemetry(u, "metrics")
    ad = t.filter(pc.equal(t["entity_raw"], NEZHA_OB_PODS[2]))
    # TimeStamp of this pod is +2e8 s; stored times follow the Time string, inside the window
    w = h["store"].incident(u)["time"]["window"]
    assert ad.num_rows and pc.min(ad["ts_ns"]).as_py() >= w["start_ns"] and pc.max(ad["ts_ns"]).as_py() <= w["end_ns"]
    off = _findings(h, "nezha:2022-08-22:03:0", "TS_COLUMN_OFFSET")
    assert off and off[0]["severity"] == "info" and "adservice" in off[0]["detail"]
    assert set(pc.unique(t["metric"]).to_pylist()) >= {"cpu-usage-rate-pct", "memory-usage-mi", "pod-server-latency-p90-s"}
    kpi = t.filter(pc.equal(t["metric_set"], "kpi"))
    assert kpi.num_rows and kpi["service_id"].null_count == kpi.num_rows


def test_traces_and_logs(nezha_home):
    h = nezha_home
    u = h["by_sid"]["nezha:2022-08-22:03:0"]
    tr = h["store"].telemetry(u, "traces")
    roots = tr.filter(pc.equal(tr["entity_raw"], NEZHA_OB_PODS[0]))
    assert roots["parent_span_id"].null_count == roots.num_rows
    d = pc.subtract(tr["duration_ns"], 321).to_numpy() % 1000
    assert (d == 0).all()                                             # End - Start, not Duration * 1000
    lg = h["store"].telemetry(u, "logs")
    msgs = set(lg["message"].to_pylist())
    assert "request 1 complete" in msgs and any(m.startswith("not-json") for m in msgs)
    assert _findings(h, "nezha:2022-08-22:03:0", "PARSE_ERROR")
    t_lg = h["store"].telemetry(h["by_sid"]["nezha:2023-01-30:11:0"], "logs")
    assert set(t_lg["level"].to_pylist()) == {"info", "error"}


def test_legacy_view_and_evidence(nezha_home):
    h = nezha_home
    u = h["by_sid"]["nezha:2022-08-22:03:0"]
    inc = h["store"].incident(u)
    tel = legacy_telemetry(h["store"], u)
    m = tel["metrics"]
    assert "cart_cpu-usage-rate-pct" in m.columns and (m["time"] % 60 == 0).all()
    assert not any(c.startswith("frontend-") for c in m.columns)
    ev = evidence.build(visible_case(inc), tel)
    assert ev["features"]["has_metrics"] == ev["features"]["has_logs"] == ev["features"]["has_traces"] == 1


def test_records_are_schema_valid_and_not_rejected(nezha_home):
    h = nezha_home
    for u, q in h["q"].items():
        assert not [f for f in q["findings"] if f["code"] in ("SCHEMA_INVALID", "ADAPTER_EXCEPTION", "INVARIANT_VIOLATION")], q
        assert q["state"] in ("ACCEPT", "ACCEPT_WITH_WARNINGS"), q
    inc = h["store"].incident(h["by_sid"]["nezha:2022-08-22:04:0"])
    assert inc["time"]["anchor_original"] == {"value": "2022-08-22 04:01:54", "unit": "iso8601", "tz": "UTC"}


def test_torn_csv_row_dropped_and_reported(nezha_home):
    h = nezha_home
    sid = "nezha:2023-01-30:11:0"
    pe = [f for f in _findings(h, sid, "PARSE_ERROR") if "malformed CSV" in f["detail"]]
    assert len(pe) == 1 and pe[0]["modality"] == "logs" and pe[0]["severity"] == "warn"
    assert "2023-01-30/log/11_40_log.csv data row 0 (10 fields, header 8)" in pe[0]["detail"]
    lg = h["store"].telemetry(h["by_sid"][sid], "logs")
    t1140 = _utc_s("2023-01-30 11:40:00")
    rows = lg.filter(pc.and_(pc.greater_equal(lg["ts_ns"], t1140 * 10**9), pc.less(lg["ts_ns"], (t1140 + 60) * 10**9)))
    # the torn row (pod 0) is gone; the next row keeps its raw data-row index 1
    assert rows["entity_raw"].to_pylist() == [NEZHA_TT_PODS[1]] and rows["src_row"].to_pylist() == [1]
    assert h["q"][h["by_sid"][sid]]["state"] == "ACCEPT_WITH_WARNINGS"


def test_overflowed_log_time_recovered_from_timestamp(nezha_home):
    h = nezha_home
    sid = "nezha:2023-01-30:11:0"
    lg = h["store"].telemetry(h["by_sid"][sid], "logs")
    want = (_utc_s("2023-01-30 11:45:00") + 6) * 10**9 + 295_000_000
    hit = lg.filter(pc.equal(lg["ts_ns"], want))
    assert hit.num_rows == 1 and hit["entity_raw"][0].as_py() == NEZHA_TT_PODS[1]
    f = _findings(h, sid, "TS_COLUMN_OFFSET")
    assert f and f[0]["modality"] == "logs" and f[0]["severity"] == "info" and f[0]["detail"].startswith("1 log rows")
    assert not _findings(h, sid, "TS_OUT_OF_RANGE")


def test_visible_outputs_invariant_to_label_content(nezha_home, tmp_path):
    """Data-flow check: change every label field except the anchor (`inject_time`) and the label
    artefacts; every model-visible output must stay byte-identical."""
    import json
    dh = tmp_path / "perturbed"
    root = nezha_tree(dh / "raw" / "nezha-test")
    for fl in root.glob("*/*-fault_list.json"):
        data = json.loads(fl.read_text(encoding="utf-8"))
        for entries in data.values():
            for e in entries:
                pods = NEZHA_TT_PODS if e["inject_pod"].startswith("ts-") else NEZHA_OB_PODS
                e["inject_pod"] = pods[(pods.index(e["inject_pod"]) + 1) % len(pods)]
                e["inject_type"] = "exception" if e["inject_type"] != "exception" else "cpu_consumed"
                e["inject_timestamp"] = "0"
        fl.write_text(json.dumps(data), encoding="utf-8")
    for art in (root.parent / "construct_data").glob("*.json"):
        art.write_text(json.dumps({"someservice": {"other": "OtherMetric(ms)"}}), encoding="utf-8")
    prep.build_dataset("nezha", nezha_config(), dh, max_workers=1, log=lambda *a: None)
    pert = CanonicalStore(dh)
    assert pert.labels("nezha") != nezha_home["labels"]           # the perturbation reached the labels

    def visible(store):
        out = {}
        for inc in store.incidents("nezha", states=None):
            out[inc["incident_uid"]] = {k: inc[k] for k in ("candidates", "context", "system", "dataset_subset", "time",
                                                            "source_id", "telemetry")}
        sm = (store.root / "nezha" / "visible" / "service_map.json").read_bytes()
        return out, sm
    assert visible(pert) == visible(nezha_home["store"])


def _utc_s(s: str) -> int:
    from datetime import datetime, timezone
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())


def test_rebuild_is_noop_and_deterministic(nezha_home):
    h = nezha_home
    before = h["store"].build("nezha")["dataset_digest"]
    r = prep.build_dataset("nezha", nezha_config(), h["dh"], max_workers=1, log=lambda *a: None)
    assert r["dataset_digest"] == before
