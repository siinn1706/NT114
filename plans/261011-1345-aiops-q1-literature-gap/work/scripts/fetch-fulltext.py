"""Download open full texts for read50.csv into the private store and log every attempt.

Candidates per paper, in order: OpenAlex OA locations with a pdf_url, ACM DL pdf for 10.1145 DOIs,
then an arXiv preprint whose title matches (marked as preprint version). A file counts only if it starts
with %PDF. Existing files are kept. Usage: python -X utf8 fetch-fulltext.py
"""
import os
import csv
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
STORE = WORK.parents[2] / "private" / "fulltext"
MAILTO = os.environ.get("NCKH_MAILTO", "")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"


def http(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/pdf,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type", "")


def norm(t):
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def arxiv_candidates(title):
    words = " AND ".join(f"ti:{w}" for w in norm(title).split()[:8] if len(w) > 3)
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode({"search_query": words, "max_results": 5})
    data, _ = http(url)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in ET.fromstring(data).findall("a:entry", ns):
        t = e.find("a:title", ns).text or ""
        aid = e.find("a:id", ns).text.rsplit("/abs/", 1)[-1]
        if norm(t)[:60] == norm(title)[:60]:
            out.append(("arxiv-preprint", f"https://arxiv.org/pdf/{aid}"))
    time.sleep(3)
    return out


def main():
    STORE.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(WORK / "read50.csv", encoding="utf-8")))
    ids = "|".join(r["openalex_id"] for r in rows)
    meta_url = "https://api.openalex.org/works?" + urllib.parse.urlencode(
        {"filter": f"openalex_id:{ids}", "per-page": 50, "select": "id,locations", "mailto": MAILTO})
    meta = {w["id"].rsplit("/", 1)[-1]: w for w in json.loads(http(meta_url)[0])["results"]}
    log = []
    for r in rows:
        dest = STORE / f"{r['read_id']}.pdf"
        if dest.exists():
            log.append([r["read_id"], r["doi"], "existing", "", "ok", dest.stat().st_size])
            continue
        cands = []
        for loc in meta.get(r["openalex_id"], {}).get("locations") or []:
            if loc.get("pdf_url"):
                kind = "publisher" if loc.get("version") == "publishedVersion" else (loc.get("version") or "unknown")
                cands.append((kind, loc["pdf_url"]))
        if r["doi"].startswith("10.1145/"):
            cands.append(("publisher", f"https://dl.acm.org/doi/pdf/{r['doi']}"))
        got = False
        tried_arxiv = False
        while not got:
            for kind, url in cands:
                try:
                    data, ctype = http(url)
                except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                    log.append([r["read_id"], r["doi"], kind, url, f"error {getattr(e, 'code', e)}", 0])
                    continue
                if data[:4] == b"%PDF":
                    dest.write_bytes(data)
                    log.append([r["read_id"], r["doi"], kind, url, "ok", len(data)])
                    got = True
                    break
                log.append([r["read_id"], r["doi"], kind, url, f"not pdf ({ctype[:30]})", len(data)])
            if got or tried_arxiv:
                break
            tried_arxiv = True
            try:
                cands = arxiv_candidates(r["title"])
            except Exception as e:  # arXiv API failures must not stop the batch
                log.append([r["read_id"], r["doi"], "arxiv-search", "", f"error {e}", 0])
                cands = []
            if not cands:
                log.append([r["read_id"], r["doi"], "arxiv-search", "", "no title match", 0])
        print(r["read_id"], "ok" if got else "MISSING", flush=True)
    with open(WORK / "access-log.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["read_id", "doi", "version", "url", "result", "bytes"])
        w.writerows(log)


if __name__ == "__main__":
    main()
