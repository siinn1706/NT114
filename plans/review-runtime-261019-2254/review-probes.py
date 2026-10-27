"""Read-only review reproductions on synthetic test fixtures. No real model calls."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "nt114-rca/nt114-rca"
SCRATCH = Path(__file__).resolve().parent
sys.path[:0] = [str(PROJECT / "src"), str(PROJECT / "tests")]

from rca import analyze, llm, run_grid, selective
from test_analyze import _grid

findings = {}

# Runbook section 7 starts the primary with the pilot arguments path; sampling
# is the next step and asks for a different arguments file.
pilot = run_grid.load_cfg(PROJECT / "configs/exp/dev-pilot.yaml")
sampling = run_grid.load_cfg(PROJECT / "configs/exp/dev-sampling.yaml")
pm, sm = pilot["models"][0], sampling["models"][0]
assert pm["launch_args"] != sm["launch_args"]
client = llm.LLM(sm["name"], revision=sm["revision"], cache=llm.Cache(SCRATCH / "probe-cache.sqlite"))
try:
    client.server_fingerprint(SCRATCH / sm["launch_args"], sm["quantization"])
except RuntimeError as exc:
    findings["sampling_launch_path"] = {
        "runbook_creates": pm["launch_args"], "sampling_requires": sm["launch_args"],
        "observed": str(exc), "network_calls": 0,
    }
else:
    raise AssertionError("missing sampling arguments unexpectedly accepted")

# Use the existing analysis test fixture, explicitly synthetic. All functions
# below read already generated grid rows; backend labels do not cause inference.
fixture = SCRATCH / "analysis-fixture"
fixture.mkdir(exist_ok=True)
frame = analyze.load(_grid(fixture, n=8, roles=("val", "test")))
dev = frame.split_role.eq("val")
frame.loc[dev, "model_revision"] = "different-dev-revision"
frame.loc[dev, "server_fp"] = "different-dev-server"
frame.loc[dev, "backend"] = "mock"
frame["exec_sig"] = ["different-dev-signature" if b else "test-signature" for b in dev]
path = fixture / "mismatched-grid.jsonl"
path.write_text("\n".join(json.dumps(r) for r in frame.to_dict("records")) + "\n", encoding="utf-8")
cfg = {
    "grids": [str(path)], "out_dir": str(fixture / "analysis"), "n_boot": 30,
    "n_perm": 30, "scores": ["consensus"], "contrasts": [],
    "selective": {"coverage": [0.7]}, "preregistration_sha": "synthetic-review-probe",
}
res = analyze.run(cfg)
fit = res["tables"]["table_selective"].query("kind == 'dev_fit'")
assert res["meta"]["headline"] and len(fit) and not fit.no_source.any()
findings["incompatible_dev_source"] = {
    "headline": res["meta"]["headline"], "target_backend": "vllm", "dev_backend": "mock",
    "different_revision_server_and_signature": True, "dev_fit_rows": len(fit),
    "source_accepted": not bool(fit.no_source.any()), "fixture": "synthetic",
}

# Baselines supplied to the same headline analysis retain their DEV rows.
bl = frame.drop(columns="model").copy()
bl["baseline"] = "review-fixture-baseline"
bl["no_row_reason"] = None
bl["reference_only"] = False
bl["ac1"] = bl.split_role.eq("val").astype(float)
bl["ac3"] = bl.ac1
bl["correct"] = bl.ac1.astype(bool)
blpath = fixture / "baselines.jsonl"
blpath.write_text("\n".join(json.dumps(r) for r in bl.to_dict("records")) + "\n", encoding="utf-8")
res_bl = analyze.run({**cfg, "baselines": [str(blpath)], "out_dir": str(fixture / "analysis-baselines")})
tab = res_bl["tables"]["table_baselines"]
assert tab["AC@1"].eq(0.5).all()
assert not bl.loc[bl.split_role.eq("test"), "ac1"].any()
findings["baseline_dev_pooling"] = {
    "headline": res_bl["meta"]["headline"], "test_ac1": 0.0, "dev_ac1": 1.0,
    "published_ac1": tab["AC@1"].tolist(), "has_split_role": "split_role" in tab,
    "fixture": "synthetic",
}

# Missing NaN-bootstrap accounting on threshold/reference risk, despite the
# protocol's explicit NaN-draw requirement. One of two clusters is answered.
thr = selective.apply_threshold([True, False], [0.9, 0.1], 0.8, ["a", "b"], n_boot=1000)
ref = selective.references([True, False], [0, 1], clusters=["a", "b"], n_boot=1000)
assert "risk_nan_draws" not in thr
findings["threshold_nan_draw_accounting"] = {
    "threshold_output": thr,
    "l1_output": next(r for r in ref if r["policy"] == "L1 self-abstain"),
    "expected_undefined_draw_probability": 0.25,
}

out = SCRATCH / "review-probes.json"
out.write_text(json.dumps(findings, indent=2) + "\n", encoding="utf-8")
print(json.dumps(findings, indent=2))
