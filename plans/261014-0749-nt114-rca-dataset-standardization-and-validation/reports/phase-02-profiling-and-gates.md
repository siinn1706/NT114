# Phase 02 report: raw profiling and compatibility gates (2026-10-14)

## Commands

```text
PYTHONPATH=src .venv/Scripts/python -I -m rca.profile --source <id>   # 9 sources, read-only
PYTHONPATH=src .venv/Scripts/python -m rca.profile --matrix           # data/reports/compatibility-matrix.json
PYTHONPATH=src .venv/Scripts/python -m pytest -q tests/test_profile.py  # T22: 8 passed
```

Outputs: `RCA_ROOT/data/reports/profile/{rcaeval-zenodo,nezha,agenticopseval,cloud-opsbench,petshop,dejavu,anomod,msds,rcabench-fse26}.json`
and `RCA_ROOT/data/reports/compatibility-matrix.json` (18 rows: tier, gate, evidence pointer, reason).
The measured values are tabulated in [../research/compatibility-matrix.md](../research/compatibility-matrix.md#measured-in-phase-02-2026-10-14).
Archives were read in place (zip central directory, tar stream into memory); nothing was extracted
to disk.

## Gate outcomes

| Source | Gate | Result | Tier |
|---|---|---|---|
| Nezha | metric alignment rule + ≥95% incidents with M, L, T in [t−600 s, t+300 s] | 101/101 → pass | A |
| AIOps2025 | archive time zone from in-archive timestamps; every window covered or natural_absent | UTC+8 names; 358 covered, 42 natural_absent → pass | A (service+pod 318), B (node 82) |
| RCA100 | ≥80% service-resolvable | 83/103 = 80.6% → pass | A (per-incident tier for the other 20) |
| RCABench | per-case telemetry + machine-readable root-cause service | 1,422/1,422 → pass | A (no adapter yet, M3) |
| AnoMod | per-run label file naming the service | none → fail | C |
| MSDS | per-experiment root-cause component | none → fail | C |

## Defects found in the profiler during this phase (fixed, with tests)

1. **Parquet statistics read from the wrong column.** `_parquet_time_stats` indexed row-group
   statistics by Arrow top-level field position. Parquet statistics are per leaf column, and the
   AIOps2025 trace schema has nested columns (`references`) before `startTime`. As a result the trace
   time ranges were the min/max of an unrelated string column, and all 400 windows were reported
   uncovered. Fix: map flat fields to leaf columns by path. Test
   `test_parquet_time_stats_skip_nested_leaves`.
2. **Nezha anchored on `inject_timestamp`.** On 2023-01-29, `inject_timestamp` is about −8 h from
   `inject_time` for 24 of 28 incidents (−28,710 … −29,303 s). The hour keys, the minute file names
   and the metric `Time` strings ("… +0000 UTC") all agree with `inject_time`. With the wrong anchor,
   24 incidents had no rows in any modality and the gate read 77/101 (fail). With `inject_time` as
   the anchor: 101/101. The adapter contract
   ([../design/adapter-contracts.md](../design/adapter-contracts.md) §3.2) is updated to anchor on
   `inject_time` and to keep `inject_timestamp` as `anchor_original` evidence.
3. **Cloud-OpsBench metrics path.** `metrics.csv` sits under `raw_data/`; the profiler looked at the
   case root and reported 0. Measured: 170, as in the catalog.

## Reconciliation with `incidents.jsonl`

`registry_rows` equals the profiled incident count for RCAEval (735; the zips hold 736 case
directories, the extra one being the `multi-source-data` duplicate, see `#/duplicates`), Nezha (101),
Cloud-OpsBench (754) and PetShop (68). AgenticOpsEval has 503 registry rows = AIOps2025 400 +
RCA100 103. RCABench has no registry rows (layout unknown at acquisition); 1,422 cases were measured,
against 1,430 in the paper. The data does not explain the difference of 8, and it is recorded as such.

## Split feasibility (≥20 groups and test share ≥10%)

| Dataset | `cell` groups | `physical` groups | Feasible protocols |
|---|---|---|---|
| RCAEval | 109 | 620 | within-grouped, within-retrieval, eval-only (loso: one fold per system, 3 systems) |
| Nezha | 7 | 13 | eval-only (xdata after a second A adapter) |
| AIOps2025 (A) | 87 | 318 | within-grouped, within-retrieval, eval-only |

## Integrity

`git status` of the outer repository shows `nt114-rca/` as untracked (unchanged since phase 01).
`data/raw/` is read-only to the profiler; no write call targets it (reads only via `open(..., "rb")`,
`zipfile`, `tarfile` stream mode).
