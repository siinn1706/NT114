# Phase 04: OpenRCA gated acquisition

Status: PENDING:drive-quota (2026-10-14). Venv, gate re-check and `AppTelecomDeploymentList.xlsx` are done; Drive refused the three archives. Receipt: [cook receipt](receipts/cook-receipt-20261014.json)

## Requirements

- Gate (owner decision D2): source, licence, ground-truth quality, independence and relevance.
  These were verified during planning (catalog section A5). Cook re-checks only what can drift:
  the Drive folder listing, the file IDs, and the `microsoft/OpenRCA` README link.
- The gate fails if the folder listing changed in a way that removes or renames a zip, or if the
  repo no longer points to this folder. On failure the source becomes `PENDING: decision` and the
  difference is recorded.
- Acquisition uses `gdown` inside an isolated venv `RCA_ROOT/.venv-acquire`, pinned to the release
  current at install time with its version recorded. Each file ID is downloaded on its own with
  resume. `--folder` mode is not used because the folder has only 4 files.
- Integrity is `local-only`. Compute the SHA-256 at completion, compare the byte size with the
  Drive-rounded size (±0.05 G), and record both. The source state is `VERIFIED-LOCAL-ONLY`, never
  `VERIFIED`.

## Files

- Create: `RCA_ROOT/.venv-acquire/`. It must be ignored: add `.venv-acquire/` to
  `RCA_ROOT/.gitignore` in the same edit style as phase 01.
- Create: `RCA_ROOT/data/raw/openrca/drive-<YYYYMMDD>/{Bank.zip,Market.zip,Telecom.zip,AppTelecomDeploymentList.xlsx}`.
- Create: `RCA_ROOT/data/provenance/openrca.json`, including the gate evidence from the catalog.

## Steps

1. Re-read the folder listing:
   `https://drive.google.com/embeddedfolderview?id=1wGiEnu4OkWrjPxfx5ZTROnU37-5UDoPM`. Compare
   it with the four names and IDs in the seed.
2. Create the venv and install the tool, as separate commands:

   ```
   python -m venv .venv-acquire
   .venv-acquire/Scripts/python -m pip install gdown
   .venv-acquire/Scripts/python -m pip show gdown
   ```

   Record the version from `pip show`.
3. Download each file into a `.part` path. Run one command per file ID, in its own new directory:

   ```
   .venv-acquire/Scripts/gdown --continue --id <file_id> -O data/raw/openrca/drive-<date>/incoming/<name>
   ```

   Option names follow the installed version's `--help`. On a quota or interstitial failure, wait
   and retry with backoff (6 attempts, cap 1 h). If it still fails, the source becomes
   `PENDING: drive-quota` and keeps its partial file.
4. Move completed files out of `incoming/`, then run `verify` and `audit-archives` (header-only).
5. In provenance, record the Drive IDs, the modification dates shown, the exact sizes, the SHA-256
   values, the `gdown` version, and `integrity_level: local-only`. Also record the paper's
   observability-bias caveat (missing-telemetry records were filtered out).

## Checks

- Exactly four files are present. Their SHA-256 values are in `checksums.sha256` with
  `local-only`.
- `audit-archives` finds 0 unsafe members.
- `pip list` in the global interpreter is unchanged, shown by a diff before and after.
- `git check-ignore` confirms `.venv-acquire/` and `data/raw/openrca/` are ignored.

## Risk and rollback

- R13 (Drive quota): handled by backoff and the PENDING state.
- Rollback deletes `.venv-acquire/` and `data/raw/openrca/`. The global environment is never
  touched.
