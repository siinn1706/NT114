---
phase: 3
title: "Thành phần chung: đồ thị trace, S-first, tool tất định, bộ chọn đường"
status: planned
owner_skills: [nckh-backend, nckh-test]
---

# Giai đoạn 03: Thành phần chung (M2)

## Yêu cầu

- ~~Chỉ bắt đầu khi phase 01 đã được chủ dự án duyệt và có lệnh `nckh-cook` cho kế hoạch này.~~ Điều kiện đã thỏa ngày 2026-10-26 (a02 và quyền phase 03–08).
- `rcl_path.py` hiện thực đúng [đặc tả a02](work/path-selection-spec-a02.md) §2 và các kiểm §5 của nó.
- Module mới (tên đề xuất, chốt khi làm): `src/rca/rcl_trace_graph.py` (dựng đồ thị trace từ vùng visible, chọn trace S-first chỉ định trước, không dùng S-best), `src/rca/rcl_tools.py` (tool metric n-sigma, log, trace tất định, đọc thẳng `store.py`/`legacy_view.py`), `src/rca/rcl_path.py` (quy tắc chọn đường theo đặc tả phase 02).
- Không sửa `evidence.py`, prompt `v1`, splits hay bundle.

## Tệp

- Đọc: `src/rca/store.py`, `legacy_view.py`, `evidence.py` (tham khảo), `ablate.py`, `audit.py`, `tests/test_leakage.py`, `tests/test_leakage_audit.py`.
- Tạo: ba module trên và `tests/test_rcl_trace_graph.py`, `tests/test_rcl_tools.py`, `tests/test_rcl_path.py`.
- Sửa nhỏ, có test: danh sách quét import của kiểm rò rỉ (`audit.py` hoặc test) để bao module mới.

## Các bước

1. Viết test trước cho từng hàm, dùng fixture tổng hợp trong `tests/fixtures`.
2. Viết module; chạy test hẹp, rồi toàn bộ `pytest`.

## Kiểm tra

- Tất định: hai lần chạy cùng đầu vào cho cùng hash đầu ra tool.
- Hoán vị nhãn: đổi nhãn fixture không đổi đầu ra tool, đồ thị hay đường được chọn.
- Canary: chuỗi canary đặt trong cột nhãn không xuất hiện trong bất kỳ đầu ra nào.
- Quét import: module mới không import đường đọc nhãn.
- ~~Với `no_trace`, bộ chọn đường trả `no_trace` và tool trace không được gọi.~~ Sửa 2026-10-26 theo [đặc tả a01](work/path-selection-spec.md): với điều kiện `no_trace`, bộ chọn trả `no_trace` khi arm dùng khung và khóa có khung hợp lệ, ngược lại trả `frame_free`; không bao giờ trả `trace`; tool trace không được gọi.
- `pytest` toàn bộ exit 0. Cổng **S2** khi bất kỳ test rò rỉ nào thất bại; không nới test.

## Rủi ro và hoàn tác

- Đọc parquet thô tốn bộ nhớ: giới hạn theo cửa sổ visible, đo trên fixture.
- Hoàn tác: module mới tách biệt; xóa file mới và hoàn nguyên sửa nhỏ theo diff.
