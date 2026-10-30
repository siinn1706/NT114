---
phase: 2
title: "Kiểm hồi quy trên vòng 1"
status: completed
priority: P1
effort: "0.5h"
dependencies: [1]
---

# Phase 2: Kiểm hồi quy trên vòng 1

## Mục tiêu

Chứng minh analyzer đã sửa cho đúng các con số của vòng 1 mà báo cáo `results-261029-0130` đang dùng, và không có vấn đề toàn vẹn mới.

## File

- Không sửa file nào trong repo.
- Output ghi vào `runtime/analysis-missing-source-{a-v13,b-v1,ab}-recheck-261029/`, là thư mục mới. Các thư mục output cũ giữ nguyên.

## Các bước

1. Chạy analyzer đã sửa trên ba bộ đầu vào:
   - **A:** `runtime/kaggle-output-v13/rclagent-smoke/rclagent-smoke-results.zip` với `runtime/bundle-missing-source-a/manifest.json`.
   - **B:** `runtime/kaggle-output-b-v1/rclagent-smoke/rclagent-smoke-results.zip` với `runtime/bundle-missing-source-b/manifest.json`.
   - **A+B:** hai cặp trên trong cùng một lệnh.

2. Viết một script so sánh nhỏ, đặt trong scratchpad (không đưa vào repo), cho từng bộ:
   - Các khóa sau trong `summary.json` mới phải bằng bản cũ, so sau `sort_keys`: `runs`, `status`, `integrity_problems`, `suffixed_top1`, `by_condition`, `cpu_baselines_by_trace`.
   - Với `screening`, so mọi khóa cũ; bỏ qua hai khóa mới `missing_pairs` và `evaluable`.
   - Hai khóa mới phải có giá trị sau: `provisional` là False, `unscored_passed` rỗng.
   - Ở mọi so sánh, `evaluable` là True và `missing_pairs` rỗng.

3. Kiểm thêm một lần: chạy A với manifest A-r2. Analyzer phải từ chối vì `bundle_sha256` lệch.

## Verification

- Script so sánh in `MATCH` cho cả A, B, A+B và thoát mã 0.
- Lần chạy A với manifest A-r2 thoát khác 0, kèm thông báo lệch bundle.
- Lưu log vào `runtime/test-logs/analyze-missing-source-recheck-01.log`.

## Rủi ro và rollback

Nếu có trường nào lệch: dừng lại, ghi khóa bị lệch và nguyên nhân, rồi quay về phase 1. Không sửa output cũ, không sửa báo cáo kết quả trong phase này.
