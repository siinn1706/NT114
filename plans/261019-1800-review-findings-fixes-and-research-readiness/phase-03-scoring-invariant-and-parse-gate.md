---
title: "Phase 03: Scoring invariant and feasibility parse gate"
status: completed
priority: P2
effort: 0.5 d
dependencies: [phase-00]
---

# Phase 03: Miss rank (F7) and completion parse rate (F3)

## Context

- `score.correctness` (`src/rca/score.py:23-27`): a miss gets `n_candidates + 1`. With
  `n_candidates` ≤ 4 that is ≤ 5 = `RANK_CAP`, so `cell_table` counts it in AC@k for k ≥ n+1 and
  MRR@5 adds 1/(n+1). Same for parse failures (empty ranking) and for baselines and contrasts, which
  read the same `rank`.
- `feasibility.grid_stats` (`src/rca/feasibility.py:132-152`): `parse_rate` = share of cells with any
  valid sample (`not parse_failed`), and `verdict` gates on it against `MIN_PARSE_RATE`. Grid rows
  already carry the completion-level `parse_rate` (valid / n) from `llm.aggregate`.
- Phase 00 may add a test-environment item for `test_run_end_to_end_with_fake_server` here.

## Requirements

1. **Miss rank.** Miss and parse-failure rank = `max(n_candidates, RANK_CAP) + 1`, with `RANK_CAP`
   imported from `rca.metrics`. Ranks for `n_candidates` ≥ 5 are byte-identical to today. Docstring
   states the invariant: a miss is never within the top-`RANK_CAP` window.
2. `metrics.rank_of_truth` (legacy, `len(ranking) + 1`) has no caller in `src`; remove it or apply the
   same rule. Check `tests/` for callers first.
3. **Parse gate.** `grid_stats` reports:
   - `completion_parse_rate` = Σ(parse_rate × n) / Σ n over live rows (n from `row["sampling"]["n"]`);
   - `cell_any_valid_rate` (today's number, renamed);
   - `cell_all_valid_rate`;
   - per-cell completion parse rate in `parse_rate_by_cell`.
   `verdict` gates on `completion_parse_rate`. The feasibility report columns are renamed accordingly
   (`feasibility.py:286`).
4. `compare_sampling` already uses the row `parse_rate`; leave it, but weight by n for consistency if
   n can differ between arms (it cannot within one config).

## Files

- Modify: `src/rca/score.py`, `src/rca/metrics.py` (legacy helper only), `src/rca/feasibility.py`.
- Tests: `tests/test_score.py`, `tests/test_analyze.py` (AC@k/MRR on a 3-candidate frame),
  `tests/test_contrasts.py` (ac5 on small sets), `tests/test_feasibility.py`.

## Regression tests

1. `test_miss_is_beyond_cap_for_small_candidate_sets`: n_candidates ∈ {1, 2, 3, 4}, wrong ranking and
   empty ranking → rank 6, AC@5 false.
2. `test_cell_table_small_candidates`: a 3-candidate cell of misses → AC@1-5 = 0 and MRR@5 = 0.
3. `test_rank_unchanged_for_large_candidate_sets`: n_candidates ∈ {5, 12} → rank n+1 as before.
4. `test_grid_stats_completion_parse_rate`: one live row with parse_rate 0.1 (1 of 10) →
   `completion_parse_rate` 0.1, `cell_any_valid_rate` 1.0, `verdict` infeasible on parse.
5. Existing `test_grid_stats_ignore_cached_rows` and `test_verdict` updated to the new names.

## Acceptance

- [ ] Tests 1, 2, 4 fail on the current code and pass after; test 3 passes before and after.
- [ ] Baseline and visibility outputs for canonical datasets are unchanged (all have ≥ 5 candidates;
      confirm with a one-line min(n_candidates) check per dataset on the evidence files).
- [ ] Docs that name the feasibility parse rate (`docs/gpu_deployment.md`) use the new term.

## Risk

Low. Changing the miss rank for small sets changes no canonical result if the min-candidates check
holds; if it does not, record which records change.
