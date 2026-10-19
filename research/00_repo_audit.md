# 00 — Repository-grounded audit (NT114-RCA)

Audit date: 2026-10-18. Commit audited: `fee95cf` on `main`. Every claim here was read from the
working tree; nothing was modified, installed or committed.

**Path convention.** Code paths are relative to `nt114-rca/nt114-rca/` (for example
`src/rca/llm.py:114`). Paths that start with `/` are relative to the repository root (for example
`/plans/...`). JSON reports have no line numbers, so they are cited by file and field.

**Status labels.** IMPLEMENTED = code exists and is wired into the runtime path. PARTIAL = code
exists but is incomplete or not wired in. DOCUMENTED_ONLY = described in docs or plans, with no
code. MISSING = neither. A separate column says whether the component has ever been **executed on
a real model**. UNKNOWN marks anything this audit could not establish.

> **Update 2026-10-19.** The owner removed Jev, escalation and the separate decision layer
> (`/plans/261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md`). The system is now single-LLM. Rows below that cite `src/rca/decide.py`,
> `src/rca/jev.py` or `src/rca/gate.py` describe the audited commit; those files are deleted and
> recoverable from the git tag `pre-single-llm`. Statements the change or the phase-06 CPU
> measurements alter carry an inline dated update. The measurements are in
> [05](05_evidence_instrument_audit.md) and [06](06_statistics_validation.md).

## Executive summary

The repository contains a careful, leakage-aware **offline evaluation harness** for single-shot LLM
root-cause ranking under ablated telemetry, followed by an external decision model (Jev). The data
layer is mature: four canonical datasets, quality states, injection-level evaluation units, and
verified cell-held-out splits. The inference, decision and analysis layers are implemented and
tested against mocks.

**No real-model result exists.** Every grid on disk comes from the mock LLM and mock Jev, and the
GPU pilot is marked "NOT RUN YET" (`configs/exp/dev-pilot.yaml:1`). The system is not agentic: one
prompt goes to one LLM, which ranks a fixed candidate list. It does not call tools, it acquires no
evidence step by step, and it has no separate candidate-generation stage.

## Five most important blockers

| # | Blocker | Evidence |
|---|---|---|
| 1 | No real-model output exists, and the M0 gates (Linux portability gate, GPU probe, TypeSafe key) are still open, so no scientific question can be answered yet | `configs/exp/dev-pilot.yaml:1`; `/plans/261015-0047-nt114-rca-llm-jev-research-and-implementation/decisions.md:46-50`; `results_smoke_canonical/grid.jsonl`: all 106 rows have `backend: mock` (counted in this audit) |
| 2 | The project's gap claims come from a survey corpus that contained **journals only**: conference papers and arXiv were excluded, yet most LLM-RCA work appears at conferences. Every novelty statement is therefore UNVERIFIED UNTIL LITERATURE REVIEW | `/plans/261011-1345-aiops-q1-literature-gap/work/q1-protocol.md:25`; `/plans/261015-0047-.../design/research-design.md:15-18` |
| 3 | Raw LLM completions (including `reason`) and token logprobs were thrown away before caching. **Addressed 2026-10-18 (uncommitted):** they are now persisted, see [01, blocker 2](01_experimental_readiness.md#blockers-that-could-invalidate-conclusions) | Before the fix: `src/rca/llm.py:114-117,129-136` at `fee95cf`; claim at `/plans/.../design/research-design.md:61` |
| 4 | The evidence builder names at most 10 services per block, and only those above fixed thresholds, so the root is sometimes not named in the text the LLM reads (**evidence omission**). The root stays in the candidate list, so this does not rule out a correct answer, but missingness effects may track what the builder omits. Measured on the full sets 2026-10-19: the root is named in `full` for 216/218 RCAEval test, 80/97 Nezha, 77/86 RCA100 and 298/318 AIOps2025 records ([04](04_evidence_visibility_results.md)) | `src/rca/evidence.py:218,240-246,256,270`; sample counts in [01 §5](01_experimental_readiness.md#5-leakage-and-confound-audit) |
| 5 | The protocol is not frozen and the comparators are incomplete. The preregistration is a draft, the prompt and Jev wording are drafts, B2 (BARO) and recalibration exist only in documents, B1 never ran on RCA100, policy cost leaves out Jev, and alias sign-off D6 is open. *Update 2026-10-19: the Jev cost gap is moot (Jev removed). B1 per block and B1m have run on all four datasets, and a BARO-style port exists under an unvalidated label ([05 §V3](05_evidence_instrument_audit.md#v3--how-strong-are-the-non-llm-baselines)). Preregistration and D6 are still open* | `/plans/.../design/preregistration.md:3`; `src/rca/jev.py:28`; `results_baselines_rca100/table_baselines.csv` (only B0 and B3); `src/rca/gate.py:75-87`; `/plans/.../decisions.md:52` |

## 1. Reconstructed runtime pipeline (canonical path)

```text
prep (offline, CPU)          run_grid prepare            run_grid run                   decide (Jev)            analyze
canonical store + splits --> evidence text per     --> LLM x n samples per cell --> stage-1 / stage-2 --> weighted tables,
+ condition matrix           condition (no labels)     Borda aggregate + score       decisions on          policy controls
                                                        (labels joined here)          visible state
```

| Step | What happens | Evidence |
|---|---|---|
| 1. Select incidents | `Canon` loads the condition matrix and the split assignments, then keeps incidents of the configured `split_role`(s) whose `full` condition applies. Optional `limit_per_system` keeps a sample spread evenly over fault types | `src/rca/run_grid.py:79-157`, `_sample` at `:51-63` |
| 2. Load telemetry | Canonical Parquet tables are rebuilt into the legacy `{metrics, logs, traces}` frames | `src/rca/legacy_view.py:102-127` |
| 3. Candidate set | **All services of the incident**, from `incident["candidates"]["services"]`, shuffled with a seed derived from the uid. Nothing generates or filters candidates | `src/rca/legacy_view.py:26-29`; `src/rca/evidence.py:302-306`; `src/rca/run_grid.py:236` |
| 4. Apply conditions | Masks: `full, no_trace, no_log, no_metric, blind_root, blind_nonroot, metrics_only`, plus `blind_nonroot_ev`, which is chosen from the full evidence text. The driver passes the root from `Truth` only for `blind_root` | `src/rca/ablate.py:19,45-63`; `src/rca/run_grid.py:212-250` |
| 5. Evidence summary | Fixed windows [t−600 s, t) and [t, t+300 s], where t is the label-derived anchor. Metrics use robust z (p80 of \|z\|) with a z ≥ 3 cut. Logs report error-rate, volume and new-template changes. Traces report p90, error rate and slow edges. At most 10 services per block, 14,000 characters in total. Absent modalities are stated explicitly | `src/rca/evidence.py:25-29,72-93,134-214,218-290` |
| 6. Retrieval (optional) | BM25, dense or hybrid (RRF k=60) over train-role incidents of the same system. `precedent` mode excludes the query's split group. Hits are shown with **their own** root labels | `src/rca/retrieve.py:27-118`, `format_hits` at `src/rca/retrieve.py:121-127`; `src/rca/run_grid.py:159-163,362-367` |
| 7. LLM call | System prompt and evidence go to vLLM through HTTP. Output is JSON constrained by a schema: `ranking` is an enum over the candidates with **at most 5 items**, plus `confidence` 0–100, `insufficient_evidence`, `next_check`. The call uses n = 10 samples at T = 0.7 (DEV config), and results are cached in SQLite under a key that includes the server fingerprint | `src/rca/llm.py:23-56,97-137`; `configs/exp/dev-pilot.yaml:22-23` |
| 8. Aggregate | Borda count over parsed samples gives the final ranking. Confidence signals: `conf_verbal` (mean of parsed samples), `conf_consensus` (top-1 votes of the Borda winner / **all** samples), `abstain_vote`, `parse_rate` | `src/rca/llm.py:206-227` |
| 9. Score | Rank of the first hit, or `n_candidates + 1` on a miss; empty ranking counts as wrong and sets `parse_failed`; set scoring for multi-root labels | `src/rca/score.py:18-27` |
| 10. Log | One JSONL row per model × incident × condition × retrieval cell, with a resume key that includes the evidence and store fingerprints. `manifest.json` records commit, dirty flag, bundle, split, models, server fingerprints and seed | `src/rca/run_grid.py:461-518,388-413` |
| 11. Decision layer | Jev state is built **only** from the evidence file and named aggregate fields. Stage 1 chooses among {accept, retrieve, escalate, abstain}; stage 2, after retrieve or escalate, chooses {accept, abstain}. Option order is shuffled, failures are fail-closed, and the pinned version is `jev-1.13.0` | `src/rca/decide.py:26-41,140-151,199-267`; `src/rca/jev.py:28-36,82-104,139-145`; `src/rca/gate.py:190-212` |
| 12. Analysis | Injection weights are renormalised per cell. Outputs: weighted AC@1/@3, Brier, ECE, AUROC/AUPRC, AURC, CW₁₀₀, and policies L0, L1, Jev variants, C1, C2, R1, R2 and the oracle. A headline guard refuses mock rows, DEV rows and mixed prompt versions | `src/rca/analyze.py:34-139`; `src/rca/metrics.py:80-242` (weighted and clustered part) |

**Agent responsibilities.** No multi-agent or tool-using agent exists. The plan scopes agentic
tools out (`/plans/.../design/research-design.md:261`). The runtime roles are: the RCA LLM
(diagnose), retrieval (show precedents), an optional escalation LLM (a second arm with the same
prompt), and Jev (decide what to do with the answer).

**Stopping and confidence decisions.** No adaptive stopping exists: n is fixed and evidence is
built in one shot. The only stopping-like decisions are the LLM's self-reported
`insufficient_evidence` flag (`src/rca/llm.py:27-28`, aggregated at `:224`) and Jev's terminal
accept/abstain after stage 2 (`src/rca/decide.py:246-251`). Policy L1 abstains when
`abstain_vote ≥ 0.5` (`src/rca/analyze.py:118`).

## 2. Component status

| Component | Status | Executed on a real model? | Evidence |
|---|---|---|---|
| Acquisition, checksums, provenance | IMPLEMENTED | n/a | `scripts/datasets/acquire.py`, `data/provenance/*.json`, `data/manifests/checksums.sha256` |
| Canonical adapters: RCAEval, Nezha, AIOps2025, RCA100 | IMPLEMENTED | n/a | `src/rca/adapters/{rcaeval,nezha,aiops2025,rca100}.py` |
| Adapters for the other catalogued sources (OpenRCA, LEMMA, GAIA, ...) | MISSING (by design) | n/a | `data/manifests/filelists/*.json` lists 18 sources; only 4 adapters exist |
| Quality states and invariants | IMPLEMENTED | n/a | `src/rca/quality.py:19-25,85-104`; `data/reports/quality-*.json` |
| Splits, eval units, exclusions | IMPLEMENTED | n/a | `src/rca/splits.py`, `src/rca/eval_units.py`; `docs/data_contract.md:146-193` |
| Missingness conditions (7 + `blind_nonroot_ev`) | IMPLEMENTED | mock only | `src/rca/ablate.py:19-63`; `src/rca/run_grid.py:212-250` |
| Logs-only, traces-only, no-telemetry states | MISSING | – | `src/rca/ablate.py:19` |
| Evidence builder (heuristic summary) | IMPLEMENTED | evidence built for 31 + 89 sampled incidents | `src/rca/evidence.py:218-290`; `results/canonical_pilot/evidence`, `results_prompt_stats/evidence` |
| Explicit candidate generator or shortlist | MISSING | – | candidates = all services (`src/rca/legacy_view.py:29`) |
| Retrieval BM25 / dense / hybrid | IMPLEMENTED (configs pin `tfidf`) | mock only | `src/rca/retrieve.py`; `configs/exp/dev-pilot.yaml:25` |
| LLM client: guided JSON, n samples, cache, server fingerprint | IMPLEMENTED | **No** | `src/rca/llm.py:82-170` |
| Raw completion and `reason` persistence | IMPLEMENTED 2026-10-18 (uncommitted); was MISSING at `fee95cf` | mock only | `src/rca/llm.py` (`raw_record`, `parse` keeps `reason`); `src/rca/run_grid.py` (`llm_raw.jsonl`) |
| Token logprobs | Persisted when `logprobs: true` (2026-10-18); no confidence estimator uses them yet (PARTIAL) | – | `src/rca/llm.py` (`compact_logprobs`) |
| Evidence visibility audit (eval-only) | IMPLEMENTED 2026-10-18 | synthetic tests; run on all four real sets 2026-10-19 ([04](04_evidence_visibility_results.md)) | `src/rca/visibility.py`; `tests/test_visibility.py` |
| Verbal, consensus and abstain-vote confidence | IMPLEMENTED | mock only | `src/rca/llm.py:206-227` |
| Recalibrated consensus (DEV-fitted) | DOCUMENTED_ONLY | – | `/plans/.../design/research-design.md:56,268`; no `isotonic`/`platt`/`recalib` in `src/` (grep) |
| Conformal or risk-controlled abstention | MISSING | – | grep in `src/` finds nothing |
| Scoring, weighted metrics, cluster bootstrap, sign-flip | IMPLEMENTED | mock only | `src/rca/score.py`; `src/rca/metrics.py` |
| Jev client, state allowlist, stage 1/2, fail-closed | IMPLEMENTED | **No live call**; `expected_model: null` | `src/rca/jev.py`; `src/rca/decide.py`; `configs/exp/dev-pilot.yaml:42` |
| Policy controls L0, L1, C1, C2, R1, R2, O | IMPLEMENTED | mock only | `src/rca/analyze.py:110-139`; `src/rca/gate.py:238-299` |
| C3 threshold, C4 learned policy, J-floor | PARTIAL (functions exist, not in `decision_report`) | – | `src/rca/gate.py:123-176,223-226`; used only by the legacy `--gate` path (`src/rca/analyze.py:249-256`) |
| Baselines B0 random, B1 max-z, B3 majority/alert | IMPLEMENTED | B0 and B3 on RCA100; **B1 not run** (empty evidence dir) | `src/rca/baselines.py`; `results_baselines_rca100/` |
| Baseline B2 BARO | DOCUMENTED_ONLY | – | `/plans/.../design/research-design.md:104`; no code in `src/` |
| Cost accounting | PARTIAL: LLM tokens and latency only; Jev usage and telemetry cost absent | – | `src/rca/decide.py:103-121`; `src/rca/gate.py:75-87` |
| GPU feasibility runner, serving profiles | IMPLEMENTED | **No** | `src/rca/feasibility.py`; `docs/gpu_deployment.md` |
| Preregistration | DOCUMENTED_ONLY (draft) | – | `/plans/.../design/preregistration.md:3,16-17` |
| Fine-tuning | DOCUMENTED_ONLY (gated) | – | `/plans/.../design/training-strategy.md` |
| Tests | IMPLEMENTED: 255 `def test_` functions counted | **Not re-run in this audit** (a hook blocks `.venv`); recorded result: 232 fast + 39 realdata passed | `tests/`; `/plans/.../decisions.md:8` |

## 3. Documentation and code mismatches

| Issue | Evidence |
|---|---|
| `gate.jev_payload` is cited as a model-facing entry point and as a TODO, but no such function exists | `README.md:74`; `docs/data_contract.md:198`; absent from `src/rca/gate.py` |
| README §3 still describes the old pilot (`Qwen2.5-7B-Instruct-AWQ`, `configs/pilot.yaml`) | `README.md:46`; superseded by `/plans/.../decisions.md:18,35` |
| The legacy `metrics.rank_of_truth` keeps the old `len(ranking)+1` miss rule. It is unused by the canonical path (which uses `score.correctness`) but still importable | `src/rca/metrics.py:8-11`; fixed rule at `src/rca/score.py:25` |
| "Cached raw outputs" was claimed as an artefact while only parsed samples were cached. Resolved 2026-10-18 (uncommitted) | `/plans/.../design/research-design.md:61` |
| Plan phase table: M1 done, M2 to M5 pending, M0 blocked | `/plans/.../plan.md:46-51` |

## Unresolved questions

- UNKNOWN: whether the live vLLM guided-JSON path reaches a parse rate ≥ 0.99 with Qwen3.5-4B in
  non-thinking mode. The feasibility test exists but has never run.
- UNKNOWN: whether TypeSafe accepts `criteria` on `noul` questions (`/plans/.../decisions.md:14`).
- UNKNOWN: how `results_prompt_stats/evidence` (89 files) was sampled. No config in the repo names it.
