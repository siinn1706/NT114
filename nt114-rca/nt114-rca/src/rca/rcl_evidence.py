"""Evidence builder of the RCLAgent adaptation WITHOUT recursion-of-thought (arms `ra`, `ra_im1`,
`ra_im1_shuf`; amendment a02). Not a reproduction of RCLAgent.

Decomposition, evidence selection and tool runs are deterministic code; the LLM only synthesises and
ranks in the single call that prompt `v1` already makes (this builder replaces its `{evidence}` block
only). Per-span LLM calls and their bottom-up merge are replaced by a rule: a flagged service none of
whose descendants is flagged is listed first.

Paths (`rcl_path.select_path`, telemetry after the condition is applied):
  trace      : S-first trace, its service call tree, trace/metric/log tools per service.
  no_trace   : framed arms only, when the incident's key has a valid frame: metric/log tools ordered
               and merged along the frame's edges among the candidates. The trace tool never runs.
  frame_free : flat metric/log evidence per candidate in the shuffled candidate order.

Inputs: a `VisibleCase`, the condition-applied telemetry and, for framed arms, a frame (`im1_frame`);
never a label. Only fixed windows are supported (`log_trace_segment_gap_s` raises).
"""
from __future__ import annotations

import hashlib
import json

from . import evidence, rcl_path, rcl_tools
from . import rcl_trace_graph as tg

# Bump whenever `build` can produce different text or features for the same inputs.
BUILDER_VERSION = "ra1"
MAX_CHARS = evidence.MAX_CHARS
# arm -> reads a frame (`uses_frame` of the path rule)
ARMS = {"ra": False, "ra_im1": True, "ra_im1_shuf": True}


def fingerprint(**options) -> str:
    blob = json.dumps({"builder": BUILDER_VERSION, "normal_s": evidence.NORMAL_S, "anomal_s": evidence.ANOMAL_S,
                       "max_chars": MAX_CHARS, "nsigma": rcl_tools.NSIGMA, "top_metrics": rcl_tools.TOP_METRICS,
                       "self_ratio": rcl_tools.SELF_RATIO, "min_baseline_spans": rcl_tools.MIN_BASELINE_SPANS,
                       "sfirst": [tg.SFIRST_BEFORE_S, tg.SFIRST_AFTER_S], "options": options}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def _lines(svc: str, parts: dict[str, list[str]]) -> str:
    return f"- {svc}: " + "; ".join(f"{k}: {x}" for k in ("trace", "metric", "log") for x in parts.get(k, []))


def _order(first: list[str], rest: list[str]) -> list[str]:
    return list(dict.fromkeys(first + rest))


def build(case, tel: dict, arm: str, frame: dict | None = None, log_trace_segment_gap_s: float | None = None) -> dict:
    """{'text', 'features', 'path', 'frame_sha256'} for one arm. `frame`: {'valid', 'sha256', 'edges'} of the
    incident's key (framed arms only; its sha256 is recorded on every path, the frame is read only on
    `no_trace`)."""
    if arm not in ARMS:
        raise ValueError(f"unknown R-a arm {arm!r}")
    if log_trace_segment_gap_s is not None:
        raise NotImplementedError("the R-a builder supports fixed windows only")
    if frame is not None and not ARMS[arm]:
        raise ValueError(f"arm {arm!r} reads no frame")
    t, cands = case.inject_time, list(case.services)
    shuffled = evidence.shuffled_candidates(case)
    valid = bool(frame and frame.get("valid"))
    path = rcl_path.select_path(rcl_path.has_spans(tel.get("traces"), cands), ARMS[arm], valid)

    tools: dict[str, dict[str, list[str]]] = {}
    for kind, out in (("metric", rcl_tools.metric_tool(tel.get("metrics"), t, cands)),
                      ("log", rcl_tools.log_tool(tel.get("logs"), t, cands))):
        for svc, ll in out.items():
            tools.setdefault(svc, {})[kind] = ll
    blocks, order, flagged, edges = [], [], set(tools), []
    feats = {"has_metrics": int(tel.get("metrics") is not None), "has_logs": int(tel.get("logs") is not None),
             "has_traces": int(tel.get("traces") is not None)}

    if path == "trace":
        tid = tg.s_first(tel["traces"], t)
        tree = tg.trace_tree(tel["traces"], tid) if tid is not None else None
        if tree is not None:
            lines, tflag = rcl_tools.trace_tool(tel["traces"], tid, t, cands)
            for svc, ll in lines.items():
                tools.setdefault(svc, {})["trace"] = ll
            flagged |= tflag & set(cands)
            edges = tree["edges"]
            head = ["## Selected trace (root span with the longest duration near incident start)",
                    "Call edges: " + ("; ".join(f"{p} -> {c}" for p, c in edges) or "none (single service)")]
            order = tg.dfs_order(edges, tree["entry"], tree["nodes"])
        else:
            head = ["## Selected trace", "- no root span starts within 60 s before to 300 s after incident start"]
        blocks.append("\n".join(head))
    elif path == "no_trace":
        cs = set(cands)
        edges = sorted((p, c) for p, c in frame["edges"] if p in cs and c in cs and p != c)
        entries = sorted({p for p, _ in edges} - {c for _, c in edges})
        for e in entries:
            order = _order(order, tg.dfs_order(edges, e, []))
        blocks.append("\n".join([
            "## Service dependency frame (historical calls in train-role traces, before incident start)",
            "Frame edges among candidates: " + ("; ".join(f"{p} -> {c}" for p, c in edges) or "none")]))

    deepest = tg.deepest_flagged(edges, flagged) if path != "frame_free" else []
    order = _order([s for s in deepest if s in tools], _order([s for s in order if s in tools], [s for s in shuffled if s in tools]))
    title = {"trace": "## Per-service tool results (bottom-up: deepest anomalous first, then call-tree order)",
             "no_trace": "## Per-service tool results (bottom-up along frame edges, then frame order)",
             "frame_free": "## Per-service tool results"}[path]
    body = [title]
    if path != "frame_free":
        body.append("Deepest anomalous services (no anomalous descendant): " + (", ".join(deepest) or "none"))
    body += [_lines(s, tools[s]) for s in order] or ["- no tool flagged any candidate"]
    quiet = [s for s in shuffled if s not in tools]
    if quiet:
        body.append("No tool finding: " + ", ".join(quiet))
    blocks.append("\n".join(body))
    missing = [k for k in ("metrics", "logs", "traces") if tel.get(k) is None]
    if missing:
        blocks.append("## Not available\n- " + ", ".join(missing) + " were not collected for this incident.")

    feats.update(n_flagged_services=len(flagged & set(cands)), n_listed_services=len(order))
    text = "\n\n".join(blocks)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n[truncated]"
    return {"text": text, "features": feats, "path": path,
            "frame_sha256": frame.get("sha256") if frame is not None else None}
