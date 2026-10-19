# CPU validation and readiness gate (phase 06)

Plan: [261019-1800 review findings](../261019-1800-review-findings-fixes-and-research-readiness/plan.md).
Windows 11 Pro, CPU only, mock LLM only. Tables and smoke outputs were written to the session
scratchpad, so no repository result directory changed.

## Verdict

**Tier 1 (CPU validation) passes.** All seven findings are fixed. Every regression test failed on
HEAD `2198ed7` and passes now. Evidence, prompts and the published leakage audit are unchanged.
Tiers 2 and 3 still need owner decisions and the GPU machine (open items below).

## Checks

| # | Check | Command (from `nt114-rca/nt114-rca`, `PYTHONPATH=src`) | Exit | Result |
|---|---|---|---|---|
| 1 | Non-realdata suite | `python -m pytest -q -m "not realdata" -rfE` | 0 | 346 passed, 56 deselected, 0 failed (369 s; rerun after the owner follow-up). The baseline was 313; 33 tests were added |
| 2 | Realdata suite | `python -m pytest -q -m realdata -rfEs` | 0 | 56 passed, 0 skipped (83 s) |
| 3 | Offline smoke chain (`configs/exp/smoke-offline.yaml`, synthetic home rebuilt in scratch) | synth → normalize → conditions → split → `prepare` → `run` → `run` again → `analyze` → `rca.reproduce` | 0 at every step | 156 rows, and the rerun added none. Manifest v3: `store` block with split `within-rcaeval-retrieval-0-610aa5a5`, 48 eligible, 48 entries, 0 ignored files; `exec_sig` per model. All 7 tables reproduced. After a one-line edit of a published CSV, `reproduce` exits 1 with `table_shift (published_modified)` |
| 4 | Canonical smoke (`smoke-canonical.yaml`, repo data home, mock) | `prepare` → `run` → `analyze` → `rca.reproduce` | 0 | 53 rows; all 6 tables reproduced |
| 5 | Evidence fingerprints | sha256 of `results_visibility/*/evidence/*.json` against the single-LLM plan's `reports/evidence-digests-after.txt` | – | **0/862 changed.** 6 extra files sit in the pre-existing `_smoke_rcaeval` directory, which the after-file never listed. Evidence-building code was not edited |
| 6 | Leakage | `tests/test_leakage.py` (in check 1); `python -m rca.leakage_audit` on `store-rcaeval-grouped.yaml` with `out` in scratch | 0 | Store bound to `within-rcaeval-grouped-0-e9b2c81c`: 374 eligible, 374 entries, 0 excluded, 0 ignored. Audit JSONL and summary byte-identical to the published `results_store/rcaeval/` files |
| 7 | Prompt freeze | session probe: 144 prompts on the synthetic home × {none, hybrid} | 0 | `4efde402b2c8bb07…`, equal to the pre-change digest |
| 8 | V7 real slice (Nezha, mock; out redirected to scratch) | `run_grid run` → `analyze` → `reproduce` | 0 | 752 rows; all 8 tables reproduced |

Red → green: the updated test files were run against the HEAD source in a scratch worktree (since
removed). 37 tests failed there. All of them are new or contract-changed tests from phases 01–05,
and all pass now.

Analysis runtime, measured on the offline smoke grid (156 rows): `n_boot` 2,000 took 32.5 s and
10,000 took 151.0 s. Most of that time is the pre-existing per-draw `cell_table` and AUROC bootstraps.

## Tier 2: DEV pilot (open)

- [x] Tier 1 green.
- [ ] `llms.txt` chain on the GPU machine: bundle at the pinned revision, portability, Linux gate,
      GPU probe, and feasibility on DEV with the completion parse gate.
- [ ] `dev-pilot.yaml` dry checks. The `prepare` store must hold the grouped split's train role
      only, and the manifest must show 0 ignored store files. `dev-sampling.yaml` shares that
      evidence dir, so check its manifest too.
- [x] Q1 pilot spec frozen: estimators in `src`; pool `single_modality` declared in
      `configs/analysis/dev-pilot.yaml`; SESOI 0.05 and protocol v2 §9 accepted by the owner
      (`decisions.md`, 2026-10-19).
- [ ] Owner approval to run the model.

## Tier 3: main experiment (open)

- [ ] DEV pilot finished; `pilot_decision` result, measured consensus distribution and ICC
      recorded; `h1_power.py` rerun with the measured parameters.
- [ ] Confirmatory family chosen; preregistration frozen; `preregistration_sha` set.
- [ ] DEV thresholds frozen: tau values and source strata written before any test run.
- [ ] Headline guard passes on a dry frame: mixed signature, DEV, mock and oracle checks.
- [ ] Test-role config uses a fresh `out` and evidence dir; manifest signature recorded.

## Owner follow-up (2026-10-19, after the decisions)

**Pool verification.** The pool was checked with a mock DEV grid (val role, `retrieval: none`,
visibility evidence, outputs in scratch), analysed with `configs/analysis/dev-pilot.yaml`. It is one
stratum: rcaeval × service × val × model × `pool:single_modality` × none. It holds 210 records
(equal to the sum of the three source cells) and 78 injections. The same definition gives 108
injections and 285 records on the test role, from the visibility audit, matching the H1 note.

The check found a weighting bug. In the pooled cell each injection weighed 1–3, because
`reweight` counts distinct incidents, while an incident has one record per pooled condition. Each
injection now has total weight 1 (`analyze._pooled`; `test_pooled_cell_weighs_each_injection_once`
failed before the fix and passes after).

**Grids without `exec_sig`.** These are kept unchanged and not relabelled. `run` refuses to append
to them. Their configs now write to fresh directories:

| Old grid (rows, all mock) | Config | Fresh output |
|---|---|---|
| `results_smoke/grid.jsonl` (312) | `configs/exp/smoke-offline.yaml`, `configs/analysis/example-mock.yaml` | `results_smoke_sig/` |
| `results_smoke_canonical/grid.jsonl` (106) | `configs/exp/smoke-canonical.yaml`, `docs/gpu_deployment.md` | `results_smoke_canonical_sig/` |
| `results_v7/nezha/grid.jsonl` (752) | `configs/exp/v7-nezha-mock.yaml`, `configs/analysis/v7-nezha-mock.yaml` | `results_v7_sig/nezha/` |

`results_dev_pilot/` does not exist yet, so `dev-pilot.yaml` starts with a signed grid.

**Stale directories.** `plans/review-runtime-261019-1746/pytest-unsandboxed` and `pytest-valid`
were deleted after checking their resolved paths, that no process referenced them, and that they
held no reparse points. Both baseline logs (`cpu-tests.log`, `cpu-tests-verified.log`) are kept.
