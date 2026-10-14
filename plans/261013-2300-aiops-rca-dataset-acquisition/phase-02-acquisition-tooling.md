# Phase 02: Acquisition and verification tooling

Status: done (2026-10-14). Receipt: [cook receipt](receipts/cook-receipt-20261014.json)

## Requirements

Build a single-file, stdlib-only CLI, `RCA_ROOT/scripts/datasets/acquire.py`. It must be one
file because `python -I` drops the script directory from `sys.path`. External tools are limited
to git, git-lfs and, in phase 04 only, `gdown` inside `.venv-acquire`.

| Subcommand | Behaviour |
|---|---|
| `check-metadata --source ID` | Re-reads host metadata and compares it with the registry. Exits 3 on drift. |
| `plan --source ID` | Prints the files, expected bytes, integrity level and budget decision. Downloads nothing. |
| `fetch --source ID [--budget-gb 250 --reserve-gb 100]` | Resumable, idempotent download into `data/raw/<id>/<version>/`. |
| `verify --source ID` | Hashes every file, compares with publisher anchors, checks counts and bytes, scans for LFS pointers, then sets the state. |
| `audit-archives --source ID` | Reads zip/tar headers only. Flags absolute paths, `..`, links, devices, ratio > 100 and encrypted members (reported, not treated as an error). Never extracts. |
| `catalog` | Rebuilds `dataset_catalog.json`, `checksums.sha256`, `incidents.jsonl` and `not-acquired.json`. |
| `status` | Prints a table of each source's state, integrity level, reason and next action. |

Required behaviour:

- **Integrity levels (D8)**: every file record carries `integrity_level` from `publisher-hash`,
  `publisher-size` and `local-only`. It also records `publisher_anchor`, which names the
  algorithm, value and the source of that value, plus the `local_sha256`. A file without a
  publisher hash is never shown as publisher-verified. The source state is then
  `VERIFIED-LOCAL-ONLY` instead of `VERIFIED`.
- **Mechanisms**:
  - HTTP Range resume for HF, Zenodo and aiops.cn raw. HF uses
    `…/resolve/<rev>/<path>`, Zenodo uses `/api/records/<id>/files/<name>/content`, and aiops.cn
    uses `/-/raw/<sha>/<path>`. All three answered HTTP 206 on 2026-10-13.
  - Git at a pinned SHA: `git init`, then `git fetch --depth 1 origin <sha>`, then
    `git checkout <sha>`.
- **Retries**: 6 attempts with exponential backoff and jitter. A `.part` file is renamed
  atomically only after its hash or size check passes.
- **Budget (D5)**: before each artefact, compute `need = expected_bytes` (Drive-rounded sizes
  are rounded up to GiB). If need exceeds the remaining budget, or the free space left would fall
  below the reserve, the source becomes `PENDING: budget`. The state records the exact shortfall
  and the flag that would allow it. Partial downloads stay resumable. `status` and the catalog
  report it, and it is never dropped silently. An unknown size requires
  `--allow-unknown-size`.
- **Logging**: one JSON line per artefact attempt goes to `data/manifests/download_manifest.jsonl`.
  Failed attempts are kept.
- **State vocabulary**: `VERIFIED`, `VERIFIED-LOCAL-ONLY`, `PARTIAL`,
  `PENDING:{zenodo-unavailable|budget|decision|license|discovery|deferred|metadata-only}` and
  `BLOCKED:{reason}`.

## Files

- Create: `RCA_ROOT/scripts/datasets/acquire.py`.
- Create: `RCA_ROOT/scripts/datasets/sources.json`, from
  [sources-seed.json](research/sources-seed.json) plus the phase-01 recheck.
- Create: `RCA_ROOT/tests/test_datasets_acquire.py`, using stdlib `unittest`, local fixtures and a
  local `http.server`. It needs no network.
- `requirements.txt` stays unchanged.

## Steps

1. Implement the registry loader. It rejects unpinned entries and unknown kinds.
2. Implement the HTTP downloader with resume, retries, the budget policy and integrity levels.
3. Implement the adapters (HF, Zenodo, aiops.cn raw, GitHub git, Drive via `gdown`). Each one only
   expands a source into `(url_or_id, relpath, expected_size, publisher_anchor, integrity_level)`.
4. Implement the git adapter, the LFS pointer scan and `git fsck`.
5. Implement `audit-archives`: `zipfile.infolist()`/`testzip()` (CRC is read in memory) and
   `tarfile.getmembers()`. Encrypted zip members are listed and their CRC test is skipped, with the
   skip recorded.
6. Implement `verify`, `catalog` and `status`.
7. Write the tests.

## Checks

From `RCA_ROOT`, run `python -I -m unittest tests/test_datasets_acquire.py`. It must cover:

- Resume after a dropped connection.
- A hash mismatch that leaves the state PARTIAL.
- Budget refusal producing `PENDING: budget` with the shortfall recorded and no file written.
- An idempotent rerun that transfers 0 bytes.
- Unsafe zip/tar members flagged, with no extraction.
- An LFS pointer detected.
- An unpinned registry entry rejected.
- A `local-only` file that can never produce `VERIFIED`.

Also check that `src/`, `configs/` and `tests/test_pipeline.py` keep their inventory hashes.

## Risk and rollback

- The new files are additive. Rollback deletes `scripts/datasets/` and the new test.
- R8: the tool never imports or executes downloaded content.
