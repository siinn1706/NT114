---
phase: 5
title: "Kiểm output và phân tích"
status: planned
priority: P1
effort: "5h"
dependencies: [4]
---

# Phase 5: Kiểm output và phân tích

## Context
- Chỉ bắt đầu khi sếp báo hai kernel chạy xong; tải output về `K/runtime/kaggle-output-{a,b}-x1/`.
- Mốc so: `K/runtime/kaggle-output-{a,b}-s1-v3/` và `K/runtime/analysis-evidence-loss-s1-v3/runs.csv`.
- Kết quả phase 3 bước 5 cho biết analyzer đóng băng có nhận tên điều kiện mới không.

## Requirements
- Kiểm hash zip khớp `.sha256`, `bundle_sha256` trong `run-once.json` khớp bundle đã đẩy, hash prereg còn khớp.
- Analyzer đóng băng chạy vào thư mục mới `K/runtime/analysis-evidence-loss-x1/` nếu nhận tên điều kiện mới; hash biên nhận RQ (b) phải còn khớp.
- Script so sánh mới tính C1 đến C5 đúng định nghĩa prereg, đọc `author-score.txt`, `events.jsonl` (gồm `x1_injection`), `worker-status.json` và `runs.csv` của S1 v3; có test với dữ liệu tổng hợp và một test so với số tính tay trên một run thật.
- Không sửa luật sau khi thấy output; mọi thay đổi ghi `deviation-log.md`.

## Files
- Create: `K/compare-x1-runs.py`, `K/test-compare-x1-runs.py`.
- Create (gitignored): `K/runtime/analysis-evidence-loss-x1/`, `K/runtime/analysis-x1-outcomes/` (`outcomes.csv`, `pairs.csv`, `summary.json`).
- Create khi cần: `F:/Nam/UIT/NT114 - NCKH/plans/261102-0004-rclagent-rq-c-x1-known-service-query/deviation-log.md`.

## Steps
1. Tải output, kiểm hash và biên nhận.
2. Kiểm thứ tự hint theo seed 0 bằng `check-hash-seed-order.py` (S1 v3 làm bên cũ chỉ để kiểm thứ tự, không ghép đầu ra).
3. Chạy analyzer đóng băng nếu áp dụng được.
4. Viết và test `compare-x1-runs.py`, rồi chạy để có C1 đến C5.
5. Đếm sự kiện `x1_injection` theo run: số lần gộp, dịch vụ có bảng, có cắt hay không.

## Checks
- Mọi test thoát 0; ghi lệnh và mã thoát.
- Số run trong output: A 18, B 15, hoặc danh sách run thiếu và lớp dừng.
- C1 đến C5 có cột nguồn trong `outcomes.csv`.

## Risk / Rollback
- Run bị cắt hoặc hỏng: báo theo lớp `H_*`, không thay bằng chạy lại trừ khi sếp quyết.
- Analyzer không nhận tên mới: chỉ dùng script mới, ghi giới hạn là nhãn S1 đến S4 không có cho X1.
- Rollback: xóa các thư mục `runtime/analysis-*x1*`; output tải về giữ nguyên.
