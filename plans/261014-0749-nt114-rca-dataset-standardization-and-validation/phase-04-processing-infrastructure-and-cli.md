---
phase: 4
title: "Processing infrastructure: safe extraction, build driver, validators, CLI"
status: completed
priority: P1
effort: "2.5d"
dependencies: [3]
---

# Phase 04: Processing infrastructure: safe extraction, build driver, validators, CLI

## Goal
Provide the dataset-independent machinery every adapter runs inside: safe extraction, a
resumable and idempotent build driver, per-incident validators with quality states, a run ledger,
and the `python -m rca.prep` CLI.

## Inputs
- [design/cli-and-portability.md](design/cli-and-portability.md), [design/quality-leakage-splits.md](design/quality-leakage-splits.md) §1–2
- Phase-03 modules

## Outputs
- Working CLI commands `profile`, `extract`, `normalize`, `validate`, `status` (others stubbed
  with exit 2 "not implemented in this phase" until their phase).

## Files
- Create: `RCA_ROOT/src/rca/safe_extract.py` — rules from design §4; receipt `.extract.json`
- Create: `RCA_ROOT/src/rca/prep.py` — argparse CLI; config loading with defaults and hash;
  path resolution (`--data-home` > `RCA_DATA_HOME` > config > `RCA_ROOT/data`); `build_dataset`
  driver (design adapter-contracts §1); run ledger; exit codes
- Create: `RCA_ROOT/src/rca/quality.py` — finding codes table, per-incident validators,
  state roll-up, override application
- Create: `RCA_ROOT/configs/prep.yaml`, `RCA_ROOT/configs/quality_overrides.yaml` (empty list with schema comment)
- Create: `RCA_ROOT/.gitattributes` — LF for `*.json`, `*.jsonl`, `*.sha256`, `*.yaml`
- Modify: `RCA_ROOT/.gitignore` — add `!data/splits/` (reports were added in phase 02)
- Create: `RCA_ROOT/tests/test_safe_extract.py`, `RCA_ROOT/tests/test_prep_driver.py`, `RCA_ROOT/tests/test_quality.py`
- Create: `RCA_ROOT/tests/fixtures/build_fixtures.py` — fixture builders (shared by later phases)

## Tasks
1. Tests first: T05 (unsafe tar/zip members built in `tmp_path`), T06 (a fake in-memory adapter
   yielding present/empty/absent/broken modalities and one REJECT, a kill simulated by raising
   mid-run, then a resume; assert the final JSONL contains every incident, including those
   completed before the kill, with their stats, and that no telemetry file was rewritten), T07 (one crafted case per finding code).
2. `safe_extract.py`: implement checks in the order of design §4; tar uses `filter="data"` plus
   explicit checks; zip uses `ZipInfo` checks; per-member atomic write; receipt with sizes and
   sha256; resume skips verified members.
3. `quality.py`: validators run on the in-memory IncidentRecord, LabelRecord and table stats.
   Validators that need several incidents (duplicates, overlap) live in phase 09; this phase only
   implements per-incident checks.
4. `prep.py` driver: per incident → discover, label, map, window, normalize (stream batches to
   `ParquetSink`), derive ModalityInfo, validate, atomically write
   `work/runs/<dataset>/records/<uid>.json` (all record parts and stats, REJECTs included), then
   the `.done` marker. Finalization concatenates the record files in uid order into the three
   JSONL files and writes `_build.json` last; it never recomputes stats. Parallelism: `concurrent.futures.ProcessPoolExecutor`
   with `max_workers` from config; results merged in uid order so output is deterministic.
5. Run ledger: one JSON line per incident with timings, rows in/out per member, peak RSS
   (`psutil` is not added; use `resource` on Linux and `ctypes` `GetProcessMemoryInfo` on
   Windows, or record `UNKNOWN`).
6. Wire `profile` to `rca.profile` (phase 02) and `status` to read `_build.json` files.

## Tests
- T05, T06, T07 green; T01, T03, T04 still green.

## Completion criteria
- `python -m rca.prep status` runs on the real data home and reports "no canonical builds".
- `python -m rca.prep normalize --dataset <fake>` (fixture adapter registered only in tests)
  shows: second run rewrites nothing (file mtimes unchanged), killed run resumes.
- Unsafe archive fixtures all rejected with exit 4.

## Risks and rollback
- Windows multiprocessing needs the `if __name__ == "__main__"` guard and picklable adapters;
  T06 runs with `max_workers: 2` on Windows to catch this.
- Rollback: new files plus two ignore/attribute edits.
