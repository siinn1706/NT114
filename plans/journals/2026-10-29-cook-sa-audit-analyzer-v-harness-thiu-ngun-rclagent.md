---
title: Cook sửa audit analyzer và harness thiếu nguồn RCLAgent
date: 2026-10-29
summary: "Analyzer kiểm retry theo thứ tự, gắn ZIP với bundle, báo provisional; runtime dừng tool server không sẵn sàng và chấm từng run"
---

# Cook sửa audit analyzer và harness thiếu nguồn RCLAgent

## What happened
Thực hiện plan 261029-1128 (3 phase, --auto). Analyzer: kiểm chuỗi malformed retry theo thứ tự log (F1/F6), từ chối SHA256 sai bằng SystemExit (F10), ZIP lệch bundle/khóa progress thừa/run trùng (F3/F4), thêm missing_pairs/evaluable, sessions/unscored_passed/provisional, dòng events hỏng thành lỗi toàn vẹn (F2/F7). Runtime: start_tool_server dừng server không sẵn sàng (F5), score_runs chấm từng run và ghi scorer-status.json (F2).

## Evidence
- test-analyze-missing-source-results.py: 16 test, 14 lỗi trên code cũ, 16/16 pass sau sửa.
- Chạy lại vòng 1 A, B, A+B: mọi khóa số khớp summary đã lưu; A với manifest A-r2 bị từ chối.
- Suite: 37/38 harness, 14, 11, 4, 6, 16.

## Decision
- Kiểm cổng 5000 bằng connect thay vì bind: TIME_WAIT sau khi dừng server trước sẽ làm bind lỗi trên Linux.
- test_expanded_kaggle_dataset_hash_verification lỗi có chủ đích tới lần dựng gói sau (gói stage còn runtime cũ 777b8c37…); không nới test.

## Next steps
Chấm vòng 2 bằng analyzer mới khi Kaggle xong. Dựng gói sau sẽ đưa runtime mới vào và làm test hash pass lại.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
