"""Simulated MDE of H1 (`gain_exact@0.7` vs C2) on the verified test denominator (CPU, no model, no data).

usage: python -X utf8 h1-mde-recheck.py OUT_CSV

Structure from receipt 02-h1-membership-04: 69 traced injections x 3 records + 39 RE2-SS injections x 2
records = 108 injections / 285 records; weight 1 / records of the injection. Estimator and CI are the
analysis' own: `rca.selective.selective_endpoints` (cluster bootstrap over injections, percentile 95 %).
A replication is "detected" when the CI excludes 0. Assumptions (placeholders until a DEV pilot):
- correctness: per-injection propensity ~ Beta with mean 1 - e and concentration k (records of one
  injection correlated); base error e in {0.3, 0.5, 0.7}; k = 4;
- score: consensus-like, 11 levels (round(sigmoid(mu * (2c - 1) + N(0,1)), 1)); mu sets the effect;
- the expected gain of each mu is the mean point estimate over the replications.
Sensitivity (D10): the same with clusters = groups of 3 injections sharing one propensity.
"""
import csv
import sys

import numpy as np

from rca import selective

TRACED, SS = 69, 39
REPS, BOOT = 300, 1000
MUS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]


def structure():
    inj = np.r_[np.repeat(np.arange(TRACED), 3), np.repeat(np.arange(TRACED, TRACED + SS), 2)]
    w = 1.0 / np.bincount(inj)[inj]
    return inj, w


def simulate(rng, inj, w, err, mu, k, groups):
    unit = groups[inj] if groups is not None else inj
    q = rng.beta((1 - err) * k, err * k, size=unit.max() + 1)[unit]
    c = rng.random(len(inj)) < q
    s = np.round(1 / (1 + np.exp(-(mu * (2 * c - 1) + rng.normal(size=len(c))))), 1)
    clusters = unit if groups is not None else inj
    e = selective.selective_endpoints(c, s, clusters, w, coverages=(0.7,), n_boot=BOOT,
                                      seed=int(rng.integers(1 << 30)))["gain_exact@0.7"]
    return e["est"], (e["lo"] > 0) or (e["hi"] < 0)


def main():
    out = sys.argv[1]
    inj, w = structure()
    assert len(inj) == 285 and inj.max() + 1 == 108
    grp = np.r_[np.arange(TRACED) // 3, TRACED // 3 + np.arange(SS) // 3]       # groups of 3 repeats
    rows = []
    for clustering, groups in (("injection", None), ("group_id", grp)):
        for err in (0.3, 0.5, 0.7):
            rng = np.random.default_rng(0)
            for mu in MUS:
                res = [simulate(rng, inj, w, err, mu, 4, groups) for _ in range(REPS)]
                est = np.array([r[0] for r in res])
                rows.append({"clustering": clustering, "base_error": err, "mu": mu, "mean_gain": round(float(est.mean()), 4),
                             "power": round(float(np.mean([r[1] for r in res])), 3), "reps": REPS, "n_boot": BOOT})
                print(rows[-1], flush=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        wr.writeheader()
        wr.writerows(rows)


if __name__ == "__main__":
    main()
