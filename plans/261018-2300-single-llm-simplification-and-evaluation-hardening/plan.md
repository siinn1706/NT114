---
title: "NT114-RCA: single-LLM simplification and evaluation hardening (CPU only)"
description: "Remove Jev and every second model, then rebuild the evaluation core so that one LLM's own ranking, confidence and abstention are measured with paired, injection-level, reproducible statistics."
status: in-progress
priority: P1
effort: 16-20 person-days [A], 0 GPU-days
branch: main
tags: [refactor, research, evaluation, statistics, tech-debt]
blockedBy: []
blocks: []
supersedes: [261015-0047-nt114-rca-llm-jev-research-and-implementation (Jev, escalation, RQ4-RQ5 and E3-E5, E8)]
created: 2026-10-18
---

# Single-LLM simplification and evaluation hardening

## Overview

The owner has decided to remove Jev and to adopt a single-LLM architecture, with no separate
judge, decision model or escalation model. This reverses decision D1 of the
[Jev master plan](../261015-0047-nt114-rca-llm-jev-research-and-implementation/plan.md).

This plan does three things, all on CPU, without GPU and without real-model inference:

1. **Remove the obsolete layer.** It deletes Jev, the escalation role, the route-matched controls
   and the learned routing policy (about 750 lines of source and 21 tests).
2. **Fix the evaluation core.** The scout found that none of the paired contrasts the
   protocol depends on is implemented. Uncertainty exists only for AC@1. Confidence, cost and
   reproducibility have gaps that would weaken any H1/H2/H3 paper.
3. **Run the CPU-only validation and experiments.** These are things that need no model output:
   - the evidence-instrument audit;
   - non-LLM baselines on all four datasets;
   - simulation checks of the statistics;
   - a text-level leakage audit;
   - power analysis on the real set sizes.

The plan deliberately does **not** implement any H1, H2 or H3 method:

- no conformal or risk-control abstention rule;
- no acquisition policy;
- no shortlist arm.

It builds the shared measurement layer that all three directions need, and leaves the
hypotheses, their confirmatory family and the preregistration to after the literature review.

Evidence for every claim is in the [scout report](research/scout-report.md).

## Target architecture

```text
canonical data ─► prepare (evidence per condition, label-free)
                    │
                    ▼
          one LLM, one prompt per cell ──► grid.jsonl + llm_raw.jsonl     (GPU later; mock now)
          (condition × retrieval arm)          │
                                               ▼   eval-only zone (labels joined here)
             ┌──────────── score ─────────────┼──────────── visibility flags, baselines ─┐
             ▼                                ▼                                          ▼
     confidence registry ──► selective evaluator ──► paired-contrast engine ──► tables + manifest
     (scores from the same    (answer / abstain;       (per-injection, CI,       (reproduce from
      LLM's outputs only)      any cached arm)           sign-flip, Holm)          caches only)
```

**The invariant.** Every reported answer comes from one model's single call on one cell. Every
abstention decision is a deterministic rule on that same call's outputs, fitted on DEV labels at
most. No answer is replaced by, or gated on, another model's output.

What survives, and why:

| Capability | Kept as | Justification |
|---|---|---|
| RCA ranking | One fixed LLM for the main study, prompt `v1` unchanged, top-5 output cap kept | Core task. Ranks beyond 5 are **right-censored** ("not in the top 5"), never exact ranks |
| Retrieval | A **fixed experimental arm** (`retrieval: [none, hybrid]`), never chosen per incident by a model | Precedent retrieval is a scientific factor. The routing decision was Jev's, and it goes away with Jev |
| Confidence | Scores derived from the same LLM's samples: consensus, verbal, verbal SD, abstain vote, Borda margin, vote entropy, and token probability when logprobs exist | H1 needs several estimators, all computable on CPU from cached raw outputs. Token probability is built and fixture-tested only; it **requires real-model validation** on DEV before any use |
| Abstention | The LLM's own flag (L1), plus a threshold on a confidence score, set on DEV and frozen for test | This is selective prediction on one model. No judge is involved |
| Model sweeps | Independent runs of the same pipeline remain supported (sampling variants, an optional cross-family replication) | Not part of the minimum paper. No prediction may depend on another model's output |

## Phases

| # | Phase | Priority | Effort [A] | Depends on | Status |
|---|---|---|---|---|---|
| 0 | [Gate: audit jobs finished, turn-2–4 work committed](phase-00-gate-audit-jobs-and-baseline-commit.md) | P1 | 0.5 d | – | done (2026-10-19) |
| 1 | [Decision record and protocol reset](phase-01-decision-record-and-protocol-reset.md) | P1 | 1 d | 0 | done (2026-10-19) |
| 2 | [Remove Jev, escalation and model routing](phase-02-remove-jev-escalation-and-routing.md) | P1 | 2–3 d | 0, 1 | pending |
| 3 | [Evaluation core: confidence registry, selective evaluator, paired contrasts](phase-03-evaluation-core.md) | P1 | 4–5 d | 2 | pending |
| 4 | [Cost ledger and reproducibility](phase-04-cost-ledger-and-reproducibility.md) | P2 | 2 d | 2 | pending |
| 5 | [Leakage and baseline fairness](phase-05-leakage-and-baseline-fairness.md) | P1 | 3–4 d (incl. BARO-style and task 5a) | 0, 2 | pending |
| 6 | [CPU-only validation experiments](phase-06-cpu-validation-experiments.md) | P1 | 2–3 d | 3, 4, 5 | pending |
| 7 | [Docs, research reports and old-plan supersession](phase-07-docs-and-supersession.md) | P2 | 1 d | 6 | pending |
| 8 | [Retire the legacy `data_root` path](phase-08-optional-retire-legacy-path.md) | P3 | 1 d | 2 | pending (approved 2026-10-18) |

```text
0 ─► 1 ─► 2 ─┬─► 3 ─┐
             ├─► 4 ─┼─► 6 ─► 7
             ├─► 5 ─┘
             └─► 8 (optional, any time after 2)
```

Phases 3, 4 and 5 touch disjoint files (see each phase's file list) and can run in parallel. Phase 6
is the only phase that produces results.

## Why this order (impact × simplicity × reuse)

| Change | Scientific impact | Simplification | Reused by |
|---|---|---|---|
| Paired-contrast engine with injection-level CI and sign-flip (P3) | **Highest.** Without it no confirmatory claim can be tested correctly | Replaces the ad hoc McNemar and the legacy tables | H1, H2, H3 |
| Confidence registry + selective evaluator (P3) | High. It is the abstention capability that Jev provided, rebuilt on one model | Replaces `decide` + Jev policies + R1/R2 | H1 (core), H2 (stopping rule), H3 (abstain when the root is absent) |
| Remove Jev / escalation (P2) | Removes an external, unseeded, paid dependency and licence issue D3 | About −750 lines of source, −21 tests, −1 credential | All |
| Baseline fairness (P5) | High. A 4B model must beat an evidence-order baseline, not only max-z | Small | H1, H3 |
| Leakage audit, text level (P5, P6) | Medium to high for any retrieval claim | Small | H1 retrieval arm, H2 |
| Cost ledger (P4) | Medium. It is required for H2 and for honest cost claims | Small | H2 (core), H1 |
| Visibility join and censored-rank metrics (P3) | Medium | Small | H3 (core), H1 strata |

## Internet use and provenance policy (owner decision, 2026-10-18)

Claude Code may use the Internet whenever it is useful, in every phase, with no separate approval.
That covers dependencies, datasets, reference implementations, research artefacts, documentation
and external verification. These rules keep the work reproducible:

1. **Dependencies.** Each new package or version is pinned in NT114's lock file. The change is
   noted in [decisions](decisions.md), with the reason. Reference implementations whose
   dependencies would conflict with NT114 get their own environment, as in phase 05 task 5a.
2. **Downloaded artefacts** (releases, reference code, papers, data):
   - each one goes into its own new directory outside the source tree and is treated as
     untrusted data;
   - interpreters run with `-I`, and scripts are never run from inside the download directory;
   - provenance (URL, version or commit, access date, per-file sha256) is recorded next to every
     result that uses the artefact.
3. **Dataset integrity.** External data enters NT114 only through the existing `rca.prep` route.
   It is checked with `verify-bundle` and `verify-splits`. Existing bundles, splits and condition
   matrices are never modified in place. A changed upstream source produces a new build id, never
   a silent replacement.
4. **Train/test isolation.** Nothing downloaded may change split assignments or make test
   labels reachable from a model-facing path. The label-isolation and import tests apply to
   external material too: for example, the RE1 alignment of V8 runs in the eval-only zone.
5. **No runtime dependency.** Pipeline steps never call external services. Phase 04's
   `rca.reproduce` test runs with networking disabled. Once inputs are local, results never depend
   on availability on the Internet.

## Not in scope (non-goals)

- Any GPU run or real-model inference.
- A runtime dependency of the pipeline on an external service. Internet use is allowed (see the
  Internet policy), but `prepare`, `run`, `analyze` and `reproduce` must work offline once their
  inputs are on disk.
- Any hypothesis-specific method: conformal or risk-control thresholds, acquisition policies,
  oracle or root-removed shortlist arms, recalibration maps beyond a generic interface.
- A choice of the confirmatory family, the preregistration text or the paper framing. These come
  after the literature review (`/research/03_elicit_search_pack.md`).
- Changes to datasets, splits, evidence text or prompt `v1`, including the top-5 ranking cap.
  Evidence fingerprints must not change; phase 06 verifies this. A full-ranking prompt may become
  a separate experimental arm after the literature review, particularly if H3 is selected.
- Commits or pushes without the owner's explicit approval at each gate.

## Critical prior work

- **H3:** "Where Root Cause Analysis Fails: A Retrieval-Reranking Decomposition", by Hada M Muhammad et al., a NeurIPS 2026 poster from
  September 2026
  ([neurips.cc/virtual/2026/poster/139698](https://neurips.cc/virtual/2026/poster/139698)).
  The owner verified the full text on 2026-10-18.
  - **What it does.** It splits top-k RCA accuracy into retrieval failures and reranking failures.
    It then evaluates a two-stage pipeline: a multi-signal retriever followed by an LLM reranker.
  - **Datasets.** RCAEval RE1 (Online Boutique, Sock Shop and Train Ticket, 125 incidents each),
    plus WADI, SWaT and HVAC. It does **not** evaluate Nezha, RCA100 or AIOps2025.
  - **Why it matters here.** It already proposes the decomposition that H3 describes in
    `/research/02_research_directions.md`. Any H3 framing must position itself against it, and
    novelty in the decomposition itself cannot be claimed.
  - **How its numbers are used.** Its published BARO and LLM results are **external reference
    values**, not NT114 results. A direct comparison requires the five alignments listed in
    phase 06: incident IDs, preprocessing, split, label granularity and candidate set.
    NT114's 375 RE1 cases are treated as a **likely shared upstream benchmark**, not as a
    verified one-to-one match. Phase 06 check V8 compares canonical incident IDs, injection
    timestamps and telemetry fingerprints on CPU, in the eval-only zone. Its comparison step
    waits until the DecompRCA release has been inspected. Until it passes, no paper-level
    alignment is claimed and the published results are not directly comparable.

  The literature note is in `/research/02_research_directions.md` (H3) and
  `/research/03_elicit_search_pack.md` (RQ4).

## Statistical assumptions (summary; details in phase 03)

1. **Unit.** The injection is the independent unit. Records of one injection are treated as
   exchangeable within it, and injections as independent of each other. Faults repeated on the
   same system and load profile can violate independence; leakage audit V6 reports such
   near-duplicates.
2. **Pairing.** Paired contrasts compare the same incidents under two arms. Whether an arm exists
   (whether a condition applies) depends on the label, so it is not missing at random. Estimates
   hold for the applicable intersection only, and are reported as such.
3. **Sign-flip test.** It assumes that per-injection differences are symmetric about zero under
   the null. Under that assumption it tests a mean difference of zero.
4. **Percentile cluster bootstrap.** It needs enough clusters for the bootstrap distribution to
   approximate the sampling distribution. Phase 06 V4 checks coverage on each dataset's real
   cluster structure; RCA100 has the fewest, with 70 tier-A injections. Where coverage fails, the
   result carries that caveat or uses a different interval.
5. **Top-5 censoring.** AC@1 to AC@5 are exact. Mean rank and MRR are reported only in censored
   form (MRR@5, where a censored rank contributes 0), never as exact means.
6. **Sampling.** Outputs come from one fixed model at T = 0.7 with n = 10 samples. Sampling
   variance is part of the incident-level outcome and is not modelled separately.
7. **DEV-to-test transfer.** DEV-fitted thresholds assume that DEV and test share a
   distribution. That is known to be false for some strata, since 94 test incidents lie in
   test-only strata. Realised test risk is therefore always reported next to the target.

## Red-team review (inline, four personas)

| # | Persona | Finding | Resolution |
|---|---|---|---|
| R1 | Failure | The running audit jobs start `rca.visibility` in a fresh process after `prepare`. Editing `src/` mid-run would mix code versions into one result | Phase 00 gate: no source edit until both jobs exit |
| R2 | Failure | The turn-2–4 work is uncommitted. Deleting Jev on top makes one unreviewable diff | Phase 00: the owner reviews and commits (or explicitly declines) before phase 02. A tag `pre-single-llm` is proposed, but it is created only on approval |
| R3 | Assumptions | Removing Jev removes the old paper's main contribution (RQ4/RQ5). Novelty now rests on an unverified literature gap | Phase 01 records this as a risk. The infrastructure is direction-agnostic, so the review can choose H1, H2 or H3 without rework |
| R4 | Assumptions | A DEV-fitted threshold may not transfer: 94 test incidents are in strata that DEV lacks | Phase 03 reports DEV-fit-then-test risk next to the test-oracle curve, with a stratified shift table |
| R5 | Scope | "Keep everything generic" can become a framework. The risk is building H2's policy engine early | The selective evaluator takes **given** action vectors. It contains only fixed, random and threshold controls; policies belong to the hypotheses |
| R6 | Scope | Forking paths: the analysis can be run many ways before the family is fixed | Phase 03: the headline guard requires a `preregistration_sha` in the analysis config. Without one, tables are written as `exploratory_` |
| R7 | Failure | A `blind_root` variant can be identical to `full` (2 of 3 smoke incidents). A contrast that includes them measures a null manipulation | Phase 06 reports manipulation-check rates. Phase 03 contrasts accept a `require_changed` filter and report both versions |
| R8 | Security | Removing Jev must not leave stale key handling or docs that tell people to export a key | Phase 02 verification: a grep for `TYPESAFE`/`jev` in `src/ tests/ configs/ docs/ README.md` must return nothing |
| R9 | Assumptions | The old plan's MDEs (n = 592 RCA-Z, etc.) predate the exclusion counts now measured | Phase 06 recomputes them from the measured applicable intersections |

## Validation gate (critical questions)

Answered by the owner on 2026-10-18; every default was accepted (recorded in
[decisions](decisions.md)):

1. Retrieval: keep it as a fixed experimental arm (default), or remove it entirely?
2. Model list: allow sweeps of independent single-model runs in one config (default), or allow
   exactly one model per config?
3. Legacy RCAEval `data_root` path: retire it in optional phase 08 (default), or keep it?
4. Uncommitted turn-2–4 work: commit it before phase 02 (default), or keep everything in one
   change set?

## Definition of Done

- [ ] `grep -riE "jev|typesafe|escalat" src tests configs docs README.md` returns nothing except the absence assertions in `tests/test_feasibility.py` (old plans and journals are untouched)
- [ ] The non-realdata suite passes. The realdata suite passes where the bundle is present
- [ ] A mock end-to-end run (synthetic) produces the grid, raw outputs, confidence table, selective table, paired-contrast table and manifest. Re-running `rca.reproduce` on it gives byte-identical tables
- [ ] Simulation checks pass: cluster-bootstrap 95 % CI coverage within the Monte-Carlo band; sign-flip type-I error ≤ α + MC error
- [ ] Evidence fingerprints of every visibility evidence file are unchanged by the refactor
- [ ] Phase 06 reports exist under `/research/` with numerator, denominator and exclusions for every number
- [ ] `/research/00`–`02` and the old plan's `plan.md` state which parts are superseded

## Unresolved questions

The owner resolved the three earlier questions on 2026-10-18 (see [decisions](decisions.md)):

- the top-5 cap is kept;
- BARO-style is approved conditionally;
- replication is optional.

Resolved on 2026-10-18:

- the source of the BARO fixtures;
- the decomposition paper's benchmarks;
- the RE1 alignment approach (V8);
- the execution of task 5a (Claude Code on the owner's Windows machine, in phase 05, before
  phase 06);
- Internet access across the whole workflow (see the Internet policy). The DecompRCA release is
  downloaded in phase 06 for V8.

No questions remain open.
