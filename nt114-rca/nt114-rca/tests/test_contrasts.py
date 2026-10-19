"""Paired-contrast engine: intersection, pairing, decomposable and set metrics, Holm, simulation checks."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rca import contrasts


def _records(conds, n_inj=30, per=2, p=None, seed=0):
    """Records of `per` incidents per injection under each condition; `p`: P(correct) per condition."""
    rng = np.random.default_rng(seed)
    p = p or {c: 0.6 for c in conds}
    rows = []
    for i in range(n_inj):
        for j in range(per):
            uid = f"u{i}_{j}"
            for c in conds:
                ok = rng.random() < p[c]
                rows.append({"incident_uid": uid, "injection_id": f"i{i}", "condition": c, "rank": 1 if ok else 6,
                             "correct": ok, "score_consensus": rng.random(), "score_verbal": rng.random(),
                             "representative": j == 0})
    return pd.DataFrame(rows)


def test_intersection_reports_dropped_incidents():
    df = _records(["full", "blind_root"], n_inj=5, per=1)
    df = df[~((df.incident_uid == "u0_0") & (df.condition == "blind_root"))]          # only in one arm
    spec = {"name": "x", "a": {"condition": "full"}, "b": {"condition": "blind_root"}, "metric": "ac1"}
    arms, common, dropped = contrasts.intersect(df, spec)
    assert "u0_0" not in common and dropped == {"a": 1, "b": 0}
    row = contrasts.evaluate(df, spec, n_boot=200, n_perm=200)
    assert row["n_incidents"] == 4 and row["dropped_a"] == 1


def test_decomposable_estimate_is_mean_of_per_injection_differences():
    df = pd.DataFrame({"incident_uid": ["a", "b", "c"] * 2, "injection_id": ["i", "i", "j"] * 2,
                       "condition": ["full"] * 3 + ["x"] * 3, "rank": [1, 1, 1, 1, 6, 6],
                       "correct": [True, True, True, True, False, False]})
    row = contrasts.evaluate(df, {"name": "d", "a": {"condition": "full"}, "b": {"condition": "x"}, "metric": "ac1"},
                             n_boot=200, n_perm=200)
    # injection i: (0 + 1) / 2 = 0.5; injection j: 1 -> mean 0.75 (not the per-record 2/3)
    assert row["est"] == pytest.approx(0.75) and row["n_injections"] == 2 and row["test"] == "sign_flip"


def test_did_and_censored_mrr():
    df = pd.DataFrame({"incident_uid": ["a"] * 4, "injection_id": ["i"] * 4,
                       "condition": ["full", "b", "c", "d"], "rank": [1, 7, 2, 2], "correct": [True, False, False, False]})
    spec = {"name": "did", "kind": "did", "a": {"condition": "full"}, "b": {"condition": "b"},
            "c": {"condition": "c"}, "d": {"condition": "d"}, "metric": "mrr5"}
    assert contrasts.evaluate(df, spec, n_boot=50, n_perm=50)["est"] == pytest.approx(1.0)   # (1 - 0) - (0.5 - 0.5)


def test_set_metric_uses_paired_cluster_bootstrap():
    df = _records(["full"], n_inj=40, per=2)
    df["score_consensus"] = np.where(df["correct"], 0.9, 0.1)          # a perfect detector
    spec = {"name": "a", "a": {"score": "consensus"}, "b": {"score": "verbal"}, "metric": "auroc",
            "within": {"condition": "full"}}
    row = contrasts.evaluate(df, spec, n_boot=300)
    assert row["test"] == "cluster_bootstrap" and row["est"] > 0.3 and row["lo"] > 0


def test_require_changed_and_holm_families():
    df = _records(["full", "blind_root"], n_inj=10, per=1)
    df["same_as_full"] = (df.condition == "blind_root") & df.incident_uid.isin(["u0_0", "u1_0"])
    specs = [{"name": "c1", "a": {"condition": "full"}, "b": {"condition": "blind_root"}, "metric": "ac1",
              "require_changed": True},
             {"name": "c2", "a": {"condition": "full"}, "b": {"condition": "blind_root"}, "metric": "ac3"}]
    out = contrasts.run(df, specs, families={"F": ["c1", "c2"]}, n_boot=200, n_perm=200)
    assert out.loc[out["filter"] == "require_changed", "n_incidents"].item() == 8
    fam = out[out.family == "F"]
    assert len(fam) == 2 and (fam["p_holm"] >= fam["p"] - 1e-12).all()
    assert out.loc[out["filter"] == "require_changed", "exploratory"].item()          # filtered rows are not in a family
    assert out["assumptions"].str.contains("intersection").all()


def test_duplicate_records_per_arm_are_refused():
    df = _records(["full"], n_inj=3, per=1)
    df = pd.concat([df, df.assign(model="other")], ignore_index=True)
    with pytest.raises(ValueError, match="several records per incident"):
        contrasts.intersect(df, {"name": "x", "a": {"condition": "full"}, "b": {"condition": "full"}, "metric": "ac1"})


def test_simulation_coverage_and_type_one_error():
    """RCA100-like structure (70 injections, 1-4 records each): the 95 % CI covers the true difference in
    [0.93, 0.97] of replications (Monte-Carlo band for 400 draws) and sign-flip type-I error is <= 0.07."""
    rng = np.random.default_rng(1)
    sizes = rng.integers(1, 5, 70)
    spec = {"name": "s", "a": {"condition": "full"}, "b": {"condition": "x"}, "metric": "ac1"}

    def sample(shift):
        rows = []
        for i, k in enumerate(sizes):
            base = rng.random() * 0.6 + 0.2                    # injection-level difficulty (clustering)
            for j in range(k):
                for c, s in (("full", shift), ("x", 0.0)):
                    ok = rng.random() < base + s
                    rows.append({"incident_uid": f"{i}_{j}", "injection_id": i, "condition": c,
                                 "rank": 1 if ok else 6, "correct": ok})
        return pd.DataFrame(rows)

    reps, cover, reject = 400, 0, 0
    for r in range(reps):
        row = contrasts.evaluate(sample(0.1), spec, n_boot=300, n_perm=10, seed=r)
        cover += row["lo"] <= 0.1 <= row["hi"]
        reject += contrasts.evaluate(sample(0.0), spec, n_boot=10, n_perm=400, seed=r)["p"] < 0.05
    assert 0.93 <= cover / reps <= 0.97, cover / reps
    assert reject / reps <= 0.07, reject / reps
