"""Build driver: resume, idempotency, worker-count independence, portability, exception capture."""
from __future__ import annotations

import shutil

from conftest import build_fixture_home, fixture_config
from fixtures.adapters import RaisingAdapter
from rca import prep
from rca.store import read_json, read_jsonl

DS = "canonical/v1/rcaeval"


def _outputs(dh):
    ds = dh / DS
    files = sorted(p for p in ds.rglob("*") if p.is_file() and p.name != "_build.json")
    return {p.relative_to(ds).as_posix(): p.read_bytes() for p in files}


def _mtimes(dh):
    return {p: p.stat().st_mtime_ns for p in (dh / DS).rglob("*.parquet")}


def test_rebuild_is_noop_and_force_is_identical(tmp_path):
    dh = tmp_path / "dh"
    r1 = build_fixture_home(dh)
    out1, mt1 = _outputs(dh), _mtimes(dh)
    logs = []
    r2 = prep.build_dataset("rcaeval", fixture_config(), dh, max_workers=1, log=logs.append)
    assert "0 to build" in logs[0] and "8 up to date" in logs[0]
    assert _mtimes(dh) == mt1
    assert _outputs(dh) == out1
    r3 = prep.build_dataset("rcaeval", fixture_config(), dh, max_workers=1, force=True, log=lambda *a: None)
    assert _outputs(dh) == out1
    assert r1["build_id"] == r2["build_id"] == r3["build_id"]
    assert r1["dataset_digest"] == r3["dataset_digest"]


def test_resume_rebuilds_only_unfinished(tmp_path):
    dh = tmp_path / "dh"
    build_fixture_home(dh)
    out1 = _outputs(dh)
    recs = sorted((dh / "work/runs/rcaeval/records").glob("*.done"))
    for d in recs[:2]:       # as if the process was killed before these markers were written
        d.unlink()
    logs = []
    prep.build_dataset("rcaeval", fixture_config(), dh, max_workers=1, log=logs.append)
    assert "2 to build" in logs[0]
    assert _outputs(dh) == out1


def test_config_change_invalidates_markers(tmp_path):
    dh = tmp_path / "dh"
    build_fixture_home(dh)
    cfg = fixture_config()
    cfg["windows"]["evidence"]["pre_s"] = 601
    cfg["_hash"] = prep.config_hash(cfg)
    logs = []
    prep.build_dataset("rcaeval", cfg, dh, max_workers=1, log=logs.append)
    assert "8 to build" in logs[0]


def test_two_workers_match_one_and_data_home_is_portable(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    build_fixture_home(a, max_workers=1)
    build_fixture_home(b, max_workers=2)
    assert _outputs(a) == _outputs(b)
    ra, rb = read_json(a / DS / "_build.json"), read_json(b / DS / "_build.json")
    assert ra["build_id"] == rb["build_id"] and ra["dataset_digest"] == rb["dataset_digest"]
    # moved data home: same canonical bytes, paths stay relative
    c = tmp_path / "moved"
    shutil.move(str(a), str(c))
    for r in read_jsonl(c / DS / "visible/incidents.jsonl"):
        for m in ("metrics", "logs", "traces"):
            p = r["telemetry"][m]["path"]
            assert p is None or (c / p).is_file()


def test_config_hash_ignores_data_home():
    cfg = fixture_config()
    h = prep.config_hash(cfg)
    cfg.setdefault("paths", {})["data_home"] = "/somewhere/else"
    assert prep.config_hash(cfg) == h


def test_adapter_exception_is_recorded_not_dropped(tmp_path):
    dh = tmp_path / "dh"
    from fixtures.build_fixtures import rcaeval_zips
    rcaeval_zips(dh / "raw")
    r = prep.build_dataset("rcaeval", fixture_config(), dh, max_workers=2, adapter_cls=RaisingAdapter, log=lambda *a: None)
    assert r["exceptions"] == 1
    assert r["counts"]["records"] == 7 and r["counts"]["states"].get("QUARANTINE") == 1
    exc = read_jsonl(dh / DS / "eval_only/exceptions.jsonl")
    assert len(exc) == 1 and exc[0]["state"] == "QUARANTINE"
    assert "boom in logs" in exc[0]["exception"]
    assert exc[0]["incident_uid"] not in {x["incident_uid"] for x in read_jsonl(dh / DS / "visible/incidents.jsonl")}


def test_cli_status_and_validate(tmp_path, capsys, monkeypatch):
    dh = tmp_path / "dh"
    build_fixture_home(dh)
    assert prep.main(["--data-home", str(dh), "status"]) == prep.EXIT_OK
    assert "rcaeval" in capsys.readouterr().out
    assert prep.main(["--data-home", str(dh), "validate", "--dataset", "rcaeval"]) == prep.EXIT_OK
    rep = read_json(dh / "reports/quality-rcaeval.json")
    assert rep["invariant_error_count"] == 0 and rep["states"]["REJECT"] == 1
    assert prep.main(["--data-home", str(tmp_path / "empty"), "validate", "--dataset", "rcaeval"]) == prep.EXIT_PRECONDITION
