# Test baseline and diagnosis of the unfinished CPU run (phase 00)

Plan: [261019-1800 review findings](../261019-1800-review-findings-fixes-and-research-readiness/plan.md),
phase 00. Machine: Windows 11 Pro 10.0.26300, CPython 3.12 venv `nt114-rca/nt114-rca/.venv`, CPU only.

## Result

The single failure in the unfinished CPU run was an **environment** failure, not a code failure.
`tests/test_feasibility.py::test_run_end_to_end_with_fake_server` starts `scripts/serve_model.sh`
through `bash`. In a PowerShell-launched process, `bash` resolves to the WSL launcher, and that
launcher cannot run a script when no distribution is installed. The test passes when Git Bash comes
first on `PATH`. The test now resolves Git Bash explicitly on Windows. If no POSIX bash exists, it
skips and the reason names the WSL launcher, so it never passes silently on the stub.

## Baseline at HEAD `2198ed7` (before any fix)

| Selection | Command (from `nt114-rca/nt114-rca`, Git Bash, basetemp in the session scratchpad) | Result |
|---|---|---|
| Non-realdata | `.venv/Scripts/python.exe -m pytest -q -m "not realdata" --basetemp=<scratch>/pt-nr` | 313 passed, 56 deselected, 0 failed (290 s) |

The earlier `plans/review-runtime-261019-1746/cpu-tests.log` errors were `PermissionError`s on a
basetemp under `plans/`. They come from the sandbox, not from the code. That run's 72-test progress
(23 %) matches the 313-test non-realdata selection.

## Environment evidence

From PowerShell:

```text
> Get-Command bash -All
C:\WINDOWS\system32\bash.exe
C:\Users\Siinn\AppData\Local\Microsoft\WindowsApps\bash.exe
> bash -c "echo ok"
<3>WSL (10 - Relay) ERROR: CreateProcessCommon:800: execvpe(/bin/bash) failed: No such file or directory
exit=1
```

Under Git Bash, `bash` is `/usr/bin/bash` (Git for Windows), and the test passes there.

Reproduction: run the test from PowerShell with the pre-fix test code. Before the test change it fails
on the stub, and it passes from Git Bash. After the change (`tests/test_feasibility.py::_posix_bash_dir`)
it passes from both shells.

## Classification

| Failure | Class | Fix |
|---|---|---|
| `test_run_end_to_end_with_fake_server` (unfinished run) | Environment: the WSL `bash.exe` launcher wins `PATH` | The test prepends Git Bash's directory to `PATH`, or skips naming the WSL launcher (landed with phase 03) |

H-code is refuted: the test passes unchanged at HEAD when Git Bash is first on `PATH`.
