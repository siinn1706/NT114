"""Đọc ca lỗi RCAEval (RE1/RE2/RE3) và chuẩn hóa tên dịch vụ.

Hỗ trợ hai cách sắp xếp thư mục mà RCAEval phát hành:
  - Zenodo:        data/RE2/RE2-OB/checkoutservice_cpu/1/{metrics.csv|json, logs.csv, traces.csv, inject_time.txt}
  - Hugging Face:  data/re2ob_checkoutservice_cpu_1/{metrics.parquet, logs.parquet, traces.parquet, inject_time.txt}

Định dạng (kiểm tra từ mã nguồn và notebook demo của RCAEval):
  metrics : cột `time` (unix giây) + cột `{dịch vụ}_{chỉ số}` (cpu, mem, diskio, latency-50, latency-90, ...)
  logs    : time, timestamp (ns), container_name, message, level, ...
  traces  : traceID, spanID, parentSpanID, serviceName, methodName, operationName,
            startTime (µs), duration (µs), statusCode
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

SYSTEM_CODES = {"ob": "online-boutique", "ss": "sock-shop", "tt": "train-ticket"}
_FILES = {
    "metrics": ["metrics.parquet", "metrics.json", "simple_metrics.csv", "metrics.csv", "data.csv"],
    "logs": ["logs.parquet", "logs.csv"],
    "traces": ["traces.parquet", "traces.csv"],
}


@dataclass
class VisibleCase:
    """Phần mô hình được thấy: KHÔNG có nhãn (root_service, fault). Mọi hàm đưa dữ liệu vào
    bằng chứng, prompt, truy hồi hay Jev chỉ nhận kiểu này."""
    case_id: str
    dataset: str
    system: str
    inject_time: int      # unix giây (dùng để đặt cửa sổ bằng chứng, không đưa vào văn bản)
    path: Path | None = None
    services: list[str] = field(default_factory=list)


@dataclass
class Truth:
    """Nhãn đúng; chỉ dùng cho chấm điểm, chọn mục tiêu ablation và mặt nạ kho oracle.
    `root_service` = None khi nhãn chỉ là một tập dịch vụ (`root_ids`, chấm theo tập)."""
    root_service: str | None
    fault: str
    root_ids: tuple[str, ...] = ()
    granularity: str = "service"


@dataclass
class Case:
    case_id: str          # vd: re2-ob_checkoutservice_cpu_1
    dataset: str          # re1 | re2 | re3
    system: str           # online-boutique | sock-shop | train-ticket
    root_service: str     # nhãn đúng: dịch vụ gây lỗi
    fault: str            # cpu | mem | disk | delay | loss | socket | f1..f5
    inject_time: int      # unix giây
    path: Path
    services: list[str] = field(default_factory=list)  # danh sách ứng viên, điền khi load

    def visible(self) -> VisibleCase:
        return VisibleCase(self.case_id, self.dataset, self.system, self.inject_time, self.path, self.services)

    def truth(self) -> Truth:
        return Truth(self.root_service, self.fault)


# ---------------------------------------------------------------- tìm ca
def _parse_service_fault(token: str) -> tuple[str, str, str | None]:
    """'checkoutservice_cpu' -> ('checkoutservice', 'cpu', None);
    'ts-route-service_f3_1' -> ('ts-route-service', 'f3', '1') (đợt tiêm thứ 2 của cùng ô lỗi).
    Tên không khớp bộ từ vựng lỗi thì tách theo dấu _ cuối như trước."""
    from .adapters.rcaeval import parse_cell
    parsed = parse_cell(token)
    if parsed:
        return parsed
    svc, _, fault = token.rpartition("_")
    return svc, fault, None


def discover_cases(root: str | Path, datasets=("re2", "re3")) -> list[Case]:
    """Quét mọi thư mục có inject_time.txt bên dưới `root`."""
    root = Path(root)
    cases: list[Case] = []
    for inj in sorted(root.rglob("inject_time.txt")):
        d = inj.parent
        rel = str(d.relative_to(root)).lower().replace("\\", "/")

        m_flat = re.match(r"^(re[123])(ob|ss|tt)_(.+)_(\d+)$", d.name.lower())
        m_zen = re.search(r"(re[123])-(ob|ss|tt)/([^/]+)/(\d+)$", rel)
        if m_flat:
            ds, sys_code, mid, inst = m_flat.groups()
        elif m_zen:
            ds, sys_code, mid, inst = m_zen.groups()
        else:
            continue
        if ds not in datasets:
            continue
        svc, fault, batch = _parse_service_fault(mid)
        with open(inj, encoding="utf-8") as f:
            t = int(float(f.read().strip().split()[0]))
        cases.append(Case(
            case_id=f"{ds}-{sys_code}_{svc}_{fault}{f'b{batch}' if batch else ''}_{inst}",
            dataset=ds, system=SYSTEM_CODES[sys_code],
            root_service=canon(svc), fault=fault, inject_time=t, path=d,
        ))
    seen: dict[str, Path] = {}
    for c in cases:  # run_grid bỏ qua ca trùng case_id, nên trùng ở đây là mất dữ liệu âm thầm
        if c.case_id in seen:
            raise ValueError(f"case_id trùng {c.case_id!r}: {seen[c.case_id]} và {c.path}")
        seen[c.case_id] = c.path
    return cases


# ---------------------------------------------------------------- đọc file
def _find(case_dir: Path, kind: str) -> Path | None:
    for name in _FILES[kind]:
        p = case_dir / name
        if p.exists():
            return p
    return None


def _read_metrics(p: Path) -> pd.DataFrame:
    if p.suffix == ".parquet":
        return pd.read_parquet(p)
    if p.suffix == ".json":  # {metric: [[ts, val], ...]} như RCAEval.read_metrics
        raw = {k: v for k, v in json.load(open(p)).items() if v}
        times = sorted({ts for v in raw.values() for ts, _ in v})
        pos = {t: i for i, t in enumerate(times)}
        arr = np.full((len(times), len(raw)), np.nan)
        for j, vals in enumerate(raw.values()):
            for ts, val in vals:
                if val is not None:
                    arr[pos[ts], j] = val
        df = pd.DataFrame(arr, columns=list(raw))
        df.insert(0, "time", np.asarray(times, dtype=np.int64))
        return df
    df = pd.read_csv(p)
    return df.drop(columns=[c for c in df.columns if c.startswith("time.")])


def _read_table(p: Path | None) -> pd.DataFrame | None:
    if p is None:
        return None
    df = pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(p, low_memory=False)
    return None if df.empty else df


# ---------------------------------------------------------------- tên dịch vụ
def canon(name: str) -> str:
    """Chuẩn hóa tên: 'frontendservice' / 'frontend' / 'ts-auth-service' -> khóa so khớp."""
    s = re.sub(r"[^a-z0-9]", "", str(name).lower())
    s = re.sub(r"^ts", "", s) if s.startswith("ts") and len(s) > 4 else s
    return re.sub(r"service$", "", s) or s


def metric_services(metrics: pd.DataFrame) -> list[str]:
    svcs = {canon(c.rsplit("_", 1)[0]) for c in metrics.columns if c != "time" and "_" in c}
    return sorted(s for s in svcs if s)


def load_case(case: Case) -> dict:
    """Trả về {'metrics', 'logs', 'traces'} (DataFrame hoặc None) và điền case.services."""
    mp = _find(case.path, "metrics")
    metrics = _read_metrics(mp) if mp else None
    logs = _read_table(_find(case.path, "logs"))
    traces = _read_table(_find(case.path, "traces"))

    if logs is not None and "container_name" in logs:
        logs["svc"] = logs["container_name"].map(canon)
    if traces is not None:
        traces["svc"] = traces["serviceName"].map(canon)
        for col in ("startTime", "duration"):
            traces[col] = pd.to_numeric(traces[col], errors="coerce")

    svcs = set(metric_services(metrics)) if metrics is not None else set()
    if traces is not None:
        svcs |= set(traces["svc"].dropna().unique())
    if logs is not None and "svc" in logs:
        svcs |= set(logs["svc"].dropna().unique())
    case.services = sorted(s for s in svcs if s)
    return {"metrics": metrics, "logs": logs, "traces": traces}
