---
phase: 3
title: "Canonical schema, store and adapter contract"
status: completed
priority: P1
effort: "2d"
dependencies: [2]
---

# Phase 03: Canonical schema, store and adapter contract

## Goal
Implement the versioned `CanonicalIncident` contract, its validator, the deterministic reader and
writer, the service-identity module and the adapter interface, all test-first on synthetic
records, with no dataset-specific code.

## Inputs
- [design/canonical-schema.md](design/canonical-schema.md), [design/adapter-contracts.md](design/adapter-contracts.md) §1–2
- Phase-02 profiles (to confirm every field has a source in at least one A dataset)

## Outputs
- JSON Schema v1.0.0 and the Python mirror; store, identity and adapter-base modules; tests green.

## Files
- Create: `RCA_ROOT/schemas/canonical_incident.v1.schema.json` — `$defs` for IncidentRecord,
  ModalityInfo, LabelRecord, QualityRecord, BuildReceipt (`_build.json`), SplitManifest
- Create: `RCA_ROOT/src/rca/schema.py` — `SCHEMA_VERSION`, enums, `validate_record(kind, obj)`,
  `validate_dataset(root)` (invariants 1–11), `LABEL_DENYLIST`, `DECISION_STATE_ALLOWED_KEYS`,
  `make_incident_uid(dataset_id, key)`
- Create: `RCA_ROOT/src/rca/store.py` — `write_jsonl_atomic`, `read_jsonl`, `dump_json`
  (sorted keys, UTF-8, LF), `ParquetSink` (streaming writer with fixed Arrow schemas per modality),
  `table_content_sha256`, `CanonicalStore` (visible incidents, lazy telemetry, labels, quality,
  filters by quality state)
- Create: `RCA_ROOT/src/rca/identity.py` — `ServiceMap`, rules `alias` / `pod-to-deployment` /
  `canon`, collision and idempotence checks; imports `canon` from `rca.data` (no copy)
- Create: `RCA_ROOT/src/rca/adapters/__init__.py` (registry: name → class), `RCA_ROOT/src/rca/adapters/base.py`
  (`RawRef`, `Finding`, `DiscoveredIncident`, `LabelDraft`, `TimeInfo`, `Adapter` protocol,
  `MemberSource` abstraction that reads members from a directory, a zip, or an extracted tree)
- Create: `RCA_ROOT/configs/service_aliases.yaml` — empty mapping with a header comment on review rules
- Create: `RCA_ROOT/tests/test_schema.py`, `RCA_ROOT/tests/test_store.py`, `RCA_ROOT/tests/test_identity.py`
- Preserve: `src/rca/data.py` (only imported)

## Tasks
1. Write T03/T04/T23 first from the examples in the design doc (valid records, one failing
   record per invariant, UTF-8 non-ASCII round trip, null handling, int64 ns preservation).
2. Author the JSON Schema with `additionalProperties: false` on writer-side definitions.
3. Implement `schema.py`: load the JSON Schema once (path relative to the package via
   `importlib.resources`-style lookup from `RCA_ROOT/schemas`), validate with `jsonschema`, then
   the cross-field invariants. Denylist matching is on exact key names and `_`-separated tokens.
4. Implement `store.py`: Arrow schemas from design §4 as module constants; `ParquetSink` writes to
   `<path>.part`, then `os.replace`; `table_content_sha256` hashes the canonical row
   serialization defined in design §4 (combine chunks, sort, per-column name/type/validity/values
   with fixed endianness), so the hash ignores batch boundaries and IPC framing. T04 asserts the
   same digest for one table written with three different batch sizes. JSONL writer sorts records by `incident_uid`.
5. Implement `identity.py` with the three rules and checks; `canon(id) == id` enforced.
6. Implement `adapters/base.py` and the registry; `MemberSource` supports `dir://`, `zip://` and
   `extracted://` refs and always opens members in binary mode, decoding text as UTF-8 with
   `errors="strict"` (decode errors become `PARSE_ERROR` findings).

## Tests
- T03 `test_schema.py`, T04 `test_store.py`, T23 `test_identity.py`
  (pod patterns, collisions, alias override, idempotence, non-service `infra` columns).

## Completion criteria
- Fast suite green; T01 still green.
- Two consecutive writes of the same synthetic dataset produce byte-identical JSONL and equal
  `content_sha256`.
- Schema file validates itself against the 2020-12 meta-schema.

## Risks and rollback
- Over-design of the schema: every field must be filled by at least one A adapter or be
  explicitly optional; fields with no producer are removed before closing the phase.
- Rollback: new files only; delete them.
