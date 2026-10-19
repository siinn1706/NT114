---
title: "Phase 07: Research extensions (owner gate)"
status: pending
priority: P3
effort: per extension, after owner selection
dependencies: [phase-06]
---

# Phase 07: Research extensions (owner-gated)

Nothing here is a correctness fix. Each item starts only after phase 06 and an explicit owner
decision recorded in the single-LLM `decisions.md`. The question-by-question map is in
[design/research-question-map.md](design/research-question-map.md).

| Item | Questions | Needs | Owner decision |
|---|---|---|---|
| X1 Q1 confirmatory path | Q1 | Phase 05 estimators, DEV pilot, SESOI | SESOI 0.05; family (H1-primary, E3, E1 on `full`) |
| X2 Raw-support instrument | Q4, Q10, Q7 | New eval-only module that scores root signal in raw telemetry per modality, independent of the evidence text | Approve instrument definition and validation sample |
| X3 Summarizer arms | Q4, Q2 | Evidence builder variants as new fingerprints (never replacing v1 evidence) with controlled token budgets | Approve new arms; frozen v1 evidence stays the primary arm |
| X4 Sample-count curve | Q9 | Post-hoc subsampling of the n = 10 raw samples (k = 1…10), no new model calls | None beyond X1 (exploratory) |
| X5 Natural vs masked missingness | Q11, Q6 | Matched comparison of naturally metrics-only RCAEval injections vs `metrics_only` on multimodal ones | Approve matching variables |
| X6 Candidate-set decomposition | Q3 | Full-ranking prompt arm (new prompt version) and visibility `in_candidates` | New prompt version; position against the decomposition paper |
| X7 Cross-cell stability score | Q5 | Agreement of top-1 across evidence variants of the same incident | Whether a score built from several calls of the same model is admissible under "abstention is a rule on that same call's outputs" |
| X8 Set-valued precedents | – | Prompt version rendering root sets | Only if AIOps2025/RCA100 retrieval arms are wanted |
| M4 Fine-tuning | RQ6 | `sft_export.py`, `scripts/train_lora.py` (do not exist) | Gate in `261015-0047/phase-05-m4-gated-fine-tuning.md`; out of this plan |

Q8 is answered by the owner's decision (single LLM; no stronger-model call). Its remaining
single-model part (spend tokens on evidence, samples or abstention) is covered by X3, X4 and the cost
ledger.
