import json

import pytest
from jsonschema import Draft202012Validator

from fixtures import records as R
from rca import schema
from rca.store import write_jsonl_atomic


def test_schema_file_is_valid_2020_12():
    with open(schema.SCHEMA_PATH, encoding="utf-8") as f:
        Draft202012Validator.check_schema(json.load(f))


@pytest.mark.parametrize("kind,rec", [("IncidentRecord", R.incident()), ("LabelRecord", R.label()),
                                      ("QualityRecord", R.quality()), ("SourceIndexRecord", R.source_index())])
def test_examples_validate(kind, rec):
    assert schema.validate_record(kind, rec) == []


def test_unknown_field_rejected_and_uid_pattern():
    rec = R.incident()
    rec["root_service"] = "checkout"
    assert schema.validate_record("IncidentRecord", rec)
    assert schema.validate_record("IncidentRecord", R.incident(uid="Synth.XYZ"))
    assert schema.make_incident_uid("rcaeval", "k") == schema.make_incident_uid("rcaeval", "k")
    assert schema.UID_RE.match(schema.make_incident_uid("rcaeval", "RE2-OB/checkoutservice_cpu/1"))


def test_denylist_tokens():
    for name in ("root_service", "fault", "fault_type", "label", "gt", "answer_key", "key_observations", "is_root"):
        assert schema.denylisted(name), name
    for name in ("ts_ns", "service_id", "metric", "message", "rows", "status"):
        assert not schema.denylisted(name), name


def _errs(rec, lab=None):
    return schema.check_incident(rec, lab)


def test_invariants_each_have_a_failing_case():
    assert _errs(R.incident(), R.label()) == []
    # 3 denylist
    r = R.incident(); r["context"] = {"visible_text": None, "fault": "x"}
    assert any(e.startswith("inv3") for e in _errs(r))
    # 4 status semantics
    r = R.incident(); r["telemetry"]["logs"]["rows"] = 0
    assert any(e.startswith("inv4") for e in _errs(r))
    r = R.incident(); r["telemetry"]["traces"]["path"] = "x.parquet"
    assert any(e.startswith("inv4") for e in _errs(r))
    # 5 anchor in window
    r = R.incident(); r["time"]["window"]["start_ns"] = r["time"]["anchor_ns"] + 1
    assert any(e.startswith("inv5") for e in _errs(r))
    r["time"]["window"]["clipped_start"] = True
    assert not any(e.startswith("inv5") for e in _errs(r))
    # 6 timestamp range
    r = R.incident(); r["telemetry"]["logs"]["t_min_ns"] = 10
    assert any(e.startswith("inv6") for e in _errs(r))
    # 7 candidates sorted, unique, canon-stable
    r = R.incident(); r["candidates"]["services"] = ["frontend", "cart"]
    assert any(e.startswith("inv7") for e in _errs(r))
    r = R.incident(); r["candidates"]["services"] = ["cartservice"]
    assert any(e.startswith("inv7") for e in _errs(r))
    # 8 A-tier root must be a candidate unless quarantined
    lab = R.label(); lab["root_cause"]["primary_root_service"] = "payment"
    assert any(e.startswith("inv8") for e in _errs(R.incident(), lab))
    assert not any(e.startswith("inv8") for e in _errs(R.incident(quality_state="QUARANTINE"), lab))
    # 9 duplicates are REJECT
    lab = R.label(); lab["group"]["duplicate_of"] = R.UID
    assert any(e.startswith("inv9") for e in _errs(R.incident(), lab))
    # 11 relative POSIX paths
    for bad in ("C:/x.parquet", "/abs.parquet", "a\\b.parquet", "../x.parquet", "a" * 200):
        r = R.incident(); r["telemetry"]["logs"]["path"] = bad
        assert any(e.startswith("inv11") for e in _errs(r)), bad


def test_validate_dataset_invariants_1_2(tmp_path):
    ds = tmp_path / "canonical" / "v1" / "synth"
    u2 = schema.make_incident_uid("synth", "other")
    write_jsonl_atomic(ds / "visible" / "incidents.jsonl", [R.incident(), R.incident(uid=u2)])
    write_jsonl_atomic(ds / "eval_only" / "labels.jsonl", [R.label(), R.label(uid=u2)])
    write_jsonl_atomic(ds / "eval_only" / "quality.jsonl", [R.quality(), R.quality(uid=u2)])
    write_jsonl_atomic(ds / "eval_only" / "source_index.jsonl", [R.source_index(), R.source_index(uid=u2)])
    assert schema.validate_dataset(ds) == []
    write_jsonl_atomic(ds / "eval_only" / "labels.jsonl", [R.label()])
    assert any("inv2" in e for e in schema.validate_dataset(ds))
    bad = R.incident(); bad["extra"] = 1
    write_jsonl_atomic(ds / "visible" / "incidents.jsonl", [bad])
    assert any(e.startswith("inv1") for e in schema.validate_dataset(ds))
