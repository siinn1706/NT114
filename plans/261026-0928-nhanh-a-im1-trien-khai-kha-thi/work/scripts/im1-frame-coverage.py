"""Build the IM1 frames of the grouped RCAEval split and measure their coverage of the H1 pool (CPU, no model).

usage: python -X utf8 im1-frame-coverage.py DATA_HOME SPLIT_NAME MEMBERSHIP_CSV FRAMES_DIR OUT_JSON OUT_CSV

Frames: `rca.im1_frame.build_all` reads only the split's train-role incidents (assignments.jsonl) and their
pre-anchor trace rows (ts_ns, trace_id, span_id, parent_span_id, service_id). No label, val or test
telemetry or result file is opened. Path counts combine frame validity with the label-free membership
cells (receipt 02-h1-membership-04): for a framed arm, `no_trace` records of a key with a valid frame take
the `no_trace` path, other `no_trace` records `frame_free`; records of traced systems under `no_metric` /
`no_log` are counted on the `trace` path assuming a valid span exists (not checked here: that would read
val/test traces); untraced systems are `frame_free`.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

from rca import im1_frame
from rca.store import CanonicalStore, read_jsonl


def main():
    home, split, mem, fdir, out_json, out_csv = (Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]),
                                                 Path(sys.argv[5]), Path(sys.argv[6]))
    split_dir = home / "splits" / split
    roles = {a["incident_uid"]: a["split"] for a in read_jsonl(split_dir / "assignments.jsonl")}
    frames = im1_frame.build_all(CanonicalStore(home), ["rcaeval"], split_dir, roles, fdir)
    man = im1_frame.manifest(frames)
    valid = {(e["key"][1], e["key"][2]) for e in man.values() if e["valid"]}

    paths = defaultdict(lambda: defaultdict(int))
    for row in csv.DictReader(mem.open(encoding="utf-8")):
        if row["kind"] != "cell":
            continue
        role, sub, sysname = row["role"], row["subset"], row["system"]
        traced = row["natural_traces"] == "present"
        nt, nm, nl = int(row["rec_no_trace"]), int(row["rec_no_metric"]), int(row["rec_no_log"])
        for arm in ("ra", "ra_im1"):
            p = paths[(role, arm)]
            p["trace"] += (nm + nl) if traced else 0
            p["frame_free"] += 0 if traced else nm + nl
            framed = arm == "ra_im1" and (sub, sysname) in valid
            p["no_trace" if framed else "frame_free"] += nt
            p["records"] += nm + nl + nt
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["role", "arm", "trace", "no_trace", "frame_free", "records"])
        for (role, arm), p in sorted(paths.items()):
            w.writerow([role, "ra_im1, ra_im1_shuf" if arm == "ra_im1" else arm,
                        p["trace"], p["no_trace"], p["frame_free"], p["records"]])
    out_json.write_text(json.dumps({"split": split, "min_contributing": im1_frame.MIN_CONTRIBUTING,
                                    "frames": man}, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    for e in man.values():
        print(e["key"][1], e["key"][2], "valid" if e["valid"] else "INVALID", "contributing", e["n_contributing"],
              "edges", e["n_edges"], "retained", round(e["retained_real_share"], 3))


if __name__ == "__main__":
    main()
