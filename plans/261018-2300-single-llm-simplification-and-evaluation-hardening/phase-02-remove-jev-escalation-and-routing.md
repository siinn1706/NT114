---
title: "Phase 2: Remove Jev, the escalation role and model routing"
status: done
priority: P1
effort: 2-3 d
dependencies: [phase-00, phase-01]
---

# Phase 2: Remove Jev, escalation and routing

## Context

[Scout report §1](research/scout-report.md#1-where-jev-and-the-multi-model-routing-live) lists
every Jev seam with line numbers. Nothing here has produced a real result, because every grid on
disk is mock. That means no backward-compatibility burden exists for the grid or decision
formats, except the mock smoke outputs, which are regenerated.

## Requirements

1. No source, test, config or evergreen doc mentions Jev, TypeSafe or escalation.
2. The single-LLM invariant is enforced in code:
   - `run_grid` accepts the model roles `primary` and `replication` only;
   - no grid row depends on another model's row;
   - the `model_role` field stays, so existing analysis keys stay stable.
3. The kept parts of `gate.py` move to `src/rca/selective.py`:
   - `outcomes`, `evaluate`, `fixed`, `coverage_matched_threshold`, `coverage_matched_random`,
     `evaluate_draws` and `oracle_policy`;
   - the `oracle_store` refusal that lived in `decide.select_rows`.

   The action set becomes `answer` / `abstain`, plus `retrieve`, which means "the answer of the
   cached retrieval cell of the same model". There is no `escalate`.
4. The evidence builder, prompt, cache key, scoring and splits stay unchanged. Phase 06 checks
   the evidence fingerprints against the digests from phase 00.

## Files

**Delete**

- `src/rca/jev.py`
- `src/rca/decide.py`
- `tests/test_jev.py`
- `tests/test_decide.py`

**Create**

- `src/rca/selective.py` (the kept evaluator, with an English docstring)
- `tests/test_selective.py` (ports the kept assertions of `tests/test_stats.py:90-127`)

**Delete after porting**

- `src/rca/gate.py`

**Modify**

| File | Change |
|---|---|
| `src/rca/schema.py` | Drop `DECISION_STATE_ALLOWED_KEYS`. Keep `denylisted` (used by the leakage tests) |
| `src/rca/run_grid.py` | `MODEL_ROLES = ("primary", "replication")`. Drop the Jev manifest fields and `from . import jev` |
| `src/rca/analyze.py` | Drop `policy_table`, `jev_score_table`, `decision_report`, the Jev checks in `guard_headline`, the `--gate` and `--decisions` CLI options, and the `gate` import. Phase 03 rebuilds the tables |
| `src/rca/data.py:35`, `src/rca/feasibility.py:12`, `src/rca/visibility.py` (docstring) | Remove Jev wording |
| `configs/exp/smoke-offline.yaml`, `smoke-canonical.yaml`, `dev-pilot.yaml` | Drop the `jev:` blocks and the `mock-escalation` models |
| `configs/hardware/rtx4080-laptop-12gb.yaml` | Change the role of the two former escalation profiles to `replication` (their capacity data stays useful) |
| `tests/test_leakage.py` | `MODEL_FACING` = `evidence.py`, `llm.py`, `retrieve.py`. Delete the Jev-state tests (lines 136-153 and the parts at 72-73, 199-251). Keep and adapt the `no_precedent` refusal test to `selective` |
| `tests/test_stats.py` | Remove the gate tests that were moved |
| `tests/test_visibility.py:98` | Module list without `jev` and `decide`; add `selective` |
| `tests/test_feasibility.py:64,221` | Keep the assertions that `jev` is absent. They now also guard against reintroducing it |
| `README.md`, `docs/data_contract.md` (§8 and lines 4, 13, 198-214), `docs/gpu_deployment.md` | Remove the Jev steps and the key handling. Renumber the deployment steps |

## Steps

1. Run the narrow tests first: `pytest tests/test_leakage.py tests/test_stats.py -q`. Record
   the baseline pass count.
2. Create `selective.py` by moving the code, with no behaviour change. Port the tests and run
   them.
3. Delete the Jev modules and tests. Strip `analyze`, `schema` and `run_grid`.
4. Edit the configs and docs.
5. Run the full non-realdata suite, then the mock end-to-end chain on synthetic data:
   `prepare` → `run` (mock) → `analyze`.

## Verification

- `grep -riE "jev|typesafe|escalat" src tests configs docs README.md` returns no match. The
  only allowed exception is the `"jev" not in cfg` assertions in `test_feasibility.py`; the grep
  in the Definition of Done excludes that one file explicitly.
- `pytest -m "not realdata"` passes. The count equals the old count, minus the deleted Jev tests,
  plus the new tests.
- `python -m rca.run_grid run configs/exp/smoke-offline.yaml` raises `ValueError` if a model with
  `role: escalation` is added (new test).
- `git diff --stat` shows that no file under `src/rca/adapters/`, `evidence.py`, `llm.py`,
  `splits.py` or `score.py` changed.

## Risks and rollback

- Hidden consumers of `gate`: `analyze` is the only importer (verified by grep). Rollback is
  `git checkout` of the phase-00 commit or tag.
