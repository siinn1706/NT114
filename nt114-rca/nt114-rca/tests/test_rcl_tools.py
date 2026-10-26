"""Deterministic tools of the RCLAgent adaptation: behaviour, determinism and label independence."""
from __future__ import annotations

import hashlib
import json
import secrets
import shutil

import numpy as np
import pandas as pd

from rca import rcl_path, rcl_tools
from rca import rcl_trace_graph as tg
from rca.legacy_view import legacy_telemetry, visible_case
from rca.store import CanonicalStore, read_jsonl, write_jsonl_atomic

T = 1_000_000


def _metrics():
    rng = np.random.default_rng(0)
    times = np.arange(T - 600, T + 300)
    after = times >= T
    cart = rng.normal(20, 1, len(times))
    cart[after] += 50
    return pd.DataFrame({"time": times, "cartservice_cpu": cart, "cartservice_latency-50": cart,
                         "frontend_cpu": rng.normal(20, 1, len(times)), "redis_cpu": cart})


def test_metric_tool_flags_n_sigma_shift_on_candidates_only():
    out = rcl_tools.metric_tool(_metrics(), T, ["cart", "frontend"])
    assert list(out) == ["cart"]
    assert out["cart"][0].startswith("cpu up ") and "sigma" in out["cart"][0]
    assert not any("latency" in x for x in out["cart"])         # latency-50 is dropped
    assert rcl_tools.metric_tool(None, T, ["cart"]) == {}


def test_log_tool_maps_to_candidates():
    rows = []
    for k, t in enumerate(range(T - 600, T + 300, 2)):
        err = t >= T and k % 2 == 0
        rows.append({"timestamp": t * 10**9, "container_name": "cartservice", "svc": "cartservice",
                     "message": "rpc error Unavailable" if err else f"ok {k}", "level": "error" if err else "info"})
    out = rcl_tools.log_tool(pd.DataFrame(rows), T, ["cart"])
    assert list(out) == ["cart"] and any("error-log rate" in x for x in out["cart"])
    assert rcl_tools.log_tool(pd.DataFrame(rows), T, ["frontend"]) == {}


def _traces():
    rows = []
    for k, s in enumerate(range(T - 590, T + 290, 10)):
        slow = 200_000 if s >= T else 0
        tid = f"t{k:04d}"
        rows += [{"traceID": tid, "spanID": f"{tid}r", "parentSpanID": None, "svc": "frontend", "startTime": s * 10**6,
                  "duration": 3000 + 2000 + slow, "statusCode": 0},
                 {"traceID": tid, "spanID": f"{tid}c", "parentSpanID": f"{tid}r", "svc": "cart", "startTime": s * 10**6,
                  "duration": 2000 + slow, "statusCode": 2 if s >= T + 200 else 0}]
    return pd.DataFrame(rows)


def test_trace_tool_flags_self_time_and_errors_not_the_caller():
    tr = _traces()
    tid = tg.s_first(tr, T)
    lines, flagged = rcl_tools.trace_tool(tr, tid, T, ["cart", "frontend"])
    assert flagged >= {"cart"} and "frontend" not in flagged      # caller's self time is unchanged
    assert "x" in lines["cart"][0] and "frontend" in lines
    assert rcl_tools.trace_tool(None, tid, T, ["cart"]) == ({}, set())
    assert rcl_tools.trace_tool(tr, None, T, ["cart"]) == ({}, set())


def _dh(canonical_synth, tmp_path):
    dh = tmp_path / "dh"
    for part in ("canonical", "reports", "splits"):
        shutil.copytree(canonical_synth["dh"] / part, dh / part)
    return dh


def tool_outputs(dh) -> str:
    """Hash of every tool output and selected path for every incident of the synthetic store."""
    store = CanonicalStore(dh)
    out = {}
    for inc in store.incidents("rcaeval"):
        vc = visible_case(inc)
        tel = legacy_telemetry(store, vc.case_id)
        tid = tg.s_first(tel["traces"], vc.inject_time)
        lines, flagged = rcl_tools.trace_tool(tel["traces"], tid, vc.inject_time, vc.services)
        out[vc.case_id] = {"metric": rcl_tools.metric_tool(tel["metrics"], vc.inject_time, vc.services),
                           "log": rcl_tools.log_tool(tel["logs"], vc.inject_time, vc.services),
                           "trace": lines, "flagged": sorted(flagged), "trace_id": tid,
                           "path": rcl_path.select_path(rcl_path.has_spans(tel["traces"], vc.services), True, True)}
    return json.dumps(out, sort_keys=True)


def test_tools_are_deterministic_and_label_free(canonical_synth, tmp_path):
    dh = _dh(canonical_synth, tmp_path)
    base = tool_outputs(dh)
    assert hashlib.sha256(base.encode()).hexdigest() == hashlib.sha256(tool_outputs(dh).encode()).hexdigest()
    assert '"path": "trace"' in base and '"path": "no_trace"' in base   # SS has no traces

    labels = dh / "canonical/v1/rcaeval/eval_only/labels.jsonl"
    labs = read_jsonl(labels)
    canary = f"CANARY_{secrets.token_hex(8)}"
    fields = [(l["root_cause"], l["fault"]) for l in labs]
    fields = fields[1:] + fields[:1]                              # cyclic permutation of labels
    for l, (rc, fa) in zip(labs, fields):
        l["root_cause"], l["fault"] = rc, fa
        l["root_cause"]["original"] = canary
        l["fault"]["type_raw"] = canary
    write_jsonl_atomic(labels, labs)
    after = tool_outputs(dh)
    assert after == base and canary not in after
