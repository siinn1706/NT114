"""Missing-observability operators and the per-incident condition matrix."""
from __future__ import annotations

import hashlib

import pandas as pd
import pytest

from rca import ablate, legacy_view
from rca.splits import condition_matrix, condition_row
from rca.store import CanonicalStore


def _tel():
    tr = pd.DataFrame({"svc": ["a", "a", "a", "b", "b", "c", "c", "c", "d"], "duration": range(9),
                       "parentSpanID": [None, "x", "x", "y", "y", "z", "z", "z", "w"]})
    return {"metrics": pd.DataFrame({"time": [1]}), "logs": pd.DataFrame({"x": [1]}), "traces": tr}


def test_drop_conditions_remove_exactly_one_modality():
    tel = _tel()
    for cond, m in (("no_metric", "metrics"), ("no_log", "logs"), ("no_trace", "traces")):
        out = ablate.apply(tel, cond, "a")
        assert out[m] is None
        for other in {"metrics", "logs", "traces"} - {m}:
            assert out[other] is tel[other]


def test_metrics_only_drops_logs_and_traces_and_keeps_metrics():
    tel = _tel()
    out = ablate.apply(tel, "metrics_only", "a")
    assert out["logs"] is None and out["traces"] is None and out["metrics"] is tel["metrics"]
    assert ablate.applicable("metrics_only", tel)
    assert not ablate.applicable("metrics_only", {**tel, "logs": None, "traces": None})   # would equal full
    assert not ablate.applicable("metrics_only", {**tel, "metrics": None})
    assert ablate.CONDITIONS[:6] == ("full", "no_trace", "no_log", "no_metric", "blind_root", "blind_nonroot")


def test_metrics_only_matrix_rule():
    r = _row(("present", "present", "natural_absent"))
    assert r["conditions"]["metrics_only"] == {"applicable": True, "reason": "ok"}
    r = _row(("present", "natural_absent", "empty"))
    assert r["conditions"]["metrics_only"]["reason"] == "no logs or traces to drop (equals full)"
    r = _row(("natural_absent", "present", "present"), traces=_tel()["traces"])
    assert r["conditions"]["metrics_only"]["reason"] == "metrics natural_absent"


def test_blind_root_equals_mask_of_root_and_keeps_callers():
    tel = _tel()
    out = ablate.apply(tel, "blind_root", "a")
    pd.testing.assert_frame_equal(out["traces"], ablate.mask_service_traces(tel, "a")["traces"])
    assert "a" not in set(out["traces"]["svc"])
    assert out["traces"]["svc"].value_counts().to_dict() == tel["traces"][tel["traces"]["svc"] != "a"]["svc"].value_counts().to_dict()
    assert out["metrics"] is tel["metrics"] and out["logs"] is tel["logs"]


def test_blind_nonroot_target_never_root_and_closest_count():
    tel = _tel()   # a:3, b:2, c:3, d:1 -> closest to root a is c (equal count)
    assert ablate.choose_nonroot_target(tel, "a", "uid-1") == "c"
    for uid in (f"u{i}" for i in range(50)):
        t = ablate.choose_nonroot_target(tel, "b", uid)
        assert t != "b" and t in {"a", "c", "d"}   # a, c, d all differ by 1 from b's 2 spans
        expect = min(["a", "c", "d"], key=lambda s: hashlib.sha256(f"{uid}{s}".encode()).hexdigest())
        assert t == expect
    out = ablate.apply(tel, "blind_nonroot", "a", nonroot_target="c")
    pd.testing.assert_frame_equal(out["traces"], ablate.mask_service_traces(tel, "c")["traces"])
    with pytest.raises(ValueError):
        ablate.apply(tel, "blind_nonroot", "a")
    with pytest.raises(ValueError):
        ablate.apply(tel, "blind_nonroot", "a", nonroot_target="a")


def test_blind_preconditions():
    tel = _tel()
    assert ablate.applicable("blind_root", tel, "a") and ablate.applicable("blind_nonroot", tel, "a")
    assert not ablate.applicable("blind_root", tel, "zz")
    only_root = {**tel, "traces": tel["traces"][tel["traces"]["svc"] == "a"]}
    assert ablate.applicable("blind_root", only_root, "a") and not ablate.applicable("blind_nonroot", only_root, "a")
    assert ablate.choose_nonroot_target(only_root, "a", "u") is None
    assert not ablate.applicable("blind_nonroot", {**tel, "traces": None}, "a")
    assert ablate.applicable("blind_root", tel)          # legacy call without a root keeps its behaviour


def _row(statuses, state="ACCEPT", anchor_kind="injection", codes=(), traces=None, root="a"):
    inc = {"incident_uid": "x.0000000000000001", "time": {"anchor_kind": anchor_kind},
           "telemetry": {m: {"status": s} for m, s in zip(("metrics", "logs", "traces"), statuses)}}
    lab = {"root_cause": {"primary_root_service": root}}
    q = {"state": state, "findings": [{"code": c} for c in codes]}
    return condition_row(inc, lab, q, traces)


def test_condition_rules():
    tr = _tel()["traces"]
    r = _row(("present", "present", "present"), traces=tr)
    assert all(v["applicable"] for v in r["conditions"].values()) and r["nonroot_target"] == "c"
    r = _row(("present", "natural_absent", "natural_absent"))
    assert r["conditions"]["full"]["applicable"]
    assert not r["conditions"]["no_metric"]["applicable"] and "nothing left" in r["conditions"]["no_metric"]["reason"]
    assert r["conditions"]["no_trace"]["reason"] == "traces natural_absent"
    r = _row(("present", "present", "empty"))
    assert r["conditions"]["blind_root"]["reason"] == "traces empty"
    for kw in ({"state": "REJECT"}, {"anchor_kind": "window_start"}, {"codes": ("PRE_WINDOW_SHORT",)}):
        r = _row(("present", "present", "present"), traces=tr, **kw)
        assert not any(v["applicable"] for v in r["conditions"].values()), kw
        assert r["nonroot_target"] is None
    r = _row(("present", "present", "present"), traces=tr, root="zz")
    assert r["conditions"]["blind_root"]["reason"] == "root has no spans"


def test_matrix_on_fixture_build(rcaeval_home):
    store = CanonicalStore(rcaeval_home)
    m = condition_matrix(store, "rcaeval")
    labels = store.labels("rcaeval")
    by_sid = {labels[u]["source_incident_id"]: u for u in labels}
    row = lambda sid: m["incidents"][by_sid[sid]]
    assert not any(v["applicable"] for v in row("rcaeval:re2ob_checkoutservice_cpu_multi-source-data")["conditions"].values())
    assert row("rcaeval:re2ss_orders_mem_1")["conditions"]["no_trace"]["reason"] == "traces natural_absent"
    assert row("rcaeval:re3ss_carts_f1_1")["conditions"]["blind_root"]["reason"] == "traces empty"
    assert row("rcaeval:re3ss_carts_f1_1")["natural"]["traces"] == "empty"
    ob = row("rcaeval:re2ob_cartservice_delay_1")
    assert ob["conditions"]["blind_root"]["applicable"] and ob["conditions"]["blind_nonroot"]["applicable"]
    assert ob["nonroot_target"] not in (None, "cart")
    # the matrix target equals the target chosen from the full telemetry the evidence path loads
    uid = by_sid["rcaeval:re2ob_cartservice_delay_1"]
    tel = legacy_view.legacy_telemetry(store, uid)
    assert ablate.choose_nonroot_target(tel, "cart", uid) == ob["nonroot_target"]
    assert condition_matrix(store, "rcaeval") == m    # deterministic
