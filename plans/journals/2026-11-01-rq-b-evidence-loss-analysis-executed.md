---
title: RQ (b) evidence-loss analysis executed
date: 2026-11-01
summary: "Phases 1-8 done: frozen codebook v1, analyzer (124 tests), confirmatory run, blind audit 12/12, results report; nothing committed"
---

# RQ (b) evidence-loss analysis executed

## What happened
- Executed plan 261031-2311 with /ak:cook --auto. Codebook v1 frozen locally by SHA256 (receipt kaggle/evidence-loss-prereg.json), analyzer plus 124 tests, calibration on 2 runs of case 99f095.
- Confirmatory run on S1 v2 and round 2: every scout number recomputed exactly; independent raw-data script matched; r2 vs S1 v2 labels agree 62/62 (determinism only).
- Blind LLM audit of 12 runs: 12/12 agreement on I0-I3 and first_loss_linear; 6 interpretation points, owner accepted all proposals, no deviation.
- Results (metric, main table without 99f095): S0_gt_span_absent 3/4, S2_root_label_lost_hit_kept 2/3, S4_inputs_present_not_rank1 1/4, S0_gt_span_present_not_queried 0/4; no_stage_implicated not triggered; within-case contrast not testable, so no causal stage claim. All outcomes were exposed before the freeze.
- Side findings: 8 productcatalogservice NO_ROWS queries come from model-typed timestamps off by 1e8-3e8 s (non-GT, no label effect); codebook text erratum on de6a50 s28 logged.

## Problems
- First phase 4/6 workflow died on the session limit; rerun cleanly.
- One agent could not write a report .md; saved from its returned text.
- A verifier claimed CRLF in frozen files; byte check showed 0 CR.

## Next steps
- Owner: Q7 (commit freeze point), Q9 (separate NO_KPI wording effect), LLM replay, second reader of another model family, whether to move the decision scripts out of runtime/.
- S1 v3 confirmation follows the phase 9 note when Kaggle finishes.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
