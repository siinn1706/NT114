---
title: "Phase 6: M5 — Selected extensions, reproducibility package, paper-ready results"
status: todo
priority: P1
effort: 12 person-days (weeks 7–12, 2026-11-30 → 2027-01-08; holiday weeks reduce capacity)
dependencies: [phase-04]
---

# Phase 6: M5 — Selected extensions, reproducibility package, paper-ready results

## Context links

[Research design](design/research-design.md) §7 (O1–O9), §10 · [Architecture](design/architecture.md) §5–6 ·
`decisions.md` (week-6 checkpoint)

## Goal and research justification

Run only the optional extensions chosen at the week-6 checkpoint. Make every reported number
regenerable from the released artefacts. Produce the figures and tables. Writing runs in parallel
from week 3 (plan.md timeline); this phase finishes and freezes it.

## Dependencies

Phase 04 done. Phase 05 is independent (its results enter only if ready by week 10).

## Tasks

1. **Selected extensions** (priority order unless the checkpoint says otherwise): O4 `jev-1.14.0`
   rerun on RCA-T (version drift); E2b recurring-fault regime on RCA-REC with O3 `no_precedent`; O7 second sampling seed on
   RCA-T; O1 thinking mode on RCA-T; O2 BM25/dense; O6 answer-token probability; O5 Nemotron; O10 J-short; O9 K8s
   demo (only if D4 = in). Each is exploratory and tabulated separately.
2. **Reproducibility package** <!-- Red team B9 --> built in `paper/artifact/`, which is
   git-ignored (phase 01 task 7) and published **only** to the private HF dataset repo. Never
   commit it: `jev_raw.jsonl` holds NC-licensed evidence, and LLM prompts in the retrieval arm
   hold precedent root causes (train labels, `retrieve.py:121`). Contents: configs, `decisions.md`, the preregistration
   and its hash, every `manifest.json`, `jev_raw.jsonl`, LLM cache exports (raw outputs), the
   `analyze` command list, `requirements-lock.txt` + vLLM version, model revisions. Labels and
   NC-licensed evidence stay in the private HF repo; the public artefact (if any, D5) holds only
   label-free derived outputs allowed by the licences.
3. **Regeneration check**: on a clean checkout + bundle + cached outputs, one script regenerates
   all tables and figures byte-identically with no network (`scripts/reproduce_tables.sh`).
4. **Figures**: (1) pipeline; (2) AC@1 heatmap condition × dataset; (3) overconfidence gap and
   CW₁₀₀ by condition, with `blind_root` vs `blind_nonroot_ev` contrasted (main figure); (4) error
   detection AUROC by signal and condition; (5) risk–coverage curves with policy points; (6) "per
   100 incidents" table: Jev vs controls; (7) Jev diagnostics (position bias, stability, J-noconf).
5. **Paper**: Method and Setup match the code and preregistration; Results follow the
   confirmatory → replication → exploratory order; a deviations section lists every
   `decisions.md` entry after the freeze; threats to validity from research-design §10.
6. **Literature recheck** (weeks 6 and 11, as the note planned): arXiv/OpenAlex for new LLM-RCA
   missingness, calibration or Jev papers; update positioning.
7. **Docs**: `README.md` gains the LLM + Jev commands; `docs/data_contract.md` §8 is final.

## Files

| File | Action |
|---|---|
| `scripts/reproduce_tables.sh` | create |
| `src/rca/analyze.py` | modify (final figures) |
| `paper/` (draft, figures, `results/` summary CSVs) | create |
| `README.md`, `docs/data_contract.md` | modify |

## Tests

| Check | Pass condition |
|---|---|
| `reproduce_tables.sh` on a clean checkout | exit 0, tables byte-identical, no network |
| Full suite on Linux | green |
| Headline tables | no mock rows, no DEV rows, single prompt/question version, single Jev version |

## Acceptance criteria / Definition of Done

- [ ] Selected extensions done or explicitly dropped (logged)
- [ ] Reproduction script regenerates every table and figure
- [ ] Paper draft complete, with a deviations section; an outside reader reviewed it (week 12)
- [ ] Final plan DoD (plan.md) checked

## Risks

| Risk | Mitigation |
|---|---|
| Holiday weeks (2026-12-21 → 2027-01-01) | Experiments end by 2026-12-18; holiday weeks are for writing only |
| New competing paper | Recheck tasks; reposition on the controls (C1/C2) and the `blind_root` contrast |
| Licence limits on releasing outputs | D5 decides; private release for reviewers if needed |

## Next

Submission; then archive the plan with `/ak:plan archive`.
