"""Biến telemetry thành bản tóm tắt bằng chứng dạng văn bản cho LLM.

Không đưa dữ liệu thô vào prompt (quá dài). Mỗi modality được rút gọn thành vài dòng/dịch vụ:
  metric : chỉ số lệch nhiều nhất so với trước lỗi (robust z-score: median + MAD)
  log    : tốc độ dòng lỗi trước/sau, mẫu log mới xuất hiện sau lỗi
  trace  : p90 độ trễ và tỷ lệ lỗi trước/sau theo dịch vụ, các cạnh gọi chậm lên nhiều nhất

Cửa sổ: bình thường = [t-600s, t), bất thường = [t, t+300s], t = inject_time. Với nguồn ghi log/trace
theo đợt hoặc bị cắt (Nezha, AIOps2025, RCA100), log/trace chỉ so trong đoạn dữ liệu liên tục chứa t
(`log_trace_segment_gap_s`); đoạn dừng chưa tới MIN_AFTER_S sau t thì không so sánh trước/sau.
Thứ tự dịch vụ trong danh sách ứng viên được xáo trộn theo seed của ca để không lộ nhãn.
"""
from __future__ import annotations

import hashlib
import json
import random
import re

import numpy as np
import pandas as pd

from .data import canon

NORMAL_S, ANOMAL_S = 600, 300
MAX_CHARS = 14_000  # ~3.5k token
# Bump whenever `build` can produce different text or features for the same telemetry and options:
# cached evidence and results are keyed by `fingerprint`, so a stale output is rebuilt, never reused.
BUILDER_VERSION = "3"


def _windows(df: pd.DataFrame, tcol: pd.Series, t: int):
    normal = df[(tcol >= t - NORMAL_S) & (tcol < t)]
    anomal = df[(tcol >= t) & (tcol <= t + ANOMAL_S)]
    return normal, anomal


def _segment(tcol: pd.Series, t: float, gap_s: float) -> tuple[float, float]:
    """Bounds of the contiguous stretch of data around t (rows no more than `gap_s` apart), clipped to
    [t - NORMAL_S, t + ANOMAL_S]. For sources that record logs/traces only in bursts around each
    injection, so the fixed windows would compare against neighbouring injections' bursts."""
    s = np.sort(tcol.dropna().to_numpy(dtype=float))
    s = s[(s >= t - NORMAL_S) & (s <= t + ANOMAL_S)]
    if len(s) == 0:
        return t, t
    cuts = np.flatnonzero(np.diff(s) > gap_s)
    starts, ends = np.r_[s[0], s[cuts + 1]], np.r_[s[cuts], s[-1]]
    k = np.flatnonzero((starts <= t) & (ends >= t))
    if len(k):
        return float(starts[k[0]]), float(ends[k[0]])
    after = np.flatnonzero(starts > t)       # anchor in a gap: the next stretch, nothing before
    if len(after) and starts[after[0]] - t <= gap_s:
        return t, float(ends[after[0]])
    before = np.flatnonzero(ends < t)
    if len(before) and t - ends[before[-1]] <= gap_s:
        return float(starts[before[-1]]), t
    return t, t


def _windows_for(df: pd.DataFrame, tcol: pd.Series, t: int, segment_gap_s: float | None):
    """(normal, anomal, normal seconds, anomal seconds). Without `segment_gap_s`: the fixed windows."""
    if segment_gap_s is None:
        normal, anomal = _windows(df, tcol, t)
        return normal, anomal, NORMAL_S, ANOMAL_S
    lo, hi = _segment(tcol, t, segment_gap_s)
    normal = df[(tcol >= lo) & (tcol < t)]
    anomal = df[(tcol >= t) & (tcol <= hi)]
    return normal, anomal, t - lo, hi - t


# ---------------------------------------------------------------- metric
def metric_scores(metrics: pd.DataFrame, t: int) -> pd.DataFrame:
    m = metrics.loc[:, ~metrics.columns.str.endswith("latency-50")]
    m = m.replace([np.inf, -np.inf], np.nan).ffill()
    normal, anomal = _windows(m, m["time"], t)
    rows = []
    for col in m.columns:
        if col == "time" or "_" not in col:
            continue
        a, b = normal[col].dropna(), anomal[col].dropna()
        if len(a) < 5 or len(b) < 3:
            continue
        med = a.median()
        mad = (a - med).abs().median() * 1.4826
        scale = mad if mad > 1e-9 else (a.std() if a.std() > 1e-9 else abs(med) * 0.05 + 1e-6)
        z = (b - med) / scale
        # phân vị 80% của |z|: bắt độ lệch kéo dài, bỏ qua gai nhiễu đơn lẻ
        zq = float(z.abs().quantile(0.8))
        svc, metric = col.rsplit("_", 1)
        rows.append({"svc": svc, "metric": metric.replace("-90", ""), "z": zq,
                     "dir": "up" if z.median() > 0 else "down",
                     "before": float(med), "after": float(b.median())})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- log
_MASK = [(re.compile(r"[0-9a-f]{8}-[0-9a-f-]{27,}", re.I), "<uuid>"),
         (re.compile(r"\b0x[0-9a-f]+\b|\b[0-9a-f]{12,}\b", re.I), "<hex>"),
         (re.compile(r"\d+(\.\d+)?"), "<n>"),
         (re.compile(r"\"[^\"]*\"|'[^']*'"), "<str>")]
_ERR = re.compile(r"error|exception|fail|timeout|refused|unavailable|panic|fatal", re.I)


def template(msg: str) -> str:
    """Mẫu log đơn giản bằng regex. Có thể thay bằng Drain3 nếu cần chính xác hơn."""
    s = str(msg)[:200]
    for pat, rep in _MASK:
        s = pat.sub(rep, s)
    return s


MIN_BASELINE_S = 30   # segment mode: less pre-anchor data than this is no baseline
MIN_AFTER_S = 30      # segment mode: less post-anchor data than this supports no after-vs-before claim


def _log_t(logs: pd.DataFrame) -> pd.Series:
    if "timestamp" in logs:
        return pd.to_numeric(logs["timestamp"], errors="coerce") / 1e9
    return pd.to_numeric(logs["time"], errors="coerce")


def _trace_t(traces: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(traces["startTime"], errors="coerce") / 1e6


def short_after(tcol: pd.Series, t: float, segment_gap_s: float | None) -> bool:
    """Segment mode: the recorded data around t stops less than MIN_AFTER_S after t (the source export
    ends there), so a missing span or log line after t says nothing about the incident."""
    if segment_gap_s is None:
        return False
    return _segment(tcol, t, segment_gap_s)[1] - t < MIN_AFTER_S


def log_summary(logs: pd.DataFrame, t: int, segment_gap_s: float | None = None) -> dict[str, list[str]]:
    df = logs.assign(_t=_log_t(logs), tpl=logs["message"].map(template))
    lvl = df["level"].astype(str).str.lower() if "level" in df else pd.Series("", index=df.index)
    df["is_err"] = lvl.isin(["error", "warn", "warning", "fatal", "critical"]) | df["message"].astype(str).str.contains(_ERR)
    normal, anomal, dur_n, dur_a = _windows_for(df, df["_t"], t, segment_gap_s)
    if segment_gap_s is not None and dur_a < MIN_AFTER_S:
        return {}
    no_base = segment_gap_s is not None and dur_n < MIN_BASELINE_S
    out: dict[str, list[str]] = {}
    for svc in sorted(set(df["svc"].dropna())):
        n, a = normal[normal["svc"] == svc], anomal[anomal["svc"] == svc]
        if no_base:
            rate_a = a["is_err"].sum() / (dur_a / 60)
            if rate_a > 1.0:
                out[svc] = [f"error-log rate {rate_a:.1f}/min after incident start (no pre-incident baseline recorded)"]
            continue
        rate_n = n["is_err"].sum() / (dur_n / 60)
        rate_a = a["is_err"].sum() / (dur_a / 60)
        vol_n, vol_a = len(n) / (dur_n / 60), len(a) / (dur_a / 60)
        new = [x for x in a.loc[a["is_err"], "tpl"].value_counts().index if x not in set(n["tpl"])][:2]
        lines = []
        if rate_a > max(1.0, 2 * rate_n):
            lines.append(f"error-log rate {rate_n:.1f}/min -> {rate_a:.1f}/min")
        if vol_n > 0 and (vol_a / vol_n < 0.3 or vol_a / vol_n > 3):
            lines.append(f"log volume {vol_n:.0f}/min -> {vol_a:.0f}/min")
        lines += [f'new error template: "{x[:120]}"' for x in new]
        if lines:
            out[svc] = lines
    return out


# ---------------------------------------------------------------- trace
def _is_err(code: pd.Series) -> pd.Series:
    c = pd.to_numeric(code, errors="coerce")
    return c.notna() & (c != 0) & ((c < 200) | (c >= 400))


def trace_summary(traces: pd.DataFrame, t: int, segment_gap_s: float | None = None) -> tuple[dict[str, list[str]], list[str]]:
    tr = traces.dropna(subset=["startTime", "duration"]).copy()
    tr["_t"] = _trace_t(tr)
    tr["err"] = _is_err(tr["statusCode"]) if "statusCode" in tr else False
    if segment_gap_s is not None:            # one segment for all services and edges
        lo, hi = _segment(tr["_t"], t, segment_gap_s)
        if hi - t < MIN_AFTER_S:
            return {}, []
        tr = tr[(tr["_t"] >= lo) & (tr["_t"] <= hi)]
    normal, anomal = _windows(tr, tr["_t"], t)
    per_svc: dict[str, list[str]] = {}
    for svc in sorted(set(tr["svc"].dropna())):
        n, a = normal[normal["svc"] == svc], anomal[anomal["svc"] == svc]
        if len(n) < 5:
            if len(a) == 0 and len(n) > 0:
                per_svc[svc] = ["spans disappeared after incident start"]
            continue
        lines = []
        p90n, p90a = n["duration"].quantile(.9) / 1e3, (a["duration"].quantile(.9) / 1e3 if len(a) else np.nan)
        if np.isnan(p90a):
            lines.append("no spans after incident start")
        elif p90a > 1.5 * p90n:
            lines.append(f"p90 latency {p90n:.1f}ms -> {p90a:.1f}ms (x{p90a / max(p90n, 1e-6):.1f})")
        en, ea = n["err"].mean(), (a["err"].mean() if len(a) else 0)
        if ea > max(0.02, 2 * en):
            lines.append(f"span error rate {en:.1%} -> {ea:.1%}")
        if lines:
            per_svc[svc] = lines

    # cạnh gọi parent_svc -> child_svc
    edges = []
    if "parentSpanID" in tr:
        parent = tr.set_index("spanID")["svc"].to_dict()
        tr["psvc"] = tr["parentSpanID"].map(parent)
        cross = tr[tr["psvc"].notna() & (tr["psvc"] != tr["svc"])]
        normal, anomal = _windows(cross, cross["_t"], t)
        for (p, c), g in normal.groupby(["psvc", "svc"]):
            ga = anomal[(anomal["psvc"] == p) & (anomal["svc"] == c)]
            if len(g) >= 5 and len(ga) >= 3:
                r = ga["duration"].median() / max(g["duration"].median(), 1)
                if r > 1.5:
                    edges.append((r, f"{p} -> {c}: median latency x{r:.1f}"))
    edges = [s for _, s in sorted(edges, reverse=True)[:5]]
    return per_svc, edges


# ---------------------------------------------------------------- ghép văn bản
def build(case, tel: dict, top_metrics_per_svc: int = 3, max_services: int = 10,
          log_trace_segment_gap_s: float | None = None) -> dict:
    """Trả về {'text': bằng chứng, 'features': đặc trưng số cho lớp quyết định}.

    `log_trace_segment_gap_s`: so sánh log/trace chỉ trong đoạn dữ liệu liên tục quanh t (nguồn ghi
    log/trace theo từng đợt quanh mỗi lần tiêm lỗi, vd Nezha); None = cửa sổ cố định."""
    seg = log_trace_segment_gap_s
    t = case.inject_time
    blocks, feats = [], {"has_metrics": 0, "has_logs": 0, "has_traces": 0,
                         "max_metric_z": 0.0, "n_flagged_services": 0, "z_gap_top2": 0.0}
    flagged: dict[str, float] = {}

    if tel.get("metrics") is not None:
        feats["has_metrics"] = 1
        ms = metric_scores(tel["metrics"], t)
        if len(ms):
            ms["svc"] = ms["svc"].map(canon)
            agg = ms.groupby("svc")["z"].max().sort_values(ascending=False)
            feats["max_metric_z"] = float(min(agg.iloc[0], 1e3))
            if len(agg) > 1:
                feats["z_gap_top2"] = float(min(agg.iloc[0], 1e3) - min(agg.iloc[1], 1e3))
            lines = ["## Metrics (robust z-score vs. 10 min before incident)"]
            for svc in agg.index[:max_services]:
                if agg[svc] < 3:
                    continue
                flagged[svc] = max(flagged.get(svc, 0), agg[svc])
                top = ms[(ms["svc"] == svc) & (ms["z"] >= 3)].nlargest(top_metrics_per_svc, "z")
                desc = "; ".join(f"{r.metric} {r.dir} z={min(r.z, 999):.0f} ({r.before:.3g}->{r.after:.3g})" for r in top.itertuples())
                lines.append(f"- {svc}: {desc}")
            if len(lines) == 1:
                lines.append("- no metric deviates strongly (all |z| < 3)")
            blocks.append("\n".join(lines))

    if tel.get("logs") is not None:
        feats["has_logs"] = 1
        ls = log_summary(tel["logs"], t, seg)
        lines = ["## Logs (5 min after vs. 10 min before)" if seg is None else
                 "## Logs (after vs. before incident start, within the contiguous recorded data around it)"]
        for svc, ll in list(ls.items())[:max_services]:
            flagged[svc] = flagged.get(svc, 0) + 1
            lines += [f"- {svc}: {x}" for x in ll]
        if short_after(_log_t(tel["logs"]), t, seg):
            lines.append(f"- recorded log data covers less than {MIN_AFTER_S} s after incident start; no comparison possible")
        elif len(lines) == 1:
            lines.append("- no notable change in error logs")
        blocks.append("\n".join(lines))

    if tel.get("traces") is not None:
        feats["has_traces"] = 1
        ts, edges = trace_summary(tel["traces"], t, seg)
        lines = ["## Traces (per service, after vs. before)" if seg is None else
                 "## Traces (per service, after vs. before, within the contiguous recorded data around incident start)"]
        for svc, ll in list(ts.items())[:max_services]:
            flagged[svc] = flagged.get(svc, 0) + 1
            lines += [f"- {svc}: {x}" for x in ll]
        if edges:
            lines.append("Slowest-growing call edges:")
            lines += [f"- {e}" for e in edges]
        if short_after(_trace_t(tel["traces"].dropna(subset=["startTime", "duration"])), t, seg):
            lines.append(f"- recorded trace data covers less than {MIN_AFTER_S} s after incident start; no comparison possible")
        elif len(lines) == 1:
            lines.append("- no notable change in traces")
        blocks.append("\n".join(lines))

    missing = [k for k in ("metrics", "logs", "traces") if tel.get(k) is None]
    if missing:
        blocks.append("## Not available\n- " + ", ".join(missing) + " were not collected for this incident.")

    feats["n_flagged_services"] = len(flagged)
    text = "\n\n".join(blocks)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n[truncated]"
    return {"text": text, "features": feats}


def fingerprint(**options) -> str:
    """Identity of `build`'s output for given telemetry: builder version, window rules and the
    per-dataset options passed to `build`."""
    blob = json.dumps({"builder": BUILDER_VERSION, "normal_s": NORMAL_S, "anomal_s": ANOMAL_S,
                       "max_chars": MAX_CHARS, "min_baseline_s": MIN_BASELINE_S, "min_after_s": MIN_AFTER_S,
                       "options": options}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def shuffled_candidates(case) -> list[str]:
    seed = int(hashlib.md5(case.case_id.encode()).hexdigest()[:8], 16)
    c = list(case.services)
    random.Random(seed).shuffle(c)
    return c
