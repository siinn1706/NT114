"""Phase 06, second pass: publisher PDF endpoints for no-access records that OpenAlex marks open access.

usage: python -X utf8 -I fulltext-publisher-oa.py LEDGER_IN LEDGER_OUT
Only records with open_access.is_oa = true in the stored OpenAlex response are tried, so no paywalled copy is fetched.
Endpoints by DOI prefix: IEEE stamp PDF (arnumber from the doi.org redirect), ACM /doi/pdf/, Springer /content/pdf/.
Elsevier (10.1016) is skipped: ScienceDirect serves a CAPTCHA, which is not bypassed. One attempt per URL.
"""
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import UA, WORK, now_utc, read_csv, write_csv  # noqa: E402

import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("fa", Path(__file__).with_name("fulltext-access.py"))
fa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fa)


def final_url(url):
    request = urllib.request.Request(url, headers={"User-Agent": UA}, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.geturl()
    except urllib.error.HTTPError as error:
        return error.geturl() or ""
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return ""


def endpoints(doi):
    if doi.startswith("10.1109/"):
        landing = final_url(f"https://doi.org/{doi}")
        m = re.search(r"/document/(\d+)", landing)
        return [("ieee-stamp", f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={m.group(1)}")] if m else []
    if doi.startswith("10.1145/") or doi.startswith("10.14778/"):
        return [("acm", f"https://dl.acm.org/doi/pdf/{doi}")] if doi.startswith("10.1145/") else []
    if doi.startswith(("10.1007/", "10.1186/")):
        return [("springer", f"https://link.springer.com/content/pdf/{doi}.pdf")]
    return []


def main():
    rows = read_csv(sys.argv[1])
    t0 = {r["openalex_id"]: r for r in read_csv(WORK / "records" / "t0r2b-t0.csv")}
    tried = 0
    for row in rows:
        if row["status"] != "no-access" or not row["doi"]:
            continue
        work = json.loads((fa.RAW / f"{row['openalex_id']}-openalex.json").read_text(encoding="utf-8"))
        oa = work.get("open_access") or {}
        if not oa.get("is_oa"):
            continue
        best = work.get("best_oa_location") or {}
        for source, url in endpoints(row["doi"]):
            tried += 1
            status, body = fa.fetch_pdf(url)
            time.sleep(2)
            if status == 200 and body[:4] == b"%PDF":
                row.update(status="full-text-journal" if best.get("version") != "submittedVersion" else "full-text-preprint",
                           source=f"publisher-oa:{source}", url=url, http=status, version=best.get("version") or "",
                           license=best.get("license") or oa.get("oa_status", ""), as_of_utc=now_utc(),
                           reason=row["reason"] + f"publisher OA ({oa.get('oa_status')}) endpoint")
                fa.store(dict(t0[row["openalex_id"]], rank=row["rank"]), body, row)
                break
            row["reason"] += f"publisher-oa:{source} HTTP {status}{' non-PDF' if status == 200 else ''}; "
    write_csv(sys.argv[2], rows, fa.FIELDS)
    print(json.dumps({"tried": tried, "status": {s: sum(r["status"] == s for r in rows) for s in sorted({r["status"] for r in rows})}}))


if __name__ == "__main__":
    main()
