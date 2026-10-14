"""Builds small raw-data fixtures in a temp directory. No binary fixture is committed.

`rcaeval_zips(dst)` writes RCAEval-shaped zips that reproduce the known raw defects: a duplicate
`multi-source-data` case, the `ts-route-service_f3` / `ts-route-service_f3_1` batch pair, a
header-only `traces.csv`, `root_cause.txt` label artefacts, natural absence of traces, `.DS_Store`
members, and one `startTimeMillis` mismatch.
"""
from __future__ import annotations

import importlib.util
import random
import shutil
import zipfile
from pathlib import Path

RCA_ROOT = Path(__file__).resolve().parents[2]
TRACE_HEADER = "time,traceID,spanID,serviceName,methodName,operationName,startTimeMillis,startTime,duration,statusCode,parentSpanID\n"


def _make_synthetic():
    spec = importlib.util.spec_from_file_location("make_synthetic", RCA_ROOT / "scripts" / "make_synthetic.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _case(ms, out: Path, sysname: str, root: str, fault: str, inst: int, seed: int, subset: str = "RE2") -> Path:
    """Write one case with make_synthetic, then move it under <subset>-<sys>/<root>_<fault>/<inst>."""
    tmp = out / "_tmp"
    ms.make_case(tmp, sysname, ms.SYSTEMS[sysname], root, fault, inst, random.Random(seed))
    src = tmp / f"RE2-{sysname}" / f"{root}_{fault}" / str(inst)
    dst = out / f"{subset}-{sysname}" / f"{root}_{fault}" / str(inst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    shutil.rmtree(tmp)
    return dst


def _simple_from_full(case: Path) -> None:
    """simple_metrics.csv = the cpu and latency-90 columns of metrics.csv (a second metric set)."""
    lines = (case / "metrics.csv").read_text(encoding="utf-8").splitlines()
    head = lines[0].split(",")
    keep = [0] + [i for i, c in enumerate(head) if c.endswith(("_cpu", "_latency-90"))]
    rows = [",".join(r.split(",")[i] for i in keep) for r in lines]
    (case / "simple_metrics.csv").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")


def rcaeval_tree(dst: Path) -> Path:
    """Directory layout `<dst>/RE{2,3}-*/...` with every defect; returns dst."""
    ms = _make_synthetic()
    dst.mkdir(parents=True, exist_ok=True)
    c1 = _case(ms, dst, "OB", "checkoutservice", "cpu", 1, 1)
    _simple_from_full(c1)
    c2 = _case(ms, dst, "OB", "cartservice", "delay", 1, 2)
    _simple_from_full(c2)
    (dst / "RE2-OB" / ".DS_Store").write_bytes(b"\x00\x01")
    dup = c1.parent / "multi-source-data"
    shutil.copytree(c1, dup)
    (dup / "simple_metrics.csv").unlink()
    # one startTimeMillis mismatch in the cart case
    tr = (c2 / "traces.csv").read_text(encoding="utf-8").splitlines()
    head = tr[0].split(",")
    if "startTimeMillis" not in head:
        tr = _with_millis(tr)
    rows = [r.split(",") for r in tr[1:]]
    rows[0][6] = str(int(rows[0][6]) + 5000)
    (c2 / "traces.csv").write_text("\n".join([TRACE_HEADER.strip()] + [",".join(r) for r in rows]) + "\n", encoding="utf-8")
    _ensure_millis(c1)
    _ensure_millis(dup)
    # RE3-TT batch pair
    for cell_fault, seed in (("f3", 3), ("f3_1", 4)):
        c = _case(ms, dst, "TT", "ts-route-service", "delay", 1, seed, subset="RE3")
        target = c.parent.parent / f"ts-route-service_{cell_fault}" / "1"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(c), str(target))
        shutil.rmtree(c.parent)
        _ensure_millis(target)
    # RE3-SS: header-only traces + root_cause.txt; second case without traces
    c = _case(ms, dst, "SS", "carts", "cpu", 1, 5, subset="RE3")
    target = c.parent.parent / "carts_f1" / "1"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(c), str(target)); shutil.rmtree(c.parent)
    (target / "traces.csv").write_text(TRACE_HEADER, encoding="utf-8")
    (target / "root_cause.txt").write_text("CANARY_ROOT_CAUSE_LINE carts failed to write order\n", encoding="utf-8")
    c = _case(ms, dst, "SS", "carts", "cpu", 2, 6, subset="RE3")
    target2 = target.parent / "2"
    shutil.move(str(c), str(target2)); shutil.rmtree(c.parent)
    # RE2-SS: natural absence of traces
    _case(ms, dst, "SS", "orders", "mem", 1, 7)
    for logs in dst.rglob("logs.csv"):
        _log_hhmm(logs)
    return dst


def _log_hhmm(p: Path) -> None:
    """Give the logs `time` column the HH:MM (UTC) of `timestamp`, as the real files carry."""
    import pandas as pd
    df = pd.read_csv(p)
    df["time"] = pd.to_datetime(df["timestamp"], unit="ns", utc=True).dt.strftime("%H:%M")
    df.to_csv(p, index=False)


def _with_millis(lines):
    head = lines[0].split(",")
    out = [TRACE_HEADER.strip()]
    for r in lines[1:]:
        v = r.split(",")
        rec = dict(zip(head, v))
        st = int(rec["startTime"])
        out.append(",".join([rec.get("time", "00:00"), rec["traceID"], rec["spanID"], rec["serviceName"], rec.get("methodName", ""),
                             rec.get("operationName", ""), str(st // 1000), str(st), rec["duration"], rec.get("statusCode", ""),
                             rec.get("parentSpanID", "")]))
    return out


def _ensure_millis(case: Path) -> None:
    p = case / "traces.csv"
    if p.exists():
        lines = p.read_text(encoding="utf-8").splitlines()
        if "startTimeMillis" not in lines[0]:
            p.write_text("\n".join(_with_millis(lines)) + "\n", encoding="utf-8")


def rcaeval_zips(dst: Path, edit=None) -> Path:
    """Zip each `RE*-*` directory of `rcaeval_tree` into `<dst>/zenodo-test/RE*-*.zip`; `edit(tree)` may
    change the tree before zipping."""
    tree = rcaeval_tree(dst / "_tree")
    if edit:
        edit(tree)
    out = dst / "zenodo-test"
    out.mkdir(parents=True, exist_ok=True)
    for d in sorted(tree.iterdir()):
        with zipfile.ZipFile(out / f"{d.name}.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(d.rglob("*")):
                arc = f"{d.name}/{f.relative_to(d).as_posix()}" + ("/" if f.is_dir() else "")
                if f.is_dir():
                    z.writestr(arc, b"")
                else:
                    z.write(f, arc)
    shutil.rmtree(tree)
    return out


# ---------------------------------------------------------------- Nezha
NEZHA_OB_PODS = ["frontend-579b9bff58-t2dbm", "cartservice-579f59597d-wc2lz", "adservice-5f6585d649-fnmft"]
NEZHA_TT_PODS = ["ts-contacts-service-866bd68c97-xcqfx", "ts-gateway-service-6f6cfc45b-d9pnv"]


def _utc(s: str) -> int:
    from datetime import datetime, timezone
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())


def _go_time(ts: float) -> str:
    from datetime import datetime, timezone
    d = datetime.fromtimestamp(int(ts), timezone.utc)
    return f"{d:%Y-%m-%d %H:%M:%S}.{int(round((ts % 1) * 1e9)):09d} +0000 UTC m=+0.1"


def _nezha_day(root: Path, date: str, pods: list[str], faults: dict, t0: int, t1: int, seed: int,
               stamp_offset_pod: str | None = None, broken_log_minute: int | None = None,
               torn_log_minute: int | None = None, sentinel_log_minute: int | None = None) -> None:
    import csv
    import json
    rnd = random.Random(seed)
    d = root / date
    for sub in ("metric", "log", "trace"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    (d / f"{date}-fault_list.json").write_text(json.dumps(faults, indent=4), encoding="utf-8")
    hdr = ["Time", "TimeStamp", "PodName", "CpuUsageRate(%)", "MemoryUsage(Mi)", "PodServerLatencyP90(s)"]
    for p in pods:
        with open(d / "metric" / f"{p}_metric.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(hdr)
            for k, t in enumerate(range(t0, t1, 60)):
                ts = t + 0.25 + k * 1e-3
                stamp = int(ts) + (200_000_000 if p == stamp_offset_pod else 0)
                w.writerow([_go_time(ts), stamp, p, f"{rnd.uniform(1, 5):.4f}", f"{rnd.uniform(100, 110):.2f}",
                            f"{rnd.uniform(0.01, 0.02):.4f}"])
    with open(d / "metric" / "front_service.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Time", "TimeStamp", "ServiceName", "SuccessRate(%)", "LatencyP90(s)"])
        for t in range(t0, t1, 60):
            w.writerow([_go_time(t + 0.5), t, "Frontend", 100, f"{rnd.uniform(0.1, 0.2):.3f}"])
    (d / "metric" / "dependency.csv").write_text(f"Source,Target,Weight\n{pods[0]},{pods[1]},1\n", encoding="utf-8")
    day0 = _utc(f"{date} 00:00:00")
    for t in range(t0, t1, 60):
        mins = (t - day0) // 60
        name = f"{mins // 60:02d}_{mins % 60:02d}"
        with open(d / "log" / f"{name}_log.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Timestamp", "TimeUnixNano", "Node", "PodName", "Container", "TraceID", "SpanID", "Log"])
            for j, p in enumerate(pods):
                ns = (t + 5 + j) * 10**9 + 123
                if p.startswith("ts-"):
                    level = "ERROR" if j else "INFO"
                    inner = f"19:00:00.000 {level}  t.s.Impl#1 TraceID: a{j} SpanID: b{j} [op][done]\n"
                else:
                    inner = json.dumps({"message": f"request {j} complete", "severity": "info"}) + "\n"
                log = json.dumps({"log": inner, "stream": "stdout", "time": "x"})
                if broken_log_minute is not None and mins == broken_log_minute and j == 0:
                    log = "not-json " + inner.strip()
                row = [f"{date}T00:00:00Z", ns, "1.1.1.1", p, "server", f"tr{t}{j}", f"sp{t}{j}", log]
                if sentinel_log_minute is not None and mins == sentinel_log_minute and j == 1:
                    # overflowed TimeUnixNano as in the real TT logs; Timestamp (UTC, ms, no Z) is right
                    from datetime import datetime, timezone
                    row[0] = datetime.fromtimestamp(t + 5 + j, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + ".295"
                    row[1] = "-6795364578871345152"
                if torn_log_minute is not None and mins == torn_log_minute and j == 0:
                    row += ['ulate distance][time: 175]\\n","stream":"stdout"}', ""]   # tail of another row
                w.writerow(row)
        with open(d / "trace" / f"{name}_trace.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["TraceID", "SpanID", "ParentID", "PodName", "OperationName", "StartTimeUnixNano",
                        "EndTimeUnixNano", "Duration"])
            for j, p in enumerate(pods):
                st = (t + 10 + j) * 10**9 + 777
                dur_us = rnd.randint(1000, 9000)
                w.writerow([f"tr{t}", f"s{t}{j}", "root" if j == 0 else f"s{t}0", p, f"op{j}", st, st + dur_us * 1000 + 321, dur_us])


def nezha_tree(dst: Path) -> Path:
    """Nezha-shaped `rca_data` and `construct_data` under `dst`: one OB day with two incidents 8 minutes
    apart (the second with `inject_timestamp` 8 h early), a pod whose `TimeStamp` is +2e8 s off and a
    non-JSON log row; one TT day whose minute files end 3 minutes after the incident (clipped window)
    and whose 11:40 log file has one row with two extra fields (a torn write, as in the real 2023-01-29 10:06 file)
    and whose 11:45 log file has one row with an overflowed TimeUnixNano and a valid Timestamp."""
    import json
    root = dst / "rca_data"
    ob = {"03": [{"inject_time": "2022-08-22 03:53:54", "inject_timestamp": str(_utc("2022-08-22 03:53:54")),
                  "inject_pod": NEZHA_OB_PODS[1], "inject_type": "cpu_contention"}],
          "04": [{"inject_time": "2022-08-22 04:01:54", "inject_timestamp": str(_utc("2022-08-22 04:01:54") - 28800),
                  "inject_pod": NEZHA_OB_PODS[0], "inject_type": "return"}]}
    _nezha_day(root, "2022-08-22", NEZHA_OB_PODS, ob, _utc("2022-08-22 03:20:00"), _utc("2022-08-22 04:40:00"), 1,
               stamp_offset_pod=NEZHA_OB_PODS[2], broken_log_minute=3 * 60 + 50)
    tt = {"11": [{"inject_time": "2023-01-30 11:51:46", "inject_timestamp": str(_utc("2023-01-30 11:51:46")),
                  "inject_pod": NEZHA_TT_PODS[0], "inject_type": "network_delay"}]}
    _nezha_day(root, "2023-01-30", NEZHA_TT_PODS, tt, _utc("2023-01-30 11:20:00"), _utc("2023-01-30 11:55:00"), 2,
               torn_log_minute=11 * 60 + 40, sentinel_log_minute=11 * 60 + 45)
    cd = dst / "construct_data"
    cd.mkdir(parents=True, exist_ok=True)
    (cd / "root_cause_hipster.json").write_text(json.dumps({"cartservice": {"cpu_contention": "CpuUsageRate(%)"}}), encoding="utf-8")
    (cd / "root_cause_ts.json").write_text(json.dumps({"ts-contacts-service": {"network_delay": "NetworkP90(ms)"}}), encoding="utf-8")
    return root
