"""Tạo các điều kiện thiếu dữ liệu giám sát.

full          : giữ nguyên
no_trace      : bỏ toàn bộ trace
no_log        : bỏ toàn bộ log
no_metric     : bỏ toàn bộ metric
blind_root    : xóa span của CHÍNH dịch vụ gây lỗi (dịch vụ chưa gắn trace — câu chuyện 3 giờ sáng).
                Span của dịch vụ gọi nó vẫn còn, giống ngoài đời: người gọi thấy chậm nhưng không thấy bên trong.
blind_nonroot : đối chứng — xóa span của MỘT dịch vụ không phải gốc (chọn bởi `choose_nonroot_target`).
metrics_only  : bỏ cả log lẫn trace (đường cơ sở chỉ-metric, so cặp trên cùng sự cố).

Toán tử che (`mask_service_traces`) không biết nhãn: nó nhận một tên dịch vụ. Chỉ bộ điều khiển
điều kiện mới truyền dịch vụ gốc (từ `Truth`) hay dịch vụ đối chứng vào.
"""
from __future__ import annotations

import hashlib

CONDITIONS = ("full", "no_trace", "no_log", "no_metric", "blind_root", "blind_nonroot", "metrics_only")


def mask_service_traces(tel: dict, service: str) -> dict:
    """Bỏ mọi span có `svc == service`; các modality khác giữ nguyên đối tượng."""
    out = dict(tel)
    if tel.get("traces") is not None:
        tr = tel["traces"]
        out["traces"] = tr[tr["svc"] != service].copy()
    return out


def choose_nonroot_target(tel: dict, root_service: str, uid: str) -> str | None:
    """Dịch vụ không phải gốc có số span gần với số span của gốc nhất; hòa thì theo sha256(uid + dịch vụ).
    Tất định trên mọi máy (không dùng hash() của Python)."""
    tr = tel.get("traces")
    if tr is None or not len(tr):
        return None
    counts = tr["svc"].dropna().value_counts()
    n_root = int(counts.get(root_service, 0))
    others = [s for s in counts.index if s != root_service]
    if n_root == 0 or not others:
        return None
    return min(others, key=lambda s: (abs(int(counts[s]) - n_root), hashlib.sha256(f"{uid}{s}".encode()).hexdigest()))


def apply(tel: dict, condition: str, root_service: str, nonroot_target: str | None = None) -> dict:
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition {condition!r}")
    out = dict(tel)
    if condition == "no_trace":
        out["traces"] = None
    elif condition == "no_log":
        out["logs"] = None
    elif condition == "no_metric":
        out["metrics"] = None
    elif condition == "metrics_only":
        out["logs"] = out["traces"] = None
    elif condition == "blind_root":
        out = mask_service_traces(tel, root_service)
    elif condition == "blind_nonroot":
        if nonroot_target is None or nonroot_target == root_service:
            raise ValueError("blind_nonroot needs a non-root target")
        out = mask_service_traces(tel, nonroot_target)
    return out


def available(tel: dict) -> dict:
    """Modality nào còn dữ liệu (dùng làm đặc trưng cho lớp quyết định)."""
    return {k: tel.get(k) is not None and len(tel[k]) > 0 for k in ("metrics", "logs", "traces")}


def applicable(condition: str, tel_full: dict, root_service: str | None = None) -> bool:
    """Bỏ ô vô nghĩa: vd Sock Shop không có trace thì no_trace/blind_root trùng với full.
    `blind_*` cần thêm: gốc có ít nhất một span (và với blind_nonroot, còn dịch vụ khác có span)."""
    if condition in ("no_trace", "blind_root", "blind_nonroot"):
        if tel_full.get("traces") is None:
            return False
        if condition == "no_trace" or root_service is None:
            return condition != "blind_nonroot"
        svcs = set(tel_full["traces"]["svc"].dropna())
        if root_service not in svcs:
            return False
        return condition == "blind_root" or bool(svcs - {root_service})
    if condition == "no_log":
        return tel_full.get("logs") is not None
    if condition == "metrics_only":
        return tel_full.get("metrics") is not None and (tel_full.get("logs") is not None or tel_full.get("traces") is not None)
    return True
