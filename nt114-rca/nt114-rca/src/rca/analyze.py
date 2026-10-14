"""Tổng hợp kết quả lưới thành các bảng cho 3 câu hỏi nghiên cứu.

  python -m rca.analyze results/grid.jsonl                         # bảng câu hỏi 1-2
  python -m rca.analyze results/grid.jsonl --gate MODEL_SMALL [MODEL_BIG]   # câu hỏi 3
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from . import gate
from .metrics import (ac_at_k, aurc, avg_at_k, confident_wrong_rate, ece, holm, mcnemar,
                      selective_accuracy)


def load(path) -> pd.DataFrame:
    return pd.DataFrame([json.loads(l) for l in open(path) if l.strip()])


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


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("grid")
    ap.add_argument("--gate", nargs="+", help="mô hình cơ sở [mô hình lớn]")
    ap.add_argument("--wrong-penalty", type=float, default=2.0)
    a = ap.parse_args()
    df = load(a.grid)
    outdir = Path(a.grid).parent
    pd.set_option("display.width", 200, "display.max_columns", 30)

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
