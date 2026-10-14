# Dataset compatibility matrix and A/B/C classification

Sources: the acquisition catalog (`plans/261013-2300-aiops-rca-dataset-acquisition/research/dataset-catalog.md`),
`RCA_ROOT/data/provenance/<id>.json`, `RCA_ROOT/data/manifests/{incidents.jsonl,lineage-report.json}`,
and the planning scout ([repo-audit.md](repo-audit.md)). `?` = UNKNOWN or UNVERIFIED; phase 02
resolves it, or the source stays out of the A set. Phase 02 measured values are in the section
"Measured in phase 02" below and in `RCA_ROOT/data/reports/compatibility-matrix.json`; the table keeps
the planning values, and the Tier column shows the measured outcome.

## Classification rule

- **A: service-level RCA evaluation.** Injected or expert-validated root cause; the label maps to
  a service with a documented deterministic rule; at least one of metrics, logs or traces is
  time-aligned to the incident; licence permits local research use; status VERIFIED.
- **B: auxiliary.** Usable for training, domain adaptation or robustness (natural metric-only,
  configuration faults, node-level labels), but fails one A criterion.
- **C: excluded.** Unverified, not acquired, duplicate or derivative, no usable label, or no
  permission.

A dataset can contribute an A subset and a B subset (for example AIOps2025 service+pod faults are
A; node faults are B). Membership is recorded per incident (`eval_tier` in labels), not only per
dataset.

## Matrix

| Dataset (source id) | Lineage | Publication / version | Incidents (verified) | Systems | Modalities M/L/T | Time units | Label source and granularity | Service mapping | Known defects | Tier |
|---|---|---|---|---|---|---|---|---|---|---|
| RCAEval RE2, RE3 (`rcaeval-zenodo`) | L1 | WWW'25 Companion; Zenodo 14590730 | RE2 270 (+1 duplicate), RE3 90 | OB, SS, TT | M L T; SS: no T (RE2), T absent/empty (RE3) | metrics s; logs ns; traces µs; `inject_time` s | Directory name: service + fault, injected | Identity (service is in path); fault parser must handle `_f3_1` | duplicate `multi-source-data`; `root_cause.txt` label artefacts; D1 parse bug | **A** (reference) |
| RCAEval RE1 (`rcaeval-zenodo`) | L1 | same | 375 | OB, SS, TT | M only (natural) | s | same | same | `main_cpu` column in RE1-OB | **A** (natural metric-only stratum, descriptive only) |
| RCAEval HF (`rcaeval-hf`) | L1 copy | HF @afeacb11 | 735 copies | — | — | — | — | — | incomplete copy, truncated `inject_time` | **C** (copy; cross-check only) |
| Nezha (`nezha`) | L4 | FSE'23, git @d8140101 | 101 (OB 56, TT 45) | OB, TT | M L T (continuous stream) | traces/logs ns; metrics `TimeStamp` suspect (+2e8 s) | `fault_list.json`: pod + fault type + time, injected | pod → deployment by stripping replica-set and pod hashes (`?` for StatefulSets) | timestamp offset; overlapping windows | **A** (gate pass, measured; was: A if the timestamp check passes) |
| AIOps2025 (`agenticopseval`) | L2 | arXiv 2606.29193; GitLab @69cf3643 | 400 (service 195, pod 123, node 82) | OB + TiDB + Redis on k8s | M L T (daily archives) | ISO UTC labels; Parquet ts `?` | `groundtruth.jsonl`, injected; multi-entity for network faults | `service` field present; pod `paymentservice-1` → `paymentservice` | 31 incidents on archive-less UTC dates (TZ `?`) | **A** for service/pod (gate pass, measured); **B** for node |
| RCA100 (`agenticopseval`) | L3 | v1.1, Alibaba Cloud | 103 | OTel demo | M L T + events, alerts | ISO UTC | `answer_key/*.gt.json` `root_cause_entities[]` | entity types `?` | controlled-distribution answer key | **A** (gate pass: 83/103 = 80.6%; the 20 other cases are not service-level) |
| OpenRCA (`openrca`) | L5 | ICLR'25 | 335 (paper) | Bank, Market, Telecom | M L T | `?` | `record.csv`, expert-filtered | `?` | not acquired (Drive quota); biased to full observability | **C (pending acquisition)**; adapter spec reserved |
| RCABench FSE'26 (`rcabench-fse26`) | L11 | arXiv 2510.04711; Zenodo 17105974 | 1,430 (paper, UNVERIFIED) | `?` | `?` | `?` | `?` | `?` | creator placeholder; layout unknown | **A** after profiling (gate pass, measured); no adapter yet (milestone M3) |
| Cloud-OpsBench (`cloud-opsbench`) | L9 | v1.0.0, HF @1a02e543 | 754 (app 659, node 48, namespace 47) | boutique, trainticket | L + k8s state + alerts; M in 170; no T | ISO | `index.jsonl` `fault_object` + config-level `root_cause` | `app/<deployment>` → service | agent-tool format; config faults | **B** (auxiliary: config and lifecycle faults, no traces) |
| PetShop (`petshop`) | L10 | CLeaR'24 | 68 | AWS PetShop | M only | s | `target.json` `root_cause.node` (AWS resource) | resource, not service | — | **B** (metric-only, non-microservice entities) |
| DejaVu A1–D (`dejavu`) | L13 | FSE'22 | `?` (`faults.csv` ×5) | 5 enterprise/benchmark systems | M only | s | `faults.csv` `root_cause_node` (docker/db/os) | node, not service | `.ipynb_checkpoints` copy of a label file | **B** |
| AnoMod (`anomod`) | L12 | MSR'26 | `?` | SocialNetwork, TrainTicket | M L T + API, coverage | `?` | injection names in paths; format `?` | `?` | — | **C** (gate fail, measured) |
| MSDS (`msds`) | L14 | ESOCC'20 | `?` | OpenStack | M L T | `?` | `IMPORTANT_experiment_start_end_data.txt`; granularity `?` | `?` | — | **C** (gate fail, measured) |
| AIOps 2020/2021 upstream | L5 | label files only | 159 (2021) | Telecom, Bank | — | — | lineage reference | — | no telemetry | **C** (lineage metadata only) |
| GAIA, Eadro, LEMMA, LO2 | L6–L8 | — | — | — | — | — | — | — | not acquired (licence / decision) | **C** |

## Promotion gates (decided now, applied in phase 02)

| Source | Gate to pass | If it fails |
|---|---|---|
| Nezha | Metric timestamps can be aligned by a documented rule (prefer the `Time` string; accept `TimeStamp` only where it agrees within 60 s), and ≥95% of incidents have M, L and T rows inside [t−600 s, t+300 s] | The metric modality is marked `corrupted` for the affected files; incidents stay A with traces and logs only, flagged `ACCEPT_WITH_WARNINGS` |
| AIOps2025 | Archive time zone determined from in-archive timestamps; every labelled incident window either falls inside an archive or is marked `natural_absent` | Incidents without telemetry → `REJECT` (`NO_TELEMETRY`) |
| RCA100 | ≥80% of cases have `root_cause_entities` resolvable to a `topology.json` service | Whole dataset B; the service-level subset is still marked `eval_tier=A-candidate` for an appendix |
| RCABench | Member listing shows per-case telemetry plus a machine-readable root-cause service | C, with the listing recorded |
| AnoMod | A per-run label file naming the injected service exists | C |
| MSDS | A root-cause component per experiment exists | C |

## Evaluation roles

- **Primary evaluation:** RCAEval RE2 + RE3 (A). It is the only A source that already backs the
  existing pipeline, and it has all three modalities on OB and TT.
- **Second benchmark:** Nezha (A after the gate) and AIOps2025 service/pod (A).
- **Natural missingness strata:** RE2-SS (no T) and RE3-SS (T absent or empty), each compared
  only with OB/TT of the same release. RCAEval RE1 (M only) is a different collection with a
  different fault set and is reported descriptively, not in inferential comparisons.
- **Auxiliary:** Cloud-OpsBench, PetShop, DejaVu, AIOps2025 node faults.
- **Never pooled for headline numbers** across datasets with different label granularity. Pooled
  tables are allowed only within one `label_granularity`, with per-dataset rows shown.

## Measured in phase 02 (2026-10-14)

Generated by `python -m rca.profile --source <id>` and `python -m rca.profile --matrix`. Each row
points at a JSON pointer in `RCA_ROOT/data/reports/profile/<source>.json`.

| Source | Planning value | Measured value | Evidence |
|---|---|---|---|
| RCAEval Zenodo | RE2 270 (+1), RE3 90, RE1 375 | RE1 375 (M only); RE2 271 incl. the `multi-source-data` duplicate (OB 91, SS 90 M L, TT 90); RE3 90 (SS: 17 M L, 13 with header-only traces) | `rcaeval-zenodo.json#/zips` |
| RCAEval time units | metrics s, logs ns, traces µs | logs `timestamp` ns (360 files); traces `startTime` µs and `startTimeMillis` ms (240 files; 13 header-only); 0 mismatching rows in 5,643,102 checked over 12 cases | `#/time_units`, `#/trace_time_check` |
| RCAEval non-service metric prefixes | `main` in RE1-OB | RE2/RE3: 22–39 per subset (Istio passthrough, GKE nodes, `frontend-external` …), kept as `infra`; RE1: none beyond the service set | `#/non_service_metric_prefixes` |
| RCAEval split feasibility | — | `cell`: 109 groups (largest 40); `physical`: 620 groups; within-grouped, within-retrieval and eval-only feasible | `#/split_feasibility` |
| Nezha anchor | `inject_timestamp`, must equal `inject_time` | `inject_time` (UTC) matches hour keys, minute file names and metric `Time`; `inject_timestamp` differs on 29/101 (24 on 2023-01-29 by about −8 h, 5 by ±60 s) | `nezha.json#/dates` |
| Nezha metric time | `TimeStamp` suspect (+2e8 s) | One 2022-08-22 file has a non-constant 2e8 s `TimeStamp` offset; 115 others agree within 60 s. Rule: use `Time` | `#/metric_time_offset` |
| Nezha gate | ≥95% with M, L, T in [t−600, t+300] | 101/101 (100%) → **pass** | `#/gate` |
| Nezha traces | Duration unit `?` | µs (40,000 spans checked) | `#/duration_unit` |
| Nezha split feasibility | eval-only and xdata only | `cell` 7 groups, `physical` 13 groups → eval-only only (and xdata once a second A adapter exists) | `#/split_feasibility` |
| AIOps2025 archive time zone | `?` | Hourly member names are UTC+8 (410 log, 390 trace members agree) | `agenticopseval.json#/AIOps2025/hourly_name_minus_utc_hours` |
| AIOps2025 coverage | 31 on archive-less dates | 358/400 windows covered by both log and trace members; 42 not (19 overlap no member at all) → natural_absent, REJECT `NO_TELEMETRY`; gate **pass** | `#/AIOps2025/gate` |
| AIOps2025 labels | service 195, pod 123, node 82 | Same; 179 list-valued `instance`; 55 multi-service with a named `service`, 73 without | `#/AIOps2025` |
| RCA100 gate | ≥80% service-resolvable | 83/103 (80.58%) → **pass**; entity kinds: apm.service 83, k8s.node 17, k8s.pod 1, not-in-topology 2 | `#/RCA100` |
| RCABench | 1,430 (paper), layout `?` | 1,422 case directories, all Train-Ticket (namespace `ts`); each has `{abnormal,normal}_{logs,traces,metrics}` Parquet and `injection.json`; injection point: single service 1,168, source/target pair 254 → gate **pass** | `rcabench-fse26.json#/gate` |
| Cloud-OpsBench | M in 170 | 754 cases (boutique 550, trainticket 204); `raw_data/metrics.csv` in 170; no traces | `cloud-opsbench.json` |
| DejaVu | `?` | 601 incidents: A1 78, A2 110, B 158, C 99, D 156 | `dejavu.json#/sets` |
| PetShop | 68 | 68 (train 20, test 48); root causes are AWS resources | `petshop.json` |
| AnoMod | `?` | 67 experiments; the fault is only in directory names, with no label file naming the service → gate **fail** | `anomod.json` |
| MSDS | `?` | Experiment start/end text files only; no per-incident root-cause component → gate **fail** | `msds.json` |
