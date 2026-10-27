"""Phase 01 checks: SJR CSV hash/counts and the §4 topic regex on positive/negative samples."""
import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PLAN, SEED, SJR_CSV, SJR_SHA, WORK, load_sjr, sha_file, topic_ok, write_csv  # noqa: E402

OLD = PLAN.parent / "261011-1345-aiops-q1-literature-gap" / "work"

types = Counter()
with open(SJR_CSV, encoding="utf-8") as handle:
    for row in csv.DictReader(handle, delimiter=";"):
        types[row["Type"]] += 1
sjr = load_sjr()
journals = {id(v): v for v in sjr.values() if v["type"] == "journal"}
summary = {"sha256": sha_file(SJR_CSV), "expected": SJR_SHA, "types": dict(types),
           "journal_best_q1": sum(1 for v in journals.values() if v["best"] == "Q1"),
           "journal_cs_q1": sum(1 for v in journals.values() if v["cs_q1"])}

rng = random.Random(SEED)
read50 = list(csv.DictReader(open(OLD / "read-final.csv", encoding="utf-8")))
screened = {r["doi"]: r for r in csv.DictReader(open(OLD / "screened.csv", encoding="utf-8"))}
pos = [screened[r["doi"]] for r in read50 if r["doi"] in screened and screened[r["doi"]].get("abstract")]
pos = rng.sample(pos, min(30, len(pos)))
raw = list(csv.DictReader(open(OLD / "raw-hits.csv", encoding="utf-8")))
offtopic = [r for r in raw if any(w in (r["title"] + r["abstract"]).lower()
            for w in ("bearing", "power grid", "patient", "wind turbine", "gearbox", "transformer oil"))]
neg = rng.sample(offtopic, min(30, len(offtopic)))
rows = [{"sample": "positive", "doi": r["doi"], "title": r["title"][:120],
         "topic_ok": int(topic_ok(r["title"], r["abstract"]))} for r in pos]
rows += [{"sample": "negative", "doi": r["doi"], "title": r["title"][:120],
          "topic_ok": int(topic_ok(r["title"], r["abstract"]))} for r in neg]
write_csv(WORK / "regex-check.csv", rows, ["sample", "doi", "title", "topic_ok"])
summary["regex_positive_pass"] = f"{sum(r['topic_ok'] for r in rows if r['sample']=='positive')}/{len(pos)}"
summary["regex_negative_pass"] = f"{sum(r['topic_ok'] for r in rows if r['sample']=='negative')}/{len(neg)}"
(WORK / "sjr-regex-summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
print(json.dumps(summary, indent=1))
