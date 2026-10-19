---
title: "Phase 00: Test baseline and failure diagnosis"
status: completed
priority: P1
effort: 0.5 d
dependencies: []
---

# Phase 00: Test baseline and failure diagnosis

## Context

- `plans/review-runtime-261019-1746/cpu-tests.log`: mass `E` from `PermissionError` on a pytest
  basetemp inside `plans/` (sandboxed run). Environmental, not code.
- `cpu-tests-verified.log`: unfinished; one `F` at position 153; progress ratio matches the 313-test
  `-m "not realdata"` collection (369 total, 56 realdata).
- Position 153 of `pytest --collect-only -q -m "not realdata"` is
  `tests/test_feasibility.py::test_run_end_to_end_with_fake_server`. It writes a `#!/usr/bin/env bash`
  shim, and `feasibility.py:244` starts `shutil.which("bash")`. On Windows, `which -a bash` lists
  Git Bash, `C:\Windows\System32\bash.exe` (WSL stub) and a WindowsApps alias; which one wins depends
  on the launching shell's `PATH`.
- Hypothesis H-env: the failure is the WSL stub winning `PATH`. Alternative H-code: a real regression
  in `feasibility.run` / `grid_stats`.

## Requirements

1. Record the baseline **before any fix** on the execution machine, with a basetemp outside `plans/`
   and outside any sandbox-restricted directory.
2. Identify the failing node id(s) from pytest's own report (`-rfE`), not from position arithmetic.
3. Classify each failure as environment or code with evidence.
4. Do not edit tests to make them pass in this phase.

## Steps

From `nt114-rca/nt114-rca`, analysis venv active, `PYTHONPATH=src`:

1. `python -m pytest -m "not realdata" -q -rfE --basetemp="<scratch>/pt-nr" 2>&1 | tee <scratch>/baseline-not-realdata.log`
2. `python -m pytest -m realdata -q -rfEs --basetemp="<scratch>/pt-rd"` (raw data is not in the transfer
   bundle; skips are expected on the GPU machine and prove nothing about the data).
3. For each failure: rerun alone with `-x -vv --tb=long`.
4. For `test_run_end_to_end_with_fake_server` specifically (Windows only):
   - `python -c "import shutil; print(shutil.which('bash'))"` in the same shell;
   - rerun with Git Bash first on `PATH` (`$env:PATH = "C:\Program Files\Git\usr\bin;" + $env:PATH`);
   - pass with Git Bash and fail with the stub → environment. Fail with both → code; capture the traceback.
5. On the Linux execution machine run step 1 again; the bash question does not arise there.
6. Remove the stale sandbox artefacts `plans/review-runtime-261019-1746/pytest-*` only with the
   owner's OK (they are untracked; the two `.log` files are evidence and stay).

## Outputs

- `plans/reports/test-261019-<hhmm>-baseline-diagnosis.md`: command, platform, counts
  (passed/failed/errors/skipped), each failure with class (environment/code) and evidence.

## Acceptance

- [ ] Counts for both selections are recorded with the exact commands.
- [ ] Every failure has a class and a reproduction command.
- [ ] If H-code holds, a fix item is added to phase 03 (owner of `feasibility.py`) before phase 06.
- [ ] If H-env holds, the test gets an explicit precondition: on Windows it resolves Git Bash
      explicitly, or skips with a reason naming the WSL stub. It never passes silently on the stub.
      This test edit lands in phase 03, not here.

## Risk

A sandboxed runner reproduces the `PermissionError` flood. Use a basetemp in the session scratch
directory, and say so in the report.
