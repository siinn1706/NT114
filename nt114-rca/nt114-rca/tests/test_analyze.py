"""Analysis entry point: exploratory prefix, headline guard, censored ranks, DEV-fit transfer, visibility join."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from rca import analyze


def _grid(tmp_path, n=24, backend="vllm", roles=("test",), **over):
    rng = np.random.default_rng(0)
    rows = []
    for role in roles:
        for i in range(n):
            uid = f"rcaeval.{role}{i:04d}"
            for cond in ("full", "blind_root"):
                rank = int(rng.choice([1, 1, 2, 4, 7]))
                rows.append({"key": f"m|{uid}|{cond}", "model": "m", "model_role": "primary", "model_revision": "r1",
                             "server_fp": "fp", "prompt_version": "v1", "backend": backend, "incident_uid": uid,
                             "case_id": uid, "dataset": "rcaeval", "label_granularity": "service", "split_role": role,
                             "set_scored": False, "system": "s", "fault": "cpu", "condition": cond, "retrieval": "none",
                             "store_mode": "-", "oracle_store": False, "evidence_fp": "e1", "rank": rank,
                             "correct": rank == 1, "parse_failed": False, "conf_consensus": rng.integers(0, 11) / 10,
                             "conf_verbal": rng.random(), "conf_verbal_sd": rng.random() / 5, "abstain_vote": 0.0, **over})
    p = tmp_path / "grid.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return p


def _cfg(tmp_path, grid, **over):
    return {"grids": [str(grid)], "out_dir": str(tmp_path / "out"), "n_boot": 50, "n_perm": 50,
            "contrasts": [{"name": "drop", "a": {"condition": "full"}, "b": {"condition": "blind_root"}, "metric": "ac1",
                           "require_changed": True}], **over}


def test_without_preregistration_every_table_is_exploratory(tmp_path):
    res = analyze.run(_cfg(tmp_path, _grid(tmp_path, backend="mock")))
    files = sorted(p.name for p in (tmp_path / "out").iterdir())
    assert files and all(f.startswith("exploratory_") for f in files)
    for name in ("table_cells", "table_confidence", "table_selective", "table_contrasts", "table_shift"):
        assert f"exploratory_{name}.csv" in files
    assert not res["meta"]["headline"]


def test_tables_report_censored_ranks_only(tmp_path):
    cells = analyze.run(_cfg(tmp_path, _grid(tmp_path)))["tables"]["table_cells"]
    for j in range(1, 6):
        assert {f"AC@{j}", f"AC@{j}_lo", f"AC@{j}_hi"} <= set(cells)
    assert {"MRR@5", "MRR@5_lo", "Brier_consensus_lo", "AUROC_consensus_lo", "AURC_consensus_lo", "ECE_support_consensus_lo"} <= set(cells)
    assert not [c for c in cells if "mean_rank" in c.lower() or c.startswith("Avg") or c == "MRR"]


@pytest.mark.parametrize("over, msg", [({"backend": "mock"}, "mock"), ({"oracle_store": True}, "oracle_store")])
def test_headline_guard_refuses(tmp_path, over, msg):
    with pytest.raises(analyze.HeadlineGuardError, match=msg):
        analyze.run(_cfg(tmp_path, _grid(tmp_path, **over), preregistration_sha="0" * 64))


def test_headline_guard_refuses_mixed_revisions_and_evidence(tmp_path):
    g = analyze.load(_grid(tmp_path))
    g.loc[0, "model_revision"] = "r2"
    with pytest.raises(analyze.HeadlineGuardError, match="model_revision"):
        analyze.guard_headline(g)
    g = analyze.load(_grid(tmp_path))
    g.loc[g.condition == "blind_root", "evidence_fp"] = "e2"
    with pytest.raises(analyze.HeadlineGuardError, match="evidence fingerprints"):
        analyze.guard_headline(g)


def test_headline_run_keeps_unvalidated_scores_out(tmp_path):
    res = analyze.run(_cfg(tmp_path, _grid(tmp_path), preregistration_sha="0" * 64))
    assert res["meta"]["headline"] and "token_prob" not in set(res["tables"]["table_confidence"]["score"])
    assert (tmp_path / "out" / "table_cells.csv").is_file()
    assert (tmp_path / "out" / "exploratory_table_confidence_unvalidated.csv").is_file()


def test_dev_rows_fit_thresholds_and_never_enter_tables(tmp_path):
    res = analyze.run(_cfg(tmp_path, _grid(tmp_path, roles=("val", "test")), selective={"coverage": [0.7], "risk": [0.3]}))
    t = res["tables"]
    assert set(t["table_cells"]["split_role"]) == {"test"}
    fit = t["table_selective"][t["table_selective"]["kind"] == "dev_fit"]
    assert len(fit) and {"tau", "coverage", "coverage_lo", "risk", "n_dev_records"} <= set(fit)
    assert set(t["table_shift"]["split_role"]) == {"val", "test"}


def test_visibility_join_and_require_changed(tmp_path):
    grid = _grid(tmp_path)
    g = analyze.load(grid)
    vis = tmp_path / "vis.jsonl"
    uids = sorted(g.incident_uid.unique())
    vis.write_text("\n".join(json.dumps({"incident_uid": u, "condition": c, "named": True,
                                         "same_as_full": c == "blind_root" and i < 4})
                             for i, u in enumerate(uids) for c in ("full", "blind_root")) + "\n", encoding="utf-8")
    res = analyze.run(_cfg(tmp_path, grid, visibility=[str(vis)]))
    con = res["tables"]["table_contrasts"]
    assert con.loc[con["filter"] == "none", "n_incidents"].item() == len(uids)
    assert con.loc[con["filter"] == "require_changed", "n_incidents"].item() == len(uids) - 4
    assert "table_cells_by_named" in res["tables"] and res["meta"]["counts"]["visibility_joined"] == 2 * len(uids)


def test_cli_reports_guard_errors(tmp_path, capsys):
    import yaml
    cfg = tmp_path / "a.yaml"
    cfg.write_text(yaml.safe_dump(_cfg(tmp_path, _grid(tmp_path, backend="mock"), preregistration_sha="x")), encoding="utf-8")
    assert analyze.main([str(cfg)]) == 2 and "HeadlineGuardError" in capsys.readouterr().out
    assert analyze.main([str(_grid(tmp_path))]) == 0


def test_precedent_root_strata_cover_retrieval_rows_only(tmp_path):
    g = analyze.load(_grid(tmp_path))
    hyb = g.assign(retrieval="hybrid", store_mode="precedent", key=g["key"] + "|hybrid",
                   hit_has_truth=[i % 3 == 0 for i in range(len(g))])
    grid = tmp_path / "grid_r.jsonl"
    grid.write_text("\n".join(json.dumps(r) for r in pd.concat([g.assign(hit_has_truth=False), hyb])
                              .to_dict("records")) + "\n", encoding="utf-8")
    res = analyze.run(_cfg(tmp_path, grid, contrasts=[]))
    t = res["tables"]["table_cells_by_precedent_root"]
    assert set(t["retrieval"]) == {"hybrid"} and set(t["precedent_has_root"]) == {True, False}
    for (cond, has), sub in hyb.groupby(["condition", "hit_has_truth"]):
        row = t[(t["condition"] == cond) & (t["precedent_has_root"] == has)].iloc[0]
        assert row["n_records"] == len(sub) == row["n_injections"]
        assert row["AC@1"] == pytest.approx((sub["rank"] == 1).mean())
    assert res["meta"]["tables"]["table_cells_by_precedent_root"] == "exploratory_table_cells_by_precedent_root.csv"
    assert "table_cells_by_precedent_root" not in analyze.run(_cfg(tmp_path / "n", _grid(tmp_path)))["tables"]


def test_precedent_root_flag_is_read_by_the_analysis_only():
    """The flag is written by the grid runner after the model call and read by the analysis tables; no
    confidence score, selective threshold, retrieval or prompt code ever sees it."""
    from pathlib import Path
    src = Path(analyze.__file__).parent
    users = sorted(p.name for p in src.rglob("*.py") if "hit_has_truth" in p.read_text(encoding="utf-8"))
    assert users == ["analyze.py", "run_grid.py"]
    run_grid = (src / "run_grid.py").read_text(encoding="utf-8")
    assert run_grid.count("hit_has_truth") == 1 and run_grid.index("hit_has_truth") > run_grid.index("llm.ask(")


def test_small_candidate_misses_count_for_no_ac_at_k(tmp_path):
    from rca import score
    from rca.data import Truth
    rows = []
    for i in range(6):
        uid = f"rcaeval.t{i:04d}"
        sc = score.correctness([] if i % 2 else ["frontend"], Truth("cart", "cpu"), 3)
        rows.append({"model": "m", "incident_uid": uid, "case_id": uid, "dataset": "rcaeval", "split_role": "test",
                     "condition": "full", "retrieval": "none", "store_mode": "-", "rank": sc["rank"],
                     "correct": sc["correct_at_1"], "parse_failed": sc["parse_failed"], "conf_consensus": 0.5,
                     "conf_verbal": 0.5})
    cells = analyze.cell_table(analyze.attach_units(pd.DataFrame(rows)), n_boot=20)
    for j in range(1, 6):
        assert cells[f"AC@{j}"].item() == 0.0
    assert cells["MRR@5"].item() == 0.0


# ---------------------------------------------------------------- calibration source -> target, CIs everywhere
def _write(tmp_path, df, name="g2.jsonl"):
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(r) for r in df.to_dict("records")) + "\n", encoding="utf-8")
    return p


def _two_datasets(tmp_path):
    g = analyze.load(_grid(tmp_path, n=30, roles=("val", "test")))
    odd = g["incident_uid"].str[-1].astype(int) % 2 == 1
    g.loc[odd, "dataset"] = "nezha"
    g.loc[odd, "conf_consensus"] = (g.loc[odd, "conf_consensus"] / 2).round(2)     # another score scale
    return g


def test_dev_fit_never_pools_datasets(tmp_path):
    from rca import selective
    g = _two_datasets(tmp_path)
    res = analyze.run(_cfg(tmp_path, _write(tmp_path, g), contrasts=[], selective={"coverage": [0.7]}))
    sel = res["tables"]["table_selective"]
    fit = sel[(sel.kind == "dev_fit") & (sel.score == "consensus") & (sel.condition == "full")]
    taus = {}
    for ds in ("rcaeval", "nezha"):
        d = g[(g.dataset == ds) & (g.split_role == "val") & (g.condition == "full")]
        want = selective.fit_threshold(d["correct"].to_numpy(bool), d["conf_consensus"].to_numpy(float), coverage=0.7)
        row = fit[fit.dataset == ds].iloc[0]
        assert row["tau"] == pytest.approx(want) and row["source_split_role"] == "val"
        assert json.loads(row["source_stratum"])["dataset"] == ds and row["n_dev_injections"] == len(d)
        taus[ds] = want
    assert taus["rcaeval"] != taus["nezha"]


def test_dev_fit_without_a_source_stratum_is_reported_not_pooled(tmp_path):
    g = analyze.load(_grid(tmp_path, roles=("val", "test")))
    g.loc[g.split_role == "test", "label_granularity"] = "pod"
    res = analyze.run(_cfg(tmp_path, _write(tmp_path, g), contrasts=[], selective={"coverage": [0.7]}))
    fit = res["tables"]["table_selective"].query("kind == 'dev_fit'")
    assert len(fit) and fit["no_source"].all() and fit["tau"].isna().all()


def test_declared_pool_is_one_source_and_one_target(tmp_path):
    from rca import selective
    g = analyze.load(_grid(tmp_path, roles=("val", "test")))
    pools = {"pooled": {"condition": ["full", "blind_root"]}}
    res = analyze.run(_cfg(tmp_path, _write(tmp_path, g), contrasts=[], selective={"coverage": [0.7], "pools": pools}))
    sel = res["tables"]["table_selective"]
    fit = sel[(sel.kind == "dev_fit") & (sel.score == "consensus") & (sel.condition == "pool:pooled")]
    d = g[g.split_role == "val"]
    w = 1.0 / d.groupby("incident_uid")["incident_uid"].transform("size")
    want = selective.fit_threshold(d["correct"].to_numpy(bool), d["conf_consensus"].to_numpy(float), w.to_numpy(), coverage=0.7)
    assert len(fit) == 1 and fit["tau"].item() == pytest.approx(want)
    curve = sel[(sel.kind == "curve") & (sel.condition == "pool:pooled") & (sel.score == "consensus")]
    assert curve["n_scored"].item() == (g.split_role == "test").sum()
    shift = res["tables"]["table_shift"]
    pooled = shift[shift.condition == "pool:pooled"]
    assert set(pooled["split_role"]) == {"val", "test"} and pooled["n_records"].sum() == len(g)


def test_pooled_cell_weighs_each_injection_once():
    """An incident appears once per pooled condition; each injection still has total weight 1."""
    df = pd.DataFrame({"dataset": "d", "split_role": "test", "model": "m", "retrieval": "none",
                       "condition": ["a", "b", "c", "a"], "incident_uid": ["i1", "i1", "i1", "i2"],
                       "injection_id": ["j1", "j1", "j1", "j2"], "weight": 1.0})
    p = analyze._pooled(df, {"pool": {"condition": ["a", "b", "c"]}})
    assert set(p["condition"]) == {"pool:pool"}
    assert p.groupby("injection_id")["weight"].sum().tolist() == pytest.approx([1.0, 1.0])


def test_every_reported_metric_has_a_ci(tmp_path):
    res = analyze.run(_cfg(tmp_path, _grid(tmp_path, roles=("val", "test")), contrasts=[],
                           selective={"coverage": [0.7], "risk": [0.3]}))
    counts = {"n_records", "n_scored", "n_dev", "n_dev_records", "n_dev_injections", "n_injections", "goal_value",
              "tau", "validated", "draws", "AUROC", "AUROC_lo", "AUROC_hi", "oracle_risk", "oracle_coverage",
              "parse_failed"}
    for name in ("table_confidence", "table_selective", "table_cells"):
        t = res["tables"][name]
        num = [c for c in t.select_dtypes("number").columns
               if not c.endswith(("_lo", "_hi", "_nan_draws")) and c not in counts]
        missing = [c for c in num if t[c].notna().any() and not {f"{c}_lo", f"{c}_hi"} <= set(t)]
        assert not missing, (name, missing)
    assert "selective_ties" in res["meta"]
