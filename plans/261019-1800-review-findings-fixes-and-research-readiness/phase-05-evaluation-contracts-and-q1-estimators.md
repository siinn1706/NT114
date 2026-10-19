---
title: "Phase 05: Evaluation contracts and Q1 estimators"
status: completed
priority: P1
effort: 2 d
dependencies: [phase-03]
---

# Phase 05: Evaluation contracts (F6) and Q1 estimators

## Protocol intent (what the fixes must match)

Protocol v2 §3: injection is the unit (`weight = 1/records of the injection`); every reported metric
carries a CI; datasets are never pooled in headline tables; DEV is never reported; DEV-fit thresholds
are reported next to the test-oracle curve and a stratified shift table. AIOps2025 set-scored
incidents are never pooled with top-1 incidents (§2). The H1 note
(`plans/261019-1501-sua-review-h1-power-va-sang-loc/research/h1-endpoint-va-power.md`) separates E1
(fixed coverage, exact, boundary ties answered fractionally), E1t (ties answered together, achieved
coverage ≥ c), E2 (DEV-fit threshold, achieved coverage reported) and E3 (base error − AURC). Its
H1-primary set pools `no_metric`, `no_log`, `no_trace` on RCAEval. That pooling is the only one the
protocol work so far declares, and it must be declared, not implicit.

## Current behaviour (verified)

- `analyze.selective_table` (`src/rca/analyze.py:209-253`): DEV rows are filtered on
  `model, condition, retrieval, store_mode` only, so one threshold is fitted on DEV pooled across
  datasets, label granularities and set-scored strata and applied to each test cell.
- `selective.shift_table` (`src/rca/selective.py:298-312`): groups by `system, fault, split_role`,
  pooling models, conditions and retrieval arms; base error and level shares are unweighted record
  means.
- CIs present: `table_cells` (all), `table_confidence` AUROC, `dev_fit` coverage and risk.
  CIs absent: `table_confidence` AUPRC, AURC, Brier, ECE, gap; `table_selective` curve AURC,
  risk@0.5/0.7/0.9, coverage_at_risk; references L1 coverage and risk, C2 risk.
- The E1 exact-coverage estimator and `pilot_decision` exist only in
  `plans/261019-1501-.../work/h1_power.py` (8 tests), not in `src`.

## Requirements

1. **Explicit source → target for calibration.**
   - Default fit key = the full target stratum: `dataset, label_granularity, set_scored, model,
     condition, retrieval, store_mode`.
   - Optional analysis-config pooling, declared and named:
     `selective: {pools: {single_modality: {condition: [no_metric, no_log, no_trace]}}}`. A pool defines
     both the DEV source and the test target (the pooled test set is evaluated as one cell with
     `condition = pool:<name>`). No other implicit pooling.
   - Every `dev_fit` row carries `source_split_role=val`, `source_stratum` (JSON of the filter),
     `n_dev_records`, `n_dev_injections`, and the target stratum columns.
   - A target stratum with no DEV source writes a row with `no_source` and NaN, never a pooled fit.
2. **Shift table.** Group by the strata columns (`strata_cols` minus `split_role`, plus pool cells)
   × system × fault × split_role. Base error and confidence-level shares are injection-weighted
   (`weight`), with `n_records`, `n_injections` and `present_in`. Called on the frame that still holds
   DEV and test rows, after `reweight`.
3. **CIs for every reported metric** with the existing cluster bootstrap (`analyze._boot` or
   `metrics.cluster_bootstrap_means` where the statistic is a weighted mean):
   - `table_confidence`: AUPRC, AURC, Brier, ECE, gap;
   - `table_selective` curve rows: AURC, risk@c for each c, coverage_at_risk;
   - references: L1 coverage and risk; C2 risk (= base error, weighted mean); O coverage.
   A statistic undefined in a draw (no answered rows, one class) is NaN in that draw and ignored, and
   the share of NaN draws is reported as `<metric>_nan_draws` when > 0.
4. **Q1 estimators in `src/rca/selective.py`** (ported, not re-derived, from `h1_power.py`):
   - `exact_coverage_risk(correct, score, coverage, weights)`: answers the top-weight rows up to
     exactly `coverage`; the boundary tie group is answered fractionally, equal to the expectation of
     the seeded random tie-break of `coverage_matched_threshold` (C1).
   - `gain_vs_random(...)`: base error − exact-coverage risk; C2 analytic.
   - Rows in `table_selective`, each labelled by `kind`:
     `fixed_exact` (E1, achieved coverage = c by construction), `fixed_ties_together` (E1t, reports
     achieved coverage), `dev_fit` (E2, achieved coverage with CI, existing), `aurc_gain` (E3). Each
     with a cluster-bootstrap CI over injections.
   - Tie handling is stated in the table docstring and in `analysis_meta.json["selective_ties"]`.
   - `pilot_decision` stays in the plan's work dir but imports the `src` estimators; its 8 tests must
     still pass against them.
5. Headline guard keeps working; DEV rows still never enter `table_cells` or contrasts.

## Files

- Modify: `src/rca/analyze.py` (`selective_table`, `confidence_table`, `run`, meta),
  `src/rca/selective.py` (`shift_table`, `references`, new estimators).
- Modify (import only): `plans/261019-1501-sua-review-h1-power-va-sang-loc/work/h1_power.py`.
- Tests: `tests/test_analyze.py`, `tests/test_selective.py`,
  `plans/261019-1501-.../work/test_h1_power.py`.
- Docs: protocol v2 gets a dated addendum (§2 selective rows, pools, tie rule), recorded in the
  single-LLM `decisions.md` as **pending owner** until accepted.

## Regression tests

1. `test_dev_fit_never_pools_datasets`: DEV rows of two datasets with different score scales → each
   test cell's tau equals the tau fitted on its own dataset's DEV; row carries `source_stratum`.
2. `test_dev_fit_no_source_row`: test granularity absent from DEV → `no_source`, no tau.
3. `test_declared_pool_fits_and_scores_pooled_cell`: `single_modality` pool → one `pool:` cell, tau
   from pooled DEV only.
4. `test_shift_table_is_stratified_and_weighted`: two conditions with different error rates and an
   injection with 3 records → separate rows; base error equals the weighted mean.
5. `test_every_reported_metric_has_ci`: for each table, every numeric metric column outside an
   allow-list of counts/ids/thresholds has `_lo`/`_hi` siblings.
6. `test_exact_coverage_matches_c1_expectation`: matches the mean of 4,000 C1 draws within 0.004
   (same as the plan test).
7. `test_ties_together_reports_achieved_coverage`: consensus with 11 levels → achieved coverage > c
   and reported.
8. Plan tests `test_h1_power.py`: 8 passed using the `src` estimators.

## Acceptance

- [ ] Tests 1-5 fail on the current code and pass after; 6-8 pass.
- [ ] Analysis runtime on the canonical mock grid at `n_boot` 2,000 and 10,000 is measured and
      reported (CPU, wall seconds).
- [ ] `rca.reproduce` on a fresh analysis exits 0 (byte-identical tables across two runs).

## Risk

- Strict stratum matching can leave test strata without a DEV source (94 test incidents lie in
  test-only strata). That is the honest outcome; the `no_source` row makes it visible.
- Bootstrapping risk@c per draw is a Python loop over levels; if runtime is excessive, vectorise over
  tie levels as `h1_power.level_mats` does, not by lowering B.

## Implementation notes (2026-10-19)

- E1/E1t/E3 are **columns on the `curve` rows**, not separate `kind` rows: `risk_exact@c` and
  `gain_exact@c` (E1; `gain_exact` is the planned `gain_vs_random`), `risk@c` with
  `coverage_ties@c` (E1t), `AURC` and `gain_AURC` (E3), each with `_lo`/`_hi`. E2 stays in
  `kind = dev_fit` rows. One row per cell × score keeps the table joinable. The tie rules are in
  `analyze.SELECTIVE_TIES` and `analysis_meta.json["selective_ties"]`.
- The `dev_fit` column `n_dev` became `n_dev_records`, next to `n_dev_injections`.
- Estimators live in `rca.selective` (`level_mats`, `boot_mats`, `gain_*`, `exact_coverage_risk`,
  `selective_endpoints`, `confidence_endpoints`). `h1_power.py` imports them, and its 8 tests pass.
- Runtime on the offline smoke grid (156 rows, 16 cells), wall time on this Windows CPU:
  `n_boot` 2,000 → 32.5 s, 10,000 → 151.0 s. The profile is dominated by the pre-existing per-draw
  loops in `cell_table` and the `confidence_table` AUROC (`metrics.cluster_bootstrap`, 42 of 44 s).
  The new vectorised selective and confidence endpoints are a small share.
- Protocol v2 §9 addendum written and accepted by the owner (2026-10-19).
- Pool weights: within a pooled cell, weight = 1 / records of the injection, so each injection
  weighs 1. `reweight`'s distinct-incident count gave an injection with three pooled conditions
  weight 3. The bug was found while verifying the DEV pool and fixed with a regression test.
