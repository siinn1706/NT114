"""Select ~50 papers from top100.csv for full-text reading (phase 03 rules).

Mandatory: the 12 key papers, every R3 paper in clusters B3 and B5, the RAG counter-evidence paper,
and 5 recent surveys. The rest is filled by score with per-cluster caps.
"""
import csv
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
TARGET = 50
KEY = ["LLM-Enhanced Failure Localization", "multi-agent framework for root cause", "Bayesian Networks",
       "neurosymbolic fusion", "Uncertainty-Aware Multimodal Anomaly", "Separating the Wheat", "UDA-RCL",
       "Topo-MFP", "Graph Autoencoder", "CRFD", "Log-Template Retrieval", "Unstable Logs"]
SURVEYS = ["A Survey of AIOps in the Era of Large Language Models", "Intelligent Root Cause Localization in MicroService",
           "Failure Diagnosis in Microservice Systems: A Comprehensive", "agentic NetOps and AIOps",
           "Trustworthy AI-based Performance Diagnosis"]
EXTRA = ["When RAG hurts"]
CAPS = {"B1": 5, "B4": 6, "B6": 2, "SV": 6}


def main():
    rows = list(csv.DictReader(open(WORK / "top100.csv", encoding="utf-8")))
    chosen = {}

    def take(r, why):
        chosen.setdefault(r["openalex_id"], (r, why))

    for r in rows:
        t = r["title"]
        if any(k.lower() in t.lower() for k in KEY):
            take(r, "key paper (05/10 report)")
        elif any(s.lower() in t.lower() for s in SURVEYS):
            take(r, "recent survey for taxonomy")
        elif any(e.lower() in t.lower() for e in EXTRA):
            take(r, "counter-evidence for retrieval")
        elif r["cluster"] in ("B3", "B5") and r["R"] == "3":
            take(r, f"R3 in {r['cluster']} (LLM/RAG for ops)")
    count = {}
    for r, _ in chosen.values():
        count[r["cluster"]] = count.get(r["cluster"], 0) + 1
    for r in rows:
        if len(chosen) >= TARGET:
            break
        if r["openalex_id"] in chosen:
            continue
        cap = CAPS.get(r["cluster"])
        if cap is not None and count.get(r["cluster"], 0) >= cap:
            continue
        take(r, "by score within cluster cap")
        count[r["cluster"]] = count.get(r["cluster"], 0) + 1
    out = sorted(chosen.values(), key=lambda x: int(x[0]["rank"]))
    with open(WORK / "read50.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["read_id", "rank", "openalex_id", "doi", "cluster", "R", "year", "venue", "title", "why", "oa_url"])
        for n, (r, why) in enumerate(out, 1):
            w.writerow([f"P{n:02d}", r["rank"], r["openalex_id"], r["doi"], r["cluster"], r["R"], r["year"],
                        r["venue"], r["title"], why, r["oa_url"]])
    by = {}
    for r, _ in out:
        by[r["cluster"]] = by.get(r["cluster"], 0) + 1
    print(len(out), by, "with oa_url:", sum(1 for r, _ in out if r["oa_url"]))


if __name__ == "__main__":
    main()
