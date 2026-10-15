---
title: "Phase 1: M0 — Prerequisites, owner decisions and preregistration draft"
status: in-progress
priority: P1
effort: 3 person-days (week 1, 2026-10-19 → 10-23)
dependencies: []
---

# Phase 1: M0 — Prerequisites, owner decisions and preregistration draft

## Context links

- [Repository audit](research/repo-audit.md) · [Jev verification](research/jev-api-verification.md) ·
  [Model selection](research/model-selection.md) · [Research design](design/research-design.md)
- Data release gates: `plans/261014-0749-nt114-rca-dataset-standardization-and-validation/reports/release-handoff-nt114-data-v1.md`

## Goal and research justification

Remove every external blocker before code depends on it. The data release is not accepted until
the Linux gate passes. Jev access, its pinned version and the GPU tier decide what M2–M3 can
run. Writing the preregistration draft now stops later results from shaping the hypotheses.

## Dependencies

None. M1 (phase 02) can start in parallel: it needs no GPU and no Jev key.

## Tasks

1. **Linux GPU portability gate** (owner, on the GPU machine; CPU use only). <!-- Red team F1 -->
   `verify_portability.sh` step 0 refuses any `src/`, `configs/` or `schemas/` change since the
   bundle commit `cd96e9e`, so once phase 02 code lands on `main` the gate can never pass from
   `main`. Run it from a detached worktree pinned to the bundle commit:
   `git worktree add ../nt114-gate cd96e9e && cd ../nt114-gate/nt114-rca/nt114-rca`, then the
   release handoff commands, including `bash scripts/verify_portability.sh <bundle>`. Never edit
   the script to pass. At the start of phase 03, rerun steps 1–3 (`verify-bundle`, `status`,
   `verify-splits`) and the full test suite at HEAD on Linux, without step 0. Record
   the output in the data plan's `reports/phase-12-portability.md`. Exit: steps 0–5 pass and the
   `status` counts equal `bundle.json`.
2. **Hardware decision.** Record GPU model, VRAM, driver/CUDA and disk in `decisions.md`. Map it
   to tier S/M/L ([model-selection §4](research/model-selection.md)) and confirm the model trio.
3. **Model-card probe** (read-only). For Qwen3.5-9B, Qwen3.5-27B, Gemma 4 E4B / 26B-A4B, record
   from the official HF cards: licence, context, chat template and thinking toggle, official FP8 or
   4-bit checkpoint and the revision sha, minimum vLLM version. Resolve every **[S]** row in
   model-selection §2.
4. **Jev access (hard exit criterion of M0).** <!-- Red team F6, F7 --> Obtain a TypeSafe key.
   Confirm that `model: "jev-1.13.0"` is accepted. Make one hand-written smoke call with a
   synthetic state (no dataset text), outside the repo, and record the **exact** response `model`
   string and the response field layout in `decisions.md`; the version guard and its test are
   written against that observed string. Record the org rate limit from the console. Store the key
   only in the environment (`TYPESAFE_API_KEY`). If no key exists by 2026-10-30, the Jev part of
   the preregistration and the Jev freeze move out of phase 03 into a hashed addendum before E4,
   and the owner is told the M3 start is at risk.
5. **Owner decisions** (plan.md "Open decisions"): D1 provider, D2 hardware tier, D3 sending NC
   evidence to Jev, D4 K8s demo in or out, D5 target venue and date, D6 alias review sign-off.
6. **Preregistration draft.** Copy RQs, hypotheses, endpoints, sets, comparators and the
   statistical plan from `design/research-design.md` into `design/preregistration.md`, with
   placeholders only for DEV-tuned items (prompt text, Jev wording). It is frozen at the end of M2.
7. **Secret hygiene before any key exists.** <!-- Red team F9 --> Add `.env`, `results*/` and
   `paper/artifact/` to `nt114-rca/nt114-rca/.gitignore` and check with `git check-ignore`. This is
   the only repository change in M0.
8. **Researcher availability.** Record person-days per week for weeks 1–12 (exams, teaching,
   holidays) in `decisions.md`; re-plan the timeline if weeks 1–3 have under 8 person-days.
9. **Decision log.** Create `decisions.md` in this plan directory (date, decision, evidence,
   owner). Every later deviation is appended there.

## Existing modules to reuse

`scripts/verify_portability.sh`, `rca.prep verify-bundle`, `rca.prep status`, `verify-splits`.

## Files

| File | Action |
|---|---|
| `plans/261015-0047-.../decisions.md` | create |
| `plans/261015-0047-.../design/preregistration.md` | create (draft) |
| `plans/261014-0749-.../reports/phase-12-portability.md` | append Linux output (owner) |
| `research/model-selection.md` | update the [S] rows with card facts |

No source file changes; only the `.gitignore` entries of task 7.

## Interfaces and contracts

None new. This phase confirms external contracts: the Jev request/response shape
(research/jev-api-verification §2) and the model serving flags.

## Testing strategy

| Check | Pass condition |
|---|---|
| `verify_portability.sh` | exit 0, all 6 steps |
| `PYTHONPATH=src python -m pytest -q tests` on Linux | all pass (230 or more) |
| Jev smoke call | HTTP 200, `model == "jev-1.13.0"`, `probabilities` sum to 1 |
| Model probe | each chosen model has a pinned repo + revision and a confirmed licence |

## Acceptance criteria / Definition of Done

- [ ] Linux gate passed from the `cd96e9e` worktree and recorded (or, if blocked, M2 start date moved and logged)
- [x] `.gitignore` covers `.env`, `results*/`, `paper/artifact/` (verified with `git check-ignore`)
- [ ] Researcher availability per week recorded
- [ ] GPU tier and model trio recorded in `decisions.md`
- [ ] Jev access confirmed with the pinned version; exact response `model` string and rate limit recorded; key not in any file
- [ ] D1–D6 answered or explicitly deferred with a date
- [x] `design/preregistration.md` draft exists

## Risks

| Risk | Mitigation |
|---|---|
| GPU machine not available in week 1 | M1 continues on CPU; M2 slips; the week-6 checkpoint absorbs ≤1 week |
| Jev key delayed | M1–M2 LLM work continues; E4 needs Jev by week 5 at the latest (cutoff in plan.md) |
| Linux gate fails | Fix through the data plan's procedure only; no redesign here |

## Security

Keys only in shell environment variables. `.env` is **not** git-ignored today
(`nt114-rca/nt114-rca/.gitignore` has no entry); task 7 adds it before the key is obtained in
task 4. Never echo keys. The smoke call uses
synthetic text, no dataset content.

## Next

Phase 02 (in parallel) and phase 03 (needs tasks 1–4).
