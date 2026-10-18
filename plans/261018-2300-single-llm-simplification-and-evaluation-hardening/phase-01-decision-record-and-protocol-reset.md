---
title: "Phase 1: Decision record and protocol reset (documents only)"
status: done
priority: P1
effort: 1 d
dependencies: [phase-00]
---

# Phase 1: Decision record and protocol reset

## Context

[Old research design](../261015-0047-nt114-rca-llm-jev-research-and-implementation/design/research-design.md)
§2, §5, §7 and §9 · [scout report](research/scout-report.md) §1–2.

## Goal

Write down, before any code changes, what the single-LLM study can and cannot claim. Then the
refactor in phase 02 deletes only what the new protocol does not need.

## Requirements

1. **Decision log.** Record that D1 is reversed and D3 is moot. Add the owner's answers to the
   validation questions in [plan.md](plan.md#validation-gate-critical-questions).
2. **Protocol skeleton** (`design/protocol-v2.md`). It records the single-LLM invariant from
   plan.md and lists the measurement endpoints, which do not depend on any hypothesis:
   - accuracy: AC@1 to AC@5 (exact) and MRR@5. The top-5 cap of prompt `v1` is kept, so ranks
     beyond 5 are right-censored. No exact mean rank is ever reported;
   - confidence quality (Brier, ECE on the support, gap, AUROC/AUPRC with positive = wrong);
   - selective metrics (risk–coverage, AURC, selective risk at 0.5/0.7/0.9);
   - cost per incident;
   - validity strata (dataset, granularity, condition, modality regime, coverage cause,
     `named`, `same_as_full`).

   It states that the confirmatory family, the hypotheses and the MDE targets stay **open slots**
   until the literature review. Old H1a–H3b are kept as candidate contrasts and are not
   committed to. H4b, H4c and H5 are retired.
3. **Comparator table v2.** Keep B0, B1, B3, L0 and L1. Add "BARO-style" as a conditional
   baseline. It becomes B2 only after the equivalence tests of phase 05 pass. Add B1m, the
   evidence-order baseline. Keep C1 (coverage-matched threshold, as a point on the risk–coverage
   curve), C2 (random deferral, analytic) and O. Retire J, J-AA, J-floor, R1, R2, L2 and C4 (the
   learned GBR policy is a second decision model). C3 becomes "a confidence threshold fitted on
   DEV, answer/abstain only".
4. **Experiment matrix v2.** Keep E1 (LLM-only missingness grid), E2/E2b (retrieval arm), E6
   (baselines). E7 (cross-family replication) becomes optional and leaves the minimum paper:
   the main study uses one fixed LLM. Retire E3, E4, E5's Jev part and E8. A full-ranking
   prompt arm is listed as a candidate for after the literature review (for H3), not planned.
5. **Risk entry.** The old paper's main contribution (RQ4) is gone. The novelty of whatever
   replaces it is UNVERIFIED UNTIL LITERATURE REVIEW.

## Files

- Create `plans/261018-2300-.../design/protocol-v2.md`.
- Modify `plans/261018-2300-.../decisions.md` (append only).

## Verification

- Every retired arm, RQ and experiment from the old design is listed with a reason. A diff
  against the old §5 and §7 tables shows nothing left unaccounted for.
- No sentence in protocol-v2 asserts a hypothesis direction or a confirmatory family.

## Risks

- The owner may still want a cost-aware "retrieve or not" rule. Under the invariant, that rule
  would be a threshold on the same LLM's confidence. It belongs to H2 and is not built here.
