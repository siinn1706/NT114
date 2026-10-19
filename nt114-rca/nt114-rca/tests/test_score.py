"""Scoring: parse failures are wrong, set-scored labels, eval-unit weights."""
from __future__ import annotations

import json

from rca import score
from rca.data import Truth
from rca.legacy_view import truth


def test_empty_ranking_is_wrong():
    r = score.correctness([], Truth("cart", "cpu"), n_candidates=7)
    assert r == {"rank": 8, "correct_at_1": False, "correct_at_3": False, "set_scored": False, "parse_failed": True}
    ok = score.correctness(["cart", "frontend"], Truth("cart", "cpu"), 7)
    assert ok["rank"] == 1 and ok["correct_at_1"] and not ok["parse_failed"]
    miss = score.correctness(["frontend", "payment"], Truth("cart", "cpu"), 7)
    assert miss["rank"] == 8 and not miss["correct_at_3"]          # a short wrong ranking is never correct@k


def test_set_scoring():
    t = Truth(None, "net", root_ids=("cart", "redis"), granularity="multi-service")
    assert score.truth_ids(t) == ("cart", "redis")
    r = score.correctness(["redis", "frontend"], t, 5)
    assert r["correct_at_1"] and r["set_scored"]
    assert score.correctness(["frontend", "cart"], t, 5)["rank"] == 2
    assert not score.correctness(["frontend"], t, 5)["correct_at_3"]
    # a primary root wins over the set
    assert score.truth_ids(Truth("cart", "cpu", root_ids=("cart", "redis"))) == ("cart",)


def test_legacy_view_truth_fills_set_fields():
    lab = {"root_cause": {"primary_root_service": None, "root_service_ids": ["a", "b"], "label_granularity": "multi-service"},
           "fault": {"type_raw": "x"}}
    t = truth(lab)
    assert t.root_service is None and t.root_ids == ("a", "b") and t.granularity == "multi-service"


def test_units(tmp_path):
    rep = {"units": {"d.2": {"weight": 0.5, "injection_id": "i1", "representative": False, "excluded_from_primary": None,
                             "coverage": {"logs": {"cause": "covered"}, "traces": {"cause": "export_gap"}}},
                     "d.1": {"weight": 0.5, "injection_id": "i1", "representative": True, "excluded_from_primary": "short",
                             "coverage": {"logs": {"cause": "covered"}, "traces": {"cause": "covered"}}}}}
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "eval-units-d.json").write_text(json.dumps(rep), encoding="utf-8")
    u = score.units(tmp_path, "d")
    assert u["incident_uid"].tolist() == ["d.1", "d.2"] and u["weight"].sum() == 1.0
    assert u.set_index("incident_uid").loc["d.2", "cov_traces"] == "export_gap"
    d = score.default_units(["b", "a", "a"])
    assert d["incident_uid"].tolist() == ["a", "b"] and (d["weight"] == 1).all() and (d["injection_id"] == d["incident_uid"]).all()


def test_a_miss_is_beyond_the_rank_cap_for_small_candidate_sets():
    for n in (1, 2, 3, 4):
        for ranking in ([], ["frontend"]):
            r = score.correctness(ranking, Truth("cart", "cpu"), n)
            assert r["rank"] == 6 and not r["correct_at_3"], (n, ranking)


def test_miss_rank_is_unchanged_for_large_candidate_sets():
    for n in (5, 12):
        assert score.correctness(["frontend"], Truth("cart", "cpu"), n)["rank"] == n + 1
