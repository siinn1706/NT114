---
phase: 6
title: "Truy cập toàn văn 100 bài và ledger quyền"
status: done
receipt: work/receipts/06-access-publisher-01.json
owner_skills: [nckh-literature]
---

# Giai đoạn 06: Truy cập toàn văn

## Yêu cầu

- Mỗi bài T1 có một trạng thái truy cập: `full-text-journal`, `full-text-accepted`, `full-text-preprint` (ghi khác biệt), `abstract-only`, `no-access`, kèm lý do.
- PDF chỉ lưu `private/fulltext/261024/`; ghi SHA-256, kích thước, phiên bản, URL nguồn, quyền (OA license hoặc quyền truy cập của chủ dự án).
- Không tự động hóa SSO, không vượt paywall.

## Tệp

- Đọc: `work/records/t1-top100.csv`, `work/reuse-fulltext-map.csv`.
- Tạo: `private/fulltext/261024/<record_id>.pdf`, `private/fulltext/261024/<record_id>.txt`, `work/access-ledger.csv` (record, nguồn, URL, HTTP, version, license, pdf_sha256, text_sha256, extractor+version, số trang), `work/manual-download-request.md`, `work/receipts/06-*.json`.

## Các bước

1. Dùng lại toàn văn cũ có `reusable=1`, hash lại.
2. Batch 10 bài: OpenAlex `best_oa_location` → Unpaywall → arXiv (khớp tiêu đề + tác giả, ghi version) → trang publisher OA.
3. Trích text bằng `pypdf` (ghi version) hoặc extractor sẵn có; ghi số trang, text hash; PDF ảnh → `image-only`, cần OCR + đối chiếu trực quan nếu dùng.
4. Bài không lấy được: ghi vào `manual-download-request.md` (DOI, tiêu đề, lý do) cho chủ dự án tải tay vào `private/fulltext/261024/`; trạng thái `waiting-human` chỉ cho các bài này, phase 07 vẫn chạy trên bài đã có.
5. Đếm số bài có toàn văn; nếu < 30, dừng chờ chủ dự án tải tay trước khi chấm F ([protocol §7](protocol.md)).

## Kiểm tra

- 100 dòng trong `access-ledger.csv`, mỗi dòng một trạng thái.
- Mọi `pdf_sha256` khớp file trên đĩa; file bắt đầu bằng `%PDF`.
- `git status` không hiện file nào dưới `private/`.

## Rủi ro và hoàn tác

- Preprint khác bản tạp chí: ghi khác biệt đã thấy (tiêu đề, bảng kết quả); số liệu cho quyết định T3 lấy bản tạp chí nếu có.
- Publisher chặn tải tự động (403): không thử lại liên tục; chuyển sang yêu cầu tải tay.
- Hoàn tác: xóa PDF hỏng/sai bài (hash không khớp DOI), giữ dòng ledger lỗi.
