---
title: "Phase 5: Leakage checks and baseline fairness"
status: todo
priority: P1
effort: 3-4 d
dependencies: [phase-00, phase-02]
---

# Phase 5: Leakage and baseline fairness

## Context

[Scout report §3 and §5](research/scout-report.md#3-baseline-fairness).

- B1 reads only the Metrics block.
- The evidence order is itself a ranking hint.
- B3 majority uses the scored test set's prior.
- Nobody has checked text-level near-duplicates between test evidence and the retrieval store.

## Requirements

### Baselines (`src/rca/baselines.py`)

1. **B1m evidence order.** Rank services by first appearance across all evidence blocks, in
   block order. A service line counts, and so does an endpoint of a slow call edge. The remaining
   candidates follow in the evidence file's shuffled order. This is the fair non-LLM reference for
   "the summary already ranks the root".
2. **Per-modality variants.** Compute B1 for each block on its own (metrics, logs, traces). This
   way every condition that has any block gets a non-LLM row. A condition with no usable block
   gets an explicit `no_row_reason`, never a silent gap.
3. **B3 majority prior.** Take the prior from the **train** role of the config's split when one
   exists. On eval-only splits, the row is labelled `label_prior: scored_set` and is excluded
   from comparisons (a reference only).
4. **Joint table.** Write rows keyed exactly like the grid: incident, condition and injection
   weight. `analyze` (phase 03) can then put a baseline next to the LLM in the same paired
   contrast.
5. **BARO-style baseline** (approved conditionally on 2026-10-18), in `src/rca/baro.py`, pure
   NumPy:
   - **Faithfulness.** It reproduces the reference algorithm and preprocessing of the official
     implementation in the RCAEval package: the anomaly-time detection step, the robust scaling of
     each metric between the normal and anomalous windows, the aggregation from metrics to
     services, the handling of constant or missing series, and the tie order. Each step is traced
     to the reference source, with file and function, in the module docstring. It runs on the raw
     metric frames from `legacy_view.legacy_telemetry`, not on the evidence text.
   - **Equivalence tests** (`tests/test_baro.py`). They compare the NumPy implementation with
     reference fixtures produced by the official implementation (task 5a). Rankings must match
     exactly on the top 5, and on the full ranking where the fixture has one. Scores must agree
     within 1e-6. A score is compared only where the fixture carries an instrumented score; see 5a.
     NT114 code and tests never import RCAEval. Only the JSON fixtures and their provenance enter
     the repository. Until every fixture test passes, all outputs and tables label the baseline
     `BARO-style (unvalidated)`, and it is never called B2.
5a. **Official reference fixtures** (approved 2026-10-18). They are generated in a separate,
   isolated, CPU-only environment outside NT114's `.venv`. The environment is separate for
   dependency hygiene: RCAEval's dependencies never enter NT114's lock file.
   - **Who, where and when.** Claude Code runs the task on the owner's local Windows machine.
     It runs during phase 05, after these three gates:
     - the phase 00 gate has passed;
     - `scripts/export_baro_inputs.py` exists and its tests pass;
     - the NumPy implementation is in place.

     It must finish before phase 06 starts.
   - **Isolation.** A dedicated CPU-only Python virtual environment in its own directory outside
     `nt114-rca/nt114-rca/`, for example a sibling `baro-reference/` directory. Its interpreter
     path is recorded in the provenance file. No GPU is used. Nothing from it is added to NT114's
     lock file or requirements.
   - **Pinning.** The upstream RCAEval repository at one recorded commit sha, plus the exact
     dependency versions installed (a `pip freeze` captured into the provenance file).
   - **Inputs.** The raw metric frames of a fixed, small incident sample are exported from NT114
     (`legacy_view.legacy_telemetry`, metrics only) as files with a sha256 each. The sample
     covers RCAEval RE2 and RE3 incidents from the grouped split's DEV role, at least one per
     system. It also covers a few **RE1 DEV incidents**, at least one per RE1 system (Online
     Boutique, Sock Shop, Train Ticket), so that RE1-specific preprocessing is validated, because
     RE1 is metrics-only with its own column layout. Edge cases are included too: constant series,
     missing values, and ties. The reference side reads
     exactly these files, so both sides see identical inputs.
   - **Recorded preprocessing.** For each call, record:
     - the anomaly-detection and inject-time inputs;
     - the normal and anomalous window bounds;
     - column selection and renaming;
     - resampling or interpolation;
     - the metric-to-service mapping (the column-name parsing rule, and the resulting
       column → service table);
     - every non-default argument.
   - **Rankings and scores.** The official `baro()` API returns a ranking but no scores. Rankings
     come from the unmodified call. Scores come from **reference-side instrumentation only**: a
     wrapper that records the intermediate per-metric and per-service scores at the points where
     the algorithm computes them, without changing any computation. Each instrumented run must
     return a ranking identical to the uninstrumented call on the same input; otherwise its scores
     are discarded. The instrumentation code and its diff against upstream are stored with the
     fixtures.
   - **Provenance** (`tests/fixtures/baro/provenance.json`). It records:
     - the upstream commit;
     - the environment freeze;
     - the Python version and platform;
     - the input file digests;
     - the incident uids and the data-bundle id;
     - the preprocessing record;
     - the metric-to-service table;
     - the instrumentation sha256;
     - who generated the fixtures, and when.

     The test refuses fixtures whose input digests differ from the files NT114 exports today.
   - **Overlap with B1 max-z.** For each incident and condition with metrics, report:
     - top-1 agreement;
     - top-5 Jaccard;
     - Kendall τ on the shared top-5;
     - the paired ΔAC@1 between the two, with the phase-03 engine.

     If they almost always agree, the report says that B1 already stands in for BARO-style on this
     evidence.

### Leakage

6. **Leakage tests** (`tests/test_leakage.py`). On canonical synthetic data:
   - every retrieval store entry has split role `train` and never belongs to the query's
     manifest group;
   - a `no_precedent` (oracle) row is refused by `selective` and by the headline guard.
7. **Text-level near-duplicate audit** (`src/rca/leakage_audit.py`, new, eval-only). For each
   query incident and condition, it computes:
   - the maximum TF-IDF cosine against same-system store entries;
   - the maximum line-set Jaccard against the same entries;
   - whether the nearest entry shares the query's (root, fault) cell, read from labels in the
     eval-only zone.

   Outputs:
   - `leakage_near_duplicates.jsonl` (flags and similarities only, no service names);
   - a summary per split with counts above 0.90, 0.95 and 0.99.

   The output directory may not be inside the evidence directory; this reuses
   `visibility.out_dir`.

## Files

| Action | File |
|---|---|
| Create | `src/rca/leakage_audit.py`, `tests/test_leakage_audit.py`, `src/rca/baro.py`, `tests/test_baro.py`, `scripts/export_baro_inputs.py` (NT114 side, writes the raw-metric inputs and their digests) |
| Created outside the repository (5a) | The isolated reference environment and the instrumented wrapper. Only `tests/fixtures/baro/*.json` and `provenance.json` are copied in |
| Modify | `src/rca/baselines.py`, `tests/test_baselines.py`, `tests/test_leakage.py` |

## Verification

- `pytest tests/test_baselines.py tests/test_leakage.py tests/test_leakage_audit.py -q` passes.
- The B1m fixture test checks the order on the evidence text used in `tests/test_visibility.py`:
  metrics services first, then logs, then traces, then the edge endpoints.
- `tests/test_baro.py` runs, and is marked skip with the reason "reference fixtures missing"
  until the fixtures exist. A label test asserts the `BARO-style (unvalidated)` naming while it
  is skipped.
- The RCA100 B3 numbers stay at 0.586 / 0.374 on the 70 tier-A injections (`label_prior:
  scored_set`). This proves that the refactor changed the labelling, not the values.
- The near-duplicate audit refuses an output path inside the evidence directory (test).

## Risks

- **B1m may be strong.** If it is close to the LLM, that is a finding about the evidence
  summary, and it changes how any H1/H3 result is framed. It is reported, not tuned away.
