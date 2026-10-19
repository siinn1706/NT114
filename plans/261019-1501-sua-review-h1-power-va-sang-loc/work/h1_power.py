"""Design-stage power for the H1 selective-risk contrasts (CPU only).

Synthetic data only: no model output, no NT114 labels, no test rows. The estimators of
`rca.metrics` and `rca.selective` are used unchanged; this file adds the exact-coverage form of
C1 (the expectation of the seeded tie-break in `selective.coverage_matched_threshold`) and a
vectorised cluster bootstrap over injections (same draws as `metrics.cluster_draws`).

Endpoints (proposal; nothing here is preregistered):
  E1  fixed-coverage gain  G_c   = base error - risk of answering exactly a c share of the weight,
                                   highest score first, boundary tie group answered fractionally.
                                   C2 (random deferral) has expected risk = base error at any coverage.
  E1t same, ties answered together (`metrics.selective_risk_at`): realised coverage >= c.
  E2  frozen-threshold gain G_tau = base error - risk(score >= tau) on test, tau from
                                   `selective.fit_threshold` on DEV (coverage goal c). Realised test
                                   coverage is reported, not matched; C2 is valid at any coverage.
  E3  AURC gain            G_A   = base error - AURC (ties answered together, `metrics.aurc_w`).
Test: percentile cluster bootstrap over injections (as `contrasts.py` for non-decomposable
metrics); H0 G <= 0 is rejected when the lower bound of the two-sided (1 - alpha) interval > 0.

Generator: injection effect u_i (ICC), record latent l = sqrt(icc) u + sqrt(1-icc) e ~ N(0, 1),
correct = l > Phi^-1(err); n = 10 samples agree with probability expit(m + s (rho l + sqrt(1-rho^2) z)),
score = agreeing samples / 10 (11 levels, ties as in the consensus estimator). rho = 0 is the null.

usage: python -I h1_power.py <out_dir> [--reps N] [--boot B] [--seed S]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from statistics import NormalDist

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "nt114-rca" / "nt114-rca" / "src"))
from rca import metrics, selective  # noqa: E402

COVERAGE = 0.7
ALPHAS = {"a05": 0.05, "a05_holm3": 0.05 / 3}   # alone, and the first Holm step of a 3-test family
N_SAMPLES = 10

# Cluster structure (records per injection) of the measured sets: protocol v2 §5.1, research/06 V5,
# and the RCAEval condition matrix (single-modality removal applies to 108 test / 78 DEV injections).
STRUCTURES = {
    "rcaeval_full": {"test": [1] * 218, "dev": [1] * 143},
    "rcaeval_missing_pool": {"test": [3] * 69 + [2] * 39, "dev": [3] * 54 + [2] * 24},
    "rcaeval_blindroot_x_ev": {"test": [1] * 52, "dev": None},
    "nezha_full": {"test": [1] * 97, "dev": None},
    "rca100_full": {"test": [2] * 16 + [1] * 54, "dev": None},
    "aiops2025_full": {"test": [1] * 318, "dev": None},
}


# ---------------------------------------------------------------- generator
def generate(sizes, err, rho, rng, icc=0.5, m=1.0, s=1.5):
    """(correct, score, clusters, weights) for one synthetic set."""
    sizes = np.asarray(sizes, int)
    cl = np.repeat(np.arange(len(sizes)), sizes)
    u = rng.normal(size=len(sizes))
    lat = np.sqrt(icc) * u[cl] + np.sqrt(1 - icc) * rng.normal(size=len(cl))
    correct = lat > NormalDist().inv_cdf(err)
    z = rng.normal(size=len(cl))
    p = 1 / (1 + np.exp(-(m + s * (rho * lat + np.sqrt(1 - rho ** 2) * z))))
    score = rng.binomial(N_SAMPLES, p) / N_SAMPLES
    return correct, score, cl, 1.0 / sizes[cl]


# ---------------------------------------------------------------- estimators on level matrices
# The level-matrix estimators live in `rca.selective` (shared with `rca.analyze`); E1/E1t default to COVERAGE here.
level_mats, boot_mats, _base = selective.level_mats, selective.boot_mats, selective._base
gain_threshold, gain_aurc = selective.gain_threshold, selective.gain_aurc


def gain_exact(Wl, Cl, coverage=COVERAGE):
    return selective.gain_exact(Wl, Cl, coverage)


def gain_tiegroup(Wl, Cl, coverage=COVERAGE):
    return selective.gain_tiegroup(Wl, Cl, coverage)


def ci_lo(draws, alpha):
    return float(np.nanquantile(draws, alpha / 2))


def ci(draws, level):
    a = 1 - level
    return float(np.nanquantile(draws, a / 2)), float(np.nanquantile(draws, 1 - a / 2))


# ---------------------------------------------------------------- truth (large sample)
def truth(err, rho, n=400_000, seed=1):
    rng = np.random.default_rng(seed)
    c, s, cl, w = generate([1] * n, err, rho, rng)
    lv, Mw, Mc, _ = level_mats(c, s, cl, w)
    Wl, Cl = Mw.sum(0, keepdims=True), Mc.sum(0, keepdims=True)
    return {"true_gain_exact": float(gain_exact(Wl, Cl)[0]),
            "true_gain_tiegroup": float(gain_tiegroup(Wl, Cl)[0][0]),
            "true_cov_tiegroup": float(gain_tiegroup(Wl, Cl)[1][0]),
            "true_gain_aurc": float(gain_aurc(Wl, Cl)[0]),
            "true_auroc": metrics.auroc(~c[:50_000], -s[:50_000]),
            "share_at_top_level": float((s == s.max()).mean())}


# ---------------------------------------------------------------- one scenario
def simulate(structure, err, rho, reps, n_boot, seed, icc=0.5):
    st = STRUCTURES[structure]
    rng = np.random.default_rng(seed)
    rej = {f"{e}_{a}": 0 for e in ("E1", "E1t", "E2", "E3") for a in ALPHAS}
    est = {e: [] for e in ("E1", "E1t", "E2", "E3")}
    cov_e2, cov_e1t, boundary = [], [], []
    n_e2 = 0
    for r in range(reps):
        c, s, cl, w = generate(st["test"], err, rho, rng, icc)
        lv, Mw, Mc, inv = level_mats(c, s, cl, w)
        Wl, Cl = boot_mats(Mw, Mc, inv, n_boot, seed + r)
        g1 = gain_exact(Wl, Cl)
        g1t, cv1t = gain_tiegroup(Wl, Cl)
        g3 = gain_aurc(Wl, Cl)
        draws = {"E1": g1, "E1t": g1t, "E3": g3}
        if st["dev"] is not None:
            dc, ds, dcl, dw = generate(st["dev"], err, rho, rng, icc)
            tau = selective.fit_threshold(dc, ds, dw, coverage=COVERAGE)
            g2, cv2 = gain_threshold(Wl, Cl, lv, tau)
            draws["E2"] = g2
            cov_e2.append(cv2[0])
            n_e2 += 1
        cov_e1t.append(cv1t[0])
        T = Wl[0].sum()
        j = int(np.argmax(Wl[0].cumsum() >= COVERAGE * T - 1e-12))
        boundary.append(Wl[0, j] / T)
        for e, d in draws.items():
            est[e].append(d[0])
            for a, al in ALPHAS.items():
                rej[f"{e}_{a}"] += ci_lo(d[1:], al) > 0
    out = {"structure": structure, "n_injections": len(st["test"]), "n_records": int(sum(st["test"])),
           "err": err, "rho": rho, "icc": icc, "reps": reps, "boot": n_boot}
    for e, v in est.items():
        if v:
            out[f"{e}_mean"], out[f"{e}_sd"] = float(np.nanmean(v)), float(np.nanstd(v))
    for k, v in rej.items():
        e = k.split("_")[0]
        nn = n_e2 if e == "E2" else reps
        out[f"power_{k}"] = v / nn if nn else np.nan
    out["E1t_cov_mean"] = float(np.mean(cov_e1t))
    out["boundary_tie_share_mean"] = float(np.mean(boundary))
    if cov_e2:
        q = np.quantile(cov_e2, [0.05, 0.5, 0.95])
        out.update(E2_cov_p05=float(q[0]), E2_cov_p50=float(q[1]), E2_cov_p95=float(q[2]),
                   E2_cov_off_by_gt_0_10=float(np.mean(np.abs(np.asarray(cov_e2) - COVERAGE) > 0.10)))
    return out


def simulate_interaction(rho_full, rho_miss, err_full, err_miss, reps, n_boot, seed, icc=0.5):
    """Paired DiD on the 108 multimodal RCAEval test injections: G_c(missing pool) - G_c(full),
    both arms resampled with the same injection draws."""
    sizes = np.asarray(STRUCTURES["rcaeval_missing_pool"]["test"])
    rng = np.random.default_rng(seed)
    q = NormalDist().inv_cdf
    rej = {a: 0 for a in ALPHAS}
    ests = []
    for r in range(reps):
        k = len(sizes)
        u = rng.normal(size=k)
        arms = []
        for sz, rho, err in ((np.ones(k, int), rho_full, err_full), (sizes, rho_miss, err_miss)):
            cl = np.repeat(np.arange(k), sz)
            lat = np.sqrt(icc) * u[cl] + np.sqrt(1 - icc) * rng.normal(size=len(cl))
            c = lat > q(err)
            p = 1 / (1 + np.exp(-(1.0 + 1.5 * (rho * lat + np.sqrt(1 - rho ** 2) * rng.normal(size=len(cl))))))
            s = rng.binomial(N_SAMPLES, p) / N_SAMPLES
            lv, Mw, Mc, inv = level_mats(c, s, cl, 1.0 / sz[cl])
            arms.append((Mw, Mc, inv))
        counts, _ = metrics.cluster_draws(np.arange(k), n_boot, seed + r)
        C = np.vstack([np.ones((1, k)), counts])
        g = [gain_exact(C @ Mw, C @ Mc) for Mw, Mc, _ in arms]
        d = g[1] - g[0]
        ests.append(d[0])
        for a, al in ALPHAS.items():
            rej[a] += ci_lo(d[1:], al) > 0
    return {"rho_full": rho_full, "rho_missing": rho_miss, "err_full": err_full, "err_missing": err_miss,
            "n_injections": len(sizes), "did_mean": float(np.mean(ests)), "did_sd": float(np.std(ests)),
            **{f"power_{a}": v / reps for a, v in rej.items()}}


# ---------------------------------------------------------------- DEV pilot decision rule
def pilot_decision(correct, score, clusters, weights, power_curve, sesoi=0.05, coverage=COVERAGE,
                   n_boot=4000, seed=0, alpha=ALPHAS["a05_holm3"]):
    """Proposed DEV-pilot rule for the H1 primary endpoint (E1). Uses DEV labels only.

    power_curve: [(true_gain, power)] for the declared test structure at the DEV base error and the
    declared alpha (from the simulation table). Returns the decision and the quantities behind it.
      futility      upper 95 % bound of G_c(DEV) < sesoi
      confirmatory  power at max(lower 80 % bound, 0) >= 0.80, and the cross-fitted DEV threshold
                    transfers within +-0.10 of the coverage goal in both folds
      exploratory   otherwise (estimate with CI, no confirmatory claim)
    """
    c = np.asarray(correct, bool)
    lv, Mw, Mc, inv = level_mats(c, score, clusters, weights)
    Wl, Cl = boot_mats(Mw, Mc, inv, n_boot, seed)
    g = gain_exact(Wl, Cl)
    lo80, hi80 = ci(g[1:], 0.80)
    lo95, hi95 = ci(g[1:], 0.95)
    delta = max(lo80, 0.0)
    xs, ps = zip(*sorted(power_curve))
    pw = float(np.interp(delta, xs, ps))
    # 2-fold cross-fitting by injection: fit tau on one fold, realised coverage on the other
    _, inv_all = np.unique(np.asarray(clusters), return_inverse=True)
    fold = np.random.default_rng(seed).permutation(inv_all.max() + 1) % 2
    s, w = np.asarray(score, float), np.asarray(weights, float)
    covs = []
    for f in (0, 1):
        fit, ev = fold[inv_all] == f, fold[inv_all] != f
        tau = selective.fit_threshold(c[fit], s[fit], w[fit], coverage=coverage)
        covs.append(float(w[ev][s[ev] >= tau].sum() / w[ev].sum()))
    transfer_ok = all(abs(x - coverage) <= 0.10 for x in covs)
    if hi95 < sesoi:
        decision = "futility"
    elif pw >= 0.80 and transfer_ok:
        decision = "confirmatory"
    else:
        decision = "exploratory"
    return {"decision": decision, "gain": float(g[0]), "ci80": (lo80, hi80), "ci95": (lo95, hi95),
            "delta_conservative": delta, "power_at_delta": pw, "crossfit_coverage": covs,
            "transfer_ok": transfer_ok, "base_error": float(_base(Wl[:1], Cl[:1])[0]), "sesoi": sesoi,
            "alpha": alpha}


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--reps", type=int, default=300)
    ap.add_argument("--boot", type=int, default=999)
    ap.add_argument("--seed", type=int, default=20261019)
    a = ap.parse_args(argv)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    errs, rhos = (0.2, 0.35, 0.5), (0.0, 0.15, 0.3, 0.45, 0.6)
    tr = {(e, r): truth(e, r) for e in errs for r in rhos}
    rows = []
    for i, st in enumerate(STRUCTURES):
        for j, e in enumerate(errs):
            for k, r in enumerate(rhos):
                row = simulate(st, e, r, a.reps, a.boot, a.seed + 1000 * i + 100 * j + 10 * k)
                rows.append({**row, **tr[(e, r)]})
                print(f"{st} err={e} rho={r} E1={row['E1_mean']:.3f} pow={row['power_E1_a05']:.2f}/"
                      f"{row['power_E1_a05_holm3']:.2f} ({time.time() - t0:.0f}s)", flush=True)
    inter = [simulate_interaction(0.3, rm, 0.3, 0.45, a.reps, a.boot, a.seed + 77 + n)
             for n, rm in enumerate((0.3, 0.45, 0.6))]
    import csv
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(out / "h1-power-grid.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=keys)
        wr.writeheader()
        wr.writerows(rows)
    with open(out / "h1-power-interaction.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(inter[0]))
        wr.writeheader()
        wr.writerows(inter)
    # MDE: smallest true E1 gain with power >= 0.80 (linear interpolation over the rho grid)
    mde = []
    for st in STRUCTURES:
        for e in errs:
            g = sorted((r["true_gain_exact"], r) for r in rows if r["structure"] == st and r["err"] == e)
            for al in ALPHAS:
                xs = [x for x, _ in g]
                ps = [r[f"power_E1_{al}"] for _, r in g]
                val = None
                for x0, x1, p0, p1 in zip(xs, xs[1:], ps, ps[1:]):
                    if p0 < 0.8 <= p1:
                        val = x0 + (0.8 - p0) * (x1 - x0) / (p1 - p0)
                        break
                if val is None and ps[0] >= 0.8:
                    val = xs[0]
                mde.append({"structure": st, "err": e, "alpha": al,
                            "mde_gain_E1": round(val, 4) if val is not None else f"> {xs[-1]:.3f}",
                            "auroc_at_mde_grid_max": round(g[-1][1]["true_auroc"], 3)})
    with open(out / "h1-mde.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(mde[0]))
        wr.writeheader()
        wr.writerows(mde)
    (out / "h1-power-run.json").write_text(json.dumps(
        {"reps": a.reps, "boot": a.boot, "seed": a.seed, "coverage": COVERAGE, "alphas": ALPHAS,
         "structures": {k: {"test_injections": len(v["test"]), "test_records": sum(v["test"]),
                            "dev_injections": len(v["dev"]) if v["dev"] else None} for k, v in STRUCTURES.items()},
         "seconds": round(time.time() - t0, 1), "numpy": np.__version__}, indent=1), encoding="utf-8")
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
