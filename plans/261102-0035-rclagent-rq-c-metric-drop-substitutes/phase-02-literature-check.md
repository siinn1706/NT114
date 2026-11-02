---
phase: 2
title: "Tra tài liệu"
status: planned
priority: P2
effort: "3h"
dependencies: []
---

# Phase 2: Tra tài liệu

## Context
- Bài RCLAgent gốc: [arXiv 2605.14866](https://arxiv.org/html/2605.14866v1).
- Bài nối tiếp cùng dòng đệ quy: [arXiv 2601.02732](https://arxiv.org/pdf/2601.02732).
- Bài về thất bại của agent RCA: [arXiv 2602.09937](https://arxiv.org/html/2602.09937v1) và [arXiv 2608.21310](https://arxiv.org/html/2608.21310).
- Báo cáo tài liệu đã có: [research-261031-2311](../reports/research-261031-2311-evidence-loss-attribution-methods.md), [researcher-261023-2223-q1-evidence](../reports/researcher-261023-2223-q1-evidence.md).

## Requirements
- Đọc toàn văn phần phương pháp và thí nghiệm của hai bài RCLAgent; các bài khác đọc đủ để trả lời câu hỏi dưới đây.
- Trả lời, có trích vị trí (mục, trang):
  1. Bài nào đo RCLAgent hoặc agent đi theo trace khi thiếu một nguồn telemetry?
  2. Bài nào dùng độ trễ trace làm tín hiệu thay thế khi thiếu metric, hoặc dựng KPI từ trace?
  3. Điểm mù "dịch vụ lỗi không có span trong trace" đã có ai báo chưa?
- Chỉ trích câu đã đọc; mọi khẳng định "chưa ai làm" ghi là "không tìm thấy trong các bài đã đọc".

## Files
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/reports/research-261102-rclagent-missing-metric-and-trace-blind-spot.md`.

## Steps
1. Tải và đọc hai bài RCLAgent.
2. Tìm thêm bằng một lượt tìm có ghi truy vấn (từ khóa: missing telemetry, incomplete observability, trace-derived latency, LLM agent RCA).
3. Viết báo cáo: bảng bài, câu trả lời từng câu hỏi, vị trí trích, giới hạn của lượt tra.

## Checks
- Mỗi khẳng định có URL và vị trí trong bài.
- Danh sách truy vấn đã dùng được ghi trong báo cáo.

## Risk / Rollback
- Nếu một bài đã làm đúng hướng X sắp chọn, phase 6 ghi rõ và hạ hạng hướng đó về "tái hiện", không xóa.
- Rollback: xóa báo cáo.
