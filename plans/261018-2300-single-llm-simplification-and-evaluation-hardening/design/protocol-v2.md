---
title: "Protocol v2: single-LLM measurement protocol (skeleton)"
status: draft
created: 2026-10-18
supersedes: "../../261015-0047-nt114-rca-llm-jev-research-and-implementation/design/research-design.md §2, §5, §7 (Jev parts)"
---

# Protocol v2 (skeleton)

This file fixes **what is measured and how**, not what is hypothesised. The confirmatory family,
the hypotheses, their directions and the MDE targets are open slots, filled only after the
literature review (`/research/03_elicit_search_pack.md`) and frozen in a preregistration whose
sha256 the analysis config must carry (`preregistration_sha`). Without it, every table is written
with an `exploratory_` prefix.

## 1. Single-LLM invariant

- Every reported answer comes from one model's single call (n samples) on one cell
  (incident × condition × retrieval arm).
- Every abstention is a deterministic rule on that same call's outputs. A rule may be fitted on
  DEV labels at most, and is frozen before test.
- No answer is replaced by, or gated on, another model's output. There is no judge, decision
  model or escalation model.
- Retrieval is a fixed experimental arm (`retrieval: [none, hybrid]`), never chosen per incident by
  a model. A "retrieve" action in the selective evaluator means "take the cached retrieval cell of
  the same model".
- Model sweeps (sampling variants, an optional cross-family replication) are independent runs of
  the same pipeline. No prediction depends on another run.

## 2. Measurement endpoints (hypothesis-independent)

| Group | Endpoints | Notes |
|---|---|---|
| Accuracy | AC@1, AC@2, AC@3, AC@4, AC@5 (exact); MRR@5 | Prompt `v1` returns at most 5 ranked services, so ranks beyond 5 are **right-censored**. A censored rank contributes 0 to MRR@5. No exact mean rank or uncapped MRR is ever reported. Parse failures count as wrong and are tabulated separately |
| Confidence quality | Brier; ECE on the discrete support (consensus: 11 levels at n = 10) plus 10 equal-width bins for verbal; overconfidence gap (mean confidence − accuracy); AUROC and AUPRC for error detection (positive = wrong, ties 0.5) | One row per confidence estimator in the registry (phase 03). Token probability is exploratory until validated on real-model DEV output |
| Selective | Risk–coverage curve; AURC; selective risk at coverage 0.5, 0.7, 0.9; coverage and risk of L1 | DEV-fit thresholds are reported next to the test-oracle curve and with a stratified shift table |
| Cost | Prompt, completion and total tokens per incident; tokens per sample; LLM latency (cached share flagged); retrieval seconds; preparation seconds; end-to-end per incident along any declared arm path | GPU-seconds stay NaN until a GPU run records them |
| Validity strata | dataset; label granularity; condition; modality regime (natural metrics-only vs multimodal); coverage cause; `named` (root named in the evidence); `same_as_full` (manipulation changed nothing) | `named` is a stratum, never an "unanswerable" label: an unnamed root can still be ranked first |

AIOps2025 set-scored incidents form a separate table and are never pooled with top-1 incidents.

## 3. Statistical conventions

- The injection is the independent unit. Records carry `weight = 1/records of the injection`.
- Paired contrasts use the intersection of incidents where both arms apply. An estimate holds
  for that intersection only and is reported as such. A `require_changed` filter (drop incidents
  whose manipulated evidence equals `full`) is reported next to the unfiltered version.
- Intervals: paired cluster bootstrap over injections, B = 10,000, percentile 95 % CI, seed from
  the config. Every reported metric carries a CI.
- Tests: paired sign-flip permutation test (10,000 draws) for endpoints that decompose per
  injection; the cluster bootstrap otherwise. Holm correction within declared families only.
- Calibration (2026-10-19, [research/06](../../../research/06_statistics_validation.md#v4--calibration)):
  on every test structure, CI coverage is 0.930–0.955 and sign-flip type-I is 0.025–0.041.
  Retrieval contrasts are reported stratified by the query's max store cosine
  ([research/05 §V6](../../../research/05_evidence_instrument_audit.md#v6--text-level-leakage-from-the-retrieval-store)).
- Datasets are never pooled in headline tables.
- DEV (grouped val) is never reported as a result.
- Assumptions are listed in [plan.md](../plan.md#statistical-assumptions-summary-details-in-phase-03)
  and carried in every contrast output.

## 4. Comparators v2

| ID | Arm | Status | Labels? |
|---|---|---|---|
| B0 | Random ranking (1/\|C\|, analytic) | kept | no |
| B1 | Max-z metric heuristic, per modality as well | kept | no |
| B1m | Evidence-order baseline: services in the order the evidence text lists them | **new** (the evidence lists services in z-score order, so the LLM can copy it) | no |
| B2 | BARO-style (pure NumPy) | **conditional**: labelled "BARO-style" until the equivalence tests against the official implementation pass (phase 05); its overlap with B1 is reported | no |
| B3 | RCA100 majority class and alert entity | kept; the majority uses the **train** prior, not the scored set's | train labels |
| L0 | LLM, always answer | kept (main baseline) | no |
| L1 | LLM self-abstention (`abstain_vote ≥ 0.5`) | kept | no |
| C1 | Coverage-matched confidence threshold | kept, as a point on the risk–coverage curve | no |
| C2 | Coverage-matched random deferral (analytic + draws) | kept | no |
| C3 | Confidence threshold fitted on DEV, answer/abstain only | redefined | DEV labels |
| O | Oracle | kept (analysis-only upper bound) | yes |

Retired, with reasons:

| ID | Reason |
|---|---|
| J, J-AA, J-floor | Jev is removed (second model) |
| L2 | Escalation model removed (second model) |
| R1, R2 | Route-matched controls existed only to isolate Jev's routing |
| C4 | The learned cost-sensitive policy is itself a second decision model; under the invariant only fixed rules on the LLM's own outputs remain |

## 5. Experiment matrix v2

| ID | Experiment | Status |
|---|---|---|
| E1 | LLM-only missingness grid (all applicable conditions, incl. `blind_nonroot_ev`) | kept |
| E2 / E2b | Retrieval arm (novel-fault grouped split; recurring-fault regime) | kept |
| E6 | Non-LLM baselines B0, B1, B1m, B2 (conditional), B3 | kept, extended |
| E7 | Cross-family replication | **optional**, outside the minimum paper; the main study uses one fixed LLM |
| E3 | Escalation arm | retired (second model) |
| E4 | Jev decisions | retired |
| E5 | Jev comparators (Jev part) | retired; C1–C3 and O move to the selective evaluator |
| E8 | Jev robustness | retired |
| — | Full-ranking prompt arm | candidate for after the literature review (mainly for H3); not planned |

Old optional extensions: O1 (thinking mode), O2 (BM25/dense), O6 (answer-token probability, now
the `token_prob` estimator pending validation) and O7 (second sampling seed) remain candidates.
O4, O10 (Jev) are retired. O3 (`no_precedent`) remains with E2b. O5, O8 and O9 are unchanged and
out of scope here.

### 5.1 Measured instrument facts (2026-10-19, CPU only)

These figures come from [research/05](../../../research/05_evidence_instrument_audit.md) and
[research/06](../../../research/06_statistics_validation.md). They constrain E1 and E2 before any
model is run.

- **Manipulation check.** This is the share of records whose `full` evidence text is unchanged by
  the condition (test role):
  - `blind_nonroot` is unchanged in 80–98 % of records. It is not a manipulation for most
    incidents.
  - `blind_nonroot_ev` changes the text in every record it applies to.
  - RCA100 `blind_root` is unchanged in 83 of 86 records, which leaves 3 records after
    `require_changed`.
  - The single-modality conditions never equal `full`.
- **Measured intersections (test).**

  | Set | Records | Injections |
  |---|---:|---:|
  | RCAEval `full` | 218 | 218 |
  | RCAEval `blind_root` ∩ `blind_nonroot_ev` | 52 | 52 |
  | Nezha `full` | 97 | 97 |
  | RCA100 `full` | 86 | 70 |
  | AIOps2025 `full` | 318 | 318 |

- **MDEs.** The paired AC@1 MDE at 80 % power, assuming 20 % discordance, is:
  - RCAEval `full` 0.10;
  - the `blind_root` ∩ `blind_nonroot_ev` intersection 0.18 (not reachable at 10 %);
  - Nezha 0.14, RCA100 0.16, AIOps2025 0.08.

  The full table is in research/06. The discordance rates are placeholders until a DEV pilot.
- **Retrieval store (RCAEval grouped).**
  - There is no line-level copying: the max Jaccard is 0.455.
  - No same-cell (root, fault) entry is reachable, by construction of the split.
  - A same-root entry under another fault is reachable for every test query. The split's cell
    includes the fault family.
    - Its nearest store neighbour has the query's root in 67 of 218 test `full` queries (36.0
      expected without regard to similarity).
    - Under `blind_root` it does in 29 of 69 (11.0 expected).
  - 29 of 218 test `full` queries have a cross-cell neighbour with cosine ≥ 0.95.
  - E2 is therefore reported stratified by max cosine, with the evaluation-only covariate "the
    top 3 hold the query's root". It is reported in `table_cells_by_precedent_root`, from the grid's
    `hit_has_truth` flag.
  - That covariate describes the retrieval regime of the grouped split. It is not a leakage
    finding, and no prediction, confidence score or threshold uses it.
  - Any `blind_root` × retrieval cell is read with it.
  - A root-held-out split is deferred to a separate experiment, conditional on the literature
    review. The existing splits are kept.

## 6. Research questions: what remains

Old hypotheses H1a, H1b (accuracy under `blind_root`), H2a, H2b (overconfidence gap) and H3a,
H3b (confidence as an error detector) are kept as **candidate contrasts**. They are not committed
to, and no direction is asserted here. H4a, H4b, H4c (Jev deferral) and H5 (Jev routing) are
retired with Jev. RQ6 (fine-tuning) is unchanged and out of scope.

## 7. Risk

The old paper's main contribution (RQ4: Jev as a post-LLM safety layer) is gone. The novelty of
whatever replaces it (H1, H2 or H3 in `/research/02_research_directions.md`) is **UNVERIFIED
UNTIL LITERATURE REVIEW**. For H3, the decomposition paper listed in
[plan.md](../plan.md#critical-prior-work) already exists, so novelty in the decomposition itself
cannot be claimed.

## 8. Accounting against the old design

| Old item (research-design.md) | v2 |
|---|---|
| §2 RQ1–RQ3, H1a–H3b | candidate contrasts (§6) |
| §2 RQ4, H4a–H4c; RQ5, H5 | retired |
| §2 RQ6 | unchanged, out of scope |
| §5 B0, B1, B3, L0, L1, C1, C2, O | kept (§4) |
| §5 B2 | conditional BARO-style |
| §5 C3 | redefined |
| §5 J, J-AA, J-floor, L2, R1, R2, C4 | retired (§4) |
| §7 E1, E2, E6 | kept; E2b kept |
| §7 E7 | optional |
| §7 E3, E4, E5 (Jev part), E8 | retired |
| §7 O1–O10 | §5 |
| §8 Avg@5, mean rank | replaced by AC@1–5 and MRR@5 (censored) |
| §8 CWA₁₀₀, Jev cost | CWA₁₀₀ uses the answering cell's own confidence; Jev cost retired |
| §9.5 confirmatory family | open slot |
| §9.6 MDE table | replaced by the V5 table in [research/06](../../../research/06_statistics_validation.md#v5--minimum-detectable-effects) (2026-10-19; the discordance rates stay placeholders until a DEV pilot) |

## 9. Addendum 2026-10-19: selective endpoints, calibration source and pools (accepted by the owner 2026-10-19)

Implemented by plan [261019-1800](../../261019-1800-review-findings-fixes-and-research-readiness/plan.md)
(phase 05); `analysis_meta.json["selective_ties"]` carries the tie rules below.

- **Fixed coverage, two tie rules.** `risk@c` answers whole tie groups (achieved coverage ≥ c,
  reported as `coverage_ties@c`). `risk_exact@c` answers exactly c of the weight, with the boundary
  tie group answered fractionally; this is the expected risk of C1's seeded random tie-break.
  `gain_exact@c` = base error − `risk_exact@c` is the contrast with C2 random deferral.
  `gain_AURC` = base error − AURC.
- **DEV-fit transfer (source → target).** A threshold is fitted on the DEV (val) rows of the
  target's own stratum (dataset, label granularity, set-scored, model, condition, retrieval, store
  mode) and applied unchanged to that test cell. Each `dev_fit` row records `source_split_role`,
  `source_stratum`, `n_dev_records` and `n_dev_injections`, plus the achieved test coverage and risk
  with CIs. A stratum without DEV rows gets a `no_source` row with no threshold; it is never fitted
  on pooled DEV data.
- **Pools are declared, never implicit.** `selective.pools` in the analysis config
  (`{name: {column: [values]}}`) adds a cell `column = pool:<name>`. The pool is formed the same way
  on DEV (source) and test (target). Within the pooled cell, weight = 1 / (records of the injection),
  so every injection weighs 1. The H1-primary pool is
  `single_modality: {condition: [no_metric, no_log, no_trace]}` on RCAEval with `retrieval = none`
  (declared in `configs/analysis/dev-pilot.yaml`; 78 injections / 210 records on DEV, 108 / 285 on
  test).
- **CIs.** Every selective, reference and confidence endpoint carries a cluster-bootstrap CI over
  injections. When a statistic is undefined in some draws, those draws are ignored and their share
  is reported as `<metric>_nan_draws`.
- **Shift table.** It is stratified by the same strata (pool cells included) × system × fault ×
  split role. Base error and confidence-level shares are injection-weighted.
