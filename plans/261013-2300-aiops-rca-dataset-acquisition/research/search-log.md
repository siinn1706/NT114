# Search log and coverage

## First pass (2026-10-13)

| Channel | Queries or targets | Outcome |
|---|---|---|
| Local repo | `git ls-files`, `.gitignore`, `private/`, `nt114-rca` archive and moved folder, `df -h`, tool versions | No real data present; only the synthetic generator exists |
| GitHub API (`gh`) | RCAEval, Nezha, rca_baselines, GAIA, DejaVu, TraceRCA, AIOps-Challenge-2020-Data, OpenRCA, PetShop, Eadro, ITBench, LogHub, CIRCA, PyRCA, train-ticket, AnoMod, Cloud-OpsBench | Licences, commits, trees and READMEs captured in [evidence/](evidence/) |
| Hugging Face Hub | Searches for "root cause analysis", "microservice", "aiops", "OpenRCA", "RCAEval", "trainticket", "telemetry fault injection"; `Lemma-RCA-NEC` author; paper search "microservice root cause analysis dataset" | Official RCAEval, LEMMA and Cloud-OpsBench repos plus mirrors; FSE'26 benchmark found through HF papers |
| Figshare API | 31048672, 31925976 | VERIFIED metadata and MD5 |
| Zenodo API and web (CLI, WebFetch, Chrome) | 14590730, 7615393, 6955909, 20516735, 3549604 | HTTP 504 on every attempt; nothing verified in this pass |
| aiops.cn GitLab API | Public project list (71 projects); projects 65, 68, 83, 107, 110 | AgenticOpsEval, upstream AIOps 2020/2021/2025 and Nankai mirrors |
| Web search | Nezha; LEMMA-RCA; microservice RCA datasets with M/L/T 2025–2026; OpenRCA origin; Eadro Zenodo; AnoMod/LO2 | New leads: AgenticOpsEval, Cloud-OpsBench, 2607.13548, AnoMod, LO2, TrainTicketTrace |
| arXiv / ICLR proceedings | 2607.13548, 2510.04711, OpenRCA PDF | OpenRCA construction details (lines 89–261, 640); FSE'26 Zenodo DOI 10.5281/zenodo.17105974 |

## Second pass after owner decisions (2026-10-13)

| Channel | Targets | Outcome |
|---|---|---|
| Zenodo API | 14590730, 14504481, 17105974, 18342898, 6955909, 3549604, 7615394, 20516735 | All reachable. Files, sizes, MD5 and licences recorded in [zenodo-records-2026-10-13.txt](evidence/zenodo-records-2026-10-13.txt). Eadro `license: null`; LEMMA Zenodo is metadata-only with CC-BY-ND-4.0 |
| Zenodo ranged reads (zip central directory only) | RCAEval 9 zips | Member lists and CRC32; 0 unsafe members; compared with HF in [rcaeval-zenodo-vs-hf-comparison.txt](evidence/rcaeval-zenodo-vs-hf-comparison.txt) |
| HF API (`?blobs=true`) | RCAEval @afeacb11, Cloud-OpsBench @1a02e543, LEMMA ×2 | RCAEval HF is incomplete versus Zenodo (five difference classes); Cloud-OpsBench HF equals GitHub ea05dafb on 27,104 paths |
| GitHub API | `microsoft/OpenRCA` @c1bd4af7, Cloud-OpsBench `main` | OpenRCA Drive folder link; Cloud-OpsBench `main` moved to 6b986be4 (drift, pin kept) |
| Google Drive (curl, `embeddedfolderview`) | OpenRCA folder 1wGiEnu4OkWrjPxfx5ZTROnU37-5UDoPM | 4 files with IDs and Drive-rounded sizes; no publisher checksums ([openrca-drive-root.html](evidence/openrca-drive-root.html)) |
| aiops.cn GitLab tree and raw endpoints | Projects 65, 83, 107, 110 | Raw endpoint supports Range; AIOps2025 `checksums.md5`; RCA100 `summary.json`; 2020 `sha256sum.txt` names do not match stored files; 2021 `AIOps2021.zip` HEAD returned 500 |
| OpenRCA ICLR PDF (pdftotext) | Licence and ground-truth construction | CC BY-NC (SA terms described), 1,753 → 412 → 335 records, missing-telemetry filter |

## Saturation

The last three channels (HF mirror search, aiops.cn project list, HF paper search) produced
mirrors of known families plus one new family each (Cloud-OpsBench, AgenticOpsEval and the
FSE'26 benchmark). The second pass added no new family. Saturation is not proven, so phase 01
repeats one bounded round: OpenAlex and Semantic Scholar queries for "root cause analysis
dataset microservice" from 2024 onward, and Papers with Code dataset pages. It adds a family only
when that family has a primary download link and a licence.

## Coverage gaps

- MSDS root-cause label granularity is UNVERIFIED; it stays B auxiliary until a label file is seen.
- The canonical location of the AIOps Challenge 2022 (Market cloudbed) raw release was not found.
- LO2 (PROMISE'25), TrainTicketTrace (SANER'26 workshop) and TraceRCA data have no primary link.
- OpenRCA per-system record counts were not extracted cleanly from the PDF; phase 06 counts them
  from `record.csv`.
- The LEMMA licence notice on `lemmarca.info` was not read.
- No paid, gated or login-only portals were queried (Tianchi, CCF registration pages).
