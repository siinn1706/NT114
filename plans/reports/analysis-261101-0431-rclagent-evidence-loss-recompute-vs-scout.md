# Recompute vs scout: phase 4 confirmatory run, RQ (b) evidence loss

Ngày 2026-11-01. Nội dung là báo cáo trả về của agent chạy phase 4, lưu nguyên văn (tiếng Anh). Kiểm chéo độc lập: `plans/reports/verify-261101-rclagent-evidence-loss-p4.md`.

Status: DONE_WITH_CONCERNS
Summary: The confirmatory runs ran on `s1-v2` and `r2` with the frozen analyzer. The freeze hashes still match, the 124 tests pass, and no frozen file was edited. All invariants pass, every scout number recomputed identically, and the labels agree 62 of 62 between the two corpora.

## Outputs
- Outputs are in `K/runtime/analysis-evidence-loss-s1-v2/`, `K/runtime/analysis-evidence-loss-r2/` and `K/runtime/analysis-evidence-loss-r2-vs-s1-v2/` (`joined.csv` plus `summary.json`). `K` is `F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`.
- Calibration exclusion: the analyzer has no exclude flag, so `runs.csv` keeps all 72 runs per corpus. The main table drops case `99f095` in all three conditions, as codebook 13.1 says. The sensitivity columns are "all 8 cases" and "only the two calibration runs removed".

## Invariants (S1 v2 / r2)
- **Freeze:** `prereg.frozen`, `codebook_sha_matches`, `analyzer_sha_matches` and `imports_sha_match` are all true.
- **Problems:** `integrity_problems` is empty and `completed_without_score` is 0.
- **Scorer:** scorer equivalence compared 70 of 70 scored runs (S1 v2) and 62 of 62 (r2), with 0 mismatches.
- **Join:** tool_results joined 5281/5281 and 4910/4910, 10191 in total.
- **Hint:** `hint_equivalence` is 70 true and 2 `NA` for S1 v2, and 62 true and 10 `NA` for r2. The `NA` runs are the censored ones.
- **Metric budget:** `tool_result_budget` events for metric tables are 0. They exist only for `search_logs` (2876 in S1 v2).
- **Fallback and unseen branches:** self-state fallback spans are 0 and `unseen_branches` is `{}`.
- **Independent check from the raw zips:**
  - `response.number` matches the preceding request in 6855/6855 (S1 v2) and 6352/6352 (r2).
  - 3888/3888 tree nodes have the right parent.
  - 3642/3642 consolidate prompts match the child count in the tree.

## Indicator margins, S1 v2
Format is k/n over completed runs. "Main" drops `99f095`.

| Condition | Table | Runs (completed) | I0 | I1 | I2 | I3 | I4 (R@1) | I5 same / diff / refusal |
|---|---|---|---|---|---|---|---|---|
| `metric` | main | 21 (20) | 11/20 | 11/11 | 3/20 | 11/20 | 8/20 | 7 / 4 / 9 |
| `metric` | all 8 cases | 24 (23) | 14/23 | 14/14 | 3/23 | 14/23 | 10/23 | 8 / 4 / 11 |
| `metric_no_log` | main | 21 (21) | 15/21 | 14/15 | 4/21 | 12/21 | 10/21 | 13 / 3 / 5 |
| `metric_no_log` | all 8 cases | 24 (24) | 18/24 | 17/18 | 4/24 | 15/24 | 10/24 | 16 / 3 / 5 |
| `no_metric` | main | 21 (20) | 0/20 | none | 0/20 | 0/20 | 4/20 | 5 / 0 / 15 |
| `no_metric` | all 8 cases | 24 (23) | 0/23 | none | 0/23 | 0/23 | 5/23 | 7 / 0 / 16 |

- **`no_metric`:** I0 is 0 by design, since the metric source is removed. I1 has no denominator because I0 never holds.
- **`de6a50 metric_no_log`:** it has no GT span, yet I0 is true 3 of 3 because a `frontendservice` span received the GT table.
- **Lenient and strict variants (all 8 cases):** `I2_lenient` is 9/23, 10/24 and 4/23, and `I3_strict` is 11/23, 12/24 and 0/23, in the order `metric`, `metric_no_log`, `no_metric`.

## `first_loss_linear` and `final_residual`
| Condition | Table | `first_loss_linear` | `final_residual` |
|---|---|---|---|
| `metric` | main | S0 9, S2 8, preserved 3, NA 1 | S0 9, none 8, `reaches_final_input_not_rank1` 3 (all `top1_equals_wrong_root_label`), NA 1 |
| `metric` | all 8 cases | S0 9, S2 11, preserved 3, NA 1 | S0 9, none 10, `reaches_final_input_not_rank1` 4, NA 1 |
| `metric_no_log` | main | S0 6, S1 1, S2 10, S3 1, preserved 3 | S0 6, S1 1, none 10, `reaches_final_input_not_rank1` 4 |
| `metric_no_log` | all 8 cases | S0 6, S1 1, S2 13, S3 1, preserved 3 | S0 6, S1 1, none 10, `reaches_final_input_not_rank1` 7 |
| `no_metric` | main | S0 20, NA 1 | S0 16, none 4, NA 1 |
| `no_metric` | all 8 cases | S0 23, NA 1 | S0 18, none 5, NA 1 |

- **`reaches_final_input_not_rank1`:** every run in this residual splits to `top1_equals_wrong_root_label`. None are `top1_differs_from_root_label` or `root_refusal`.
- **Flags (all 8 cases):** `chain_weakened` is 11 / 13 / 0 for `metric` / `metric_no_log` / `no_metric`. `hint_weakened` is 0 / 2 / 0, and `hit_without_evidence` is 0 / 0 / 5.
- **Outcome sentences, main table, `metric`:** `S0_gt_span_absent` 3/4, `S0_gt_span_present_not_queried` 0/4, `S2_root_label_lost_hit_kept` 2/3 and `S4_inputs_present_not_rank1` 1/4. This matches the codebook's own forecast. These are a preview only; the formal outcome is for the next analysis phase.

## Recompute vs scout
Every item matches exactly, including each count named in the phase file. No scout number was off.
- **Run and join counts:** 144 runs; 10191 tool results (5281 + 4910); 3888 tree nodes; 3642 consolidate prompts; 70 and 62 completed runs; GT spans per case 13, 10, 1, 2, 10, and 0 in the other three.
- **`metric` funnel (14 runs):** GT table 14; abnormal GT spans 92/98; GT in hint 14; root names GT 3; R@1 10.
- **`no_metric` (15 runs):** 0 tables, 0/108 abnormal spans, R@1 5.
- **`metric_no_log` (15 runs):** 8 R@1.
- **Self-state abnormal rate:** 324/327 with a table, 66/1574 without.
- **D1 and error-log claims:**
  - 14 spans claim `has_error_logs`, all `frontendservice`. Under the codebook's definition these split into 4 `D1` and 10 `D1_na`.
  - The 10 `D1_na` spans are all in `metric_no_log`, where the log source was removed.
  - 11/11 failing and 0/18 passing runs carry the claim; under `D1` it is 4/11 and 0/18.
  - That is a definition difference, not a mismatch.
- **Logs:** 222/222 non-empty log results condensed (r2: 200/200). All 298146 log rows have `severity: unknown` (r2: 267295), and none contain `error`, `exception` or `fail`.
- **Reviewer figures:** `I2` 3/14; S2 11/14; root vs top-1 `same` 8, `diff` 4, `refusal` 11.
- **Condition overlap:** `agent_complete` overlap `metric` vs `metric_no_log` 1156/1249.

## The 8 `productcatalogservice` NO_ROWS cases
The model typed a wrong timestamp, so the query window missed the data.
- **What happened:** the leading digits of the 10-digit second field were written `14` or `16` instead of `17`. The `de6a50` case is 100000000 s off and the other two are 300000000 s off.
- **Oracle check:** running the harness metric tool on the case input at the span's own timestamp returns NO_KPI, with 8646 to 10087 rows matching the service name. At the model's timestamp it returns NO_ROWS.
- **Counts:** 8 in `metric` and exactly 8 in `metric_no_log` (same spans), in both S1 v2 and r2. They come from `30e3c7` (3), `5f7a77` (3) and `de6a50` (2 of 3 seeds).
- **Scope:** all 8 queries were for a non-GT service, so no I0 or `S0_empty_result` label is affected. The 54 `frontendservice` NO_ROWS per condition are the `frontend` metric-name issue, with correct timestamps.

## Label join, r2 vs S1 v2
This is a determinism check, not independent stability and not a second source of evidence.
- **Groups:** 62 pairs both completed, 2 both censored, 8 completed in S1 v2 but censored in r2.
- **Agreement:** the 62 completed pairs agree 62 of 62 on every compared column, including I0 to I5, rank, MRR, `first_loss_linear`, `final_residual`, D1 and D2. The list of differing pairs is empty.
- **Plan expectation:** the plan allowed I4 and I5 to differ in up to 14 pairs, but they agreed in all 62.

## The 8 `H_cap` runs
All eight are `no_metric` in r2 and are kept out of the main table. Their stop points are:

| Case, seed | Request count at stop |
|---|---|
| `272a47` s28 | 11 |
| `30e3c7` s26 | 10 |
| `30e3c7` s28 | 10 |
| `5f7a77` s26 | 160 |
| `5f7a77` s27 | 160 |
| `5f7a77` s28 | 159 |
| `7bbfa6` s28 | 25 |
| `99f095` s28 | 12 |

For these runs I0 is `NA_censored` and everything after it is `NA`.

## Housekeeping
- **Erratum:** added to `deviation-log.md` as "Erratum 1". Codebook section 4 says `de6a50 metric_no_log` s26 to s28 have I1 true and I3 false. In the raw events s28's only carrier is a `frontendservice` span with `is_abnormal=false`, so I1 is false there and the analyzer is right. The `de6a50` labels are s26 S3, s27 S2, s28 S1. The codebook was not edited, its hash is unchanged, and no label changes.
- **Plan labels:** updated to the codebook v1 names in `plan.md` and phases 01, 07 and 08, including the ranking wording ("sorted by k/n descending, then k, with n always shown"). A final grep finds no stale names.
- **Status:** phase-04 and the `plan.md` table row now say completed.

## Concerns
- The report `.md` was refused (see top), so the report content above needs to be saved by the caller.
- `phase-08` has CRLF line endings, as it did before. I replaced text only inside lines and added no new line breaks.
- Nothing was committed or pushed. I left some scratch scripts in the session scratchpad; none are in the repo. The join snippet is in Appendix A of the report content, which I could not save, so it exists only in my scratchpad as `join-labels.py`.
