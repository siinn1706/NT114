---
phase: 3
title: "Kiểm điều kiện với vòng 2"
status: completed
priority: P1
effort: "1.5h"
dependencies: [2]
---

# Phase 3: Kiểm điều kiện với vòng 2

## Goal
Xác định, bằng một script tái chạy được, các lượt không chạm trần ở vòng 2 có đầu ra model giống S1 hay không.

## Files to Create / Modify
- Create: `compare-run-outputs.py`
- Create: `test-compare-run-outputs.py`
- Create: `runtime/analysis-missing-source-r2-vs-s1-v2/`

## Tasks & Steps
1. Tìm cách so đã dùng ở mục 5 của [phân tích vòng 2](../reports/analysis-261029-1629-rclagent-round-2-budget-stops.md) (vòng 1 so vòng 2: bỏ id ngẫu nhiên, so content và tool call). Repo chưa có script cho việc này; nếu tìm thấy mã ad-hoc trong `runtime/` thì dùng lại logic đó.
2. Viết `compare-run-outputs.py OUT LABEL1 ZIP1 MANIFEST1 LABEL2 ZIP2 MANIFEST2`:
   - nạp hai bên qua `load()` của analyzer để giữ các kiểm SHA256 và bundle;
   - ghép lượt theo `(trace_id, condition, seed)`;
   - với mỗi cặp: trạng thái hai bên, có chạm trần ở bên 1 không (dùng `cause()` của `analyze-completion-and-budget-stops.py`), R@1/MRR/top-1 hai bên, và mức trùng đầu ra model (trùng hoàn toàn, chỉ khác response cuối, khác sớm hơn kèm vị trí request đầu tiên khác);
   - ghi `pairs.csv` và `summary.json`.
3. Viết test CPU bằng ZIP tổng hợp nhỏ, theo kiểu của `test-analyze-completion-and-budget-stops.py`: trùng hoàn toàn, khác id ngẫu nhiên vẫn tính trùng, khác response cuối, khác sớm, lượt thiếu một bên.
4. Chạy cho vòng 2 (ZIP và manifest r2 của A và B, xem `results-261029-1448`) so với S1 v2, từng gói.
5. Ghi riêng: 64 lượt không chạm trần (kể cả 2 lượt B hỏng giao thức ở cả hai vòng) và 8 lượt từng chạm trần.

## Verification
- `$PY test-compare-run-outputs.py` pass.
- Chạy lại toàn bộ test hiện có theo lệnh trong handoff 261030-1156; mong đợi 44, 14, 11, 4, 6, 16, 4 pass.
- File `.py` mới dùng LF (`git ls-files --eol` hoặc `file`).
