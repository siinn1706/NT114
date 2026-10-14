---
phase: 5
title: "RCAEval reference adapter and legacy view"
status: completed
priority: P1
effort: "3d"
dependencies: [4]
---

# Phase 05: RCAEval reference adapter and legacy view

## Goal
Build canonical RCAEval (RE1, RE2, RE3) from the Zenodo originals, streamed from the zips, and
prove that the legacy pipeline sees the same telemetry through a compatibility view.

## Inputs
- `RCA_ROOT/data/raw/rcaeval-zenodo/zenodo-14590730/RE{1,2,3}-{OB,SS,TT}.zip`
- `data/reports/profile/rcaeval-zenodo.json` (phase 02)
- Spec: [design/adapter-contracts.md](design/adapter-contracts.md) §3.1

## Outputs
- `RCA_ROOT/data/canonical/v1/rcaeval/` (visible, eval_only, `_build.json`)
- `RCA_ROOT/data/reports/quality-rcaeval.json`
- Phase report with counts per subset × system × quality state

## Files
- Create: `RCA_ROOT/src/rca/adapters/rcaeval.py` — discovery via `MemberSource` (zip or directory
  layout, so synthetic data from `scripts/make_synthetic.py` also works), cell parser with the
  fault vocabulary, duplicate detection, label artefacts, metric column split, unit conversion,
  `FAULT_FAMILY` table (`cpu→cpu, mem→memory, disk→disk-io, delay→network-delay,
  loss→network-loss, socket→socket, f1..f5→code-defect`)
- Create: `RCA_ROOT/src/rca/legacy_view.py` — `visible_case(incident)` → `rca.data.VisibleCase`
  with `case_id = incident_uid` (so the candidate shuffle seed carries no label);
  `truth(label)` → `rca.data.Truth`; `legacy_telemetry(store, uid, metric_set="simple")` →
  `{"metrics", "logs", "traces"}` DataFrames with the exact column names and units that
  `ablate`/`evidence` use today (metric `_` encoded as `.`, design schema §4)
- Modify: `RCA_ROOT/src/rca/data.py`
  - add `VisibleCase` (`case_id, dataset, system, inject_time, path, services`) and
    `Truth` (`root_service, fault`) dataclasses; keep `Case` as the legacy class with a
    `visible()` and `truth()` split, so existing callers keep working (D13)
  - fix D1 in `_parse_service_fault` with the fault vocabulary regex (shared constant imported
    from `adapters/rcaeval.py`); encode the batch in `case_id` (`…_f3b1_<n>`); assert `case_id`
    uniqueness in `discover_cases` (raise with both paths on collision)
  - `encoding="utf-8"` at line 70
- Create: `RCA_ROOT/tests/test_adapter_rcaeval.py`, `RCA_ROOT/tests/test_legacy_compat.py`,
  `RCA_ROOT/tests/test_realdata_samples.py` (`rcaeval` section)
- Preserve: `evidence.py`, `ablate.py`, `retrieve.py`, `run_grid.py` (unchanged in this phase)

## Tasks
1. Tests first: T08 on fixture zips containing every known defect, including both
   `ts-route-service_f3/1` and `ts-route-service_f3_1/1` (distinct ids, both discovered); T10
   parity harness that extracts N cases from a zip into `tmp_path` (`safe_extract`), runs the
   current `data.discover_cases` + `load_case` + `evidence.build`, and compares the **evidence
   text and features per condition** with `legacy_telemetry` + `evidence.build`. Candidate order
   and prompts are not compared: the canonical path seeds the shuffle with `incident_uid`, so
   legacy and canonical prompts are intentionally not byte-comparable.
2. Implement discovery: one `MemberSource` per zip; group members by case directory; numeric
   instance dirs are cases; non-numeric dirs go through the duplicate check.
3. Labels: parse the cell; map service with `identity.ServiceMap` rule `canon`; `eval_tier=A`.
4. Anchor and window per spec; `time.end_ns = null`.
5. Normalize: stream `metrics.csv`/`simple_metrics.csv` (or `data.csv`/`simple_data.csv` for
   RE1) with `pyarrow.csv.open_csv`, melt to long in batches; logs and traces per spec; record
   per-member row counts in the ledger.
6. Candidates: services present in any modality (as today), minus `kind=infra` ids.
7. Build: `python -m rca.prep normalize --dataset rcaeval`, then `validate`.
8. HF parity (T09): for 20 seeded random case pairs, compare canonical tables with the HF
   Parquet; classify every difference into the 6 known classes; any other class fails the test.
9. Phase report: counts (expected 736 discovered → 735 accepted-or-warned + 1 REJECT duplicate,
   unless the profile says otherwise), findings histogram, build time, canonical size on disk.

## Tests
- T08, T09 (realdata), T10 (fixtures + 10 real cases); T01 and T02 still green.

## Completion criteria
- 100% of discovered RCAEval incidents have records; 0 `ADAPTER_EXCEPTION`.
- The 3 RE3-TT `ts-route-service_f3_1` incidents carry `primary_root_service = "route"` (canon of
  `ts-route-service`) and fault `f3`, and coexist with the 3 `ts-route-service_f3` incidents
  (6 distinct ids in both the canonical store and the legacy `discover_cases`).
- Every A-tier incident has `primary_root_service ∈ candidates.services`, or is QUARANTINE with a
  finding that names why.
- `root_cause.txt` content appears in no visible file (grep test).
- T10: evidence text identical for all compared cases.
- Rebuild is a no-op (all `.done` markers valid) and a forced rebuild gives identical digests.

## Risks and rollback
- Metric column split could differ from the legacy `rsplit("_", 1)` on unusual names: T10 catches
  it; when the legacy split is wrong, record it as a fix in the report instead of copying the bug.
- Legacy `case_id`s change for the 3 batch cases only; existing `results/` from older runs keyed
  on the colliding id are not comparable for those cases (noted in the phase report).
- Rollback: delete `data/canonical/v1/rcaeval/`; revert `data.py`.
