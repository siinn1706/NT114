# Phase 06: Integrity, mirror completeness and lineage

Status: done (2026-10-14). Receipt: [cook receipt](receipts/cook-receipt-20261014.json)

## Requirements

- Re-verify every acquired file from disk, independent of the download-time hashes. Each line in
  the checksum manifest keeps its `integrity_level` (`publisher-hash`, `publisher-size`,
  `local-only`, `host-reported`) so local hashes are never presented as publisher-authenticated
  (owner decision D8).
- Build the incident registry `data/manifests/incidents.jsonl`, with one row per incident per copy
  and these fields: `incident_id`, `source_id`, `lineage_group`, `system`, `root_cause_entity`,
  `fault`, `fault_cell`, `inject_or_start_time`, `modalities_present`, `label_file`,
  `label_in_path`, `copy_of`.
- Re-prove HF-mirror completeness against the canonical release (owner decision D7) for RCAEval
  and Cloud-OpsBench, and the other cross-copy identities in
  [lineage-and-overlap.md](research/lineage-and-overlap.md).
- All of this reads labels, listings and metadata only. Telemetry is not transformed.

## Files

- Create: `RCA_ROOT/data/manifests/checksums.sha256`, in `sha256  relative/path` format and
  sorted, plus `checksums-levels.tsv` (`relative/path<TAB>integrity_level<TAB>anchor`).
- Create: `RCA_ROOT/data/manifests/incidents.jsonl`.
- Create: `RCA_ROOT/data/manifests/mirror-completeness-rcaeval.json` and
  `mirror-completeness-cloud-opsbench.json`.
- Create: `RCA_ROOT/data/manifests/lineage-report.json`, with group counts, identities and
  anomalies.

## Steps

1. Recompute the SHA-256 of every file under `data/raw/` into `checksums.sha256`, then run
   `sha256sum -c` on it as a separate command.
2. RCAEval completeness (HF @afeacb11 against Zenodo 14590730). Read zip central directories and
   member CRC32 in memory; never extract. Expected result, from
   [the planning comparison](research/evidence/rcaeval-zenodo-vs-hf-comparison.txt):
   - `RE3-TT/ts-route-service_f3_1/{1,2,3}` on Zenodo maps to HF `re3tt_ts-route-service_f3_{4,5,6}`
     with equal `inject_time.txt` CRC32 (69008df7, d1ddf769, 9554f34a).
   - `re2tt_ts-auth-service_cpu_1` has no `logs.csv` on HF (Zenodo: 181,151,448 B).
   - 13 RE3-SS header-only `traces.csv` (116 B, CRC 566ce7f8) exist only on Zenodo.
   - 8 `root_cause.txt` files exist only on HF (RE3-SS).
   - Auxiliary files (logts, tracets_err, tracets_lat, cluster_info, pod-node, simple_*,
     postprocess log, png) exist only on Zenodo.

   Any further difference is reported as drift. Verdict: HF is a **derived, incomplete** copy, and
   Zenodo stays canonical.
3. Cloud-OpsBench completeness (HF @1a02e543 against GitHub source commit ea05dafb): compare the
   27,104 artefact paths. For the 27,054 non-LFS files compare git blob IDs. For the 50 HF-LFS
   files compute the git blob SHA-1 locally (`git hash-object` on the downloaded file) and compare
   with the GitHub tree blob ID. Expected: 27,104/27,104 paths and blob IDs equal. Record that
   GitHub `main` moved to 6b986be4 and do not follow it.
4. Extract incident rows from label artefacts only:
   - RCAEval: directory names plus `inject_time.txt` (and `root_cause.txt` where present).
   - AIOps2025: `groundtruth.jsonl`. RCA100: `cases/<id>/gt.json` and `answer_key/`.
   - Nezha: the fault lists. PetShop: `target.json`. Cloud-OpsBench: its case index.
   - OpenRCA (if acquired): `record.csv` inside each zip, read in memory; expect 335 records in
     total across the three systems.
   - Other sources: their documented label files, or `UNKNOWN`.
5. Other identities:
   - AIOps2025 against aiops.cn project 107: metadata only. Re-read the blob IDs of
     `groundtruth.jsonl` and `input.json` and record them.
   - OpenRCA against AIOps 2020/2021 metadata: compare date ranges and the failure lists downloaded
     in phase 05. No telemetry comparison is done, because those archives are not acquired.
6. Count the independent incidents per lineage group. Rows with `copy_of` set are excluded, and
   `fault_cell` repetition counts are reported separately.
7. Record known anomalies (the RCAEval differences above, the Nezha label path defect, the
   OpenRCA missing-telemetry filter). None of them is repaired.

## Checks

- `sha256sum -c data/manifests/checksums.sha256` exits 0, with exit status recorded.
- Every line in `checksums-levels.tsv` has one of the four levels, and no `local-only` line has a
  publisher anchor.
- The RCAEval report lists exactly the five known difference classes, or reports the extra
  differences as drift.
- The Cloud-OpsBench report shows 27,104/27,104 equal blob IDs, or lists every mismatch.
- `lineage-report.json` reports `independent_incidents` per group, and the total excludes every
  `copy_of` row.
- Running the step twice produces byte-identical `incidents.jsonl`, which shows it is
  deterministic.

## Risk and rollback

- These are read-only checks. The outputs are manifest files that can be regenerated.
- A mismatch is reported as data, never "fixed".
