---
title: "Phase 8 (optional): Retire the legacy RCAEval data_root path"
status: todo
priority: P3
effort: 1 d
dependencies: [phase-02]
---

# Phase 8 (optional): Retire the legacy `data_root` path

Run this phase only if the owner chooses it (validation question 3).

## Context

Every experiment config uses `source: canonical`. The legacy path reads RCAEval directly from
`data_root`. It consists of:

- `run_grid.select_cases` and the non-canonical branches of `prepare` and `load_evidence`
  (`run_grid.py:302-345`);
- `data.discover_cases` and `data.load_case`;
- `configs/pilot.yaml` and `configs/synthetic.yaml`;
- `tests/test_legacy_compat.py` and `tests/test_legacy_golden.py`.

The golden test protected evidence parity during the migration to the canonical store, and that
migration is complete. `legacy_view.py` stays, because the canonical path builds telemetry
through it (`run_grid.py:230`).

## Requirements

1. Before deleting, confirm that `tests/test_legacy_golden.py`'s parity is also asserted for the
   canonical synthetic path. If it is not, port the assertion to `tests/test_run_grid_canonical.py`
   first.
2. Remove the legacy branches, configs and tests. `load_cfg` rejects a config without
   `source: canonical`, with a clear message.
3. Keep `data.Case`, `Truth` and `VisibleCase`. They are the shared types.

## Verification

- The non-realdata and realdata suites pass.
- V1 (evidence digests) from phase 06 still passes.
- `grep -n "data_root" src configs` returns nothing.

## Rollback

`git revert` of the phase commit.
