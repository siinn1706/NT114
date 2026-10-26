"""IM1 frame on the synthetic store: label-free, train-only, frozen before val/test evidence, every record
kept in the denominator; the four arms end to end with the mock LLM (one call per answer)."""
from __future__ import annotations

import hashlib
import json
import secrets
import shutil
from collections import Counter

import pytest

from conftest import canonical_run_cfg
from rca import im1_frame, run_grid
from rca.llm import LLM, build_messages
from rca.store import read_json, read_jsonl, write_jsonl_atomic

ARMS = ["l0", "ra", "ra_im1", "ra_im1_shuf"]
CONDS = ["full", "no_trace", "no_log", "no_metric"]


def _home(canonical_synth, tmp_path):
    dh = tmp_path / "dh"
    for part in ("canonical", "reports", "splits"):
        shutil.copytree(canonical_synth["dh"] / part, dh / part)
    return dh


def _cfg(dh, out, **over):
    return canonical_run_cfg(dh, out, conditions=CONDS, retrieval=["none"], arms=ARMS,
                             models=[{"name": "mock-small", "backend": "mock"}], **over)


def _frame_hashes(cfg) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(run_grid.frames_dir(cfg).glob("*.json"))}


@pytest.fixture(scope="module")
def run4(canonical_synth, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("im1")
    dh = _home(canonical_synth, tmp)
    cfg = _cfg(dh, tmp / "res")
    calls = Counter()
    real = LLM.ask

    def counted(self, messages, candidates, scope=None):
        calls[scope or "l0"] += 1
        return real(self, messages, candidates, scope)

    LLM.ask = counted
    try:
        run_grid.prepare(cfg)
        frozen = _frame_hashes(cfg)
        run_grid.run(cfg)
    finally:
        LLM.ask = real
    return {"cfg": cfg, "dh": dh, "rows": read_jsonl(cfg["out"]), "calls": dict(calls), "frozen": frozen}


def test_frames_are_frozen_and_recorded_in_the_manifest(run4):
    cfg = run4["cfg"]
    assert run4["frozen"] and _frame_hashes(cfg) == run4["frozen"]          # val/test evidence changed nothing
    run_grid.prepare(cfg)                                                   # rebuild gives the frozen hashes
    assert _frame_hashes(cfg) == run4["frozen"]
    man = read_json(cfg["out"].replace("grid.jsonl", "manifest.json"))
    frames = im1_frame.load_frozen(run_grid.frames_dir(cfg))
    assert man["im1_frames"] == im1_frame.manifest(frames)
    systems = {tuple(e["key"])[2]: e for e in man["im1_frames"].values()}
    assert systems["online-boutique"]["valid"] and systems["train-ticket"]["valid"]
    assert not systems["sock-shop"]["valid"] and systems["sock-shop"]["n_contributing"] == 0


def test_paths_and_denominator_per_arm(run4):
    rows = run4["rows"]
    cells = {a: sorted((r["incident_uid"], r["condition"]) for r in rows if r.get("arm", "l0") == a) for a in ARMS}
    assert all(cells[a] == cells["l0"] for a in ARMS)                      # no record leaves any arm
    by = {(r["arm"], r["system"], r["condition"]): r["path"] for r in rows if "arm" in r}
    for arm in ("ra_im1", "ra_im1_shuf"):
        assert by[(arm, "online-boutique", "no_trace")] == "no_trace"
        assert by[(arm, "sock-shop", "full")] == "frame_free"              # key without a valid frame
        assert by[(arm, "online-boutique", "full")] == "trace"
    assert by[("ra", "online-boutique", "no_trace")] == "frame_free"
    framed = [r for r in rows if r.get("arm") in ("ra_im1", "ra_im1_shuf")]
    assert all(r["frame_sha256"] for r in framed)


def test_one_call_per_answer_for_every_arm(run4):
    rows = run4["rows"]
    assert all(r.get("llm_calls", 1) == 1 for r in rows)
    assert run4["calls"] == {a: sum(r.get("arm", "l0") == a for r in rows) for a in ARMS}


def test_frame_used_only_on_the_no_trace_path(run4):
    cfg = run4["cfg"]
    ev = {a: {r["incident_uid"]: r for r in run_grid.load_arm_evidence(cfg, a)} for a in ("ra", "ra_im1", "ra_im1_shuf")}
    for uid, r in ev["ra"].items():
        for cond, e in r["conditions"].items():
            for a in ("ra_im1", "ra_im1_shuf"):
                f = ev[a][uid]["conditions"][cond]
                if f["path"] != "no_trace":
                    assert f["text"] == e["text"]
    assert any(ev["ra_im1"][u]["conditions"]["no_trace"]["text"] != ev["ra_im1_shuf"][u]["conditions"]["no_trace"]["text"]
               for u in ev["ra"] if "no_trace" in ev["ra"][u]["conditions"])


def test_tampered_frame_is_refused(run4, tmp_path):
    cfg = dict(run4["cfg"], im1_frames_dir=str(tmp_path / "frames"))
    shutil.copytree(run_grid.frames_dir(run4["cfg"]), tmp_path / "frames")
    p = next((tmp_path / "frames").glob("*.real.json"))
    fr = json.loads(p.read_text(encoding="utf-8"))
    fr["edges"] = fr["edges"][1:]
    p.write_text(json.dumps(fr), encoding="utf-8")
    with pytest.raises(RuntimeError, match="does not match its sha256"):
        run_grid.load_arm_evidence(cfg, "ra_im1")


def test_test_role_incident_never_builds_a_frame(run4):
    cn = run_grid.Canon(run4["cfg"])
    test_uid = next(u for u, r in cn.roles.items() if r == "test")
    inc = cn.store.incident(test_uid)
    with pytest.raises(ValueError, match="train-role"):
        im1_frame.build_frame(cn.store, [inc], cn.roles, im1_frame.key_of(inc, cn.split_id))


def framed_artifacts(cfg) -> dict[str, str]:
    run_grid.prepare(cfg)
    out = {f"frame|{k}": v for k, v in _frame_hashes(cfg).items()}
    for arm in ("ra_im1", "ra_im1_shuf"):
        for r in run_grid.load_arm_evidence(cfg, arm):
            for cond, ev in r["conditions"].items():
                out[f"{arm}|{r['incident_uid']}|{cond}"] = json.dumps(
                    [ev, build_messages(r["vc"], r["candidates"], ev["text"])], sort_keys=True)
    return out


def test_frames_and_framed_evidence_are_label_free(canonical_synth, tmp_path):
    dh = _home(canonical_synth, tmp_path)
    base = framed_artifacts(_cfg(dh, tmp_path / "a"))
    labels = dh / "canonical/v1/rcaeval/eval_only/labels.jsonl"
    labs = read_jsonl(labels)
    canary = f"CANARY_{secrets.token_hex(8)}"
    fields = [(l["root_cause"], l["fault"]) for l in labs]
    fields = fields[1:] + fields[:1]                       # permutes train labels too
    for l, (rc, fa) in zip(labs, fields):
        l["root_cause"], l["fault"] = dict(rc, original=canary), dict(fa, type_raw=canary)
    write_jsonl_atomic(labels, labs)
    cfg = _cfg(dh, tmp_path / "b")
    after = framed_artifacts(cfg)
    assert after == base and not [k for k, v in after.items() if canary in v]
    assert not [p for p in run_grid.frames_dir(cfg).glob("*.json") if canary in p.read_text(encoding="utf-8")]
