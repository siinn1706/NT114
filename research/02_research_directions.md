# 02 — Three candidate research directions: feasibility on this repository

Path convention as in [00](00_repo_audit.md). Effort figures marked **[A]** are this audit's
assumptions, not measurements. GPU throughput on the 12 GB laptop has never been measured
(`/plans/.../decisions.md:36`).

> **Every research-gap statement in this file is UNVERIFIED UNTIL LITERATURE REVIEW.** The
> earlier survey excluded conference papers and arXiv
> (`/plans/261011-1345-aiops-q1-literature-gap/work/q1-protocol.md:25`). No direction is claimed
> to be novel.

> **Update 2026-10-19.** The owner removed Jev, escalation and the separate decision layer
> (`/plans/261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md`). The system is now single-LLM. Rows below that cite `src/rca/decide.py`,
> `src/rca/jev.py` or `src/rca/gate.py` describe the audited commit; those files are deleted and
> recoverable from the git tag `pre-single-llm`. Statements the change or the phase-06 CPU
> measurements alter carry an inline dated update. The measurements are in
> [05](05_evidence_instrument_audit.md) and [06](06_statistics_validation.md).

## Executive summary

| | H1 uncertainty, selective prediction, abstention under missing telemetry | H2 budget-aware adaptive evidence acquisition | H3 candidate-generation vs candidate-ranking failures |
|---|---|---|---|
| Fit with the current code | Highest. It **is** the current plan's RQ1–RQ4 | Medium. Offline simulation is possible from the existing condition grid | Medium to high. Mostly an eval-only analysis on top of the H1 grid, plus one oracle arm |
| Extra GPU beyond the planned E1 grid | Small (a second confidence signal needs re-runs only if logprobs are wanted) | **None** for the smallest version | Small (one oracle-shortlist arm, about 300 prompts **[A]**) |
| Engineering effort **[A]** | 2–4 days | 3–5 days | 2–4 days |
| Main validity risk | Literature overlap; discrete consensus; weak `blind_root` | "Acquisition" means revealing pre-collected data, and token cost stands in for collection cost | Findings are tied to this heuristic summariser; the top-5 output cap hides ranks |
| Depends on Jev (owner decision D1)? | Yes, as planned. *Update 2026-10-19: D1 is reversed; Jev was removed, and H1 abstention is a fixed rule on the same call's outputs* | No. D1 says Jev stays the mandatory post-LLM layer, so a pivot must keep Jev or reopen D1 with the owner. *Moot 2026-10-19 (D1 reversed)* | No (same note) |

All three directions share the same blocker. There is no real-model grid yet, and H2 and H3 both
consume the E1 grid that H1 needs anyway. One reading of the evidence: H2 and H3 can be added as
analyses of the same DEV/E1 runs at low extra cost, so the decision tomorrow is mainly about the
**paper's framing and baselines**, not about separate engineering tracks. Whether any framing is
publishable depends on the literature review in [03](03_elicit_search_pack.md).

---

## H1 — Missing telemetry, uncertainty estimation, selective prediction and abstention

**What the repository already does.** Controlled missingness, LLM confidence signals,
risk-coverage evaluation and an external deferral model, with coverage-matched controls
(`/plans/.../design/research-design.md:27-33`).

**Reusable modules**

- Missingness: `src/rca/ablate.py:19-63`, the condition matrix, and `blind_nonroot_ev`
  (`src/rca/run_grid.py:212-226`).
- Confidence signals: verbal, consensus, sample SD of verbal, abstain vote and parse rate
  (`src/rca/llm.py:206-227`). The self-abstention instruction is in the prompt
  (`src/rca/llm.py:27-28`).
- Selective metrics: Brier, support-ECE, AUROC/AUPRC, weighted AURC and selective risk at a given
  coverage (`src/rca/metrics.py:98-190`); cluster bootstrap and sign-flip test (`:204-242`).
- Policies and controls: L0, L1, C1, C2, R1, R2, O (`src/rca/analyze.py:110-139`;
  `src/rca/gate.py:238-299`); Jev stages (`src/rca/decide.py`). *Update 2026-10-19: `decide.py`, `gate.py`, `jev.py` and the Jev stages are deleted; R1 and R2 are retired. L1, C2, O and the DEV-fit thresholds now live in `src/rca/selective.py`, and confidence scoring in `src/rca/confidence.py`.*
- Natural missingness strata: coverage causes (`docs/data_contract.md:190-193`) and RE1 as
  naturally metrics-only.

**Missing interfaces, data and labels**

- Persistence of raw completions and token logprobs: added 2026-10-18, uncommitted. Completions
  and parsed outputs go to `llm_raw.jsonl` and the cache value. Logprobs are recorded only when a
  model sets `logprobs: true`. A token-probability confidence estimator itself is still missing.
- Recalibration fitted on DEV (DOCUMENTED_ONLY).
- A conformal or risk-control threshold with a finite-sample guarantee (MISSING). Whether this is
  standard for LLM-RCA is UNVERIFIED.
- An explicit "missingness-aware" confidence: for example, conditioning the threshold on the
  `has_*` features, which already exist (`src/rca/evidence.py:226-227`). There is no code for it.
- A label for "should abstain". The current target is wrong@1 (`src/rca/metrics.py:165-169`).
  Evidence omission (`named = false`, from `src/rca/visibility.py`) is a useful stratum for this,
  but it is **not** an "unanswerable" label: an unnamed root can still be ranked first (see H3).

**Smallest valid experiment**

- Set: RCA-T multimodal subset (108 incidents; 69 with `blind_root`), with DEV (143) for any
  tuning (`/plans/.../design/research-design.md:130-132`).
- Conditions: `full`, `metrics_only`, `blind_root`, `blind_nonroot_ev`. Primary model only;
  n = 10, T = 0.7; no retrieval and no Jev.
- Comparison: consensus vs verbal as error detectors (AUROC, paired cluster bootstrap), and
  selective risk at coverage 0.7 and 0.9, all **within condition and paired across conditions**.
- Size **[A]**: about 350 prompts (n = 10) on test plus about 450 on DEV.

**Required baselines and metrics**

- Baselines: B0, B1 max-z (needed because the evidence order leaks the z-ranking), L0, L1,
  random deferral C2, and a coverage-matched consensus threshold C1.
- Metrics: AC@1; Brier; AUROC/AUPRC (positive = wrong); AURC; selective risk at fixed coverage;
  overconfidence gap; CW₁₀₀. Report injection-level CIs.

**Effort and key risks**

- Effort **[A]**: 1 day for logging fixes, 1–2 days for recalibration and a conformal threshold,
  about 0.5 GPU-day (unmeasured).
- Risks:
  - Consensus may be degenerate (11 levels; many ties).
  - `blind_root` may barely change the evidence ([01 §5](01_experimental_readiness.md#5-leakage-and-confound-audit)).
  - A 4B model may sit near the B1 floor.
  - LLM confidence and selective prediction are broadly studied, and the specific RCA ×
    missing-modality combination may already be covered (UNVERIFIED).

**Open literature questions (need paper verification)**

1. Which LLM-RCA papers report calibration or selective-prediction metrics, and with which
   confidence estimators?
2. Has any paper evaluated LLM-RCA with modalities removed in a controlled way, and did it
   measure confidence as well as accuracy?
3. For enum-constrained answers, does self-consistency vote share match or beat token-probability
   and verbal confidence in published comparisons?
4. Are conformal or risk-controlling abstention methods used in AIOps or incident diagnosis, and
   on which datasets?

---

## H2 — Budget-aware adaptive acquisition of observability evidence

**Key observation.** For a fully multimodal incident, the grid already evaluates five of the
eight modality subsets: `full` = M+L+T, `no_trace` = M+L, `no_log` = M+T, `no_metric` = L+T, and
`metrics_only` = M (`src/rca/ablate.py:45-63`). Because every arm is run for every incident, a
**sequential acquisition policy can be replayed offline** with full feedback, the same way
`gate.py` replays answer/retrieve/escalate (`src/rca/gate.py:66-115`).

**Reusable modules**

- Modality masks and applicability (`src/rca/ablate.py`) and the condition matrix.
- The offline outcome and reward machinery: `outcomes`, `evaluate`, and `reward` with a
  per-1k-token cost (`src/rca/gate.py:59-115`).
- Policies: threshold and learned policies (`src/rca/gate.py:123-176`). Stage-1/stage-2 decisions
  in `src/rca/decide.py` have the shape of "decide, maybe acquire, decide again".
- Per-arm token and latency columns (`src/rca/decide.py:103-121`).
- A single-service trace mask (`src/rca/ablate.py:22-28`), which is the building block for
  service-targeted acquisition.

**Missing interfaces, data and labels**

- An acquisition action space and a state machine: `acquire_logs`, `acquire_traces`, and possibly
  `acquire_traces(service)`. No code exists.
- The L-only, T-only and empty states are not among `CONDITIONS` (`src/rca/ablate.py:19`). Their
  absence limits which acquisition orders can be replayed.
- An inverse mask (keep the traces of selected services only) for targeted acquisition. MISSING.
- **A cost model.** Real costs of querying logs or traces are absent from the data. Prompt tokens
  are the only measured proxy (`src/rca/run_grid.py:506`). Using tokens as the "acquisition cost"
  is a construct-validity risk.
- Budget-matched controls (random acquisition at the same rate; fixed-order acquisition). The
  route-matched control logic can be adapted (`src/rca/gate.py:260-283`).

**Smallest valid experiment (no extra GPU beyond E1)**

- Set: RCAEval incidents that have all three modalities (RE2/RE3 Online Boutique and Train
  Ticket; Sock Shop has no traces). Use DEV for the threshold and RCA-T for reporting
  (69 incidents with traces in RCA-T, `/plans/.../design/research-design.md:132`).
- Policy: start at `metrics_only`. If the consensus is below τ (τ tuned on DEV), acquire to
  `full`. A second variant acquires one modality (M+L or M+T) and then decides again.
- Comparators: never acquire; always acquire; random acquisition at the policy's acquisition
  rate; a fixed order (logs first, then traces); and the oracle.
- Metrics: AC@1 and selective risk against mean cost (prompt tokens, plus acquisitions counted);
  area under the accuracy–budget curve; the budget-matched difference with an injection-level CI.

**Effort and key risks**

- Effort **[A]**: 3–5 days of analysis code, and no new GPU if E1 includes `metrics_only`,
  `no_log`, `no_trace` and `full` on the same incidents (it does, per
  `configs/exp/dev-pilot.yaml:18`).
- Risks:
  - **Construct validity.** Acquisition here means unmasking pre-collected telemetry: no system
    is queried, collection cost and latency are not real, and the windows are centred on the
    label-derived anchor (`docs/data_contract.md:124-127`).
  - **Small n.** About 69 trace-bearing test incidents, with an MDE on the order of 12+ pp
    **[A]**.
  - The summariser caps each block at 10 services, so "more evidence" can mean little new text.
  - Ordering effects can only be replayed for orders the grid contains.

**Open literature questions**

1. Which papers study cost- or budget-aware evidence or tool acquisition for RCA or incident
   diagnosis, LLM-based or not, and how do they define cost?
2. What do active feature acquisition and cost-sensitive sequential classification use as
   standard baselines and metrics (for example, accuracy vs budget curves)?
3. Do LLM RCA agents report the number of tool calls or queried telemetry as a cost, and is
   there evidence that adaptive querying beats querying everything?
4. Has offline replay over pre-collected modality subsets been accepted as a valid evaluation of
   acquisition policies, or do reviewers require live environments?

---

## H3 — Separating candidate-generation failures from candidate-ranking failures

**Key observation.** The prompt-level candidate set is **every service of the incident**
(`src/rca/legacy_view.py:26-29`). The root is always inside it for tier A (`src/rca/quality.py:96-100`;
no `ROOT_NOT_CANDIDATE` in any `data/reports/quality-*.json`). The JSON schema constrains the
answer to that list (`src/rca/llm.py:44-56`), so the model can always output the root.

**Three distinct quantities.** They must not be merged.

| # | Name | Definition (per incident × condition) | Where it is measured | Current pipeline |
|---|---|---|---|---|
| 1 | **Evidence omission** | The summary does not name a true root explicitly (no `- <root>:` line in any block and no call edge with the root as an endpoint). Eval-only flag `named = false` | `python -m rca.visibility <cfg>` (`src/rca/visibility.py`) | Occurs. Each block lists only thresholded services, at most 10 per block (`src/rca/evidence.py:218,240-246,256,270`). Sampled rates are in [01 §5](01_experimental_readiness.md#5-leakage-and-confound-audit) |
| 2 | **Candidate-generation failure** | No true root is in the candidate set the ranker may choose from. Eval-only flag `in_candidates = false` | `rca.visibility` (`in_candidates`); a future shortlist arm would log its own membership | **Zero by construction** for tier A, because the candidate set is all services. It becomes non-zero only if a shortlist or filter stage is added |
| 3 | **Candidate-ranking failure** | A true root is in the candidate set but is not ranked first (`rank > 1`). Sub-cases: rank 2–5, or not in the top 5 (stored as `n_candidates + 1` because the output is capped at 5, `src/rca/llm.py:50`; `src/rca/score.py:25`. *Update 2026-10-19: the cap is kept by the owner; ranks > 5 are censored, so only AC@1–5 and MRR@5 are reported*) | Grid rows (`rank`) | Every wrong answer today is a ranking failure, because category 2 is empty |

**Evidence omission is a stratum, not a failure stage.** An unnamed root does **not** make a
correct answer impossible. The root is still a legal candidate. The model can pick it from:

- the candidate list itself,
- the absence of signals from services that would otherwise be expected to show symptoms,
- caller-side symptoms (for example, an upstream service's slowdown with the root never named),
- the root id appearing inside a quoted log template (`token_anywhere`, not counted as named),
- retrieved precedents,
- pre-training knowledge of the topology.

How often a correct answer coincides with an unnamed root is an empirical question.

**Correct decomposition.** Write C = root in the candidate set and E = root named in the evidence
(flags from `rca.visibility`), and correct@1 from the grid:

```text
P(correct@1) = P(C) · [ P(E | C) · P(correct@1 | E, C) + P(¬E | C) · P(correct@1 | ¬E, C) ]
             + P(¬C) · 0            (an answer outside the candidate set cannot be scored correct)
```

Today P(C) = 1, so the bracket is the whole decomposition. Both conditional accuracies are
reported. P(correct@1 | ¬E, C) is an estimate, not an assumed zero.

**Error attribution (descriptive, mutually exclusive).**

- Wrong ∧ ¬C → candidate-generation failure.
- Wrong ∧ C ∧ ¬E → ranking failure **with** evidence omission.
- Wrong ∧ C ∧ E → ranking failure **despite** the root being named.

The second bucket co-occurs with omission. It does not show that omission caused the error.
A causal claim needs an intervention on the evidence text: add the root's line to an omitted
case, or remove it from a named case. Neither exists in the code.

**Reusable modules**

- Evidence files with per-condition text (label-free) and eval-only labels (`store.labels`).
- `score.correctness` ranks (`src/rca/score.py:23-27`); AC@3 and AC@5 from `rank`.
- B1 max-z ordering as a non-LLM generator and ranker (`src/rca/baselines.py:38-44`).
- `nonroot_ev_target` line counting (`src/rca/run_grid.py:209-226`), which can be reused to test
  whether the root is named.
- The oracle-flag pattern (`oracle_store`, refused by `decide`, `src/rca/decide.py:62-64`) as the
  template for an oracle-shortlist arm.

**Missing interfaces, data and labels**

- The eval-only flags `named` and `in_candidates` per condition are now produced by
  `src/rca/visibility.py` (added 2026-10-18). Full-set results are in
  [04](04_evidence_visibility_results.md): `in_candidates` is 1 in every record of all four sets;
  `named` in `full` is 216/218 (RCAEval test), 80/97 (Nezha), 77/86 (RCA100), 298/318 (AIOps2025).
- An explicit generator → ranker interface: a shortlist of K candidates passed as the JSON
  `enum`. MISSING. `build_messages` and `schema` take any candidate list
  (`src/rca/llm.py:44-62`), so the change is small.
- An **oracle-shortlist arm**: K candidates that include the root. It isolates ranking, uses
  labels, and must be flagged and kept out of Jev and headlines.
- A **root-removed arm**: a shortlist without the root. It tests whether the model abstains when
  generation fails, which links to H1.
- Full rank information beyond 5 (raise `maxItems`, or record a "not in top 5" category
  separately).

**Smallest valid experiment**

- Part A (no GPU for the flags; the E1 grid for accuracy): per dataset × condition, report
  P(E | C), P(correct@1 | E, C) and P(correct@1 | ¬E, C) with injection-level CIs, plus the
  three-bucket error attribution, and the same for B1. Descriptive only.
- Part B (about 300 prompts **[A]**): on RCA-T `full` and `blind_root`, an oracle shortlist of
  K = 5 (root plus the 4 highest-z non-roots) and a root-removed shortlist of K = 5. Compare AC@1
  inside the shortlist with 1/K and with B1 inside the shortlist. Report the abstain vote and
  consensus on the root-removed arm.
- Metrics: shortlist membership rate (category 2), evidence-mention rate (category 1), AC@1
  conditional on membership and on mention, the three-bucket error shares with injection-level
  CIs, and the abstention rate when the root is outside the shortlist.

**Effort and key risks**

- Effort **[A]**: 1 day for the eval-only label and decomposition, 1–2 days for the shortlist
  arms and their guards, about 0.2 GPU-day.
- Risks:
  - The findings describe this heuristic summariser, not LLM-RCA in general.
  - Text matching of service names depends on the alias decisions (D6 open).
  - The oracle shortlist uses labels, so it is analysis-only.
  - Choosing the shortlist distractors (top-z) can bias difficulty.
  - The decomposition may already be standard in retrieval-augmented or agentic RCA work.
    This is now confirmed for at least one paper; see below.

**Critical prior work (added 2026-10-18).** "Where Root Cause Analysis Fails: A Retrieval-Reranking Decomposition" (Hada M Muhammad et al.,
NeurIPS 2026 poster, September 2026, https://neurips.cc/virtual/2026/poster/139698).

- **Status.** The owner verified the full text on 2026-10-18. *Re-checked 2026-10-19 against the transcribed PDF (arXiv:2609.36686v1): datasets, incident counts and the retrieval/reranking framing below match. The reranker is gpt-oss-120b, and the RE1 preprocessing is `main-ase.py`, not the current RCAEval `main.py` (see the alignment gaps). The paper does not evaluate Nezha, RCA100 or AIOps2025; its "AIOps" mentions are related work.*
- **What it does.** It decomposes top-k RCA accuracy into retrieval failures and reranking
  failures, and evaluates a multi-signal retriever followed by an LLM reranker.
- **Datasets.** RCAEval RE1 (Online Boutique, Sock Shop and Train Ticket, 125 incidents each),
  plus WADI, SWaT and HVAC. It does not evaluate Nezha, RCA100 or AIOps2025.
- **Consequence for H3.** The retrieval/reranking decomposition is already published. H3 cannot
  claim it as new. Any remaining H3 contribution has to come from elsewhere. Candidates are:
  - evidence omission as a separate stratum;
  - behaviour under controlled missing telemetry;
  - confidence or abstention when the root is outside a shortlist;
  - the three datasets the paper does not cover.

  Each of these is UNVERIFIED UNTIL LITERATURE REVIEW.
- **External reference values.** Its published BARO and LLM results go in the table below, as
  external references only. Each value is transcribed with its table or figure number. None is
  directly comparable with an NT114 result until five things are aligned and the alignment is
  recorded: incident IDs, preprocessing, split, label granularity and candidate set. NT114's
  RCAEval evaluation uses the cell-held-out grouped split over RE1–RE3. NT114 has not checked
  whether its RE1 incidents, metric preprocessing and candidate sets match the paper's.

Transcribed on 2026-10-19 from arXiv:2609.36686v1 (PDF sha256 `2269ec70…9468d`, kept outside the
repository). The LLM reranker is gpt-oss-120b, n = 3 runs at T = 1.0 (mean ± std). "DK" means the
domain document. Evaluation is at service level over n = 125 incidents per suite.

**External reference, not directly comparable.**

| System (RE1) | Method | Metric | Value | Source (table/figure) | Aligned with NT114? |
|---|---|---|---|---|---|
| Online Boutique | BARO | top@1 | 0.784 | Table 3 (also Table 2) | no |
| Sock Shop | BARO | top@1 | 0.856 | Table 3 | no |
| Train Ticket | BARO | top@1 | 0.560 | Table 3 | no |
| Online Boutique | LLM, no DK | top@1 | 0.875 ± 0.009 | Table 3 | no |
| Sock Shop | LLM, no DK | top@1 | 0.872 ± 0.024 | Table 3 | no |
| Train Ticket | LLM, no DK | top@1 | 0.653 ± 0.024 | Table 3 | no |
| Online Boutique | LLM, with DK | top@1 | 0.888 ± 0.008 | Table 3 | no |
| Sock Shop | LLM, with DK | top@1 | 0.944 ± 0.008 | Table 3 | no |
| Train Ticket | LLM, with DK | top@1 | 0.685 ± 0.009 | Table 3 | no |
| Online Boutique | retriever (+stc, K = 15) | Retrieval@15 | 0.98 | Table 2 | no |
| Sock Shop | retriever (+stc, K = 15) | Retrieval@15 | 1.00 | Table 2 | no |
| Train Ticket | retriever (+stc, K = 15) | Retrieval@15 | 0.91 | Table 2 | no |
| Online Boutique | LLM, no DK | Rerank@1 | 0.90 | Table 2 | no |
| Sock Shop | LLM, no DK | Rerank@1 | 0.87 | Table 2 | no |
| Train Ticket | LLM, no DK | Rerank@1 | 0.72 | Table 2 | no |

**Known alignment gaps** (phase 06, V8 and V3):

- **Incident IDs.** V8 step 1 inventoried NT114's 375 RE1 incidents (125 per system). Step 2
  could not run: the code release named in the abstract (github.com/cruiseresearchgroup/DecompRCA)
  returned HTTP 404 on 2026-10-19.
- **Preprocessing.** The paper replicates RCAEval's `main-ase.py`. It keeps the raw `_latency-50`
  and `_latency-90` columns (Appendix B). NT114's BARO-style port follows the current `main.py`
  at `259ea41`, which drops `_latency-50` and renames `_latency-90`. `main-ase.py` was removed
  upstream in commit `67c0a8b`.
- **Split.** NT114 scores the grouped split's test and DEV roles over RE1–RE3. The paper scores
  all 125 RE1 incidents of each suite.
- **Granularity.** Both work at service level. The paper folds `-db` instances into their
  service, as NT114's port does.
- **Candidate set.** Not checked. NT114 ranks over the canonical candidate list; the paper ranks
  over metric-column prefixes.

**Open literature questions**

1. Do LLM-RCA papers report stage-wise errors (retrieval or candidate recall vs final
   localisation precision)? On which benchmarks?
2. How do two-stage RCA pipelines (statistical candidate filter → LLM re-ranker) compare with
   end-to-end LLM ranking?
3. Is there evidence that LLMs abstain or flag when the true answer is outside the provided
   candidate set? What methods detect "answer not in the options"?
4. Which recall@K and Avg@K conventions do RCA benchmarks use, so that results stay comparable?

## Unresolved questions

- Will the owner keep Jev mandatory (D1) if the framing moves to H2 or H3?
  (`/plans/.../decisions.md:17`)
- Is an analysis-only oracle-shortlist arm acceptable under the preregistration, or must it be
  declared exploratory?
