# Dataset provenance

One row per registry source, generated from the provenance records in
[`data/provenance/`](../data/provenance/) and the catalog
[`data/manifests/dataset_catalog.json`](../data/manifests/dataset_catalog.json) as of 2026-10-14.
Each JSON record holds the full field set: canonical URL, publication or DOI, publisher, licence
and its evidence, revision, artefact list, host metadata, retrieval time, expected and verified
file counts and bytes, integrity levels, archive audit, labels, modalities, known limitations,
lineage edges, state, reason and next action. Fields that were not read in a recorded step are
`UNKNOWN`.

How the data was fetched and how to reproduce it: [acquisition_plan.md](acquisition_plan.md).

## Per-source summary

| Source | State | Licence | Revision / record | Files verified / expected | Bytes verified | Integrity levels | Record |
|---|---|---|---|---|---|---|---|
| `petshop` | VERIFIED | CC-BY-4.0 (data, LICENSE_DATASET); Apache-2.0 (code) | 2e96f937 | 164 / 164 | 18,712,735 | publisher-hash | [json](../data/provenance/petshop.json) |
| `anomod` | VERIFIED | CC-BY-4.0 | 18342898 | 1 / 1 | 201,917,396 | publisher-hash | [json](../data/provenance/anomod.json) |
| `msds` | VERIFIED | CC-BY-4.0 | 3549604 | 2 / 2 | 650,495,000 | publisher-hash | [json](../data/provenance/msds.json) |
| `rcaeval-zenodo` | VERIFIED | CC-BY-4.0 (Zenodo record) | 14590730 | 9 / 9 | 5,161,758,943 | publisher-hash | [json](../data/provenance/rcaeval-zenodo.json) |
| `rcaeval-hf` | VERIFIED | MIT (HF card) | afeacb11 | 2,080 / 2,080 | 3,442,007,684 | publisher-hash | [json](../data/provenance/rcaeval-hf.json) |
| `nezha` | VERIFIED | MIT | d8140101 | 1,252 / 1,252 | 3,042,817,082 | publisher-hash | [json](../data/provenance/nezha.json) |
| `cloud-opsbench` | VERIFIED | MIT | 1a02e543 | 27,110 / 27,110 | 3,840,845,678 | publisher-hash | [json](../data/provenance/cloud-opsbench.json) |
| `agenticopseval` | VERIFIED | AIOps2025: CC BY-NC 4.0 (README); RCA100: CC BY-NC-SA 4.0 (RCA100/LICENSE) | 69cf3643 | 857 / 857 | 13,426,756,118 | publisher-hash | [json](../data/provenance/agenticopseval.json) |
| `dejavu` | VERIFIED | CC-BY-4.0 | 6955909 | 12 / 12 | 4,545,204,660 | publisher-hash | [json](../data/provenance/dejavu.json) |
| `rcabench-fse26` | VERIFIED | CC-BY-4.0 | 17105974 | 3 / 3 | 13,446,969,567 | publisher-hash | [json](../data/provenance/rcabench-fse26.json) |
| `openrca` | PENDING:drive-quota | CC BY-NC 4.0 stated with SA terms -> treat BY-NC-SA | 20261014 | 0 / 4 | 0 | local-only | [json](../data/provenance/openrca.json) |
| `gaia` | PENDING:decision | CONFLICT: LICENSE file GPL-2.0; README Apache-2.0 | 238a9e24 | 0 / 122 | 0 | publisher-hash | [json](../data/provenance/gaia.json) |
| `eadro` | PENDING:license | UNKNOWN | 7615394 | 0 / 2 | 0 | publisher-hash | [json](../data/provenance/eadro.json) |
| `lemma-rca-product-review` | PENDING:deferred | CONFLICT: Zenodo 20516735 cc-by-nd-4.0; HF cc-by-nc-4.0 | 63aa4abe | 0 / 6 | 0 | publisher-hash | [json](../data/provenance/lemma-rca-product-review.json) |
| `lemma-rca-cloud-computing` | PENDING:deferred | CONFLICT: as above | 9e5ad23f | 0 / 8 | 0 | publisher-hash | [json](../data/provenance/lemma-rca-cloud-computing.json) |
| `aiops2020-upstream` | PENDING:metadata-only | CONFLICT: organiser non-commercial terms (GitHub) vs CC BY-NC 4.0 (mirror) | 17d7929d | 3 / 3 | 115,628 | publisher-hash | [json](../data/provenance/aiops2020-upstream.json) |
| `aiops2021-upstream` | PENDING:metadata-only | CC BY-NC 4.0 (mirror README) | cdd0861d | 2 / 2 | 20,581 | publisher-hash | [json](../data/provenance/aiops2021-upstream.json) |
| `lo2v2` | PENDING:decision | CC-BY-4.0 (Zenodo record) | 18937117 | 0 / 6 | 0 | publisher-hash | [json](../data/provenance/lo2v2.json) |

Notes:

- **Bytes** count the acquired artefacts as downloaded (compressed). The ten verified sources hold
  47,777,484,863 B. The `aiops*-upstream` label files add 136,209 B, and the Nezha git pack adds
  its `.git` directory. The total is far below the 250 GB budget.
- `agenticopseval` verified 13,426,756,118 B against a declared 13,403,947,520 B. The declared
  figure covers only the LFS objects; the 324 small non-LFS files (anchored by git blob ID) have
  no declared size.
- The `aiops*-upstream` rows are lineage references: only their README and label files were
  fetched (owner decision D4).
- `openrca` already holds `AppTelecomDeploymentList.xlsx` (24,349 B, local SHA-256 `6af1fac2...`
  in [`download_manifest.jsonl`](../data/manifests/download_manifest.jsonl)). It is not in
  `checksums.sha256` because the source as a whole is not verified.

## Integrity levels

Publisher-verified integrity and local hashing are kept separate.

- [`data/manifests/checksums.sha256`](../data/manifests/checksums.sha256) holds the **local**
  SHA-256 of every acquired file of every verified source: 31,495 files. It is
  `sha256sum -c` compatible from the project root.
- [`data/manifests/checksums-levels.tsv`](../data/manifests/checksums-levels.tsv) gives, for the
  same paths, the integrity level and the **publisher** anchor that was matched. All 31,495 files
  are `publisher-hash`:
  - 29,550 match a git blob ID at the pinned commit;
  - 1,918 match an LFS or host SHA-256;
  - 27 match a Zenodo MD5.
- No acquired file is `local-only`. OpenRCA would be the only `local-only` source, because Drive
  publishes no checksum. It can therefore reach at most `VERIFIED-LOCAL-ONLY`.
- Extra cross-checks: the 18 AIOps2025 archives also match the publisher's `checksums.md5`, and
  the Cloud-OpsBench LFS files match GitHub blob IDs. See
  [dataset_quality_audit.md](dataset_quality_audit.md#mirror-completeness-owner-decision-d7).

Archive audit (headers and member names only; nothing was extracted): every zip and tar of every
verified source has 0 unsafe members, 0 encrypted members and 0 errors. The counts are in each
provenance record under `archive_audit`. The DejaVu split archive `DejaVu-D-raw.zip.001`-`.007`
cannot be audited part by part and was not joined.

## Not-acquired register

Every eligible dataset that is not verified, with its exact reason. The machine-readable form is
[`data/manifests/not-acquired.json`](../data/manifests/not-acquired.json).

| Source | State | Exact reason | Next action |
|---|---|---|---|
| `openrca` | PENDING:drive-quota | Drive refused all 3 downloads (quota/interstitial) | rerun fetch after the Drive quota window (~24 h); never with cookies |
| `gaia` | PENDING:decision | licence conflict: LICENSE file GPL-2.0 vs README Apache-2.0 | owner acknowledges licence conflict (plan question 1), then fetch |
| `eadro` | PENDING:license | Zenodo record has no licence | find a licence in the ICSE'23 artefact or ask the authors |
| `lemma-rca-product-review` | PENDING:deferred | owner decision D3: licence conflict (Zenodo CC-BY-ND-4.0 vs HF CC-BY-NC-4.0); ~10 incidents for 86.6 GB | ask the authors which licence governs: lemmarca.info has expired (2026-10-14) and lemma-rca.github.io states CC BY-ND 4.0, conflicting with the HF cards (CC-BY-NC-4.0) |
| `lemma-rca-cloud-computing` | PENDING:deferred | owner decision D3: licence conflict (Zenodo CC-BY-ND-4.0 vs HF CC-BY-NC-4.0); ~10 incidents for 86.6 GB | ask the authors which licence governs: lemmarca.info has expired (2026-10-14) and lemma-rca.github.io states CC BY-ND 4.0, conflicting with the HF cards (CC-BY-NC-4.0) |
| `aiops2020-upstream` | PENDING:metadata-only | allowed small files verified (publisher-hash); archives not acquired (owner decision D4) | archives need a separate owner request |
| `aiops2021-upstream` | PENDING:metadata-only | allowed small files verified (publisher-hash); archives not acquired (owner decision D4) | archives need a separate owner request |
| `lo2v2` | PENDING:decision | found in the phase-01 saturation round (2026-10-14); OAuth2 microservice logs/metrics/traces with Locust-scenario anomaly labels, not root-cause labels; 69,963,617,238 B | owner decides whether an auxiliary anomaly dataset of ~70 GB is wanted; fits the remaining budget |

Eligible candidates outside the registry, also not acquired:

| Candidate | Exact reason | State |
|---|---|---|
| AIOps Challenge 2020 archives (15 daily zips, 3,099,514,219 B in total) and `AIOps2021.zip` (size UNKNOWN; the host returned HTTP 500) | Redundant with OpenRCA (owner decision D4). The 2020 mirror's `sha256sum.txt` does not match its stored names. Per-file sizes and host SHA-256 are in [`_aiops-upstream-file-metadata-20261014.json`](../data/provenance/_aiops-upstream-file-metadata-20261014.json) | metadata only |
| HF RCAEval mirror `Shra9701/RCAEval`, HF OpenRCA re-uploads, aiops.cn project 107 and `aiops-nankai` mirrors | Duplicates of acquired sources; never used as sources | not acquired (duplicate) |
| RCAEval Zenodo v0.0.1, Figshare v2, TORAI, LEMMA `*_Preprocessed`, LO2 v1 | Superseded or derived | not acquired (derived) |
| TrainTicketTrace, TraceRCA data, AIOps Challenge 2022 raw release | No primary download link found | PENDING:discovery |
