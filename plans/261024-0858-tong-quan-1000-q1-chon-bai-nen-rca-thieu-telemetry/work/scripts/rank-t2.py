"""Phase 07: merge F-score batches and select T2 (protocol §7 "Cổng T2").

usage: python -X utf8 -I rank-t2.py OVERRIDES_CSV
OVERRIDES_CSV: openalex_id,field,value,reason (final values after cross-check review; may be header-only).
Reads work/appraisal/batch-*.csv; writes work/appraisal/f-scores.csv (all rows, with f_rank) and
work/records/t2-top10.csv. Gate: t2_gate = 1. Order: F_total desc, then F1, F3, F2, R_total (T1), DOI/openalex_id.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK, read_csv, write_csv  # noqa: E402

FS = ["F1", "F2", "F3", "F4", "F5", "F6"]
t1 = {r["openalex_id"]: r for r in read_csv(WORK / "records" / "t1-top100.csv")}
ledger = {r["openalex_id"]: r for r in read_csv(WORK / "access-ledger-final.csv")}
rows = [r for p in sorted((WORK / "appraisal").glob("batch-*.csv")) for r in read_csv(p)]
ids = [r["openalex_id"] for r in rows]
if len(ids) != len(set(ids)):
    raise SystemExit("duplicate openalex_id across batches")
by_id = {r["openalex_id"]: r for r in rows}
for o in read_csv(sys.argv[1]):
    by_id[o["openalex_id"]][o["field"]] = o["value"]
    by_id[o["openalex_id"]]["override"] = (by_id[o["openalex_id"]].get("override", "") + f"{o['field']}={o['value']} ({o['reason']}); ")
for r in rows:
    if not ledger[r["openalex_id"]]["status"].startswith("full-text"):
        raise SystemExit(f"{r['openalex_id']}: F score without full text")
    r["F_total"] = str(sum(int(r[k]) for k in FS))
    r["R_total"] = t1[r["openalex_id"]]["R_total"]
    r.setdefault("override", "")


def key(r):
    return (-int(r["F_total"]), -int(r["F1"]), -int(r["F3"]), -int(r["F2"]), -int(r["R_total"]),
            t1[r["openalex_id"]]["doi"] or r["openalex_id"])


gated = sorted([r for r in rows if r["t2_gate"] == "1"], key=key)
for i, r in enumerate(gated, start=1):
    r["f_rank"] = str(i)
for r in rows:
    r.setdefault("f_rank", "")
ordered = gated + sorted([r for r in rows if r["t2_gate"] != "1"], key=key)
fields = list(rows[0].keys())
for extra in ("R_total", "f_rank", "override"):
    if extra not in fields:
        fields.append(extra)
write_csv(WORK / "appraisal" / "f-scores.csv", ordered, fields)
top = gated[:10]
write_csv(WORK / "records" / "t2-top10.csv",
          [{"t2_rank": r["f_rank"], "openalex_id": r["openalex_id"], "doi": t1[r["openalex_id"]]["doi"],
            "title": t1[r["openalex_id"]]["title"], "t1_rank": t1[r["openalex_id"]]["rank"], "R_total": r["R_total"],
            **{k: r[k] for k in FS}, "F_total": r["F_total"]} for r in top],
          ["t2_rank", "openalex_id", "doi", "title", "t1_rank", "R_total", *FS, "F_total"])
gap = int(gated[9]["F_total"]) - int(gated[10]["F_total"]) if len(gated) > 10 else None
ties = [r["openalex_id"] for r in gated if len(gated) > 9 and r["F_total"] == gated[9]["F_total"]]
print(json.dumps({"scored": len(rows), "gated": len(gated), "top": len(top), "gap_10_11": gap,
                  "tied_with_rank10": ties}))
