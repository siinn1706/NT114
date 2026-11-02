---
phase: 1
title: "Đọc nguyên văn công trình liên quan"
status: completed
priority: P1
effort: "6h"
dependencies: []
---

# Phase 1: Đọc nguyên văn công trình liên quan

Biên nhận: [báo cáo nguyên văn](../reports/research-261102-rclagent-direction-a-related-work-full-text.md) (2026-11-02).
- [Báo cáo nguyên văn](../reports/research-261102-rclagent-direction-a-related-work-full-text.md): 10/11 bài đọc từ text trích bằng `pypdf`, có ghi URL và SHA256. ReconRCA chỉ đọc được abstract vì bản IEEE đóng.
- Controller tự kiểm lại hai điểm trên nguyên văn: RCLAgent tr. 14 (tiền đề phủ trace) và AMER-RCL tr. 4–7 (horizontal expansion; Algorithm 1 chỉ đi trên một trace).
- Không có bài nào đã làm M3 cho agent LLM. Ba bài chạm một phần: AMER-RCL, agent tự do truy vấn, GALA+. Vì vậy phase 3 phải thêm baseline "SQL agent trên toàn cửa sổ".

## Context
- [Tra tính mới](../reports/research-261102-rclagent-direction-a-novelty.md) mới đọc qua tóm tắt của công cụ. Subagent không có Bash nên không giải nén được PDF; controller thì có.
- Bài cần đọc nguyên văn:
  - RCLAgent 2605.14866: Sec. VI và phần cuối chưa đọc.
  - TorAI (DOI 10.1145/3808137, arXiv 2604.13522): có dùng span của bên gọi không, chạy trên bộ dữ liệu nào.
  - ARMOR 2603.25538.
  - 2601.22208, Sec. 4.2.
  - 2608.21310, Sec. 5.3, Table 3.
  - GALA+ 2608.08968.
  - 2607.13548.
  - "Free to Look" 2610.35767.
  - Hybrid RCA (CLOSER 2025).
  - AMER-RCL 2601.02732.
  - Tìm ReconRCA (ICWS 2025).

## Requirements
- Tải PDF bằng `curl` vào một thư mục mới riêng trong scratchpad, rồi trích text bằng `pypdf` chạy với `python -I`. Mỗi file ghi URL và SHA256.
- Mỗi bài ghi: vấn đề, cơ chế, bộ dữ liệu, mức trùng với M1, M2, M3 và với phép đo phạm vi trace, kèm số mục hoặc số trang và tối đa một trích dẫn ngắn.
- Ghi rõ câu tuyên bố tính mới nào được phép viết, câu nào không.

## Files
- Create: `plans/reports/research-261102-rclagent-direction-a-related-work-full-text.md`.

## Steps
1. Tải và trích text từng bài; bài nào không tải được thì ghi lý do.
2. Đọc các mục đã nêu, điền ma trận.
3. Cập nhật mục 3 của báo cáo tra tính mới nếu kết luận đổi.

## Checks
- Mỗi ô "trùng" hoặc "không trùng" có số trang hoặc số mục từ text đã trích.
- Không còn câu nào gắn nhãn [UNVERIFIED] trong phần kết luận.

## Risk / Rollback
- Tìm thấy bài đã làm M3: dừng, báo sếp, rồi đổi trọng tâm ở phase 3.
- Rollback: xóa báo cáo; PDF chỉ nằm trong scratchpad.
