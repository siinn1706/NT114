---
title: "NT114-RCA: LLM root-cause diagnosis under missing observability, with Jev as the mandatory decision layer"
description: "Research and engineering master plan: LLM RCA, confidence reliability and a Jev post-LLM decision layer on the nt114-data-v1 release, in 12 weeks."
status: in-progress
priority: P1
effort: 43 person-days + ~6 GPU-days
branch: main
tags: [research, llm, rca, jev, calibration, experiments]
blockedBy: [261014-0749-nt114-rca-dataset-standardization-and-validation]
blocks: []
created: 2026-10-15
---

# NT114-RCA: LLM + Jev research and implementation plan

## Overview

We measure how missing metrics, logs and traces change the accuracy and the confidence of
LLM root-cause diagnosis in microservice systems. We test whether confidence signals detect wrong
answers. We test whether **Jev** (TypeSafe's decision model, the required post-LLM layer) reduces
confidently wrong *accepted* diagnoses beyond coverage-matched controls. This happens on the
frozen `nt114-data-v1` release (RCAEval, Nezha, AIOps2025, RCA100) with injection-level,
preregistered statistics. The LLM-only baseline is preserved for every comparison. Planning only;
nothing here is implemented.

## Plan documents

| # | Required content | Where |
|---|---|---|
| 1 | Repository audit | [research/repo-audit.md](research/repo-audit.md) |
| 2, 3, 9, 10 | RQs and hypotheses; related approaches and baselines; experiment matrix; evaluation and statistics | [design/research-design.md](design/research-design.md) |
| 4, 14 | Model selection; hardware and resources | [research/model-selection.md](research/model-selection.md) |
| 5, 6, 7, 12 | Architecture; Jev integration; confidence strategy (§4.4, research-design §8); file-level scope | [design/architecture.md](design/architecture.md), [research/jev-api-verification.md](research/jev-api-verification.md) |
| 8 | Training strategy | [design/training-strategy.md](design/training-strategy.md) |
| 11, 13 | Roadmap; tests and validation | phase files below |
| 15 | Timeline | below |
| 16 | Risks | [risks.md](risks.md) |
| 17 | Red-team findings | below |
| 18, 19 | Definition of Done; cook handoff | below |
| – | Decision log (append-only); preregistration draft | [decisions.md](decisions.md), [design/preregistration.md](design/preregistration.md) |

## Phases

| # | Phase | Weeks | Status |
|---|-------|-------|--------|
| 1 | [M0: Prerequisites, owner decisions, preregistration draft](./phase-01-m0-audit-prerequisites-and-design-decisions.md) | 1 | **Blocked** (Linux gate, GPU probe, TypeSafe access); D1–D8 decided 2026-10-15 |
| 2 | [M1: Offline end-to-end LLM + Jev pipeline (CPU, mocks)](./phase-02-m1-offline-end-to-end-pipeline.md) | 1–2 | Done (2026-10-15) |
| 3 | [M2: Real-model inference, live Jev on DEV, freezes](./phase-03-m2-real-model-inference-and-live-jev.md) | 3 | Pending |
| 4 | [M3: Baselines, confidence, minimum experiment set](./phase-04-m3-baselines-confidence-and-main-experiments.md) | 4–6 | Pending (CPU baselines B0, B1, B3 done early) |
| 5 | [M4: Gated fine-tuning (optional)](./phase-05-m4-gated-fine-tuning.md) | 7–8 | Pending |
| 6 | [M5: Extensions, reproducibility, paper results](./phase-06-m5-ablations-reproducibility-and-paper-results.md) | 7–12 | Pending |

Dependencies: 1 ∥ 2 → 3 → 4 → {5 (gated), 6}. The GPU machine is first needed at phase 03
task 1. Everything before that runs on CPU without paid calls.

## Selected design (summary)

- **Evaluation protocol:** RCAEval on the cell-held-out `within-rcaeval-grouped` split (0 test incidents share a (root, fault) cell with the store; the twin-rich retrieval split is a labelled secondary regime). Confirmatory family of 8 contrasts; the Jev tests use J-AA at matched coverage.
- **Architecture:** offline full-feedback grid (all LLM arms cached) → Jev decides on visible
  states (stage 1: accept/retrieve/escalate/abstain; stage 2 after retrieve/escalate:
  accept/abstain) → label join and analysis. Online behaviour equals the replayed chosen path.
- **Models (12 GB RTX 4080 Laptop, D2):** primary Qwen3.5-4B at FP8 (non-thinking); fallback
  Qwen3-4B-Instruct-2507. The escalation model is a 4-bit 8–9B model, chosen by measurement:
  Qwen3.5-9B NF4 or Qwen3-8B-AWQ. Cross-family replication uses Phi-4-mini-instruct. No 14B–27B
  models. VRAM estimates are in [model-selection §3](research/model-selection.md).
- **Jev:** `POST /v1/systemone` (TypeSafe direct, the only adapter), pinned `jev-1.13.0`, `choice` + `noul`, numbers as banded
  text, shuffled option order, cached, fail-closed. Jev probabilities are treated as uncalibrated
  scores and evaluated, not trusted.
- **Training:** zero-shot primary; retrieval as dynamic few-shot; QLoRA only behind the week-6 gate.

## Timeline (12 weeks; week 1 starts Mon 2026-10-19)

| Week | Dates | Engineering / experiments | Writing |
|---|---|---|---|
| 1 | 10-19 | M0; M1 start | – |
| 2 | 10-26 | M1 | – |
| 3 | 11-02 | M2 (GPU): DEV pilot, freezes, preregistration hash | Related work, Method |
| 4 | 11-09 | M3: E1, E6 | Setup |
| 5 | 11-16 | M3: E2, E3, E4 (Jev must be live by 11-16) | Results RQ1–2 |
| 6 | 11-23 | M3: E5, E7, E8; **checkpoint 11-27** | Results RQ3 |
| 7–8 | 11-30 → 12-11 | M4 (gated) or extensions | Results RQ4–5 |
| 9 | 12-14 | Extensions end 12-18; reproduction script | Discussion, threats |
| 10–11 | 12-21 → 01-01 | holidays: no experiments | Intro, full draft |
| 12 | 01-04 → 01-08 | Final regeneration | Outside review, submit |

## Owner decisions (answered 2026-10-15; details in [decisions.md](decisions.md))

| ID | Answer | Still required |
|---|---|---|
| D1 | TypeSafe direct, pinned `jev-1.13.0`; Jev stays the mandatory post-LLM layer | Key, exact response `model` string, rate limit (M0 exit) |
| D2 | RTX 4080 Laptop, 12 GB: 3–4B primary, 4-bit 7–9B evaluated if feasible, QLoRA/LoRA only, no 14B–27B | Probe GPU, driver, CUDA, PyTorch, free VRAM (`scripts/gpu_probe.py`) |
| D3 | AIOps2025/RCA100 evidence is **not** sent to TypeSafe; their Jev states use the J-noevidence form (enforced in `rca.decide`) | Licence and data-processing terms verified before lifting (`jev.evidence_cleared`) |
| D4 | Kubernetes demo out of scope | – |
| D5 | 2027-01-08 provisional; venue TBD | Venue |
| D6 | Alias sign-off needs verified raw-data / topology evidence and collision tests | Evidence and tests, before M3 |
| D7 | RCA100 primary: tier A (86 tasks / 70 injections); all 103 tasks / 86 injections secondary | – |
| D8 | RCAEval primary: cell-held-out `within-rcaeval-grouped-0-e9b2c81c`; retrieval split secondary (E2b) | – |

### Original decision requests

| ID | Decision | Evidence needed | Default if unanswered by |
|---|---|---|---|
| D1 | Jev provider: TypeSafe direct (recommended and the only adapter built; documented pinning) / Cloudflare (ZDR listed) / OpenRouter | Can the provider pin `jev-1.13.0`? | TypeSafe, 10-23 |
| D2 | GPU tier and machine | Hardware available | tier M assumed; 10-23 |
| D3 | May AIOps2025/RCA100 evidence (CC BY-NC / BY-NC-SA, "private transfer only") be sent to Jev? | Licence reading; Jev data terms | AIO/R100 Jev runs wait; 11-13 |
| D4 | K8s live demo (proposal note phase 4) in or out | Proposal obligations | out (optional O9); 11-27 |
| D5 | Target venue and submission date; public artefact scope | Advisor | 2027-01-08, private artefact |
| D6 | Service-alias review sign-off (data plan blocker 2) | `docs/dataset_quality_audit.md` | must close before M3 |
| D7 | RCA100 headline set: tier-A 86 tasks / 70 injections (recommended) vs all 103 tasks / 86 injections | Protocol §2a/§2b, split tier rules | tier A headline, 103-task secondary |
| D8 | Primary RCAEval protocol: cell-held-out `within-rcaeval-grouped-0-e9b2c81c` (recommended; 0/218 test twins) vs the data plan's `within-rcaeval-retrieval` (138/144 twins), which becomes the secondary recurring-fault regime E2b | Twin counts (research-design §6); data plan split notes | grouped primary; before the preregistration (end of M2) |

## Definition of Done (whole plan)

- [ ] Linux gate passed; the run manifests tie every result to a commit, bundle, model revisions and `jev-1.13.0`
- [ ] Preregistration frozen before the main grid; deviations logged
- [ ] E1–E8 complete; LLM-only baseline and Jev reported side by side on all four datasets where the licence decision D3 permits (else Jev with the preregistered J-noevidence state on AIO/R100)
- [ ] Confirmatory RCAEval table (8 contrasts: H1a, H1b, H2a, H2b, H3a, H3b, H4b, H4c) on the cell-held-out split, with injection-level CIs and Holm p-values; H4a reported as a secondary key result
- [ ] Replications on Nezha, AIOps2025 (± 5 short-log), RCA100 (next to the B3 baselines)
- [ ] Jev diagnostics: position bias, stability, J-noconf, error rate
- [ ] No mock, DEV or mixed-version rows in headline tables (guarded and tested)
- [ ] `reproduce_tables.sh` regenerates every table offline
- [ ] Paper draft with a deviations section, reviewed by an outside reader

## Red Team Review

Two hostile reviewers ran on 2026-10-15. Reviewer A covered methodology and assumptions;
reviewer B covered failure modes, scope and security. The reviews produced 19 findings; 18 remain
after deduplication (A8 = B2). All carry file:line or data-count evidence, and the orchestrator
re-verified the load-bearing claims (portability step 0, `denylisted`, empty-ranking rank, split
twins and compositions). All 18 are accepted (proposed); the owner may still reject any.

| # | Sev. | Finding | Resolution (where) |
|---|---|---|---|
| A1 | Critical | C1/C2 cannot isolate Jev when Jev also swaps answers via escalate/retrieve | Confirmatory Jev arm is J-AA; route-matched controls R1/R2 for full J (research-design §2, §5) |
| A2 | Critical | CWA₁₀₀ makes H4a near-tautological; "whose confidence" undefined | H4a demoted to secondary; H4b/H4c on selective risk at matched coverage; CWA uses the final arm's confidence (§2, §8) |
| B1 | Critical | Linux gate fails from `main` once M1 lands (`verify_portability.sh:24-25`) | Gate runs from a `cd96e9e` worktree; HEAD re-check at M2 start (phase 01 task 1) |
| B2/A8 | Critical | Recursive denylist rejects the allowed key `assistant_first_answer` (`schema.py:36,45-47`) | Allowlist exact match for top-level keys; denylist on nested keys only; `_DENY_TOKENS` untouched (phase 02 task 5, architecture §7) |
| B3 | Critical | Total parse failure scores as correct (`metrics.py:11`, `run_grid.py` `rk == 1`) | Empty ranking = wrong, `parse_failed` column, Critical test (phase 02 task 2) |
| A3 | High | Retrieval split: 138/144 test incidents have a same-cell twin in the store | Primary RCAEval protocol switched to cell-held-out `within-rcaeval-grouped` (0/218 twins); recurring regime E2b secondary (§6) — **needs owner confirmation (D8)** |
| A4 | High | RCA-T dominated by RE1 metrics-only; blind_root counts wrong | Recounted on the grouped split; modality regime is a stratum; per-condition primary analyses (§4, §6, §9) |
| A5 | High | `blind_nonroot` may leave evidence unchanged; H1b over-claims | New evidence-matched control `blind_nonroot_ev`; H1b restated as root trace visibility (§4; phase 02 task 7) |
| A6 | High | Consensus with n = 5 has 6 levels; ECE bins and C1 ill-posed | n = 10; support-based ECE, Brier, tie conventions; C1 with randomised tie-breaking (§2, §8) |
| A7 | High | Holm family under-counted; MDE misapplied; sign-flip undefined for some endpoints | 8 enumerated contrasts; bootstrap tests for AUROC/selective risk; simulation-based power in M2; AIO n = 245 (§9) |
| B4 | High | Label-derived grid fields (`hit_has_truth`, `hits[].root`) escape the planned test | Decision inputs from evidence + aggregates only; end-to-end label-store permutation; canaries in those fields (phase 02) |
| B5 | High | `gate.action_table` cannot serve the needed arms/sets | New `decide.action_table`; `Canon` split-role list (phase 02 task 7) |
| B6 | High | No slack for one researcher; Jev deadline inconsistent | Jev key is a hard M0 exit; preregistration in two parts; Cloudflare adapter and J-short cut; availability recorded (phases 01, 03) |
| B7 | High | Jev cache/resume semantics unsafe; alias routes unpinnable | TypeSafe-only; cache only validated 200s keyed by the observed model; retry ledger (phase 02) |
| B8 | High | LLM/retrieval cache keys miss server state, `max_tokens`, embedder kind | Server fingerprint, `max_tokens` in key; embedder kind in `store_fp`; "reproducible from cache only" (architecture §6, §10) |
| B9 | High | Artefact would commit NC evidence and train labels to GitHub; no D3 = no fallback | Artefact git-ignored, private HF only; hygiene moved to M0; J-noevidence fallback; DoD "where licence permits" |
| A9 | Medium | SFT data overstated (1,223 examples, effective n ≈ 374); Δgap is an artefact of masking | Counts fixed; Δgap conditional on Δaccuracy (training-strategy §2, phase 05) |
| B10 | Medium | Hardware claims unverified; M4 precision mismatch | M2 gate measures KV and throughput of the measured-feasible models (12 GB since D2: 4B primary, 8–9B 4-bit escalation candidates); M4 holds precision fixed (phases 03, 05) |

### Whole-Plan Consistency Sweep

All plan files were searched for superseded terms: the retrieval split as primary, `(140)`,
`n = 5`, `J-short` in the minimum set, `H4a` in the confirmatory family, `1.5–1.8k`, the
Cloudflare adapter in M1, `visible_columns`, a single-part preregistration and `paper/artifact`
committed to git. Every hit was updated. The remaining mentions of `within-rcaeval-retrieval`
describe the secondary E2b regime or the audit's facts. No unresolved contradiction is known.
`ak plan validate` passes.

## Validation Log

Read-only checks on 2026-10-15 (no tests were re-run: the `.venv` is blocked by a hook and the
system Python lacks pytest; the recorded 230-passed result is cited instead).

| Claim | Check | Result |
|---|---|---|
| Portability step 0 fails once `src/configs/schemas` diverge from `cd96e9e` | Read `verify_portability.sh:24-25` | Verified |
| `denylisted("assistant_first_answer")` is True | Read `schema.py` `_DENY_TOKENS` and matcher | Verified |
| Empty ranking is scored rank 1 | Read `metrics.rank_of_truth` | Verified |
| Grouped split 374/143/218, 0 twins; retrieval split 138/144 twins | Counted from the split manifests | Verified |
| RCA100 103 tasks / 86 injections; tier A 86 / 70 | Release manifest and split tier rules | Verified |
| Jev API, pricing, confidence formula, no calibration claim | TypeSafe docs (research/jev-api-verification.md) | Verified from docs; no live call |
| Model licences and release dates | Secondary sources | **[S] — confirm on model cards in M0** |
| Hardware memory fits | Estimates | **[A] — measured in the M2 gate** |
| Linux GPU gate | `release` handoff docs | **Pending** (M0 prerequisite) |

Plan structure: `ak plan validate` passes; the whole-plan sweep found no remaining contradiction.

## Cook handoff

After approval: `/ak:cook "F:/Nam/UIT/NT114 - NCKH/plans/261015-0047-nt114-rca-llm-jev-research-and-implementation/plan.md"`.
Deep mode: run a scout pass at the start of each phase. Phase 02 is the first implementation
phase and needs no GPU or keys. Do not use `--auto` unless the owner asks.
