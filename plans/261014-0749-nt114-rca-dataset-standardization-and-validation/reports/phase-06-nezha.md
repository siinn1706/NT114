# Phase 06: Nezha adapter

Date: 2026-10-14. Status: completed. Build `nezha-ea30424eba55`, adapter 1.0.3.

## Outcome

All 101 Nezha incidents (56 Online Boutique, 45 Train Ticket) are converted and accepted, all as
ACCEPT_WITH_WARNINGS for measured reasons. Every label is valid and tier A, every root is a
candidate, `validate` reports 0 invariant errors, and a rebuild is a no-op with the same
`dataset_digest` (`56ec3db8aef93edca59346ad82b3e09f81a024cb7ed7b6c4ae80267f166c8217`).
Evidence text was built for all 101 incidents (146–3,286 characters, none above 14,000), and the
evidence leakage scan found 0 hits.

## Why the first build accepted 0 of 101

The first real build (adapter 1.0.0) rejected 96 incidents and quarantined 5, although the 8
fixture tests passed. The fixture tests never checked quality states or schema validity.

1. **Schema mismatch (96 REJECT, `SCHEMA_INVALID`).** The adapter wrote
   `anchor_original = {unit: "datetime", ..., inject_timestamp: ...}`; the schema allows units
   `s|ms|us|ns|iso8601` and no extra key. Fixed in the adapter, not the schema: unit `iso8601`
   (`YYYY-MM-DD HH:MM:SS`), and the disagreeing `inject_timestamp` stays in the label record and
   in the `ANCHOR_FIELD_DISAGREE` finding.
2. **Torn CSV row (5 QUARANTINE, `ADAPTER_EXCEPTION`).** `2023-01-29/log/10_06_log.csv` data row
   629 is a complete row followed by the tail of another row (10 fields, header 8); a scan of all
   1,031 Nezha CSV files found no other malformed row. The adapter now re-reads such a file row by
   row, drops only the malformed row, keeps raw row indices in `src_row`, and records a
   `PARSE_ERROR` (warn) naming the file and row.

A third defect surfaced while checking the warnings: 124 Train Ticket ERROR log rows carry the
overflow sentinel `-6795364578871345152` in `TimeUnixNano` and were dropped as
`TS_OUT_OF_RANGE` in 21 incidents. Their `Timestamp` column is UTC (the UTC+8 time inside each
message agrees), so the adapter now takes their time from it and records `TS_COLUMN_OFFSET`
(info). No validation rule was relaxed.

## Quality states and findings

| Finding | Incidents | Severity | Cause |
|---|---|---|---|
| BASELINE_CONTAMINATED | 86 | warn | another injection inside [t − 600 s, t + 300 s] |
| LOW_COVERAGE (logs, traces) | 66 | warn | logs/traces exist only in ~3-minute bursts (below) |
| WINDOW_CLIPPED | 16 | warn | window crosses the first or last minute file of a day |
| PARSE_ERROR | 10 | warn | 5 torn-row, 5 non-JSON `Log` fields kept as raw text |
| PRE_WINDOW_SHORT | 4 | warn | 4–54 s of data before the anchor; excluded from all conditions |
| TS_COLUMN_OFFSET | 45 | info | 24 metric `TimeStamp` offsets; 21 recovered sentinel log times |
| ANCHOR_FIELD_DISAGREE | 29 | info | `inject_timestamp` ≠ `inject_time` |

The full per-incident list is `data/canonical/v1/nezha/eval_only/quality.jsonl`.

## Completion criteria

- 100% of incidents have records: 101/101.
- Root ∈ candidates for every A-tier incident: 101/101.
- All three modalities non-empty on both sides of the anchor in [t − 600 s, t + 300 s]: 98/101
  (97%, gate ≥ 95%). The 3 shortfalls have no metric rows before the anchor (clipped at the day's
  stream start).
- Conditions: 97 incidents × 6 conditions; the 4 PRE_WINDOW_SHORT incidents are inapplicable with
  that reason. Split `eval-only-nezha-0-38cde4e0` (test 101, 7 groups, largest 34) verifies OK.

## Log/trace evidence window (owner decision 2026-10-14: option b, applied)

Each Nezha minute file holds rows from 41 s before to 20 s after its minute, and only the three
files from each injection minute exist, so logs and traces cover about [t − 95 s, t + 85 s]
around each injection. The default evidence compares logs and traces in the 5 minutes after the
anchor with the 10 minutes before; for Nezha that "before" window held the incident's own burst
plus, in 86 incidents, an earlier injection's fault burst. The data are correct; that baseline
was not fault-free.

Applied: `configs/prep.yaml` `evidence.log_trace_segment_gap_s: {nezha: 30}`. For Nezha only,
`evidence.build` compares logs and traces inside the contiguous stretch of rows (gaps ≤ 30 s)
holding the anchor, clipped to [t − 600 s, t + 300 s], and divides counts by the seconds actually
covered. With under 30 s of pre-anchor data the text says "no pre-incident baseline recorded"
instead of comparing. Metrics and every other dataset keep the fixed windows, and their text is
unchanged. The `evidence` section is excluded from the build hash, so no rebuild was needed.

Measured on the real build (all 101 accepted incidents, `nezha-ea30424eba55`):

| | Fixed windows | Burst segment |
|---|---|---|
| Evidence built / failed | 101 / 0 | 101 / 0 |
| Characters min / median / max | 146 / 1786 / 3286 | 313 / 1903 / 3584 |
| Incidents stated as "no pre-incident baseline" | — | 8 |
| Evidence leakage scan hits | 0 | 0 |
| Metric z-score ranks root first | 20 / 101 | 20 / 101 |
| Root not flagged | 3 | 3 |

The metric ranking is unchanged by design (metrics are continuous). The 8 no-baseline incidents
are a remaining property of the source: their own burst starts less than 30 s before the anchor.

## Tests

- `tests/test_adapter_nezha.py`: 12 tests, including schema/state checks, the torn row, the
  sentinel time, and label-perturbation invariance (visible outputs byte-identical when every
  label field except `inject_time` and the artefact contents change).
- `tests/test_realdata_nezha.py`: 7 tests on the real build (counts, states, anchors, the torn
  row, sentinel rows, seeded raw-vs-canonical parity for logs, traces and metrics).

## Lineage and cross-dataset audit

The first audit with Nezha found 202 unexplained lineage rows. Two causes, neither in the data:
the adapter wrote `source_incident_id` as `nezha:<date>_<hh>_<i>` while the registry uses
`nezha:<date>:<hh>:<i>` (adapter 1.0.3 uses the registry form; uids, telemetry and visible
records are unchanged), and the audit compared the registry's deployment name with the whole
Nezha fault-list entry (it now accepts the raw pod or its deployment). The 29 remaining anchor
differences are classified as explained only where the registry time equals the label's own
`inject_timestamp`. Audit `audit-1f527b64de9c.json` (RCAEval + Nezha, 837 incidents): 0
unexplained lineage rows, 0 duplicates, 0 cross-dataset overlaps, 0 leakage hits, 0 split errors;
exit 0. The eval-only split was re-pinned to the new build; the manifest pinned to the old build is
kept under `data/splits/_superseded/`.
