"""Phase 05: validate screener CSVs against their batches, check anchor drift, merge to one T1 table.

usage: python -X utf8 -I merge-screen.py PREFIX SCREENER [REFERENCE_ANCHOR_CSV]  -> work/screen/<PREFIX>-<SCREENER>-merged.csv, work/screen/<PREFIX>-<SCREENER>-check.json
Anchor drift (protocol §6): every session's anchor decisions and R1 must equal those of the reference session
(default: the first batch of PREFIX; pass the anchors file of the very first screening session to compare across prefixes).
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK, write_csv  # noqa: E402

HEADER = ["openalex_id", "decision", "codes", "R1", "R2", "R3", "R4", "R5", "R6", "R_total", "read_level", "evidence"]
RANGE = {"R1": 3, "R2": 2, "R3": 2, "R4": 1, "R5": 1, "R6": 1}
DECISIONS = {"include", "exclude", "needs-review", "context-survey"}


def load(path, ids):
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != HEADER:
            raise SystemExit(f"{path.name}: header {reader.fieldnames}")
        rows = list(reader)
    errors = []
    if [r["openalex_id"] for r in rows] != ids:
        errors.append("ids/order differ from input")
    for r in rows:
        try:
            scores = {k: int(r[k]) for k in RANGE}
            if any(not 0 <= v <= RANGE[k] for k, v in scores.items()) or int(r["R_total"]) != sum(scores.values()):
                errors.append(f"{r['openalex_id']}: R out of range or total")
        except ValueError:
            errors.append(f"{r['openalex_id']}: non-integer R")
        if r["decision"] not in DECISIONS:
            errors.append(f"{r['openalex_id']}: decision {r['decision']}")
        codes = set(r["codes"].split("|"))
        if r["decision"] == "include" and (not {"I1", "I2", "I3"} <= codes or any(c.startswith("E") for c in codes)):
            errors.append(f"{r['openalex_id']}: include without I1|I2|I3 or with E code")
    return rows, errors


prefix, who = sys.argv[1], sys.argv[2]
inp = WORK / "screen" / "input"
manifest = json.loads((inp / f"{prefix}-manifest.json").read_text(encoding="utf-8"))
anchor_ids = [json.loads(line)["openalex_id"] for line in (inp / "anchors.jsonl").read_text(encoding="utf-8").splitlines()]
report = {"prefix": prefix, "screener": who, "batches": {}, "anchor_drift": []}
merged, reference = [], None
if len(sys.argv) > 3:
    reference = {r["openalex_id"]: (r["decision"], r["R1"]) for r in load(Path(sys.argv[3]), anchor_ids)[0]}
for b in manifest["batches"]:
    ids = [json.loads(line)["openalex_id"] for line in (inp / f"{b['batch']}.jsonl").read_text(encoding="utf-8").splitlines()]
    rows, errors = load(WORK / "screen" / f"{b['batch']}-{who}.csv", ids)
    anchors, a_errors = load(WORK / "screen" / f"anchors-{b['batch']}-{who}.csv", anchor_ids)
    key = {r["openalex_id"]: (r["decision"], r["R1"]) for r in anchors}
    reference = reference or key
    drift = [a for a in anchor_ids if key[a] != reference[a]] if not a_errors else ["anchor file invalid"]
    report["batches"][b["batch"]] = {"n": len(rows), "errors": errors + a_errors, "anchor_drift": drift}
    report["anchor_drift"] += [f"{b['batch']}:{a}:{reference.get(a)}->{key.get(a)}" for a in drift if a in key]
    merged += [dict(r, batch=b["batch"]) for r in rows]
report["n"] = len(merged)
report["decisions"] = {d: sum(r["decision"] == d for r in merged) for d in sorted(DECISIONS)}
report["valid"] = all(not v["errors"] for v in report["batches"].values())
write_csv(WORK / "screen" / f"{prefix}-{who}-merged.csv", merged, HEADER + ["batch"])
(WORK / "screen" / f"{prefix}-{who}-check.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print(json.dumps({k: report[k] for k in ("n", "decisions", "valid", "anchor_drift")}))
