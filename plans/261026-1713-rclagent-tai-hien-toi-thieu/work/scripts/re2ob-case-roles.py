"""Map each raw RE2-OB case of the author's layout to its NT114 incident and split role (CPU, no model).

usage: python -X utf8 re2ob-case-roles.py RAW_RE2OB VISIBLE_INCIDENTS ASSIGNMENTS OUT_CSV

Join key: `inject_time.txt` (unix s) == `time.anchor_original.value` of a visible RE2 online-boutique
incident. Only visible metadata and split roles are read: no label file, no result file. The case
directory name is the author's layout and already names the injected service and fault, so it is kept
as the case id and never used to choose a case. Rows keep the author's order (sorted directory, then
sorted digit instance), which is the order of `preprocess_re2ob.py`.
"""
import csv
import json
import sys
from pathlib import Path

raw, inc, asg, out = (Path(a) for a in sys.argv[1:5])
anchors = {}
for line in inc.open(encoding="utf-8"):
    r = json.loads(line)
    if r["dataset_subset"] == "RE2" and r["system"] == "online-boutique":
        anchors.setdefault(int(r["time"]["anchor_original"]["value"]), []).append(r["incident_uid"])
roles = {}
for line in asg.open(encoding="utf-8"):
    a = json.loads(line)
    roles[a["incident_uid"]] = a["split"]
rows = []
for d in sorted(p for p in raw.iterdir() if p.is_dir()):
    for inst in sorted(p for p in d.iterdir() if p.is_dir() and p.name.isdigit()):
        t = int((inst / "inject_time.txt").read_text().strip())
        uids = anchors.get(t, [])
        rows.append({"order": len(rows) + 1, "case_id": f"{d.name}_{inst.name}", "inject_ts": t,
                     "incident_uid": ";".join(uids), "n_match": len(uids),
                     "role": ";".join(sorted({roles.get(u, "unassigned") for u in uids})) or "unmatched"})
with out.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
from collections import Counter
print("cases", len(rows), "match counts", dict(Counter(r["n_match"] for r in rows)), "roles", dict(Counter(r["role"] for r in rows)))
first = next((r for r in rows if r["role"] == "train"), None)
print("first train-role case in author order:", first and (first["order"], first["case_id"], first["incident_uid"]))
