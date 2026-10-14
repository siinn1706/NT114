# Repository and raw-data audit (planning scout, 2026-10-14)

`RCA_ROOT` = `nt114-rca/nt114-rca`. Every claim below was read from the repository or the raw files
during planning. Raw archives were read in place (zip central directories, the first bytes of
members, and one tar listing). Nothing was extracted or modified. Items marked **UNVERIFIED** are
assumptions that phase 02 must confirm.

## 1. What has been acquired and verified

The acquisition plan finished on 2026-10-14
(`plans/261013-2300-aiops-rca-dataset-acquisition/plan.md`, receipt `receipts/cook-receipt-20261014.json`).

| Source id | State (`data/.state/<id>.json`) | Raw location under `data/raw/` | Raw size on disk | Raw form |
|---|---|---|---|---|
| `rcaeval-zenodo` | VERIFIED | `rcaeval-zenodo/zenodo-14590730/RE{1,2,3}-{OB,SS,TT}.zip` | 4.9 G | 9 zips; CSV per case |
| `rcaeval-hf` | VERIFIED (derived copy, `copy_of`) | `rcaeval-hf/...` | 3.3 G | Parquet per case |
| `agenticopseval` | VERIFIED | `agenticopseval/gitlab-69cf36430b43/{AIOps2025,RCA100}` | 13 G | AIOps2025: 18 daily `tar.gz`; RCA100: Parquet per case |
| `nezha` | VERIFIED (git @d8140101) | `nezha/git-d8140101fdb4/rca_data/<date>/` | 3.2 G (2.8 G `rca_data`) | CSV per minute / per pod |
| `cloud-opsbench` | VERIFIED | `cloud-opsbench/hf-1a02e54329cc/benchmark/...` | 3.7 G | JSON per case, 170 `metrics.csv` |
| `petshop` | VERIFIED | `petshop/git-2e96f937c4c0/dataset/...` | 23 M | `metrics.csv` + `target.json` |
| `dejavu` | VERIFIED | `dejavu/zenodo-6955909/{A1,A2,B,C,D}.zip` + 7-part raw | 4.3 G | pickles/CSV + `faults.csv` |
| `rcabench-fse26` | VERIFIED (bytes only) | `rcabench-fse26/...` | 13 G | one 13.4 GB `tar.gz`, members **not listed** |
| `anomod` | VERIFIED (bytes only) | `anomod/zenodo-18342898/AnoMod.zip` | 193 M | 44,291 members; label format not parsed |
| `msds` | VERIFIED (bytes only) | `msds/zenodo-3549604/*.zip` | 621 M | traces/logs/metrics; label granularity unknown |
| `openrca` | PENDING:drive-quota | — | 24 K | not acquired |
| `aiops2020/2021-upstream` | PENDING:metadata-only | label files only | <1 M | lineage reference |
| `gaia`, `eadro`, `lemma-*`, `lo2v2` | PENDING (decision / licence / deferred) | — | — | not acquired |

Integrity: 31,495 files, all `publisher-hash`, listed in `data/manifests/checksums.sha256` with
levels in `checksums-levels.tsv`. Incident registry: `data/manifests/incidents.jsonl` (3,055 rows,
2,320 independent; lineage groups L1–L10). These outputs are reused; acquisition is not repeated.

## 2. Raw formats observed (sampled)

### RCAEval Zenodo (canonical L1)

- Case path `RE<n>-<SYS>/<service>_<fault>/<instance>/`. Case counts per zip:
  RE1 125×3 (metrics only: `data.csv`, plus `simple_data.csv` except RE1-OB), RE2-OB 91,
  RE2-SS 90, RE2-TT 90, RE3 30×3. Total 736 `inject_time.txt` files; one is a duplicate (below),
  so 735 incidents, matching `incidents.jsonl`.
- RE2/RE3 case files: `metrics.csv` (wide, `time` in unix s, column `<svc>_<prom-metric>`),
  `simple_metrics.csv` (wide, `<svc>_{cpu,mem,diskio,latency-50,latency-90,...}`), `logs.csv`
  (`time` is a `HH:MM` string, `timestamp` is unix ns, `container_name`, `message`, `level`, ...),
  `traces.csv` (`time` `HH:MM` string, `startTimeMillis` ms, `startTime` µs, `duration` µs,
  `statusCode`, `parentSpanID`), and derived aggregates `logts.csv`, `tracets_lat.csv`,
  `tracets_err.csv`, `cluster_info.json`, `pod-node-{1,2}.csv`, `metrics_postprocess.log`, `metrics.png`.
- RE3-SS log columns differ from RE2-OB (`pod_name`, `node_name`, no `level`).
- RE2-SS has no traces (natural). RE3-SS: 17 cases without `traces.csv`, 13 with a 116-byte
  header-only file.
- **RE2-OB `checkoutservice_cpu/multi-source-data/`** holds a full case whose `inject_time.txt`
  (`1705354566`) equals `checkoutservice_cpu/1`. Same incident, packaged twice. The directory also
  ships a nested `multi-source-data.zip` (12.7 MB) and `.DS_Store` files.
- **RE3-TT `ts-route-service_f3_1/{1,2,3}`**: a second batch of fault `f3` on `ts-route-service`.
- **RE3-SS ships 8 `root_cause.txt` files in the Zenodo zip itself.** Each holds one log line from
  the root-cause service. `docs/dataset_quality_audit.md` says they "do not exist in the Zenodo
  release"; that is wrong. `mirror-completeness-rcaeval.json` lists them under `hf_root_cause_txt`
  but not under `files_only_on_hf_by_name`, which agrees with the zip. They are label artefacts:
  using them as telemetry would leak the answer.

### Nezha (L4)

- `rca_data/<date>/<date>-fault_list.json`: `{hour: [{inject_time, inject_timestamp (s),
  inject_pod, inject_type}]}`; 4 dates, 101 incidents (56 OB, 45 TT).
- Telemetry is a continuous stream per date: `log/HH_MM_log.csv` and `trace/HH_MM_trace.csv`
  (one file per minute), `metric/<pod>_metric.csv` (one file per pod, 1-minute rows),
  `traceid/HH_MM_traceid.csv`.
- Trace columns: `TraceID, SpanID, ParentID ("root" for roots), PodName, OperationName,
  StartTimeUnixNano, EndTimeUnixNano, Duration`. Log columns: `Timestamp, TimeUnixNano, Node,
  PodName, Container, TraceID, SpanID, Log` (`Log` is nested JSON text).
- **Metric `TimeStamp` disagrees with `Time`.** In `2022-08-22/metric/adservice-..._metric.csv`,
  `Time` = `2022-08-22 03:51:19 UTC` (= 1661140279) while `TimeStamp` = `1861140279`, exactly
  2×10⁸ s later. Prevalence across files is **UNVERIFIED**.
- Labels are pods (`frontend-579b9bff58-t2dbm`); the service needs a pod→deployment mapping.
- Consecutive injections are about 8 minutes apart, so a 10-minute normal window of incident *k*
  contains the anomaly of incident *k−1*.
- `construct_data/root_cause_{hipster,ts}.json` maps service→fault→indicator (a metric name or a
  log template). It is label-derived and must stay evaluation-only.

### AgenticOpsEval AIOps2025 (L2)

- `groundtruth.jsonl` (400): `fault_category, fault_type, instance_type ∈ {service 195, pod 123,
  node 82}, service, instance (str 221 / list 179), source, destination, start_time, end_time
  (UTC, 1–1500 s), key_observations, key_metrics, fault_description`.
- `key_observations`, `key_metrics`, `fault_description` are label-derived scoring aids. They must
  never reach a prompt.
- Telemetry is 18 daily archives (`2025-06-06..14`, `2025-06-17..29`), each with hourly log and
  trace Parquet slices and per-pod/service/node/TiDB metric Parquet. The archives contain macOS
  `._*` AppleDouble members.
- 31 incidents have a UTC start date (06-05, 06-16, 06-23, 06-26) with no archive of that name.
  The archives are probably named by local date (UTC+8). **UNVERIFIED**: phase 02 must read the
  timestamps inside one archive.

### AgenticOpsEval RCA100 (L3)

- 103 cases `cases/tNNN/{metrics,logs,traces,events,alerts}.parquet, task.json, topology.json}`.
- `task.json` holds the alert window and `prompt_text` (model-visible by design). Ground truth is
  `answer_key/tNNN.gt.json` (`root_cause_entities[]`, `raw_ground_truth`).
- The answer-key README says the folder is no longer publicly readable and must be distributed
  "through controlled channels only". Entity types (APM operations, services, pods) and the
  service-level share are **UNVERIFIED**.

### Others

- Cloud-OpsBench: `index.jsonl` (754: boutique 550, trainticket 204; `fault_object` kind app 659 /
  node 48 / namespace 47; 8 categories such as admission, scheduling, startup). Per case:
  `metadata.json`, `tool_cache.json` (Kubernetes API responses keyed by tool call),
  `raw_data/{alert,k8s_states,logs}.json`, and `metrics.csv` in 170 cases. No traces. Faults are
  mostly configuration and lifecycle faults.
- PetShop: 68 `target.json` (`root_cause.node` is an AWS resource; `target` is the symptom
  metric), `metrics.csv`; metric-only; AWS application, not a microservice graph.
- DejaVu: `faults.csv` (`timestamp, object, fault_description, kpi, name, node_type,
  root_cause_node`); entities are docker/db/os nodes; metric-only processed sets.
- AnoMod: SocialNetwork and TrainTicket; members named like
  `Lv_C_exception_injection_<ts>_em`; label format **UNVERIFIED**.
- MSDS: `sequential_data/{traces,logs,metrics,reports}` and
  `IMPORTANT_experiment_start_end_data.txt`; root-cause granularity **UNVERIFIED**.
- RCABench FSE'26: one 13.4 GB `tar.gz`; member layout **UNKNOWN**.

## 3. Existing pipeline: assumptions and defects

| # | Location | Finding | Consequence | Planned fix (phase) |
|---|---|---|---|---|
| D1 | `src/rca/data.py:45-48`, `:59-69` | `_parse_service_fault` splits on the last `_`. Zenodo `RE3-TT/ts-route-service_f3_1/<n>` parses as service `ts-route-service_f3`, fault `1`. | Three RE3-TT incidents get root `routeservicef3` (`canon("ts-route-service_f3")`), which is never a candidate, so they are always "wrong". Fixing only the parser would make their `case_id` collide with `ts-route-service_f3/{1,2,3}`, and `run_grid` would silently skip 3 cases (`run_grid.py:61-63`, key at `:120`). | Explicit fault-vocabulary parser; batch encoded in `case_id` (`…_f3b1_<n>`); uniqueness assertion in `discover_cases` (05) |
| D2 | `src/rca/data.py:70`; `src/rca/run_grid.py:27`, `:72`, `:79` | `open()` without `encoding`. On Windows the default is cp1252: `json.dump(..., ensure_ascii=False)` raises on non-Latin-1 text, and `json.load` misreads UTF-8 (reproduced on Cloud-OpsBench `tool_cache.json`). | The pipeline is not portable between the Windows prep machine and the Linux GPU machine. | UTF-8 everywhere; deterministic JSON writer (03, 11) |
| D3 | `src/rca/run_grid.py:65` | The evidence record stores `asdict(case)`, including `root_service` and `fault`, next to the model-visible evidence. | Ground truth and model-visible data share a file. Anything that later exports evidence for training also exports labels. | Evidence files hold only visible fields; labels are joined at scoring time from the eval-only store (11) |
| D4 | `src/rca/run_grid.py:93-98`; `src/rca/retrieve.py:81-87` | The case store holds every prepared case with its label. `precedent` excludes only the same `case_id`; repeated injections of the same cell (3–5 per cell) stay retrievable. There is no train/test split. | Held-out labels are retrievable. Fine for the stated `precedent` ablation, but no split-aware evaluation exists. | The store is built from the train split only; `precedent` / `no_precedent` keep their meaning inside it (10, 11) |
| D5 | `src/rca/ablate.py:7-8`, `:25-27` | `blind_root` deletes the root's spans, and there is no matched control. A service with metrics and logs but no spans is a signature that can point at the root. | The `blind_root` effect cannot be separated from "a service lost its spans". | Add `blind_nonroot` control with a deterministic, matched target (10) |
| D6 | `src/rca/ablate.py:36-42` | `applicable()` checks only `is not None`. A header-only `traces.csv` (13 RE3-SS cases) yields an empty DataFrame → `_read_table` returns `None`; the absence is indistinguishable from "no file". | Natural "empty" and "absent" telemetry are merged. | Canonical per-modality status (`present`, `natural_absent`, `empty`, `corrupted`) (03) |
| D7 | `src/rca/data.py:116-120`, `:123-125` | `canon()` is a lossy regex (strip non-alnum, `ts` prefix, `service` suffix). No collision check; `metric_services` takes every `<x>_<y>` column, including `main_cpu` in RE1-OB. | Silent identity merges are possible; candidate lists may include non-services. | Explicit per-system service map with collision and idempotence checks; `canon` kept for compatibility (03, 05) |
| D8 | `src/rca/data.py:24-29` | Metric file preference `simple_metrics.csv` before `metrics.csv`. | The richer `metrics.csv` is never read. | Canonical store keeps both as `metric_set` = `full` / `simple`; the legacy view defaults to `simple` (05) |
| D9 | `src/rca/evidence.py:22`, `:26-29` | Fixed windows 600 s before / 300 s after `inject_time`. Fine for RCAEval case files; wrong for continuous streams with incidents 8 minutes apart (Nezha). | Baseline windows contain another incident. | Canonical incidents record `baseline_contaminated_by` overlaps; window bounds are part of the config (06, 09) |
| D10 | `README.md` §1; system Python | `requirements.txt` is unpinned and the system Python 3.12.10 has none of pandas, pyarrow, pyyaml or pytest installed. | Results are not reproducible across machines. | Project `.venv` plus `requirements-lock.txt` (01) |
| D11 | `docs/dataset_quality_audit.md` (anomalies table, mirror section) | States that the 8 RE3-SS `root_cause.txt` files are HF-only; the Zenodo zip has them. | A wrong provenance claim. | Correct the doc (01) |
| D13 | `src/rca/data.py:37-38`; `src/rca/run_grid.py:70`, `:123`, `:124` | The label-bearing `Case` (`root_service`, `fault`) is passed into `evidence.build`, `CaseStore.search` and `build_messages`. | Labels are reachable from model-facing code by attribute access; an import scan cannot detect it. | `VisibleCase` without label attributes for model-facing calls; `Truth` passed separately (05, 11) |
| D14 | `src/rca/retrieve.py:83-84`, `:117`; `src/rca/gate.py:28`, `:41`, `:157` | `no_precedent` masks with the query's (root, fault); its hits are shown in the prompt and its `hit_top_sim` feeds the Jev state by default. | The Jev input becomes label-conditioned. | `precedent` (label-free, group-based) is the headline mode and the only Jev source; `no_precedent` is an oracle ablation with a caller-supplied exclusion set (10, 11) |
| D12 | `src/rca/run_grid.py:79-80`; `load_evidence` | `Case(**r["case"])` stores absolute `path` values from the prep machine. | Evidence files are not portable. | Store relative refs (11) |

What already works and must be preserved: synthetic end-to-end run
(`configs/synthetic.yaml`), `tests/test_pipeline.py`, `tests/test_datasets_acquire.py`, the
acquisition CLI `scripts/datasets/acquire.py` (`verify`, `audit-archives`, `catalog`, `status`),
`scripts/datasets/lineage.py`, the per-case shuffled candidate order
(`src/rca/evidence.py:212-216`), and the result-row fields consumed by
`src/rca/gate.py:27-52` and `src/rca/analyze.py`.

## 4. Overlap, duplication, label inconsistencies

- L1: HF RCAEval is a derived copy (`copy_of`), with 6 difference classes, including a truncated
  `inject_time` (`re1ob_currencyservice_loss_1`). Only Zenodo is ingested.
- L1 internal: `multi-source-data` duplicates `RE2-OB/checkoutservice_cpu/1`.
- L2 vs aiops.cn project 107: identical ground truth (not acquired).
- L5: OpenRCA ⊂ AIOps 2020–2022; not acquired yet.
- Shared systems, not shared incidents: Online Boutique in L1, L2, L4, L9 (and L3 OTel demo is
  a different app); Train Ticket in L1, L4, L9, L12.
- Label granularity differs: service (RCAEval, Cloud-OpsBench `app/*`), pod (Nezha, AIOps2025
  `pod`), node (AIOps2025 `node`, Cloud-OpsBench `node/*`, DejaVu), multi-entity (AIOps2025 network
  faults: 179 list-valued instances), AWS resource (PetShop), entity list (RCA100).
- Fault vocabularies are disjoint across datasets (`cpu` vs `cpu_contention` vs `cpu stress`).
  Fault types are stored as source strings plus a coarse `fault_family` mapping; they are never
  merged silently.
