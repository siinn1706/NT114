"""Phase 02 extras: map old full texts to DOIs by hash and split non-journal seed records into the prior-work pool."""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PLAN, RECORD_FIELDS, WORK, commit_batch, load_state, read_csv, sha_file, write_csv  # noqa: E402

OLD = PLAN.parent / "261011-1345-aiops-q1-literature-gap" / "work"
FULLTEXT = PLAN.parent.parent / "private" / "fulltext"

read_final = {r["read_id"]: r for r in read_csv(OLD / "read-final.csv")}
access = read_csv(OLD / "access-log.csv")
ok_bytes = {}
for row in access:
    if row["result"].startswith("ok"):
        ok_bytes[row["read_id"]] = row
fulltext_rows = []
for path in sorted(FULLTEXT.rglob("*")):
    if not path.is_file():
        continue
    rid = path.stem
    meta = read_final.get(rid, {})
    head = path.read_bytes()[:5]
    fulltext_rows.append({
        "file": str(path.relative_to(PLAN.parent.parent)).replace("\\", "/"), "sha256": sha_file(path),
        "bytes": path.stat().st_size, "is_pdf": int(head.startswith(b"%PDF")),
        "read_id": rid if meta else "", "doi": meta.get("doi", ""), "title": meta.get("title", ""),
        "old_read_level": meta.get("read_level", ""),
        "arxiv": rid.replace("pace-lm-", "") if path.parent.name == "261019" else "",
        "reusable": int(bool(meta) and head.startswith(b"%PDF")),
    })
write_csv(WORK / "reuse-fulltext-map.csv", fulltext_rows, list(fulltext_rows[0]))

seed = read_csv(WORK / "records" / "seed-reused.csv")
pool = [r for r in seed if r["source_type"] != "journal"]
not_found = read_csv(WORK / "records" / "reuse-not-found.csv")
write_csv(WORK / "records" / "prior-work-pool.csv", pool, RECORD_FIELDS)
summary = {
    "fulltext_files": len(fulltext_rows), "fulltext_reusable_pdf_with_doi": sum(r["reusable"] for r in fulltext_rows),
    "seed_rows": len(seed), "seed_source_types": dict(Counter(r["source_type"] for r in seed).most_common()),
    "prior_work_pool_rows": len(pool), "not_found": len(not_found),
    "not_found_arxiv_doi": sum(1 for r in not_found if r["key"].startswith("10.48550/")),
}
(WORK / "records" / "reuse-summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
state = load_state()
commit_batch(state, "02", "reuse-seed",
             [WORK / "records" / "seed-reused.csv", WORK / "reuse-fulltext-map.csv",
              WORK / "records" / "prior-work-pool.csv", WORK / "records" / "reuse-summary.json"],
             receipt="work/receipts/02-reuse-seed-01.json|work/receipts/02-reuse-extras-01.json")
state = load_state()
state["phases"]["02"]["status"] = "committed"
from common import save_state  # noqa: E402
save_state(state)
print(json.dumps(summary, indent=1))
