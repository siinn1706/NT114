"""Focused checks of the H1 power estimators against the unchanged rca.metrics / rca.selective code.

run: <analysis venv python> -m pytest -q test_h1_power.py   (from this directory)
"""
import itertools

import numpy as np
import pandas as pd
import pytest

import h1_power as hp
from rca import metrics, selective


def _point(correct, score, weights=None):
    c = np.asarray(correct, bool)
    lv, Mw, Mc, inv = hp.level_mats(c, score, np.arange(len(c)), weights)
    return lv, Mw.sum(0, keepdims=True), Mc.sum(0, keepdims=True)


def test_exact_coverage_equals_expected_random_tie_break():
    rng = np.random.default_rng(3)
    c = rng.random(40) < 0.6
    s = rng.integers(0, 4, 40) / 3          # heavy ties
    _, Wl, Cl = _point(c, s)
    exact = hp.gain_exact(Wl, Cl, 0.7)[0]
    t = pd.DataFrame({"answer_ok": c, "answer_conf": s, "answer_tok": 0.0})
    draws = selective.coverage_matched_threshold(t, 0.7, draws=4000, seed=1)
    base = 1 - c.mean()
    mc = base - selective.evaluate_draws(t, draws)["selective_risk"]
    # exact uses 0.7*40 = 28 rows, as round(0.7*40) in the code
    assert exact == pytest.approx(mc, abs=0.004)


def test_tiegroup_matches_metrics_selective_risk_at():
    rng = np.random.default_rng(5)
    c = rng.random(60) < 0.5
    s = rng.integers(0, 11, 60) / 10
    w = rng.uniform(0.3, 1.0, 60)
    _, Wl, Cl = _point(c, s, w)
    g, cov = hp.gain_tiegroup(Wl, Cl, 0.7)
    base = 1 - np.average(c, weights=w)
    assert base - g[0] == pytest.approx(metrics.selective_risk_at(c, s, 0.7, w))
    assert cov[0] >= 0.7


def test_aurc_matches_metrics():
    rng = np.random.default_rng(7)
    c = rng.random(50) < 0.6
    s = rng.integers(0, 11, 50) / 10
    w = rng.uniform(0.2, 1.0, 50)
    _, Wl, Cl = _point(c, s, w)
    base = 1 - np.average(c, weights=w)
    assert base - hp.gain_aurc(Wl, Cl)[0] == pytest.approx(metrics.aurc_w(c, s, w))


def test_same_auroc_different_selective_risk():
    """Three errors among ten rows, distinct scores: AUROC does not fix the risk at coverage 0.7."""
    s = np.arange(10, 0, -1) / 10           # descending, no ties
    seen = {}
    for pos in itertools.combinations(range(10), 3):
        c = np.ones(10, bool)
        c[list(pos)] = False
        au = round(metrics.auroc(~c, -s), 5)
        _, Wl, Cl = _point(c, s)
        risk = round(0.3 - hp.gain_exact(Wl, Cl, 0.7)[0], 5)
        seen.setdefault(au, set()).add(risk)
    assert {round(1 / 7, 5), round(2 / 7, 5)} <= seen[round(13 / 21, 5)]


def test_frozen_threshold_realised_coverage_review_example():
    dev_s = np.array([0.9] * 8 + [0.5] * 2)
    dev_c = np.array([True] * 7 + [False] * 3)
    tau = selective.fit_threshold(dev_c, dev_s, coverage=0.7)
    assert tau == 0.9
    test_s = np.array([0.9] * 9 + [0.5])
    test_c = np.array([True] * 6 + [False] * 4)
    lv, Wl, Cl = _point(test_c, test_s)
    g, cov = hp.gain_threshold(Wl, Cl, lv, tau)
    assert cov[0] == pytest.approx(0.9)
    assert g[0] == pytest.approx(0.4 - 3 / 9)


def test_bootstrap_row_zero_is_the_point_estimate():
    rng = np.random.default_rng(11)
    c, s, cl, w = hp.generate([3] * 20 + [1] * 10, 0.35, 0.4, rng)
    lv, Mw, Mc, inv = hp.level_mats(c, s, cl, w)
    Wl, Cl = hp.boot_mats(Mw, Mc, inv, 50, 0)
    assert Wl.shape == (51, len(lv))
    assert hp.gain_aurc(Wl[:1], Cl[:1])[0] == pytest.approx(1 - np.average(c, weights=w) - metrics.aurc_w(c, s, w))


def test_generator_null_has_no_gain_and_base_error_is_respected():
    t = hp.truth(0.35, 0.0, n=200_000)
    assert abs(t["true_gain_exact"]) < 0.005
    assert t["true_auroc"] == pytest.approx(0.5, abs=0.01)
    rng = np.random.default_rng(0)
    c, *_ = hp.generate([1] * 200_000, 0.35, 0.3, rng)
    assert 1 - c.mean() == pytest.approx(0.35, abs=0.005)


def test_pilot_decision_branches():
    curve = [(0.0, 0.05), (0.05, 0.5), (0.10, 0.9), (0.2, 1.0)]
    rng = np.random.default_rng(2)
    c, s, cl, w = hp.generate([1] * 400, 0.4, 0.0, rng)
    assert hp.pilot_decision(c, s, cl, w, curve, sesoi=0.10, n_boot=1000)["decision"] == "futility"
    c, s, cl, w = hp.generate([1] * 400, 0.4, 0.9, rng)
    strong = hp.pilot_decision(c, s, cl, w, curve, sesoi=0.05, n_boot=1000)
    assert strong["decision"] in ("confirmatory", "exploratory")
    assert strong["ci80"][0] > 0
    assert strong["decision"] == "confirmatory" or not strong["transfer_ok"]
