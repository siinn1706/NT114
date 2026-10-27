"""Build the inputs of the scorer check of RCLAgent `evaluate.py` (no model call).

usage: python -X utf8 scorer-fixtures.py CODE_DIR OUT_DIR

1. `OUT_DIR/sample`: a byte copy of the author's `sample_data` (groundtruth, error_traces, one result file);
   the clone is never written. Expected by hand: label recommendationservice, first candidate
   recommendationservice-1 -> rank 0, R@1 = MRR = 1 over 1 fault.
2. `OUT_DIR/fixture`: a synthetic case set (fake names, no NT114 data) that exposes two rules of the code:
   - best-of-traces: fault A has two traces, one misses (label absent) and one hits at rank 2; the author
     rule reports rank 2 (R@1 = 0, R@3 = 1); a pre-specified first trace would report a miss;
   - denominator: fault C has no result file; the code divides by faults with results (2), not by the
     3 ground-truth faults, and prints a warning.
   Fault B has one trace that hits at rank 0.
"""
import json
import shutil
import sys
from pathlib import Path

code, out = Path(sys.argv[1]), Path(sys.argv[2])
if out.exists():
    sys.exit(f"exists: {out}")
shutil.copytree(code / "sample_data", out / "sample", ignore=shutil.ignore_patterns("metric", "log", "trace"))

fx = out / "fixture"
(fx / "result").mkdir(parents=True)
(fx / "groundtruth.csv").write_text(
    "timestamp,level,cmdb_id,failure_type\n"
    "1700000000,service,svc-a,cpu\n"
    "1700010000,service,svc-b,cpu\n"
    "1700020000,service,svc-c,cpu\n", encoding="utf-8", newline="\n")
# same printed-DataFrame layout as the author's error_traces.txt: line 0 is the header, line i is trace i
header = "       timestamp     cmdb_id           span_id                          trace_id  duration\n"
rows = [(1700000060000, "t1"), (1700000090000, "t2"), (1700010030000, "t3")]
(fx / "error_traces.txt").write_text(
    header + "".join(f"{i}  {ts}  front-0  s{i}  {tid}  100\n" for i, (ts, tid) in enumerate(rows)),
    encoding="utf-8", newline="\n")
results = {1: ["svc-x", "svc-y", "svc-z"],            # fault A, first trace: miss
           2: ["svc-x", "svc-y", "svc-a-0"],          # fault A, second trace: rank 2
           3: ["svc-b", "svc-x"]}                     # fault B: rank 0
for i, rc in results.items():
    (fx / "result" / f"conversation_trace_{i}.txt").write_text(json.dumps({"root_causes": rc}), encoding="utf-8")
print("expected sample: R@1 1.0000 (1/1), MRR 1.0000")
print("expected fixture (author rule): 2 faults evaluated out of 3, R@1 0.5000, R@3 1.0000, MRR 0.6667")
print("pre-specified first trace (not computed by the code): fault A miss -> R@1 0.5000, R@3 0.5000, MRR 0.5000")
