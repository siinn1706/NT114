---
phase: 8
title: "Auxiliary (B) adapters and gated-source decisions"
status: deferred
priority: P3
effort: "2d"
dependencies: [5]
---

# Phase 08: Auxiliary (B) adapters and gated-source decisions

> **Deferred to milestone M3 (owner decision 2026-10-14).** No B dataset is built. The primary
> deliverables (RCAEval, Nezha, AIOps2025, RCA100, their splits, eval units and the bundle) do not
> depend on this phase: no split, condition matrix or evidence reads a B dataset, and the audit
> reports PetShop, DejaVu and Cloud-OpsBench as "not built", not missing. Running this phase later
> needs a re-run of phases 09 (audit) and 12 (a new bundle); existing manifests stay valid because
> they pin only the builds they use.

## Goal
Normalize the B datasets the later training and robustness work can use (PetShop, DejaVu,
Cloud-OpsBench), and close the decision record for every conditional source.

## Inputs
- Raw: `petshop/git-2e96f937c4c0/dataset`, `dejavu/zenodo-6955909/{A1,A2,B,C,D}.zip`,
  `cloud-opsbench/hf-1a02e54329cc`
- Phase-02 gate outcomes for RCABench, AnoMod, MSDS; OpenRCA acquisition state
- Spec: [design/adapter-contracts.md](design/adapter-contracts.md) §3.5–3.6

## Outputs
- `RCA_ROOT/data/canonical/v1/{petshop,dejavu,cloud-opsbench}/` with `eval_tier=B`
- Decision entries for `rcabench-fse26`, `anomod`, `msds`, `openrca` in
  `data/reports/compatibility-matrix.json` (adapter built: yes/no, reason)

## Files
- Create: `RCA_ROOT/src/rca/adapters/petshop.py`, `RCA_ROOT/src/rca/adapters/dejavu.py`,
  `RCA_ROOT/src/rca/adapters/cloud_opsbench.py`
- Create: `RCA_ROOT/tests/test_adapters_aux.py`
- Create (only if a gate passed in phase 02): `RCA_ROOT/src/rca/adapters/<source>.py` + tests,
  following the phase-05 pattern

## Tasks
1. Tests first (T14) from fixtures mirroring each layout.
2. PetShop: one incident per `issue_N`; keep the publisher's `train/test` folder as
   `source_split` in labels; entity kind `resource`.
3. DejaVu: incidents from each `faults.csv` (not the checkpoint copy); metrics windowed with the
   config window; entity kind `node`.
4. Cloud-OpsBench: incidents from `index.jsonl`; `app/<x>` service mapping; logs and metrics
   where present; raw refs for Kubernetes state, alerts and tool cache; trajectories and process
   labels as eval-only artefacts.
5. For each gated source, write the decision with evidence pointers. A passing source gets an
   adapter in this phase only if its effort fits ≤1 day; otherwise it is listed as ready for a
   follow-up with the spec it needs.
6. Build, validate, report.

## Tests
- T14; realdata counts: PetShop 68, Cloud-OpsBench 754, DejaVu = sum of the five `faults.csv`
  row counts from the profile.

## Completion criteria
- All B builds complete with 0 adapter exceptions; every B incident has `eval_tier=B`.
- Counts reconcile with `lineage-report.json`: PetShop 68, Cloud-OpsBench 754 (or each
  difference is explained); `python -m rca.prep audit` is re-run and stays clean.
- Every conditional source has a decision entry; none is left without a state.

## Risks and rollback
- This phase is independent of A results; if time is short it can run after phase 12 without
  blocking the LLM plan (the next plan reads only A datasets for headline evaluation).
- Rollback: delete the three canonical directories.
