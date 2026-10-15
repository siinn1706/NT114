"""Non-LLM baselines and injection reweighting."""
from __future__ import annotations

from pathlib import Path

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
    assert tab.loc["B3 majority", "AC@1_per_record"] == pytest.approx(56 / 86)
    assert tab.loc["B3 alert-entity", "AC@1"] == pytest.approx(0.374, abs=5e-4)
    assert tab.loc["B3 alert-entity", "AC@1_per_record"] == pytest.approx(32 / 86)
