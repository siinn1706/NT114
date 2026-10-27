"""Phase 05: deterministic T1 ranking -> top 100 + reserve-nonllm (protocol §6 "Chọn 100").

usage: python -X utf8 -I rank-t1.py T0_CSV SCREEN_CSV RESOLUTION_CSV TAG
SCREEN_CSV: first-screener merged table. RESOLUTION_CSV: openalex_id,final_decision,R1..R6 (blank = keep first
screener's value), written after re-reading disagreements; it may be header-only.
Writes work/records/<TAG>-t1-ranked.csv (every eligible/fill row with rank) and work/records/<TAG>-t1.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK, read_csv, write_csv  # noqa: E402

RS = ["R1", "R2", "R3", "R4", "R5", "R6"]
t0 = {r["openalex_id"]: r for r in read_csv(sys.argv[1])}
screen = {r["openalex_id"]: dict(r, final_decision=r["decision"]) for r in read_csv(sys.argv[2])}
for res in read_csv(sys.argv[3]):
    row = screen[res["openalex_id"]]
    row["final_decision"] = res["final_decision"] or row["decision"]
    for k in RS:
        if res.get(k, "") != "":
            row[k] = res[k]
    row["R_total"] = str(sum(int(row[k]) for k in RS))
tag = sys.argv[4]


def key(r):
    m = t0[r["openalex_id"]]
    return (-int(r["R_total"]), -int(r["R1"]), -int(r["R3"]), -int(r["R2"]), int(m["q1_weak"] or 0),
            -int(m["year"] or 0), m["doi"] or r["openalex_id"])


inc = [r for r in screen.values() if r["final_decision"] == "include"]
eligible = sorted([r for r in inc if int(r["R1"]) >= 2], key=key)
fill = sorted([r for r in inc if int(r["R1"]) == 1], key=key)
top = [dict(r, tier="eligible") for r in eligible[:100]]
top += [dict(r, tier="fill-r1") for r in fill[:max(0, 100 - len(top))]]
in_top = {r["openalex_id"] for r in top}
reserve = [dict(r, tier="reserve-nonllm") for r in sorted(inc, key=key)
           if r["openalex_id"] not in in_top and r["R1"] == "3" and r["R5"] == "1" and r["R6"] == "1"][:10]
rows = []
for rank, r in enumerate(top + reserve, start=1):
    m = t0[r["openalex_id"]]
    rows.append({"rank": rank if r["tier"] != "reserve-nonllm" else "", "tier": r["tier"], "openalex_id": r["openalex_id"],
                 "doi": m["doi"], "year": m["year"], "venue": m["venue"], "q1_weak": m["q1_weak"], "title": m["title"],
                 **{k: r[k] for k in RS}, "R_total": r["R_total"], "final_decision": r["final_decision"]})
write_csv(WORK / "records" / f"{tag}-t1-ranked.csv", rows, list(rows[0]))
summary = {"n_screened": len(screen), "decisions": {d: sum(r["final_decision"] == d for r in screen.values())
                                                    for d in ("include", "exclude", "needs-review", "context-survey")},
           "eligible_R1ge2": len(eligible), "top": len(top), "fill_r1": sum(r["tier"] == "fill-r1" for r in top),
           "reserve_nonllm": len(reserve)}
(WORK / "records" / f"{tag}-t1.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
print(json.dumps(summary))
