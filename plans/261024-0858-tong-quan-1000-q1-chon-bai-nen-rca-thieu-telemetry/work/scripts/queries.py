"""Parse the frozen query table (protocol.md §5) and build OpenAlex URLs.

usage: python -X utf8 -I queries.py probe [NAME] [--amend]  -> work/<NAME> (page 1 per query; --amend = §10 synonym table)
       python -X utf8 -I queries.py export  -> work/queries.json
"""
import json
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PLAN, WORK, abstract_from_index, http_json, now_utc, sha_bytes, write_csv  # noqa: E402

BASE_FILTER = "from_publication_date:2020-01-01,primary_location.source.type:journal,type:article|review"


def date_filter():
    """Q-5 upper bound: to_publication_date frozen in work/state.json (absent before freeze)."""
    state_path = WORK / "state.json"
    if state_path.exists():
        upper = json.loads(state_path.read_text(encoding="utf-8")).get("to_publication_date")
        if upper:
            return f"{BASE_FILTER},to_publication_date:{upper}"
    return BASE_FILTER


def load_queries(amend=False):
    """Frozen §5 table, or with amend=True the §10 step-2 synonym table in work/amendments.md (ids S1..)."""
    if amend:
        text = (WORK / "amendments.md").read_text(encoding="utf-8")
        section = text[text.index("## §10 bước 2"):]
        pattern = r"^\| (S\d) \| [^|]+ \| `(.+)` \|$"
    else:
        text = (PLAN / "protocol.md").read_text(encoding="utf-8")
        section = text[text.index("## 5."):text.index("## 6.")]
        pattern = r"^\| ([A-D]\d) \| [^|]+ \| `(.+)` \|$"
    rows = re.findall(pattern, section, re.M)
    return [{"id": qid, "query": query} for qid, query in rows]


def url_for(query, *, per_page=200, cursor=None, select=None, page=None):
    """Cursor paging needs an API key (HTTP 401 without one); basic page= paging covers up to 10,000 results."""
    params = {"filter": f"title_and_abstract.search:{query},{date_filter()}", "per-page": per_page}
    if cursor:
        params["cursor"] = cursor
    if page:
        params["page"] = page
    if select:
        params["select"] = select
    return "https://api.openalex.org/works?" + urllib.parse.urlencode(params, safe=":,|*")


def and_clauses(query):
    """Split a query on top-level AND; return each clause's terms (quoted phrases or bare words, no OR)."""
    clauses, depth, buf = [], 0, ""
    tokens = re.split(r"(\(|\)| AND )", query)
    for tok in tokens:
        if tok == "(":
            depth += 1
        elif tok == ")":
            depth -= 1
        if tok == " AND " and depth == 0:
            clauses.append(buf)
            buf = ""
        else:
            buf += tok
    clauses.append(buf)
    out = []
    for clause in clauses:
        terms = re.findall(r'"([^"]+)"|([A-Za-z][\w-]*)', clause)
        terms = [a or b for a, b in terms if (a or b) not in ("OR", "AND", "NOT")]
        out.append([t.lower() for t in terms])
    return out


def stem(term):
    return term if len(term) <= 4 else term[:max(4, len(term) - 2)]


def clause_coverage(query, works):
    """Share of works with abstract whose title+abstract hits at least one term of every AND clause."""
    clauses = and_clauses(query)
    with_abs = [w for w in works if w.get("abstract_inverted_index")]
    hits = 0
    for w in with_abs:
        text = ((w.get("title") or "") + " " + abstract_from_index(w["abstract_inverted_index"])).lower()
        if all(any(stem(t) in text for t in clause) for clause in clauses):
            hits += 1
    return len(with_abs), hits


def main():
    queries = load_queries(amend="--amend" in sys.argv)
    if sys.argv[1] == "export":
        (WORK / "queries.json").write_text(json.dumps(queries, ensure_ascii=False, indent=1), encoding="utf-8")
        print(len(queries), "queries exported")
        return
    rows = []
    for q in queries:
        url = url_for(q["query"], per_page=200, cursor=None, select="id,title,publication_year,abstract_inverted_index")
        status, raw, data = http_json(url)
        titles = " || ".join((w.get("title") or "")[:90] for w in (data or {}).get("results", [])[:5])
        n_abs, n_hit = clause_coverage(q["query"], (data or {}).get("results", []))
        rows.append({"id": q["id"], "query": q["query"], "http": status,
                     "page1_with_abstract": n_abs, "page1_all_clauses_hit": n_hit,
                     "clause_coverage": round(n_hit / n_abs, 3) if n_abs else "",
                     "count": (data or {}).get("meta", {}).get("count", ""),
                     "error": "" if data else raw[:200].decode("utf-8", "replace"),
                     "top5_titles": titles, "raw_sha256": sha_bytes(raw), "as_of_utc": now_utc()})
        print(q["id"], status, rows[-1]["count"], "coverage", rows[-1]["clause_coverage"])
    args = [a for a in sys.argv[2:] if a != "--amend"]
    name = args[0] if args else "query-probe.csv"
    if (WORK / name).exists():
        raise SystemExit(f"{name} exists; probe outputs are immutable")
    write_csv(WORK / name, rows, list(rows[0]))


if __name__ == "__main__":
    main()
