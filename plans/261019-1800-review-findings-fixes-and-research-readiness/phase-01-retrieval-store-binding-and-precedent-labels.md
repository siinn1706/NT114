---
title: "Phase 01: Bind the retrieval store to the split; keep precedent labels"
status: completed
priority: P1
effort: 1 d
dependencies: [phase-00]
---

# Phase 01: Retrieval store binding (F1) and precedent labels (F4)

## Context

- `run_grid._store_entries` (`src/rca/run_grid.py:348-361`) loads every `store/*.json` under
  `evidence_dir` and checks only `evidence_fp`, which depends on builder, dataset build and matrix
  row, **not** on split or `store_limit`. `prepare` writes store files for the current split only
  (`:314-323`) but never removes others.
- Shared evidence dirs exist today: `dev-pilot.yaml` / `dev-sampling.yaml`
  (`results_dev_pilot/evidence`); `store-rcaeval-grouped.yaml` / `visibility-rcaeval.yaml`
  (`results_visibility/rcaeval/evidence`).
- Leak path: prepare with split A (train = X), then run with split B where some of X are val/test →
  their labels are shown as precedents.
- No-split branch (`:359-361`): with `split: null` and retrieval on, the store is built from the scored
  records, so labels of other scored incidents become precedents.
- F4: entries drop `root_ids` and `granularity`. `format_hits` prints `root cause: None`;
  `CaseStore.oracle_exclusions` compares `root == root` (None matches None); `hit_has_truth` compares
  only `h["root"]`.
- Label shapes (aggregate counts): RCAEval 736 service/single; AIOps2025 123 pod, 122 service,
  82 node (no primary), 73 multi-service (no primary); RCA100 83 service, 3 pod, 17 node (no primary);
  Nezha 101 pod.

## Requirements

1. **Eligible set.** The store is exactly `{incident_uid of Canon.store_incidents()}`: train role of
   the configured split, `full` applicable, after `store_limit`. `_store_entries` loads
   `store/<uid>.json` for each eligible uid and nothing else.
   - A missing eligible file raises (`run prepare`).
   - Extra files are ignored; their count goes to the manifest as `store_extra_files_ignored`.
   - Assert, for every entry, `cn.roles[uid] == "train"` and uid not in the selected query uids.
2. **No-split retrieval refused.** `run` and `prepare` raise when any retrieval arm is on and
   `split` is null. If a test depends on the old branch, move it to a split fixture; do not keep the
   branch.
3. **Store fingerprint binds the split.** `store_fp` blob adds `split_id`, `split_sha256`,
   `store_limit` and the sorted eligible uids (already implied by entries, kept explicit). The
   manifest records `store_fp`, `store_size`, `store_limit`.
4. **Labels kept.** Entries carry `root` (primary or None), `root_ids` (tuple) and `granularity`.
5. **Prompt `v1` precedent rule.** A precedent is shown only when it has a single service-level root
   (`root_service` not None). Others (node, multi-service without primary) are excluded from the store
   and counted per reason in the manifest (`store_excluded: {node: n, set_only: n}`). `format_hits`
   output for included entries is byte-identical to today. `format_hits` raises if it is ever given
   an entry whose root is None (defence in depth).
6. **Oracle and flags use sets.** `oracle_exclusions(truth)` excludes entries whose `root_ids ∪ {root}`
   intersects `truth_ids(truth)` with the same fault; it never matches on None. `hit_has_truth` uses
   the same set intersection.

Rendering set-valued precedents is a prompt change and belongs to a new prompt version (phase 07).

## Files

- Modify: `src/rca/run_grid.py` (`_store_entries`, `run`, `prepare`, `write_manifest`),
  `src/rca/retrieve.py` (`oracle_exclusions`, `format_hits` guard).
- Tests: `tests/test_leakage.py`, `tests/test_run_grid_canonical.py` (synthetic canonical fixtures in
  `tests/conftest.py`).

## Regression tests (write first, see them fail)

1. `test_store_ignores_files_from_another_split`: prepare with `within-rcaeval-retrieval-0` on the
   synthetic home, copy an extra `store/<uid>.json` whose uid is a test-role incident into the store
   dir, run → that uid is never an entry or a hit; manifest counts 1 ignored file.
2. `test_store_follows_split_change`: prepare split A, then switch config to a split B whose train role
   differs (synthetic: build a second split with another seed) without re-preparing → run raises for
   missing eligible files; after `prepare` the entries equal B's train uids.
3. `test_store_limit_change`: `store_limit: 2` then `store_limit: null` and back → entries are exactly
   the first k sorted train uids each time; `store_fp` differs between limits.
4. `test_retrieval_without_split_is_refused`.
5. `test_precedent_without_service_root_is_excluded_and_counted`: synthetic labels with a node-level
   and a multi-service train incident → excluded, manifest counts by reason; `format_hits` never
   contains `None`.
6. `test_oracle_exclusion_uses_root_sets`: set-scored query with `root_ids` {a, b} excludes a store
   entry with root a and the same fault; a None/None pair is never excluded by equality.
7. `test_format_hits_unchanged_for_service_roots`: golden string for two service-level hits.

## Acceptance

- [ ] Tests 1-7 fail on the current code (where applicable) and pass after the fix.
- [ ] `tests/test_leakage.py` and `tests/test_run_grid_canonical.py` pass in full.
- [ ] Evidence goldens unchanged; RCAEval store prompts unchanged (test 7).
- [ ] Manifest of a retrieval run shows split id, store size, ignored and excluded counts.

## Risk and rollback

- Risk: an existing script relies on the no-split store (smoke configs use `retrieval: [none]`, so
  none is known). Rollback: revert the phase commit; no data is touched.

## Implementation notes (2026-10-19)

- Prompt freeze: the digest of 144 rendered prompts (12 synthetic incidents × conditions × {none,
  hybrid}, 48 store entries) is `4efde402b2c8bb07…` before and after the change.
- `rca.leakage_audit.inputs` had the same unbound glob over `store/*.json`. It now reuses
  `run_grid._store_entries`, so the audit sees exactly the store the model sees
  (`tests/test_leakage_audit.py::test_audits_the_store_bound_to_the_split_not_every_store_file`).
  On the RCAEval grouped store its outputs are byte-identical to the published V6 files
  (374 entries, 0 ignored files).
- `docs/data_contract.md` §7.3 documents the binding.
