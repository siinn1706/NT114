"""No label reaches model-visible data: canary, type guard, permutation invariance, scans."""
from __future__ import annotations

import ast
import json
import secrets
import shutil
from pathlib import Path

import pandas as pd
import pytest

from conftest import canonical_run_cfg
from rca import audit, evidence, retrieve, run_grid, selective
from rca.data import VisibleCase
from rca.llm import build_messages
from rca.retrieve import CaseStore, Embedder, format_hits
from rca.store import read_jsonl, write_jsonl_atomic

RCA_ROOT = Path(__file__).resolve().parents[1]
MODEL_FACING = ("evidence.py", "llm.py", "retrieve.py", "rcl_path.py", "rcl_trace_graph.py", "rcl_tools.py",
                "rcl_evidence.py", "im1_frame.py")
PERM_CONDITIONS = ["full", "no_metric", "no_log", "no_trace"]


def _tfidf() -> Embedder:
    e = Embedder.__new__(Embedder)
    e.model_name, e.st, e.kind, e._fit = "tfidf", None, "tfidf-svd", None
    return e


def _home(canonical_synth, tmp_path) -> Path:
    dh = tmp_path / "dh"
    for part in ("canonical", "reports", "splits"):
        shutil.copytree(canonical_synth["dh"] / part, dh / part)
    return dh


def _labels_path(dh):
    return dh / "canonical/v1/rcaeval/eval_only/labels.jsonl"


def _test_uids(cfg) -> list[str]:
    cn = run_grid.Canon(cfg)
    return sorted(u for u, r in cn.roles.items() if r == "test")


def model_artifacts(cfg) -> dict[str, str]:
    """Everything a model would see, for test-role incidents: evidence and prompts with every
    retrieval method in `precedent` mode."""
    run_grid.prepare(cfg)
    recs = run_grid.load_evidence(cfg)
    cn = run_grid.Canon(cfg)
    store = CaseStore(run_grid._store_entries(cfg, cn)[0], _tfidf())
    members = {}
    for u, g in cn.group.items():
        members.setdefault(g, set()).add(u)
    out = {}
    for r in recs:
        vc, tr, cands = r["vc"], r["truth"], r["candidates"]
        grp = frozenset(members.get(cn.group.get(vc.case_id), ()))
        out[f"{vc.case_id}|candidates"] = json.dumps(cands)
        for cond, ev in r["conditions"].items():
            out[f"{vc.case_id}|{cond}|evidence"] = json.dumps(ev, sort_keys=True)
            for meth in ("none", "bm25", "dense", "hybrid"):
                hits = [] if meth == "none" else store.search(
                    ev["text"], vc, meth, "precedent", 3, exclude_ids=run_grid.exclusions(store, vc, tr, "precedent", grp))
                msgs = build_messages(vc, cands, ev["text"], format_hits(hits))
                out[f"{vc.case_id}|{cond}|{meth}|prompt"] = json.dumps(msgs)
    return out


def test_canary_label_never_reaches_model(canonical_synth, tmp_path):
    dh = _home(canonical_synth, tmp_path)
    cfg = canonical_run_cfg(dh, tmp_path / "res", conditions=PERM_CONDITIONS)
    canary = f"CANARY_{secrets.token_hex(8)}"
    test = set(_test_uids(cfg))
    labs = read_jsonl(_labels_path(dh))
    for l in labs:
        if l["incident_uid"] in test:
            l["root_cause"]["original"] = canary
            l["fault"]["type_raw"] = canary
            l["validity_notes"] = [canary]
    write_jsonl_atomic(_labels_path(dh), labs)
    arts = model_artifacts(cfg)
    assert arts
    assert not [k for k, v in arts.items() if canary in v]
    for f in (dh / "canonical/v1/rcaeval/visible").rglob("*"):
        if f.is_file():
            assert canary.encode() not in f.read_bytes()


def test_label_permutation_invariance(canonical_synth, tmp_path):
    dh = _home(canonical_synth, tmp_path)
    base = model_artifacts(canonical_run_cfg(dh, tmp_path / "a", conditions=PERM_CONDITIONS))
    cfg = canonical_run_cfg(dh, tmp_path / "b", conditions=PERM_CONDITIONS)
    test = _test_uids(cfg)
    labs = {l["incident_uid"]: l for l in read_jsonl(_labels_path(dh))}
    fields = [(labs[u]["root_cause"], labs[u]["fault"]) for u in test]
    fields = fields[1:] + fields[:1]                         # cyclic shift among test-role incidents only
    assert any(labs[u]["root_cause"]["primary_root_service"] != f[0]["primary_root_service"] for u, f in zip(test, fields))
    for u, (rc, fa) in zip(test, fields):
        labs[u]["root_cause"], labs[u]["fault"] = rc, fa
    write_jsonl_atomic(_labels_path(dh), list(labs.values()))
    assert model_artifacts(cfg) == base


def test_model_facing_entry_points_only_see_visible_cases(canonical_synth, tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    dh = _home(canonical_synth, tmp_path)
    cfg = canonical_run_cfg(dh, tmp_path / "res", retrieval=["none", "hybrid"], models=[{"name": "mock-small", "backend": "mock"}])
    seen = []

    def guard(fn, pos=0):
        def wrapped(*a, **k):
            case = a[pos]
            assert isinstance(case, VisibleCase) and not hasattr(case, "root_service") and not hasattr(case, "fault")
            seen.append(fn.__name__)
            return fn(*a, **k)
        return wrapped

    monkeypatch.setattr(run_grid.evidence, "build", guard(evidence.build))
    monkeypatch.setattr(run_grid.evidence, "shuffled_candidates", guard(evidence.shuffled_candidates))
    monkeypatch.setattr(run_grid, "build_messages", guard(build_messages))
    monkeypatch.setattr(retrieve.CaseStore, "search", guard(retrieve.CaseStore.search, pos=2))
    run_grid.prepare(cfg)
    run_grid.run(cfg)
    assert {"build", "shuffled_candidates", "build_messages", "search"} <= set(seen)


def test_selective_evaluation_refuses_the_label_masked_store():
    """`no_precedent` masks the store by the query's true label: such rows never enter a selective
    evaluation, and the retrieval arm's similarity comes from the label-free `precedent` store."""
    rows = []
    for mode, sim in (("-", None), ("precedent", 0.3), ("no_precedent", 0.9)):
        rows.append({"model": "m", "model_role": "primary", "prompt_version": "v1", "incident_uid": "x.0000000000000001",
                     "case_id": "x.0000000000000001", "condition": "full", "system": "s",
                     "retrieval": "none" if sim is None else "hybrid", "store_mode": mode, "oracle_store": mode == "no_precedent",
                     "features": {"has_metrics": 1}, "hits": [] if sim is None else [{"dense_sim": sim}], "correct": True,
                     "rank": 1, "conf_consensus": 0.5, "conf_verbal": 0.5, "abstain_vote": 0.0, "parse_rate": 1.0,
                     "prompt_tokens": 1, "completion_tokens": 1, "latency_s": 0.0})
    df = pd.DataFrame(rows)
    with pytest.raises(ValueError, match="oracle_store"):
        selective.action_table(df)
    assert selective.action_table(df[~df.oracle_store])["hit_top_sim"].tolist() == [0.3]


def test_model_facing_modules_never_touch_labels():
    banned_attrs = {"root_service", "labels", "truth", "primary_root_service", "root_cause", "quality_state"}
    for name in MODEL_FACING:
        tree = ast.parse((RCA_ROOT / "src/rca" / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert node.attr not in banned_attrs, f"{name}:{node.lineno} .{node.attr}"
                assert not (node.attr == "fault"), f"{name}:{node.lineno} .fault"
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                # quality_state depends on the label (e.g. ROOT_NOT_CANDIDATE): selection only, never a model input
                assert not any(s in node.value for s in ("eval_only", "quality_state", "truth_time")), f"{name}:{node.lineno}"
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mods = [a.name for a in node.names] + ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
                assert not any(m and ("store" in m or "legacy_view" in m) for m in mods), f"{name}:{node.lineno}"


def test_visible_zone_scans_clean_and_detect_plants(rcaeval_home, tmp_path):
    from rca.store import CanonicalStore
    clean = audit.leakage_scan(CanonicalStore(rcaeval_home), "rcaeval")
    assert clean["total_hits"] == 0 and clean["label_texts_checked"] >= 1
    dh = tmp_path / "dh"
    shutil.copytree(rcaeval_home, dh)
    inc = dh / "canonical/v1/rcaeval/visible/incidents.jsonl"
    recs = read_jsonl(inc)
    recs[0]["context"]["visible_text"] = "alert: CANARY_ROOT_CAUSE_LINE carts failed to write order"
    recs[1]["context"]["visible_text"] = "see RE2-OB/checkoutservice_cpu/1/metrics.csv"
    recs[2]["root_service"] = "cart"
    write_jsonl_atomic(inc, recs)
    hit = audit.leakage_scan(CanonicalStore(dh), "rcaeval")
    assert hit["artefact_hits"] and hit["path_hits"] and hit["denylist_hits"]


def test_evidence_scan_flags_label_keys(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps({"schema": 2, "conditions": {"full": {"text": "ok"}}}), encoding="utf-8")
    assert audit.evidence_scan(tmp_path, set())["total_hits"] == 0
    (tmp_path / "b.json").write_text(json.dumps({"case": {"root_service": "cart"}}), encoding="utf-8")
    assert audit.evidence_scan(tmp_path, set())["total_hits"] >= 1


def test_headline_guard_refuses_the_label_masked_store():
    from rca import analyze
    df = pd.DataFrame([{"model": "m", "model_revision": "r", "server_fp": "f", "prompt_version": "v1", "backend": "vllm",
                        "incident_uid": "x.1", "condition": "full", "retrieval": "hybrid", "store_mode": m,
                        "oracle_store": m == "no_precedent", "evidence_fp": "e", "split_role": "test"}
                       for m in ("precedent", "no_precedent")])
    with pytest.raises(analyze.HeadlineGuardError, match="oracle_store"):
        analyze.guard_headline(df)
    analyze.guard_headline(df[~df.oracle_store])


def test_store_entries_are_train_role_and_never_in_the_query_group(canonical_synth, tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    cfg = canonical_run_cfg(canonical_synth["dh"], tmp_path, retrieval=["none", "hybrid"])
    run_grid.prepare(cfg)
    recs = run_grid.load_evidence(cfg)
    cn = run_grid.Canon(cfg)
    entries, _ = run_grid._store_entries(cfg, cn)
    assert entries and {cn.roles[e["case_id"]] for e in entries} == {"train"}
    store = CaseStore(entries, _tfidf())
    members = {}
    for u, g in cn.group.items():
        members.setdefault(g, set()).add(u)
    checked = 0
    for r in recs:
        vc, tr = r["vc"], r["truth"]
        grp = frozenset(members.get(cn.group.get(vc.case_id), ()))
        for meth in ("bm25", "dense", "hybrid"):
            for h in store.search(r["conditions"]["full"]["text"], vc, meth, "precedent", 10,
                                  exclude_ids=run_grid.exclusions(store, vc, tr, "precedent", grp)):
                assert cn.roles[h["case_id"]] == "train" and h["case_id"] not in grp
                assert cn.group.get(h["case_id"]) != cn.group.get(vc.case_id)
                checked += 1
    assert checked


# ---------------------------------------------------------------- store bound to the split
def _store_files(cfg) -> set[str]:
    return {p.stem for p in (Path(cfg["evidence_dir"]) / "store").glob("*.json")}


def test_store_follows_the_configured_split_not_the_evidence_dir(canonical_synth, tmp_path, monkeypatch):
    """Store files written for another split stay on disk; they never become precedents."""
    from rca import splits
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    dh = _home(canonical_synth, tmp_path)
    assert splits.split_cmd("within-rcaeval-retrieval", 1, canonical_synth["pcfg"], dh) in (0, 3)
    a = canonical_run_cfg(dh, tmp_path / "res", retrieval=["none", "hybrid"], conditions=["full"])
    b = {**a, "split": "within-rcaeval-retrieval-1"}
    run_grid.prepare(a)
    cn_b = run_grid.Canon(b)
    train_b = {i["incident_uid"] for i in cn_b.store_incidents()}
    stale = _store_files(a) - train_b
    assert stale and {cn_b.roles[u] for u in stale} - {"train"}       # split A's store holds B's held-out incidents
    assert train_b - _store_files(a)
    with pytest.raises(RuntimeError, match="prepare"):
        run_grid._store_entries(b, cn_b)                              # B's train incidents are not prepared yet
    run_grid.prepare(b)
    entries, info = run_grid._store_entries(b, cn_b)
    assert {e["case_id"] for e in entries} == train_b
    assert not {e["case_id"] for e in entries} & {vc.case_id for vc, _ in cn_b.selected()}
    assert info["ignored_files"] == len(_store_files(b) - train_b) > 0
    assert info["split_id"] == cn_b.split_id


def test_store_limit_selects_the_first_train_incidents(canonical_synth, tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    cfg = canonical_run_cfg(canonical_synth["dh"], tmp_path / "res", retrieval=["none", "hybrid"], conditions=["full"])
    run_grid.prepare(cfg)
    train = sorted(i["incident_uid"] for i in run_grid.Canon(cfg).store_incidents())
    small = {**cfg, "store_limit": 2}
    e_small, i_small = run_grid._store_entries(small, run_grid.Canon(small))
    e_all, i_all = run_grid._store_entries(cfg, run_grid.Canon(cfg))
    assert [e["case_id"] for e in e_small] == train[:2] and i_small["ignored_files"] == len(train) - 2
    assert [e["case_id"] for e in e_all] == train and i_all["ignored_files"] == 0
    assert i_small["binding"] != i_all["binding"]


def test_retrieval_without_a_split_is_refused(canonical_synth, tmp_path):
    cfg = canonical_run_cfg(canonical_synth["dh"], tmp_path / "res", split=None, retrieval=["none", "hybrid"])
    for step in (run_grid.prepare, run_grid.run):
        with pytest.raises(ValueError, match="split"):
            step(cfg)


def test_precedents_without_a_service_root_are_excluded_and_counted(canonical_synth, tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    dh = _home(canonical_synth, tmp_path)
    cfg = canonical_run_cfg(dh, tmp_path / "res", retrieval=["none", "hybrid"], conditions=["full"])
    train = sorted(i["incident_uid"] for i in run_grid.Canon(cfg).store_incidents())
    labs = read_jsonl(_labels_path(dh))
    for l in labs:
        if l["incident_uid"] == train[0]:
            l["root_cause"].update(primary_root_service=None, root_service_ids=["node-7"], label_granularity="node")
        if l["incident_uid"] == train[1]:
            l["root_cause"].update(primary_root_service=None, root_service_ids=["cart", "redis"],
                                   label_granularity="multi-service")
    write_jsonl_atomic(_labels_path(dh), labs)
    run_grid.prepare(cfg)
    entries, info = run_grid._store_entries(cfg, run_grid.Canon(cfg))
    assert info["excluded"] == {"node": 1, "multi-service": 1}
    assert {e["case_id"] for e in entries} == set(train[2:])
    assert all(e["root"] is not None and e["root_ids"] and e["granularity"] for e in entries)
    assert "None" not in format_hits(entries[:3])


def _entry(uid, root, ids, gran="service", fault="cpu"):
    return {"case_id": uid, "system": "s", "root": root, "root_ids": ids, "granularity": gran, "fault": fault,
            "text": f"metrics latency errors {uid} cart redis frontend checkout payment"}


def test_oracle_exclusion_and_hits_use_root_sets():
    store = CaseStore([_entry("t.1", "cart", ("cart",)), _entry("t.2", "redis", ("redis",)),
                       _entry("t.3", "cart", ("cart",), fault="mem")], _tfidf())
    assert store.oracle_exclusions(("cart", "redis"), "cpu") == {"t.1", "t.2"}      # set-scored query
    assert store.oracle_exclusions(("cart",), "cpu") == {"t.1"}
    assert store.oracle_exclusions((), "cpu") == frozenset()
    with pytest.raises(ValueError, match="service-level root"):
        format_hits([_entry("t.4", None, ("cart", "redis"), "multi-service")])


def test_format_hits_text_is_unchanged_for_service_roots():
    hits = [_entry("t.1", "cart", ("cart",)), _entry("t.2", "redis", ("redis",), fault="mem")]
    assert format_hits(hits) == (
        "# Similar past incidents (resolved, root cause known)\n\n"
        "### Past incident 1 — root cause: cart (cpu)\nmetrics latency errors t.1 cart redis frontend checkout payment\n\n"
        "### Past incident 2 — root cause: redis (mem)\nmetrics latency errors t.2 cart redis frontend checkout payment")
