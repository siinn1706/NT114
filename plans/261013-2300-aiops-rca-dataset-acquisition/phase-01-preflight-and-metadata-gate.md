# Phase 01: Preflight, ignore contract, metadata and Zenodo re-verification

Status: done (2026-10-14). Receipt: [cook receipt](receipts/cook-receipt-20261014.json)

## Requirements

- Set `RCA_ROOT = nt114-rca/nt114-rca` (owner decision D1; do not flatten). Record it in
  `data/manifests/run-context.json`.
- Take an attempt inventory **before** any change.
- Ignore contract: `data/raw/` and `data/.state/` are ignored, while `data/manifests/` and
  `data/provenance/` are trackable.
- Re-read the metadata of every source in [sources-seed.json](research/sources-seed.json), record
  any drift, and never overwrite a pin silently.
- Zenodo backoff (D6): 5 attempts with exponential backoff over at least 30 minutes, then one
  attempt per hour for up to 24 hours. An unreachable source becomes `PENDING: zenodo-unavailable`,
  never REJECTED, and its earlier verified metadata stays in the seed.
- Run one bounded saturation round for PENDING-DISCOVERY families: LO2, TrainTicketTrace,
  TraceRCA and AIOps 2022 raw.

## Files

- Modify: `RCA_ROOT/.gitignore`. Replace the single line `data/` with the block below and leave
  the other lines byte-identical; keep the preimage in the receipt.

  ```
  data/*
  !data/manifests/
  !data/provenance/
  ```

- Create: `plans/261013-2300-aiops-rca-dataset-acquisition/attempt-before.json`.
- Create: `RCA_ROOT/data/manifests/run-context.json`. It records RCA_ROOT, `budget_gb` (250),
  `reserve_gb` (100), free space, tool versions, the date and the owner decisions D1–D8.
- Create: `RCA_ROOT/data/provenance/_metadata-recheck-<date>.json`.

## Steps

1. Take the inventory:

   ```
   python -X utf8 "C:/Users/Siinn/.claude/skills/nckh-plan/references/_shared/scripts/check-receipt.py" inventory --root "nt114-rca/nt114-rca" --output "plans/261013-2300-aiops-rca-dataset-acquisition/attempt-before.json"
   ```

2. Run `df -h /f` and record the result. Abort if free space is below `budget_gb + reserve_gb`.
3. Edit `.gitignore`. Then run these two commands separately:

   ```
   git check-ignore -v "nt114-rca/nt114-rca/data/raw/x"
   git check-ignore "nt114-rca/nt114-rca/data/manifests/x"
   ```

   The first must exit 0 and the second must exit 1.
4. Re-read metadata per kind:
   - HF: `https://huggingface.co/api/datasets/<repo>/revision/<rev>?blobs=true`
   - Zenodo: `/api/records/<id>`
   - GitHub: `gh api repos/<repo>/commits/<rev>`
   - aiops.cn: `/api/v4/projects/<id>/repository/commits/<rev>`
   - Drive: the `embeddedfolderview` listing for the OpenRCA folder

   Compare revision, files, bytes, hashes and licence, and mark each source
   `match | drift | unreachable`.
5. Apply the Zenodo backoff for records 14590730, 17105974, 18342898, 6955909, 3549604 and
   7615394.
6. Saturation round on OpenAlex: search `"root cause analysis" AND (dataset OR benchmark) AND
   microservice` from 2024 onward. Add a family only when it has a primary link and a licence.

## Checks

- The inventory's mtime precedes every other change.
- Both `git check-ignore` exit codes match the specification and are recorded separately.
- The recheck file lists every seed source with a status. A drifted source has its new pin
  recorded beside the old one.
- No source is marked REJECTED because it was unreachable.

## Risk and rollback

- Restore `.gitignore` from the receipt preimage.
- Drift and outages change states, not the plan (R1, R9).
