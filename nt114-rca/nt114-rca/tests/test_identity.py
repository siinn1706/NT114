import pytest

from rca.data import canon
from rca.identity import ServiceMap, load_aliases, pod_pattern


def test_canon_rule_and_idempotence():
    sm = ServiceMap()
    for raw in ("checkoutservice", "ts-auth-service", "front-end", "carts-db"):
        sid = sm.map("sys", raw)
        assert canon(sid) == sid
        assert sm.map("sys", sid) == sid
    assert sm.entries["sys"]["checkoutservice"] == {"service_id": "checkout", "rule": "canon", "kind": "service"}


def test_pod_to_deployment_only_for_known_services():
    sm = ServiceMap()
    sm.declare_services("ob", ["frontend", "paymentservice"])
    assert sm.map("ob", "frontend-579b9bff58-t2dbm", kind="pod") == "frontend"
    assert sm.entries["ob"]["frontend-579b9bff58-t2dbm"]["rule"] == "pod-to-deployment"
    assert sm.map("ob", "paymentservice-1", kind="pod") == "payment"
    assert sm.map("ob", "unknownthing-579b9bff58-t2dbm", kind="pod") is None
    assert sm.map("ob", "paymentservice-5489989-q7ws7", kind="pod") == "payment"     # 7-character template hash
    assert sm.map("ob", "frontend-12345-q7ws7", kind="pod") is None
    assert pod_pattern("ts-config-mongo") == "plain"                                  # not a short hash


def test_collisions_and_alias_override():
    sm = ServiceMap()
    sm.map("ob", "frontend")
    sm.map("ob", "frontendservice")
    assert sm.collisions("ob") == {"frontend": ["frontend", "frontendservice"]}
    sm2 = ServiceMap(aliases={"ob": {"frontendservice": {"service_id": "frontend", "reason": "r"}}})
    sm2.map("ob", "frontend")
    sm2.map("ob", "frontendservice")
    assert sm2.collisions("ob") == {}
    assert sm2.entries["ob"]["frontendservice"]["rule"] == "alias"
    # punctuation-only differences are the same identifier, not a collision
    sm3 = ServiceMap()
    sm3.map("ss", "front-end")
    sm3.map("ss", "frontend")
    assert sm3.collisions("ss") == {}


def test_infra_columns_excluded():
    sm = ServiceMap(infra={"ob": {"main", "istio-init"}})
    assert sm.map("ob", "main") == "main"
    assert sm.is_infra("ob", "main")
    assert not sm.is_infra("ob", sm.map("ob", "cartservice"))


def test_alias_must_be_canon_stable(tmp_path):
    p = tmp_path / "a.yaml"
    p.write_text("aliases:\n  ob:\n    x: {service_id: CartService, reason: r}\n", encoding="utf-8")
    sm = ServiceMap(aliases=load_aliases(p))
    with pytest.raises(ValueError):
        sm.map("ob", "x")


def test_alias_can_declare_foreign_container_as_infra():
    from rca.identity import ServiceMap
    sm = ServiceMap(aliases={"online-boutique": {
        "frontendservice": {"service_id": "frontend"},
        "payment": {"service_id": "sockshoppayment", "kind": "infra"}}})
    for raw in ("frontend", "frontendservice", "paymentservice", "payment"):
        sm.map("online-boutique", raw)
    assert sm.map("online-boutique", "frontendservice") == "frontend"
    assert sm.map("online-boutique", "payment") == "sockshoppayment"
    assert sm.is_infra("online-boutique", "sockshoppayment") and not sm.is_infra("online-boutique", "payment")
    assert sm.collisions("online-boutique") == {}


def test_alias_file_is_part_of_config_hash(monkeypatch, tmp_path):
    from rca import prep
    cfg = prep.load_config()
    h = prep.config_hash(cfg)
    alt = tmp_path / "aliases.yaml"
    alt.write_text("aliases: {}\n", encoding="utf-8")
    monkeypatch.setattr(prep, "ALIASES", alt)
    assert prep.config_hash(cfg) != h
