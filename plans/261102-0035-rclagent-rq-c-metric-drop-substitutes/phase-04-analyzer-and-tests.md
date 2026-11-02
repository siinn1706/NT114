---
phase: 4
title: "Script phân tích và test"
status: completed
priority: P1
effort: "5h"
dependencies: [3]
---

# Phase 4: Script phân tích và test

Biên nhận: [kết quả, mục 10](../reports/analysis-261102-rclagent-metric-drop-substitutes-results.md) (30 test mới và 5 bộ test cũ thoát 0).

## Context
- Codebook đóng băng của phase 3.
- `K/runtime/analysis-evidence-loss-s1-v2/runs.csv` (và `-s1-v3/runs.csv` cho phase 5) đã có `I2`, `I3`, `rank` cho mọi run `no_metric`; U3 và U4 đọc thẳng từ đây.
- Hàm đọc zip, `events.jsonl` và so khớp tên dịch vụ ở `K/analyze-evidence-loss.py` (đóng băng; import được nhờ `if __name__ == '__main__'` ở dòng 1127 và cách nạp `importlib` ở dòng 52; chỉ import, không sửa).
- Quy ước test của `K/`: `K/test-analyze-evidence-loss.py`, chạy bằng `K/runtime/harness-env/Scripts/python.exe -X utf8`.

## Requirements
- Script mới chỉ tính phần chưa có: `U0_data`, `U0_baseline`, `U_struct`, `top1_is_struct_max` (từ bundle và mốc của phase 1), `U1_delivered`, `U2_flagged` (từ `events.jsonl`). U3, U4 và R@1 được nối vào từ hai `runs.csv` (đường dẫn là đối số), không tính lại.
- Đầu ra: `pairs.csv` (một dòng mỗi cặp, mọi chỉ báo, vị trí mất đầu tiên, `hit_without_substitute`, tập `D`/`R`/`K`), `cases.csv`, `summary.json` (hash codebook, hash script, hash zip, hash hai `runs.csv`).
- Đọc zip và so khớp tên dịch vụ bằng hàm import từ analyzer RQ (b); không sao chép logic.
- Từ chối ghi vào thư mục đã có `summary.json`.
- Có test: dữ liệu tổng hợp cho từng chỉ báo mới (đúng, sai, NA, `tie` của `U_struct`), test nối `runs.csv` (thiếu run thì báo lỗi, không im lặng), một test so với số đếm tay trên một cặp thật, và test hash biên nhận.

## Files
- Create: `K/analyze-metric-substitutes.py`, `K/test-analyze-metric-substitutes.py`.
- Modify: `K/metric-substitute-prereg.json` (thêm hash script và module nạp), `K/README.md` (một mục ngắn).

## Steps
1. Viết test trước cho từng chỉ báo trên dữ liệu tổng hợp.
2. Viết script.
3. Chạy test mới, rồi bộ test cũ của `K/` mà script import.
4. Ghi hash script vào biên nhận.

## Checks
- Test mới và cũ thoát 0; ghi lệnh và mã thoát từng bộ.
- Hash `K/evidence-loss-prereg.json` của RQ (b) vẫn khớp (analyzer không đổi).

## Risk / Rollback
- Nếu một định nghĩa của codebook không tính được tất định, dừng và ghi deviation, không sửa im lặng.
- Rollback: xóa hai file script và test.
