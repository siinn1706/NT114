---
phase: 1
title: "Đóng băng giao thức, kiểm SJR, dựng state/checkpoint"
status: done
receipt: work/receipts/01-freeze-01.json
owner_skills: [nckh-method, nckh-literature]
---

# Giai đoạn 01: Đóng băng giao thức

## Yêu cầu

- [protocol.md](protocol.md) được kiểm, chạy thử truy vấn, review ngữ cảnh mới và hash **trước** mọi bản ghi screening.
- Ấn bản SJR được xác nhận là mới nhất tại ngày chạy hoặc amendment sang ấn bản mới.
- `work/state.json` và thư mục receipt tồn tại; inventory đầu attempt được ghi ngoài vùng đo.

## Tệp

- Đọc: [protocol.md](protocol.md), [plan.md](plan.md), [q1-protocol 11/10](../261011-1345-aiops-q1-literature-gap/work/q1-protocol.md), [decisions.md](../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md), [review 23/10](../reports/review-261023-2223-research-focus-and-paper-foundation.md), [Q1 audit 23/10](../reports/researcher-261023-2223-q1-evidence.md).
- Tạo: `work/state.json`, `work/amendments.md`, `work/protocol-freeze.json` (SHA-256 protocol, thời điểm, revision git), `work/query-probe.csv`, `work/sjr-edition-check.md`, `research/protocol-review.md`, `work/receipts/01-*.json`.
- Chỉ sửa `protocol.md` trong phase này, trước freeze.

## Các bước

1. Inventory: `check-receipt.py inventory --root <plan-dir> --output <ngoài plan-dir>`.
2. Kiểm ấn bản SJR qua trình duyệt (trang journalrank, năm mới nhất trong dropdown). Ghi kết quả; nếu có ấn bản > 2025, tải qua Chrome như 11/10, hash, amendment Q-1.
3. Hash lại CSV SJR, đếm `Type` và số journal Q1-CS; so với số ghi ở [plan §3](plan.md).
4. Chạy thử mỗi truy vấn §5 một trang (`per_page=1`), ghi `meta.count`, lỗi cú pháp, 5 tiêu đề đầu vào `work/query-probe.csv`. Sửa cú pháp hỏng (không đổi khái niệm).
5. Kiểm regex §4 trên 30 bản ghi seed RCA chắc chắn (dương) và 30 bản ghi ngoài miền từ `raw-hits.csv` (âm); sửa nếu sai > 1 mỗi phía.
6. Spawn `nckh-reviewer` ngữ cảnh mới review protocol: câu hỏi, PCC, cổng Q1, rubric R/F/G, tie-break, shortfall, rủi ro thiên lệch. Ghi `research/protocol-review.md`; sửa phát hiện chặn; phát hiện không áp dụng ghi lý do.
7. Đổi `revision` của protocol thành `frozen-<ngày>`, hash, ghi `work/protocol-freeze.json` và `state.json.protocol_sha256`.

## Kiểm tra

- `sha256sum protocol.md` khớp `protocol-freeze.json`; exit 0 ghi trong receipt.
- `query-probe.csv` có 17 dòng, mỗi dòng có HTTP status và count; không truy vấn nào lỗi.
- Review không còn phát hiện chặn mở.
- Chưa tồn tại file nào dưới `work/screen/`.

## Rủi ro và hoàn tác

- SCImago chặn truy cập: giữ ấn bản 2025 đã hash, ghi “không xác nhận được ấn bản mới hơn” là giới hạn, không chặn.
- Truy vấn trả quá nhiều nhiễu (> 20.000): thu hẹp bằng ràng buộc hệ thống, ghi trước freeze.
- Hoàn tác: xóa các file mới tạo của phase (trừ receipt lỗi), khôi phục protocol từ git.
