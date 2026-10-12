"""Run queries.csv against OpenAlex and cache raw JSON per query page.

Usage: python -X utf8 search-openalex.py [--pages N] [--only Q01,Q02]
Cached pages are never re-requested. Each search page costs OpenAlex credits.
"""
import os
import argparse
import csv
import json
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
RAW = WORK / "raw"
MAILTO = os.environ.get("NCKH_MAILTO", "")
SELECT = ("id,doi,title,publication_year,publication_date,type,cited_by_count,primary_location,"
          "authorships,abstract_inverted_index,referenced_works_count,open_access")


def fetch(url, attempts=5):
    req = urllib.request.Request(url, headers={"User-Agent": f"nckh-survey (mailto:{MAILTO})"})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r), dict(r.headers)
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == attempts - 1:
                raise
            wait = int(e.headers.get("Retry-After") or 0) or 2 ** (attempt + 1)
            print("429, retry after", wait, "s; body:", e.read()[:200], flush=True)
            time.sleep(min(wait, 60))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--per-page", type=int, default=200)
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    only = {q for q in args.only.split(",") if q}
    RAW.mkdir(exist_ok=True)
    log = []
    with open(WORK / "queries.csv", encoding="utf-8") as f:
        queries = list(csv.DictReader(f))
    for q in queries:
        if only and q["id"] not in only:
            continue
        for page in range(1, args.pages + 1):
            path = RAW / f"{q['id']}-p{page}.json"
            if path.exists():
                if len(json.loads(path.read_text(encoding="utf-8"))["results"]) < args.per_page:
                    break
                continue
            flt = f"{q['filters']},title_and_abstract.search:{q['boolean']}"
            url = ("https://api.openalex.org/works?" + urllib.parse.urlencode({
                "filter": flt, "per-page": args.per_page, "page": page,
                "select": SELECT, "mailto": MAILTO}))
            data, headers = fetch(url)
            data["_meta_request"] = {"url": url, "ran_utc": datetime.now(timezone.utc).isoformat(),
                                     "cost_usd": headers.get("X-RateLimit-Cost-USD"),
                                     "remaining_usd": headers.get("X-RateLimit-Remaining-USD")}
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            count = data["meta"]["count"]
            log.append((q["id"], page, count, len(data["results"]), headers.get("X-RateLimit-Remaining-USD")))
            print(q["id"], page, "count", count, "got", len(data["results"]),
                  "remaining_usd", headers.get("X-RateLimit-Remaining-USD"), flush=True)
            if len(data["results"]) < args.per_page:
                break
            time.sleep(1.0)


if __name__ == "__main__":
    main()
