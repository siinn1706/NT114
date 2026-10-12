"""Keyword-group hints for manual relevance screening of q1-hits.csv.

Writes screen-sheet.tsv: idx, auto hint (groups matched in title+abstract), year, venue, title.
The hint only orders the sheet; the relevance score R is assigned by a human reader.
"""
import csv
import re
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
GROUPS = {
    "SYS": r"microservice|cloud[- ]native|kubernetes|cloud (system|service|platform)|online service|distributed system|aiops|it operation|incident",
    "DET": r"anomal|failure detection|fault detection|incident detection",
    "RCA": r"root[- ]cause|fault locali|failure locali|fault diagnos|failure diagnos|troubleshoot",
    "LLM": r"large language model|\bllms?\b|language model|gpt|agent",
    "RET": r"retrieval|\brag\b|bm25|knowledge base|historical incident|similar incident|case-based",
    "TEL": r"\blogs?\b|\btraces?\b|tracing|metric|telemetry|multimodal|multi-source",
    "EXP": r"explain|interpretab|uncertaint|confidence|calibrat|hallucinat|faithful",
    "PROP": r"propagat|call graph|dependency graph|topolog|causal",
}


def main():
    with open(WORK / "q1-hits.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for i, r in enumerate(rows):
        text = f"{r['title']} {r['abstract']}".lower()
        hit = [g for g, p in GROUPS.items() if re.search(p, text)]
        core = ("SYS" in hit) + ("DET" in hit or "RCA" in hit)
        out.append((core, len(hit), i, ",".join(hit), r["year"], r["venue"][:40], r["title"][:150]))
    out.sort(key=lambda x: (-x[0], -x[1], x[2]))
    with open(WORK / "screen-sheet.tsv", "w", encoding="utf-8", newline="") as f:
        f.write("idx\tcore\thint\tyear\tvenue\ttitle\n")
        for core, _, i, hint, year, venue, title in out:
            f.write(f"{i}\t{core}\t{hint}\t{year}\t{venue}\t{title}\n")
    print("core=2:", sum(1 for o in out if o[0] == 2), "core=1:", sum(1 for o in out if o[0] == 1),
          "core=0:", sum(1 for o in out if o[0] == 0))


if __name__ == "__main__":
    main()
