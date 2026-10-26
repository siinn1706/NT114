"""Path selection for the RCLAgent adaptation without recursion-of-thought (path-selection spec a02 §2).

The path depends only on telemetry available after the condition is applied and on the arm's frame
state: never on labels, root services, fault types, model outputs or scores.

  trace      : the incident has at least one valid span (non-empty span id and service, service in the
               candidate list); decomposition over its trace graph.
  no_trace   : no valid span, the arm reads a frame and its key has a valid frame; frame-guided evidence.
  frame_free : otherwise; flat per-candidate evidence. The record stays in the denominator.
"""
from __future__ import annotations

import pandas as pd

PATHS = ("trace", "no_trace", "frame_free")


def has_spans(traces: pd.DataFrame | None, candidates) -> bool:
    """True when the (condition-applied) trace frame holds a span with a span id and a candidate service."""
    if traces is None or not len(traces):
        return False
    sid = traces["spanID"]
    ok = sid.notna() & (sid.astype(str) != "") & traces["svc"].notna()
    return bool(traces.loc[ok, "svc"].isin(set(candidates)).any())


def select_path(has_spans: bool, uses_frame: bool, frame_valid: bool) -> str:
    if has_spans:
        return "trace"
    if uses_frame and frame_valid:
        return "no_trace"
    return "frame_free"
