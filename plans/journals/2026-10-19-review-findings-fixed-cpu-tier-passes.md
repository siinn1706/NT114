---
title: "Review findings fixed; CPU readiness tier passes"
date: 2026-10-19
summary: "Plan 261019-1800 phases 00-06 executed with /ak:cook --auto: 7 findings fixed test-first, the WSL bash failure proven environmental, all CPU checks green; nothing committed."
---

## What happened

- Executed `plans/261019-1800-review-findings-fixes-and-research-readiness` phases 00-06 on the
  Windows CPU machine with the mock LLM only.
- The unfinished CPU run's single failure was environmental. Under PowerShell, `bash` resolves to
  the WSL launcher, which fails with `execvpe(/bin/bash) failed`. The fake-server test now resolves
  Git Bash explicitly, or skips and names the launcher.
- The fixes:
  - The store is bound to the split's train role, with a binding hash in the resume key and manifest.
  - Precedents without a single service root are excluded under prompt v1 and counted.
  - An execution signature (`exec_sig`) covers rows, raw records, the manifest (v3) and the headline guard.
  - A miss gets rank `max(n, 5) + 1`.
  - The parse gate counts completions.
  - `reproduce` checks the published CSVs.
  - On the evaluation side: same-stratum DEV fit with `no_source` rows, declared pools, CIs on every
    endpoint with `_nan_draws`, an injection-weighted stratified shift table, and E1/E1t/E3
    estimators in `rca.selective`.
- Found during validation: `leakage_audit` had the same unbound store glob as finding 1. It now reuses
  `_store_entries`, and its output is byte-identical to the published V6 audit.

## Evidence

- 345 non-realdata and 56 realdata tests pass.
- 37 updated tests fail on HEAD `2198ed7`.
- Smoke, canonical and V7 chains reproduce.
- Evidence digests: 0/862 changed. Prompt digest `4efde402…` unchanged.
- Reports: `plans/reports/test-261019-1911-baseline-diagnosis.md`,
  `plans/reports/test-261019-1921-cpu-validation-readiness.md`.

## Decisions pending

- Protocol v2 §9 addendum: pending owner.
- SESOI 0.05.
- Deleting the stale `plans/review-runtime-261019-1746/pytest-*` directories.
- Commit approval.

## Next steps

Owner review and commit. After that, tier 2 on the GPU machine: the `llms.txt` chain, then the
`dev-pilot.yaml` dry checks.
