"""Mark each hit with its SJR 2025 Best Quartile (Q1 or not) using sjr-2025-q1-matched.txt.

Usage: python -X utf8 q1-filter.py [input.csv] [output.csv]
Default: raw-hits.csv -> q1-hits.csv (only Q1, non-MDPI rows; flags kept as columns).
Prints counts for the PRISMA ledger. Rerunning on top100.csv must report 100% Q1.
"""
import csv
import json
import sys
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
Q1_WEAK = {"21693536": "IEEE Access", "20452322": "Scientific Reports"}


def load_q1():
    table = {}
    for entry in (WORK / "sjr-2025-q1-matched.txt").read_text(encoding="utf-8").strip().split(";"):
        issns, sjr, cs = entry.split(",")
        for issn in issns.split("/"):
            table[issn] = (float(sjr), cs == "1", issns)
    return table


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else WORK / "raw-hits.csv"
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else WORK / "q1-hits.csv"
    q1 = load_q1()
    with open(src, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    kept, counts = [], {"input": len(rows), "not_q1": 0, "mdpi": 0, "q1_kept": 0, "q1_weak": 0, "cs_q1": 0}
    for r in rows:
        issns = [i.replace("-", "").upper() for i in r["issns"].split("|") if i]
        hit = next((q1[i] for i in issns if i in q1), None)
        if not hit:
            counts["not_q1"] += 1
            continue
        if any(k in r["publisher"].lower() for k in ("mdpi", "multidisciplinary digital publishing")):
            counts["mdpi"] += 1
            continue
        r["sjr_2025"], r["cs_category_q1"], r["sjr_issns"] = hit[0], int(hit[1]), hit[2]
        r["quartile"] = "Q1"
        r["q1_weak"] = int(any(i in Q1_WEAK for i in issns))
        counts["q1_kept"] += 1
        counts["q1_weak"] += r["q1_weak"]
        counts["cs_q1"] += r["cs_category_q1"]
        kept.append(r)
    if dst != src and kept:
        with open(dst, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(kept[0].keys()))
            w.writeheader()
            w.writerows(kept)
    counts["all_input_q1"] = counts["not_q1"] == 0 and counts["mdpi"] == 0
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
