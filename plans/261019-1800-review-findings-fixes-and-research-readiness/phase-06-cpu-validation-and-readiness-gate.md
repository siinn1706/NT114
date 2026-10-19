---
title: "Phase 06: CPU validation and DEV-pilot readiness gate"
status: completed
priority: P1
effort: 0.5-1 d
dependencies: [phase-01, phase-02, phase-03, phase-04, phase-05]
---

# Phase 06: CPU validation and readiness gate

## CPU validation (tier 1)

Run from `nt114-rca/nt114-rca`, analysis venv, `PYTHONPATH=src`, basetemp outside `plans/`:

1. `python -m pytest -m "not realdata" -q -rfE` → 0 failures, or each remaining failure classified as
   environment in the phase 00 report with its reproduction command.
2. `python -m pytest -m realdata -q -rfEs` where raw data exists; skips counted, not claimed as passes.
3. Offline smoke chain at the top of `configs/exp/smoke-offline.yaml` (synthetic, mock) → grid, raw,
   manifest v3 with `exec_sig` and store block, tables; then `python -m rca.reproduce <out>` → 0.
4. Canonical smoke chain (`configs/exp/smoke-canonical.yaml`, mock backend) on the verified bundle.
5. Evidence fingerprints: rerun the digest comparison used in the single-LLM plan
   (`reports/evidence-digests-after.txt`) → 0/862 changed.
6. Leakage: `tests/test_leakage.py` and `rca.leakage_audit` on the RCAEval grouped store config;
   manifest shows the store bound to `within-rcaeval-grouped-0-e9b2c81c`.
7. Prompt freeze: hash of rendered prompts on 5 synthetic incidents × {none, hybrid} equals the
   pre-phase-01 hash (record it in phase 01 before editing).
8. V7 real-slice reproduce (research/05) exits 0.

## DEV-pilot readiness (tier 2): checklist, not executed here

- [ ] Tier 1 green.
- [ ] `llms.txt` chain on the GPU machine: bundle at pinned revision, portability at the bundle
      commit, recheck with `main`, Linux gate, GPU probe, feasibility on DEV with the completion parse
      gate (phase 03).
- [ ] `dev-pilot.yaml` dry checks: `prepare` writes the store for the grouped split's train role only;
      on a fresh evidence dir the manifest reports 0 ignored store files. `dev-sampling.yaml` shares
      that evidence dir, so check its manifest too.
- [ ] Q1 pilot spec frozen in the repo: estimators in `src` (phase 05), pool `single_modality`
      declared in the DEV analysis config, SESOI confirmed by the owner, `pilot_decision` inputs named.
- [ ] Owner approval to run the model.

## Main-experiment readiness (tier 3): checklist

- [ ] DEV pilot finished; `pilot_decision` result and measured consensus distribution/ICC recorded;
      `h1_power.py` rerun with measured parameters.
- [ ] Confirmatory family chosen; preregistration frozen; `preregistration_sha` set.
- [ ] DEV thresholds frozen (tau values and source strata written before any test run).
- [ ] Headline guard passes on a dry frame (mixed signature, DEV, mock, oracle checks).
- [ ] Test-role config uses a fresh `out` and evidence dir; manifest signature recorded.

## Output

`plans/reports/test-261019-<hhmm>-cpu-validation-readiness.md`: each check with command, exit code,
counts; tier verdicts.

## Acceptance

- [ ] Checks 1-8 recorded with exit codes; tier 1 verdict stated plainly.
- [ ] Tier 2 and 3 checklists copied into the report with the items still open.
