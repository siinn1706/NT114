# Preregistration (DRAFT)

Status: **draft, not frozen**. Part 1 (everything below except the Jev wording) is frozen and hashed
at the end of M2; part 2 (Jev question wording `JEV_QUESTION_VERSION`, J-floor value) is frozen
before E4. After a freeze, changes are appended as dated deviations, never edited in place.

Copied on 2026-10-15 from [research-design.md](research-design.md) §2, §5, §6, §8 and §9. Code
contracts that implement these rules: `src/rca/score.py` (scoring, eval units), `src/rca/metrics.py`
(weighted metrics, cluster bootstrap, sign-flip test), `src/rca/gate.py` (policies, C1/C2, R1/R2,
oracle), `src/rca/decide.py` and `src/rca/jev.py` (Jev decisions).

## Placeholders tuned on DEV (filled at the freeze)

| Item | Value | Frozen at |
|---|---|---|
| Prompt text (`llm.PROMPT_VERSION`) | `v1` draft; final text and hash: _TBD_ | end of M2 |
| Jev question wording (`jev.JEV_QUESTION_VERSION`) | `q1-draft`; final wording and hash: _TBD_ | before E4 |
| Observed Jev response `model` string | _TBD (M0 smoke call)_ | M0 |
| J-floor confidence floor | _TBD (DEV)_ | before E4 |
| Simulation-based power per confirmatory endpoint | _TBD (DEV pilot)_ | end of M2 |
| Primary / escalation / replication model repos and revision shas | _TBD (M0 model probe)_ | end of M2 |

## 2. Research questions and hypotheses

All effects are paired within incident, with the injection as the independent unit (handoff
§2b). Sampling uses n = 10 at T = 0.7, so consensus confidence has 11 levels. For the Qwen3.5
primary, the presence penalty (0, the current setting, or 1.5, the card value) is chosen on DEV by
the fixed rule of `rca.feasibility.compare_sampling` and frozen with prompt v1, before any test-set run. "Confident" means
consensus ≥ 0.8, i.e. ≥ 8 of 10 samples (primary), and verbal ≥ 0.8 (secondary).

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
only as the labelled **recurring-fault regime** (E2b).

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
5. **Confirmatory family** (Holm, α = 0.05, 8 contrasts): H1a, H1b, H2a, H2b,
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
