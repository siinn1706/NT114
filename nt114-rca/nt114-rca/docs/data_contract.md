# Data contract: canonical incidents, splits and the transfer bundle

This is the contract between data preparation (`python -m rca.prep`) and everything that consumes
it: `run_grid`, evidence, retrieval, the LLM layer and the offline evaluation. The JSON Schema
[`schemas/canonical_incident.v1.schema.json`](../schemas/canonical_incident.v1.schema.json) is the
authority for record fields. This page explains the zones, the files, the rules and how to use
them. It does not copy the field list.

## 1. Pipeline

```text
raw (immutable) -> adapter -> canonical/v1/<dataset>/{visible, eval_only} -> validate -> audit
                -> conditions (condition matrix) -> split (manifests) -> run_grid (evidence, LLM)
                -> export (bundle) -> verify-bundle on the GPU machine
```

Model-facing code receives only `VisibleCase` objects. Labels travel separately as `Truth` and
are read only by scoring, the ablation driver, the split builder and the `no_precedent` oracle.

## 2. Zones and layout of the data home

The data home is `--data-home`, else `$RCA_DATA_HOME`, else `paths.data_home` in
[`configs/prep.yaml`](../configs/prep.yaml), else `<repo>/data`. Every path stored in a record is
relative to it and uses `/`.

| Path | Zone | Contents | Written by |
|---|---|---|---|
| `raw/<source>/` | immutable input | verified downloads | acquisition tooling only |
| `work/` | scratch | per-incident build records, `.done` markers, ledgers, extractions | `normalize`, `extract` |
| `canonical/v1/<dataset>/visible/` | model-visible | `incidents.jsonl`, `service_map.json`, `telemetry/<uid>/{metrics,logs,traces}.parquet` | `normalize`, `validate` |
| `canonical/v1/<dataset>/eval_only/` | evaluation-only | `labels.jsonl`, `quality.jsonl`, `source_index.jsonl`, `exceptions.jsonl` | `normalize`, `validate` |
| `canonical/v1/<dataset>/_build.json` | receipt | build id, adapter, config hash, counts, `dataset_digest` | `normalize`, `validate` |
| `reports/` | reports | `quality-<dataset>.json`, `condition-matrix-<dataset>.json`, `audit-<build>.json`, `profile/` | `validate`, `conditions`, `audit`, `profile` |
| `splits/<protocol>[-<fold>]-<seed>-<hash8>/` | split manifests | `split.json`, `assignments.jsonl` | `split` (write-once) |
| `export/<name>-<YYYYMMDD>-<hash8>/` | transfer unit | `bundle.json`, `MANIFEST.sha256`, `parts/` | `export` (write-once) |

The visible zone never contains a label, a label artefact, a raw source path or a
`source_incident_id`. `incident_uid` is `<dataset>.<16 hex>` of a hash, so it carries no label.

### Telemetry tables

One Parquet file per incident and modality, zstd level 3, time as `int64` nanoseconds UTC. The
exact Arrow schemas are in [`src/rca/store.py`](../src/rca/store.py) (`SCHEMAS`). Every row keeps
its provenance: `src_file` (index into the incident's `source_index` members), `src_row`, and for
metrics `src_col`, so a wide CSV can be rebuilt column by column. Metrics are stored long
(`entity_raw`, `service_id`, `metric`, `metric_set`, `value`); `legacy_view.legacy_telemetry`
rebuilds the wide frames the evidence builder expects.

`content_sha256` in each `ModalityInfo` hashes the sorted table content, independent of Parquet
writer bytes. String columns are hashed as int64 little-endian lengths followed by the
concatenated UTF-8 data.

### Modality status

| Status | Meaning |
|---|---|
| `present` | rows exist in the stored window |
| `natural_absent` | the source never collected this modality for the incident |
| `empty` | the file exists but has no rows (for example a header-only `traces.csv`) |
| `corrupted` | the member could not be parsed (`PARSE_ERROR`, QUARANTINE) |

`ablated` is not a stored status. Missingness caused by an experiment exists only in the
evaluation-only ablation log, and the evidence text for natural and ablated absence is identical.

## 3. Building and checking

```bash
export PYTHONPATH=src
python -m rca.prep status
python -m rca.prep normalize --dataset rcaeval      # resumable; --force rebuilds; --workers N
python -m rca.prep validate  --dataset rcaeval      # exit 3 when QUARANTINE items need a decision
python -m rca.prep audit [--evidence-stats]
python -m rca.prep conditions --dataset rcaeval
python -m rca.prep eval-units --dataset rcaeval     # independent units, weights, exclusions, coverage strata
python -m rca.prep split --protocol within-rcaeval-grouped --seed 0
python -m rca.prep verify-splits
python -m rca.prep export --bundle nt114-data-v1
python -m rca.prep verify-bundle <bundle_dir> [--deep]
```

Exit codes: 0 ok, 2 usage, 3 finished with items that need attention, 4 integrity failure,
5 precondition missing.

`build_id` is a hash of the config hash, adapter version, schema version and input digests, so a
rebuild with the same inputs gives the same id. A rebuild without `--force` skips every incident
whose `.done` marker matches (input digest, config hash, adapter version). The config hash
ignores `paths.data_home`, so moving the data home does not invalidate a build.

## 4. Quality states

| State | Meaning | Enters splits |
|---|---|---|
| `ACCEPT` | no finding above `info` | yes |
| `ACCEPT_WITH_WARNINGS` | at least one `warn` | yes |
| `QUARANTINE` | needs a human decision | no, unless overridden |
| `REJECT` | unusable (duplicate, no telemetry, invalid label) | never |

Finding codes and severities are defined in [`src/rca/quality.py`](../src/rca/quality.py)
(`FINDING_CODES`). The only manual path is
[`configs/quality_overrides.yaml`](../configs/quality_overrides.yaml): each entry needs the
incident uid, new state, reason, initials and date. The rule findings stay in `quality.jsonl`,
and the record shows `decided_by: manual:<initials>:<date>`.

## 5. Missing-observability conditions

| Condition | Operation | Applicable when |
|---|---|---|
| `full` | none | at least one modality present |
| `no_metric` / `no_log` / `no_trace` | drop the modality | it is present and another modality remains |
| `blind_root` | remove spans of the root service (`ablate.mask_service_traces`) | traces present and the root has spans |
| `blind_nonroot` | remove spans of one non-root service (control) | as above, and another service has spans |
| `metrics_only` | drop logs and traces (metrics-only baseline) | metrics present and logs or traces present (otherwise it equals `full`) |

Conditions of one incident are variants of one sample, not independent samples: compare them
paired on identical incidents (`pair_id` = `incident_uid` in `ablation_log.jsonl`).

All conditions also need `anchor_kind` ∈ {`injection`, `alert`}, no `PRE_WINDOW_SHORT` finding
and an `ACCEPT`/`ACCEPT_WITH_WARNINGS` state. `reports/condition-matrix-<dataset>.json` records,
for every incident and condition, `applicable` and a reason, plus the `blind_nonroot` target. The
target is the non-root service whose span count is closest to the root's, with ties broken by
`sha256(uid + service)`, so it is identical on every machine. In the canonical path `run_grid`
reads conditions only from this matrix.

**Threat to validity (anchor visibility).** The anchor time comes from label files
(`inject_time.txt`, AIOps2025 `start_time`). It is used only to place the evidence window, as
standard RCA benchmarks do with alert time. It never appears as text in evidence or prompts.
RCA100 uses its first firing alert instead (`anchor_kind: alert`), which is a real observation.

**Evidence windows.** Metrics, logs and traces compare 5 min after with 10 min before the anchor.
A dataset listed in `configs/prep.yaml` `evidence.log_trace_segment_gap_s` (Nezha 30 s, AIOps2025
and RCA100 60 s) instead compares logs and traces inside the contiguous stretch of rows holding the
anchor (gaps up to that value), with rates over the seconds covered. Under 30 s of pre-anchor data
is stated as "no pre-incident baseline". Under 30 s of post-anchor data (`evidence.MIN_AFTER_S`, an
export that stops at the anchor) gives no after-vs-before line at all, only "recorded log/trace
data covers less than 30 s after incident start; no comparison possible". Metrics merged across
entities are averaged on 60 s buckets, 30 s for RCA100 (`legacy_view.METRIC_ALIGN_S`, its native
resolution). The `evidence` section does not enter the build hash.

**Evidence caching.** Evidence and results are keyed by a fingerprint: `evidence.BUILDER_VERSION`,
the window constants, the per-dataset `evidence` options, `legacy_view.VIEW_VERSION` and metric
bucket, the dataset's `dataset_digest` and the incident's condition-matrix row. `run_grid prepare`
rebuilds any evidence file whose fingerprint differs; `run` and `load_evidence` refuse a stale file
("run `prepare` again"), and result keys carry the evidence and retrieval-store fingerprints. Bump
`BUILDER_VERSION` or `VIEW_VERSION` whenever their output can change for the same input.

## 6. Splits

Grouping is union-find. `physical` joins incidents whose evidence windows
(`windows.evidence`, default [t−600 s, t+300 s]) overlap within one stream
(`dataset/lineage/subset/system`), incidents linked by `duplicate_of`/`copy_of`, incidents with
an equal non-null `group.group_id` (records cut from one source incident, e.g. RCA100 tasks of one
injection), incidents with equal telemetry `content_sha256`, and, for datasets in
`splits.GROUP_BY_DAY` (AIOps2025, whose campaign day predicts the fault type), incidents of the same
source day. `cell` adds equal `fault_cell` (`lineage/system/root service/fault family`).

| Protocol | Grouping | Assignment |
|---|---|---|
| `within-<dataset>-grouped` | cell | whole groups, greedy stratified fill to 60/20/20 of incidents by system × fault family; a stratum with fewer than 3 groups goes to test |
| `within-<dataset>-retrieval` | physical | same fill; same-cell repeats may be precedents in train |
| `loso-<dataset>` | cell | one manifest per system (`params.fold`): that system is test, the others train |
| `eval-only-<dataset>` | cell | every accepted A-tier incident in test |
| `xdata-<train>-to-<test>` | cell, over both datasets | A-tier incidents of `<test>` in test; incidents of `<train>` in train unless they share a group with a test incident (`counts.train_dropped_shared_group`) |

`assignments.jsonl` holds `{incident_uid, split, group_id_hash}` sorted by uid and nothing else.
The directory name ends with the first 8 hex of its sha256; `split` refuses to overwrite, so the
same inputs give the same directory. A rebuilt dataset with unchanged assignments re-pins the
manifest and moves the old one to `splits/_superseded/`. `verify-splits` reports `HASH_MISMATCH`,
`GROUP_SPANS_SPLITS` and `STALE` (a pinned build's `dataset_digest` changed). Only `ACCEPT` and
`ACCEPT_WITH_WARNINGS` incidents enter. B-tier incidents may only train, and only when their group
is not in validation or test (otherwise they are left out, `counts.tier_b_dropped_held_out_group`).
`split.json` sets `headline_ok: false` when the test share is below 10%, or when a within split has
fewer than 3 groups. `within-aiops2025-grouped` is such a case: day and fault-cell grouping join all
400 incidents into one group, so no fault-cell-held-out split of AIOps2025 exists; use
`within-aiops2025-retrieval` (day groups) or the cross-dataset protocols.

### Evaluation units and primary exclusions

`reports/eval-units-<dataset>.json` (evaluation-only, never a model input) gives every accepted
record its independent statistical unit:

- `injection_id`: records cut from one fault injection share it (`group.group_id`, else
  `duplicate_of`/`copy_of`, else the uid). Statistics resample injections (cluster bootstrap) and
  weight each record by `weight` = 1 / records of its injection, so every injection counts once.
  `representative` marks the smallest uid of each injection for the one-record-per-injection
  sensitivity analysis.
- `excluded_from_primary`: the reason from
  [`configs/eval_exclusions.yaml`](../configs/eval_exclusions.yaml), or null. Excluded records
  stay in the store, the splits and secondary analyses; that file is not part of the build hash.
  An entry with `status: lifted` stays as the record of the decision and excludes nothing.
- `coverage.logs` / `coverage.traces`: seconds of recorded data after the anchor in the stretch
  the evidence builder uses, and the cause: `covered` (≥ 30 s, so an absent error is a real
  absence), `export_truncated` (the stored export ends sooner), `export_gap` (data resumes after a
  gap), or the natural status (`natural_absent`, `empty`). Report results by these strata.

## 7. Leakage rules

1. Zone separation by type: `evidence.build`, `evidence.shuffled_candidates`,
   `llm.build_messages` and `CaseStore.search` receive `VisibleCase` objects,
   which have no `root_service` or `fault` attribute. `tests/test_leakage.py` asserts this at
   every entry point and scans those modules' source for label access.
2. Label artefacts (`root_cause.txt` and similar) are referenced only from
   `LabelRecord.label_artifacts` and never ingested.
3. Retrieval (owner decision R1). The store holds train-role incidents of a
   `within-*-retrieval` split.
   - `precedent` (headline, label-free) excludes the query's own split group. It is the only mode
     whose hits and similarity may reach a headline prompt or the selective evaluation.
   - `no_precedent` is an oracle ablation. The caller adds incidents with the query's
     (root, fault) from `Truth` through `CaseStore.search(..., exclude_ids=...)`; `retrieve.py`
     never reads query labels. Its result rows carry `oracle_store: true`.
   - The store is bound to the configured split: exactly its train-role incidents (after
     `store_limit`) are loaded from `<evidence_dir>/store/`; files left there by another split or
     limit are ignored and counted, a missing one stops the run, and retrieval without a split is
     refused. Prompt v1 names one service root per precedent, so train incidents labelled only by a
     root set or a node are excluded and counted by granularity. The manifest's `store` block records
     the split, the counts and a binding hash, which is part of every retrieval row's resume key.
4. The masking operator takes a service name; only the condition driver passes the root or the
   control target. The masked service is logged in `ablation_log.jsonl` next to the results,
   never in the evidence directory.
5. Checks: canary label, label-permutation invariance (evidence, prompts for every retrieval
   method in `precedent` mode), denylisted keys and Parquet columns
   (`schema.LABEL_DENYLIST`), raw-path fragments and free-text label artefacts in the visible zone
   (`rca.audit.leakage_scan`).
6. Text-level near-duplicates (eval-only): `python -m rca.leakage_audit <cfg>` compares each query
   incident's evidence with the same-system `precedent` store entries (the query's split group
   excluded): maximum TF-IDF cosine, maximum line-set Jaccard, and whether the nearest entry shares
   the query's (root, fault). It writes flags and similarities only, next to the results; an output
   directory inside the evidence directory is refused. Tests: `tests/test_leakage.py` (store entries
   are train-role and outside the query's group; `no_precedent` rows are refused by `selective` and
   the headline guard), `tests/test_leakage_audit.py`.
7. Evaluation zone: `visibility`, `leakage_audit`, `alignment`, `baselines`, `baro` and the
   analysis modules (`analyze`, `confidence`, `contrasts`, `selective`) may read labels. No
   model-facing module (`llm`, `evidence`, `retrieve`, `run_grid`) imports them; `tests/test_confidence.py`
   checks the imports.
8. **Train-role structure for the IM1 frame** (owner decisions D9 and D11 of 2026-10-26; amendment a02 of 2026-10-26, sha256 in `plans/261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md`). This is a new use of train-role information, separate from rule 3 (retrieval).
   - **Arms.** Result rows carry `arm` ∈ {`l0`, `ra`, `ra_im1`, `ra_im1_shuf`}. Only `ra_im1` (`train_structure = im1_frame`) and `ra_im1_shuf` (`im1_frame_shuffled`) read a frame. `ra` is also IM1's same-pipeline frame-free control. `retrieval = none` keeps its meaning: no precedent store and no retrieved text. Rows without an `arm` field are read as `l0` when `retrieval = none` and stay the existing retrieval arm when `retrieval = hybrid`. Rows of different arms are never pooled, thresholds are never fitted across arms, and every table names the arm. Framed rows also carry `frame_sha256`.
   - **Source.** Incidents that the run's split assigns to `train` (`assignments.jsonl`), read through the visible zone. No val or test incident, and no incident outside the split, is opened to build, check or tune a frame.
   - **Window.** Per train incident, trace rows with `anchor_ns − 600 s ≤ ts_ns < anchor_ns` (the evidence "before" window, `evidence.NORMAL_S`). No row at or after the anchor is read. The anchor is used only to place this window, as in §5 (anchor visibility).
   - **Fields.** `trace_id`, `span_id`, `parent_span_id` and `service_id`; `ts_ns` only for the window filter. `trace_id` is read only to resolve a `parent_span_id` within its trace. `duration_ns`, `status_code`, `operation`, `entity_raw`, logs and metrics are not read.
   - **Edges.** A directed edge `parent service → child service` for each span whose `parent_span_id` resolves to a span of the same `trace_id`, when both `service_id`s are non-null and differ. The frame stores the node set, the edge set and, per edge, the number of contributing train incidents, nothing else.
   - **Key.** One frame per `(dataset, dataset_subset, system, split)`. A frame is never transferred to another subset of the same system (for example RE2-TT to RE3-TT) in the current MVP, because a shared topology or deployment has not been established. The key is fixed here and is never chosen by comparing keys on results.
   - **Validity.** A frame is valid when at least 3 train incidents of its key contributed at least one edge. Otherwise the key has no frame. The threshold is fixed and is not lowered after seeing coverage or results.
   - **Freezing.** Each frame is written once as JSON with its sha256 before any val or test evidence of a framed arm is built. The run manifest records the frame hashes; a run refuses a frame whose hash differs from the manifest, and rebuilding a frame after val or test evidence exists must give the same hash or the run stops.
   - **Edge-shuffled control.** For each valid frame, one shuffled frame with the same node set and the same number of edges, no self-loops, drawn uniformly without replacement first from ordered pairs that are not real edges (filled from real edges only when too few remain), with the single seed derived from the real frame's sha256. No other seed is tried. Its share of retained real edges is recorded; above 0.5 the control is reported as not informative for that key. The control keeps node set and edge count only; it does not control other topology properties (degree sequence, direction pattern, reachability).
   - **Use.** A frame enters only the `no_trace` path of framed arms. Evidence and prompts may show service names and frame edges, never train incident ids, times or any other field above.
   - **Fallback.** A key without a valid frame uses the `frame_free` path declared before evaluation. Those cases stay in the denominator and are reported as `frame_free`.
   - **Reporting.** The declared pool (for H1, `single_modality` with all its records) is the population of every arm's primary result, including records on the `frame_free` path. Results on the subgroup with a valid frame are exploratory and are reported separately; they never replace the full-pool result, and IM1 is never described as covering all of H1. The frame coverage reported is the coverage measured after building the frames, not a projection.
   - **Forbidden.** Labels (`eval_only/`, `LabelRecord`, `Truth`), root services, fault types and families, any key or column in `schema.LABEL_DENYLIST`, val or test telemetry, and any model output, for building, checking, keying or tuning a frame.
   - **Checks** (`tests/test_im1_frame.py`, `tests/test_im1_leakage.py`): permuting train labels leaves the frame hash unchanged; a canary label value never appears in a frame; rows at or after the anchor are excluded; a val or test incident passed to the builder raises; building val/test evidence leaves the frame hash unchanged; the builder imports no label-reading module (rule 7); the shuffled frame keeps the node and edge counts and records its retained share; a key without a valid frame yields `frame_free` and the record stays counted.

## 8. Selective evaluation (eval-only)

The system is a single LLM: every answer comes from one model's call on one cell, and abstention is
a fixed rule on that call's own outputs. `selective.action_table()` joins the cached cells of one
primary model (without retrieval, and with `hybrid` retrieval from the `precedent` store) into an
evaluation table. It holds correctness, so it is evaluation-only and nothing in it reaches a prompt.
It refuses a grid that contains `oracle_store` (`no_precedent`) rows. `run_grid` accepts the model
roles `primary` and `replication` only; several models in one config are independent runs. Tests:
`tests/test_selective.py`, `tests/test_leakage.py`.

### Run records next to the grid

- `prepare_log.jsonl` (appended by `prepare`): per (incident, condition) the telemetry read and build
  seconds, telemetry rows per modality, evidence characters, `truncated` and the evidence
  fingerprint; `kind: store` rows are the retrieval store. It is outside the evidence directory, so
  fingerprints and cache keys do not depend on it. Wall times measure the machine in the manifest.
- Grid rows carry `retrieval_s` (0.0 without retrieval).
- `manifest.json` (`manifest_version: 3`): git commit, bundle, split and its `split.json` sha256,
  Python, platform, package versions, `evidence.BUILDER_VERSION`, `legacy_view.VIEW_VERSION`,
  the sha256 of the resolved config and its copy `config.yaml`, the `prepare_log.jsonl` sha256,
  models with their execution settings and `exec_sig`, sampling, and the retrieval `store` block.
  The manifest and the config copy are checked by `llm.check_no_secrets`.
- Resume is keyed by the execution signature: `exec_sig` hashes everything that changes a model's
  output (model, revision, backend, prompt version, samples, temperature, seed, max tokens, chat
  template arguments, logprobs, presence penalty, server fingerprint). Rows, raw records and the
  manifest carry it; `run` refuses a grid holding rows of a configured model under a signature the
  config does not declare, and the headline guard refuses mixed signatures.
- `rca.analyze` writes `analysis_config.yaml` and the sha256 of every input and table into
  `analysis_meta.json`; `python -m rca.reproduce <analysis dir>` reruns the analysis offline and
  exits 1 naming each table that differs, including a published CSV that was deleted or edited
  (`published_missing`, `published_modified`). Tests: `tests/test_reproduce.py`.

## 9. Using the data from code

```python
from rca.store import CanonicalStore
from rca.legacy_view import visible_case, legacy_telemetry, truth

store = CanonicalStore(data_home)
split = data_home / "splits" / "within-rcaeval-grouped-0-<hash8>"
for inc in store.incidents("rcaeval", split_dir=split, role="test"):   # visible records only
    vc = visible_case(inc)                       # VisibleCase for model-facing code
    tel = legacy_telemetry(store, vc.case_id)    # {"metrics", "logs", "traces"} DataFrames
labels = store.labels("rcaeval")                 # evaluation-only: scoring and ablation targets
```

`run_grid` uses the same calls, and accepts only configs with `source: canonical`
([`configs/canonical_pilot.yaml`](../configs/canonical_pilot.yaml),
[`configs/canonical_synthetic.yaml`](../configs/canonical_synthetic.yaml)). Canonical evidence
files (`schema: 2`) contain `incident_uid`, `system`, `candidates` and `conditions` only.
`tests/golden/canonical_synthetic_evidence.sha256` pins the synthetic evidence. It was captured
when the canonical path still matched the retired direct RCAEval loader: the text was identical
for every shared condition.

Known, intended differences from the retired direct loader:

- Candidates exclude infrastructure entities (node exporters, `main`, `istio-init`, mesh
  pseudo-clusters, truncated pod-network prefixes). `adapters/rcaeval.py` lists them (`is_infra`).
- Metric values are parsed exactly (Arrow), so they can differ from pandas' default CSV parser in
  about the 12th significant digit. Evidence text is unchanged.
- The batch cell `ts-route-service_f3_1` is fault `f3` (batch 1) of `ts-route-service`. The old
  parser read it as root `ts-route-service_f3`, fault `1`. Legacy case ids for those 3 cases now
  end in `_f3b1_<n>`.
- The candidate shuffle is seeded with `incident_uid`, so canonical and legacy prompts are not
  byte-comparable.

## 10. Transfer bundle

`export` copies, or hard-links when the file system allows, the selected parts into
`export/<name>-<YYYYMMDD>-<hash8>/parts/`, using the data-home layout. Because of that layout,
every command runs with `--data-home <bundle>/parts`. Raw data, `work/`, results and caches are
not included. Do not edit files inside a bundle: a hard-linked file shares its bytes with the
source. `configs/` holds copies of the repository's `configs/*.yaml` (build config, aliases,
evidence options, primary exclusions) as they were at export.

`bundle.json` records the datasets with their build ids and digests, split ids, licences from
`manifests/dataset_catalog.json` (non-commercial, controlled or unknown licences are marked
"private transfer only"), the git commit, the lock-file hash and package versions, every
telemetry `content_sha256`, and every `blind_nonroot` target. `verify-bundle` recomputes all
sha256 values and reports missing or extra files. `--deep` also recomputes the content hashes and
targets. [`scripts/verify_portability.sh`](../scripts/verify_portability.sh) runs the complete
check on Linux.

## 11. Versioning

- `SCHEMA_VERSION` (`src/rca/schema.py`, currently `1.0.0`): a MAJOR bump means records change
  incompatibly and need a rebuild; a MINOR bump adds optional fields.
- Each adapter has a `version`. A change invalidates its `.done` markers, so the next `normalize`
  rebuilds that dataset.
- Split manifests and bundles are immutable. A new build gives new digests, so `verify-splits`
  reports old manifests as `STALE`, and new manifests are generated next to them.
