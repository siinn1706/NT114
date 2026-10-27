"""Phase 05: pick the 5 fixed drift anchors from the first screening batch (protocol §6, seed 20261024).

usage: python -X utf8 -I pick-anchors.py BATCH_JSONL  -> work/screen/input/anchors.jsonl (refuses to overwrite)
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SEED, WORK  # noqa: E402

lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
picked = sorted(random.Random(SEED).sample(range(len(lines)), 5))
with open(WORK / "screen" / "input" / "anchors.jsonl", "x", encoding="utf-8", newline="\n") as handle:
    handle.write("".join(lines[i] + "\n" for i in picked))
print(json.dumps([json.loads(lines[i])["openalex_id"] for i in picked]))
