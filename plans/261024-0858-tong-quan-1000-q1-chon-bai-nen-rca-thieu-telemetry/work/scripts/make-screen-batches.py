"""Phase 05: split T0 candidates into screening batches of 50 in a seeded permutation (protocol §6).

usage: python -X utf8 -I make-screen-batches.py T0_CSV PREFIX [START_INDEX]
Writes work/screen/input/<PREFIX>-NNN.jsonl (immutable) and work/screen/input/<PREFIX>-manifest.json.
Records already present in an earlier manifest (any prefix) are skipped, so snowball batches add only new ids.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SEED, WORK, read_csv, sha_file  # noqa: E402

FIELDS = ["openalex_id", "doi", "title", "venue", "year", "type", "abstract", "abstract_source",
          "sjr_cs_categories", "q1_weak", "topic_gate"]


def main():
    src, prefix = Path(sys.argv[1]), sys.argv[2]
    start = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    out = WORK / "screen" / "input"
    out.mkdir(parents=True, exist_ok=True)
    if (out / f"{prefix}-manifest.json").exists():
        raise SystemExit("manifest exists; batches are immutable")
    seen = set()
    for manifest in out.glob("*-manifest.json"):
        if manifest.name.startswith("dbl-"):  # double-screening samples are not primary batches
            continue
        seen |= set(json.loads(manifest.read_text(encoding="utf-8"))["ids"])
    rows = [r for r in read_csv(src) if r["openalex_id"] not in seen]
    rows.sort(key=lambda r: r["openalex_id"])
    random.Random(SEED).shuffle(rows)
    batches = []
    for n, i in enumerate(range(0, len(rows), 50), start=start):
        path = out / f"{prefix}-{n:03d}.jsonl"
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            for r in rows[i:i + 50]:
                rec = {k: r.get(k, "") for k in FIELDS}
                rec["abstract"] = rec["abstract"][:3000]
                handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
        batches.append({"batch": path.stem, "n": len(rows[i:i + 50]), "sha256": sha_file(path)})
    manifest = {"source": str(src).replace("\\", "/"), "source_sha256": sha_file(src), "seed": SEED,
                "batches": batches, "ids": [r["openalex_id"] for r in rows]}
    (out / f"{prefix}-manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(json.dumps({"records": len(rows), "batches": len(batches)}))


if __name__ == "__main__":
    main()
