---
phase: 2
title: "Đăng ký trước X1 và decision record"
status: planned
priority: P1
effort: "2h"
dependencies: [1]
---

# Phase 2: Đăng ký trước X1 và decision record

## Context
- Quyết định sếp chốt 2026-11-02 trong [plan.md](./plan.md): hai nhánh, kiểm hồi quy, đổi khung RQ (c).
- Mẫu prereg trước: [codebook RQ (b)](../reports/prereg-261031-2311-rclagent-evidence-loss-codebook.md) và biên nhận `K/evidence-loss-prereg.json`.
- Kết quả phase 1.

## Requirements
- Prereg viết trước khi có bất kỳ output nào của X1, và có hash (SHA256 sau khi đổi CRLF thành LF, như RQ (b)).
- Tuyên bố phơi nhiễm: các số S1 v2/v3 của 8 case đã thấy (R@1 0/9 ở `metric` cho 3 case không có span GT; R@1 từng case có span GT), và kết quả phase 1.
- Nội dung bắt buộc:
  1. Hai điều kiện mới: `metric_x1p` (metric `repaired`, logs `author`, `--x1 prompt`) và `metric_x1q` (như trên, `--x1 query`). Mốc so: run `metric` của S1 v3 cùng case và seed.
  2. Câu chữ nguyên văn của gợi ý `x1_prompt` (tiếng Anh như prompt tác giả), chèn vào đâu trong request self-state, và luật nhận diện request self-state (request có tool `search_fluctuating_metrics`). Câu chữ không nhắc dịch vụ cụ thể nào ngoài danh sách 12 tên.
  3. Luật của `x1_query`: dịch vụ nào được hỏi, timestamp nào, thứ tự gộp, bỏ kết quả `NO_ROWS`/`NO_KPI`, trần kích thước từ phase 1, loại sự kiện ghi lại.
  4. Câu kết cục, tính bằng script, R@1 lấy từ `author-score.txt`:
     - C1 (chính): số case không có span GT (trên 3) mà `metric_x1p` có R@1 bằng 1 ở ít nhất 2/3 seed; mốc S1 v3 là 0/3.
     - C2: số run `metric_x1p` (trên 9, ba case không có span GT) mà model tự hỏi metric của GT (I0 theo định nghĩa analyzer, chỉ đếm truy vấn của model).
     - C3 (cận trên): như C1 cho `metric_x1q`.
     - C4 (hồi quy): số case có span GT (trên 5, báo riêng `99f095` vì là case hiệu chỉnh của RQ (b)) mà số seed có R@1 bằng 1 của `metric_x1p` thấp hơn S1 v3.
     - C5: số run hoàn tất và lớp dừng harness (`H_cap`, `H_parse`, `H_context`, `H_other`) theo nhánh.
  5. Cách đọc: mọi câu là mô tả trên n nhỏ. Không có ngưỡng "hiệu quả". C3 là cận trên có bơm bảng GT, không là bằng chứng cho can thiệp thực tế.
- Decision record ghi khung RQ (c) mới cho X1 và lý do (R@1 bằng 0 ở cả `metric` và `no_metric` trên 3 case), trỏ về decision-261028-1104.

## Files
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/reports/prereg-261102-rclagent-x1-known-service-query.md` (LF; `.gitattributes` đã có `plans/reports/prereg-*.md text eol=lf`).
- Create: `K/x1-prereg.json` (hash prereg, hash `metric-repair.py`, hash `smoke-worker.py` sau phase 3 được thêm ở phase 4).
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/reports/decision-261102-rclagent-rq-c-x1-framing.md`.

## Steps
1. Viết prereg theo các mục trên, dùng số phase 1 cho trần gộp.
2. Gửi sếp câu chữ gợi ý `x1_prompt` và câu kết cục để duyệt; ghi lần duyệt (ngày, phiên bản) trong prereg.
3. Tính hash, ghi `K/x1-prereg.json`.
4. Viết decision record.

## Checks
- Hash trong `K/x1-prereg.json` khớp hash tính lại.
- Mỗi câu kết cục chỉ ra cột hoặc file nguồn và đơn vị đếm.
- Prereg không chứa nhãn GT trong câu chữ gợi ý.

## Risk / Rollback
- Sửa prereg sau khi đóng băng phải qua `deviation-log.md` trong thư mục plan này.
- Rollback: xóa ba file mới; chưa có output Kaggle nào phụ thuộc chúng.
