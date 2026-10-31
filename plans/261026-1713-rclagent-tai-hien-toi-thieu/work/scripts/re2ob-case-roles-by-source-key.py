"""Map each raw RE2-OB case to its NT114 incident by source directory, not by inject time (CPU, no model).

usage: python -X utf8 re2ob-case-roles-by-source-key.py RAW_RE2OB VISIBLE_INCIDENTS SOURCE_INDEX QUALITY ASSIGNMENTS OUT_CSV

Join key: `source_incident_key` of `eval_only/source_index.jsonl` == `RE2-OB/<fault dir>/<instance>`, the
same directory the author's preprocess reads. Inject time is only a cross-check. Only provenance,
quality state and split role are read: no label file, no result file. Every visible RE2 online-boutique
incident that shares a case's inject time but comes from another source key is listed with its source key
and quality state, so a duplicate stays visible instead of being dropped silently.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

raw, inc, src, qual, asg, out = (Path(a) for a in sys.argv[1:7])
visible = {}
for line in inc.open(encoding="utf-8"):
    r = json.loads(line)
    if r["dataset_subset"] == "RE2" and r["system"] == "online-boutique":
        visible[r["incident_uid"]] = int(r["time"]["anchor_original"]["value"])
keys = {}
for line in src.open(encoding="utf-8"):
    r = json.loads(line)
    if r["incident_uid"] in visible:
        keys[r["incident_uid"]] = r["source_incident_key"]
state = {}
for line in qual.open(encoding="utf-8"):
    r = json.loads(line)
    state[r["incident_uid"]] = r["state"]
roles = {}
for line in asg.open(encoding="utf-8"):
    a = json.loads(line)
    roles[a["incident_uid"]] = a["split"]
by_key = {}
for uid, key in keys.items():
    by_key.setdefault(key, []).append(uid)
rows = []
for d in sorted(p for p in raw.iterdir() if p.is_dir()):
    for inst in sorted(p for p in d.iterdir() if p.is_dir() and p.name.isdigit()):
        t = int((inst / "inject_time.txt").read_text().strip())
        key = f"RE2-OB/{d.name}/{inst.name}"
        uids = by_key.get(key, [])
        uid = uids[0] if len(uids) == 1 else ""
        others = sorted(u for u, at in visible.items() if at == t and u not in uids)
        rows.append({"order": len(rows) + 1, "case_id": f"{d.name}_{inst.name}", "source_key": key,
                     "inject_ts": t, "incident_uid": ";".join(uids), "n_match": len(uids),
                     "anchor_matches": uid != "" and visible[uid] == t,
                     "quality_state": state.get(uid, "") if uid else "",
                     "role": roles.get(uid, "unassigned") if uid else "unmatched",
                     "same_inject_time_other_uids": ";".join(
                         f"{u}|{keys.get(u, '?')}|{state.get(u, '?')}|{roles.get(u, 'unassigned')}" for u in others)})
with out.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
print(json.dumps({"cases": len(rows), "match_counts": dict(Counter(r["n_match"] for r in rows)),
                  "anchor_mismatches": sum(not r["anchor_matches"] for r in rows),
                  "roles": dict(Counter(r["role"] for r in rows)),
                  "quality": dict(Counter(r["quality_state"] for r in rows)),
                  "cases_with_same_time_other_uids": [r["case_id"] for r in rows if r["same_inject_time_other_uids"]]},
                 indent=2))
