---
title: Fix blockers before the train-split run
date: 2026-10-27
summary: "Six-phase plan done: batch harness and 5-trace pilot package verified on CPU; run_grid runs on the train role; integrity fixes with red-then-green tests."
---

# Fix blockers before the train-split run

## What happened
- Harness: search_logs budget now split per model response (floor(2048/n)); n=1 unchanged byte-for-byte. Requirements file complete; KNOWN_SERVICES read from upstream; ladder parses once.
- Batch runner: one subpackage per trace, per-trace caps and deadline, progress.json with resume and failed-trace recording. The v8 package regenerated in the new layout is byte-identical (9 files). Pilot of 5 train traces (130 spans, 3,528 endpoint comparisons) promoted; verify-package pass. No GPU run yet.
- Scan scripts share re2ob-endpoint-common.py; 450-trace outputs byte-identical except the wall-clock elapsed_seconds line.
- nt114-rca: train-role retrieval allowed (own incident and group excluded at search time); stray evidence ignored; split and condition matrix pinned to the current build; node-only train queries excluded and recorded (aiops2025 29, rca100 17); partial normalize refuses a full build; an unextracted AIOps2025 day archive stops normalize; RCA100 times without an offset fail the incident (real data all carry +08:00); LLM parse dedupes rankings and rejects malformed confidence and shapes; safe_extract verifies sha256 and rejects receipt-name and case collisions; analyze blocks train rows from headlines.
- Checks: harness 29, budget 11, T4 4 OK; pytest not-realdata 447 passed; verify-splits 16/16; verify-bundle OK.

## Decision
- uniqueItems not added to the vLLM schema: a schema change forces a PROMPT_VERSION bump and invalidates every cache key; dedupe in parse and aggregation instead.
- No canonical data regeneration needed: the offset and extraction fixes do not change outputs on the real data.

## Next steps
- Owner approval for the 5-trace Kaggle pilot (the 45-span trace may hit the 1,800 s deadline).
- Owner approval to commit on feat/rclagent-harness-budget-guard; never merge to main.
- The next prep extract re-extracts all AIOps2025 days once (old receipts lack archive_sha256).

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
