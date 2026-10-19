---
title: "Phase 6: CPU-only validation experiments"
status: blocked
priority: P1
effort: 2-3 d (plus about 2 h of unattended CPU time for the RCAEval store)
dependencies: [phase-03, phase-04, phase-05]
---

# Phase 6: CPU-only validation experiments

**Status (2026-10-19).**
- **Done:** V1–V7, and V8 step 1 (the RE1 inventory in `results_alignment/re1/`).
- **Blocked:** V8 step 2. The DecompRCA release returned HTTP 404 from the web and from the
  GitHub API (`results_alignment/re1/provenance.json`).
- **Until step 2 runs:** no paper-level alignment is claimed, and the paper's numbers stay
  external reference values.
- **To unblock:** inspect the release once it is public, then run
  `python -m rca.alignment compare`.

## Context

These are the only results this plan produces. None of them needs model output. Each one is a
precondition for interpreting a later GPU result. The evidence files are reused from
`results_visibility/<ds>/evidence/` (prepared on 2026-10-18), so no telemetry is re-read, except
for the RCAEval retrieval store.

## Experiments

| ID | Question | Command (sketch) | Output |
|---|---|---|---|
| V1 | Did the refactor change any evidence? | Recompute sha256 of every `results_visibility/*/evidence/*.json` and compare with `reports/evidence-digests-before.txt` (phase 00) | Pass/fail plus a count |
| V2 | Evidence-instrument audit: what does each manipulation actually change? | Read the visibility JSONL and the evidence files. Per dataset × split role × condition: `same_as_full` rate, truncation rate, prompt-token distribution (`rca.capacity` prompt stats), block presence, named-service count | `/research/05_evidence_instrument_audit.md` |
| V3 | How strong are the non-LLM baselines on every cell? | `python -m rca.baselines configs/exp/baselines-<ds>.yaml` for the 4 datasets. New configs reuse the visibility evidence dirs and split roles. B0, B1 (each modality), B1m, B3 | `results_baselines_<ds>/`, in a combined table |
| V4 | Is the statistics engine calibrated on this data's cluster structure? | Simulation with the **real** injection structure of each dataset (from the eval-units reports): 1,000 replications of null and of shifted paired binaries, giving the CI coverage and type-I error of the contrast engine | `/research/06_statistics_validation.md` |
| V5 | What effects can the sets detect? | MDEs for paired AC@1 contrasts on the measured intersections (for example the RCAEval test `blind_root ∩ blind_nonroot_ev` incidents and injections). Discordance assumptions are 10 %, 20 % and 30 %, computed by simulation through the same engine. They are placeholders until a DEV pilot exists | Section in research/06 |
| V6 | Is there text-level leakage from the store? | `prepare` with `retrieval: [hybrid]` on the grouped split builds the 374 train-role store files (about 18 s each, about 2 h unattended). Then `python -m rca.leakage_audit` over val and test | Section in research/05 |
| V8 | Do NT114's 375 RCAEval RE1 incidents correspond to the decomposition paper's RE1 benchmark (125 per system)? | `python -m rca.alignment` (new, CPU-only, eval-only). Step 1 runs inside NT114: for each RE1 incident it writes the canonical incident uid, the source case id, the system, the injection timestamp and a telemetry fingerprint (sha256 of the raw metric file, plus a canonicalised content hash). Step 2 compares these with the DecompRCA release, **after the release has been inspected**. A match needs an equal system, an equal injection timestamp and an equal fingerprint, and partial matches are listed by which key failed | `results_alignment/re1/` and a section in research/05 |
| V7 | Does the simplified pipeline run end to end and reproduce? | The synthetic mock chain: `prepare` → `run` (mock LLM) → `analyze` → `reproduce`. Also one real-dataset slice with the mock LLM (Nezha, 97 incidents; evidence reused) | Pass/fail, recorded in the plan |

**External reference values.** The decomposition paper's published BARO and LLM results on
RCAEval RE1 (Online Boutique, Sock Shop and Train Ticket, with 125 incidents each) are entered
into `/research/02_research_directions.md` (H3). Each value carries its table or figure
reference. They appear next to V3 only in a separate "external reference, not directly
comparable" block.

A direct comparison needs five alignments, each verified and recorded:

- the incident IDs;
- the preprocessing;
- the split;
- the label granularity;
- the candidate set.

Until then, no NT114 number is placed in the same column as these values, and no difference
between them is computed.

**Status of RE1 alignment (2026-10-18).** The 375 RE1 cases are treated as a **likely shared
upstream benchmark**. They are not a verified one-to-one match with the paper. V8 is the check:

- It reads labels only for the eval-only report. Its outputs are written outside every evidence
  and model-facing directory, enforced the same way as `visibility.out_dir`.
- No uid, timestamp or fingerprint mapping reaches a prompt, an evidence file or the cache key.
  The model-facing import test covers `rca.alignment`.
- Step 2 cannot run until the DecompRCA release has been inspected: its file list, its
  incident identifiers and its preprocessing scripts. Claude Code downloads the release under
  the Internet policy in plan.md:
  - into its own directory outside the repository;
  - treated as untrusted data;
  - with its URL, version or commit, access date and per-file sha256 recorded in
    `results_alignment/re1/provenance.json`.
- Until step 2 passes, no claim of paper-level alignment is made, and the paper's published
  results stay external reference values.
- Even a full V8 match aligns only the incidents and the telemetry. Preprocessing, split,
  granularity and the candidate set still need their own checks.

## Rules for the reports

- Every number gives its numerator, denominator, percentage and exclusions.
- Observations are kept apart from causal claims.
- A missing root name is never described as making a correct answer impossible.
- Mock-LLM outputs are never reported as results. V7 is a plumbing check only.
- No GPU and no real-model inference. Downloads follow the Internet policy in plan.md.

## Files

| Action | File |
|---|---|
| Create | `src/rca/alignment.py`, `tests/test_alignment.py`, `configs/exp/baselines-{rcaeval,nezha,aiops2025}.yaml` (RCA100 exists), `configs/exp/store-rcaeval-grouped.yaml`, `configs/analysis/*.yaml` for V7, `/research/05_evidence_instrument_audit.md`, `/research/06_statistics_validation.md`, `scripts/simulate_contrasts.py` (if it is not part of `rca.contrasts`) |
| Outputs (git-ignored) | `results_baselines_*/`, `results_store/`, `results_leakage/`, `results_v7/`, `results_alignment/` |

## Verification

- V1 passes, meaning zero changed digests. Any change stops the phase and is reported.
- V4: CI coverage is within [0.93, 0.97] and type-I error ≤ 0.07 for every dataset structure.
  Otherwise the bootstrap method is revised in phase 03 before any GPU work.
- V7: `rca.reproduce` exits 0 on both runs.
- Each research report ends with its unresolved questions.

## Risks

- **V6 can find near-duplicates on the cell-held-out split** (for example, the same system under
  the same load gives near-identical metric lines). If it does, retrieval claims need a
  similarity-stratified analysis. That is reported here; it is not fixed by changing the split.
