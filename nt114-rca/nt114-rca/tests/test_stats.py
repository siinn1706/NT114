"""Weighted metrics, injection-clustered statistics and the randomised controls."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score, roc_auc_score

from rca import gate, metrics


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


def _table(n=50, seed=0):
    rng = np.random.default_rng(seed)
    conf = np.round(rng.random(n), 1)                  # many ties
    return pd.DataFrame({"answer_ok": rng.random(n) < conf, "answer_conf": conf, "answer_tok": 100.0,
                         "escalate_ok": rng.random(n) < 0.7, "escalate_conf": 0.9, "escalate_tok": 300.0,
                         "retrieve_ok": rng.random(n) < 0.5, "retrieve_conf": 0.5, "retrieve_tok": 200.0})


def test_coverage_match():
    t = _table()
    draws = gate.coverage_matched_threshold(t, 0.62, draws=200, seed=0)
    k = round(0.62 * len(t))
    assert all((d == "answer").sum() == k for d in draws)
    assert len({tuple(d) for d in draws}) > 1                        # ties broken differently per draw
    accepted = np.array([(d == "answer").to_numpy() for d in draws])
    # every accepted row is at least as confident as every rejected row, in every draw
    for row in accepted:
        assert t["answer_conf"][row].min() >= t["answer_conf"][~row].max()
    rnd = gate.coverage_matched_random(t, 0.62, draws=50, seed=1)
    assert all((d == "answer").sum() == k for d in rnd)
    res = gate.evaluate_draws(t, draws)
    assert res["coverage"] == pytest.approx(k / len(t)) and res["draws"] == 200


def test_route_matched():
    t = _table()
    ref = pd.Series(np.repeat(["answer", "abstain", "escalate", "retrieve"], [20, 10, 12, 8]), index=t.index)
    for draws in (gate.route_matched_random(t, ref, draws=20), gate.route_matched_consensus(t, ref, draws=20)):
        for d in draws:
            assert d.value_counts().to_dict() == ref.value_counts().to_dict()
    r2 = gate.route_matched_consensus(t, ref, draws=1)[0]
    assert t["answer_conf"][r2 == "abstain"].max() <= t["answer_conf"][r2 == "answer"].min()


def test_evaluate_uses_final_arm_confidence_and_weights():
    t = pd.DataFrame({"answer_ok": [False, False], "answer_conf": [0.9, 0.2], "answer_tok": [10.0, 10.0],
                      "escalate_ok": [False, True], "escalate_conf": [0.2, 0.95], "escalate_tok": [30.0, 30.0]})
    r = gate.evaluate(t, pd.Series(["escalate", "answer"]))
    assert r["confident_wrong_per_100"] == 0.0 and r["wrong_per_100"] == 100.0    # escalate arm's 0.2 is not confident
    r = gate.evaluate(t, pd.Series(["answer", "escalate"]), weights=[3, 1])
    assert r["confident_wrong_per_100"] == pytest.approx(75.0) and r["acc_answered"] == pytest.approx(0.25)
    assert gate.oracle_policy(t).tolist() == ["abstain", "escalate"]
    with pytest.raises(ValueError, match="retrieve"):
        gate.evaluate(t, pd.Series(["retrieve", "answer"]))
