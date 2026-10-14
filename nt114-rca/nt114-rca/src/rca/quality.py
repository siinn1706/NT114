"""Per-incident validators, quality-state roll-up and reviewed overrides.

Dataset-level checks (duplicates across incidents, window overlap, lineage) live in `rca.audit`.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from .adapters.base import Finding
from .schema import MODALITIES, SEVERITY_RANK, STATE_OF_SEVERITY, STATES, check_incident, validate_record

VALIDATOR_VERSION = "1.0.0"

# code -> default severity (some codes choose their severity from a measured rate; see callers)
FINDING_CODES = {
    "SCHEMA_INVALID": "reject", "LABEL_UNPARSEABLE": "reject", "LABEL_INVALID": "reject", "DUPLICATE": "reject",
    "NO_TELEMETRY": "reject", "ROOT_NOT_CANDIDATE": "quarantine", "SERVICE_ID_COLLISION": "quarantine",
    "UNEXPLAINED_EXTRA_CASE": "quarantine", "ADAPTER_EXCEPTION": "quarantine", "TS_OUT_OF_RANGE": "warn",
    "TS_COLUMN_OFFSET": "warn", "TRACE_TIME_MISMATCH": "warn", "ANCHOR_OUTSIDE_WINDOW": "quarantine",
    "WINDOW_CLIPPED": "warn", "LOW_COVERAGE": "warn", "PRE_WINDOW_SHORT": "warn", "BASELINE_CONTAMINATED": "warn",
    "METRIC_NONFINITE": "info", "METRIC_CONSTANT": "info", "UNIT_SUSPECT": "warn", "EMPTY_MODALITY_FILE": "info",
    "PARSE_ERROR": "warn", "TRACE_ORPHAN_SPANS": "info", "LOG_LEVEL_MISSING": "info",
    "LABEL_ARTIFACT_PRESENT": "info", "MULTI_ROOT": "info", "NON_SERVICE_ENTITY": "info",
    "INVARIANT_VIOLATION": "quarantine", "ANCHOR_FIELD_DISAGREE": "info", "METRIC_GROUP_DROPPED": "info",
}


def finding(code: str, detail: str = "", modality: str | None = None, severity: str | None = None,
            evidence_ref: str | None = None) -> Finding:
    if code not in FINDING_CODES:
        raise KeyError(code)
    return Finding(code, severity or FINDING_CODES[code], modality, detail, evidence_ref)


def roll_up(findings) -> str:
    worst = max((SEVERITY_RANK[f["severity"] if isinstance(f, dict) else f.severity] for f in findings), default=0)
    return STATE_OF_SEVERITY[worst]


def validate_incident(rec: dict, label: dict | None, stats: dict, cfg: dict) -> list[Finding]:
    """Per-incident checks on the in-memory records and table stats.

    stats: {modality: {"rows", "ts_out_of_range", "nonfinite", "orphan_spans", "has_level", ...}}"""
    out: list[Finding] = []
    for kind, obj in (("IncidentRecord", rec), ("LabelRecord", label)):
        if obj is not None:
            errs = validate_record(kind, obj)
            if errs:
                out.append(finding("SCHEMA_INVALID", f"{kind}: {errs[0]} (+{len(errs) - 1})"))
    tel = rec["telemetry"]
    if all(tel[m]["status"] in ("natural_absent", "empty") for m in MODALITIES):
        out.append(finding("NO_TELEMETRY", "no modality has rows"))
    anchor = rec["time"]["anchor_ns"]
    present = [tel[m] for m in MODALITIES if tel[m]["status"] == "present"]
    if present:
        lo, hi = min(m["t_min_ns"] for m in present), max(m["t_max_ns"] for m in present)
        if not (lo <= anchor <= hi):
            out.append(finding("ANCHOR_OUTSIDE_WINDOW", f"anchor {anchor} not in [{lo}, {hi}]"))
        ev = (cfg.get("windows") or {}).get("evidence", {"pre_s": 600})
        pre = (anchor - lo) / 1e9
        if pre < min(300, ev.get("pre_s", 600)):
            out.append(finding("PRE_WINDOW_SHORT", f"{pre:.0f}s of data before the anchor"))
    w = rec["time"]["window"]
    if w["clipped_start"] or w["clipped_end"]:
        out.append(finding("WINDOW_CLIPPED", f"start={w['clipped_start']} end={w['clipped_end']}"))
    for m in MODALITIES:
        st = stats.get(m, {})
        rows = st.get("rows", 0)
        if tel[m]["status"] == "empty":
            out.append(finding("EMPTY_MODALITY_FILE", "member has no rows in the window", m))
        if tel[m]["status"] == "present":
            cov = tel[m]["coverage"]
            if cov is not None and cov < 0.5:
                out.append(finding("LOW_COVERAGE", f"coverage {cov:.2f}", m))
        bad_ts = st.get("ts_out_of_range", 0)
        if bad_ts:
            share = bad_ts / max(rows + bad_ts, 1)
            out.append(finding("TS_OUT_OF_RANGE", f"{bad_ts} rows ({share:.2%})", m,
                               "quarantine" if share > 0.01 else "warn"))
        nonfinite = st.get("nonfinite", 0)
        if nonfinite:
            share = nonfinite / max(rows, 1)
            out.append(finding("METRIC_NONFINITE", f"{nonfinite} values ({share:.2%})", m,
                               "warn" if share > 0.05 else "info"))
        orphans = st.get("orphan_spans", 0)
        if orphans:
            share = orphans / max(rows, 1)
            out.append(finding("TRACE_ORPHAN_SPANS", f"{orphans} spans ({share:.2%})", m,
                               "warn" if share > 0.20 else "info"))
        if m == "logs" and tel[m]["status"] == "present" and not st.get("has_level", True):
            out.append(finding("LOG_LEVEL_MISSING", "no level column; keyword fallback", m))
    if label is not None:
        rc = label["root_cause"]
        svcs = set(rec["candidates"]["services"])
        if label["eval_tier"] == "A":
            p = rc["primary_root_service"]
            if (p is not None and p not in svcs) or (p is None and not set(rc["root_service_ids"]) <= svcs):
                out.append(finding("ROOT_NOT_CANDIDATE", f"root {p or rc['root_service_ids']} not among {len(svcs)} candidates"))
        if len(rc["entities"]) > 1:
            out.append(finding("MULTI_ROOT", f"{len(rc['entities'])} entities"))
        if label["label_artifacts"]:
            out.append(finding("LABEL_ARTIFACT_PRESENT", ", ".join(a["kind"] for a in label["label_artifacts"])))
        if label["group"]["duplicate_of"] or label["group"]["copy_of"]:
            out.append(finding("DUPLICATE", f"duplicate_of={label['group']['duplicate_of']} copy_of={label['group']['copy_of']}"))
    return out


def invariant_findings(rec: dict, label: dict | None, data_home: Path | None) -> list[Finding]:
    return [finding("INVARIANT_VIOLATION", e) for e in check_incident(rec, label, data_home)]


def load_overrides(path: Path | None) -> dict[str, dict]:
    if path is None or not Path(path).is_file():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    out = {}
    for o in data.get("overrides", []) or []:
        for k in ("incident_uid", "state", "reason", "initials", "date"):
            if not o.get(k):
                raise ValueError(f"override missing {k}: {o}")
        if o["state"] not in STATES:
            raise ValueError(f"bad override state: {o}")
        out[o["incident_uid"]] = o
    return out


def quality_record(uid: str, findings, overrides: dict | None = None) -> dict:
    fj = [f.to_json() if isinstance(f, Finding) else f for f in findings]
    fj.sort(key=lambda f: (-SEVERITY_RANK[f["severity"]], f["code"], f["modality"] or "", f["detail"]))
    rec = {"incident_uid": uid, "state": roll_up(fj), "findings": fj, "validator_version": VALIDATOR_VERSION,
           "decided_by": "rule", "override_reason": None}
    o = (overrides or {}).get(uid)
    if o:
        rec.update(state=o["state"], decided_by=f"manual:{o['initials']}:{o['date']}", override_reason=o["reason"])
    return rec
