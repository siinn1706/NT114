"""The canonical view reproduces what the legacy loader feeds the evidence builder.

Fixture cases are read twice: directly by `data.load_case` and from the canonical build through
`legacy_view`. Evidence text and features must match exactly for every ablation condition.
`realdata` repeats the check on 10 real RCAEval cases when the raw data is present.
"""
from __future__ import annotations

import random

import numpy as np
import pandas as pd
import pytest

from conftest import REAL_DATA, real_data_available
from rca import ablate, evidence, legacy_view
from rca.data import canon, discover_cases, load_case
from rca.store import CanonicalStore, read_jsonl

DS = "canonical/v1/rcaeval"


def _key(case, root) -> str:
    rel = case.path.relative_to(root).as_posix().split("/")
    return "/".join(rel[-3:])


def _pairs(home, root, datasets=("re1", "re2", "re3")):
    src = {r["source_incident_key"]: r["incident_uid"] for r in read_jsonl(home / DS / "eval_only/source_index.jsonl")}
    return [(c, src[_key(c, root)]) for c in discover_cases(root, datasets)]


def _assert_same_tel(old: dict, new: dict):
    assert (old["metrics"] is None) == (new["metrics"] is None)
    if old["metrics"] is not None:
        a, b = old["metrics"], new["metrics"]
        assert list(a.columns) == list(b.columns)
        assert (a["time"].to_numpy() == b["time"].to_numpy()).all()
        np.testing.assert_allclose(a.drop(columns="time").to_numpy(float), b.drop(columns="time").to_numpy(float),
                                   rtol=1e-9, equal_nan=True)   # pandas fast float parser: ~1e-12 rel. error
    for m, cols in (("logs", ["timestamp", "container_name", "message", "svc"]),
                    ("traces", ["traceID", "spanID", "serviceName", "startTime", "duration", "svc"])):
        assert (old[m] is None) == (new[m] is None), m
        if old[m] is not None:
            a, b = old[m][cols].reset_index(drop=True), new[m][cols].reset_index(drop=True)
            for c in cols:
                assert a[c].astype(str).tolist() == b[c].astype(str).tolist(), (m, c)


def _assert_same_evidence(case, uid, old_tel, new_tel, store):
    inc = store.incident(uid)
    vis = legacy_view.visible_case(inc)
    lab = legacy_view.truth(store.labels("rcaeval")[uid])
    assert lab.root_service == case.root_service
    # canonical candidates = legacy candidates minus infrastructure entities (node exporters, `main`, ...)
    infra = {e["service_id"] for ent in store.service_map("rcaeval").values() for e in ent.values() if e["kind"] == "infra"}
    assert set(vis.services) <= set(case.services)
    assert set(case.services) - set(vis.services) <= infra, set(case.services) - set(vis.services)
    for cond in ablate.CONDITIONS:
        if not ablate.applicable(cond, old_tel):
            assert not ablate.applicable(cond, new_tel)
            continue
        e_old = evidence.build(case, ablate.apply(old_tel, cond, case.root_service))
        e_new = evidence.build(vis, ablate.apply(new_tel, cond, lab.root_service))
        assert e_old["text"] == e_new["text"], (case.case_id, cond)
        # pandas' default CSV float parser is not correctly rounded, Arrow's is: last-ulp differences
        assert e_old["features"] == pytest.approx(e_new["features"], rel=1e-9), (case.case_id, cond)


def test_fixture_cases_match_legacy_loader(rcaeval_home, rcaeval_dir_tree):
    store = CanonicalStore(rcaeval_home)
    pairs = _pairs(rcaeval_home, rcaeval_dir_tree)
    assert len(pairs) == 7         # the multi-source-data copy is invisible to the legacy loader
    for case, uid in pairs:
        old = load_case(case)
        new = legacy_view.legacy_telemetry(store, uid)
        _assert_same_tel(old, new)
        _assert_same_evidence(case, uid, old, new, store)


def test_visible_case_carries_no_label(rcaeval_home):
    store = CanonicalStore(rcaeval_home)
    for inc in store.incidents("rcaeval", states=None):
        v = legacy_view.visible_case(inc)
        assert not hasattr(v, "root_service") and not hasattr(v, "fault")
        assert v.case_id == inc["incident_uid"]


def test_service_canon_agrees_with_legacy(rcaeval_home):
    smap = CanonicalStore(rcaeval_home).service_map("rcaeval")
    for system, entries in smap.items():
        for raw, e in entries.items():
            if e["kind"] == "service":
                assert e["service_id"] == canon(raw), (system, raw)


@pytest.mark.realdata
@pytest.mark.skipif(not real_data_available(), reason="raw RCAEval not present")
def test_real_cases_match_legacy_loader(tmp_path_factory):
    """Ten real cases (one per subset and system, plus a second-batch RE3-TT cell) through both loaders."""
    from conftest import fixture_config
    from rca import prep
    zips = sorted((REAL_DATA / "raw/rcaeval-zenodo").rglob("RE*-*.zip"))
    rng = random.Random(7)
    dh = tmp_path_factory.mktemp("realdh")
    tree = tmp_path_factory.mktemp("realtree")
    picked = []
    import zipfile
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            cases = sorted({n.rsplit("/", 1)[0] for n in zf.namelist() if n.endswith("/inject_time.txt")})
            cases = [c for c in cases if c.rsplit("/", 1)[1].isdigit()]
            pick = rng.sample(cases, 1)
            if z.stem == "RE3-TT":     # also the second-batch cell whose label the old parser shifted
                pick += [c for c in cases if "/ts-route-service_f3_1/" in c + "/"][:1]
            for c in pick:
                for n in zf.namelist():
                    if n.startswith(c + "/") and not n.endswith("/"):
                        dst = tree / n
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        dst.write_bytes(zf.read(n))
                picked.append(c)
    assert len(picked) == 10
    cfg = fixture_config(str(tree))
    prep.build_dataset("rcaeval", cfg, dh, max_workers=2, log=lambda *a: None)
    store = CanonicalStore(dh)
    src = {r["source_incident_key"]: r["incident_uid"] for r in read_jsonl(dh / DS / "eval_only/source_index.jsonl")}
    for case in discover_cases(tree, ("re1", "re2", "re3")):
        uid = src[_key(case, tree)]
        old = load_case(case)
        new = legacy_view.legacy_telemetry(store, uid)
        _assert_same_tel(old, new)
        _assert_same_evidence(case, uid, old, new, store)
