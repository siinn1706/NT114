"""No label reaches model-visible data: canary, type guard, permutation invariance, scans, Jev allowlist."""
from __future__ import annotations

import ast
import json
import secrets
import shutil
from pathlib import Path

import pandas as pd
import pytest

from conftest import canonical_run_cfg
from rca import audit, decide, evidence, gate, jev, retrieve, run_grid
from rca.data import VisibleCase
from rca.llm import build_messages
from rca.retrieve import CaseStore, Embedder, format_hits
from rca.schema import DECISION_STATE_ALLOWED_KEYS
from rca.store import read_jsonl, write_jsonl_atomic

RCA_ROOT = Path(__file__).resolve().parents[1]
MODEL_FACING = ("evidence.py", "llm.py", "retrieve.py", "gate.py", "jev.py")
FIXED_AGG = {"ranking": [], "conf_verbal": 0.7, "conf_consensus": 0.5, "abstain_vote": 0.0, "n_samples": 10}
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
    """Everything a model or Jev would see, for test-role incidents: evidence, prompts with every
    retrieval method in `precedent` mode, and Jev states."""
    run_grid.prepare(cfg)
    recs = run_grid.load_evidence(cfg)
    cn = run_grid.Canon(cfg)
    store = CaseStore(run_grid._store_entries(cfg, recs, cn), _tfidf())
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
                agg = {**FIXED_AGG, "ranking": cands[:3]}
                inp = decide.decision_inputs(r, agg, cond, hits[0]["dense_sim"] if hits else None)
                out[f"{vc.case_id}|{cond}|{meth}|jev"] = json.dumps(jev.build_state(inp), sort_keys=True)
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


def test_jev_state_allowlist_and_precedent_similarity():
    inp = jev.DecisionInputs("evidence text", ["cart", "frontend"], 0.83, 0.8, 10, 0.0,
                             {"metrics": 1, "logs": 0, "traces": 1}, 5, top_sim=0.41)
    assert set(jev.build_state(inp)) <= DECISION_STATE_ALLOWED_KEYS
    rows = []
    for mode, sim in (("precedent", 0.3), ("no_precedent", 0.9)):
        for meth in ("none", "hybrid"):
            rows.append({"model": "m", "case_id": "x.0000000000000001", "condition": "full", "system": "s",
                         "retrieval": meth, "store_mode": "-" if meth == "none" else mode, "features": {"has_metrics": 1},
                         "hits": [] if meth == "none" else [{"dense_sim": sim}], "correct": True, "conf_consensus": 0.5,
                         "conf_verbal": 0.5, "abstain_vote": 0.0, "n_candidates": 3, "prompt_tokens": 1, "completion_tokens": 1})
    df = pd.DataFrame(rows).drop_duplicates(subset=["retrieval", "store_mode"])
    t = gate.action_table(df, "m", store_mode="precedent")
    assert t["hit_top_sim"].tolist() == [0.3]
    # the default (as used by `analyze --gate`) must be the label-free store
    assert gate.action_table(df, "m")["hit_top_sim"].tolist() == [0.3]
    with pytest.raises(ValueError, match="oracle"):
        gate.action_table(df, "m", store_mode="no_precedent")
    assert gate.action_table(df, "m", store_mode="no_precedent", oracle=True)["hit_top_sim"].tolist() == [0.9]


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


def _e2e(cfg) -> Path:
    """prepare -> run (mock LLM) -> decide (mock Jev); returns jev_raw.jsonl."""
    run_grid.prepare(cfg)
    run_grid.run(cfg)
    decide.run(cfg)
    return Path(cfg["out"]).parent / "jev_raw.jsonl"


def _e2e_cfg(dh, out, conditions=PERM_CONDITIONS):
    """`blind_root` is label-dependent by design (it masks the true root), so the permutation test leaves it out."""
    return canonical_run_cfg(dh, out, conditions=conditions, retrieval=["none", "hybrid"],
                             store_modes=["precedent"], n_samples=3,
                             models=[{"name": "m-primary", "backend": "mock", "role": "primary"},
                                     {"name": "m-esc", "backend": "mock", "role": "escalation"}],
                             jev={"backend": "mock", "cache": str(out / "jev.sqlite"), "variants": ["J-full", "J-AA"]})


def _request_shas(path: Path) -> dict:
    return {(r["incident_uid"], r["condition"], r["variant"], r["stage"]): r["request_sha"] for r in read_jsonl(path)}


def test_jev_states_label_permutation_invariant(canonical_synth, tmp_path, monkeypatch):
    """Permuting the label store (test-role roots and faults) and rerunning the whole chain leaves every
    Jev request unchanged, although scoring columns of the grid change."""
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    dh = _home(canonical_synth, tmp_path)
    base = _request_shas(_e2e(_e2e_cfg(dh, tmp_path / "a")))
    cfg = _e2e_cfg(dh, tmp_path / "b")
    test = _test_uids(cfg)
    labs = {l["incident_uid"]: l for l in read_jsonl(_labels_path(dh))}
    fields = [(labs[u]["root_cause"], labs[u]["fault"]) for u in test]
    fields = fields[1:] + fields[:1]
    for u, (rc, fa) in zip(test, fields):
        labs[u]["root_cause"], labs[u]["fault"] = rc, fa
    write_jsonl_atomic(_labels_path(dh), list(labs.values()))
    got = _request_shas(_e2e(cfg))
    assert base and got == base
    a = pd.DataFrame(read_jsonl(tmp_path / "a" / "grid.jsonl")).sort_values("key")["truth"].tolist()
    b = pd.DataFrame(read_jsonl(tmp_path / "b" / "grid.jsonl")).sort_values("key")["truth"].tolist()
    assert a != b                                       # the labels did change


def test_canary_not_in_jev_requests(canonical_synth, tmp_path, monkeypatch):
    """A canary written into every label-derived grid field never reaches a Jev request."""
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    dh = _home(canonical_synth, tmp_path)
    cfg = _e2e_cfg(dh, tmp_path / "res", PERM_CONDITIONS + ["blind_root"])
    run_grid.prepare(cfg)
    run_grid.run(cfg)
    canary = f"CANARY_{secrets.token_hex(8)}"
    rows = read_jsonl(Path(cfg["out"]))
    for r in rows:
        r["truth"], r["fault"], r["hit_has_truth"], r["truth_ids"] = canary, canary, canary, [canary]
        for h in r["hits"]:
            h["root"] = canary
    write_jsonl_atomic(Path(cfg["out"]), rows)
    decide.run(cfg)
    raw = (Path(cfg["out"]).parent / "jev_raw.jsonl").read_text(encoding="utf-8")
    assert raw.strip() and canary not in raw
