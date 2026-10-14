"""Nezha (FSE'23) adapter: Online Boutique (2022-08-*) and Train Ticket (2023-01-*) fault streams.

Layout: `rca_data/<date>/{<date>-fault_list.json, metric/<pod>_metric.csv, metric/front_service.csv,
log/HH_MM_log.csv, trace/HH_MM_trace.csv}`. One incident per fault-list entry. Telemetry is a
continuous day stream, so each incident stores the slice [anchor - pre_s, anchor + post_s]
(`windows.default`), clipped at the edges of the day's minute files.

Time rules (measured in phase 02): the anchor is `inject_time` read as UTC; it agrees with the hour
keys, the minute file names and the metric `Time` strings, while `inject_timestamp` is about -8 h on
2023-01-29. Metric time comes from the `Time` string; `TimeStamp` is only compared and reported.
Log time is `TimeUnixNano`; 124 Train Ticket rows carry an overflow sentinel there and are timed from
their UTC `Timestamp` column instead. Logs and traces exist only in ~3-minute bursts around each
injection (each minute file holds rows from 41 s before to 20 s after its minute); metrics are continuous.
"""
from __future__ import annotations

import csv
import io
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv

from ..identity import DEPLOYMENT_POD, STATEFULSET_POD, ServiceMap, load_aliases
from ..quality import finding
from . import register
from .base import (Adapter, BuildContext, DiscoveredIncident, LabelDraft, MemberSource, ModalityAbsent, RawRef,
                   TimeInfo, checksum_index, member_index)

DEFAULT_ROOT = "nezha/git-d8140101fdb4/rca_data"
FAULT_FAMILY = {"cpu_contention": "cpu", "cpu_consumed": "cpu", "network_delay": "network-delay",
                "return": "code-defect", "exception": "code-defect"}
LABEL_ARTIFACTS = {"online-boutique": "root_cause_hipster.json", "train-ticket": "root_cause_ts.json"}
AUX_METRIC_FILES = ("dependency.csv", "source_50.csv", "destination_50.csv")
KPI_FILE = "front_service.csv"
UNIT_SUFFIX = {"%": "pct", "s": "s", "m": "m", "Mi": "mi", "Ops": "ops", "ms": "ms"}
LEVEL_RE = re.compile(r"^\S+\s+(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL)\b")
GO_TIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))? ([+-])(\d{2})(\d{2})")


def system_of(date: str) -> str:
    return "online-boutique" if date.startswith("2022-") else "train-ticket"


def metric_name(col: str) -> tuple[str, str | None]:
    """`CpuUsageRate(%)` -> (`cpu-usage-rate-pct`, `%`); `SyscallRead` -> (`syscall-read`, None)."""
    m = re.match(r"^(?P<n>[^(]+)(?:\((?P<u>[^)]*)\))?$", col.strip())
    base, unit = (m["n"], m["u"]) if m else (col, None)
    kebab = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "-", base.strip()).lower()
    if unit:
        kebab += "-" + UNIT_SUFFIX.get(unit, re.sub(r"[^a-z0-9]+", "", unit.lower()))
    return kebab, unit or None


def go_time_ns(s: str) -> int | None:
    """'2022-08-22 03:51:19.607158889 +0000 UTC m=+0.11' -> ns UTC."""
    m = GO_TIME_RE.match(s or "")
    if not m:
        return None
    date, hh, mm, ss, frac, sign, oh, om = m.groups()
    secs = int(datetime.strptime(f"{date} {hh}:{mm}:{ss}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
    secs -= (1 if sign == "+" else -1) * (int(oh) * 3600 + int(om) * 60)
    return secs * 10**9 + int((frac or "0").ljust(9, "0"))


ISO_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))?Z?$")


def iso_utc_ns(s: str | None) -> int | None:
    """Log `Timestamp` ('2023-01-29T09:20:29.295' or '...:28.579588645Z', always UTC) -> ns."""
    m = ISO_RE.match(s or "")
    if not m:
        return None
    date, hh, mm, ss, frac = m.groups()
    secs = int(datetime.strptime(f"{date} {hh}:{mm}:{ss}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
    return secs * 10**9 + int((frac or "0").ljust(9, "0"))


def inject_time_s(s: str) -> int:
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())


def minute_of(name: str) -> int | None:
    m = re.match(r"^(\d{2})_(\d{2})_(log|trace)\.csv$", name)
    return int(m[1]) * 60 + int(m[2]) if m else None


@register
class NezhaAdapter(Adapter):
    name = "nezha"
    version = "1.0.3"
    dataset_id = "nezha"
    source_ids = ("nezha",)

    def __init__(self):
        self._src: MemberSource | None = None
        self._smap: ServiceMap | None = None

    # ------------------------------------------------------------ sources
    def _root(self, ctx: BuildContext) -> tuple[Path, str]:
        """(base, rel): rel is relative to the raw root when the data sits under it (member paths are
        then `<relpath under raw>`, as for every source), else relative to the data home."""
        root_cfg = ctx.dataset_cfg.get("root")
        root = (ctx.data_home / root_cfg) if root_cfg else ctx.raw_root / DEFAULT_ROOT
        for base in (ctx.raw_root, ctx.data_home):
            try:
                return base, root.resolve().relative_to(base.resolve()).as_posix()
            except ValueError:
                continue
        return root.parent, root.name

    def _source(self, ctx: BuildContext) -> MemberSource:
        if self._src is None:
            base, rel = self._root(ctx)
            self._src = MemberSource(self.source_ids[0], base, rel)
        return self._src

    def close(self):
        if self._src is not None:
            self._src.close()
            self._src = None

    def _dates(self, ctx) -> list[str]:
        src = self._source(ctx)
        return sorted(p.name for p in src.path.iterdir() if p.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}$", p.name))

    def _ref(self, ctx, name: str, sums: dict) -> RawRef:
        src = self._source(ctx)
        r = src.ref(name)
        return RawRef(r.source_id, r.member, sums.get(r.member), r.size)

    # ------------------------------------------------------------ 1 discover
    def discover(self, ctx: BuildContext):
        src = self._source(ctx)
        sums = checksum_index(ctx)
        win = (ctx.config.get("windows") or {}).get("nezha") or (ctx.config.get("windows") or {}).get("default", {})
        pre, post = int(win.get("pre_s", 1200)), int(win.get("post_s", 600))
        ev = (ctx.config.get("windows") or {}).get("evidence", {"pre_s": 600, "post_s": 300})
        art_dir = src.path.parent / "construct_data"
        for date in self._dates(ctx):
            ddir = src.path / date
            system = system_of(date)
            with open(ddir / f"{date}-fault_list.json", encoding="utf-8") as f:
                fl = json.load(f)
            entries = [(h, i, e) for h in sorted(fl) for i, e in enumerate(fl[h])]
            anchors = {(h, i): inject_time_s(e["inject_time"]) for h, i, e in entries}
            day0 = int(datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
            minutes = {kind: {minute_of(p.name): p.name for p in (ddir / kind).glob("*.csv") if minute_of(p.name) is not None}
                       for kind in ("log", "trace")}
            all_min = sorted(set(minutes["log"]) | set(minutes["trace"]))
            stream = (day0 + all_min[0] * 60, day0 + all_min[-1] * 60 + 59) if all_min else None
            metric_files = sorted(p.name for p in (ddir / "metric").glob("*_metric.csv"))
            for h, i, e in entries:
                t = anchors[(h, i)]
                lo, hi = t - pre, t + post
                clipped_start = clipped_end = False
                if stream:
                    clipped_start, clipped_end = lo < stream[0], hi > stream[1]
                    lo, hi = max(lo, stream[0]), min(hi, stream[1])
                refs: dict[str, list[RawRef]] = defaultdict(list)
                refs["label"].append(self._ref(ctx, f"{date}/{date}-fault_list.json", sums))
                for mf in metric_files:
                    refs["metrics:default"].append(self._ref(ctx, f"{date}/metric/{mf}", sums))
                if (ddir / "metric" / KPI_FILE).is_file():
                    refs["metrics:kpi"].append(self._ref(ctx, f"{date}/metric/{KPI_FILE}", sums))
                for kind, role in (("log", "logs"), ("trace", "traces")):
                    for mnt in sorted(minutes[kind]):   # one spare minute each side: files hold rows by arrival
                        if (lo - day0) // 60 - 1 <= mnt <= (hi - day0) // 60 + 1:
                            refs[role].append(self._ref(ctx, f"{date}/{kind}/{minutes[kind][mnt]}", sums))
                for aux in AUX_METRIC_FILES:
                    if (ddir / "metric" / aux).is_file():
                        refs["aux"].append(self._ref(ctx, f"{date}/metric/{aux}", sums))
                art = art_dir / LABEL_ARTIFACTS[system]
                if art.is_file():
                    member = (Path(src.rel).parent / "construct_data" / art.name).as_posix()
                    refs["label_artifact"].append(RawRef(self.source_ids[0], member, sums.get(member), art.stat().st_size))
                others = sorted(f"{h2}/{i2}" for (h2, i2), t2 in anchors.items()
                                if (h2, i2) != (h, i) and t - int(ev.get("pre_s", 600)) <= t2 <= t + int(ev.get("post_s", 300)))
                yield DiscoveredIncident(
                    source_incident_key=f"{date}/{h}/{i}", source_incident_id=f"nezha:{date}:{h}:{i}", refs=dict(refs),
                    hints={"date": date, "system": system, "entry": e, "anchor_s": t, "window": (lo, hi),
                           "clipped": (clipped_start, clipped_end), "contaminated_by": others,
                           "dataset_version": Path(src.rel).parent.name, "source_id": self.source_ids[0]})

    def _open(self, ctx, ref: RawRef):
        src = self._source(ctx)
        return src.open(ref.member[len(src.rel) + 1:])

    # ------------------------------------------------------------ 2 label
    def read_label(self, inc: DiscoveredIncident, ctx: BuildContext):
        e, system, date = inc.hints["entry"], inc.hints["system"], inc.hints["date"]
        smap = self.service_map(ctx)
        findings = []
        pod, ftype = e["inject_pod"], e["inject_type"]
        system_ok = pod.startswith("ts-") == (system == "train-ticket")
        if not system_ok:
            findings.append(finding("LABEL_INVALID", f"pod {pod!r} does not belong to the {system} stream of {date}"))
        sid = smap.map(system, pod, "pod")
        if sid is None:
            findings.append(finding("LABEL_INVALID", f"pod {pod!r} does not map to a known deployment"))
        family = FAULT_FAMILY.get(ftype, "unknown")
        notes = []
        if family == "unknown":
            findings.append(finding("LABEL_INVALID", f"fault type {ftype!r} outside the documented vocabulary", severity="warn"))
            notes.append(f"unknown fault type {ftype!r}")
        valid = system_ok and sid is not None
        arts = [{"kind": f"nezha:{Path(r.member).name}", "ref": r.member} for r in inc.refs.get("label_artifact", [])]
        lab = LabelDraft(
            original=e, entities=[{"raw": pod, "kind": "pod", "service_id": sid}],
            root_service_ids=[sid] if sid else [], primary_root_service=sid, label_granularity="pod",
            fault_type_raw=ftype, fault_family=family, label_source="label-file", injection_kind="injected",
            label_validity="valid" if valid else "invalid", validity_notes=notes,
            eval_tier="A" if valid else "excluded",
            eval_tier_reason="Nezha injected pod fault mapped to its deployment" if valid else "root pod not mappable",
            fault_cell=f"L4/{system}/{sid or 'unknown'}/{family}", system=system, dataset_subset=date,
            lineage_group="L4", label_artifacts=arts)
        return lab, findings

    # ------------------------------------------------------------ 3 identity
    def service_map(self, ctx: BuildContext) -> ServiceMap:
        if self._smap is None:
            from ..prep import ALIASES
            smap = ServiceMap(aliases=load_aliases(ALIASES))
            src = self._source(ctx)
            for date in self._dates(ctx):
                pods = [p.name.removesuffix("_metric.csv") for p in (src.path / date / "metric").glob("*_metric.csv")]
                deps = []
                for p in pods:
                    m = DEPLOYMENT_POD.match(p) or STATEFULSET_POD.match(p)
                    deps.append(m["d"] if m else p)
                smap.declare_services(system_of(date), deps)
            self._smap = smap
        return self._smap

    # ------------------------------------------------------------ 4 anchor
    def anchor_and_window(self, inc: DiscoveredIncident, label: LabelDraft, ctx: BuildContext):
        e = inc.hints["entry"]
        t = inc.hints["anchor_s"]
        findings = []
        try:
            ts_field = int(e["inject_timestamp"])
        except (KeyError, ValueError):
            ts_field = None
        if ts_field is not None and ts_field != t:
            findings.append(finding("ANCHOR_FIELD_DISAGREE", f"inject_timestamp - inject_time = {ts_field - t} s; inject_time used"))
        if inc.hints["contaminated_by"]:
            findings.append(finding("BASELINE_CONTAMINATED",
                                    f"{len(inc.hints['contaminated_by'])} other injection(s) in the evidence window: "
                                    + ", ".join(inc.hints["contaminated_by"])))
        lo, hi = inc.hints["window"]
        cs, ce = inc.hints["clipped"]
        # `inject_time` is "YYYY-MM-DD HH:MM:SS" (ISO 8601 with a space separator); the disagreeing
        # `inject_timestamp` stays in the label record's `original` and in the finding above
        return TimeInfo(anchor_ns=t * 10**9, anchor_kind="injection",
                        anchor_original={"value": e["inject_time"], "unit": "iso8601", "tz": "UTC"},
                        end_ns=None, window_start_ns=lo * 10**9, window_end_ns=hi * 10**9 + 999_999_999,
                        clipped_start=cs, clipped_end=ce), findings

    # ------------------------------------------------------------ 5 normalize
    def normalize(self, inc, modality, tinfo, smap, ctx, findings):
        system = inc.hints["system"]
        if modality == "metrics":
            refs = [(k.split(":", 1)[1], r) for k, rs in inc.refs.items() if k.startswith("metrics:") for r in rs]
            if not refs:
                raise ModalityAbsent()
            offsets, dropped = [], []
            for set_name, ref in sorted(refs, key=lambda x: (x[0], x[1].member)):
                t = self._metrics(inc, ref, set_name, system, smap, ctx, offsets, dropped)
                if t is not None:
                    yield t
            _report_dropped(dropped, modality, findings)
            if offsets:
                n = sum(c for _, c, _ in offsets)
                findings.append(finding("TS_COLUMN_OFFSET",
                                        f"TimeStamp differs from Time by more than 60 s in {n} rows of {len(offsets)} file(s) "
                                        f"({', '.join(f'{f}: median {o:.0f} s' for f, _, o in offsets)}); Time used",
                                        "metrics", "info"))
        elif modality in ("logs", "traces"):
            refs = inc.refs.get(modality, [])
            if not refs:
                raise ModalityAbsent()
            bad, dropped = [0, 0], []          # [non-JSON Log rows, rows timed from Timestamp]
            for ref in refs:
                t = self._logs(inc, ref, system, smap, ctx, bad, dropped) if modality == "logs" else \
                    self._traces(inc, ref, system, smap, ctx, findings, dropped)
                if t is not None:
                    yield t
            _report_dropped(dropped, modality, findings)
            if modality == "logs" and bad[0]:
                findings.append(finding("PARSE_ERROR", f"{bad[0]} log rows whose Log field is not JSON kept as raw text", "logs"))
            if modality == "logs" and bad[1]:
                findings.append(finding("TS_COLUMN_OFFSET", f"{bad[1]} log rows with an invalid TimeUnixNano "
                                                            "(overflow sentinel); time taken from the UTC Timestamp column",
                                        "logs", "info"))

    def _csv(self, ctx, ref: RawRef, dropped: list | None = None) -> pa.Table:
        """All columns as strings. If Arrow rejects the file, re-read it row by row: rows whose field
        count differs from the header are skipped and appended to `dropped` as (member, data row,
        fields, header fields), and the table gets a `__src_row` column with raw data-row indices."""
        with self._open(ctx, ref) as f:
            data = f.read()
        header = data.split(b"\n", 1)[0].decode("utf-8").rstrip("\r").split(",")
        ro = pacsv.ReadOptions(block_size=1 << 24, column_names=header, skip_rows=1)
        co = pacsv.ConvertOptions(column_types={c: pa.string() for c in header}, strings_can_be_null=False,
                                  quoted_strings_can_be_null=False)
        try:
            return pacsv.read_csv(io.BytesIO(data), read_options=ro, parse_options=pacsv.ParseOptions(newlines_in_values=True),
                                  convert_options=co)
        except pa.ArrowInvalid as e:
            from ..prep import ParseFailure
            if dropped is None:
                raise ParseFailure(f"{ref.member}: {e}") from e
            err = e
        csv.field_size_limit(1 << 30)
        try:
            reader = csv.reader(io.StringIO(data.decode("utf-8"), newline=""))
            next(reader, None)
            cols: list[list[str]] = [[] for _ in header]
            src_rows, bad = [], []
            for i, row in enumerate(reader):
                if len(row) != len(header):
                    bad.append((ref.member, i, len(row), len(header)))
                    continue
                for c, v in zip(cols, row):
                    c.append(v)
                src_rows.append(i)
        except (csv.Error, UnicodeDecodeError) as e:
            from ..prep import ParseFailure
            raise ParseFailure(f"{ref.member}: {err}; row-wise re-read failed: {e}") from e
        if not bad:     # Arrow failed for another reason: keep the original failure
            from ..prep import ParseFailure
            raise ParseFailure(f"{ref.member}: {err}")
        dropped.extend(bad)
        out = {h: pa.array(c, pa.string()) for h, c in zip(header, cols)}
        out["__src_row"] = pa.array(src_rows, pa.int64())
        return pa.table(out)

    def _metrics(self, inc, ref, set_name, system, smap, ctx, offsets, dropped) -> pa.Table | None:
        t = self._csv(ctx, ref, dropped)
        names = t.column_names
        if "Time" not in names:
            from ..prep import ParseFailure
            raise ParseFailure(f"{ref.member}: no Time column")
        n = t.num_rows
        if n == 0:
            return None
        ts = np.array([-1 if (v := go_time_ns(s)) is None else v for s in t["Time"].to_pylist()], dtype=np.int64)
        ts_ok = ts >= 0
        if "TimeStamp" in names:
            stamp = np.array([float(x) if x else np.nan for x in t["TimeStamp"].to_pylist()])
            diff = stamp - ts / 1e9
            off = ts_ok & np.isfinite(diff) & (np.abs(diff) > 60)
            if off.any():
                offsets.append((ref.member.rsplit("/", 1)[-1], int(off.sum()), float(np.median(diff[off]))))
        if set_name == "kpi":
            ent_col, kind = "ServiceName", "service"
        else:
            ent_col, kind = "PodName", "pod"
        skip = {"Time", "TimeStamp", ent_col, "__src_row"}
        keep = [(j, c) for j, c in enumerate(names) if c not in skip]
        if not keep:
            return None
        ent = t[ent_col].to_pylist() if ent_col in names else [None] * n
        if set_name == "kpi":
            # entry-point KPI of the whole application; not attributed to a service id
            sids = [None] * n
        else:
            sids = [smap.map(system, e, "pod") if e else None for e in ent]
        cols = {"ts_ns": [], "entity_raw": [], "entity_kind": [], "service_id": [], "metric": [], "value": [],
                "unit": [], "src_row": [], "src_col": []}
        rows = _src_rows(t)
        for j, c in keep:
            mname, unit = metric_name(c)
            raw = t[c]
            vals = pc.cast(pc.if_else(pc.equal(raw, ""), pa.scalar(None, pa.string()), raw), pa.float64(), safe=False) \
                if _all_numeric(raw) else pa.array([_float(x) for x in raw.to_pylist()], pa.float64())
            cols["ts_ns"].append(pa.array(ts, mask=~ts_ok))
            cols["entity_raw"].append(pa.array(ent, pa.string()))
            cols["entity_kind"].append(pa.array([kind] * n, pa.string()))
            cols["service_id"].append(pa.array(sids, pa.string()))
            cols["metric"].append(pa.array([mname] * n, pa.string()))
            cols["value"].append(pa.chunked_array([vals]).combine_chunks() if isinstance(vals, pa.ChunkedArray) else vals)
            cols["unit"].append(pa.array([unit] * n, pa.string()))
            cols["src_row"].append(pa.array(rows))
            cols["src_col"].append(pa.array(np.full(n, j, dtype=np.int32)))
        out = {k: pa.concat_arrays(v) for k, v in cols.items()}
        total = len(out["ts_ns"])
        return pa.table({
            "ts_ns": out["ts_ns"], "entity_raw": out["entity_raw"], "entity_kind": out["entity_kind"],
            "service_id": out["service_id"], "metric": out["metric"],
            "metric_set": pa.array([set_name] * total, pa.string()), "value": out["value"], "unit": out["unit"],
            "src_file": pa.array(np.full(total, member_index(inc, ref.member), dtype=np.int32)),
            "src_row": out["src_row"], "src_col": out["src_col"],
        })

    def _logs(self, inc, ref, system, smap, ctx, bad, dropped) -> pa.Table | None:
        t = self._csv(ctx, ref, dropped)
        n = t.num_rows
        if n == 0:
            return None
        need = {"TimeUnixNano", "PodName", "Log"}
        if not need <= set(t.column_names):
            from ..prep import ParseFailure
            raise ParseFailure(f"{ref.member}: missing columns {sorted(need - set(t.column_names))}")
        msgs, levels = [], []
        for raw in t["Log"].to_pylist():
            msg, lvl = _parse_log(raw)
            if msg is None:
                bad[0] += 1
                msg = raw
            msgs.append(msg)
            levels.append(lvl)
        pods = t["PodName"].to_pylist()
        sids = [smap.map(system, p, "pod") if p else None for p in pods]
        ts = _to_int(t["TimeUnixNano"])
        if "Timestamp" in t.column_names:
            from ..schema import TS_MAX_NS, TS_MIN_NS
            invalid = pc.fill_null(pc.or_(pc.less(ts, TS_MIN_NS), pc.greater_equal(ts, TS_MAX_NS)), True).to_numpy(zero_copy_only=False)
            if invalid.any():
                vals = ts.to_pylist()
                stamps = t["Timestamp"].to_pylist()
                for k in np.flatnonzero(invalid):
                    v = iso_utc_ns(stamps[k])
                    if v is not None:
                        vals[k] = v
                        bad[1] += 1
                ts = pa.array(vals, pa.int64())
        return pa.table({
            "ts_ns": ts, "entity_raw": pa.array([p or None for p in pods], pa.string()),
            "service_id": pa.array(sids, pa.string()), "level": pa.array(levels, pa.string()),
            "message": pa.array(msgs, pa.string()), "template": pa.nulls(n, pa.string()),
            "trace_id": _nullable(t["TraceID"]) if "TraceID" in t.column_names else pa.nulls(n, pa.string()),
            "span_id": _nullable(t["SpanID"]) if "SpanID" in t.column_names else pa.nulls(n, pa.string()),
            "src_file": pa.array(np.full(n, member_index(inc, ref.member), dtype=np.int32)),
            "src_row": pa.array(_src_rows(t)),
        })

    def _traces(self, inc, ref, system, smap, ctx, findings, dropped) -> pa.Table | None:
        t = self._csv(ctx, ref, dropped)
        n = t.num_rows
        if n == 0:
            return None
        need = {"TraceID", "SpanID", "ParentID", "PodName", "StartTimeUnixNano", "EndTimeUnixNano"}
        if not need <= set(t.column_names):
            from ..prep import ParseFailure
            raise ParseFailure(f"{ref.member}: missing columns {sorted(need - set(t.column_names))}")
        start, end = _to_int(t["StartTimeUnixNano"]), _to_int(t["EndTimeUnixNano"])
        dur_ns = pc.subtract(end, start)
        if "Duration" in t.column_names:
            d = _to_int(t["Duration"]).to_numpy(zero_copy_only=False).astype(float)
            s = dur_ns.to_numpy(zero_copy_only=False).astype(float)
            ok = np.isfinite(d) & np.isfinite(s) & (d > 0) & (s > 0)
            if ok.any():
                ratio = float(np.median(s[ok] / d[ok]))
                if not 900 <= ratio <= 1100:
                    findings.append(finding("UNIT_SUSPECT", f"Duration is not microseconds in {ref.member.rsplit('/', 1)[-1]} "
                                                            f"(median (End-Start)/Duration = {ratio:.3g}); End-Start used", "traces"))
        parent = t["ParentID"]
        parent = pc.if_else(pc.or_(pc.equal(parent, "root"), pc.equal(parent, "")), pa.scalar(None, pa.string()), parent)
        pods = t["PodName"].to_pylist()
        sids = [smap.map(system, p, "pod") if p else None for p in pods]
        return pa.table({
            "ts_ns": start, "duration_ns": dur_ns, "trace_id": t["TraceID"], "span_id": t["SpanID"],
            "parent_span_id": parent, "entity_raw": pa.array([p or None for p in pods], pa.string()),
            "service_id": pa.array(sids, pa.string()),
            "operation": t["OperationName"] if "OperationName" in t.column_names else pa.nulls(n, pa.string()),
            "status_code": pa.nulls(n, pa.string()),
            "src_file": pa.array(np.full(n, member_index(inc, ref.member), dtype=np.int32)),
            "src_row": pa.array(_src_rows(t)),
        })


# ---------------------------------------------------------------- helpers
def _src_rows(t: pa.Table) -> np.ndarray:
    if "__src_row" in t.column_names:
        return t["__src_row"].to_numpy()
    return np.arange(t.num_rows, dtype=np.int64)


def _report_dropped(dropped: list, modality: str, findings: list) -> None:
    if dropped:
        findings.append(finding("PARSE_ERROR", f"{len(dropped)} malformed CSV row(s) dropped: " + "; ".join(
            f"{m.rsplit('/', 3)[-3]}/{m.rsplit('/', 2)[-2]}/{m.rsplit('/', 1)[-1]} data row {i} ({n} fields, header {h})"
            for m, i, n, h in dropped[:5]), modality))


def _parse_log(raw: str) -> tuple[str | None, str | None]:
    """Docker JSON line -> (message, level). OB services log JSON with `message`/`severity`; TT logs
    plain text whose second token is the level. Returns (None, None) when the outer JSON is invalid."""
    try:
        outer = json.loads(raw)
        inner = outer["log"] if isinstance(outer, dict) else None
    except (ValueError, TypeError, KeyError):
        return None, None
    if not isinstance(inner, str):
        return None, None
    inner = inner.rstrip("\n")
    if inner.startswith("{"):
        try:
            obj = json.loads(inner)
        except ValueError:
            obj = None
        if isinstance(obj, dict):
            lvl = obj.get("severity") or obj.get("level")
            msg = obj.get("message")
            return (msg if isinstance(msg, str) else inner), (str(lvl).lower() if lvl else None)
    m = LEVEL_RE.match(inner)
    return inner, (m[1].lower() if m else None)


def _all_numeric(col) -> bool:
    try:
        pc.cast(pc.if_else(pc.equal(col, ""), pa.scalar(None, pa.string()), col), pa.float64())
        return True
    except (pa.ArrowInvalid, pa.ArrowNotImplementedError):
        return False


def _float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _nullable(col):
    return pc.if_else(pc.equal(col, ""), pa.scalar(None, pa.string()), col)


def _to_int(col) -> pa.Array:
    col = _nullable(col)
    try:
        return pc.cast(col, pa.int64()).combine_chunks()
    except (pa.ArrowInvalid, pa.ArrowNotImplementedError):
        out = []
        for v in col.to_pylist():
            try:
                out.append(int(v) if v is not None else None)
            except ValueError:
                try:
                    out.append(int(float(v)))
                except ValueError:
                    out.append(None)
        return pa.array(out, pa.int64())
