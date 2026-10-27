"""Phase 04: merge seed + search (+ snowball) records, deduplicate, apply Q-1..Q-9 and the §4 topic gate.

usage: python -X utf8 -I build-t0.py OUT_TAG RECORD_CSV [RECORD_CSV ...]
Writes work/records/<OUT_TAG>-candidates.csv, <OUT_TAG>-excluded.csv, <OUT_TAG>-dedup-groups.csv,
<OUT_TAG>-fuzzy-review.csv and <OUT_TAG>-summary.json. Deterministic for the same inputs.
"""
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RECORD_FIELDS, WORK, load_sjr, load_state, norm_issn, read_csv, sha_file, topic_ok, write_csv  # noqa: E402

Q1_WEAK = {"21693536", "20452322"}
TO_DATE = load_state().get("to_publication_date", "")
EXTRA = ["origins", "n_origins", "sjr_title", "sjr_type", "sjr_best", "sjr_cs_q1", "sjr_cs_categories",
         "q1_weak", "q1_rule_trace", "dup_group", "topic_gate", "exclude_reason"]


def norm_title(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def merge(records):
    """Several rows of one OpenAlex work -> one row: newest metadata, longest abstract, all origins."""
    records = sorted(records, key=lambda r: (r["retrieved_at_utc"], r["origin"]))
    best = dict(records[-1])
    longest = max(records, key=lambda r: (len(r["abstract"]), r["abstract"]))
    best["abstract"], best["abstract_source"] = longest["abstract"], longest["abstract_source"]
    origins = sorted({r["origin"] for r in records})
    best["origins"], best["n_origins"] = "|".join(origins), len(origins)
    return best


def issns_of(rec):
    return [norm_issn(x) for x in rec["issns"].split("|") + [rec["issn_l"]] if x]


def gate(rec, sjr):
    trace, reasons = [], []
    entry = next((sjr[i] for i in issns_of(rec) if i in sjr), None)
    trace.append("Q-3:" + ("match" if entry else "no-issn-match"))
    if not entry:
        reasons.append("Q-3-no-sjr-issn")
    else:
        rec.update(sjr_title=entry["title"], sjr_type=entry["type"], sjr_best=entry["best"],
                   sjr_cs_q1=entry["cs_q1"], sjr_cs_categories=entry["cs_cats"])
        trace.append(f"Q-2:{entry['type']}")
        if entry["type"] != "journal":
            reasons.append("Q-2-not-journal")
        trace.append(f"Q-4:cs_q1={entry['cs_q1']},best={entry['best']}")
        if not entry["cs_q1"]:
            reasons.append("Q-4-q1-noncs" if entry["best"] == "Q1" else "Q-4-not-q1")
    if not rec["publication_date"] or rec["publication_date"] < "2020-01-01":
        reasons.append("Q-5-before-2020")
    elif TO_DATE and rec["publication_date"] > TO_DATE:
        reasons.append("Q-5-after-cutoff")
    if rec["type"] not in ("article", "review"):
        reasons.append(f"Q-6-type-{rec['type'] or 'unknown'}")
    publisher = f"{rec['publisher']} {entry['publisher'] if entry else ''}"
    if re.search(r"MDPI|Multidisciplinary Digital Publishing", publisher, re.I):
        reasons.append("Q-7-mdpi")
    rec["q1_weak"] = int(any(i in Q1_WEAK for i in issns_of(rec)))
    if str(rec["is_retracted"]) == "1":
        reasons.append("Q-8-retracted")
    if rec["language"] and rec["language"] != "en":
        reasons.append(f"Q-9-lang-{rec['language']}")
    elif not rec["language"]:
        title = rec["title"] or ""
        ascii_share = sum(c.isascii() for c in title) / max(1, len(title))
        trace.append(f"Q-9:lang-empty,ascii={ascii_share:.2f}")
        if ascii_share < 0.9:
            reasons.append("Q-9-lang-unknown-nonascii")
    rec["topic_gate"] = int(topic_ok(rec["title"], rec["abstract"]))
    if not rec["topic_gate"]:
        reasons.append("T-off-topic-metadata")
    rec["q1_rule_trace"] = ";".join(trace)
    rec["exclude_reason"] = "|".join(reasons)
    return not reasons


def origin_kind(origin):
    parts = origin.split(":")
    return ":".join(parts[:2]) if parts[0] == "search" else parts[0]


def main():
    tag, inputs = sys.argv[1], [Path(p) for p in sys.argv[2:]]
    sjr = load_sjr()
    by_id, no_id = defaultdict(list), []
    for path in inputs:
        for rec in read_csv(path):
            (by_id[rec["openalex_id"]] if rec["openalex_id"] else no_id).append(rec)
    merged = [merge(v) for _, v in sorted(by_id.items())]
    by_doi = defaultdict(list)
    for rec in merged:
        rec["dup_group"] = ""
        if rec["doi"]:
            by_doi[rec["doi"]].append(rec)
    groups = []
    for doi, recs in sorted(by_doi.items()):
        if len(recs) > 1:
            for r in recs:
                r["dup_group"] = f"doi:{doi}"
            groups.append({"group": f"doi:{doi}", "openalex_ids": "|".join(r["openalex_id"] for r in recs)})
    kept, excluded, review, seen_doi = [], [], [], set()
    for rec in merged:
        ok = gate(rec, sjr)
        if not ok and rec["exclude_reason"] == "T-off-topic-metadata" and not rec["abstract"]:
            # Protocol §4: title-only records that fail the topic gate are reviewed, not excluded outright.
            rec["exclude_reason"] = "T-needs-review-title-only"
            review.append(rec)
            continue
        if ok and rec["doi"] and rec["doi"] in seen_doi:
            rec["exclude_reason"] = "D-duplicate-doi"
            ok = False
        if ok:
            if rec["doi"]:
                seen_doi.add(rec["doi"])
            kept.append(rec)
        else:
            excluded.append(rec)
    by_title = defaultdict(list)
    for rec in kept:
        by_title[norm_title(rec["title"])].append(rec)
    fuzzy = [{"title_norm": t, "openalex_ids": "|".join(r["openalex_id"] for r in rs),
              "dois": "|".join(r["doi"] for r in rs), "years": "|".join(str(r["year"]) for r in rs)}
             for t, rs in sorted(by_title.items()) if len(rs) > 1]
    fields = RECORD_FIELDS + EXTRA
    out = WORK / "records"
    write_csv(out / f"{tag}-candidates.csv", kept, fields)
    write_csv(out / f"{tag}-excluded.csv", excluded, fields)
    write_csv(out / f"{tag}-needs-review-t0.csv", review, fields)
    write_csv(out / f"{tag}-dedup-groups.csv", groups, ["group", "openalex_ids"])
    write_csv(out / f"{tag}-fuzzy-review.csv", fuzzy, ["title_norm", "openalex_ids", "dois", "years"])
    reasons = Counter(r for rec in excluded for r in rec["exclude_reason"].split("|"))
    kinds = Counter(origin_kind(o) for rec in kept for o in rec["origins"].split("|"))
    summary = {"inputs": [{"path": str(p).replace("\\", "/"), "sha256": sha_file(p)} for p in inputs],
               "rows_without_openalex_id": len(no_id), "unique_works": len(merged), "kept": len(kept),
               "excluded": len(excluded), "needs_review_t0": len(review), "exclude_reasons_multi": dict(reasons.most_common()),
               "doi_groups": len(groups), "fuzzy_title_groups": len(fuzzy),
               "kept_with_abstract": sum(1 for r in kept if r["abstract"]),
               "kept_q1_weak": sum(int(r["q1_weak"]) for r in kept), "kept_by_origin": dict(kinds.most_common())}
    (out / f"{tag}-summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "inputs"}, indent=1))


if __name__ == "__main__":
    main()
