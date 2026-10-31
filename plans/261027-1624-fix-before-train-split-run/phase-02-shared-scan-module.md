---
phase: 2
title: "Gom phần chung của hai script scan"
status: completed
priority: P3
effort: "0.5d"
dependencies: []
---

# Phase 2: Gom phần chung của hai script scan

## Goal
Bỏ khoảng 120 dòng chép giống nhau giữa hai script scan (finding U4), để bản sửa ở một chỗ không bị lệch khỏi chỗ kia.

## Files to Create / Modify
- Create: `plans/261026-1713-rclagent-tai-hien-toi-thieu/work/scripts/re2ob-endpoint-common.py`. File này chứa phần sở hữu trace và ca, cắt dữ liệu, exec endpoint tác giả, `serve()` và `own_round`. Script dùng nó qua importlib, giống `tool-result-budget.py`.
- Modify: `.../work/scripts/re2ob-tool-response-scan.py`, `.../work/scripts/re2ob-tool-result-budget-impact.py`

## Tasks & Steps
1. Diff hai script, liệt kê đúng các đoạn trùng (scan dòng khoảng 82/111/172, impact dòng khoảng 81/109/177).
2. Chuyển các đoạn trùng sang module chung, không đổi logic.
3. Chạy lại hai script vào thư mục output mới và so với output đã commit.

## Verification
- `tool-response-scan.csv/json` và `tool-result-budget-impact.json`/`trace-impact.csv` mới trùng byte với bản đã commit. So bằng `cmp`, ghi log vào `work/logs/`.
- Kiểm nhanh 2 trace (giống check-03) trước khi chạy đầy đủ, vì lượt đầy đủ mất khoảng 37 phút.

## Risk / Rollback
Thấp: chỉ là script phân tích, không thuộc gói Kaggle. Nếu output lệch byte thì rollback và tìm nguyên nhân trước khi sửa tiếp.
