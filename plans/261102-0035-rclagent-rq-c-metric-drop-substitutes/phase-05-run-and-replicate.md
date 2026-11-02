---
phase: 5
title: "Chạy trên S1 v2, kiểm lặp S1 v3"
status: completed
priority: P1
effort: "1h"
dependencies: [4]
---

# Phase 5: Chạy trên S1 v2, kiểm lặp S1 v3

Biên nhận: [kết quả, mục 6](../reports/analysis-261102-rclagent-metric-drop-substitutes-results.md) (S1 v2 và S1 v3 trùng từng byte, `integrity_problems` rỗng).

## Context
- Zip S1 v2: `K/runtime/kaggle-output-{a,b}-s1-v2/rclagent-smoke/rclagent-smoke-results.zip`, manifest `K/s1-v2/{a,b}/manifest.json`.
- Zip S1 v3: `K/runtime/kaggle-output-{a,b}-s1-v3/...`, manifest `K/s1-v3/{a,b}/manifest.json`. S1 v3 là bản sao của S1 v2 (`runs.csv` trùng từng byte, [báo cáo S1 v3](../reports/analysis-261101-s1-v3-hashseed-and-evidence-loss-check.md)), chỉ dùng kiểm lặp.

## Requirements
- Kiểm hash codebook và script khớp biên nhận trước khi chạy.
- Chạy S1 v2 vào `K/runtime/analysis-metric-substitutes-s1-v2/` (nối `K/runtime/analysis-evidence-loss-s1-v2/runs.csv`), S1 v3 vào `K/runtime/analysis-metric-substitutes-s1-v3/` (nối `K/runtime/analysis-evidence-loss-s1-v3/runs.csv`).
- So hai `pairs.csv`; liệt kê mọi cặp lệch. 10 cặp `order_only` của S1 v3 chỉ khác phản hồi cuối, nên lệch nếu có chỉ được ở `U4_rank`.

## Files
- Create (gitignored): hai thư mục output trên.

## Steps
1. Kiểm hash.
2. Chạy script trên S1 v2, rồi S1 v3.
3. So hai `pairs.csv` bằng một đoạn `join` ngắn, ghi lệnh vào báo cáo phase 6.

## Checks
- `summary.json` của cả hai có `integrity_problems` rỗng và hash khớp.
- Số cặp: `D` 6, `R` 3, `K` 5 (hoặc ghi rõ cặp thiếu vì run hỏng).

## Risk / Rollback
- Lệch ngoài `U4_rank`: là phát hiện về tính tất định, báo trong phase 6, không chỉnh luật.
- Rollback: xóa hai thư mục output.
