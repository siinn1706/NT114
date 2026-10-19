"""Kiểu dữ liệu dùng chung (VisibleCase, Truth, Case) và chuẩn hóa tên dịch vụ.

Telemetry được đọc từ kho chuẩn hóa (`rca.store`, `rca.legacy_view`); các adapter trong `rca.adapters`
đọc bản phát hành gốc. Module này không đọc thư mục RCAEval trực tiếp.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class VisibleCase:
    """Phần mô hình được thấy: KHÔNG có nhãn (root_service, fault). Mọi hàm đưa dữ liệu vào
    bằng chứng, prompt hay truy hồi chỉ nhận kiểu này."""
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
    services: list[str] = field(default_factory=list)  # danh sách ứng viên

    def visible(self) -> VisibleCase:
        return VisibleCase(self.case_id, self.dataset, self.system, self.inject_time, self.path, self.services)

    def truth(self) -> Truth:
        return Truth(self.root_service, self.fault)


def canon(name: str) -> str:
    """Chuẩn hóa tên: 'frontendservice' / 'frontend' / 'ts-auth-service' -> khóa so khớp."""
    s = re.sub(r"[^a-z0-9]", "", str(name).lower())
    s = re.sub(r"^ts", "", s) if s.startswith("ts") and len(s) > 4 else s
    return re.sub(r"service$", "", s) or s
