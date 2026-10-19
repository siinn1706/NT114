# 05 — Evidence-instrument audit, non-LLM baselines, store leakage and RE1 alignment (CPU only)

Phase 06 of `plans/261018-2300-single-llm-simplification-and-evaluation-hardening/`, run on
2026-10-19. No model was called and no GPU was used. Outputs are git-ignored under
`nt114-rca/nt114-rca/`: `results_v2/`, `results_baselines_<ds>/`, `results_baselines_logs/`,
`results_store/`, `results_v7/` and `results_alignment/`.

**Reading rules.** Each rate gives its numerator and denominator. On RCAEval, Nezha and AIOps2025
the test role has one record per injection, so record and injection counts are equal. RCA100 has
86 records over 70 injections, and its AC@1 is injection-weighted. These are observations, not
causal claims. Being named in the evidence is a property of the summary. An unnamed root can
still be ranked first.

## V1 — Did the refactor change any evidence?

**It did not.** All 862 evidence files under `results_visibility/{rcaeval,nezha,rca100,aiops2025}/evidence/`
(361 + 97 + 86 + 318) have the same sha256 as in
`plans/.../reports/evidence-digests-before.txt` (phase 00): 0 of 862 changed. The digests after the
refactor are in `reports/evidence-digests-after.txt`.

Before the store build reused this directory, all 361 RCAEval query files were checked. All 361
still matched their fingerprints, so `prepare` rebuilt none of them.

## V2 — What does each manipulation actually change?

Source: `results_v2/instrument_audit.csv`, built from the visibility JSONL and the evidence files.
Prompt tokens are an estimate: prompt characters / 3, plus 30 (`rca.capacity.prompt_chars`). They
are not tokenizer counts.

**Truncation.** No record in any dataset, role or condition reached the 6,000-character cap (0
truncated records).

**`same_as_full`: evidence text identical to `full`.**

| Dataset, role | blind_root | blind_nonroot | blind_nonroot_ev |
|---|---|---|---|
| RCAEval test | 20 / 69 (29 %) | 62 / 69 (90 %) | 0 / 52 |
| RCAEval DEV | 28 / 54 (52 %) | 48 / 54 (89 %) | 0 / 40 |
| Nezha test | 55 / 97 (57 %) | 81 / 97 (84 %) | 0 / 73 |
| RCA100 test | 83 / 86 (97 %) | 84 / 86 (98 %) | 0 / 7 |
| AIOps2025 test | 46 / 83 (55 %) | 66 / 83 (80 %) | 0 / 41 |

- The span-count-matched control (`blind_nonroot`) leaves the evidence text unchanged in 80–98 %
  of records. For most incidents it is therefore not a manipulation of what the model reads.
- The evidence-matched control (`blind_nonroot_ev`) changes the text in every record where it
  applies. It applies only where `nonroot_ev_target` finds an evidence-matched non-root target.
  On RCA100 that is 7 of 86 records.
- On RCA100, `blind_root` leaves the text unchanged in 83 of 86 records. A `blind_root` contrast on
  RCA100 measures almost nothing. The `require_changed` filter keeps 3 records.
- Single-modality conditions (`no_trace`, `no_log`, `no_metric`, `metrics_only`) never equal
  `full` (0 in every cell).

**Block presence in `full`.**

| Dataset, role | Metrics block | Logs block | Traces block |
|---|---|---|---|
| RCAEval test | 218 / 218 | 108 / 218 | 69 / 218 |
| RCAEval DEV | 143 / 143 | 78 / 143 | 54 / 143 |
| Nezha test | 94 / 97 | 97 / 97 | 97 / 97 |
| RCA100 test | 86 / 86 | 86 / 86 | 86 / 86 |
| AIOps2025 test | 318 / 318 | 304 / 318 | 283 / 318 |

The RCAEval gaps are RE1, which has metrics only. Three Nezha incidents have no Metrics block.

**Size of the summary in `full`.**

| Dataset, role | Named services (median, mean) | Candidates (mean) | Prompt tokens (p50 / p95 / max) |
|---|---|---|---|
| RCAEval test | 10, 9.99 | 31.7 | 810 / 1,409 / 1,819 |
| RCAEval DEV | 10, 8.76 | 29.1 | 653 / 1,062 / 1,507 |
| Nezha test | 10, 12.16 | 26.0 | 956 / 1,466 / 1,585 |
| RCA100 test | 10, 9.51 | 18.0 | 827 / 973 / 1,124 |
| AIOps2025 test | 10, 10.36 | 14.0 | 795 / 1,091 / 1,236 |

The largest estimated prompt in any cell is 1,819 tokens (RCAEval test, `blind_root` and
`blind_nonroot`). `no_metric` shrinks the summary most: the median number of named services falls
to 2 on RCAEval, 4 on Nezha, 0 on RCA100 and 2 on AIOps2025.

## V3 — How strong are the non-LLM baselines?

Command: `python -m rca.baselines configs/exp/baselines-<ds>.yaml` (`--baro` on RCAEval). The
complete grid, with every role, baseline and condition plus `n_no_row`, is in
`results_baselines_logs/table_baselines_combined.csv`. Baselines are defined in
`src/rca/baselines.py`.

**AC@1 on `full`, headline role (test).**

| Baseline | RCAEval (218) | Nezha (97) | RCA100 (86 rec / 70 inj) | AIOps2025 (318) |
|---|---|---|---|---|
| B0 random (analytic) | 0.053 | 0.065 | 0.056 | 0.088 |
| B1 max-z (Metrics block) | 148 / 218 = 0.679 | 20 / 94 = 0.213 | 43 / 86 rec; 0.486 inj-weighted | 54 / 318 = 0.170 |
| B1 logs | 10 / 108 = 0.093 | 14 / 97 = 0.144 | 6 / 86; 0.075 | 102 / 304 = 0.336 |
| B1 traces | 16 / 69 = 0.232 | 20 / 97 = 0.206 | 4 / 86; 0.046 | 99 / 283 = 0.350 |
| B1m evidence order | 148 / 218 = 0.679 | 21 / 97 = 0.216 | 43 / 86; 0.486 | 54 / 318 = 0.170 |
| B3 majority | 8 / 218 = 0.037 (train prior) | 8 / 97 = 0.082 (scored set) | 56 / 86; 0.586 (scored set) | 71 / 318 = 0.223 (scored set) |
| B3 alert-entity | — | — | 32 / 86; 0.374 | — |
| BARO-style (unvalidated) | 116 / 218 = 0.532 | not run | not run | not run |

Each B1 variant is scored only where its block exists. The denominators differ, and the rows
without the block are counted in `n_no_row`. B3 rows labelled "scored set" use the scored
incidents' own label prior (`reference_only`), so they are never comparators. The RCA100 B3
values (0.586 and 0.374) are unchanged by the refactor; `test_rca100_tier_a_protocol_numbers`
passes.

**Observations.**

- **B1m equals B1 max-z wherever a Metrics block exists.** The block comes first, so the two
  rankings start the same. B1m differs only where metrics are missing. On `no_metric` it scores
  15 / 108 (RCAEval test), 20 / 97 (Nezha), 6 / 86 (RCA100) and 114 / 304 = 0.375 (AIOps2025).
- **On AIOps2025, the order of the evidence is a stronger hint without metrics than with them.**
  B1m scores 0.375 on `no_metric`, against 0.170 on `full`, where the metric lines come first.
- **On RCAEval, metric order alone puts the root first in 148 of 218 test incidents (0.679).**
  On DEV it does so in 103 of 143 (0.720). This is the reference an LLM result on RCAEval has to
  be read against.
- **Masking the root's traces collapses the traces-only ranking.** B1 traces goes from 16 / 69 to
  2 / 69 on RCAEval test, from 20 / 97 to 0 / 97 on Nezha, and from 99 / 283 (`full`) to 6 / 83
  (`blind_root`) on AIOps2025. The subsets differ: `blind_root` applies to fewer incidents.

**BARO-style vs B1 max-z on RCAEval** (`results_baselines_rcaeval/table_baro_overlap.csv`). Both
are scored on the same incidents in each row. ΔAC@1 = B1 max-z − BARO-style. The test is a paired
sign-flip, and the CI is a cluster bootstrap over injections.

| Role, condition | n | Top-1 agreement | Top-5 Jaccard | Kendall τ (shared top 5) | ΔAC@1 [95 % CI], p |
|---|---|---|---|---|---|
| test, full | 218 | 96 / 218 = 0.440 | 0.418 | 0.639 | +0.147 [+0.069, +0.225], p = 0.001 |
| test, blind_root | 69 | 17 / 69 = 0.246 | 0.315 | 0.630 | −0.043 [−0.217, +0.130], p = 0.74 |
| test, blind_nonroot_ev | 52 | 15 / 52 = 0.288 | 0.329 | 0.611 | −0.173 [−0.346, 0.000], p = 0.11 |
| DEV, full | 143 | 56 / 143 = 0.392 | 0.420 | 0.606 | +0.336 [+0.238, +0.427], p < 0.001 |

- The two agree on the top-1 service in fewer than half of the incidents. **B1 max-z does not
  stand in for BARO-style** on this evidence; the two rank differently.
- The gap between them is not stable across roles: +0.147 on test and +0.336 on DEV. The roles
  hold different system and fault mixes (grouped split). DEV gaps are not used for any claim.
- Not comparable with the published BARO numbers (research/02, H3). NT114 scores the grouped
  split over RE1–RE3 with `main.py` preprocessing; the paper scores all RE1 incidents with
  `main-ase.py`.

**BARO-style validation (phase 05, task 5a).** Fixtures come from the official
`RCAEval/e2e/baro.py` at `259ea41`, run in an isolated CPU environment. On all 19 fixture inputs,
the NumPy port reproduces the full metric ranking, the service ranking and the scores to within
1e-6. The inputs are 16 DEV incidents covering RE1 (all three systems), RE2 and RE3, plus 3 edge
cases. The baseline keeps the label "BARO-style (unvalidated)" until the owner decides the
renaming.

## V6 — Text-level leakage from the retrieval store

**Setup.**
- `prepare` ran with `configs/exp/store-rcaeval-grouped.yaml` (grouped split
  `within-rcaeval-grouped-0-e9b2c81c`, `retrieval: [hybrid]`). It built 374 train-role store
  files and 361 val and test query files, and exited 0.
- The logged load and build time per store incident had a median of 1.6 s, 0.25 h in total
  (`results_store/rcaeval/prepare_log.jsonl`).
- `python -m rca.leakage_audit` then compared 1,380 query records (val and test, all
  conditions) with the same-system store entries outside the query's split group. Between 102
  and 143 entries were compared per query.
- Outputs are in `results_store/rcaeval/leakage_near_duplicates{.jsonl,_summary.csv}`.

**Results.** In the table, "c" is the TF-IDF cosine of the retrieval tokenizer and "J" is the
Jaccard similarity of the evidence-line sets.

| Role | Condition | n | c ≥ 0.90 | c ≥ 0.95 | c ≥ 0.99 | J ≥ 0.90 |
|---|---|---:|---:|---:|---:|---:|
| test | full | 218 | 97 | 29 | 2 | 0 |
| test | metrics_only | 108 | 26 | 6 | 1 | 0 |
| test | no_log | 108 | 22 | 1 | 0 | 0 |
| test | blind_root | 69 | 12 | 5 | 0 | 0 |
| test | blind_nonroot | 69 | 13 | 4 | 0 | 0 |
| test | blind_nonroot_ev | 52 | 8 | 0 | 0 | 0 |
| test | no_trace | 69 | 5 | 1 | 0 | 0 |
| test | no_metric | 108 | 0 | 0 | 0 | 0 |
| val | full | 143 | 74 | 31 | 3 | 0 |

- **Test, `full`:**
  - Max cosine: median 0.890, 90th percentile 0.962, maximum 0.997.
  - Max Jaccard: median 0.13, 90th percentile 0.30, maximum 0.455.
  - No query reaches J ≥ 0.90 in any role or condition.
  - So the high cosines come from a shared vocabulary (the same system's metric and service
    names). They do not come from copied evidence lines.
- **`no_metric`:** maximum cosine 0.856. This is expected, because the store holds `full`
  evidence.
- **Nearest-same-cell share is 0.0 in every row. This holds by construction, not as a
  finding.** On this split, each of the 127 (root, fault) cells belongs to exactly one split
  group (735 incidents, 91 groups). Excluding the query's group therefore removes every
  same-cell entry. So the store cannot hand the model a precedent with the query's own
  (root, fault) pair.
- **Same root service, other fault: reachable** (added 2026-10-19; same run, same similarities,
  so the columns above are unchanged).
  - The split's cell is system / root service / fault family. Removing the query's group therefore
    leaves the store entries that share its root service under another fault.
  - The scored label is the root service.
  - The audit now reports, per query:
    - whether such an entry is reachable;
    - whether the nearest entry (by cosine) has the query's root;
    - whether one of the 3 nearest has it (`top_k` = 3 in every experiment config).
  - Next to each count is the number expected if entries were picked without regard to
    similarity: the sum, over queries, of the share of reachable entries with the query's root.
    For the top 3, the per-query chance is 1 − C(n − m, 3) / C(n, 3), where n is the number of
    reachable entries and m the number with the query's root.

  | Role | Condition | n | Same root reachable | Nearest has root (expected) | Top 3 has root (expected) |
  |---|---|---:|---:|---:|---:|
  | test | full | 218 | 218 | 67 (36.0) | 111 (89.1) |
  | test | blind_root | 69 | 69 | 29 (11.0) | 46 (27.7) |
  | test | blind_nonroot_ev | 52 | 52 | 27 (8.4) | 36 (21.0) |
  | test | metrics_only | 108 | 108 | 19 (17.0) | 45 (42.5) |
  | test | no_log | 108 | 108 | 36 (17.0) | 64 (42.5) |
  | test | no_metric | 108 | 108 | 24 (17.0) | 51 (42.5) |
  | val | full | 143 | 134 | 37 (19.7) | 59 (50.1) |

  - Test `full`, split by the query's max cosine, gives the nearest-has-root count (expected):
    - < 0.90: 44 of 121 (20.5);
    - 0.90–0.95: 12 of 68 (10.3);
    - ≥ 0.95: 11 of 29 (5.1).
  - These are observations about what the store makes reachable. They say nothing yet about
    whether the model uses it.

**Verdict.**
- **No line-level copying:** no query reaches J ≥ 0.90.
- **Same cell: excluded by construction.** No precedent with the query's own (root, fault) is
  reachable.
- **Same root: reachable. This is a property of the retrieval regime, not a finding of leakage.**
  - The grouped split holds out fault cells, not root services. Precedents labelled with the
    query's root under another fault are legitimate training precedents under this protocol.
  - Every test query can reach one.
  - Similarity ranks them above chance: the nearest has the query's root in 67 of 218 test `full`
    queries against 36.0 expected.
  - The excess is larger under `blind_root`: 29 of 69 against 11.0. So, under `blind_root` with
    retrieval, the precedents shown can still name the masked service. Whether the model uses
    that is an outcome question for the analysis, not something this audit shows.
- **Near-duplicates across cells.** 29 of 218 test `full` queries (13 %) have a store entry with
  cosine ≥ 0.95, and 2 have one ≥ 0.99. These neighbours belong to other cells, and 11 of the
  29 share the query's root.
- **Consequence for reporting.** Any retrieval effect is reported:
  - stratified by the query's max cosine (< 0.90, 0.90–0.95, ≥ 0.95);
  - with the evaluation-only covariate "the top 3 hold the query's root".

  A retrieval gain then cannot rest unseen on near-identical neighbours or on same-root labels.
  Both can also *hurt*: a near-identical neighbour can carry a different label, and a same-root
  precedent can carry the wrong fault.
- **Where the covariate is reported.** `rca.analyze` writes `table_cells_by_precedent_root`: the
  retrieval cells split by the grid's `hit_has_truth` flag, with records, injections and outcomes
  per stratum.
  - The flag is computed after retrieval and after the model call.
  - It is used only by this evaluation-only table.
  - No prompt, retrieval selection, cache key, confidence score or threshold reads it.
- **The split is not changed.** A root-held-out split is deferred. It would be a separate
  experiment, run only if the literature review justifies it. An aggregate retrieval contrast
  without this stratification is exploratory.

## V7 — Does the simplified pipeline run end to end and reproduce?

This is a plumbing check only. Mock-LLM outputs are not results.

- **Synthetic mock chain.** `tests/test_reproduce.py` runs `prepare`, `run` with the mock LLM,
  `analyze` and `reproduce` with sockets disabled. `reproduce` exits 0. After a one-row edit it
  exits 1 and names `table_cells`. Pass.
- **Real slice.** Nezha, 97 incidents, mock LLM, evidence reused (`configs/exp/v7-nezha-mock.yaml`,
  `configs/analysis/v7-nezha-mock.yaml`). `run`, `analyze` and `python -m rca.reproduce
  results_v7/nezha/analysis` all succeed: "all 8 tables reproduced", exit 0. A mock-vs-B1m
  contrast confirms that baseline rows can enter a paired contrast with LLM rows. Pass.

## V8 — RE1 alignment with the decomposition paper

**Step 1 (inside NT114)** writes `results_alignment/re1/re1_inventory.jsonl` with
`python -m rca.alignment inventory results_alignment/re1`. Results:

- 375 RE1 incidents: 125 Online Boutique, 125 Sock Shop, 125 Train Ticket.
- In 375 of 375, `inject_time.txt` equals the canonical anchor.
- The raw `data.csv` fingerprints are 375 distinct sha256 values.

The paper also evaluates 125 incidents per system (Appendix B). Equal counts are not a
match.

**Step 2 has not run.** The release the paper's abstract names
(https://github.com/cruiseresearchgroup/DecompRCA) returned HTTP 404 on 2026-10-19, both from the
web and from the GitHub API (`results_alignment/re1/provenance.json`). With no release to inspect,
there are no incident identifiers or fingerprints to compare. **No paper-level alignment is
claimed.** The comparator is ready (`python -m rca.alignment compare`, `tests/test_alignment.py`).
A match requires the same system, injection timestamp and raw fingerprint; a partial match is
listed with the key that failed.

## Unresolved questions

1. Should `blind_nonroot` be retired in favour of `blind_nonroot_ev`? The former leaves the
   evidence unchanged for 80–98 % of records.
2. Can RCA100 keep `blind_root` as a condition? The text changes in only 3 of 86 records.
3. Should BARO-style be relabelled "BARO-style", or called B2, now that the fixture tests pass?
   This is the owner's decision.
4. Should a `main-ase.py`-faithful variant (raw `_latency-50` and `_latency-90` kept) be added,
   so the paper's preprocessing can be matched?
5. When, if ever, will the DecompRCA release become public? V8 step 2 depends on it.
6. Is BARO-style meaningful on Nezha, RCA100 and AIOps2025? Their metric frames are bucketed
   long-format tables, and the reference preprocessing was validated on RCAEval only.
7. Should the similarity strata of V6 be fixed in the preregistration before any retrieval run?
   The cut points 0.90 and 0.95 here are descriptive, not tuned. Should the audit also run for
   Nezha, RCA100 and AIOps2025, whose grouped stores have not been built?
