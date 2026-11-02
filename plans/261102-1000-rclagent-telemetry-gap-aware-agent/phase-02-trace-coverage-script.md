---
phase: 2
title: "Script đo phạm vi trace"
status: completed
priority: P1
effort: "4h"
dependencies: []
---

# Phase 2: Script đo phạm vi trace

Biên nhận: [báo cáo, mục 2](../reports/analysis-261102-rclagent-trace-coverage-and-non-llm-baselines.md) (2026-11-02).
- `test-measure-trace-coverage.py` có 4 test, thoát 0. Lệnh chạy `measure-trace-coverage.py runtime/trace-coverage --roles-allowed train,val` thoát 0.
- SHA256 (CRLF thành LF): script `76912aa2…f2dd`, test `976a7ab0…78dc`, `coverage.csv` `18bc970d…16dd27`.
- Kết quả trên train khớp phép đếm khám phá: 59/240 truy vấn không có span GT; 5 case có mọi truy vấn như vậy, 17 case có ít nhất một.
- Trên val: 25/105 (23,8%); 2/21 case có mọi truy vấn như vậy, 7/21 có ít nhất một.
- Ở mọi truy vấn thuộc nhóm `none`, cửa sổ lỗi có ít nhất 396 trace khác đi qua GT; trung vị là 1 419 trên train và 516 trên val. Vì vậy M3 luôn có bằng chứng để lấy.

## Context
- Phép đếm khám phá ngày 2026-11-02 cho kết quả 59/240 truy vấn train không có span GT. Phép đếm này dùng một script tạm trong scratchpad; script không có test.
- Dữ liệu dùng:
  - Danh sách truy vấn và vai trò: `work/tool-response-scan/tool-response-scan.csv` (cột `role`, `trace_id`, `case_id`).
  - Trace thô: `F:/Nam/UIT/nt114-paper-artifacts/W7165616276/data/re2ob/trace/all/trace_jaeger-span.csv`.

## Requirements
- Script `K/measure-trace-coverage.py` nhận các vai trò được phép, mặc định `train,val`, và từ chối `test`.
- Với mỗi truy vấn, script ghi:
  - Số span server của GT.
  - Số span client gọi tới GT.
  - Số trace khác trong cửa sổ [`inject_ts`, `inject_ts` + 600 s) có đi qua GT.
  - Thời điểm trace được giao bắt đầu, tính so với lúc tiêm lỗi.
- Cách nhận span client phải ghi tường minh: so khớp tên RPC của GT trong `operation_name`, khi `cmdb_id` khác GT. Phải có bảng ánh xạ tên dịch vụ sang tên RPC.
- Output là `coverage.csv` và `summary.json`, có hash input.

## Files
- Create: `K/measure-trace-coverage.py`, `K/test-measure-trace-coverage.py`.
- Create (gitignored): `K/runtime/trace-coverage/`.

## Steps
1. Viết test trên trace tổng hợp: truy vấn có span server, chỉ có span client, và không có span nào của GT.
2. Viết script, chạy trên train và val.
3. So số của train với phép đếm khám phá (59/240); ghi mọi chỗ lệch.

## Checks
- Test thoát 0.
- Train cho đúng 240 truy vấn, 48 case.
- Không có dòng nào có `role = test`.

## Risk / Rollback
- Lệch với phép đếm khám phá: tin script có test, và ghi lý do lệch.
- Rollback: xóa hai file script và thư mục output.
