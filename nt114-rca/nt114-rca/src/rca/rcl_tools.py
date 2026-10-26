"""Deterministic metric, log and trace tools for the RCLAgent adaptation (replace the LLM tool calls).

Inputs are the legacy telemetry frames after the condition is applied and the incident's candidate
services; no label, root service or fault type. Windows follow the evidence builder: before =
[t - 600 s, t), after = [t, t + 300 s], t = anchor (seconds). Output: {candidate: [line, ...]} sorted
by service, only candidates with something to report.

  metric : n-sigma (n = 3): median of the after window against mean and standard deviation of the
           before window, per `<service>_<metric>` column.
  log    : `evidence.log_summary` (error-rate change, volume change, new error templates).
  trace  : per service in the selected trace, maximum self time (duration minus direct children)
           against the service's p90 self time before t across all traces, and error spans.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import rcl_trace_graph as tg
from .data import canon
from .evidence import ANOMAL_S, NORMAL_S, _is_err, log_summary

NSIGMA = 3.0
TOP_METRICS = 3
SELF_RATIO = 1.5        # trace: self time this many times the pre-incident p90 flags the service
MIN_BASELINE_SPANS = 5


def _windows(df: pd.DataFrame, tcol: pd.Series, t: int):
    return df[(tcol >= t - NORMAL_S) & (tcol < t)], df[(tcol >= t) & (tcol <= t + ANOMAL_S)]


def metric_tool(metrics: pd.DataFrame | None, t: int, candidates) -> dict[str, list[str]]:
    if metrics is None or not len(metrics):
        return {}
    cand = set(candidates)
    m = metrics.loc[:, ~metrics.columns.str.endswith("latency-50")]
    m = m.replace([np.inf, -np.inf], np.nan).ffill()
    normal, anomal = _windows(m, m["time"], t)
    hits: dict[str, list[tuple[float, str]]] = {}
    for col in sorted(m.columns):
        if col == "time" or "_" not in col:
            continue
        svc, metric = col.rsplit("_", 1)
        svc = canon(svc)
        if svc not in cand:
            continue
        a, b = normal[col].dropna(), anomal[col].dropna()
        if len(a) < 5 or len(b) < 3:
            continue
        mu, sd = float(a.mean()), float(a.std())
        scale = sd if sd > 1e-9 else abs(mu) * 0.05 + 1e-6
        z = (float(b.median()) - mu) / scale
        if abs(z) >= NSIGMA:
            name = metric.replace("-90", "")
            hits.setdefault(svc, []).append(
                (abs(z), f"{name} {'up' if z > 0 else 'down'} {min(abs(z), 999):.0f} sigma ({mu:.3g}->{float(b.median()):.3g})"))
    return {s: [x for _, x in sorted(v, key=lambda p: (-p[0], p[1]))[:TOP_METRICS]] for s, v in sorted(hits.items())}


def log_tool(logs: pd.DataFrame | None, t: int, candidates) -> dict[str, list[str]]:
    if logs is None or not len(logs):
        return {}
    cand, out = set(candidates), {}
    for svc, lines in log_summary(logs, t).items():
        s = canon(svc)
        if s in cand:
            out.setdefault(s, []).extend(lines)
    return dict(sorted(out.items()))


def trace_tool(traces: pd.DataFrame | None, trace_id: str | None, t: int, candidates) -> tuple[dict[str, list[str]], set[str]]:
    """(lines per candidate in the selected trace, flagged services)."""
    if traces is None or not len(traces) or trace_id is None:
        return {}, set()
    sp = tg.spans(traces)
    sp = sp.assign(_self=tg.self_time(sp), _t=pd.to_numeric(sp["startTime"], errors="coerce") / 1e6,
                   _err=_is_err(sp["statusCode"]) if "statusCode" in sp else False)
    normal, _ = _windows(sp, sp["_t"], t)
    base = normal.groupby("svc")["_self"].agg(["size", lambda s: s.quantile(0.9)])
    base.columns = ["n", "p90"]
    cand, out, flagged = set(candidates), {}, set()
    for svc, g in sp[sp["traceID"] == trace_id].groupby("svc", sort=True):
        mx, nerr = float(g["_self"].max()) / 1e3, int(g["_err"].sum())
        parts = [f"in selected trace {len(g)} span(s), max self time {mx:.1f}ms"]
        if svc in base.index and base.at[svc, "n"] >= MIN_BASELINE_SPANS:
            p90 = float(base.at[svc, "p90"]) / 1e3
            r = mx / max(p90, 1e-3)
            parts.append(f"vs p90 before {p90:.1f}ms (x{r:.1f})")
            if r >= SELF_RATIO:
                flagged.add(svc)
        else:
            parts.append("no pre-incident baseline")
        if nerr:
            parts.append(f"{nerr} error span(s)")
            flagged.add(svc)
        if svc in cand:
            out[str(svc)] = ["; ".join(parts)]
    return out, flagged
