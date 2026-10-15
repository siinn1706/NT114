---
title: "Phase 2: M1 — Minimal offline end-to-end RCA LLM + Jev pipeline (CPU, no paid calls)"
status: done
priority: P1
effort: 7 person-days (weeks 1–2, 2026-10-19 → 10-30)
dependencies: []
---

# Phase 2: M1 — Minimal offline end-to-end RCA LLM + Jev pipeline

## Context links

[Architecture](design/architecture.md) §3–8 · [Jev verification](research/jev-api-verification.md) ·
[Repo audit](research/repo-audit.md) §3 (issues A1–A8) · `nt114-rca/nt114-rca/docs/data_contract.md`

## Goal and research justification

One command chain (`prepare → run → decide → analyze`) runs end to end on CPU with the mock LLM
and mock Jev. It produces correctly weighted, stratified tables on synthetic data and on a 2-per-
system sample of the real bundle. Every validity rule (injection units, set scoring, leakage,
version pinning, stale-cache refusal) is enforced by code and tests **before** any real model
output exists, so real results cannot be produced by a broken harness.

## Dependencies

None (runs on the Windows prep machine). Live Jev and GPU are not needed.

## Key insights

- `gate.jev_payload` is incompatible with the real API (A1, A2). Fix it before anyone calls Jev.
- Set-scored AIOps2025 incidents are currently always wrong (A3). Fix scoring before any AIO number.
- `metrics.bootstrap_ci` is i.i.d. (A4). Statistics must cluster on injections from day one.

## Tasks

1. **Hygiene.** Confirm the M0 `.gitignore` entries exist. Fix doc drift A8 in
   `docs/data_contract.md` §8.
2. **Scoring (`score.py`, `data.Truth`, `legacy_view.truth`).** `Truth` gains
   `root_ids: tuple[str, ...] = ()` and `granularity: str = "service"`. `score.correctness(ranking,
   truth, n_candidates)` returns `{rank, correct_at_1, correct_at_3, set_scored, parse_failed}`;
   set-scored = any member of `root_ids`. <!-- Red team F3 --> An empty ranking (all samples failed
   to parse) is **wrong**: `rank = n_candidates + 1`, `parse_failed = True`. Today
   `metrics.rank_of_truth([], t)` returns 1 and `run_grid` scores it as correct
   (`metrics.py:11`, `run_grid.py` `"correct": rk == 1`). `score.units(dataset)` loads `eval-units-<dataset>.json` (weight, injection_id,
   representative, coverage cause, excluded_from_primary).
3. **LLM (`llm.py`).** Add `PROMPT_VERSION = "v1"`, `model_revision`, `chat_template_kwargs`
   (`enable_thinking: false` by default), `max_tokens`, `logprobs` (off by default) and a
   **server fingerprint** to the request and the cache key. <!-- Red team F8 --> The fingerprint is
   the sha of (vLLM `/v1/models` response, the launch arguments written by
   `scripts/serve_model.sh`, and the T=0 answer to a fixed canary prompt), computed once per run
   and checked against the config's revision and quantisation; a mismatch stops the run. The
   mock backend's RNG is seeded from a fixed mock seed, not from the cache key, so key changes do
   not alter test fixtures. The prompt text stays unchanged until M2 freezes it.
4. **Grid (`run_grid.py`).** Models carry `role: primary|escalation|replication` and `revision`.
   Rows add `prompt_version`, `model_revision`, `model_role`, `sampling`, `truth_ids`,
   `label_granularity`; `correct`/`rank` come from `score.correctness`. Write
   `results/<exp>/manifest.json` (architecture §5). Result keys include the prompt version and
   model revision.
5. **Jev (`jev.py`).** `build_state(inputs) -> dict`: top-level keys must match
   `DECISION_STATE_ALLOWED_KEYS` exactly (the allowlist takes precedence); `schema.denylisted` runs
   only on **nested** keys under them. <!-- Red team F2 --> `denylisted("assistant_first_answer")`
   is True today (`schema.py:36,45-47`), so a recursive check over top-level keys would reject an
   allowed key. `_DENY_TOKENS` is never edited by this plan. Numbers are banded text; `build_questions(available_actions, stage) -> dict` with `criteria` maps;
   `order_options(questions, seed)`; `JevClient(model="jev-1.13.0", backend="live"|"mock",
   cache)` with `.decide(state, questions) -> JevResult`; one provider only, TypeSafe (`POST
   https://api.typesafe.ai/v1/systemone`). <!-- Red team F7 --> A Cloudflare/OpenRouter adapter is
   added only if D1 forces it and the route can pin `jev-1.13.0`. Retry and backoff on
   429/529/5xx; response validation and a version guard against the exact `model` string recorded
   in M0 (architecture §4.5); SQLite cache that stores **only validated 200 responses**, keyed by
   the observed response `model`; the deterministic `mock` backend.
6. **Schema contract.** Extend `schema.DECISION_STATE_ALLOWED_KEYS` with `assistant_ranking`,
   `assistant_flagged_insufficient`, `candidate_count`, `decision_stage`; update
   `docs/data_contract.md` §8 accordingly.
7. **Decisions (`decide.py`).** `python -m rca.decide <cfg>`: read `grid.jsonl` and the evidence
   files; build the action table and the decision inputs as specified below; for every incident × condition × Jev variant, call
   stage 1 and both stage-2 states; write `decisions.jsonl` and `jev_raw.jsonl`; raise on
   `oracle_store` rows. <!-- Red team F7 --> A decision row counts as done only when every stage
   status is `ok`; failed calls go to `jev_retry.jsonl` and are retried on the next run; a
   fail-closed `abstain` is applied only at analysis time to calls that still fail after the final
   retry pass.
   <!-- Red team F4, F5 --> `DecisionInputs` is built from the evidence file (`conditions[c].text`,
   availability) and the LLM aggregate fields (`ranking`, `conf_verbal`, `conf_consensus`,
   `abstain_vote`, `next_check`, `n_candidates`) and the top precedent similarity only. It never
   reads `truth`, `truth_ids`, `fault`, `correct`, `rank`, `hits[].root` or `hit_has_truth`. The
   action table is a new `decide.action_table` keyed on `(incident_uid, condition)` with optional
   arms selected by `model_role` and `retrieval`, filtered first to one `prompt_version` and
   `model_revision`, failing on duplicate keys. Jev's `accept` maps to the existing `answer`
   action name in one place. `gate.action_table` stays as it is for the comparators.
   `run_grid.Canon` accepts a list of split roles (`split_roles: [train, test]` for RCA-Z).
   <!-- Red team A5 --> `run_grid.prepare_canonical` adds the condition `blind_nonroot_ev`
   wherever `blind_root` applies: the non-root service present in the `full` evidence text with
   the number of evidence lines closest to the root's, ties broken by `sha256(uid + service)`. The
   target is written to `ablation_log.jsonl` (eval-only), never to the evidence directory. Each
   evidence record also stores, per condition, whether its text equals `full` (label-free).
8. **Policies (`gate.py`).** Move `jev_payload`/`jev_call` into `jev.py` (remove them from
   `gate.py`; update `test_leakage.py`). Add `jev_policy(decisions, variant)`, `jev_floor_policy`,
   `coverage_matched_threshold` (C1), `coverage_matched_random` (C2), `oracle_policy`;
   route-matched controls R1/R2 (research-design §5); C1 with randomised tie-breaking; `evaluate()`
   takes `weights`. <!-- Red team A1, A6 -->
9. **Statistics (`metrics.py`).** Weighted AC@k, ECE (equal-mass and equal-width), Brier, weighted
   AUROC/AUPRC, weighted risk–coverage and AURC, `cluster_bootstrap(values, clusters, weights, fn,
   paired=...)`, `sign_flip_test(diff_per_injection)`, `per_injection(df, value_col)`.
10. **Analysis (`analyze.py`).** Group by dataset × granularity × condition (× coverage cause);
    headline vs secondary tables; refuse mock rows, DEV rows and mixed `prompt_version` /
    `jev_question_version` in headline tables; policy table with CIs; `--smoke` flag for mock output.
11. **Configs.** `configs/exp/smoke-offline.yaml` (synthetic, mock LLM ×2 roles, mock Jev) and
    `configs/exp/smoke-canonical.yaml` (real bundle, `limit_per_system: 2`, mock backends).
12. **Tests** (below).

## Existing modules to reuse

`run_grid.prepare/load_evidence/exclusions`, `retrieve.CaseStore`, `gate.action_table/evaluate/
threshold_policy/learned_policy`, `metrics.*`, `tests/fixtures`, `conftest.canonical_synth`.

## File inventory (deep)

| File | Action | ~LOC | Test impact |
|---|---|---|---|
| `src/rca/score.py` | create | 120 | `test_score.py` |
| `src/rca/jev.py` | create | 300 | `test_jev.py` |
| `src/rca/decide.py` | create | 250 | `test_decide.py` |
| `scripts/serve_model.sh` | create | 30 | writes launch args for the server fingerprint |
| `src/rca/llm.py` | modify | +30 | `test_pipeline.py` (cache key) |
| `src/rca/run_grid.py` | modify | +80 | `test_run_grid_canonical.py` |
| `src/rca/gate.py` | modify | +100 / −45 | `test_decide.py`, `test_leakage.py` |
| `src/rca/metrics.py` | modify | +120 | `test_stats.py` |
| `src/rca/analyze.py` | modify | +150 | `test_decide.py` (smoke tables) |
| `src/rca/schema.py`, `data.py`, `legacy_view.py` | modify | +12 | `test_schema.py`, `test_legacy_compat.py` |
| `configs/exp/smoke-offline.yaml`, `smoke-canonical.yaml` | create | – | smoke runs |
| `docs/data_contract.md` §8, `.gitignore` | modify | – | – |

## Interfaces

```python
# score.py
def correctness(ranking: list[str], truth: Truth) -> dict          # rank, correct_at_1, correct_at_3, set_scored
def units(data_home: Path, dataset: str) -> pd.DataFrame           # uid -> weight, injection_id, representative, cov_logs, cov_traces, excluded

# jev.py
JEV_QUESTION_VERSION = "q1-draft"
def build_state(inp: DecisionInputs) -> dict                       # keys ⊆ DECISION_STATE_ALLOWED_KEYS
def build_questions(actions: tuple[str, ...], stage: str) -> dict
class JevClient:
    def __init__(self, provider="typesafe", model="jev-1.13.0", backend="live", cache=None, max_retries=6): ...
    def decide(self, state: dict, questions: dict, seed: str) -> JevResult   # action, probabilities, confidence, supported, option_order, model, status, usage, latency_s, cached

# decide.py
def decision_inputs(evidence_rec: dict, agg: dict, condition: str, top_sim: float | None) -> DecisionInputs   # never reads a grid row
def action_table(rows: pd.DataFrame, prompt_version: str, revisions: dict) -> pd.DataFrame          # keyed (incident_uid, condition); optional arms; fails on duplicates
def run(cfg: dict) -> None                                          # writes decisions.jsonl, jev_raw.jsonl
```

## Test scenario matrix (deep)

| Priority | Scenario | Test |
|---|---|---|
| Critical | Permuting the **label store** and rerunning `prepare → run (mock) → decide (mock Jev)` end to end leaves every Jev request sha unchanged (extends `test_leakage.py:96`) | `test_leakage.py::test_jev_states_label_permutation_invariant` |
| Critical | A canary placed in `truth`, `hit_has_truth` and `hits[].root` never appears in `jev_raw.jsonl` requests | `test_leakage.py::test_canary_not_in_jev_requests` |
| Critical | `assistant_first_answer` passes; a nested `{"telemetry_available": {"root": ...}}` raises; `_DENY_TOKENS` unchanged | `test_jev.py::test_state_allowlist` |
| Critical | Empty ranking is wrong with rank n_candidates + 1 and `parse_failed` | `test_score.py::test_empty_ranking_is_wrong` |
| Critical | Duplicate `(incident_uid, condition)` rows for one prompt version/revision make `decide` fail | `test_decide.py::test_duplicate_rows_fail` |
| High | Error responses are not cached; a row with a failed stage is retried on resume | `test_jev.py::test_errors_not_cached`, `test_decide.py::test_resume_retries_failed` |
| High | Server fingerprint mismatch stops `run`; embedder kind is in `store_fp`; a TF-IDF fallback under a dense config fails | `test_pipeline.py::test_server_fingerprint`, `test_run_grid_canonical.py::test_embedder_kind_pinned` |
| Critical | Payload matches the API: `model`, `criteria` map for choice, noul shape; no `options` field | `test_jev.py::test_payload_shape` |
| Critical | Version mismatch in a response stops the run | `test_jev.py::test_version_guard` |
| Critical | Set-scored AIOps2025 record is correct when the answer is any member of `root_ids` | `test_score.py::test_set_scoring` |
| Critical | Cluster bootstrap on duplicated records equals the bootstrap on one record per injection | `test_stats.py::test_cluster_bootstrap_invariance` |
| High | 429 then 200 retries and succeeds; 422 does not retry | `test_jev.py::test_retry_policy` (fake HTTP server, as in `test_pipeline.py`) |
| High | Error status → `abstain` + flagged; error rate reported | `test_decide.py::test_fail_closed` |
| High | Cache hit makes no HTTP call; changed question version misses the cache | `test_jev.py::test_cache_key` |
| High | `decide` raises on `oracle_store` rows | `test_decide.py::test_rejects_oracle_rows` |
| High | Options unavailable for a dataset are absent from criteria | `test_jev.py::test_available_actions` |
| High | `analyze` refuses mock and DEV rows in headline tables | `test_decide.py::test_headline_guards` |
| High | Changing `PROMPT_VERSION` or model revision changes the LLM cache key and result key | `test_pipeline.py::test_cache_key_versions` |
| Medium | Option order is deterministic per (uid, condition, stage) and logged | `test_jev.py::test_option_order` |
| Medium | C1 with randomised tie-breaking hits the target coverage exactly per draw; its reported value is the mean over 1,000 seeded draws | `test_stats.py::test_coverage_match` |
| High | `blind_nonroot_ev` target is label-free except for excluding the root, deterministic, appears in the `full` evidence, and is logged only in `ablation_log.jsonl` | `test_run_grid_canonical.py::test_blind_nonroot_ev` |
| Medium | Route-matched controls R1/R2 reproduce J's per-action rates | `test_stats.py::test_route_matched` |
| Medium | Weighted ECE/AUROC equal the unweighted ones when all weights are 1 | `test_stats.py` |
| Medium | End-to-end smoke on synthetic data produces all tables | `test_decide.py::test_smoke_end_to_end` |

## Verification commands

```bash
cd nt114-rca/nt114-rca
PYTHONPATH=src python -m pytest -q -m "not realdata"
PYTHONPATH=src python -m pytest -q tests/test_leakage.py tests/test_jev.py tests/test_score.py tests/test_stats.py tests/test_decide.py
# synthetic end-to-end (commands at the top of configs/exp/smoke-offline.yaml)
PYTHONPATH=src python -m rca.run_grid prepare configs/exp/smoke-offline.yaml
PYTHONPATH=src python -m rca.run_grid run     configs/exp/smoke-offline.yaml
PYTHONPATH=src python -m rca.decide           configs/exp/smoke-offline.yaml
PYTHONPATH=src python -m rca.analyze results_smoke/grid.jsonl --decisions results_smoke/decisions.jsonl --smoke
# real bundle, mock backends, 2 incidents per system
RCA_DATA_HOME=<bundle>/parts PYTHONPATH=src python -m rca.run_grid prepare configs/exp/smoke-canonical.yaml
```

## Acceptance criteria / Definition of Done

- [x] All fast tests pass (≥ the current 230 plus the new ones), and no test was weakened
- [x] The synthetic end-to-end chain runs with zero network access (sockets blocked in the test)
- [x] The canonical smoke runs on the real bundle for all four datasets (2 per system) with mock backends
- [x] Issues A1–A6 and A8 closed, each with a test; parse failures scored wrong
- [x] No live Jev or LLM call was made in this phase
- [x] `docs/data_contract.md` §8 matches the code

## Risks

| Risk | Mitigation |
|---|---|
| Changing `Truth` breaks legacy callers | New fields have defaults; `test_legacy_compat.py` and `test_legacy_golden.py` must stay green |
| `gate.action_table` assumes one big model | Generalise via `model_role`; keep the old signature as a thin wrapper |
| Scope creep into the data layer | Out-of-scope list in architecture §8 |

## Security

No secrets in configs; the client reads `TYPESAFE_API_KEY` from the
environment and never logs headers. `jev_raw.jsonl` stores bodies, not headers.

## Next

Phase 03 needs this phase done plus phase 01 tasks 1–4.
