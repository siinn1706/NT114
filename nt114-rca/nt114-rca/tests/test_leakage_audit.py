"""Near-duplicate audit between query evidence and the retrieval store (evaluation-only)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from conftest import canonical_run_cfg
from rca import leakage_audit, run_grid

A = "## Metrics (x)\n- cart: cpu up z=9\n- front: latency up z=4\n## Logs (y)\n- front: error-log rate 0.0/min -> 5.0/min"
B = "## Metrics (x)\n- pay: mem up z=7\n## Logs (y)\n- db: log volume 3/min -> 90/min"


def _q(uid, text, system="s", group="g1", cell=("cart", "cpu")):
    return {"incident_uid": uid, "condition": "full", "system": system, "split_role": "test", "group": group,
            "cell": cell, "text": text}


def test_exact_copy_scores_one_and_group_and_system_are_excluded():
    store = [{"incident_uid": "t1", "system": "s", "group": "g2", "cell": ("cart", "cpu"), "text": A},
             {"incident_uid": "t2", "system": "s", "group": "g3", "cell": ("pay", "mem"), "text": B},
             {"incident_uid": "t3", "system": "s", "group": "g1", "cell": ("cart", "cpu"), "text": A},   # query's group
             {"incident_uid": "t4", "system": "other", "group": "g4", "cell": ("cart", "cpu"), "text": A}]
    out = leakage_audit.audit([_q("q1", A), _q("q2", B, cell=("x", "y")), _q("q3", A, system="none"),
                               _q("q4", B, cell=("pay", "cpu"))], store)
    assert out[0]["n_store"] == 2 and out[0]["max_cosine"] == pytest.approx(1.0) and out[0]["max_jaccard"] == 1.0
    assert out[0]["nearest_same_cell"] is True
    assert out[1]["nearest_same_cell"] is False and out[1]["max_jaccard"] == 1.0
    assert out[2]["n_store"] == 0 and np.isnan(out[2]["max_cosine"]) and out[2]["nearest_same_cell"] is None
    assert leakage_audit.jaccard(frozenset("ab"), frozenset("bc")) == pytest.approx(1 / 3)
    s = leakage_audit.summary(pd.DataFrame(out))
    assert s["n_records"].item() == 4 and s["n_compared"].item() == 3
    assert s["cosine_ge_0.99"].item() == 3 and s["nearest_same_cell_share"].item() == pytest.approx(1 / 3)


def test_same_root_reachability_is_separate_from_same_cell():
    """The split removes the query's (root, fault) cell; an entry with the same root and another fault stays."""
    store = [{"incident_uid": "t1", "system": "s", "group": "g2", "cell": ("pay", "mem"), "text": B},
             {"incident_uid": "t2", "system": "s", "group": "g3", "cell": ("cart", "cpu"), "text": A},
             {"incident_uid": "t3", "system": "s", "group": "g4", "cell": ("front", "cpu"), "text": A + "\n- x"}]
    same_root, other = leakage_audit.audit([_q("q1", B, cell=("pay", "cpu")), _q("q2", B, cell=("db", "cpu"))],
                                           store, top_k=2)
    assert same_root["nearest_same_cell"] is False and same_root["nearest_same_root"] is True
    assert same_root["same_root_reachable"] is True and same_root["same_root_in_top_k"] is True
    assert same_root["same_root_share"] == pytest.approx(1 / 3)
    assert same_root["same_root_in_top_k_chance"] == pytest.approx(2 / 3)       # 1 - C(2,2) / C(3,2)
    assert other["same_root_reachable"] is False and other["nearest_same_root"] is False
    assert other["same_root_share"] == 0 and other["same_root_in_top_k_chance"] == 0
    s = leakage_audit.summary(pd.DataFrame([same_root, other]))
    assert s[["same_root_reachable", "nearest_same_root", "same_root_in_top_k"]].iloc[0].tolist() == [1, 1, 1]
    assert s["nearest_same_root_chance"].item() == pytest.approx(0.33)
    assert s["same_root_in_top_k_chance"].item() == pytest.approx(0.67)


def test_outputs_hold_no_service_names(canonical_synth, tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    cfg = canonical_run_cfg(canonical_synth["dh"], tmp_path / "res", retrieval=["none", "hybrid"])
    run_grid.prepare(cfg)
    queries, store = leakage_audit.inputs(cfg)
    rows = leakage_audit.audit(queries, store)
    assert rows and all(r["n_store"] > 0 for r in rows)
    names = {q["cell"][0] for q in queries} | {e["cell"][0] for e in store}
    blob = json.dumps(rows)
    assert not [n for n in names if n and f'"{n}"' in blob]
    assert set(rows[0]) == {"incident_uid", "condition", "split_role", "n_store", "max_cosine", "max_jaccard",
                            "nearest_same_cell", "same_root_reachable", "same_root_share", "nearest_same_root",
                            "same_root_in_top_k", "same_root_in_top_k_chance"}


def test_refuses_an_output_path_inside_the_evidence_dir(tmp_path):
    cfg = {"out": str(tmp_path / "ev" / "sub" / "grid.jsonl"), "evidence_dir": str(tmp_path / "ev")}
    with pytest.raises(ValueError, match="evidence dir"):
        leakage_audit.out_dir(cfg)
