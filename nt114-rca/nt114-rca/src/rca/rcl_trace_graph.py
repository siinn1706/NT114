"""Trace graph for the RCLAgent adaptation without recursion-of-thought (deterministic code, no LLM).

Reads the legacy trace frame (`legacy_view.legacy_telemetry`: traceID, spanID, parentSpanID, svc,
startTime and duration in µs, statusCode) after the condition is applied, so a dropped or masked
modality never reaches it. No label, root service or fault type is an input.

A span's parent resolves only to a span of the same trace; a span whose parent is empty or does not
resolve is a root span. S-first (reproduction-protocol §7): among root spans starting in
[anchor - 60 s, anchor + 300 s], the trace whose root span lasts longest; ties go to the smallest
trace id. "Best rank over traces" (S-best) uses labels and is never computed here.
"""
from __future__ import annotations

import pandas as pd

SFIRST_BEFORE_S, SFIRST_AFTER_S = 60, 300


def _str(s: pd.Series) -> pd.Series:
    return s.where(s.notna(), "").astype(str)


def spans(traces: pd.DataFrame) -> pd.DataFrame:
    """Valid spans (span id and service present) with string ids and the parent's service `psvc`
    (empty when the parent does not resolve within the same trace). Row order is kept."""
    t = traces[traces["spanID"].notna() & traces["svc"].notna()].copy()
    for c in ("traceID", "spanID", "parentSpanID"):
        t[c] = _str(t[c]) if c in t else ""
    t = t[t["spanID"] != ""]
    par = (t[["traceID", "spanID", "svc"]].drop_duplicates(["traceID", "spanID"])
           .rename(columns={"spanID": "parentSpanID", "svc": "psvc"}))
    m = t.reset_index(drop=True).merge(par, on=["traceID", "parentSpanID"], how="left")
    m["psvc"] = m["psvc"].where(m["psvc"].notna() & (m["parentSpanID"] != ""), "")
    return m


def self_time(sp: pd.DataFrame) -> pd.Series:
    """Span duration minus the summed duration of its direct children (µs, floored at 0)."""
    child = sp[sp["psvc"] != ""].groupby(["traceID", "parentSpanID"])["duration"].sum()
    key = pd.MultiIndex.from_arrays([sp["traceID"], sp["spanID"]])
    sub = pd.Series(child.reindex(key).to_numpy(), index=sp.index).fillna(0)
    return (pd.to_numeric(sp["duration"], errors="coerce") - sub).clip(lower=0)


def s_first(traces: pd.DataFrame | None, anchor_s: int) -> str | None:
    if traces is None or not len(traces):
        return None
    sp = spans(traces)
    root = sp[sp["psvc"] == ""]
    st = pd.to_numeric(root["startTime"], errors="coerce") / 1e6
    root = root[(st >= anchor_s - SFIRST_BEFORE_S) & (st <= anchor_s + SFIRST_AFTER_S)]
    root = root.assign(_d=pd.to_numeric(root["duration"], errors="coerce")).dropna(subset=["_d"])
    if not len(root):
        return None
    return str(root.sort_values(["_d", "traceID"], ascending=[False, True]).iloc[0]["traceID"])


def service_edges(traces: pd.DataFrame) -> dict[tuple[str, str], int]:
    """Directed `parent service -> child service` edges (distinct services) with their span counts."""
    sp = spans(traces)
    cross = sp[(sp["psvc"] != "") & (sp["psvc"] != sp["svc"])]
    return {(str(p), str(c)): int(n) for (p, c), n in cross.groupby(["psvc", "svc"]).size().sort_index().items()}


def trace_tree(traces: pd.DataFrame, trace_id: str) -> dict:
    """Service graph of one trace: entry service, nodes (services) and sorted edges."""
    sp = spans(traces)
    tr = sp[sp["traceID"] == trace_id]
    roots = tr[tr["psvc"] == ""].assign(_d=pd.to_numeric(tr["duration"], errors="coerce"))
    entry = str(roots.sort_values(["_d", "spanID"], ascending=[False, True]).iloc[0]["svc"]) if len(roots) else None
    edges = sorted({(str(p), str(c)) for p, c in zip(tr["psvc"], tr["svc"]) if p and p != c})
    return {"trace_id": trace_id, "entry": entry, "nodes": sorted(set(map(str, tr["svc"]))), "edges": edges}


def _children(edges) -> dict[str, list[str]]:
    ch: dict[str, list[str]] = {}
    for p, c in edges:
        ch.setdefault(p, []).append(c)
    return {p: sorted(set(c)) for p, c in ch.items()}


def dfs_order(edges, start: str | None, nodes) -> list[str]:
    """Pre-order DFS from `start` (children by name), then unreached nodes by name."""
    ch, seen, out = _children(edges), set(), []
    stack = [start] if start is not None else []
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        out.append(n)
        stack.extend(reversed(ch.get(n, [])))
    return out + sorted(set(nodes) - seen)


def descendants(edges, node: str) -> set[str]:
    ch, seen, stack = _children(edges), set(), list(_children(edges).get(node, []))
    while stack:
        n = stack.pop()
        if n not in seen:
            seen.add(n)
            stack.extend(ch.get(n, []))
    seen.discard(node)
    return seen


def deepest_flagged(edges, flagged) -> list[str]:
    """Bottom-up merge by rule (replaces per-span LLM calls): flagged services none of whose
    descendants is flagged, by name."""
    f = set(flagged)
    return sorted(s for s in f if not (descendants(edges, s) & f))
