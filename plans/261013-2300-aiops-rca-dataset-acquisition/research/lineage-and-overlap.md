# Lineage, overlap and contamination analysis

Revision 2 (2026-10-13 23:32). The unit of independence is the **incident**: one fault
occurrence with one telemetry window and one ground-truth label. Packaging, mirrors and relabelling
never add incidents.

## Lineage groups

| Group | Canonical (acquired) | Other copies (counted zero times) | Identity evidence |
|---|---|---|---|
| L1 RCAEval | Zenodo 14590730 (originals) | HF `phamquiluan/RCAEval@afeacb11` (derived, **incomplete**: 1 log file missing, 3 cases renamed, 8 labels added, auxiliary files omitted); HF `Shra9701/RCAEval`; Figshare v2; TORAI; Zenodo v0.0.1 | Remote zip directory vs HF tree: 735 = 735 incidents after mapping the 3 renamed cases by `inject_time.txt` CRC32 (VERIFIED) |
| L2 AIOps Challenge 2025 | aiops.cn project 110 `AIOps2025/` | Project 107; project 88 sample | Same ground-truth and input blob IDs (VERIFIED); archive bytes differ |
| L3 Tianchi 2025 | Project 110 `RCA100/` | UNKNOWN | — |
| L4 Nezha | GitHub `IntelligentDDS/Nezha@d8140101` | aiops.cn project 69 | Mirror README cites upstream |
| L5 AIOps Challenge 2020–2022 | OpenRCA (Drive) | Upstream 2020 (project 65, GitHub NetManAIOps) and 2021 (project 83): metadata and label files only; `cdreetz/OpenRCA`; `shaowenchen/openrca` | OpenRCA paper states the challenge origin (VERIFIED). The per-year mapping (Telecom←2020, Bank←2021, Market←2022) is PLAUSIBLE from dates; phase 05 compares failure lists |
| L6 Eadro | Not acquired (licence) | aiops.cn project 68 | Mirror README cites the DOI |
| L7 GAIA | GitHub `CloudWise-OpenSource/GAIA-DataSet@238a9e24` (if approved) | aiops.cn projects 22 and 63 | — |
| L8 LEMMA-RCA | Deferred | `*_Preprocessed`; Zenodo 20516735 (metadata only); `lechengzheng/AIOps` | — |
| L9 Cloud-OpsBench | HF `LLM4Ops/Cloud-OpsBench@1a02e543` | GitHub `@ea05dafb` (source); GitHub `main` has since moved to `6b986be4` | 27,104/27,104 artifact paths; 27,054 identical blob IDs; 50 LFS files with equal sizes (VERIFIED). Content equality of those 50 is proved in phase 06 |
| L10 PetShop | GitHub `@2e96f937` | — | — |
| L11 RCABench (FSE'26) | Zenodo 17105974 | GitHub platform code inside the record | arXiv page links the DOI (VERIFIED) |
| L12 AnoMod | Zenodo 18342898 | `EvoTestOps/AnoMod` (says data moved to Zenodo) | Repo README (VERIFIED) |
| L13 DejaVu | Zenodo 6955909 | — | — |
| L14 MSDS | Zenodo 3549604 v1.1 | Earlier concept versions (3484800) | — |

## Overlap types

1. **Same incident, different packaging** (L1, L2, L5, L9): count once. Every copy gets a
   `copy_of` edge to the canonical incident.
2. **Same system, different incidents**:
   - Online Boutique/HipsterShop: L1, L2, L4, L9, L11 (UNVERIFIED) and possibly L5 Market.
   - Train Ticket: L1, L4, L9, L12 and Eadro.
   - SocialNetwork: L12 and Eadro.
   - OpenStack: L14.
   - Others: OTel Demo (L3) and the PetShop AWS application (L10).
   The catalog records `system` so later work can hold out whole systems.
3. **Repeated injections of one (service, fault) cell**: RCAEval RE1 has 5 repetitions and RE2 has
   3. A `fault_cell` key keeps repetitions from counting as independent evidence.
4. **Subset of upstream with corrected labels** (L5): OpenRCA labels override upstream labels;
   upstream copies are reference-only.

## Identity checks (phase 06)

- File level: publisher hashes (Zenodo/Figshare MD5, HF LFS SHA-256, git object IDs,
  `checksums.md5`, `manifest.json`) plus local SHA-256 of every file.
- Incident level: the key `(system, root_cause_entity, fault, inject_or_start_time)`.
- **RCAEval HF vs Zenodo**: re-run the comparison on local copies, then additionally compare the
  bytes of every `inject_time.txt`. Report the five difference classes above as data, not defects
  to fix.
- **Cloud-OpsBench**: for the 50 LFS files, check that the git blob SHA-1 of the local content
  equals the GitHub blob ID at `ea05dafb`.
- **OpenRCA vs AIOps 2020/2021**: compare failure lists (time, component) from OpenRCA
  `record.csv` against `aiops21_groundtruth.csv` and the 2020 failure list. This uses label files
  only; telemetry is not compared unless the owner later approves upstream archive downloads.

## Contamination notes

- **Label leakage through paths**: the RCAEval case directories (Zenodo
  `RE2-TT/ts-order-service_cpu/1`, HF `re2tt_ts-order-service_cpu_1`), Nezha fault lists and the
  RCA100 non-blind files `gt.json` and `answer_key/` sit next to the telemetry. Field
  `label_in_path` flags this.
- **Pre-training exposure**: first-public dates are recorded per source: RCAEval Zenodo
  2024-12-17 (v0.0.1), OpenRCA Drive files 2025-02-23, AIOps2025 GitLab 2026-06/07, and so on.
- **Observability bias**: OpenRCA dropped records with missing telemetry. RCAEval Sock Shop
  naturally lacks traces, and RE3-SS ships header-only trace files. Recording these per source is
  in scope; analysing them is not.
- **Fine-tuning splits (future)**: split by lineage group and preferably by system, never by file
  or repetition.
