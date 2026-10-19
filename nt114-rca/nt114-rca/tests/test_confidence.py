"""Confidence registry: known values, token alignment on fixtures, missing raw outputs, isolation."""
from __future__ import annotations

import ast
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from rca import confidence

RCA_ROOT = Path(__file__).resolve().parents[1]


def _s(*rankings, ok=True):
    return [{"ok": ok and bool(r), "ranking": list(r)} for r in rankings]


def test_registry_declares_every_score():
    assert set(confidence.REGISTRY) == {"consensus", "verbal", "verbal_agreement", "not_insufficient",
                                        "borda_margin", "vote_entropy", "token_prob"}
    assert not confidence.REGISTRY["token_prob"].validated
    assert all(s.validated for n, s in confidence.REGISTRY.items() if n != "token_prob")
    assert {n for n, s in confidence.REGISTRY.items() if s.probability} == {"consensus", "verbal"}


def test_borda_margin_and_vote_entropy_known_values():
    s = _s(["a", "b"], ["a", "c"], ["b", "a"], [])
    s[3]["ok"] = False
    # Borda: a = 5+5+4 = 14, b = 4+5 = 9, c = 4 -> (14 - 9) / (5 x 4 samples)
    assert confidence.borda_margin(s) == pytest.approx(5 / 20)
    p = np.array([2, 1]) / 3
    assert confidence.vote_entropy(s) == pytest.approx(1 - (-(p * np.log(p)).sum()) / math.log(3))
    assert confidence.vote_entropy(_s(["a"], ["a"])) == pytest.approx(1.0)
    assert confidence.vote_entropy(_s([], ok=False)) == 0.0


def test_token_prob_aligns_tokens_of_the_first_ranking_entry():
    text = '{"reason": "x", "ranking": ["cart", "redis"], "confidence": 80}'
    pieces = ['{"reason": "x", "ranking": ["', "ca", "rt", '", "redis"], "confidence": 80}']
    lps = [{"token": t, "logprob": v} for t, v in zip(pieces, [-0.1, -0.5, -0.3, -0.2])]
    assert confidence.first_entry_logprob(text, lps) == pytest.approx(-0.4)          # "ca" and "rt" only
    assert math.isnan(confidence.first_entry_logprob(text, lps[:-1]))                 # concatenation differs
    assert math.isnan(confidence.first_entry_logprob('{"ranking": []}', [{"token": '{"ranking": []}', "logprob": -1}]))
    raw = {"texts": [text, text], "logprobs": [lps, None]}
    assert confidence.token_prob(raw) == pytest.approx(-0.4)
    assert math.isnan(confidence.token_prob({"texts": [text], "logprobs": None}))


def test_scores_count_rows_without_raw_outputs(tmp_path):
    grid = pd.DataFrame({"key": ["k1", "k2"], "conf_consensus": [0.8, 0.2], "conf_verbal": [0.7, 0.4],
                         "conf_verbal_sd": [0.1, 0.3], "abstain_vote": [0.0, 0.5]})
    p = tmp_path / "llm_raw.jsonl"
    p.write_text(json.dumps({"key": "k1", "samples": _s(["a"], ["a"]), "texts": [], "logprobs": None}) + "\n{torn",
                 encoding="utf-8")
    raw = confidence.load_raw(p)
    sc, counts = confidence.scores(grid, raw)
    assert counts == {"rows": 2, "missing_raw": 1, "token_prob_available": 0}
    assert sc["score_vote_entropy"].iloc[0] == 1.0 and np.isnan(sc["score_vote_entropy"].iloc[1])
    assert sc["score_verbal_agreement"].tolist() == [-0.1, -0.3]
    assert sc["score_not_insufficient"].tolist() == [1.0, 0.5]


def test_model_facing_modules_never_import_the_evaluation_zone():
    zone = {"analyze", "confidence", "contrasts", "selective", "alignment", "leakage_audit", "baselines", "baro",
            "visibility"}
    for mod in ("llm", "evidence", "retrieve", "run_grid"):
        tree = ast.parse((RCA_ROOT / "src" / "rca" / f"{mod}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                names = {(node.module or "").split(".")[-1]} | {a.name for a in node.names}
            elif isinstance(node, ast.Import):
                names = {a.name.split(".")[-1] for a in node.names}
            else:
                continue
            assert not names & zone, f"{mod}.py:{node.lineno} imports {sorted(names & zone)}"
