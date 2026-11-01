---
title: RQ (b) evidence-loss plan
date: 2026-10-31
summary: "Hard-mode plan for locating where RCLAgent loses evidence under no_metric; red-teamed, validated, owner decisions recorded"
---

# RQ (b) evidence-loss plan

## What happened
Wrote a hard-mode plan at plans/261031-2311-rclagent-evidence-loss-analysis/ (9 phases, 32h, CPU only) for RQ (b): at which stage RCLAgent loses evidence when metrics are missing. Three scouts covered the S1 v2 and round-2 zips, the author's coordinator.py, and the attribution literature.

## Key findings that shaped the plan
- The evidence path is not linear. The final prompt sees the root consolidation report, the full Global Evidence Graph and the string-matched hint (coordinator.py 465-503), so a single "first stage lost" label over-blames consolidation. The plan uses an indicator vector I0-I5 per run instead.
- R@1 is identical across the 3 seeds in 7 of 8 cases, so the threshold-based rule for choosing X's target could never fire. The rule became descriptive, with not_testable and no_stage_implicated as valid outcomes.
- Validation caught 11 wrong claims, all fixed: attempt is 0-based; tool_result_budget exists only for search_logs; metric and no_metric diverge at request 3-7, not 1-2. check-plan.py returns VERIFIED.

## Decision
The owner chose: one blind agent as the second coder, do not wait for S1 v3, no LLM replay, and a descriptive rule with no thresholds.

## Next steps
Start phase 1 (codebook draft and exposure statement) via /ak:cook. Q7 (freeze commit and branch base) is still open. Nothing is committed.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
