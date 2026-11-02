---
phase: 6
title: "Báo cáo, bàn giao, commit và PR"
status: planned
priority: P2
effort: "3h"
dependencies: [5]
---

# Phase 6: Báo cáo, bàn giao, commit và PR

## Context
- Output phase 5, prereg và decision record phase 2, báo cáo oracle phase 1.
- Mẫu báo cáo: [kết quả RQ (b)](../reports/analysis-261101-1023-rclagent-evidence-loss-results.md); mẫu bàn giao: [handoff RQ (b)](../reports/handoff-261101-1045-rclagent-evidence-loss.md).

## Requirements
- Báo cáo kết quả tiếng Việt: trả lời câu (c) cho X1 bằng lời thường trong tối đa 8 dòng; bảng C1 đến C5 theo case và seed cạnh S1 v3; mục giới hạn (n = 3 và 5 case, seed gần như nhân bản, `x1_query` là cận trên có bơm bảng GT, tool đã sửa gần như oracle, quỹ đạo tách sớm nên không ghép cặp theo request); mục tái lập (lệnh, hash, đường dẫn).
- Không dùng ngôn ngữ nhân quả tổng quát; chỉ mô tả trên các case này.
- Bàn giao ghi file nào ở GitHub, file nào chỉ có trong `runtime/`.
- Commit theo conventional commit, không nhắc AI hay mã phase; không commit `runtime/`, token Kaggle hay dữ liệu niêm phong.

## Files
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/reports/analysis-261102-rclagent-x1-results.md` (đổi ngày theo ngày viết).
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/reports/handoff-261102-rclagent-x1.md` (đổi ngày theo ngày viết).
- Modify: `F:/Nam/UIT/NT114 - NCKH/plans/261102-0004-rclagent-rq-c-x1-known-service-query/plan.md` (trạng thái từng phase kèm link biên nhận).
- Modify khi cần: `llms.txt`, `K/README.md`.

## Steps
1. Viết báo cáo kết quả từ `outcomes.csv`, không chép số tay.
2. Cho một reviewer ngữ cảnh mới rà báo cáo và diff (nckh-code-review cho mã, nckh-review cho báo cáo).
3. Viết bàn giao, cập nhật plan.
4. Commit lên `feat/rclagent-rq-c-x1-known-service-query`, push, mở PR.

## Checks
- Mọi số trong báo cáo truy được về một cột của `outcomes.csv` hoặc `runs.csv`.
- Link trong báo cáo và plan đều mở được.
- CI hoặc bộ test `K/` chạy lại thoát 0 trên nhánh.

## Risk / Rollback
- Reviewer tìm thấy lỗi số: sửa trước khi mở PR, ghi vào báo cáo.
- Rollback: đóng PR; nhánh giữ lại để đối chiếu.
