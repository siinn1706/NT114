"""Measure the §4 topic gate against the R labels of the 11/10 screened corpus (recall-oriented check)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PLAN, WORK, read_csv, sha_file, topic_ok  # noqa: E402

src = PLAN.parent / "261011-1345-aiops-q1-literature-gap" / "work" / "screened.csv"
rows = read_csv(src)
out = {"source": str(src.relative_to(PLAN.parent)), "source_sha256": sha_file(src), "by_R": {}}
for r_label in "3210":
    group = [r for r in rows if r["R"] == r_label]
    out["by_R"][r_label] = {"n": len(group), "pass": sum(topic_ok(r["title"], r["abstract"]) for r in group)}
(WORK / (sys.argv[1] if len(sys.argv) > 1 else "regex-calibration.json")).write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))
