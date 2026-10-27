"""Reproduce top_k resume drift using the test suite's synthetic canonical home."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "nt114-rca/nt114-rca"
SCRATCH = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT / "src"))
from rca import run_grid

test_root = SCRATCH / "pytest-focused-verified"
cfg = run_grid.load_cfg(PROJECT / "configs/canonical_synthetic.yaml")
cfg.update(
    data_home=str(test_root / "canon0/data_synth_home"),
    evidence_dir=str(test_root / "repro0/evidence"),
    out=str(SCRATCH / "resume-probe/grid.jsonl"),
    cache=str(SCRATCH / "resume-probe/cache.sqlite"),
    conditions=["full"], retrieval=["hybrid"], store_modes=["precedent"],
    limit_per_system=1, top_k=3, models=[{"name": "mock-small", "backend": "mock"}],
)
cfg["_hash"] = hashlib.sha256(json.dumps({k: v for k, v in cfg.items() if k != "_hash"}, sort_keys=True).encode()).hexdigest()[:10]
log = io.StringIO()
with contextlib.redirect_stdout(log):
    run_grid.run(cfg)
before = Path(cfg["out"]).read_bytes()
first = [json.loads(x) for x in before.decode().splitlines()]
assert first and all(len(r["hits"]) == 3 for r in first)
cfg["top_k"] = 1
cfg["_hash"] = hashlib.sha256(json.dumps({k: v for k, v in cfg.items() if k != "_hash"}, sort_keys=True).encode()).hexdigest()[:10]
with contextlib.redirect_stdout(log):
    run_grid.run(cfg)
after = Path(cfg["out"]).read_bytes()
import yaml
saved = yaml.safe_load((Path(cfg["out"]).parent / "config.yaml").read_text(encoding="utf-8"))
assert before == after and saved["top_k"] == 1
report = {
    "fixture": "synthetic", "rows": len(first), "first_run_top_k": 3,
    "second_run_top_k": 1, "grid_byte_identical": before == after,
    "actual_hit_counts": [len(r["hits"]) for r in first], "recorded_config_top_k": saved["top_k"],
    "requested_conditions": cfg["conditions"], "observed_conditions": sorted({r["condition"] for r in first}),
}
(SCRATCH / "resume-probe.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
(SCRATCH / "resume-probe.log").write_text(log.getvalue(), encoding="utf-8")
print(json.dumps(report, indent=2))
