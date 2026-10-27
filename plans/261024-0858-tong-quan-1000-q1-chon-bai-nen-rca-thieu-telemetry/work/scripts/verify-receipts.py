"""Phase 10: run check-receipt.py verify on every receipt and classify the result.

usage: python -X utf8 -I verify-receipts.py CHECK_RECEIPT_PY OUT_CSV
Classes: verified; superseded-state (only work/state.json changed since, by later checkpoints);
changed-later (only input/output files changed since, by later dated work); other (any other finding,
e.g. a compound command without segment exit statuses). Recorded commands are never executed.
"""
import collections
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

PLAN = Path(__file__).resolve().parents[2]
checker, out = sys.argv[1:3]
rows = []
for r in sorted((PLAN / "work" / "receipts").glob("*.json")):
    p = subprocess.run([sys.executable, "-X", "utf8", checker, "verify", "--receipt", str(r), "--workspace", str(PLAN)],
                       capture_output=True, text=True)
    d = json.loads(p.stdout)
    found = d.get("findings", [])
    files = sorted({m.group(1) for x in found for m in [re.match(r"(?:input|output) (\S+?):", x)] if m})
    other = [x for x in found if not re.match(r"(?:input|output) \S+?:", x)]
    cls = ("verified" if d["verdict"] == "VERIFIED" else "other" if other
           else "superseded-state" if files == ["work/state.json"] else "changed-later")
    rows.append({"receipt": r.stem, "verdict": d["verdict"], "class": cls, "changed_files": "|".join(files),
                 "other": " | ".join(other)[:300]})
with open(out, "w", encoding="utf-8", newline="") as h:
    w = csv.DictWriter(h, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(json.dumps(collections.Counter(r["class"] for r in rows)))
