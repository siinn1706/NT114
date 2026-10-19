"""Selective-risk reduction vs random deferral implied by an error-detection AUROC (binormal, equal variance).

usage: python -I selective_gain.py
Analytic planning aid only (no data): base error e, coverage c; score of wrong items ~ N(d,1), correct ~ N(0,1),
AUROC = Phi(d / sqrt 2). Abstain on the highest (1 - c) 'wrongness' scores.
"""
from statistics import NormalDist

N = NormalDist()


def risk_at_coverage(e, auroc, c):
    d = 2 ** 0.5 * N.inv_cdf(auroc)
    lo, hi = -10.0, 10.0
    for _ in range(200):  # threshold t with P(score < t) = c
        t = (lo + hi) / 2
        kept = (1 - e) * N.cdf(t) + e * N.cdf(t - d)
        lo, hi = (t, hi) if kept < c else (lo, t)
    return e * N.cdf(t - d) / c


print("e, AUROC, coverage -> selective risk, reduction vs random deferral (= e)")
for e in (0.2, 0.3, 0.4):
    for a in (0.55, 0.65, 0.75, 0.85):
        for c in (0.9, 0.7, 0.5):
            r = risk_at_coverage(e, a, c)
            print(f"e={e:.1f} AUROC={a:.2f} c={c:.1f} -> risk={r:.3f} reduction={e - r:.3f}")
