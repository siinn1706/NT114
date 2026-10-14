---
title: Public AIOps/RCA raw dataset acquisition with provenance
created: 2026-10-13
revised: 2026-10-13 23:32 (revision 2, owner decisions applied)
timezone: Asia/Saigon
status: executed 2026-10-14 (OpenRCA PENDING:drive-quota; owner review pending-personal-review)
receipt: receipts/cook-receipt-20261014.json
mode: executed with /nckh-cook --auto
plan_location: plans/ (repository convention {date}-{time}-{slug})
project_root: nt114-rca/nt114-rca  (RCA_ROOT; kept as-is per owner decision 1)
research_topic: Overconfident LLM Root Cause Diagnosis Under Missing Observability
flags: --deep
---

# Public AIOps/RCA raw dataset acquisition with provenance

## Outcome

`RCA_ROOT/data/raw/` holds a pinned, integrity-checked, provenance-documented copy of every
approved public RCA dataset, with original files, licences and version metadata preserved. Each
file records whether its integrity is **publisher-verified** or only **locally hashed**. Each
incident carries a lineage group, so mirrors and re-packaging never inflate independent counts.
Every eligible dataset that was not acquired is listed with its exact reason.

## Owner decisions (2026-10-13)

| # | Decision | Applied in |
|---|---|---|
| D1 | Do not flatten `nt114-rca/nt114-rca` unless a verified technical issue requires it | `RCA_ROOT` throughout |
| D2 | OpenRCA is conditional: verify source, licence, ground truth, independence and relevance first, then use `gdown` in an isolated venv with resume. A missing publisher checksum does not disqualify it | Verification done (catalog A5); [phase 04](phase-04-openrca-gated-acquisition.md) |
| D3 | Defer LEMMA-RCA until its licence conflict is resolved and a research reason exists | [phase 05](phase-05-deferred-pending-and-lineage-metadata.md) |
| D4 | AIOps 2020/2021 are enabled as lineage references: metadata and provenance first, no redundant archive downloads | [phase 05](phase-05-deferred-pending-and-lineage-metadata.md) |
| D5 | 250 GB budget and 100 GB reserve, both configurable; never silently drop a dataset over budget | [phase 02](phase-02-acquisition-tooling.md) |
| D6 | Retry Zenodo with backoff; unavailable means PENDING, never REJECTED | [phase 01](phase-01-preflight-and-metadata-gate.md) |
| D7 | Verify that HF mirrors contain the complete official releases | Done for RCAEval and Cloud-OpsBench; re-proved in [phase 06](phase-06-integrity-and-lineage.md) |
| D8 | Keep publisher-verified checksums distinct from local hashes | `integrity_level` field everywhere |

## Constraints

- Scope covers discovery, verification, acquisition, integrity, provenance and documentation only.
- Raw files are byte-preserved. Archives are audited, never extracted.
- Large binaries never enter git.
- Only official mechanisms are used. The single exception is `gdown`, an authorised third-party
  client for the official OpenRCA Drive files, run in an isolated venv.
- Third-party repository scripts are never executed. Python that reads downloaded data runs with
  `-I`.
- No global configuration change is made; git-lfs is already installed globally.

## Non-goals

Preprocessing, format conversion, merging, relabelling, training, fine-tuning, inference, RAG,
benchmark execution, and any change to `RCA_ROOT/src/`, `RCA_ROOT/configs/` or
`RCA_ROOT/tests/test_pipeline.py`.

## Evidence base

- [research/dataset-catalog.md](research/dataset-catalog.md): A/B/C catalog, scores, mirror
  completeness and the OpenRCA verification.
- [research/lineage-and-overlap.md](research/lineage-and-overlap.md): 14 lineage groups and the
  identity checks.
- [research/risk-register.md](research/risk-register.md): R1–R17.
- [research/search-log.md](research/search-log.md): search channels and coverage gaps.
- [research/sources-seed.json](research/sources-seed.json): pinned revisions, files, publisher
  hashes, licences and target state.
- [research/evidence/SHA256SUMS.txt](research/evidence/SHA256SUMS.txt): hashes of every evidence
  file read for this plan.

## Revised acquisition queue and storage

Bytes are publisher-declared compressed sizes, as downloaded.

| Order | Source | Bytes | Integrity level | Gate |
|---|---|---|---|---|
| 1 | PetShop @2e96f937 | 18,609,770 (+ about 5 MB code) | publisher-hash | — |
| 2 | AnoMod (Zenodo 18342898) | 201,917,396 | publisher-hash | Zenodo re-read |
| 3 | MSDS (Zenodo 3549604), B auxiliary | 650,495,000 | publisher-hash | Zenodo re-read |
| 4 | RCAEval Zenodo 14590730 (canonical) | 5,161,758,943 | publisher-hash | Zenodo re-read |
| 5 | RCAEval HF @afeacb11 (derived copy) | 3,442,007,684 | publisher-hash | — |
| 6 | Nezha @d8140101 | 3,042,817,082 (+ up to about 3 GB `.git` pack) | publisher-hash | — |
| 7 | Cloud-OpsBench HF @1a02e543 | 3,840,845,678 | publisher-hash | — |
| 8 | AgenticOpsEval @69cf3643: AIOps2025 | 9,741,961,087 | publisher-hash | — |
| 8 | AgenticOpsEval @69cf3643: RCA100 | 3,682,521,875 (declared) | publisher-size + local-only | — |
| 9 | DejaVu (Zenodo 6955909) | 4,545,204,660 | publisher-hash | Zenodo re-read |
| 10 | RCABench FSE'26 (Zenodo 17105974) | 13,446,969,567 | publisher-hash | Zenodo re-read |
| 11 | OpenRCA (Drive) | about 8.2 G (Drive-rounded) + 24,349 | local-only | Phase-04 gate (verification passed in planning) |
| — | **Subtotal, approved** | **about 56.0–56.6 GB** (items 1–10 sum to 47,775,108,742 B; OpenRCA is 8.2 G, either GB or GiB). Up to about 3 GB more for the Nezha `.git` pack | | |
| 12 | GAIA @238a9e24 | 5,786,350,112 | publisher-hash | Owner acknowledges licence conflict |
| — | **Total with GAIA** | **about 62–65.4 GB** | | |

That leaves at least 184 GB of the default budget unused. F: has 832 GB free against the 100 GB
reserve. No approved source is close to the budget limit.

## Eligible datasets not acquired

| Dataset | Exact reason | State | Next action |
|---|---|---|---|
| LEMMA-RCA Product Review + Cloud Computing (86,635,947,335 B) | Licence conflict (Zenodo CC-BY-ND-4.0 vs HF CC-BY-NC-4.0); about 10 incidents; owner decision D3 | DEFERRED | Read the licence on `lemmarca.info` and ask the authors |
| Eadro (127,676,922 B) | Zenodo record has no licence | PENDING-LICENSE | Look for a licence in the ICSE'23 artefact, or ask the authors |
| GAIA (5,786,350,112 B) | GPL-2.0 vs Apache-2.0 conflict | PENDING-DECISION | Owner acknowledgement (question 1) |
| AIOps 2020 / 2021 upstream archives | Redundant with OpenRCA (D4); the 2020 mirror's hash file does not match its stored names | METADATA-ONLY | Label files only; archives need a separate owner request |
| RCAEval Zenodo v0.0.1, Figshare v2, TORAI, LEMMA preprocessed, AIOps2025 project 107, HF/aiops.cn mirrors | Superseded, derived, re-packaged or duplicate (catalog section C) | NOT-ACQUIRED | — |
| LO2, TrainTicketTrace, TraceRCA, AIOps Challenge 2022 raw | No primary download link found | PENDING-DISCOVERY | Phase-01 saturation round |

## Phases

| Phase | Status | Depends on | Purpose |
|---|---|---|---|
| [Phase 01: Preflight, ignore contract, metadata and Zenodo re-verification](phase-01-preflight-and-metadata-gate.md) | done ([receipt](receipts/cook-receipt-20261014.json)) | — | Paths, inventory, ignore rules, drift and Zenodo backoff |
| [Phase 02: Acquisition and verification tooling](phase-02-acquisition-tooling.md) | done ([receipt](receipts/cook-receipt-20261014.json)) | 01 | `acquire.py`, integrity levels, budget policy, tests |
| [Phase 03: Publisher-hashed acquisition](phase-03-tier1-acquisition.md) | done ([receipt](receipts/cook-receipt-20261014.json)) | 02 | Queue items 1–10 |
| [Phase 04: OpenRCA gated acquisition](phase-04-openrca-gated-acquisition.md) | PENDING:drive-quota ([receipt](receipts/cook-receipt-20261014.json)) | 02 | Queue item 11 (`gdown`, `local-only`) |
| [Phase 05: Deferred, pending and lineage-metadata sources](phase-05-deferred-pending-and-lineage-metadata.md) | done ([receipt](receipts/cook-receipt-20261014.json)) | 02 | GAIA, Eadro, LEMMA, AIOps 2020/2021 metadata |
| [Phase 06: Integrity, mirror completeness and lineage](phase-06-integrity-and-lineage.md) | done ([receipt](receipts/cook-receipt-20261014.json)) | 03 (04 and 05 when run) | Hashes, identity checks, incident registry |
| [Phase 07: Catalog, provenance docs and reproducibility](phase-07-docs-and-reproducibility.md) | done ([receipt](receipts/cook-receipt-20261014.json)) | 06 | Docs, not-acquired register, dry run |

## Acceptance checklist for /nckh-cook

1. Every registry source has `data/provenance/<id>.json` containing the phase-07 fields. Unknown
   values are `UNKNOWN`.
2. Every downloaded file appears in `data/manifests/checksums.sha256` with an `integrity_level`.
   Every `publisher-hash` file matches its publisher hash, with zero mismatches. Every
   `local-only` file is labelled as such and is never reported as publisher-verified.
3. Expected and actual file counts and bytes match for every VERIFIED source. PARTIAL sources list
   the exact missing paths.
4. No LFS pointer remains, and every git source passes `git fsck`.
5. The archive audit finds zero unsafe members, and nothing is extracted.
6. The outer repo shows no file under `RCA_ROOT/data/raw/` or `data/.state/`. `git check-ignore`
   confirms the ignore contract.
7. `incidents.jsonl` assigns a lineage group to every incident. Independent counts exclude
   `copy_of` rows.
8. The HF vs canonical completeness reports for RCAEval and Cloud-OpsBench exist and reproduce
   the planning findings, or document any change.
9. Each source has one state from VERIFIED, VERIFIED-LOCAL-ONLY, PARTIAL, PENDING (with subtype)
   and BLOCKED, plus a reason and next action for every non-VERIFIED state.
10. A rerun of `fetch` transfers 0 bytes and leaves the manifests byte-identical.
11. The four docs exist, cite provenance paths, and include the not-acquired register.
12. `src/`, `configs/` and `tests/test_pipeline.py` hashes are unchanged from the phase-01
    inventory.

## Execution result (2026-10-14)

Evidence: [cook receipt](receipts/cook-receipt-20261014.json) (`check-receipt.py verify` VERIFIED,
0 findings); raw command log `work/raw/attempts/commands.jsonl` (git-ignored).

| # | Acceptance item | Result |
|---|---|---|
| 1 | Provenance per source | 18 records in `RCA_ROOT/data/provenance/` |
| 2 | Checksums and integrity levels | 31,495 files; all `publisher-hash`; `sha256sum -c` exit 0 |
| 3 | Counts and bytes | 10 sources VERIFIED, 47,777,484,863 B, 0 missing |
| 4 | LFS and fsck | 0 LFS pointers; Nezha `git fsck` 0 |
| 5 | Archive audit | 0 unsafe, 0 encrypted; nothing extracted |
| 6 | Ignore contract | outer `git status` shows nothing under `data/raw`, `data/.state`, `.venv-acquire` |
| 7 | Lineage | 3,055 incident rows, 2,320 independent; deterministic across two runs |
| 8 | Mirror completeness | RCAEval: 5 planning classes reproduced plus one new (HF `inject_time` truncated). Cloud-OpsBench: 27,105/27,106 common paths equal; only `README.md` differs |
| 9 | One state per source | 10 VERIFIED, 8 PENDING with reason and next action |
| 10 | Idempotent rerun | 0 B transferred; manifests byte-identical |
| 11 | Docs | four files in `RCA_ROOT/docs/`; 0 broken links |
| 12 | Pipeline untouched | `src/`, `configs/`, `tests/test_pipeline.py` hashes unchanged |

Deviations from the plan:

- Tests run as `python -I tests/test_datasets_acquire.py`, because `-I` drops cwd from the
  module path, so `-m unittest` cannot find them.
- `incidents.jsonl` is built by `scripts/datasets/lineage.py`, not by `acquire.py catalog`.
  `provenance.py` was added for the per-source records.
- RCA100 is `publisher-hash`, not `publisher-size`: its Parquet files are LFS objects with SHA-256
  pointers.
- `acquire.py fetch` gained `--retries`, and records `PENDING:drive-quota` with exit 5 when Drive
  refuses every file.
- `aiops21_groundtruth.csv` has 159 records, not the 165 lines counted in planning.
- OpenRCA was stopped after the quota response repeated, instead of waiting out the full 6-hour
  backoff.

## Explicitly avoid

- Running `RCAEval.utility.download_*`, `unzip_all.sh`, notebooks or any repository code,
  including the RCABench platform zips.
- Extracting, decrypting (AIOps 2020), converting, merging, renaming or relabelling anything.
- Using mirrors (`Shra9701/RCAEval`, `cdreetz/OpenRCA`, `aiops-nankai/*`, project 107) as sources.
- Downloading LEMMA, Eadro, GAIA (before acknowledgement) or the AIOps 2020/2021 archives.
- Changing global configuration, or committing `data/raw/` or `data/.state/`.

## Remaining blockers and questions (after execution, 2026-10-14)

1. **GAIA**: do you accept local research use under the stricter of GPL-2.0 and Apache-2.0? If
   not, it stays PENDING:decision.
2. **Eadro**: it has no licence. It stays PENDING:license until a licence is found or the authors
   (Cheryl Lee et al., ICSE'23) are asked.
3. **OpenRCA**: Google Drive refused all three archives (quota). Rerun
   `acquire.py fetch --source openrca --gdown .venv-acquire/Scripts/gdown.exe` after about 24 hours;
   it resumes. `gdown` 6.4.2 is pinned in `.venv-acquire`.
4. **LO2 v2** (found in the saturation round): acquire about 70 GB of anomaly-labelled
   (not root-cause-labelled) data as auxiliary, or keep PENDING:decision?
5. **LEMMA-RCA**: `lemmarca.info` has expired, and `lemma-rca.github.io` states CC BY-ND 4.0
   against the HF cards' CC-BY-NC-4.0. Only the authors can resolve this.
6. **Owner review**: acceptance remains `pending-personal-review`.
