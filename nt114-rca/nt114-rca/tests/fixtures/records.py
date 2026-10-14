"""Valid example records for schema and store tests (values are synthetic)."""
import copy

from rca.schema import SCHEMA_VERSION, make_incident_uid

T0 = 1_705_354_566 * 10**9
UID = make_incident_uid("synth", "RE2-OB/checkoutservice_cpu/1")


def modality(status="present", path=None, rows=10, services=("checkout",)):
    present = status == "present"
    return {"status": status, "path": path if present else None, "rows": rows if present else 0,
            "services": list(services) if present else [], "t_min_ns": T0 - 600 * 10**9 if present else None,
            "t_max_ns": T0 + 300 * 10**9 if present else None, "coverage": 1.0 if present else None,
            "metric_sets": [], "content_sha256": "0" * 64 if present else None, "notes": []}


def incident(uid=UID, **over):
    rec = {
        "schema_version": SCHEMA_VERSION, "incident_uid": uid, "dataset_id": "synth", "dataset_subset": "RE2",
        "dataset_version": "test", "source_id": "synthetic", "lineage_group": "L1", "system": "online-boutique",
        "time": {"anchor_ns": T0, "anchor_kind": "injection",
                 "anchor_original": {"value": str(T0 // 10**9), "unit": "s", "tz": "UTC"}, "end_ns": None,
                 "window": {"start_ns": T0 - 600 * 10**9, "end_ns": T0 + 300 * 10**9,
                            "clipped_start": False, "clipped_end": False}},
        "candidates": {"services": ["cart", "checkout", "frontend"], "source": "telemetry"},
        "telemetry": {"metrics": modality(path=f"canonical/v1/synth/visible/telemetry/{uid}/metrics.parquet"),
                      "logs": modality(path=f"canonical/v1/synth/visible/telemetry/{uid}/logs.parquet"),
                      "traces": modality("natural_absent")},
        "context": {"visible_text": None},
        "repro": {"adapter": {"name": "synth", "version": "1.0.0"}, "build_id": "b1", "config_hash": "a" * 64,
                  "input_digest": "b" * 64},
        "quality_state": "ACCEPT",
    }
    for k, v in over.items():
        rec[k] = v
    return rec


def label(uid=UID, **over):
    rec = {
        "incident_uid": uid, "source_incident_id": "synth:re2ob_checkoutservice_cpu_1",
        "root_cause": {"original": "checkoutservice",
                       "entities": [{"raw": "checkoutservice", "kind": "service", "service_id": "checkout"}],
                       "root_service_ids": ["checkout"], "primary_root_service": "checkout", "label_granularity": "service"},
        "fault": {"type_raw": "cpu", "family": "cpu"}, "label_source": "path", "injection_kind": "injected",
        "label_validity": "valid", "validity_notes": [], "eval_tier": "A", "eval_tier_reason": "test",
        "group": {"fault_cell": "L1/online-boutique/checkout/cpu", "copy_of": None, "duplicate_of": None, "group_id": None},
        "label_artifacts": [], "truth_time": {"end_ns": None},
    }
    rec.update(over)
    return rec


def quality(uid=UID, state="ACCEPT", findings=()):
    return {"incident_uid": uid, "state": state, "findings": list(findings), "validator_version": "1.0.0",
            "decided_by": "rule", "override_reason": None}


def source_index(uid=UID):
    return {"incident_uid": uid, "source_incident_id": "synth:re2ob_checkoutservice_cpu_1",
            "source_incident_key": "RE2-OB/checkoutservice_cpu/1",
            "members": [{"role": "metrics:simple", "source_id": "synthetic", "member": "RE2-OB.zip!x/metrics.csv",
                         "sha256": None, "size": 10}], "label_files": []}


def deep(rec):
    return copy.deepcopy(rec)
