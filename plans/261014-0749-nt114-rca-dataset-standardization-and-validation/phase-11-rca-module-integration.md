---
phase: 11
title: "Integration with the existing RCA modules"
status: completed
priority: P1
effort: "2d"
dependencies: [10]
---

# Phase 11: Integration with the existing RCA modules

## Goal
Let `run_grid` prepare and run on canonical data and split manifests with minimal edits, while
the legacy RCAEval directory path and `configs/synthetic.yaml` keep working.

## Inputs
- `RCA_ROOT/src/rca/{data,ablate,evidence,retrieve,run_grid}.py`; `legacy_view.py`; split manifests
- Golden file from phase 01

## Outputs
- Canonical configs and an end-to-end synthetic run through the canonical path

## Files
- Modify: `RCA_ROOT/src/rca/run_grid.py`
  - `load_cfg`: `open(path, encoding="utf-8")`
  - `select_cases`: if `cfg["source"] == "canonical"`, read `CanonicalStore` filtered by
    `split_dir` + `split_role` (default `test`) and quality state; else the current
    `discover_cases` path
  - Model-facing calls receive `VisibleCase` only (D13): `evidence.build(vc, ...)`,
    `evidence.shuffled_candidates(vc)`, `build_messages(vc, ...)`, `store.search(..., vc, ...,
    exclude_ids=...)`. `Truth` is used only by `ablate.apply` (target), `rank_of_truth`, the
    oracle exclusion set and the result-row `truth` field. In the canonical path
    `vc.case_id = incident_uid`.
  - `prepare`: telemetry from `legacy_view.legacy_telemetry` for canonical sources; conditions
    taken from `condition-matrix-<dataset>.json` (not `ablate.applicable`); evidence file holds
    `{"incident_uid", "system", "candidates", "conditions", "schema": 2}` and **no** label fields
    (D3); relative paths only (D12); `blind_nonroot` target from `ablate.choose_nonroot_target`;
    eval-only ablation log `ablation_log.jsonl` written next to the results (not in the evidence
    dir); UTF-8 writes (D2)
  - `prepare` also builds `full`-condition evidence for **every** train-role incident of the
    configured split into `<evidence_dir>/store/` (not limited by `limit_per_system`; optional
    `store_limit`), because the retrieval store needs it (F6)
  - `load_evidence`: reads schema 2 and the legacy format; labels joined from
    `CanonicalStore.labels` (canonical) or from the legacy `case` block (legacy files)
  - `run`: the case store is built from `<evidence_dir>/store/` (train role) when a split is
    configured (D4); otherwise the current behaviour. `precedent` passes the query's `group_id`
    members as `exclude_ids` (label-free); `no_precedent` adds same-(root, fault) uids from
    `Truth` and its rows carry `oracle_store: true`. Result rows keep every existing field and add
    `incident_uid`, `pair_id`, `split_id`, `oracle_store`
  - Retrieval configs use the `within-*-retrieval` split; gate/fine-tuning configs use
    `within-*-grouped`
- Modify: `RCA_ROOT/src/rca/data.py` — none beyond phase 05 (verify)
- Unchanged: `evidence.py`, `llm.py`, `gate.py`, `metrics.py`, `analyze.py` (they only read
  `case_id`, `system`, `inject_time` and `services`, which `VisibleCase` provides). `retrieve.py`
  was changed in phase 10 (`exclude_ids`)
- Note for the next plan: `gate.action_table` defaults to `store_mode="no_precedent"`
  (`gate.py:28`); Jev and headline gate runs must pass `store_mode="precedent"` (recorded in the
  handoff)
- Create: `RCA_ROOT/configs/canonical_synthetic.yaml` — synthetic data built through the RCAEval
  adapter's directory mode, mock backend
- Create: `RCA_ROOT/configs/canonical_pilot.yaml` — RCAEval RE2+RE3, `within-rcaeval-grouped`
  split, `limit_per_system: 10`, same models block as `pilot.yaml`
- Create: `RCA_ROOT/tests/test_run_grid_canonical.py`
- Modify: `RCA_ROOT/README.md` — a short section "Canonical data path" (commands only; links to
  `docs/data_contract.md` written in phase 12)

## Tasks
1. Tests first: T19 (canonical synthetic end to end, mock backend; asserts no label keys in
   evidence files; the store is **non-empty** and its uid set **equals** train-role ∩ eligible;
   no test or validation uid in the store; generated conditions equal the condition matrix;
   result row fields ⊇ the fields read by `gate.action_table` and `analyze.load`).
2. Implement the `run_grid` edits above; keep functions small; no new abstractions beyond
   reading the store.
3. Re-run T02 golden comparison on the legacy synthetic config (visible part must match).
4. Run `canonical_pilot.yaml` `prepare` on real RCAEval (no LLM call); report counts per condition
   and the evidence length distribution (chars) against `MAX_CHARS`.

## Tests
- T19, T02, T01, T10, T16 green.

## Completion criteria
- Legacy synthetic run output (visible part) equals the golden set.
- Canonical synthetic run completes with the mock backend; `analyze` runs on its JSONL.
- No evidence file contains `root_service`, `fault` or a source path.

## Risks and rollback
- `analyze.py` or `gate.py` may read a field that moved: T19 asserts the field set; any needed
  field stays in the result row.
- Rollback: revert `run_grid.py`; legacy configs are unaffected by the new configs.
