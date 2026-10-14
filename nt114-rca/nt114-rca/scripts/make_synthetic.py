"""Sinh dữ liệu GIẢ theo đúng định dạng RCAEval (layout Zenodo) để test pipeline khi chưa tải dữ liệu thật.
Không dùng số liệu này cho bài báo.

  python scripts/make_synthetic.py data_synth --per-fault 2
  python scripts/make_synthetic.py data_synth_home/raw/synthetic --anchor-gap 12000  # cửa sổ các ca không chồng nhau (chia tập theo nhóm)
"""
import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd

SYSTEMS = {
    "OB": {"graph": {"frontend": ["cartservice", "productcatalogservice", "currencyservice", "recommendationservice",
                                  "checkoutservice", "adservice"],
                     "checkoutservice": ["cartservice", "currencyservice", "paymentservice", "shippingservice",
                                         "emailservice"],
                     "recommendationservice": ["productcatalogservice"]}, "traces": True},
    "SS": {"graph": {"front-end": ["carts", "orders", "catalogue", "user"], "orders": ["payment", "shipping", "carts"]},
           "traces": False},
    "TT": {"graph": {"ts-ui-dashboard": ["ts-travel-service", "ts-order-service", "ts-auth-service"],
                     "ts-travel-service": ["ts-route-service", "ts-station-service"],
                     "ts-order-service": ["ts-station-service"]}, "traces": True},
}
FAULTS = ["cpu", "mem", "delay", "loss"]
T0 = 1_705_000_000


def services(graph):
    s = set(graph)
    for v in graph.values():
        s |= set(v)
    return sorted(s)


def make_case(out: Path, sysname: str, spec: dict, root: str, fault: str, inst: int, rng: random.Random):
    graph, svcs = spec["graph"], services(spec["graph"])
    t_inj = T0 + rng.randint(0, 10_000)
    times = np.arange(t_inj - 600, t_inj + 300)
    after = times >= t_inj
    nr = np.random.default_rng(rng.randint(0, 1 << 30))

    # metrics: cpu, mem, latency-90, latency-50 cho mọi dịch vụ
    m = {"time": times}
    for s in svcs:
        cpu = nr.normal(20, 2, len(times))
        mem = nr.normal(300, 5, len(times))
        lat = nr.normal(0.05, 0.005, len(times))
        if s == root:
            if fault == "cpu": cpu[after] += 60
            if fault == "mem": mem[after] += 400
            if fault in ("delay", "loss"): lat[after] += 0.3
        callees = graph.get(s, [])
        if root in callees and fault in ("delay", "loss", "cpu"):
            lat[after] += 0.2  # triệu chứng lan lên người gọi
        m[f"{s}_cpu"], m[f"{s}_mem"], m[f"{s}_latency-90"], m[f"{s}_latency-50"] = cpu, mem, lat, lat * 0.6
    d = out / f"RE2-{sysname}" / f"{root}_{fault}" / str(inst)
    d.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(m).to_csv(d / "metrics.csv", index=False)
    (d / "inject_time.txt").write_text(str(t_inj))

    # logs
    rows = []
    for t in times[::2]:
        for s in rng.sample(svcs, 3):
            err = (s == root and t >= t_inj and rng.random() < 0.6) or rng.random() < 0.02
            msg = (f"request failed: rpc error code = Unavailable after {rng.randint(100, 900)}ms" if err
                   else f"request handled in {rng.randint(1, 50)}ms id={rng.getrandbits(48):x}")
            rows.append({"time": "00:00", "timestamp": int(t * 1e9) + rng.randint(0, 999_999),
                         "container_name": s, "message": msg, "level": "error" if err else "info"})
    pd.DataFrame(rows).to_csv(d / "logs.csv", index=False)

    # traces (Sock Shop không có trace, đúng như RCAEval)
    if spec["traces"]:
        entry = [s for s in graph if all(s not in v for v in graph.values())][0]
        spans = []

        def span(svc, parent, start_us, trace, t):
            sid = f"{rng.getrandbits(64):016x}"
            dur = rng.randint(500, 3000)
            child_t = start_us + 100
            for c in graph.get(svc, []):
                if rng.random() < 0.7:
                    cd = span(c, sid, child_t, trace, t)
                    dur += cd
                    child_t += cd
            if svc == root and t >= t_inj and fault in ("delay", "loss", "cpu"):
                dur += rng.randint(100_000, 300_000)
            code = 2 if (svc == root and t >= t_inj and fault == "loss" and rng.random() < 0.4) else 0
            spans.append({"time": "00:00", "traceID": trace, "spanID": sid, "serviceName": svc,
                          "methodName": "Call", "operationName": f"{svc}/Call", "startTime": start_us,
                          "duration": dur, "statusCode": code, "parentSpanID": parent})
            return dur

        for t in times[::3]:
            span(entry, None, int(t * 1e6), f"{rng.getrandbits(128):032x}", t)
        pd.DataFrame(spans).to_csv(d / "traces.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--per-fault", type=int, default=2)
    ap.add_argument("--anchor-gap", type=int, default=0, help="giây giữa hai ca liên tiếp, cộng độ lệch ngẫu nhiên 0..10000 s (0 = như cũ)")
    a = ap.parse_args()
    rng = random.Random(0)
    out = Path(a.out) / "RE2"
    base, k = T0, 0
    for sysname, spec in SYSTEMS.items():
        svcs = services(spec["graph"])
        for fault in FAULTS:
            for root in rng.sample(svcs, 3):
                for inst in range(1, a.per_fault + 1):
                    if a.anchor_gap:
                        T0, k = base + k * a.anchor_gap, k + 1   # make_case đọc T0 lúc gọi
                    make_case(out, sysname, spec, root, fault, inst, rng)
    print("done:", sum(1 for _ in out.rglob("inject_time.txt")), "cases")
