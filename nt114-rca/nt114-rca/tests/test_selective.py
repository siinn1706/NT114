"""Selective evaluator on one model's cached cells: action table, evaluation, controls."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rca import selective


def _table(n=50, seed=0):
    rng = np.random.default_rng(seed)
    conf = np.round(rng.random(n), 1)                  # many ties
    return pd.DataFrame({"answer_ok": rng.random(n) < conf, "answer_conf": conf, "answer_tok": 100.0,
                         "retrieve_ok": rng.random(n) < 0.5, "retrieve_conf": 0.5, "retrieve_tok": 200.0})


def _grid_rows(oracle_sim=None):
    rows = []
    for meth, mode, sim in (("none", "-", None), ("hybrid", "precedent", 0.3)) + ((("hybrid", "no_precedent", oracle_sim),) if oracle_sim else ()):
        rows.append({"model": "m", "model_role": "primary", "prompt_version": "v1", "incident_uid": "x.0000000000000001",
                     "case_id": "x.0000000000000001", "condition": "full", "system": "s", "retrieval": meth,
                     "store_mode": mode, "oracle_store": mode == "no_precedent", "features": {"has_metrics": 1},
                     "hits": [] if sim is None else [{"dense_sim": sim}], "correct": True, "rank": 1,
                     "conf_consensus": 0.5, "conf_verbal": 0.5, "abstain_vote": 0.0, "parse_rate": 1.0,
                     "n_candidates": 3, "prompt_tokens": 1, "completion_tokens": 1, "latency_s": 0.1})
    return pd.DataFrame(rows)


def test_action_table_uses_precedent_store_and_refuses_oracle_rows():
    t = selective.action_table(_grid_rows())
    assert t["hit_top_sim"].tolist() == [0.3] and t["retrieve_tok"].tolist() == [4.0]
    with pytest.raises(ValueError, match="oracle_store"):
        selective.action_table(_grid_rows(oracle_sim=0.9))


def test_action_table_has_no_second_model_arm():
    rows = _grid_rows()
    other = rows.iloc[[0]].assign(model="big", model_role="replication", correct=False)
    t = selective.action_table(pd.concat([rows, other], ignore_index=True))
    assert len(t) == 1 and bool(t["answer_ok"].iloc[0])
    assert {c.split("_")[0] for c in t if c.endswith("_ok")} == {"answer", "retrieve"}


def test_coverage_match():
    t = _table()
    draws = selective.coverage_matched_threshold(t, 0.62, draws=200, seed=0)
    k = round(0.62 * len(t))
    assert all((d == "answer").sum() == k for d in draws)
    assert len({tuple(d) for d in draws}) > 1                        # ties broken differently per draw
    accepted = np.array([(d == "answer").to_numpy() for d in draws])
    # every accepted row is at least as confident as every rejected row, in every draw
    for row in accepted:
        assert t["answer_conf"][row].min() >= t["answer_conf"][~row].max()
    rnd = selective.coverage_matched_random(t, 0.62, draws=50, seed=1)
    assert all((d == "answer").sum() == k for d in rnd)
    res = selective.evaluate_draws(t, draws)
    assert res["coverage"] == pytest.approx(k / len(t)) and res["draws"] == 200


def test_evaluate_uses_final_arm_confidence_and_weights():
    t = pd.DataFrame({"answer_ok": [False, False], "answer_conf": [0.9, 0.2], "answer_tok": [10.0, 10.0],
                      "retrieve_ok": [False, True], "retrieve_conf": [0.2, 0.95], "retrieve_tok": [30.0, 30.0]})
    r = selective.evaluate(t, pd.Series(["retrieve", "answer"]))
    assert r["confident_wrong_per_100"] == 0.0 and r["wrong_per_100"] == 100.0    # retrieve arm's 0.2 is not confident
    r = selective.evaluate(t, pd.Series(["answer", "retrieve"]), weights=[3, 1])
    assert r["confident_wrong_per_100"] == pytest.approx(75.0) and r["acc_answered"] == pytest.approx(0.25)
    assert selective.oracle_policy(t).tolist() == ["abstain", "retrieve"]
    with pytest.raises(ValueError, match="retrieve"):
        selective.evaluate(t.drop(columns=["retrieve_ok", "retrieve_conf", "retrieve_tok"]), pd.Series(["retrieve", "answer"]))
    with pytest.raises(ValueError, match="unknown actions"):
        selective.evaluate(t, pd.Series(["defer", "answer"]))


def test_run_grid_accepts_independent_runs_only():
    from rca import run_grid
    run_grid._check_roles([{"name": "a"}, {"name": "b", "role": "replication"}])
    with pytest.raises(ValueError, match="role must be one of"):
        run_grid._check_roles([{"name": "a"}, {"name": "big", "role": "judge"}])


def test_risk_coverage_summary_and_coverage_at_risk():
    c = np.array([1, 1, 0, 1, 0, 0], bool)
    s = np.array([0.9, 0.8, 0.8, 0.5, 0.2, np.nan])
    r = selective.risk_coverage_summary(c, s)
    assert r["n_scored"] == 5                                         # the NaN score is left out and counted
    # answering the top 3 (0.9 and the 0.8 tie together) gives coverage 3/5 and risk 1/3
    assert r["risk@0.5"] == pytest.approx(1 / 3)
    assert selective.coverage_at_risk(c[:5], s[:5], 0.0) == pytest.approx(0.2)
    assert selective.coverage_at_risk(c[:5], s[:5], 0.3) == pytest.approx(0.8)
    assert selective.coverage_at_risk(c[:5], s[:5], 0.4) == pytest.approx(1.0)


def test_dev_fit_threshold_transfers_unchanged():
    dc, ds = np.array([1, 1, 0, 0], bool), np.array([0.9, 0.7, 0.5, 0.3])
    assert selective.fit_threshold(dc, ds, coverage=0.5) == 0.7
    assert selective.fit_threshold(dc, ds, risk=0.0) == 0.7
    assert selective.fit_threshold(np.zeros(2, bool), np.array([0.6, 0.4]), risk=0.1) == float("inf")
    with pytest.raises(ValueError):
        selective.fit_threshold(dc, ds)
    tc, ts = np.array([1, 0, 1, 0]), np.array([0.95, 0.8, 0.6, 0.1])
    out = selective.apply_threshold(tc, ts, 0.7, clusters=[0, 1, 2, 3], n_boot=200)
    assert out["coverage"] == pytest.approx(0.5) and out["risk"] == pytest.approx(0.5)
    assert out["coverage_lo"] <= 0.5 <= out["coverage_hi"]


def test_references_and_random_arm():
    refs = {r["policy"]: r for r in selective.references([True, False, True, False], [0.0, 0.0, 1.0, 0.0])}
    l1 = refs["L1 self-abstain"]
    assert l1["coverage"] == pytest.approx(0.75) and l1["risk"] == pytest.approx(2 / 3)
    assert refs["C2 random deferral"]["risk"] == pytest.approx(0.5)
    assert refs["O oracle"]["coverage"] == pytest.approx(0.5)
    t = _table()
    for d in selective.random_arm(t, 0.3, draws=5):
        assert (d == "retrieve").sum() == 15 and set(d) <= {"answer", "retrieve"}


def test_shift_table_marks_strata_missing_from_dev():
    df = pd.DataFrame({"system": ["a", "a", "b"], "fault": ["cpu", "cpu", "mem"], "split_role": ["val", "test", "test"],
                       "correct": [True, False, False], "conf_consensus": [0.8, 0.8, 0.2]})
    t = selective.shift_table(df)
    assert set(t["present_in"]) == {"test+val", "test"}
    assert t.loc[(t.system == "b"), "base_error"].item() == 1.0


# ---------------------------------------------------------------- fixed-coverage endpoints with CIs
def test_exact_coverage_risk_is_the_expected_c1_tie_break():
    rng = np.random.default_rng(3)
    c = rng.random(40) < 0.6
    s = rng.integers(0, 4, 40) / 3                     # heavy ties at the boundary
    t = pd.DataFrame({"answer_ok": c, "answer_conf": s, "answer_tok": 0.0})
    mc = selective.evaluate_draws(t, selective.coverage_matched_threshold(t, 0.7, draws=4000, seed=1))["selective_risk"]
    assert selective.exact_coverage_risk(c, s, 0.7) == pytest.approx(mc, abs=0.004)


def test_endpoints_report_achieved_coverage_and_cis():
    from rca import metrics
    rng = np.random.default_rng(5)
    n = 90
    c = rng.random(n) < 0.6
    s = rng.integers(0, 11, n) / 10
    w = rng.uniform(0.3, 1.0, n)
    cl = np.arange(n) // 3
    e = selective.selective_endpoints(c, s, cl, w, coverages=(0.7,), risk_goals=(0.3,), n_boot=300, seed=1)
    assert e["risk@0.7"]["est"] == pytest.approx(metrics.selective_risk_at(c, s, 0.7, w))
    assert e["coverage_ties@0.7"]["est"] >= 0.7                       # ties answered together
    assert e["risk_exact@0.7"]["est"] == pytest.approx(selective.exact_coverage_risk(c, s, 0.7, w))
    assert e["AURC"]["est"] == pytest.approx(metrics.aurc_w(c, s, w))
    assert e["coverage_at_risk0.3"]["est"] == pytest.approx(selective.coverage_at_risk(c, s, 0.3, w))
    base = 1 - np.average(c, weights=w)
    assert e["gain_exact@0.7"]["est"] == pytest.approx(base - e["risk_exact@0.7"]["est"])
    for k, v in e.items():
        assert v["lo"] <= v["est"] + 1e-12 and v["est"] <= v["hi"] + 1e-12, k


def test_undefined_draws_are_ignored_and_their_share_reported():
    """One wrong record in 8 injections: a draw without it has no positive, so AUPRC is undefined there."""
    c = np.array([True] * 7 + [False])
    out = selective.confidence_endpoints(c, np.linspace(0.9, 0.2, 8), np.arange(8), n_boot=500, seed=0)
    share = out["AUPRC"]["nan_draws"]
    assert share == pytest.approx((7 / 8) ** 8, abs=0.06) and np.isfinite(out["AUPRC"]["lo"])
    assert "nan_draws" not in out["AURC"]


def test_vectorised_confidence_metrics_match_the_reference_functions():
    from rca import metrics
    rng = np.random.default_rng(11)
    n = 80
    c = rng.random(n) < 0.55
    p = rng.integers(0, 11, n) / 10
    w = rng.uniform(0.2, 1.0, n)
    r = selective.confidence_endpoints(c, p, np.arange(n) // 2, w, probability=True, support="discrete",
                                       n_boot=200, seed=2)
    assert r["AUPRC"]["est"] == pytest.approx(metrics.auprc(~c, -p, w))
    assert r["AURC"]["est"] == pytest.approx(metrics.aurc_w(c, p, w))
    assert r["Brier"]["est"] == pytest.approx(metrics.brier(c, p, w))
    assert r["ECE"]["est"] == pytest.approx(metrics.ece_w(c, p, w, "support"))
    assert r["gap"]["est"] == pytest.approx(metrics.overconfidence_gap(c, p, w))
    q = rng.random(n)
    r = selective.confidence_endpoints(c, q, np.arange(n), w, probability=True, support="continuous", n_boot=50)
    assert r["ECE"]["est"] == pytest.approx(metrics.ece_w(c, q, w, "width"))


def test_references_carry_cis_when_clusters_are_given():
    c = np.array([True, False, True, False, True, True])
    refs = {r["policy"]: r for r in selective.references(c, [0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
                                                         clusters=np.arange(6), n_boot=200)}
    for name, keys in (("L1 self-abstain", ("coverage", "risk")), ("C2 random deferral", ("risk",)),
                       ("O oracle", ("coverage",))):
        for k in keys:
            assert refs[name][f"{k}_lo"] <= refs[name][k] <= refs[name][f"{k}_hi"]


def test_shift_table_is_stratified_and_injection_weighted():
    df = pd.DataFrame({"system": "a", "fault": "cpu", "split_role": ["val"] * 4 + ["test"] * 4,
                       "condition": ["full", "no_log"] * 4, "correct": [True, False, True, True, False, False, False, True],
                       "conf_consensus": 0.5, "weight": [1, 1, 1, 1, 1 / 3, 1, 1 / 3, 1], "injection_id": list("ppqqrsrt")})
    t = selective.shift_table(df, strata=["condition"])
    assert set(t["condition"]) == {"full", "no_log"} and len(t) == 4
    row = t[(t.condition == "full") & (t.split_role == "test")].iloc[0]
    assert row["base_error"] == pytest.approx(1.0) and row["n_injections"] == 1        # records r, r: one injection
    row = t[(t.condition == "no_log") & (t.split_role == "val")].iloc[0]
    assert row["base_error"] == pytest.approx(0.5)
