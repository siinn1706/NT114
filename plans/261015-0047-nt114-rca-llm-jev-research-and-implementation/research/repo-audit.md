# Repository audit (2026-10-15)

Scope: `nt114-rca/nt114-rca/` at `main` `2cb1d7c` (clean), dataset plan
`plans/261014-0749-nt114-rca-dataset-standardization-and-validation/`, release
`nt114-data-v1-20261014-6fdd9835`, and the note `note/Kế hoạch triển khai ...md`.
Every claim below was read from source in this session unless marked otherwise.

Legend: **[F]** confirmed fact (file:line or command), **[R]** recorded by an earlier
report and not re-run here, **[A]** assumption.

## 1. What exists and can be reused

| Module | State | Reuse in this plan |
|---|---|---|
| `src/rca/store.py`, `legacy_view.py`, `splits.py`, `eval_units.py`, `ablate.py`, `evidence.py` | Done by the data plan; contract in `docs/data_contract.md` | Reuse unchanged (data layer is frozen) |
| `src/rca/run_grid.py` | `prepare` + `run`, canonical source, resumable JSONL, evidence/store fingerprints in result key **[F]** `run_grid.py:356` | Extend: escalation model, scoring via label set, run manifest, prompt version |
| `src/rca/llm.py` | vLLM HTTP client, JSON-schema guided output, `n` samples, SQLite cache, `mock` backend, `aggregate` (Borda, `conf_verbal`, `conf_consensus`, `abstain_vote`) **[F]** | Extend: prompt version and model revision in the cache key, thinking toggle, optional logprobs |
| `src/rca/retrieve.py` | BM25, dense (bge-small, TF-IDF fallback), hybrid RRF, `precedent`/`no_precedent` **[F]** | Reuse unchanged |
| `src/rca/gate.py` | Offline action table, reward, threshold, GBR "learned" policy, LOSO, a draft `jev_payload`/`jev_call` **[F]** | Keep comparators; move Jev to `jev.py`; fix payload |
| `src/rca/metrics.py` | AC@k, Avg@5, confident-wrong, ECE, AURC, selective acc, McNemar, i.i.d. bootstrap, Holm **[F]** | Extend with injection weights and cluster bootstrap |
| `src/rca/analyze.py` | Cell table, retrieval McNemar, gate table **[F]** | Extend: strata, primary/secondary separation, eval-unit join |
| `tests/` | 28 files; `test_leakage.py` checks `gate.jev_payload` state keys **[F]** | Extend |
| `schema.DECISION_STATE_ALLOWED_KEYS` | 5 keys **[F]** `src/rca/schema.py:39` | Extend by an explicit contract change (see architecture §4) |

Release counts **[R]** (`reports/release-handoff-nt114-data-v1.md`): RCAEval 735 accepted
(RE1 375 metrics-only, RE2 270, RE3 90), Nezha 101, AIOps2025 400 (tier A 318, 245 top-1, 73
set-scoring-only), RCA100 103 tasks / 86 injections (tier A: 86 tasks / 70 injections, verified from `eval-units-rca100.json` and the `eval-only-rca100` assignments this session). Condition applicability **[F]**
(read from `data/reports/condition-matrix-*.json`, counts only):

| Dataset | full | no_metric | no_log | no_trace | metrics_only | blind_root / blind_nonroot |
|---|---|---|---|---|---|---|
| RCAEval | 735 | 360 | 360 | 240 | 360 | 228 |
| Nezha | 97 | 97 | 97 | 97 | 97 | 97 |
| AIOps2025 | 400 | 384 | 384 | 361 | 384 | 83 |
| RCA100 | 103 | 103 | 103 | 103 | 103 | 86 |

Split sizes **[F]** (`data/splits/*/split.json`): `within-rcaeval-retrieval` 451/140/144
(train/val/test), `within-rcaeval-grouped` 374/143/218, `within-aiops2025-retrieval`
141/36/170, `within-rca100-retrieval` 69/15/19, `eval-only-*` = all tier-A,
`xdata-rcaeval-to-nezha` shares systems OB and TT; `xdata-rcaeval-to-{aiops2025,rca100}`
share none.

## 2. Prerequisite status

| Gate | Status | Evidence |
|---|---|---|
| Linux GPU portability (`verify_portability.sh` steps 0–5) | **Pending** | `reports/phase-12-portability.md` "Linux verification has not run"; release record "not yet accepted" **[F]** |
| Windows fast suite | 230 passed on 2026-10-14 **[R]**; not re-run here (project venv is blocked by a local hook, the system Python has no pytest) | `reports/phase-12-portability.md` |
| Service-alias owner review | Open (`reviewed_by: owner to confirm`) **[R]** | release handoff "Remaining blockers" 2 |
| GPU on the prep machine | None (`nvidia-smi` absent, no torch) **[F]** | this session |
| Jev account / key | Unknown **[A]** | `gate.jev_call` reads `JEV_URL`, `JEV_TOKEN` |

The data plan says training must not start until the Linux gate passes. This plan makes the
gate an M0 exit criterion for any GPU work, not only training.

## 3. Compatibility issues that this plan must fix (necessary, small, outside data prep)

| # | Issue | Evidence | Consequence if ignored | Fix (phase) |
|---|---|---|---|---|
| A1 | Jev payload uses `options: [...]` and a string `criteria`; the API needs `criteria` as a map option → description and has no `options` field | `src/rca/gate.py:157-179` vs `docs.typesafe.ai/api.md` | Every live call fails with 422 or silently ignores the action set | `jev.py` (M1) |
| A2 | Jev call has no `model` field, no version pin, no retry on 429/529, no cache | `gate.py:182-190` | `jev-latest` moves (1.14 shipped 2026-10-14), non-reproducible results, rate-limit crashes | `jev.py` (M1) |
| A3 | `legacy_view.truth()` returns only `primary_root_service`; for the 73 AIOps2025 set-scoring-only incidents it is `None`, so `rank_of_truth` scores them wrong | `src/rca/legacy_view.py:32-34`, `metrics.py:8` | Biased AIOps2025 accuracy | scoring module (M1) |
| A4 | `metrics.bootstrap_ci` resamples rows i.i.d.; `analyze.py` ignores `weight` and `injection_id` | `metrics.py:63`, `analyze.py:25` | RCA100 103 tasks treated as independent; violates protocol §2b.1 | stats module (M1) |
| A5 | `analyze.cell_table` mixes datasets and strata in one group-by key without dataset or coverage cause | `analyze.py:25` | Violates protocol §2b.4 | `analyze.py` (M1) |
| A6 | LLM cache key lacks a prompt version and the model's revision; model name only | `llm.py:84` | A prompt or weight change silently reuses stale answers | `llm.py` (M1) |
| A7 | `gate.leave_one_system_out` assumes ≥2 systems; AIOps2025 and RCA100 have one | `gate.py:137` | Comparator tuning undefined outside RCAEval | tune comparators on the RCAEval dev split only (M3) |
| A8 | Doc drift: `docs/data_contract.md` §8 says the `action_table` default is `no_precedent`; code default is `precedent` | `data_contract.md` §8 vs `gate.py:28` | Confuses readers; no runtime effect | docs fix (M1) |
| A9 | `canonical_pilot.yaml` serves `Qwen/Qwen2.5-7B-Instruct-AWQ`, a 2024 model | `configs/canonical_pilot.yaml:28` | Out-of-date baseline | new experiment configs (M2) |

None of these touch adapters, the canonical schema, splits or the bundle. The data layer stays
frozen.

## 4. What does not exist yet

- Any non-LLM RCA baseline in code (no BARO; grep `baro` returns nothing) **[F]**.
- An escalation path in `run_grid` (a second model is supported only as another grid row).
- A run manifest tying a result file to code commit, bundle id, model revisions, Jev version.
- A preregistered analysis plan.
- SFT export (left open by the data handoff §4).
