"""Độ đo: độ chính xác, "sai mà chắc", độ hiệu chỉnh, risk–coverage, kiểm định thống kê."""
from __future__ import annotations

import numpy as np
from scipy.stats import binomtest


def ac_at_k(ranks, k: int) -> float:
    return float(np.mean(np.asarray(ranks) <= k))


def avg_at_k(ranks, k: int = 5) -> float:
    return float(np.mean([ac_at_k(ranks, j) for j in range(1, k + 1)]))


def confident_wrong_rate(correct, conf, thr: float = 0.8) -> float:
    """Tỷ lệ ca trả lời SAI với độ tự tin >= thr, trên tổng số ca (con số kỹ sư hiểu ngay)."""
    correct, conf = np.asarray(correct, bool), np.asarray(conf, float)
    return float(np.mean(~correct & (conf >= thr)))


def ece(correct, conf, n_bins: int = 10) -> float:
    correct, conf = np.asarray(correct, float), np.clip(np.asarray(conf, float), 0, 1)
    bins = np.minimum((conf * n_bins).astype(int), n_bins - 1)
    return float(sum(np.abs(correct[bins == b].mean() - conf[bins == b].mean()) * (bins == b).mean()
                     for b in range(n_bins) if (bins == b).any()))


def risk_coverage(correct, conf):
    """Sắp ca theo độ tự tin giảm dần; trả coverage[i], risk[i] khi chỉ trả lời i+1 ca tự tin nhất."""
    correct, conf = np.asarray(correct, float), np.asarray(conf, float)
    order = np.argsort(-conf, kind="stable")
    c = correct[order]
    n = np.arange(1, len(c) + 1)
    return n / len(c), 1 - np.cumsum(c) / n


def aurc(correct, conf) -> float:
    cov, risk = risk_coverage(correct, conf)
    return float(np.mean(risk))


def selective_accuracy(correct, conf, coverage: float = 0.8) -> float:
    cov, risk = risk_coverage(correct, conf)
    i = max(int(np.ceil(coverage * len(cov))) - 1, 0)
    return float(1 - risk[i])


def mcnemar(correct_a, correct_b) -> dict:
    """McNemar chính xác (nhị thức) cho hai cấu hình trên CÙNG tập ca."""
    a, b = np.asarray(correct_a, bool), np.asarray(correct_b, bool)
    n01, n10 = int((~a & b).sum()), int((a & ~b).sum())
    p = binomtest(n01, n01 + n10, 0.5).pvalue if n01 + n10 else 1.0
    return {"a_only": n10, "b_only": n01, "p": float(p)}


def bootstrap_ci(values, fn=np.mean, n: int = 2000, alpha: float = 0.05, seed: int = 0):
    rng = np.random.default_rng(seed)
    v = np.asarray(values)
    stats = [fn(v[rng.integers(0, len(v), len(v))]) for _ in range(n)]
    return float(np.quantile(stats, alpha / 2)), float(np.quantile(stats, 1 - alpha / 2))


def holm(pvals: dict) -> dict:
    """Hiệu chỉnh Holm cho nhiều so sánh."""
    items = sorted(pvals.items(), key=lambda x: x[1])
    m, out, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


# ---------------------------------------------------------------- weighted metrics (eval-unit weights)
def _w(weights, n) -> np.ndarray:
    w = np.ones(n) if weights is None else np.asarray(weights, float)
    if len(w) != n:
        raise ValueError("weights length differs from values")
    return w


def wmean(values, weights=None) -> float:
    v = np.asarray(values, float)
    w = _w(weights, len(v))
    return float((w * v).sum() / w.sum())


def ac_at_k_w(ranks, k: int, weights=None) -> float:
    return wmean(np.asarray(ranks) <= k, weights)


def brier(correct, conf, weights=None) -> float:
    c, p = np.asarray(correct, float), np.clip(np.asarray(conf, float), 0, 1)
    return wmean((p - c) ** 2, weights)


def ece_w(correct, conf, weights=None, strategy: str = "width", n_bins: int = 10) -> float:
    """Weighted ECE. `width`: equal-width bins; `mass`: equal-mass bins (by weight); `support`: one bin
    per distinct confidence value (consensus has n_samples + 1 levels)."""
    c, p = np.asarray(correct, float), np.clip(np.asarray(conf, float), 0, 1)
    w = _w(weights, len(c))
    if strategy == "width":
        bins = np.minimum((p * n_bins).astype(int), n_bins - 1)
    elif strategy == "support":
        _, bins = np.unique(np.round(p, 9), return_inverse=True)
    elif strategy == "mass":
        order = np.argsort(p, kind="stable")
        cum = np.cumsum(w[order]) / w.sum()
        bins = np.empty(len(p), int)
        bins[order] = np.minimum((cum * n_bins - 1e-12).astype(int), n_bins - 1)
    else:
        raise ValueError(strategy)
    tot = w.sum()
    return float(sum(abs((w[m] * c[m]).sum() - (w[m] * p[m]).sum()) / tot
                     for m in (bins == b for b in np.unique(bins))))


def overconfidence_gap(correct, conf, weights=None) -> float:
    """Mean confidence minus accuracy (> 0 = overconfident)."""
    return wmean(conf, weights) - wmean(correct, weights)


def auroc(labels, scores, weights=None) -> float:
    """Weighted Mann-Whitney AUROC: P(score of a positive > score of a negative), ties count 0.5."""
    y, s = np.asarray(labels, bool), np.asarray(scores, float)
    w = _w(weights, len(y))
    if y.all() or not y.any():
        return float("nan")
    order = np.argsort(s, kind="stable")
    s, y, w = s[order], y[order], w[order]
    _, start = np.unique(s, return_index=True)
    stops = np.append(start[1:], len(s))
    neg_below, num = 0.0, 0.0
    for a, b in zip(start, stops):
        wp, wn = (w[a:b] * y[a:b]).sum(), (w[a:b] * ~y[a:b]).sum()
        num += wp * (neg_below + 0.5 * wn)
        neg_below += wn
    return float(num / ((w * y).sum() * (w * ~y).sum()))


def auprc(labels, scores, weights=None) -> float:
    """Weighted average precision (positives = `labels`), thresholds at distinct scores."""
    y, s = np.asarray(labels, bool), np.asarray(scores, float)
    w = _w(weights, len(y))
    if not y.any():
        return float("nan")
    out, tp, fp, prev_recall = 0.0, 0.0, 0.0, 0.0
    total = (w * y).sum()
    for v in np.unique(s)[::-1]:
        m = s == v
        tp += (w[m] * y[m]).sum()
        fp += (w[m] * ~y[m]).sum()
        recall = tp / total
        out += (recall - prev_recall) * tp / (tp + fp)
        prev_recall = recall
    return float(out)


def error_detection(correct, conf, weights=None) -> dict:
    """Errors are the positives; a lower confidence should flag them."""
    wrong = ~np.asarray(correct, bool)
    s = -np.asarray(conf, float)
    return {"AUROC": auroc(wrong, s, weights), "AUPRC": auprc(wrong, s, weights)}


def risk_coverage_w(correct, conf, weights=None):
    """Weighted risk-coverage: rows by confidence (descending, ties grouped); coverage = answered weight."""
    c, p = np.asarray(correct, float), np.asarray(conf, float)
    w = _w(weights, len(c))
    cov, risk = [], []
    for v in np.unique(p)[::-1]:
        m = p >= v
        cov.append(w[m].sum() / w.sum())
        risk.append(1 - (w[m] * c[m]).sum() / w[m].sum())
    return np.array(cov), np.array(risk)


def aurc_w(correct, conf, weights=None) -> float:
    """Area under the weighted risk-coverage step curve (ties answered together)."""
    cov, risk = risk_coverage_w(correct, conf, weights)
    return float(np.sum(np.diff(np.concatenate([[0.0], cov])) * risk))


def selective_risk_at(correct, conf, coverage: float, weights=None) -> float:
    """Risk when answering the most confident rows up to `coverage` (by weight; ties answered together)."""
    cov, risk = risk_coverage_w(correct, conf, weights)
    i = int(np.searchsorted(cov, coverage - 1e-12))
    return float(risk[min(i, len(risk) - 1)])


# ---------------------------------------------------------------- injection-clustered statistics
def per_injection(df, value_col: str, cluster_col: str = "injection_id", weight_col: str = "weight"):
    """Weighted mean of `value_col` per injection (one value per independent unit)."""
    g = df.assign(_wv=df[value_col].astype(float) * df[weight_col]).groupby(cluster_col)
    return g["_wv"].sum() / g[weight_col].sum()


def cluster_bootstrap(values, clusters, weights=None, fn=None, n: int = 10000, seed: int = 0,
                      alpha: float = 0.05) -> dict:
    """Percentile bootstrap resampling injections (clusters) with replacement.

    `values`: 1-D, or 2-D (records x arms) for a paired statistic; every draw resamples the same
    clusters for all arms. `fn(values, weights) -> float`; default: weighted mean (1-D) or weighted
    mean of column 0 minus column 1 (2-D). Returns est, lo, hi and p = two-sided share of draws on the
    other side of 0 from the estimate."""
    v = np.asarray(values, float)
    cl = np.asarray(clusters)
    w = _w(weights, len(v))
    if fn is None:
        fn = (lambda x, ww: float((ww * x).sum() / ww.sum())) if v.ndim == 1 else \
             (lambda x, ww: float((ww * (x[:, 0] - x[:, 1])).sum() / ww.sum()))
    uniq, inv = np.unique(cl, return_inverse=True)
    members = [np.flatnonzero(inv == i) for i in range(len(uniq))]
    rng = np.random.default_rng(seed)
    stats = np.empty(n)
    for b in range(n):
        idx = np.concatenate([members[i] for i in rng.integers(0, len(uniq), len(uniq))])
        stats[b] = fn(v[idx], w[idx])
    est = fn(v, w)
    lo, hi = np.nanquantile(stats, [alpha / 2, 1 - alpha / 2])
    side = stats <= 0 if est > 0 else stats >= 0
    p = float(min(1.0, 2 * np.mean(side))) if est != 0 else 1.0
    return {"est": float(est), "lo": float(lo), "hi": float(hi), "p": p, "n_clusters": int(len(uniq))}


def sign_flip_test(diff_per_injection, n: int = 10000, seed: int = 0) -> dict:
    """Paired permutation test on per-injection differences (random sign flips of each unit)."""
    d = np.asarray(diff_per_injection, float)
    d = d[~np.isnan(d)]
    if not len(d):
        return {"mean": float("nan"), "p": float("nan"), "n": 0}
    obs = abs(d.mean())
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1.0, 1.0], size=(n, len(d)))
    null = np.abs((signs * d).mean(axis=1))
    return {"mean": float(d.mean()), "p": float((1 + np.sum(null >= obs - 1e-12)) / (n + 1)), "n": int(len(d))}


# ---------------------------------------------------------------- censored ranks and vectorised cluster bootstrap
RANK_CAP = 5    # prompt v1 returns at most 5 services per sample: ranks beyond the cap are censored


def mrr_at_k(ranks, k: int = RANK_CAP, weights=None) -> float:
    """Censored mean reciprocal rank: 1/rank within the top k, 0 beyond (rank > k is unknown)."""
    r = np.asarray(ranks, float)
    return wmean(np.where(r <= k, 1.0 / r, 0.0), weights)


def cluster_draws(clusters, n: int, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Bootstrap draws over clusters as a (n x k) count matrix, plus the cluster index of every record."""
    uniq, inv = np.unique(np.asarray(clusters), return_inverse=True)
    k = len(uniq)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, k, (n, k))
    counts = np.zeros((n, k))
    np.add.at(counts, (np.repeat(np.arange(n), k), idx.ravel()), 1.0)
    return counts, inv


def cluster_bootstrap_means(values, clusters, weights=None, n: int = 10000, seed: int = 0,
                            alpha: float = 0.05) -> dict:
    """Percentile cluster bootstrap of weighted means, vectorised. `values`: (records,) or (records x m);
    every draw resamples the same clusters for all columns. Returns est, lo, hi (arrays for 2-D input)."""
    v = np.asarray(values, float)
    one = v.ndim == 1
    v = v[:, None] if one else v
    w = _w(weights, len(v))
    counts, inv = cluster_draws(clusters, n, seed)
    k = counts.shape[1]
    s = np.zeros((k, v.shape[1]))
    np.add.at(s, inv, w[:, None] * v)
    wc = np.bincount(inv, weights=w, minlength=k)
    with np.errstate(invalid="ignore", divide="ignore"):
        stats = (counts @ s) / (counts @ wc)[:, None]
    est = (w[:, None] * v).sum(0) / w.sum()
    lo, hi = np.nanquantile(stats, [alpha / 2, 1 - alpha / 2], axis=0)
    out = {"est": est, "lo": lo, "hi": hi, "n_clusters": int(k)}
    return {key: (val[0] if one and isinstance(val, np.ndarray) else val) for key, val in out.items()}
