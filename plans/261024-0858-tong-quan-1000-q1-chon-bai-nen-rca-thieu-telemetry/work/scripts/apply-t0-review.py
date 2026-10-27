"""Phase 04: apply title+venue decisions for needs-review-t0 records (protocol §4) and write the final T0 file.

usage: python -X utf8 -I apply-t0-review.py TAG KEEP_IDS_COMMA_SEPARATED
Writes work/records/<TAG>-t0-review-decisions.csv and work/records/<TAG>-t0.csv (candidates + kept reviews).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK, read_csv, write_csv  # noqa: E402

tag, keep = sys.argv[1], set(sys.argv[2].split(","))
review = read_csv(WORK / "records" / f"{tag}-needs-review-t0.csv")
unknown = keep - {r["openalex_id"] for r in review}
if unknown:
    raise SystemExit(f"ids not in review file: {sorted(unknown)}")
decisions = [{"openalex_id": r["openalex_id"], "title": r["title"], "venue": r["venue"],
              "t0_decision": "keep" if r["openalex_id"] in keep else "exclude",
              "basis": "title+venue: software-system operations with failure/observability topic"
              if r["openalex_id"] in keep else "title+venue: outside Population or no failure-diagnosis topic",
              "decided_by": "agent (single reader)"} for r in review]
write_csv(WORK / "records" / f"{tag}-t0-review-decisions.csv", decisions, list(decisions[0]))
cands = read_csv(WORK / "records" / f"{tag}-candidates.csv")
kept = [dict(r, topic_gate="title-review-keep", exclude_reason="") for r in review if r["openalex_id"] in keep]
rows = cands + kept
write_csv(WORK / "records" / f"{tag}-t0.csv", rows, list(cands[0]))
print(len(cands), "+", len(kept), "=", len(rows))
