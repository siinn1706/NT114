"""Phase 06: full-text access for the T1 top 100 in batches of 10 (protocol §9).

usage: python -X utf8 -I fulltext-access.py T1_TOP100_CSV
Order per record: reusable old full text (hash re-checked) -> OpenAlex OA locations -> Unpaywall -> arXiv
(title similarity >= 0.92 and first-author surname match). Only open-access URLs are fetched; no SSO, no retries
on 401/403. PDFs and extracted text go to <repo>/private/fulltext/261024/ (gitignored); raw API responses to
work/raw/fulltext/. Per batch: work/access/batch-NNN.csv, checkpointed in state phase 06 as access-NNN.
Merged ledger: work/access-ledger.csv. Requires RESEARCH_CONTACT_EMAIL for Unpaywall (never written to files).
"""
import csv
import difflib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PLAN, UA, WORK, batch_done, commit_batch, http_get, load_state, now_utc, read_csv, sha_bytes, sha_file, write_csv  # noqa: E402

import pypdf  # noqa: E402

PHASE = "06"
REPO = PLAN.parents[1]
PRIVATE = REPO / "private" / "fulltext" / "261024"
RAW = WORK / "raw" / "fulltext"
FIELDS = ["rank", "openalex_id", "doi", "title", "status", "source", "url", "http", "version", "license",
          "pdf_path", "pdf_sha256", "pdf_bytes", "text_sha256", "pages", "text_chars", "extractor", "reason",
          "as_of_utc"]


def norm_title(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def fetch_pdf(url):
    """Return (status, bytes); 401/403 and non-PDF bodies are not retried."""
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/pdf,*/*"})
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, b""
    except (urllib.error.URLError, TimeoutError, ConnectionError, ValueError):
        return 0, b""


def extract(pdf_bytes):
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    return len(reader.pages), text


def store(rec, pdf, row):
    PRIVATE.mkdir(parents=True, exist_ok=True)
    path = PRIVATE / f"{rec['openalex_id']}.pdf"
    if not path.exists():
        path.write_bytes(pdf)
    pages, text = extract(pdf)
    (PRIVATE / f"{rec['openalex_id']}.txt").write_text(text, encoding="utf-8")
    row.update(pdf_path=str(path.relative_to(REPO)).replace("\\", "/"), pdf_sha256=sha_bytes(pdf), pdf_bytes=len(pdf),
               text_sha256=sha_bytes(text.encode("utf-8")), pages=pages, text_chars=len(text),
               extractor=f"pypdf {pypdf.__version__}")
    if len(text.strip()) < 2000:
        row["status"], row["reason"] = "image-only", "extracted text < 2000 chars; OCR needed before use"
    return row


def oa_candidates(rec, raw_prefix):
    out = []
    oid = rec["openalex_id"]
    status, raw = http_get(f"https://api.openalex.org/works/{oid}?select=id,open_access,best_oa_location,locations")
    (RAW / f"{raw_prefix}-openalex.json").write_bytes(raw)
    if status == 200:
        work = json.loads(raw)
        locs = [work.get("best_oa_location")] + (work.get("locations") or [])
        for loc in locs:
            if loc and loc.get("is_oa") and loc.get("pdf_url"):
                out.append(("openalex", loc["pdf_url"], loc.get("version") or "", loc.get("license") or ""))
    email = os.environ.get("RESEARCH_CONTACT_EMAIL")
    if rec["doi"] and email:
        url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(rec['doi'])}?email={urllib.parse.quote(email)}"
        status, raw = http_get(url)
        (RAW / f"{raw_prefix}-unpaywall.json").write_bytes(raw)
        if status == 200:
            data = json.loads(raw)
            for loc in [data.get("best_oa_location")] + (data.get("oa_locations") or []):
                if loc and loc.get("url_for_pdf"):
                    out.append(("unpaywall", loc["url_for_pdf"], loc.get("version") or "", loc.get("license") or ""))
    return out


def arxiv_candidate(rec, raw_prefix):
    query = urllib.parse.quote(f'ti:"{norm_title(rec["title"])[:200]}"')
    status, raw = http_get(f"http://export.arxiv.org/api/query?search_query={query}&max_results=5")
    (RAW / f"{raw_prefix}-arxiv.xml").write_bytes(raw)
    time.sleep(3)
    if status != 200:
        return None
    ns = {"a": "http://www.w3.org/2005/Atom"}
    surname = norm_title(rec.get("first_author", "")).split(" ")[-1] if rec.get("first_author") else ""
    for entry in ET.fromstring(raw).findall("a:entry", ns):
        title = norm_title(entry.findtext("a:title", "", ns))
        ratio = difflib.SequenceMatcher(None, title, norm_title(rec["title"])).ratio()
        authors = " ".join(norm_title(a.findtext("a:name", "", ns)) for a in entry.findall("a:author", ns))
        if ratio >= 0.92 and surname and surname in authors:
            abs_id = entry.findtext("a:id", "", ns).rsplit("/abs/", 1)[-1]
            return ("arxiv", f"https://arxiv.org/pdf/{abs_id}", f"preprint arXiv:{abs_id}", "arXiv")
    return None


def access(rec, reuse):
    row = {k: "" for k in FIELDS}
    row.update(rank=rec["rank"], openalex_id=rec["openalex_id"], doi=rec["doi"], title=rec["title"], as_of_utc=now_utc())
    old = reuse.get(rec["doi"].lower()) if rec["doi"] else None
    if old:
        src = REPO / old["file"]
        if src.is_file() and sha_file(src) == old["sha256"]:
            row.update(status="full-text-journal", source="reuse", url=old["file"], version="as reused (phase 02 map)")
            return store(rec, src.read_bytes(), row)
    tried = []
    prefix = rec["openalex_id"]
    for source, url, version, license_ in oa_candidates(rec, prefix):
        if url in tried:
            continue
        tried.append(url)
        status, body = fetch_pdf(url)
        time.sleep(1)
        if status == 200 and body[:4] == b"%PDF":
            kind = {"publishedVersion": "full-text-journal", "acceptedVersion": "full-text-accepted"}.get(
                version, "full-text-preprint" if version == "submittedVersion" else "full-text-journal")
            row.update(status=kind, source=source, url=url, http=status, version=version, license=license_)
            return store(rec, body, row)
        row["reason"] += f"{source} HTTP {status}{' non-PDF' if status == 200 else ''}; "
    cand = arxiv_candidate(rec, prefix)
    if cand:
        source, url, version, license_ = cand
        status, body = fetch_pdf(url)
        if status == 200 and body[:4] == b"%PDF":
            row.update(status="full-text-preprint", source=source, url=url, http=status, version=version,
                       license=license_, reason=row["reason"] + "journal version not open; preprint differences unchecked")
            return store(rec, body, row)
        row["reason"] += f"arxiv HTTP {status}; "
    row.update(status="no-access", reason=(row["reason"] or "no open-access location found; ").strip())
    return row


def main():
    top = read_csv(sys.argv[1])
    t0 = {r["openalex_id"]: r for r in read_csv(WORK / "records" / "t0r2b-t0.csv")}
    reuse = {r["doi"].lower(): r for r in read_csv(WORK / "reuse-fulltext-map.csv") if r["reusable"] == "1" and r["doi"]}
    RAW.mkdir(parents=True, exist_ok=True)
    (WORK / "access").mkdir(exist_ok=True)
    state = load_state()
    rows = []
    for b, i in enumerate(range(0, len(top), 10)):
        name = f"access-{b:03d}"
        part = WORK / "access" / f"batch-{b:03d}.csv"
        if batch_done(state, PHASE, name, inputs=[Path(sys.argv[1])]):
            rows += read_csv(part)
            continue
        batch = [dict(r, first_author=t0[r["openalex_id"]].get("first_author", "")) for r in top[i:i + 10]]
        out = [access(r, reuse) for r in batch]
        write_csv(part, out, FIELDS)
        commit_batch(state, PHASE, name, [part], inputs=[Path(sys.argv[1])], count=len(out),
                     full_text=sum(r["status"].startswith("full-text") for r in out))
        rows += out
        print(name, {s: sum(r["status"] == s for r in out) for s in sorted({r["status"] for r in out})}, flush=True)
    write_csv(WORK / "access-ledger.csv", rows, FIELDS)
    counts = {s: sum(r["status"] == s for r in rows) for s in sorted({r["status"] for r in rows})}
    print(json.dumps({"n": len(rows), "status": counts}))


if __name__ == "__main__":
    main()
