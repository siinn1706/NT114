"""Canonical incident contract (schema v1): validation, invariants, label denylist, ids.

The JSON Schema in `schemas/canonical_incident.v1.schema.json` is the source of truth; this module
loads it once and adds the cross-field invariants that JSON Schema cannot express.
"""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

SCHEMA_VERSION = "1.0.0"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "canonical_incident.v1.schema.json"

MODALITIES = ("metrics", "logs", "traces")
STATUSES = ("present", "natural_absent", "empty", "corrupted")
STATES = ("ACCEPT", "ACCEPT_WITH_WARNINGS", "QUARANTINE", "REJECT")
SPLIT_STATES = ("ACCEPT", "ACCEPT_WITH_WARNINGS")
SEVERITY_RANK = {"info": 0, "warn": 1, "quarantine": 2, "reject": 3}
STATE_OF_SEVERITY = {0: "ACCEPT", 1: "ACCEPT_WITH_WARNINGS", 2: "QUARANTINE", 3: "REJECT"}

UID_RE = re.compile(r"^[a-z0-9-]+\.[0-9a-f]{16}$")
TS_MIN_NS = 1_420_070_400 * 10**9   # 2015-01-01 UTC
TS_MAX_NS = 1_893_456_000 * 10**9   # 2030-01-01 UTC
MAX_RELPATH = 180

# Names that must never appear as a key or column in the model-visible zone.
LABEL_DENYLIST = frozenset({
    "root", "root_cause", "root_service", "root_service_ids", "primary_root_service", "root_cause_entity",
    "fault", "fault_type", "fault_family", "fault_cell", "fault_description", "fault_category",
    "label", "labels", "label_artifacts", "gt", "ground_truth", "answer", "answer_key",
    "key_observations", "key_metrics", "inject_pod", "inject_type", "culprit", "source_incident_id",
})
_DENY_TOKENS = frozenset({"root", "fault", "label", "gt", "answer", "culprit"})

def denylisted(name: str) -> bool:
    n = str(name).lower()
    return n in LABEL_DENYLIST or any(t in _DENY_TOKENS for t in n.split("_"))


def make_incident_uid(dataset_id: str, key: str) -> str:
    return f"{dataset_id}.{hashlib.sha256(f'{dataset_id}|{key}'.encode()).hexdigest()[:16]}"


@lru_cache(maxsize=1)
def _schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=None)
def _validator(kind: str):
    from jsonschema import Draft202012Validator
    root = _schema()
    if kind not in root["$defs"]:
        raise KeyError(kind)
    return Draft202012Validator({"$ref": f"#/$defs/{kind}", "$defs": root["$defs"]})


def validate_record(kind: str, obj: dict) -> list[str]:
    """JSON Schema errors for one record of `kind` (IncidentRecord, LabelRecord, ...)."""
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
            for e in sorted(_validator(kind).iter_errors(obj), key=lambda e: list(map(str, e.absolute_path)))]


def is_relpath(p: str) -> bool:
    return (bool(p) and len(p) <= MAX_RELPATH and "\\" not in p and not p.startswith("/")
            and not re.match(r"^[A-Za-z]:", p) and ".." not in p.split("/"))


def _walk_keys(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, f"{prefix}/{k}"
            yield from _walk_keys(v, f"{prefix}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_keys(v, f"{prefix}/{i}")


def check_incident(rec: dict, label: dict | None = None, data_home: Path | None = None) -> list[str]:
    """Cross-field invariants 3-8 and 11 for one incident (and its label when given)."""
    errs = []
    for k, where in _walk_keys(rec):
        if denylisted(k):
            errs.append(f"inv3 denylisted key {where}")
    for m in MODALITIES:
        mi = rec["telemetry"][m]
        st, path, rows = mi["status"], mi["path"], mi["rows"]
        if st == "present" and not (path and rows > 0):
            errs.append(f"inv4 {m}: present needs path and rows>0")
        if st == "present" and data_home is not None and not (data_home / path).is_file():
            errs.append(f"inv4 {m}: file missing {path}")
        if st == "empty" and rows != 0:
            errs.append(f"inv4 {m}: empty needs rows==0")
        if st in ("natural_absent", "empty", "corrupted") and rows != 0:
            errs.append(f"inv4 {m}: {st} needs rows==0")
        if st == "natural_absent" and path is not None:
            errs.append(f"inv4 {m}: natural_absent needs path==null")
        if path is not None and not is_relpath(path):
            errs.append(f"inv11 {m}: bad path {path!r}")
        for t in (mi["t_min_ns"], mi["t_max_ns"]):
            if t is not None and not (TS_MIN_NS <= t < TS_MAX_NS):
                errs.append(f"inv6 {m}: timestamp {t} out of range")
    w, a = rec["time"]["window"], rec["time"]["anchor_ns"]
    if w["start_ns"] is not None and w["end_ns"] is not None:
        if not (w["start_ns"] < a <= w["end_ns"]) and not (w["clipped_start"] or w["clipped_end"]):
            errs.append("inv5 anchor outside window")
    if not (TS_MIN_NS <= a < TS_MAX_NS):
        errs.append("inv6 anchor out of range")
    svcs = rec["candidates"]["services"]
    if svcs != sorted(set(svcs)):
        errs.append("inv7 candidates not sorted/unique")
    from .data import canon
    bad = [s for s in svcs if canon(s) != s]
    if bad:
        errs.append(f"inv7 candidates not canon-stable: {bad}")
    if label is not None:
        if label["incident_uid"] != rec["incident_uid"]:
            errs.append("inv2 label uid mismatch")
        rc = label["root_cause"]
        if label["eval_tier"] == "A" and rec["quality_state"] not in ("QUARANTINE", "REJECT"):
            p = rc["primary_root_service"]
            if (p is not None and p not in svcs) or (p is None and not set(rc["root_service_ids"]) <= set(svcs)):
                errs.append("inv8 A-tier root not in candidates without QUARANTINE")
        g = label["group"]
        if (g["copy_of"] or g["duplicate_of"]) and rec["quality_state"] != "REJECT":
            errs.append("inv9 duplicate not REJECT")
    return errs


def validate_dataset(ds_root: Path, data_home: Path | None = None) -> list[str]:
    """Invariants 1-11 over one built dataset directory `canonical/v1/<dataset_id>`.

    Invariant 10 (rebuild determinism) is checked by the build driver and tests, not here."""
    from .store import read_jsonl
    errs: list[str] = []
    inc = read_jsonl(ds_root / "visible" / "incidents.jsonl")
    lab = read_jsonl(ds_root / "eval_only" / "labels.jsonl")
    qual = read_jsonl(ds_root / "eval_only" / "quality.jsonl")
    src = read_jsonl(ds_root / "eval_only" / "source_index.jsonl")
    for kind, recs in (("IncidentRecord", inc), ("LabelRecord", lab), ("QualityRecord", qual),
                       ("SourceIndexRecord", src)):
        for r in recs:
            errs += [f"inv1 {kind} {r.get('incident_uid')}: {e}" for e in validate_record(kind, r)]
    uids = [r["incident_uid"] for r in inc]
    if len(set(uids)) != len(uids):
        errs.append("inv2 duplicate incident_uid")
    if uids != sorted(uids):
        errs.append("inv2 incidents not sorted by uid")
    for name, recs in (("labels", lab), ("quality", qual), ("source_index", src)):
        if [r["incident_uid"] for r in recs] != uids:
            errs.append(f"inv2 {name} uid list differs from incidents")
    labels = {r["incident_uid"]: r for r in lab}
    for r in inc:
        errs += [f"{r['incident_uid']}: {e}" for e in check_incident(r, labels.get(r["incident_uid"]), data_home)]
    return errs
