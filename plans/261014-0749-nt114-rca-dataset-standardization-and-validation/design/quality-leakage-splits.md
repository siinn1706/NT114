# Data quality, leakage prevention, splits and missing-observability conditions

## 1. Quality states

| State | Meaning | Enters splits? |
|---|---|---|
| `ACCEPT` | No finding above `info` | yes |
| `ACCEPT_WITH_WARNINGS` | At least one `warn`; usable, and the warnings are reported per stratum | yes |
| `QUARANTINE` | Needs a human decision (possible corruption, unexplained duplicate, identity collision, adapter exception) | no, unless a manual override with a reason is written to `configs/quality_overrides.yaml` |
| `REJECT` | Not usable: no parseable label, duplicate, no telemetry, invalid label | never |

Overrides are the only manual path. Each has `incident_uid`, new state, reason, initials and date,
and is applied by the validator, so the record shows `decided_by: manual:...`. No correction is
ever made by editing canonical files by hand.

## 2. Finding codes

| Code | Severity | Check |
|---|---|---|
| `SCHEMA_INVALID` | reject | record fails JSON Schema |
| `LABEL_UNPARSEABLE` | reject | label missing or not parseable |
| `LABEL_INVALID` | reject | label names an entity that exists nowhere in the system's service map or topology |
| `DUPLICATE` | reject | `copy_of` or `duplicate_of` set |
| `NO_TELEMETRY` | reject | all three modalities `natural_absent` or `empty` |
| `ROOT_NOT_CANDIDATE` | quarantine | A-tier label not in `candidates.services` |
| `SERVICE_ID_COLLISION` | quarantine | two raw identifiers collapse to one id without a declared alias |
| `UNEXPLAINED_EXTRA_CASE` | quarantine | extra case directory not provably a duplicate |
| `ADAPTER_EXCEPTION` | quarantine | adapter raised |
| `TS_OUT_OF_RANGE` | quarantine if >1% rows, else warn | timestamps outside [2015, 2030) |
| `TS_COLUMN_OFFSET` | warn | two time columns disagree by a constant offset; the documented column was used |
| `TRACE_TIME_MISMATCH` | warn | `startTimeMillis` vs `startTime`, or `Duration` vs end−start |
| `ANCHOR_OUTSIDE_WINDOW` | quarantine | anchor not inside stored telemetry range |
| `WINDOW_CLIPPED` | warn | window cut by stream boundary |
| `LOW_COVERAGE` | warn | a present modality covers <50% of window seconds |
| `PRE_WINDOW_SHORT` | warn | <300 s of data before the anchor (evidence baseline would be thin) |
| `BASELINE_CONTAMINATED` | warn | another incident's anchor lies inside this window |
| `METRIC_NONFINITE` | info / warn >5% | NaN or inf values |
| `METRIC_CONSTANT` | info | metric constant across the window |
| `UNIT_SUSPECT` | warn | a metric's median changes by ≥10³ between adjacent incidents of one system (unit flip) |
| `EMPTY_MODALITY_FILE` | info | header-only file → `empty` |
| `PARSE_ERROR` | warn (partial) / quarantine (whole file) | rows that failed parsing, counted |
| `TRACE_ORPHAN_SPANS` | info / warn >20% | `parent_span_id` not found in window |
| `LOG_LEVEL_MISSING` | info | no level column; error detection falls back to keywords |
| `LABEL_ARTIFACT_PRESENT` | info | a label artefact sits beside telemetry (recorded, never ingested) |
| `MULTI_ROOT` | info | label names several entities |
| `NON_SERVICE_ENTITY` | info | `kind=infra` column excluded from candidates |

## 3. Dataset-level and cross-dataset audits (`rca.prep audit`)

Outputs `data/reports/audit-<build>.json` plus a Markdown summary in the report directory of the
active plan.

- **Duplicates inside a dataset:** incident fingerprint = (system, anchor_ns rounded to 1 s,
  root entity, fault family). Equal fingerprints with different uids → `DUPLICATE` candidates.
  Telemetry duplicates: equal `content_sha256` on any modality across incidents.
- **Cross-dataset overlap:** the same fingerprint across datasets, or equal `content_sha256`.
  Expected: none among acquired A sources (HF RCAEval is not ingested). Any hit is reported.
- **Lineage consistency:** every canonical incident maps to exactly one row of the acquisition
  `data/manifests/incidents.jsonl` (by `source_incident_id`); counts per lineage group match
  `lineage-report.json` for every dataset that has a completed build (RCAEval 735 + 1 duplicate,
  Nezha 101, AIOps2025 400, RCA100 103; B datasets Cloud-OpsBench 754 and PetShop 68 once
  phase 08 has run). Datasets without a build are listed as "not built", not as missing.
- **Imbalance and coverage:** per dataset × system × fault family: incident counts, modality
  status counts, candidate-set sizes, root-position histogram (is the root often the first or the
  only flagged service?), and quality-state counts.
- **Label leakage scan:** see §4.

## 4. Leakage prevention

### Threat model

What must never reach the LLM prompt, evidence text or features, retrieval queries, or the Jev
state: the root-cause identity, the fault type, label artefacts, the ablation target, the cause of
missingness (natural vs ablated), source paths or ids that encode labels, and labels of incidents
outside the training split.

### Controls

1. **Zone separation, enforced by type:** model-facing code (`evidence.build`,
   `evidence.shuffled_candidates`, `llm.build_messages`, `CaseStore.search`, `gate.jev_payload`)
   receives a `VisibleCase` (`case_id`, `dataset`, `system`, `inject_time`, `services`, `path`)
   that has **no** `root_service` or `fault` attribute. Truth travels in a separate `Truth`
   object and is passed only to `ablate.apply` (target choice), scoring and the oracle store
   mask. An import scan alone is not enough, because labels on a shared object are reachable by
   attribute access. `LabelRecord` is loaded only by scoring code, the ablation driver and the
   split builder.
2. **Opaque ids:** `incident_uid` is a hash. `source_incident_id` (which encodes labels for
   RCAEval) is eval-only.
3. **Label-artefact quarantine:** RCAEval `root_cause.txt`, AIOps2025 `key_*`/`fault_description`,
   RCA100 `answer_key/` and `raw_ground_truth`, Nezha `root_cause_*.json`, and Cloud-OpsBench
   `golden-trajectory`/`process-label` are referenced only from `label_artifacts`.
4. **Retrieval (owner decision R1):** the case store holds training-role incidents only, under
   a retrieval protocol that groups only physical duplicates, overlapping windows and equal
   content (not fault cells), so same-cell repeats remain legitimate precedents.
   - `precedent` (headline, **label-free**): eligibility = train role ∧ different `group_id`
     (from the split manifest); no comparison with the query's labels. This is the only mode
     whose hits and `hit_top_sim` may enter the prompt for Jev runs and the Jev state.
   - `no_precedent` (**oracle ablation**): additionally excludes entries with the query's
     (root, fault). The exclusion set is computed by the caller from `Truth` and passed to
     `CaseStore.search(exclude_ids=...)`; `retrieve.py` itself never reads labels of the query.
     Rows are tagged `store_mode=no_precedent` and reported separately; their `hit_top_sim` is
     never used as a Jev input.
5. **Ablation operator is label-agnostic:** `mask_service_traces(tel, service)` takes a service
   name; the root is passed in only by the condition driver. `blind_root` and `blind_nonroot` call
   the same operator.

### Tests (phase 09 and 10)

| Test | Mechanism | Pass condition |
|---|---|---|
| Canary label | Synthetic fixture whose label fields hold a random token `CANARY_<hex>` that appears nowhere in telemetry | Token absent from every visible file, evidence text, prompt, retrieval query and Jev payload |
| Visible-type guard | Build evidence, candidates, prompts, store queries and the Jev payload from `VisibleCase` objects | Runs without error; `hasattr(case, "root_service")` is false at every model-facing entry point (asserted by a wrapper in the test) |
| Label-permutation invariance | Shuffle labels among **test-role** incidents only; rebuild evidence, prompts with `retrieval ∈ {none, bm25, dense, hybrid}` in `precedent` mode, and `gate.jev_payload` states, for conditions `full`, `no_metric`, `no_log`, `no_trace` | Byte-identical evidence, prompts and Jev states (`no_precedent` is excluded by design and labelled oracle) |
| Masking parity | For each incident, `blind_root` output equals `mask_service_traces(tel, root)`, and `blind_nonroot` equals `mask_service_traces(tel, chosen)` | Equal tables |
| Denylist scan | Scan visible JSONL keys and Parquet column names | No denylisted name |
| Free-text artefact scan | Search visible JSONL text fields (`context.visible_text`) and evidence text for the exact free-text label artefacts (`fault_description` items, `raw_ground_truth` narratives, `root_cause.txt` lines). Metric vocabularies such as AIOps2025 `key_metrics` are **not** scanned, because they are real telemetry names | Zero hits |
| Path scan | Search visible files for raw path fragments (`RE2-OB/`, `_cpu/`, `fault_list`) | Zero hits |
| Store isolation | Build the retrieval store for a split | No test or validation uid present; assertion in code plus test |
| Jev state | Build the payload via `gate.jev_payload` from a row of a test variant | Keys ⊆ allowlist; values contain no label token (canary) |

## 5. Splitting

### Grouping

Two grouping rules, each a connected component (union-find):

- **`physical` grouping** joins incidents with (a) overlapping **evidence** windows within one
  stream (evidence window from config, default [t−600 s, t+300 s], not the wider storage window),
  (b) `copy_of` / `duplicate_of`, (c) equal `content_sha256` on any modality.
- **`cell` grouping** = `physical` plus same `fault_cell`
  (`<lineage>/<system>/<root entity>/<fault family>`; spans RE1, RE2 and RE3).

All variants (conditions) of an incident share its `incident_uid`, so they always share its split.

Phase 02 measures the number of groups per dataset under both rules. Predeclared outcome for
Nezha: injections are about 480 s apart, so even evidence windows chain whole days; Nezha gets
only `eval-only-nezha` and `xdata-*-to-nezha` protocols unless the measurement shows ≥20 groups.

### Protocols (all deterministic from `seed` and the sorted group list)

| Protocol id | Use | Rule |
|---|---|---|
| `within-<dataset>-grouped` | gate training, fine-tuning (no same-cell leakage) | `cell` grouping; groups shuffled by seed, assigned to train/val/test by greedy fill to 60/20/20 of incidents, stratified by system × fault family (a stratum with <3 groups goes to test) |
| `within-<dataset>-retrieval` | retrieval experiments (`precedent` / `no_precedent`) | `physical` grouping, same fill rule; same-cell repeats may fall in train and serve as precedents |
| `loso-<dataset>` | cross-system generalization | one fold per system; test = all groups of that system. Shipped as one manifest directory per fold, `loso-<dataset>-<fold>-<seed>-<hash8>`, with `params.fold` in `split.json` |
| `xdata-<train>-to-<test>` | cross-dataset | train = A groups of the training dataset(s); test = A groups of the target dataset; shared systems (OB in RCAEval and Nezha) reported, not hidden |
| `eval-only-<dataset>` | zero-shot LLM evaluation | every accepted A incident in test; no train (used when no learned component is involved) |

Only `ACCEPT` and `ACCEPT_WITH_WARNINGS` incidents enter. B-tier incidents may enter train sets
only; their tier is recorded per assignment.

### Manifests (`data/splits/<protocol>-<seed>-<hash8>/`)

- `split.json`: protocol, seed, parameters, schema version, list of `{dataset_id, build_id,
  input_digest}` it was built from, counts per split × stratum, creation time, and `assignments_sha256`.
- `assignments.jsonl`: `{incident_uid, split, group_id_hash}` sorted by uid. No labels.
- The directory name includes the first 8 hex of `assignments_sha256`. The CLI refuses to write
  into an existing split directory, and `verify-splits` recomputes the hash. A split referencing a
  build whose `input_digest` changed is reported as `STALE`.

Split manifests are small and tracked in git (`.gitignore` gets `!data/splits/`).

## 6. Missing-observability conditions

| Condition | Operation | Applicable when (natural status) | Notes |
|---|---|---|---|
| `full` | none | ≥1 modality present | baseline |
| `no_metric` / `no_log` / `no_trace` | drop modality | that modality `present` **and** ≥1 other modality present after the drop | skip otherwise (no fake ablation of absent data, no all-empty cells) |
| `blind_root` | remove spans of the root service | traces `present`, root has ≥1 span, label has `primary_root_service` | existing condition |
| `blind_nonroot` | remove spans of one non-root service | as above, and ≥1 other service has spans | control. Target = the non-root service whose span count is closest to the root's (ties broken by `sha256(uid + service)`); recorded in the eval-only ablation log |
| `natural` | none | — | not an ablation: `full` results stratified by natural status. Inferential comparisons are paired **within one release** (RE2-SS vs RE2-OB/TT, RE3-SS vs RE3-OB/TT, same fault set). RE1 (metric-only) is a different collection and is **descriptive only** |

**Anchor precondition (all conditions):** `anchor_kind ∈ {injection, alert}` and no
`PRE_WINDOW_SHORT` finding. Incidents with `anchor_kind = window_start` (Cloud-OpsBench) or a
short pre-window get no evidence conditions and are excluded from overconfidence tables.

**Anchor visibility (owner decision R3):** the anchor time comes from label files
(`inject_time.txt`, Nezha `fault_list.json`) and is used only to place evidence windows, as in
standard RCA benchmarks where it approximates alert time. It never appears as text in evidence or
prompts. This is recorded as a threat to validity in `docs/data_contract.md`.

**Single source of applicability:** in the canonical path, `run_grid` reads applicability from
`condition-matrix-<dataset>.json`; `ablate.applicable` is kept only for the legacy path.

Visible missingness text is identical for natural and ablated absence (the evidence builder keeps
its current "not available" sentence). The cause is recorded only in eval-only metadata, so the
model cannot distinguish the experiment from a real outage.

Applicability is precomputed per incident into `data/reports/condition-matrix-<build>.json`
(uid × condition → applicable, reason), so later runs do not re-derive it.

### Missingness tests

- `no_<m>` removes exactly that modality and leaves the others byte-identical.
- `blind_root` removes only spans whose `service_id` equals the root; span counts of other services
  are unchanged; parent edges into the removed service remain (caller spans stay, as in the
  existing design).
- `blind_nonroot` never selects the root and is deterministic across runs and machines.
- A condition is never generated when not applicable; the matrix marks it with a reason.
- Natural `empty` and `natural_absent` remain distinguishable in eval-only metadata and identical
  in visible evidence text.
