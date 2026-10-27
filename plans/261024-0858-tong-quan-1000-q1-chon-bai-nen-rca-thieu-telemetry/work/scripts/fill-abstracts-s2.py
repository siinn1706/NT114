"""Phase 04: second abstract lane via the Semantic Scholar batch endpoint (one POST per 500 DOIs).

usage: python -X utf8 -I fill-abstracts-s2.py TAG [--title-only]
Targets the DOIs in work/abstract-fill-log-<TAG>.csv that Crossref could not fill. Writes
work/records/abstract-fill-s2-<TAG>.csv (full rows, origin abstract-fill:s2) and work/abstract-fill-s2-log-<TAG>.csv.
"""
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RECORD_FIELDS, UA, WORK, now_utc, read_csv, sha_bytes, write_csv  # noqa: E402


def main():
    tag = sys.argv[1]
    sfx = "-tonly" if "--title-only" in sys.argv[2:] else ""
    missing = {r["doi"]: r for r in read_csv(WORK / f"abstract-fill-log-{tag}{sfx}.csv") if r["got_abstract"] == "0"}
    rows = {r["openalex_id"]: r for r in read_csv(WORK / "records" / f"{tag}-candidates.csv")}
    rows.update({r["openalex_id"]: r for r in read_csv(WORK / "records" / f"{tag}-excluded.csv")})
    rows.update({r["openalex_id"]: r for r in read_csv(WORK / "records" / f"{tag}-needs-review-t0.csv")})
    dois = sorted(missing)
    raw_dir = WORK / "raw" / "s2"
    raw_dir.mkdir(parents=True, exist_ok=True)
    out, log = [], []
    for i in range(0, len(dois), 500):
        chunk = dois[i:i + 500]
        body = json.dumps({"ids": [f"DOI:{d}" for d in chunk]}).encode()
        headers = {"Content-Type": "application/json", "User-Agent": UA}
        if os.environ.get("SEMANTIC_SCHOLAR_API_KEY"):
            headers["x-api-key"] = os.environ["SEMANTIC_SCHOLAR_API_KEY"]
        for wait in (0, 5, 20, 60):
            time.sleep(wait)
            request = urllib.request.Request("https://api.semanticscholar.org/graph/v1/paper/batch?fields=abstract,externalIds",
                                             data=body, headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    status, raw = response.status, response.read()
            except urllib.error.HTTPError as error:
                status, raw = error.code, error.read() or b""
            if status != 429:
                break
        (raw_dir / f"batch-{tag}{sfx}-{i // 500:02d}-{now_utc().replace(':', '')}.json").write_bytes(raw)
        results = json.loads(raw) if status == 200 else [None] * len(chunk)
        for doi, item in zip(chunk, results):
            abstract = (item or {}).get("abstract") or ""
            log.append({"doi": doi, "http": status, "got_abstract": int(bool(abstract)), "raw_sha256": sha_bytes(raw)})
            if abstract:
                rec = rows[missing[doi]["openalex_id"]]
                new = {k: rec.get(k, "") for k in RECORD_FIELDS}
                new.update(abstract=abstract, abstract_source="semanticscholar", origin="abstract-fill:s2",
                           raw_sha256=sha_bytes(raw), retrieved_at_utc=now_utc())
                out.append(new)
    write_csv(WORK / "records" / f"abstract-fill-s2-{tag}{sfx}.csv", out, RECORD_FIELDS)
    write_csv(WORK / f"abstract-fill-s2-log-{tag}{sfx}.csv", log, ["doi", "http", "got_abstract", "raw_sha256"])
    print(json.dumps({"targets": len(dois), "filled": len(out)}))


if __name__ == "__main__":
    main()
