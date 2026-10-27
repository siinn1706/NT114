"""Phase 05: join merged first-screener tables and keep only ids present in the current T0.

usage: python -X utf8 -I concat-screen.py T0_CSV OUT_CSV MERGED_CSV [MERGED_CSV ...]
Fails on a duplicate id or on a T0 id without a screening row; prints ids dropped because they left T0.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import read_csv, write_csv  # noqa: E402

t0 = {r["openalex_id"] for r in read_csv(sys.argv[1])}
rows, seen, dropped = [], set(), []
for path in sys.argv[3:]:
    for r in read_csv(path):
        if r["openalex_id"] in seen:
            raise SystemExit(f"duplicate id {r['openalex_id']} in {path}")
        seen.add(r["openalex_id"])
        (rows if r["openalex_id"] in t0 else dropped).append(r)
missing = sorted(t0 - seen)
if missing:
    raise SystemExit(f"T0 ids without screening row: {missing[:10]} ({len(missing)})")
write_csv(sys.argv[2], rows, list(rows[0]))
print(json.dumps({"rows": len(rows), "dropped_not_in_t0": [r["openalex_id"] for r in dropped]}))
