"""Build read-final.csv: the planned 50 papers plus replacements, with the reading level actually reached.

read_level: full-text (has an extraction record), abstract-only (no full text found; user accepted abstract level),
dropped (replacement candidate that could not be read or was off-topic). Also writes reading counts into prisma-counts.json.
Usage: python -X utf8 build-read-final.py
"""
import csv
import json
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
IEEE_SKIPPED = {"P23", "P25", "P46", "P47", "P48"}
REPLACEMENTS = {  # id: (doi, cluster, reason)
    "P51": ("10.14778/3797919.3797937", "B3", "replacement: B3 lacked full text"),
    "P53": ("10.1016/j.future.2025.108185", "B3", "replacement: B3 lacked full text"),
    "P55": ("10.1145/3797910", "B3", "replacement: B3 lacked full text"),
    "P56": ("10.1145/3674726", "B2", "replacement for B2 paper without full text"),
    "P57": ("10.1145/3734868", "B2", "replacement for B2 paper without full text"),
    "P58": ("10.1186/s13677-024-00666-0", "B2", "replacement for B2 paper without full text"),
    "P59": ("10.1145/3392149", "B2", "replacement for B2 paper without full text"),
    "P62": ("10.1186/s13677-025-00766-5", "B1", "replacement for B1 paper without full text"),
    "P63": ("10.1145/3801729", "B1", "replacement for B1 paper without full text"),
    "P64": ("10.1145/3702978", "B1", "replacement for B1 paper without full text"),
    "P65": ("10.1186/s13677-022-00296-4", "B1", "replacement for B1 paper without full text"),
    "P66": ("10.1007/s40747-024-01659-x", "B1", "replacement for B1 paper without full text"),
    "P67": ("10.1145/3749840", "B4", "replacement for B4 paper without full text"),
    "P68": ("10.1145/3801747", "B4", "replacement for B4 paper without full text"),
    "P69": ("10.1145/3830238", "B5", "replacement for B5 paper without full text"),
    "P70": ("10.37965/jdmd.2026.1505", "B5", "replacement for B5 paper without full text"),
    "P71": ("10.1145/3700436", "B6", "replacement for B6 paper without full text"),
    "P73": ("10.1016/j.mlwa.2024.100570", "B3", "replacement: B3 lacked full text"),
    "P74": ("10.1016/j.iswa.2025.200608", "SV", "extra recent Q1 survey (rank 14)"),
}
DROPPED = {
    "P52": "B3 candidate; repository connection failed",
    "P54": "candidate; not accessible at the time",
    "P60": "candidate; dynamic repository page",
    "P61": "candidate; dynamic repository page",
    "P72": "B5 candidate; early-access page shows abstract only, education domain",
}


def titles():
    out = {}
    for name in ("screened.csv", "top100.csv"):
        for r in csv.DictReader(open(WORK / name, encoding="utf-8")):
            out.setdefault(r["doi"].lower(), (r["title"], r.get("year", ""), r.get("venue", "")))
    return out


def main():
    ext = {json.loads(x)["id"]: json.loads(x) for x in (WORK / "extraction.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()}
    t = titles()
    rows = []
    for r in csv.DictReader(open(WORK / "read50.csv", encoding="utf-8")):
        rid = r["read_id"]
        if rid in ext:
            level = "full-text"
        elif rid in IEEE_SKIPPED:
            level = "abstract-only (IEEE skipped by user decision)"
        else:
            level = "abstract-only (no accessible full text)"
        rows.append([rid, r["doi"], r["cluster"], r["year"], r["venue"], r["title"], "planned: " + r["why"], level,
                     ext[rid]["read_level"] if rid in ext else ""])
    for rid, (doi, cl, why) in REPLACEMENTS.items():
        title, year, venue = t.get(doi.lower(), ("", "", ""))
        e = ext.get(rid)
        rows.append([rid, doi, cl, e["year"] if e else year, e["venue"] if e else venue, title, why,
                     "full-text" if e else "missing extraction", e["read_level"] if e else ""])
    for rid, why in DROPPED.items():
        rows.append([rid, "", "", "", "", "", why, "dropped", ""])
    with open(WORK / "read-final.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["read_id", "doi", "cluster", "year", "venue", "title", "why", "read_level", "sections_read"])
        w.writerows(rows)
    counts = {
        "planned": 50,
        "full_text_planned": sum(1 for x in rows if x[0] <= "P50" and x[7] == "full-text"),
        "full_text_replacements": sum(1 for x in rows if x[0] > "P50" and x[7] == "full-text"),
        "full_text_total": sum(1 for x in rows if x[7] == "full-text"),
        "abstract_only": sum(1 for x in rows if x[7].startswith("abstract-only")),
        "abstract_only_ieee_skipped": sum(1 for x in rows if "IEEE" in x[7]),
        "dropped_candidates": sum(1 for x in rows if x[7] == "dropped"),
        "extraction_records": len(ext),
    }
    p = WORK / "prisma-counts.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["phase03_reading"] = counts
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(counts))
    missing = [x[0] for x in rows if x[7] == "missing extraction"]
    print("missing extraction:", missing)


if __name__ == "__main__":
    main()
