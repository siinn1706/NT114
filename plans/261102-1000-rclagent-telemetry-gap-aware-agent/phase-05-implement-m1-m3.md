---
phase: 5
title: "Cài M1, M2, M3 trong harness"
status: completed
priority: P1
effort: "14h"
dependencies: [3]
---

# Phase 5: Cài M1, M2, M3 trong harness

## Context
- Đặc tả và prereg đã đóng băng ở phase 3.
- Hook: `adapt_payload` (`K/smoke-worker.py:108`), `get_tool` (`K/smoke-worker.py:338`), ngân sách tool (`K/tool-result-budget.py`), các điều kiện (`K/kaggle-runtime.py`, `K/add-condition-runs.py`).
- Bộ test hiện có: `K/test-kaggle-harness.py`, `K/test-missing-source-conditions.py`, `K/test-tool-result-budget.py`.

## Requirements
- Ba cờ độc lập `--gap-aware`, `--trace-kpi` và `--trace-expand`, mặc định tắt.
- Khi cả ba tắt, payload giống từng byte với S1 v3 trên payload mẫu.
- M2 và M3 chỉ dùng dữ liệu tới thời điểm truy vấn và mốc train, không dùng nhãn. Test phải chứng minh điều này.
- Kết quả M3 có trần kích thước, và được ghi dưới loại sự kiện riêng trong `events.jsonl` để analyzer phân biệt.
- Không sửa `upstream/`.

## Files
- Modify: `K/smoke-worker.py`, `K/kaggle-runtime.py`, `K/add-condition-runs.py`.
- Create: `K/telemetry-gap.py` (M1–M3), `K/test-telemetry-gap.py`.

## Steps
1. Viết test trước: tắt cờ thì giống từng byte; có test riêng cho từng thành phần; có test chặn rò nhãn và nhìn trước.
2. Cài từng thành phần.
3. Chạy toàn bộ test cũ và mới.
4. Cho code reviewer soi diff.

## Checks
- Mọi bộ test thoát 0.
- Hash của prereg vẫn khớp.

## Risk / Rollback
- M3 làm vượt ngữ cảnh: giảm trần, ghi deviation, không đổi giả thuyết.
- Rollback: `git restore` các file đã sửa, xóa file mới.
