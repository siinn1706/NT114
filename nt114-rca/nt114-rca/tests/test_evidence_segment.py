"""Evidence for sources that record logs/traces in bursts or cut exports: comparisons stay inside the
contiguous stretch of data holding the anchor, rates use the seconds actually covered, and a stretch
ending right after the anchor supports no after-vs-before claim."""
from __future__ import annotations

import pandas as pd

from rca import evidence, prep
from rca.legacy_view import evidence_kwargs

T = 1_700_000_000


def _logs(spans):
    """spans: (start offset, end offset, svc, is_error, rows per second)."""
    rows = []
    for a, b, svc, err, per_s in spans:
        for k in range(int((b - a) * per_s)):
            ts = T + a + k / per_s
            rows.append({"timestamp": int(ts * 1e9), "svc": svc, "level": "error" if err else "info",
                         "message": "request failed: upstream timeout" if err else "request ok"})
    return pd.DataFrame(rows)


def test_segment_bounds_follow_the_burst_holding_the_anchor():
    t = pd.Series([T - 400 + i for i in range(150)] + [T - 60 + i for i in range(150)], dtype=float)
    assert evidence._segment(t, T, 30) == (T - 60, T + 89)
    # anchor just before the first row of a burst: no baseline, the burst is the after side
    t2 = pd.Series([T + 5 + i for i in range(60)], dtype=float)
    assert evidence._segment(t2, T, 30) == (T, T + 64)


def test_previous_injection_burst_no_longer_masks_the_change():
    # an earlier injection's burst is full of errors; this incident's own burst has none before t
    logs = _logs([(-400, -250, "cart", True, 2), (-60, 0, "cart", False, 2), (0, 90, "cart", True, 2)])
    fixed = evidence.log_summary(logs, T)
    seg = evidence.log_summary(logs, T, segment_gap_s=30)
    assert "cart" not in fixed          # 300 old errors over 10 min hide 180 new ones over 5 min
    # 180 errors over the 89.5 s actually covered after t (last row at t + 89.5)
    assert seg["cart"][0].startswith("error-log rate 0.0/min -> 120.7/min")


def test_no_baseline_is_stated_not_assumed():
    logs = _logs([(-10, 0, "cart", False, 2), (0, 90, "cart", True, 2)])
    seg = evidence.log_summary(logs, T, segment_gap_s=30)
    assert seg["cart"] == ["error-log rate 120.7/min after incident start (no pre-incident baseline recorded)"]


def test_trace_comparison_ignores_other_bursts():
    def spans(a, b, dur_us):
        return [{"traceID": f"x{i}", "spanID": f"s{a}{i}", "parentSpanID": None, "svc": "cart",
                 "startTime": int((T + a + i) * 1e6), "duration": dur_us, "statusCode": 0} for i in range(b - a)]
    tr = pd.DataFrame(spans(-400, -250, 90_000) + spans(-60, 0, 10_000) + spans(0, 90, 40_000))
    assert "cart" not in evidence.trace_summary(tr, T)[0]                 # old slow burst hides the change
    assert evidence.trace_summary(tr, T, segment_gap_s=30)[0]["cart"][0].startswith("p90 latency 10.0ms -> 40.0ms")


def test_export_ending_near_the_anchor_supports_no_claim():
    # the source export stops 10 s after t: absent spans or logs afterwards say nothing about the incident
    logs = _logs([(-300, 10, "cart", False, 2)])
    assert evidence.log_summary(logs, T, segment_gap_s=60) == {}

    def spans(a, b, svc):
        return [{"traceID": f"{svc}{i}", "spanID": f"{svc}{a}{i}", "parentSpanID": None, "svc": svc,
                 "startTime": int((T + a + i) * 1e6), "duration": 10_000, "statusCode": 0} for i in range(b - a)]
    tr = pd.DataFrame(spans(-300, 10, "cart") + spans(-300, -5, "ad"))
    assert evidence.trace_summary(tr, T)[0]["ad"] == ["no spans after incident start"]   # fixed windows
    assert evidence.trace_summary(tr, T, segment_gap_s=60) == ({}, [])

    class Case:
        inject_time = T
    text = evidence.build(Case(), {"logs": logs, "traces": tr}, log_trace_segment_gap_s=60)["text"]
    assert "recorded log data covers less than 30 s after incident start; no comparison possible" in text
    assert "recorded trace data covers less than 30 s after incident start; no comparison possible" in text
    assert "no notable change" not in text and "no spans" not in text
    # data running past the threshold keeps the normal comparison and no coverage note
    long = evidence.build(Case(), {"logs": _logs([(-300, 120, "cart", False, 2)])}, log_trace_segment_gap_s=60)["text"]
    assert "covers less than" not in long and "no notable change in error logs" in long


def test_config_selects_segment_mode_per_dataset():
    cfg = prep.load_config()
    assert evidence_kwargs(cfg, "nezha") == {"log_trace_segment_gap_s": 30.0}
    assert evidence_kwargs(cfg, "aiops2025") == {"log_trace_segment_gap_s": 60.0}
    assert evidence_kwargs(cfg, "rca100") == {"log_trace_segment_gap_s": 60.0}
    assert evidence_kwargs(cfg, "rcaeval") == {}
    # the evidence section does not change the build hash
    body = {k: v for k, v in cfg.items() if k != "evidence"}
    assert prep.config_hash(body) == cfg["_hash"]


def test_default_mode_text_unchanged():
    logs = _logs([(-400, -250, "cart", True, 2), (-60, 0, "cart", False, 2), (0, 90, "cart", True, 2)])

    class Case:
        inject_time = T
    a = evidence.build(Case(), {"logs": logs})["text"]
    assert a.startswith("## Logs (5 min after vs. 10 min before)")
    b = evidence.build(Case(), {"logs": logs}, log_trace_segment_gap_s=30)["text"]
    assert b.startswith("## Logs (after vs. before incident start, within the contiguous recorded data around it)")
