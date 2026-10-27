"""Phase 05: build the blind double-screening sample (protocol §6 "Mẫu kép").

usage: python -X utf8 -I make-double-sample.py PREFIX SCREENER [FORCED_IDS]
Sample = 10% of screened records stratified by first-screener decision (seed 20261024) + every needs-review
+ forced ids (borderline rows flagged by screeners and the provisional ranks 90-110, from any prefix).
Writes work/screen/input/dbl-<PREFIX>-NNN.jsonl (input fields only, no first-screener data) and a manifest.
"""
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SEED, WORK, read_csv, sha_file  # noqa: E402

prefix, who = sys.argv[1], sys.argv[2]
forced = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else set()
inp = WORK / "screen" / "input"
if (inp / f"dbl-{prefix}-manifest.json").exists():
    raise SystemExit("double-screening manifest exists")
records = {}
# Forced ids (ranks 90-110) may come from another prefix's batches, so index every screening manifest.
for manifest in sorted(inp.glob("*-manifest.json")):
    if manifest.name.startswith("dbl-"):
        continue
    for b in json.loads(manifest.read_text(encoding="utf-8"))["batches"]:
        for line in (inp / f"{b['batch']}.jsonl").read_text(encoding="utf-8").splitlines():
            records[json.loads(line)["openalex_id"]] = line
rows = sorted(read_csv(WORK / "screen" / f"{prefix}-{who}-merged.csv"), key=lambda r: r["openalex_id"])
rng = random.Random(SEED)
reasons = {r["openalex_id"]: "needs-review" for r in rows if r["decision"] == "needs-review"}
for decision in ("include", "exclude", "context-survey"):
    group = [r["openalex_id"] for r in rows if r["decision"] == decision]
    for i in rng.sample(group, math.ceil(0.1 * len(group))):
        reasons.setdefault(i, f"stratified-10pct:{decision}")
for i in sorted(forced):
    reasons.setdefault(i, "forced-borderline")
ids = sorted(reasons)
rng.shuffle(ids)
batches = []
for n, k in enumerate(range(0, len(ids), 50)):
    path = inp / f"dbl-{prefix}-{n:03d}.jsonl"
    with open(path, "x", encoding="utf-8", newline="\n") as handle:
        handle.write("".join(records[i] + "\n" for i in ids[k:k + 50]))
    batches.append({"batch": path.stem, "n": len(ids[k:k + 50]), "sha256": sha_file(path)})
(inp / f"dbl-{prefix}-manifest.json").write_text(json.dumps({"seed": SEED, "batches": batches, "reasons": reasons},
                                                             indent=1), encoding="utf-8")
print(json.dumps({"n": len(ids), "by_reason": {r: list(reasons.values()).count(r) for r in sorted(set(reasons.values()))}}))
