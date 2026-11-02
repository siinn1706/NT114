---
phase: 3
title: "Cờ --x1 trong harness và test"
status: planned
priority: P1
effort: "5h"
dependencies: [2]
---

# Phase 3: Cờ `--x1` trong harness và test

## Context
- `K/smoke-worker.py`: `adapt_payload` (108), `Guard` (130), `Guard.post` gọi `adapt_payload` (187) và `validate_calls` (237), `install_guards` (275), `get_tool` (338-357), argparse (450-470).
- `K/kaggle-runtime.py`: `worker_options` (494-500) chuyển cờ từ mục `runs` của manifest sang worker.
- `K/add-condition-runs.py`: `CONDITIONS` (16-19), `condition_runs` (21-23).
- Test hiện có: `K/test-kaggle-harness.py`, `K/test-missing-source-conditions.py`.
- Prereg phase 2 là nguồn duy nhất cho câu chữ gợi ý và luật gộp.

## Requirements
- Không sửa `upstream/`, analyzer hay codebook.
- `--x1 off` là mặc định; với `off`, payload và kết quả tool giống từng byte với harness hiện tại.
- `prompt`: trong `adapt_payload`, chỉ với request có tool `search_fluctuating_metrics`, chèn câu chữ nguyên văn của prereg vào đúng vị trí đã định. Không đổi các request khác (consolidation, tổng hợp cuối).
- `query`: trong `get_tool`, khi model gọi `search_fluctuating_metrics(service, ts)` ở pha trace và nguồn metric là `repaired`, harness gọi thêm `guard.source_response` cho mọi dịch vụ đã biết khác tại cùng `ts`, gộp kết quả có bảng theo luật prereg, áp trần kích thước. Sự kiện `tool_result` của lệnh model giữ nguyên `response` gốc; phần gộp ghi ở sự kiện riêng `x1_injection` (dịch vụ đã hỏi, loại kết quả từng dịch vụ, chuỗi giao cho model, có cắt hay không).
- Truy vấn tự sinh không đi qua `validate_query` theo kiểu làm dừng run vì tên dịch vụ; vẫn kiểm timestamp nằm trong cửa sổ đã đóng gói.
- `worker_options` truyền `x1` khi mục run có khóa này; `add-condition-runs.py` nhận tập điều kiện qua tham số (giữ mặc định `CONDITIONS` cũ để S1 dựng lại được như cũ).

## Files
- Modify: `K/smoke-worker.py`, `K/kaggle-runtime.py`, `K/add-condition-runs.py`.
- Modify: `K/test-kaggle-harness.py` (hoặc tạo `K/test-x1-harness.py` nếu tách riêng giảm độ phức tạp).
- Modify: `K/README.md` (một mục ngắn về `--x1`).

## Steps
1. Thêm hằng câu chữ gợi ý (đọc từ prereg khi viết, so hash trong test) và danh sách dịch vụ đã biết (đọc từ `upstream/config.py` trong gói lúc chạy, không chép tay).
2. Cài `prompt` trong `adapt_payload` (thêm tham số `x1`), truyền qua `Guard`.
3. Cài `query` trong `get_tool` và sự kiện `x1_injection`.
4. Thêm `--x1` vào argparse và `worker_options`; thêm tham số tập điều kiện cho `add-condition-runs.py`.
5. Test:
   - `off`: payload mẫu của S1 v3 qua `adapt_payload` giống từng byte trước và sau thay đổi; `get_tool` không phát `x1_injection`.
   - `prompt`: chỉ request self-state đổi; câu chữ trùng prereg; request consolidation không đổi.
   - `query`: với `metric_df` tổng hợp có bảng cho một dịch vụ, kết quả gộp đúng thứ tự, bỏ `NO_ROWS`/`NO_KPI`, áp trần; `tool_result` giữ `response` gốc.
   - `worker_options` và `condition_runs` sinh đúng `run_id` `{trace}--metric_x1p--s{seed}`.
   - Analyzer đóng băng chạy trên một zip tổng hợp có tên điều kiện mới: ghi kết quả (chạy hay báo lỗi) để phase 5 chọn đường.
6. Chạy toàn bộ bộ test cũ của `K/` (con số test của handoff RQ (b)); không test nào được làm yếu đi.

## Checks
- Mọi test mới và cũ thoát 0, ghi lệnh và mã thoát từng bộ.
- `git diff` không chạm `upstream/`, `analyze-evidence-loss.py`, codebook.
- Hash `K/evidence-loss-prereg.json` vẫn khớp (analyzer không đổi).

## Risk / Rollback
- `prompt` làm vượt ngữ cảnh: câu chữ ngắn (dưới 100 token); test đo token nếu có tokenizer.
- Sự kiện mới làm analyzer báo `integrity_problems`: phát hiện ở bước 5, xử lý ở phase 5 bằng script so sánh riêng.
- Rollback: `git revert` commit của phase này; gói S1 cũ dựng lại được vì mặc định không đổi.
