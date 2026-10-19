"""Evidence visibility audit: root named in the evidence vs candidate membership (evaluation-only)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from conftest import RCA_ROOT, canonical_run_cfg
from rca import run_grid, visibility
from rca.store import CanonicalStore

TEXT = ("## Metrics (robust z-score vs. 10 min before incident)\n- cart: cpu up z=9 (1->2)\n- front: latency up z=4\n\n"
        "## Logs (5 min after vs. 10 min before)\n- front: error-log rate 0.0/min -> 5.0/min\n"
        "- front: new error template: \"call to cart failed\"\n\n"
        "## Traces (per service, after vs. before)\n- front: p90 latency 1.0ms -> 3.0ms (x3.0)\n"
        "Slowest-growing call edges:\n- front -> pay: median latency x2.0")
CANDS = ["cart", "front", "pay", "db", "car"]


def test_block_and_edge_flags():
    v = visibility.visibility(TEXT, ("cart",), CANDS)
    assert v["named"] and v["named_metrics"] and not v["named_logs"] and not v["named_traces"]
    assert v["token_anywhere"] and v["in_candidates"] and v["has_traces_block"]
    v = visibility.visibility(TEXT, ("pay",), CANDS)
    assert v["named"] and v["named_trace_edge"] and not v["named_traces"] and not v["named_metrics"]
    v = visibility.visibility(TEXT, ("front",), CANDS)
    assert v["named_metrics"] and v["named_logs"] and v["named_traces"]


def test_unnamed_root_and_candidate_membership_are_separate():
    v = visibility.visibility(TEXT, ("db",), CANDS)
    assert v["in_candidates"] and not v["named"] and not v["token_anywhere"]
    v = visibility.visibility(TEXT, ("car",), CANDS)                  # "car" is not a word in "cart"
    assert not v["named"] and not v["token_anywhere"]
    v = visibility.visibility(TEXT, ("ghost",), CANDS)
    assert not v["in_candidates"] and not v["named"]
    assert visibility.visibility(TEXT, ("ghost", "cart"), CANDS)["named"]   # set-scored: any member counts
    no_tr = visibility.visibility("## Metrics (x)\n- cart: cpu up z=9\n\n## Not available\n- traces were not collected",
                                  ("cart",), CANDS)
    assert not no_tr["has_traces_block"] and not no_tr["has_logs_block"] and no_tr["named"]


def _digest(d: Path) -> dict:
    return {p.relative_to(d).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.rglob("*")) if p.is_file()}


def test_audit_on_canonical_synthetic(canonical_synth, tmp_path):
    dh = canonical_synth["dh"]
    cfg = canonical_run_cfg(dh, tmp_path, conditions=["full", "no_metric", "blind_root"], retrieval=["none"],
                            store_modes=["precedent"], models=[])
    run_grid.prepare(cfg)
    ev_dir = Path(cfg["evidence_dir"])
    before = _digest(ev_dir)
    path = tmp_path / "cfg.yaml"
    path.write_text(yaml.safe_dump({k: v for k, v in cfg.items() if k != "_hash"}), encoding="utf-8")
    tab = visibility.main([str(path)])
    assert _digest(ev_dir) == before                                   # evidence files untouched, nothing added

    out = Path(cfg["out"]).parent
    recs = pd.read_json(out / "evidence_visibility.jsonl", lines=True)
    n_expected = sum(len(json.loads(f.read_text(encoding="utf-8"))["conditions"]) for f in ev_dir.glob("*.json"))
    assert len(recs) == n_expected and recs["in_candidates"].all()
    br = recs[recs.condition == "blind_root"]
    assert len(br) and not br["named_traces"].any() and not br["named_trace_edge"].any()
    assert set(tab["condition"]) == set(recs["condition"]) and tab["n_records"].sum() == len(recs)
    assert {"split_id", "split_role", "named_given_candidate"} <= set(tab.columns)
    assert (out / "table_evidence_visibility.csv").is_file()
    roots = {l["root_cause"]["primary_root_service"] for l in CanonicalStore(dh).labels("rcaeval").values()}
    blob = (out / "evidence_visibility.jsonl").read_text(encoding="utf-8")
    assert not [r for r in roots if f'"{r}"' in blob]                   # flags only, no service names
    counts = json.loads((out / "visibility_counts.json").read_text(encoding="utf-8"))
    assert counts["selected"] == len(list(ev_dir.glob("*.json"))) and not counts["missing_evidence"]
    assert counts["in_roles"] == counts["selected"] + len(counts["excluded_full_not_applicable"])

    f = next(iter(sorted(ev_dir.glob("*.json"))))                      # a file prepared for other conditions
    rec = json.loads(f.read_text(encoding="utf-8"))
    rec["conditions"].pop("no_metric", None) or rec["conditions"].pop("full")
    f.write_text(json.dumps(rec), encoding="utf-8")
    with pytest.raises(RuntimeError, match="applicable"):
        visibility.rows(cfg)
    rec["evidence_fp"] = "stale"
    f.write_text(json.dumps(rec), encoding="utf-8")
    with pytest.raises(RuntimeError, match="stale evidence"):
        visibility.rows(cfg)


def test_outputs_never_go_into_the_evidence_dir(tmp_path):
    cfg = {"out": str(tmp_path / "ev" / "grid.jsonl"), "evidence_dir": str(tmp_path / "ev")}
    with pytest.raises(ValueError, match="evidence dir"):
        visibility.out_dir(cfg)


def test_model_facing_modules_do_not_import_the_audit():
    for mod in ("llm", "evidence", "retrieve", "selective", "run_grid"):
        assert "visibility" not in (RCA_ROOT / "src" / "rca" / f"{mod}.py").read_text(encoding="utf-8"), mod
