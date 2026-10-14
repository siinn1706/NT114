"""AIOps Challenge 2025 adapter (AgenticOpsEval mirror): HipsterShop + TiDB + Redis on Kubernetes.

Layout: `AIOps2025/{groundtruth.jsonl, input.json, <day>.tar.gz}`; the day archives are extracted by
`rca.prep extract` into `work/extract/agenticopseval/<version>/AIOps2025/<day>/<day>/` with
`{log-parquet, trace-parquet}/*_<day>_HH-00-00.parquet` (hourly) and `metric-parquet/**/*_<day>.parquet`
(daily). Member refs point into the archive (`<archive>!<member>`) with the sha256 from the
extraction receipt.

Time rules (README, measured in phase 02 on 410 log and 390 trace members): file-name times are
UTC+8; in-file times are UTC (`@timestamp`, metric `time` ISO strings; trace `startTime` us).

Leakage rules: the anchor is `start_time`; `end_time` goes only to the label (`truth_time.end_ns`)
because the fault duration identifies the fault type (io fault always 5 min, pod kill 0 min). The
stored window is [anchor - pre_s, anchor + post_s] from config, never `end_time`. The `input.json`
description is not copied (it states start and end). `key_observations`, `key_metrics`,
`fault_description` and the fault-specific fields stay in the label record; metric sets and names
are fixed by the archive layout, never chosen from `key_metrics`.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from ..data import canon
from ..identity import DEPLOYMENT_POD, STATEFULSET_POD, ServiceMap, load_aliases
from ..quality import finding
from . import register
from .base import (Adapter, BuildContext, DiscoveredIncident, LabelDraft, ModalityAbsent, RawRef, TimeInfo,
                   checksum_index, member_index)

DEFAULT_ROOT = "agenticopseval/gitlab-69cf36430b43/AIOps2025"
SYSTEM = "hipstershop"
NAME_UTC_OFFSET_S = 8 * 3600          # hourly/daily file names are UTC+8
FAULT_FAMILY = {
    "cpu stress": "cpu", "memory stress": "memory", "io fault": "disk-io",
    "network delay": "network-delay", "network loss": "network-loss", "network corrupt": "network-other",
    "pod failure": "pod-lifecycle", "pod kill": "pod-lifecycle", "dns error": "dns",
    "target port misconfig": "config", "code error": "code-defect",
    "jvm cpu": "jvm", "jvm exception": "jvm", "jvm gc": "jvm", "jvm latency": "jvm",
    "node cpu stress": "node", "node memory stress": "node", "node disk fill": "node",
}
LABEL_ARTIFACT_FIELDS = ("key_observations", "key_metrics", "fault_description", "patterns", "path", "volumePath", "image")
# TiDB components: the status port of a metric `instance` (TiDB defaults: tidb-server 10080, TiKV 20180)
# decides the component; `object_type` is used only when there is no port. Measured: rows of the
# infra_tidb `block_cache_size` KPI carry object_type `tidb` but port 20180 and cf=all (a RocksDB/TiKV
# block cache), so the port is the reliable signal.
TIDB_PORT = {"10080": "tidb-tidb", "20180": "tidb-tikv"}
TIDB_OBJECT = {"tidb": "tidb-tidb", "tikv": "tidb-tikv", "pd": "tidb-pd"}
TIDB_COMPONENTS = ("tidb-tidb", "tidb-tikv", "tidb-pd")
APM_COLUMNS = ("client_error", "client_error_ratio", "error", "error_ratio", "request", "response", "rrt", "rrt_max",
               "server_error", "server_error_ratio", "timeout")
QUALIFIERS = ("type", "sql_type", "cf", "device", "mountpoint")
HOURLY_RE = re.compile(r"_(\d{4}-\d{2}-\d{2})_(\d{2})-00-00\.parquet$")
DAILY_RE = re.compile(r"_(\d{4}-\d{2}-\d{2})\.parquet$")
LEVEL_RE = re.compile(r"\b(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|SEVERE)\b")
DELETED = " (deleted)"


def iso_s(s: str) -> int:
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


def name_start_s(day: str, hour: int = 0) -> int:
    """UTC epoch of a UTC+8 file-name time."""
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()) + hour * 3600 - NAME_UTC_OFFSET_S


def iso_to_ns(arr) -> pa.Array:
    """ISO 8601 strings with `Z` or an offset -> int64 ns; unparseable or 'null' -> null."""
    arr = arr.combine_chunks() if isinstance(arr, pa.ChunkedArray) else arr
    try:
        return pc.cast(pc.cast(arr, pa.timestamp("ns", "UTC")), pa.int64())
    except (pa.ArrowInvalid, pa.ArrowNotImplementedError):
        out = []
        for v in arr.to_pylist():
            try:
                d = datetime.fromisoformat(v.replace("Z", "+00:00"))
                out.append(int(d.timestamp()) * 10**9 + d.microsecond * 1000)
            except (AttributeError, ValueError):
                out.append(None)
        return pa.array(out, pa.int64())


def metric_set_of(rel: str) -> str:
    """Metric set from the archive path (fixed per layout; never from labels)."""
    if rel.startswith("metric-parquet/apm/service/"):
        return "default"
    if rel.startswith("metric-parquet/apm/pod/"):
        return "apm-pod"
    if rel.startswith("metric-parquet/apm/pod_ns_"):
        return "namespace"
    if rel.startswith("metric-parquet/infra/infra_node/"):
        return "node"
    if rel.startswith(("metric-parquet/infra/infra_pod/", "metric-parquet/infra/infra_tidb/", "metric-parquet/other/")):
        return "default"
    return "other"


@register
class Aiops2025Adapter(Adapter):
    name = "aiops2025"
    version = "1.0.1"
    dataset_id = "aiops2025"
    source_ids = ("agenticopseval",)

    def __init__(self):
        self._smap: ServiceMap | None = None
        self._receipts: dict[str, dict] = {}

    # ------------------------------------------------------------ sources
    def _raw(self, ctx) -> Path:
        return ctx.raw_root / (ctx.dataset_cfg.get("root") or DEFAULT_ROOT)

    def _extract(self, ctx) -> Path:
        """Extraction root: <work>/extract/<path of the raw root under raw/>."""
        raw = self._raw(ctx)
        try:
            rel = raw.resolve().relative_to(ctx.raw_root.resolve())
        except ValueError:
            rel = Path(raw.name)
        return ctx.work / "extract" / rel

    def _days(self, ctx) -> list[str]:
        ex = self._extract(ctx)
        if not ex.is_dir():
            return []
        return sorted(p.name for p in ex.iterdir() if p.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}$", p.name)
                      and (p / ".extract.json").is_file())

    def _receipt(self, ctx, day: str) -> dict:
        if day not in self._receipts:
            with open(self._extract(ctx) / day / ".extract.json", encoding="utf-8") as f:
                r = json.load(f)
            if not r.get("complete"):
                raise RuntimeError(f"extraction of {day} is incomplete")
            self._receipts[day] = r
        return self._receipts[day]

    def _raw_ref(self, ctx, name: str, sums: dict) -> RawRef:
        p = self._raw(ctx) / name
        member = p.resolve().relative_to(ctx.raw_root.resolve()).as_posix()
        return RawRef(self.source_ids[0], member, sums.get(member), p.stat().st_size)

    def _member_ref(self, ctx, day: str, rel: str) -> RawRef:
        """`rel` is the path inside the archive (e.g. `2025-06-06/log-parquet/...`)."""
        e = self._receipt(ctx, day)["members"][rel]
        arc = (self._raw(ctx) / f"{day}.tar.gz").resolve().relative_to(ctx.raw_root.resolve()).as_posix()
        return RawRef(self.source_ids[0], f"{arc}!{rel}", e["sha256"], e["size"])

    def _path(self, ctx, ref: RawRef) -> Path:
        arc, rel = ref.member.split("!", 1)
        day = Path(arc).name.split(".")[0]
        return self._extract(ctx) / day / rel

    def _labels(self, ctx) -> tuple[list[dict], set[str]]:
        raw = self._raw(ctx)
        with open(raw / "groundtruth.jsonl", encoding="utf-8") as f:
            gt = [json.loads(line) for line in f if line.strip()]
        with open(raw / "input.json", encoding="utf-8") as f:
            inp = {r["uuid"] for r in json.load(f)}
        return gt, inp

    # ------------------------------------------------------------ 1 discover
    def discover(self, ctx: BuildContext):
        sums = checksum_index(ctx)
        win = (ctx.config.get("windows") or {}).get("aiops2025") or (ctx.config.get("windows") or {}).get("default", {})
        pre, post = int(win.get("pre_s", 1200)), int(win.get("post_s", 600))
        gt, inp = self._labels(ctx)
        hourly: dict[str, list[tuple[int, str, str]]] = {"logs": [], "traces": []}   # (utc start s, day, rel)
        daily: list[tuple[int, str, str, str]] = []                                    # (utc start s, day, rel, set)
        for day in self._days(ctx):
            for rel in sorted(self._receipt(ctx, day)["members"]):
                sub = rel.split("/", 1)[1] if "/" in rel else rel
                if sub.startswith(("log-parquet/", "trace-parquet/")):
                    m = HOURLY_RE.search(rel)
                    if m:
                        hourly["logs" if sub.startswith("log") else "traces"].append(
                            (name_start_s(m[1], int(m[2])), day, rel))
                elif sub.startswith("metric-parquet/"):
                    m = DAILY_RE.search(rel)
                    if m:
                        daily.append((name_start_s(m[1]), day, rel, metric_set_of(sub)))
        metric_days = sorted({(s, d) for s, d, _, _ in daily})
        label_refs = [self._raw_ref(ctx, "groundtruth.jsonl", sums), self._raw_ref(ctx, "input.json", sums)]
        for g in gt:
            t = iso_s(g["start_time"])
            lo, hi = t - pre, t + post
            refs: dict[str, list[RawRef]] = defaultdict(list)
            refs["label"] = list(label_refs)
            for role, files in hourly.items():
                for s, day, rel in files:     # one hour per member; 60 s margin for late-arriving rows
                    if s - 60 <= hi and s + 3600 + 60 >= lo:
                        refs[role].append(self._member_ref(ctx, day, rel))
            for s, day, rel, mset in daily:
                if s <= hi and s + 86400 > lo:
                    refs[f"metrics:{mset}"].append(self._member_ref(ctx, day, rel))
            covered = [(s, s + 86400) for s, _ in metric_days if s <= hi and s + 86400 > lo]
            cs = not any(a <= lo < b for a, b in covered) if covered else False
            ce = not any(a <= hi < b for a, b in covered) if covered else False
            yield DiscoveredIncident(
                source_incident_key=g["uuid"], source_incident_id=f"aiops2025:{g['uuid']}", refs=dict(refs),
                hints={"entry": g, "in_input": g["uuid"] in inp, "anchor_s": t, "window": (lo, hi), "clipped": (cs, ce),
                       "dataset_version": Path(ctx.dataset_cfg.get("root") or DEFAULT_ROOT).parent.name,
                       "source_id": self.source_ids[0], "visible_text": None})

    # ------------------------------------------------------------ 2 label
    def read_label(self, inc: DiscoveredIncident, ctx: BuildContext):
        g = inc.hints["entry"]
        smap = self.service_map(ctx)
        findings, notes = [], []
        if not inc.hints["in_input"]:
            findings.append(finding("LABEL_INVALID", f"uuid {g['uuid']} missing from input.json", severity="warn"))
        it, inst = g["instance_type"], g["instance"]
        raws = inst if isinstance(inst, list) else [inst]
        entities = []
        for r in raws:
            if it == "node":
                entities.append({"raw": r, "kind": "node", "service_id": None})
                continue
            if canon(r) in smap.known[SYSTEM]:
                entities.append({"raw": r, "kind": "service", "service_id": smap.resolve(SYSTEM, r, "service")})
            else:
                entities.append({"raw": r, "kind": "pod", "service_id": smap.resolve(SYSTEM, r, "pod")})
        unmapped = [e["raw"] for e in entities if e["kind"] != "node" and e["service_id"] is None]
        for r in unmapped:
            findings.append(finding("LABEL_INVALID", f"label entity {r!r} does not map to a known service"))
        sids = sorted({e["service_id"] for e in entities if e["service_id"]})
        named = canon(g["service"]) if g.get("service") else None
        if named and named not in smap.known[SYSTEM]:
            findings.append(finding("LABEL_INVALID", f"service field {g['service']!r} is not a known service"))
            named = None
        if named and named not in sids:
            notes.append(f"service field {g['service']!r} not among the instance entities")
            sids = sorted(set(sids) | {named})
        family = FAULT_FAMILY.get(g["fault_type"], "unknown")
        if family == "unknown":
            findings.append(finding("LABEL_INVALID", f"fault type {g['fault_type']!r} outside the documented vocabulary", severity="warn"))
            notes.append(f"unknown fault type {g['fault_type']!r}")
        if it == "node":
            primary, gran, tier, reason = None, "node", "B", "node-level fault: no service root"
        elif named:
            primary, gran = named, ("pod" if it == "pod" else ("multi-service" if len(sids) > 1 else "service"))
            tier, reason = "A", ("named service of a multi-entity fault" if len(sids) > 1 else f"{it}-level fault on a service")
        elif len(sids) == 1:
            primary, gran, tier, reason = sids[0], ("pod" if it == "pod" else "service"), "A", f"{it}-level fault on a service"
        else:
            primary, gran, tier, reason = None, "multi-service", "A", "set-scoring-only"
        valid = not unmapped and (it == "node" or bool(sids))
        if not valid:
            tier, reason = "excluded", "root entity not mappable"
        arts = [{"kind": f"aiops2025:{k}", "ref": f"{inc.refs['label'][0].member}#{g['uuid']}"}
                for k in LABEL_ARTIFACT_FIELDS if k in g]
        lab = LabelDraft(
            original=g, entities=entities, root_service_ids=sids, primary_root_service=primary, label_granularity=gran,
            fault_type_raw=g["fault_type"], fault_family=family, label_source="label-file", injection_kind="injected",
            label_validity="valid" if valid else "invalid", validity_notes=notes, eval_tier=tier, eval_tier_reason=reason,
            fault_cell=f"L2/{SYSTEM}/{primary or ('+'.join(sids) if sids else raws[0])}/{family}", system=SYSTEM,
            # one subset: the campaign day is associated with the fault type (injection schedule)
            dataset_subset="AIOps2025", lineage_group="L2", label_artifacts=arts, truth_end_ns=iso_s(g["end_time"]) * 10**9)
        return lab, findings

    # ------------------------------------------------------------ 3 identity
    def service_map(self, ctx: BuildContext) -> ServiceMap:
        """Services: the APM service files of every extracted day, plus the three TiDB components."""
        if self._smap is None:
            from ..prep import ALIASES
            smap = ServiceMap(aliases=load_aliases(ALIASES))
            names = set(TIDB_COMPONENTS)
            for day in self._days(ctx):
                for rel in self._receipt(ctx, day)["members"]:
                    m = re.search(r"/metric-parquet/apm/service/service_(.+)_\d{4}-\d{2}-\d{2}\.parquet$", rel)
                    if m:
                        names.add(m[1])
            smap.declare_services(SYSTEM, sorted(names))
            self._smap = smap
        return self._smap

    def _pod(self, smap, pod: str | None) -> str | None:
        if not pod or pod == "null":
            return None
        base = pod[:-len(DELETED)] if pod.endswith(DELETED) else pod
        return smap.map(SYSTEM, base, "pod")

    # ------------------------------------------------------------ 4 anchor
    def anchor_and_window(self, inc: DiscoveredIncident, label: LabelDraft, ctx: BuildContext):
        t, (lo, hi), (cs, ce) = inc.hints["anchor_s"], inc.hints["window"], inc.hints["clipped"]
        g = inc.hints["entry"]
        return TimeInfo(anchor_ns=t * 10**9, anchor_kind="injection",
                        anchor_original={"value": g["start_time"], "unit": "iso8601", "tz": "UTC"},
                        end_ns=None, window_start_ns=lo * 10**9, window_end_ns=hi * 10**9 + 999_999_999,
                        clipped_start=cs, clipped_end=ce), []

    # ------------------------------------------------------------ 5 normalize
    def normalize(self, inc, modality, tinfo, smap, ctx, findings):
        lo, hi = tinfo.window_start_ns, tinfo.window_end_ns
        if modality == "metrics":
            refs = sorted(((k.split(":", 1)[1], r) for k, rs in inc.refs.items() if k.startswith("metrics:") for r in rs),
                          key=lambda x: (x[0], x[1].member))
            if not refs:
                raise ModalityAbsent()
            for mset, ref in refs:
                t = self._metrics(inc, ref, mset, smap, ctx, lo, hi)
                if t is not None:
                    yield t
        elif modality in ("logs", "traces"):
            refs = inc.refs.get(modality, [])
            if not refs:
                raise ModalityAbsent()
            for ref in refs:
                t = (self._logs if modality == "logs" else self._traces)(inc, ref, smap, ctx, lo, hi)
                if t is not None:
                    yield t

    def _read(self, ctx, ref, columns=None) -> pa.Table:
        from ..prep import ParseFailure
        try:
            return pq.read_table(self._path(ctx, ref), columns=columns)
        except (pa.ArrowInvalid, OSError) as e:
            raise ParseFailure(f"{ref.member}: {e}") from e

    @staticmethod
    def _in_window(ts: pa.Array, lo: int, hi: int) -> np.ndarray:
        """Row indices inside [lo, hi] (the driver filters again and counts what it drops)."""
        m = pc.and_(pc.greater_equal(ts, lo - 60 * 10**9), pc.less_equal(ts, hi + 60 * 10**9))
        return np.flatnonzero(pc.fill_null(m, False).to_numpy(zero_copy_only=False))

    def _metrics(self, inc, ref, mset, smap, ctx, lo, hi) -> pa.Table | None:
        t = self._read(ctx, ref)
        if t.num_rows == 0 or "time" not in t.column_names:
            return None
        ts_all = iso_to_ns(t["time"])
        idx = self._in_window(ts_all, lo, hi)
        if len(idx) == 0:
            return None
        t = t.take(idx)
        ts = ts_all.take(pa.array(idx))
        n = t.num_rows
        names = t.column_names
        sub = ref.member.split("!", 1)[1].split("/", 1)[1]

        def col(c):
            return [None if v in (None, "null") else v for v in t[c].to_pylist()] if c in names else [None] * n

        otype = col("object_type")
        if "kpi_key" in names:                       # infra families: one value column named after the KPI
            kpis = col("kpi_key")
            vcols = sorted({k for k in kpis if k and k in names})
            quals = {q: col(q) for q in QUALIFIERS}
            inst, pod, node = col("instance"), col("pod"), col("kubernetes_node")
            ents, kinds, sids = [], [], []
            for k in range(n):
                e, kind, sid = self._infra_entity(smap, otype[k], inst[k], pod[k], node[k])
                ents.append(e), kinds.append(kind), sids.append(sid)
            mnames = [".".join([kpis[k]] + [str(quals[q][k]) for q in QUALIFIERS if quals[q][k] is not None]) if kpis[k] else None
                      for k in range(n)]
            values = np.full(n, np.nan)
            src_col = np.full(n, -1, dtype=np.int32)
            for vc in vcols:
                sel = np.array([kp == vc for kp in kpis])
                v = pc.cast(t[vc], pa.float64(), safe=False).to_numpy(zero_copy_only=False)
                values[sel] = np.asarray(v, dtype=float)[sel]
                src_col[sel] = names.index(vc)
            keep = np.array([m is not None for m in mnames]) & (src_col >= 0)
            row_idx = idx
            sets = ["node" if kinds[k] == "node" else mset for k in range(n)]
            out = pa.table({
                "ts_ns": ts, "entity_raw": pa.array(ents, pa.string()), "entity_kind": pa.array(kinds, pa.string()),
                "service_id": pa.array(sids, pa.string()), "metric": pa.array(mnames, pa.string()),
                "metric_set": pa.array(sets, pa.string()), "value": pa.array(values, pa.float64()),
                "unit": pa.nulls(n, pa.string()),
                "src_file": pa.array(np.full(n, member_index(inc, ref.member), dtype=np.int32)),
                "src_row": pa.array(row_idx.astype(np.int64)), "src_col": pa.array(src_col)})
            return out.filter(pa.array(keep))
        # APM families: one row per entity and minute, one column per KPI
        oid = col("object_id")
        if sub.startswith("metric-parquet/apm/service/"):
            sids, kind = [smap.map(SYSTEM, o, "service") if o else None for o in oid], "service"
        elif sub.startswith("metric-parquet/apm/pod/"):
            sids, kind = [self._pod(smap, o) for o in oid], "pod"
        else:
            sids, kind = [None] * n, "namespace"
        parts = []
        for c in APM_COLUMNS:
            if c not in names:
                continue
            parts.append(pa.table({
                "ts_ns": ts, "entity_raw": pa.array(oid, pa.string()), "entity_kind": pa.array([kind] * n, pa.string()),
                "service_id": pa.array(sids, pa.string()), "metric": pa.array([c] * n, pa.string()),
                "metric_set": pa.array([mset] * n, pa.string()),
                "value": pc.cast(t[c], pa.float64(), safe=False), "unit": pa.nulls(n, pa.string()),
                "src_file": pa.array(np.full(n, member_index(inc, ref.member), dtype=np.int32)),
                "src_row": pa.array(idx.astype(np.int64)), "src_col": pa.array(np.full(n, names.index(c), dtype=np.int32))}))
        return pa.concat_tables(parts) if parts else None

    def _trace_service(self, smap, name: str, tags, svc: list) -> str | None:
        """A Jaeger process name that is not a service (measured: `redis`, client spans emitted by
        cartservice with `peer.service=redis-cart:6379`) maps to the service its spans call when one
        `peer.service` covers at least 99% of them; otherwise the canon rule applies."""
        if name in smap.entries[SYSTEM] or canon(name) in smap.known[SYSTEM] or name in smap.aliases.get(SYSTEM, {}):
            return smap.map(SYSTEM, name, "service")
        rows = [i for i, s in enumerate(svc) if s == name]
        peers = _tag(tags.take(pa.array(rows)), "peer.service")
        counts: dict[str, int] = defaultdict(int)
        for p in peers:
            if p:
                counts[canon(p.rsplit(":", 1)[0])] += 1
        best = max(counts, key=counts.get) if counts else None
        if best in smap.known[SYSTEM] and counts[best] >= 0.99 * len(rows):
            return smap.record(SYSTEM, name, best, "peer-service-tag", "service")
        return smap.map(SYSTEM, name, "service")

    def _infra_entity(self, smap, otype, inst, pod, node) -> tuple[str | None, str, str | None]:
        """(entity_raw, kind, service_id) of one infra metric row."""
        if otype == "pod" and pod:
            return pod, "pod", self._pod(smap, pod)
        if otype == "node":
            return node or inst, "node", None
        if otype in TIDB_OBJECT:
            if node:                                # node-exporter disk rows filed under TiKV
                return node, "node", None
            port = inst.rsplit(":", 1)[1] if inst and ":" in inst else None
            if port in TIDB_PORT:
                comp, rule = TIDB_PORT[port], "tidb-status-port"
            elif inst and STATEFULSET_POD.match(inst) and STATEFULSET_POD.match(inst)["d"] in TIDB_COMPONENTS:
                comp, rule = STATEFULSET_POD.match(inst)["d"], "pod-to-deployment"
            else:
                comp, rule = TIDB_OBJECT[otype], "tidb-object-type"
            raw = inst or otype
            return raw, "pod", smap.record(SYSTEM, raw, canon(comp), rule, "pod")
        return inst or node or pod, "unknown", None

    def _logs(self, inc, ref, smap, ctx, lo, hi) -> pa.Table | None:
        t = self._read(ctx, ref, ["@timestamp", "k8_pod", "message"])
        if t.num_rows == 0:
            return None
        ts_all = iso_to_ns(t["@timestamp"])
        idx = self._in_window(ts_all, lo, hi)
        if len(idx) == 0:
            return None
        t = t.take(idx)
        n = t.num_rows
        pods = t["k8_pod"].to_pylist()
        msgs = t["message"].to_pylist()
        return pa.table({
            "ts_ns": ts_all.take(pa.array(idx)), "entity_raw": pa.array(pods, pa.string()),
            "service_id": pa.array([self._pod(smap, p) for p in pods], pa.string()),
            "level": pa.array([_level(m) for m in msgs], pa.string()), "message": pa.array(msgs, pa.string()),
            "template": pa.nulls(n, pa.string()), "trace_id": pa.nulls(n, pa.string()), "span_id": pa.nulls(n, pa.string()),
            "src_file": pa.array(np.full(n, member_index(inc, ref.member), dtype=np.int32)),
            "src_row": pa.array(idx.astype(np.int64))})

    def _traces(self, inc, ref, smap, ctx, lo, hi) -> pa.Table | None:
        t = self._read(ctx, ref, ["traceID", "spanID", "operationName", "references", "startTime", "duration", "tags", "process"])
        if t.num_rows == 0:
            return None
        start_ns = pc.multiply(pc.cast(t["startTime"], pa.int64()), 1000).combine_chunks()
        idx = self._in_window(start_ns, lo, hi)
        if len(idx) == 0:
            return None
        t = t.take(idx)
        n = t.num_rows
        svc = pc.struct_field(t["process"], "serviceName").to_pylist()
        tags = t["tags"].combine_chunks()
        sid_of = {s: self._trace_service(smap, s, tags, svc) for s in set(svc) if s}
        return pa.table({
            "ts_ns": start_ns.take(pa.array(idx)),
            "duration_ns": pc.multiply(pc.cast(t["duration"], pa.int64()), 1000),
            "trace_id": t["traceID"], "span_id": t["spanID"], "parent_span_id": _parent(t["references"]),
            "entity_raw": pa.array(svc, pa.string()),
            "service_id": pa.array([sid_of.get(s) for s in svc], pa.string()),
            "operation": t["operationName"], "status_code": _status(tags),
            "src_file": pa.array(np.full(n, member_index(inc, ref.member), dtype=np.int32)),
            "src_row": pa.array(idx.astype(np.int64))})


# ---------------------------------------------------------------- helpers
def _level(msg: str | None) -> str | None:
    if not msg:
        return None
    s = msg.lstrip()
    if s.startswith("{"):
        try:
            obj = json.loads(s)
        except ValueError:
            obj = None
        if isinstance(obj, dict):
            lvl = obj.get("severity") or obj.get("level")
            if lvl:
                return str(lvl).lower()
    m = LEVEL_RE.search(s[:120])
    return m[1].lower() if m else None


def _parent(refs) -> pa.Array:
    """First CHILD_OF reference of each span (Jaeger), else the first reference, else null."""
    out = []
    for rs in refs.to_pylist():
        p = None
        for r in rs or []:
            if r.get("refType") == "CHILD_OF":
                p = r.get("spanID")
                break
        if p is None and rs:
            p = rs[0].get("spanID")
        out.append(p or None)
    return pa.array(out, pa.string())


def _tag(tags, key: str) -> list:
    flat = pc.list_flatten(tags)
    parent = pc.list_parent_indices(tags).to_numpy(zero_copy_only=False)
    keys = pc.struct_field(flat, "key")
    sel = pc.fill_null(pc.equal(keys, key), False).to_numpy(zero_copy_only=False)
    vals = pc.struct_field(flat, "value").to_numpy(zero_copy_only=False)
    out = [None] * len(tags)
    for i, v in zip(parent[sel], vals[sel]):
        if out[i] is None:
            out[i] = v
    return out


def _status(tags) -> pa.Array:
    """gRPC `status.code`, else `http.status_code`, else '2' (gRPC UNKNOWN) when the span has `error=true`."""
    tags = tags.combine_chunks() if isinstance(tags, pa.ChunkedArray) else tags
    grpc, http, err = _tag(tags, "status.code"), _tag(tags, "http.status_code"), _tag(tags, "error")
    out = [g if g is not None else (h if h is not None else ("2" if str(e).lower() == "true" else None))
           for g, h, e in zip(grpc, http, err)]
    return pa.array(out, pa.string())
