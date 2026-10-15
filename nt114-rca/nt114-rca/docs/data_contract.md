# Data contract: canonical incidents, splits and the transfer bundle

This is the contract between data preparation (`python -m rca.prep`) and everything that consumes
it: `run_grid`, evidence, retrieval, the LLM layer and the Jev decision layer. The JSON Schema
[`schemas/canonical_incident.v1.schema.json`](../schemas/canonical_incident.v1.schema.json) is the
authority for record fields. This page explains the zones, the files, the rules and how to use
them. It does not copy the field list.

## 1. Pipeline

```text
raw (immutable) -> adapter -> canonical/v1/<dataset>/{visible, eval_only} -> validate -> audit
                -> conditions (condition matrix) -> split (manifests) -> run_grid (evidence, LLM, Jev)
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
   `llm.build_messages`, `CaseStore.search` and `gate.jev_payload` receive `VisibleCase` objects,
   which have no `root_service` or `fault` attribute. `tests/test_leakage.py` asserts this at
   every entry point and scans those modules' source for label access.
2. Label artefacts (`root_cause.txt` and similar) are referenced only from
   `LabelRecord.label_artifacts` and never ingested.
3. Retrieval (owner decision R1). The store holds train-role incidents of a
   `within-*-retrieval` split.
   - `precedent` (headline, label-free) excludes the query's own split group. It is the only mode
     whose hits and similarity may reach the prompt for Jev runs and the Jev state.
   - `no_precedent` is an oracle ablation. The caller adds incidents with the query's
     (root, fault) from `Truth` through `CaseStore.search(..., exclude_ids=...)`; `retrieve.py`
     never reads query labels. Its result rows carry `oracle_store: true`.
4. The masking operator takes a service name; only the condition driver passes the root or the
   control target. The masked service is logged in `ablation_log.jsonl` next to the results,
   never in the evidence directory.
5. Checks: canary label, label-permutation invariance (evidence, prompts for every retrieval
   method in `precedent` mode, Jev states), denylisted keys and Parquet columns
   (`schema.LABEL_DENYLIST`), raw-path fragments and free-text label artefacts in the visible zone
   (`rca.audit.leakage_scan`).

## 8. Jev decision state

`jev.build_state()` produces the Jev state. Its top-level keys must be in
`schema.DECISION_STATE_ALLOWED_KEYS` (exact match): `evidence`, `assistant_first_answer`,
`assistant_ranking`, `assistant_confidence`, `assistant_flagged_insufficient`,
`telemetry_available`, `similar_past_incident_similarity`, `candidate_count`, `decision_stage`.
The allowlist takes precedence over the label denylist, because the denylist's `answer` token would
otherwise reject `assistant_first_answer`; `schema.denylisted` is applied to nested keys only.
Numbers reach Jev as text with a verbal band (`"8 of 10 samples agree (high)"`).

`decide.decision_inputs()` builds the state from the evidence file and named LLM aggregate fields
(`ranking`, `conf_verbal`, `conf_consensus`, `abstain_vote`, `n_candidates`, top precedent
similarity) only, never from a whole grid row: grid rows also carry `truth`, `truth_ids`, `fault`,
`correct`, `rank`, `hits[].root` and `hit_has_truth`. The similarity comes from `precedent` rows;
`decide` refuses a grid with `oracle_store` (`no_precedent`) rows. `gate.action_table` (the legacy
comparator table) defaults to `store_mode="precedent"` and raises on `no_precedent` unless
`oracle=True`. Root service, fault, label artefacts, masked service, missingness cause,
`source_incident_id` and dataset paths are never allowed. Tests: `tests/test_jev.py`,
`tests/test_leakage.py`.

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

`run_grid` uses the same calls when a config sets `source: canonical`
([`configs/canonical_pilot.yaml`](../configs/canonical_pilot.yaml),
[`configs/canonical_synthetic.yaml`](../configs/canonical_synthetic.yaml)). Canonical evidence
files (`schema: 2`) contain `incident_uid`, `system`, `candidates` and `conditions` only.

Known, intended differences from the legacy loader:

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
