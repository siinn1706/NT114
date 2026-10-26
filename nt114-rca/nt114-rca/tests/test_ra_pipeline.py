"""R-a arm end to end with the mock LLM on synthetic data: one call per answer, l0 unchanged, arms never
share a cache entry, no record leaves the denominator, labels never reach R-a evidence or prompts."""
from __future__ import annotations

import json
import secrets
import shutil
from collections import Counter

import numpy as np
import pandas as pd
import pytest

from conftest import canonical_run_cfg
from rca import llm as llm_mod
from rca import rcl_path, run_grid, score
from rca.llm import LLM, build_messages
from rca.store import read_jsonl, write_jsonl_atomic

CONDS = ["full", "no_trace", "no_log", "no_metric", "blind_root", "blind_nonroot_ev"]
PERM_CONDITIONS = ["full", "no_metric", "no_log", "no_trace"]
VOLATILE = {"ts", "latency_s", "cached", "retrieval_s"}


def _home(canonical_synth, tmp_path):
    dh = tmp_path / "dh"
    for part in ("canonical", "reports", "splits"):
        shutil.copytree(canonical_synth["dh"] / part, dh / part)
    return dh


def _cfg(dh, out, **over):
    return canonical_run_cfg(dh, out, conditions=CONDS, retrieval=["none"],
                             models=[{"name": "mock-small", "backend": "mock"}], **over)


def _rows(cfg):
    return read_jsonl(cfg["out"])


@pytest.fixture(scope="module")
def grids(canonical_synth, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("ra")
    dh = _home(canonical_synth, tmp)
    calls = Counter()
    real = LLM.ask

    def counted(self, messages, candidates, scope=None):
        calls[scope or "l0"] += 1
        return real(self, messages, candidates, scope)

    LLM.ask = counted
    try:
        base, both = _cfg(dh, tmp / "base"), _cfg(dh, tmp / "both", arms=["l0", "ra"])
        run_grid.prepare(base)
        run_grid.run(base)
        calls.clear()
        run_grid.prepare(both)
        run_grid.run(both)
    finally:
        LLM.ask = real
    return {"base": _rows(base), "both": _rows(both), "calls": dict(calls), "cfg": both, "dh": dh}


def test_l0_rows_are_unchanged_by_adding_the_ra_arm(grids):
    strip = lambda rows: sorted(({k: v for k, v in r.items() if k not in VOLATILE | {"cfg"}} for r in rows),
                                key=lambda r: r["key"])
    l0 = [r for r in grids["both"] if "arm" not in r]
    assert l0 and strip(l0) == strip(grids["base"])


def test_one_llm_call_per_answer(grids):
    """Every answer row comes from exactly one `ask` (one call with n samples); no second call of any role."""
    ra = [r for r in grids["both"] if r.get("arm") == "ra"]
    assert ra and all(r["llm_calls"] == (r["outcome"] != "not_applicable") for r in ra)
    assert grids["calls"] == {"l0": sum("arm" not in r for r in grids["both"]), "ra": sum(r["llm_calls"] for r in ra)}
    assert len({r["key"] for r in grids["both"]}) == len(grids["both"])


def test_ra_rows_cover_the_same_cells_and_stay_in_the_denominator(grids):
    l0 = {(r["incident_uid"], r["condition"]) for r in grids["both"] if "arm" not in r}
    ra = [r for r in grids["both"] if r.get("arm") == "ra"]
    assert {(r["incident_uid"], r["condition"]) for r in ra} == l0
    assert all(r["retrieval"] == "none" and r["path"] in rcl_path.PATHS and r["frame_sha256"] is None for r in ra)
    assert all(r["path"] != "trace" for r in ra if r["condition"] == "no_trace")
    assert {r["path"] for r in ra} == {"trace", "frame_free"}           # sock-shop has no traces
    assert set(Counter(r["outcome"] for r in ra)) <= set(score.OUTCOMES)
    assert sum(Counter(r["outcome"] for r in ra).values()) == len(ra)


def test_arms_never_share_a_cache_entry():
    m = LLM("mock-small", backend="mock", n=1, cache=llm_mod.Cache(":memory:"))
    m.server_fingerprint()
    msgs = [{"role": "user", "content": "x"}]
    assert m.key(msgs, ["a"]) != m.key(msgs, ["a"], scope="ra") != m.key(msgs, ["a"], scope="ra_im1")


def test_arm_config_is_validated(tmp_path):
    with pytest.raises(ValueError):
        run_grid.cfg_arms({"arms": ["l0", "nope"]})
    with pytest.raises(ValueError):
        run_grid.cfg_arms({"arms": ["ra", "ra"]})
    assert run_grid.cfg_arms({}) == ["l0"]


def ra_artifacts(cfg) -> dict[str, str]:
    run_grid.prepare(cfg)
    out = {}
    for r in run_grid.load_arm_evidence(cfg, "ra"):
        vc = r["vc"]
        out[f"{vc.case_id}|candidates"] = json.dumps(r["candidates"])
        for cond, ev in r["conditions"].items():
            out[f"{vc.case_id}|{cond}|evidence"] = json.dumps(ev, sort_keys=True)
            out[f"{vc.case_id}|{cond}|prompt"] = json.dumps(build_messages(vc, r["candidates"], ev["text"]))
    return out


def test_ra_evidence_is_label_free(canonical_synth, tmp_path):
    dh = _home(canonical_synth, tmp_path)
    cfg = lambda name: canonical_run_cfg(dh, tmp_path / name, conditions=PERM_CONDITIONS, retrieval=["none"],
                                         arms=["l0", "ra"])
    base = ra_artifacts(cfg("a"))
    labels = dh / "canonical/v1/rcaeval/eval_only/labels.jsonl"
    labs = read_jsonl(labels)
    canary = f"CANARY_{secrets.token_hex(8)}"
    fields = [(l["root_cause"], l["fault"]) for l in labs]
    fields = fields[1:] + fields[:1]
    assert any(l["root_cause"]["primary_root_service"] != f[0]["primary_root_service"] for l, f in zip(labs, fields))
    for l, (rc, fa) in zip(labs, fields):
        l["root_cause"], l["fault"] = dict(rc, original=canary), dict(fa, type_raw=canary)
    write_jsonl_atomic(labels, labs)
    after = ra_artifacts(cfg("b"))
    assert after == base and not [k for k, v in after.items() if canary in v]


def test_analysis_keeps_arms_apart(grids, tmp_path):
    from rca import analyze, selective
    res = analyze.run({"grids": [grids["cfg"]["out"]], "out_dir": str(tmp_path / "an"), "data_home": str(grids["dh"]),
                       "n_boot": 50, "n_boot_contrasts": 50, "n_perm": 50})
    cells = res["tables"]["table_cells"]
    assert set(cells["arm"]) == {"l0", "ra"}
    assert not cells.duplicated(["model", "arm", "condition", "retrieval", "store_mode", "split_role", "set_scored",
                                 "label_granularity"]).any()
    cost = res["tables"]["table_cost"]
    ra_cost = cost[(cost["kind"] == "cell") & (cost["arm"] == "ra")]
    assert len(ra_cost) and (ra_cost["max_llm_calls_per_answer"] <= 1).all()
    assert set(cost.loc[cost["kind"] == "path", "arm"].dropna()) <= {"l0"}
    df = pd.DataFrame(grids["both"])
    l0 = selective.select_rows(df, "v1")["answer"]
    ra = selective.select_rows(df, "v1", arms={"answer": "none"}, evidence_arm="ra")["answer"]
    assert "arm" not in l0 or l0["arm"].isna().all()
    assert (ra["arm"] == "ra").all() and len(ra) == len(l0)


def test_dev_fit_thresholds_never_cross_arms():
    from rca import analyze
    rng = np.random.default_rng(0)
    rows = []
    for arm, shift in (("l0", 0.0), ("ra", 0.4)):
        for role in ("val", "test"):
            for i in range(40):
                s = float(np.clip(rng.uniform(0, 0.6) + shift, 0, 1))
                rows.append({"dataset": "d", "model": "m", "arm": arm, "condition": "full", "retrieval": "none",
                             "store_mode": "-", "split_role": role, "incident_uid": f"{arm}{role}{i}",
                             "injection_id": f"{arm}{role}{i}", "weight": 1.0, "correct": rng.random() < s,
                             "abstain_vote": 0.0, "score_x": s})
    df = pd.DataFrame(rows)
    tab = analyze.selective_table(df[df.split_role == "test"], ["x"], df[df.split_role == "val"],
                                  {"coverage": [0.5]}, n_boot=20)
    fit = tab[tab["kind"] == "dev_fit"].set_index("arm")
    assert json.loads(fit.at["ra", "source_stratum"])["arm"] == "ra" and fit.at["ra", "n_dev_records"] == 40
    assert fit.at["ra", "tau"] != fit.at["l0", "tau"]
    # the ra threshold equals one fitted on ra DEV rows alone
    alone = analyze.selective_table(df[(df.split_role == "test") & (df.arm == "ra")], ["x"],
                                    df[(df.split_role == "val") & (df.arm == "ra")], {"coverage": [0.5]}, n_boot=20)
    assert alone[alone["kind"] == "dev_fit"]["tau"].iloc[0] == fit.at["ra", "tau"]
