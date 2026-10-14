"""Real-data service identity: reviewed aliases stay scoped to their system, only intended merges exist,
and the RCAEval incidents whose cluster also ran the other demo have system-scoped candidates, correct
ground-truth matching, clean evidence and no label leakage."""
from __future__ import annotations

import json
from collections import defaultdict

import pyarrow.parquet as pq
import pytest

from conftest import REAL_DATA
from rca import audit, evidence, prep
from rca.data import canon
from rca.legacy_view import evidence_kwargs, legacy_telemetry, visible_case
from rca.store import CanonicalStore

pytestmark = [pytest.mark.realdata,
              pytest.mark.skipif(not (REAL_DATA / "canonical/v1/rcaeval/_build.json").is_file(),
                                 reason="no real RCAEval build")]

# The incidents whose metrics also cover the other demo's containers (measured 2026-10-14).
SHARED_CLUSTER = {"rcaeval.4303ec727622942a": "online-boutique", "rcaeval.d5bb2ac1b3c6bb37": "online-boutique",
                  "rcaeval.4d62cb4318958396": "online-boutique", "rcaeval.76e86a2d6f0e1dc1": "sock-shop"}
OTHER_PREFIX = {"online-boutique": "sockshop", "sock-shop": "onlineboutique"}
REVIEWED_ALIASES = {
    ("online-boutique", "frontendservice"): ("frontend", "service"),
    ("online-boutique", "front-end"): ("sockshopfrontend", "infra"),
    ("online-boutique", "payment"): ("sockshoppayment", "infra"),
    ("online-boutique", "shipping"): ("sockshopshipping", "infra"),
    ("sock-shop", "paymentservice"): ("onlineboutiquepayment", "infra"),
    ("sock-shop", "shippingservice"): ("onlineboutiqueshipping", "infra"),
}
# service ids reached from two or more raw non-pod spellings, per dataset/system (all intended)
INTENDED_MERGES = {("rcaeval", "online-boutique", "frontend"): {"frontend", "frontendservice"},
                   ("aiops2025", "hipstershop", "rediscart"): {"redis", "redis-cart"}}


@pytest.fixture(scope="module")
def rc():
    store = CanonicalStore(REAL_DATA)
    smap = json.loads((REAL_DATA / "canonical/v1/rcaeval/visible/service_map.json").read_text(encoding="utf-8"))
    return {"store": store, "labels": store.labels("rcaeval"), "smap": smap,
            "incs": {i["incident_uid"]: i for i in store.incidents("rcaeval", states=None)}}


def test_reviewed_aliases_are_system_scoped(rc):
    for (system, raw), (sid, kind) in REVIEWED_ALIASES.items():
        e = rc["smap"][system][raw]
        assert (e["service_id"], e["rule"], e["kind"]) == (sid, "alias", kind)
    # an alias of one system never applies in another: Train Ticket has none of these names as aliases
    assert not [r for r, e in rc["smap"]["train-ticket"].items() if e["rule"] == "alias"]
    # the same raw spelling keeps its own meaning in its own system
    assert rc["smap"]["sock-shop"]["front-end"]["service_id"] == "frontend"
    assert rc["smap"]["sock-shop"]["frontend"]["service_id"] == "onlineboutiquefrontend"
    assert rc["smap"]["online-boutique"]["frontend"]["service_id"] == "frontend"


def test_only_intended_merges_across_datasets():
    seen = {}
    for ds in ("rcaeval", "nezha", "aiops2025", "rca100"):
        p = REAL_DATA / "canonical/v1" / ds / "visible/service_map.json"
        if not p.is_file():
            continue
        for system, m in json.loads(p.read_text(encoding="utf-8")).items():
            by = defaultdict(set)
            for raw, e in m.items():
                if e["kind"] != "pod" and e["service_id"] is not None:
                    by[e["service_id"]].add(raw)
            seen.update({(ds, system, sid): raws for sid, raws in by.items() if len(raws) > 1})
    assert seen == {k: v for k, v in INTENDED_MERGES.items() if (REAL_DATA / "canonical/v1" / k[0]).is_dir()}


def test_other_system_containers_never_become_candidates(rc):
    infra = {s: {e["service_id"] for e in m.values() if e["kind"] == "infra"} for s, m in rc["smap"].items()}
    for inc in rc["incs"].values():
        assert not set(inc["candidates"]["services"]) & infra[inc["system"]], inc["incident_uid"]


@pytest.mark.parametrize("uid", sorted(SHARED_CLUSTER))
def test_shared_cluster_incident_is_system_scoped(rc, uid):
    inc, system = rc["incs"][uid], SHARED_CLUSTER[uid]
    assert inc["system"] == system and inc["quality_state"] in ("ACCEPT", "ACCEPT_WITH_WARNINGS")
    cands = set(inc["candidates"]["services"])
    others = set().union(*(set(i["candidates"]["services"]) for u, i in rc["incs"].items()
                           if u != uid and i["system"] == system and i["dataset_subset"] == inc["dataset_subset"]))
    assert cands <= others                                   # nothing appears only in this incident
    assert not [c for c in cands if c.startswith(OTHER_PREFIX[system])]
    # every telemetry row of a foreign container keeps its raw name and carries the infra id
    t = pq.read_table(REAL_DATA / inc["telemetry"]["metrics"]["path"], columns=["entity_raw", "service_id"]).to_pandas()
    foreign = {r for r, e in rc["smap"][system].items()
               if e["kind"] == "infra" and str(e["service_id"]).startswith(OTHER_PREFIX[system])}
    rows = t[t["entity_raw"].isin(foreign)]
    assert len(rows) and rows["service_id"].str.startswith(OTHER_PREFIX[system]).all()
    assert not set(rows["service_id"]) & cands


@pytest.mark.parametrize("uid", sorted(SHARED_CLUSTER))
def test_shared_cluster_ground_truth_matches(rc, uid):
    lab, inc = rc["labels"][uid], rc["incs"][uid]
    root = lab["root_cause"]["primary_root_service"]
    raw = lab["root_cause"]["original"]
    assert lab["label_validity"] == "valid" and lab["label_source"] == "path"
    assert f"_{raw}_" in lab["source_incident_id"]           # the label comes from the case path
    assert rc["smap"][inc["system"]].get(raw, {"service_id": canon(raw)})["service_id"] == root
    assert root in inc["candidates"]["services"]
    t = pq.read_table(REAL_DATA / inc["telemetry"]["metrics"]["path"], columns=["service_id"]).to_pandas()
    assert (t["service_id"] == root).any()


@pytest.mark.parametrize("uid", sorted(SHARED_CLUSTER))
def test_shared_cluster_evidence_is_clean_and_deterministic(rc, uid, tmp_path):
    store, inc = rc["store"], rc["incs"][uid]
    vc = visible_case(inc)
    kw = evidence_kwargs(prep.load_config(), "rcaeval")
    tel = legacy_telemetry(store, uid)
    assert not [c for c in tel["metrics"].columns if OTHER_PREFIX[inc["system"]] in c]   # infra never reaches evidence
    a = evidence.build(vc, tel, **kw)
    b = evidence.build(vc, legacy_telemetry(store, uid), **kw)
    assert a == b
    assert OTHER_PREFIX[inc["system"]] not in a["text"]
    flagged = {ln[2:].split(":", 1)[0] for ln in a["text"].splitlines()
               if ln.startswith("- ") and ":" in ln and "->" not in ln.split(":", 1)[0] and " " not in ln[2:].split(":", 1)[0]}
    assert flagged <= set(inc["candidates"]["services"]), flagged - set(inc["candidates"]["services"])
    (tmp_path / f"{uid}.json").write_text(json.dumps({"incident_uid": uid, "conditions": {"full": a}}), encoding="utf-8")
    assert audit.evidence_scan(tmp_path, audit._label_texts(store, "rcaeval"))["total_hits"] == 0


def test_visible_zone_has_no_label_leakage(rc):
    assert audit.leakage_scan(rc["store"], "rcaeval")["total_hits"] == 0
