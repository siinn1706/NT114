"""Cost ledger and reproducibility: prepare log, retrieval timing, manifest v2, cost table, reproduce."""
from __future__ import annotations

import json
import socket
from pathlib import Path

import pandas as pd
import pytest

from conftest import canonical_run_cfg
from rca import analyze, cost, llm, reproduce, run_grid
from rca.store import read_jsonl


def _no_network(*a, **k):
    raise OSError("network disabled in this test")


@pytest.fixture(scope="module")
def chain(canonical_synth, tmp_path_factory):
    """prepare -> run -> analyze on the synthetic bundle with the mock LLM, sockets disabled throughout."""
    mp = pytest.MonkeyPatch()
    mp.setenv("HF_HUB_OFFLINE", "1")
    mp.setattr(socket, "socket", _no_network)
    mp.setattr(socket, "create_connection", _no_network)
    out = tmp_path_factory.mktemp("repro")
    cfg = canonical_run_cfg(canonical_synth["dh"], out, retrieval=["none", "hybrid"])
    run_grid.prepare(cfg)
    run_grid.run(cfg)
    acfg = {"grids": [cfg["out"]], "out_dir": str(out / "analysis"), "n_boot": 50, "n_perm": 50, "seed": 3,
            "contrasts": [{"name": "drop", "a": {"condition": "full"}, "b": {"condition": "blind_root"}, "metric": "ac1",
                           "within": {"model": "mock-small", "retrieval": "none"}}]}
    res = analyze.run(acfg)
    yield {"cfg": cfg, "out": out, "res": res, "mp": mp}
    mp.undo()


def test_prepare_log_has_one_row_per_incident_and_condition(chain):
    cfg = chain["cfg"]
    log = read_jsonl(run_grid.prepare_log_path(cfg))
    cn = run_grid.Canon(cfg)
    query = [r for r in log if r["kind"] == "query"]
    expected = {(vc.case_id, c) for vc, _ in cn.selected() for c in cn.conditions(vc.case_id)}
    assert len(query) == len(expected) and {(r["incident_uid"], r["condition"]) for r in query} == expected
    assert {r["incident_uid"] for r in log if r["kind"] == "store"} == {p.stem for p in (Path(cfg["evidence_dir"]) / "store").glob("*.json")}
    for r in log:
        assert r["wall_s"] >= r["load_s"] >= 0 and r["evidence_chars"] > 0 and isinstance(r["truncated"], bool)
        assert set(r["telemetry_rows"]) == {"metrics", "logs", "traces"}
        assert r["evidence_fp"] == cn.evidence_fp(r["incident_uid"])


def test_prepare_log_never_changes_the_evidence(chain):
    cn = run_grid.Canon(chain["cfg"])
    vc, _ = cn.selected()[0]
    conds = cn.conditions(vc.case_id)
    rows = []
    with_log = run_grid._canonical_evidence(cn, vc, conds, rows)
    assert rows and with_log == run_grid._canonical_evidence(cn, vc, conds)
    on_disk = json.loads((Path(chain["cfg"]["evidence_dir"]) / f"{vc.case_id}.json").read_text(encoding="utf-8"))
    assert on_disk == json.loads(json.dumps(with_log))


def test_grid_rows_time_retrieval(chain):
    rows = read_jsonl(Path(chain["cfg"]["out"]))
    assert all(r["retrieval_s"] == 0.0 for r in rows if r["retrieval"] == "none")
    assert all(r["retrieval_s"] > 0 for r in rows if r["retrieval"] != "none")


def test_manifest_v3(chain):
    out = Path(chain["cfg"]["out"]).parent
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert {"manifest_version", "python", "platform", "packages", "evidence_builder_version", "legacy_view_version",
            "config_sha256", "config_copy", "split_sha256", "prepare_log_sha256"} <= set(man)
    assert man["manifest_version"] == 3 and man["packages"]["numpy"] and man["split_sha256"]
    assert man["store"]["split_id"] == man["split_id"] and man["store"]["ignored_files"] == 0
    assert all(m["exec_sig"] and m["execution"]["n"] == chain["cfg"]["n_samples"] for m in man["models"])
    assert man["prepare_log_sha256"] == run_grid._sha256(run_grid.prepare_log_path(chain["cfg"]))
    import hashlib
    assert man["config_sha256"] == hashlib.sha256((out / "config.yaml").read_bytes()).hexdigest()
    llm.check_no_secrets(man)
    for k, v in man.items():
        assert k.lower() not in llm.SECRET_KEYS and not (isinstance(v, str) and v.lower().startswith("bearer "))


def test_config_copy_refuses_credentials(tmp_path):
    with pytest.raises(ValueError, match="credential"):
        run_grid.write_config_copy({"out": str(tmp_path / "grid.jsonl"), "models": [{"name": "m", "api_key": "x"}]})


def test_cost_table_cells_and_paths(chain):
    t = chain["res"]["tables"]["table_cost"]
    cells, paths = t[t.kind == "cell"], t[t.kind == "path"]
    assert len(cells) and t["gpu_s"].isna().all()
    assert (cells.loc[cells.retrieval == "none", "prepare_logged"] == 1.0).all()
    assert {"answer", "answer+retrieve"} <= set(paths["path"])
    for (ds, m, cond), g in paths.groupby(["dataset", "model", "condition"]):
        a, ar = g[g.path == "answer"].iloc[0], g[g.path == "answer+retrieve"]
        if len(ar):
            assert ar["total_tokens"].iloc[0] > a["total_tokens"]


def test_cost_counts_preparation_once_per_path(tmp_path):
    rows = [{"dataset": "d", "model": "m", "condition": "full", "retrieval": r, "store_mode": s, "incident_uid": "u",
             "prompt_tokens": 100, "completion_tokens": 10, "latency_s": 2.0, "retrieval_s": rs, "cached": False,
             "sampling": {"n": 5}} for r, s, rs in (("none", "-", 0.0), ("hybrid", "precedent", 0.5))]
    log = tmp_path / "prepare_log.jsonl"
    log.write_text(json.dumps({"incident_uid": "u", "condition": "full", "kind": "query", "wall_s": 3.0, "ts": 1}) + "\n",
                   encoding="utf-8")
    t = cost.table_cost(pd.DataFrame(rows), [log])
    p = t[t.path == "answer+retrieve"].iloc[0]
    assert p["total_tokens"] == 220 and p["e2e_s"] == pytest.approx(3.0 + 0.5 + 4.0)
    c = t[(t.kind == "cell") & (t.retrieval == "none")].iloc[0]
    assert c["tokens_per_sample"] == pytest.approx(22.0) and c["e2e_s"] == pytest.approx(5.0)


def test_reproduce_matches_then_names_the_changed_table(chain, capsys):
    adir = chain["out"] / "analysis"
    assert "table_cells_by_precedent_root" in chain["res"]["meta"]["tables"]       # retrieval rows present
    assert reproduce.main([str(adir)]) == 0
    grid = Path(chain["cfg"]["out"])
    lines = grid.read_text(encoding="utf-8").splitlines()
    r = json.loads(lines[0])
    r["rank"], r["correct"] = (2, False) if r["rank"] == 1 else (1, True)
    grid.write_text("\n".join([json.dumps(r)] + lines[1:]) + "\n", encoding="utf-8")
    capsys.readouterr()
    assert reproduce.main([str(adir)]) == 1
    msg = capsys.readouterr().out
    assert "table_cells" in msg and "input changed" in msg
    assert reproduce.main([str(chain["out"])]) == 2


def _small_analysis(tmp_path) -> Path:
    from test_analyze import _cfg, _grid
    analyze.run(_cfg(tmp_path, _grid(tmp_path), contrasts=[]))
    return tmp_path / "out"


def test_reproduce_flags_a_modified_published_table(tmp_path, capsys):
    adir = _small_analysis(tmp_path)
    assert reproduce.main([str(adir)]) == 0
    with open(adir / "exploratory_table_cells.csv", "a", encoding="utf-8") as f:
        f.write("\n")
    out = reproduce.reproduce(adir)
    assert out["tables"]["table_cells"] == "published_modified"
    assert {s for n, s in out["tables"].items() if n != "table_cells"} == {"match"}
    capsys.readouterr()
    assert reproduce.main([str(adir)]) == 1 and "table_cells (published_modified)" in capsys.readouterr().out


def test_reproduce_flags_a_deleted_published_table(tmp_path):
    adir = _small_analysis(tmp_path)
    (adir / "exploratory_table_shift.csv").unlink()
    assert reproduce.reproduce(adir)["tables"]["table_shift"] == "published_missing"
    assert reproduce.main([str(adir)]) == 1
