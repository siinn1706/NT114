"""Per-incident validators, state roll-up and reviewed overrides."""
from __future__ import annotations

import pytest

from fixtures import records as R
from rca import quality as Q
from rca.adapters.base import Finding


def _codes(fs):
    return {f.code for f in fs}


def test_roll_up_takes_worst_severity():
    assert Q.roll_up([]) == "ACCEPT"
    assert Q.roll_up([Q.finding("METRIC_CONSTANT")]) == "ACCEPT"
    assert Q.roll_up([Q.finding("METRIC_CONSTANT"), Q.finding("TS_COLUMN_OFFSET")]) == "ACCEPT_WITH_WARNINGS"
    assert Q.roll_up([Q.finding("TS_COLUMN_OFFSET"), Q.finding("ROOT_NOT_CANDIDATE")]) == "QUARANTINE"
    assert Q.roll_up([Q.finding("ROOT_NOT_CANDIDATE").to_json(), Q.finding("DUPLICATE").to_json()]) == "REJECT"


def test_unknown_code_is_an_error():
    with pytest.raises(KeyError):
        Q.finding("NOT_A_CODE")


def test_valid_record_has_no_findings():
    assert Q.validate_incident(R.incident(), R.label(), {}, {}) == []


def test_no_telemetry_and_root_not_candidate():
    rec = R.incident()
    for m in ("metrics", "logs", "traces"):
        rec["telemetry"][m] = R.modality("natural_absent")
    rec["candidates"]["services"] = ["cart"]
    assert {"NO_TELEMETRY", "ROOT_NOT_CANDIDATE"} <= _codes(Q.validate_incident(rec, R.label(), {}, {}))


def test_anchor_outside_window_and_short_pre_window():
    rec = R.incident()
    for m in ("metrics", "logs", "traces"):
        rec["telemetry"][m]["t_min_ns"] = R.T0 + 10 * 10**9
    codes = _codes(Q.validate_incident(rec, R.label(), {}, {}))
    assert "ANCHOR_OUTSIDE_WINDOW" in codes
    rec = R.incident()
    for m in ("metrics", "logs", "traces"):
        rec["telemetry"][m]["t_min_ns"] = R.T0 - 120 * 10**9
    assert "PRE_WINDOW_SHORT" in _codes(Q.validate_incident(rec, R.label(), {}, {}))


@pytest.mark.parametrize("bad,rows,severity", [(5, 10_000, "warn"), (500, 10_000, "quarantine")])
def test_ts_out_of_range_severity_follows_share(bad, rows, severity):
    fs = Q.validate_incident(R.incident(), R.label(), {"logs": {"rows": rows, "ts_out_of_range": bad}}, {})
    f = next(f for f in fs if f.code == "TS_OUT_OF_RANGE")
    assert f.severity == severity and f.modality == "logs"


def test_label_artifact_multi_root_and_duplicate():
    lab = R.label()
    lab["label_artifacts"] = [{"kind": "rcaeval:root_cause.txt", "ref": "x.zip!a/root_cause.txt"}]
    lab["group"]["duplicate_of"] = "synth.00000000000000aa"
    lab["root_cause"]["entities"] = [{"raw": "a", "kind": "service", "service_id": "checkout"},
                                     {"raw": "b", "kind": "service", "service_id": "cart"}]
    codes = _codes(Q.validate_incident(R.incident(), lab, {}, {}))
    assert {"LABEL_ARTIFACT_PRESENT", "MULTI_ROOT", "DUPLICATE"} <= codes


def test_schema_invalid_is_reported():
    rec = R.incident()
    rec["quality_state"] = "MAYBE"
    assert "SCHEMA_INVALID" in _codes(Q.validate_incident(rec, R.label(), {}, {}))


def test_quality_record_sorted_and_override_applied(tmp_path):
    fs = [Q.finding("METRIC_CONSTANT", "b"), Q.finding("ROOT_NOT_CANDIDATE", "a"), Q.finding("TS_COLUMN_OFFSET", "c")]
    q = Q.quality_record(R.UID, fs)
    assert [f["code"] for f in q["findings"]] == ["ROOT_NOT_CANDIDATE", "TS_COLUMN_OFFSET", "METRIC_CONSTANT"]
    assert q["state"] == "QUARANTINE" and q["decided_by"] == "rule"
    p = tmp_path / "ov.yaml"
    p.write_text(f"overrides:\n  - incident_uid: {R.UID}\n    state: ACCEPT_WITH_WARNINGS\n"
                 "    reason: root listed under an alias, checked by hand\n    initials: NN\n    date: 2026-10-14\n",
                 encoding="utf-8")
    q = Q.quality_record(R.UID, fs, Q.load_overrides(p))
    assert q["state"] == "ACCEPT_WITH_WARNINGS" and q["decided_by"] == "manual:NN:2026-10-14"
    assert q["findings"][0]["code"] == "ROOT_NOT_CANDIDATE"      # findings are kept under an override


def test_override_needs_reason_and_valid_state(tmp_path):
    p = tmp_path / "ov.yaml"
    p.write_text(f"overrides:\n  - incident_uid: {R.UID}\n    state: ACCEPT\n    initials: NN\n    date: 2026-10-14\n", encoding="utf-8")
    with pytest.raises(ValueError, match="reason"):
        Q.load_overrides(p)
    p.write_text(f"overrides:\n  - incident_uid: {R.UID}\n    state: FINE\n    reason: r\n    initials: NN\n    date: d\n", encoding="utf-8")
    with pytest.raises(ValueError, match="state"):
        Q.load_overrides(p)
    assert Q.load_overrides(tmp_path / "missing.yaml") == {}


def test_repo_overrides_file_loads():
    assert isinstance(Q.load_overrides(__import__("rca.prep", fromlist=["OVERRIDES"]).OVERRIDES), dict)


def test_finding_json_roundtrip():
    f = Q.finding("LOW_COVERAGE", "coverage 0.40", "logs")
    assert isinstance(f, Finding)
    assert f.to_json() == {"code": "LOW_COVERAGE", "severity": "warn", "modality": "logs", "detail": "coverage 0.40",
                           "evidence_ref": None}
