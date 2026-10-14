# Phase 07: Catalog, provenance docs and reproducibility check

Status: done (2026-10-14). Receipt: [cook receipt](receipts/cook-receipt-20261014.json)

## Requirements

- Finalise one provenance record per source in `data/provenance/<id>.json` with these fields:
  canonical source URL, publication/DOI, publisher/maintainer, licence text and its evidence path,
  exact artefact URLs, revision or version, retrieval date, file count (expected and verified),
  total bytes, hash list reference, `integrity_level` summary, label and modality availability,
  known limitations, lineage edges, verification state with reason, and decisions taken. Unknown
  values are `UNKNOWN`.
- Generate `data/manifests/dataset_catalog.json` and `data/manifests/not-acquired.json` from
  provenance with `acquire.py catalog`. The not-acquired register lists every eligible dataset
  that is not VERIFIED or VERIFIED-LOCAL-ONLY, with its exact reason, state and next action
  (owner requirement: report every eligible dataset not acquired).
- Write four docs in `RCA_ROOT/docs/`. They hold only claims present in provenance or the
  research files, with links rather than copied tables where possible.
  - `dataset_discovery.md`: the search log, the catalog and the A/B/C decisions.
  - `dataset_quality_audit.md`: scores, label validity, anomalies, mirror completeness and
    contamination flags.
  - `acquisition_plan.md`: commands per source, budget, order and reproduce-from-clean-checkout
    steps.
  - `dataset_provenance.md`: a per-source summary table linking the JSON records, with integrity
    levels shown separately, and the not-acquired register.
- Prove reproducibility with a dry run from a clean copy of the tracked files.

## Files

- Create: `RCA_ROOT/docs/dataset_discovery.md`, `dataset_quality_audit.md`, `acquisition_plan.md`
  and `dataset_provenance.md`.
- Create or update: `RCA_ROOT/data/manifests/dataset_catalog.json`,
  `data/manifests/not-acquired.json` and `data/provenance/*.json`.
- Modify: `RCA_ROOT/README.md`, §5 only. Add one line that links `docs/acquisition_plan.md`.
  This is the only README edit, and the owner can veto it.

## Steps

1. Run `python -I scripts/datasets/acquire.py catalog`, then `status`, as separate commands.
2. Write the docs from provenance. Keep each under 800 lines.
3. Reproducibility dry run: copy the tracked files (scripts, registry, manifests, provenance)
   into a scratch directory with no `data/raw/`. Then run
   `python -I scripts/datasets/acquire.py plan --source <id>` for every VERIFIED and
   VERIFIED-LOCAL-ONLY source. Each plan must resolve the identical URL or file-ID list and
   expected hashes recorded in the manifest. No download is needed for this check.
4. Compare against `attempt-before.json`:

   ```
   check-receipt.py verify --receipt <receipt> --before plans/261013-2300-aiops-rca-dataset-acquisition/attempt-before.json --workspace nt114-rca/nt114-rca
   ```

   The only changed files may be `.gitignore`, `README.md` §5, and the new `scripts/datasets/*`,
   `tests/test_datasets_acquire.py`, `docs/*`, `data/manifests/*` and `data/provenance/*`.
5. Run the plan's acceptance checklist items 1–12 and record each result with its evidence path in
   a cook receipt.

## Checks

- The catalog lists every registry source with exactly one state, and every non-VERIFIED state
  carries a reason and a next action.
- `not-acquired.json` contains at least the rows of the plan's "Eligible datasets not acquired"
  table, updated with run outcomes (for example `PENDING: budget` or `PENDING: drive-quota`).
- The dry-run URL and hash lists equal the recorded ones for 100% of the verified sources.
- `src/`, `configs/` and `tests/test_pipeline.py` have hashes unchanged from the inventory.
- `git -C "F:/Nam/UIT/NT114 - NCKH" status --porcelain` lists no file under `data/raw/`,
  `data/.state/` or `.venv-acquire/`.
- The docs cite provenance paths. A spot check of 5 random claims against provenance gives 5
  matches.

## Risk and rollback

- The docs and manifests are additive. Rollback deletes the new files and reverts the README §5
  line.
- Owner review stays `pending-personal-review` until the owner scores the result. The cook receipt
  must not claim acceptance on the owner's behalf.
