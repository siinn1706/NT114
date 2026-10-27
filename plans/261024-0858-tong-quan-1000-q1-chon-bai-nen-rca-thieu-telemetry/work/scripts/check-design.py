"""Phase 09 checks on the design documents (phase-09 "Kiểm tra" list, mechanical part only).

usage: python -X utf8 -I check-design.py
Checks: each of the four docs starts with the conditional line; no unqualified "đầu tiên"/"novel"/"first" claim (the trace label "S-first" is not a claim);
each hypothesis id in improvement-hypotheses.md has a falsifier and >= 1 prior-work CSV row; both branches (a)
and (b) appear in reproduction-protocol.md and mvp-outline.md; test-matrix.md states the no-label-in-prompt rule.
Exits non-zero on any failure. Judgment checks (verdicts, MDE, oracle use) are left to the fresh-context review.
"""
import csv
import json
import re
import sys
from pathlib import Path

PLAN = Path(__file__).resolve().parents[2]
DOCS = ["reproduction-protocol", "improvement-hypotheses", "test-matrix", "mvp-outline"]
COND = "Có điều kiện: chờ chủ dự án chấp nhận bài nền RCLAgent"
text = {d: (PLAN / "design" / f"{d}.md").read_text(encoding="utf-8") for d in DOCS}
fail = []
for d, t in text.items():
    if COND not in "\n".join(t.splitlines()[:3]):
        fail.append(f"{d}: conditional line missing at top")
    for w in re.findall(r"đầu tiên|\bnovel\b|(?<!S-)\bfirst\b", t, flags=re.I):
        fail.append(f"{d}: claim word '{w}'")
hyp = sorted(set(re.findall(r"\bIM\d\b", text["improvement-hypotheses"])))
rows = list(csv.DictReader(open(PLAN / "work" / "prior-work-improvements.csv", encoding="utf-8")))
for h in hyp:
    if not any(r["hypothesis_id"] == h for r in rows):
        fail.append(f"{h}: no prior-work row")
    block = text["improvement-hypotheses"].split(h, 1)[1][:4000]
    if not re.search(r"falsifier|bác bỏ", block, flags=re.I):
        fail.append(f"{h}: no falsifier near its heading")
for d in ("reproduction-protocol", "mvp-outline"):
    if not (re.search(r"[Nn]hánh \(?a\)?", text[d]) and re.search(r"[Nn]hánh \(?b\)?", text[d])):
        fail.append(f"{d}: branches (a)/(b) not both present")
if not re.search(r"nhãn|label", text["test-matrix"], flags=re.I):
    fail.append("test-matrix: no-label-in-prompt rule not found")
print(json.dumps({"hypotheses": hyp, "prior_rows": len(rows), "failures": fail}, ensure_ascii=False))
sys.exit(1 if fail else 0)
