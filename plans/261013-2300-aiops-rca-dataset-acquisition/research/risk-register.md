# Risk register

Revision 2 (2026-10-13 23:32).

| ID | Risk | Status | Impact | Evidence | Mitigation in the plan |
|---|---|---|---|---|---|
| R1 | Zenodo outage | Recurred earlier today; recovered at 23:3x | High | 504s, then 200s, on 2026-10-13 | Phase 01 re-reads every Zenodo record with backoff (5 tries over ≥30 min, then hourly up to 24 h). An unavailable source is PENDING, never REJECTED |
| R2 | Licence conflicts | Open | Medium | LEMMA (BY-ND vs BY-NC), GAIA (GPL-2.0 vs Apache-2.0), OpenRCA (BY-NC text with SA terms), RCAEval (CC-BY-4.0 on Zenodo vs MIT elsewhere), AIOps 2020 (organiser terms vs BY-NC) | The strictest reading applies; local research use only; every licence text is archived; GAIA needs owner acknowledgement; LEMMA is deferred |
| R3 | No licence at all (Eadro) | Open | Medium | Zenodo `license: null` | PENDING-LICENSE; not downloaded. The next action is to ask the authors or find a licence in the ICSE'23 artefact |
| R4 | Raw data committed by the outer repo | Mitigated by design | High | `nt114-rca/` is untracked; nested `.gitignore` has `data/` | Phase 01 ignore block plus `git check-ignore` checks |
| R5 | Storage exhaustion | Low | High | Approved queue ≈ 62–66 GB; F: has 832 GB free | A 250 GB budget and 100 GB reserve, both configurable. Over-budget sources become `PENDING: budget` with the shortfall reported, never dropped silently |
| R6 | Partial download or leftover LFS pointer | Medium | High | LFS on HF/GitLab | Size and publisher-hash checks, pointer scan, atomic rename after verification |
| R7 | Malicious archives | Low | High | Third-party zips and tars | Header-only audit; nothing is extracted |
| R8 | Third-party code execution | Medium | High | `RCAEval.utility`, `unzip_all.sh`, notebooks, RCABench platform zips | Never executed; archived as files; Python runs with `-I`; `gdown` only in `.venv-acquire` |
| R9 | Upstream drift | Observed | Medium | Cloud-OpsBench GitHub `main` moved to `6b986be4` today; HF modified today | Everything is pinned; drift creates a new version directory |
| R10 | Duplicate counting | Mitigated by design | High | lineage-and-overlap.md | Lineage groups, `copy_of` edges, per-group independent counts |
| R11 | Weak or altered ground truth | Observed | High | HF RCAEval adds 8 `root_cause.txt` and relabels `f3_1`→`f3`; Nezha README path defect; OpenRCA filtered 77 of 412 | Canonical originals are preferred; derived-copy differences are recorded; nothing is relabelled |
| R12 | Incomplete "lossless" mirror | Observed | High | HF RCAEval lacks the 181 MB `logs.csv` of `re2tt_ts-auth-service_cpu_1` | Zenodo is canonical; the HF copy is flagged in provenance |
| R13 | Google Drive acquisition (OpenRCA) | Open | Medium | Rounded sizes only; virus-scan interstitial; possible quota throttling | `gdown` (pinned version) per file ID with resume in an isolated venv; integrity `local-only`; the exact byte size is recorded at completion; retry after the quota window |
| R14 | Weak dataset metadata (RCABench creator placeholder) | Observed | Low | Zenodo creators field | Authenticity anchored on the arXiv DOI link; recorded as a limitation |
| R15 | Doubly nested project path | Accepted (owner decision 1) | Low | `nt114-rca/nt114-rca` | `RCA_ROOT` variable; no flattening |
| R16 | Throttling on large single files (RCABench 13.4 GB, AIOps2025 archives) | Medium | Medium | Sizes | HTTP Range resume, `.part` files, exponential backoff with jitter |
| R17 | Observability bias in sources | Observed | Medium (scientific) | OpenRCA filter (2); RCAEval SS has no traces | Recorded per source in provenance under `observability_notes` |
