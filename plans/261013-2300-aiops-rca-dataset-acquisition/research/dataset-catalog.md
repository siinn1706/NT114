# Dataset discovery catalog and ranked shortlist

Revision 2 (2026-10-13 23:32, Asia/Saigon). It applies the owner decisions and the second
verification pass, in which Zenodo was reachable again.

Evidence is in [evidence/](evidence/), hashed in [evidence/SHA256SUMS.txt](evidence/SHA256SUMS.txt).
Large API dumps that can be regenerated are listed with their hashes in
[evidence/regenerable-evidence.txt](evidence/regenerable-evidence.txt).

- **VERIFIED**: read from the primary host in this attempt.
- **UNVERIFIED**: comes from a secondary source, or has not been checked.
- **UNKNOWN**: not measured.
- **Bytes**: the publisher-declared size of the artefact as downloaded (compressed), unless noted.

## Integrity levels (used everywhere in this plan)

| Level | Meaning |
|---|---|
| `publisher-hash` | The local file matches a hash published by the dataset owner or host for that exact artefact: Zenodo/Figshare MD5, HF LFS SHA-256, git object ID at a pinned commit, or a shipped `checksums.md5`/`manifest.json`. |
| `publisher-size` | Only a declared byte size or row count is available, for example RCA100 `summary.json` or Drive-rounded sizes. |
| `local-only` | No publisher hash exists. The local SHA-256 is computed at retrieval and proves later integrity, not authenticity. |

## Scoring rubric

Each criterion is scored 0–5 and weighted: authenticity 20%, label validity 25%, telemetry 20%,
independence 15%, integrity 10% and licence/usability 10%. Hard exclusions apply first.

## Category A — gold RCA, approved for acquisition

| Rank | Dataset | Score | Bytes | Licence | Integrity level |
|---|---|---|---|---|---|
| A1 | RCAEval, Zenodo 14590730 (canonical originals) | 89 | 5,161,758,943 | CC-BY-4.0 (Zenodo) | publisher-hash (MD5 ×9) |
| A1′ | RCAEval, HF `afeacb11` (derived Parquet working copy) | — | 3,442,007,684 | MIT (HF card) | publisher-hash (LFS SHA-256 / blob IDs) |
| A2 | AgenticOpsEval / AIOps2025 | 87 | 9,741,961,087 (18 archives) | CC BY-NC 4.0 | publisher-hash (`checksums.md5`) |
| A3 | AgenticOpsEval / RCA100 v1.1 | 85 | 3,682,521,875 declared, 831 files | CC BY-NC-SA 4.0 (LICENSE read) | publisher-size + local-only |
| A4 | Nezha (FSE'23) | 85 | 3,042,817,082 blob bytes | MIT | publisher-hash (git objects) |
| A5 | OpenRCA (ICLR'25), conditional, verified below | 84 | ≈ 8.2 G (Drive-rounded: 2.6 + 2.7 + 2.9) + 24,349 | CC BY-NC 4.0 per paper; SA wording, so treated as BY-NC-SA | local-only (+ publisher-size) |
| A6 | FSE'26 fault-propagation benchmark (RCABench) | 82 | 13,446,969,567 | CC-BY-4.0 | publisher-hash (MD5 ×3) |
| A7 | AnoMod (MSR'26) | 80 | 201,917,396 | CC-BY-4.0 | publisher-hash (MD5) |
| A8 | Cloud-OpsBench v1.0.0 | 77 | 3,840,845,678 | MIT | publisher-hash (`manifest.json` SHA-256 + HF) |
| A9 | PetShop (CLeaR'24), metric-only | 76 | 18,609,770 (`dataset/`) | CC-BY-4.0 (data) | publisher-hash (git objects) |
| A10 | DejaVu A1/A2/B/C/D (FSE'22), metric-only | 70 | 4,545,204,660 | CC-BY-4.0 | publisher-hash (MD5 ×12) |

### A1 RCAEval

- Publication: WWW 2025 Companion, DOI 10.1145/3701716.3715290, arXiv 2412.17015.
- The Zenodo concept DOI is 10.5281/zenodo.14504480 and has two versions: 14504481 (v0.0.1,
  2024-12-17, 5,136,300,342 B) and **14590730**, the latest and the one cited, with
  9 zips totalling 5,161,758,943 B.
- **Licence differs by host.** Zenodo says CC-BY-4.0, while HF, Figshare and GitHub say MIT. Both
  are permissive; both are recorded and the attribution requirement of CC-BY applies.
- Faults are injected. Labels are the service and fault from the case path and `inject_time.txt`.
- **Mirror completeness, VERIFIED by remote central-directory comparison**
  ([evidence/rcaeval-zenodo-vs-hf-comparison.txt](evidence/rcaeval-zenodo-vs-hf-comparison.txt)).
  The HF copy is **not** a complete copy of the Zenodo originals:
  1. 732 of 735 case names match. Zenodo `RE3-TT/ts-route-service_f3_1/{1,2,3}` became HF
     `re3tt_ts-route-service_f3_{4,5,6}`. The `inject_time.txt` CRC32 values are identical
     (69008df7, d1ddf769, 9554f34a), so these are the same incidents. HF folded the fault label
     `f3_1` into `f3`.
  2. `re2tt_ts-auth-service_cpu_1` has a 181,151,448-byte `logs.csv` on Zenodo and no logs file
     on HF. This is a real data loss in the HF copy.
  3. Thirteen RE3-SS cases carry a 116-byte, header-only `traces.csv` on Zenodo (identical CRC
     566ce7f8) and none on HF. The traces are absent in both copies; only the representation
     differs.
  4. HF adds 8 `root_cause.txt` files (RE3-SS) that do not exist on Zenodo. These are labels added
     after release, and their provenance is UNKNOWN.
  5. HF omits the auxiliary originals: `logts.csv`, `tracets_err.csv`, `tracets_lat.csv`,
     `cluster_info.json`, `pod-node-*.csv`, `simple_*`, `metrics_postprocess.log` and `metrics.png`.
- Decision: Zenodo is the canonical raw source, and HF is a derived working copy flagged with
  these five differences.

### A2–A3 AgenticOpsEval

- arXiv 2606.29193 (preprint). aiops.cn GitLab project 110 at commit `69cf3643…`.
- The raw endpoint `/-/raw/<sha>/<path>` serves LFS content with HTTP Range (206 verified). Cook
  downloads per file, which avoids keeping a duplicate `.git/lfs` store.
- AIOps2025: 18 archives measured at 9,741,961,087 B in total (the README's "11.9 GB" is
  presumably uncompressed), plus `checksums.md5`, `groundtruth.jsonl` and `input.json`.
- RCA100: `LICENSE` reads CC BY-NC-SA 4.0. `manifest.txt` lists task IDs only, not hashes.
  `summary.json` declares 3,682,521,875 B and per-case byte and row counts. Ground truth lives in
  `cases/<id>/gt.json` and `answer_key/`.

### A5 OpenRCA — verification for owner decision 2

| Question | Finding | Evidence |
|---|---|---|
| Original source | Microsoft `microsoft/OpenRCA@c1bd4af7` links the Drive folder `1wGiEnu4…`. The folder holds `Bank.zip`, `Market.zip` and `Telecom.zip` (2025-02-23) plus `AppTelecomDeploymentList.xlsx` (24,349 B, added later) | [evidence/microsoft_OpenRCA.md](evidence/microsoft_OpenRCA.md), [evidence/openrca-drive-root.html](evidence/openrca-drive-root.html) |
| Licence | The paper's ethics statement gives CC BY-NC 4.0 but describes ShareAlike terms. No separate data licence file exists (repo `LICENSE` is MIT, for code). Strictest reading: BY-NC-SA. Local research use is permitted | [evidence/openrca-iclr2025-text.txt](evidence/openrca-iclr2025-text.txt) lines 640–648 |
| Ground-truth quality | 1,753 challenge records were balanced down to 412 and filtered to 335 after three engineers checked that each label is identifiable from the telemetry | same, lines 242–261 |
| Independence | It is a subset of the AIOps Challenge series, so it is not independent of the AIOps 2020/2021 upstream data. No other approved source contains these incidents | lineage L5 |
| Relevance | High: LLM-RCA benchmark, multimodal, deployed systems. **Caveat:** records with missing telemetry were removed (filter 2), so OpenRCA is biased toward full observability. That is exactly the variable our study perturbs, and it must be stated | same, line 259 |
| Verdict | Passes the gate. Approved for acquisition with `gdown` in an isolated venv, file by file, with resume. Integrity is `local-only`; Drive sizes are only rounded | — |

### A6 RCABench (FSE'26)

Zenodo 17105974, CC-BY-4.0, 2025-09-12. It holds `rcabench-absolute_anomaly.tar.gz`
(13,444,974,981 B) and two code zips. The record's creator field is a placeholder
("Identifiers, Family name"); authenticity therefore rests on the arXiv 2510.04711 page linking
this DOI (VERIFIED). The paper reports 1,430 validated cases; the count in the archive is UNVERIFIED
until phase 06.

### A7 AnoMod, A10 DejaVu

- AnoMod: Zenodo 18342898, CC-BY-4.0, `isDescribedBy` 10.1145/3793302.3793324, one zip. Five
  modalities on SocialNetwork and TrainTicket.
- DejaVu: Zenodo 6955909, CC-BY-4.0, `isPublishedIn` 10.1145/3540250.3549092. Processed datasets
  A1, A2, B, C and D plus a 7-part raw archive for D. Labels are in `faults.csv`. Whether the
  faults are injected or production faults is UNKNOWN per dataset.

## Category B — auxiliary or conditional

| Dataset | Bytes | State | Exact reason |
|---|---|---|---|
| GAIA MicroSS @238a9e24 | 5,786,350,112 (git blobs; the LFS patterns do not match the split zips) | PENDING-DECISION | Licence conflict: `LICENSE` file says GPL-2.0, README says Apache-2.0. Labels are injection logs. Needs the owner's acknowledgement of the conflict |
| MSDS (ESOCC'20), Zenodo 3549604 v1.1 | 650,495,000 | Approved, auxiliary | OpenStack M/L/T with injected anomalies, CC-BY-4.0. Root-cause label granularity is UNVERIFIED, so it is not used as gold |
| LEMMA-RCA Original ×2 | 86,635,947,335 | DEFERRED (owner decision 3) | Licence unresolved: Zenodo 20516735 says **CC-BY-ND-4.0**, the HF cards say CC-BY-NC-4.0, and GitHub says both. The Zenodo README names `LICENSE_NOTICE.md`, which is absent from the record, and moves canonical access to `lemmarca.info`. About 10 incidents |
| Eadro, Zenodo 7615394 | 127,676,922 | PENDING-LICENSE | The record has **no licence** (`license: null`), so there is no explicit permission. Not rejected |
| AIOps Challenge 2020 (aiops.cn project 65 @17d7929d; GitHub `NetManAIOps/AIOps-Challenge-2020-Data`) | Example: `2020_04_11.zip` 232,077,926 B; total UNKNOWN | METADATA-ONLY (owner decision 4) | Upstream lineage reference for OpenRCA Telecom (PLAUSIBLE). The mirror's `sha256sum.txt` names `*_lock.zip` files that do not match the stored names, so it is not a usable publisher hash |
| AIOps Challenge 2021 (aiops.cn project 83 @cdd0861d) | `AIOps2021.zip` size UNKNOWN (HEAD returned 500) | METADATA-ONLY (owner decision 4) | Upstream for OpenRCA Bank (PLAUSIBLE: 2021-03 timestamps). `aiops21_groundtruth.csv` has 165 rows. CC BY-NC 4.0 per the mirror README |

## Category C — rejected or not acquired as a duplicate or derivative

| Candidate | Exact reason | Evidence |
|---|---|---|
| HF `Shra9701/RCAEval` | Byte-identical to official HF RCAEval (2,080/2,080 hashes) | regenerable-evidence.txt |
| HF `cdreetz/OpenRCA` (68,652,658,522 B), `shaowenchen/openrca` | Unofficial re-uploads with no licence field; the official Drive release is acquired | HF API |
| HF `lechengzheng/AIOps` | Placeholder: 2 files, 2,340 B | HF API |
| aiops.cn `aiops-nankai/data/trace/{data-nezha,data-eadro,gaia,trainticket,hipster-shop}`, `data/gaia-dataset` | Mirrors that cite their upstream | Project READMEs |
| aiops.cn project 107 `aiopschallenge2025` | Same 400 incidents as AIOps2025: identical `groundtruth.jsonl` and `input.json` blob IDs, archives re-packed | t107.json, t110.json |
| RCAEval Zenodo v0.0.1 (14504481) | Superseded by 14590730 | Zenodo versions API |
| RCAEval Figshare v2 (4,462,854,310 B) | Re-packaging with extra preprocessed series; kept as the documented fallback only | Figshare API |
| TORAI (Figshare 31925976) | Derived from RE2 | RCAEval README line 300 |
| LEMMA `*_Preprocessed` | Derived artefacts | HF cards |
| arXiv 2607.13548 | No new dataset | arXiv abstract |
| Synthetic or instruction HF sets (camel-ai/aiops, smoltrace-aiops-tasks, htunn/aiops-gemma, etc.), PyRCA/CIRCA simulators | No telemetry-grounded RCA labels | HF cards and repos |
| LogHub | Log anomaly labels, not root causes | Repo |
| ITBench | Live framework, not a static dataset | Repo |
| LO2, TrainTicketTrace, TraceRCA, AIOps Challenge 2022 raw | PENDING-DISCOVERY: no primary download link found | search-log.md |
