---
phase: 4
title: "Báo cáo S1 cạnh vòng 2"
status: completed
priority: P1
effort: "1.5h"
dependencies: [2, 3]
---

# Phase 4: Báo cáo S1 cạnh vòng 2

## Goal
Một report tiếng Việt đặt S1 v2 cạnh vòng 2 theo mục 4 của phân tích 261029-1629, không thay kết luận pilot đã nhận.

## Files to Create / Modify
- Create: `plans/reports/results-261031-HHMM-rclagent-s1-v2-budget-sensitivity.md`
- Modify: `plans/reports/handoff-261030-1156-rclagent-s1-continue-on-github.md` (bảng "Đang ở đâu": S1 v2 đã chạy và phân tích, link report)
- Modify: `plans/reports/handoff-261029-1710-rclagent-budget-sensitivity-s1.md` (thêm mục cập nhật ngắn, link report)

## Tasks & Steps
1. Mục nguồn gốc: kernel, tài khoản chạy, hash, thời gian chạy (A 25.387 s, B 16.135 s so với ước tính 7,5–8 giờ), link file JSON ở phase 1.
2. Bảng tỷ lệ hoàn tất hợp lệ theo gói và điều kiện, vòng 2 cạnh S1, có cột lý do hỏng.
3. R@1 và MRR trên toàn bộ lượt (lượt lỗi tính 0) và trên lượt hợp lệ, kèm mẫu số.
4. Các cặp mà cả hai lượt đều hoàn tất (từ `pairs.json`).
5. Bảng 8 lượt từng chạm trần ở vòng 2: trạng thái S1, số request, số vòng tối đa của span từng bị dừng, điểm.
6. Kết quả kiểm điều kiện từ phase 3. Khác biệt nào cũng ghi lại, không quy cho việc đổi trần.
7. Hai lượt B hỏng ở cả hai vòng: ghi là lỗi giao thức lặp lại, không phải do trần.
8. Giới hạn: n nhỏ (8 case, 3 seed), tính tất định của vLLM không được đảm bảo, S1 là kiểm độ nhạy chứ không phải ước lượng độ chính xác.
9. Câu hỏi còn mở ở cuối report.

## Verification
- Mọi con số trong report truy được về một file trong `runtime/analysis-*-s1-v2` hoặc `runtime/analysis-missing-source-r2-vs-s1-v2`.
- Mọi link tương đối trong report và hai handoff mở được.
- Rà văn phong bằng `nckh-review` hoặc reviewer độc lập trước khi commit.
