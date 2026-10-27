"""Phase 05: snowball round from provisional T1 seeds via OpenAlex referenced_works + cites (protocol §5).

usage: python -X utf8 -I snowball.py ROUND RANKED_CSV
Seeds = every row of RANKED_CSV. Backward: referenced_works of the seeds, fetched with the §5 base/date filter.
Forward: works citing any seed (cites:W1|W2...), same filter; the seed of each forward hit is recovered from its
referenced_works. One batch = 25 seeds, checkpointed in state phase 05 as snowball-<ROUND>-NNN.
Raw: work/raw/snowball/<ROUND>-NNN-<lane>-pNNN.json; rows: work/records/snowball-<ROUND>-batches/<batch>.csv;
merged: work/records/snowball-<ROUND>.csv (origin snowball:<seed>:<backward|forward>).
"""
import json
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (OA_SELECT, RECORD_FIELDS, WORK, batch_done, commit_batch, http_get, load_state,  # noqa: E402
                    normalize_work, now_utc, read_csv, sha_bytes, write_csv)
from queries import date_filter  # noqa: E402

PHASE = "05"
SELECT = OA_SELECT + ",referenced_works"


def short(oa_id):
    return oa_id.rsplit("/", 1)[-1]


def fetch(filt, raw_prefix):
    """All pages of /works for a filter; returns (works, raw_paths). Raises on a non-200 page."""
    works, paths, page = [], [], 0
    while True:
        page += 1
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode(
            {"filter": filt, "per-page": 200, "page": page, "select": SELECT}, safe=":,|")
        status, raw = http_get(url)
        path = Path(f"{raw_prefix}-p{page:03d}.json")
        if path.exists():
            raise SystemExit(f"raw page exists: {path}")
        path.write_bytes(raw)
        paths.append(path)
        if status != 200:
            raise SystemExit(f"{path.name}: HTTP {status}")
        data = json.loads(raw)
        works += [(w, sha_bytes(raw)) for w in data.get("results", [])]
        if not data.get("results") or page * 200 >= min(data["meta"]["count"], 10000):
            return works, paths


def main():
    rnd, ranked = sys.argv[1], sys.argv[2]
    seeds = [r["openalex_id"] for r in read_csv(ranked)]
    raw_dir = WORK / "raw" / "snowball"
    part_dir = WORK / "records" / f"snowball-{rnd}-batches"
    raw_dir.mkdir(parents=True, exist_ok=True)
    part_dir.mkdir(parents=True, exist_ok=True)
    state = load_state()
    merged = []
    for b, i in enumerate(range(0, len(seeds), 25)):
        name = f"snowball-{rnd}-{b:03d}"
        part = part_dir / f"{name}.csv"
        if batch_done(state, PHASE, name, inputs=[Path(ranked)]):
            merged += read_csv(part)
            continue
        chunk = seeds[i:i + 25]
        seedset = set(chunk)
        # backward: the seeds' own reference lists
        own, _ = fetch(f"openalex:{'|'.join(chunk)}", raw_dir / f"{name}-seeds")
        refs = {}
        for w, _ in own:
            for ref in w.get("referenced_works") or []:
                refs.setdefault(short(ref), short(w["id"]))
        rows, retrieved = [], now_utc()
        ref_ids = sorted(refs)
        for k in range(0, len(ref_ids), 50):
            got, _ = fetch(f"openalex:{'|'.join(ref_ids[k:k + 50])},{date_filter()}", raw_dir / f"{name}-back{k // 50:02d}")
            rows += [normalize_work(w, f"snowball:{refs[short(w['id'])]}:backward", sha, retrieved) for w, sha in got]
        # forward: works citing any seed of the batch
        got, _ = fetch(f"cites:{'|'.join(chunk)},{date_filter()}", raw_dir / f"{name}-fwd")
        for w, sha in got:
            cited = sorted(seedset & {short(r) for r in w.get("referenced_works") or []}) or ["unknown"]
            rows.append(normalize_work(w, f"snowball:{cited[0]}:forward", sha, retrieved))
        write_csv(part, rows, RECORD_FIELDS)
        commit_batch(state, PHASE, name, [part], inputs=[Path(ranked)], attempt=f"{name}-a01", count=len(rows),
                     seeds=len(chunk), backward_refs=len(ref_ids))
        merged += rows
        print(f"{name}: {len(chunk)} seeds, {len(ref_ids)} refs, {len(rows)} rows", flush=True)
    write_csv(WORK / "records" / f"snowball-{rnd}.csv", merged, RECORD_FIELDS)
    print(json.dumps({"seeds": len(seeds), "rows": len(merged)}))


if __name__ == "__main__":
    main()
