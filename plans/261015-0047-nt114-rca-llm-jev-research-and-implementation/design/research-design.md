# Research design: overconfident LLM root-cause diagnosis under missing observability

Status: proposed, revised after the red-team review (plan.md "Red Team Review"). It is frozen as
the preregistration (`design/preregistration.md`) in two parts: the LLM part at the end of M2 and
the Jev addendum before E4. Both are hashed into the decision log. After the freeze, every change
to a hypothesis, endpoint or analysis is logged as a deviation.

## 1. Problem and motivation

An on-call engineer asks an LLM assistant which service caused an incident. Telemetry is often
incomplete: a service is not instrumented for tracing, a log export is truncated, or metrics are
the only signal. If the assistant answers wrongly **with high confidence**, it sends the engineer
to the wrong service. The cost is time-to-mitigation, not just a lower accuracy number.

Gaps confirmed by the project's literature survey (`plans/reports/research-261012-q1-survey-and-directions.md`):
N1 (LLM-RCA under missing modalities: 0 dedicated papers; P18 and P08 list it as a limitation)
and N2 (confidence-triggered retrieval: future work in P50 and P31). G3 (calibrated confidence for
LLM-RCA) is only partly filled by P42 (GPT-4, mostly one system).

## 2. Research questions and hypotheses

All effects are paired within incident, with the injection as the independent unit (handoff
§2b). Sampling uses n = 10 at T = 0.7, so consensus confidence has 11 levels. "Confident" means
consensus ≥ 0.8, i.e. ≥ 8 of 10 samples (primary), and verbal ≥ 0.8 (secondary).
<!-- Red team A6: n raised from 5 to 10; discrete support handled in §8 -->

| RQ | Question | Hypotheses | Endpoint and set |
|---|---|---|---|
| RQ1 | How does missing observability change LLM RCA accuracy? | **H1a** AC@1 under `blind_root` < `full`. **H1b** The `blind_root` drop exceeds the drop under the evidence-matched control `blind_nonroot_ev` (§4). This separates losing the **root's trace signal** from losing the same amount of evidence text | ΔAC@1 and difference-in-differences; RCA-Z `blind_root` subset (174) |
| RQ2 | Does missing telemetry make the LLM overconfident? | **H2a** The overconfidence gap (mean consensus − accuracy) is larger under `blind_root` than `full`. **H2b** It is larger under `metrics_only` than `full` | Δgap; RCA-Z applicable subsets (174; 282) |
| RQ3 | Can confidence detect wrong diagnoses, and does that degrade under missingness? | **H3a** Consensus AUROC > verbal AUROC (`full`). **H3b** Consensus AUROC under `full` > under `blind_root` | ΔAUROC; RCA-Z (592; 174) |
| RQ4 | Does Jev's deferral reduce wrong **accepted** diagnoses beyond simple controls? | **H4b** At equal coverage, J-AA (Jev with {accept, abstain}) has lower selective risk than random deferral (C2). **H4c** (two-sided) J-AA vs coverage-matched consensus threshold (C1) | Selective risk at J-AA's coverage; RCA-T (218) |
| RQ5 | Do retrieval and escalation add value when Jev chooses them? | **H5** (two-sided, secondary) Full J vs J-AA vs matched-route controls R1/R2 (§5) on selective accuracy, coverage, tokens and latency | RCA-T, NEZ |

**H4a** ("Jev lowers CWA₁₀₀ vs always-accept L0") is what the owner asked about, and it is
reported as a key descriptive result with CIs. It is **not** in the confirmatory family: L0 never
abstains, so any deferring policy lowers CWA₁₀₀ almost by construction (red team A2). The
confirmatory Jev tests (H4b, H4c) hold coverage fixed and use selective risk, which does not
depend on the confidence variable that defines CWA.

RQ6 (fine-tuning) is optional and gated (phase 05). It is not part of the minimum paper.

### What a negative result means

If H4b fails, Jev's deferral is no better than random at RCA, and that is the finding. If H1b
fails, the missingness effect is an evidence-volume effect, not a root-visibility effect. Both
are reportable.

## 3. Contributions that can realistically be shown

1. A leakage-safe, paired benchmark of LLM RCA under controlled and natural missing observability
   on four datasets, with injection-level statistics, evaluated on **cell-held-out** RCAEval (no
   test incident shares its (root, fault) cell with the store or training data).
2. A controlled contrast (`blind_root` vs the evidence-matched `blind_nonroot_ev`) that separates
   "the root's traces are missing" from "less evidence", for accuracy and for overconfidence.
3. An evaluation of confidence signals (verbal, consensus, recalibrated consensus, Jev-verifier) as
   error detectors under missingness.
4. The first evaluation of a decision model (Jev) as a post-LLM safety layer, with coverage- and
   route-matched controls that isolate what Jev contributes, plus its failure modes (option-order
   bias, number insensitivity, version drift).
5. A reproducible artefact: configs, manifests, cached raw outputs, analysis scripts.

## 4. Variables

| Kind | Variables |
|---|---|
| Independent (manipulated) | condition {`full`, `no_metric`, `no_log`, `no_trace`, `metrics_only`, `blind_root`, `blind_nonroot`, `blind_nonroot_ev`}; decision policy; action set; LLM (primary, escalation, replication); retrieval {none, hybrid-precedent}; Jev state variant |
| Natural | RCAEval RE1 metrics-only (natural absence; 110 of RCA-T, 310 of RCA-Z); RCA100 and AIOps2025 coverage causes (`covered`, `export_truncated`, `export_gap`) |
| Dependent | rank of truth; correct@1/@3; parse failure; verbal and consensus confidence; abstain vote; Jev action, probabilities, noul; tokens; latency |
| Blocking | dataset, system, fault family, label granularity, **modality regime** (RE1 natural metrics-only vs RE2/RE3 multimodal), injection |

Confounders and controls:

- **Evidence volume and the `blind_root` control.** `blind_root` deletes only the root's spans; the
  root's metrics and logs stay, so H1b is about trace visibility. The release's `blind_nonroot`
  target is matched on raw span count. The evidence builder lists only changed services (≤ 10),
  so removing an unflagged service can leave the text unchanged (red team A5). This plan therefore
  adds **`blind_nonroot_ev`**: the non-root service that appears in the `full` evidence text with
  the number of evidence lines closest to the root's, ties broken by `sha256(uid + service)`. The
  condition driver picks it, the same way the release picks the `blind_nonroot` target, and logs
  it in `ablation_log.jsonl` (eval-only). We report, per incident, whether each control's evidence
  equals `full` and its prompt-token delta. H1b uses `blind_nonroot_ev`; `blind_nonroot` is
  secondary.
- **Candidate count.** Systems differ (sock-shop ~10, train-ticket ~60). Report the random baseline
  1/|C| per incident and stratify by system.
- **Modality regime.** RE1 incidents carry only `full`. Every RQ4 result is reported by regime,
  and a claim of "helps under missing observability" requires the multimodal-regime estimate to
  have the same sign as the pooled one (red team A4).
- **Natural vs ablated absence.** The evidence text is identical by contract, but RE1 incidents
  differ from RE2/RE3 ones, so RE1 vs `metrics_only` is descriptive only.
- **Candidate order.** Shuffled with a uid seed; constant across conditions of an incident.
- **Sampling noise.** Fixed seed; a second seed on DEV measures run-to-run variance.
- **Jev option order.** Randomised per call, seeded and logged; tested for position bias.

## 5. Baselines, controls and comparators

Jev is the default and required decision layer. Everything else is a comparison arm or a
control. None of them replaces Jev in the default architecture.

| ID | Arm | Role | Labels? |
|---|---|---|---|
| B0 | Random ranking (1/\|C\|, analytic) | Floor | no |
| B1 | Max-z metric heuristic | Non-LLM, from evidence features | no |
| B2 | BARO (RCAEval package; metrics) | Published statistical baseline (RCAEval RE2/RE3) | no |
| B3 | RCA100 majority class (`inventory`) and alert-entity | Required by protocol §2a | majority uses the label prior |
| L0 | LLM-only, always accept (primary) | **Main baseline, preserved** | no |
| L1 | LLM-only + self-abstention (`abstain_vote` ≥ 0.5) | The LLM's own deferral | no |
| L2 | Always the escalation model | Escalation reference | no |
| **J** | **LLM + Jev**, all available actions (argmax of Jev's choice) | **Default system** | no |
| J-AA | Jev with {accept, abstain} | Confirmatory Jev arm for H4b/H4c; isolates deferral from answer replacement (red team A1) | no |
| J-floor | J + a Jev-confidence floor tuned on DEV | TypeSafe's routing pattern | DEV labels |
| C1 | Coverage-matched consensus threshold; ties broken at random, expectation over 1,000 draws | Isolates *which* incidents Jev defers | no |
| C2 | Coverage-matched random deferral (analytic + 1,000 draws) | Must be beaten (H4b) | no |
| R1 | Route-matched random: retrieve/escalate/abstain at J's per-action rates, chosen at random | Isolates Jev's routing from "some answers come from a stronger arm" (H5) | no |
| R2 | Route-matched consensus rule: lowest-consensus incidents get abstain, then escalate, then retrieve, at J's rates | Simple routing control (H5) | no |
| C3 | Threshold policy tuned on DEV (`gate.threshold_policy`) | Reviewer's simple comparator | DEV labels |
| C4 | Learned cost-sensitive policy (`gate.learned_policy`), trained on DEV | Secondary comparator | DEV labels |
| O | Oracle | Upper bound | yes (analysis only) |

## 6. Evaluation sets (fixed before any model run)

Primary RCAEval protocol: **`within-rcaeval-grouped-0-e9b2c81c`** (cell-held-out). Verified on
2026-10-15 (counts only): 0 of 218 test and 0 of 143 val incidents share a (root, fault) cell with
the train role. The physically grouped `within-rcaeval-retrieval` split has a same-cell twin in
its store for 138 of 144 test incidents. Retrieval there is close to a label lookup, so it is used
only as the labelled **recurring-fault regime** (E2b). <!-- Red team A3 -->

| Set | Split / role | Incidents | Applicable (blind_root / metrics_only / no_trace) | Used for |
|---|---|---|---|---|
| **DEV** | grouped val | 143 (65 RE1) | 54 / 78 / 54 | Prompt, Jev state and wording, comparator tuning, J-floor, recalibration maps, pilot, power simulation |
| **STORE** | grouped train | 374 | – | Retrieval store (precedent mode; no same-cell neighbours) |
| **RCA-T** | grouped test | 218 (110 RE1, 108 multimodal) | 69 / 108 / 69 | RQ4–5 (Jev, retrieval, policies) |
| **RCA-Z** | grouped train ∪ test | 592 (310 RE1) | 174 / 282 / 186 | RQ1–3 (zero-shot, no fitting, no retrieval queries) |
| RCA-REC | `within-rcaeval-retrieval` test, its train as store | 144 | 41 / 64 / 43 | E2b recurring-fault regime (secondary) |
| **NEZ** | `eval-only-nezha`; store = `xdata-rcaeval-to-nezha` train (735 RCAEval, shared OB/TT) | 97 applicable (101) | 97 / 97 / 97 | External RQ1–5; the store differs from STORE, and this is reported |
| **AIO** | `eval-only-aiops2025` | 318 tier A: 245 top-1 + 73 set-scored | 83 / 384 (all 400) | External RQ1–4; no retrieve action; set-scored reported separately |
| **R100** | `eval-only-rca100` | headline 86 tier-A tasks / 70 injections; secondary 103 tasks / 86 injections | – | External RQ1–4; no retrieve action; next to B3 (D7) |

DEV is never reported as a result. RCA-Z contains STORE incidents; that is valid for zero-shot
RQ1–3 because nothing is fitted on them, but they are never retrieval queries. Comparators tuned
on DEV transfer unchanged to every set, as Jev does untuned.

## 7. Experiment matrix

**Minimum set (defensible paper).**

| ID | Experiment | Model | Sets × conditions | Retrieval | RQ |
|---|---|---|---|---|---|
| E1 | LLM-only missingness grid | primary | RCA-Z, DEV, NEZ, AIO, R100 × all applicable (incl. `blind_nonroot_ev`) | none | 1–3 |
| E2 | Retrieval arm (novel-fault) | primary | DEV, RCA-T, NEZ × all applicable | hybrid, precedent | 5, Jev retrieve |
| E3 | Escalation arm | escalation | DEV, RCA-T, NEZ, AIO, R100 × all applicable | none | 5, Jev escalate, L2 |
| E4 | Jev decisions, stage 1 + 2 (J, J-AA) | Jev 1.13.0 | DEV, RCA-T, NEZ, AIO, R100 | – | 4, 5 |
| E5 | Comparators and controls (C1–C4, R1–R2, L0–L2, O) | offline | as E4 | – | 4, 5 |
| E6 | Non-LLM baselines B0–B3 | – | all sets | – | 1 |
| E7 | Cross-family replication of E1/E2/E4 on RCA-T | replication | RCA-T × all applicable | none + hybrid | generality |
| E8 | Jev robustness: option rotations (DEV, RCA-T), repeat-call stability (DEV), J-noconf (DEV, RCA-T), J-noevidence (DEV; also the D3 = no fallback state for AIO/R100) | Jev | as listed | – | validity |

**Optional extensions** (week-6 checkpoint): E2b recurring-fault regime on RCA-REC (with O3
`no_precedent` on the same set); O1 thinking mode; O2 BM25/dense; O4 `jev-1.14.0` rerun on RCA-T;
O5 Nemotron 3 Nano; O6 answer-token probability; O7 second sampling seed; O8 fine-tuning
(phase 05); O9 K8s demo; O10 J-short state.

Volume estimate **[A]**: about 6.5k prompts for E1, 1.6k for E2, 4.3k for E3 and 1.8k for E7,
with n = 10. Pilot data (30 canonical incidents, red team B) suggests a median of only ~800
evidence characters, so the token volumes are probably far below the earlier 3.5k-token
assumption. M2 measures them. Jev: about 14k decision calls plus about 8k robustness calls.

## 8. Metrics

**Accuracy:** AC@1, AC@3, Avg@5, mean rank; parse failures counted as wrong and tabulated
separately. AIOps2025 set-scored incidents: a hit is any `root_service_ids` member, in a separate
table, never pooled with top-1.

**Confidence quality:**
- Brier score (primary calibration metric; binning-free).
- ECE on the discrete support of consensus (one bin per level, 11 levels), plus 10 equal-width
  bins for verbal confidence (comparable with P42) and a smoothed (kernel) ECE.
- Reliability diagrams.
- Overconfidence gap (mean confidence − accuracy).
- AUROC and AUPRC for error detection (positive = wrong); ties count 0.5 (Mann–Whitney).
- CW₁₀₀ = confidently wrong per 100 incidents.

**Decision quality (per policy):**
- Coverage, selective accuracy and selective risk.
- WA₁₀₀ (accepted ∧ wrong).
- CWA₁₀₀ (accepted ∧ wrong ∧ confidence ≥ 0.8). The confidence is that of the **arm that produced
  the final answer** (primary, primary + retrieval, or escalation). This rule is frozen in the
  preregistration.
- abstain₁₀₀ and per-action rates.
- Risk–coverage curves and AURC (score = Jev P(accept) for J/J-AA; consensus for L0).
- Selective risk at coverage 0.5, 0.7 and 0.9.
- Tokens, latency and Jev cost per incident along the chosen path.

The utility `gate.reward` with penalties {1, 2, 5} is secondary.

## 9. Statistical methodology

1. **Unit and weights.** The injection is the unit; records carry `weight` (1/records of the
   injection). Conditions are variants, never samples.
2. **Per-condition primary analyses.** Each confirmatory contrast uses the incidents where its
   conditions apply, with one value per injection. Pooled-over-condition summaries (per-injection
   mean over applicable conditions) are secondary and always shown by modality regime.
3. **Intervals.** Paired cluster bootstrap over injections, B = 10,000, percentile 95 % CI, seed
   0. Datasets are never pooled in headline tables; a stratified pooled estimate is secondary.
4. **Tests.** Endpoints that decompose per injection (ΔAC@1, DiD, Δgap) use a paired sign-flip
   permutation test (10,000 draws). Endpoints that do not (AUROC, selective risk at matched
   coverage) use the paired cluster bootstrap: the p-value is the share of bootstrap differences
   on the other side of 0, two-sided. Exact McNemar on `representative` records is a sensitivity
   check.
5. **Confirmatory family** (Holm, α = 0.05, 8 contrasts) <!-- Red team A7 -->: H1a, H1b, H2a, H2b,
   H3a, H3b (RCA-Z), H4b, H4c (RCA-T). External datasets repeat the same contrasts as
   replications, with CIs and Holm within each dataset. H4a, H5, CWA₁₀₀, J-floor, C3/C4, the
   per-condition RQ4 tables and every optional extension are secondary or exploratory, with CIs only.
6. **Power.** Rough MDEs for a paired binary with 20 % discordance at 80 % power
   (2.8·√(0.2/n)) **[A]**:

   | Set | n | MDE |
   |---|---|---|
   | RCA-Z (`full`) | 592 | 5.1 pp |
   | RCA-Z `blind_root` | 174 | 9.5 pp (the DiD for H1b ≈ 13 pp) |
   | RCA-T | 218 | 8.5 pp |
   | AIO (top-1) | 245 | 10 pp |
   | NEZ | 97 | 12.7 pp |
   | R100 (tier A) | 70 | 15 pp |

   These are placeholders. In M2, a simulation-based power analysis per confirmatory endpoint
   (resampling DEV pilot discordance, error rates and Jev coverage) replaces them and is frozen
   in the preregistration.
7. **Strata (protocol §2b.4).** Dataset, label granularity, condition, coverage cause, modality
   regime. AIOps2025 is reported with and without the 5 short-log incidents. RCA100 is reported
   next to B3.
8. **Primary vs auxiliary.** `excluded_from_primary` applies to headline tables only (none
   active). Auxiliary results (optional extensions, mock runs, DEV) never enter headline tables;
   `analyze` refuses rows with `backend: mock`, `split_role: val` or mixed versions in a headline
   table.

## 10. Threats to validity

| Threat | Type | Mitigation / disclosure |
|---|---|---|
| Anchor time from labels places the window | internal | Standard practice; never in text (data contract §5) |
| Protocol deviates from AgenticOpsEval (no fault window end, no prompt text) | external | Not comparable with published numbers; stated |
| Pretraining contamination (OB/TT service names, RCAEval papers) | internal | Per-incident labels are not memorisable from names; the `blind_root` contrast is within-model |
| Repeated injections make retrieval a label lookup | internal | Primary split is cell-held-out (0 same-cell twins); the recurring regime is separate and labelled |
| `blind_root` hides traces only; its applicability depends on the label (root must have spans) | construct | H1b stated as trace visibility; the subset is described; the evidence-matched control is used |
| Discrete consensus (11 levels) | conclusion | Support-based ECE, Brier, tie conventions, randomised tie-breaking in C1 |
| Single primary family | external | Cross-family replication E7 |
| Jev is a closed, versioned model trained on undisclosed data | reproducibility | Pin `jev-1.13.0`, cache raw responses, release them privately; drift check O4 |
| Small external sets | conclusion | MDEs reported; external sets are replications |
| Prompt and state tuned on DEV only | internal | DEV excluded from all results |
| Evidence text injection (log lines) | internal | Benchmark data; noted |
| Mock LLM / mock Jev | conclusion | Never in results (guarded) |
| Offline full-feedback evaluation ≠ online deployment | external | vLLM batching and Jev (no seed) are not deterministic, so results are reproducible **from cached outputs only**; latency is summed per chosen path |

## 11. Related technical approaches

| Approach | Representative work | Relation to this study |
|---|---|---|
| Statistical metric RCA | BARO (Pham et al., FSE 2024), RCAEval baselines (Pham et al., WWW 2025) | B2 baseline |
| Multi-modal non-LLM RCA | Nezha (Yu et al., FSE 2023) | Dataset; no model reuse |
| LLM RCA, agentic | OpenRCA (Xu et al., ICLR 2025), RCACopilot (Chen et al., EuroSys 2024) | Agentic tools are out of scope; we test a single-shot evidence-summary LLM |
| Retrieval of past incidents | P31 (CIS 2025), P50 (RAG can hurt) | E2, E2b, RQ5 |
| Verbalised confidence | Xiong et al. (ICLR 2024): LLMs are overconfident when verbalising | Verbal arm |
| Sampling consistency | Wang et al. (ICLR 2023) self-consistency; Farquhar et al. (Nature 2024) semantic entropy | Consensus arm; semantic entropy reduces to vote share for enum answers |
| Self-evaluation | Kadavath et al. (2022) P(True) | Jev `supported` noul is an external-verifier analogue |
| Selective prediction | Geifman and El-Yaniv (NeurIPS 2017); Kamath et al. (ACL 2020) | Risk–coverage, AURC, deferral |
| Model cascades | FrugalGPT (Chen et al., 2023) | Escalation action, R1/R2 controls |
| Calibration | Guo et al. (ICML 2017) | Brier, ECE, recalibration on DEV |

Bibliographic details are confirmed in the paper-writing pass (phase 06), not here.
