"""run_grid on the canonical path: synthetic data built by the RCAEval adapter, mock LLM."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from conftest import canonical_run_cfg
from rca import analyze, run_grid, selective
from rca.store import CanonicalStore, read_jsonl

LABEL_KEYS = {"root_service", "fault", "truth", "root", "case", "path", "fault_type", "root_cause"}
GATE_FIELDS = {"model", "retrieval", "store_mode", "case_id", "condition", "system", "features", "hits",
               "conf_consensus", "conf_verbal", "abstain_vote", "correct", "prompt_tokens", "completion_tokens"}
ANALYZE_FIELDS = {"rank", "parse_rate", "hit_has_truth", "store_mode", "retrieval", "condition", "model", "case_id"}
ROW_FIELDS = {"prompt_version", "model_revision", "model_role", "sampling", "truth_ids", "label_granularity",
              "parse_failed", "set_scored", "correct_at_3", "server_fp", "split_role"}


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
        assert ROW_FIELDS <= set(r)
        assert r["prompt_version"] == "v1" and r["model_role"] == "primary" and r["split_role"] == "test"
        assert r["truth_ids"] == [r["truth"]] and r["correct"] == (r["rank"] == 1)
        assert r["oracle_store"] == (r["store_mode"] == "no_precedent")
        lab = labels[r["incident_uid"]]
        assert r["truth"] == lab["root_cause"]["primary_root_service"]
        for h in r["hits"]:
            assert roles[h["case_id"]] == "train"
            if r["store_mode"] == "no_precedent":
                hl = labels[h["case_id"]]
                assert (hl["root_cause"]["primary_root_service"], hl["fault"]["type_raw"]) != (r["truth"], r["fault"])
    df = analyze.load(cfg["out"])
    assert len(analyze.cell_table(analyze.attach_units(df), n_boot=50))
    t = selective.action_table(df[~df.oracle_store.astype(bool)], model="mock-small")
    assert len(t) and "hit_top_sim" in t
    res = selective.evaluate(t, selective.fixed(t, "answer"))
    assert res["coverage"] == pytest.approx(1.0)


def test_rerun_is_idempotent(synth, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    cfg = synth["cfg"]
    ev = {p.name: p.read_bytes() for p in Path(cfg["evidence_dir"]).rglob("*.json")}
    n = sum(1 for _ in open(cfg["out"], encoding="utf-8"))
    run_grid.prepare(cfg)
    run_grid.run(cfg)
    assert {p.name: p.read_bytes() for p in Path(cfg["evidence_dir"]).rglob("*.json")} == ev
    assert sum(1 for _ in open(cfg["out"], encoding="utf-8")) == n


GOLDEN = Path(__file__).resolve().parent / "golden/canonical_synthetic_evidence.sha256"
FIXTURE_GOLDEN = Path(__file__).resolve().parent / "golden/canonical_fixture_evidence.sha256"
ALL_CONDITIONS = ["full", "no_trace", "no_log", "no_metric", "metrics_only", "blind_root", "blind_nonroot",
                  "blind_nonroot_ev"]


def read_golden(path: Path) -> dict[str, str]:
    return dict(reversed(line.split("  ")) for line in path.read_text(encoding="utf-8").splitlines())


def evidence_digests(ev_dir: Path) -> dict[str, str]:
    """sha256 of the model-visible part (candidates, conditions) of every query and store evidence file."""
    out = {}
    for f in sorted(ev_dir.rglob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        blob = json.dumps({"candidates": r["candidates"], "conditions": r["conditions"]}, sort_keys=True,
                          ensure_ascii=False, separators=(",", ":"))
        out[f.relative_to(ev_dir).as_posix()] = hashlib.sha256(blob.encode()).hexdigest()
    return out


def test_canonical_synthetic_matches_golden(canonical_synth, tmp_path, monkeypatch):
    """Evidence parity: the digests were captured when this path matched the retired direct RCAEval loader
    (identical text for every shared condition; features within the float-parser tolerance)."""
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    cfg = canonical_run_cfg(canonical_synth["dh"], tmp_path)
    run_grid.prepare(cfg)
    assert evidence_digests(Path(cfg["evidence_dir"])) == read_golden(GOLDEN)


@pytest.fixture(scope="module")
def fixture_eval_home(tmp_path_factory) -> Path:
    """The RCAEval fixture zips (every known raw defect) built, condition-matrixed and split eval-only."""
    from conftest import build_fixture_home, fixture_config
    from rca import splits
    dh = tmp_path_factory.mktemp("fixture_eval") / "dh"
    build_fixture_home(dh)
    pcfg = fixture_config()
    assert splits.conditions_cmd("rcaeval", pcfg, dh) == 0
    assert splits.split_cmd("eval-only-rcaeval", 0, pcfg, dh) == 0
    return dh


def test_fixture_build_matches_golden(fixture_eval_home, tmp_path, monkeypatch):
    """Evidence regression on the raw-defect fixture cases, all three systems and every applicable condition.

    Evidence is rebuilt from scratch, so a change to the canonical view or the evidence builder fails here even
    when the evidence fingerprint was not bumped. The digests were captured when all 36 condition pairs the retired
    direct RCAEval loader could build on these cases had identical text and features within 1e-9. Recapture them
    only for an intended evidence change."""
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    cfg = canonical_run_cfg(fixture_eval_home, tmp_path, split="eval-only-rcaeval-0", retrieval=["none"],
                            conditions=ALL_CONDITIONS)
    cfg.pop("systems")
    run_grid.prepare(cfg)
    got = evidence_digests(Path(cfg["evidence_dir"]))
    assert len(got) == 7 and got == read_golden(FIXTURE_GOLDEN)


def test_load_cfg_rejects_non_canonical_configs(tmp_path):
    p = tmp_path / "old.yaml"
    p.write_text("evidence_dir: x\nconditions: [full]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="only `source: canonical`"):
        run_grid.load_cfg(p)


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


def test_nonroot_ev_target_is_evidence_matched():
    full = ("## Metrics\n- a: cpu up\n- b: mem up\n- c: x\n- c: y\n\n"
            "## Traces (per service, after vs. before)\n- a: slow\n- b: slow\n- c: slow\n- d: err")
    # root a has 2 lines; b has 2 (closest), c has 3, d has 1
    assert run_grid.nonroot_ev_target(full, "a", "u1") == "b"
    assert run_grid.nonroot_ev_target(full, "a", "u1") == run_grid.nonroot_ev_target(full, "a", "u1")
    assert run_grid.nonroot_ev_target("## Metrics\n- a: up", "a", "u") is None           # no Traces block
    assert run_grid.nonroot_ev_target("## Traces (x)\n- a: slow", "a", "u") is None      # only the root is listed
    tie = "## Traces (x)\n- a: s\n- b: s\n- c: s"
    picks = {run_grid.nonroot_ev_target(tie, "a", f"u{i}") for i in range(20)}
    assert picks == {"b", "c"}                                                         # ties by sha256(uid + service)


def test_blind_nonroot_ev(canonical_synth, tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    cfg = canonical_run_cfg(canonical_synth["dh"], tmp_path, conditions=["full", "blind_root", "blind_nonroot_ev"],
                            retrieval=["none"])
    run_grid.prepare(cfg)
    cn = run_grid.Canon(cfg)
    labels = CanonicalStore(canonical_synth["dh"]).labels("rcaeval")
    log = {(r["pair_id"], r["condition"]): r["masked_service"] for r in read_jsonl(Path(cfg["out"]).parent / "ablation_log.jsonl")}
    seen = 0
    for f in sorted(Path(cfg["evidence_dir"]).glob("*.json")):
        text = f.read_text(encoding="utf-8")
        rec = json.loads(text)
        uid = rec["incident_uid"]
        root = labels[uid]["root_cause"]["primary_root_service"]
        assert set(rec["same_as_full"]) == set(rec["conditions"]) and rec["same_as_full"]["full"]
        if "blind_nonroot_ev" not in rec["conditions"]:
            assert "blind_root" not in cn.conditions(uid) or rec.get("skipped") == ["blind_nonroot_ev"]
            continue
        seen += 1
        target = log[(uid, "blind_nonroot_ev")]
        assert target not in (None, root)
        assert f"- {target}:" in rec["conditions"]["full"]["text"].split("## Traces", 1)[1]
        assert target == run_grid.nonroot_ev_target(rec["conditions"]["full"]["text"], root, uid)
        assert "masked" not in text and "nonroot_target" not in text                     # target only in the eval-only log
        assert rec["conditions"]["blind_nonroot_ev"]["text"] != rec["conditions"]["full"]["text"]
    assert seen
    before = {p.name: p.read_bytes() for p in Path(cfg["evidence_dir"]).glob("*.json")}
    run_grid.prepare(cfg)                                                              # current files are reused
    assert {p.name: p.read_bytes() for p in Path(cfg["evidence_dir"]).glob("*.json")} == before


def test_embedder_kind_pinned(canonical_synth, tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    from rca import retrieve

    class FallbackEmbedder(retrieve.Embedder):
        def __init__(self, name):
            super().__init__("tfidf")
            self.model_name = name                         # a dense model was asked for, TF-IDF is what loaded

    cfg = canonical_run_cfg(canonical_synth["dh"], tmp_path / "a", conditions=["full"], retrieval=["none", "hybrid"],
                            store_modes=["precedent"], embedder="BAAI/bge-small-en-v1.5")
    run_grid.prepare(cfg)
    monkeypatch.setattr(run_grid, "Embedder", FallbackEmbedder)
    with pytest.raises(RuntimeError, match="unavailable"):
        run_grid.run(cfg)

    class FakeDense(retrieve.Embedder):
        """Reports kind `st` (a dense model loaded) but computes TF-IDF vectors."""
        def __init__(self, name):
            super().__init__("tfidf")
            self.kind = "st"

        def _as_tfidf(self, fn, *a):
            self.kind = "tfidf-svd"
            try:
                return fn(*a)
            finally:
                self.kind = "st"

        def fit(self, texts):
            self._as_tfidf(super().fit, texts)
            return self

        def encode(self, texts):
            return self._as_tfidf(super().encode, texts)

    monkeypatch.setattr(run_grid, "Embedder", FakeDense)
    run_grid.run(cfg)
    monkeypatch.undo()
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    cfg_t = {**cfg, "embedder": "tfidf", "out": str(tmp_path / "b" / "grid.jsonl"), "cache": str(tmp_path / "b" / "c.sqlite")}
    run_grid.run(cfg_t)
    fp = lambda path: {json.loads(l)["store_fp"] for l in open(path, encoding="utf-8")} - {None}
    assert fp(cfg["out"]) and fp(cfg_t["out"]) and fp(cfg["out"]).isdisjoint(fp(cfg_t["out"]))
