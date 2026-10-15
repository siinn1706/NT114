---
title: "Phase 4: M3 — Baselines, confidence and the minimum experiment set (E1–E8)"
status: todo
priority: P1
effort: 10 person-days + ~3 GPU-days (weeks 4–6, 2026-11-09 → 11-27)
dependencies: [phase-03]
---

# Phase 4: M3 — Baselines, confidence and the minimum experiment set

## Context links

[Research design](design/research-design.md) §5–9 · [Architecture](design/architecture.md) §4–6 ·
`design/preregistration.md` (frozen) · handoff §2a/§2b

## Goal and research justification

Produce every number the minimum paper needs: RQ1–RQ5 on RCAEval with confirmatory statistics,
and replications on Nezha, AIOps2025 and RCA100. Run the grids first (GPU), then all policies
offline (CPU). End with the week-6 checkpoint decision.

## Dependencies

Phase 03 exit (frozen prompt, Jev wording, preregistration, `tuned.json`).

## Tasks

1. **Non-LLM baselines (`baselines.py`)** — *B0, B1 and B3 implemented on CPU ahead of this phase
   (2026-10-15): `python -m rca.baselines configs/exp/baselines-rca100.yaml` gives majority 0.586 /
   alert-entity 0.374 on the 70 tier-A injections (0.651 / 0.372 per task) and 0.477 / 0.304 on all
   103 tasks / 86 injections; B1 needs the evidence files of `prepare`; B2 still to do.* B0 random (analytic per incident), B1 max-z from
   evidence features, B3 RCA100 majority (`inventory`, train prior) and alert-entity (from the
   visible first alert), B2 BARO via the `RCAEval` package in a **separate venv** on RCAEval RE2/RE3
   metrics, through `legacy_view.legacy_telemetry` wide frames. Expect the protocol numbers for B3:
   0.586 / 0.374 on the 70 tier-A injections (injection-weighted), else stop and investigate.
2. **E1 LLM-only grid**, primary model: RCA-Z, DEV, NEZ, AIO, R100 (cell-held-out `within-rcaeval-grouped` sets, research-design §6), all applicable conditions,
   retrieval none (`configs/exp/main-primary.yaml`).
3. **E2 retrieval arm**: DEV, RCA-T and NEZ with hybrid/precedent. NEZ uses the train store of
   `xdata-rcaeval-to-nezha`.
4. **E3 escalation arm**: escalation model on DEV, RCA-T, NEZ, AIO, R100 (`main-escalation.yaml`).
5. **E7 replication**: replication model on RCA-T, retrieval none and hybrid (`main-replication.yaml`).
6. **E4 Jev decisions**: `rca.decide` on DEV, RCA-T, NEZ, AIO, R100 for variants J-full and
   J-AA; E7's grid with J-full. Subject to D3 for AIO/R100.
7. **E8 Jev robustness**: option rotations (DEV, RCA-T), repeat-call stability (DEV), J-noconf
   (DEV + RCA-T), J-noevidence (DEV; also the preregistered state for AIO/R100 if D3 = no). J-short
   is optional (O10).
8. **E5 policies and controls** (offline): L0, L1, L2, J, J-floor, J-AA, C1, C2, R1, R2, C3, C4, O, on
   every set; the utility with wrong penalties {1, 2, 5} as secondary.
9. **Confidence analysis**: per condition, ECE/Brier/gap/AUROC/AUPRC for verbal, consensus,
   recalibrated consensus (map from DEV) and Jev `supported`; reliability diagrams; risk–coverage.
10. **Confirmatory analysis** exactly as preregistered (Holm family on RCAEval); replication
    tables per external dataset; strata per protocol §2b.4; AIOps2025 with and without the 5
    short-log incidents; RCA100 next to B3.
11. **Week-6 checkpoint** (in `decisions.md`): decide phase 05 (training gate) and which optional
    extensions O1–O9 go into phase 06, by expected information per GPU-day.

## Existing modules to reuse

`run_grid`, `decide`, `gate` policies, `metrics`, `analyze`; `retrieve.CaseStore`; `eval_units`.

## Files

| File | Action |
|---|---|
| `src/rca/baselines.py`, `tests/test_baselines.py` | create |
| `configs/exp/main-primary.yaml`, `main-escalation.yaml`, `main-replication.yaml`, `jev-main.yaml` | create |
| `src/rca/analyze.py` | modify (confirmatory report, replication tables, figures 1–5 drafts) |
| `results/<exp>/` | generated, git-ignored; manifests and summary tables copied to `paper/results/` (phase 06) |

## Interfaces and contracts

Inputs frozen by phase 03. Output tables: `table_accuracy_by_condition.csv`,
`table_confidence.csv`, `table_policies.csv`, `table_confirmatory.csv` (estimate, CI, p, p_holm,
n_injections), `table_replication_<dataset>.csv`; each has a header row with the manifest sha.

## Testing strategy

| Check | Pass condition |
|---|---|
| `test_baselines.py` | B3 reproduces 0.586 / 0.374 on the 70 tier-A RCA100 injections (realdata marker); B0 equals 1/\|C\| |
| Grid completeness | every (model, set, condition, arm) cell has the expected row count from the condition matrix; 0 parse-failure-only incidents unexplained |
| Jev | error rate ≤ 1 % per set; 100 % rows `jev-1.13.0` |
| Determinism | rerunning `analyze` gives byte-identical tables (bootstrap seed fixed) |
| No DEV leakage | headline tables contain no `val`-role uid (guard + test) |

## Acceptance criteria / Definition of Done

- [ ] E1–E8 complete with manifests; B0–B3 computed
- [ ] Confirmatory table for the 8 contrasts (H1a, H1b, H2a, H2b, H3a, H3b, H4b, H4c) with CIs and Holm p-values; H4a and H5 reported as secondary
- [ ] Replication tables for NEZ, AIO (± 5 short-log), R100 (headline: 86 tier-A tasks / 70 injections, next to B3; secondary: 103 tasks / 86 injections)
- [ ] Confidence and policy tables with risk–coverage figures
- [ ] Week-6 checkpoint decision logged (training gate, optional extensions)

## Risks

| Risk | Mitigation |
|---|---|
| GPU time overruns | Scope cut order: E7 retrieval arm → E3 on AIO → n = 5 samples (logged deviation) |
| Retrieval changes AC@1 by < 2 pp everywhere (note's checkpoint) | RQ5 becomes a negative result; Jev keeps the retrieve action for completeness; paper focus on RQ1–4 |
| AC@1 near random on external sets | Report it; external sets still test calibration/overconfidence; no prompt change post-freeze |
| Jev rate limit | Cached, resumable, spread over days; start E4 on DEV/RCA-T first |

## Security

Same as phase 03. Results contain labels (`truth`) and stay on the private machines and the
private HF repo only.

## Next

Phase 05 (if the gate passes) and phase 06.
