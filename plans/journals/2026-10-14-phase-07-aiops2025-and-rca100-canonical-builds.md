---
title: Phase 07 AIOps2025 and RCA100 canonical builds
date: 2026-10-14
summary: "Both datasets fully accepted; audit uncovered RCA100 shared injections and two audit-scan bugs, all fixed"
---

# Phase 07 AIOps2025 and RCA100 canonical builds

## What happened
Phase 07 built AIOps2025 (400/400 accepted, `aiops2025-40efa9b2d22f`) and RCA100 (103/103, `rca100-5cd15b7a1d8f`), validated both (0 invariant errors, no-op rebuilds) and passed the full suite (202 tests).

## Problems found and fixed
- Label entity names leaked into `visible/service_map.json` via `ServiceMap.map` in `read_label`; the perturbation test caught it and labels now use `ServiceMap.resolve`.
- The audit crashed on list-valued AIOps registry entities (`TypeError: unhashable type: 'list'`).
- The audit leakage scan skipped AIOps artefacts referenced as `groundtruth.jsonl#<uuid>` (0 texts checked); it now checks 96.
- The audit found 7 unexplained RCA100 duplicate groups: 28 tasks in 11 groups were cut from one injection each (identical events export, same first alert). Adapter 1.0.1 records a label-free `group.group_id`, which audit and splits use; there are 86 independent injections.
- The AIOps evidence matched 9 label-description strings, all verbatim log text. 5 AIOps log notes come from hourly log files missing in the source.

## Decisions pending (owner)
RCA100 log/trace evidence policy; scoring one task or all tasks per injection; RCAEval cross-system candidates in 4 incidents; alias and identity-rule confirmation.

## Next steps
Owner answers, then Phase 08; re-run 09/10/12 for M2.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
