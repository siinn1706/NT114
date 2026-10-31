---
phase: 2
title: "Chạy analyzer S1 v2"
status: completed
priority: P1
effort: "0.5h"
dependencies: [1]
---

# Phase 2: Chạy analyzer S1 v2

## Goal
Có số liệu chính thức của S1 v2 bằng đúng analyzer đã dùng cho vòng 2.

## Files to Create / Modify
- Create: `runtime/analysis-missing-source-a-s1-v2/`
- Create: `runtime/analysis-missing-source-b-s1-v2/`
- Create: `runtime/analysis-missing-source-ab-s1-v2/`
- Create: `runtime/analysis-missing-source-completion-s1-v2/`

## Tasks & Steps
Đặt `PY=runtime/harness-env/Scripts/python.exe -X utf8`, `ZA=runtime/kaggle-output-a-s1-v2/rclagent-smoke/rclagent-smoke-results.zip`, `MA=s1-v2/a/manifest.json`, tương tự `ZB`, `MB`.

1. `$PY analyze-missing-source-results.py runtime/analysis-missing-source-a-s1-v2 $ZA $MA`
2. `$PY analyze-missing-source-results.py runtime/analysis-missing-source-b-s1-v2 $ZB $MB`
3. `$PY analyze-missing-source-results.py runtime/analysis-missing-source-ab-s1-v2 $ZA $MA $ZB $MB`
4. `$PY analyze-completion-and-budget-stops.py runtime/analysis-missing-source-completion-s1-v2 A $ZA $MA B $ZB $MB`
5. Đối chiếu số thô ở review: A 36/36, B 34/36 với hai lỗi không do trần. Nếu analyzer báo khác thì dừng và ghi lại.

## Verification
- Không lệnh nào báo `Duplicate runs`, lỗi SHA256 hay lỗi bundle.
- `summary.json` không có `integrity_problems`, không có lượt pass mà thiếu điểm, cờ provisional là false.
- `budget-stops.json` của S1 rỗng, vì không lượt nào dừng vì trần.
