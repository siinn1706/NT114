---
phase: 2
title: "Raw profiling and compatibility gates"
status: completed
priority: P1
effort: "2d"
dependencies: [1]
---

# Phase 02: Raw profiling and compatibility gates

## Goal
Replace every UNKNOWN in the compatibility matrix with a measured value or an explicit
"not determinable", and decide each promotion gate from evidence before any adapter is written.

## Inputs
- `RCA_ROOT/data/raw/**` (read-only), `data/manifests/{incidents.jsonl,lineage-report.json,checksums.sha256}`
- [research/compatibility-matrix.md](research/compatibility-matrix.md) promotion gates
- [research/repo-audit.md](research/repo-audit.md) §2

## Outputs
- `RCA_ROOT/data/reports/profile/<source_id>.json` for: `rcaeval-zenodo`, `nezha`,
  `agenticopseval`, `cloud-opsbench`, `petshop`, `dejavu`, `rcabench-fse26`, `anomod`, `msds`
- `RCA_ROOT/data/reports/compatibility-matrix.json` (tier per source and per subset, gate
  outcomes with evidence refs)
- Updated [research/compatibility-matrix.md](research/compatibility-matrix.md) (UNKNOWN cells resolved)

## Files
- Create: `RCA_ROOT/src/rca/profile.py` — profiler library + `python -m rca.profile --source <id>`
- Create: `RCA_ROOT/tests/test_profile.py` — unit tests for the inference helpers
- Modify: `RCA_ROOT/.gitignore` — add `!data/reports/` (reports are small JSON and tracked)

## Tasks
1. Profiler core (stdlib + pyarrow, no pandas needed):
   - Member inventory from directories, zip central directories, and tar streams (`tarfile.open(mode="r|gz")`,
     never extracting to disk; members of interest are read into memory up to a byte cap).
   - For tabular members (CSV, Parquet, JSON lines): header, first 1,000 rows, inferred types,
     null rates, row count when cheap (Parquet metadata) or `UNKNOWN` (large CSV in zip).
   - Time-unit inference: for each numeric or string time column, classify magnitude
     (s ≈ 1e9, ms ≈ 1e12, µs ≈ 1e15, ns ≈ 1e18) and parse ISO strings; cross-check pairs of time
     columns and report constant offsets.
   - Identifier inventory: distinct entity names per system (service, pod, node), pod-name
     pattern classification (Deployment, StatefulSet, other).
   - Label files: parse and count; reconcile with `incidents.jsonl` rows of that source.
   - Record `largest_member_bytes` per source.
2. Source investigations (each answers a gate question):
   - **RCAEval:** per-zip case counts, modality sets, all distinct log and trace column sets
     across RE1–RE3, `startTimeMillis` vs `startTime` consistency on a 5% sample, the
     `multi-source-data` duplicate check, the list of non-service metric prefixes (e.g. `main`).
   - **Nezha:** `TimeStamp` − `Time` for every metric file (count, distinct offsets);
     for each of the 101 incidents, rows per modality in [t−600 s, t+300 s]; Duration unit check;
     pod pattern → deployment mapping coverage. Gate: compatibility-matrix row "Nezha".
   - **AIOps2025:** stream one archive (`2025-06-06.tar.gz`): log, trace and metric Parquet
     schemas, time column units, min/max time per hourly slice → archive time zone; then a
     metadata-only pass over all 18 archives (min/max per member from Parquet statistics) to map
     each of the 400 labelled windows to archives. Gate: every window covered or explained.
   - **RCA100:** for all 103 cases, read `topology.json` and `answer_key/*.gt.json`; classify
     `root_cause_entities` kinds; compute the share resolvable to a topology service. Gate: ≥80%.
   - **RCABench:** one streaming pass over the 13.4 GB tar listing members and reading small
     label-like members (`*.json`, `*.csv` < 5 MB with names containing `label`, `fault`, `root`,
     `inject`). Gate: per-case telemetry + machine-readable root-cause service.
   - **AnoMod, MSDS:** list label-like members and parse one; gate per matrix.
   - **DejaVu:** parse all five `faults.csv`; count incidents per set.
   - **Cloud-OpsBench:** schemas of `logs.json`, `metrics.csv`, `k8s_states.json`; time anchors.
3. Split feasibility: for RCAEval, Nezha and AIOps2025, count groups under the `physical` and
   `cell` grouping rules ([design/quality-leakage-splits.md](design/quality-leakage-splits.md) §5),
   using anchors and the evidence window from labels only. Record which protocols are feasible
   (≥20 groups and a test share ≥10%); infeasible protocols are dropped from phase 10's list in
   the report (expected for Nezha: eval-only and xdata only).
4. Write `compatibility-matrix.json`: per source and subset → tier A/B/C, gate result
   (`pass`/`fail`/`not-applicable`), evidence (profile JSON pointer), and the reason.
5. Update the Markdown matrix in this plan with the measured values; keep the original planning
   values visible where they changed.

## Tests (write first)
- T22 `tests/test_profile.py`: time-unit classification on s/ms/µs/ns and ISO samples; constant
  offset detection (the Nezha 2e8 case); pod pattern classifier (Deployment hash, StatefulSet
  ordinal, plain name); tar streaming reader never writes to disk (assert on a tmp dir).

## Completion criteria
- Every source in the matrix has a profile JSON; every gate has an outcome with an evidence
  pointer; no `?` remains in the A/B/C column.
- Profile counts reconcile with `incidents.jsonl` per source (differences explained in the JSON).
- `git status` shows only the new code, tests, reports and `.gitignore` change; `data/raw/` untouched
  (`sha256sum -c` on touched archives' entries still exit 0).

## Risks and rollback
- RCABench streaming read is long (13 GB decompression), and a gzip stream cannot seek. The
  profiler checkpoints its result per member (`work/profile/rcabench-fse26.partial.jsonl`); after
  an interruption it re-streams from the start, skips already-profiled members by name, and only
  reads the remaining ones. Run it in the background; it is read-only.
- A gate that cannot be decided from the data is recorded as `fail` with reason
  `not-determinable`; the source stays C/B. No guessing.
