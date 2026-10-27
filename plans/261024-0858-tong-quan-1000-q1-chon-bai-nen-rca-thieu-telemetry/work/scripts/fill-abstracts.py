"""Phase 04: fetch missing abstracts from Crossref for records that pass every Q gate.

usage: python -X utf8 -I fill-abstracts.py TAG [--title-only]
--title-only targets <TAG>-needs-review-t0.csv (title-only records that failed the topic gate) and writes
the same outputs with a "-tonly" suffix.
Reads work/records/<TAG>-candidates.csv and <TAG>-excluded.csv; targets records without abstract whose only
exclusion (if any) is the topic gate. Writes work/records/abstract-fill-<TAG>.csv (full rows, abstract replaced,
origin abstract-fill:crossref) and work/abstract-fill-log-<TAG>.csv. Checkpointed per 50 DOIs.
"""
import html
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (RECORD_FIELDS, WORK, batch_done, commit_batch, http_get, load_state, now_utc,  # noqa: E402
                    read_csv, sha_bytes, write_csv)

PHASE = "04"


def clean(jats):
    text = re.sub(r"<[^>]+>", " ", jats or "")
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    return re.sub(r"^(Abstract|ABSTRACT)\s*[:.]?\s*", "", text)


def main():
    tag = sys.argv[1]
    sfx = "-tonly" if "--title-only" in sys.argv[2:] else ""
    if sfx:
        rows = read_csv(WORK / "records" / f"{tag}-needs-review-t0.csv")
    else:
        rows = read_csv(WORK / "records" / f"{tag}-candidates.csv")
        rows += [r for r in read_csv(WORK / "records" / f"{tag}-excluded.csv")
                 if r["exclude_reason"] == "T-off-topic-metadata"]
    targets = sorted((r for r in rows if not r["abstract"] and r["doi"]), key=lambda r: r["openalex_id"])
    state = load_state()
    raw_dir = WORK / "raw" / "crossref"
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_rows, log = [], []
    for i in range(0, len(targets), 50):
        chunk = targets[i:i + 50]
        name = f"fill-{tag}{sfx}-{i // 50:03d}"
        part_path = WORK / "records" / "abstract-fill-batches" / f"{name}.csv"
        log_path = WORK / "records" / "abstract-fill-batches" / f"{name}-log.csv"
        if batch_done(state, PHASE, name):
            out_rows += read_csv(part_path)
            log += read_csv(log_path)
            continue
        part, part_log = [], []
        for rec in chunk:
            url = "https://api.crossref.org/works/" + urllib.parse.quote(rec["doi"], safe="/")
            status, raw = http_get(url, retries=4)
            raw_name = raw_dir / f"{rec['openalex_id']}.json"
            raw_name.write_bytes(raw)
            abstract = ""
            if status == 200:
                try:
                    abstract = clean(json.loads(raw)["message"].get("abstract", ""))
                except (json.JSONDecodeError, KeyError):
                    abstract = ""
            part_log.append({"openalex_id": rec["openalex_id"], "doi": rec["doi"], "http": status,
                             "got_abstract": int(bool(abstract)), "raw_sha256": sha_bytes(raw)})
            if abstract:
                new = {k: rec.get(k, "") for k in RECORD_FIELDS}
                new.update(abstract=abstract, abstract_source="crossref", origin="abstract-fill:crossref",
                           raw_sha256=sha_bytes(raw), retrieved_at_utc=now_utc())
                part.append(new)
            time.sleep(0.15)
        write_csv(part_path, part, RECORD_FIELDS)
        write_csv(log_path, part_log, ["openalex_id", "doi", "http", "got_abstract", "raw_sha256"])
        commit_batch(state, PHASE, name, [part_path, log_path], count=len(part), requested=len(chunk))
        out_rows += part
        log += part_log
        print(f"{name}: {len(part)}/{len(chunk)} abstracts", flush=True)
    write_csv(WORK / "records" / f"abstract-fill-{tag}{sfx}.csv", out_rows, RECORD_FIELDS)
    write_csv(WORK / f"abstract-fill-log-{tag}{sfx}.csv", log, ["openalex_id", "doi", "http", "got_abstract", "raw_sha256"])
    print(json.dumps({"targets": len(targets), "filled": len(out_rows),
                      "http_non200": sum(1 for r in log if str(r["http"]) != "200")}))


if __name__ == "__main__":
    main()
