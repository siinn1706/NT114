"""Phase 08: check that each T3 text file on disk is the text hashed in phase 07.

usage: python -X utf8 -I check-text-hashes.py OUT_CSV
fulltext-access.py hashes the extracted text as LF UTF-8 in memory, while Path.write_text on Windows stores
CRLF. For each id in work/records/t2-top10.csv this compares the phase 07 input text_sha256 with the sha256 of
the raw file bytes and of the bytes after CRLF -> LF. Exits non-zero if any record matches neither.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK, read_csv, write_csv  # noqa: E402

REPO = WORK.parents[2]
want = {r["openalex_id"]: r for p in sorted((WORK / "appraisal" / "input").glob("batch-*.json"))
        for r in json.loads(p.read_text(encoding="utf-8"))}
rows = []
for r in read_csv(WORK / "records" / "t2-top10.csv"):
    i = r["openalex_id"]
    data = (REPO / want[i]["text_path"]).read_bytes()
    raw, lf = hashlib.sha256(data).hexdigest(), hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()
    rows.append({"openalex_id": i, "t2_text_sha256": want[i]["text_sha256"], "raw_sha256": raw, "lf_sha256": lf,
                 "crlf_count": data.count(b"\r\n"), "match": "raw" if raw == want[i]["text_sha256"]
                 else "lf" if lf == want[i]["text_sha256"] else "none"})
write_csv(sys.argv[1], rows, list(rows[0]))
bad = [r["openalex_id"] for r in rows if r["match"] == "none"]
print(json.dumps({"n": len(rows), "match_lf": sum(r["match"] == "lf" for r in rows), "none": bad}))
sys.exit(1 if bad else 0)
