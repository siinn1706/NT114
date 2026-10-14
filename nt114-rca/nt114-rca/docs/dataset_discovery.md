# Dataset discovery

Scope: public AIOps root-cause-analysis (RCA) datasets for the study *Overconfident LLM Root Cause
Diagnosis Under Missing Observability*. This page records where we searched, what we found and the
A/B/C decision for each candidate. It covers discovery only. Per-file integrity is in
[dataset_provenance.md](dataset_provenance.md) and scores are in
[dataset_quality_audit.md](dataset_quality_audit.md).

The machine-readable sources of truth are:

- the registry [`scripts/datasets/sources.json`](../scripts/datasets/sources.json), with pinned
  revisions, categories and lineage groups;
- the catalog [`data/manifests/dataset_catalog.json`](../data/manifests/dataset_catalog.json), with one
  state per source;
- one provenance record per source in [`data/provenance/<id>.json`](../data/provenance/).

The planning evidence (search logs, API dumps, licence texts and their SHA-256 list) lives in the
plan folder `plans/261013-2300-aiops-rca-dataset-acquisition/research/` of the outer repository.

## Search channels

| Date | Channel | Targets | Outcome |
|---|---|---|---|
| 2026-10-13 | GitHub API | RCAEval, Nezha, rca_baselines, GAIA, DejaVu, TraceRCA, AIOps-Challenge-2020-Data, OpenRCA, PetShop, Eadro, ITBench, LogHub, CIRCA, PyRCA, train-ticket, AnoMod, Cloud-OpsBench | Licences, commits, trees and READMEs captured |
| 2026-10-13 | Hugging Face Hub | "root cause analysis", "microservice", "aiops", "OpenRCA", "RCAEval", "trainticket", "telemetry fault injection"; author `Lemma-RCA-NEC`; paper search | Official RCAEval, LEMMA and Cloud-OpsBench repositories plus mirrors; the FSE'26 benchmark |
| 2026-10-13 | Figshare API | 31048672, 31925976 | RCAEval v2 and TORAI metadata |
| 2026-10-13 | Zenodo API | 14590730, 14504481, 17105974, 18342898, 6955909, 3549604, 7615394, 20516735 | First pass: HTTP 504. Second pass: all reachable |
| 2026-10-13 | aiops.cn GitLab API | Public project list (71); projects 65, 68, 83, 107, 110 | AgenticOpsEval and the upstream AIOps 2020/2021/2025 releases |
| 2026-10-13 | Web search, arXiv, ICLR proceedings | Nezha, LEMMA-RCA, OpenRCA origin, Eadro, AnoMod/LO2, 2607.13548, 2510.04711 | New families: AgenticOpsEval, Cloud-OpsBench, AnoMod, RCABench |
| 2026-10-13 | Google Drive folder listing | OpenRCA folder `1wGiEnu4OkWrjPxfx5ZTROnU37-5UDoPM` | 4 files with IDs and Drive-rounded sizes |
| 2026-10-14 | `acquire.py check-metadata` per source | All 18 registry sources | File lists pinned in [`data/manifests/filelists/`](../data/manifests/filelists/); drift summary in [`data/provenance/_metadata-recheck-20261014.json`](../data/provenance/_metadata-recheck-20261014.json) |
| 2026-10-14 | OpenAlex works search, Zenodo records search (saturation round) | "root cause analysis microservice dataset benchmark" from 2024 (1,893 hits, top 40 read); "LO2 microservice API anomaly"; "\"root cause\" microservice dataset" | One new family: LO2 v2 (Zenodo 18937117). One rejection: DOI 10.25439/rmt.33274566 (a thesis, not a dataset) |
| 2026-10-14 | `lemmarca.info`, `lemma-rca.github.io` | LEMMA-RCA licence notice | `lemmarca.info` has expired (parking page). The GitHub Pages site states CC BY-ND 4.0. Saved under [`data/provenance/evidence/`](../data/provenance/evidence/) |

No paid, gated or login-only portal was queried (Tianchi, CCF registration pages).

## Saturation

The last channels returned only mirrors of known families, plus one new family per channel
(Cloud-OpsBench, AgenticOpsEval, RCABench and, in the 2026-10-14 round, LO2 v2). Saturation is
not proven. A new family is added only when it has a primary download link and a licence.

Still pending discovery, because no primary download link was found: **TrainTicketTrace**,
**TraceRCA** data and the **AIOps Challenge 2022** raw release.

## Decisions

The scoring rubric (authenticity 20%, label validity 25%, telemetry 20%, independence 15%,
integrity 10%, licence 10%) and the hard exclusions are applied in
[dataset_quality_audit.md](dataset_quality_audit.md). Anomaly labels are never counted as
root-cause labels.

### Category A — gold RCA labels, approved for acquisition

| Registry id | Dataset | Publication | Licence | Lineage group |
|---|---|---|---|---|
| `rcaeval-zenodo` | RCAEval RE1–RE3, Zenodo 14590730 (canonical originals) | WWW'25 Companion, doi:10.1145/3701716.3715290 | CC-BY-4.0 | L1 |
| `rcaeval-hf` | RCAEval Hugging Face copy `@afeacb11` (derived working copy) | as above | MIT (HF card) | L1, `copy_of` rcaeval-zenodo |
| `agenticopseval` | AgenticOpsEval: AIOps2025 (400 incidents) and RCA100 (103 tasks) | arXiv 2606.29193 | CC BY-NC 4.0 / CC BY-NC-SA 4.0 | L2+L3 |
| `nezha` | Nezha (Online Boutique, Train Ticket) | ESEC/FSE 2023 | MIT | L4 |
| `openrca` | OpenRCA Bank / Market / Telecom (conditional, owner decision D2) | ICLR 2025 | CC BY-NC 4.0 with ShareAlike wording | L5 |
| `rcabench-fse26` | RCABench fault-propagation benchmark | arXiv 2510.04711 (FSE'26) | CC-BY-4.0 | L11 |
| `anomod` | AnoMod (SocialNetwork, TrainTicket) | MSR 2026, doi:10.1145/3793302.3793324 | CC-BY-4.0 | L12 |
| `cloud-opsbench` | Cloud-OpsBench v1.0.0 | UNKNOWN | MIT | L9 |
| `petshop` | PetShop (metric-only) | amazon-science | CC-BY-4.0 (data) | L10 |
| `dejavu` | DejaVu A1/A2/B/C/D (metric-only) | ESEC/FSE 2022, doi:10.1145/3540250.3549092 | CC-BY-4.0 | L13 |

### Category B — auxiliary or conditional

| Registry id | Dataset | Why B |
|---|---|---|
| `msds` | MSDS (OpenStack) | Root-cause label granularity is unverified, so it is not used as gold |
| `gaia` | GAIA MicroSS | Licence conflict (`LICENSE` says GPL-2.0, README says Apache-2.0); needs the owner's acknowledgement |
| `eadro` | Eadro (ICSE'23) | Zenodo record has no licence |
| `lemma-rca-product-review`, `lemma-rca-cloud-computing` | LEMMA-RCA Original | Deferred (owner decision D3): licence conflict and about 10 incidents for 86.6 GB |
| `aiops2020-upstream`, `aiops2021-upstream` | AIOps Challenge 2020 / 2021 (aiops.cn mirrors) | Lineage references for OpenRCA (owner decision D4): label files only |
| `lo2v2` | LO2 v2 (OAuth2 microservice) | Anomaly labels, not root-cause labels; about 70 GB; awaiting an owner decision |

### Category C — rejected, or not acquired because it duplicates or derives from a kept source

| Candidate | Reason |
|---|---|
| HF `Shra9701/RCAEval` | Byte-identical to the official HF RCAEval (2,080 of 2,080 hashes) |
| HF `cdreetz/OpenRCA`, `shaowenchen/openrca` | Unofficial re-uploads without a licence field; the official Drive release is the source |
| HF `lechengzheng/AIOps` | Placeholder (2 files, 2,340 B) |
| aiops.cn `aiops-nankai/*` trace mirrors, `data/gaia-dataset` | Mirrors that cite their upstream |
| aiops.cn project 107 `aiopschallenge2025` | Same 400 incidents as AIOps2025: identical `groundtruth.jsonl` and `input.json` blob IDs, re-confirmed on the acquired copy (see [`lineage-report.json`](../data/manifests/lineage-report.json)) |
| RCAEval Zenodo v0.0.1 (14504481) | Superseded by 14590730 |
| RCAEval Figshare v2, TORAI | Re-packaging or derived from RE2 |
| LEMMA `*_Preprocessed` | Derived artefacts |
| LO2 v1 (Zenodo 14938118) | Superseded by LO2 v2 |
| arXiv 2607.13548 | No new dataset |
| Synthetic or instruction-tuning HF sets, PyRCA/CIRCA simulators | No telemetry-grounded RCA labels |
| LogHub | Log anomaly labels, not root causes |
| ITBench | Live framework, not a static dataset |
| DOI 10.25439/rmt.33274566 | PhD thesis marked "All rights reserved"; not a dataset |

The current state of every A and B source, and the exact reason for each one not acquired, is in
[dataset_provenance.md](dataset_provenance.md#not-acquired-register).
