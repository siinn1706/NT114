---
phase: 9
title: "Cross-dataset quality, lineage and leakage audit"
status: completed
priority: P1
effort: "2d"
dependencies: [5]
---

> Runs once per milestone: first on RCAEval (Milestone 1), then again after phases 06/07
> (Milestone 2) and 08 (Milestone 3). Each run uses only built datasets.

# Phase 09: Cross-dataset quality, lineage and leakage audit

## Goal
Prove, across all canonical builds, that there are no unexplained duplicates, that every
incident reconciles with the acquisition lineage registry, that coverage and imbalance are
reported, and that no label can reach model-visible data.

## Inputs
- All canonical builds; `RCA_ROOT/data/manifests/{incidents.jsonl,lineage-report.json}`
- [design/quality-leakage-splits.md](design/quality-leakage-splits.md) §3–4

## Outputs
- `RCA_ROOT/data/reports/audit-<build>.json` and a Markdown summary in this plan's `reports/`
- Leakage test suite in CI-style fast suite

## Files
- Create: `RCA_ROOT/src/rca/audit.py` — fingerprints, `content_sha256` duplicate index, lineage
  reconciliation, imbalance and coverage tables, denylist and raw-path scans
- Modify: `RCA_ROOT/src/rca/prep.py` — wire `audit`
- Modify: `RCA_ROOT/src/rca/schema.py` — finalize `DECISION_STATE_ALLOWED_KEYS` from
  `gate.jev_payload` state keys (`evidence`, `assistant_first_answer`, `assistant_confidence`,
  `telemetry_available`, `similar_past_incident_similarity`)
- Create: `RCA_ROOT/tests/test_audit.py`, `RCA_ROOT/tests/test_leakage.py`

## Tasks
1. Tests first: T15 with planted duplicates across two fixture datasets; T16:
   - canary label;
   - visible-type guard: every model-facing entry point (`evidence.build`,
     `evidence.shuffled_candidates`, `llm.build_messages`, `CaseStore.search`,
     `gate.jev_payload`) is exercised with a `VisibleCase`, which has no label attributes;
   - permutation invariance (labels shuffled among test-role incidents) for evidence, prompts
     with `retrieval ∈ {none, bm25, dense, hybrid}` in `precedent` mode, and Jev states;
   - denylist, path and free-text artefact scans;
   - import boundary via `ast` (secondary check: no `CanonicalStore.labels` or `eval_only`
     access in `evidence.py`, `llm.py`, `retrieve.py`, `gate.py`);
   - the Jev allowlist on `gate.jev_payload` output, with `hit_top_sim` taken from
     `precedent` rows only.
2. Audit implementation per design §3; report per dataset × system × fault family: incidents,
   modality status counts, quality states, candidate-set size distribution, root rank among
   flagged services in `full` evidence (sanity signal for trivially easy subsets).
3. Run `python -m rca.prep audit` on the real builds; any unexplained duplicate or lineage
   mismatch becomes a QUARANTINE finding via `quality_overrides.yaml` with reason, never a silent
   drop.
4. Write the Markdown summary (counts, top findings, decisions taken).

## Tests
- T15, T16 green; all earlier tests green.

## Completion criteria
- 0 unexplained cross-dataset duplicates; every canonical incident with a lineage registry
  counterpart maps to exactly one row; counts equal `lineage-report.json` for every **built**
  dataset (B datasets are "not built" until phase 08, not "missing") or differences are explained.
- Leakage scans report 0 hits on real builds.
- Imbalance and coverage tables exist for every A dataset.

## Risks and rollback
- False positives in path scans (service names that look like path fragments): the scan uses
  path-shaped patterns (`RE\d-[A-Z]{2}/`, `_\w+/\d+/`, `fault_list`), and each exception is listed.
- Rollback: report-only phase; no canonical data changes except recorded overrides.
