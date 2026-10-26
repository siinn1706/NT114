"""Trace graph of the RCLAgent adaptation: parent resolution, S-first, self time, DFS, bottom-up merge."""
from __future__ import annotations

import pandas as pd

from rca import rcl_trace_graph as tg

A = 1_000_000          # anchor (s)


def _span(tid, sid, parent, svc, start_s, dur_us, code=0):
    return {"traceID": tid, "spanID": sid, "parentSpanID": parent, "svc": svc,
            "startTime": int(start_s * 1e6), "duration": dur_us, "statusCode": code}


def frame():
    return pd.DataFrame([
        _span("t2", "r2", None, "frontend", A + 10, 5000),
        _span("t2", "c2", "r2", "checkout", A + 10, 4000),
        _span("t2", "p2", "c2", "payment", A + 10, 3500),
        _span("t1", "r1", None, "frontend", A + 5, 5000),       # same duration as t2's root: tie -> t1
        _span("t1", "x1", "r1", "cart", A + 5, 100),
        _span("t1", "o1", "zz", "cart", A + 5, 50),              # parent missing in its trace: a root span
        _span("t3", "r3", None, "frontend", A - 120, 9000),     # before the S-first window
        _span("t4", "r4", "c2", "ad", A + 20, 10),               # parent id exists only in another trace
    ])


def test_parent_resolves_only_within_the_same_trace():
    sp = tg.spans(frame())
    psvc = dict(zip(sp["spanID"], sp["psvc"]))
    assert psvc["c2"] == "frontend" and psvc["p2"] == "checkout"
    assert psvc["o1"] == "" and psvc["r4"] == ""


def test_s_first_window_and_tie_break():
    assert tg.s_first(frame(), A) == "t1"
    assert tg.s_first(frame()[frame()["traceID"] != "t1"], A) == "t2"
    assert tg.s_first(frame()[frame()["traceID"] == "t3"], A) is None
    assert tg.s_first(None, A) is None


def test_self_time_subtracts_direct_children():
    sp = tg.spans(frame())
    st = dict(zip(sp["spanID"], tg.self_time(sp)))
    assert st["r2"] == 1000 and st["c2"] == 500 and st["p2"] == 3500


def test_edges_tree_order_and_deepest_flagged():
    assert tg.service_edges(frame()) == {("checkout", "payment"): 1, ("frontend", "cart"): 1, ("frontend", "checkout"): 1}
    tree = tg.trace_tree(frame(), "t2")
    assert tree["entry"] == "frontend" and tree["edges"] == [("checkout", "payment"), ("frontend", "checkout")]
    assert tg.dfs_order(tree["edges"], tree["entry"], tree["nodes"] + ["zeta"]) == ["frontend", "checkout", "payment", "zeta"]
    assert tg.deepest_flagged(tree["edges"], {"frontend", "checkout", "payment"}) == ["payment"]
    assert tg.deepest_flagged(tree["edges"], {"frontend"}) == ["frontend"]


def test_deterministic_and_row_order_free():
    f = frame()
    shuffled = f.sample(frac=1, random_state=3)
    assert tg.s_first(f, A) == tg.s_first(shuffled, A)
    assert tg.service_edges(f) == tg.service_edges(shuffled)
    assert tg.trace_tree(f, "t2") == tg.trace_tree(shuffled, "t2")
