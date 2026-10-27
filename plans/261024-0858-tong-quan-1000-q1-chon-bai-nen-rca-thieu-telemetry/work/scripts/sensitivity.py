"""Phase 08: protocol §8 weight sensitivity.

usage: python -X utf8 -I sensitivity.py F_CSV TOP_K OUT_CSV [--xcheck XCHECK_CSV] [--focus ID]
--focus ID adds the rank of ID to every scenario; focus_tied = 1 when any other id has the same score as ID
(not necessarily the leader). Cell scenarios outside the rubric range are skipped, so a cell at its maximum
is moved by -1 only.
F_CSV: rows with openalex_id, F1..F6 and t2_gate (rows with t2_gate != 1 are ignored).
18 scenarios: w_i in {0.5, 1.5} for each i (12) and w_i = 0 for each i (6); all other weights 1.
With --xcheck, extra scenarios move one F cell by +1/-1 where the phase 07 cross-check reader differed
(bounded to the rubric range). A tie at rank 1 counts as not keeping rank 1.
Writes one row per scenario: winner, whether the baseline rank-1 keeps rank 1 alone, top-K ids and
ids that enter the top-K but are not in the baseline top-K. Prints the stability verdict (>= 15/18).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import read_csv, write_csv  # noqa: E402

FS = ["F1", "F2", "F3", "F4", "F5", "F6"]
MAX = {"F1": 5, "F2": 5, "F3": 10, "F4": 4, "F5": 3, "F6": 3}


def ranking(table, weights):
    score = {i: sum(weights[k] * table[i][k] for k in FS) for i in table}
    # same tie-break order as phase 07: F1, F3, F2, then id
    order = sorted(table, key=lambda i: (-score[i], -table[i]["F1"], -table[i]["F3"], -table[i]["F2"], i))
    return order, score


def main():
    args = sys.argv[1:]
    xcheck = focus = None
    if "--focus" in args:
        focus = args[args.index("--focus") + 1]
        args = args[:args.index("--focus")] + args[args.index("--focus") + 2:]
    if "--xcheck" in args:
        xcheck = args[args.index("--xcheck") + 1]
        args = args[:args.index("--xcheck")]
    f_csv, top_k, out = args[0], int(args[1]), args[2]
    table = {r["openalex_id"]: {k: int(r[k]) for k in FS} for r in read_csv(f_csv) if r["t2_gate"] == "1"}
    base_order, _ = ranking(table, dict.fromkeys(FS, 1.0))
    base_top, leader = base_order[:top_k], base_order[0]
    scenarios = [(f"w_{k}={w}", {**dict.fromkeys(FS, 1.0), k: w}, None) for k in FS for w in (0.5, 1.5)]
    scenarios += [(f"w_{k}=0", {**dict.fromkeys(FS, 1.0), k: 0.0}, None) for k in FS]
    if xcheck:
        for r in read_csv(xcheck):
            i = r["openalex_id"]
            if i not in table:
                continue
            for k in FS:
                if int(r[k]) != table[i][k]:
                    for d in (1, -1):
                        v = table[i][k] + d
                        if 0 <= v <= MAX[k]:
                            scenarios.append((f"{i}:{k}{d:+d}", dict.fromkeys(FS, 1.0), (i, k, v)))
    rows, kept = [], 0
    for name, weights, cell in scenarios:
        t = {i: dict(v) for i, v in table.items()}
        if cell:
            t[cell[0]][cell[1]] = cell[2]
        order, score = ranking(t, weights)
        tie = score[order[0]] == score[order[1]]
        keeps = order[0] == leader and not tie
        if not cell:
            kept += keeps
        rows.append({"scenario": name, "kind": "cell" if cell else "weight", "winner": order[0],
                     "winner_score": f"{score[order[0]]:g}", "runner_up": order[1],
                     "runner_up_score": f"{score[order[1]]:g}", "tie_at_1": int(tie),
                     "baseline_leader_keeps_1": int(keeps), "top_k": "|".join(order[:top_k]),
                     "entrants": "|".join(i for i in order[:top_k] if i not in base_top),
                     **({"focus_rank": order.index(focus) + 1,
                         "focus_tied": int(sum(score[j] == score[focus] for j in order) > 1)} if focus else {})})
    write_csv(out, rows, list(rows[0]))
    print(json.dumps({"pool": len(table), "baseline_leader": leader, "weight_scenarios": 18,
                      "leader_keeps": kept, "stable": kept >= 15,
                      **({"focus": focus, "focus_rank1_alone": sum(r["focus_rank"] == 1 and not r["focus_tied"]
                                                                   for r in rows if r["kind"] == "weight")} if focus else {}),
                      "entrants": sorted({e for r in rows for e in r["entrants"].split("|") if e})}))


if __name__ == "__main__":
    main()
