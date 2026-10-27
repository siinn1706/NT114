"""Deduplicate the targeted-search ledger against every earlier record and ledger file of this plan.

usage: python -X utf8 -I dedup-targeted-search.py LEDGER_CSV OUT_CSV
A row matches when its DOI, arXiv id or a distinctive title fragment occurs (case-insensitive) in any
CSV under work/ (except the ledger itself) or in research/cards/. OUT_CSV is the ledger plus
`dedup_hits` (files that mention the work) and `dedup_status` (new | seen-before | n/a).
"""
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PLAN  # noqa: E402

TITLE_FRAGMENTS = {
    "TORAI": "blind spots in microservice",
    "PRAXIS": "integrating program analysis with observability",
    "CARE (IEEE TSE)": "context aware root cause identification",
    "GALA+": "graph-augmented llm agents",
    "RCLAgent TDSC": "multi-agent recursion-of-thought",
    "PRISM / Graph-Free Root Cause Analysis": "graph-free root cause analysis",
    "How Far Can RCA Go on Real-World Telemetry Data?": "how far can root cause analysis go",
    "Beyond Fault Localization (trajectory study)": "trajectory-level study of llm agents",
    "Where RCA Fails: Retrieval-Reranking Decomposition": "retrieval-reranking decomposition",
    "MonitorRank": "root cause detection in a service-oriented architecture",
}
ledger, out = Path(sys.argv[1]), sys.argv[2]
files = [p for p in (PLAN / "work").rglob("*.csv") if p.resolve() != ledger.resolve() and "raw" not in p.parts]
files += list((PLAN / "research" / "cards").rglob("*.md"))
texts = {p: p.read_text(encoding="utf-8", errors="replace").lower() for p in files}
rows = list(csv.DictReader(open(ledger, encoding="utf-8")))
for row in rows:
    keys = [k.lower() for k in re.findall(r"(?:10\.\d{4,}/\S+|\d{4}\.\d{5})", row["identifier"])]
    if row["candidate"] in TITLE_FRAGMENTS:
        keys.append(TITLE_FRAGMENTS[row["candidate"]])
    hits = sorted({str(p.relative_to(PLAN)).replace("\\", "/") for p, t in texts.items() for k in keys if k in t})
    row["dedup_hits"] = "|".join(hits)
    row["dedup_status"] = "n/a" if not keys else "seen-before" if hits else "new"
with open(out, "w", encoding="utf-8", newline="") as h:
    w = csv.DictWriter(h, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
for r in rows:
    print(r["candidate"], r["dedup_status"], r["dedup_hits"][:160])
