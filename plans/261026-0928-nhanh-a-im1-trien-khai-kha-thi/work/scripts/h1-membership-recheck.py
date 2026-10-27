"""Recount the H1 pool `single_modality` on the grouped RCAEval split (CPU, no model, no labels).

usage: python -X utf8 h1-membership-recheck.py DATA_HOME SPLIT_NAME OUT_CSV

Reads only label-free inputs:
- splits/<SPLIT>/assignments.jsonl (incident_uid, split role)
- canonical/v1/rcaeval/visible/incidents.jsonl (subset, system, natural modality status, quality)
- reports/condition-matrix-rcaeval.json, only `applicable` of no_metric/no_log/no_trace and `natural`
- reports/eval-units-rcaeval.json, only injection_id and excluded_from_primary
It never opens canonical/v1/rcaeval/eval_only (labels), split.json strata or any result file.
The condition-matrix fields blind_root and nonroot_target depend on labels and are not read.
"""
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

POOL = ("no_metric", "no_log", "no_trace")
EXPECTED = {  # design figures being checked (test-matrix §2, protocol v2 §9)
    ("test", "injections"): 108, ("test", "records"): 285,
    ("val", "injections"): 78, ("val", "records"): 210,
    ("test", "traced_injections"): 69, ("test", "RE2-SS_injections"): 39,
}


def main():
    home, split, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    roles = {}
    for line in (home / "splits" / split / "assignments.jsonl").open(encoding="utf-8"):
        a = json.loads(line)
        roles[a["incident_uid"]] = a["split"]
    inc = {}
    for line in (home / "canonical/v1/rcaeval/visible/incidents.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        inc[r["incident_uid"]] = r
    cm = json.loads((home / "reports/condition-matrix-rcaeval.json").read_text(encoding="utf-8"))["incidents"]
    units = json.loads((home / "reports/eval-units-rcaeval.json").read_text(encoding="utf-8"))["units"]

    cells = defaultdict(lambda: {"inj": set(), "rec": 0, **{c: 0 for c in POOL}, "excluded": 0})
    train_traced = defaultdict(int)
    missing = []
    for uid, role in sorted(roles.items()):
        r = inc.get(uid)
        if r is None or uid not in cm:
            missing.append(uid)
            continue
        traces = r["telemetry"]["traces"]["status"]
        if role == "train" and traces == "present":
            train_traced[(r["dataset_subset"], r["system"])] += 1
        if role not in ("val", "test"):
            continue
        key = (role, r["dataset_subset"], r["system"], traces)
        for c in POOL:
            if cm[uid]["conditions"].get(c, {}).get("applicable"):
                cell = cells[key]
                cell["inj"].add(units[uid]["injection_id"])
                cell["rec"] += 1
                cell[c] += 1
                cell["excluded"] += units[uid]["excluded_from_primary"] is not None

    rows = []
    totals = defaultdict(lambda: {"inj": set(), "rec": 0, **{c: 0 for c in POOL}, "excluded": 0})
    for (role, sub, system, traces), c in sorted(cells.items()):
        rows.append({"kind": "cell", "role": role, "subset": sub, "system": system, "natural_traces": traces,
                     "injections": len(c["inj"]), "records": c["rec"],
                     **{f"rec_{k}": c[k] for k in POOL}, "excluded_from_primary_records": c["excluded"],
                     "expected": "", "match": ""})
        for tk in (role, f"{role}|traced" if traces == "present" else f"{role}|untraced"):
            t = totals[tk]
            t["inj"] |= c["inj"]
            t["rec"] += c["rec"]
            t["excluded"] += c["excluded"]
            for k in POOL:
                t[k] += c[k]
    for tk, t in sorted(totals.items()):
        role, _, part = tk.partition("|")
        rows.append({"kind": "total", "role": role, "subset": part or "all", "system": "all", "natural_traces": part or "all",
                     "injections": len(t["inj"]), "records": t["rec"], **{f"rec_{k}": t[k] for k in POOL},
                     "excluded_from_primary_records": t["excluded"], "expected": "", "match": ""})
    # comparisons against the design figures
    get = {(r["role"], r["subset"]): r for r in rows if r["kind"] == "total"}
    re2ss = sum(r["injections"] for r in rows if r["kind"] == "cell" and r["role"] == "test"
                and r["subset"] == "RE2" and r["system"] == "sock-shop")
    observed = {
        ("test", "injections"): get[("test", "all")]["injections"], ("test", "records"): get[("test", "all")]["records"],
        ("val", "injections"): get[("val", "all")]["injections"], ("val", "records"): get[("val", "all")]["records"],
        ("test", "traced_injections"): get.get(("test", "traced"), {"injections": 0})["injections"],
        ("test", "RE2-SS_injections"): re2ss,
    }
    for (role, what), exp in EXPECTED.items():
        obs = observed[(role, what)]
        rows.append({"kind": "check", "role": role, "subset": what, "system": "", "natural_traces": "",
                     "injections": obs, "records": "", **{f"rec_{k}": "" for k in POOL},
                     "excluded_from_primary_records": "", "expected": exp, "match": obs == exp})
    for (sub, system), n in sorted(train_traced.items()):
        rows.append({"kind": "train_traced_incidents", "role": "train", "subset": sub, "system": system,
                     "natural_traces": "present", "injections": n, "records": "", **{f"rec_{k}": "" for k in POOL},
                     "excluded_from_primary_records": "", "expected": "", "match": ""})
    for system in sorted({r["system"] for r in inc.values()} - {s for _, s in train_traced}):
        rows.append({"kind": "train_traced_incidents", "role": "train", "subset": "", "system": system,
                     "natural_traces": "present", "injections": 0, "records": "", **{f"rec_{k}": "" for k in POOL},
                     "excluded_from_primary_records": "", "expected": "", "match": ""})
    out.parent.mkdir(parents=True, exist_ok=True)
    sources = [home / "splits" / split / "assignments.jsonl", home / "canonical/v1/rcaeval/visible/incidents.jsonl",
               home / "reports/condition-matrix-rcaeval.json", home / "reports/eval-units-rcaeval.json"]
    side = {"data_home": str(home), "split": split,
            "inputs": {str(p.relative_to(home)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
    out.with_suffix(".inputs.json").write_text(json.dumps(side, indent=1), encoding="utf-8")
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        if r["kind"] != "cell":
            print(r["kind"], r["role"], r["subset"], r["system"], r["injections"], r["records"], r["expected"], r["match"])
    print("missing_from_store_or_matrix", len(missing))
    bad = [r for r in rows if r["kind"] == "check" and not r["match"]]
    print("design_mismatches", len(bad))


if __name__ == "__main__":
    main()
