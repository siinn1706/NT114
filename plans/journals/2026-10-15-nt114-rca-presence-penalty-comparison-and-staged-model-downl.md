---
title: NT114-RCA presence-penalty comparison and staged model downloads
date: 2026-10-15
summary: Pushed the deployment kit; added a presence_penalty option and a DEV comparison with a fixed decision rule; downloads staged
---

# NT114-RCA presence-penalty comparison and staged model downloads

## What happened
- Pushed 291923e and a7b8441 after the safety scan (fast-forward, not merged).
- The pinned Qwen3.5-4B repo has no generation_config.json, so the current requests use vLLM's neutral defaults (presence penalty 0). The 0 arm therefore equals the current configuration.
- Added a `presence_penalty` model option. It enters the cache key, row key and manifest only when set, so earlier keys stay valid. Rows also gain `conf_verbal_sd`.
- Added `configs/exp/dev-sampling.yaml` (143 DEV incidents, full and no_metric, two retrieval settings, two arms) and `rca.feasibility compare-sampling`. Its decision rule is fixed in code: keep 0 unless 1.5 has a parse rate of at least 0.99, an incident-cluster CI gain above 0, and at most 25 % more tokens.
- Downloads are staged: primary and fallback first, then AWQ, with 9B NF4 only if needed.

## Evidence
- 267 fast and 40 real-data tests pass. No GPU, Jev or training run.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
