---
phase: 8
title: "Review ngữ cảnh mới, toàn bộ test, handoff"
status: planned
owner_skills: [nckh-review, nckh-code-review, nckh-handoff]
---

# Giai đoạn 08: Review và bàn giao

## Yêu cầu

- `nckh-code-review` trên diff phase 03–06: rò rỉ, đếm lời gọi, mẫu số, test bị suy yếu.
- `nckh-review` trên gói khả thi và câu chữ: không gọi R-a là tái hiện, không gọi IM1 là cải tiến đã chứng minh hay mới, đúng quy ước đọc CI.
- Gate matrix theo §4 của [plan](plan.md); mỗi `pass` có receipt.
- Handoff: trạng thái, artifact và hash, cổng mở, câu hỏi cho chủ dự án (cấp quyền chạy, M5).

## Tệp

- Đọc: diff, log test, receipt, phase 01–07.
- Tạo trong thư mục kế hoạch: `research/final-review.md`, `work/gate-matrix.csv`, `work/handoff.md`.

## Các bước

1. Chạy `pytest` toàn bộ với receipt.
2. Review; sửa theo bằng chứng; review lại nếu sửa thực chất.
3. Chạy `check-plan.py` trên thư mục kế hoạch.

## Kiểm tra

- `pytest` exit 0; `check-plan.py` exit 0.
- Không `pass` thiếu receipt; trạng thái cuối tối đa `ready-for-review`.

## Rủi ro và hoàn tác

- Review phát hiện rò rỉ: quay lại phase tương ứng bằng attempt mới, giữ attempt cũ.
- Hoàn tác: không commit trong kế hoạch này, nên hoàn tác là hoàn nguyên working tree theo diff đã ghi.
