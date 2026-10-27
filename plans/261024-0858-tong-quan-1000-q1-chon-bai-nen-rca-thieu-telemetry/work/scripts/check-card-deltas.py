"""Phase 10 follow-up: show that T3 cards changed after their phase 08 checkpoint only by appended controller notes.

usage: python -X utf8 -I check-card-deltas.py OUT_CSV
For each t3-* batch whose card hash no longer matches work/state.json, strip the two known appended note
blocks (hash note, gate correction note) from the end of the file and compare the remainder with the
recorded hash. Exit 0 only if every changed card reduces exactly to its recorded version.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PLAN, load_state  # noqa: E402

NOTES = {
    "hash-note": ("\n## Hash note (controller, 2026-10-26)\n- The T2 text sha256 equals the sha256 of this same file "
                  "after CRLF to LF conversion (fulltext-access.py hashes the LF text in memory; Windows write_text "
                  "stores CRLF). Same content; see work/t3-text-hash-check.csv, receipt 08-text-hash-01.\n"),
    "gate-correction-note": ("\n## Gate correction note (controller, 2026-10-26)\n- After the fresh-context review some "
                             "gate values for this record changed; the current value and its evidence are in "
                             "work/t3-gate-corrections-a02.csv and the `correction` column of work/g-gates.csv "
                             "(receipt 08-merge-t3-03). Those files supersede the gate lines above where they differ.\n"),
}
state = load_state()
rows, ok = [], True
for batch, entry in state["phases"]["08"]["batches"].items():
    if not batch.startswith("t3-"):
        continue
    for out in entry["outputs"]:
        data = (PLAN / out["path"]).read_bytes()
        current = hashlib.sha256(data).hexdigest()
        if current == out["sha256"]:
            continue
        removed, rest = [], data
        for name, text in reversed(list(NOTES.items())):
            note = text.encode("utf-8")
            if rest.endswith(note):
                rest, removed = rest[:-len(note)], [name] + removed
        match = hashlib.sha256(rest).hexdigest() == out["sha256"]
        ok &= match
        rows.append({"card": out["path"], "recorded_sha256": out["sha256"], "current_sha256": current,
                     "appended_notes": "|".join(removed), "remainder_equals_recorded": match})
with open(sys.argv[1], "w", encoding="utf-8", newline="") as h:
    w = csv.DictWriter(h, fieldnames=["card", "recorded_sha256", "current_sha256", "appended_notes",
                                      "remainder_equals_recorded"])
    w.writeheader()
    w.writerows(rows)
print(json.dumps({"changed": len(rows), "all_reduce_to_recorded": ok}))
sys.exit(0 if ok and rows else 1)
