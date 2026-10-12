"""Combine screened search + snowball hits, score them and select the top ~100.

score = 0.45*R/3 + 0.20*I + 0.20*N + 0.15*V
  I = percentile of citations/year within eligible papers (R >= 2)
  N = 1 (2024-2026), 0.6 (2022-2023), 0.3 (2020-2021)
  V = percentile of SJR 2025 within eligible papers, halved for q1-weak venues
Selection: every cluster gets its best min(8, available) papers, the rest is filled by score up to TARGET.
"""
import csv
import json
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
TARGET = 100
MIN_PER_CLUSTER = 8
YEAR_NOW = 2026
KEY_TITLES = ["LLM-Enhanced Failure Localization", "multi-agent framework for root cause", "Bayesian Networks",
              "neurosymbolic fusion", "Uncertainty-Aware Multimodal Anomaly", "Separating the Wheat", "UDA-RCL",
              "Topo-MFP", "Graph Autoencoder", "CRFD", "Log-Template Retrieval", "Unstable Logs"]


def decisions(name):
    out = {}
    for line in (WORK / name).read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            continue
        for tok in line.split():
            idx, r, cluster = tok.split(":")
            out[int(idx)] = (int(r), cluster)
    return out


def pct(values):
    ordered = sorted(values)
    n = len(ordered)
    return lambda v: (sum(1 for x in ordered if x <= v) - 1) / (n - 1) if n > 1 else 1.0


def main():
    rows = []
    for csv_name, dec_name, source in [("q1-hits.csv", "screen-decisions.txt", "search"),
                                       ("snowball-q1.csv", "screen-decisions-snowball.txt", "snowball")]:
        dec = decisions(dec_name)
        with open(WORK / csv_name, encoding="utf-8") as f:
            for i, r in enumerate(csv.DictReader(f)):
                r["R"], r["cluster"] = dec.get(i, (0, ""))
                r["source"] = source
                r["exclude_reason"] = {0: "off-topic (title/abstract)", 1: "tangential (R1)"}.get(r["R"], "")
                rows.append(r)
    eligible = [r for r in rows if r["R"] >= 2]
    for r in eligible:
        r["cites_per_year"] = int(r["cited_by"]) / max(1, YEAR_NOW - int(r["year"]) + 1)
    p_i = pct([r["cites_per_year"] for r in eligible])
    p_v = pct([float(r["sjr_2025"]) for r in eligible])
    for r in eligible:
        y = int(r["year"])
        r["I"] = round(p_i(r["cites_per_year"]), 3)
        r["N"] = 1.0 if y >= 2024 else 0.6 if y >= 2022 else 0.3
        r["V"] = round(p_v(float(r["sjr_2025"])) * (0.5 if r["q1_weak"] in (1, "1") else 1), 3)
        r["score"] = round(0.45 * r["R"] / 3 + 0.20 * r["I"] + 0.20 * r["N"] + 0.15 * r["V"], 4)
    eligible.sort(key=lambda r: -r["score"])
    chosen, seen = [], set()
    for cluster in sorted({r["cluster"] for r in eligible}):
        for r in [x for x in eligible if x["cluster"] == cluster][:MIN_PER_CLUSTER]:
            chosen.append(r)
            seen.add(id(r))
    for r in eligible:
        if len(chosen) >= TARGET:
            break
        if id(r) not in seen:
            chosen.append(r)
            seen.add(id(r))
    chosen.sort(key=lambda r: -r["score"])
    for r in eligible:
        if id(r) not in seen:
            r["exclude_reason"] = "eligible, below top-100 cut"
    fields = ["rank", "openalex_id", "doi", "title", "year", "venue", "publisher", "issns", "cluster", "R", "I", "N", "V",
              "score", "cited_by", "sjr_2025", "q1_weak", "cs_category_q1", "source", "oa_url"]
    with open(WORK / "top100.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for n, r in enumerate(chosen, 1):
            w.writerow({**r, "rank": n})
    with open(WORK / "screened.csv", "w", newline="", encoding="utf-8") as f:
        cols = ["openalex_id", "doi", "title", "year", "venue", "source", "R", "cluster", "score", "exclude_reason",
                "abstract"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    clusters = {}
    for r in chosen:
        clusters[r["cluster"]] = clusters.get(r["cluster"], 0) + 1
    titles = [r["title"].lower() for r in chosen]
    key_status = {k: any(k.lower() in t for t in titles) for k in KEY_TITLES}
    counts = json.loads((WORK / "prisma-counts.json").read_text(encoding="utf-8")) \
        if (WORK / "prisma-counts.json").exists() else {}
    counts.update({
        "q1_screened_total": len(rows),
        "r3": sum(1 for r in rows if r["R"] == 3), "r2": sum(1 for r in rows if r["R"] == 2),
        "r1_excluded": sum(1 for r in rows if r["R"] == 1), "r0_excluded": sum(1 for r in rows if r["R"] == 0),
        "eligible_r_ge_2": len(eligible), "top_selected": len(chosen), "top_by_cluster": clusters,
        "top_q1_weak": sum(1 for r in chosen if r["q1_weak"] in (1, "1")),
        "key_papers_in_top": key_status,
    })
    (WORK / "prisma-counts.json").write_text(json.dumps(counts, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(counts, ensure_ascii=False))


if __name__ == "__main__":
    main()
