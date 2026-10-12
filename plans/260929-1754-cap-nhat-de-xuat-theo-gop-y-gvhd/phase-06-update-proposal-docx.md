---
phase: 6
title: "Cập nhật Proposal.docx"
status: completed
effort: 3h
---

# Phase 06 — Cập nhật Proposal.docx

## Mục tiêu
Ghép nội dung đã soạn ở phase 01–05 và 08 vào `Proposal_v2.docx`, giữ nguyên style và định dạng của bản gốc.

## Tệp
- Đọc: `D:/NT114/Proposal.docx`
- Ghi: `D:/NT114/Proposal_v2.docx`. Không ghi đè file gốc.

## Thay đổi theo từng mục

| Mục | Thay đổi |
|---|---|
| Tên đề tài | Đổi thành tên đề cương: "Phát triển hệ thống phát hiện sự cố và phân tích nguyên nhân gốc cho microservices trên Kubernetes sử dụng truy xuất lai và mô hình ngôn ngữ lớn" |
| 1, 3 | Viết lại theo phạm vi mới: phát hiện → định vị/phân loại → giải thích, trên K8s (phase 08) |
| 2. Mục tiêu | Thêm các mục tiêu: phát hiện sự cố; hệ thống end-to-end trên K8s; chiến lược nén telemetry; Hybrid Retrieval; khung đánh giá giải thích đa tầng; pipeline tái lập bằng MLOps |
| 4.1 Đầu vào | Thêm một đoạn chuyển tiếp: telemetry thô được chuyển thành incident card (trỏ sang 5.1) |
| 4.2 Đầu ra | `Rank/score` trỏ sang độ đo ở 6.1; `Explain` phải kèm `evidence_ids`. Sửa lỗi chính tả "xả ra" thành "xảy ra" |
| 5 | Tách thành 5.0 Kiến trúc tổng thể (phase 08), 5.1 Tiền xử lý và nén telemetry (phase 01), 5.2 Hybrid Retrieval (phase 02), 5.3 MLOps/DevOps (phase 05), và 5.4 Công nghệ (danh sách cũ, bỏ câu "chưa được khóa" ở những chỗ nay đã chốt; ghi rõ chỉ dùng mô hình open-weight) |
| 6 | Viết lại thành 6.1–6.5 (phase 03 và 04, cộng các độ đo truy hồi từ phase 02) |
| 7 | Bổ sung các sản phẩm MLOps |
| 8 | Đổi thành "Các điểm đã điều chỉnh theo góp ý": bảng 5 dòng gồm góp ý → mục đã bổ sung. Giữ lại các câu hỏi chưa được trả lời |
| 9 (mới) | Hướng mở rộng (phase 05) |

## Các bước
1. Sao lưu: copy `Proposal.docx` thành `Proposal_v2.docx`.
2. Dùng skill `anthropic-skills:docx` (hoặc python-docx) để chèn heading, đoạn văn và bảng theo đúng style đã có trong file (Heading, List Paragraph…).
3. Chèn 4 sơ đồ (kiến trúc tổng thể, pipeline nén, hybrid retrieval, đánh giá đa tầng) dạng PNG, vẽ bằng skill `scientific-figure` hoặc `ak-excalidraw`.
4. Chuyển sang PDF bằng LibreOffice và xem từng trang: font tiếng Việt, đánh số mục, bảng không tràn lề.

## Kiểm tra
- Đi qua các tiêu chí nghiệm thu trong plan.md liên quan tới Proposal, đánh dấu từng mục.
- File mở được trong Word/LibreOffice và không bị mất phần nội dung cũ nào không nằm trong danh sách sửa.

## Rollback
- Xóa `Proposal_v2.docx`. File gốc không bị động tới.
