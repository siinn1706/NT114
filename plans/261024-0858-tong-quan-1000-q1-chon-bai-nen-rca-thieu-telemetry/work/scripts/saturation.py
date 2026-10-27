"""Protocol §10: new valid T0 records per collection step (saturation curve).

usage: python -X utf8 -I saturation.py OUT_JSON T0_CSV:LABEL [T0_CSV:LABEL ...] -- STEP_LABEL=RECORDS_CSV[,CSV...] ...
Each T0 is the gate output after a step; a new record is credited to every step source whose rows contain it.
"""
import json
import sys

sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.as_posix())
from common import read_csv  # noqa: E402

out, rest = sys.argv[1], sys.argv[2:]
cut = rest.index("--")
t0s = [a.rsplit(":", 1) for a in rest[:cut]]
steps = {}
for arg in rest[cut + 1:]:
    label, files = arg.split("=", 1)
    steps[label] = set().union(*({r["openalex_id"] for r in read_csv(f)} for f in files.split(",")))
curve, prev = [], set()
for path, label in t0s:
    ids = {r["openalex_id"] for r in read_csv(path)}
    new = ids - prev
    curve.append({"t0": label, "n_t0": len(ids), "new": len(new) if prev else None,
                  "new_by_source": {s: len(new & v) for s, v in steps.items()} if prev else None,
                  "new_from_source_only": {s: len(new & v - set().union(*(w for t, w in steps.items() if t != s)))
                                           for s, v in steps.items()} if prev else None})
    prev = ids
json.dump({"curve": curve}, open(out, "w", encoding="utf-8"), indent=1)
print(json.dumps(curve))
