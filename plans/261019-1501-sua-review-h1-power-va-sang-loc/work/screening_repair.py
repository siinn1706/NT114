"""Rebuild an auditable screening ledger and the record-to-work PRISMA flow (CPU only, no network).

Reads the frozen review workspace (never writes there):
  ../../261019-1045-.../work/{corpus.csv, screening-check.csv, findings.csv, prisma-counts.json}
  ../../261019-1045-.../work/raw/sr1/{search.csv, screen.csv, fulltext.csv}   (Elicit SR1 exports)
Writes to <out_dir>:
  screening.csv                 one row per work: every decision that exists, who made it, and what is missing
  prisma-flow.json              record and work counts kept apart, full-text "not retrieved" separated
  screening-check-supplement.csv  seeded draw that tops the Elicit-excluded check up to 10 % (39 of 390)
  delayed-rescreen-sample.csv   seeded 30 of the 127 checked records, decisions blank, eligible after 24 h

usage: python -I screening_repair.py <out_dir>
"""
import csv
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

REVIEW = Path(__file__).resolve().parents[2] / "261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit" / "work"
SEED = 20261019
CHECK_DONE_AT = "2026-10-19T13:42:33+07:00"     # last write of screening-check.csv
ELIGIBLE_AFTER = "2026-10-20T13:42:33+07:00"    # Phase 03: re-screen >= 24 h later


def rows(p):
    return list(csv.DictReader(open(p, encoding="utf-8-sig")))


def norm(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def doi(d):
    return (d or "").lower().replace("https://doi.org/", "").strip()


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    corpus = rows(REVIEW / "corpus.csv")
    search = rows(REVIEW / "raw" / "sr1" / "search.csv")
    screen = {r["Paper ID"]: r for r in rows(REVIEW / "raw" / "sr1" / "screen.csv")}
    ft = {r["Paper ID"]: r for r in rows(REVIEW / "raw" / "sr1" / "fulltext.csv")}
    check = rows(REVIEW / "screening-check.csv")
    findings = rows(REVIEW / "findings.csv")

    by_title, by_doi = {}, {}
    for c in corpus:
        by_title.setdefault(norm(c["title"]), c["work_id"])
        for d in (c["dois"] or "").split(";"):
            if doi(d):
                by_doi[doi(d)] = c["work_id"]

    def work_of(r):
        return by_doi.get(doi(r.get("DOI"))) or by_title.get(norm(r.get("Title")))

    # ---- SR1 records -> works, decisions per record
    rec = []
    for r in search:
        pid = r["Paper ID"]
        s, f = screen.get(pid, {}), ft.get(pid)
        if f is None:
            ft_status = "not_reached" if s.get("Screening judgement") == "Exclude" else "missing_in_export"
        elif f["Screening judgement"] == "Include":
            ft_status = "included"
        elif f.get("Exclusion reason") == "Full text not available":
            ft_status = "not_retrieved"
        else:
            ft_status = "excluded_content"
        reason = "" if f is None else (f.get("Criteria not met") or f.get("Exclusion reason") or "")
        rec.append({"paper_id": pid, "work_id": work_of(r), "abstract": s.get("Screening judgement", ""),
                    "abstract_unmet": s.get("Criteria not met", ""), "ft_status": ft_status, "ft_reason": reason})
    unmapped = [x for x in rec if not x["work_id"]]

    # ---- per-work ledger
    order = {"included": 4, "excluded_content": 3, "not_retrieved": 2, "not_reached": 1, "missing_in_export": 0}
    per_work = {}
    for x in rec:
        if not x["work_id"]:
            continue
        cur = per_work.get(x["work_id"])
        if cur is None or order[x["ft_status"]] > order[cur["ft_status"]]:
            per_work[x["work_id"]] = x
    chk = {}
    for r in check:
        x = next((y for y in rec if y["paper_id"] == r["paper_id"]), None)
        if x and x["work_id"]:
            chk[x["work_id"]] = r
    hyp = {}
    for f in findings:
        if f.get("work_id"):
            hyp.setdefault(f["work_id"], set()).update(h.strip() for h in re.split(r"[;/,]", f["hypothesis"]) if h.strip())
    rule = re.compile(json.load(open(REVIEW / "prisma-counts.json", encoding="utf-8"))["non_sr1_title_keyword_rule"], re.I)

    ledger = []
    for c in corpus:
        w = c["work_id"]
        x = per_work.get(w)
        in_sr1 = "SR1" in c["sources"].split(";")
        if in_sr1 and x:
            method = "Elicit SR1 (AI screening; 127-record manual agreement check)"
            final = {"included": "included_after_fulltext", "excluded_content": "excluded_fulltext_with_reason",
                     "not_retrieved": "undetermined_fulltext_not_retrieved", "not_reached": "excluded_abstract",
                     "missing_in_export": "undetermined_export_gap"}[x["ft_status"]]
        elif in_sr1:
            method, final = "Elicit SR1", "undetermined_unmapped_record"
        else:
            method = "title keyword rule only (no manual title/abstract decision)"
            final = "candidate_not_manually_screened" if rule.search(c["title"]) else "not_relevant_by_title_rule"
        m = chk.get(w, {})
        ledger.append({
            "work_id": w, "title": c["title"], "year": c["year"], "sources": c["sources"], "n_records": c["n_records"],
            "screening_method": method,
            "elicit_abstract": (x or {}).get("abstract", ""), "elicit_abstract_unmet": (x or {}).get("abstract_unmet", ""),
            "elicit_fulltext_status": (x or {}).get("ft_status", ""), "elicit_fulltext_reason": (x or {}).get("ft_reason", ""),
            "manual_check_decision": m.get("manual_decision", ""), "manual_check_agree": m.get("agree", ""),
            "hypotheses_in_findings": ";".join(sorted(hyp.get(w, []))),
            "relevance_h1_h2_h3": "",  # Phase 03 asked for 0/1/2 per hypothesis per work; never assigned
            "final_status": final,
        })
    with open(out / "screening.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(ledger[0]))
        wr.writeheader()
        wr.writerows(ledger)

    # ---- PRISMA flow: records and works kept apart
    sr1_works = {x["work_id"] for x in rec if x["work_id"]}
    flow = {
        "records_identified_total": json.load(open(REVIEW / "prisma-counts.json", encoding="utf-8"))
        ["records_identified"]["total"],
        "works_after_dedup": len(corpus),
        "sr1": {
            "records": len(rec), "works": len(sr1_works), "within_sr1_duplicate_records": len(rec) - len(sr1_works) - len(unmapped),
            "unmapped_records": len(unmapped),
            "records_abstract": dict(Counter(x["abstract"] for x in rec)),
            "records_fulltext": dict(Counter(x["ft_status"] for x in rec if x["abstract"] == "Include")),
            "records_fulltext_content_reasons": dict(Counter(x["ft_reason"] for x in rec if x["ft_status"] == "excluded_content")),
            "works_final_status": dict(Counter(l["final_status"] for l in ledger if "SR1" in l["sources"].split(";"))),
        },
        "outside_sr1": {
            "works": sum(1 for l in ledger if "SR1" not in l["sources"].split(";")),
            "works_final_status": dict(Counter(l["final_status"] for l in ledger if "SR1" not in l["sources"].split(";"))),
        },
        "manual_title_abstract_decisions": {"works_with_decision": sum(1 for l in ledger if l["manual_check_decision"]),
                                            "relevance_assigned": 0},
        "note": "SR1 records = Elicit export rows (1,267); SR1 works = distinct works after the corpus dedup. "
                "Full-text 'not_retrieved' is Elicit's 'Full text not available', not a content exclusion.",
    }
    (out / "prisma-flow.json").write_text(json.dumps(flow, indent=1, ensure_ascii=False), encoding="utf-8")

    # ---- top the excluded-record check up to 10 % of 390
    excluded = [x for x in rec if x["abstract"] == "Exclude"]
    need = round(0.10 * len(excluded)) - sum(1 for r in check if r["elicit_decision"] == "Exclude")
    done = {r["paper_id"] for r in check}
    pool = [x for x in excluded if x["paper_id"] not in done]
    random.Random(SEED + 1).shuffle(pool)
    sup = out / "screening-check-supplement.csv"
    if not sup.exists():  # once written it holds manual decisions and is never overwritten
        with open(sup, "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(["sample_no", "paper_id", "elicit_decision", "criteria_not_met", "title", "year", "abstract",
                         "manual_decision", "agree", "note"])
            for i, x in enumerate(pool[:max(need, 0)], 1):
                s = screen[x["paper_id"]]
                wr.writerow([i, x["paper_id"], "Exclude", x["abstract_unmet"], s["Title"], s["Year"],
                             (s.get("Abstract") or "")[:1500], "", "", ""])

    # ---- delayed re-screen sample: blind (no earlier decisions), not fillable before ELIGIBLE_AFTER
    smp = list(check)
    random.Random(SEED + 2).shuffle(smp)
    resc = out / "delayed-rescreen-sample.csv"
    if resc.exists():
        print(json.dumps({"need_supplement": need, **flow["sr1"], "outside": flow["outside_sr1"]}, indent=1))
        return
    with open(resc, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["rescreen_no", "paper_id", "title", "year", "first_check_at", "eligible_after",
                     "rescreen_decision", "rescreen_at"])
        for i, r in enumerate(smp[:30], 1):
            wr.writerow([i, r["paper_id"], r["title"], r["year"], CHECK_DONE_AT, ELIGIBLE_AFTER, "", ""])
    print(json.dumps({"need_supplement": need, **flow["sr1"], "outside": flow["outside_sr1"]}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
