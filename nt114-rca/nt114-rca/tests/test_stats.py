"""Weighted metrics and injection-clustered statistics."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score, roc_auc_score

from rca import metrics


def test_weighted_metrics_equal_unweighted_with_unit_weights():
    rng = np.random.default_rng(1)
    c = rng.random(200) < 0.6
    p = np.round(rng.random(200), 2)
    w = np.ones(200)
    assert metrics.ece_w(c, p, w, "width") == pytest.approx(metrics.ece(c, p))
    assert metrics.ac_at_k_w(np.where(c, 1, 3), 1, w) == pytest.approx(c.mean())
    assert metrics.auroc(~c, -p, w) == pytest.approx(roc_auc_score(~c, -p))
    assert metrics.auprc(~c, -p, w) == pytest.approx(average_precision_score(~c, -p))
    assert metrics.brier(c, p) == pytest.approx(np.mean((p - c) ** 2))
    assert metrics.overconfidence_gap(c, p) == pytest.approx(p.mean() - c.mean())


def test_weights_equal_duplication():
    c, p = np.array([1, 0, 1, 0]), np.array([0.9, 0.8, 0.3, 0.6])
    dup_c, dup_p = np.repeat(c, [2, 1, 1, 3]), np.repeat(p, [2, 1, 1, 3])
    w = np.array([2, 1, 1, 3], float)
    for fn in (metrics.brier, metrics.aurc_w, lambda a, b, ww=None: metrics.ece_w(a, b, ww, "support")):
        assert fn(c, p, w) == pytest.approx(fn(dup_c, dup_p))
    assert metrics.auroc(c == 0, -p, w) == pytest.approx(metrics.auroc(dup_c == 0, -dup_p))


def test_auroc_ties_count_half():
    assert metrics.auroc([1, 0], [0.5, 0.5]) == 0.5
    assert metrics.auroc([1, 0, 1, 0], [1, 0, 1, 0]) == 1.0


def test_support_ece_one_bin_per_level():
    c, p = np.array([1, 1, 0, 0]), np.array([0.5, 0.5, 0.5, 0.5])
    assert metrics.ece_w(c, p, strategy="support") == pytest.approx(0.0)
    assert metrics.ece_w(c, p, strategy="mass", n_bins=2) == pytest.approx(0.5)


def test_risk_coverage_and_selective_risk():
    c, p = np.array([1, 1, 0, 0]), np.array([0.9, 0.8, 0.7, 0.1])
    cov, risk = metrics.risk_coverage_w(c, p)
    assert cov.tolist() == [0.25, 0.5, 0.75, 1.0] and risk.tolist() == pytest.approx([0, 0, 1 / 3, 0.5])
    assert metrics.selective_risk_at(c, p, 0.5) == 0.0
    assert metrics.aurc_w(c, p) == pytest.approx(np.mean(risk))


def test_cluster_bootstrap_invariance():
    """Duplicated records weighted 1/size give the same bootstrap as one record per injection."""
    rng = np.random.default_rng(0)
    v = rng.random(40) < 0.5
    sizes = rng.integers(1, 4, 40)
    dup_v = np.repeat(v, sizes)
    dup_cl = np.repeat(np.arange(40), sizes)
    dup_w = np.repeat(1 / sizes, sizes)
    a = metrics.cluster_bootstrap(v, np.arange(40), n=500)
    b = metrics.cluster_bootstrap(dup_v, dup_cl, dup_w, n=500)
    assert a == pytest.approx(b)
    naive = metrics.cluster_bootstrap(dup_v, np.arange(len(dup_v)), n=500)
    assert naive["est"] != pytest.approx(a["est"]) or naive["hi"] - naive["lo"] != pytest.approx(a["hi"] - a["lo"])


def test_paired_bootstrap_and_sign_flip():
    rng = np.random.default_rng(2)
    a = rng.random(300) < 0.7
    b = rng.random(300) < 0.4
    r = metrics.cluster_bootstrap(np.c_[a, b], np.arange(300), n=1000)
    assert r["lo"] > 0 and r["p"] < 0.01
    assert metrics.sign_flip_test(a.astype(float) - b, n=2000)["p"] < 0.01
    same = metrics.sign_flip_test(np.r_[np.ones(20), -np.ones(20)], n=2000)
    assert same["p"] > 0.5 and same["mean"] == 0


def test_per_injection():
    df = pd.DataFrame({"injection_id": ["i", "i", "j"], "weight": [0.5, 0.5, 1], "ok": [1, 0, 1]})
    assert metrics.per_injection(df, "ok").to_dict() == {"i": 0.5, "j": 1.0}


def test_known_values_with_ties():
    # positives = wrong. Scores: 0.2 negative, 0.5 positive and 0.5 negative (a tie), 0.9 positive.
    # Positive-negative pairs ranked correctly: 1 + 0.5 (tie) + 1 + 1, over 4 pairs.
    y, s = np.array([0, 1, 0, 1], bool), np.array([0.2, 0.5, 0.5, 0.9])
    assert metrics.auroc(y, s) == pytest.approx(3.5 / 4)
    assert metrics.auroc(y, s) == pytest.approx(roc_auc_score(y, s))
    # risk-coverage with a tie: answer 0.9 -> risk 0 at coverage 1/4; add the 0.5 tie -> 1/3 at 3/4; all -> 2/4
    c, p = np.array([1, 1, 0, 0], bool), np.array([0.9, 0.5, 0.5, 0.2])
    assert metrics.aurc_w(c, p) == pytest.approx(0.25 * 0 + 0.5 * (1 / 3) + 0.25 * 0.5)


def test_holm_textbook_example():
    # m = 4, sorted p = 0.005, 0.01, 0.03, 0.04 -> 4 x 0.005, 3 x 0.01, 2 x 0.03, max(1 x 0.04, 0.06)
    adj = metrics.holm({"a": 0.01, "b": 0.04, "c": 0.03, "d": 0.005})
    assert adj == pytest.approx({"d": 0.02, "a": 0.03, "c": 0.06, "b": 0.06})


def test_censored_mrr_and_vectorised_cluster_bootstrap():
    assert metrics.mrr_at_k([1, 2, 6, 11]) == pytest.approx((1 + 0.5 + 0 + 0) / 4)
    rng = np.random.default_rng(0)
    v, cl, w = rng.random(60), np.repeat(np.arange(20), 3), rng.random(60) + 0.5
    fast = metrics.cluster_bootstrap_means(v, cl, w, n=4000, seed=3)
    slow = metrics.cluster_bootstrap(v, cl, w, n=4000, seed=7)
    assert fast["est"] == pytest.approx(slow["est"])
    assert fast["lo"] == pytest.approx(slow["lo"], abs=0.02)
    assert fast["hi"] == pytest.approx(slow["hi"], abs=0.02)
    two = metrics.cluster_bootstrap_means(np.column_stack([v, 1 - v]), cl, w, n=200)
    assert two["est"][0] + two["est"][1] == pytest.approx(1.0)
