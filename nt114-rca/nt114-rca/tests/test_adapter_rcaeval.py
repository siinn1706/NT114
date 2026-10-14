"""RCAEval adapter on fixture zips that carry every known raw defect."""
from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq
import pytest

from rca.adapters.rcaeval import is_infra, legacy_metric_set, parse_cell
from rca.schema import validate_dataset
from rca.store import CanonicalStore, read_json, read_jsonl

DS = "canonical/v1/rcaeval"


@pytest.fixture(scope="module")
def built(rcaeval_home):
    ds = rcaeval_home / DS
    inc = {r["incident_uid"]: r for r in read_jsonl(ds / "visible/incidents.jsonl")}
    lab = {r["incident_uid"]: r for r in read_jsonl(ds / "eval_only/labels.jsonl")}
    q = {r["incident_uid"]: r for r in read_jsonl(ds / "eval_only/quality.jsonl")}
    src = {r["incident_uid"]: r for r in read_jsonl(ds / "eval_only/source_index.jsonl")}
    by_src = {lab[u]["source_incident_id"]: u for u in lab}
    return {"inc": inc, "lab": lab, "q": q, "src": src, "uid": by_src, "ds": ds}


@pytest.mark.parametrize("cell,expected", [
    ("checkoutservice_cpu", ("checkoutservice", "cpu", None)),
    ("ts-route-service_f3", ("ts-route-service", "f3", None)),
    ("ts-route-service_f3_1", ("ts-route-service", "f3", "1")),
    ("ts-auth-service_socket", ("ts-auth-service", "socket", None)),
    ("carts_disk", ("carts", "disk", None)),
    ("frontend_unknownfault", None),
])
def test_parse_cell(cell, expected):
    assert parse_cell(cell) == expected


def test_infra_rules_keep_real_services():
    for name in ("gke-cluster-1-default-pool-x", "ip-10-0-1-2", "10-192-1-2-9100", "istio-init", "main", "ts", "front"):
        assert is_infra(name), name
    for name in ("frontend", "frontend-external", "loadgenerator", "redis", "ts-route-service", "carts"):
        assert not is_infra(name), name


def test_legacy_metric_set_choice():
    assert legacy_metric_set("RE2", ["full", "simple"]) == "simple"
    assert legacy_metric_set("RE1", ["full", "simple"]) == "full"
    assert legacy_metric_set("RE3", ["full"]) == "full"


def test_every_case_discovered_and_dataset_valid(built, rcaeval_home):
    assert len(built["inc"]) == 8
    assert validate_dataset(built["ds"], rcaeval_home) == []
    receipt = read_json(built["ds"] / "_build.json")
    assert receipt["counts"]["records"] == 8 and receipt["counts"]["exceptions"] == 0


def test_batch_cell_labels_are_not_shifted(built):
    """`ts-route-service_f3_1/1` is fault f3 batch 1, not root `ts-route-service_f3` fault `1`."""
    for sid in ("rcaeval:re3tt_ts-route-service_f3_1", "rcaeval:re3tt_ts-route-service_f3_1_1"):
        lab = built["lab"][built["uid"][sid]]
        assert lab["root_cause"]["primary_root_service"] == "route"
        assert lab["fault"]["type_raw"] == "f3" and lab["fault"]["family"] == "code-defect"
        assert lab["label_validity"] == "valid"
    batch = built["lab"][built["uid"]["rcaeval:re3tt_ts-route-service_f3_1_1"]]
    assert any("batch 1" in n for n in batch["validity_notes"])
    assert built["uid"]["rcaeval:re3tt_ts-route-service_f3_1"] != built["uid"]["rcaeval:re3tt_ts-route-service_f3_1_1"]


def test_multi_source_duplicate_rejected_and_linked(built):
    dup = built["uid"]["rcaeval:re2ob_checkoutservice_cpu_multi-source-data"]
    orig = built["uid"]["rcaeval:re2ob_checkoutservice_cpu_1"]
    assert built["q"][dup]["state"] == "REJECT"
    assert built["lab"][dup]["group"]["duplicate_of"] == orig
    assert built["q"][orig]["state"] == "ACCEPT"
    # the duplicate's telemetry is still converted, so content-hash audits can confirm the copy
    assert built["inc"][dup]["telemetry"]["metrics"]["status"] == "present"


def test_modality_status_distinguishes_absent_and_empty(built):
    t = lambda sid, m: built["inc"][built["uid"][sid]]["telemetry"][m]["status"]
    assert t("rcaeval:re3ss_carts_f1_1", "traces") == "empty"            # header-only traces.csv
    assert t("rcaeval:re3ss_carts_f1_2", "traces") == "natural_absent"   # no traces.csv
    assert t("rcaeval:re2ss_orders_mem_1", "traces") == "natural_absent"
    assert t("rcaeval:re2ob_cartservice_delay_1", "traces") == "present"


def test_findings_for_planted_defects(built):
    codes = lambda sid: {f["code"] for f in built["q"][built["uid"][sid]]["findings"]}
    assert "TRACE_TIME_MISMATCH" in codes("rcaeval:re2ob_cartservice_delay_1")
    assert {"EMPTY_MODALITY_FILE", "LABEL_ARTIFACT_PRESENT"} <= codes("rcaeval:re3ss_carts_f1_1")
    assert codes("rcaeval:re2ob_checkoutservice_cpu_1") == set()


def test_label_artifact_is_eval_only(built, rcaeval_home):
    uid = built["uid"]["rcaeval:re3ss_carts_f1_1"]
    roles = {m["role"] for m in built["src"][uid]["members"] if m["member"].endswith("root_cause.txt")}
    assert roles == {"label_artifact"}
    assert built["lab"][uid]["label_artifacts"][0]["kind"] == "rcaeval:root_cause.txt"
    visible = rcaeval_home / DS / "visible"
    for f in visible.rglob("*"):
        if f.is_file():
            assert b"CANARY_ROOT_CAUSE_LINE" not in f.read_bytes(), f
            if f.suffix == ".parquet":
                t = pq.read_table(f)
                for c in t.column_names:
                    if t[c].type == "string":
                        assert not any("CANARY_ROOT_CAUSE_LINE" in (v or "") for v in t[c].to_pylist())


def test_no_member_outside_case_and_no_ds_store(built):
    for s in built["src"].values():
        for m in s["members"]:
            assert ".DS_Store" not in m["member"]
            assert "!" in m["member"] and not m["member"].startswith("/")


def test_metric_timestamps_are_exact_seconds(built, rcaeval_home):
    store = CanonicalStore(rcaeval_home)
    uid = built["uid"]["rcaeval:re2ob_checkoutservice_cpu_1"]
    t = store.telemetry(uid, "metrics")
    ts = t["ts_ns"].to_numpy()
    assert (ts % 10**9 == 0).all()
    anchor = built["inc"][uid]["time"]["anchor_ns"]
    assert ts.min() == anchor - 600 * 10**9 and ts.max() == anchor + 299 * 10**9
    assert set(t["metric_set"].to_pylist()) == {"full", "simple"}


def test_candidates_cover_root_and_exclude_infra(built):
    for uid, lab in built["lab"].items():
        cands = built["inc"][uid]["candidates"]["services"]
        assert lab["root_cause"]["primary_root_service"] in cands
        assert not any(is_infra(c) for c in cands)


def _add_metric_columns(case: Path, names) -> None:
    for f in ("metrics.csv", "simple_metrics.csv"):
        p = case / f
        if p.exists():
            lines = p.read_text(encoding="utf-8").splitlines()
            lines = [lines[0] + "".join(f",{n}_cpu" for n in names)] + [r + ",0.1" * len(names) for r in lines[1:]]
            p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_other_system_containers_are_infra_and_never_merge(tmp_path, monkeypatch):
    """A neighbouring demo's containers scraped into a case (Sock Shop `carts` in an OB case, OB `frontend`
    in a Sock Shop case) become infra under the other system's prefix: never candidates, and OB
    `frontend` does not merge with Sock Shop `front-end`. The fixture has 2-4 cases per system, so the
    own-system share limit is raised from the real-data 5%."""
    from conftest import fixture_config
    from fixtures.build_fixtures import rcaeval_zips
    from rca import prep
    from rca.adapters import rcaeval
    monkeypatch.setattr(rcaeval, "FOREIGN_OWN_MAX", 0.4)

    def edit(tree):
        _add_metric_columns(tree / "RE2-OB/cartservice_delay/1", ["carts"])
        _add_metric_columns(tree / "RE2-SS/orders_mem/1", ["frontend"])
    dh = tmp_path / "dh"
    rcaeval_zips(dh / "raw", edit)
    prep.build_dataset("rcaeval", fixture_config(), dh, max_workers=1, log=lambda *a: None)
    store = CanonicalStore(dh)
    labs = store.labels("rcaeval")
    uid = {l["source_incident_id"]: u for u, l in labs.items()}
    smap = read_json(dh / DS / "visible/service_map.json")
    assert smap["online-boutique"]["carts"] == {"service_id": "sockshopcarts", "rule": "other-system-container", "kind": "infra"}
    assert smap["sock-shop"]["frontend"]["service_id"] == "onlineboutiquefrontend"
    assert smap["sock-shop"]["front-end"]["service_id"] == "frontend"
    ob = store.incident(uid["rcaeval:re2ob_cartservice_delay_1"])
    ss = store.incident(uid["rcaeval:re2ss_orders_mem_1"])
    assert "sockshopcarts" not in ob["candidates"]["services"] and "carts" not in ob["candidates"]["services"]
    assert "onlineboutiquefrontend" not in ss["candidates"]["services"] and "frontend" in ss["candidates"]["services"]
    m = store.telemetry(ss["incident_uid"], "metrics")
    ids = dict(zip(m["entity_raw"].to_pylist(), m["service_id"].to_pylist()))
    assert ids["frontend"] == "onlineboutiquefrontend" and ids["front-end"] == "frontend"     # raw identity kept
