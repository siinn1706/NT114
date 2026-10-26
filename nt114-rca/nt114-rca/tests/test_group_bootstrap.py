"""D10 sensitivity: group_id bootstrap against independent references; the primary analysis unchanged;
CI readings; IM1 contrasts kept out of families."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from rca import contrasts


def frame(n_groups=30, reps=3, seed=0, same=False):
    """Two arms per incident; the three repeats of a group share a group effect (correlated)."""
    rng = np.random.default_rng(seed)
    rows = []
    for g in range(n_groups):
        effect = rng.normal(0.15, 0.4)
        for r in range(reps):
            uid = f"g{g:02d}r{r}"
            pa = float(np.clip(0.5 + effect / 2, 0, 1))
            ca = rng.random() < pa
            cb = ca if same else rng.random() < 0.5
            for cond, c in (("x", ca), ("y", cb)):
                rows.append({"incident_uid": uid, "injection_id": uid, "group_id": f"G{g:02d}", "condition": cond,
                             "correct": c, "rank": 1 if c else 6, "score_consensus": rng.random()})
    return pd.DataFrame(rows)


SPEC = {"name": "x_vs_y", "a": {"condition": "x"}, "b": {"condition": "y"}, "metric": "ac1"}


def test_primary_analysis_is_unchanged_by_the_sensitivity_columns():
    df = frame()
    a = contrasts.evaluate(df, SPEC, n_boot=2000, n_perm=2000)
    b = contrasts.evaluate(df, SPEC, n_boot=2000, n_perm=2000, group_col="group_id")
    assert {k: a[k] for k in ("est", "lo", "hi", "p")} == {k: b[k] for k in ("est", "lo", "hi", "p")}
    assert "lo_group" not in a and b["n_groups"] == 30


def test_group_ci_equals_the_bootstrap_of_group_means():
    """Equal group sizes: resampling groups of per-injection differences is the ordinary bootstrap of the
    group means. Reference 1: the same estimator on collapsed units (exact). Reference 2: scipy's
    percentile bootstrap of group means (independent code and RNG)."""
    from rca import metrics
    df = frame(n_groups=40)
    row = contrasts.evaluate(df, SPEC, n_boot=20000, n_perm=100, group_col="group_id")
    a, b = df[df.condition == "x"].set_index("incident_uid"), df[df.condition == "y"].set_index("incident_uid")
    diff = (a["rank"] <= 1).astype(float) - (b["rank"] <= 1).astype(float)
    gm = diff.groupby(a["group_id"]).mean()
    exact = metrics.cluster_bootstrap_means(gm.to_numpy(), gm.index.to_numpy(), None, n=20000, seed=0)
    assert np.isclose(row["lo_group"], exact["lo"]) and np.isclose(row["hi_group"], exact["hi"])
    ref = stats.bootstrap((gm.to_numpy(),), np.mean, n_resamples=20000, method="percentile",
                          random_state=np.random.default_rng(1)).confidence_interval
    assert abs(row["lo_group"] - ref.low) < 0.02 and abs(row["hi_group"] - ref.high) < 0.02


def test_paired_arms_use_the_same_groups():
    df = frame(same=True)
    row = contrasts.evaluate(df, SPEC, n_boot=500, n_perm=100, group_col="group_id")
    assert row["lo_group"] == row["hi_group"] == 0.0                   # identical arms: every draw is 0
    auroc = contrasts.evaluate(df, {**SPEC, "metric": "auroc"}, n_boot=200, group_col="group_id")
    assert auroc["n_groups"] == 30 and np.isfinite(auroc["lo_group"])


def test_injection_split_across_groups_raises():
    df = frame()
    m = df.incident_uid == "g00r1"
    df.loc[m, "injection_id"], df.loc[m, "group_id"] = "g00r0", "G99"    # one injection, two groups
    with pytest.raises(ValueError, match="several group_id"):
        contrasts.evaluate(df, SPEC, n_boot=50, n_perm=50, group_col="group_id")


@pytest.mark.parametrize("lo,hi,metric,sesoi,want", [
    (-0.02, 0.03, "ac1", 0.05, "excludes_practical_effect"),
    (-0.10, 0.08, "ac1", 0.05, "insufficient_evidence"),
    (-0.20, -0.01, "ac1", 0.05, "evidence_of_harm"),
    (0.06, 0.20, "ac1", 0.05, "evidence_of_benefit"),
    (0.06, 0.20, "brier", None, "evidence_of_harm"),                 # lower is better
    (0.01, 0.02, "gap", None, "nonzero"),
    (np.nan, 0.1, "ac1", 0.05, None),
])
def test_ci_reading(lo, hi, metric, sesoi, want):
    assert contrasts.ci_reading(lo, hi, metric, sesoi) == want


def test_ci_reading_is_written_and_never_says_rejected():
    out = contrasts.run(frame(), [SPEC], n_boot=200, n_perm=200, group_col="group_id", sesoi=0.05)
    assert out["ci_reading"].iloc[0] in {"excludes_practical_effect", "insufficient_evidence", "evidence_of_harm",
                                         "evidence_of_benefit"}
    assert "ci_reading_group" in out and not out.astype(str).apply(lambda c: c.str.contains("reject")).any().any()


def test_im1_contrasts_never_enter_a_family():
    spec = {"name": "im1", "a": {"arm": "ra_im1"}, "b": {"arm": "ra"}, "metric": "ac1"}
    df = frame().assign(arm=lambda d: d["condition"].map({"x": "ra_im1", "y": "ra"}), condition="no_trace")
    with pytest.raises(ValueError, match="exploratory IM1 arm"):
        contrasts.run(df, [spec], families={"H": ["im1"]}, n_boot=50, n_perm=50)
    out = contrasts.run(df, [spec], n_boot=50, n_perm=50)
    assert bool(out["exploratory"].iloc[0])
