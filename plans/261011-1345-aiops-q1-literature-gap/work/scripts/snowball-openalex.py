"""One snowball round on OpenAlex: missing seed DOIs, named seed titles, forward and backward citations.

Seeds are rows of q1-hits.csv given by screen-sheet idx (KEY_IDX). Results are cached in raw/SB-*.json
with the same layout as search pages so merge-hits.py can ingest them.
"""
import os
import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
RAW = WORK / "raw"
MAILTO = os.environ.get("NCKH_MAILTO", "")
SELECT = ("id,doi,title,publication_year,publication_date,type,cited_by_count,primary_location,"
          "authorships,abstract_inverted_index,referenced_works_count,open_access")
JOURNAL = "type:article|review,primary_location.source.type:journal,from_publication_date:2020-01-01"
# 11 key papers + 6 surveys (idx in screen-sheet.tsv)
KEY_IDX = [25, 61, 7, 65, 92, 42, 33, 38, 4, 35, 343, 11, 2, 54, 136, 10, 138]
NAMED = ["FlexLog", "CoLA log anomaly detection", "LLM-LADE", "LogRAIL", "LogFiT",
         "FRLog", "Semantics over statistics log anomaly"]


def get(params, path=None):
    if path and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode({**params, "mailto": MAILTO})
    req = urllib.request.Request(url, headers={"User-Agent": f"nckh-survey (mailto:{MAILTO})"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
                data["_meta_request"] = {"url": url, "ran_utc": datetime.now(timezone.utc).isoformat(),
                                         "remaining_usd": r.headers.get("X-RateLimit-Remaining-USD")}
                break
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4:
                raise
            time.sleep(2 ** (attempt + 1))
    if path:
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    time.sleep(0.5)
    return data


def main():
    rows = list(csv.DictReader(open(WORK / "q1-hits.csv", encoding="utf-8")))
    keys = [rows[i]["openalex_id"] for i in KEY_IDX]
    seeds = [l.strip() for l in open(WORK / "seed-dois.txt", encoding="utf-8") if l.strip()]
    have = {r["doi"] for r in csv.DictReader(open(WORK / "raw-hits.csv", encoding="utf-8"))}
    missing = [d for d in seeds if d not in have]
    if missing:
        d = get({"filter": "doi:" + "|".join(missing), "per-page": 50, "select": SELECT}, RAW / "SB-seed-doi.json")
        print("seed doi", len(d["results"]))
    for i, name in enumerate(NAMED):
        d = get({"filter": f"{JOURNAL},title.search:{name}", "per-page": 5, "select": SELECT},
                RAW / f"SB-named-{i}.json")
        print("named", name, d["meta"]["count"])
    for page in range(1, 4):
        d = get({"filter": f"{JOURNAL},cites:{'|'.join(keys)}", "per-page": 200, "page": page,
                 "select": SELECT}, RAW / f"SB-forward-p{page}.json")
        print("forward page", page, "count", d["meta"]["count"], "got", len(d["results"]))
        if len(d["results"]) < 200:
            break
    refs = get({"filter": "openalex_id:" + "|".join(keys), "per-page": 50, "select": "id,referenced_works"},
               RAW / "KR-key-refs.json")
    ref_ids = sorted({w.rsplit("/", 1)[-1] for r in refs["results"] for w in r.get("referenced_works") or []})
    print("backward reference ids", len(ref_ids))
    for n in range(0, len(ref_ids), 50):
        d = get({"filter": f"{JOURNAL},openalex_id:{'|'.join(ref_ids[n:n + 50])}", "per-page": 50,
                 "select": SELECT}, RAW / f"SB-backward-{n // 50:02d}.json")
        print("backward batch", n // 50, "journal hits", len(d["results"]), d["_meta_request"]["remaining_usd"])


if __name__ == "__main__":
    main()
