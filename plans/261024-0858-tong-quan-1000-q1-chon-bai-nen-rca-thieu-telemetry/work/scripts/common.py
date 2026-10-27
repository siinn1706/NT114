"""Shared helpers: paths, hashing, HTTP with retry, SJR lookup, state checkpoint."""
import csv
import datetime as dt
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PLAN = Path(__file__).resolve().parents[2]
WORK = PLAN / "work"
SJR_CSV = PLAN.parent / "261011-1345-aiops-q1-literature-gap" / "work" / "scimagojr-2025-nckh.csv"
SJR_SHA = "6f20399957173a13e3c1729a5fb3b5821844ba75e8d640c8b3040ab19a6f7180"
SEED = 20261024
UA = "nt114-literature-review/1.0 (research; contact via repository owner)"
CS_CATEGORIES = [
    "Artificial Intelligence", "Computer Networks and Communications", "Software", "Information Systems",
    "Computer Science Applications", "Hardware and Architecture", "Computational Theory and Mathematics",
    "Computer Science (miscellaneous)", "Computer Vision and Pattern Recognition", "Human-Computer Interaction",
    "Signal Processing", "Theoretical Computer Science", "Computer Graphics and Computer-Aided Design",
]
SYSTEM_RE = re.compile(r"microservice|cloud|cloud-native|online service|web service|distributed system|data ?center|"
                       r"software system|IT operation|AIOps|kubernetes|container|serverless|large-scale system|"
                       r"service system|\blogs?\b|log-based|log analysis|intelligent operation|"
                       r"operation and maintenance|\bO&M\b|IT service|\bdatabases?\b|\bDBMS\b|\bAI systems?\b", re.I)
TASK_RE = re.compile(r"root.?cause|fault|failure|incident|anomal|diagnos|outage|trouble|alert|locali[sz]|triage|"
                     r"degradation", re.I)


STRONG_RE = re.compile(r"root.?cause (analysis|locali[sz]ation|diagnosis|identification)|fault locali[sz]ation|"
                       r"failure (diagnosis|locali[sz]ation)|incident management|AIOps|log pars|log anomaly|"
                       r"log analysis", re.I)


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    return sha_bytes(Path(path).read_bytes())


def now_utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _with_key(url):
    """Append OPENALEX_API_KEY from the environment to OpenAlex requests only; callers log the keyless url."""
    key = os.environ.get("OPENALEX_API_KEY", "")
    if not key or not url.startswith("https://api.openalex.org/"):
        return url
    return url + ("&" if "?" in url else "?") + urllib.parse.urlencode({"api_key": key})


def http_get(url, *, retries=6, timeout=60):
    """Return (status, bytes). Retries 429/5xx/network errors with backoff; 4xx other than 429 return at once."""
    delay = 2.0
    last = None
    sent = _with_key(url)
    for _ in range(retries):
        request = urllib.request.Request(sent, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            last = (error.code, error.read() or b"")
            if error.code != 429 and error.code < 500:
                return last
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            last = (0, str(error).encode())
        time.sleep(delay)
        delay = min(delay * 2, 60)
    return last


def http_json(url, **kw):
    status, data = http_get(url, **kw)
    try:
        return status, data, json.loads(data) if status == 200 else None
    except json.JSONDecodeError:
        return status, data, None


def norm_issn(value):
    return re.sub(r"[^0-9X]", "", (value or "").upper())


def norm_doi(value):
    value = (value or "").strip()
    value = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", value, flags=re.I)
    return value.lower()


def load_sjr():
    """Map ISSN -> dict(title, type, best, cs_q1, categories, publisher) from the frozen SJR CSV."""
    if sha_file(SJR_CSV) != SJR_SHA:
        raise SystemExit("SJR CSV hash changed")
    table = {}
    with open(SJR_CSV, encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            cats = {k.strip(): v for k, v in re.findall(r"([^;]+?) \((Q\d)\)", row["Categories"])}
            entry = {"title": row["Title"], "type": row["Type"], "best": row["SJR Best Quartile"],
                     "cs_q1": int(any(cats.get(c) == "Q1" for c in CS_CATEGORIES)),
                     "cs_cats": "|".join(c for c in CS_CATEGORIES if cats.get(c) == "Q1"),
                     "publisher": row["Publisher"], "sjr": row["SJR"]}
            for issn in row["Issn"].split(","):
                issn = norm_issn(issn)
                if issn:
                    table.setdefault(issn, entry)
    return table


def topic_ok(title, abstract):
    text = f"{title or ''} {abstract or ''}"
    return bool((SYSTEM_RE.search(text) and TASK_RE.search(text)) or STRONG_RE.search(text))


def abstract_from_index(index):
    if not index:
        return ""
    words = []
    for word, positions in index.items():
        for p in positions:
            words.append((p, word))
    return " ".join(w for _, w in sorted(words))


# ---- state checkpoint -------------------------------------------------------
STATE = WORK / "state.json"


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"protocol_sha256": None, "phases": {}}


def save_state(state):
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, STATE)


def _rel(path):
    return str(Path(path).resolve().relative_to(PLAN)).replace("\\", "/")


def next_attempt(state, phase, batch):
    """Attempt number for a new run of this batch (1 + attempts already recorded)."""
    entry = state.get("phases", {}).get(phase, {}).get("batches", {}).get(batch, {})
    return len(entry.get("attempts", [])) + 1


def batch_done(state, phase, batch, inputs=()):
    """A batch is skipped only when committed under the current protocol with matching input/output hashes."""
    entry = state.get("phases", {}).get(phase, {}).get("batches", {}).get(batch)
    if not entry or entry.get("status") != "committed":
        return False
    if entry.get("protocol_sha256") != state.get("protocol_sha256"):
        return False
    recorded = {i["path"]: i["sha256"] for i in entry.get("inputs", [])}
    for path in inputs:
        if recorded.get(_rel(path)) != sha_file(path):
            return False
    return all((PLAN / o["path"]).is_file() and sha_file(PLAN / o["path"]) == o["sha256"]
               for o in entry.get("outputs", []))


def commit_batch(state, phase, batch, outputs, inputs=(), attempt=None, receipt="", **extra):
    ph = state.setdefault("phases", {}).setdefault(phase, {"status": "running", "batches": {}})
    prev = ph["batches"].get(batch, {})
    attempts = list(prev.get("attempts", []))
    attempt = attempt or f"{batch}-a{len(attempts) + 1:02d}"
    attempts.append({"attempt": attempt, "status": "committed", "at": now_utc()})
    ph["batches"][batch] = {
        "status": "committed", "attempt": attempt, "protocol_sha256": state.get("protocol_sha256"),
        "inputs": [{"path": _rel(p), "sha256": sha_file(p)} for p in inputs],
        "outputs": [{"path": _rel(p), "sha256": sha_file(p)} for p in outputs],
        "receipt": receipt, "attempts": attempts, **extra}
    save_state(state)


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


# ---- OpenAlex record normalization ------------------------------------------
OA_SELECT = ("id,doi,title,publication_year,publication_date,type,language,primary_location,"
             "abstract_inverted_index,authorships,cited_by_count,is_retracted,best_oa_location,ids")
RECORD_FIELDS = ["openalex_id", "doi", "arxiv", "title", "year", "publication_date", "venue", "source_type",
                 "issn_l", "issns", "publisher", "type", "language", "first_author", "cited_by",
                 "is_retracted", "oa_url", "abstract", "abstract_source", "origin", "raw_sha256",
                 "retrieved_at_utc"]


def normalize_work(work, origin, raw_sha, retrieved):
    loc = work.get("primary_location") or {}
    src = loc.get("source") or {}
    best = work.get("best_oa_location") or {}
    authors = work.get("authorships") or []
    abstract = abstract_from_index(work.get("abstract_inverted_index"))
    arxiv = ""
    for location_url in [loc.get("landing_page_url") or "", best.get("landing_page_url") or ""]:
        match = re.search(r"arxiv\.org/abs/([\w.]+?)(v\d+)?$", location_url)
        if match:
            arxiv = match.group(1)
    return {
        "openalex_id": (work.get("id") or "").rsplit("/", 1)[-1], "doi": norm_doi(work.get("doi")),
        "arxiv": arxiv, "title": (work.get("title") or "").strip(), "year": work.get("publication_year") or "",
        "publication_date": work.get("publication_date") or "", "venue": src.get("display_name") or "",
        "source_type": src.get("type") or "", "issn_l": src.get("issn_l") or "",
        "issns": "|".join(src.get("issn") or []), "publisher": src.get("host_organization_name") or "",
        "type": work.get("type") or "", "language": work.get("language") or "",
        "first_author": ((authors[0].get("author") or {}).get("display_name") if authors else "") or "",
        "cited_by": work.get("cited_by_count") or 0, "is_retracted": int(bool(work.get("is_retracted"))),
        "oa_url": best.get("pdf_url") or best.get("landing_page_url") or "",
        "abstract": abstract, "abstract_source": "openalex" if abstract else "",
        "origin": origin, "raw_sha256": raw_sha, "retrieved_at_utc": retrieved,
    }
