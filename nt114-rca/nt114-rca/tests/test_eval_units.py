"""Evaluation units: injection grouping, weights, representative, primary exclusions, coverage strata."""
from __future__ import annotations

import pytest

from fixtures.agenticops_fixtures import RCA100_CASES
from rca import prep
from rca.eval_units import eval_units, load_exclusions
from test_adapter_rca100 import _build


@pytest.fixture(scope="module")
def shared(tmp_path_factory):
    cases = {**RCA100_CASES, "t005": ("F014-httpError5xx.eee", ["payment"], *RCA100_CASES["t001"][2:])}
    return _build(tmp_path_factory.mktemp("units"), cases)


def test_injections_weights_and_representative(shared):
    h = shared
    pair = sorted([h["by_case"]["F014-httpError5xx.aaa"], h["by_case"]["F014-httpError5xx.eee"]])
    rep = eval_units(h["store"], "rca100", prep.load_config(), exclusions={})
    u = rep["units"]
    assert rep["counts"]["accepted_records"] == 5 and rep["counts"]["independent_injections"] == 4
    assert u[pair[0]]["injection_id"] == u[pair[1]]["injection_id"] == "rca100-injection:t001"
    assert u[pair[0]]["weight"] == u[pair[1]]["weight"] == 0.5
    assert [u[p]["representative"] for p in pair] == [True, False]
    others = set(u) - set(pair)
    assert all(u[x]["weight"] == 1.0 and u[x]["representative"] and u[x]["injection_id"] == x for x in others)
    assert sum(r["weight"] for r in u.values()) == pytest.approx(4)


def test_coverage_strata_separate_truncated_exports_from_covered(shared):
    h = shared
    u = eval_units(h["store"], "rca100", prep.load_config(), exclusions={})["units"]
    cov = lambda task, m: u[h["by_case"][RCA100_CASES[task][0]]]["coverage"][m]
    assert cov("t001", "logs")["cause"] == "covered" and cov("t001", "logs")["after_s"] >= 30
    assert cov("t003", "logs")["cause"] == "export_truncated"        # export stops 100 s before the anchor
    assert cov("t003", "traces")["cause"] == "export_truncated"


def test_primary_exclusions_are_recorded_not_dropped(shared, tmp_path):
    h = shared
    uid = h["by_case"]["F001-nodeDown.ccc"]
    p = tmp_path / "excl.yaml"
    p.write_text(f"exclusions:\n  - {{dataset: rca100, incident_uid: {uid}, reason: test reason, status: temporary, decided: test}}\n",
                 encoding="utf-8")
    rep = eval_units(h["store"], "rca100", prep.load_config(), exclusions=load_exclusions(p))
    assert rep["units"][uid]["excluded_from_primary"] == "test reason [temporary, test]"
    assert rep["counts"]["accepted_records"] == 5 and rep["counts"]["primary_records"] == 4
    with pytest.raises(ValueError):
        eval_units(h["store"], "rca100", prep.load_config(), exclusions={"rca100": {"rca100.0000000000000000": "x"}})


def test_lifted_exclusions_stay_recorded_but_exclude_nothing(tmp_path):
    p = tmp_path / "excl.yaml"
    p.write_text("exclusions:\n"
                 "  - {dataset: rca100, incident_uid: a, reason: r1, status: lifted, decided: d, lifted: checks pass}\n"
                 "  - {dataset: rca100, incident_uid: b, reason: r2, status: temporary, decided: d}\n", encoding="utf-8")
    assert load_exclusions(p) == {"rca100": {"b": "r2 [temporary, d]"}}


def test_shipped_exclusions_are_all_lifted_with_a_reason():
    import yaml
    from rca.eval_units import EXCLUSIONS
    rows = yaml.safe_load(EXCLUSIONS.read_text(encoding="utf-8"))["exclusions"]
    assert len(rows) == 4 and all(r["status"] == "lifted" and r["lifted"] for r in rows)
    assert load_exclusions() == {}
