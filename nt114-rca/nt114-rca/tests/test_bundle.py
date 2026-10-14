"""Export bundle: integrity after a copy, tamper detection, deep fingerprints, portable layout."""
from __future__ import annotations

import shutil

from conftest import fixture_config
from rca import bundle, prep, splits
from rca.store import CanonicalStore, read_json


def _export(rcaeval_home, tmp_path):
    dh = tmp_path / "dh"
    shutil.copytree(rcaeval_home, dh)
    (dh / "manifests").mkdir()
    (dh / "manifests/dataset_catalog.json").write_text(
        '{"sources": [{"id": "rcaeval-zenodo", "license": "CC-BY-4.0"}]}', encoding="utf-8")
    cfg = fixture_config()
    assert splits.conditions_cmd("rcaeval", cfg, dh) == 0
    splits.split_cmd("eval-only-rcaeval", 0, cfg, dh)
    assert bundle.export_cmd("t", ["visible", "eval_only", "splits", "reports", "manifests"], False, cfg, dh) == 0
    (b,) = [p for p in (dh / "export").iterdir() if not p.name.startswith(".")]
    return dh, b


def test_export_copy_verify(rcaeval_home, tmp_path):
    dh, b = _export(rcaeval_home, tmp_path)
    moved = tmp_path / "elsewhere" / b.name
    shutil.copytree(b, moved)
    assert bundle.verify_bundle(moved, deep=True) == []
    meta = read_json(moved / "bundle.json")
    assert meta["datasets"]["rcaeval"]["build_id"] == CanonicalStore(dh).build("rcaeval")["build_id"]
    assert meta["licences"]["rcaeval-zenodo"] == {"license": "CC-BY-4.0", "note": None}
    assert meta["code"]["git_dirty"] in (True, False, None) and "git_commit" in meta["code"]
    assert not (moved / "parts/raw").exists() and not (moved / "parts/work").exists()
    shipped = {p.name for p in (bundle.RCA_ROOT / "configs").glob("*.yaml")}
    assert {"eval_exclusions.yaml", "prep.yaml", "service_aliases.yaml"} <= shipped == {p.name for p in (moved / "configs").iterdir()}
    assert (b / "configs/prep.yaml").stat().st_nlink == 1                  # a copy: later config edits never reach it
    for line in (moved / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
        rel = line.split("  ", 1)[1]
        assert "\\" not in rel and not rel.startswith("/") and ":" not in rel
    # the bundle's parts work as a data home
    assert prep.main(["--data-home", str(moved / "parts"), "status"]) == 0
    assert prep.main(["--data-home", str(moved / "parts"), "verify-splits"]) == 0
    assert prep.main(["verify-bundle", str(moved)]) == 0


def test_tampering_is_detected(rcaeval_home, tmp_path):
    _, b = _export(rcaeval_home, tmp_path)
    c = tmp_path / "copy"
    shutil.copytree(b, c)
    pq_file = next(c.rglob("*.parquet"))
    data = bytearray(pq_file.read_bytes())
    data[len(data) // 2] ^= 0xFF
    pq_file.write_bytes(bytes(data))
    assert any(e.startswith("MISMATCH") for e in bundle.verify_bundle(c))
    pq_file.unlink()
    assert any(e.startswith("MISSING") for e in bundle.verify_bundle(c))
    (c / "parts/stray.txt").write_text("x", encoding="utf-8")
    assert any(e.startswith("EXTRA") for e in bundle.verify_bundle(c))
    assert prep.main(["verify-bundle", str(c)]) == 4


def test_deep_check_catches_content_drift(rcaeval_home, tmp_path):
    _, b = _export(rcaeval_home, tmp_path)
    c = tmp_path / "copy"
    shutil.copytree(b, c)
    meta = read_json(c / "bundle.json")
    uid, h = next((u, h) for u, h in meta["content_sha256"]["rcaeval"].items() if h)
    meta["content_sha256"]["rcaeval"][uid]["metrics"] = "0" * 64
    import json
    import hashlib
    (c / "bundle.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    lines = [l if not l.endswith("  bundle.json") else f"{hashlib.sha256((c / 'bundle.json').read_bytes()).hexdigest()}  bundle.json"
             for l in (c / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()]
    (c / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert bundle.verify_bundle(c) == []
    assert any(e.startswith("CONTENT_SHA256") for e in bundle.verify_bundle(c, deep=True))


def test_export_is_write_once_and_rejects_unknown_parts(rcaeval_home, tmp_path, capsys):
    dh, b = _export(rcaeval_home, tmp_path)
    cfg = fixture_config()
    capsys.readouterr()
    assert bundle.export_cmd("t", ["visible", "eval_only", "splits", "reports", "manifests"], False, cfg, dh) == 0
    assert "exists" in capsys.readouterr().out
    assert bundle.export_cmd("t", ["visible", "work"], False, cfg, dh) == 2


def test_licence_per_subset_is_kept_and_marked_private(tmp_path):
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests/dataset_catalog.json").write_text(
        '{"sources": [{"id": "agenticopseval", "license": {"AIOps2025": "CC BY-NC 4.0", "RCA100": "CC BY-NC-SA 4.0"}},'
        ' {"id": "nezha", "license": "MIT"}]}', encoding="utf-8")
    got = bundle._licences(tmp_path, {"agenticopseval", "nezha", "other"})
    assert got["agenticopseval"] == {"license": {"AIOps2025": "CC BY-NC 4.0", "RCA100": "CC BY-NC-SA 4.0"},
                                     "note": "private transfer only"}
    assert got["nezha"]["note"] is None and got["other"]["note"] == "private transfer only"
