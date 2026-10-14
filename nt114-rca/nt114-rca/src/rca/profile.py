"""Read-only profiler of the raw datasets.

  python -m rca.profile --source rcaeval-zenodo      # writes data/reports/profile/<source>.json
  python -m rca.profile --matrix                     # writes data/reports/compatibility-matrix.json

Archives are read in place: zip members through `zipfile`, tar.gz members as a stream
(`tarfile.open(mode="r|gz")`) into memory up to a byte cap. Nothing is extracted to disk and no
code from the raw data is executed.
"""
from __future__ import annotations

import argparse
import collections
import csv
import io
import json
import math
import re
import statistics
import sys
import tarfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .identity import pod_pattern
from .store import read_json, write_json_atomic

RCA_ROOT = Path(__file__).resolve().parents[2]
UNIT_RANGES = {"s": (1.4e9, 1.95e9), "ms": (1.4e12, 1.95e12), "us": (1.4e15, 1.95e15), "ns": (1.4e18, 1.95e18)}
UNIT_NS = {"s": 10**9, "ms": 10**6, "us": 10**3, "ns": 1}


# ---------------------------------------------------------------- inference helpers
def parse_iso_ns(s: str) -> int | None:
    """ISO-8601 or Go-style ('2022-08-22 03:51:19.607158889 +0000 UTC m=+0.11') timestamp -> ns UTC."""
    s = str(s).strip()
    m = re.match(r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))?\s*(Z|[+-]\d{2}:?\d{2})?", s)
    if not m:
        return None
    date, hh, mm, ss, frac, tz = m.groups()
    dt = datetime.strptime(f"{date} {hh}:{mm}:{ss}", "%Y-%m-%d %H:%M:%S")
    off = 0
    if tz and tz != "Z":
        sign = -1 if tz[0] == "-" else 1
        digits = tz[1:].replace(":", "")
        off = sign * (int(digits[:2]) * 3600 + int(digits[2:]) * 60)
    secs = int(dt.replace(tzinfo=timezone.utc).timestamp()) - off
    return secs * 10**9 + int((frac or "0").ljust(9, "0"))


def classify_time_unit(values) -> str:
    """'s' | 'ms' | 'us' | 'ns' by magnitude (2014-2031 epoch range), 'iso8601', or 'unknown'."""
    nums, strs = [], 0
    for v in values:
        if v is None or v == "":
            continue
        try:
            nums.append(float(v))
        except (TypeError, ValueError):
            strs += parse_iso_ns(v) is not None
    if nums:
        med = statistics.median(nums)
        for unit, (lo, hi) in UNIT_RANGES.items():
            if lo <= med < hi:
                return unit
        return "unknown"
    return "iso8601" if strs else "unknown"


def to_ns(value, unit: str) -> int | None:
    if value is None or value == "":
        return None
    if unit == "iso8601":
        return parse_iso_ns(value)
    try:
        return int(round(float(value) * UNIT_NS[unit])) if unit != "ns" else int(value)
    except (TypeError, ValueError, KeyError):
        return None


def constant_offset_s(a_ns, b_ns, tol_s: float = 60.0) -> dict:
    """Compare two time columns: {'pairs', 'median_offset_s', 'constant': bool, 'distinct_offsets_s'}."""
    diffs = [(b - a) / 1e9 for a, b in zip(a_ns, b_ns) if a is not None and b is not None]
    if not diffs:
        return {"pairs": 0, "median_offset_s": None, "constant": False, "distinct_offsets_s": []}
    med = statistics.median(diffs)
    const = all(abs(d - med) <= tol_s for d in diffs)
    distinct = sorted({round(d / 1e6) * 1e6 if abs(d) >= 1e6 else round(d) for d in diffs})[:10]
    return {"pairs": len(diffs), "median_offset_s": med, "constant": const, "distinct_offsets_s": distinct}


def iter_tar_stream(path: Path, want=lambda name: False, max_bytes: int = 64 << 20):
    """Stream a tar.gz; yield (TarInfo, bytes|None). Bytes are read into memory only for members
    where want(name) is true and size <= max_bytes. Never writes to disk."""
    with tarfile.open(path, mode="r|gz") as t:
        for m in t:
            data = None
            if m.isfile() and want(m.name) and m.size <= max_bytes:
                f = t.extractfile(m)
                data = f.read() if f is not None else None
            yield m, data


def csv_head(raw: io.BufferedIOBase, n: int = 1000) -> tuple[list[str], list[list[str]]]:
    text = io.TextIOWrapper(raw, encoding="utf-8", errors="replace", newline="")
    r = csv.reader(text)
    header = next(r, [])
    rows = []
    for i, row in enumerate(r):
        if i >= n:
            break
        rows.append(row)
    return header, rows


def column_profile(header, rows) -> dict:
    out = {}
    for j, h in enumerate(header):
        vals = [r[j] if j < len(r) else "" for r in rows]
        nonnull = [v for v in vals if v not in ("", "nan", "NaN", "None")]
        num = 0
        for v in nonnull:
            try:
                float(v)
                num += 1
            except ValueError:
                pass
        out[h] = {"null_rate": round(1 - len(nonnull) / max(len(vals), 1), 4),
                  "type": "numeric" if nonnull and num == len(nonnull) else ("string" if nonnull else "empty"),
                  "time_unit": classify_time_unit(nonnull[:200]) if re.search(r"time|ts|stamp", h, re.I) else None}
    return out


def _counter(c) -> dict:
    return dict(sorted(collections.Counter(c).items()))


# ---------------------------------------------------------------- grouping (split feasibility)
def count_groups(items: list[dict], pre_s: int = 600, post_s: int = 300, rule: str = "physical") -> dict:
    """items: {key, stream, anchor_s, cell}. Union-find over overlapping evidence windows within a
    stream (physical), plus equal cell (cell rule)."""
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    by_stream = collections.defaultdict(list)
    for i, it in enumerate(items):
        by_stream[it["stream"]].append(i)
    for idx in by_stream.values():
        idx.sort(key=lambda i: items[i]["anchor_s"])
        for a, b in zip(idx, idx[1:]):
            if items[b]["anchor_s"] - pre_s <= items[a]["anchor_s"] + post_s:
                union(a, b)
    if rule == "cell":
        first = {}
        for i, it in enumerate(items):
            if it["cell"] in first:
                union(first[it["cell"]], i)
            else:
                first[it["cell"]] = i
    sizes = collections.Counter(find(i) for i in range(len(items)))
    return {"groups": len(sizes), "largest_group": max(sizes.values()) if sizes else 0,
            "singletons": sum(1 for v in sizes.values() if v == 1)}


def feasibility(n_incidents: int, phys: dict, cell: dict) -> dict:
    def ok(g):
        return g["groups"] >= 20 and (1 - g["largest_group"] / max(n_incidents, 1)) >= 0.10
    return {"within-grouped": ok(cell), "within-retrieval": ok(phys), "eval-only": n_incidents > 0}


# ---------------------------------------------------------------- RCAEval (Zenodo)
RCAEVAL_CELL = re.compile(r"^(?P<svc>.+?)_(?P<fault>cpu|mem|disk|delay|loss|socket|f[1-5])(?:_(?P<batch>\d+))?$")
SYS = {"OB": "online-boutique", "SS": "sock-shop", "TT": "train-ticket"}


def profile_rcaeval(raw: Path, sample_every: int = 20) -> dict:
    base = raw / "rcaeval-zenodo" / "zenodo-14590730"
    out = {"source_id": "rcaeval-zenodo", "zips": {}, "column_sets": {}, "time_units": {}, "duplicates": [],
           "non_service_metric_prefixes": {}, "trace_time_check": {}, "unparseable_cells": [], "label_artifacts": [],
           "largest_member_bytes": 0, "pre_window_s": {}}
    colsets = collections.defaultdict(collections.Counter)
    units = collections.defaultdict(collections.Counter)
    items, sample_i = [], 0
    ttc = {"rows_checked": 0, "mismatch_rows": 0, "cases_checked": 0}
    pre_window = []
    for zp in sorted(base.glob("RE*.zip")):
        subset, sysc = zp.stem.split("-")
        z = zipfile.ZipFile(zp)
        infos = {i.filename: i for i in z.infolist() if not i.is_dir()}
        out["largest_member_bytes"] = max(out["largest_member_bytes"], max(i.file_size for i in infos.values()))
        cases = sorted(n.rsplit("/", 1)[0] for n in infos if n.endswith("/inject_time.txt"))
        mods = collections.Counter()
        prefixes_metric, prefixes_tel = set(), set()
        for cdir in cases:
            files = {n.rsplit("/", 1)[1]: i for n, i in infos.items() if n.rsplit("/", 1)[0] == cdir}
            _, cell, inst = cdir.split("/")
            m = RCAEVAL_CELL.match(cell)
            if not m:
                out["unparseable_cells"].append(cdir)
            if "root_cause.txt" in files:
                out["label_artifacts"].append(f"{zp.name}!{cdir}/root_cause.txt")
            t_inj = int(float(z.read(f"{cdir}/inject_time.txt").decode().split()[0]))
            if not inst.isdigit():
                sib = [c for c in cases if c.startswith(f"{subset}-{sysc}/{cell}/") and c != cdir]
                same = [c for c in sib if z.read(f"{c}/inject_time.txt") == z.read(f"{cdir}/inject_time.txt")]
                out["duplicates"].append({"case": f"{zp.name}!{cdir}", "same_inject_time_as": same,
                                          "inject_time": t_inj})
                continue
            present = []
            for mod, names in (("metrics", ("metrics.csv", "data.csv")), ("logs", ("logs.csv",)), ("traces", ("traces.csv",))):
                hit = next((n for n in names if n in files), None)
                if hit is None:
                    continue
                hdr, rows = csv_head(z.open(files[hit]), 300 if mod != "metrics" else 30)
                if mod != "metrics":
                    colsets[f"{subset}/{mod}"][",".join(hdr)] += 1
                    for c, p in column_profile(hdr, rows).items():
                        if p["time_unit"]:
                            units[f"{mod}.{c}"][p["time_unit"]] += 1
                    if mod == "logs" and "container_name" in hdr:
                        j = hdr.index("container_name")
                        prefixes_tel |= {r[j] for r in rows if len(r) > j}
                    if mod == "traces" and "serviceName" in hdr:
                        j = hdr.index("serviceName")
                        prefixes_tel |= {r[j] for r in rows if len(r) > j}
                else:
                    prefixes_metric |= {c.split("_", 1)[0] for c in hdr if c != "time" and "_" in c}
                    if rows:
                        j = hdr.index("time")
                        first = float(rows[0][j])
                        pre_window.append(t_inj - first)
                present.append(mod if rows else f"{mod}:empty")
            mods[",".join(present)] += 1
            if "traces.csv" in files and files["traces.csv"].file_size > 200:
                sample_i += 1
                if sample_i % sample_every == 1:
                    ttc["cases_checked"] += 1
                    hdr, rows = csv_head(z.open(files["traces.csv"]), 10**9)
                    a, b = hdr.index("startTimeMillis"), hdr.index("startTime")
                    for r in rows:
                        ttc["rows_checked"] += 1
                        try:
                            if int(float(r[a])) != int(float(r[b])) // 1000:
                                ttc["mismatch_rows"] += 1
                        except (ValueError, IndexError):
                            ttc["mismatch_rows"] += 1
            if m:
                items.append({"key": f"{subset}-{sysc}/{cell}/{inst}", "stream": f"{subset}-{sysc}", "anchor_s": t_inj,
                              "cell": f"L1/{SYS[sysc]}/{m['svc']}/{m['fault']}"})
        out["zips"][zp.name] = {"cases": len(cases), "modality_sets": dict(mods)}
        out["non_service_metric_prefixes"][f"{subset}-{sysc}"] = sorted(prefixes_metric - prefixes_tel) if prefixes_tel else []
    out["column_sets"] = {k: dict(v) for k, v in colsets.items()}
    out["time_units"] = {k: dict(v) for k, v in units.items()}
    out["trace_time_check"] = ttc
    pw = sorted(pre_window)
    out["pre_window_s"] = {"min": pw[0], "median": statistics.median(pw), "lt_300": sum(x < 300 for x in pw)} if pw else {}
    n = len(items)
    phys, cell = count_groups(items, rule="physical"), count_groups(items, rule="cell")
    out["incidents"] = n
    out["split_feasibility"] = {"physical": phys, "cell": cell, "feasible": feasibility(n, phys, cell)}
    out["registry_rows"] = _registry_count("rcaeval-zenodo")
    return out


def _registry_count(source_id: str) -> int:
    p = RCA_ROOT / "data" / "manifests" / "incidents.jsonl"
    with open(p, encoding="utf-8") as f:
        return sum(1 for line in f if json.loads(line)["source_id"] == source_id)


# ---------------------------------------------------------------- Nezha
def profile_nezha(raw: Path) -> dict:
    base = raw / "nezha" / "git-d8140101fdb4" / "rca_data"
    out = {"source_id": "nezha", "dates": {}, "metric_time_offset": {}, "duration_unit": {}, "pod_patterns": {},
           "incidents_window_rows": [], "largest_member_bytes": 0}
    items, offsets, dur = [], collections.Counter(), collections.Counter()
    for d in sorted(p for p in base.iterdir() if p.is_dir()):
        with open(d / f"{d.name}-fault_list.json", encoding="utf-8") as f:
            fl = json.load(f)
        incs = [e for hour in sorted(fl) for e in fl[hour]]
        pods = collections.Counter(e["inject_pod"] for e in incs)
        system = "online-boutique" if d.name.startswith("2022") else "train-ticket"
        anchor_mismatch = sum(parse_iso_ns(e["inject_time"] + "Z") // 10**9 != int(e["inject_timestamp"]) for e in incs)
        out["dates"][d.name] = {"incidents": len(incs), "system": system, "inject_types": _counter(e["inject_type"] for e in incs),
                                "inject_time_vs_timestamp_mismatch": anchor_mismatch,
                                "inject_timestamp_minus_inject_time_s": _counter(
                                    int(e["inject_timestamp"]) - parse_iso_ns(e["inject_time"] + "Z") // 10**9 for e in incs),
                                "inject_pod_patterns": _counter(pod_pattern(p) for p in pods)}
        # metric files: Time string vs TimeStamp; per-minute row counts keyed by the Time string
        metric_minutes = collections.Counter()
        for mf in sorted((d / "metric").glob("*.csv")):
            out["largest_member_bytes"] = max(out["largest_member_bytes"], mf.stat().st_size)
            with open(mf, "rb") as f:
                hdr, rows = csv_head(f, 10**6)
            if "Time" in hdr:
                ti = hdr.index("Time")
                for r in rows:
                    ns = parse_iso_ns(r[ti]) if len(r) > ti else None
                    if ns is not None:
                        metric_minutes[ns // (60 * 10**9)] += 1
            if "Time" in hdr and "TimeStamp" in hdr:
                a, b = hdr.index("Time"), hdr.index("TimeStamp")
                res = constant_offset_s([parse_iso_ns(r[a]) for r in rows], [int(float(r[b])) * 10**9 for r in rows if r[b]])
                key = "none" if res["median_offset_s"] is not None and abs(res["median_offset_s"]) <= 60 else \
                      f"{res['median_offset_s']:.0f}s" if res["median_offset_s"] is not None else "unknown"
                offsets[(d.name, key, res["constant"])] += 1
            pod = mf.name.removesuffix("_metric.csv")
            out["pod_patterns"][pod_pattern(pod)] = out["pod_patterns"].get(pod_pattern(pod), 0) + 1
        # traces: Duration unit
        for tf in sorted((d / "trace").glob("*.csv"))[:5]:
            with open(tf, "rb") as f:
                hdr, rows = csv_head(f, 2000)
            s, e, du = hdr.index("StartTimeUnixNano"), hdr.index("EndTimeUnixNano"), hdr.index("Duration")
            for r in rows:
                try:
                    span_ns, v = int(r[e]) - int(r[s]), float(r[du])
                except ValueError:
                    continue
                if span_ns > 0:
                    ratio = span_ns / max(v, 1e-9)
                    dur[min(("ns", 1), ("us", 1e3), ("ms", 1e6), key=lambda u: abs(math.log10(max(ratio, 1e-12)) - math.log10(u[1])))[0]] += 1
        # rows per incident in [t-600, t+300]
        minute_rows = {}
        for kind in ("log", "trace"):
            for fp in (d / kind).glob("*.csv"):
                hh, mm = fp.name.split("_")[:2]
                with open(fp, "rb") as f:
                    minute_rows[(kind, int(hh), int(mm))] = sum(1 for _ in f) - 1
                out["largest_member_bytes"] = max(out["largest_member_bytes"], fp.stat().st_size)
        day0 = parse_iso_ns(f"{d.name}T00:00:00Z") // 10**9
        for e in incs:
            # anchor: the inject_time string read as UTC; it matches the hour keys, the minute file names and
            # the metric Time strings, while inject_timestamp is about -8 h on 2023-01-29
            t = parse_iso_ns(e["inject_time"] + "Z") // 10**9
            row = {"date": d.name, "inject_pod": e["inject_pod"], "anchor_s": t}
            for kind in ("log", "trace"):
                n = 0
                for s_ in range(t - 600, t + 301, 60):
                    mins = (s_ - day0) // 60
                    n += minute_rows.get((kind, mins // 60, mins % 60), 0)
                row[f"{kind}_rows_approx"] = n
            row["metric_rows_approx"] = sum(metric_minutes.get(m, 0) for m in range((t - 600) // 60, (t + 300) // 60 + 1))
            out["incidents_window_rows"].append(row)
            items.append({"key": f"{d.name}/{t}", "stream": d.name, "anchor_s": t,
                          "cell": f"L4/{system}/{e['inject_pod'].rsplit('-', 2)[0]}/{e['inject_type']}"})
    out["metric_time_offset"] = [{"date": k[0], "offset": k[1], "constant": k[2], "files": v} for k, v in sorted(offsets.items())]
    out["duration_unit"] = dict(dur)
    n = len(items)
    phys, cell = count_groups(items, rule="physical"), count_groups(items, rule="cell")
    gaps = []
    for s in {i["stream"] for i in items}:
        a = sorted(i["anchor_s"] for i in items if i["stream"] == s)
        gaps += [y - x for x, y in zip(a, a[1:])]
    out["incidents"] = n
    out["anchor_gap_s"] = {"min": min(gaps), "median": statistics.median(gaps), "max": max(gaps)}
    out["split_feasibility"] = {"physical": phys, "cell": cell, "feasible": feasibility(n, phys, cell)}
    out["registry_rows"] = _registry_count("nezha")
    w = out["incidents_window_rows"]
    mlt = sum(1 for r in w if r["metric_rows_approx"] and r["log_rows_approx"] and r["trace_rows_approx"])
    out["gate"] = {"window_mlt": mlt, "window_mlt_share": round(mlt / max(len(w), 1), 4), "threshold": 0.95,
                   "metric_time_rule": "Time string; TimeStamp is not used (see metric_time_offset)",
                   "result": "pass" if mlt / max(len(w), 1) >= 0.95 else "fail"}
    return out


# ---------------------------------------------------------------- AIOps2025 + RCA100 (AgenticOpsEval)
def _parquet_time_stats(data: bytes) -> dict:
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(io.BytesIO(data))
    sch = pf.schema_arrow
    out = {"columns": [f"{f.name}:{f.type}" for f in sch], "rows": pf.metadata.num_rows, "time": {}}
    leaf = {pf.metadata.schema.column(i).path: i for i in range(pf.metadata.num_columns)}
    for f in sch:
        # statistics are per leaf column; only flat (top-level, non-nested) time columns are read
        j = leaf.get(f.name)
        if j is None or not re.search(r"time|stamp", f.name, re.I):
            continue
        lo = hi = None
        for rg in range(pf.metadata.num_row_groups):
            st = pf.metadata.row_group(rg).column(j).statistics
            if st is None or not st.has_min_max:
                continue
            lo = st.min if lo is None else min(lo, st.min)
            hi = st.max if hi is None else max(hi, st.max)
        if lo is not None:
            out["time"][f.name] = {"min": str(lo), "max": str(hi)}
    return out


def profile_aiops2025(raw: Path, all_archives: bool = True) -> dict:
    base = raw / "agenticopseval" / "gitlab-69cf36430b43" / "AIOps2025"
    with open(base / "groundtruth.jsonl", encoding="utf-8") as f:
        gt = [json.loads(line) for line in f if line.strip()]
    with open(base / "input.json", encoding="utf-8") as f:
        inp = json.load(f)
    out = {"source_id": "agenticopseval", "subset": "AIOps2025", "incidents": len(gt),
           "instance_type": _counter(g["instance_type"] for g in gt),
           "instance_is_list": sum(isinstance(g["instance"], list) for g in gt),
           "multi_service_with_named_service": sum(isinstance(g["instance"], list) and len({str(x).rsplit('-', 1)[0] for x in g["instance"]}) > 1 and bool(g["service"]) for g in gt),
           "multi_service_without_named_service": sum(isinstance(g["instance"], list) and len({str(x).rsplit('-', 1)[0] for x in g["instance"]}) > 1 and not g["service"] for g in gt),
           "input_uuids_match": sorted(i["uuid"] for i in inp) == sorted(g["uuid"] for g in gt),
           "fault_types": _counter(g["fault_type"] for g in gt), "archives": {}, "member_samples": {},
           "largest_member_bytes": 0}
    archives = sorted(base.glob("*.tar.gz")) if all_archives else sorted(base.glob("*.tar.gz"))[:1]
    hour_ranges = []   # (archive, kind, file_hour_label, min_ns, max_ns)
    for ap in archives:
        day = ap.name[:10]
        stats = collections.Counter()

        def want(n, _seen=out["member_samples"]):
            b = n.rsplit("/", 1)[-1]
            if b.startswith("._"):
                return False
            if "/trace-parquet/" in n or "/log-parquet/" in n:
                return True
            return "/metric-parquet/" in n and len(_seen) < 6 and "apm/pod" in n
        for m, data in iter_tar_stream(ap, want=want, max_bytes=1 << 30):
            b = m.name.rsplit("/", 1)[-1]
            stats["appledouble" if b.startswith("._") else ("file" if m.isfile() else "other")] += 1
            out["largest_member_bytes"] = max(out["largest_member_bytes"], m.size)
            if data is None:
                continue
            st = _parquet_time_stats(data)
            kind = "trace" if "/trace-parquet/" in m.name else "log" if "/log-parquet/" in m.name else "metric"
            if kind not in out["member_samples"] or (kind == "metric" and len(out["member_samples"]) < 6):
                out["member_samples"].setdefault(kind, {"member": m.name, **st})
            hm = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{2})-\d{2}-\d{2}", b)
            for col, mm in st["time"].items():
                lo, hi = _to_ns_guess(mm["min"]), _to_ns_guess(mm["max"])
                if lo and hi and hm:
                    hour_ranges.append((day, kind, f"{hm[1]}T{hm[2]}", col, lo, hi))
        out["archives"][ap.name] = dict(stats)
    # time zone of hourly file names: offset between the name hour and the UTC min timestamp
    tz = collections.Counter()
    for day, kind, label, col, lo, hi in hour_ranges:
        name_ns = parse_iso_ns(label + ":00:00Z")
        tz[(kind, col, round((name_ns - lo) / 3.6e12))] += 1
    out["hourly_name_minus_utc_hours"] = [{"kind": k[0], "column": k[1], "offset_h": k[2], "files": v} for k, v in sorted(tz.items())]
    # coverage of each labelled window by the union of hourly member time ranges (per kind)
    cov = collections.Counter()
    uncovered = []
    spans = collections.defaultdict(list)
    for day, kind, label, col, lo, hi in hour_ranges:
        spans[kind].append((lo, hi, day))
    for g in gt:
        s, e = parse_iso_ns(g["start_time"]), parse_iso_ns(g["end_time"])
        hit = {k: sorted({d for lo, hi, d in v if lo <= e and hi >= s}) for k, v in spans.items()}
        ok = all(hit.get(k) for k in ("trace", "log"))
        cov["covered" if ok else "uncovered"] += 1
        cov[f"archives_{max((len(v) for v in hit.values()), default=0)}"] += 1
        if not ok:
            uncovered.append({"uuid": g["uuid"], "start_time": g["start_time"]})
    out["window_coverage"] = dict(cov)
    out["uncovered_windows"] = uncovered
    offs = {o["offset_h"] for o in out["hourly_name_minus_utc_hours"]}
    out["gate"] = {"archive_name_tz_offset_h": sorted(offs), "tz_determined": len(offs) == 1,
                   "covered": cov["covered"], "natural_absent": cov["uncovered"],
                   "result": "pass" if len(offs) == 1 else "fail",
                   "rule": "a window is covered when both log and trace hourly members overlap it; "
                           "uncovered windows are natural_absent (REJECT NO_TELEMETRY)"}
    items = [{"key": g["uuid"], "stream": "aiops2025", "anchor_s": parse_iso_ns(g["start_time"]) // 10**9,
              "cell": f"L2/aiops2025/{g['service'] or g['instance']}/{g['fault_type']}"} for g in gt if g["instance_type"] != "node"]
    n = len(items)
    phys, cell = count_groups(items, rule="physical"), count_groups(items, rule="cell")
    out["split_feasibility_A"] = {"incidents": n, "physical": phys, "cell": cell, "feasible": feasibility(n, phys, cell)}
    return out


def _to_ns_guess(v: str) -> int | None:
    try:
        x = float(v)
    except ValueError:
        return parse_iso_ns(v)
    for unit, (lo, hi) in UNIT_RANGES.items():
        if lo <= x < hi:
            return int(x * UNIT_NS[unit])
    return None


def profile_rca100(raw: Path) -> dict:
    base = raw / "agenticopseval" / "gitlab-69cf36430b43" / "RCA100"
    mapping = read_json(base / "answer_key" / "mapping.json")["task_to_case_id"]
    kinds, resolvable, per_case = collections.Counter(), 0, []
    for tdir in sorted((base / "cases").iterdir()):
        topo = read_json(tdir / "topology.json")
        svc_names = {e["name"] for e in topo.get("entities", []) if e.get("type") == "apm.service"}
        all_names = {e["name"]: e.get("type") for e in topo.get("entities", [])}
        gt = read_json(base / "answer_key" / f"{tdir.name}.gt.json")
        ents = gt.get("root_cause_entities", [])
        res = []
        for ent in ents:
            k = "apm.service" if ent in svc_names else all_names.get(ent, "not-in-topology")
            kinds[k] += 1
            res.append(ent in svc_names or str(ent).split("::")[0] in svc_names)
        ok = bool(ents) and all(res)
        resolvable += ok
        per_case.append({"task": tdir.name, "case_prefix": mapping.get(tdir.name, "").split(".")[0],
                         "entities": ents, "service_resolvable": ok, "n_services_in_topology": len(svc_names)})
    n = len(per_case)
    return {"source_id": "agenticopseval", "subset": "RCA100", "incidents": n, "entity_kinds": dict(kinds),
            "service_resolvable": resolvable, "service_resolvable_share": round(resolvable / max(n, 1), 4),
            "gate_threshold": 0.8, "gate": "pass" if resolvable / max(n, 1) >= 0.8 else "fail", "cases": per_case}


# ---------------------------------------------------------------- auxiliary
def profile_cloud_opsbench(raw: Path) -> dict:
    base = raw / "cloud-opsbench" / "hf-1a02e54329cc"
    with open(base / "index.jsonl", encoding="utf-8") as f:
        idx = [json.loads(line) for line in f if line.strip()]
    kinds = _counter(r["fault_object"].split("/")[0] for r in idx)
    sample = idx[0]
    case = base / sample["metadata_path"].rsplit("/", 1)[0]
    files = sorted(p.relative_to(case).as_posix() for p in case.rglob("*") if p.is_file())
    meta = read_json(case / "metadata.json")
    mcsv = sum(1 for r in idx if (base / r["metadata_path"].rsplit("/", 1)[0] / "raw_data" / "metrics.csv").exists())
    return {"source_id": "cloud-opsbench", "incidents": len(idx), "systems": _counter(r["system"] for r in idx),
            "fault_object_kinds": kinds, "categories": _counter(r["category"] for r in idx),
            "cases_with_metrics_csv": mcsv, "sample_case_files": files, "metadata_keys": sorted(meta),
            "anchor_field_candidates": sorted(k for k in meta if "time" in k.lower()),
            "traces": "natural_absent (no trace files)", "registry_rows": _registry_count("cloud-opsbench")}


def profile_petshop(raw: Path) -> dict:
    base = raw / "petshop" / "git-2e96f937c4c0" / "dataset"
    targets = sorted(base.rglob("target.json"))
    nodes = collections.Counter()
    for t in targets:
        nodes[read_json(t)["root_cause"]["node"]] += 1
    hdr = []
    if targets:
        with open(targets[0].parent / "metrics.csv", "rb") as f:
            hdr, _ = csv_head(f, 5)
    return {"source_id": "petshop", "incidents": len(targets), "root_cause_nodes": dict(nodes),
            "splits": _counter(t.relative_to(base).parts[1] for t in targets),
            "metrics_columns_sample": hdr[:12], "modalities": ["metrics"], "registry_rows": _registry_count("petshop")}


def profile_dejavu(raw: Path) -> dict:
    base = raw / "dejavu" / "zenodo-6955909"
    out = {"source_id": "dejavu", "sets": {}}
    for zp in sorted(base.glob("*.zip")):
        z = zipfile.ZipFile(zp)
        fc = [n for n in z.namelist() if n.endswith("faults.csv") and "checkpoint" not in n]
        if not fc:
            continue
        hdr, rows = csv_head(z.open(fc[0]), 10**6)
        j = hdr.index("node_type") if "node_type" in hdr else None
        out["sets"][zp.stem] = {"incidents": len(rows), "columns": hdr,
                                "node_types": _counter(r[j] for r in rows) if j is not None else None,
                                "checkpoint_files_ignored": [n for n in z.namelist() if "checkpoint" in n]}
    out["incidents"] = sum(v["incidents"] for v in out["sets"].values())
    return out


def _zip_label_probe(zp: Path, pattern: str) -> dict:
    z = zipfile.ZipFile(zp)
    names = z.namelist()
    lab = [n for n in names if re.search(pattern, n, re.I) and not n.endswith("/")]
    sample = {}
    for n in lab[:2]:
        info = z.getinfo(n)
        if info.file_size < 2_000_000:
            sample[n] = z.read(n)[:1500].decode("utf-8", "replace")
    return {"archive": zp.name, "members": len(names), "label_like": len(lab), "label_like_examples": lab[:10], "samples": sample}


def profile_anomod(raw: Path) -> dict:
    zp = raw / "anomod" / "zenodo-18342898" / "AnoMod.zip"
    z = zipfile.ZipFile(zp)
    exps = sorted({n.split("/")[2] for n in z.namelist() if n.count("/") >= 3 and n.split("/")[1].endswith("_data")})
    probe = _zip_label_probe(zp, r"(label|ground|root_cause|fault_info|inject.*\.json)")
    return {"source_id": "anomod", "experiments": len(exps), "experiment_examples": exps[:12],
            "experiment_name_encodes_fault": True, **probe,
            # the label-like name matches are telemetry files of exception-injection runs, not labels
            "gate": "fail", "gate_reason": "no machine-readable root-cause service label; the fault is encoded only in experiment "
                                           "directory names, and the name-matched members are trace/event/API telemetry files"}


def profile_msds(raw: Path) -> dict:
    base = raw / "msds" / "zenodo-3549604"
    out = {"source_id": "msds", "archives": {}}
    for zp in sorted(base.glob("*.zip")):
        z = zipfile.ZipFile(zp)
        imp = [n for n in z.namelist() if n.endswith("IMPORTANT_experiment_start_end_data.txt")]
        out["archives"][zp.name] = {"members": len(z.namelist()),
                                    "experiment_file": imp[0] if imp else None,
                                    "experiment_file_head": z.read(imp[0])[:1200].decode("utf-8", "replace") if imp else None}
    out["gate"] = "fail"
    out["gate_reason"] = "experiment start/end times only; no per-incident root-cause service label"
    return out


def profile_rcabench(raw: Path, work: Path) -> dict:
    base = raw / "rcabench-fse26" / "zenodo-17105974"
    tgz = base / "rcabench-absolute_anomaly.tar.gz"
    part = work / "profile" / "rcabench-fse26.partial.jsonl"
    part.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if part.exists():
        with open(part, encoding="utf-8") as f:
            done = {json.loads(line)["name"] for line in f if line.strip()}
    want_re = re.compile(r"(label|fault|root|inject|ground|meta|conf)[^/]*\.(json|csv|ya?ml|txt)$", re.I)
    tops, n = collections.Counter(), 0
    with open(part, "a", encoding="utf-8", newline="\n") as fo:
        for m, data in iter_tar_stream(tgz, want=lambda name: bool(want_re.search(name)) and name not in done, max_bytes=5 << 20):
            n += 1
            tops["/".join(m.name.split("/")[:2])] += 1
            if data is not None:
                fo.write(json.dumps({"name": m.name, "size": m.size, "head": data[:800].decode("utf-8", "replace")}, ensure_ascii=False) + "\n")
    with open(part, encoding="utf-8") as f:
        labels = [json.loads(line) for line in f if line.strip()]
    cases = [k for k in tops if k.count("/") == 1]
    case_dirs = {k.split("/")[0] for k in cases}
    telemetry = {k.split("/")[0] for k in cases if re.search(r"/(abnormal|normal)_(logs|traces|metrics)\.parquet$", k)}
    # display_config is a JSON string inside injection.json; its injection_point names the target
    point_re = re.compile(r'injection_point\\?":\{([^}]*)\}')
    point_kind = {}
    for l in labels:
        m = point_re.search(l["head"]) if l["name"].endswith("/injection.json") else None
        if m:
            keys = set(re.findall(r'"?([A-Za-z_]+)\\?":', m.group(1)))
            point_kind[l["name"].split("/")[0]] = ("single_service" if keys & {"app_name", "app_label"} else
                                                    "service_pair" if {"source_service", "target_service"} <= keys else "other")
    labelled = {c for c, k in point_kind.items() if k != "other"}
    both = case_dirs & telemetry & labelled
    gate = {"cases": len(case_dirs), "cases_with_telemetry_parquet": len(telemetry & case_dirs),
            "injection_point_kinds": _counter(point_kind.values()), "cases_with_both": len(both),
            "rule": "per-case abnormal/normal logs|traces|metrics Parquet and an injection.json injection_point naming "
                    "a service (app_name/app_label) or a source/target service pair",
            "result": "pass" if case_dirs and len(both) == len(case_dirs) else "fail"}
    return {"source_id": "rcabench-fse26", "tar_members": n, "top_level_dirs": len(tops), "top_level_examples": list(tops)[:15],
            "label_like_members": len(labels), "label_like_examples": labels[:6], "case_like_dirs": len(cases), "gate": gate,
            "zips": {zp.name: _zip_label_probe(zp, r"\.(json|csv)$")["members"] for zp in sorted(base.glob("*.zip"))}}


SOURCES = {
    "rcaeval-zenodo": lambda raw, work: profile_rcaeval(raw),
    "nezha": lambda raw, work: profile_nezha(raw),
    "agenticopseval": lambda raw, work: {"AIOps2025": profile_aiops2025(raw), "RCA100": profile_rca100(raw)},
    "cloud-opsbench": lambda raw, work: profile_cloud_opsbench(raw),
    "petshop": lambda raw, work: profile_petshop(raw),
    "dejavu": lambda raw, work: profile_dejavu(raw),
    "anomod": lambda raw, work: profile_anomod(raw),
    "msds": lambda raw, work: profile_msds(raw),
    "rcabench-fse26": lambda raw, work: profile_rcabench(raw, work),
}


def run(source: str, data_home: Path) -> Path:
    t0 = time.time()
    res = SOURCES[source](data_home / "raw", data_home / "work")
    res = {"profiled_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "elapsed_s": round(time.time() - t0, 1), **res}
    out = data_home / "reports" / "profile" / f"{source}.json"
    write_json_atomic(out, res, indent=1)
    return out


# ---------------------------------------------------------------- compatibility matrix
# Sources that were not acquired or are lineage-only have no profile; their tier is a recorded decision.
UNPROFILED = [
    {"source_id": "rcaeval-hf", "subset": None, "tier": "C", "gate": "not-applicable", "evidence": "data/manifests/lineage-report.json",
     "reason": "copy of the Zenodo release (735 cases, truncated inject_time); cross-check only (tests/test_realdata_samples.py)", "incidents": 735},
    {"source_id": "openrca", "subset": None, "tier": "C", "gate": "not-applicable", "evidence": "data/provenance/openrca.json",
     "reason": "not acquired (Google Drive quota); adapter spec reserved", "incidents": None},
    {"source_id": "aiops2020-2021", "subset": None, "tier": "C", "gate": "not-applicable", "evidence": "data/manifests/lineage-report.json",
     "reason": "label files only, no telemetry; lineage metadata", "incidents": None},
    {"source_id": "gaia,eadro,lemma,lo2", "subset": None, "tier": "C", "gate": "not-applicable", "evidence": None,
     "reason": "not acquired (licence or acquisition decision)", "incidents": None},
]


def _ev(source: str, pointer: str) -> str:
    return f"data/reports/profile/{source}.json#{pointer}"


def matrix(data_home: Path) -> dict:
    """Tier (A/B/C) and promotion-gate outcome per source and subset, from the profile JSONs."""
    pdir = data_home / "reports" / "profile"
    P = {p.stem: read_json(p) for p in sorted(pdir.glob("*.json"))}
    rows = []

    def add(src, subset, tier, gate, ptr, reason, incidents=None):
        rows.append({"source_id": src, "subset": subset, "tier": tier, "gate": gate,
                     "evidence": _ev(src, ptr), "incidents": incidents, "reason": reason})

    if r := P.get("rcaeval-zenodo"):
        z = r["zips"]
        n = lambda rel: sum(v["cases"] for k, v in z.items() if k.startswith(rel))
        add("rcaeval-zenodo", "RE2+RE3", "A", "not-applicable", "/zips", "reference: injected service in the case path; "
            f"M L T on OB/TT, natural T absence on SS; duplicate {r['duplicates'][0]['case'] if r['duplicates'] else 'none'} rejected",
            n("RE2") + n("RE3"))
        add("rcaeval-zenodo", "RE1", "A", "not-applicable", "/zips", "natural metric-only stratum, descriptive only", n("RE1"))
    if r := P.get("nezha"):
        g = r.get("gate", {})
        add("nezha", None, "A", g.get("result", "fail"), "/gate",
            f"metrics aligned by the Time string; {g.get('window_mlt')}/{r['incidents']} incidents have M, L and T rows in "
            "[t-600 s, t+300 s]" + ("" if g.get("result") == "pass" else "; metric modality corrupted for affected incidents, ACCEPT_WITH_WARNINGS")
            + "; split protocols: eval-only (too few groups for grouped splits)", r["incidents"])
    if a := P.get("agenticopseval"):
        x, g = a["AIOps2025"], a["AIOps2025"].get("gate", {})
        it = x["instance_type"]
        add("agenticopseval", "AIOps2025 service+pod", "A" if g.get("result") == "pass" else "C", g.get("result", "fail"), "/AIOps2025/gate",
            f"archive hour names are UTC{'/'.join(f'{h:+d}' for h in g.get('archive_name_tz_offset_h', []))} h; {g.get('covered')} windows covered, "
            f"{g.get('natural_absent')} natural_absent (REJECT NO_TELEMETRY), counted over all 400", it.get("service", 0) + it.get("pod", 0))
        add("agenticopseval", "AIOps2025 node", "B", "not-applicable", "/AIOps2025/instance_type", "node-level labels", it.get("node", 0))
        y = a["RCA100"]
        add("agenticopseval", "RCA100", "A" if y["gate"] == "pass" else "B", y["gate"], "/RCA100/service_resolvable_share",
            f"{y['service_resolvable']}/{y['incidents']} cases resolve to a topology service (threshold {y['gate_threshold']}); "
            "the other cases are not service-level (eval_tier per incident)", y["incidents"])
    if r := P.get("rcabench-fse26"):
        g = r.get("gate", {})
        add("rcabench-fse26", None, "A" if g.get("result") == "pass" else "C", g.get("result", "fail"), "/gate",
            f"{g.get('cases_with_both')}/{g.get('cases')} cases have telemetry Parquet and an injection point "
            f"({g.get('injection_point_kinds')}); service pairs and non-service sources (e.g. mysql) need a per-incident rule; "
            "no adapter yet", g.get("cases"))
    if r := P.get("cloud-opsbench"):
        add("cloud-opsbench", None, "B", "not-applicable", "/fault_object_kinds",
            f"configuration/lifecycle faults; {r['traces']}; metrics CSV in {r['cases_with_metrics_csv']} cases", r["incidents"])
    if r := P.get("petshop"):
        add("petshop", None, "B", "not-applicable", "/root_cause_nodes", "metric-only; root causes are AWS resources, not services", r["incidents"])
    if r := P.get("dejavu"):
        add("dejavu", None, "B", "not-applicable", "/sets", "metric-only; root causes are docker/db/os nodes", r["incidents"])
    for src in ("anomod", "msds"):
        if r := P.get(src):
            add(src, None, "A" if r["gate"] == "pass" else "C", r["gate"], "/gate_reason", r["gate_reason"], r.get("experiments"))
    rows += UNPROFILED
    return {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "profiles": {k: v.get("profiled_at") for k, v in P.items()}, "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="rca.profile")
    ap.add_argument("--source", choices=sorted(SOURCES))
    ap.add_argument("--matrix", action="store_true", help="write data/reports/compatibility-matrix.json from the profiles")
    ap.add_argument("--data-home", default=None)
    a = ap.parse_args(argv)
    from .prep import resolve_data_home
    dh = resolve_data_home(a.data_home, {})
    if a.matrix:
        out = dh / "reports" / "compatibility-matrix.json"
        write_json_atomic(out, matrix(dh), indent=1)
        print(out)
        return 0
    if not a.source:
        ap.error("--source or --matrix is required")
    print(run(a.source, dh))
    return 0


if __name__ == "__main__":
    sys.exit(main())
