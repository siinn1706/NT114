# Phase 12: export bundle and portability (2026-10-14)

## Outcome

Bundle `data/export/nt114-data-v1-20261014-6fdd9835` (3,263 data files plus `bundle.json` and
`MANIFEST.sha256`, 10.67 GB) is exported from the clean code commit `cd96e9e`. It holds the four
primary builds, 16 split manifests, all reports (audit, quality, condition matrices, eval units),
manifests, provenance and a copy of `configs/`. It verifies on Windows in place, after a full copy,
and as an upload to the private HF dataset `siinn1706/nt114-rca-data`. The Linux verification has
not run. The owner skipped a local Docker preflight, so it is the first step on the GPU machine.
The release record is [release-handoff-nt114-data-v1.md](release-handoff-nt114-data-v1.md).

It supersedes bundle `0a45570e`, which was exported from uncommitted code
(`rca_root_tracked: false`) and before the RCAEval exclusions were lifted.

## Checks run (Windows)

| Check | Result |
|---|---|
| `verify-bundle` in place | OK, exit 0 |
| Copy with `robocopy /E` to a separate directory | 3,265 files, 0 failed |
| `verify-bundle --deep` on the copy | OK (deep), exit 0 |
| `prep --data-home <copy>/parts status` | counts equal `bundle.json` (RCAEval 703/32/1 reject, Nezha 0/101, AIOps2025 381/19, RCA100 9/94); 16 splits |
| `prep --data-home <copy>/parts verify-splits` | 16 OK, exit 0 |
| `sha256sum --quiet -c MANIFEST.sha256` on the copy (Git bash) | exit 0 |
| HF remote against `MANIFEST.sha256` | private; 3,265/3,265 files, 0 missing, 0 extra, 0 mismatched (3,098 LFS sha256, rest git blob) at HF commit `c5c4a6dc` |
| `verify_portability.sh` step 0 (code tie) under Git bash | passes for this bundle; fails, as intended, for an older checkout and for a dirty export |
| Full test suite (Windows) | 230 passed |

The copy was deleted after the checks.

## bundle.json

- Builds: `rcaeval-2f4bf056cb8a` (adapter 1.0.1), `nezha-ea30424eba55` (1.0.3),
  `aiops2025-40efa9b2d22f` (1.0.1), `rca100-430dfff49e51` (1.0.2); schema 1.0.0.
- Licences: AgenticOpsEval (AIOps2025 CC BY-NC 4.0, RCA100 CC BY-NC-SA 4.0) "private transfer
  only"; Nezha MIT; RCAEval Zenodo CC-BY-4.0.
- Code: `git_commit` `cd96e9e8dc1906ee287cc54e9f02fe4b6b75a55e`, `git_dirty: false`,
  `rca_root_tracked: true`, `requirements-lock.txt` sha256 `0db90dc3…`.

## Next step on the GPU machine

Follow the commands in the release handoff. They clone the branch, create the venv from
`requirements-lock.txt`, download the bundle from HF and run
`bash scripts/verify_portability.sh <bundle>`. Record the output here, then set phase 12 to completed.
