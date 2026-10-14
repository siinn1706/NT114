# Release handoff: nt114-data-v1 (2026-10-14)

## Outcome

Data release `nt114-data-v1` is prepared. The code is on GitHub, and the bundle is in a private
Hugging Face dataset repository. The bundle names the clean code commit that built it, and the
transfer checks pass on Windows. The release is **not yet accepted**: the mandatory Linux
verification on the GPU machine has not run, so phase 12, M1/M2 and the plan stay in progress.
Phase 08 (M3) is deferred.

The machine-readable record is `nt114-rca/nt114-rca/releases/nt114-data-v1.json`.

## Code and storage

| Item | Value |
|---|---|
| Code commit (bundle `code.git_commit`) | `cd96e9e8dc1906ee287cc54e9f02fe4b6b75a55e`, `git_dirty: false` |
| GitHub | `siinn1706/NT114` (private), `main` (fast-forward merged from `release/nt114-data-v1`, since deleted) |
| Hugging Face | `siinn1706/nt114-rca-data` (private dataset), path `nt114-data-v1-20261014-6fdd9835/`, commit `c5c4a6dc455cac5d0545b98d8d40266b2bbdaa05`; 3,265/3,265 remote files match the local bundle (3,098 by LFS sha256, the rest by git blob hash) |
| `requirements-lock.txt` sha256 | `0db90dc34b62f9d6fce4f226ff3d3ff4c55bc48e4456b3f7852d3c0729e64db0` |

GitHub holds the source, tests, configs, schema, scripts, docs, plans, the release manifest, and the small
label-free data manifests (`data/splits`, `data/manifests` without `incidents.jsonl`,
`data/provenance`, `data/reports` without `condition-matrix-*`). Hugging Face holds the full bundle:
canonical data, eval-only labels, split manifests, reports, manifests, provenance and checksums.

## Bundle

| Item | Value |
|---|---|
| Bundle ID | `nt114-data-v1-20261014-6fdd9835` (schema 1.0.0) |
| `MANIFEST.sha256` sha256 | `1a51a7c5e2e611aeb6a2ce1dd88267e03f03357db94eccdd5544cca4345a5712` |
| `bundle.json` sha256 | `26d10fa7707715769f0c430e4b3bca1024b6500bcd680fe01eeef7c22f3ac7ae` |
| Size | 10,673,010,725 bytes; 3,263 data files plus `bundle.json` and `MANIFEST.sha256` |
| Supersedes | `nt114-data-v1-20261014-0a45570e`, which was exported from uncommitted code before the exclusion lift |

## Builds and counts

| Dataset | Build (adapter) | Raw | Accepted (ACCEPT / AWW) | Rejected | Independent injections | Evaluation-eligible |
|---|---|---|---|---|---|---|
| RCAEval | `rcaeval-2f4bf056cb8a` (1.0.1) | 736 | 735 (703 / 32) | 1 duplicate | 735 | 735 primary, 0 excluded |
| Nezha | `nezha-ea30424eba55` (1.0.3) | 101 | 101 (0 / 101) | 0 | 101 | 101; 97 for `metrics_only` |
| AIOps2025 | `aiops2025-40efa9b2d22f` (1.0.1) | 400 | 400 (381 / 19) | 0 | 400 | tier A 318 (73 set-scoring-only, so 245 top-1), B 82; report with and without the 5 short-log incidents |
| RCA100 | `rca100-430dfff49e51` (1.0.2) | 103 | 103 (9 / 94) | 0 | 86 | 103 tasks, 86 tier A; statistics on 86 injections |

No record is quarantined. Label validity is 100 %. The audit `audit-9338d463a84f.json` reports 0
leakage hits and 0 split errors.

## Exclusion policy

`configs/eval_exclusions.yaml` has no active entry. The four RCAEval shared-cluster incidents
(`rcaeval.4303ec727622942a`, `d5bb2ac1b3c6bb37`, `4d62cb4318958396`, `76e86a2d6f0e1dc1`) were
lifted after `tests/test_realdata_identity.py` passed, and they keep `status: lifted` with the
reason. Other dataset-specific rules are in `design/handoff-llm-jev.md` §2a/§2b: AIOps2025 is
reported with and without the 5 short-log incidents; RCA100 uses injection units, equal weights,
cluster bootstrap and majority-class/alert-entity baselines.

## Active split manifests (seed 0)

`eval-only-aiops2025-0-f92dd409`, `eval-only-nezha-0-38cde4e0`, `eval-only-rca100-0-b8a32300`,
`eval-only-rcaeval-0-87d5bcc3`, `loso-rcaeval-online-boutique-0-17c12b9c`,
`loso-rcaeval-sock-shop-0-1cf7f474`, `loso-rcaeval-train-ticket-0-066d5f53`,
`within-aiops2025-grouped-0-f92dd409` (`headline_ok: false`, degenerate),
`within-aiops2025-retrieval-0-bb231eaa`, `within-rca100-grouped-0-753fb47c`,
`within-rca100-retrieval-0-3bfc8743`, `within-rcaeval-grouped-0-e9b2c81c`,
`within-rcaeval-retrieval-0-45ef97c3`, `xdata-rcaeval-to-aiops2025-0-730c1c48`,
`xdata-rcaeval-to-nezha-0-28246781`, `xdata-rcaeval-to-rca100-0-a2a83b78`.

## Linux verification (GPU machine)

```bash
git clone https://github.com/siinn1706/NT114.git && cd NT114/nt114-rca/nt114-rca
python3.12 -m venv .venv && . .venv/bin/activate && pip install -r requirements-lock.txt
hf auth login   # account with access to the private dataset
hf download siinn1706/nt114-rca-data --repo-type dataset --local-dir ~/nt114-rca-data
bash scripts/verify_portability.sh ~/nt114-rca-data/nt114-data-v1-20261014-6fdd9835
```

The script runs these steps:

0. It checks that the checkout contains the bundle commit and has no `src/`, `configs/` or `schemas/` changes since that commit.
1. It runs `verify-bundle` and `sha256sum -c`.
2. It runs `verify-bundle --deep`.
3. It runs `status` and `verify-splits` on the bundle's `parts/`. Compare the `status` counts with `bundle.json`.
4. It runs the fast test suite.
5. It runs a synthetic `run_grid prepare` and `run` with the mock backend, without network.

Record the output in `reports/phase-12-portability.md`. Phase 12, M1/M2 and the plan can then be
set to completed.

## Restricted data

- AgenticOpsEval data (AIOps2025 CC BY-NC 4.0, RCA100 CC BY-NC-SA 4.0) may be used only for non-commercial research.
  It may be shared privately with the team. RCAEval data is CC BY 4.0 and Nezha data is MIT.
- The owner chose to store the full bundle, including `eval_only` labels, in a **private** HF
  repository. It must stay private, with access limited to the team. The GPU machine has the same
  constraints: non-commercial use, and no copy to public storage.
- Labels stay isolated. Training and inference read only `visible/` data and train-role splits.
  `eval_only/` is read only by scoring, ablation and split code (import-boundary test). The RCA100
  answer key must never enter prompts or public repositories. The GitHub repository has no
  eval-only labels: `incidents.jsonl` and the `condition-matrix-*` reports are git-ignored.

## Remaining blockers

1. Linux verification on the GPU machine (mandatory acceptance gate).
2. The owner's final review of the six service aliases. The evidence is in
   `docs/dataset_quality_audit.md`. `reviewed_by` still says "owner to confirm".
3. Phase 08 / M3 (auxiliary B datasets) is deferred.

The next plan covers RCA LLM inference, confidence estimation and Jev as the mandatory post-LLM
decision layer. It must not start training until gate 1 passes.
