---
title: "Phase 3: Evaluation core — confidence registry, selective evaluator, paired-contrast engine"
status: todo
priority: P1
effort: 4-5 d
dependencies: [phase-02]
---

# Phase 3: Evaluation core

## Context

[Scout report §2](research/scout-report.md#2-evaluation-gaps-found-while-scouting): no paired
contrast is implemented. The only paired test is an unclustered McNemar. Only AC@1 has a CI.
`excluded_from_primary` is never applied. Two analysis paths disagree. The old statistical plan
([research-design §9](../261015-0047-nt114-rca-llm-jev-research-and-implementation/design/research-design.md))
remains the methodological target: the injection as unit, paired cluster bootstrap with
B = 10,000, sign-flip for decomposable endpoints, and Holm within a declared family.

## Goal

One analysis entry point. Given grids (mock now, real later), it produces every table H1, H2 or
H3 would need, with correct units and uncertainty. It implements none of their methods.

## Requirements

### 1. Confidence registry — `src/rca/confidence.py` (new)

Each score is declared with:

- a name;
- an orientation (higher means more confident);
- its discrete support, or `continuous`;
- whether it needs `llm_raw.jsonl`.

Every score is computed only from the same model's call on the same cell:

| Score | Source | Note |
|---|---|---|
| `consensus` | grid `conf_consensus` | 11 levels at n = 10 |
| `verbal` | grid `conf_verbal` | – |
| `verbal_agreement` | −`conf_verbal_sd` | – |
| `not_insufficient` | 1 − `abstain_vote` | – |
| `borda_margin` | raw parsed samples | Normalised gap between the top-two Borda totals |
| `vote_entropy` | raw parsed samples | 1 − normalised entropy of the top-1 votes |
| `token_prob` | raw logprobs | Mean log-probability of the tokens of `ranking[0]` in each sample, averaged over samples. NaN when the model ran without `logprobs: true`. The tokens are located by re-parsing the JSON text; locating them is unit-tested on fixtures. **Requires real-model validation:** the registry marks it `validated: false`, and `analyze` writes it only to exploratory tables until a DEV run checks token alignment and its error-detection value |

The registry joins `llm_raw.jsonl` to the grid on `key`. A grid row without a raw record gets
NaN for the raw-only scores and is counted, never dropped silently.

### 2. Selective evaluator — `src/rca/selective.py` (extends phase 02)

- **Risk–coverage curve** for any registry score. Ties are answered together, and weights are
  injection weights. Outputs are AURC, selective risk at coverage 0.5, 0.7 and 0.9, and the
  coverage at a target risk.
- **DEV-fit transfer.** A threshold is fitted on `split_role == val` rows for a target coverage
  or a target risk, then applied unchanged to test. The test table reports the target, the
  realised coverage and the realised risk with a cluster-bootstrap CI, next to the test-oracle
  curve point. This is the generic C3. Conformal or risk-control variants are a later plug-in.
  They take the same function signature and are not implemented here.
- **References:**
  - L1: the LLM's own flag, `abstain_vote ≥ 0.5`;
  - C2: random deferral, whose risk is analytic and equals the base error at any coverage;
  - O: the oracle, for analysis only.
- **Arm selection.** The evaluator can evaluate a **given** per-incident choice among cached
  cells of the same model: `answer` from cell A, `answer` from cell B, or `abstain`. Cost
  accumulates along a declared path. This is the hook that H2 needs later. It ships with fixed
  and random controls only.
- **Shift table.** It compares DEV and test by system × fault family: n, base error and the
  share of each confidence level. It is reported with every DEV-fit result.

### 3. Paired-contrast engine — `src/rca/contrasts.py` (new)

A contrast is declared in config, not in code. Examples:

```yaml
contrasts:
  - {name: drop_blind_root, a: {condition: full}, b: {condition: blind_root}, metric: ac1}
  - {name: did_root_vs_nonroot_ev, kind: did, a: {condition: full}, b: {condition: blind_root},
     c: {condition: full}, d: {condition: blind_nonroot_ev}, metric: ac1}
  - {name: auroc_consensus_vs_verbal, a: {score: consensus}, b: {score: verbal}, metric: auroc,
     within: {condition: full}}
families: {}            # filled from the preregistration; empty -> every p-value is unadjusted and labelled exploratory
```

How a contrast is computed:

- It restricts to the **intersection** of incidents where every arm exists. It reports n
  incidents, n injections, and the incidents dropped per arm with reasons.
- Optional filters are `require_changed: true` (drop incidents where the manipulated variant
  has `same_as_full`), `named`, and any stratum column. The unfiltered and filtered results are
  both written.
- **Decomposable metrics** (AC@1, AC@3, gap, Brier) are aggregated per injection, using
  `metrics.per_injection`. The output is a cluster-bootstrap CI and a sign-flip p, using
  `metrics.sign_flip_test`.
- **Non-decomposable metrics** (AUROC, AURC, selective risk at a coverage) use the paired cluster
  bootstrap, resampling the same injections for both arms.
- Holm is applied within each declared family only.

**Assumptions the engine states in every output table.** Each table carries an `assumptions`
column, or a header in its sidecar JSON, that names the assumption each test relies on:

| Method | Used for | Assumption | How it is checked or disclosed |
|---|---|---|---|
| Paired sign-flip permutation test | Decomposable endpoints (ΔAC@k, DiD, Δgap, ΔBrier), per-injection differences | Injections are independent. Under H0 each per-injection difference is symmetric about 0 (exchangeable signs). It tests a zero mean only under that symmetry | The skewness of the per-injection differences is reported. Phase 06 V4 measures type-I error on simulated nulls that have the real cluster structure |
| Percentile paired cluster bootstrap | CIs for every endpoint; p-values for non-decomposable endpoints (ΔAUROC, ΔAURC, Δselective risk) | Injections are i.i.d. draws from a population of injections. There are enough clusters (each dataset's count is reported). The statistic is smooth enough for the percentile method. The p-value is the two-sided share of draws across 0 | V4 checks coverage per dataset. If coverage falls outside [0.93, 0.97], the table is marked, and BCa or a studentised interval is evaluated before any GPU work |
| Exact McNemar on `representative` records | Sensitivity only | One record per injection; discordant pairs are binomial | Never a headline test |
| Holm | Multiplicity within a declared family | Valid under arbitrary dependence; it controls FWER only within the family declared in the preregistration | Families are empty until the literature review. All p-values are unadjusted and labelled exploratory until then |
| Analysis on the intersection | Every paired contrast | Arm availability depends on labels (for example, `blind_root` needs the root to have spans), so it is not missing at random | The estimand is stated as "on the applicable intersection". Per-arm drop counts are reported, and no extrapolation to all incidents is claimed |
| Censored ranks | Rank endpoints | Rank > 5 is unknown (`n_candidates + 1` in the grid is a sentinel, not a value) | Only AC@1–5 and MRR@5 are computed. A test fails if any table contains an uncensored mean rank |
| DEV-fitted thresholds | Selective transfer | DEV and test share the conditional error distribution; known to be false in some strata | The shift table, and realised test risk next to the target |
| Sampling | All | n = 10 samples at T = 0.7 from one fixed model; sample variance is folded into each incident's outcome | Seeds and the sampling configuration come from the manifest |

### 4. Analysis entry point — `src/rca/analyze.py` (rewrite)

- Run as `python -m rca.analyze <analysis.yaml>`. The config names:
  - the grid file(s);
  - the optional visibility JSONL;
  - the optional baselines JSONL;
  - the `data_home`;
  - the contrasts and families;
  - `preregistration_sha` (optional).
- It writes the following tables:
  - `table_cells` (weighted, with a CI on **every** metric: AC@1 to AC@5, MRR@5 (censored), Brier, gap, ECE support,
    AUROC, AURC);
  - `table_confidence`;
  - `table_selective`;
  - `table_contrasts`;
  - `table_shift`.
- `excluded_from_primary` removes records from headline tables and is reported as a count.
- **Headline guard.**
  - The existing checks stay: mock rows, DEV rows, mixed `prompt_version`.
  - New refusals: mixed `model_revision` within one model, mixed `server_fp` within one model,
    any `oracle_store` row, and mixed evidence builder fingerprints.
  - Without `preregistration_sha`, every file gets the prefix `exploratory_`, whatever else holds.
- The visibility flags (`named`, `in_candidates`, `same_as_full`) are joined as strata when they
  are given. The join lives in the eval-only zone. No model-facing module imports `analyze`,
  `confidence`, `contrasts` or `selective`. `tests/test_confidence.py` asserts this, so
  `tests/test_leakage.py` stays owned by phase 05.
- The legacy `cell_table` and `retrieval_tests` are removed. Exact McNemar on `representative`
  records stays as a sensitivity column in `table_contrasts`.

### 5. Statistics checks — `tests/test_contrasts.py`, `tests/test_confidence.py`, `tests/test_selective.py`

- **Known values.** Check AUROC and AURC on hand-computed toy data, with ties included.
  Check Holm against a textbook example.
- **Pairing.** A contrast on arms with different applicability uses only the intersection. A
  test plants an incident present in one arm only and checks that it is reported as dropped.
- **Simulation** (fast in CI; the full version runs in phase 06):
  - clustered binary data with RCA100-like structure, 70 clusters with up to 4 records each;
  - the nominal 95 % CI must cover the true difference in [0.93, 0.97] of 400 replications;
  - under the null, sign-flip rejection at α = 0.05 must be ≤ 0.07.
- **Guards.** A mock row, an oracle row or mixed revisions refuse a headline table. A missing
  `preregistration_sha` gives the `exploratory_` prefix.

## Files

| Action | File |
|---|---|
| Create | `src/rca/confidence.py`, `src/rca/contrasts.py`, `tests/test_confidence.py`, `tests/test_contrasts.py`, `configs/analysis/example-mock.yaml` |
| Modify | `src/rca/selective.py`, `src/rca/analyze.py`, `src/rca/metrics.py` (helpers only; no behaviour change to existing functions), `tests/test_selective.py`, `tests/test_stats.py` |

## Verification

- `pytest tests/test_confidence.py tests/test_contrasts.py tests/test_selective.py tests/test_stats.py -q`
  passes, then the full non-realdata suite passes.
- `python -m rca.analyze configs/analysis/example-mock.yaml` on the phase-02 mock grid writes
  the five `exploratory_` tables and exits 0. With a mock row and a fake
  `preregistration_sha`, it exits with the `HeadlineGuardError` message.

## Risks

- **`token_prob` alignment** between the JSON text and the tokens is fragile. It is optional and
  NaN when unsupported. It is fixture-tested only and flagged `validated: false`. It needs
  real-model validation on DEV (token alignment on real vLLM output, then its AUROC against
  consensus) before it may enter a headline or confirmatory table.
- **Bootstrap cost** (B = 10,000 × many cells) on CPU. The draws are vectorised over clusters,
  `n_boot` is configurable, and the smoke configs use 200.
