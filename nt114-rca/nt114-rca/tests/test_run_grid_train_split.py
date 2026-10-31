"""run_grid on the train role of a split: retrieval store, evidence directory and build binding."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from conftest import canonical_run_cfg
from rca import run_grid, splits
from rca.store import CanonicalStore


def _rows(cfg):
    return [json.loads(line) for line in open(cfg["out"], encoding="utf-8")]


def test_train_role_queries_retrieve_from_the_train_store_without_their_own_group(canonical_synth, tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    cfg = canonical_run_cfg(canonical_synth["dh"], tmp_path, split_role="train", conditions=["full"],
                            retrieval=["none", "bm25"])
    run_grid.prepare(cfg)
    run_grid.run(cfg)
    cn = run_grid.Canon(cfg)
    rows = _rows(cfg)
    assert rows and {r["split_role"] for r in rows} == {"train"}
    man = json.loads((Path(cfg["out"]).parent / "manifest.json").read_text(encoding="utf-8"))
    assert man["split_roles"] == ["train"] and "excluded_queries" not in man   # every synthetic label names a service
    retrieved = [r for r in rows if r["retrieval"] == "bm25"]
    assert retrieved and any(r["hits"] for r in retrieved)
    for r in retrieved:
        for h in r["hits"]:
            assert cn.roles[h["case_id"]] == "train"
            assert h["case_id"] != r["case_id"] and cn.group[h["case_id"]] != cn.group[r["case_id"]]


def test_test_role_store_still_refuses_a_scored_incident(canonical_synth, tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    cfg = canonical_run_cfg(canonical_synth["dh"], tmp_path, conditions=["full"], retrieval=["none", "bm25"])
    run_grid.prepare(cfg)
    train = run_grid.Canon(cfg).store_incidents()[0]["incident_uid"]
    # A train incident scored under the test role would be its own precedent.
    monkeypatch.setattr(run_grid.Canon, "selected", lambda self: [(SimpleNamespace(case_id=train), None)])
    with pytest.raises(RuntimeError, match="outside the scored set"):
        run_grid._store_entries(cfg, run_grid.Canon(cfg))


def test_stray_evidence_files_are_skipped_but_selected_files_are_checked(canonical_synth, tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    cfg = canonical_run_cfg(canonical_synth["dh"], tmp_path, conditions=["full"], retrieval=["none"])
    run_grid.prepare(cfg)
    ev = Path(cfg["evidence_dir"])
    files = sorted(ev.glob("*.json"))
    cn = run_grid.Canon(cfg)
    stray = json.loads(files[0].read_text(encoding="utf-8"))
    stray.update(incident_uid=cn.store_incidents()[0]["incident_uid"], evidence_fp="from-another-split")
    (ev / "zz-stray.json").write_text(json.dumps(stray), encoding="utf-8")
    assert sorted(r["incident_uid"] for r in run_grid.load_evidence(cfg)) == sorted(f.stem for f in files)
    stale = json.loads(files[0].read_text(encoding="utf-8"))
    stale["evidence_fp"] = "stale"
    files[0].write_text(json.dumps(stale), encoding="utf-8")
    with pytest.raises(RuntimeError, match="stale evidence"):
        run_grid.load_evidence(cfg)


def test_split_or_matrix_of_another_build_stops_the_run(canonical_synth, tmp_path, monkeypatch):
    cfg = canonical_run_cfg(canonical_synth["dh"], tmp_path, conditions=["full"], retrieval=["none"])
    run_grid.Canon(cfg)  # the current build, split and matrix agree
    build = CanonicalStore.build
    with monkeypatch.context() as m:
        m.setattr(CanonicalStore, "build", lambda self, ds: {**build(self, ds), "dataset_digest": "rebuilt"})
        with pytest.raises(RuntimeError, match="verify-splits"):
            run_grid.Canon(cfg)
    matrix = splits.load_condition_matrix
    with monkeypatch.context() as m:
        m.setattr(splits, "load_condition_matrix", lambda *a, **k: {**matrix(*a, **k), "build_id": "older-build"})
        with pytest.raises(RuntimeError, match="conditions"):
            run_grid.Canon(cfg)


def test_node_level_labels_are_left_out_of_train_queries_and_counted(canonical_synth, tmp_path, monkeypatch):
    cfg = canonical_run_cfg(canonical_synth["dh"], tmp_path, split_role="train", conditions=["full"], retrieval=["none"])
    cn = run_grid.Canon(cfg)
    train = [vc.case_id for vc, _ in cn.selected()]
    node_level = train[0]
    labels = cn.labels()
    rc = {**labels[node_level]["root_cause"], "primary_root_service": None, "root_service_ids": [],
          "label_granularity": "node"}
    monkeypatch.setitem(labels, node_level, {**labels[node_level], "root_cause": rc})
    assert [vc.case_id for vc, _ in cn.selected()] == train[1:]
    assert cn.excluded_queries == {"no_service_label": 1}
    test_cfg = canonical_run_cfg(canonical_synth["dh"], tmp_path / "test", conditions=["full"], retrieval=["none"])
    test_cn = run_grid.Canon(test_cfg)
    before = [vc.case_id for vc, _ in test_cn.selected()]
    test_cn._labels = labels
    assert [vc.case_id for vc, _ in test_cn.selected()] == before and test_cn.excluded_queries == {}
