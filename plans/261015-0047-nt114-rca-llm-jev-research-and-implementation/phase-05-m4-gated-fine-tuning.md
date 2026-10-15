---
title: "Phase 5: M4 — Gated fine-tuning (optional; runs only if the week-6 gate passes)"
status: todo
priority: P3
effort: 6 person-days + ~2 GPU-days (weeks 7–8, 2026-11-30 → 12-11), or 0 if gated out
dependencies: [phase-04]
---

# Phase 5: M4 — Gated fine-tuning

## Context links

[Training strategy](design/training-strategy.md) · [Research design](design/research-design.md) §2 (RQ6) ·
handoff §2b.2 (training only from train-role records)

## Goal and research justification

Test whether QLoRA/LoRA SFT on train-role incidents changes accuracy **and** overconfidence on
held-out fault cells and on another dataset. The motivation is scientific (does SFT worsen
calibration under missingness?), not a speed-up. The minimum paper does not depend on it.

## Gate (all must hold; decided and logged at the week-6 checkpoint)

1. Phase 04 DoD met. 2. Zero-shot DEV AC@1 in [1.5 × random, 0.85]. 3. ≥ 3 weeks to the
submission freeze. 4. A tier M/L GPU is available for ≥ 2 days. If the gate fails, mark this phase
`cancelled` with the reason and move its time to phase 06.

## Tasks

1. `sft_export.py`: from `within-rcaeval-grouped` train-role evidence (all applicable
   conditions), write chat JSONL with the frozen prompt v1 and the target JSON (`ranking[0]` =
   truth; the other items are the base model's own order; confidence tokens masked from the loss).
   DEV = the split's val role.
2. `scripts/train_lora.py`: QLoRA (tier M) or LoRA bf16 (tier L), rank 16, α 32, lr ∈ {1e-4, 2e-4},
   ≤ 3 epochs, early stop on DEV loss; pinned library versions in a training lock file.
3. Serve base + adapter in vLLM (`--enable-lora`); rerun E1 (no retrieval) on
   `within-rcaeval-grouped` test (218) and `xdata-rcaeval-to-nezha` test (97); then Jev (J-full).
4. Compare SFT vs zero-shot on the same incidents: ΔAC@1, Δgap, ΔAUROC, Jev CWA₁₀₀ (paired,
   cluster bootstrap); exploratory (not in the Holm family).

## Files

| File | Action |
|---|---|
| `src/rca/sft_export.py`, `tests/test_sft_export.py` | create |
| `scripts/train_lora.py`, `requirements-train.lock` | create |
| `configs/exp/sft.yaml` | create |

## Tests

| Priority | Scenario | Test |
|---|---|---|
| Critical | No val/test/eval-only uid, and no incident sharing a group with them, appears in the export | `test_sft_export.py::test_train_role_only` |
| Critical | Export prompt is byte-identical to the inference prompt v1 | `test_sft_export.py::test_prompt_identity` |
| High | Confidence tokens are masked (labels = -100) | `test_sft_export.py::test_confidence_masked` |

## Acceptance criteria / Definition of Done

- [ ] Gate decision logged (run or cancelled)
- [ ] If run: adapter pinned by hash; SFT vs zero-shot table with CIs on both test sets; Jev rerun
- [ ] Results labelled exploratory and kept out of the confirmatory table

## Risks

| Risk | Mitigation |
|---|---|
| Over-fitting to 3 systems | Cell-held-out test + cross-dataset test; report both |
| Quantisation mismatch (QLoRA trained, served at another precision) | <!-- Red team B10 --> Serve the SFT model at the training base precision **and** rerun the zero-shot baseline at that same precision, so the comparison holds precision fixed |
| Δgap is a by-product of moving accuracy with an untrained (masked) confidence | <!-- Red team A9 --> Report Δgap conditional on Δaccuracy and recalibrated ECE (DEV map); frame the claim as "SFT changes accuracy without updating confidence" unless calibration moves after recalibration |
| Time overrun | Hard stop at the end of week 8; partial results go to the appendix or are dropped |

## Next

Phase 06.
