---
title: "Fix the runtime review findings and define research readiness (single LLM)"
description: "Close seven verified correctness findings in retrieval, resume, feasibility, scoring, reproduction and evaluation contracts, then define CPU, DEV-pilot and main-experiment readiness and map the 11 research questions to instruments."
status: in-progress
priority: P1
effort: 6-8 person-days [A], 0 GPU-days for phases 00-06
branch: main
tags: [bugfix, leakage, reproducibility, evaluation, statistics, research]
blockedBy: []
blocks: ["DEV pilot (llms.txt run order)", "main experiments"]
created: 2026-10-19
---

# Review findings: fixes and research readiness

## Scope and invariants

Planning only. Execution happens on another machine (Linux GPU machine per `llms.txt`; the CPU
phases also run on Windows). This machine's hardware is not a codebase blocker.

Kept unchanged, from [decisions](../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md)
and [protocol v2](../261018-2300-single-llm-simplification-and-evaluation-hardening/design/protocol-v2.md):

- one LLM; no Jev, judge, decision model or escalation;
- frozen bundle, splits, evidence (fingerprints must stay 0/862 changed) and prompt `v1`, including
  the top-5 cap and the precedent block text for service-level precedents;
- labels only in the eval-only zone; precedents only from the split's train role;
- fine-tuning stays the gated M4 extension (`sft_export.py` and `scripts/train_lora.py` do not exist).

`AGENTS.md` does not exist in the repository; `llms.txt` is the entry point and was read instead.

## Findings revalidated against the current code (2026-10-19)

All paths are under `nt114-rca/nt114-rca/`.

| # | Finding | Verdict | Evidence |
|---|---|---|---|
| 1 | Store not bound to split | **Confirmed, P1.** `_store_entries` globs every `evidence/store/*.json` and only checks the evidence fingerprint, which does not depend on the split. `dev-pilot.yaml` and `dev-sampling.yaml` share `results_dev_pilot/evidence`; `store-rcaeval-grouped.yaml` shares `results_visibility/rcaeval/evidence` with the visibility configs, so stale store files are a real path. The no-split branch builds the store from the query records themselves (labels of other scored incidents) | `src/rca/run_grid.py:348-361`, `:157-161`, `:314-323` |
| 2 | Resume key too narrow | **Confirmed.** Grid/raw key = model, revision, prompt, incident, condition, arm, mode, evidence_fp, store_fp, optional pp. It omits n, temperature, seed, max_tokens, chat_template_kwargs, logprobs, backend, server_fp. The cache key already includes all of them. The manifest is overwritten with the latest config, so a mixed grid looks homogeneous. `guard_headline` checks only revision and server_fp | `run_grid.py:575-577`, `:421-453`; `llm.py:103-111`; `analyze.py:63-85` |
| 3 | Feasibility parse gate | **Confirmed.** `parse_failed` is `not ranking`, true only when every sample failed; `grid_stats.parse_rate` is the share of cells with at least one valid sample, and `verdict` gates on it. `compare_sampling` already uses the per-row completion `parse_rate` | `feasibility.py:132-171`, `:328`; `score.py:27`; `llm.py:293` |
| 4 | Precedent labels lost | **Confirmed, latent.** Entries keep `root_service` only; `format_hits` prints `root cause: None`; `oracle_exclusions` matches `None == None`; `hit_has_truth` misses set labels. RCAEval (the only retrieval config) has 736/736 service-level single-root labels, so no current prompt is affected. AIOps2025 (82 node, 73 multi-service with no primary) and RCA100 (17 node) have `within-*-retrieval` splits with a train role, so the bug is reachable | `run_grid.py:356`, `retrieve.py:94-96,121-127`; label counts from `data/canonical/v1/*/eval_only/labels.jsonl` (aggregate only) |
| 5 | Reproduce ignores published CSVs | **Confirmed.** `reproduce` compares regenerated hashes with `analysis_meta.json` only; a modified or deleted published table still reports "match" | `reproduce.py:30-44` |
| 6 | Evaluation contracts | **Confirmed against protocol.** (a) DEV-fit filters on model × condition × retrieval × store_mode only, so DEV is pooled across datasets, granularities and set-scored strata, contradicting "datasets are never pooled". (b) `shift_table` groups by system × fault × role only, pooling conditions, models and arms, with unweighted means. (c) No CI on AUPRC, AURC, Brier, ECE, gap (`table_confidence`) or on AURC, risk@c, coverage@risk, L1 (`table_selective`), contradicting "every reported metric carries a CI" | `analyze.py:178-253`; `selective.py:283-312`; protocol v2 §3 |
| 7 | Miss rank n+1 | **Confirmed.** For `n_candidates` ≤ 4 a miss or parse failure has rank ≤ 5, so it counts for AC@k (k ≥ n+1) and adds 1/(n+1) to MRR@5. Flows into `cell_table`, contrasts and baselines (same `score.correctness`) | `score.py:23-27`; `analyze.py:138-139`; `contrasts.py:45`; `baselines.py:145` |

**Previous CPU test run.** `plans/review-runtime-261019-1746/cpu-tests.log` is a sandbox artefact:
`PermissionError` on the pytest basetemp under `plans/`, so its E's are environmental. The
`cpu-tests-verified.log` progress (72 tests = 23 %) matches the 313-test `-m "not realdata"` selection,
not the 369-test full suite. Position 153 of that collection is
`tests/test_feasibility.py::test_run_end_to_end_with_fake_server`, which needs Git Bash ahead of the
WSL `C:\Windows\System32\bash.exe` stub on `PATH` (recorded in the single-LLM plan's DoD). This is a
**hypothesis**, not a diagnosis; phase 00 proves or refutes it.

## Phases

Phases 00-06 completed 2026-10-19: [baseline diagnosis](../reports/test-261019-1911-baseline-diagnosis.md),
[CPU validation and readiness](../reports/test-261019-1921-cpu-validation-readiness.md). Tier 1 passes; nothing is committed.

| # | Phase | Kind | Priority | Effort | Depends on | Status |
|---|---|---|---|---|---|---|
| 00 | [Test baseline and failure diagnosis](phase-00-test-baseline-and-failure-diagnosis.md) | CPU | P1 | 0.5 d | – | completed |
| 01 | [Bind the retrieval store to the split; keep precedent labels](phase-01-retrieval-store-binding-and-precedent-labels.md) | fix (F1, F4) | P1 | 1 d | 00 | completed |
| 02 | [Execution signature and safe resume](phase-02-execution-signature-and-safe-resume.md) | fix (F2) | P2 | 1 d | 01 (same file) | completed |
| 03 | [Scoring invariant and feasibility parse gate](phase-03-scoring-invariant-and-parse-gate.md) | fix (F7, F3) | P2 | 0.5 d | 00 | completed |
| 04 | [Reproduce verifies published tables](phase-04-reproduce-verifies-published-tables.md) | fix (F5) | P2 | 0.5 d | 00 | completed |
| 05 | [Evaluation contracts and Q1 estimators](phase-05-evaluation-contracts-and-q1-estimators.md) | fix (F6) + Q1 | P1 | 2 d | 03 | completed |
| 06 | [CPU validation and DEV-pilot readiness gate](phase-06-cpu-validation-and-readiness-gate.md) | CPU gate | P1 | 0.5-1 d | 01-05 | completed |
| 07 | [Research extensions: owner gate](phase-07-research-extensions-owner-gate.md) | research, gated | P3 | – | 06 + owner | pending owner |

```text
00 ─┬─► 01 ─► 02 ─────────┐
    ├─► 03 ─► 05 ─────────┼─► 06 ─► 07 (owner-gated extensions)
    └─► 04 ───────────────┘
```

File ownership: 01 and 02 both edit `run_grid.py`, so they are sequential. 03 owns `score.py`,
`feasibility.py`; 04 owns `reproduce.py`; 05 owns `analyze.py`, `selective.py`. 05 waits for 03 so
the CI and selective tests are written against the corrected ranks. 03 and 04 can run in parallel with
01→02.

## Readiness tiers

| Tier | Meaning | Gate |
|---|---|---|
| **CPU validation** | Code is correct on synthetic, fixture and canonical-mock data | Phase 06 checklist: suite green with every failure classified, smoke chains, reproduce, 0/862 evidence fingerprints changed, every regression test from phases 01-05 |
| **Real-model DEV pilot** | One LLM may be run on DEV (`split_role: val`) | CPU tier + `llms.txt` chain (bundle at pinned revision, portability, Linux gate, GPU probe, feasibility with the **completion** parse gate) + Q1 pilot spec frozen in the repo (E1/E2 estimators in `src`, fit pool declared, SESOI confirmed by the owner) + manifest records the execution signature and store binding |
| **Main experiment** | Test-role runs whose tables may be reported | DEV pilot done; `pilot_decision` outcome recorded; confirmatory family and preregistration frozen (`preregistration_sha`); DEV thresholds frozen; headline guard passes, including the new mixed-signature check; `rca.reproduce` exits 0 on the DEV analysis. V8 step 2 blocks only paper-level RE1 alignment claims, not the main experiment |

Research questions and the Q4 design: [research-question map](design/research-question-map.md),
[Q4 paired design](design/q4-telemetry-vs-summarization.md). Correctness fixes (phases 01-05) and
research extensions (phase 07) are kept separate; no extension starts before phase 06 passes.

## Acceptance criteria (whole plan)

- [x] Every confirmed finding has a fix and a regression test that fails on the current code and
      passes after the fix (red → green recorded in the phase report).
- [x] Canonical outputs that the fixes must not change are unchanged: evidence fingerprints 0/862;
      ranks for `n_candidates` ≥ 5; prompts of service-level precedents (byte-identical `format_hits`).
- [x] The undiagnosed test failure is classified as environment or code with a reproduction command.
- [x] Readiness tiers are evaluated in phase 06 and the result recorded in the phase report.
- [ ] No GPU run, model download, commit or push without the owner's approval at each gate.

## Red-team notes (inline)

| Persona | Concern | Resolution |
|---|---|---|
| Failure | A stricter store check could silently shrink the store when files are missing | Missing eligible files raise; extra files are ignored and counted in the manifest; never silent |
| Failure | A new key format makes old grids look "not done" and appends duplicates | Phase 02 refuses to append to a grid whose rows carry another signature for the same model, and the headline guard refuses mixed signatures |
| Assumptions | Rendering set-valued precedents changes prompt `v1` | Under `v1`, precedents without a single service-level root are excluded with a recorded count; rendering sets needs a new prompt version (phase 07) |
| Scope | Q1 work can turn into H1 method development | Phase 05 ports only the estimators already specified and tested in plan 261019-1501; no new policy |
| Scope | CIs everywhere can make `analyze` slow | Phase 05 measures runtime at B = 2,000 and 10,000 on the canonical mock grid and reports it |

## Unresolved questions

None block phases 00-06. Resolved 2026-10-19: protocol v2 §9 accepted; H1 SESOI 0.05 confirmed
(`decisions.md`). Owner decisions needed later (phase 07): whether a cross-cell stability score (Q5) is admissible under the single-call
abstention invariant; whether to add summarizer and prompt variants (Q4, Q3) as new arms.
