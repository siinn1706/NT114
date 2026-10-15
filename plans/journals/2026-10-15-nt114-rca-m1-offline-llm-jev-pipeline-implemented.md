---
title: NT114-RCA M1 offline LLM + Jev pipeline implemented
date: 2026-10-15
summary: "Phase 02 done on CPU with mocks; scoring bug fixed; phase 03 blocked on GPU, Jev key and owner decisions"
---

# NT114-RCA M1 offline LLM + Jev pipeline implemented

## What happened
Phase 02 (M1) of `plans/261015-0047-nt114-rca-llm-jev-research-and-implementation` is implemented on the Windows prep machine, CPU only, with the mock LLM and mock Jev.
- New: `src/rca/score.py`, `jev.py`, `decide.py`, `scripts/serve_model.sh`, `configs/exp/smoke-offline.yaml`, `smoke-canonical.yaml`.
- Modified: `llm.py` (prompt version, revision, thinking-off template kwargs, server fingerprint in the cache key), `run_grid.py` (roles, scoring, manifest, split-role lists, `blind_nonroot_ev`, embedder kind in `store_fp`), `gate.py` (Jev policies; C1/C2, R1/R2 and oracle controls; weighted vectorised `evaluate`), `metrics.py` (weighted ECE/Brier/AUROC/AUPRC/AURC, cluster bootstrap, sign-flip test), `analyze.py` (strata, headline guards, policy table), `schema.py` (allowlist), `data.Truth`, `legacy_view.truth`, `docs/data_contract.md` §8.
- Tests: the fast suite went from 191 to 233 passed; the realdata suite passed (39). Both smoke chains ran end to end, the second on the real data for all four datasets.

## Bug found
`score.correctness` first gave a miss the rank `len(ranking)+1`, the same rule as the legacy `rank_of_truth`. A one-item wrong answer then had rank 2 and counted as correct@3. Misses now get rank `n_candidates + 1`.

## Environment
- A hook blocks `.venv`, and the system Python has no pytest, so tests ran in a scratch venv built from `requirements-lock.txt` (core packages only, no torch or sentence-transformers).
- Bash heredocs that contained quote-heavy Python failed to parse, so edit scripts were written to the scratchpad and run as files.

## Decision
Logged in the plan's `decisions.md`:
- the miss-rank scoring rule;
- how the `blind_nonroot_ev` target is chosen;
- explicit `embedder: tfidf`, with a fallback from a dense model stopping the run;
- `decide` refuses grids that contain oracle-store rows;
- the `noul` question is sent with criteria, to be confirmed by the M0 smoke call.

## Next steps
- Phase 01 owner items:
  - run the Linux gate from the `cd96e9e` worktree;
  - record the GPU tier;
  - probe the model cards;
  - get a TypeSafe key and record the exact response `model` string (by 2026-10-30);
  - decide D1–D8;
  - record researcher availability.
- Phase 03 (GPU) starts after these. No commit has been made yet.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
