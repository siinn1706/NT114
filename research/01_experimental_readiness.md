# 01 — Experimental readiness

Path convention as in [00](00_repo_audit.md): code paths are relative to `nt114-rca/nt114-rca/`;
paths that start with `/` are relative to the repository root.

## Executive summary

The data side is close to experiment-ready. Labels come with provenance and quality states, the
independent unit (the injection) is defined, and this audit re-verified the primary RCAEval split
as cell-held-out. The experiment side is not ready, for three reasons. First, no real-model run
exists. Second, the protocol is unfrozen. Third, three logging and accounting gaps would force a
GPU re-run or would bias cost claims: raw outputs are not stored, logprobs are dropped, and Jev
cost is not counted.

Two confounds need measuring before any missingness conclusion is drawn. One is the evidence
builder's root recall. The other is the weak `blind_root` manipulation, under which the root
stays named in the evidence through metrics and logs.

## Blockers that could invalidate conclusions

| # | Blocker | Why it can invalidate a conclusion | Evidence |
|---|---|---|---|
| 1 | No real-model data | Every hypothesis is untested; mock numbers are meaningless | `results_smoke_canonical/grid.jsonl` (106/106 rows `backend: mock`); `configs/exp/dev-pilot.yaml:1` |
| 2 | Raw completions and logprobs not persisted. **Addressed 2026-10-18 (uncommitted):** `llm_raw.jsonl` plus the cache value, configurable with `raw_outputs` | Without the fix, re-parsing, explanation audits and logprob or entropy confidence baselines would all need new GPU runs | `src/rca/llm.py` (`raw_record`, `request_meta`), `src/rca/run_grid.py` (`raw_output_row`); `tests/test_llm_raw.py` |
| 3 | Evidence omission. **Measured 2026-10-19** on all four full sets ([04](04_evidence_visibility_results.md)): unnamed in `full` for 2/218 RCAEval test, 17/97 Nezha, 9/86 RCA100, 20/318 AIOps2025 records; `no_metric` removes the name most often (69/86 RCA100, 93/304 AIOps2025) | Accuracy drops under missingness may track what the summariser omits. This is a stratum to report, not proof of a cause | §5 table; `src/rca/evidence.py:218,241,256,270`; `src/rca/visibility.py` |
| 4 | Gap claims rest on a journal-only literature corpus | Novelty framing and the choice of baselines may be wrong | `/plans/261011-1345-aiops-q1-literature-gap/work/q1-protocol.md:25` |
| 5 | Protocol not frozen; comparators and cost incomplete | DEV-to-test drift, a missing published baseline (BARO), and understated policy cost | `/plans/.../design/preregistration.md:3`; [00 §2](00_repo_audit.md#2-component-status) |

## 1. Ground-truth labels

| Dataset | Accepted records | Label source and granularity | Known label issues | Evidence |
|---|---|---|---|---|
| RCAEval (RE1/RE2/RE3) | 735 (703 ACCEPT, 32 with warnings, 1 REJECT duplicate) | Injection target from the case directory name plus `inject_time.txt`; service level; fault family | The label is encoded in the raw path (`label_in_path`). RE1 is metrics-only. Sock Shop has no traces, and 13 RE3-SS trace files are header-only | `docs/dataset_quality_audit.md:128-133,148-152`; `data/reports/quality-rcaeval.json` |
| Nezha | 101, **all** ACCEPT_WITH_WARNINGS | Fault lists stored next to the telemetry; service level | `BASELINE_CONTAMINATED` in 86/101 (the pre-window overlaps another injection), `LOW_COVERAGE` 66, `WINDOW_CLIPPED` 16, `PARSE_ERROR` 10 | `data/reports/quality-nezha.json` (`findings`) |
| AIOps2025 | 400; 318 tier A in `eval-only` | `start_time` anchor; 128 records are `MULTI_ROOT`, scored as sets | The campaign day predicts the fault type, so splits group by day and no fault-cell-held-out split exists | `data/reports/quality-aiops2025.json`; `docs/data_contract.md:151-174` |
| RCA100 | 103 tasks / 86 injections; tier A 86 / 70 | `answer_key/`; first firing alert as anchor (`anchor_kind: alert`) | 245 `LOW_COVERAGE` findings. The label-prior majority class scores 0.586 AC@1 (injection-weighted, tier A), so any method must beat it | `data/reports/quality-rca100.json`; `results_baselines_rca100/table_baselines.csv` |

- For tier A, the root is always in the candidate list. `ROOT_NOT_CANDIDATE` is a quarantine
  finding (`src/rca/quality.py:96-100`), and no dataset's quality report contains it.
- Service-alias sign-off (owner decision D6) is still open. The aliases are evidence-backed but
  await the owner's final review (`docs/dataset_quality_audit.md:261-263`;
  `/plans/.../decisions.md:52`). Wrong aliases would corrupt both scoring and candidate sets.
- Labels are injection targets. The repository does not measure whether the injected service is
  also the operational root in every case: UNKNOWN.

## 2. Dataset provenance and licences

- Provenance records, download manifests and checksums exist per source: `data/provenance/*.json`,
  `data/manifests/download_manifest.jsonl`, `data/manifests/checksums.sha256`, and the release
  `releases/nt114-data-v1.json`.
- AIOps2025 and RCA100 are non-commercial ("private transfer only"). Their evidence is withheld
  from the external Jev API until licence terms are verified (owner decision D3,
  `src/rca/decide.py:32-35`; `/plans/.../decisions.md:19`). Their Jev results therefore use a
  different state from RCAEval and Nezha, so cross-dataset Jev comparisons are not like-for-like.
- Pre-training exposure: Online Boutique and Train Ticket appear in many public sources, and
  Nezha (2023) is the oldest set (`docs/dataset_quality_audit.md:134-139`). No contamination
  probe exists in code: MISSING.

## 3. Train / validation / test separation

Re-verified in this audit by recomputing (system, root, fault family) cells from the eval-only
labels against the split assignments:

| Split | Test incidents sharing a cell with train | Val incidents sharing a cell with train | Repository claim |
|---|---|---|---|
| `within-rcaeval-grouped-0-e9b2c81c` (primary, D8) | **0 / 218** | 0 / 143 | 0/218 (`/plans/.../design/research-design.md:122-126`): **confirmed** |
| `within-rcaeval-retrieval-0-45ef97c3` (secondary E2b) | 140 / 144 | 138 / 140 | 138/144. The difference likely comes from the cell key (this audit omitted `lineage`); not material |

Confirmed side effects of whole-group stratified filling (`data/splits/within-rcaeval-grouped-0-e9b2c81c/split.json`, `counts`):

- 94 test incidents sit in strata that exist **only** in test. Examples: `sock-shop|disk-io` has
  40 test and 0 train incidents; `train-ticket|code-defect` has 30 test and 0 train.
- The fault mix of RCA-T therefore differs from STORE and DEV. Retrieval and DEV-tuned
  thresholds meet unseen fault families. This is intended (it makes the split cell-held-out), but
  results must be stratified by system × fault family.
- RCA-Z (train ∪ test, used for zero-shot RQ1–3) contains STORE incidents. That is valid only
  while nothing is fitted on them (`/plans/.../design/research-design.md:139-141`).

## 4. Baselines

| ID | Status | Evidence |
|---|---|---|
| B0 random (analytic) | Implemented; run on RCA100 | `src/rca/baselines.py:32-35`; `results_baselines_rca100/table_baselines.csv` |
| B1 max-z (evidence order) | Implemented; **never run**, because the RCA100 evidence directory is empty and nothing else was run | `src/rca/baselines.py:38-44,79-87` |
| B2 BARO | DOCUMENTED_ONLY | `/plans/.../design/research-design.md:104` |
| B3 majority / alert-entity (RCA100) | Run: 0.586 / 0.374 tier A; 0.477 / 0.304 for all 103 tasks | `results_baselines_rca100{,_all}/table_baselines.csv` |
| L0, L1, C1, C2, R1, R2, O | Implemented, mock only | `src/rca/analyze.py:110-139` |
| C3, C4, J-floor | Functions exist but are not wired into `decision_report` | `src/rca/gate.py:123-176,223-226` |

Missing comparators that matter for H1–H3: token-probability confidence (blocked by §6), a
recalibrated consensus, an agentic or tool-using LLM-RCA baseline (out of scope by
`/plans/.../design/research-design.md:261`), and a non-LLM multimodal RCA baseline. Whether any
published multimodal method can run on these sets is UNKNOWN.

## 5. Leakage and confound audit

**Controls that exist and are tested.** The visible zone and `VisibleCase` carry no label fields
(`src/rca/data.py:33-41`). The candidate shuffle is seeded by uid. Evidence files are label-free
(`src/rca/run_grid.py:229-250`). Jev states come from evidence plus aggregates only, and an
allowlist guards them (`src/rca/decide.py:140-151`; `src/rca/jev.py:117-125`). The oracle store
is refused in decisions (`src/rca/decide.py:62-64`). The headline guard refuses mock, DEV and
mixed-version rows (`src/rca/analyze.py:34-51`). Tests cover the canary, permutation invariance
and the Jev allowlist (`tests/test_leakage.py:77-237`).

**Residual risks (confirmed by reading the code):**

| Risk | Type | Evidence |
|---|---|---|
| The evidence window is centred on the label-derived injection time, so signals are cleaner than at real detection time | internal / external | `src/rca/evidence.py:25,225`; acknowledged at `docs/data_contract.md:124-127` |
| `blind_root` applies only when the root has spans, so the label selects the subset | construct | `src/rca/ablate.py:71-87` |
| Retrieval hits print the precedent's root and fault. On the retrieval split this is close to a label lookup (140/144 twins) | internal | `src/rca/retrieve.py:121-127`; §3 |
| The evidence lists services in z-score order, so the LLM can copy B1 | construct | `src/rca/evidence.py:235-246`. B1 must be reported next to every LLM number |
| The B3 majority class uses the scored set's own label prior | comparator | `src/rca/baselines.py:67-70` |

**Measured in this audit (cheap, eval-only).** Share of evidence variants whose text names the
true root as a `- <svc>:` line. The samples are small and of **unknown selection**
(`results_prompt_stats/evidence`, 89 incidents; `results/canonical_pilot/evidence`, 30 RCAEval
incidents). Treat them as a signal, not a result.

| Dataset (sample) | full | metrics_only | no_metric | blind_root |
|---|---|---|---|---|
| RCAEval (n=30 pilot) | 1.00 | 1.00 | 0.60 | 1.00 (n=20) |
| AIOps2025 (n=35–41) | 0.76 | 0.74 | 0.49 | 1.00 (n=7) |
| RCA100 (n=12) | 0.75 | 0.67 | 0.17 | 0.80 (n=10) |
| Nezha (n=4) | 1.00 | 0.75 | 0.75 | 0.75 |

Two implications follow.

1. On AIOps2025 and RCA100 the root is not named in about a quarter of the sampled `full`
   prompts. **Superseded 2026-10-19:** on the full sets the rates are 20/318 and 9/86
   ([04](04_evidence_visibility_results.md) §3); the samples overstated omission. This is **evidence omission**, not an accuracy ceiling. The root stays in the
   candidate list, so the model can still rank it first. Accuracy must be reported separately for
   named and unnamed cases ([02, H3](02_research_directions.md#h3--separating-candidate-generation-failures-from-candidate-ranking-failures)).
2. `blind_root` leaves the root visible through metrics and logs in every sampled RCAEval case.
   H1a and H1b may therefore show small effects, and the effects concern trace visibility only.
   The repository already states this (`/plans/.../design/research-design.md:74-83`).

The script used is outside the repository, at
`C:\Users\Siinn\AppData\Local\Temp\claude\F--Nam-UIT-NT114---NCKH\d8776131-dd82-42a4-ba0c-7ed4f55ce6c3\scratchpad\ev_recall.py`.

## 6. Metrics, cost accounting, reproducibility, logging

| Area | State | Gap | Evidence |
|---|---|---|---|
| Accuracy | AC@1/@3 (weighted, cluster CI); AC@5/Avg@5 only in the legacy table | The output is capped at 5 items, so rank > 5 is stored as `n+1` and the full rank curve is lost | `src/rca/analyze.py:85-107,162`; `src/rca/llm.py:50`; `src/rca/score.py:25` |
| Confidence | Brier, support-ECE, AUROC/AUPRC, AURC, selective risk, CW₁₀₀ | No recalibration, no conformal coverage guarantee | `src/rca/metrics.py:98-190` |
| Cost | Prompt and completion tokens and latency per arm; retrieve and escalate add the primary's cost | Jev usage and cost **excluded**; no telemetry-acquisition cost; no GPU-seconds or money | `src/rca/decide.py:103-121`; `src/rca/gate.py:75-87,111-112` |
| Reproducibility | Pinned model revisions, server fingerprint in the cache key, `manifest.json` (commit, dirty flag, bundle), lock file, write-once splits | vLLM batching and Jev are non-deterministic (results reproduce from caches only). Raw texts are not cached. The bundle is private (HF) | `src/rca/llm.py:97-105,151-170`; `src/rca/run_grid.py:388-413`; `/plans/.../design/research-design.md:253` |
| Result logging | Append-only JSONL with resume keys; Jev raw requests and responses in `jev_raw.jsonl`; failures listed in `jev_retry.jsonl` | LLM raw responses missing (the asymmetry with Jev) | `src/rca/run_grid.py:461-516`; `src/rca/decide.py:215-266` |
| Tests | 255 test functions | Not re-run in this audit; recorded 232 + 39 passed | `/plans/.../decisions.md:8` |

## 7. Confirmed problems vs risks that need experiments

**Confirmed (fixable without a GPU):**

1. Raw LLM completions and logprobs were not stored. Fixed 2026-10-18, uncommitted; see blocker 2.
2. Policy cost excludes Jev (`src/rca/gate.py:75-87`).
3. B1 has not been run; B2 and recalibration are documented only.
4. C3, C4 and J-floor are not wired into the reported policy table (`src/rca/analyze.py:110-139`).
5. The preregistration, prompt `v1` and Jev `q1-draft` are not frozen.
6. Alias sign-off D6 is open.
7. Stale doc references (`README.md:74`, `docs/data_contract.md:198`).
8. Literature gap claims are unverified against conference and arXiv work.

**Risks that need experiments (DEV first):**

| Risk | Test |
|---|---|
| A 4B primary model is near random on 30–60-candidate systems | DEV pilot AC@1 vs B0/B1 per system |
| Consensus collapses (most incidents 10/10 or 0/10), leaving AUROC and C1 with ties | Histogram of `conf_consensus` on DEV |
| Guided JSON parse rate < 0.99 | `rca.feasibility` on 12 DEV incidents |
| Accuracy differs between named and unnamed roots (evidence omission) | `python -m rca.visibility <cfg> --roles val test` on the real bundle (CPU only), joined to the DEV grid |
| `blind_root` effect ≈ 0 because metrics and logs still show the root | DEV ΔAC@1 and the share of `same_as_full` variants |
| Jev position bias or version drift | E8 rotations on DEV |
| Power: the MDEs are placeholders | Simulation from DEV discordance (`/plans/.../design/research-design.md:226-228`) |

## Unresolved questions

- How was `results_prompt_stats/evidence` sampled? This determines whether the §5 recall numbers
  generalise.
- Will the owner accept storing raw LLM completions in the private bundle? They may contain
  NC-licensed log text.
