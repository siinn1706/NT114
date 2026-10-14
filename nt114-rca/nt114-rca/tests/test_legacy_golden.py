"""Legacy run_grid path: the visible part of the synthetic evidence equals the baseline captured before any change."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from rca import run_grid

RCA_ROOT = Path(__file__).resolve().parents[1]


def test_legacy_synthetic_matches_golden(tmp_path):
    """Legacy path: visible part of the evidence equals the baseline captured before any change."""
    subprocess.run([sys.executable, str(RCA_ROOT / "scripts/make_synthetic.py"), str(tmp_path / "data_synth")],
                   check=True, capture_output=True)
    cfg = run_grid.load_cfg(RCA_ROOT / "configs/synthetic.yaml")
    cfg["data_root"], cfg["evidence_dir"] = str(tmp_path / "data_synth"), str(tmp_path / "evidence")
    run_grid.prepare(cfg)
    got = {}
    for f in sorted((tmp_path / "evidence").glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        blob = json.dumps({"candidates": r["candidates"], "conditions": r["conditions"]}, sort_keys=True,
                          ensure_ascii=False, separators=(",", ":"))
        got[f.name] = hashlib.sha256(blob.encode()).hexdigest()
    want = {}
    for line in (RCA_ROOT / "tests/golden/synthetic_evidence.sha256").read_text(encoding="utf-8").splitlines():
        h, name = line.split("  ")
        want[name] = h
    assert got == want
