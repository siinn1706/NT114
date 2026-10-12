"""Build IEEE-style references for every paper actually read, and verify each DOI against Crossref.

For each non-dropped row in read-final.csv: fetch Crossref metadata (cached under raw/crossref/), check that the DOI
resolves, that the Crossref title matches the recorded title, and that one of the journal ISSNs is Q1 in SJR 2025.
Writes references.csv (read_id, read_level, ieee, doi_ok, title_ratio, sjr_quartile, sjr_title).
Usage: python -X utf8 build-references.py
"""
import os
import csv
import difflib
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
RAW = WORK / "raw" / "crossref"
MAILTO = os.environ.get("NCKH_MAILTO", "")


def sjr():
    out = {}
    for r in csv.DictReader(open(WORK / "scimagojr-2025-nckh.csv", encoding="utf-8"), delimiter=";"):
        for i in r["Issn"].replace(" ", "").split(","):
            if i:
                out[i.upper()] = (r["SJR Best Quartile"], r["Title"])
    return out


def crossref(doi):
    path = RAW / (re.sub(r"[^A-Za-z0-9._-]", "_", doi) + ".json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi) + f"?mailto={MAILTO}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": f"nckh-survey (mailto:{MAILTO})"}), timeout=60) as r:
            data = json.loads(r.read())["message"]
    except urllib.error.HTTPError as e:
        data = {"error": e.code}
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    time.sleep(1)
    return data


def norm(t):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"<[^>]+>", "", t or "").lower())


def ieee(m, doi):
    names = []
    for a in m.get("author", [])[:6]:
        given = " ".join(p[0] + "." for p in re.split(r"[\s-]+", a.get("given", "")) if p)
        names.append(f"{given} {a.get('family', '')}".strip() if given else a.get("name", a.get("family", "")))
    if len(m.get("author", [])) > 6:
        authors = names[0] + " et al."
    elif len(names) == 2:
        authors = names[0] + " and " + names[1]
    elif len(names) > 2:
        authors = ", ".join(names[:-1]) + ", and " + names[-1]
    else:
        authors = names[0] if names else ""
    title = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", (m.get("title") or [""])[0])).strip())
    venue = html.unescape((m.get("container-title") or [""])[0])
    parts = [f"{authors}, “{title},” *{venue}*"]
    if m.get("volume"):
        parts.append(f"vol. {m['volume']}")
    if m.get("issue"):
        parts.append(f"no. {m['issue']}")
    if m.get("page"):
        parts.append(f"pp. {m['page']}" if "-" in m["page"] else f"Art. no. {m['page']}")
    elif m.get("article-number"):
        parts.append(f"Art. no. {m['article-number']}")
    year = (m.get("published") or m.get("issued") or {}).get("date-parts", [[None]])[0][0]
    parts.append(str(year))
    return ", ".join(parts) + f", doi: {doi}."


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    q = sjr()
    rows = []
    for r in csv.DictReader(open(WORK / "read-final.csv", encoding="utf-8")):
        if r["read_level"] == "dropped" or not r["doi"]:
            continue
        m = crossref(r["doi"])
        ok = "error" not in m
        ratio = difflib.SequenceMatcher(None, norm(r["title"]), norm((m.get("title") or [""])[0])).ratio() if ok else 0
        issns = [i.replace("-", "").upper() for i in m.get("ISSN", [])] if ok else []
        quart = next((q[i] for i in issns if i in q), ("not-found", ""))
        rows.append([r["read_id"], "full-text" if r["read_level"] == "full-text" else "abstract-only",
                     ieee(m, r["doi"]) if ok else f"DOI not resolved: {r['doi']}", int(ok), round(ratio, 3), quart[0], quart[1]])
    with open(WORK / "references.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["read_id", "read_level", "ieee", "doi_ok", "title_ratio", "sjr_quartile", "sjr_title"])
        w.writerows(rows)
    print("refs", len(rows), "doi_fail", [x[0] for x in rows if not x[3]],
          "title<0.85", [(x[0], x[4]) for x in rows if x[3] and x[4] < 0.85],
          "not_q1", [(x[0], x[5]) for x in rows if x[5] != "Q1"])


if __name__ == "__main__":
    main()
