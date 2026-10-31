---
phase: 1
title: "Kiểm nguồn gốc và quyền riêng tư"
status: completed
priority: P1
effort: "0.5h"
dependencies: []
---

# Phase 1: Kiểm nguồn gốc và quyền riêng tư

## Goal
Ghi lại bằng chứng rằng output S1 v2 đến từ đúng gói v2 và kernel, dataset đều private.

## Files to Create / Modify
- Create: `runtime/kaggle-provenance-s1-v2.json`
- Create: `runtime/kaggle-private-status-s1-v2.json`

## Tasks & Steps
1. Ghi vào `kaggle-provenance-s1-v2.json` cho A và B: kernel id, trạng thái `COMPLETE`, SHA256 của results ZIP, bundle và manifest SHA256 lấy từ `run-once.json` và `input-verification.json`, `harness_limits`, `run/status.json` (elapsed, số trace pass/failed).
2. So bundle SHA256 với `s1-v2/{a,b}/rclagent-kaggle-bundle.zip.sha256` đã commit.
3. Chạy `check-kaggle-private.py` (đọc `--help` trước) cho hai dataset `siinn1706/...-s1-261029` và hai kernel `svuittri/...-s1-gpu-261030`. Ghi kết quả vào `kaggle-private-status-s1-v2.json`, theo dạng của `kaggle-private-status-s1.json`.
4. Nếu API không trả trạng thái kernel của `svuittri`, ghi rõ "chưa kiểm qua API" và nguồn thay thế (ảnh chụp sếp gửi), không đoán.

## Verification
- `sha256sum -c` trên hai file `.sha256` của results ZIP đều OK.
- Bundle SHA256 trong output bằng giá trị đã commit trong `s1-v2/`.
- File privacy không có dòng nào `public`.
