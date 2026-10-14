# CanonicalIncident schema v1 and storage layout

Contract file (created in phase 03): `RCA_ROOT/schemas/canonical_incident.v1.schema.json`
(JSON Schema 2020-12). The Python mirror is `RCA_ROOT/src/rca/schema.py`. JSON Schema is the single
source of truth; `schema.py` loads it, validates with `jsonschema`, and adds the cross-field
invariants that JSON Schema cannot express.

## 1. Design decisions

| Decision | Choice | Reason |
|---|---|---|
| Visible vs ground truth | Two physically separate zones per dataset: `visible/` and `eval_only/` | A loader for prompts, evidence or Jev can be given only `visible/`. Leakage then requires an explicit cross-zone read, which tests can forbid |
| Record files | JSON Lines, UTF-8, `\n`, keys sorted, one record per line, sorted by `incident_uid` | Small (≤ a few MB per dataset), diffable, deterministic, readable on any OS |
| Telemetry | Apache Parquet (pyarrow), zstd level 3, one file per incident and modality, explicit Arrow schema | Columnar, compressed 5–10× over CSV, lazy column reads, identical on Windows and Linux |
| Time | `int64` nanoseconds since the Unix epoch, UTC, in every canonical column; the original value and unit kept in the record | One unit removes the s/ms/µs/ns mix; int64 avoids tz-aware Arrow types that differ across pandas versions |
| Incident id | `incident_uid = "<dataset_id>.<first 16 hex of sha256(dataset_id + '|' + source_incident_key)>"` | Opaque (RCAEval paths contain the label), stable across rebuilds, safe as a Windows file name |
| Unknown values | JSON `null` plus a sibling `*_status` or `findings` entry; the string `"UNKNOWN"` only in provenance text fields | Distinguishes "not provided by source" from "not computed" |
| Large telemetry | Lazy references: the record lists relative paths and summary stats; data is read only on demand | Record files stay small; GPU machine can load one incident at a time |
| Wide vs long metrics | Long format in canonical storage; wide view built on demand for the legacy pipeline | Heterogeneous sources (per-pod files, per-service columns) fit one long schema without inventing column names |

## 2. Layout of one canonical dataset

```text
data/canonical/v1/<dataset_id>/            dataset_id ∈ {rcaeval, nezha, aiops2025, rca100, cloud-opsbench, petshop, dejavu, ...}
├── _build.json                            build receipt: schema + adapter version, config hash, input digests, counts, timings
├── visible/                               model-safe zone
│   ├── incidents.jsonl                    IncidentRecord per incident
│   ├── service_map.json                   per system: raw identifier → service_id, rule used, declared aliases
│   └── telemetry/<incident_uid>/{metrics,logs,traces}.parquet
└── eval_only/                             never read by evidence, prompt, retrieval-query or Jev code
    ├── labels.jsonl                       LabelRecord per incident
    ├── source_index.jsonl                 incident_uid → original id, raw member refs (with sha256), label files
    └── quality.jsonl                      QualityRecord per incident
```

Root of everything: `RCA_DATA_HOME` (env var) or `paths.data_home` in `configs/prep.yaml`,
default `RCA_ROOT/data`. All paths inside records are relative POSIX paths from `RCA_DATA_HOME`.

## 3. Record types

### 3.1 IncidentRecord (`visible/incidents.jsonl`)

| Field | Type | Notes |
|---|---|---|
| `schema_version` | str, `"1.0.0"` | SemVer of this schema |
| `incident_uid` | str, `^[a-z0-9-]+\.[0-9a-f]{16}$` | opaque id |
| `dataset_id`, `dataset_subset`, `dataset_version` | str, str or null, str | e.g. `rcaeval`, `RE2`, `zenodo-14590730` |
| `source_id` | str | acquisition registry id, e.g. `rcaeval-zenodo` |
| `lineage_group` | str | from `incidents.jsonl` of acquisition (L1…L14) |
| `system` | str | normalized system name: `online-boutique`, `sock-shop`, `train-ticket`, `aiops2025-hipstershop`, `otel-demo`, ... |
| `time.anchor_ns` | int | injection time (or alert/window start) in ns UTC |
| `time.anchor_kind` | enum `injection`, `alert`, `window_start` | what the anchor means |
| `time.anchor_original` | `{value: str, unit: "s"\|"ms"\|"us"\|"ns"\|"iso8601", tz: str}` | raw value as read |
| `time.end_ns` | int or null | only when the source gives it as model input and its value is shown to be label-independent; null for AIOps2025 and RCA100, whose given window ends are ground-truth fault ends (AIOps2025 window length identifies fault type, see adapter-contracts §3.3) |
| `time.window` | `{start_ns, end_ns, clipped_start: bool, clipped_end: bool}` | bounds of the stored telemetry slice |
| `candidates.services` | list[str], sorted, unique | candidate `service_id`s visible to the model |
| `candidates.source` | enum `telemetry`, `topology`, `telemetry+topology` | how the list was built (never from labels) |
| `telemetry.<m>` for m ∈ metrics, logs, traces | ModalityInfo | see below |
| `context.visible_text` | str or null | source-provided incident description that the benchmark itself shows the solver, minus any label-derived content (RCA100 alert title + entity; Cloud-OpsBench query). Null for AIOps2025, whose description is a template around the ground-truth window |
| `repro.adapter` | `{name, version}` | |
| `repro.build_id`, `repro.config_hash` | str | link to `_build.json` |
| `repro.input_digest` | str (sha256) | hash over the sorted sha256 list of raw members used |
| `quality_state` | enum `ACCEPT`, `ACCEPT_WITH_WARNINGS`, `QUARANTINE`, `REJECT` | details in `eval_only/quality.jsonl` |

**ModalityInfo**

| Field | Type | Notes |
|---|---|---|
| `status` | enum `present`, `natural_absent`, `empty`, `corrupted` | natural state at the source. `ablated` exists only on condition views (§3.4) |
| `path` | str or null | relative path of the Parquet file |
| `rows` | int | 0 unless `present` |
| `services` | list[str] | service_ids with ≥1 row |
| `t_min_ns`, `t_max_ns` | int or null | observed time range |
| `coverage` | float 0–1 or null | fraction of the window seconds with ≥1 row (metrics) or ≥1 event (logs, traces) |
| `metric_sets` | list[str] | metrics only: e.g. `["full", "simple"]` |
| `content_sha256` | str or null | sha256 of the canonical row serialization of the table (§4), independent of Parquet writer bytes and Arrow chunking |
| `notes` | list[str] | finding codes that affected this modality |

Status semantics:

- `present`: rows exist inside the window.
- `natural_absent`: the source never collected this modality for this incident (no file, or the
  dataset has no such modality, for example RE2-SS traces).
- `empty`: a file exists but holds zero data rows (header only), or no rows fall inside the window.
- `corrupted`: the file exists but failed parsing or validation (undecodable, impossible timestamps,
  unit mismatch that cannot be resolved by a documented rule). The raw file stays untouched; the
  quality record says why.

### 3.2 LabelRecord (`eval_only/labels.jsonl`)

| Field | Type | Notes |
|---|---|---|
| `incident_uid` | str | join key |
| `source_incident_id` | str | original id, e.g. `rcaeval:re2ob_checkoutservice_cpu_1`, `aiops2025:345fbe93-80` |
| `root_cause.original` | any JSON | label exactly as in the source (string, list or object) |
| `root_cause.entities` | list of `{raw, kind, service_id}` | kind ∈ `service`, `pod`, `container`, `node`, `namespace`, `operation`, `resource`, `unknown`; `service_id` null when unmappable |
| `root_cause.root_service_ids` | list[str] | mapped services, sorted |
| `root_cause.primary_root_service` | str or null | single service when the label names exactly one; null otherwise |
| `root_cause.label_granularity` | enum `service`, `pod`, `node`, `multi-service`, `operation`, `resource`, `config` | granularity of the source label |
| `fault.type_raw` | str | e.g. `cpu`, `f3`, `cpu_contention`, `network corrupt` |
| `fault.family` | enum `cpu`, `memory`, `disk-io`, `network-delay`, `network-loss`, `network-other`, `socket`, `code-defect`, `config`, `pod-lifecycle`, `node`, `dns`, `jvm`, `other`, `unknown` | coarse family via the explicit `FAULT_FAMILY` table in each adapter module, never inferred by regex; unmapped values → `unknown` plus a finding |
| `label_source` | enum `path`, `label-file`, `path+label-file` | |
| `injection_kind` | enum `injected`, `natural`, `unknown` | |
| `label_validity` | enum `valid`, `ambiguous`, `invalid` | with `validity_notes` |
| `eval_tier` | enum `A`, `B`, `excluded` | per incident, with `eval_tier_reason` |
| `group.fault_cell` | str | `<lineage>/<system>/<primary_root_service or entity>/<fault.family>` |
| `group.copy_of`, `group.duplicate_of` | str or null | incident_uid or external copy |
| `group.group_id` | str | connected-component id used for splitting (phase 10) |
| `label_artifacts` | list of `{kind, ref}` | e.g. RCAEval `root_cause.txt`, AIOps2025 `key_observations`, RCA100 `raw_ground_truth`, Nezha `root_cause_*.json` |
| `truth_time.end_ns` | int or null | fault end when known only from labels |

### 3.3 QualityRecord (`eval_only/quality.jsonl`)

`{incident_uid, state, findings: [{code, severity: info|warn|quarantine|reject, modality, detail,
evidence_ref}], validator_version, decided_by: "rule" | "manual:<initials>:<YYYY-MM-DD>",
override_reason}`. State = the most severe finding (`reject` > `quarantine` > `warn` > `info`)
unless a manual override with a reason is recorded. Finding codes live in
[quality-leakage-splits.md](quality-leakage-splits.md#finding-codes).

### 3.4 Condition view (produced by `ablate`, not stored in canonical)

`{variant_id = "<incident_uid>~<condition>", pair_id = incident_uid, condition, modalities:
{m: present | natural_absent | empty | corrupted | ablated}, masked_service_ref: eval-only}`.
The visible part (`modalities` with `ablated` collapsed to "not available") feeds the evidence
builder and Jev. The masked service is written only to the eval-only ablation log.

## 4. Telemetry Parquet schemas (canonical v1)

All tables carry `src_file` (int32 index into `source_index.jsonl` member list) and `src_row`
(int64 row number in that member) so any value is traceable to raw bytes.

| Modality | Columns (type) | Sort |
|---|---|---|
| metrics | `ts_ns` int64, `entity_raw` string, `entity_kind` dict<string>, `service_id` string?, `metric` string (original source name, `_` allowed), `metric_set` dict<string>, `value` float64, `unit` string? | `service_id, metric, ts_ns` |
| logs | `ts_ns` int64, `entity_raw` string, `service_id` string?, `level` string?, `message` string, `template` string?, `trace_id` string?, `span_id` string? | `ts_ns` |
| traces | `ts_ns` int64 (span start), `duration_ns` int64, `trace_id` string, `span_id` string, `parent_span_id` string? (null for roots), `entity_raw` string, `service_id` string?, `operation` string, `status_code` string? | `ts_ns` |

The legacy wide view (`legacy_view.py`) needs `<service>_<metric>` columns split on the last
`_`, so it encodes `_` in metric names as `.` (reversible: canonical names never contain `.` →
checked by the validator; if a source does, the view fails loudly). Canonical storage keeps the
original names.

`content_sha256` is computed over a canonical row serialization, not over Arrow IPC bytes:
`combine_chunks()`, sort by the modality sort key, then for each column in schema order hash
`name`, Arrow type string, the validity bitmap as bytes, and values (int64/float64 as
little-endian 8-byte, strings as UTF-8 with a 4-byte little-endian length prefix). The result
does not depend on batch boundaries, padding or IPC metadata version. The same pyarrow version
is also pinned on both machines (`requirements-lock.txt`).

Values are never rescaled except time units. `NaN`/`inf` metric values are kept and counted in
the quality findings (`METRIC_NONFINITE`).

## 5. Invariants checked by `rca.schema.validate_dataset`

1. Every record validates against the JSON Schema; unknown fields are rejected on write.
2. `incident_uid` is unique, matches the pattern, and is identical in all three record files.
3. No field of an IncidentRecord, and no column of a visible Parquet file, has a name on the
   label denylist (`root`, `root_cause`, `fault`, `label`, `gt`, `answer`, `key_observations`, ...).
   `visible/` never contains a raw source path.
4. `status == present` ⇔ file exists and `rows > 0`; `empty` ⇒ `rows == 0`; `natural_absent` ⇒
   `path == null`.
5. `window.start_ns < anchor_ns ≤ window.end_ns`, unless a `clipped_*` flag explains it.
6. Every `ts_ns` lies in [2015-01-01, 2030-01-01) UTC; violations are `TS_OUT_OF_RANGE`.
7. `candidates.services` is sorted and unique; each id satisfies `canon(id) == id` (so the legacy
   evidence code cannot re-map it); no two raw identifiers collapse to one id unless the alias is
   declared in `service_map.json`.
8. For `eval_tier == A`: `primary_root_service ∈ candidates.services` when it is set, and
   `root_service_ids ⊆ candidates.services` when it is null (set-scoring-only incidents);
   otherwise the finding is `ROOT_NOT_CANDIDATE` and the state is `QUARANTINE`.
9. `copy_of` or `duplicate_of` set ⇒ state `REJECT` with `DUPLICATE`; such incidents never enter a
   split.
10. Rebuilding with the same inputs, config and package versions produces byte-identical JSONL and
    identical `content_sha256` for every table.
11. All stored paths are relative POSIX (no drive letter, no `\`, no `..`), ≤ 180 characters.

## 6. Versioning

- Schema SemVer. MAJOR: a reader of the old version would misread data → new directory
  `canonical/v2/`. MINOR: new optional field. PATCH: documentation or validator-only change.
- Adapter SemVer is independent and recorded in `_build.json`. An adapter MAJOR bump requires a
  rebuild of that dataset; splits that reference it are re-validated (phase 10 checks
  `input_digest` lists).
- Readers accept the same schema MAJOR and ignore unknown optional fields; writers are strict.

## 7. Example records (RCAEval RE2-OB, values from the raw zip)

```json
{"candidates":{"services":["ad","cart","checkout","currency","email","frontend","payment","productcatalog","recommendation","redis","shipping"],"source":"telemetry"},
 "context":{"visible_text":null},"dataset_id":"rcaeval","dataset_subset":"RE2","dataset_version":"zenodo-14590730",
 "incident_uid":"rcaeval.<16 hex>","lineage_group":"L1","quality_state":"ACCEPT",
 "repro":{"adapter":{"name":"rcaeval","version":"1.0.0"},"build_id":"<id>","config_hash":"<sha256>","input_digest":"<sha256>"},
 "schema_version":"1.0.0","source_id":"rcaeval-zenodo","system":"online-boutique",
 "telemetry":{"logs":{"status":"present","path":"canonical/v1/rcaeval/visible/telemetry/rcaeval.<hex>/logs.parquet","rows":"<n>","services":["..."],"t_min_ns":"<n>","t_max_ns":"<n>","coverage":"<f>","metric_sets":[],"content_sha256":"<sha256>","notes":[]},
              "metrics":{"status":"present","metric_sets":["full","simple"],"...":"..."},
              "traces":{"status":"present","...":"..."}},
 "time":{"anchor_kind":"injection","anchor_ns":1705354566000000000,"anchor_original":{"value":"1705354566","unit":"s","tz":"UTC"},"end_ns":null,
         "window":{"start_ns":"<case first ts>","end_ns":"<case last ts>","clipped_start":false,"clipped_end":false}}}
```

```json
{"incident_uid":"rcaeval.<16 hex>","source_incident_id":"rcaeval:re2ob_checkoutservice_cpu_1",
 "root_cause":{"original":"checkoutservice","entities":[{"raw":"checkoutservice","kind":"service","service_id":"checkout"}],
   "root_service_ids":["checkout"],"primary_root_service":"checkout","label_granularity":"service"},
 "fault":{"type_raw":"cpu","family":"cpu"},"label_source":"path","injection_kind":"injected",
 "label_validity":"valid","validity_notes":[],"eval_tier":"A","eval_tier_reason":"RCAEval service-level injected fault",
 "group":{"fault_cell":"L1/online-boutique/checkout/cpu","copy_of":null,"duplicate_of":null,"group_id":"<assigned in phase 10>"},
 "label_artifacts":[],"truth_time":{"end_ns":null}}
```

The duplicate `RE2-OB/checkoutservice_cpu/multi-source-data` gets its own `incident_uid`, a
LabelRecord with `group.duplicate_of` = the uid above, and quality state `REJECT` (`DUPLICATE`).
Its telemetry is not converted; `source_index.jsonl` keeps the raw refs.

Placeholders `<...>` stand for values produced by the build; they are not fabricated here.

## Implementation deviations (recorded 2026-10-14)

The code is the authority for these points; `RCA_ROOT/docs/data_contract.md` describes the shipped contract.

| Design text | Shipped behaviour | Why |
|---|---|---|
| Metric rows keep `src_file`, `src_row` | Metric rows also keep `src_col` (column index in the wide CSV) | A long metric row comes from one cell; the column is needed to rebuild the CSV |
| `content_sha256` over table content | String columns are hashed as int64 little-endian lengths followed by the concatenated UTF-8 bytes | Independent of Parquet writer bytes and of Arrow buffer offsets |
| Coverage per modality | Share of 60 s buckets in the stored window that hold at least one row (integer arithmetic) | Deterministic on both machines |
| `build_id` free-form | `<dataset>-<sha256(config_hash, adapter version, schema version, input digests)[:12]>` | A rebuild from the same inputs gives the same id |
| `_build.json` counts only | Also `dataset_digest` = sha256 of the four zone files (`incidents.jsonl`, `labels.jsonl`, `quality.jsonl`, `source_index.jsonl`) | `verify-splits` and bundles detect stale builds by digest |
| The duplicate's telemetry is not converted | It is converted like any incident; the REJECT state keeps it out of every split and condition | Duplicate detection runs at assembly, after per-incident conversion |
| `group.group_id` assigned in phase 10 | `group.group_id` stays `null` in labels; the split manifest holds `group_id_hash` per assignment | Groups depend on the protocol (`cell` vs `physical`); labels stay protocol-independent |
| Service aliases | An alias entry may carry `kind` (e.g. `infra`, kept out of candidates); `configs/service_aliases.yaml` is folded into the build config hash | Foreign containers scraped in the same cluster (RCAEval OB/SS) must not merge with services |
| Evidence records (run_grid) | Canonical evidence JSONL is schema 2: no label fields, `incident_uid`, `variant_id`, `pair_id`; truth joined at scoring time | Leakage boundary between visible and eval-only zones |
