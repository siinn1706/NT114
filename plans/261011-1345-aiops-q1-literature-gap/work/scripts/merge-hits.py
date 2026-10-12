"""Merge cached OpenAlex pages into a hits CSV, deduplicated by DOI then normalized title.

Usage: merge-hits.py [glob] [output] [--exclude existing.csv]; default Q*-p*.json -> raw-hits.csv.
"""
import csv
import sys
import json
import re
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]


def abstract(inv):
    if not inv:
        return ""
    pos = sorted((i, w) for w, idx in inv.items() for i in idx)
    return " ".join(w for _, w in pos)


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pattern = args[0] if args else "Q*-p*.json"
    out_name = args[1] if len(args) > 1 else "raw-hits.csv"
    exclude = set()
    if "--exclude" in sys.argv:
        with open(WORK / sys.argv[sys.argv.index("--exclude") + 1], encoding="utf-8") as f:
            for r in csv.DictReader(f):
                exclude.add(r["doi"] or norm_title(r["title"]))
    rows, by_key, raw_count = [], {}, 0
    for path in sorted((WORK / "raw").glob(pattern)):
        qid = path.stem.rsplit("-p", 1)[0] if path.name.startswith("Q") else path.stem
        for w in json.loads(path.read_text(encoding="utf-8"))["results"]:
            raw_count += 1
            doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
            key = doi or norm_title(w.get("title"))
            if key in exclude:
                continue
            if key in by_key:
                by_key[key]["queries"].add(qid)
                continue
            src = ((w.get("primary_location") or {}).get("source") or {})
            rec = {
                "openalex_id": w["id"].rsplit("/", 1)[-1], "doi": doi, "title": w.get("title") or "",
                "year": w.get("publication_year"), "type": w.get("type"),
                "venue": src.get("display_name") or "", "issn_l": src.get("issn_l") or "",
                "issns": "|".join(src.get("issn") or []), "publisher": src.get("host_organization_name") or "",
                "cited_by": w.get("cited_by_count") or 0,
                "oa_url": (w.get("open_access") or {}).get("oa_url") or "",
                "abstract": abstract(w.get("abstract_inverted_index")), "queries": {qid},
            }
            by_key[key] = rec
            rows.append(rec)
    fields = list(rows[0].keys())
    with open(WORK / out_name, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=fields)
        wr.writeheader()
        for r in rows:
            wr.writerow({**r, "queries": "|".join(sorted(r["queries"]))})
    issns = sorted({i for r in rows for i in r["issns"].split("|") if i})
    (WORK / out_name.replace(".csv", "-issns.txt")).write_text("\n".join(issns), encoding="utf-8")
    print(json.dumps({"raw_records": raw_count, "unique": len(rows), "unique_issns": len(issns),
                      "no_issn": sum(1 for r in rows if not r["issns"])}))


if __name__ == "__main__":
    main()
