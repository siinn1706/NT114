"""BARO-style NumPy port vs reference fixtures produced by the official RCAEval implementation.

The fixtures (`tests/fixtures/baro/`) come from an isolated CPU environment outside NT114
(`provenance.json`); NT114 never imports RCAEval. A fixture is used only when the input NT114
exports today has the digest the reference side read.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from pathlib import Path

import pandas as pd
import pytest

from conftest import REAL_DATA
from rca import baro

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "baro"
HAVE = (FIX / "reference.json").is_file() and (FIX / "provenance.json").is_file()
needs_fixtures = pytest.mark.skipif(not HAVE, reason="reference fixtures missing")


def _export():
    spec = importlib.util.spec_from_file_location("export_baro_inputs", ROOT / "scripts" / "export_baro_inputs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fixtures() -> dict:
    return {f["name"]: f for f in json.loads((FIX / "reference.json").read_text(encoding="utf-8"))} if HAVE else {}


def _inputs() -> dict:
    return {i["name"]: i for i in json.loads((FIX / "provenance.json").read_text(encoding="utf-8"))["inputs"]} if HAVE else {}


def _digest(frame: pd.DataFrame) -> str:
    buf = io.StringIO()
    frame.to_csv(buf, index=False, lineterminator="\n")
    return hashlib.sha256(buf.getvalue().encode("utf-8")).hexdigest()


def _check(frame: pd.DataFrame, inject_time: int, fx: dict):
    assert _digest(frame) == fx["input_sha256"], "input differs from the one the reference read: regenerate fixtures"
    got = baro.rank(frame, inject_time)
    cols = [c for c, _ in got["metrics"]]
    assert cols[:5] == fx["ranks"][:5]
    assert cols == fx["ranks"]
    assert got["services"] == fx["services"]
    if fx["scores"] is not None:
        ref = dict(fx["scores"])
        for c, s in got["metrics"]:
            assert s == pytest.approx(ref[c], abs=1e-6, rel=1e-12), c


def test_unvalidated_label():
    assert baro.NAME == "BARO-style (unvalidated)" and "B2" not in baro.NAME


@needs_fixtures
def test_provenance_pins_upstream_and_inputs():
    prov = json.loads((FIX / "provenance.json").read_text(encoding="utf-8"))
    assert prov["upstream"]["commit"] == baro.REFERENCE_COMMIT and prov["upstream"]["working_tree_clean"]
    assert prov["environment"]["gpu"] is None and prov["environment"]["pip_freeze"]
    assert prov["instrumentation"]["sha256"] == hashlib.sha256((FIX / "reference_runner.py.txt").read_bytes()).hexdigest()
    assert prov["reference_sha256"] == hashlib.sha256((FIX / "reference.json").read_bytes()).hexdigest()
    fx = _fixtures()
    assert all(f["instrumented_ranking_identical"] for f in fx.values())
    real = [i for i in prov["inputs"] if i["incident_uid"]]
    assert {i["subset"] for i in real} == {"RE1", "RE2", "RE3"}
    assert {i["system"] for i in real if i["subset"] == "RE1"} == {"online-boutique", "sock-shop", "train-ticket"}


@needs_fixtures
@pytest.mark.parametrize("name", [n for n in _inputs() if n.startswith("edge_")])
def test_edge_cases_match_the_reference(name):
    frame, t0 = _export().edge_frames()[name]
    _check(frame, t0, _fixtures()[name])


@pytest.mark.realdata
@needs_fixtures
@pytest.mark.skipif(not (REAL_DATA / "canonical/v1/rcaeval/_build.json").is_file(), reason="needs the real RCAEval build")
@pytest.mark.parametrize("name", [n for n, i in _inputs().items() if i["incident_uid"]])
def test_real_dev_incidents_match_the_reference(name):
    from rca.legacy_view import legacy_telemetry, visible_case
    from rca.store import CanonicalStore
    st = CanonicalStore(REAL_DATA)
    inp = _inputs()[name]
    frame = legacy_telemetry(st, inp["incident_uid"])["metrics"]
    assert visible_case(st.incident(inp["incident_uid"])).inject_time == inp["inject_time"]
    _check(frame, inp["inject_time"], _fixtures()[name])
