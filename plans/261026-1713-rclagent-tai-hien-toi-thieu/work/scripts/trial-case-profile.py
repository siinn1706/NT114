"""Profile the author's preprocessed RE2-OB output for one pre-chosen case (CPU, no model, no labels).

usage: python -X utf8 trial-case-profile.py DATA_RE2OB ROLES_CSV CASE_ID OUT_JSON

Reads only the author's merged telemetry files and `error_traces.txt`; `groundtruth.csv` is not opened.
Reports:
- overlap of case time windows in the merged dataset (the tool server queries by time, not by case);
- the error traces of the case: author rule = top-5 root spans by duration in [inject-60 s, inject+300 s];
- per trace: span count reachable from the root via parent links (one agent per span), depth, and the
  number of log rows / log characters the author's `search_logs` would return for each span (service
  substring match, +-60 s, after the INFO/DEBUG filter the tool server applies at load);
- peak working set of this process after loading the three files the way `tool_server.py` does
  (Windows `GetProcessMemoryInfo`), as an estimate of the tool server's memory need;
- a lower bound on LLM calls per trace: per span >= 1 self-state call + 1 consolidation call, plus one
  synthesis call (tool rounds add calls; the self-state loop has no round limit in the code).
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import ctypes
import ctypes.wintypes as wt

import pandas as pd


def peak_gb():
    class PMC(ctypes.Structure):
        _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD)] + [(n, ctypes.c_size_t) for n in (
            "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage",
            "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
    c = PMC()
    c.cb = ctypes.sizeof(c)
    ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb)
    return round(c.PeakWorkingSetSize / 2**30, 2)

data, roles_csv, case_id, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
cases = list(csv.DictReader(roles_csv.open(encoding="utf-8")))
inject = {c["case_id"]: int(c["inject_ts"]) for c in cases}
t0 = inject[case_id]

ts_sorted = sorted(inject.values())
gaps = [b - a for a, b in zip(ts_sorted, ts_sorted[1:])]
traces = pd.read_csv(data / "trace" / "all" / "trace_jaeger-span.csv", dtype={"status_code": str}, low_memory=False)
metrics = pd.read_csv(data / "metric" / "all" / "metrics.csv", low_memory=False)
logs = pd.read_csv(data / "log" / "all" / "logs.csv", low_memory=False)
logs = logs[~logs["value"].astype(str).str.lower().str.contains(r"severity:\s*(?:info|debug)", regex=True, na=False)]
loaded = {"spans": len(traces), "metric_rows": len(metrics), "log_rows_after_filter": len(logs), "peak_gb": peak_gb()}
print("tool-server-like load", loaded, flush=True)

lines = (data / "error_traces.txt").read_text().splitlines()
et = []
for i, line in enumerate(lines[1:], start=1):
    p = line.split()
    if len(p) >= 6:
        et.append({"line": i, "timestamp_ms": int(p[1]), "cmdb_id": p[2], "span_id": p[3], "trace_id": p[4],
                   "duration": int(p[5])})
mine = [e for e in et if t0 * 1000 - 60_000 <= e["timestamp_ms"] <= t0 * 1000 + 300_000]

children = defaultdict(list)
sub = traces[traces["trace_id"].isin({e["trace_id"] for e in mine})]
for r in sub.itertuples():
    if isinstance(r.parent_span, str):
        children[r.parent_span].append(r)
by_id = {r.span_id: r for r in sub.itertuples()}

prof = []
for e in sorted(mine, key=lambda e: -e["duration"]):
    stack, seen, depth, n_log_rows, n_log_chars, svcs = [(e["span_id"], 0)], set(), 0, 0, 0, set()
    while stack:
        sid, d = stack.pop()
        if sid in seen:
            continue
        seen.add(sid)
        depth = max(depth, d)
        r = by_id.get(sid)
        if r is not None:
            ts = int(str(r.timestamp)[:10])
            hit = logs[logs["cmdb_id"].astype(str).str.contains(str(r.cmdb_id), na=False, regex=False)
                       & logs["timestamp"].between(ts - 60, ts + 60)]
            n_log_rows, n_log_chars = max(n_log_rows, len(hit)), max(n_log_chars, int(hit.to_csv(index=False).__len__()))
            svcs.add(str(r.cmdb_id))
        stack.extend((c.span_id, d + 1) for c in children.get(sid, []))
    n = len(seen)
    prof.append({**e, "spans": n, "depth": depth, "services": sorted(svcs),
                 "max_log_rows_one_call": n_log_rows, "max_log_chars_one_call": n_log_chars,
                 "llm_calls_lower_bound": 2 * n + 1})
res = {"load": loaded, "case_id": case_id, "inject_ts": t0, "n_error_traces_of_case": len(mine),
       "min_gap_between_case_injections_s": min(gaps), "error_traces_total": len(et), "traces": prof}
out.write_text(json.dumps(res, indent=1), encoding="utf-8", newline="\n")
print(json.dumps({k: v for k, v in res.items() if k != "traces"}))
for p in prof:
    print({k: p[k] for k in ("line", "duration", "spans", "depth", "max_log_rows_one_call", "max_log_chars_one_call",
                             "llm_calls_lower_bound")})
