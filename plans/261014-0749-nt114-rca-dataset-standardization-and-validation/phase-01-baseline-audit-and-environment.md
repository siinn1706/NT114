---
phase: 1
title: "Baseline audit, environment lock and regression golden set"
status: completed
priority: P1
effort: "0.5d"
dependencies: []
---

# Phase 01: Baseline audit, environment lock and regression golden set

## Goal
Freeze a reproducible Python environment, prove the raw data and existing code are intact, and
capture golden outputs so later phases can show they preserved behaviour.

## Inputs
- `RCA_ROOT` = `F:/Nam/UIT/NT114 - NCKH/nt114-rca/nt114-rca`
- [research/repo-audit.md](research/repo-audit.md) (defects D1–D12)
- `RCA_ROOT/data/manifests/checksums.sha256`, `data/.state/*.json`

## Outputs
- `RCA_ROOT/.venv/` (git-ignored), `RCA_ROOT/requirements-lock.txt`
- `RCA_ROOT/tests/golden/synthetic_evidence.sha256`
- Corrected `RCA_ROOT/docs/dataset_quality_audit.md` (D11)
- Phase report `plans/261014-0749-nt114-rca-dataset-standardization-and-validation/reports/phase-01-baseline.md`

## Files
- Modify: `RCA_ROOT/requirements.txt` — add `jsonschema>=4.21`; keep existing pins style
- Create: `RCA_ROOT/requirements-lock.txt` — `pip freeze` output from the venv
- Create: `RCA_ROOT/tests/golden/synthetic_evidence.sha256`
- Create: `RCA_ROOT/pytest.ini` — `markers = realdata: needs data/raw`, `testpaths = tests`
- Modify: `RCA_ROOT/docs/dataset_quality_audit.md` — anomalies table row and mirror section about `root_cause.txt`
- Preserve: everything under `src/`, `configs/`, `scripts/`, `data/raw/`, `data/manifests/`, `data/provenance/`

## Tasks
1. Create the venv with Python 3.12: `py -3.12 -m venv .venv`, then
   `.venv/Scripts/python -m pip install -r requirements.txt`. Do not install `RCAEval` or `vllm`
   (not needed for data work; vLLM belongs to the GPU machine).
2. `.venv/Scripts/python -m pip freeze > requirements-lock.txt`.
3. Run the existing suites and record exit codes and summaries in the phase report:
   `PYTHONPATH=src .venv/Scripts/python -m pytest -q tests/test_pipeline.py` and
   `.venv/Scripts/python -I tests/test_datasets_acquire.py`.
4. Verify raw integrity once (takes minutes; 47.8 GB):
   `bash -c "cd RCA_ROOT && sha256sum -c --quiet data/manifests/checksums.sha256"`; record the
   exit code. Also `python -I scripts/datasets/acquire.py status`.
5. Record the hashes of `src/rca/*.py`, `configs/*.yaml`, `tests/test_pipeline.py` in the report
   (baseline for "preserved" claims).
6. Golden capture: run the synthetic pipeline twice into two temp dirs
   (`make_synthetic.py`, `run_grid prepare configs/synthetic.yaml` with `evidence_dir` overridden).
   If both runs give identical evidence files, store `sha256  <case_id>.json` for the
   `conditions` and `candidates` parts (canonical JSON dump of those two keys) in
   `tests/golden/synthetic_evidence.sha256`. If they differ, record the source of
   non-determinism in the report and capture the golden set from whatever is deterministic.
7. Fix D11 in `docs/dataset_quality_audit.md`: the 8 RE3-SS `root_cause.txt` files exist in the
   Zenodo `RE3-SS.zip` (cite the zip member list) and in HF; they are label artefacts.
8. Write the phase report: environment versions, test results, integrity result, baseline hashes,
   and the D1–D12 list with the phase that fixes each.

## Tests
- T01 existing suite green before any change.

## Completion criteria
- Both existing suites pass in the venv; raw `sha256sum -c` exit 0.
- Golden file exists and two synthetic runs agree with it.
- `requirements-lock.txt` committed; `.venv/` ignored (already in `.gitignore`).
- The audit doc no longer claims the `root_cause.txt` files are HF-only.

## Risks and rollback
- If the existing suite fails before any change, stop and record it; do not "fix" it inside this
  plan without listing the fix as a separate item in the report.
- Rollback: delete `.venv/`, revert the two edited files.
