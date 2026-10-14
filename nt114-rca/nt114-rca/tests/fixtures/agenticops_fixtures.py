"""Synthetic AgenticOpsEval trees: AIOps2025 (day archives already extracted, with receipts) and RCA100
(pre-cut cases plus the answer key). Shapes follow the measured raw files; values are generated."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

UTC = timezone.utc
CST = timezone(timedelta(hours=8))
AIOPS_SERVICES = ["frontend", "cartservice", "checkoutservice", "redis-cart"]
AIOPS_PODS = {"frontend": ["frontend-0"], "cartservice": ["cartservice-0"], "checkoutservice": ["checkoutservice-0"],
              "redis-cart": ["redis-cart-0"]}
AIOPS_DAYS = ["2025-06-06", "2025-06-07"]          # extracted; 2025-06-08 has no archive


def _iso_z(s: float) -> str:
    return datetime.fromtimestamp(s, UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _utc(s: str) -> int:
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


def _write(p: Path, table: pa.Table) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, p)


# ---------------------------------------------------------------- AIOps2025
AIOPS_LABELS = [
    # service-level fault on one service
    {"uuid": "a-svc", "fault_category": "code", "fault_type": "code error", "instance_type": "service",
     "service": "checkoutservice", "instance": "checkoutservice", "source": "checkoutservice", "destination": "",
     "start_time": "2025-06-06T03:10:00Z", "end_time": "2025-06-06T03:15:00Z",
     "key_observations": [{"type": "log", "keyword": ["checkout failed"]}], "key_metrics": ["rrt"],
     "fault_description": ["checkoutservice code error"]},
    # node fault
    {"uuid": "c-node", "fault_category": "node", "fault_type": "node cpu stress", "instance_type": "node",
     "service": "", "instance": "aiops-k8s-01", "source": "", "destination": "",
     "start_time": "2025-06-06T05:00:00Z", "end_time": "2025-06-06T05:05:00Z",
     "key_observations": [], "key_metrics": ["node_cpu_usage_rate"], "fault_description": ["cpu stress on node"]},
    # multi-entity network fault with an empty service field; window crosses UTC+8 midnight (23:55)
    {"uuid": "b-net", "fault_category": "network", "fault_type": "network loss", "instance_type": "service",
     "service": "", "instance": ["cartservice", "redis-cart", "redis-cart-0"], "source": "cartservice",
     "destination": "redis-cart", "start_time": "2025-06-06T15:55:00Z", "end_time": "2025-06-06T16:00:00Z",
     "key_observations": [], "key_metrics": ["rrt"], "fault_description": ["loss between cart and redis"]},
    # pod-level fault on a TiDB component
    {"uuid": "d-pod", "fault_category": "io", "fault_type": "io fault", "instance_type": "pod",
     "service": "", "instance": ["tidb-tikv-0", "tidb-tikv"], "source": "", "destination": "",
     "start_time": "2025-06-07T01:00:00Z", "end_time": "2025-06-07T01:05:00Z", "path": "/var/lib/tikv",
     "key_observations": [], "key_metrics": ["io_util"], "fault_description": ["io fault on tikv"]},
    # a day whose archive is missing: no telemetry at all
    {"uuid": "e-gap", "fault_category": "pod", "fault_type": "pod kill", "instance_type": "pod",
     "service": "", "instance": "frontend-0", "source": "", "destination": "",
     "start_time": "2025-06-08T02:00:00Z", "end_time": "2025-06-08T02:00:00Z",
     "key_observations": [], "key_metrics": [], "fault_description": ["pod kill"]},
]


def _aiops_hour_logs(t0: int, seed: int) -> pa.Table:
    rng = np.random.default_rng(seed)
    rows = {"k8_namespace": [], "@timestamp": [], "agent_name": [], "k8_pod": [], "message": [], "k8_node_name": []}
    for s in range(t0, t0 + 3600, 10):
        for svc, pods in AIOPS_PODS.items():
            for pod in pods:
                err = rng.random() < 0.05
                rows["k8_namespace"].append("hipstershop")
                rows["@timestamp"].append(_iso_z(s + rng.random()))
                rows["agent_name"].append("filebeat")
                rows["k8_pod"].append(pod)
                rows["message"].append(json.dumps({"severity": "error" if err else "info",
                                                   "message": f"{svc} request {'failed' if err else 'ok'}"}))
                rows["k8_node_name"].append("aiops-k8s-01")
    rows["k8_pod"][0] = "example-ant-29160960-lpx4l"          # a non-hipstershop pod (no service id)
    return pa.table(rows)


_TAG = pa.struct([("key", pa.string()), ("type", pa.string()), ("value", pa.string())])
_REF = pa.struct([("refType", pa.string()), ("traceID", pa.string()), ("spanID", pa.string())])
_PROC = pa.struct([("serviceName", pa.string()), ("tags", pa.list_(_TAG))])


def _aiops_hour_traces(t0: int, seed: int) -> pa.Table:
    rng = np.random.default_rng(seed)
    cols = {k: [] for k in ("traceID", "spanID", "flags", "operationName", "references", "startTime",
                            "startTimeMillis", "duration", "tags", "logs", "process")}

    def span(tid, sid, parent, op, start_us, dur_us, svc, tags):
        cols["traceID"].append(tid), cols["spanID"].append(sid), cols["flags"].append(1)
        cols["operationName"].append(op)
        cols["references"].append([{"refType": "CHILD_OF", "traceID": tid, "spanID": parent}] if parent else [])
        cols["startTime"].append(start_us), cols["startTimeMillis"].append(start_us // 1000)
        cols["duration"].append(dur_us), cols["tags"].append(tags), cols["logs"].append(None)
        cols["process"].append({"serviceName": svc, "tags": [{"key": "ip", "type": "string", "value": "10.0.0.9"}]})

    for k, s in enumerate(range(t0, t0 + 3600, 20)):
        tid = f"{seed:04x}{k:08x}"
        st = s * 1_000_000 + int(rng.integers(0, 10**6))
        err = rng.random() < 0.05
        span(tid, f"{tid}-f", None, "hipstershop.Frontend/Cart", st, 9000, "frontend",
             [{"key": "http.status_code", "type": "int64", "value": "500" if err else "200"}])
        span(tid, f"{tid}-c", f"{tid}-f", "hipstershop.CartService/GetCart", st + 100, 5000, "cartservice",
             [{"key": "status.code", "type": "int64", "value": "0"}])
        # client spans to redis, emitted under the process name `redis`
        span(tid, f"{tid}-r", f"{tid}-c", "HGET", st + 200, 800, "redis",
             [{"key": "peer.service", "type": "string", "value": "redis-cart:6379"},
              {"key": "db.system", "type": "string", "value": "redis"}] + ([{"key": "error", "type": "bool", "value": "true"}] if err else []))
    return pa.table({**{k: cols[k] for k in ("traceID", "spanID")}, "flags": pa.array(cols["flags"], pa.int64()),
                     "operationName": cols["operationName"], "references": pa.array(cols["references"], pa.list_(_REF)),
                     "startTime": pa.array(cols["startTime"], pa.int64()), "startTimeMillis": pa.array(cols["startTimeMillis"], pa.int64()),
                     "duration": pa.array(cols["duration"], pa.int64()), "tags": pa.array(cols["tags"], pa.list_(_TAG)),
                     "logs": pa.array(cols["logs"], pa.null()), "process": pa.array(cols["process"], _PROC)})


def _aiops_day_metrics(day: str, seed: int) -> dict[str, pa.Table]:
    """{path under metric-parquet/: table} for one UTC+8 day, one row per minute."""
    rng = np.random.default_rng(seed)
    d0 = int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=CST).timestamp())
    ts = list(range(d0, d0 + 86400, 60))
    times = [_iso_z(s) for s in ts]
    n = len(ts)
    out = {}

    def apm(obj, otype):
        return {"time": times, "client_error": rng.poisson(1, n).astype(float), "client_error_ratio": rng.random(n),
                "error": rng.poisson(1, n).astype(float), "error_ratio": rng.random(n), "object_id": [obj] * n,
                "object_type": [otype] * n, "request": 100 + rng.normal(0, 3, n), "response": 100 + rng.normal(0, 3, n),
                "rrt": 1500 + rng.normal(0, 20, n), "rrt_max": 9000 + rng.normal(0, 200, n),
                "server_error": rng.poisson(1, n).astype(float), "server_error_ratio": rng.random(n), "timeout": np.zeros(n)}
    for svc in AIOPS_SERVICES:
        out[f"apm/service/service_{svc}_{day}.parquet"] = pa.table(apm(svc, "service"))
    out[f"apm/pod/pod_checkoutservice-0 (deleted)_{day}.parquet"] = pa.table(apm("checkoutservice-0 (deleted)", "pod"))
    out[f"apm/pod_ns_hipstershop_{day}.parquet"] = pa.table(apm("hipstershop", "namespace"))

    def infra(kpi, rows):
        cols = {"time": [], "cf": [], "device": [], "instance": [], "kpi_key": [], "kubernetes_node": [],
                "mountpoint": [], "namespace": [], "object_type": [], "pod": [], "sql_type": [], "type": [], kpi: []}
        for r in rows:
            for k in range(n):
                cols["time"].append(times[k]), cols["kpi_key"].append(kpi), cols[kpi].append(float(r.get("v", 1.0) + rng.normal(0, .01)))
                for c in ("cf", "device", "instance", "kubernetes_node", "mountpoint", "namespace", "object_type", "pod", "sql_type", "type"):
                    cols[c].append(r.get(c, "null"))
        return pa.table(cols)
    out[f"infra/infra_pod/infra_pod_pod_cpu_usage_{day}.parquet"] = infra(
        "pod_cpu_usage", [{"object_type": "pod", "pod": p, "namespace": "hipstershop", "v": 0.2} for ps in AIOPS_PODS.values() for p in ps])
    out[f"infra/infra_node/infra_node_node_cpu_usage_rate_{day}.parquet"] = infra(
        "node_cpu_usage_rate", [{"object_type": "node", "kubernetes_node": "aiops-k8s-01", "instance": "aiops-k8s-01", "v": 30.0}])
    # tidb-server status port 10080; the block cache rows carry the TiKV port 20180 under object_type tidb
    out[f"infra/infra_tidb/infra_tidb_qps_{day}.parquet"] = infra(
        "qps", [{"object_type": "tidb", "instance": "10.233.1.1:10080", "type": "Select", "v": 10.0}])
    out[f"infra/infra_tidb/infra_tidb_block_cache_size_{day}.parquet"] = infra(
        "block_cache_size", [{"object_type": "tidb", "instance": "10.233.1.2:20180", "cf": "all", "v": 1e9}])
    out[f"other/infra_tikv_io_util_{day}.parquet"] = infra(
        "io_util", [{"object_type": "tikv", "instance": "10.233.1.2:20180", "v": 0.1},
                    {"object_type": "tikv", "instance": "10.0.0.5:9100", "kubernetes_node": "aiops-k8s-01", "device": "vda", "v": 0.3}])
    out[f"other/infra_pd_region_count_{day}.parquet"] = infra(
        "region_count", [{"object_type": "pd", "instance": "tidb-pd-0", "v": 500.0}])
    return out


def aiops_tree(data_home: Path, labels: list[dict] | None = None) -> Path:
    """raw/agenticopseval-test/AIOps2025 (labels, archive stand-ins) and its extraction under work/extract."""
    labels = labels if labels is not None else AIOPS_LABELS
    raw = data_home / "raw" / "agenticopseval-test" / "AIOps2025"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "groundtruth.jsonl").write_text("".join(json.dumps(g) + "\n" for g in labels), encoding="utf-8")
    (raw / "input.json").write_text(json.dumps([{"uuid": g["uuid"], "Anomaly Description": "an incident"} for g in labels]),
                                    encoding="utf-8")
    ex = data_home / "work" / "extract" / "agenticopseval-test" / "AIOps2025"
    hours = {"2025-06-06": [10, 11, 12, 13, 23], "2025-06-07": [0, 8, 9]}
    for k, day in enumerate(AIOPS_DAYS):
        (raw / f"{day}.tar.gz").write_bytes(b"archive stand-in")
        files: dict[str, pa.Table] = {}
        for h in hours[day]:
            t0 = int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=CST).timestamp()) + h * 3600
            files[f"{day}/log-parquet/log_filebeat-server_{day}_{h:02d}-00-00.parquet"] = _aiops_hour_logs(t0, 100 * k + h)
            files[f"{day}/trace-parquet/trace_jaeger-span_{day}_{h:02d}-00-00.parquet"] = _aiops_hour_traces(t0, 100 * k + h)
        for rel, t in _aiops_day_metrics(day, 7 + k).items():
            files[f"{day}/metric-parquet/{rel}"] = t
        members = {}
        for rel, t in files.items():
            p = ex / day / rel
            _write(p, t)
            members[rel] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "size": p.stat().st_size}
        # AppleDouble entries are skipped by extraction; a stray one on disk must be ignored
        junk = ex / day / day / "log-parquet" / f"._log_filebeat-server_{day}_10-00-00.parquet"
        junk.write_bytes(b"\x00\x05\x16\x07 not parquet")
        (ex / day / ".extract.json").write_text(json.dumps({"archive": f"{day}.tar.gz", "complete": True, "members": members}),
                                                encoding="utf-8")
    return raw


# ---------------------------------------------------------------- RCA100
RCA100_SERVICES = ["frontend", "checkout", "payment", "cart", "inventory"]
RCA100_NODES = ["cn-hongkong.10.0.2.37", "cn-hongkong.10.0.2.71"]
RCA100_CASES = {
    # task: (case id in the answer key, root entities, first OCCURRED alert (UTC), alert_trigger_time, log/trace end offset)
    "t001": ("F014-httpError5xx.aaa", ["payment"], "2026-04-25T05:20:26Z", "", 120),
    "t002": ("F050-podCrashLoop.bbb", ["cart-64944cd445-8pbgx"], "2026-04-25T07:10:00Z", "", 60),
    "t003": ("F001-nodeDown.ccc", ["cn-hongkong.10.0.2.37"], "2026-04-25T09:00:00Z", "", -100),
    "t004": ("F023-nullPointerException.ddd", ["inventory"], "2026-04-25T11:30:00Z", "2026-04-25T19:30:30+08:00", 120),
}
# metric groups present only in the case of one fault (as measured on the real export)
LABEL_FOLLOWING = {"t002": ("k8s.pod", "pod_restart_count"), "t004": ("apm.metric.exception", "arms_exception_requests_error_count_raw")}


def _rca100_metrics(alert: int, extra, seed: int) -> pa.Table:
    rng = np.random.default_rng(seed)
    rows = {k: [] for k in ("time", "domain", "entity_set", "entity_id", "entity_name", "metric", "value", "metric_set_id", "service")}

    def add(es, name, metric, base):
        for s in range(alert - 3600 - 600, alert + 240, 30):
            rows["time"].append(s * 1_000_000), rows["domain"].append(es.split(".")[0]), rows["entity_set"].append(es)
            rows["entity_id"].append(hashlib.md5(name.encode()).hexdigest()), rows["entity_name"].append(name)
            rows["metric"].append(metric), rows["value"].append(float(base + rng.normal(0, base * 0.01 + 1e-3)))
            rows["metric_set_id"].append(f"{es}@set"), rows["service"].append("None")
    for svc in RCA100_SERVICES:
        add("apm.service.legacy", svc, "latency", 0.01)
        add("k8s.deployment", svc, "deployment_cpu_usage_total", 0.5)
        add("apm.operation", f"{svc}::/api/op", "error_count", 1.0)
    add("k8s.deployment", "chaosblade-operator", "deployment_cpu_usage_total", 0.1)
    for node in RCA100_NODES:
        add("k8s.node", node, "node_ready_status", 1.0)
    if extra:
        add(extra[0], "cart-64944cd445-8pbgx" if extra[0] == "k8s.pod" else "inventory", extra[1], 1.0)
    return pa.table({**rows, "time": pa.array(rows["time"], pa.int64())})


def _rca100_logs(alert: int, end_off: int, seed: int) -> pa.Table:
    rng = np.random.default_rng(seed)
    cols = {k: [] for k in ("content", "_time_", "_container_name_", "_pod_name_", "_namespace_")}
    for s in np.arange(alert - 1200, alert + end_off, 2.0):
        for svc in RCA100_SERVICES:
            err = rng.random() < 0.05
            cols["content"].append(f"2026-04-25 [main] {'ERROR' if err else 'INFO'} {svc} handled request")
            cols["_time_"].append(datetime.fromtimestamp(float(s), CST).isoformat())
            cols["_container_name_"].append(svc), cols["_pod_name_"].append(f"{svc}-658c476d-8cbsl")
            cols["_namespace_"].append("cms-demo")
    return pa.table(cols)


def _rca100_traces(alert: int, end_off: int, seed: int) -> pa.Table:
    rng = np.random.default_rng(seed)
    cols = {k: [] for k in ("traceId", "spanId", "parentSpanId", "kind", "spanName", "startTime", "endTime", "duration",
                            "serviceName", "statusCode")}
    for k, s in enumerate(np.arange(alert - 1200, alert + end_off, 5.0)):
        tid = f"{seed:04x}{k:012x}"
        st = int(s * 1e9)
        for j, (svc, parent) in enumerate((("frontend", ""), ("checkout", f"{tid}-0"), ("payment", f"{tid}-1"))):
            d = int(2e6 + rng.integers(0, 10**6))
            cols["traceId"].append(tid), cols["spanId"].append(f"{tid}-{j}"), cols["parentSpanId"].append(parent)
            cols["kind"].append("2"), cols["spanName"].append(f"{svc}/op"), cols["startTime"].append(str(st + j * 1000))
            cols["endTime"].append(str(st + j * 1000 + d)), cols["duration"].append(str(d)), cols["serviceName"].append(svc)
            cols["statusCode"].append("2" if rng.random() < 0.05 else "1")
    return pa.table(cols)


def rca100_tree(data_home: Path, cases: dict | None = None) -> Path:
    cases = cases if cases is not None else RCA100_CASES
    root = data_home / "raw" / "agenticopseval-test" / "RCA100"
    ak = root / "answer_key"
    ak.mkdir(parents=True, exist_ok=True)
    mapping = {t: c[0] for t, c in cases.items()}
    (ak / "mapping.json").write_text(json.dumps({"version": "1", "seed": 0, "task_to_case_id": mapping,
                                                 "case_id_to_task": {v: k for k, v in mapping.items()}}), encoding="utf-8")
    for k, (t, (case_id, roots, alert_iso, trig, end_off)) in enumerate(sorted(cases.items())):
        alert = _utc(alert_iso)
        c = root / "cases" / t
        c.mkdir(parents=True, exist_ok=True)
        win = {"start": datetime.fromtimestamp(alert - 120, UTC).isoformat(), "end": datetime.fromtimestamp(alert + 480, UTC).isoformat()}
        (ak / f"{t}.gt.json").write_text(json.dumps({
            "incident_id": case_id, "case_id": case_id, "time_range_start": win["start"], "time_range_end": win["end"],
            "root_cause_entities": roots, "alert_trigger_time": trig}), encoding="utf-8")
        (c / "task.json").write_text(json.dumps({
            "task_id": t, "alert_title": f"{RCA100_SERVICES[k % 5]} 错误次数告警", "alert_trigger_time": trig,
            "alert_window": win, "alert_entity": {"entity_id": "x", "entity_name": f"{RCA100_SERVICES[k % 5]}::/api/op"},
            "prompt_text": f'<alert_event alert_time="{datetime.fromtimestamp(alert, CST).isoformat()}" /> 帮我分析下根因。'},
            ensure_ascii=False), encoding="utf-8")
        _write(c / "alerts.parquet", pa.table({
            "status": ["RESOLVED", "OCCURRED", "OCCURRED"], "time_s": pa.array([alert - 5000, alert + 60, alert], pa.int64()),
            "time": [datetime.fromtimestamp(x, CST).strftime("%Y-%m-%dT%H:%M:%S%z") for x in (alert - 5000, alert + 60, alert)],
            "subtype": ["NORMAL_TRIGGER"] * 3}))
        # one injection's k8s events: tasks cut from the same injection share this export byte for byte
        _write(c / "events.parquet", pa.table({"eventId": ["{}"], "level": ["Warning"], "pod_name": ["prometheus-56879cc97f-9b5pf"],
                                               "time_s": pa.array([alert - 30], pa.int64())}))
        ents = [{"id": s, "type": "apm.service", "name": s} for s in RCA100_SERVICES]
        ents += [{"id": n, "type": "k8s.node", "name": n} for n in RCA100_NODES]
        ents += [{"id": "chaos", "type": "k8s.deployment", "name": "chaosblade-operator"}]
        (c / "topology.json").write_text(json.dumps({"case_id": t, "window": win, "entities": ents, "edges": []}), encoding="utf-8")
        _write(c / "metrics.parquet", _rca100_metrics(alert, LABEL_FOLLOWING.get(t), 10 + k))
        _write(c / "logs.parquet", _rca100_logs(alert, end_off, 20 + k))
        _write(c / "traces.parquet", _rca100_traces(alert, end_off, 30 + k))
    return root
