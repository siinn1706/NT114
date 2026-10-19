---
title: Elicit literature review selects narrowed H1 for NT114
date: 2026-10-19
summary: "Executed plan 261019-1045: Elicit quota exhausted by one review, remaining rounds on arXiv/OpenAlex; H1 narrowed recommended, H2/H3 pre-empted, power is the main H1 risk"
---

# Elicit literature review selects narrowed H1 for NT114

## What happened
- Executed the Elicit literature-review plan 261019-1045 end to end (CPU only, no model runs, no commit).
- One thorough Elicit systematic review (SR1) consumed 0 -> 24 -> 100 % of the monthly quota; SR1 paused at extraction (144/551 rows). `useFigures` is not in the plan; `search_papers` cap is 300 and it is blocked once quota is exhausted. Elicit is unavailable until 2026-11-18T16:00Z.
- Remaining search, snowball and gap rounds ran on arXiv API, OpenAlex and Crossref: 2,255 records -> 1,958 works; 35 full texts read; 53 findings with 11 fields each; verify-report.py passes; 10/10 spot checks match.
- Manual 10 % screening check of SR1: 119/127 agree, kappa 0.846, all disagreements Elicit over-inclusions.

## Decision (recommendation, not frozen)
- H1 narrowed is recommended: matched-coverage selective risk of the call's own confidence under controlled telemetry removal on public fault-injection benchmarks. Closest prior work: LM-PACE (ECE only, private), TelemetrySuffBench (synthetic agent traces), Nautil (case files), CoreSec (non-LLM).
- H2 overlap exists (TraceBudget, VerifyRCA, BudgetSRE; quality flags on the first two). H3 overlap exists (DecompRCA NeurIPS 2026; repo still 404).
- Main H1 risk is power: verbal-confidence AUROC 0.51-0.65 implies about 0.02-0.06 selective-risk gain at coverage 0.7, below the RCAEval MDE 0.10.

## Corrections found during execution
- Earlier notes on SR1 screening (333/934) were wrong; export says 877/390.
- DecompRCA Retrieval@15 on RE1-TT is 0.91 for the +stc pipeline retriever (0.98 is magnitude-only).

## Next steps
- DEV pilot measuring consensus AUROC and discordance before filling protocol v2 section 9.5 (proposal in report section 12).
- Re-run the H1 gap query on Elicit after 2026-11-18.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
