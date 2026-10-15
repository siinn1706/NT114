"""Tổng hợp kết quả lưới thành các bảng cho các câu hỏi nghiên cứu.

  python -m rca.analyze results/grid.jsonl                         # bảng câu hỏi 1-2
  python -m rca.analyze results/grid.jsonl --gate MODEL_SMALL [MODEL_BIG]   # lớp quyết định cũ
  python -m rca.analyze results/grid.jsonl --decisions results/decisions.jsonl [--data-home D] [--smoke]

Bảng chính (headline) từ chối: dòng mock, dòng DEV (split_role val) và dòng trộn phiên bản prompt /
câu hỏi Jev. `--smoke` cho phép chúng nhưng ghi rõ bảng là smoke. Trọng số và cụm = eval-units
(một lần tiêm lỗi là một đơn vị); không có báo cáo eval-units thì mỗi bản ghi là một đơn vị.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import gate, score
from .metrics import (ac_at_k, ac_at_k_w, aurc, aurc_w, avg_at_k, brier, cluster_bootstrap, confident_wrong_rate,
                      ece, ece_w, error_detection, holm, mcnemar, overconfidence_gap, selective_accuracy)


def load(path) -> pd.DataFrame:
    with open(path, encoding="utf-8") as f:
        return pd.DataFrame([json.loads(l) for l in f if l.strip()])


class HeadlineGuardError(ValueError):
    pass


def guard_headline(grid: pd.DataFrame, decisions: pd.DataFrame | None = None) -> None:
    """Headline tables never contain mock rows, DEV rows or mixed prompt / Jev question versions."""
    problems = []
    if "backend" in grid and (grid["backend"] == "mock").any():
        problems.append("mock LLM rows")
    if "split_role" in grid and (grid["split_role"] == "val").any():
        problems.append("DEV (split_role=val) rows")
    if "prompt_version" in grid and grid["prompt_version"].nunique() > 1:
        problems.append(f"mixed prompt_version {sorted(grid['prompt_version'].unique())}")
    if decisions is not None and len(decisions):
        if (decisions["jev_backend"] == "mock").any():
            problems.append("mock Jev rows")
        if decisions["jev_question_version"].nunique() > 1:
            problems.append(f"mixed jev_question_version {sorted(decisions['jev_question_version'].unique())}")
        if "split_role" in decisions and (decisions["split_role"] == "val").any():
            problems.append("DEV decision rows")
    if problems:
        raise HeadlineGuardError("refusing headline tables: " + "; ".join(problems) + " (use --smoke for a smoke report)")


def attach_units(df: pd.DataFrame, data_home: Path | None = None, uid_col: str = "incident_uid") -> pd.DataFrame:
    """Join weight / injection_id / coverage causes; one unit per record when no eval-units report exists."""
    uid = df[uid_col].fillna(df["case_id"]) if "case_id" in df else df[uid_col]
    df = df.assign(incident_uid=uid)
    frames = []
    for ds in sorted(df["dataset"].dropna().unique()) if "dataset" in df else []:
        path = Path(data_home) / "reports" / f"eval-units-{ds}.json" if data_home else None
        if path is not None and path.is_file():
            frames.append(score.units(data_home, ds))
    known = pd.concat(frames) if frames else pd.DataFrame(columns=score.UNIT_COLUMNS)
    rest = score.default_units(set(df["incident_uid"]) - set(known["incident_uid"]))
    units = pd.concat([known, rest], ignore_index=True)
    out = df.drop(columns=[c for c in score.UNIT_COLUMNS if c != "incident_uid" and c in df]).merge(
        units, on="incident_uid", how="left")
    return reweight(out)


def reweight(df: pd.DataFrame) -> pd.DataFrame:
    """Equal weight per injection within each evaluated cell: weight = 1 / (records of that injection in
    the cell). The eval-units weights count every record of the dataset, so in a cell holding only part
    of an injection (a condition not applicable to every task, a `limit_per_system` sample) that
    injection would otherwise count less than one. On the full sets the weights are unchanged."""
    keys = [c for c in strata_cols(df) if c != "label_granularity"] + ["injection_id"]
    n = df.groupby(keys, dropna=False)["incident_uid"].transform("nunique")
    return df.assign(weight=1.0 / n)


def strata_cols(df: pd.DataFrame, extra=()) -> list[str]:
    return [c for c in ("dataset", "label_granularity", *extra, "model", "condition", "retrieval", "store_mode") if c in df]


def weighted_cell_table(df: pd.DataFrame, n_boot: int = 2000, extra=()) -> pd.DataFrame:
    """Per dataset x granularity [x extra strata, e.g. coverage cause] x model x condition x retrieval:
    weighted accuracy (CI over injections), calibration, error detection and selective metrics."""
    rows = []
    cols = strata_cols(df, extra)
    for k, g in df.groupby(cols, dropna=False):
        c, w = g["correct"].astype(bool).values, g["weight"].values
        ci = cluster_bootstrap(c, g["injection_id"].values, w, n=n_boot)
        rec = dict(zip(cols, k if isinstance(k, tuple) else (k,)))
        rec.update({"n_records": len(g), "n_injections": g["injection_id"].nunique(),
                    "AC@1": ac_at_k_w(g["rank"], 1, w), "AC@1_lo": ci["lo"], "AC@1_hi": ci["hi"],
                    "AC@3": ac_at_k_w(g["rank"], 3, w),
                    "parse_failed": float(np.average(g["parse_failed"].astype(float), weights=w)) if "parse_failed" in g else 0.0})
        for name in ("consensus", "verbal"):
            conf = g[f"conf_{name}"].astype(float).values
            ed = error_detection(c, conf, w)
            rec.update({f"Brier_{name}": brier(c, conf, w), f"gap_{name}": overconfidence_gap(c, conf, w),
                        f"ECE_{name}": ece_w(c, conf, w, "support" if name == "consensus" else "width"),
                        f"AUROC_{name}": ed["AUROC"], f"AUPRC_{name}": ed["AUPRC"],
                        f"CW100_{name}": float(100 * np.average(~c & (conf >= 0.8), weights=w))})
        rec["AURC_consensus"] = aurc_w(c, g["conf_consensus"].astype(float).values, w)
        rows.append(rec)
    return pd.DataFrame(rows)


def policy_table(t: pd.DataFrame, decisions: pd.DataFrame, variants=("J-full", "J-AA"), draws: int = 1000,
                 **rw) -> pd.DataFrame:
    """Per dataset x condition: L0, L1, L2, Jev variants, C1/C2 at J-AA's coverage, R1/R2 at J-full's routes, O."""
    out = []
    for (ds, cond), g in t.groupby(["dataset", "condition"]):
        g = g.reset_index(drop=True)
        w = g["weight"].values
        pols = {"L0 always answer": gate.fixed(g, "answer"),
                "L1 self-abstain": pd.Series(np.where(g["abstain_vote"] >= 0.5, "abstain", "answer"), index=g.index)}
        if "escalate_ok" in g:
            pols["L2 always escalate"] = gate.fixed(g, "escalate")
        jev = {}
        for v in variants:
            if v in set(decisions["variant"]):
                jev[v], flagged = gate.jev_policy(g, decisions, v)
                pols[v] = jev[v]
        res = [{"policy": n, **gate.evaluate(g, c, w, **rw)} for n, c in pols.items()]
        ref_cov = next((r["coverage"] for r in res if r["policy"] == "J-AA"), None)
        if ref_cov is not None:
            res.append({"policy": "C1 coverage-matched consensus", **gate.evaluate_draws(g, gate.coverage_matched_threshold(g, ref_cov, draws=draws), w, **rw)})
            res.append({"policy": "C2 coverage-matched random", **gate.evaluate_draws(g, gate.coverage_matched_random(g, ref_cov, draws=draws), w, **rw)})
        if "J-full" in jev:
            res.append({"policy": "R1 route-matched random", **gate.evaluate_draws(g, gate.route_matched_random(g, jev["J-full"], draws=draws), w, **rw)})
            res.append({"policy": "R2 route-matched consensus", **gate.evaluate_draws(g, gate.route_matched_consensus(g, jev["J-full"], draws=draws), w, **rw)})
        res.append({"policy": "O oracle", **gate.evaluate(g, gate.oracle_policy(g), w, **rw)})
        for r in res:
            r.update(dataset=ds, condition=cond, n_records=len(g), n_injections=g["injection_id"].nunique())
            r.pop("actions", None)
        out += res
    return pd.DataFrame(out)


def jev_score_table(t: pd.DataFrame, decisions: pd.DataFrame, variant: str = "J-full") -> pd.DataFrame:
    """Error detection of Jev's stage-1 P(accept) and `supported`, next to the LLM's consensus."""
    rows = []
    for (ds, cond), g in t.groupby(["dataset", "condition"]):
        g = g.reset_index(drop=True)
        sc = gate.jev_scores(g, decisions, variant)
        c, w = g["answer_ok"].values, g["weight"].values
        for name, s in (("consensus", g["answer_conf"]), ("jev_p_accept", sc["p_accept"]), ("jev_supported", sc["supported"])):
            ok = ~np.isnan(s.values)
            ed = error_detection(c[ok], s.values[ok], w[ok]) if ok.any() else {"AUROC": np.nan, "AUPRC": np.nan}
            rows.append({"dataset": ds, "condition": cond, "score": name, "n": int(ok.sum()), **ed})
    return pd.DataFrame(rows)


def cell_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for k, g in df.groupby(["model", "condition", "retrieval", "store_mode"]):
        c = g["correct"].astype(bool).values
        rows.append({
            "model": k[0], "condition": k[1], "retrieval": k[2], "store_mode": k[3], "n": len(g),
            "AC@1": ac_at_k(g["rank"], 1), "AC@3": ac_at_k(g["rank"], 3), "Avg@5": avg_at_k(g["rank"]),
            "mean_rank": g["rank"].mean(),                                   # số dịch vụ phải kiểm tra
            "conf_wrong_consensus": confident_wrong_rate(c, g["conf_consensus"]),
            "conf_wrong_verbal": confident_wrong_rate(c, g["conf_verbal"]),
            "ECE_consensus": ece(c, g["conf_consensus"]), "ECE_verbal": ece(c, g["conf_verbal"]),
            "AURC": aurc(c, g["conf_consensus"]), "SelAcc@80": selective_accuracy(c, g["conf_consensus"], 0.8),
            "abstain_vote": g["abstain_vote"].mean(), "parse_rate": g["parse_rate"].mean(),
            "hit_has_truth": g["hit_has_truth"].mean(),
        })
    return pd.DataFrame(rows)


def retrieval_tests(df: pd.DataFrame) -> pd.DataFrame:
    """McNemar: mỗi cấu hình truy hồi so với không truy hồi, cùng mô hình, cùng điều kiện, cùng tập ca."""
    out = []
    base = df[df.retrieval == "none"]
    for (m, cond, meth, mode), g in df[df.retrieval != "none"].groupby(["model", "condition", "retrieval", "store_mode"]):
        b = base[(base.model == m) & (base.condition == cond)].set_index("case_id")["correct"]
        x = g.set_index("case_id")["correct"]
        common = b.index.intersection(x.index)
        t = mcnemar(b[common].values, x[common].values)
        out.append({"model": m, "condition": cond, "retrieval": meth, "store_mode": mode, "n": len(common),
                    "delta_AC@1": x[common].mean() - b[common].mean(), **t})
    out = pd.DataFrame(out)
    if len(out):
        adj = holm({i: p for i, p in out["p"].items()})
        out["p_holm"] = out.index.map(adj)
    return out


def decision_report(grid: pd.DataFrame, decisions: pd.DataFrame, outdir: Path, data_home=None, smoke=False,
                    draws: int = 1000, n_boot: int = 2000, **rw) -> dict:
    """Weighted cell table, policy table and Jev score table; headline guards unless `smoke`."""
    from . import decide
    if not smoke:
        guard_headline(grid, decisions)
    prefix = "smoke_" if smoke else ""
    g = attach_units(grid, data_home)
    cells = weighted_cell_table(g, n_boot)
    cells_cov = weighted_cell_table(g, n_boot, ("cov_logs", "cov_traces"))
    t = attach_units(decide.action_table(grid, grid["prompt_version"].iloc[0]), data_home)
    pol = policy_table(t, decisions, draws=draws, **rw)
    js = jev_score_table(t, decisions)
    err_rate = float((~decisions["done"].astype(bool)).mean()) if len(decisions) else 0.0
    for name, tab in (("table_cells_weighted", cells), ("table_cells_by_coverage", cells_cov), ("table_policies", pol),
                      ("table_jev_scores", js)):
        tab.to_csv(outdir / f"{prefix}{name}.csv", index=False)
    return {"cells": cells, "cells_by_coverage": cells_cov, "policies": pol, "jev_scores": js, "jev_error_rate": err_rate}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("grid")
    ap.add_argument("--gate", nargs="+", help="mô hình cơ sở [mô hình lớn]")
    ap.add_argument("--decisions", help="decisions.jsonl của rca.decide")
    ap.add_argument("--data-home", help="thư mục dữ liệu chứa reports/eval-units-<dataset>.json")
    ap.add_argument("--smoke", action="store_true", help="cho phép dòng mock/DEV; bảng ghi tiền tố smoke_")
    ap.add_argument("--draws", type=int, default=1000)
    ap.add_argument("--wrong-penalty", type=float, default=2.0)
    a = ap.parse_args()
    df = load(a.grid)
    outdir = Path(a.grid).parent
    pd.set_option("display.width", 200, "display.max_columns", 30)
    if a.decisions:
        from .decide import load_decisions
        rep = decision_report(df, load_decisions(a.decisions), outdir, a.data_home, a.smoke, a.draws,
                              wrong_penalty=a.wrong_penalty)
        print(("== SMOKE REPORT (mock / DEV rows allowed; not a result)\n" if a.smoke else "") +
              f"Jev error rate: {rep['jev_error_rate']:.3%}")
        cols = ["dataset", "condition", "policy", "coverage", "selective_risk", "confident_wrong_per_100",
                "wrong_per_100", "abstain_per_100", "tokens_per_incident"]
        print(rep["policies"][cols].round(3).to_string(index=False))
        print(rep["jev_scores"].round(3).to_string(index=False))
        raise SystemExit(0)

    ct = cell_table(df)
    ct.to_csv(outdir / "table_cells.csv", index=False)
    print("\n== Câu hỏi 1: thiếu dữ liệu -> sai bao nhiêu, sai mà chắc bao nhiêu (không truy hồi)")
    print(ct[ct.retrieval == "none"][["model", "condition", "n", "AC@1", "mean_rank", "conf_wrong_consensus",
                                      "ECE_consensus", "ECE_verbal", "abstain_vote"]].round(3).to_string(index=False))

    rt = retrieval_tests(df)
    rt.to_csv(outdir / "table_retrieval_tests.csv", index=False)
    print("\n== Câu hỏi 2: truy hồi giúp hay hại (McNemar so với không truy hồi, hiệu chỉnh Holm)")
    if len(rt):
        print(rt.round(3).to_string(index=False))

    if a.gate:
        t = gate.action_table(df, a.gate[0], a.gate[1] if len(a.gate) > 1 else None)
        res = gate.leave_one_system_out(t, wrong_penalty=a.wrong_penalty)
        res.to_csv(outdir / "table_gate.csv", index=False)
        print(f"\n== Câu hỏi 3: lớp quyết định (phạt sai = {a.wrong_penalty}), trên 100 sự cố")
        cols = ["test_system", "policy", "coverage", "acc_answered", "wrong_per_100",
                "confident_wrong_per_100", "abstain_per_100", "tokens_per_incident", "reward"]
        print(res[cols].round(3).to_string(index=False))
