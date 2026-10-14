---
phase: 12
title: "Export bundle, portability verification, docs and handoff"
status: in-progress
priority: P1
effort: "1.5d"
dependencies: [11]
---

# Phase 12: Export bundle, portability verification, docs and handoff

## Goal
Package the validated canonical data, splits and reports into a verifiable bundle, prove it
works unchanged on Linux, and document the data contract for the LLM + Jev plan.

## Inputs
- Everything produced by phases 05–11
- [design/cli-and-portability.md](design/cli-and-portability.md) §6–7, [design/handoff-llm-jev.md](design/handoff-llm-jev.md)

## Outputs
- `RCA_ROOT/data/export/<bundle_id>/` (not in git)
- `RCA_ROOT/docs/data_contract.md`; updated `docs/dataset_quality_audit.md`, `README.md`
- Portability report in this plan's `reports/phase-12-portability.md`

## Files
- Create: `RCA_ROOT/src/rca/bundle.py` — export (copy or hard-link; never modify sources),
  `MANIFEST.sha256`, `bundle.json`, `verify_bundle`
- Modify: `RCA_ROOT/src/rca/prep.py` — wire `export`, `verify-bundle`
- Create: `RCA_ROOT/scripts/verify_portability.sh` — Linux script: verify bundle, `status`,
  fast test suite, canonical synthetic run with mock backend, recompute `content_sha256` of all
  tables and `blind_nonroot` targets and diff with `bundle.json`
- Create: `RCA_ROOT/tests/test_bundle.py`
- Create: `RCA_ROOT/docs/data_contract.md` — schema summary, zones, layout, CLI, quality states,
  split protocols, leakage rules, Jev decision-state allowlist, versioning; links to the JSON
  Schema rather than copying it
- Modify: `RCA_ROOT/docs/dataset_quality_audit.md` — canonical counts per dataset and tier, gate
  outcomes, link to `data/reports/audit-<build>.json`
- Modify: `RCA_ROOT/README.md` — data pipeline section (Vietnamese, matching the file's language)

## Tasks
1. Tests first: T20.
2. Implement `bundle.py`; `bundle.json` records datasets, build ids, schema/adapter versions,
   split ids, licences (from provenance) with a "private transfer only" note for NC/controlled
   sources, RCA_ROOT git commit, and the lock-file sha256.
3. Export: `python -m rca.prep export --bundle nt114-data-v1` (default parts: visible,
   eval_only, splits, reports, manifests, provenance; raw excluded).
4. Linux verification: copy the bundle to WSL2 (`/home/<user>/nt114-bundle`) or directly to the
   GPU machine; create a venv from `requirements-lock.txt` with the **same pyarrow, pandas and
   numpy versions** (other platform-specific wheels may differ; record the diff); run `scripts/verify_portability.sh`. If WSL2 is not available, run it on the GPU
   machine as the first step there and record the result.
5. Write `docs/data_contract.md` and update the other docs; verify every link and every count
   against the reports.
6. Fill the handoff checklist in [design/handoff-llm-jev.md](design/handoff-llm-jev.md) §5 with
   results.

## Tests
- T20, T21; full fast suite on Windows and Linux.

## Completion criteria
- `verify-bundle` exit 0 on Linux; 100% of `content_sha256` and `blind_nonroot` targets equal to
  `bundle.json`; fast suite green on both OS.
- Docs: 0 broken links; every number in the docs traceable to a report file.
- Handoff checklist complete.

## Risks and rollback
- Bundle size: canonical A+B estimated 10–25 GB; measured and recorded. Transfer resumable with
  `robocopy /Z` or `rsync --partial`.
- Rollback: delete the bundle directory; docs are plain edits.
