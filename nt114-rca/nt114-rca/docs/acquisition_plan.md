# Raw dataset acquisition: how to reproduce

This page shows how to rebuild `data/raw/` from a clean checkout, byte for byte, with the
committed registry and file lists. It covers acquisition only. Nothing here preprocesses, merges,
converts or relabels data, and nothing touches `src/`, `configs/` or the RCA pipeline.

Current states and the reasons a source was not acquired:
[dataset_provenance.md](dataset_provenance.md).

## Layout

```
scripts/datasets/
  sources.json        registry: one entry per source, pinned revision/record, category, lineage group
  acquire.py          check-metadata | plan | fetch | verify | audit-archives | catalog | status (stdlib only)
  lineage.py          incidents.jsonl, lineage-report.json, mirror-completeness-*.json (reads label files only)
  provenance.py       data/provenance/<id>.json from registry + file list + state
data/manifests/       tracked: filelists/<id>.json, dataset_catalog.json, not-acquired.json, checksums.sha256,
                      checksums-levels.tsv, download_manifest.jsonl, incidents.jsonl, lineage and mirror reports
data/provenance/      tracked: <id>.json per source, dated metadata re-checks, saved licence evidence
data/raw/<id>/<version>/   ignored: byte-preserved artefacts, never extracted
data/.state/<id>.json      ignored: per-source state history
.venv-acquire/             ignored: isolated venv holding only gdown (Google Drive sources)
```

`.gitignore` ignores `data/*` except `data/manifests/` and `data/provenance/`. Check it with
`git check-ignore -v data/raw/x data/manifests/x` (the first is ignored, the second is not).

## Rules the tool enforces

- **Pinned inputs.** Every source has a pinned revision or record. Hugging Face, GitHub and GitLab
  revisions are full 40-hex commits. `fetch` only downloads what the committed
  `data/manifests/filelists/<id>.json` lists. A drifted upstream is reported, never followed.
- **Integrity levels are kept apart.**
  - `publisher-hash`: matches a hash the publisher or host published for that exact file (Zenodo
    MD5, HF/GitLab LFS SHA-256, git blob ID at the pinned commit).
  - `publisher-size`: only a declared size is available.
  - `local-only`: no publisher hash exists. The local SHA-256 proves later integrity, not
    authenticity, and such a source can only reach `VERIFIED-LOCAL-ONLY`, never `VERIFIED`.
- **States.** `VERIFIED`, `VERIFIED-LOCAL-ONLY`, `PARTIAL` (missing paths listed), `PENDING:<why>`
  (`budget`, `drive-quota`, `decision`, `license`, `metadata-only`, `discovery`), and
  `BLOCKED:<why>`. Every non-VERIFIED state carries a reason and a next action.
- **Budget.** The default budget is 250 GB of raw data, and 100 GB of free disk is always kept in
  reserve. Both can be changed with `--budget-gb` and `--reserve-gb`. A source that would not fit
  becomes `PENDING:budget` with the shortfall reported; it is never dropped silently.
- **Safe downloads.** Downloads resume with HTTP Range into `.part` files and retry with backoff.
  `--segments N` splits large files into parallel ranges for hosts that throttle each connection.
  A file is renamed into place only after its size and anchor hash match.
- **No third-party code.** Archives are audited from their headers only (path traversal, absolute
  paths, links, encryption) and are never extracted. Repository scripts, notebooks and the RCABench
  platform zips are never executed. Python that reads downloaded data runs with `-I`.
- **Git sources.** Git sources are fetched at the pinned commit with
  `-c core.autocrlf=false -c core.longpaths=true -c core.symlinks=false` and `GIT_LFS_SKIP_SMUDGE=1`,
  then pass `git fsck` and a clean-worktree check. LFS pointers left in place are detected.

## Order and commands

Run every command from the project root. Each source runs `plan`, `fetch`, `verify` and
`audit-archives`, in that order, as separate commands; rerun `fetch` if it reports `PARTIAL`.

```bash
python -I scripts/datasets/acquire.py plan           --source <id>   # sizes, budget, urls_sha256; no download
python -I scripts/datasets/acquire.py fetch          --source <id> [options below]
python -I scripts/datasets/acquire.py verify         --source <id>
python -I scripts/datasets/acquire.py audit-archives --source <id>
```

| Order | Source id | Host | Fetch options used | Bytes (publisher-declared) |
|---|---|---|---|---|
| 1 | `petshop` | GitHub (git) | — | 18,712,735 |
| 2 | `anomod` | Zenodo | `--workers 2 --segments 8` | 201,917,396 |
| 3 | `msds` | Zenodo | `--workers 2 --segments 8` | 650,495,000 |
| 4 | `rcaeval-zenodo` | Zenodo | `--workers 2 --segments 8` | 5,161,758,943 |
| 5 | `rcaeval-hf` | Hugging Face | `--workers 6 --segments 4` | 3,442,007,684 |
| 6 | `nezha` | GitHub (git) | — | 3,042,817,082 (plus the `.git` pack) |
| 7 | `cloud-opsbench` | Hugging Face | `--workers 6 --segments 4` | 3,840,845,678 |
| 8 | `agenticopseval` | aiops.cn GitLab | `--workers 6 --segments 4` | 13,403,947,520 LFS bytes plus 324 small non-LFS files |
| 9 | `dejavu` | Zenodo | `--workers 2 --segments 8` | 4,545,204,660 |
| 10 | `rcabench-fse26` | Zenodo | `--workers 2 --segments 8` | 13,446,969,567 |
| 11 | `openrca` | Google Drive | `--gdown .venv-acquire/Scripts/gdown.exe --retries 2` | about 8.2 G (Drive-rounded) plus 24,349 |
| — | `aiops2020-upstream`, `aiops2021-upstream` | aiops.cn GitLab | `--allow-unknown-size` | label files only (115,628 and 20,581 B) |

Notes on hosts:

- Zenodo throttles each connection to about 400 KB/s, so segmented ranges are used.
- Anonymous Hugging Face requests may return HTTP 429. `fetch` retries, and a second `fetch` pass
  resumes whatever is left.
- Google Drive may refuse anonymous downloads for about 24 hours. `fetch` then records
  `PENDING:drive-quota` and exits with code 5. Rerun after the window. Never pass browser cookies,
  and never use the unofficial HF re-uploads.
- The OpenRCA venv: `python -m venv .venv-acquire`, then
  `.venv-acquire/Scripts/python -m pip install gdown==6.4.2`. No global install is needed.

The sources that are deferred, pending or metadata-only (GAIA, Eadro, LEMMA-RCA, LO2 v2, the
AIOps 2020/2021 archives) must not be fetched until the reason in
[dataset_provenance.md](dataset_provenance.md#not-acquired-register) is resolved.

## After acquisition

```bash
python -I scripts/datasets/lineage.py                    # incidents, lineage groups, mirror completeness
python -I scripts/datasets/provenance.py                 # data/provenance/<id>.json
python -I scripts/datasets/acquire.py catalog            # dataset_catalog.json, not-acquired.json, checksums
python -I scripts/datasets/acquire.py status             # one line per source
sha256sum -c data/manifests/checksums.sha256             # every acquired file against its recorded SHA-256
```

`checksums-levels.tsv` gives the integrity level and publisher anchor for each line of
`checksums.sha256`.

## Reproducing from a clean checkout

1. Clone the repository. `data/raw/` is absent; the registry, file lists and provenance are
   present.
2. Create `.venv-acquire` only if OpenRCA is needed (see above).
3. Run `plan --source <id>` for each source. The `urls_sha256` value in its output is a hash of the
   sorted (path, URL or file ID, anchor) list. It must equal the value recorded for the original
   acquisition. A different value means the committed file list changed.
4. Run the commands in the order table above, then the post-acquisition commands.
5. `sha256sum -c data/manifests/checksums.sha256` must report every line `OK`. A second `fetch` of
   a verified source transfers 0 bytes.

Unit tests for the tool (local HTTP server; no network needed):
`python -I tests/test_datasets_acquire.py`.
