# Giao thức tìm kiếm (đóng băng 2026-10-19T04:20Z)

Nguồn thiết kế: [phase-01](../phase-01-dong-bang-giao-thuc-va-kiem-elicit.md), [phase-02](../phase-02-tim-kiem-co-he-thong.md),
[plan.md](../plan.md) mục 5, 6, 9 và Validation Log.

## 1. Truy vấn

Đúng như bảng khối A–H của Phase 02. Thiết lập chung đã đo ở Phase 01:

- `search_papers`: semantic, corpus `elicit`, `minYear 2020`, `maxYear 2026`, `retracted: exclude_retracted`,
  `excludeKeywords: [patient, clinical, hospital, nursing, healthcare]`.
- **`maxResults` = 50** cho `search_papers` trực tiếp (trần gói là 300; xem sai lệch D1).
- Systematic review: `maxResults` 150 mỗi truy vấn, nhóm {A+B+C+D}, {E}, {F+G}.

## 2. Tiêu chí chọn/loại

I1–I5, E1–E6 như Phase 01. Dùng nguyên văn làm tiêu chí sàng lọc của systematic review.

## 3. Khử trùng lặp

DOI chuẩn hoá → arXiv ID không phiên bản → tiêu đề chuẩn hoá + năm ±1 → xem tay. Preprint + bản xuất
bản gộp một `work_id` (Phase 03).

## 4. Schema

Trích xuất: Phase 04. Phát hiện: plan.md mục 6 (11 trường).

## 5. Ngân sách

plan.md mục 9; review đầu tiên > 20 % thì dừng hỏi.

## 6. Lựa chọn của chủ dự án

Systematic review `thorough`, `useFigures: true`; cho phép nguồn công khai ngoài Elicit; không dùng bản
tóm tắt ChatGPT.

## Sai lệch so với giao thức

| ID | Ngày | Sai lệch | Lý do |
|---|---|---|---|
| D1 | 2026-10-19 | `search_papers` trực tiếp dùng `maxResults 50` thay vì 200; phần thu rộng giao cho systematic review (150/truy vấn) | Kết quả MCP đi vào ngữ cảnh của trình thực thi, không ghi thẳng ra đĩa; 200 tóm tắt mỗi truy vấn × ~30 truy vấn vượt khả năng xử lý. Systematic review thu rộng và xuất CSV |
| D3 | 2026-10-19 | Systematic review chạy với `useFigures: false` thay vì `true` | Elicit từ chối: `figure_extraction_required` (gói hiện tại không có). Lựa chọn còn lại là nâng gói, ngoài phạm vi |
| D4 | 2026-10-19 | Chỉ chạy **một** systematic review (H1, nhóm A+B+C+D); H2/H3/G dùng `search_papers` + arXiv/Crossref + sàng lọc thủ công | SR1 làm `percentUsed` 0 → 24 % khi còn đang chạy (vượt ngưỡng 20 %); chủ dự án chọn "No more reviews" |
| D5 | 2026-10-19 | Export CSV của review tải bằng script đọc transcript cục bộ, không in URL | URL export là S3 pre-signed chứa token tạm thời; ràng buộc không in token |
| D6 | 2026-10-19 | Hạn mức Elicit hết (100 %) do SR1; SR1 dừng ở trích xuất (144/551 có dữ liệu). Mọi tìm kiếm sau 04:33Z, vòng snowball và vòng gap chạy trên arXiv API, OpenAlex (search và cited-by) và Crossref; không còn lệnh Elicit nào chạy được cho tới 2026-11-18T16:00Z | 6 lệnh `search_papers` lúc 06:29Z thất bại `insufficient_quota`. Nguồn công khai ngoài Elicit được phép (Validation Log V3) |
| D7 | 2026-10-19 | Trích xuất có cấu trúc làm thủ công từ toàn văn cho các bài quyết định (relevance 2), không dùng bảng trích xuất của Elicit làm bằng chứng | Bảng Elicit thiếu 407/551 dòng và chưa được kiểm |
| D2 | 2026-10-19 | "File raw" là bản ghi rút gọn (`work/raw/<query_id>.csv`: elicitId, title, year, venue, doi, url, quyết định sơ bộ), không phải JSON đầy đủ | Cùng lý do D1; JSON đầy đủ có thể lấy lại bằng cách chạy lại truy vấn đã ghi |
