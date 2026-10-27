"""Phase 08: merge per-record T3 files and build the decision matrix (protocol §8).

usage: python -X utf8 -I merge-t3.py
Reads work/t3/<id>-{artifact,evidence,prior,gates,rescore}.csv for the ten ids in work/records/t2-top10.csv,
then applies the latest work/t3-gate-corrections-aNN.csv (gate cells changed after the fresh-context review; the old value
is kept in the `correction` column of g-gates.csv).
Writes work/artifact-audit.csv, work/evidence-ledger.csv, work/prior-work-t3.csv, work/g-gates.csv,
work/f-rescore-log.csv (changed cells only), work/f-rescore.csv (new F per record, t2_gate=1 for the
sensitivity script) and work/decision-matrix.csv (gates, h1-compat, T2 and rescored F, both ranks).
Prints the number of records passing all of G1-G5 and both rank-1 ids.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK, read_csv, write_csv  # noqa: E402

FS = ["F1", "F2", "F3", "F4", "F5", "F6"]
SUB = ["F1", "F2", "F3_code", "F3_data", "F3_compute", "F3_desc", "F4", "F5", "F6"]
GATES = ["G1", "G2", "G3", "G4", "G5"]
top = read_csv(WORK / "records" / "t2-top10.csv")
ids = [r["openalex_id"] for r in top]
t2 = {r["openalex_id"]: r for r in read_csv(WORK / "appraisal" / "f-scores.csv")}


def gather(kind):
    rows = []
    for i in ids:
        part = read_csv(WORK / "t3" / f"{i}-{kind}.csv")
        if not part or any(r["openalex_id"] != i for r in part):
            raise SystemExit(f"{i}-{kind}.csv: empty or foreign id")
        rows += part
    return rows


for kind, out in (("artifact", "artifact-audit"), ("evidence", "evidence-ledger"), ("prior", "prior-work-t3")):
    rows = gather(kind)
    write_csv(WORK / f"{out}.csv", rows, list(rows[0]))
gates = gather("gates")
for c in read_csv(sorted(WORK.glob("t3-gate-corrections-a*.csv"))[-1]):
    row = next(r for r in gates if (r["openalex_id"], r["gate"]) == (c["openalex_id"], c["gate"]))
    row["correction"] = f"{row['result']} -> {c['result']} ({c['reason']})"
    row.update(result=c["result"], evidence=c["evidence"], locator=c["locator"])
fields = list(gates[0]) + ["correction"] * ("correction" not in gates[0])
write_csv(WORK / "g-gates.csv", [{"correction": "", **r} for r in gates], fields)
g = {(r["openalex_id"], r["gate"]): r["result"].strip().lower() for r in gates}
rescore = gather("rescore")
log = []
new = {}
for i in ids:
    cells = {r["criterion"]: r for r in rescore if r["openalex_id"] == i}
    if sorted(cells) != sorted(SUB):
        raise SystemExit(f"{i}: rescore criteria {sorted(cells)}")
    for k in SUB:
        if cells[k]["old"] != t2[i][k]:
            raise SystemExit(f"{i} {k}: old {cells[k]['old']} != T2 {t2[i][k]}")
        if cells[k]["new"] != cells[k]["old"]:
            log.append({"openalex_id": i, **{x: cells[k][x] for x in ("criterion", "old", "new", "locator", "reason")}})
    v = {k: int(cells[k]["new"]) for k in SUB}
    v["F3"] = v["F3_code"] + v["F3_data"] + v["F3_compute"] + v["F3_desc"]
    new[i] = v
write_csv(WORK / "f-rescore-log.csv", log, ["openalex_id", "criterion", "old", "new", "locator", "reason"])
write_csv(WORK / "f-rescore.csv", [{"openalex_id": i, "t2_gate": "1", **{k: str(new[i][k]) for k in FS}} for i in ids],
          ["openalex_id", "t2_gate", *FS])


def order(score):
    return sorted(ids, key=lambda i: (-sum(score[i][k] for k in FS), -score[i]["F1"], -score[i]["F3"],
                                      -score[i]["F2"], -int(t2[i]["R_total"]), i))


old = {i: {k: int(t2[i][k]) for k in FS} for i in ids}
passing = [i for i in ids if all(g[(i, x)] == "pass" for x in GATES)]
rank_old = {i: n for n, i in enumerate(order(old), 1)}
pool = {i: new[i] for i in passing} if len(passing) >= 2 else new
rank_new = {i: n for n, i in enumerate(sorted(pool, key=lambda i: order(new).index(i)), 1)}
matrix = []
for r in top:
    i = r["openalex_id"]
    matrix.append({"openalex_id": i, "title": r["title"][:80], **{x: g[(i, x)] for x in GATES},
                   "all_gates": "pass" if i in passing else "fail", "h1_compat": g[(i, "h1-compat")],
                   **{f"{k}_t2": old[i][k] for k in FS}, "F_total_t2": sum(old[i].values()),
                   **{f"{k}_t3": new[i][k] for k in FS}, "F_total_t3": sum(new[i][k] for k in FS),
                   "rank_t2": rank_old[i], "rank_t3": rank_new.get(i, ""),
                   "sources": f"research/cards/t3/{i}.md; work/t3/{i}-gates.csv; work/t3/{i}-rescore.csv"})
write_csv(WORK / "decision-matrix.csv", matrix, list(matrix[0]))
leader_t2 = next(i for i in order(old) if i in pool)
leader_t3 = min(rank_new, key=rank_new.get)
print(json.dumps({"passing_all_gates": passing, "n_pass": len(passing), "rescore_changes": len(log),
                  "rank1_t2": leader_t2, "rank1_t3": leader_t3, "rank1_differs": leader_t2 != leader_t3}))
