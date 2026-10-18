---
title: "Phase 4: End-to-end cost ledger and reproducibility"
status: todo
priority: P2
effort: 2 d
dependencies: [phase-02]
---

# Phase 4: Cost ledger and reproducibility

## Context

[Scout report §4](research/scout-report.md#4-cost-and-reproducibility).

- Cost is tokens plus latency per cell.
- Evidence preparation (about 18 s per RCAEval incident, measured on 2026-10-18), retrieval time
  and the sampling multiplier are not recorded.
- The manifest lacks package versions, the builder version and the config text.
- No script regenerates the tables.

## Requirements

1. **Preparation log.** `prepare` appends one row per incident and condition to
   `<out dir>/prepare_log.jsonl`. Each row holds:
   - wall time;
   - telemetry rows read per modality;
   - evidence characters;
   - `truncated`;
   - the evidence fingerprint.

   The log lives **outside** the evidence file, so evidence fingerprints and cache keys do not
   change.
2. **Retrieval timing.** The time `CaseStore.search` takes is added to the grid row as
   `retrieval_s`. This is a new optional field; existing readers ignore it.
3. **Cost table.** `analyze` adds `table_cost`, per dataset × condition × arm. It reports:
   - prompt, completion and total tokens per incident;
   - tokens per sample;
   - LLM latency (with the `cached` share; replayed latency is flagged as such);
   - retrieval seconds;
   - preparation seconds.

   It also gives an end-to-end figure per incident along any arm path the selective evaluator
   declares. GPU-seconds stay NaN until a GPU run records them; the column exists so that H2 can
   use it.
4. **Manifest v2.** Remove the Jev fields (done in phase 02). Add:
   - Python version;
   - the versions of the locked packages that are importable (numpy, pandas, scipy, scikit-learn,
     pyarrow, yaml);
   - `evidence.BUILDER_VERSION`;
   - `legacy_view.VIEW_VERSION`;
   - the sha256 of the resolved config text, plus a copy of the config as `config.yaml` next to
     the grid;
   - the sha256 of the split manifest (`split.json`);
   - the platform string;
   - the sha256 of `prepare_log.jsonl`.
5. **Reproduction.** `python -m rca.reproduce <run dir>` regenerates every analysis table from
   the grid, raw outputs, visibility and baselines files and the copied config. It writes the
   tables to a temporary directory and compares their sha256 with the published ones. It exits
   non-zero on any difference. Bootstrap seeds come from the config, so the result is
   deterministic.

## Files

| Action | File |
|---|---|
| Create | `src/rca/reproduce.py`, `tests/test_reproduce.py` |
| Modify | `src/rca/run_grid.py` (prepare log, `retrieval_s`, manifest v2), `src/rca/analyze.py` (only the `table_cost` writer, added after phase 03 has landed, or as an isolated function in `src/rca/cost.py` if phases 3 and 4 run in parallel) |

The second option avoids a file conflict with phase 03, so `cost.py` is the default.

## Verification

- On the synthetic mock chain:
  - `prepare_log.jsonl` has one row per (incident, condition);
  - the evidence fingerprints equal those before the phase (test).
- `manifest.json` has every new key (test). No key name or value matches the secret patterns of
  `llm.check_no_secrets` (test).
- `python -m rca.reproduce <mock run dir>` exits 0, and the test runs it with networking
  disabled (socket creation patched to raise), proving the pipeline has no runtime dependency on
  external services. When one grid row is edited, it exits 1 and
  names the table that changed (test).

## Risks

- The wall time of `prepare` depends on the machine. It is reported as a measurement of that
  machine (platform string in the manifest), never as a property of the method.
