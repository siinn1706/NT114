---
title: Plan sửa lỗi audit analyzer và harness thiếu nguồn RCLAgent
date: 2026-10-29
summary: Lập plan 3 phase sửa các lỗi đã tái hiện trong audit 261029-1121
---

# Plan sửa lỗi audit analyzer và harness thiếu nguồn RCLAgent

## What happened
Audit độc lập (plans/reports/audit-261029-1121-rclagent-missing-source-analyzer-harness.md) xác nhận số liệu vòng 1 đúng, nhưng tìm được 10 lỗi tái hiện trên CPU ở analyze-missing-source-results.py và kaggle-runtime.py. Plan plans/261029-1128-rclagent-analyzer-harness-audit-fixes/ gồm 3 phase: sửa analyzer kèm test mới, kiểm hồi quy trên vòng 1, sửa runtime (F5 tool server không bị dừng khi không kịp sẵn sàng, F2 chấm từng run độc lập).

## Decision
- Sửa F1 (sự kiện retry treo trước fatal) ở phía analyzer, không sửa smoke-worker.py, vì vòng 2 đang chạy đúng bản worker hiện tại.
- Không dựng lại notebook hay bundle trong plan này. verify-package.py sẽ báo RUNTIME_SOURCE lệch có chủ đích cho tới lần dựng gói sau.
- Q1–Q9, F7 phía runtime, F8 và F9 nằm ngoài phạm vi, chờ sếp quyết.

## Next steps
Chạy /ak:cook trên plan. Phải sửa analyzer xong trước khi chấm kết quả vòng 2.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
