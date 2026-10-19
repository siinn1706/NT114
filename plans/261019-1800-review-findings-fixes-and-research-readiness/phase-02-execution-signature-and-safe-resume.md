---
title: "Phase 02: Execution signature and safe resume"
status: completed
priority: P2
effort: 1 d
dependencies: [phase-01]
---

# Phase 02: Execution signature (F2)

## Context

- Grid and raw key (`run_grid.py:575-577`): model, revision, prompt version, incident, condition,
  retrieval, store mode, evidence_fp, store_fp, optional presence penalty.
- `LLM.key` (`llm.py:103-111`) already hashes model, revision, backend, n, temperature, seed,
  max_tokens, prompt version, chat_template_kwargs, logprobs, server_fp, messages, candidates and
  optional presence penalty. Cache reuse is therefore safe; grid and raw resume are not.
- `write_manifest` rewrites `manifest.json` from the latest config, so a grid that mixes settings is
  described as homogeneous.
- `guard_headline` refuses mixed `model_revision` and `server_fp` within a model, but not sampling.
- No real-model rows exist yet (DEV pilot not run), so no migration of old grids is needed.

## Design

- `LLM.execution_signature() -> dict`: every output-affecting setting:
  `model, revision, backend, prompt_version, n, temperature, seed, max_tokens, chat_template_kwargs,
  logprobs, presence_penalty, server_fp`. `server_fp` already covers the served model list, launch
  args (quantization, max-model-len, etc.) and the T=0 canary. `exec_sig` = first 16 hex of
  sha256 of its canonical JSON.
- The cache key stays as is (`test_cache_key_and_old_entries_unchanged` must keep passing).
- Grid and raw key = current key + `|sig=<exec_sig>`; the `pp=` suffix is dropped because the
  signature carries it.
- Resume rule: before writing, read existing grid rows of this model; if any carries another
  `exec_sig`, raise and name the differing fields (from the stored `execution` dict). Use a new `out`
  path for a new configuration. Same signature → idempotent skip as today.
- Rows and raw records carry `exec_sig` and `execution` (the dict). `sampling` gains `max_tokens`.
- Manifest v3: per model `exec_sig` and `execution`; `store` block from phase 01; `manifest_version: 3`.
- `guard_headline`: mixed `exec_sig` within a model is refused.

## Files

- Modify: `src/rca/llm.py` (signature method), `src/rca/run_grid.py` (key, resume check, rows,
  manifest), `src/rca/analyze.py` (`guard_headline` only; coordinate with phase 05, which also edits
  `analyze.py`: land this one-line guard first or inside phase 05).
- Tests: `tests/test_run_grid_canonical.py`, `tests/test_llm_raw.py`, `tests/test_reproduce.py`
  (manifest), `tests/test_analyze.py` (guard).

## Regression tests

1. Parametrised over `n_samples`, `temperature`, `seed`, `max_tokens`, `presence_penalty`,
   `chat_template_kwargs`, `logprobs` (mock backend): run once, change one setting, rerun into the same
   `out` → raises naming that field; grid row count unchanged.
2. Same config twice → second run adds 0 grid rows and 0 raw rows.
3. Changing the mock `server_fp` (monkeypatched) → refused.
4. Raw record key equals grid key and carries `exec_sig`.
5. Manifest records `exec_sig` per model; `config_hash` still present.
6. `guard_headline` refuses a frame with two `exec_sig` values for one model.
7. Existing cache tests unchanged.

## Acceptance

- [ ] Tests 1-6 fail before and pass after; test 7 passes unchanged.
- [ ] `tests/test_run_grid_canonical.py::test_rerun_is_idempotent` still passes.
- [ ] The DEV-pilot and DEV-sampling configs write to different `out` paths (already true) and their
      signatures differ only in `presence_penalty`.

## Risk and rollback

- Risk: refusing on mismatch breaks a workflow that intentionally appends sweeps to one grid. The
  protocol treats sweeps as independent runs, so separate `out` paths are the contract. Rollback:
  revert the commit; existing mock grids must be regenerated (they are disposable).
