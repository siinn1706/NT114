---
phase: 10
title: "Missing-observability conditions and leakage-safe splits"
status: completed
priority: P1
effort: "2.5d"
dependencies: [9]
---

# Phase 10: Missing-observability conditions and leakage-safe splits

## Goal
Make every missing-observability condition reproducible, applicable only where the source
supports it, and paired by incident. Then generate immutable, group-isolated split manifests for
within-dataset, cross-system and cross-dataset protocols.

## Inputs
- Canonical builds and audit results (phase 09)
- [design/quality-leakage-splits.md](design/quality-leakage-splits.md) §5–6

## Outputs
- `RCA_ROOT/data/reports/condition-matrix-<dataset>.json` for every A dataset
- `RCA_ROOT/data/splits/<protocol>-<seed>-<hash8>/` (seed `0`), limited to the protocols that
  phase 02 marked feasible:
  - Milestone 1: `within-rcaeval-grouped` (cell grouping), `within-rcaeval-retrieval`
    (physical grouping), `loso-rcaeval`, `eval-only-rcaeval`.
  - Milestone 2: `eval-only-nezha`, `xdata-rcaeval-to-nezha` (no within/loso for Nezha unless
    phase 02 measured ≥20 groups); `within-aiops2025-grouped`, `within-aiops2025-retrieval`,
    `eval-only-aiops2025`, `xdata-rcaeval-to-aiops2025`; RCA100 protocols if its tier is A.

## Files
- Modify: `RCA_ROOT/src/rca/ablate.py` — add `mask_service_traces(tel, service)`; route
  `blind_root` through it; add `blind_nonroot` and `choose_nonroot_target(tel, root, uid)`;
  extend `CONDITIONS` by appending `"blind_nonroot"` (existing order kept); `apply(tel, condition,
  root_service, nonroot_target=None)`; `applicable()` keeps its current behaviour for existing
  conditions and adds the `blind_*` preconditions
- Create: `RCA_ROOT/src/rca/splits.py` — union-find grouping, protocols, manifest writer and
  verifier, staleness check
- Modify: `RCA_ROOT/src/rca/retrieve.py` — `CaseStore.search(query, case, method, mode, k,
  exclude_ids=frozenset())`: `_mask` keeps `system` equality and `case_id` exclusion, adds
  `exclude_ids`, and **no longer reads `case.root_service` / `case.fault`**. The caller computes
  `exclude_ids` (same `group_id` for `precedent`; plus same (root, fault) from `Truth` for the
  `no_precedent` oracle). Legacy behaviour is reproduced by passing the same sets (D14)
- Modify: `RCA_ROOT/src/rca/prep.py` — wire `conditions`, `split`, `verify-splits`
- Modify: `RCA_ROOT/src/rca/store.py` — `CanonicalStore.incidents(..., split_dir=..., role=...)`
- Create: `RCA_ROOT/tests/test_conditions.py`, `RCA_ROOT/tests/test_splits.py`
- Preserve: `tests/test_pipeline.py::test_ablation` passes unchanged

## Tasks
1. Tests first: T17, T18 (fixtures with repeated cells, overlapping windows, duplicate content
   hashes, a stratum with <3 groups).
2. `ablate.py` changes as listed; the eval-only ablation log line
   `{variant_id, pair_id, condition, masked_service}` is produced by the caller (`run_grid`), not
   stored by `ablate`.
3. Condition matrix: for each incident × condition, `applicable` + reason from canonical
   ModalityInfo, the anchor precondition (`anchor_kind ∈ {injection, alert}`, no
   `PRE_WINDOW_SHORT`), and the "≥1 modality remains" rule. This matrix is the only
   applicability source for the canonical path (T17 asserts that the conditions `run_grid`
   generates equal the matrix) (no telemetry load needed except span counts per service for `blind_*`, which are
   read from the traces Parquet `service_id` column only).
4. `splits.py`: group with union-find under the `physical` or `cell` rule (overlap computed on
   the evidence window, not the storage window); protocols per design; greedy stratified fill with seed;
   write `assignments.jsonl` and `split.json`; directory name from the assignments hash; refuse
   to overwrite; `verify-splits` recomputes hashes and checks `input_digest` against current builds.
5. Generate the listed manifests; commit them (they are tracked).
6. Report: per manifest, counts per split × system × fault family, number of groups, largest
   group, and the share of incidents in strata sent wholly to test.

## Tests
- T17, T18; T01 still green.

## Completion criteria
- 0 groups spanning splits (checked by `verify-splits` and the audit).
- Re-running `split` with the same inputs reproduces the same directory name.
- Condition matrices exist; no inapplicable condition is ever generated downstream.
- `blind_nonroot` never selects the root, and its target is identical on Windows and Linux
  (checked again in phase 12).

## Risks and rollback
- Union-find over shared fault cells may create very large groups for datasets with few cells
  (Cloud-OpsBench max 164 repetitions): the report shows group sizes; a protocol whose test split
  would be <10% of incidents is flagged and not used for headline results.
- Rollback: `ablate.py` change is additive; revert it and delete new split directories.
