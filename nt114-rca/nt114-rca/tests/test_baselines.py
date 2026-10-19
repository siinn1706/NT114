"""Non-LLM baselines and injection reweighting."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from conftest import REAL_DATA
from rca import analyze, baselines
from rca.run_grid import load_cfg

ROOT = Path(__file__).resolve().parents[1]


def test_random_expected():
    assert baselines.random_expected(18) == pytest.approx((1 / 18, 3 / 18))
    assert baselines.random_expected(5, 2) == pytest.approx((2 / 5, 1 - 1 / 10))
    assert baselines.random_expected(2) == pytest.approx((0.5, 1.0))


def test_max_z_ranking_follows_metrics_block():
    text = ("## Metrics (robust z-score)\n- b: cpu up z=40\n- zz: mem up z=9\n- c: lat up z=5\n"
            "## Logs (5 min after)\n- a: error spike")
    rec = {"candidates": ["a", "c", "b", "d"], "conditions": {"full": {"text": text}}}
    assert baselines.max_z_ranking(rec) == ["b", "c", "a", "d"]       # unknown "zz" dropped, rest in file order
    rec["conditions"]["no_metric"] = {"text": "## Logs\n- a: x"}
    assert baselines.max_z_ranking(rec, "no_metric") == ["a", "c", "b", "d"]


@pytest.mark.parametrize("text, svc", [
    ("frontend slow | frontend::POST /api/cart", "frontend"),
    ("timeout alert | inventory", "inventory"),          # entity without an operation
    ("cart::POST /oteldemo.CartService/AddItem", "cart"),  # no title
    ("only a title", None),
    (None, None),
])
def test_alert_entity(text, svc):
    assert baselines.alert_entity({"context": {"visible_text": text}}) == svc


def test_reweight_equal_per_injection_within_cell():
    df = pd.DataFrame({"incident_uid": ["a", "b", "c", "a", "c"], "injection_id": ["i1", "i1", "i2", "i1", "i2"],
                       "dataset": "d", "condition": ["full", "full", "full", "no_log", "no_log"], "weight": 0.5})
    w = analyze.reweight(df)
    assert w["weight"].tolist() == [0.5, 0.5, 1.0, 1.0, 1.0]     # i1 lost a task in no_log: still weight 1
    assert w.groupby(["condition", "injection_id"])["weight"].sum().eq(1.0).all()


@pytest.mark.realdata
@pytest.mark.skipif(not (REAL_DATA / "canonical/v1/rca100/_build.json").is_file()
                    or not (REAL_DATA / "splits").is_dir(), reason="needs the real RCA100 build and splits")
def test_rca100_tier_a_protocol_numbers(tmp_path):
    cfg = load_cfg(ROOT / "configs" / "exp" / "baselines-rca100.yaml")
    cfg.update(data_home=str(REAL_DATA), evidence_dir=str(tmp_path / "ev"), out=str(tmp_path / "grid.jsonl"))
    tab = baselines.table(pd.DataFrame(baselines.rows(cfg)), REAL_DATA).set_index("baseline")
    assert tab.loc["B3 majority", "n_records"] == 86 and tab.loc["B3 majority", "n_injections"] == 70
    assert tab.loc["B3 majority", "AC@1"] == pytest.approx(41 / 70)
    assert tab.loc["B3 majority", "label_prior"] == "scored_set"           # eval-only split: no train prior
    assert tab.loc["B3 majority", "AC@1_per_record"] == pytest.approx(56 / 86)
    assert tab.loc["B3 alert-entity", "AC@1"] == pytest.approx(0.374, abs=5e-4)
    assert tab.loc["B3 alert-entity", "AC@1_per_record"] == pytest.approx(32 / 86)


def test_b1m_and_per_block_rankings_on_the_visibility_fixture():
    from test_visibility import CANDS, TEXT
    rec = {"candidates": CANDS, "conditions": {"full": {"text": TEXT},
                                               "no_trace": {"text": TEXT.split("## Traces")[0]}}}
    # metrics services first, then logs, then traces, then the call-edge endpoints; the rest in file order
    assert baselines.evidence_order_ranking(rec) == ["cart", "front", "pay", "db", "car"]
    assert baselines.block_ranking(rec, "full", "Metrics") == ["cart", "front", "pay", "db", "car"]
    assert baselines.block_ranking(rec, "full", "Logs") == ["front", "cart", "pay", "db", "car"]
    assert baselines.block_ranking(rec, "full", "Traces") == ["front", "pay", "cart", "db", "car"]
    assert baselines.block_ranking(rec, "no_trace", "Traces") is None
    assert baselines.mentions("- no notable change in traces\n- recorded log data covers less than 30 s") == []


def test_rows_are_grid_keyed_with_explicit_gaps_and_a_train_prior(canonical_synth, tmp_path, monkeypatch):
    from conftest import canonical_run_cfg
    from rca import run_grid
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    cfg = canonical_run_cfg(canonical_synth["dh"], tmp_path, retrieval=["none"],
                            conditions=["full", "no_trace", "no_metric", "blind_root"])
    run_grid.prepare(cfg)
    df = pd.DataFrame(baselines.rows(cfg))
    scored = df[df["rank"].notna()]
    assert {"incident_uid", "condition", "retrieval", "rank", "correct", "split_role"} <= set(df)
    assert (scored["correct"] == (scored["rank"] == 1)).all()
    names = set(df["baseline"])
    assert {"B1 max-z", "B1 logs", "B1 traces", baselines.B1M, "B3 majority"} <= names
    gaps = df[df["no_row_reason"].notna()]
    assert set(gaps.loc[gaps.condition == "no_trace", "baseline"]) >= {"B1 traces"}
    assert set(gaps.loc[gaps.condition == "no_metric", "baseline"]) >= {"B1 max-z"}
    for (u, c), g in df[df.baseline.str.startswith("B1")].groupby(["incident_uid", "condition"]):
        assert len(g) == 4                                     # every B1 variant: a scored row or a reason
    maj = df[df.baseline == "B3 majority"]
    assert (maj["label_prior"] == "train").all() and not maj["reference_only"].any()
    tab = baselines.table(df)
    assert not tab["AC@1"].isna().any()
    from rca import analyze
    joint = analyze.joint_baselines(df)
    assert len(joint) and joint["rank"].notna().all() and "B0 random" not in set(joint["model"])


def test_scored_set_prior_is_reference_only_and_kept_out_of_contrasts():
    df = pd.DataFrame([{"incident_uid": "u1", "dataset": "rca100", "baseline": "B3 majority", "condition": "full",
                        "rank": 1.0, "correct": True, "ac1": 1.0, "ac3": 1.0, "label_prior": "scored_set",
                        "reference_only": True, "no_row_reason": None, "split_role": "test"}])
    assert not len(analyze.joint_baselines(df))
    assert baselines.table(df).loc[0, "label_prior"] == "scored_set"


def test_baro_rows_and_overlap_with_b1(canonical_synth, tmp_path, monkeypatch):
    from conftest import canonical_run_cfg
    from rca import baro, run_grid
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    cfg = canonical_run_cfg(canonical_synth["dh"], tmp_path, retrieval=["none"],
                            conditions=["full", "no_metric", "no_log"])
    run_grid.prepare(cfg)
    df = pd.DataFrame(baselines.rows(cfg, with_baro=True))
    b = df[df.baseline == baro.NAME]
    assert len(b) and set(b.loc[b.condition == "no_metric", "no_row_reason"]) == {"no metrics"}
    sc = b[b.no_row_reason.isna()]
    assert len(sc) and sc["rank"].notna().all()
    # the metrics are the same in every condition that keeps them: one ranking
    assert sc.groupby("incident_uid")["top5"].apply(lambda x: len({tuple(v) for v in x})).eq(1).all()
    ov = baselines.baro_overlap(df)
    assert set(ov["condition"]) == {"full", "no_log"}
    assert ov["top1_agreement"].between(0, 1).all() and ov["top5_jaccard"].between(0, 1).all()
    assert {"dAC1_est", "dAC1_lo", "dAC1_hi", "dAC1_p", "kendall_tau_shared_top5"} <= set(ov)


def test_kendall_on_the_shared_top5():
    assert baselines._kendall_shared(["a", "b", "c"], ["a", "b", "c"]) == pytest.approx(1.0)
    assert baselines._kendall_shared(["a", "b", "c"], ["c", "b", "a"]) == pytest.approx(-1.0)
    assert np.isnan(baselines._kendall_shared(["a", "b"], ["a", "z"]))
