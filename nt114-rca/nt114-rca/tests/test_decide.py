"""Decision runner: offline end-to-end chain, action table, fail-closed, resume, headline guards."""
from __future__ import annotations

import json
import socket
from pathlib import Path

import pandas as pd
import pytest

from conftest import canonical_run_cfg
from rca import analyze, decide, gate, jev, run_grid
from rca.store import read_jsonl

CONDS = ["full", "no_trace", "no_log", "metrics_only", "blind_root", "blind_nonroot_ev"]
MODELS = [{"name": "m-primary", "backend": "mock", "role": "primary", "revision": "r1"},
          {"name": "m-esc", "backend": "mock", "role": "escalation", "revision": "r1"}]
VARIANTS = ["J-full", "J-AA", "J-noconf", "J-noevidence"]


def _cfg(dh, out, **over):
    base = dict(conditions=CONDS, retrieval=["none", "hybrid"], store_modes=["precedent"], n_samples=10, models=MODELS,
                jev={"backend": "mock", "cache": str(out / "jev.sqlite"), "variants": VARIANTS})
    return canonical_run_cfg(dh, out, **{**base, **over})


@pytest.fixture(scope="module")
def chain(canonical_synth, tmp_path_factory):
    """prepare -> run -> decide with every socket connection refused."""
    out = tmp_path_factory.mktemp("chain")
    cfg = _cfg(canonical_synth["dh"], out)
    mp = pytest.MonkeyPatch()
    mp.setenv("HF_HUB_OFFLINE", "1")

    def no_network(*a, **k):
        raise AssertionError("network access in the offline chain")
    mp.setattr(socket.socket, "connect", no_network)
    try:
        run_grid.prepare(cfg)
        run_grid.run(cfg)
        counts = decide.run(cfg)
    finally:
        mp.undo()
    return {"cfg": cfg, "out": out, "counts": counts}


def test_smoke_end_to_end(chain):
    cfg, out = chain["cfg"], chain["out"]
    grid = analyze.load(cfg["out"])
    prim = grid[(grid.model_role == "primary") & (grid.retrieval == "none")]
    dec = decide.load_decisions(out / "decisions.jsonl")
    assert len(dec) == len(prim) * len(VARIANTS) == chain["counts"]["rows"] and dec["done"].all()
    assert set(dec["variant"]) == set(VARIANTS) and "blind_nonroot_ev" in set(dec["condition"])
    full = dec[dec.variant == "J-full"].iloc[0]
    assert {"stage1", "stage2_retrieve", "stage2_escalate"} <= set(full.dropna().index)
    aa = dec[dec.variant == "J-AA"].iloc[0]
    assert set(aa["available_actions"]) == {"accept", "abstain"} and not isinstance(aa.get("stage2_retrieve"), dict)
    for r in dec.itertuples():
        assert not set(r._asdict()) & {"truth", "truth_ids", "correct", "rank", "fault", "hit_has_truth"}
    raws = read_jsonl(out / "jev_raw.jsonl")
    noev = [r for r in raws if r["variant"] == "J-noevidence"]
    assert noev and all("evidence" not in r["request"]["state"] for r in noev)
    assert all("assistant_confidence" not in r["request"]["state"] for r in raws if r["variant"] == "J-noconf")
    rep = analyze.decision_report(grid, dec, out, smoke=True, draws=20, n_boot=50)
    pols = set(rep["policies"]["policy"])
    assert {"L0 always answer", "L1 self-abstain", "L2 always escalate", "J-full", "J-AA", "C1 coverage-matched consensus",
            "C2 coverage-matched random", "R1 route-matched random", "R2 route-matched consensus", "O oracle"} <= pols
    assert (out / "smoke_table_policies.csv").is_file() and rep["jev_error_rate"] == 0.0
    assert {"dataset", "label_granularity", "condition"} <= set(rep["cells"])
    assert {"cov_logs", "cov_traces"} <= set(rep["cells_by_coverage"]) and rep["cells"]["n_injections"].min() >= 1
    assert {"jev_p_accept", "jev_supported", "consensus"} == set(rep["jev_scores"]["score"])
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert man["prompt_version"] == "v1" and man["jev_pinned_model"] == "jev-1.13.0"
    assert {m["role"] for m in man["models"]} == {"primary", "escalation"}


def test_rerun_skips_done_rows(chain):
    again = decide.run(chain["cfg"])
    assert again["rows"] == 0 and again["skipped_done"] == chain["counts"]["rows"]


def test_headline_guards(chain):
    grid = analyze.load(chain["cfg"]["out"])
    dec = decide.load_decisions(chain["out"] / "decisions.jsonl")
    with pytest.raises(analyze.HeadlineGuardError, match="mock"):
        analyze.decision_report(grid, dec, chain["out"])
    live = grid.assign(backend="vllm")
    live_dec = dec.assign(jev_backend="live")
    analyze.guard_headline(live, live_dec)                                     # clean: no error
    with pytest.raises(analyze.HeadlineGuardError, match="DEV"):
        analyze.guard_headline(live.assign(split_role="val"))
    with pytest.raises(analyze.HeadlineGuardError, match="prompt_version"):
        analyze.guard_headline(live.assign(prompt_version=["v1", "v2"] * (len(live) // 2) + ["v1"] * (len(live) % 2)))
    with pytest.raises(analyze.HeadlineGuardError, match="jev_question_version"):
        analyze.guard_headline(live, live_dec.assign(jev_question_version=["q1", "q2"] * (len(dec) // 2) + ["q1"] * (len(dec) % 2)))


def test_duplicate_rows_fail(chain):
    grid = analyze.load(chain["cfg"]["out"])
    prim = grid[(grid.model_role == "primary") & (grid.retrieval == "none")]
    with pytest.raises(ValueError, match="duplicate"):
        decide.action_table(pd.concat([grid, prim.iloc[[0]]]), "v1")
    # another revision of the same role is filtered out, not mixed in
    other = prim.iloc[[0]].assign(model_revision="r2")
    t = decide.action_table(pd.concat([grid, other]), "v1", {"primary": "r1"})
    assert len(t) == len(prim)
    with pytest.raises(ValueError, match="no primary rows"):
        decide.action_table(grid, "v9")


def test_rejects_oracle_rows(chain):
    grid = analyze.load(chain["cfg"]["out"])
    bad = grid.iloc[[0]].assign(oracle_store=True, store_mode="no_precedent", retrieval="hybrid")
    with pytest.raises(ValueError, match="oracle"):
        decide.select_rows(pd.concat([grid, bad]), "v1", {})


def test_action_table_arms(chain):
    grid = analyze.load(chain["cfg"]["out"])
    t = decide.action_table(grid, "v1")
    for a in ("answer", "retrieve", "escalate"):
        assert {f"{a}_ok", f"{a}_tok", f"{a}_conf"} <= set(t)
    assert (t["escalate_tok"] >= t["answer_tok"]).all() and t["hit_top_sim"].notna().all()
    assert gate.evaluate(t, gate.fixed(t, "escalate"))["coverage"] == pytest.approx(1.0)


def test_fail_closed(chain):
    grid = analyze.load(chain["cfg"]["out"])
    t = decide.action_table(grid, "v1")
    dec = decide.load_decisions(chain["out"] / "decisions.jsonl")
    d = dec[dec.variant == "J-full"].copy()
    key = (t.iloc[0]["incident_uid"], t.iloc[0]["condition"])
    i = d[(d.incident_uid == key[0]) & (d.condition == key[1])].index[0]
    d.at[i, "stage1"] = {**d.at[i, "stage1"], "status": "error", "action": None}
    acts, flagged = gate.jev_policy(t, d, "J-full")
    assert acts.iloc[0] == "abstain" and flagged.iloc[0] and flagged.sum() == 1
    # a failed stage 2 on the chosen path is also fail-closed
    j = d.index[1]
    d.at[j, "stage1"] = {**d.at[j, "stage1"], "status": "ok", "action": "escalate"}
    d.at[j, "stage2_escalate"] = {**d.at[j, "stage2_escalate"], "status": "error"}
    pos = list(zip(t.incident_uid, t.condition)).index((d.at[j, "incident_uid"], d.at[j, "condition"]))
    acts, flagged = gate.jev_policy(t, d, "J-full")
    assert acts.iloc[pos] == "abstain" and flagged.iloc[pos]


class _Flaky(jev.JevClient):
    """Mock Jev whose first `fail` calls error out (as after exhausted retries)."""

    def __init__(self, fail, **kw):
        super().__init__(backend="mock", **kw)
        self.fail = fail

    def _mock(self, state, questions):
        if self.fail > 0:
            self.fail -= 1
            return {"_error": "gave up after 6 tries (HTTP 529)"}
        return super()._mock(state, questions)


def test_resume_retries_failed(canonical_synth, tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    cfg = _cfg(canonical_synth["dh"], tmp_path, conditions=["full", "no_trace"])
    cfg["jev"]["variants"] = ["J-full"]
    run_grid.prepare(cfg)
    run_grid.run(cfg)
    first = decide.run(cfg, _Flaky(4, cache=tmp_path / "j.sqlite"))
    assert first["failed"] >= 1
    retry = read_jsonl(tmp_path / "jev_retry.jsonl")
    assert len(retry) == first["failed"] and all("error" in r["status"].values() for r in retry)
    second = decide.run(cfg, _Flaky(0, cache=tmp_path / "j.sqlite"))
    assert second["rows"] == first["failed"] and second["failed"] == 0
    assert second["skipped_done"] == first["rows"] - first["failed"]
    assert read_jsonl(tmp_path / "jev_retry.jsonl") == []
    dec = decide.load_decisions(tmp_path / "decisions.jsonl")
    assert dec["done"].all() and len(dec) == first["rows"]
