---
phase: 6
title: "Báo cáo, xếp hạng X, bàn giao và PR"
status: in-progress
priority: P1
effort: "4h"
dependencies: [2, 5]
---

# Phase 6: Báo cáo, xếp hạng X, bàn giao và PR

## Context
- Output phase 5, báo cáo tài liệu phase 2, codebook phase 3.
- Mẫu: [kết quả RQ (b)](../reports/analysis-261101-1023-rclagent-evidence-loss-results.md) mục 13 (bảng hướng X).

## Requirements
- Báo cáo tiếng Việt: trả lời bằng lời thường trong tối đa 8 dòng; bảng theo cặp và theo case cho `D`, `R`, `K`; câu kết cục; giới hạn (n = 3 case, seed gần như nhân bản, phơi nhiễm, `99f095` là case hiệu chỉnh của RQ b); tái lập (lệnh, hash, đường dẫn).
- Bảng hướng X để thu hẹp mức giảm khi bỏ metric: mỗi hướng có giai đoạn nhắm tới, dữ liệu nhất quán, làm được mà không sửa `upstream/` không, tính mới theo phase 2, và điều kiện kiểm (cần chạy model). Hướng thêm nguồn mới (ví dụ KPI độ trễ dựng từ trace) ghi riêng.
- Nêu quyết định tiếp theo cho sếp: lập plan Kaggle cho hướng X hạng 1 (có thể gộp X1 đang tạm dừng vào cùng gói) hay dừng.
- Không ngôn ngữ nhân quả tổng quát.

## Files
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/reports/analysis-261102-rclagent-metric-drop-substitutes-results.md` (đổi ngày theo ngày viết).
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/reports/handoff-261102-rclagent-rq-c-step-1.md` (đổi ngày theo ngày viết).
- Modify: [plan.md](./plan.md) (trạng thái phase kèm link biên nhận), `llms.txt` nếu repo đang liệt kê báo cáo ở đó.

## Steps
1. Viết báo cáo từ `pairs.csv` và `cases.csv`, không chép số tay.
2. Reviewer ngữ cảnh mới rà báo cáo (nckh-review) và script (nckh-code-review).
3. Viết bàn giao, cập nhật plan.
4. Commit lên `feat/rclagent-rq-c-metric-drop-substitutes` (conventional commit, không nhắc AI hay mã phase; không commit `runtime/`), push, mở PR.

## Checks
- Mọi số trong báo cáo truy được về một cột của `pairs.csv`, `cases.csv` hoặc `runs.csv`.
- Link trong báo cáo và plan mở được.
- Bộ test `K/` chạy lại thoát 0 trên nhánh.

## Risk / Rollback
- Reviewer tìm thấy lỗi số: sửa trước khi mở PR.
- Rollback: đóng PR, giữ nhánh.
