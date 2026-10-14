"""RCAEval (RE1, RE2, RE3) adapter: reference implementation of the adapter contract.

Reads the Zenodo zips in place (or the same layout as plain directories, which is what
`scripts/make_synthetic.py` writes). Case directory = `RE<n>-<SYS>/<cell>/<instance>/` containing
`inject_time.txt`; the label is encoded in `<cell>` = `<service>_<fault>[_<batch>]`.
"""
from __future__ import annotations

import hashlib
import io
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv

from ..data import canon
from ..identity import ServiceMap, load_aliases
from ..quality import finding
from . import register
from .base import (Adapter, BuildContext, DiscoveredIncident, LabelDraft, MemberSource, ModalityAbsent, RawRef,
                   TimeInfo, member_index)

# cell = <service>_<fault>[_<batch>]; `ts-route-service_f3_1` is fault f3, batch 1
CELL_RE = re.compile(r"^(?P<svc>.+?)_(?P<fault>cpu|mem|disk|delay|loss|socket|f[1-5])(?:_(?P<batch>\d+))?$")
SUBSET_RE = re.compile(r"^(?P<subset>RE[123])-(?P<sys>OB|SS|TT)$")
SYSTEMS = {"OB": "online-boutique", "SS": "sock-shop", "TT": "train-ticket"}
FAULT_FAMILY = {"cpu": "cpu", "mem": "memory", "disk": "disk-io", "delay": "network-delay", "loss": "network-loss",
                "socket": "socket", "f1": "code-defect", "f2": "code-defect", "f3": "code-defect",
                "f4": "code-defect", "f5": "code-defect"}
METRIC_FILES = {"full": ("metrics.csv", "data.csv"), "simple": ("simple_metrics.csv", "simple_data.csv")}
LABEL_ARTIFACTS = ("root_cause.txt",)
# Metric-column prefixes that are not services: node exporters, sidecar init containers, mesh
# pseudo-clusters, the profiling `main` process, and truncated pod-network prefixes.
INFRA_EXACT = {"main", "istio-init", "PassthroughCluster", "InboundPassthroughClusterIpv4", "ts", "front", "queue", "session"}
INFRA_RE = re.compile(r"^(gke-.+|ip-.+|\d+(-\d+){3}-\d+)$")
DEFAULT_ROOT = "rcaeval-zenodo/zenodo-14590730"
# Other-system containers: a metric entity seen in few cases of its own system but in nearly every case
# of another system was scraped from a neighbouring demo in the same cluster (measured 2026-10-14: 15 Sock
# Shop names in 3 OB cases, 11 OB names in 1 SS case; own share <= 1.3%, other share 100%, no name
# between 10% and 30%). They become infra (`<other system><name>`), never candidates or merged services.
FOREIGN_OWN_MAX, FOREIGN_OTHER_MIN = 0.05, 0.9


def is_infra(name: str) -> bool:
    return name in INFRA_EXACT or bool(INFRA_RE.match(name))


def parse_cell(cell: str):
    m = CELL_RE.match(cell)
    return (m["svc"], m["fault"], m["batch"]) if m else None


def legacy_metric_set(subset: str | None, sets) -> str:
    """Metric set the legacy loader reads: simple_metrics.csv for RE2/RE3, data.csv for RE1."""
    if subset != "RE1" and "simple" in sets:
        return "simple"
    return "full" if "full" in sets else sorted(sets)[0]


class _Hashing(io.RawIOBase):
    """Read-through wrapper that hashes every byte read."""

    def __init__(self, f):
        self.f, self.h = f, hashlib.sha256()

    def readable(self):
        return True

    def readinto(self, b):
        data = self.f.read(len(b))
        n = len(data)
        b[:n] = data
        self.h.update(data)
        return n

    def close(self):
        self.f.close()
        super().close()


@register
class RCAEvalAdapter(Adapter):
    name = "rcaeval"
    version = "1.0.1"
    dataset_id = "rcaeval"
    source_ids = ("rcaeval-zenodo",)

    def __init__(self):
        self._sources: dict[str, MemberSource] = {}
        self._smap: ServiceMap | None = None

    # ------------------------------------------------------------ sources
    def _roots(self, ctx: BuildContext) -> list[tuple[Path, str]]:
        """[(base, rel)] for every RE<n>-<SYS> zip or directory under the configured root."""
        root_cfg = ctx.dataset_cfg.get("root")
        root = Path(root_cfg) if root_cfg else ctx.raw_root / DEFAULT_ROOT
        if not root.is_absolute():
            root = ctx.data_home / root
        base = ctx.raw_root if _is_under(root, ctx.raw_root) else ctx.data_home if _is_under(root, ctx.data_home) else root.parent
        subsets = set(ctx.dataset_cfg.get("subsets") or ["RE1", "RE2", "RE3"])
        out = []
        for p in sorted(root.rglob("RE*")):
            m = SUBSET_RE.match(p.name.removesuffix(".zip"))
            if not m or m["subset"] not in subsets:
                continue
            if (p.suffix == ".zip" and p.is_file()) or p.is_dir():
                out.append((base, p.relative_to(base).as_posix()))
        return out

    def _src(self, ctx_raw_base: Path, rel: str) -> MemberSource:
        key = f"{ctx_raw_base}|{rel}"
        if key not in self._sources:
            self._sources[key] = MemberSource(self.source_ids[0], ctx_raw_base, rel)
        return self._sources[key]

    def close(self):
        for s in self._sources.values():
            s.close()
        self._sources.clear()

    # ------------------------------------------------------------ 1 discover
    def discover(self, ctx: BuildContext):
        found = list(self._discover(ctx))
        seen: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        n_sys: dict[str, int] = defaultdict(int)
        for inc in found:
            system = SYSTEMS[inc.hints["subsys"].split("-")[1]]
            n_sys[system] += 1
            for e in self._metric_entities(inc):
                seen[system][e] += 1
        share = {s: {e: k / n_sys[s] for e, k in d.items()} for s, d in seen.items()}
        foreign = defaultdict(dict)
        for s, d in share.items():
            for e, f in d.items():
                if f > FOREIGN_OWN_MAX:
                    continue
                other = max(((share[t].get(e, 0.0), t) for t in share if t != s), default=(0.0, None))
                if other[0] >= FOREIGN_OTHER_MIN:
                    foreign[s][e] = other[1]
        for inc in found:
            inc.hints["foreign"] = dict(sorted(foreign[SYSTEMS[inc.hints["subsys"].split("-")[1]]].items()))
            yield inc

    def _metric_entities(self, inc: DiscoveredIncident) -> set[str]:
        """Entity prefixes of the metric CSV headers (first line only)."""
        out = set()
        for k, refs in inc.refs.items():
            if not k.startswith("metrics:"):
                continue
            for r in refs:
                with self._open(inc, r) as f:
                    head = f.readline().decode("utf-8", "replace").rstrip("\r\n").split(",")
                out |= {c.split("_", 1)[0] for c in head[1:] if "_" in c and c != "time" and not c.startswith("time.")}
        return out

    def _discover(self, ctx: BuildContext):
        for base, rel in self._roots(ctx):
            src = self._src(base, rel)
            subsys = Path(rel).name.removesuffix(".zip")
            names = src.names()
            prefix = f"{subsys}/" if names and names[0].startswith(f"{subsys}/") else ""
            by_case: dict[str, list[str]] = defaultdict(list)
            for n in names:
                parts = n[len(prefix):].split("/")
                if len(parts) >= 3:
                    by_case["/".join(parts[:2])].append(n)
            cases = sorted(c for c, files in by_case.items() if any(f.endswith("/inject_time.txt") for f in files))
            inject = {c: src.read_bytes(f"{prefix}{c}/inject_time.txt") for c in cases}
            for c in cases:
                cell, inst = c.split("/")
                files = {f.rsplit("/", 1)[1]: f for f in by_case[c] if f.count("/") == prefix.count("/") + 2}
                refs: dict[str, list[RawRef]] = defaultdict(list)
                for set_name, cand in METRIC_FILES.items():
                    hit = next((files[n] for n in cand if n in files), None)
                    if hit:
                        refs[f"metrics:{set_name}"].append(self._ref(src, hit))
                for mod in ("logs", "traces"):
                    if f"{mod}.csv" in files:
                        refs[mod].append(self._ref(src, files[f"{mod}.csv"]))
                refs["label"].append(self._ref(src, files["inject_time.txt"]))
                used = {r.member for rs in refs.values() for r in rs}
                for n, f in sorted(files.items()):
                    r = self._ref(src, f)
                    if n in LABEL_ARTIFACTS:
                        refs["label_artifact"].append(r)
                    elif r.member not in used:
                        refs["aux"].append(r)
                for f in sorted(set(by_case[c]) - set(files.values())):   # nested members (multi-source-data/...)
                    refs["aux"].append(self._ref(src, f))
                hints = {"base": str(base), "rel": rel, "prefix": prefix, "files": files, "subsys": subsys,
                         "dataset_version": Path(rel).parent.name or "local", "source_id": self.source_ids[0]}
                if not inst.isdigit():
                    same = [o for o in cases if o.split("/")[0] == cell and o.split("/")[1].isdigit()
                            and inject[o] == inject[c]]
                    hints["duplicate_of_key"] = f"{subsys}/{same[0]}" if same else None
                    hints["extra_case"] = True
                subset, sysc = subsys.split("-")
                yield DiscoveredIncident(
                    source_incident_key=f"{subsys}/{c}",
                    source_incident_id=f"rcaeval:{subset.lower()}{sysc.lower()}_{cell}_{inst}",
                    refs=dict(refs), hints=hints)

    def _ref(self, src: MemberSource, name: str) -> RawRef:
        info_crc = None
        if src.is_zip:
            src._z()
            info_crc = src._infos[name].CRC
        r = src.ref(name)
        return RawRef(r.source_id, r.member, None, r.size, info_crc)

    def _open(self, inc: DiscoveredIncident, member_ref: RawRef):
        src = self._src(Path(inc.hints["base"]), inc.hints["rel"])
        name = member_ref.member.split("!", 1)[1] if "!" in member_ref.member else member_ref.member[len(inc.hints["rel"]) + 1:]
        return src.open(name)

    # ------------------------------------------------------------ 2 label
    def read_label(self, inc: DiscoveredIncident, ctx: BuildContext):
        subsys = inc.hints["subsys"]
        subset, sysc = subsys.split("-")
        system = SYSTEMS[sysc]
        cell, inst = inc.source_incident_key.split("/")[1:]
        smap = self.service_map(ctx)
        findings = []
        parsed = parse_cell(cell)
        arts = [{"kind": "rcaeval:root_cause.txt", "ref": r.member} for r in inc.refs.get("label_artifact", [])]
        if parsed is None:
            findings.append(finding("LABEL_UNPARSEABLE", f"cell {cell!r} does not match the fault vocabulary"))
            return LabelDraft(original=cell, entities=[], root_service_ids=[], primary_root_service=None,
                              label_granularity="service", fault_type_raw="unknown", fault_family="unknown",
                              label_source="path", injection_kind="injected", label_validity="invalid",
                              validity_notes=["unparseable cell"], eval_tier="excluded", eval_tier_reason="unparseable label",
                              fault_cell=f"L1/{system}/unknown/unknown", system=system, dataset_subset=subset,
                              lineage_group="L1", label_artifacts=arts), findings
        svc_raw, fault, batch = parsed
        sid = smap.map(system, svc_raw, "service")
        notes = [f"batch {batch} of cell {svc_raw}_{fault}"] if batch else []
        dup_key = None
        if inc.hints.get("extra_case"):
            dup_key = inc.hints.get("duplicate_of_key")
            if dup_key is None:
                findings.append(finding("UNEXPLAINED_EXTRA_CASE", f"non-numeric instance {inst!r} with no sibling of equal inject_time"))
            else:
                notes.append(f"non-numeric instance {inst!r}; inject_time equals {dup_key}")
        tier_reason = ("RCAEval RE1 metric-only injected fault (natural missing logs and traces)" if subset == "RE1"
                       else f"RCAEval {subset} service-level injected fault")
        lab = LabelDraft(
            original=svc_raw, entities=[{"raw": svc_raw, "kind": "service", "service_id": sid}],
            root_service_ids=[sid], primary_root_service=sid, label_granularity="service",
            fault_type_raw=fault, fault_family=FAULT_FAMILY[fault], label_source="path", injection_kind="injected",
            label_validity="valid", validity_notes=notes, eval_tier="A", eval_tier_reason=tier_reason,
            fault_cell=f"L1/{system}/{sid}/{FAULT_FAMILY[fault]}", system=system, dataset_subset=subset,
            lineage_group="L1", duplicate_of_key=dup_key, label_artifacts=arts)
        return lab, findings

    # ------------------------------------------------------------ 3 identity
    def service_map(self, ctx: BuildContext) -> ServiceMap:
        if self._smap is None:
            from ..prep import ALIASES
            self._smap = ServiceMap(aliases=load_aliases(ALIASES))
        return self._smap

    def _sid(self, smap: ServiceMap, system: str, raw: str, foreign: dict | None = None) -> tuple[str, str]:
        if is_infra(raw):
            smap.infra.setdefault(system, set()).add(raw)
            return smap.map(system, raw, "infra"), "infra"
        other = (foreign or {}).get(raw)
        if other and raw not in smap.aliases.get(system, {}):    # a reviewed alias still wins
            sid = smap.record(system, raw, canon(other) + canon(raw), "other-system-container", "infra")
            return sid, "infra"
        sid = smap.map(system, raw, "service")
        return sid, smap.entries[system][raw]["kind"]      # a reviewed alias may declare kind=infra

    # ------------------------------------------------------------ 4 anchor
    def anchor_and_window(self, inc: DiscoveredIncident, label: LabelDraft, ctx: BuildContext):
        raw = self._read(inc, inc.refs["label"][0]).decode("utf-8").strip()
        t = int(float(raw.split()[0]))
        return TimeInfo(anchor_ns=t * 10**9, anchor_kind="injection",
                        anchor_original={"value": raw, "unit": "s", "tz": "UTC"}, end_ns=None,
                        window_start_ns=None, window_end_ns=None), []

    def _read(self, inc, ref: RawRef) -> bytes:
        with self._open(inc, ref) as f:
            data = f.read()
        inc.hints.setdefault("member_sha256", {})[ref.member] = hashlib.sha256(data).hexdigest()
        return data

    def _csv(self, inc, ref: RawRef, ctx: BuildContext, all_string: bool = True) -> pa.Table:
        data = self._read(inc, ref)
        header = data.split(b"\n", 1)[0].decode("utf-8").rstrip("\r").split(",")
        ro = pacsv.ReadOptions(block_size=1 << 24, column_names=_dedupe(header), skip_rows=1)
        po = pacsv.ParseOptions(newlines_in_values=True)
        co = pacsv.ConvertOptions(column_types={c: pa.string() for c in _dedupe(header)} if all_string else None,
                                  strings_can_be_null=False, quoted_strings_can_be_null=False)
        try:
            return pacsv.read_csv(io.BytesIO(data), read_options=ro, parse_options=po, convert_options=co)
        except pa.ArrowInvalid as e:
            if "UTF8" not in str(e) and "utf8" not in str(e).lower():
                from ..prep import ParseFailure
                raise ParseFailure(f"{ref.member}: {e}") from e
            co = pacsv.ConvertOptions(column_types={c: pa.binary() for c in _dedupe(header)})
            t = pacsv.read_csv(io.BytesIO(data), read_options=ro, parse_options=po, convert_options=co)
            cols = []
            bad = 0
            for c in t.column_names:
                vals = []
                for v in t[c].to_pylist():
                    try:
                        vals.append(v.decode("utf-8"))
                    except UnicodeDecodeError:
                        bad += 1
                        vals.append(v.decode("utf-8", errors="replace"))
                cols.append(pa.array(vals, pa.string()))
            inc.hints.setdefault("decode_errors", {})[ref.member] = bad
            return pa.table(cols, names=t.column_names)

    # ------------------------------------------------------------ 5 normalize
    def normalize(self, inc, modality, tinfo, smap, ctx, findings):
        system = SYSTEMS[inc.hints["subsys"].split("-")[1]]
        if modality == "metrics":
            refs = [(k.split(":", 1)[1], r) for k, rs in inc.refs.items() if k.startswith("metrics:") for r in rs]
            if not refs:
                raise ModalityAbsent()
            for set_name, ref in sorted(refs):
                yield self._metrics(inc, ref, set_name, system, smap, ctx, findings)
        elif modality == "logs":
            if not inc.refs.get("logs"):
                raise ModalityAbsent()
            t = self._logs(inc, inc.refs["logs"][0], system, smap, ctx, findings)
            if t is not None:
                yield t
        elif modality == "traces":
            if not inc.refs.get("traces"):
                raise ModalityAbsent()
            t = self._traces(inc, inc.refs["traces"][0], system, smap, ctx, findings)
            if t is not None:
                yield t
        self._decode_findings(inc, findings, modality)

    def _decode_findings(self, inc, findings, modality):
        for member, n in (inc.hints.pop("decode_errors", {}) or {}).items():
            if n:
                findings.append(finding("PARSE_ERROR", f"{n} values with invalid UTF-8 replaced in {member}", modality))

    def _src_index(self, inc, ref: RawRef) -> int:
        return member_index(inc, ref.member)

    def _metrics(self, inc, ref, set_name, system, smap, ctx, findings) -> pa.Table:
        t = self._csv(inc, ref, ctx)
        names = t.column_names
        if not names or names[0] != "time":
            from ..prep import ParseFailure
            raise ParseFailure(f"{ref.member}: first column is not 'time'")
        n = t.num_rows
        ts_ns = _seconds_to_ns(t["time"])
        keep_cols, ent, met, kinds, sids = [], [], [], [], []
        dup_time = 0
        for j, c in enumerate(names[1:], start=1):
            if c == "time" or c.startswith("time."):
                dup_time += 1
                continue
            if "_" not in c:
                findings.append(finding("PARSE_ERROR", f"metric column without service prefix skipped: {c!r}", "metrics"))
                continue
            e, m = c.split("_", 1)
            sid, kind = self._sid(smap, system, e, inc.hints.get("foreign"))
            keep_cols.append(j), ent.append(e), met.append(m), kinds.append(kind), sids.append(sid)
        if dup_time:
            findings.append(finding("METRIC_CONSTANT", f"{dup_time} duplicate time column(s) ignored in {ref.member.rsplit('/', 1)[-1]}",
                                    "metrics", "info"))
        k = len(keep_cols)
        if k == 0 or n == 0:
            return None
        vals = np.empty((k, n), dtype=np.float64)
        null = np.empty((k, n), dtype=bool)
        bad = 0
        for i, j in enumerate(keep_cols):
            raw = t[names[j]]
            v = _to_float(raw)
            blank = np.asarray(pc.equal(raw, "").to_numpy(zero_copy_only=False), dtype=bool)
            literal_nan = np.asarray(pc.is_in(pc.utf8_lower(raw), pa.array(["nan", "-nan", "+nan"])).to_numpy(zero_copy_only=False), dtype=bool)
            nonnum = np.isnan(v) & ~blank & ~literal_nan
            bad += int(np.count_nonzero(nonnum))
            vals[i], null[i] = v, blank | nonnum
        if bad:
            findings.append(finding("PARSE_ERROR", f"{bad} non-numeric metric cells set to null ({ref.member.rsplit('/', 1)[-1]})", "metrics"))
        col_idx = np.repeat(np.arange(k, dtype=np.int32), n)
        row_idx = np.tile(np.arange(n, dtype=np.int64), k)
        flat, null_mask = vals.reshape(-1), null.reshape(-1)
        ts_valid = np.tile(~ts_ns.is_null().to_numpy(zero_copy_only=False), k) if ts_ns.null_count else np.ones(n * k, dtype=bool)
        tsf = np.tile(ts_ns.fill_null(0).to_numpy(zero_copy_only=False), k)
        def dict_col(values):
            return pa.DictionaryArray.from_arrays(pa.array(col_idx), pa.array(values, pa.string())).cast(pa.string())
        out = pa.table({
            "ts_ns": pa.array(tsf.astype(np.int64), mask=~ts_valid),
            "entity_raw": dict_col(ent), "entity_kind": dict_col(kinds), "service_id": dict_col(sids),
            "metric": dict_col(met), "metric_set": pa.array(np.full(len(flat), set_name, dtype=object), pa.string()),
            "value": pa.array(flat, mask=null_mask),
            "unit": pa.nulls(len(flat), pa.string()),
            "src_file": pa.array(np.full(len(flat), self._src_index(inc, ref), dtype=np.int32)),
            "src_row": pa.array(row_idx), "src_col": pa.array(np.asarray(keep_cols, dtype=np.int32)[col_idx]),
        })
        return out

    def _logs(self, inc, ref, system, smap, ctx, findings) -> pa.Table | None:
        t = self._csv(inc, ref, ctx)
        if t.num_rows == 0:
            return None
        cols = set(t.column_names)
        need = {"timestamp", "container_name", "message"}
        if not need <= cols:
            from ..prep import ParseFailure
            raise ParseFailure(f"{ref.member}: missing columns {sorted(need - cols)}")
        ts = _to_int(t["timestamp"])
        ent = t["container_name"].to_pylist()
        sid = [self._sid(smap, system, e, inc.hints.get("foreign"))[0] if e else None for e in ent]
        n = t.num_rows
        self._check_hhmm(t, ts, findings)
        return pa.table({
            "ts_ns": ts, "entity_raw": pa.array([e or None for e in ent], pa.string()), "service_id": pa.array(sid, pa.string()),
            "level": _nullable(t["level"]) if "level" in cols else pa.nulls(n, pa.string()),
            "message": t["message"],
            "template": _nullable(t["log_template"]) if "log_template" in cols else pa.nulls(n, pa.string()),
            "trace_id": pa.nulls(n, pa.string()), "span_id": pa.nulls(n, pa.string()),
            "src_file": pa.array(np.full(n, self._src_index(inc, ref), dtype=np.int32)),
            "src_row": pa.array(np.arange(n, dtype=np.int64)),
        })

    def _check_hhmm(self, t: pa.Table, ts: pa.Array, findings) -> None:
        """`time` (HH:MM) is not used; check it against `timestamp` on a sample for a constant offset."""
        if "time" not in t.column_names:
            return
        sample = min(t.num_rows, 500)
        hhmm = t["time"].slice(0, sample).to_pylist()
        tsv = ts.slice(0, sample).to_pylist()
        offs = []
        for h, x in zip(hhmm, tsv):
            m = re.match(r"^(\d{1,2}):(\d{2})$", h or "")
            if m and x is not None:
                mod = (x // 10**9 // 60) % 1440
                offs.append((int(m[1]) * 60 + int(m[2]) - mod) % 1440)
        if offs:
            top = max(set(offs), key=offs.count)
            agree = sum(1 for o in offs if min(abs(o - top), 1440 - abs(o - top)) <= 1) / len(offs)
            if agree < 0.9:
                findings.append(finding("TS_COLUMN_OFFSET", f"logs `time` agrees with `timestamp` on {agree:.0%} of a {len(offs)}-row sample", "logs"))

    def _traces(self, inc, ref, system, smap, ctx, findings) -> pa.Table | None:
        t = self._csv(inc, ref, ctx)
        if t.num_rows == 0:
            return None
        need = {"traceID", "spanID", "serviceName", "startTime", "duration"}
        if not need <= set(t.column_names):
            from ..prep import ParseFailure
            raise ParseFailure(f"{ref.member}: missing columns {sorted(need - set(t.column_names))}")
        start_us = _to_int(t["startTime"])
        dur_us = _to_int(t["duration"])
        if "startTimeMillis" in t.column_names:
            ms = _to_int(t["startTimeMillis"])
            mism = pc.sum(pc.not_equal(ms, pc.divide(start_us, 1000))).as_py() or 0
            if mism:
                findings.append(finding("TRACE_TIME_MISMATCH", f"{mism} rows with startTimeMillis != startTime//1000", "traces"))
        ent = t["serviceName"].to_pylist()
        sid = [self._sid(smap, system, e, inc.hints.get("foreign"))[0] if e else None for e in ent]
        n = t.num_rows
        return pa.table({
            "ts_ns": pc.multiply(start_us, 1000), "duration_ns": pc.multiply(dur_us, 1000),
            "trace_id": t["traceID"], "span_id": t["spanID"],
            "parent_span_id": _nullable(t["parentSpanID"]) if "parentSpanID" in t.column_names else pa.nulls(n, pa.string()),
            "entity_raw": pa.array([e or None for e in ent], pa.string()), "service_id": pa.array(sid, pa.string()),
            "operation": t["operationName"] if "operationName" in t.column_names else pa.nulls(n, pa.string()),
            "status_code": _nullable(t["statusCode"]) if "statusCode" in t.column_names else pa.nulls(n, pa.string()),
            "src_file": pa.array(np.full(n, self._src_index(inc, ref), dtype=np.int32)),
            "src_row": pa.array(np.arange(n, dtype=np.int64)),
        })

    # ------------------------------------------------------------ candidates (as the legacy loader)
    def candidates(self, inc, services_by_modality, smap, system):
        sets = [k.split(":", 1)[1] for k in inc.refs if k.startswith("metrics:")]
        out = set()
        if sets:
            out |= set(services_by_modality.get(f"metrics:{legacy_metric_set(inc.hints['subsys'].split('-')[0], sets)}", []))
        out |= set(services_by_modality.get("logs", [])) | set(services_by_modality.get("traces", []))
        return sorted(s for s in out if s and not smap.is_infra(system, s)), "telemetry"


# ---------------------------------------------------------------- helpers
def _is_under(p: Path, root: Path) -> bool:
    try:
        Path(p).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def _dedupe(names: list[str]) -> list[str]:
    seen, out = {}, []
    for n in names:
        if n in seen:
            seen[n] += 1
            out.append(f"{n}.{seen[n]}")
        else:
            seen[n] = 0
            out.append(n)
    return out


def _nullable(col: pa.ChunkedArray) -> pa.ChunkedArray:
    return pc.if_else(pc.equal(col, ""), pa.scalar(None, pa.string()), col)


def _to_float(col: pa.ChunkedArray) -> np.ndarray:
    try:
        return pc.cast(col, pa.float64()).to_numpy(zero_copy_only=False).astype(np.float64)
    except (pa.ArrowInvalid, pa.ArrowNotImplementedError):
        out = np.full(len(col), np.nan)
        for i, v in enumerate(col.to_pylist()):
            try:
                out[i] = float(v)
            except (TypeError, ValueError):
                pass
        return out


def _to_int(col: pa.ChunkedArray) -> pa.Array:
    """String column of integers (possibly written as floats, e.g. '0.0') -> int64 with nulls."""
    col = _nullable(col)
    try:
        return pc.cast(col, pa.int64()).combine_chunks()
    except (pa.ArrowInvalid, pa.ArrowNotImplementedError):
        out = []
        for v in col.to_pylist():
            if v is None:
                out.append(None)
                continue
            try:
                out.append(int(v))
            except ValueError:
                try:
                    out.append(int(float(v)))
                except ValueError:
                    out.append(None)
        return pa.array(out, pa.int64())


def _seconds_to_ns(col: pa.ChunkedArray) -> pa.Array:
    """Unix seconds as text -> int64 ns. Integral text is converted exactly; fractional text via
    float64 (sub-microsecond rounding only)."""
    col = _nullable(col)
    try:
        return pc.multiply(pc.cast(col, pa.int64()), 10**9).combine_chunks()
    except (pa.ArrowInvalid, pa.ArrowNotImplementedError):
        f = _to_float(col)
        ok = np.isfinite(f)
        return pa.array(np.where(ok, np.round(f * 1e9), 0).astype(np.int64), mask=~ok)
