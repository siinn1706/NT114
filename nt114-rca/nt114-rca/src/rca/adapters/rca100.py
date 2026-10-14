"""RCA-100 v1.1 adapter (AgenticOpsEval mirror): OpenTelemetry demo store on Alibaba Cloud ACK.

Layout: `RCA100/cases/tNNN/{task.json, metrics, logs, traces, events, alerts .parquet, topology.json}`
(pre-cut per case) and `RCA100/answer_key/{mapping.json, tNNN.gt.json}` (eval-only). The case key is
the opaque task id; `source_incident_id` is the answer-key case id (it names the fault, so it stays
in the eval-only zone).

Time and leakage rules (measured 2026-10-14 over all 103 cases):
- Anchor: the first OCCURRED event of the entry alert (`alerts.parquet`; equals `task.alert_trigger_time`
  in 95 of the 97 cases that have one). `task.alert_window` equals the answer key's `time_range`; its
  start precedes the alert by 49-519 s and its length is associated with the fault id and the root,
  and every export is cut relative to it (metrics from start - 3600 s, logs/traces from start - 1200 s,
  all ending near the window end). The stored window is therefore fixed around the alert:
  [t - 900 s, t + 120 s], the widest span every case covers on both sides (data start >= 949 s before
  the alert, window end >= 120 s after it). The source window end goes only to `truth_time.end_ns`.
- Log and trace exports stop at a row cap (229k-800k rows); in about half the cases they end before
  t + 120 s, which is recorded per incident as LOW_COVERAGE.
- Metric groups exported only for a few cases follow the label (`apm.metric.exception` only in the 4
  NullPointerException cases, `k8s.pod/pod_restart_count` only in the podCrashLoop and
  podRestartFlapping cases). Only (entity_set, metric) pairs exported in at least half the cases are
  kept (every other pair is in 102-103 of 103 cases); the rule uses no label.
- Visible context is the alert title and alert entity name only; `prompt_text` carries the alert's
  `trans_id`, which is the suffix of the answer-key case id. Alert rule text, events and topology stay
  raw refs. `chaosblade-operator` and other non-demo deployments are never candidates.
- Several tasks can be cut from one fault injection (identical events export, same first alert);
  they share `group.group_id` so audits and splits keep them together.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from ..data import canon
from ..identity import DEPLOYMENT_POD, ServiceMap, load_aliases
from ..quality import finding
from . import register
from .aiops2025 import _level, iso_to_ns
from .base import (Adapter, BuildContext, DiscoveredIncident, LabelDraft, ModalityAbsent, RawRef, TimeInfo,
                   checksum_index, member_index)

DEFAULT_ROOT = "agenticopseval/gitlab-69cf36430b43/RCA100"
SYSTEM = "otel-demo"
WINDOW = {"pre_s": 900, "post_s": 120}       # measured bounds; `windows.rca100` in the config overrides
FAULT_FAMILY = {
    "F001-nodeDown": "node", "F002-threadExhaustion": "other", "F004-trafficHotspot": "other",
    "F005-messageQueueBacklog": "other", "F006-trafficSurge": "other", "F007-memoryPressure": "memory",
    "F009-cacheBreakdown": "other", "F010-slowSQL": "other", "F011-codeDefect": "code-defect",
    "F012-cpuDeadLoop": "cpu", "F014-httpError5xx": "code-defect", "F016-rateLimiting": "config",
    "F018-dbNetworkLatency": "network-delay", "F020-loadBalancerFailure": "other", "F022-fullGC": "jvm",
    "F023-nullPointerException": "code-defect", "F025-diskIOHigh": "disk-io", "F026-nodeCpuHigh": "node",
    "F029-redisUnavailable": "other", "F031-nodeMemoryOOM": "node", "F034-cpuFullLoad": "cpu",
    "F036-replicaScaleDown": "pod-lifecycle", "F039-resourceLimitMisconfig": "config",
    "F050-podCrashLoop": "pod-lifecycle", "F051-podPendingUnschedulable": "pod-lifecycle",
    "F052-podRestartFlapping": "pod-lifecycle", "F056-networkPolicyIsolation": "network-other",
    "F057-dnsResolutionFailure": "dns",
}
METRIC_SET = {"apm.service.legacy": "default", "k8s.deployment": "default", "apm.metric.jvm": "default",
              "apm.metric.thread": "default", "apm.metric.exception": "default", "apm.instance": "instance",
              "apm.operation": "operation", "k8s.pod": "pod", "k8s.node": "node", "k8s.namespace": "cluster",
              "k8s.cluster": "cluster"}
OTEL_ERROR = "2"      # OTel StatusCode: 0 unset, 1 ok, 2 error


@register
class Rca100Adapter(Adapter):
    name = "rca100"
    version = "1.0.2"
    dataset_id = "rca100"
    source_ids = ("agenticopseval",)

    def __init__(self):
        self._smap: ServiceMap | None = None

    def _root(self, ctx) -> Path:
        return ctx.raw_root / (ctx.dataset_cfg.get("root") or DEFAULT_ROOT)

    def _ref(self, ctx, rel: str, sums: dict) -> RawRef:
        p = self._root(ctx) / rel
        member = p.resolve().relative_to(ctx.raw_root.resolve()).as_posix()
        return RawRef(self.source_ids[0], member, sums.get(member), p.stat().st_size)

    def _path(self, ctx, ref: RawRef) -> Path:
        return ctx.raw_root / ref.member

    def _tasks(self, ctx) -> list[str]:
        return sorted(p.name for p in (self._root(ctx) / "cases").iterdir() if (p / "task.json").is_file())

    # ------------------------------------------------------------ 1 discover
    def discover(self, ctx: BuildContext):
        root = self._root(ctx)
        sums = checksum_index(ctx)
        with open(root / "answer_key" / "mapping.json", encoding="utf-8") as f:
            mapping = json.load(f)["task_to_case_id"]
        tasks = self._tasks(ctx)
        # label-free metric allowlist: (entity_set, metric) pairs exported in at least half the cases
        # (measured: 63 pairs in 102-103 cases, the two label-following pairs in 2 and 4 cases)
        seen: dict[tuple, int] = defaultdict(int)
        for t in tasks:
            m = pq.read_table(root / "cases" / t / "metrics.parquet", columns=["entity_set", "metric"])
            for p in set(zip(m["entity_set"].to_pylist(), m["metric"].to_pylist())):
                seen[p] += 1
        pairs = {p for p, k in seen.items() if 2 * k >= len(tasks)}
        win = (ctx.config.get("windows") or {}).get("rca100") or WINDOW
        occs = {}
        for t in tasks:
            al = pq.read_table(root / "cases" / t / "alerts.parquet", columns=["status", "time_s", "time"]).to_pylist()
            occs[t] = sorted((a["time_s"], a["time"]) for a in al if a["status"] == "OCCURRED")
        shared = self._shared_injections(ctx, tasks, occs, sums)
        for t in tasks:
            c = f"cases/{t}"
            refs = {"label": [self._ref(ctx, f"answer_key/{t}.gt.json", sums), self._ref(ctx, "answer_key/mapping.json", sums)],
                    "metrics:default": [self._ref(ctx, f"{c}/metrics.parquet", sums)],
                    "logs": [self._ref(ctx, f"{c}/logs.parquet", sums)], "traces": [self._ref(ctx, f"{c}/traces.parquet", sums)],
                    "aux": [self._ref(ctx, f"{c}/{n}", sums) for n in ("task.json", "alerts.parquet", "events.parquet", "topology.json")]}
            with open(root / c / "task.json", encoding="utf-8") as f:
                task = json.load(f)
            occ = occs[t]
            ent = (task.get("alert_entity") or {}).get("entity_name") or ""
            yield DiscoveredIncident(
                source_incident_key=t, source_incident_id=f"rca100:{mapping[t]}", refs=refs,
                hints={"task": task, "alert": occ[0] if occ else None, "allow_metrics": sorted(pairs or ()),
                       "group_key": shared.get(t),
                       "pre_s": int(win["pre_s"]), "post_s": int(win["post_s"]),
                       "visible_text": f"{task.get('alert_title', '')} | {ent}".strip(" |") or None,
                       "dataset_version": Path(ctx.dataset_cfg.get("root") or DEFAULT_ROOT).parent.name,
                       "source_id": self.source_ids[0]})

    def _shared_injections(self, ctx, tasks: list[str], occs: dict, sums: dict) -> dict[str, str]:
        """Tasks cut from one fault injection: byte-identical events or logs export, or the same first
        alert second (measured: 28 tasks in 11 groups, each group one fault id and root). Returns
        task -> `rca100-injection:<smallest task id>` for tasks in a group of two or more."""
        def sha(rel):
            ref = self._ref(ctx, rel, sums)
            return ref.sha256 or hashlib.sha256(self._path(ctx, ref).read_bytes()).hexdigest()

        parent = {t: t for t in tasks}

        def find(t):
            while parent[t] != t:
                parent[t] = parent[parent[t]]
                t = parent[t]
            return t

        first: dict[tuple, str] = {}
        for t in tasks:
            keys = [("events", sha(f"cases/{t}/events.parquet")), ("logs", sha(f"cases/{t}/logs.parquet"))]
            if occs[t]:
                keys.append(("alert", occs[t][0][0]))
            for k in keys:
                if k in first:
                    a, b = find(first[k]), find(t)
                    parent[max(a, b)] = min(a, b)
                else:
                    first[k] = t
        members = defaultdict(list)
        for t in tasks:
            members[find(t)].append(t)
        return {t: f"rca100-injection:{min(ms)}" for ms in members.values() if len(ms) > 1 for t in ms}

    # ------------------------------------------------------------ 2 label
    def read_label(self, inc: DiscoveredIncident, ctx: BuildContext):
        with open(self._path(ctx, inc.refs["label"][0]), encoding="utf-8") as f:
            gt = json.load(f)
        smap = self.service_map(ctx)
        fault_id = inc.source_incident_id.split(":", 1)[1].split(".", 1)[0]
        findings, notes, entities = [], [], []
        for r in gt["root_cause_entities"]:
            if canon(r) in smap.known[SYSTEM]:
                entities.append({"raw": r, "kind": "service", "service_id": smap.resolve(SYSTEM, r, "service")})
            elif DEPLOYMENT_POD.match(r) and canon(DEPLOYMENT_POD.match(r)["d"]) in smap.known[SYSTEM]:
                entities.append({"raw": r, "kind": "pod", "service_id": smap.resolve(SYSTEM, r, "pod")})
            elif r.startswith("cn-") or r in self._nodes(ctx):
                entities.append({"raw": r, "kind": "node", "service_id": None})
            else:
                entities.append({"raw": r, "kind": "unknown", "service_id": None})
                findings.append(finding("LABEL_INVALID", f"root entity {r!r} is neither a demo service, its pod, nor a node"))
        sids = sorted({e["service_id"] for e in entities if e["service_id"]})
        kinds = {e["kind"] for e in entities}
        family = FAULT_FAMILY.get(fault_id, "unknown")
        if family == "unknown":
            findings.append(finding("LABEL_INVALID", f"fault id {fault_id!r} outside the documented vocabulary", severity="warn"))
            notes.append(f"unknown fault id {fault_id!r}")
        valid = bool(entities) and "unknown" not in kinds
        if not valid:
            primary, gran, tier, reason = None, "service", "excluded", "root entity not mappable"
        elif kinds == {"node"}:
            primary, gran, tier, reason = None, "node", "B", "node-level fault: no service root"
        elif len(sids) == 1:
            primary, gran = sids[0], ("pod" if kinds == {"pod"} else "service")
            tier, reason = "A", f"{gran}-level root mapped to a demo service"
        else:
            primary, gran, tier, reason = None, "multi-service", "A", "set-scoring-only"
        end = gt.get("time_range_end")
        lab = LabelDraft(
            original={"root_cause_entities": gt["root_cause_entities"], "expected_fault_id": fault_id},
            entities=entities, root_service_ids=sids, primary_root_service=primary, label_granularity=gran,
            fault_type_raw=fault_id, fault_family=family, label_source="label-file", injection_kind="injected",
            label_validity="valid" if valid else "invalid", validity_notes=notes, eval_tier=tier, eval_tier_reason=reason,
            fault_cell=f"L2/{SYSTEM}/{primary or ('+'.join(sids) or entities[0]['raw'] if entities else 'unknown')}/{family}",
            system=SYSTEM, dataset_subset="RCA100", lineage_group="L2",
            group_key=inc.hints.get("group_key"),
            label_artifacts=[{"kind": "rca100:answer_key", "ref": inc.refs["label"][0].member}],
            truth_end_ns=int(datetime.fromisoformat(end).timestamp() * 1e9) if end else None)
        return lab, findings

    # ------------------------------------------------------------ 3 identity
    def service_map(self, ctx: BuildContext) -> ServiceMap:
        """Services: the `apm.service` entities of every case topology (the 19 demo services)."""
        if self._smap is None:
            from ..prep import ALIASES
            smap = ServiceMap(aliases=load_aliases(ALIASES))
            names = set()
            for t in self._tasks(ctx):
                with open(self._root(ctx) / "cases" / t / "topology.json", encoding="utf-8") as f:
                    names |= {e["name"] for e in json.load(f)["entities"] if e.get("type") == "apm.service"}
            smap.declare_services(SYSTEM, sorted(names))
            self._smap = smap
        return self._smap

    def _nodes(self, ctx) -> set[str]:
        if not hasattr(self, "_node_names"):
            names = set()
            for t in self._tasks(ctx):
                with open(self._root(ctx) / "cases" / t / "topology.json", encoding="utf-8") as f:
                    names |= {e["name"] for e in json.load(f)["entities"] if e.get("type") == "k8s.node"}
            self._node_names = names
        return self._node_names

    def _service(self, smap, name: str | None, kind: str) -> str | None:
        """Demo services only; any other deployment (chaosblade-operator, coredns, ...) gets no id."""
        if not name:
            return None
        if kind == "pod":
            return smap.map(SYSTEM, name, "pod")
        if canon(name) in smap.known[SYSTEM]:
            return smap.map(SYSTEM, name, "service")
        return smap.record(SYSTEM, name, None, "not-a-demo-service", "infra")

    # ------------------------------------------------------------ 4 anchor
    def anchor_and_window(self, inc: DiscoveredIncident, label: LabelDraft, ctx: BuildContext):
        al = inc.hints["alert"]
        if al is None:
            raise ValueError("no OCCURRED entry alert")
        t, raw = int(al[0]), al[1]
        findings = []
        trig = inc.hints["task"].get("alert_trigger_time")
        if trig:
            d = int(datetime.fromisoformat(trig).timestamp()) - t
            if d:
                findings.append(finding("ANCHOR_FIELD_DISAGREE", f"task alert_trigger_time - first OCCURRED alert = {d} s; alert used"))
        pre, post = inc.hints["pre_s"], inc.hints["post_s"]
        return TimeInfo(anchor_ns=t * 10**9, anchor_kind="alert",
                        anchor_original={"value": raw, "unit": "iso8601", "tz": "+08:00"},
                        end_ns=None, window_start_ns=(t - pre) * 10**9, window_end_ns=(t + post) * 10**9), findings

    # ------------------------------------------------------------ 5 normalize
    def normalize(self, inc, modality, tinfo, smap, ctx, findings):
        ref = (inc.refs.get("metrics:default") if modality == "metrics" else inc.refs.get(modality)) or []
        if not ref:
            raise ModalityAbsent()
        ref = ref[0]
        if modality == "metrics":
            t = self._metrics(inc, ref, smap, ctx, findings)
        elif modality == "logs":
            t = self._logs(inc, ref, smap, ctx)
        else:
            t = self._traces(inc, ref, smap, ctx)
        if t is None:
            return
        if modality in ("logs", "traces") and t.num_rows:
            end = pc.max(t["ts_ns"]).as_py()
            short = tinfo.window_end_ns - end
            if short > 30 * 10**9:
                rel = (end - tinfo.anchor_ns) / 1e9
                findings.append(finding("LOW_COVERAGE", f"{modality} end {abs(rel):.0f} s {'after' if rel >= 0 else 'before'} the anchor "
                                                        f"(source export stops at {pq.ParquetFile(self._path(ctx, ref)).metadata.num_rows} rows); "
                                                        "the post-anchor side is incomplete", modality))
        yield t

    def _read(self, ctx, ref, columns):
        from ..prep import ParseFailure
        try:
            return pq.read_table(self._path(ctx, ref), columns=columns)
        except (pa.ArrowInvalid, OSError) as e:
            raise ParseFailure(f"{ref.member}: {e}") from e

    def _metrics(self, inc, ref, smap, ctx, findings) -> pa.Table | None:
        t = self._read(ctx, ref, ["time", "entity_set", "entity_name", "metric", "value"])
        n0 = t.num_rows
        if n0 == 0:
            return None
        allow = {tuple(p) for p in inc.hints["allow_metrics"]}
        es, me = t["entity_set"].to_pylist(), t["metric"].to_pylist()
        keep = np.array([(a, b) in allow for a, b in zip(es, me)])
        if not keep.all():
            dropped = defaultdict(int)
            for a, b, k in zip(es, me, keep):
                if not k:
                    dropped[f"{a}/{b}"] += 1
            findings.append(finding("METRIC_GROUP_DROPPED", "metric groups exported in fewer than half the cases dropped "
                                                          "(their presence follows the fault label): "
                                    + ", ".join(f"{k} {v} rows" for k, v in sorted(dropped.items())), "metrics", "info"))
        idx = np.flatnonzero(keep)
        t = t.take(pa.array(idx))
        n = t.num_rows
        es, names = t["entity_set"].to_pylist(), t["entity_name"].to_pylist()
        ents, kinds, sids, sets, mnames = [], [], [], [], []
        for s, nm, m in zip(es, names, t["metric"].to_pylist()):
            nm = nm or None
            if s == "apm.operation":
                svc, _, op = (nm or "").partition("::")
                ents.append(nm), kinds.append("operation"), sids.append(self._service(smap, svc, "service"))
                mnames.append(m)
            elif s == "apm.instance":
                kind = "pod" if nm and DEPLOYMENT_POD.match(nm) else "service"
                ents.append(nm), kinds.append(kind), sids.append(self._service(smap, nm, kind)), mnames.append(m)
            elif s in ("k8s.node",):
                ents.append(nm), kinds.append("node"), sids.append(None), mnames.append(m)
            elif s in ("k8s.namespace", "k8s.cluster"):
                ents.append(nm), kinds.append("namespace"), sids.append(None), mnames.append(m)
            elif s == "k8s.pod":
                ents.append(nm), kinds.append("pod"), sids.append(self._service(smap, nm, "pod")), mnames.append(m)
            else:                       # apm.service.legacy, k8s.deployment, apm.metric.*
                ents.append(nm), kinds.append("service"), sids.append(self._service(smap, nm, "service")), mnames.append(m)
            sets.append(METRIC_SET.get(s, "other"))
        return pa.table({
            "ts_ns": pc.multiply(pc.cast(t["time"], pa.int64()), 1000), "entity_raw": pa.array(ents, pa.string()),
            "entity_kind": pa.array(kinds, pa.string()), "service_id": pa.array(sids, pa.string()),
            "metric": pa.array(mnames, pa.string()), "metric_set": pa.array(sets, pa.string()),
            "value": pc.cast(t["value"], pa.float64(), safe=False), "unit": pa.nulls(n, pa.string()),
            "src_file": pa.array(np.full(n, member_index(inc, ref.member), dtype=np.int32)),
            "src_row": pa.array(idx.astype(np.int64)), "src_col": pa.array(np.full(n, 6, dtype=np.int32))})

    def _logs(self, inc, ref, smap, ctx) -> pa.Table | None:
        t = self._read(ctx, ref, ["_time_", "_pod_name_", "_container_name_", "content"])
        n = t.num_rows
        if n == 0:
            return None
        pods, conts = t["_pod_name_"].to_pylist(), t["_container_name_"].to_pylist()
        sids = [self._service(smap, p, "pod") or (self._service(smap, c, "service") if c else None) for p, c in zip(pods, conts)]
        msgs = t["content"].to_pylist()
        return pa.table({
            "ts_ns": iso_to_ns(t["_time_"]), "entity_raw": pa.array(pods, pa.string()), "service_id": pa.array(sids, pa.string()),
            "level": pa.array([_level(m) for m in msgs], pa.string()), "message": pa.array(msgs, pa.string()),
            "template": pa.nulls(n, pa.string()), "trace_id": pa.nulls(n, pa.string()), "span_id": pa.nulls(n, pa.string()),
            "src_file": pa.array(np.full(n, member_index(inc, ref.member), dtype=np.int32)),
            "src_row": pa.array(np.arange(n, dtype=np.int64))})

    def _traces(self, inc, ref, smap, ctx) -> pa.Table | None:
        t = self._read(ctx, ref, ["traceId", "spanId", "parentSpanId", "spanName", "startTime", "duration", "serviceName", "statusCode"])
        n = t.num_rows
        if n == 0:
            return None
        svc = t["serviceName"].to_pylist()
        sid_of = {s: self._service(smap, s, "service") for s in set(svc) if s}
        parent = t["parentSpanId"]
        parent = pc.if_else(pc.or_(pc.equal(parent, ""), pc.equal(parent, "0000000000000000")), pa.scalar(None, pa.string()), parent)
        # OTel status (0 unset, 1 ok, 2 error) -> gRPC-style "0" ok / "2" error, as the evidence code expects
        status = pc.if_else(pc.equal(t["statusCode"], OTEL_ERROR), pa.scalar("2"), pa.scalar("0"))
        return pa.table({
            "ts_ns": pc.cast(t["startTime"], pa.int64()), "duration_ns": pc.cast(t["duration"], pa.int64()),
            "trace_id": t["traceId"], "span_id": t["spanId"], "parent_span_id": parent,
            "entity_raw": pa.array(svc, pa.string()), "service_id": pa.array([sid_of.get(s) for s in svc], pa.string()),
            "operation": t["spanName"], "status_code": status,
            "src_file": pa.array(np.full(n, member_index(inc, ref.member), dtype=np.int32)),
            "src_row": pa.array(np.arange(n, dtype=np.int64))})
