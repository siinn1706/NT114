# Processing CLI, storage layout and portability

## 1. Storage tiers under `RCA_DATA_HOME` (default `RCA_ROOT/data`)

| Tier | Path | Mutability | Git | Transferred to GPU machine |
|---|---|---|---|---|
| Immutable raw | `raw/` | read-only; verified by `acquire.py verify` | ignored | optional (`--include-raw`) |
| Acquisition metadata | `manifests/`, `provenance/` | owned by acquisition tooling | tracked | yes |
| Intermediate | `work/extract/<source>/<version>/`, `work/profile/`, `work/runs/` | disposable, rebuildable | ignored | no |
| Canonical (model-visible) | `canonical/v1/<dataset>/visible/` | rebuilt only by `normalize` | ignored | yes |
| Evaluation-only | `canonical/v1/<dataset>/eval_only/` | rebuilt only by `normalize`/`validate` | ignored | yes, as a separate bundle part |
| Split manifests | `splits/<protocol>-<seed>-<hash8>/` | write-once | tracked | yes |
| Reports | `reports/` (profile, audit, quality, condition matrix, compatibility matrix) | regenerated per build | tracked (JSON ≤ 5 MB each) | yes |
| Training-ready references | `splits/.../assignments.jsonl` + `canonical/.../visible` | derived | — | yes |
| Export bundles | `export/<bundle_id>/` | write-once | ignored | this *is* the transfer unit |

`.gitignore` change (phase 04): keep `data/*`, add `!data/splits/` and `!data/reports/`.

## 2. CLI: `python -m rca.prep <command>` (`RCA_ROOT/src/rca/prep.py`)

Every command takes `--config configs/prep.yaml` (default) and `--data-home` (overrides config and
env). Exit codes: `0` ok, `2` usage error, `3` finished with quarantined or rejected items that
need attention, `4` integrity failure, `5` precondition missing (for example raw not VERIFIED).

| Command | Purpose | Reads | Writes | Idempotence |
|---|---|---|---|---|
| `profile --source <id> [--sample N]` | Inspect raw formats: members, columns, dtypes, time units, service ids, label formats | `raw/`, `manifests/` | `reports/profile/<source>.json` | overwrites its own report only |
| `extract --source <id> [--member-glob G]` | Safe extraction of tar.gz / split archives that cannot be streamed | `raw/` | `work/extract/...` + `.extract.json` receipt | skips members whose receipt entry (size, sha256) matches |
| `normalize --dataset <id> [--limit N] [--incident UID]` | Run the adapter; build canonical records and Parquet | `raw/`, `work/extract/`, configs | `canonical/v1/<id>/` | per-incident `.done` marker keyed by `input_digest` + `config_hash` |
| `validate --dataset <id>` | Re-run validators and overrides; rewrite `quality.jsonl` and `quality_state` | canonical | `eval_only/quality.jsonl`, `reports/quality-<id>.json` | deterministic |
| `audit` | Cross-dataset duplicates, lineage reconciliation, imbalance, leakage scans | all canonical, `manifests/incidents.jsonl` | `reports/audit-<build>.json` | deterministic |
| `conditions --dataset <id>` | Applicability matrix of missing-observability conditions | canonical | `reports/condition-matrix-<id>.json` | deterministic |
| `split --protocol P --seed S [--datasets ...]` | Build a split manifest | canonical, quality | `splits/<P>-<S>-<hash8>/` | refuses to overwrite; same inputs → same hash |
| `verify-splits` | Recompute hashes; detect stale builds | splits, canonical | stdout / exit code | read-only |
| `export --bundle NAME [--include-raw] [--parts visible,eval_only,splits,reports]` | Create the transfer bundle | everything selected | `export/<bundle_id>/` | write-once |
| `verify-bundle <dir>` | Integrity after transfer | bundle | stdout, exit 0/4 | read-only |
| `status` | One table: per dataset build state, counts per quality state, last split | all | stdout | read-only |

## 3. `configs/prep.yaml` (created in phase 04)

```yaml
schema_version: "1.0.0"
paths:
  data_home: null            # null → $RCA_DATA_HOME → <RCA_ROOT>/data
  raw: raw
  work: work
  canonical: canonical/v1
  splits: splits
  reports: reports
  export: export
processing:
  chunk_rows: 500000         # pyarrow batch size for CSV/Parquet streaming
  max_workers: 2             # incidents in parallel; memory-bound, not CPU-bound
  parquet: {compression: zstd, compression_level: 3, row_group_rows: 1000000}
windows:                     # stored slice for continuous-stream datasets (s)
  default: {pre_s: 1200, post_s: 600}
datasets:
  rcaeval:   {enabled: true,  source: rcaeval-zenodo, subsets: [RE1, RE2, RE3]}
  nezha:     {enabled: true,  source: nezha}
  aiops2025: {enabled: true,  source: agenticopseval}
  rca100:    {enabled: gate,  source: agenticopseval}   # gate = phase-02 decision file decides
  petshop:   {enabled: true,  source: petshop, tier: B}
  dejavu:    {enabled: true,  source: dejavu, tier: B}
  cloud-opsbench: {enabled: true, source: cloud-opsbench, tier: B}
extraction:
  max_member_bytes: 20000000000
  max_total_ratio: 200       # uncompressed / compressed bomb guard
  skip_patterns: ["__MACOSX/*", "*/._*", "._*", "*.DS_Store"]
```

The config hash is sha256 of the canonical JSON dump of this file after defaults are applied.

## 4. Safe extraction rules (`src/rca/safe_extract.py`)

Reject a member (and fail the command with exit 4) when: absolute path or drive letter, `..`
component, symlink, hardlink, device or FIFO, Windows-reserved name (`CON`, `NUL`, `COM1`...),
characters invalid on Windows (`<>:"|?*`), resulting path longer than 240 characters, member size
over `max_member_bytes`, or cumulative ratio over `max_total_ratio`. Skip (and count) members
matching `skip_patterns`. Write to `<dest>.part` then `os.replace`. Record each member in
`.extract.json` with size and sha256. Python's `tarfile` `filter="data"` is used in addition to
these checks. Extraction never runs code and never touches `raw/`.

## 5. Chunking, lazy loading, resumability

- CSV: `pyarrow.csv.open_csv` streaming with explicit column types where known; zip members are
  streamed through `zipfile.ZipFile.open` (no temporary copy).
- Parquet sources: `pyarrow.dataset` with a filter on the time column and column projection.
- Each incident is processed independently; peak memory = largest single incident member. The
  largest member size per source is recorded by `profile`, and `chunk_rows` is lowered if needed.
- The run ledger `work/runs/<run_id>.jsonl` logs each incident: start, end, status, digests. A
  killed run restarts from the first incident without a valid `.done` marker.
- `rca.store.CanonicalStore` opens `incidents.jsonl` eagerly (small) and Parquet lazily.

## 6. Portability rules

| Risk | Rule |
|---|---|
| Path separators, drive letters | All stored paths are relative POSIX; `pathlib` at runtime; validator invariant 11 |
| Text encoding (D2) | Every `open()` passes `encoding="utf-8"` (and `newline="\n"` when writing); JSON written with `sort_keys=True, ensure_ascii=False, separators=(",", ":")` |
| File names | Incident directories use `incident_uid` (`[a-z0-9.-]`); no `:` |
| Path length | ≤ 180 characters relative; `RCA_DATA_HOME` may be moved to a short path on Windows |
| Parquet compatibility | pyarrow version pinned in `requirements-lock.txt`; int64 ns, no tz-aware types, no pandas index metadata relied upon |
| Floating-point determinism | Canonical values are copied, not computed; derived stats (coverage) use integer arithmetic |
| Line endings | `.gitattributes` in `RCA_ROOT`: `*.jsonl text eol=lf`, `*.json text eol=lf`, `*.sha256 text eol=lf` |
| Python version | 3.12 on both machines; `requirements-lock.txt` generated from the prep machine; a Linux lock is generated on the GPU machine and diffed |

## 7. Export bundle and transfer

`export/<bundle_id>/` where `bundle_id = <name>-<YYYYMMDD>-<hash8>`.

> **As shipped:** `parts/` mirrors the data-home layout (`parts/canonical/v1/<id>/{visible,eval_only,_build.json}`,
> `parts/splits/`, `parts/reports/`, `parts/manifests/`, `parts/provenance/`) instead of the
> `parts/visible` / `parts/eval_only` split below, so every command runs unchanged with
> `--data-home <bundle>/parts`. `--include-raw` adds `parts/raw/` (hard-linked or copied).
> The planned tree was:

```text
bundle.json              datasets + build ids + schema/adapter versions + split ids + git commit of RCA_ROOT + lock-file hash
MANIFEST.sha256          "<sha256>  <relative path>" for every file (GNU sha256sum format, LF)
parts/visible/...        canonical/v1/<id>/visible + _build.json
parts/eval_only/...      canonical/v1/<id>/eval_only
parts/splits/...         split directories
parts/reports/...        reports
parts/manifests/...      acquisition manifests (checksums, incidents registry)
parts/provenance/...     per-source provenance and licences
parts/raw/...            only with --include-raw (hard-linked or copied; never modified)
```

Transfer with any byte-exact tool (`robocopy /E /Z`, `rsync -a --partial`, or `tar` of the bundle
directory). On the GPU machine: `python -m rca.prep verify-bundle <dir>` (recomputes every
sha256; exit 4 on any mismatch, missing or extra file), then `python -m rca.prep status
--data-home <dir>/parts` to confirm counts equal `bundle.json`. `sha256sum -c MANIFEST.sha256`
works as an independent check on Linux.

The bundle never includes `.venv`, `results/`, caches or `work/`.
