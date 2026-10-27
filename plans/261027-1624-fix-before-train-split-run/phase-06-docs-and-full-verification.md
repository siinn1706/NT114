---
phase: 6
title: "Tài liệu và kiểm toàn bộ"
status: completed
priority: P2
effort: "0.5d"
dependencies: [1, 2, 3, 4, 5]
---

# Phase 6: Tài liệu và kiểm toàn bộ

## Goal
Tài liệu khớp với code và kết quả hiện tại. Mọi kiểm chạy lại trên revision cuối và được ghi vào report.

## Files to Create / Modify
- Modify: `README.md`: dòng 6 và 53-54 ghi trạng thái cũ (dừng ở E, 38.048 dòng metric, 0 dòng log). Cập nhật theo v8 và theo batch runner.
- Modify: `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/README.md`, `plans/reports/design-261027-1155-tool-result-budget.md` (phạm vi bảo đảm của ngân sách theo Q1)
- Modify: `nt114-rca/nt114-rca/docs/data_contract.md` nếu phase 4 hoặc 5 đổi contract (tier B trên tập train, `EXTRACT_MISSING`, múi giờ)
- Create: `plans/reports/fix-<yymmdd-hhmm>-before-train-split-run.md`

## Tasks & Steps
1. Chạy lại mọi kiểm:
   - harness, ngân sách, T4, `verify-package` (đường B);
   - `pytest -m "not realdata"`, `verify-splits`, `verify-bundle` (đường A);
   - so output của script scan (phase 2).
2. Sửa tài liệu ở mục Files, đối chiếu từng số liệu với artifact.
3. Viết report: các thay đổi, các kiểm cùng exit code, giới hạn, và việc nào còn chờ sếp duyệt (pilot GPU, tái tạo dữ liệu).
4. Đánh dấu trạng thái phase trong `plan.md`.

## Verification
- Mọi link trong README và report trỏ tới file tồn tại.
- Không còn số liệu cũ mâu thuẫn với artifact (grep `38.048`, `dừng ở bước E`).
- Không commit hay push khi chưa có lệnh của sếp.
