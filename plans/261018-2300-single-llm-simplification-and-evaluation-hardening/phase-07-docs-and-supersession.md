---
title: "Phase 7: Docs, research reports and supersession of the Jev plan"
status: done
priority: P2
effort: 1 d
dependencies: [phase-06]
---

# Phase 7: Docs and supersession

## Requirements

1. **Old plan** (`plans/261015-0047-.../plan.md`). Add a status note at the top: superseded by
   this plan for Jev, escalation, RQ4–RQ5, E3–E5 (the Jev part) and E8. Mark phases 03–06 as
   partially superseded, with links. Its decision log stays append-only: add one row pointing to
   [decisions.md](decisions.md).
2. **`/research/00`–`02`.** Edit only the statements the removal or the phase-06 measurements
   change:
   - 00, blocker 5: "policy cost leaves out Jev" becomes moot;
   - 01, §4 and §6: rows for Jev cost, C3/C4/J-floor and the McNemar path;
   - 02's summary row "Depends on Jev (D1)?": D1 is reversed;
   - the H1 module list: `decide.py` and Jev stages are gone;
   - 02, H3, and 03, RQ4: the decomposition paper was added on 2026-10-18. Re-check that note
     against the transcribed external reference values;
   - 01, §6 and 02, H3: rank beyond 5 is censored (top-5 cap kept).

   Every edit carries the date 2026-10-18 or later and the evidence.
3. **Evergreen docs** (`README.md`, `docs/data_contract.md`, `docs/gpu_deployment.md`):
   - a module map with `selective`, `confidence`, `contrasts`, `cost`, `reproduce` and
     `leakage_audit`;
   - the analysis CLI;
   - the eval-only zone (visibility, leakage audit, analysis) in the leakage rules;
   - the deployment steps without the Jev key.

   Each doc gets the smallest change that is accurate. Docs link to the code instead of copying it.
4. **Protocol v2** (from phase 01) is updated with the phase-06 numbers: measured intersections,
   MDEs and the manipulation-check rates.

## Verification

- Each changed claim was checked against code, a test or a phase-06 artefact. Links resolve
  (a markdown link check over the changed files).
- `grep -riE "jev|typesafe|escalat" README.md docs` returns nothing.
