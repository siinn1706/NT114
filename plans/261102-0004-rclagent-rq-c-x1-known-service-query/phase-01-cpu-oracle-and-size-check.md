---
phase: 1
title: "Đo tính oracle của tool metric và kích thước gộp"
status: planned
priority: P1
effort: "2h"
dependencies: []
---

# Phase 1: Đo tính oracle của tool metric và kích thước gộp

## Context
- `K/metric-repair.py`: hàm `search_fluctuating_metrics(metric_df, service_node_map, service_name, timestamp)` (dòng 19), K = 100.
- Dữ liệu: `K/s1-v2/{a,b}/rclagent-kaggle-bundle.zip`, mỗi trace có `input/metric/all/metrics.csv` và `input/trace/all/trace_jaeger-span.csv`. Đây là case train, không phải test split.
- Danh sách 12 dịch vụ đã biết: upstream `config.py:71-76` (trong bundle, dưới `upstream/`).

## Requirements
- Chỉ CPU, chỉ đọc. Không ghi vào bundle hay `runtime/analysis-*` cũ.
- Gọi đúng hàm của `metric-repair.py` (import, không chép lại logic), với `service_node_map` giống harness.
- Báo theo case: với mỗi timestamp span của trace và mỗi dịch vụ đã biết, tool trả `NO_ROWS`, `NO_KPI` hay bảng; bảng thuộc GT hay không.
- Đo kích thước (token theo tokenizer của model nếu có sẵn trong `runtime/`, nếu không thì ký tự, ghi rõ đơn vị) của chuỗi gộp mà `x1_query` sẽ trả ở mỗi span, so với ngữ cảnh 16384 và 32768.

## Files
- Create: `K/check-x1-metric-oracle.py` (script CPU nhỏ, có `--help`; không cần test riêng vì chỉ là đo một lần, kết quả ghi số).
- Create (gitignored): `K/runtime/analysis-x1-oracle/` gồm `oracle.csv` (case, span timestamp, service, kết quả, is_gt, kích thước) và `summary.json`.
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/reports/analysis-261102-rclagent-x1-metric-oracle-check.md`.

## Steps
1. Đọc tên dịch vụ đã biết từ `upstream/config.py` trong bundle; ghi hash bundle đã đọc.
2. Với 8 trace S1, lấy tập timestamp của span (cùng cách harness dựng timestamp cho model; nếu model gõ timestamp khác, dùng timestamp của span làm chuẩn và ghi rõ).
3. Gọi `search_fluctuating_metrics` cho mọi cặp (timestamp, dịch vụ); ghi loại kết quả và kích thước.
4. Tổng hợp: số bảng trả cho dịch vụ GT so với dịch vụ không phải GT theo case; kích thước gộp lớn nhất mỗi span; cảnh báo nếu chuỗi `frontend` khớp `frontend-external`.
5. Viết báo cáo ngắn: tool có đúng là oracle GT không, và trần gộp cần cho phase 3.

## Checks
- Script thoát 0; số dòng `oracle.csv` bằng (số timestamp) × 12 theo case, in ra và ghi vào báo cáo.
- Kiểm chéo một điểm với S1 v2: với một span `metric` mà run S1 v2 đã hỏi GT, kết quả script trùng `response` trong `events.jsonl` của run đó.

## Risk / Rollback
- Nếu dịch vụ không phải GT cũng nhận bảng ở nhiều span, `x1_query` không còn là "đưa thẳng GT", và báo cáo phải ghi lại; thiết kế phase 2 không đổi nhưng câu giới hạn đổi.
- Nếu kích thước gộp vượt ngữ cảnh, phase 3 đặt trần (cắt theo dịch vụ, ghi sự kiện) và prereg ghi trần đó.
- Rollback: xóa `K/runtime/analysis-x1-oracle/`, script và báo cáo.
