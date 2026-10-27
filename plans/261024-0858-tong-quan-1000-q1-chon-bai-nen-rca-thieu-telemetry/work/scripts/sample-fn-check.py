"""Phase 04: stratified false-negative sample of topic-gate exclusions (protocol §4).

usage: python -X utf8 -I sample-fn-check.py TAG  -> work/records/<TAG>-fn-sample.csv (25 borderline + 25 neither)
Only records whose sole exclusion is the topic gate are sampled.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SEED, SYSTEM_RE, TASK_RE, WORK, read_csv, write_csv  # noqa: E402

tag = sys.argv[1]
rows = [r for r in read_csv(WORK / "records" / f"{tag}-excluded.csv") if r["exclude_reason"] == "T-off-topic-metadata"]
rows.sort(key=lambda r: r["openalex_id"])
border, neither = [], []
for r in rows:
    text = f"{r['title']} {r['abstract']}"
    hits = bool(SYSTEM_RE.search(text)) + bool(TASK_RE.search(text))
    (border if hits == 1 else neither).append(r)
rng = random.Random(SEED)
sample = [dict(r, stratum="borderline") for r in rng.sample(border, min(25, len(border)))]
sample += [dict(r, stratum="neither") for r in rng.sample(neither, min(25, len(neither)))]
out = [{"stratum": r["stratum"], "openalex_id": r["openalex_id"], "title": r["title"], "venue": r["venue"],
        "abstract_head": r["abstract"][:400], "should_keep": "", "note": ""} for r in sample]
write_csv(WORK / "records" / f"{tag}-fn-sample.csv", out, list(out[0]))
print(len(border), len(neither), len(out))
