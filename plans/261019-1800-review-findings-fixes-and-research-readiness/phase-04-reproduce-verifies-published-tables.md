---
title: "Phase 04: Reproduce verifies published tables"
status: completed
priority: P2
effort: 0.5 d
dependencies: [phase-00]
---

# Phase 04: Reproduction verification (F5)

## Context

`rca.reproduce.reproduce` (`src/rca/reproduce.py:30-44`) reruns the analysis into a temp dir and
compares new table hashes with `analysis_meta.json["tables_sha256"]`. It never reads the published
CSVs, so a modified or deleted table in the run dir still reports `match`. Changed inputs are printed
but do not change the exit code.

## Requirements

1. For each table in `meta["tables"]`, read `run_dir / filename`:
   - absent → `published_missing`;
   - sha256 ≠ recorded → `published_modified`.
2. Regenerated comparison stays: `match`, `differs`, `missing` (regenerated table absent), plus
   tables regenerated but not recorded → `differs` (as today).
3. A table is `match` only when published file, recorded hash and regenerated hash all agree.
4. Also verify the recorded config copy (`meta["config"]`) exists; absent → exit 2 with a message.
5. Exit codes unchanged in meaning: 0 all match; 1 any table not `match`; 2 no analysis.
   `inputs_changed` keeps its current behaviour (reported, not failing); changing that is out of scope.

## Files

- Modify: `src/rca/reproduce.py` (and its docstring).
- Tests: `tests/test_reproduce.py` (reuse the `chain` fixture).

## Regression tests

1. `test_reproduce_flags_modified_published_table`: append a byte to one CSV → exit 1, that table is
   `published_modified`, the others `match`.
2. `test_reproduce_flags_deleted_published_table`: delete one CSV → exit 1, `published_missing`.
3. Existing `test_reproduce_matches_then_names_the_changed_table` still passes.

## Acceptance

- [ ] Tests 1-2 fail on the current code and pass after; test 3 passes.
- [ ] The V7 real-slice reproduce check (research/05) still exits 0 when rerun in phase 06.
