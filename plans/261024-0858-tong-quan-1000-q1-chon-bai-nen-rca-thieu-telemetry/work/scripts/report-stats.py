"""Phase 10: derived numbers the final report cites, computed from committed files (no hand arithmetic).

usage: python -X utf8 -I report-stats.py OUT_JSON
- protocol hash on disk vs work/protocol-freeze.json
- T0 precision = include / screened with a Wilson 95% interval (protocol §4)
- q1_weak in final T0, q1_noncs and Q-7 counts (protocol §3 Q-4, Q-7)
- saturation steps: new, dropped and net change between consecutive T0 files (protocol §10)
- T3 papers whose publication year has no SJR edition yet (SJR 2025 used as proxy)
"""
import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PLAN, read_csv, sha_file  # noqa: E402

W = PLAN / "work"
freeze = json.loads((W / "protocol-freeze.json").read_text(encoding="utf-8"))
on_disk = sha_file(PLAN / freeze["protocol"])

t1 = json.loads((W / "records" / "final-t1.json").read_text(encoding="utf-8"))
k, n, z = t1["decisions"]["include"], t1["n_screened"], 1.959963984540054
p = k / n
centre = (p + z * z / (2 * n)) / (1 + z * z / n)
half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)

t0 = read_csv(W / "records" / "t0r2b-t0.csv")
summary = json.loads((W / "records" / "t0r2b-summary.json").read_text(encoding="utf-8"))
reasons = summary["exclude_reasons_multi"]

steps = [("seed", "t0seed4-t0.csv"), ("search", "t0full2-t0.csv"), ("snowball-r1", "t0snow2-t0.csv"),
         ("snowball-r2+synonyms", "t0r2b-t0.csv")]
saturation, prev = [], None
for label, name in steps:
    ids = {r["openalex_id"] for r in read_csv(W / "records" / name)}
    row = {"step": label, "n_t0": len(ids)}
    if prev is not None:
        row.update(new=len(ids - prev), dropped=len(prev - ids), net=len(ids) - len(prev),
                   dropped_ids=sorted(prev - ids))
    saturation.append(row)
    prev = ids

with open(W / "q1-pubyear-check.csv", encoding="utf-8", newline="") as h:
    pub = list(csv.DictReader(h))

result = {
    "protocol": {"frozen_sha256": freeze["protocol_sha256"], "on_disk_sha256": on_disk,
                 "match": on_disk == freeze["protocol_sha256"]},
    "precision_t0": {"include": k, "screened": n, "precision": round(p, 4),
                     "wilson95": [round(centre - half, 4), round(centre + half, 4)],
                     "n_x_precision": round(len(t0) * p, 1)},
    "q1": {"t0_rows": len(t0), "t0_q1_weak": sum(r["q1_weak"] == "1" for r in t0),
           "excluded_q1_noncs": reasons.get("Q-4-q1-noncs", 0), "excluded_q7_mdpi": reasons.get("Q-7-mdpi", 0)},
    "saturation": saturation,
    "t3_pubyear": {"papers": len(pub), "cs_q1_in_pub_year_yes": sum(r["cs_q1_in_pub_year"] == "yes" for r in pub),
                   "sjr_year_differs_from_pub_year": sum(r["sjr_year_checked"] != r["pub_year"] for r in pub),
                   "jcr_checked": sum(not r["jcr"].startswith("not checked") for r in pub)},
}
Path(sys.argv[1]).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
sys.exit(0 if result["protocol"]["match"] else 1)
