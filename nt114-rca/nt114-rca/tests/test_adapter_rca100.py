"""RCA100 adapter on a synthetic pre-cut tree: four cases (service root, pod root outside the topology,
node root with an export ending before the alert, a disagreeing alert_trigger_time) and two metric
groups that are exported only in the case of one fault."""
from __future__ import annotations

import copy
import json

import pyarrow.compute as pc
import pytest

from fixtures.agenticops_fixtures import RCA100_CASES, rca100_tree
from rca import evidence, prep
from rca.legacy_view import evidence_kwargs, legacy_telemetry, visible_case
from rca.store import CanonicalStore
from test_adapter_aiops2025 import visible_files

DS = "rca100"


def rca100_config() -> dict:
    cfg = prep.load_config()
    cfg["datasets"][DS]["root"] = "agenticopseval-test/RCA100"
    cfg["_hash"] = prep.config_hash(cfg)
    return cfg


def _build(dh, cases=None):
    rca100_tree(dh, cases)
    receipt = prep.build_dataset(DS, rca100_config(), dh, max_workers=1, log=lambda *a: None)
    store = CanonicalStore(dh)
    labels = store.labels(DS)
    by_case = {lab["source_incident_id"].split(":", 1)[1]: u for u, lab in labels.items()}
    return {"dh": dh, "receipt": receipt, "store": store, "labels": labels, "q": store.quality(DS), "by_case": by_case}


@pytest.fixture(scope="module")
def rca_home(tmp_path_factory):
    return _build(tmp_path_factory.mktemp("rca100"))


def _uid(h, task):
    return h["by_case"][RCA100_CASES[task][0]]


def _findings(h, task, code):
    return [f for f in h["q"][_uid(h, task)]["findings"] if f["code"] == code]


def test_labels_and_tiers(rca_home):
    h = rca_home
    assert h["receipt"]["counts"]["incidents"] == 4 and h["receipt"]["exceptions"] == 0
    a = h["labels"][_uid(h, "t001")]
    assert a["root_cause"]["primary_root_service"] == "payment" and a["eval_tier"] == "A"
    assert a["fault"] == {"type_raw": "F014-httpError5xx", "family": "code-defect"}
    assert a["root_cause"]["original"] == {"root_cause_entities": ["payment"], "expected_fault_id": "F014-httpError5xx"}
    b = h["labels"][_uid(h, "t002")]
    assert b["root_cause"]["primary_root_service"] == "cart" and b["root_cause"]["label_granularity"] == "pod"
    c = h["labels"][_uid(h, "t003")]
    assert c["eval_tier"] == "B" and c["root_cause"]["primary_root_service"] is None
    for t in RCA100_CASES:
        assert h["q"][_uid(h, t)]["state"] in ("ACCEPT", "ACCEPT_WITH_WARNINGS"), h["q"][_uid(h, t)]


def test_alert_anchor_and_fixed_window(rca_home):
    h = rca_home
    from fixtures.agenticops_fixtures import _utc
    for t, (_, _, alert_iso, _, _) in RCA100_CASES.items():
        inc = h["store"].incident(_uid(h, t))
        tm = inc["time"]
        assert tm["anchor_kind"] == "alert" and tm["anchor_ns"] == _utc(alert_iso) * 10**9 and tm["end_ns"] is None
        assert tm["window"]["start_ns"] == tm["anchor_ns"] - 900 * 10**9 and tm["window"]["end_ns"] == tm["anchor_ns"] + 120 * 10**9
    assert _findings(h, "t004", "ANCHOR_FIELD_DISAGREE") and "= 30 s" in _findings(h, "t004", "ANCHOR_FIELD_DISAGREE")[0]["detail"]
    assert not _findings(h, "t001", "ANCHOR_FIELD_DISAGREE")


def test_visible_text_is_alert_title_and_entity_only(rca_home):
    h = rca_home
    inc = h["store"].incident(_uid(h, "t001"))
    assert inc["context"]["visible_text"] == "frontend 错误次数告警 | frontend::/api/op"
    for t in RCA100_CASES:
        text = h["store"].incident(_uid(h, t))["context"]["visible_text"]
        assert "F0" not in text and "prompt" not in text


def test_label_following_metric_groups_are_dropped(rca_home):
    h = rca_home
    for t, name in (("t002", "pod_restart_count"), ("t004", "arms_exception_requests_error_count_raw")):
        f = _findings(h, t, "METRIC_GROUP_DROPPED")
        assert f and name in f[0]["detail"] and f[0]["severity"] == "info"
        m = h["store"].telemetry(_uid(h, t), "metrics")
        assert name not in set(m["metric"].to_pylist())
    assert not _findings(h, "t001", "METRIC_GROUP_DROPPED")
    m = h["store"].telemetry(_uid(h, "t001"), "metrics")
    chaos = m.filter(pc.equal(m["entity_raw"], "chaosblade-operator"))
    assert chaos.num_rows and chaos["service_id"].null_count == chaos.num_rows


def test_export_cut_is_reported_and_evidence_makes_no_claim(rca_home):
    h = rca_home
    f = _findings(h, "t003", "LOW_COVERAGE")
    assert any("before the anchor" in x["detail"] and "source export stops" in x["detail"] for x in f)
    assert any("58 s after the anchor" in x["detail"] for x in _findings(h, "t002", "LOW_COVERAGE"))
    kw = evidence_kwargs(prep.load_config(), DS)
    u = _uid(h, "t003")
    ev = evidence.build(visible_case(h["store"].incident(u)), legacy_telemetry(h["store"], u), **kw)
    assert "recorded log data covers less than 30 s after incident start" in ev["text"]
    assert "recorded trace data covers less than 30 s after incident start" in ev["text"]
    assert "no spans after incident start" not in ev["text"] and "disappeared" not in ev["text"]


def test_long_metrics_reach_evidence_by_service(rca_home):
    h = rca_home
    u = _uid(h, "t001")
    m = legacy_telemetry(h["store"], u)["metrics"]
    assert (m["time"] % 30 == 0).all() and "payment_latency" in m.columns
    assert not any(c.startswith(("chaosblade", "none_", "cn-hongkong")) for c in m.columns)
    t = h["store"].incident(u)["time"]["anchor_ns"] // 10**9
    assert ((m["time"] >= t) & (m["time"] <= t + 120)).sum() >= 3           # enough post-anchor points to score
    assert len(evidence.metric_scores(m, t))


def test_visible_outputs_invariant_to_label_content(rca_home, tmp_path):
    """Data-flow check: change every answer-key field (root entities, fault id in the case id, window);
    every file under visible/ must stay byte-identical."""
    pert = copy.deepcopy(RCA100_CASES)
    roots = {"t001": ["cn-hongkong.10.0.2.71"], "t002": ["inventory"], "t003": ["checkout-64944cd445-abcde"], "t004": ["payment"]}
    for k, (t, c) in enumerate(sorted(pert.items())):
        fault = ["F034-cpuFullLoad", "F057-dnsResolutionFailure", "F010-slowSQL", "F001-nodeDown"][k]
        pert[t] = (f"{fault}.{c[0].split('.', 1)[1]}", roots[t], c[2], c[3], c[4])
    p = _build(tmp_path / "perturbed", pert)
    assert p["labels"] != rca_home["labels"]
    assert visible_files(rca_home["store"], DS) == visible_files(p["store"], DS)


def test_tasks_cut_from_one_injection_share_a_group(rca_home, tmp_path):
    """A second task of t001's injection (same first alert, identical events export, other alert
    focus) gets the same label-free group id; the audit explains the pair and splits keep it together."""
    from rca import audit, splits
    assert {lab["group"]["group_id"] for lab in rca_home["labels"].values()} == {None}
    cases = {**RCA100_CASES, "t005": ("F014-httpError5xx.eee", ["payment"], *RCA100_CASES["t001"][2:])}
    h = _build(tmp_path / "shared", cases)
    g = {c: h["labels"][u]["group"]["group_id"] for c, u in h["by_case"].items()}
    assert g["F014-httpError5xx.aaa"] == g["F014-httpError5xx.eee"] == "rca100-injection:t001"
    assert [v for c, v in g.items() if "httpError5xx" not in c] == [None] * 3
    rows = [(i, h["labels"][i["incident_uid"]]) for i in h["store"].incidents(DS, states=None)]
    d = audit.duplicates(rows)
    assert d["fingerprint"] and d["unexplained"] == 0
    items = splits.eligible(h["store"], DS)
    for it in items:                       # isolate the group-id link from the overlapping-window rule
        it["stream"] = it["uid"]
    groups = splits.group_items(items, "physical")
    pair = [h["by_case"]["F014-httpError5xx.aaa"], h["by_case"]["F014-httpError5xx.eee"]]
    assert groups[pair[0]] == groups[pair[1]] and len(set(groups.values())) == 4


def test_rebuild_is_noop_and_deterministic(rca_home):
    h = rca_home
    before = h["store"].build(DS)["dataset_digest"]
    r = prep.build_dataset(DS, rca100_config(), h["dh"], max_workers=1, log=lambda *a: None)
    assert r["dataset_digest"] == before


def test_time_without_an_offset_is_refused_not_read_as_local_time(tmp_path):
    """Every RCA100 time string carries +08:00; one without an offset would follow the machine's time
    zone, so the incident fails instead of shifting by the runner's offset."""
    cases = {**RCA100_CASES, "t004": (*RCA100_CASES["t004"][:3], "2026-04-25T19:30:30", 120)}
    h = _build(tmp_path / "naive", cases)
    assert h["receipt"]["exceptions"] == 1
    assert "F023-nullPointerException.ddd" not in h["by_case"] and len(h["by_case"]) == 3
    exc = (h["dh"] / "canonical/v1" / DS / "eval_only/exceptions.jsonl").read_text(encoding="utf-8")
    assert len(exc.splitlines()) == 1 and "has no UTC offset" in exc
