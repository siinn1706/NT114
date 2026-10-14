# Dataset quality audit

This page covers scores, label validity, anomalies found in the data, mirror completeness and
contamination flags for the RCA datasets in the registry. Claims point to a provenance record or
generated manifest. Discovery is in [dataset_discovery.md](dataset_discovery.md), and per-file
integrity is in [dataset_provenance.md](dataset_provenance.md).

**Terms.** VERIFIED means read from the acquired files or the primary host in a recorded step.
UNVERIFIED means not checked. UNKNOWN means not measured. An anomaly label (something was wrong at
time t) is never counted as a root-cause label (component X caused it).

## Scoring

Each criterion is scored 0–5, weighted, and scaled to 100. Weights: authenticity 20%, label
validity 25%, telemetry richness 20%, independence 15%, integrity 10%, licence and usability 10%.
Hard exclusions apply before scoring: no provenance, no permission, not RCA, fabricated labels,
unresolvable corruption, prohibited private data, or duplicates presented as independent. Scores
were assigned during planning from the evidence listed in the plan's `research/dataset-catalog.md`
and were not changed by the acquisition.

| Rank | Registry id | Score | Label source | Modalities |
|---|---|---|---|---|
| A1 | `rcaeval-zenodo` | 89 | Injected fault; service and fault in the case path; `inject_time.txt` per case | metrics, logs, traces (RE1 metric-only) |
| A2 | `agenticopseval` (AIOps2025) | 87 | `AIOps2025/groundtruth.jsonl`, 400 records | metrics, logs, traces, events, alerts |
| A3 | `agenticopseval` (RCA100) | 85 | `RCA100/answer_key/*.gt.json`, 103 records | Parquet telemetry per case |
| A4 | `nezha` | 85 | `rca_data/<date>/<date>-fault_list.json`: pod, fault type, time | metrics, logs, traces |
| A5 | `openrca` | 84 | `record.csv` per system; 335 records after expert review (paper) | metrics, logs, traces |
| A6 | `rcabench-fse26` | 82 | UNVERIFIED in the archive; 1,430 validated cases per the paper | UNKNOWN |
| A7 | `anomod` | 80 | Format not parsed; injection names appear in member paths | five modalities per the paper |
| A8 | `cloud-opsbench` | 77 | `index.jsonl`: `root_cause`, `fault_object` per case | Kubernetes state, logs, metrics, tool cache |
| A9 | `petshop` | 76 | 68 `target.json` files with `root_cause.node` | metrics |
| A10 | `dejavu` | 70 | `faults.csv` per dataset (format not parsed) | metrics |
| B | `msds` | — | Root-cause granularity UNVERIFIED | metrics, logs, traces |
| B | `lo2v2` | — | Locust scenario **anomaly** labels, not root cause | logs, metrics, traces |

## Label validity: incident counts from the acquired files

[`scripts/datasets/lineage.py`](../scripts/datasets/lineage.py) reads only label files, never
telemetry. It writes one row per incident to
[`data/manifests/incidents.jsonl`](../data/manifests/incidents.jsonl) and counts in
[`data/manifests/lineage-report.json`](../data/manifests/lineage-report.json). Two consecutive runs
produced byte-identical `incidents.jsonl`.

| Lineage group | Source | Incident rows | Copies (excluded) | Independent incidents | Fault cells (max repetitions) |
|---|---|---|---|---|---|
| L1 | `rcaeval-zenodo` + `rcaeval-hf` | 1,470 | 735 | 735 | 193 (5) |
| L2+L3 | `agenticopseval` | 503 (400 AIOps2025 + 103 RCA100) | 0 | 503 | 55 (38) |
| L4 | `nezha` | 101 (56 Online Boutique, 45 Train Ticket) | 0 | 101 | 56 (3) |
| L5 | `aiops2021-upstream` (labels only) | 159 | 0 | 159 | 6 (64) |
| L9 | `cloud-opsbench` | 754 | 0 | 754 | 12 (164) |
| L10 | `petshop` | 68 | 0 | 68 | 4 (26) |
| **Total** | | **3,055** | **735** | **2,320** | |

Notes:

- The L5 rows are lineage metadata for OpenRCA. The AIOps 2021 telemetry was not acquired (owner
  decision D4). Its ground-truth CSV has **159 records**, because some fields span several lines.
  The planning figure of 165 counted physical lines.
- A fault cell is one (system, service, fault) combination. Repeated injections of one cell are
  not independent evidence. Splits for later work should be made by lineage group and system,
  never by file or repetition.
- `rcabench-fse26`, `anomod`, `dejavu` and `msds` have no parsed label format yet. `lineage.py`
  only lists label-like archive members (for example `faults.csv` in each DejaVu zip). Tar files
  and the split DejaVu raw archive are not listed.
- OpenRCA counts are not available because the archives were not acquired (Drive quota; see
  [dataset_provenance.md](dataset_provenance.md#not-acquired-register)).

## Anomalies found in the data

| Source | Finding | Evidence |
|---|---|---|
| `rcaeval-hf` | Case `re1ob_currencyservice_loss_1` has `inject_time.txt` = `16933142`. The Zenodo original has `1693314223`, so the HF value is truncated (8 of 10 digits). | `incidents.jsonl` rows for `rcaeval:re1ob_currencyservice_loss_1`; `mirror-completeness-rcaeval.json` key `same_key_different_inject_time` |
| `rcaeval-hf` | `re2tt_ts-auth-service_cpu_1` has no logs; the Zenodo case ships a 181 MB `logs.csv`. | `mirror-completeness-rcaeval.json` key `hf_missing_logs` |
| `rcaeval-hf` | Zenodo `RE3-TT/ts-route-service_f3_1/{1,2,3}` became `re3tt_ts-route-service_f3_{4,5,6}`. The `inject_time` bytes are identical, so these are the same incidents; HF folded the label `f3_1` into `f3`. | key `renamed_cases` |
| `rcaeval-zenodo`, `rcaeval-hf` | 8 RE3 Sock Shop cases carry a `root_cause.txt` in both copies. The Zenodo `RE3-SS.zip` has them at `RE3-SS/{carts_f1,carts_f3,front-end_f1,front-end_f2}/{1,2}/root_cause.txt`. Each file holds a log line from the root-cause service, so it is a label artefact and must never be read as telemetry. | `RE3-SS.zip` member list; key `hf_root_cause_txt` (not listed under `files_only_on_hf_by_name`) |
| `rcaeval-zenodo` | 13 RE3 Sock Shop cases have a 116-byte, header-only `traces.csv`. The traces are absent in both copies. | key `zenodo_header_only_traces_absent_on_hf` |
| `nezha` | The README links `2022-01-29-fault_list`, but the data directories are dated `2023-01-29`. | [`data/provenance/nezha.json`](../data/provenance/nezha.json) `known_limitations` |
| `dejavu` | `D.zip` contains `.ipynb_checkpoints/faults-checkpoint.csv` next to `D/faults.csv`. The checkpoint copy is not a label source. | `lineage-report.json` key `label_candidates.dejavu` |
| `aiops2020-upstream` | The mirror's `sha256sum.txt` lists `*_lock.zip` names that are not in the repository. For example, the stored `2020_05_22.zip` hashes to `f0889e…`, while the list gives `218678d7…` for `2020_05_22_lock.zip`. It is not a usable publisher hash. | [`data/provenance/_aiops-upstream-file-metadata-20261014.json`](../data/provenance/_aiops-upstream-file-metadata-20261014.json) |
| `nezha` | On 2023-01-29, `inject_timestamp` is about 8 h earlier than `inject_time` for 24 of 28 incidents (−28,710 to −29,303 s); 5 more incidents differ by ±60 s. The hour keys, the minute file names and the metric `Time` strings agree with `inject_time`, so `inject_time` (UTC) is the anchor. | [`data/reports/profile/nezha.json`](../data/reports/profile/nezha.json) `dates.*.inject_timestamp_minus_inject_time_s` |
| `nezha` | One 2022-08-22 metric file has a `TimeStamp` column offset by about 2×10⁸ s, and not by a constant amount; the other 115 files agree with `Time` within 60 s. Metric time comes from `Time`. | `nezha.json` `metric_time_offset` |
| `nezha` | Logs and traces exist only in bursts of three minute files per injection; each file holds rows from 41 s before to 20 s after the minute in its name, so a burst covers about [t − 95 s, t + 85 s]. Metrics are continuous. A 10-minute pre-anchor log/trace baseline therefore holds the incident's own ~95 s plus, for 86 of 101 incidents, an earlier injection's fault burst (`BASELINE_CONTAMINATED`). | `rca_data/<date>/log/` listing; minute-file time spans |
| `nezha` | `2023-01-29/log/10_06_log.csv` data row 629 holds a complete row followed by the tail of another row (10 fields, header 8): a torn write. It is the only malformed row in 1,031 CSV files. The row is dropped and reported (`PARSE_ERROR`, warn) in the 5 incidents that read the file. | `tests/test_realdata_nezha.py` |
| `nezha` | 124 Train Ticket ERROR log rows (2023-01-29, travel/travel2/preserve services) carry the overflow sentinel `-6795364578871345152` in `TimeUnixNano`. Their `Timestamp` column is UTC (the UTC+8 time inside each message agrees), so the time is taken from it (`TS_COLUMN_OFFSET`, info). Dropping them would remove fault-period error logs. | `tests/test_realdata_nezha.py` |
| `agenticopseval` | AIOps2025 hourly member names are in UTC+8, while the timestamps inside the members are UTC. 42 of 400 labelled windows lack log or trace coverage (19 overlap no member at all). | `agenticopseval.json` `AIOps2025.gate` |
| `agenticopseval` | AIOps2025 `input.json` descriptions are 5 templates filled with exactly the ground-truth `start_time` and `end_time` (400/400). The window length identifies the fault type: `io fault` is always 5 min (28/28) and `pod kill` 0 min (15/15); MI(window minutes; fault type) = 1.04 bits, permutation p < 0.001. The visible record therefore carries neither the description nor the end time. | plan design `adapter-contracts.md` §3.3 |
| `agenticopseval` | RCA100 `task.json` `alert_trans_id` (also inside `prompt_text`) is the suffix of the answer-key `case_id`, a join key to the label. In 10 cases, all with root `inventory`, alert rule text contains `/sandbox/chaosblade/module/http/*`. `inventory` is the root in 55 of 103 cases. | plan design `adapter-contracts.md` §3.4 |
| `rcaeval-zenodo` | In 8 incidents the metrics CSVs end in rows with an empty `time` (for example RE2-OB `checkoutservice_mem/2`: 258 trailing rows). These rows are dropped and counted as `PARSE_ERROR` (warn). | `data/canonical/v1/rcaeval/eval_only/quality.jsonl` |
| `rcaeval-zenodo` | RE2-OB traces name the frontend `frontendservice`, while metrics and logs say `frontend` (91 incidents). A few OB and SS clusters also expose containers of the other benchmark (`front-end`, `payment`, `shipping` in OB; `paymentservice`, `shippingservice` in SS). The reviewed aliases are in [`configs/service_aliases.yaml`](../configs/service_aliases.yaml). | `service_map.json`, alias file |
| `rcaeval-hf` | HF log timestamps are whole seconds (rounded), and HF drops `"` and `'` at the edges of log messages (raw CSV `..."""` becomes `...`). The canonical build keeps the parsed message. | `tests/test_realdata_samples.py` (`hf_log_quoting`) |
| `rcabench-fse26` | 1,422 case directories against 1,430 in the paper; the data does not explain the 8. All cases are Train-Ticket (namespace `ts`). 254 injections name a source/target service pair, and some name a non-service source such as `mysql`. | `rcabench-fse26.json` `gate` |
| `rcabench-fse26` | The Zenodo creator field is a placeholder. Authenticity rests on the arXiv 2510.04711 page linking the DOI. | [`data/provenance/rcabench-fse26.json`](../data/provenance/rcabench-fse26.json) |

## Mirror completeness (owner decision D7)

**RCAEval, HF `@afeacb11` against Zenodo 14590730.** Report:
[`data/manifests/mirror-completeness-rcaeval.json`](../data/manifests/mirror-completeness-rcaeval.json).

- 735 cases on each side. 734 HF cases map to Zenodo cases by identical `inject_time.txt` bytes.
  The remaining case shares a key but has the truncated time shown above. No HF case lacks a
  Zenodo counterpart.
- All five difference classes found in planning were reproduced on the local copies: 3 renamed
  cases, 1 case missing logs, 13 header-only trace files, 8 `root_cause.txt` files (present in the Zenodo `RE3-SS.zip` too, so not an HF addition), and
  omitted auxiliary files (for example `data.csv` ×374, `logts.csv` ×270,
  `metrics_postprocess.log` ×360). One new class was found: the truncated `inject_time`.
- 14 cases differ in modality set between the copies.
- **Verdict:** HF is a derived, incomplete copy. Zenodo is canonical. HF rows are recorded with
  `copy_of: rcaeval-zenodo` and are never counted as independent.

**Cloud-OpsBench, HF `@1a02e543` against GitHub `@ea05dafb`.** Report:
[`data/manifests/mirror-completeness-cloud-opsbench.json`](../data/manifests/mirror-completeness-cloud-opsbench.json).

- HF has 27,110 files; GitHub has 27,195 blobs; 27,106 paths are common.
- 27,105 of the 27,106 common paths have equal git blob IDs. This includes the 50 LFS files, whose
  local content was hashed. The single difference is `README.md`.
- 4 files exist only on HF (`.gitattributes`, `index.jsonl`, `manifest.json`, `release.json`).
  89 exist only on GitHub, mostly agent code under `agents/`.
- **Verdict:** the HF release contains the benchmark data identically. It omits the agent code
  and adds release metadata.

**AIOps2025, aiops.cn project 110 against project 107.** The `groundtruth.jsonl` and `input.json`
blob IDs are identical, so project 107 holds the same 400 incidents. All 18 AIOps2025 archives
match the publisher's `checksums.md5`, in addition to their LFS SHA-256 anchors. See
`lineage-report.json` key `agenticopseval`.

## Contamination and bias flags

- **Label leakage through paths.** RCAEval case directories encode service and fault, Nezha fault
  lists sit next to the telemetry, and RCA100 ships `answer_key/` beside the cases. The field
  `label_in_path` in `incidents.jsonl` flags this.
- **Observability bias.** OpenRCA removed records with missing telemetry, which biases it toward
  full observability: the variable this study perturbs. RCAEval Sock Shop has no traces, and 13
  RE3 Sock Shop cases ship header-only trace files.
- **Pre-training exposure.** First public dates include RCAEval Zenodo 2024-12-17 (v0.0.1),
  OpenRCA Drive files 2025-02-23 and AIOps2025 on GitLab in 2026. Older sets (Nezha 2023,
  DejaVu 2022) are more likely to be in model pre-training data.
- **Shared systems across sources.** Online Boutique appears in RCAEval, AIOps2025, Nezha,
  Cloud-OpsBench. Train Ticket appears in RCAEval, Nezha, Cloud-OpsBench, RCABench (all 1,422
  cases) and AnoMod. The `system` field supports holding out whole systems.
- **Licences that restrict use.** AgenticOpsEval (BY-NC / BY-NC-SA) and OpenRCA (BY-NC with
  ShareAlike wording) allow local research use only.

## Canonical RCAEval build

The build `rcaeval-9bfc8d21733f` (`python -m rca.prep normalize --dataset rcaeval`, 2026-10-14) converted
all 736 case directories with 0 adapter exceptions and 0 service-identity collisions:

| State | Incidents | Cause |
|---|---|---|
| ACCEPT | 703 | |
| ACCEPT_WITH_WARNINGS | 32 | non-finite metric values (21), dropped empty-time metric rows (8), orphan spans (2), low coverage (1) |
| REJECT | 1 | `RE2-OB/checkoutservice_cpu/multi-source-data`, duplicate of `checkoutservice_cpu/1` |

Info-level findings recorded per incident: missing log level (270), header-only trace files (13),
`root_cause.txt` label artefacts (8), constant metrics (50), non-finite values (541), orphan spans (154).
The per-incident list is `data/canonical/v1/rcaeval/eval_only/quality.jsonl`; the summary is
`data/reports/quality-rcaeval.json`, and the cross-dataset audit is `data/reports/audit-<build_id>.json`.
Rules and states are defined in [data_contract.md](data_contract.md).

The current build is `rcaeval-2f4bf056cb8a` (adapter 1.0.1, 2026-10-14), with the same counts. It
fixes system-scoped identity in the 4 incidents whose cluster also ran the other demo
(`rcaeval.4303ec727622942a`, `rcaeval.d5bb2ac1b3c6bb37`, `rcaeval.4d62cb4318958396`: OB with Sock
Shop containers; `rcaeval.76e86a2d6f0e1dc1`: Sock Shop with OB containers). Before the fix their
candidate sets listed the other system's containers, and in the Sock Shop incident the OB
`frontend` merged with Sock Shop `front-end`. Now the foreign containers are infra (see the identity
table below), the 4 candidate sets hold only their own system's services, and each root is still a
candidate. The other 731 incidents take the unchanged code path; their condition applicability and
non-root trace targets are identical to the previous build, and every split keeps the same
assignments (re-pinned to the new build). The 4 incidents were excluded from primary evaluation
until targeted real-data regression tests (`tests/test_realdata_identity.py`: system-scoped
candidates and identity, ground truth matching the case path, clean deterministic evidence with no
foreign container, no label leakage) passed on this build; the owner then lifted the exclusion
(entries kept with `status: lifted` in `configs/eval_exclusions.yaml`). All 735 accepted RCAEval
records are evaluation-eligible.

## Canonical Nezha build

The build `nezha-ea30424eba55` (adapter 1.0.3, 2026-10-14) converted all 101 incidents (56 Online
Boutique, 45 Train Ticket) with 0 adapter exceptions; `validate` reports 0 invariant errors and a
rebuild is a no-op with the same `dataset_digest`. Every label is valid and tier A, and every root
is a candidate. All 101 are ACCEPT_WITH_WARNINGS, each for measured reasons: an earlier injection
inside the evidence window (86), log/trace coverage below 0.5 because of the bursts above (66),
a window clipped at a stream edge (16), parse errors (10: 5 torn-row, 5 non-JSON log rows) and
less than 60 s of data before the anchor (4; these 4 are excluded from every missingness
condition). An earlier build (adapter 1.0.0) rejected 96 incidents because the anchor record did
not match the schema and quarantined 5 on the torn row; the fixture tests then checked neither
states nor schema validity, which they now do.

Because of the bursts, Nezha log/trace evidence is compared only inside the contiguous stretch of
rows (gaps ≤ 30 s) holding the anchor, with rates over the seconds actually covered
(`configs/prep.yaml` `evidence.log_trace_segment_gap_s`). On the real build all 101 evidence texts
build, the leakage scan finds 0 hits, and 8 incidents have under 30 s of pre-anchor data and are
stated as having no pre-incident baseline. Metric evidence keeps the fixed windows.

## Canonical AIOps2025 build

The build `aiops2025-40efa9b2d22f` (adapter 1.0.1, 2026-10-14) converted all 400 labelled incidents
from the 18 extracted day archives with 0 adapter exceptions and 0 identity collisions; `validate`
reports 0 invariant errors and a rebuild is a no-op with the same `dataset_digest`. All labels are
valid. Tiers follow owner decision V3: 245 single-service A (122 service, 123 pod), 73 A
`set-scoring-only` (multi-entity network faults with an empty `service` field), 82 B (node faults).
States: 381 ACCEPT, 19 ACCEPT_WITH_WARNINGS (low log/trace/metric coverage 11, orphan spans above
5% 7, window clipped 4). Daily metric files cover every window, so no incident is rejected for
lack of telemetry; hourly log/trace gaps leave logs `natural_absent` in 16 incidents and traces
`natural_absent` or empty in 39. Phase 02 counted 42 windows without both log and trace members
under its narrower window; 38 of them are among the build's 39, the other 4 reach a neighbouring
hour in the wider stored window. Natural absence is not associated with the fault type
(permutation p = 0.71 logs, 0.80 traces).

Leakage handling: the window is fixed around `start_time` ([t − 1200 s, t + 600 s]); `end_time`,
`fault_description`, `key_*` and the `input.json` text stay eval-only; the campaign day is
associated with the fault type (MI 0.91 bits, p < 0.001), so every incident shares one
`dataset_subset` and splits must group by day. Label-perturbation tests keep every visible file
byte-identical (they caught, and now guard, label entity names reaching `service_map.json`).
Evidence text for all 400 incidents matches 9 label-description strings, each verbatim in that
incident's own log rows (`emailservice` in DNS errors, the frontend error "Can't access cart
storage"); these are telemetry, not label flow. In 5 incidents the log export stops before the
anchor because an hourly log file is missing from the source archive.

## Canonical RCA100 build

The build `rca100-5cd15b7a1d8f` (adapter 1.0.1) converted all 103 cases with 0 exceptions;
`validate` reports 0 invariant errors and a rebuild is a no-op. Tiers: 86 A (83 service roots, 3
pod roots mapped to their deployment), 17 B (node roots), matching the phase-02 gate. States:
9 ACCEPT, 94 ACCEPT_WITH_WARNINGS, all for low log/trace coverage. The source exports logs and
traces in 300 s pages with a per-page row cap, so a page keeps about 20 s of data (median); in the
120 s after the alert the median covered time is 0 s. The anchor is the first firing alert, the
window [t − 900 s, t + 120 s]; the answer-key window, whose length is associated with the fault
id, is not used. Two metric groups exported only for one fault (`apm.metric.exception` in the 4
nullPointerException cases, `k8s.pod/pod_restart_count` in 2 pod-restart cases) are dropped by a
label-free rule (keep pairs exported in at least half the cases). `inventory` is the root of 56 of
86 tier-A cases: a class imbalance kept as labelled, so results must be compared with the
majority-class baseline (0.651 top-1) and the alert-entity baseline (0.372).

The 103 tasks are not 103 independent injections. 28 tasks in 11 groups were cut from one fault
injection each: within a group the `events.parquet` export is byte-identical (or the logs export
is), the first alert lies within 75 s, and the fault id and root are the same; the tasks differ in
the alert they start from and in their log/trace pages. That leaves 86 independent injections. The
adapter (1.0.1) records each group as a label-free `group.group_id` (`rca100-injection:<first
task>`); the audit counts the pairs as explained duplicates and splits keep a group in one part.
All 103 tasks stay in the store as in the source benchmark. Owner decision (2026-10-14): the 86
injections are the statistical units (equal injection weight, cluster bootstrap by injection, and
a one-representative-per-injection sensitivity analysis); `data/reports/eval-units-rca100.json`
carries the unit, weight and representative of every task. With equal injection weight the
majority-class baseline scores 41/70 = 0.586 and the alert-entity baseline 0.374 on the 70 tier-A
injections.

The current build is `rca100-430dfff49e51` (adapter 1.0.2; a forced rebuild reproduces the same
`dataset_digest`). It maps four `checkout` pods whose pod-template hash has 7 characters, which the
pod rule had missed (identity table below); counts and states are unchanged.

## Service identity: alias and rule evidence (audit 2026-10-14)

Every non-trivial identity decision, with the telemetry that supports it. "Collision check" is the
scan of each build's `visible/service_map.json` for service ids reached from two or more raw
non-pod spellings: across all four datasets only two such ids exist, `frontend` (RCAEval OB) and
`rediscart` (AIOps2025), both intended merges listed below. `tests/test_realdata_identity.py` pins
this: the six alias entries resolve only in their own system, the same raw spelling keeps its own
meaning in the other system (`front-end` is `frontend` in Sock Shop), no infra id is ever a
candidate, and the set of multi-spelling ids equals the two intended merges. Every alias is
supported by telemetry evidence below; per the owner's rule (approve only evidence-supported,
system-scoped, collision-tested mappings) they await the owner's final review, and the
`reviewed_by` field in the alias file is left unchanged because that file is part of the build hash.
The AIOps2025 Redis and TiDB rules meet the condition the owner set. Remaining ambiguity: the
foreign-container rule is a measured threshold (own ≤ 5 %, other ≥ 90 %), not topology; a future
release with a shared service name used by both demos in normal operation would need review.

| Raw identifier | Canonical id | Dataset / system | Supporting evidence | Collision check | Status |
|---|---|---|---|---|---|
| `frontendservice` | `frontend` | RCAEval / online-boutique | Jaeger serviceName in all 91 RE2-OB incidents; its spans call productcatalog, currency, recommendation and checkout; no trace service `frontend` exists there; metrics and logs say `frontend` | `frontend` ← {`frontend`, `frontendservice`} only | alias, owner to confirm |
| `front-end`, `payment`, `shipping` | `sockshopfrontend`, `sockshoppayment`, `sockshopshipping` (infra) | RCAEval / online-boutique | Present in 3 OB incidents (RE3-OB ×2, RE1-OB ×1) together with the whole Sock Shop container set, cAdvisor metrics only; each name occurs in ≤ 1.3 % of OB incidents and 100 % of Sock Shop incidents | distinct ids, never candidates; OB `frontend`, `payment`, `shipping` untouched | alias, owner to confirm |
| `paymentservice`, `shippingservice` | `onlineboutiquepayment`, `onlineboutiqueshipping` (infra) | RCAEval / sock-shop | Present in 1 RE3-SS incident with the whole OB container set | distinct ids, never candidates | alias, owner to confirm |
| other system's containers (12 Sock Shop names in OB: carts, carts-db, catalogue, catalogue-db, orders, orders-db, queue-master, rabbitmq, rabbitmq-exporter, session-db, user, user-db; 9 OB names in Sock Shop: adservice, cartservice, checkoutservice, currencyservice, emailservice, frontend, productcatalogservice, recommendationservice, redis) | `<othersystem><name>` (infra), rule `other-system-container` | RCAEval | Adapter 1.0.1 rule: a metric-header entity found in ≤ 5 % of its own system's incidents and ≥ 90 % of the other system's. Measured shares are ≤ 1.3 % and 100 %, with no name between 10 % and 30 % | Sock Shop `front-end` stays `frontend`; OB `frontend` in the Sock Shop incident is now `onlineboutiquefrontend` | rule, verified on the rebuild |
| `redis` (Jaeger process) | `rediscart` | AIOps2025 / hipstershop | All 5,953,773 spans of the process across the 390 trace files carry `peer.service=redis-cart:6379`; no other process maps to `rediscart` | `rediscart` ← {`redis-cart`, `redis`} only | rule, confirmed by source evidence |
| `<ip>:10080` (3 IPs) | `tidbtidb` | AIOps2025 | Port 10080 occurs only under `object_type: tidb` (13 KPIs) | — | rule, confirmed by source evidence |
| `<ip>:20180` (3 IPs) | `tidbtikv` | AIOps2025 | Port 20180 occurs under `tikv` (15 KPIs) and on the `block_cache_size` rows labelled `object_type: tidb` (25,633 rows); block cache is a TiKV metric, so the port, not the label, decides | — | rule, confirmed by source evidence |
| `pd`, `tidb`, `tikv` (rows with null instance), `tidb-pd-0` | `tidbpd`, `tidbtidb`, `tidbtikv` | AIOps2025 | Object type of the row; `tidb-pd-0` by the StatefulSet pod rule. TiKV `io_util` rows keyed by node IP port 9100 (node exporter) map to the node, not a service | — | rule, confirmed by source evidence |
| `<pod> (deleted)` | base pod's service | AIOps2025 | Only 3 APM object ids carry the suffix (cartservice-2, productcatalogservice-1, productcatalogservice-2), and each base pod also occurs. Stored `entity_raw` keeps the suffix (e.g. `aiops2025.6f98d4e1fce1eed1`, `aiops2025.86f7c40dea4d05e4`, 22 rows each); only the service-map key is stripped | — | raw pod identity preserved |
| `example-ant-*` (39 CronJob pods) | none | AIOps2025 | Not a deployment of the demo | — | unmapped, never candidates |
| `checkout-5489989-*` (4 pods) | `checkout` | RCA100 / otel-demo | 7-character pod-template hash; the pod rule required 8–10 characters, so the pods were unmapped (3) or infra (1), losing 102 metric and 11,740 log rows in 2 incidents (`rca100.9fbfe46db86017ff`, `rca100.e3d9b46aef9f46e8`; neither has root `checkout`, and `checkout` was already a candidate). Short hashes are now accepted when they use Kubernetes' vowel-free encode alphabet; no raw name of another dataset changes match | — | fixed in RCA100 adapter 1.0.2 |
| 30 non-demo deployments (coredns, prometheus, mysql, valkey-cart, chaosblade-operator, …) | none (infra) | RCA100 | Not services of the demo | — | rule |

Nezha maps only by the pod rule (103 pods) and has no collisions.

A dataset-level tier for every source, with the phase-02 gate outcomes, is in
`data/reports/compatibility-matrix.json` (`python -m rca.profile --matrix`).
