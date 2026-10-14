"""Cross-dataset audit: duplicates, lineage reconciliation, imbalance tables, split isolation."""
from __future__ import annotations

import json
import shutil

from conftest import fixture_config
from fixtures import records as R
from rca import audit, prep, splits
from rca.adapters.rcaeval import RCAEvalAdapter
from rca.store import CanonicalStore, read_jsonl


class MirrorAdapter(RCAEvalAdapter):
    """The same raw data registered as a second dataset: every incident overlaps across datasets."""
    name = dataset_id = "mirror"


def _rows(*specs):
    out = []
    for uid, anchor, root, dup in specs:
        inc = R.incident(uid=uid)
        inc["time"]["anchor_ns"] = anchor
        lab = R.label(uid=uid)
        lab["root_cause"]["primary_root_service"] = root
        lab["group"]["duplicate_of"] = dup
        out.append((inc, lab))
    return out


def test_fingerprint_duplicates_explained_only_when_linked():
    a, b, c = "synth.00000000000000a1", "synth.00000000000000b2", "synth.00000000000000c3"
    rows = _rows((a, R.T0, "checkout", None), (b, R.T0 + 10**8, "checkout", a), (c, R.T0 + 5 * 10**9, "cart", None))
    d = audit.duplicates(rows)
    fp = [x for x in d["fingerprint"]]
    assert len(fp) == 1 and fp[0]["incident_uids"] == [a, b] and fp[0]["explained"]
    rows = _rows((a, R.T0, "checkout", None), (b, R.T0, "checkout", None))
    assert audit.duplicates(rows)["unexplained"] >= 1


def test_audit_on_fixture_build_and_planted_cross_dataset(rcaeval_home, tmp_path):
    rep = audit.run(rcaeval_home, fixture_config())
    assert rep["summary"]["unexplained_duplicates"] == 0     # the multi-source-data copy is linked
    assert any(x["explained"] for x in rep["duplicates"]["content"])
    assert rep["summary"]["leakage_hits"] == 0 and rep["summary"]["cross_dataset_overlaps"] == 0
    cells = rep["imbalance"]["rcaeval"]
    assert sum(c["incidents"] for c in cells) == 8
    assert {"subset", "system", "fault_family", "states", "modality_status", "candidates", "coverage"} <= set(cells[0])
    dh = tmp_path / "dh"
    shutil.copytree(rcaeval_home, dh)
    cfg = fixture_config()
    cfg["datasets"]["mirror"] = {"root": "raw/zenodo-test"}
    cfg["_hash"] = prep.config_hash(cfg)
    prep.build_dataset("mirror", cfg, dh, adapter_cls=MirrorAdapter, max_workers=1, log=lambda *a: None)
    rep = audit.run(dh, cfg)
    assert rep["summary"]["cross_dataset_overlaps"] > 0 and rep["summary"]["unexplained_duplicates"] > 0
    assert prep.main(["--data-home", str(dh), "audit"]) == prep.EXIT_ATTENTION


def test_lineage_reconciliation(rcaeval_home, tmp_path):
    dh = tmp_path / "dh"
    shutil.copytree(rcaeval_home, dh)
    store = CanonicalStore(dh)
    labels = store.labels("rcaeval")
    incs = {i["incident_uid"]: i for i in store.incidents("rcaeval", states=None)}
    reg = []
    for u, l in labels.items():
        if l["group"]["duplicate_of"]:
            continue                                   # the registry never listed the copy
        root, fault = l["root_cause"]["original"], l["fault"]["type_raw"]
        batch = next((n.split()[1] for n in l["validity_notes"] if n.startswith("batch ")), None)
        if batch:
            root, fault = f"{root}_{fault}", batch       # the registry's last-underscore parse
        reg.append({"source_id": incs[u]["source_id"], "incident_id": l["source_incident_id"], "root_cause_entity": root,
                    "fault": fault, "inject_or_start_time": str(incs[u]["time"]["anchor_ns"] // 10**9)})
    (dh / "manifests").mkdir()
    write = lambda rows: (dh / "manifests/incidents.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    write(reg)
    lin = audit.lineage(store, ["rcaeval"], dh / "manifests")["datasets"]["rcaeval"]
    assert lin["matched_one_to_one"] == 7 and lin["unexplained"] == 0
    assert lin["not_in_registry"][0]["explanation"] == "duplicate of a registered incident"
    assert sum(lin["label_differences"].values()) == 1
    write(reg + [{**reg[0], "incident_id": "rcaeval:re9xx_ghost_cpu_1"}])
    lin = audit.lineage(store, ["rcaeval"], dh / "manifests")["datasets"]["rcaeval"]
    assert lin["registry_only_count"] == 1 and lin["unexplained"] == 1


def test_lineage_for_datasets_sharing_one_source(tmp_path):
    """AIOps2025 and RCA100 both come from `agenticopseval`: each is reconciled only against its own
    id prefix; AIOps2025 registry ids are truncated uuids, RCA100 rows hold the fault without its
    taxonomy id and the answer-key window start instead of the alert."""
    from datetime import datetime, timezone

    from fixtures.agenticops_fixtures import AIOPS_LABELS, RCA100_CASES, aiops_tree, rca100_tree
    from test_adapter_aiops2025 import aiops_config
    from test_adapter_rca100 import rca100_config
    dh = tmp_path / "dh"
    aiops_tree(dh), rca100_tree(dh)
    cfg = aiops_config()
    cfg["datasets"]["rca100"]["root"] = rca100_config()["datasets"]["rca100"]["root"]
    cfg["_hash"] = prep.config_hash(cfg)
    for ds in ("aiops2025", "rca100"):
        prep.build_dataset(ds, cfg, dh, max_workers=1, log=lambda *a: None)
    store = CanonicalStore(dh)
    # artefacts referenced as `<jsonl>#<uuid>` reach the leakage scan; key_* metric names do not
    texts = audit._label_texts(store, "aiops2025")
    assert {"checkoutservice code error", "loss between cart and redis"} <= texts and "node_cpu_usage_rate" not in texts
    assert audit.leakage_scan(store, "aiops2025")["total_hits"] == 0
    reg = [{"source_id": "agenticopseval", "incident_id": f"aiops2025:{g['uuid'][:12]}", "fault": g["fault_type"],
            "root_cause_entity": g["instance"],             # the registry keeps a list-valued instance as a list
            "inject_or_start_time": g["start_time"]} for g in AIOPS_LABELS]
    for t, (case_id, roots, alert_iso, _, _) in RCA100_CASES.items():
        start = datetime.fromisoformat(alert_iso.replace("Z", "+00:00")).timestamp() - 120
        reg.append({"source_id": "agenticopseval", "incident_id": f"rca100:{case_id}", "fault": case_id.split(".")[0].split("-", 1)[1],
                    "fault_cell": case_id.split(".")[0], "root_cause_entity": roots[0],
                    "inject_or_start_time": datetime.fromtimestamp(start, timezone.utc).astimezone().isoformat()})
    (dh / "manifests").mkdir()
    write = lambda rows: (dh / "manifests/incidents.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    write(reg)
    lin = audit.lineage(store, ["aiops2025", "rca100"], dh / "manifests")["datasets"]
    a, r = lin["aiops2025"], lin["rca100"]
    assert a["registry_rows"] == 5 and a["matched_one_to_one"] == 5 and a["unexplained"] == 0 and not a["label_differences"]
    assert r["registry_rows"] == 4 and r["matched_one_to_one"] == 4 and r["unexplained"] == 0
    assert r["label_differences"] == {"registry fault without the taxonomy id prefix": 4}
    assert r["anchor_differences_explained"]["registry window start precedes the alert anchor"] == 4
    # a wrong anchor and a stray row are caught, and only in the dataset they belong to
    bad = [dict(x) for x in reg]
    bad[0]["inject_or_start_time"] = "2025-06-06T03:11:00Z"
    write(bad + [{**reg[-1], "incident_id": "rca100:F001-nodeDown.zzz"}])
    lin = audit.lineage(store, ["aiops2025", "rca100"], dh / "manifests")["datasets"]
    assert lin["aiops2025"]["unexplained"] == 1 and lin["aiops2025"]["anchor_differences"]
    assert lin["rca100"]["registry_only"] == ["rca100:F001-nodeDown.zzz"] and lin["rca100"]["unexplained"] == 1


def test_audit_reports_split_errors(rcaeval_home, tmp_path):
    dh = tmp_path / "dh"
    shutil.copytree(rcaeval_home, dh)
    splits.split_cmd("eval-only-rcaeval", 0, fixture_config(), dh)
    assert audit.run(dh, fixture_config())["summary"]["split_errors"] == 0
    d = next((dh / "splits").iterdir())
    rows = read_jsonl(d / "assignments.jsonl")
    rows[0]["split"] = "train"     # one member of a group moved, hash no longer matches either
    (d / "assignments.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    assert audit.run(dh, fixture_config())["summary"]["split_errors"] >= 1
