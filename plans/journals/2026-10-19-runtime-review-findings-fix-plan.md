---
title: Runtime review findings fix plan
date: 2026-10-19
summary: "All 7 runtime review findings confirmed against code; 8-phase fix + readiness plan written, no code edits"
---

# Runtime review findings fix plan

## What happened
Revalidated the 7 runtime review findings in `nt114-rca/nt114-rca/src/rca`, and all 7 were confirmed. In F1, the retrieval store under `evidence_dir/store` is not bound to the split. Configs share evidence dirs, so stale store files can expose held-out labels. F4 (lost precedent labels) cannot happen for RCAEval, whose 736 labels all name one service. It can happen on the AIOps2025 and RCA100 retrieval splits, which have node-level and set-only labels. F7 (miss rank n+1) only matters when an incident has 4 or fewer candidates.

The earlier CPU test run hit two kinds of problem. Its errors came from the sandbox (PermissionError on the pytest basetemp). The single F is most likely `test_feasibility.py::test_run_end_to_end_with_fake_server`, which depends on Git Bash coming before the WSL bash stub on PATH. That is a hypothesis: the progress ratio matches the 313-test `not realdata` selection, but nobody has rerun the test to confirm it.

## Decision
- Plan: `plans/261019-1800-review-findings-fixes-and-research-readiness/` (phases 00-07, plus a Q1-Q11 map and a Q4 paired-design proposal).
- Under prompt v1, precedents without a single service root are excluded from the store and counted; rendering them as sets would need a new prompt version.
- Resume refuses to append to a grid whose rows carry a different execution signature. The cache key stays unchanged.
- The miss rank becomes max(n, 5)+1, which leaves canonical ranks byte-identical.

## Next steps
Run phase 00 on the execution machine. After that, 01→02 run in sequence, alongside 03→05 and 04, and phase 06 is the readiness gate. The `ak` CLI was unavailable, so this entry was written by hand. AgentWiki publish skipped.
