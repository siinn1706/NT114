# Phase 05: Deferred, pending and lineage-metadata sources

Status: done (2026-10-14). Receipt: [cook receipt](receipts/cook-receipt-20261014.json)

## Requirements

Record a complete provenance stub for every eligible source that is not fully acquired, and run
only the actions each decision allows.

| Source | Decision | Allowed action | State after phase |
|---|---|---|---|
| `gaia` | Owner acknowledgement of the licence conflict (open question 1) | If acknowledged, run `fetch`/`verify`/`audit` at @238a9e24 (5,786,350,112 B). Otherwise record only | VERIFIED or `PENDING: decision` |
| `eadro` | No licence on the Zenodo record | Record metadata (files, MD5s); no download | `PENDING: license` |
| `lemma-rca-*` | Deferred (D3) | Record both licence texts (Zenodo CC-BY-ND-4.0 metadata; HF card CC-BY-NC-4.0). Fetch the licence notice from `lemmarca.info` **as a page read only** | `PENDING: deferred` |
| `aiops2020-upstream` | Metadata only (D4) | Record the pinned HEAD, file list with `X-Gitlab-Size`/`X-Gitlab-Content-Sha256` headers per file, and the original GitHub links and MD5. Download only `README.md`, `sha256sum.txt` and `data_release_v3.5.zip` (113,379 B, the failure list) | `PENDING: metadata-only` |
| `aiops2021-upstream` | Metadata only (D4) | As above. Download only `README.md` and `aiops21_groundtruth.csv` | `PENDING: metadata-only` |

Rules:

- GitLab header hashes are host-computed for a **mirror**, so they are recorded as
  `host-reported`. They are not `publisher-hash`.
- The 2020 mirror's `sha256sum.txt` lists `*_lock.zip` names that do not exist in the repo.
  Record this mismatch, and do not treat the file as a valid anchor.
- No archive under these sources is downloaded, decrypted or extracted.

## Files

- Create: `RCA_ROOT/data/provenance/{gaia,eadro,lemma-rca-product-review,lemma-rca-cloud-computing,aiops2020-upstream,aiops2021-upstream}.json`.
- Create, only for the small label files allowed above:
  `RCA_ROOT/data/raw/aiops2020-upstream/gitlab-<sha12>/…` and
  `RCA_ROOT/data/raw/aiops2021-upstream/gitlab-<sha12>/…`.

## Steps

1. Run `check-metadata` for each source. Write its provenance stub with state, reason and next
   action.
2. For the AIOps upstream sources, issue a HEAD request for every file. One request per file is
   enough to read the GitLab size and hash headers. `AIOps2021.zip` returned 500 on 2026-10-13;
   retry with backoff and record `UNKNOWN` if it keeps failing.
3. Download only the allowed small files, then run `verify` (`local-only` or `host-reported`).
4. GAIA: proceed only if `run-context.json` contains `decisions.gaia = "acknowledged"`.

## Checks

- Six provenance stubs exist, each with a non-empty `reason` and `next_action`.
- No file larger than 1 MB exists under `data/raw/aiops202*-upstream/`.
- Eadro and LEMMA have no `data/raw/` directory.

## Risk and rollback

- These are metadata writes only, plus at most about 0.2 MB of label files. Rollback deletes the
  stubs and the small files.
