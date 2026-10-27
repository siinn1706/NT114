"""Phase 02: re-fetch current OpenAlex metadata for every record of the 11/10 and 19/10 corpora.

Old screening/scores are not inherited. Each output row keeps origin reuse:<file>:<row>.
usage: python -X utf8 -I reuse-seed.py
"""
import json
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (OA_SELECT, PLAN, RECORD_FIELDS, WORK, batch_done, commit_batch, http_get, load_state,  # noqa: E402
                    norm_doi, normalize_work, now_utc, read_csv, sha_bytes, sha_file, write_csv)

PHASE = "02"
OLD = PLAN.parent / "261011-1345-aiops-q1-literature-gap" / "work"
ELI = PLAN.parent / "261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit" / "work"
SOURCES = [OLD / "raw-hits.csv", OLD / "snowball-hits.csv", OLD / "read-final.csv", ELI / "corpus.csv"]


def keys_from(path):
    """Yield (row_number, openalex_id, doi) from an old corpus file."""
    for n, row in enumerate(read_csv(path), start=2):
        oa = (row.get("openalex_id") or "").rsplit("/", 1)[-1]
        dois = [norm_doi(d) for d in re.split(r"[;|]", row.get("dois") or row.get("doi") or "") if d.strip()]
        yield n, oa if oa.startswith("W") else "", [d for d in dois if d.startswith("10.")]


def fetch(filter_key, values, raw_dir, tag):
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(
        {"filter": f"{filter_key}:" + "|".join(values), "per-page": 200, "select": OA_SELECT}, safe=":,|/")
    status, raw = http_get(url)
    path = raw_dir / f"{tag}.json"
    path.write_bytes(raw)
    if status != 200:
        raise SystemExit(f"{tag}: HTTP {status}")
    return json.loads(raw)["results"], sha_bytes(raw)


def main():
    state = load_state()
    if not state.get("protocol_sha256"):
        raise SystemExit("protocol not frozen")
    inventory = [{"file": str(p.relative_to(PLAN.parent)).replace("\\", "/"), "sha256": sha_file(p),
                  "rows": len(read_csv(p))} for p in SOURCES]
    write_csv(WORK / "reuse-inventory.csv", inventory, ["file", "sha256", "rows"])
    wanted_oa, wanted_doi, origins = {}, {}, []
    for path in SOURCES:
        rel = path.name if path.parent == OLD else f"elicit/{path.name}"
        for n, oa, dois in keys_from(path):
            origin = f"reuse:{rel}:{n}"
            origins.append({"origin": origin, "openalex_id": oa, "dois": "|".join(dois)})
            if oa:
                wanted_oa.setdefault(oa, origin)
            elif dois:
                for d in dois:
                    wanted_doi.setdefault(d, origin)
    write_csv(WORK / "records" / "reuse-keys.csv", origins, ["origin", "openalex_id", "dois"])
    raw_dir = WORK / "raw" / "reuse"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows, found_oa, found_doi = [], set(), set()
    for kind, wanted in (("openalex", wanted_oa), ("doi", wanted_doi)):
        keys = sorted(wanted)
        for i in range(0, len(keys), 50):
            chunk = keys[i:i + 50]
            tag = f"{kind}-{i // 50:04d}"
            batch_path = WORK / "records" / "reuse-batches" / f"{tag}.csv"
            if batch_done(state, PHASE, tag):
                part = read_csv(batch_path)
            else:
                results, raw_sha = fetch(kind, chunk, raw_dir, tag)
                part = []
                for w in results:
                    rec = normalize_work(w, "", raw_sha, now_utc())
                    key = rec["openalex_id"] if kind == "openalex" else rec["doi"]
                    rec["origin"] = wanted.get(key, f"reuse:{kind}-lookup")
                    part.append(rec)
                write_csv(batch_path, part, RECORD_FIELDS)
                commit_batch(state, PHASE, tag, [batch_path], count=len(part), requested=len(chunk))
            rows += part
            found_oa |= {r["openalex_id"] for r in part}
            found_doi |= {r["doi"] for r in part}
    missing = [{"key": k, "kind": "openalex", "origin": v} for k, v in wanted_oa.items() if k not in found_oa]
    missing += [{"key": k, "kind": "doi", "origin": v} for k, v in wanted_doi.items() if k not in found_doi]
    write_csv(WORK / "records" / "seed-reused.csv", rows, RECORD_FIELDS)
    write_csv(WORK / "records" / "reuse-not-found.csv", missing, ["key", "kind", "origin"])
    print(json.dumps({"origins": len(origins), "wanted_openalex": len(wanted_oa), "wanted_doi": len(wanted_doi),
                      "fetched_rows": len(rows), "not_found": len(missing)}, indent=1))


if __name__ == "__main__":
    main()
