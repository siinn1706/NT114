# Phase 03: Publisher-hashed acquisition

Status: done (2026-10-14). Receipt: [cook receipt](receipts/cook-receipt-20261014.json)

## Requirements

Acquire queue items 1–10 completely, at their pinned versions and in queue order. Run `fetch`,
then `verify`, then `audit-archives` per source, each as its own command with its exit status
recorded.

| Order | Source id | Mechanism | Publisher anchor | Expected |
|---|---|---|---|---|
| 1 | `petshop` | git @2e96f937 | git object IDs | 144 data files, 18,609,770 B, 68 `target.json` |
| 2 | `anomod` | Zenodo 18342898 | MD5 `30c58351…` | 1 file, 201,917,396 B |
| 3 | `msds` | Zenodo 3549604 | MD5 ×2 | 650,495,000 B |
| 4 | `rcaeval-zenodo` | Zenodo 14590730 | MD5 ×9 | 9 zips, 5,161,758,943 B, 735 cases |
| 5 | `rcaeval-hf` | HF resolve @afeacb11 | LFS SHA-256 ×1,335 + blob SHA-1 ×745 | 2,080 files, 3,442,007,684 B |
| 6 | `nezha` | git @d8140101 | git object IDs + `git fsck --full` | 1,297 tree entries |
| 7 | `cloud-opsbench` | HF resolve @1a02e543 | `manifest.json` SHA-256 + HF hashes | 27,110 files, 3,840,845,678 B |
| 8 | `agenticopseval` | aiops.cn `/-/raw/69cf3643…/` per file | AIOps2025 `checksums.md5`; RCA100 `summary.json` sizes | 18 archives, 9,741,961,087 B; RCA100 831 files |
| 9 | `dejavu` | Zenodo 6955909 | MD5 ×12 | 4,545,204,660 B |
| 10 | `rcabench-fse26` | Zenodo 17105974 | MD5 ×3 | 13,446,969,567 B |

## Files

- Create: `RCA_ROOT/data/raw/<id>/<version>/…` (ignored). Version is `zenodo-<record>`,
  `hf-<rev12>`, `git-<sha12>` or `gitlab-<sha12>`.
- Append: `RCA_ROOT/data/manifests/download_manifest.jsonl`.
- Create: `RCA_ROOT/data/provenance/<id>.json` (provisional).

## Steps

1. Run `python -I scripts/datasets/acquire.py plan --source <id>` for all ten sources. Confirm the
   total stays within budget; about 47.8 GB is expected.
2. For each source in order, run these as separate commands:

   ```
   python -I scripts/datasets/acquire.py fetch --source <id>
   python -I scripts/datasets/acquire.py verify --source <id>
   python -I scripts/datasets/acquire.py audit-archives --source <id>
   ```

3. Handle each source's specifics:
   - **AgenticOpsEval**: enumerate files from the GitLab tree API at the pinned SHA (831 RCA100
     files plus AIOps2025). AIOps2025 archives are `publisher-hash`. RCA100 files are compared with
     the `summary.json` per-case bytes where they are declared (`publisher-size`); otherwise they
     are `local-only`. Archive `README.md`, `LICENSE` and `overview.png` as well.
   - **RCAEval**: Zenodo is canonical. Leave the zips unextracted. The HF copy is recorded with
     `copy_of: rcaeval-zenodo` and its five known differences.
   - **Nezha**: list the actual label file names and record the README path defect.
   - **RCABench**: the platform zips are archived but never executed.
   - **MSDS**: record the label description as UNVERIFIED unless a label file is found in the zip
     listing.
4. Keep every README, LICENSE and dataset card byte-for-byte inside the raw tree.

## Checks

- Each source reports VERIFIED, with publisher-hash mismatches 0, LFS pointers 0, and expected
  counts and bytes equal to actual. A source that cannot reach that is PARTIAL with paths listed.
  RCA100 files that only have declared sizes report `publisher-size` and are never counted as
  hash-verified.
- `audit-archives` finds 0 unsafe members, and no extracted trees exist.
- A second `fetch` per source transfers 0 bytes.
- `git -C "F:/Nam/UIT/NT114 - NCKH" status --porcelain -- nt114-rca/nt114-rca/data/raw` prints
  nothing.

## Risk and rollback

- Interrupted sources resume from their `.part` files and state. Rollback deletes only
  `data/raw/<id>/<version>/` and its state, and keeps the manifest lines as history.
- A Zenodo outage at this point turns items 2–4, 9 and 10 into `PENDING: zenodo-unavailable`. The
  others proceed.
