# Adapter contract and dataset-specific normalization specs

## 1. Interface (`RCA_ROOT/src/rca/adapters/base.py`)

```python
@dataclass(frozen=True)
class RawRef:            # lazy pointer to raw bytes; never an absolute path
    source_id: str       # acquisition registry id
    member: str          # "<relpath under data/raw>" or "<archive relpath>!<member path>"
    sha256: str | None   # from checksums.sha256 (archives) or computed at read time (members)

@dataclass
class Finding:
    code: str; severity: Literal["info", "warn", "quarantine", "reject"]
    modality: str | None; detail: str; evidence_ref: str | None

@dataclass
class DiscoveredIncident:
    source_incident_key: str       # stable key inside the source, e.g. "RE2-OB/checkoutservice_cpu/1"
    refs: dict[str, list[RawRef]]  # modality / "label" / "aux" -> refs
    hints: dict                    # adapter-private parse results (never written to visible/)

class Adapter(Protocol):
    name: str; version: str; dataset_id: str; source_ids: tuple[str, ...]
    def discover(self, ctx: BuildContext) -> Iterator[DiscoveredIncident]: ...           # 1
    def read_label(self, inc, ctx) -> tuple[LabelDraft, list[Finding]]: ...              # 2
    def service_map(self, ctx) -> ServiceMap: ...                                         # 3
    def anchor_and_window(self, inc, label, ctx) -> tuple[TimeInfo, list[Finding]]: ...   # 4
    def normalize(self, inc, modality, window, smap, ctx) -> Iterator[pa.RecordBatch]: ... # 5 (chunked)
    # 6 missingness, 7 provenance, 8 validation are done by the shared driver, not by adapters
```

The shared driver (`src/rca/prep.py: build_dataset`) owns everything common:

1. Iterates `discover()`; computes `incident_uid`.
2. Calls `read_label`, `service_map`, `anchor_and_window`.
3. Streams `normalize()` batches into a temporary Parquet writer, applies the window filter,
   computes rows, services, coverage and `content_sha256`, and decides the ModalityInfo status
   (`present` / `empty` / `natural_absent` / `corrupted`) from what the adapter yielded and raised.
4. Runs per-incident validators (`src/rca/quality.py`) and atomically writes one per-incident
   record file `work/runs/<dataset>/records/<incident_uid>.json` holding the incident, label,
   source-index and quality parts plus all ModalityInfo stats, followed by a `.done` marker next
   to it (keyed by `input_digest` + `config_hash`). REJECTed incidents get a record file too, so
   every incident has a marker location even without telemetry.
5. Resumes: an incident with a valid `.done` marker is skipped; its record file already holds
   everything. A changed digest or config rebuilds that incident.
6. Finalizes: concatenates all record files in `incident_uid` order into the three JSONL files
   (temp + `os.replace`) and writes `_build.json` last. Finalization never recomputes telemetry
   stats. A dataset without `_build.json` is incomplete by definition.

Adapters must not: write files, read `eval_only/` of another dataset, rename or relabel services
outside `service_map`, drop rows silently (every drop is counted in a finding), or execute code
from the raw data.

### Error handling

- Parse errors on one member → that modality is `corrupted` with finding `PARSE_ERROR` (member,
  first error, row count read); the incident continues.
- Label unreadable → `LABEL_UNPARSEABLE`, state `REJECT`; telemetry is not converted.
- Unexpected adapter exception → the driver records `ADAPTER_EXCEPTION` with the traceback digest
  in the run ledger, marks the incident `QUARANTINE`, and continues; the CLI exits with code 3 when
  any incident is quarantined by an exception, so it is never silent.

## 2. Service identity mapping

`ServiceMap` is per system and explicit:
`{system: {raw_identifier: {service_id, rule, kind}}}`, written to `visible/service_map.json`.

Rules, applied in this order and recorded per entry:

1. `alias` — a declared entry in `configs/service_aliases.yaml` (hand-maintained, reviewed). Used
   only to resolve a reported collision or a known rename.
2. `pod-to-deployment` — strip the Kubernetes suffixes: `^(?P<d>.+)-[a-z0-9]{8,10}-[a-z0-9]{5}$`
   (Deployment pods) or `^(?P<d>.+)-\d+$` (StatefulSet pods), only when the stripped name is a
   known service of that system.
3. `canon` — the legacy `rca.data.canon` applied to the raw name.

Checks: each `service_id` must satisfy `canon(id) == id`; two raw identifiers of different kinds
mapping to one id are reported as `SERVICE_ID_COLLISION` (QUARANTINE for affected incidents) unless
an alias declares them equal. `main` (RE1-OB `main_cpu`) and similar non-service columns are mapped
to `kind=infra` and excluded from candidates, with a finding.

## 3. Dataset-specific specs

### 3.1 RCAEval (reference adapter, `adapters/rcaeval.py`, source `rcaeval-zenodo`)

| Step | Rule |
|---|---|
| Discover | Read each `RE*.zip` central directory; a case = directory containing `inject_time.txt`. Read members directly from the zip (`zipfile.ZipFile.open`), no extraction. `__MACOSX`, `.DS_Store`, `metrics.png`, nested `*.zip` are recorded in `source_index` as `aux` and not opened |
| Key / label | `RE<n>-<SYS>/<cell>/<instance>`; `cell` parsed by `^(?P<svc>.+?)_(?P<fault>cpu|mem|disk|delay|loss|socket|f[1-5])(?:_(?P<batch>\d+))?$`. `f3_1` → fault `f3`, `batch=1` (kept in `source_incident_id`). Zenodo has both `ts-route-service_f3/{1,2,3}` and `ts-route-service_f3_1/{1,2,3}`, so the batch is part of the source key and of the legacy `case_id` (`…_f3b1_1`); keys are asserted unique. A cell that does not match → `LABEL_UNPARSEABLE` |
| Duplicates | `multi-source-data` (non-numeric instance): compare `inject_time.txt` bytes with siblings; equal → `duplicate_of`; different → `QUARANTINE` (`UNEXPLAINED_EXTRA_CASE`) |
| Label artefacts | `root_cause.txt` → `label_artifacts` (eval-only); never parsed as logs |
| Anchor | `inject_time.txt` integer seconds → ns |
| Window | Whole case file (RCAEval cases are pre-cut); `window` = [min ts, max ts] across modalities; a finding if the anchor is not inside |
| Metrics | RE2/RE3: `metrics.csv` → `metric_set=full`; `simple_metrics.csv` → `simple`. RE1: `data.csv` → `full`, `simple_data.csv` → `simple`. Column `<svc>_<metric>` split on the first `_` after a known service prefix (longest-match against the service list from `simple_*` and `pod-node-*.csv`), not on the last `_`. `time` s → ns. Melt to long |
| Logs | `timestamp` (ns) is the time; `time` (`HH:MM`) is ignored but checked for consistency on a sample; `container_name` → entity; `level` when present; `log_template` → `template` |
| Traces | `startTime` µs → ns; cross-check `startTimeMillis == startTime // 1000` on every row (finding `TRACE_TIME_MISMATCH` with count); `duration` µs → ns; `parentSpanID` empty → null; `statusCode` kept as string |
| Missingness | No `traces.csv` → `natural_absent`; header-only → `empty`; RE2-SS → `natural_absent` |
| Cross-check | HF copy is never ingested. A parity test compares canonical tables of 20 sampled cases with the HF Parquet and expects exactly the 6 known difference classes |

### 3.2 Nezha (`adapters/nezha.py`, source `nezha`)

| Step | Rule |
|---|---|
| Discover | `rca_data/<date>/<date>-fault_list.json`; one incident per list entry; key `<date>/<hour>/<index>` |
| Label | `inject_pod` → entity kind `pod`, mapped to service by `pod-to-deployment`; `inject_type` → `type_raw`; `root_cause_{hipster,ts}.json` → `label_artifacts` |
| System | Dates `2022-08-*` → OB, `2023-01-*` → TT (verified per date by the pod names in the fault list; a mismatch is a finding) |
| Anchor | `inject_time` string parsed as UTC (measured in phase 02: it matches the hour keys, the minute file names and the metric `Time` strings on every date). `inject_timestamp` is kept as `anchor_original` evidence only: it differs on 29 of 101 incidents (24 on 2023-01-29 by about −8 h, 5 by ±60 s); a difference is finding `ANCHOR_FIELD_DISAGREE` (info) |
| Window | [anchor − `pre_s`, anchor + `post_s`] from config (default 1,200 s / 600 s, wider than evidence's 600/300 so evidence windows can change without a rebuild); clipped at the day stream boundary |
| Metrics | Per-pod CSV, one row per minute. Time from the `Time` string (UTC). `TimeStamp` is accepted only when within 60 s of `Time`; otherwise finding `TS_COLUMN_OFFSET` (count, offset value). Each numeric column becomes a metric (`CpuUsageRate(%)` → `cpu-usage-rate-pct`, with an explicit name table) |
| Logs | Minute files overlapping the window; `TimeUnixNano`; `PodName` → entity; message from the nested `Log` JSON (`message` field when parseable, the raw string otherwise; `PARSE_ERROR` count); severity → `level` |
| Traces | Minute files; `StartTimeUnixNano`; `Duration` checked against `EndTimeUnixNano − StartTimeUnixNano` to fix the unit (µs observed); `ParentID == "root"` → null |
| Overlap | Every other incident whose anchor falls in this window is listed in a `BASELINE_CONTAMINATED` finding (warn) with its uid |

### 3.3 AIOps2025 (`adapters/aiops2025.py`, source `agenticopseval`)

| Step | Rule |
|---|---|
| Extraction | Needed (tar.gz has no random access). `rca.prep extract` writes `data/work/extract/agenticopseval/AIOps2025/<day>/` with the safe-extraction rules; `._*` members skipped and counted |
| Discover | `groundtruth.jsonl` joined with `input.json` on `uuid`; key = `uuid` |
| Label | `instance_type` service → entity `service`; pod → `pod` (→ service by `pod-to-deployment`, StatefulSet form `paymentservice-1`); node → `node`, `primary_root_service=null`, `eval_tier=B`. A list-valued `instance` that maps to one service (e.g. `["paymentservice-1"]`) is treated as a single entity. A list mapping to more than one service (network faults with `source`/`destination`) → several entities, `label_granularity=multi-service`; when the `service` field names exactly one service, `primary_root_service` = that service and `eval_tier=A`; otherwise `primary_root_service=null`, `eval_tier=A` with `eval_tier_reason="set-scoring-only"` (excluded from top-1 service accuracy and from `blind_*` conditions, kept for set-based scoring); `key_observations`, `key_metrics`, `fault_description` → `label_artifacts` |
| Anchor | `start_time` (ISO UTC) → ns. `end_time` → label `truth_time.end_ns` only; visible `time.end_ns = null`. The window is `start_time − pre_s … start_time + post_s` from config, never `end_time`. `context.visible_text = null`: every `input.json` description is one of 5 templates filled with exactly the ground-truth `start_time` and `end_time` (400/400), and the window length identifies the fault type: `io fault` is always 5 min (28/28), `pod kill` always 0 min (15/15); MI(window minutes; fault_type) = 1.04 bits, permutation p < 0.001. The template choice itself is label-independent (MI with fault_type 0.10 bits, p = 0.95) and no label token occurs in the text (measured 2026-10-14) |
| Label-derived fields | `key_observations`, `key_metrics`, `fault_description`, `patterns`, `path`, `volumePath`, `image`, `end_time` exist only in `eval_only/labels.jsonl`. Metric sets and metric names are fixed per dataset from the archive layout and never selected, ordered or filtered by `key_metrics`. Candidates come from telemetry only. Tested by label-perturbation invariance (visible outputs byte-identical when every label field except `start_time` changes) |
| Archive mapping | Measured in phase 02: hourly member names are UTC+8 (410 log, 390 trace members agree); the adapter maps by in-member UTC timestamps and reads every archive that overlaps the window (an incident near midnight can span two) |
| Telemetry | Hourly log/trace Parquet and metric Parquet filtered to the window with pyarrow predicate pushdown on the time column; column names fixed in phase 02 profile |
| Missingness | Per modality: no overlapping hourly member → `natural_absent`; member present but 0 rows in the window → `empty`; `NO_TELEMETRY` (REJECT) only when every modality is absent. Daily metric files cover all 400 windows, so the build has 0 rejects (as built 2026-10-14): logs `natural_absent` 16, traces `natural_absent` 34 / `empty` 5. Phase 02 counted 42 windows without both log and trace members under its narrower window; 38 coincide with the build's 39, 4 reach a neighbouring hour in the wider stored window. Natural absence is not associated with fault type (p 0.71 logs, 0.80 traces). Deviation from the phase-02 "REJECT" note: these incidents stay ACCEPT and the `no_log`/`no_trace`/`blind_*` conditions are marked not applicable for them |
| Identity rules (no alias entries; owner to confirm) | Jaeger process `redis` → `rediscart` (`peer-service-tag`: sampled spans carry `peer.service=redis-cart:6379`); TiDB metric rows by status port (10080 → `tidbtidb`, 20180 → `tidbtikv`; `block_cache_size` rows under `object_type: tidb` carry port 20180); `tidb-pd-0` → `tidbpd`; the " (deleted)" APM pod suffix is stripped; `example-ant-*` pods stay unmapped. Label entities are resolved with `ServiceMap.resolve`, which never records into the visible `service_map.json` |
| Leakage (measured) | Campaign day vs fault type MI 0.91 bits (p 0.0005), so splits must group by day; anchor minute 0.17 bits, duration quintile 0.35 bits (duration is eval-only); `dataset_subset` constant |

### 3.4 RCA100 (`adapters/rca100.py`, gated)

Case directories are already windowed Parquet. Label from `answer_key/tNNN.gt.json`
(`root_cause_entities`, `raw_ground_truth.fault_type`) via `answer_key/mapping.json`. Entities
resolve to services through `topology.json`. `events` and `alerts` Parquet are kept as raw refs
only in v1 (the schema has three modalities; adding a fourth is a schema MINOR change deferred to
the LLM plan if needed).

Leakage rules (measured 2026-10-14 over all 103 cases):
- `task.alert_window` equals the answer key's `time_range` in 103/103 cases. Its length varies
  continuously (169–860 s, no fixed per-fault length as in AIOps2025), but with n = 103 over ~35
  fault ids a weaker association cannot be excluded. The visible record therefore gets the
  alert time as anchor (`anchor_kind="alert"`) and `time.end_ns = null`; the end goes to
  `truth_time.end_ns`. Because case Parquet is pre-cut, phase 07 also measures whether the
  telemetry extent tracks `time_range_end`; if it does, that is recorded as a threat to
  validity (the extent cannot be hidden without discarding data).
- `context.visible_text` = the alert title and alert entity name from `task.json` only. The
  `prompt_text` XML is not copied: it carries `trans_id`, which is the suffix of the answer-key
  `case_id` (`F014-httpError5xx.<trans_id>`), a direct join key to the label.
- Alerts keep title, entity, severity and time; rule definitions (`data`/`annotations` PromQL)
  are dropped. In 10 cases, all with root `inventory`, the rule text contains
  `/sandbox/chaosblade/module/http/*`; the alert firing on the root is a real observation, the
  rule text is configuration.
- `chaosblade-operator` (namespace `chaosblade`) appears identically in all 103 topologies; it is
  infrastructure, never a candidate.
- Root prior: `inventory` is the raw root in 55/103 cases and the service of one more pod root,
  so it is the primary root of 56/86 tier-A cases. This is class imbalance, not leakage; labels
  are kept as given and RCA100 results must be reported against the majority-class baseline
  (0.651 top-1) and the alert-entity baseline (0.372 top-1).

As built (2026-10-14, `rca100-5cd15b7a1d8f`):
- Anchor = first `OCCURRED` alert; window [t − 900 s, t + 120 s]; `time.end_ns = null`.
- Metrics: a label-free rarity cut keeps (entity set, metric) pairs exported in at least half the
  cases (63 pairs in 102–103 cases). It drops `apm.metric.exception` (exported only in the 4
  nullPointerException cases) and `k8s.pod/pod_restart_count` (only in 2 pod-restart cases);
  finding `METRIC_GROUP_DROPPED` in those 6. Metrics are bucketed at 30 s for the legacy view.
- Logs and traces are exported in ~300 s pages with a per-page row cap, so a page holds a median
  of ~20 s; covered time in [alert, alert + 120 s] has median 0 s (< 30 s in 82/103 cases for logs,
  74/103 for traces) and is weakly associated with the fault id (logs p 0.03, traces p 0.01).
  Evidence uses segment mode (gap 60 s) and states "less than 30 s after incident start; no
  comparison possible" instead of a comparison (84 log, 74 trace notes); the emitted note shows
  no detectable association with fault id (p 0.41, 0.46) or root (p 0.26, 0.34). The policy for
  this note is an open owner decision.
- Non-demo deployments map to no service (rule `not-a-demo-service`).
- Shared injections: tasks with a byte-identical events or logs export or the same first-alert
  second are one injection (28 tasks, 11 groups, each one fault id and root); they get
  `group.group_id = rca100-injection:<smallest task id>`, which the audit and the split grouping use.

### 3.5 Auxiliary (B) adapters

| Dataset | Spec |
|---|---|
| PetShop | `dataset/<scenario>/<split>/issue_N/{metrics.csv,target.json}`; anchor `target.timestamp` (s); label `root_cause.node` (kind `resource`); metrics only; logs/traces `natural_absent`; the dataset's own `train/test` folder is kept as `source_split` in labels and never mixed with ours |
| DejaVu | Processed `A1,A2,B,C,D` only (raw split archive not used in v1); `faults.csv` rows → incidents; `root_cause_node` kind `node`; metrics from `metrics.csv` windowed by config; `.ipynb_checkpoints/*` ignored with a finding |
| Cloud-OpsBench | `index.jsonl` rows → incidents; `fault_object` `app/<x>` → service, `node/*`, `namespace/*` → B granularity; logs from `raw_data/logs.json`; metrics from `metrics.csv` when present; traces `natural_absent`; `k8s_states.json`, `alert.json`, `tool_cache.json` kept as raw refs; `query` → visible context; `golden-trajectory` and `process-label` → eval-only artefacts; anchor = `collection_timestamp` (kind `window_start`; therefore no evidence conditions, auxiliary training use only) |

### 3.6 Conditional sources

OpenRCA, RCABench, AnoMod and MSDS get an adapter only after their phase-02 gate passes and (for
OpenRCA) after acquisition completes. Phase 08 records each gate decision in
`data/reports/compatibility-matrix.json`. A passing source is added later as one adapter file plus
fixtures; the contract does not change.
