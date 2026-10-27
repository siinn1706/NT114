"""Phase 03: run every frozen §5 query over all pages (page= paging); one query = one checkpointed batch.

usage: python -X utf8 -I search-openalex-cursor.py [--amend] [QUERY_ID ...]   (--amend: §10 synonym queries S1..)
Raw pages: work/raw/openalex/<qid>-a<attempt>-p<n>.json (immutable); rows: work/records/search-<qid>.csv;
log: work/search-log/<qid>.csv. A committed batch whose output hashes still match is skipped.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (OA_SELECT, RECORD_FIELDS, WORK, batch_done, commit_batch, http_get, load_state, next_attempt,  # noqa: E402
                    normalize_work, now_utc, sha_bytes, write_csv)
from queries import load_queries, url_for  # noqa: E402

PHASE = "03"


def run_query(state, q):
    raw_dir = WORK / "raw" / "openalex"
    raw_dir.mkdir(parents=True, exist_ok=True)
    # Failed attempts leave raw pages but no state entry; never reuse their attempt number.
    used = [int(p.name.split("-a")[1][:2]) for p in raw_dir.glob(f"{q['id']}-a*-p*.json")]
    attempt = max([next_attempt(state, PHASE, q["id"])] + [u + 1 for u in used])
    page, rows, log, meta_count, more = 0, [], [], None, True
    while more:
        page += 1
        url = url_for(q["query"], per_page=200, page=page, select=OA_SELECT)
        status, raw = http_get(url)
        retrieved = now_utc()
        path = raw_dir / f"{q['id']}-a{attempt:02d}-p{page:03d}.json"
        if path.exists():
            raise SystemExit(f"raw page exists: {path}")
        path.write_bytes(raw)
        raw_sha = sha_bytes(raw)
        if status != 200:
            log.append({"query": q["id"], "page": page, "http": status, "n": 0, "raw_sha256": raw_sha,
                        "as_of_utc": retrieved, "url": url})
            write_csv(WORK / "search-log" / f"{q['id']}-a{attempt:02d}.csv", log, list(log[0]))
            raise SystemExit(f"{q['id']} page {page}: HTTP {status}; batch left uncommitted")
        data = json.loads(raw)
        meta_count = data["meta"]["count"]
        results = data.get("results", [])
        rows += [normalize_work(w, f"search:{q['id']}:{page}", raw_sha, retrieved) for w in results]
        log.append({"query": q["id"], "page": page, "http": status, "n": len(results), "raw_sha256": raw_sha,
                    "as_of_utc": retrieved, "url": url})
        more = bool(results) and page * 200 < min(meta_count, 10000)
    rec = WORK / "records" / f"search-{q['id']}-a{attempt:02d}.csv"
    logf = WORK / "search-log" / f"{q['id']}-a{attempt:02d}.csv"
    write_csv(rec, rows, RECORD_FIELDS)
    write_csv(logf, log, list(log[0]))
    commit_batch(state, PHASE, q["id"], [rec, logf], attempt=f"{q['id']}-a{attempt:02d}", count=len(rows),
                 meta_count=meta_count, pages=page, query=q["query"])
    print(f"{q['id']}: {len(rows)} rows / meta {meta_count}, {page} pages", flush=True)


def main():
    state = load_state()
    if not state.get("protocol_sha256"):
        raise SystemExit("protocol not frozen")
    wanted = set(sys.argv[1:]) - {"--amend"}
    for q in load_queries(amend="--amend" in sys.argv):
        if wanted and q["id"] not in wanted:
            continue
        if batch_done(state, PHASE, q["id"]):
            print(f"{q['id']}: committed, skipped")
            continue
        run_query(state, q)
    state = load_state()
    state["phases"][PHASE]["status"] = "batches-committed"
    from common import save_state
    save_state(state)


if __name__ == "__main__":
    main()
