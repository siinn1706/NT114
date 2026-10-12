"""Append one extraction record (JSON object on stdin) to extraction.jsonl after checking required fields.

Empty cells must be written as "not-reported". A record with an id already present replaces the old one.
Usage: python -X utf8 add-extraction.py < record.json   |   python -X utf8 add-extraction.py --csv
"""
import csv
import json
import sys
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
FIELDS = ["id", "doi", "venue", "year", "quartile", "read_level", "source_version", "problem", "system_context",
          "datasets", "modalities", "method_family", "llm", "retrieval", "propagation", "confidence", "explanation",
          "compression_cost", "metrics", "artifacts", "limitations", "future_work", "locators"]
JSONL = WORK / "extraction.jsonl"


def load():
    if not JSONL.exists():
        return []
    return [json.loads(x) for x in JSONL.read_text(encoding="utf-8").splitlines() if x.strip()]


def main():
    rows = load()
    if "--csv" in sys.argv:
        rows.sort(key=lambda r: r["id"])
        with open(WORK / "extraction.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
        print(len(rows), "rows ->", WORK / "extraction.csv")
        return
    rec = json.loads(sys.stdin.read())
    missing = [k for k in FIELDS if not str(rec.get(k, "")).strip()]
    extra = [k for k in rec if k not in FIELDS]
    if missing or extra:
        sys.exit(f"missing={missing} extra={extra}")
    rows = [r for r in rows if r["id"] != rec["id"]] + [rec]
    JSONL.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print("ok", rec["id"], "total", len(rows))


if __name__ == "__main__":
    main()
