"""AIOps2025 adapter on a synthetic extracted tree: five labels (service, node, multi-entity across UTC+8
midnight, TiDB pod, a day without an archive)."""
from __future__ import annotations

import copy
import json

import pyarrow.compute as pc
import pytest

from fixtures.agenticops_fixtures import AIOPS_LABELS, aiops_tree
from rca import evidence, prep
from rca.legacy_view import evidence_kwargs, legacy_telemetry, visible_case
from rca.store import CanonicalStore

DS = "aiops2025"


def aiops_config() -> dict:
    cfg = prep.load_config()
    cfg["datasets"][DS]["root"] = "agenticopseval-test/AIOps2025"
    cfg["_hash"] = prep.config_hash(cfg)
    return cfg


def _build(dh, labels=None):
    aiops_tree(dh, labels)
    receipt = prep.build_dataset(DS, aiops_config(), dh, max_workers=1, log=lambda *a: None)
    store = CanonicalStore(dh)
    labels = store.labels(DS)
    return {"dh": dh, "receipt": receipt, "store": store, "labels": labels, "q": store.quality(DS),
            "by_key": {l["source_incident_id"].split(":", 1)[1]: u for u, l in labels.items()}}


@pytest.fixture(scope="module")
def aiops_home(tmp_path_factory):
    return _build(tmp_path_factory.mktemp("aiops"))


def _codes(h, key):
    return [f["code"] for f in h["q"][h["by_key"][key]]["findings"]]


def test_labels_tiers_and_states(aiops_home):
    h = aiops_home
    assert h["receipt"]["counts"]["incidents"] == 5 and h["receipt"]["exceptions"] == 0
    lab = {k: h["labels"][u] for k, u in h["by_key"].items()}
    assert lab["a-svc"]["root_cause"]["primary_root_service"] == "checkout" and lab["a-svc"]["eval_tier"] == "A"
    assert lab["c-node"]["eval_tier"] == "B" and lab["c-node"]["root_cause"]["primary_root_service"] is None
    b = lab["b-net"]
    assert b["root_cause"]["root_service_ids"] == ["cart", "rediscart"] and b["root_cause"]["primary_root_service"] is None
    assert b["eval_tier_reason"] == "set-scoring-only"
    d = lab["d-pod"]
    assert d["root_cause"]["primary_root_service"] == "tidbtikv" and d["root_cause"]["label_granularity"] == "pod"
    assert d["fault"] == {"type_raw": "io fault", "family": "disk-io"}
    for k in ("a-svc", "b-net", "c-node", "d-pod"):
        assert h["q"][h["by_key"][k]]["state"] in ("ACCEPT", "ACCEPT_WITH_WARNINGS"), h["q"][h["by_key"][k]]
    assert h["q"][h["by_key"]["e-gap"]]["state"] == "REJECT" and "NO_TELEMETRY" in _codes(h, "e-gap")
    assert "LABEL_ARTIFACT_PRESENT" in _codes(h, "a-svc")


def test_window_is_fixed_and_end_time_is_eval_only(aiops_home):
    h = aiops_home
    for key, g in ((g["uuid"], g) for g in AIOPS_LABELS):
        inc = h["store"].incident(h["by_key"][key])
        t = inc["time"]
        assert t["anchor_kind"] == "injection" and t["end_ns"] is None and inc["context"]["visible_text"] is None
        assert t["window"]["start_ns"] == t["anchor_ns"] - 1200 * 10**9                 # never from end_time
        assert t["window"]["end_ns"] == t["anchor_ns"] + 600 * 10**9 + 999_999_999
        assert h["labels"][h["by_key"][key]]["truth_time"]["end_ns"] is not None


def test_window_across_utc8_midnight_reads_both_days(aiops_home):
    h = aiops_home
    u = h["by_key"]["b-net"]
    src = [json.loads(line) for line in open(h["store"].root / DS / "eval_only" / "source_index.jsonl", encoding="utf-8")]
    members = [m["member"] for r in src if r["incident_uid"] == u for m in r["members"]]
    assert any("2025-06-06_23-00-00" in m for m in members) and any("2025-06-07_00-00-00" in m for m in members)
    assert any("metric-parquet/apm/service/service_cartservice_2025-06-07" in m for m in members)
    assert not any("/._" in m for m in members)
    inc = h["store"].incident(u)
    assert not inc["time"]["window"]["clipped_start"] and not inc["time"]["window"]["clipped_end"]
    lg = h["store"].telemetry(u, "logs")
    w = inc["time"]["window"]
    assert pc.min(lg["ts_ns"]).as_py() < inc["time"]["anchor_ns"] < pc.max(lg["ts_ns"]).as_py() <= w["end_ns"]


def test_identity_rules(aiops_home):
    h = aiops_home
    sm = json.loads((h["store"].root / DS / "visible" / "service_map.json").read_text(encoding="utf-8"))["hipstershop"]
    assert sm["redis"] == {"service_id": "rediscart", "rule": "peer-service-tag", "kind": "service"}
    assert sm["10.233.1.1:10080"]["service_id"] == "tidbtidb" and sm["10.233.1.1:10080"]["rule"] == "tidb-status-port"
    assert sm["10.233.1.2:20180"]["service_id"] == "tidbtikv"           # block cache rows filed under object_type tidb
    assert sm["tidb-pd-0"]["service_id"] == "tidbpd"
    assert sm["checkoutservice-0"]["service_id"] == "checkout"         # " (deleted)" suffix stripped
    assert sm["example-ant-29160960-lpx4l"]["service_id"] is None
    assert h["receipt"].get("collisions", {}) in ({}, {"hipstershop": {}}) or not any(h["receipt"]["collisions"].values())
    inc = h["store"].incident(h["by_key"]["d-pod"])
    assert {"tidbtidb", "tidbtikv", "tidbpd", "rediscart", "checkout"} <= set(inc["candidates"]["services"])
    m = h["store"].telemetry(h["by_key"]["d-pod"], "metrics")
    node = m.filter(pc.equal(m["entity_raw"], "aiops-k8s-01"))
    assert node.num_rows and set(node["metric_set"].to_pylist()) == {"node"} and node["service_id"].null_count == node.num_rows


def test_trace_status_and_parents(aiops_home):
    h = aiops_home
    tr = h["store"].telemetry(h["by_key"]["a-svc"], "traces")
    st = set(tr["status_code"].to_pylist())
    assert {"200", "500", "0"} <= st and "2" in st                     # http, grpc, error=true
    redis = tr.filter(pc.equal(tr["entity_raw"], "redis"))
    assert set(redis["service_id"].to_pylist()) == {"rediscart"} and redis["parent_span_id"].null_count == 0


def test_evidence_builds_and_carries_no_label_text(aiops_home):
    h = aiops_home
    kw = evidence_kwargs(prep.load_config(), DS)
    assert kw == {"log_trace_segment_gap_s": 60.0}
    for key in ("a-svc", "b-net", "c-node", "d-pod"):
        u = h["by_key"][key]
        ev = evidence.build(visible_case(h["store"].incident(u)), legacy_telemetry(h["store"], u), **kw)
        assert ev["features"]["has_metrics"] == ev["features"]["has_logs"] == ev["features"]["has_traces"] == 1
        for g in AIOPS_LABELS:
            for text in g["fault_description"]:
                assert text not in ev["text"]
        assert "network loss" not in ev["text"] and "code error" not in ev["text"]


def test_visible_outputs_invariant_to_label_content(aiops_home, tmp_path):
    """Data-flow check: change every label field except `uuid` and `start_time` (the anchor); every
    file under visible/ must stay byte-identical."""
    pert = copy.deepcopy(AIOPS_LABELS)
    swap = {"checkoutservice": "frontend", "cartservice": "checkoutservice", "redis-cart": "frontend",
            "redis-cart-0": "frontend-0", "tidb-tikv-0": "tidb-pd-0", "tidb-tikv": "tidb-tidb", "frontend-0": "cartservice-0"}
    for g in pert:
        g["fault_type"] = "jvm gc" if g["fault_type"] != "jvm gc" else "dns error"
        g["instance_type"] = {"service": "pod", "pod": "service", "node": "service"}[g["instance_type"]]
        g["instance"] = [swap.get(x, "cartservice") for x in g["instance"]] if isinstance(g["instance"], list) else swap.get(g["instance"], "cartservice")
        g["service"] = "frontend" if g["service"] != "frontend" else ""
        g["end_time"] = g["start_time"][:-3] + "59Z"
        g["key_observations"], g["key_metrics"], g["fault_description"] = [{"type": "metric"}], ["rrt_max"], ["other text"]
        g["fault_category"], g["source"], g["destination"] = "x", "frontend", "cartservice"
    p = _build(tmp_path / "perturbed", pert)
    assert p["labels"] != aiops_home["labels"]                          # the perturbation reached the labels

    assert visible_files(aiops_home["store"], DS) == visible_files(p["store"], DS)


def visible_files(store, ds) -> dict:
    """Every file under visible/, byte for byte, except `repro` in the incident records: its digests
    hash all input files, the label file included, and carry no recoverable label content."""
    root = store.root / ds / "visible"
    out = {}
    for f in sorted(root.rglob("*")):
        if f.is_file():
            out[f.relative_to(root).as_posix()] = f.read_bytes()
    out["incidents.jsonl"] = [{k: v for k, v in json.loads(line).items() if k != "repro"}
                              for line in out["incidents.jsonl"].decode("utf-8").splitlines()]
    return out


def test_rebuild_is_noop_and_deterministic(aiops_home):
    h = aiops_home
    before = h["store"].build(DS)["dataset_digest"]
    r = prep.build_dataset(DS, aiops_config(), h["dh"], max_workers=1, log=lambda *a: None)
    assert r["dataset_digest"] == before
