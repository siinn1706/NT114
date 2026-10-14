"""Độ đo: độ chính xác, "sai mà chắc", độ hiệu chỉnh, risk–coverage, kiểm định thống kê."""
from __future__ import annotations

import numpy as np
from scipy.stats import binomtest


def rank_of_truth(ranking: list[str], truth: str) -> int:
    """Vị trí (1-based) của dịch vụ gốc; = số dịch vụ kỹ sư phải kiểm tra theo thứ tự gợi ý.
    Không có trong danh sách -> len+1 (phạt)."""
    return ranking.index(truth) + 1 if truth in ranking else len(ranking) + 1


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
