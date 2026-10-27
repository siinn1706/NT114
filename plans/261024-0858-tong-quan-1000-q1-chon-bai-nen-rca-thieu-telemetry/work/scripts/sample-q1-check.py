"""Phase 04: draw 30 random T0 records and attach the raw SJR row they matched, for a manual Q1/year/type check.

usage: python -X utf8 -I sample-q1-check.py T0_CSV OUT_CSV
Reads the SJR CSV directly (raw Categories string) instead of the parsed table used by the gate.
"""
import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SEED, SJR_CSV, SJR_SHA, norm_issn, read_csv, sha_file, write_csv  # noqa: E402

if sha_file(SJR_CSV) != SJR_SHA:
    raise SystemExit("SJR CSV hash changed")
raw = {}
with open(SJR_CSV, encoding="utf-8") as handle:
    for row in csv.DictReader(handle, delimiter=";"):
        for issn in row["Issn"].split(","):
            raw.setdefault(norm_issn(issn), row)
rows = sorted(read_csv(sys.argv[1]), key=lambda r: r["openalex_id"])
out = []
for r in random.Random(SEED).sample(rows, 30):
    hits = [raw[i] for i in [norm_issn(x) for x in [r["issn_l"], *r["issns"].split("|")]] if i in raw]
    s = hits[0] if hits else {}
    out.append({"openalex_id": r["openalex_id"], "venue": r["venue"], "publication_date": r["publication_date"],
                "type": r["type"], "issns": r["issns"], "sjr_title": s.get("Title", ""), "sjr_type": s.get("Type", ""),
                "sjr_categories": s.get("Categories", ""), "gate_cs_categories": r["sjr_cs_categories"],
                "q1_weak": r["q1_weak"], "ok": "", "note": ""})
write_csv(sys.argv[2], out, list(out[0]))
