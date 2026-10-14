# Phase 07: AIOps2025 and RCA100 adapters

Date: 2026-10-14. Status: completed for both builds; three owner decisions are open (end of file).
Builds: `aiops2025-40efa9b2d22f` (adapter 1.0.1), `rca100-5cd15b7a1d8f` (adapter 1.0.1).

## Outcome

Every labelled incident of both datasets is converted, valid and accepted; none is rejected or
quarantined. `validate` reports 0 invariant errors for both, a rerun of `normalize` is a no-op
with the same `dataset_digest`, the cross-dataset audit exits 0 (0 unexplained duplicates,
0 unexplained lineage rows, 0 leakage hits over 1,340 incidents) and the full test suite passes
(202 tests, 0 skipped, real-data tests included). RCAEval (`rcaeval-9bfc8d21733f`) and Nezha
(`nezha-ea30424eba55`) builds and digests are unchanged.

| Dataset | Raw cases | Parsed | Accepted (ACCEPT / with warnings) | Quarantined | Rejected | Label validity | Leakage check | Status |
|---|---|---|---|---|---|---|---|---|
| AIOps2025 | 400 | 400 | 400 (381 / 19) | 0 | 0 | 400 valid; tiers A 318 (73 set-scoring-only), B 82 | pass | ready |
| RCA100 | 103 | 103 | 103 (9 / 94) | 0 | 0 | 103 valid; tiers A 86, B 17 | pass | ready for metrics; log/trace evidence policy open |

## Warning categories

AIOps2025 (incidents with the finding): orphan spans 236 (229 info, 7 above 5% warn), multi-root
labels 128, low coverage 11 (logs 5, traces 5, metrics 1), non-finite metric values 10, empty
modality file 5, window clipped at the export edge 4. Every record carries the info finding
`LABEL_ARTIFACT_PRESENT` (artefacts held eval-only).

RCA100: non-finite metric values 103, orphan spans 103, low log/trace coverage 94 (the paged
export, below), label-following metric groups dropped 6, anchor fields disagree 2.

## Telemetry coverage

AIOps2025: metrics present in 400 (median coverage 0.968); logs present 384, `natural_absent` 16;
traces present 361, `natural_absent` 34, `empty` 5. Jaeger traces cover only frontend,
productcatalog, recommendation, cart, redis, checkout, shipping and email, so `blind_root` is not
applicable for 131 tier-A incidents whose root has no spans.

RCA100: all three modalities present in 103 (metric coverage 0.944). Logs and traces are exported
in ~300 s pages with a row cap, so median log coverage of the window is 0.22 and trace 0.28; in the
120 s after the alert the median covered time is 0 s.

## Leakage tests

- Label-perturbation invariance (fixtures, both adapters): every answer-key field changed, every
  visible file byte-identical except `repro`. The test caught label entity names reaching
  `visible/service_map.json`; label entities are now resolved without recording.
- AIOps2025: window fixed at [start − 1200 s, start + 600 s], `end_time` and the `input.json`
  description eval-only (the description's window length identifies the fault type, MI 1.04 bits,
  p < 0.001). Associations with fault type: logs status p 0.71, traces status p 0.80, low-coverage
  p 0.40, candidate count constant. Window clipping is associated with the root (p 0.037, 4 cases,
  export edges). The campaign day carries fault-type information (MI 0.91 bits, p 0.0005), so all
  incidents share one `dataset_subset` and splits must group by day.
- RCA100: anchor = first firing alert, window [t − 900 s, t + 120 s]; the answer-key window is
  unused. `prompt_text` (it carries the case-id suffix) is not copied. Two metric groups exported
  only for one fault are dropped by a label-free rule. Modality status, clipping and candidate
  count are constant; low coverage vs fault p 0.62; the evidence "less than 30 s after incident
  start" note vs fault p 0.41 (logs) and 0.46 (traces), vs root p 0.26 and 0.34.
- Audit leakage scan of the visible zone: 0 hits for all four datasets. AIOps2025 artefacts are
  referenced as `groundtruth.jsonl#<uuid>`, which the scan previously skipped (0 texts checked);
  it now checks 96 free-text artefacts (`key_*` metric names excluded per the phase spec).
- Evidence text (builder v3) built for every accepted incident and scanned for label texts:
  RCA100 103/103, 0 hits (483–2,498 characters, 8 without a pre-incident baseline). AIOps2025
  400/400 (254–2,893 characters), 9 hits, all verbatim telemetry: the matched strings occur in
  that incident's stored log rows (533–1,039 rows; 2 in one case). They are `emailservice` (a
  service name that the DNS-fault descriptions list, matched in checkout's "lookup emailservice"
  errors) and "Can't access cart storage" (a frontend error message quoted by one code-error
  description, matched in network-loss, network-corrupt and node-memory incidents). No visible
  field or evidence line is derived from a label; the perturbation tests confirm the data flow.
  An `audit --evidence-stats` run will list these 9 matches; they are explained here.
- AIOps2025 evidence notes: 5 "less than 30 s after incident start" log notes and 4 trace notes.
  The log notes are associated with fault type (p 0.007) and root (p 0.0025) on 5 cases (3 cpu
  stress, 1 memory stress, 1 jvm exception). Their cause is an hourly log file missing from the
  source archive right after the anchor (e.g. 2025-06-08 23:00 local is absent), not a label-derived
  window. Treat the 5 incidents as a stratum or drop them from log-condition comparisons; the trace
  notes show no association (p 0.67).

Sanity signal (root position in the `full` evidence): the metric ranking puts the root first in
43 of 86 RCA100 tier-A cases and in 37 of 245 AIOps2025 single-root cases; the root is not flagged
at all in 5 and 13 of them.

## Class imbalance and baselines (RCA100)

`inventory` is the primary root of 56 of 86 tier-A cases; the labels stay as given. The handoff
now requires every RCA100 result next to the majority-class baseline (0.651 top-1) and the
alert-entity baseline (0.372 top-1). This is imbalance, not leakage: no visible field encodes the
root (all associations above are non-significant or constant).

## Shared injections in RCA100 (found by the audit)

The first audit run reported 7 unexplained duplicate groups, all RCA100. Raw inspection showed
28 tasks in 11 groups cut from one injection each (byte-identical events or logs export, first
alert within 75 s, same fault id and root), leaving 86 independent injections. Adapter 1.0.1
records a label-free `group.group_id`; the audit counts linked records as explained and splits
union on it (a fixture test isolates that link from the window-overlap rule). Splits would already
have kept these tasks together through overlapping windows. Statistics must resample by injection.

## Reproducibility

- Fingerprints: the canonical build hash is unchanged by evidence settings; the evidence cache key
  adds the evidence builder version (3), its per-dataset options (`log_trace_segment_gap_s`,
  `min_after_s`), the legacy-view version (2) and the metric alignment. Changing any of them
  invalidates cached evidence.
- Rebuilds: `normalize` without `--force` picked up the RCA100 adapter version change and rebuilt;
  the next run was a no-op with digest `a118035d…`.
- Lineage against the acquisition registry: 400/400 and 103/103 matched one to one. Explained
  differences: RCA100 registry faults lack the taxonomy prefix (103) and record the answer-key
  window start, which precedes the alert anchor by ≤ 900 s (103). The audit crashed on
  list-valued AIOps registry entities; fixed and covered by the fixture test.

## Deviations from the phase file and the benchmarks

- Phase-07 criterion "windows without telemetry are REJECT `NO_TELEMETRY` and match the phase-02
  map": daily metric files cover all 400 windows, so no incident lacks all telemetry. Phase 02
  counted 42 windows without both log and trace members; 38 coincide with the build's 39
  incidents missing logs or traces, 4 reach a neighbouring hour in the wider stored window. They
  stay ACCEPT with `natural_absent` and their `no_log`/`no_trace`/`blind_*` conditions marked not
  applicable.
- AgenticOpsEval gives agents the fault window (start and end) and, in RCA100, `prompt_text`. Our
  visible records hold the start or first alert only, a fixed window, no description text
  (AIOps2025) or the alert title and entity only (RCA100). Results are not directly comparable
  with published AgenticOpsEval numbers (stated in the handoff).
- Real-data checks are in a new `tests/test_realdata_agenticops.py` instead of extending
  `test_realdata_samples.py`.
- `work/extract/agenticopseval/` (AIOps2025 day archives) is kept: real-data tests and rebuilds
  read it.
- Splits for the new datasets are generated in the planned re-run of phases 09/10 (milestone M2),
  not here.

## Service aliases and identity rules

All six `configs/service_aliases.yaml` entries are supported by RCAEval telemetry (evidence in
`docs/dataset_quality_audit.md`); they remain "owner to confirm". AIOps2025 adds adapter rules
without alias entries (redis → rediscart by `peer.service`, TiDB rows by status port, `tidb-pd-0`,
" (deleted)" pod suffix), also for confirmation.

## Open owner decisions

1. RCA100 log/trace evidence: keep the "less than 30 s after incident start" note and stratify
   (current default), use metrics-only evidence for RCA100, or compare chunk by chunk.
2. RCAEval cross-system containers: 4 incidents list the other demo system's containers as
   candidates, and in one Sock Shop incident the OB `frontend` container merges with `front-end`.
   Recommended: record the 4 uids for exclusion at evaluation now, add alias entries at the next
   scheduled RCAEval rebuild.
3. RCA100 shared injections: keep all 103 tasks with injection-level resampling (current), or
   score one task per injection (86).
4. Confirm the alias entries and the AIOps2025 identity rules listed above.
