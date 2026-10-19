---
title: Single-LLM simplification plan completed (CPU only)
date: 2026-10-18
summary: "Phases 0-8 of 261018-2300 done: Jev removed, evaluation hardened, legacy data_root path retired; only Phase 0 committed"
---

# Single-LLM simplification plan completed (CPU only)

## What happened
- I executed plan `plans/261018-2300-single-llm-simplification-and-evaluation-hardening/` phases 0–8 under `/ak:cook --auto`. Everything ran on CPU, with no model calls.
- **V4** (`research/06_statistics_validation.md`): CI coverage was 0.930–0.955 and sign-flip type-I error was 0.025–0.041 on all five test structures. The bootstrap method is kept.
- **V5:** the paired AC@1 MDE at 20 % discordance is 0.10 for RCAEval `full` and 0.18 for the 52-injection `blind_root` ∩ `blind_nonroot_ev` intersection. H3 on that intersection is underpowered.
- **V6** (`research/05` §V6): RCAEval grouped store, 374 train files.
  - Max line-Jaccard is 0.455: no copying.
  - The nearest same-cell share is 0, which holds by construction: each (root, fault) cell lies in one split group.
  - 29 of 218 test `full` queries have a cross-cell neighbour with cosine ≥ 0.95. Retrieval is therefore reported stratified by max cosine.
- **Phase 7:**
  - The old Jev plan is marked partially superseded.
  - research/00–02 carry dated updates.
  - Protocol v2 gains §5.1, "Measured instrument facts".
- **Phase 8:**
  - Legacy-vs-canonical parity was confirmed empirically: text is identical in 52 of 52 shared pairs, and features agree within about 1e-13.
  - The golden test was ported to `tests/golden/canonical_synthetic_evidence.sha256`.
  - Removed: `data.discover_cases`, `data.load_case`, the legacy run_grid branches, `configs/pilot.yaml`, `configs/synthetic.yaml` and the legacy tests.
  - `load_cfg` now rejects non-canonical configs.

## Verification
- 309 non-realdata tests and 56 realdata tests pass.
- V1: 0 of 862 evidence files changed, and 1,236 of 1,236 are current.
- The markdown link check finds 0 broken links.

## Decision
- Only Phase 0 is committed (`b2dbb20`, tag `pre-single-llm`). Everything else is uncommitted and awaits owner approval.

## Next steps
- Owner decisions:
  - Relabel BARO-style?
  - Retire `blind_nonroot`?
  - Keep RCA100 `blind_root`?
  - Add a `main-ase.py` variant?
  - Fix the V6 strata in the preregistration?
  - Clean up `_smoke_rcaeval`?
- The DecompRCA release returns 404, which blocks V8 step 2.
- Per-phase commits are pending approval.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
