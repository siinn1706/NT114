---
phase: 6
title: "Lượt dev trên Kaggle"
status: in-progress
priority: P1
effort: "6h"
dependencies: [4, 5]
---

# Phase 6: Lượt dev trên Kaggle

## Context
- Đã có quy trình dựng và đẩy gói: `K/prepare-bundle.py`, `K/build-notebook.py`, `K/verify-package.py`, `K/check-kaggle-private.py`.
- Sếp đã cho phép đẩy và tải Kaggle mà không cần hỏi; không theo dõi lâu, sếp sẽ báo khi xong.
- Quota là 30 giờ GPU mỗi tuần.

## Requirements
- Gói theo đúng tập dev và lưới điều kiện của prereg. Chia gói để mỗi phiên dưới 10 giờ.
- Kiểm gói ở chế độ private trước khi đẩy. Ghi hash prereg vào manifest.
- Đẩy xong thì dừng, ghi trạng thái vào bàn giao.

## Files
- Create (gitignored): các thư mục upload trong `K/runtime/`.
- Create: `plans/reports/handoff-<ngày>-rclagent-telemetry-gap-dev-run.md`.

## Steps
1. Dựng gói, chạy `verify-package.py`.
2. Đẩy bằng `kaggle kernels push`, ghi version.
3. Khi sếp báo xong: tải output, kiểm hash.

## Checks
- `verify-package.py` thoát 0; kernel ở chế độ private.
- Sau khi tải: mọi run trong prereg đều có `worker-status.json`.

## Risk / Rollback
- Hết quota: dừng, báo ngày quota làm mới, chia gói sang tuần sau.
- Rollback: xóa thư mục upload; trên Kaggle chỉ còn các version private.
