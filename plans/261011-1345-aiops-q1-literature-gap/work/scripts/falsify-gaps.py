"""Run targeted falsification queries for each candidate gap: OpenAlex journals (marked Q1 by SJR 2025) and arXiv 2024-2026.

Writes falsification-log.csv (one row per query) and falsification-hits.csv (top hits with Q1 flag) for manual reading.
Raw responses are cached under raw/falsify/ so reruns cost no API credits.
Usage: python -X utf8 falsify-gaps.py
"""
import os
import csv
import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
RAW = WORK / "raw" / "falsify"
MAILTO = os.environ.get("NCKH_MAILTO", "")
NS = {"a": "http://www.w3.org/2005/Atom"}
LLM = '("large language model" OR "large language models" OR "LLM" OR "LLMs")'
MS = '("microservice" OR "microservices" OR "cloud-native" OR "cloud native")'
RC = '("root cause" OR "fault localization" OR "failure localization" OR "failure diagnosis")'
# gap id, OpenAlex boolean (title+abstract), arXiv query
QUERIES = [
    ("G1", f"{LLM} AND {RC} AND {MS}", 'abs:"root cause" AND abs:microservice AND abs:"language model"'),
    ("G2", f'{RC} AND ("retrieval-augmented" OR "retrieval augmented" OR "hybrid retrieval" OR "BM25" OR "dense retrieval") AND ({MS[1:-1]} OR "incident" OR "AIOps")',
     'abs:"root cause" AND abs:retrieval AND (abs:microservice OR abs:incident)'),
    ("G3", f'{RC} AND {LLM} AND ("calibration" OR "calibrated" OR "uncertainty" OR "confidence estimation" OR "abstain" OR "selective prediction")',
     'abs:"root cause" AND abs:"language model" AND (abs:calibration OR abs:uncertainty OR abs:confidence)'),
    ("G4", f'({RC[1:-1]} OR "AIOps" OR "incident") AND {LLM} AND ("token budget" OR "context window" OR "token cost" OR "telemetry compression" OR "context compression")',
     '(abs:"root cause" OR abs:AIOps OR abs:incident) AND abs:"language model" AND (abs:token OR abs:"context window" OR abs:compression)'),
    ("G5", f'{RC} AND {LLM} AND ("fault propagation" OR "failure propagation" OR "propagation path" OR "call graph")',
     'abs:"root cause" AND abs:"language model" AND abs:propagation'),
    ("G6", f'{RC} AND {MS} AND ("domain adaptation" OR "transfer learning" OR "cross-system" OR "unseen system" OR "generalization across")',
     'abs:"root cause" AND abs:microservice AND (abs:transfer OR abs:"domain adaptation" OR abs:"cross-system")'),
    ("G7", f'{RC} AND {LLM} AND ("explanation quality" OR "faithfulness" OR "human evaluation" OR "evidence correctness" OR "interpretability evaluation")',
     'abs:"root cause" AND abs:"language model" AND (abs:faithfulness OR abs:"human evaluation" OR abs:explanation)'),
    ("G8", f'{RC} AND ("Kubernetes") AND ("fault injection" OR "chaos engineering" OR "Chaos Mesh")',
     'abs:"root cause" AND abs:Kubernetes AND (abs:"fault injection" OR abs:chaos)'),
    ("N1", f'{RC} AND {MS} AND ("missing data" OR "incomplete" OR "partial observability" OR "missing modality" OR "uninstrumented")',
     'abs:"root cause" AND abs:microservice AND (abs:missing OR abs:incomplete OR abs:"partial observability")'),
    ("N2", f'("adaptive retrieval" OR "selective retrieval" OR "retrieval gating" OR "when to retrieve" OR "confidence-gated") AND ({RC[1:-1]} OR "AIOps" OR "incident" OR "log analysis")',
     '(abs:"adaptive retrieval" OR abs:"selective retrieval" OR abs:"when to retrieve") AND (abs:"root cause" OR abs:incident OR abs:AIOps)'),
    ("N3", f'("small language model" OR "model cascade" OR "LLM cascade" OR "model routing") AND ({RC[1:-1]} OR "AIOps" OR "incident management")',
     '(abs:"small language model" OR abs:cascade OR abs:routing) AND (abs:"root cause" OR abs:AIOps)'),
]


def q1_issns():
    out = {}
    for r in csv.DictReader(open(WORK / "scimagojr-2025-nckh.csv", encoding="utf-8"), delimiter=";"):
        if r["SJR Best Quartile"] == "Q1":
            for i in r["Issn"].replace(" ", "").split(","):
                if i:
                    out[i.upper()] = r["Title"]
    return out


def get(url, path):
    if path.exists():
        return path.read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": f"nckh-survey (mailto:{MAILTO})"})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read()
    path.write_bytes(data)
    time.sleep(3)
    return data


def openalex(gid, boolean):
    flt = ("type:article|review,primary_location.source.type:journal,from_publication_date:2020-01-01,"
           f"title_and_abstract.search:{boolean}")
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode({
        "filter": flt, "per-page": 50, "sort": "relevance_score:desc", "mailto": MAILTO,
        "select": "id,doi,title,publication_year,primary_location"})
    d = json.loads(get(url, RAW / f"{gid}-openalex.json"))
    return d["meta"]["count"], d["results"]


def arxiv(gid, q):
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode({
        "search_query": f"({q}) AND submittedDate:[202401010000 TO 202612312359]",
        "max_results": 25, "sortBy": "relevance"})
    root = ET.fromstring(get(url, RAW / f"{gid}-arxiv.xml"))
    total = int(root.find("{http://a9.com/-/spec/opensearch/1.1/}totalResults").text)
    hits = [(e.find("a:id", NS).text.rsplit("/abs/", 1)[-1], " ".join(e.find("a:title", NS).text.split()),
             e.find("a:published", NS).text[:4]) for e in root.findall("a:entry", NS)]
    return total, hits


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    q1 = q1_issns()
    today = date.today().isoformat()
    log, hits = [], []
    for gid, boolean, aq in QUERIES:
        n, res = openalex(gid, boolean)
        nq1 = 0
        for r in res:
            src = (r.get("primary_location") or {}).get("source") or {}
            issns = [i.replace("-", "").upper() for i in (src.get("issn") or [])]
            is_q1 = any(i in q1 for i in issns)
            nq1 += is_q1
            hits.append([gid, "openalex", r["id"].rsplit("/", 1)[-1], r.get("doi") or "", r.get("publication_year"),
                         src.get("display_name", ""), "Q1" if is_q1 else "", r.get("title") or ""])
        log.append([gid, "openalex journals 2020-2026", boolean, today, n, f"{nq1} Q1 in top {len(res)}"])
        an, ah = arxiv(gid, aq)
        for aid, t, y in ah:
            hits.append([gid, "arxiv", aid, "", y, "arXiv", "", t])
        log.append([gid, "arxiv 2024-2026", aq, today, an, f"top {len(ah)} saved"])
        print(gid, "openalex", n, "q1top", nq1, "| arxiv", an, flush=True)
    with open(WORK / "falsification-log.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["gap_id", "source", "query", "date", "n_results", "note"])
        w.writerows(log)
    with open(WORK / "falsification-hits.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["gap_id", "source", "id", "doi", "year", "venue", "q1", "title"])
        w.writerows(hits)


if __name__ == "__main__":
    main()
