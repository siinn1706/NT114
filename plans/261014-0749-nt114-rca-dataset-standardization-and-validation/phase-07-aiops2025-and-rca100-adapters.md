---
phase: 7
title: "AIOps2025 and RCA100 adapters"
status: completed
priority: P2
effort: "3d"
dependencies: [5]
---

# Phase 07: AIOps2025 and RCA100 adapters

## Goal
Add the AgenticOpsEval sources: AIOps2025 (service and pod faults as A, node faults as B) and
RCA100 (tier decided by its phase-02 gate), keeping their label-derived scoring aids eval-only.

## Inputs
- `RCA_ROOT/data/raw/agenticopseval/gitlab-69cf36430b43/{AIOps2025,RCA100}`
- Phase-02 profile: archive time zone, window→archive map, RCA100 gate
- Spec: [design/adapter-contracts.md](design/adapter-contracts.md) §3.3–3.4

## Outputs
- `RCA_ROOT/data/work/extract/agenticopseval/AIOps2025/<day>/` (intermediate, ~12 GB)
- `RCA_ROOT/data/canonical/v1/aiops2025/`, `RCA_ROOT/data/canonical/v1/rca100/` (if the gate
  passed, else built with `eval_tier=B`)
- Quality reports for both

## Files
- Create: `RCA_ROOT/src/rca/adapters/aiops2025.py` — `FAULT_FAMILY` from the 9 observed
  `fault_category` values and their `fault_type`s (explicit table; unknown → `unknown` + finding)
- Create: `RCA_ROOT/src/rca/adapters/rca100.py`
- Create: `RCA_ROOT/tests/test_adapter_aiops2025.py`, `RCA_ROOT/tests/test_adapter_rca100.py`;
  extend `tests/test_realdata_samples.py`

## Tasks
1. Tests first: T12 (fixture day archives with `._*` members, a midnight-spanning window, a
   window on a day without an archive, list-valued instance), T13 (fixture case + gt + mapping +
   topology).
2. Extract the 18 archives with `python -m rca.prep extract --source agenticopseval
   --member-glob "AIOps2025/*.tar.gz"`; verify the receipt; check disk before starting
   (`extract` refuses when free space < size estimate + reserve from config).
3. AIOps2025 adapter: join `groundtruth.jsonl` and `input.json`; map archives by the measured time
   zone; read Parquet with `pyarrow.dataset` filters on time and projected columns; entity mapping
   per spec; `key_*` and `fault_description` → `label_artifacts`; window from `start_time` and
   config offsets only; `end_time` → `truth_time.end_ns`; `context.visible_text = null`
   (adapter-contracts §3.3: the description's window length identifies the fault type).
4. RCA100 adapter: map `tNNN` via `answer_key/mapping.json`; read Parquet per case; resolve
   entities with `topology.json`; `context.visible_text` = alert title + alert entity name only
   (no `prompt_text` XML, which carries the answer-key join id); `time.end_ns = null`; alert rule
   text dropped; measure telemetry extent vs `time_range_end`; the answer key stays in
   `eval_only` (licence note in `_build.json`: controlled distribution).
4a. Label-perturbation invariance test for both adapters (as in `test_adapter_nezha.py`): change
   every label field except the anchor and the artefact contents; visible outputs must be
   byte-identical.
5. Build, validate, report. After a successful build and receipt check, `work/extract/` may be
   deleted (it is rebuildable); the report states whether it was kept.

## Tests
- T12, T13; realdata: 400 AIOps2025 incidents with tiers service+pod = A (318 expected from
  labels: 195 + 123) and node = B (82), or a documented difference; among A, list-valued
  instances split into "single named service" (top-1 scoring) and "set-scoring-only"
  (owner decision V3); 103 RCA100 cases.

## Completion criteria
- 100% of labelled incidents have records; incidents whose window has no telemetry are REJECT
  with `NO_TELEMETRY`, and their number equals the phase-02 window map.
- No free-text label artefact (`fault_description` items, RCA100 `raw_ground_truth` narrative)
  appears in `context.visible_text` or any visible JSONL text field (exact-string scan).
  `key_metrics` / `key_observations` keywords are metric names that legitimately exist in
  telemetry and are not scanned; the artefact fields themselves exist only in `label_artifacts`.
- Data-flow leakage: visible `time.end_ns` is null for both datasets; the label-perturbation
  invariance tests pass; AIOps2025 `context.visible_text` is null.
- RCA100 tier equals the gate decision recorded in `compatibility-matrix.json`.

## Result (2026-10-14)
Completed; details in [reports/phase-07-aiops2025-rca100.md](reports/phase-07-aiops2025-rca100.md).
- AIOps2025 `aiops2025-40efa9b2d22f`: 400/400 accepted (381 ACCEPT, 19 with warnings), tiers A 318
  (73 set-scoring-only) / B 82, as expected.
- RCA100 `rca100-5cd15b7a1d8f`: 103/103 accepted (9 / 94), tiers A 86 / B 17, matching the gate.
- Deviation: 0 `NO_TELEMETRY` rejects (daily metrics cover every window) instead of the phase-02
  count; log/trace gaps are `natural_absent` and reconciled in the report.
- Criteria met: no artefact text in visible records (audit scan, 96 + 640 texts), visible
  `time.end_ns` null, AIOps2025 `visible_text` null, perturbation tests pass, RCA100 tier equals
  the gate. `work/extract/` kept.
- Open owner decisions: RCA100 log/trace evidence policy, one task per injection or all 103,
  RCAEval cross-system candidates, alias and identity-rule confirmation.

## Risks and rollback
- Parquet timestamp column types may differ between days: the adapter casts per file and records
  a finding when a cast loses precision.
- Rollback: delete the two canonical directories and `work/extract/agenticopseval/`.
