---
phase: 5
title: "Chốt PR #2"
status: completed
priority: P2
effort: "0.5h"
dependencies: [4]
---

# Phase 5: Chốt PR #2

## Goal
Đưa [PR #2](https://github.com/siinn1706/NT114/pull/2) về trạng thái sẵn sàng merge, có đủ script, test, report và plan của S1 v2.

## Files to Create / Modify
- Commit: `compare-run-outputs.py`, `test-compare-run-outputs.py`, report S1, hai handoff đã cập nhật, thư mục plan này.
- Không commit `runtime/` (đã nằm trong `.gitignore`), `.claude/`.

## Tasks & Steps
1. Commit theo conventional commit, tách mã (`feat(reproduction)`) và tài liệu (`docs(reports)`), không ghi mã plan hay mã finding trong message.
2. Push nhánh `feat/rclagent-harness-budget-guard`.
3. Cập nhật mô tả PR #2: thêm mục S1 v2 (kết quả chính, link report), giữ phần cũ.
4. Kiểm `gh pr view 2`: mergeable, không conflict với `main`.
5. Hỏi sếp có merge không. Không tự merge.

## Verification
- `git status` sạch ngoài `.claude/`.
- `gh pr view 2 --json mergeable,state` cho `MERGEABLE`, `OPEN`.
