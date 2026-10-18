---
title: "Phase 0: Gate — audit jobs finished, turn-2–4 work reviewed and committed"
status: done
priority: P1
effort: 0.5 d
dependencies: []
---

# Phase 0: Gate before any source change

## Context

Two background audit jobs from 2026-10-18 are still running: `bghjdbdqv` (RCAEval) and
`bkj5zzdec` (Nezha → RCA100 → AIOps2025). Each job runs `rca.visibility` in a **new** Python
process after `prepare`. That process imports whatever `src/` contains at that moment, so an
edit made now would mix code versions inside one result. The turn-2–4 work (raw LLM outputs,
`rca.visibility`, the visibility configs, `research/00`–`03`) is also still uncommitted.

## Requirements

1. Both jobs have exited. Each `results_visibility/<ds>/run.log` ends with `exit 0`, and its
   counts line matches the condition matrix. Otherwise the blocker is reported, and nothing is
   excluded silently.
2. `research/04_evidence_visibility_results.md` is written, which was the pending task of
   2026-10-18.
3. The owner has reviewed the uncommitted diff and either approved a commit or explicitly chosen
   to keep one change set.

## Steps

1. Wait for the task notifications. Do not poll.
2. Validate the outputs: denominators, exclusions and the counts in `visibility_counts.json`.
   Write research/04.
3. Present `git status` and `git diff --stat` to the owner.
4. Commit only on approval, as a conventional commit without AI references in the subject. The
   trailer follows the repository's attribution rule. Optionally, and only on approval, tag
   `pre-single-llm` so that the Jev implementation can be recovered from history.
5. Record the evidence-file digests of `results_visibility/*/evidence/*.json` (sha256 list) in
   `reports/evidence-digests-before.txt`. Phase 06 compares against it.

## Verification

- `tail -2 results_visibility/*/run.log` shows `exit 0` for all four datasets.
- `ps`/`tasklist` shows no Python process left over from these jobs.
- A digest file exists, with one line per evidence file.

## Rollback

Nothing changes in the source tree in this phase.
