"""Look up arXiv preprints for papers that still lack a full text, using a looser title match.

Match = token Jaccard >= 0.75 between normalised titles (stop words removed). Prints read_id, score, arXiv id, title.
Usage: python -X utf8 find-arxiv-versions.py P14 P15 ...
"""
import csv
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
STOP = {"a", "an", "the", "for", "of", "in", "on", "with", "and", "via", "using", "to", "by", "from", "based"}
NS = {"a": "http://www.w3.org/2005/Atom"}


def toks(t):
    return {w for w in re.sub(r"[^a-z0-9]+", " ", t.lower()).split() if w not in STOP}


def search(title):
    best = (0.0, "", "")
    for n in (6, 4, 3):
        best = max(best, search_n(title, n))
        if best[0] >= 0.75:
            break
        time.sleep(3)
    return best


def search_n(title, n):
    words = sorted(toks(title), key=len, reverse=True)[:n]
    q = " AND ".join(f"ti:{w}" for w in words)
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode({"search_query": q, "max_results": 10})
    with urllib.request.urlopen(url, timeout=60) as r:
        root = ET.fromstring(r.read())
    best = (0.0, "", "")
    for e in root.findall("a:entry", NS):
        t = " ".join((e.find("a:title", NS).text or "").split())
        a, b = toks(title), toks(t)
        score = len(a & b) / max(1, len(a | b))
        if score > best[0]:
            best = (score, e.find("a:id", NS).text.rsplit("/abs/", 1)[-1], t)
    return best


def main():
    want = set(sys.argv[1:])
    for r in csv.DictReader(open(WORK / "read50.csv", encoding="utf-8")):
        if r["read_id"] not in want:
            continue
        try:
            score, aid, t = search(r["title"])
        except Exception as e:  # keep going on API errors
            score, aid, t = 0.0, "", f"error {e}"
        flag = "MATCH" if score >= 0.75 else "no"
        print(f"{r['read_id']}\t{flag}\t{score:.2f}\t{aid}\t{t[:80]}", flush=True)
        time.sleep(3)


if __name__ == "__main__":
    main()
