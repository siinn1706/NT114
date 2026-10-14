"""run_grid on the canonical path: synthetic data built by the RCAEval adapter, mock LLM."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import canonical_run_cfg
from rca import analyze, gate, run_grid
from rca.store import CanonicalStore, read_jsonl

LABEL_KEYS = {"root_service", "fault", "truth", "root", "case", "path", "fault_type", "root_cause"}
GATE_FIELDS = {"model", "retrieval", "store_mode", "case_id", "condition", "system", "features", "hits",
               "conf_consensus", "conf_verbal", "abstain_vote", "correct", "prompt_tokens", "completion_tokens"}
ANALYZE_FIELDS = {"rank", "parse_rate", "hit_has_truth", "store_mode", "retrieval", "condition", "model", "case_id"}


def _keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


@pytest.fixture(scope="module")
def synth(canonical_synth, tmp_path_factory):
    out = tmp_path_factory.mktemp("res")
    return {"dh": canonical_synth["dh"], "cfg": canonical_run_cfg(canonical_synth["dh"], out)}


def test_canonical_prepare_and_run(synth, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    cfg, dh = synth["cfg"], synth["dh"]
    run_grid.prepare(cfg)
    ev_dir = Path(cfg["evidence_dir"])
    cn = run_grid.Canon(cfg)
    files = sorted(ev_dir.glob("*.json"))
    assert files and len(files) == len(cn.selected())
    for f in files + sorted((ev_dir / "store").glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        assert rec["schema"] == 2 and not (set(_keys(rec)) & LABEL_KEYS), f.name
        assert "RE2-" not in f.read_text(encoding="utf-8")
    # generated conditions equal the condition matrix
    for f in files:
        rec = json.loads(f.read_text(encoding="utf-8"))
        assert list(rec["conditions"]) == cn.conditions(rec["incident_uid"])
    # store = train role ∩ eligible, and nothing else
    roles = {a["incident_uid"]: a["split"] for a in read_jsonl(cn.split_dir / "assignments.jsonl")}
    store_uids = {p.stem for p in (ev_dir / "store").glob("*.json")}
    eligible = {u for u, r in roles.items() if r == "train" and cn.matrix[u]["conditions"]["full"]["applicable"]}
    assert store_uids and store_uids == eligible
    assert not {u for u in store_uids if roles[u] != "train"}
    assert {json.loads(f.read_text(encoding="utf-8"))["incident_uid"] for f in files} <= {u for u, r in roles.items() if r == "test"}
    # eval-only ablation log next to the results
    log = read_jsonl(Path(cfg["out"]).parent / "ablation_log.jsonl")
    labels = CanonicalStore(dh).labels("rcaeval")
    for r in log:
        root = labels[r["pair_id"]]["root_cause"]["primary_root_service"]
        if r["condition"] == "blind_root":
            assert r["masked_service"] == root
        if r["condition"] == "blind_nonroot":
            assert r["masked_service"] not in (None, root)

    run_grid.run(cfg)
    rows = [json.loads(l) for l in open(cfg["out"], encoding="utf-8")]
    assert rows
    for r in rows:
        assert GATE_FIELDS | ANALYZE_FIELDS | {"incident_uid", "pair_id", "split_id", "oracle_store"} <= set(r)
        assert r["oracle_store"] == (r["store_mode"] == "no_precedent")
        lab = labels[r["incident_uid"]]
        assert r["truth"] == lab["root_cause"]["primary_root_service"]
        for h in r["hits"]:
            assert roles[h["case_id"]] == "train"
            if r["store_mode"] == "no_precedent":
                hl = labels[h["case_id"]]
                assert (hl["root_cause"]["primary_root_service"], hl["fault"]["type_raw"]) != (r["truth"], r["fault"])
    df = analyze.load(cfg["out"])
    assert len(analyze.cell_table(df))
    t = gate.action_table(df, "mock-small", "mock-big", retrieval="hybrid", store_mode="precedent")
    assert len(t) and "hit_top_sim" in t
    res = gate.leave_one_system_out(t)
    assert set(res["policy"]) >= {"always_answer", "learned"}


def test_rerun_is_idempotent(synth, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    cfg = synth["cfg"]
    ev = {p.name: p.read_bytes() for p in Path(cfg["evidence_dir"]).rglob("*.json")}
    n = sum(1 for _ in open(cfg["out"], encoding="utf-8"))
    run_grid.prepare(cfg)
    run_grid.run(cfg)
    assert {p.name: p.read_bytes() for p in Path(cfg["evidence_dir"]).rglob("*.json")} == ev
    assert sum(1 for _ in open(cfg["out"], encoding="utf-8")) == n


def test_changed_evidence_logic_is_never_reused(synth, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    cfg = synth["cfg"]
    ev_dir = Path(cfg["evidence_dir"])
    before = {p.name: json.loads(p.read_text(encoding="utf-8"))["evidence_fp"] for p in ev_dir.rglob("*.json")}
    n = sum(1 for _ in open(cfg["out"], encoding="utf-8"))
    monkeypatch.setattr(run_grid.evidence, "BUILDER_VERSION", "changed")
    with pytest.raises(RuntimeError, match="stale evidence"):
        run_grid.run(cfg)                     # old evidence is refused, not silently used
    run_grid.prepare(cfg)
    after = {p.name: json.loads(p.read_text(encoding="utf-8"))["evidence_fp"] for p in ev_dir.rglob("*.json")}
    assert after.keys() == before.keys() and all(after[k] != before[k] for k in after)
    run_grid.run(cfg)
    rows = [json.loads(line) for line in open(cfg["out"], encoding="utf-8")]
    assert len(rows) == 2 * n                 # every cell recomputed under the new fingerprint
    assert {r["evidence_fp"] for r in rows[n:]}.isdisjoint({r["evidence_fp"] for r in rows[:n]})


def test_evidence_options_change_the_fingerprint():
    from rca import evidence
    assert evidence.fingerprint() != evidence.fingerprint(log_trace_segment_gap_s=30.0)
    assert evidence.fingerprint(log_trace_segment_gap_s=30.0) != evidence.fingerprint(log_trace_segment_gap_s=20.0)
