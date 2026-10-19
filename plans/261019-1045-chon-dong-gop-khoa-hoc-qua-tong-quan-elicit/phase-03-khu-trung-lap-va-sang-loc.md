---
phase: 3
title: "Khử trùng lặp và sàng lọc tiêu đề/tóm tắt"
status: partial
effort: 1-1.5 ngày
depends_on: [2]
---

# Phase 03: Khử trùng lặp và sàng lọc

> **Trạng thái 2026-10-19 (sau review 261019-1441): đạt một phần.**
> - **Đã có:**
>   - khử trùng lặp;
>   - sổ sàng lọc theo công trình: [screening.csv](../261019-1501-sua-review-h1-power-va-sang-loc/work/out/screening.csv);
>   - luồng PRISMA bản ghi/công trình;
>   - kiểm tay 10 % bài Elicit loại: 39/390, 0 bất đồng, nên không phải sàng lọc lại toàn nhóm;
>   - tổng kiểm 134 bản ghi, κ 0.864.
> - **Chưa có:**
>   - relevance H1/H2/H3 (0/1/2) cho từng bài;
>   - quyết định tay cho 279 công trình ngoài SR1 qua luật tiêu đề;
>   - sàng lọc lại có trễ 30 bài. Mẫu đã rút sẵn, chỉ hợp lệ từ 2026-10-20 13:42 (giờ VN):
>     [delayed-rescreen-sample.csv](../261019-1501-sua-review-h1-power-va-sang-loc/work/out/delayed-rescreen-sample.csv).

## Yêu cầu

### Khử trùng lặp (script CPU, không gọi Elicit)

Gộp mọi nguồn thô (Elicit, nguồn đối chiếu, review của Elicit nếu có, corpus hạt giống 261011) vào
`work/corpus.csv`. Khoá gộp theo thứ tự:

1. DOI chuẩn hoá (chữ thường, bỏ tiền tố `https://doi.org/`).
2. arXiv ID không phiên bản (`2309.05833v2` → `2309.05833`).
3. Tiêu đề chuẩn hoá (chữ thường, bỏ dấu câu và stopword, gộp khoảng trắng) + năm ±1 + họ tác giả đầu.
4. Cặp còn nghi ngờ (độ tương tự tiêu đề ≥ 0.9 nhưng khác khoá) → xem tay, ghi quyết định.

**Preprint và bản xuất bản** (ví dụ PACE-LM arXiv 2309.05833 và LM-PACE FSE Companion 2024) gộp thành
một `work_id`, giữ cả hai URL, `pub_status` lấy bản peer-reviewed. Ghi rõ nếu kết quả hai bản khác nhau.

**Trạng thái xuất bản** xác minh qua DOI/Crossref, DBLP, OpenReview, trang venue; không tin riêng trường
`venue` của Elicit. Ghi `pub_status_checked_at`.

### Tái sử dụng corpus 261011

`plans/261011-1345-aiops-q1-literature-gap/work/extraction.csv` (Q1, đã đọc toàn văn) vào corpus với
`source = seed-261011`. Quyết định sàng lọc cũ **không** được kế thừa tự động: chấm lại theo tiêu chí
mới vì câu hỏi đã đổi (Jev → một LLM; tập trung H1/H2/H3). Toàn văn trong `private/fulltext/` chỉ đọc
cục bộ, không tải lên Elicit.

### Sàng lọc tiêu đề/tóm tắt

- Mỗi bài: `include` / `exclude` (mã E1–E6) / `maybe`, cộng `relevance_H1`, `relevance_H2`,
  `relevance_H3` (0/1/2, định nghĩa ở research/03).
- `maybe` đi tiếp vào Phase 04.
- Nếu dùng sàng lọc của Elicit review: kiểm tay mẫu ngẫu nhiên 10 % (tối thiểu 30) bài Elicit loại và
  toàn bộ bài Elicit giữ có relevance 2. Báo tỉ lệ bất đồng. Nếu bất đồng ở bài bị loại > 10 %, sàng
  lọc lại thủ công toàn bộ nhóm đó.
- Độ tin cậy sàng lọc: sàng lọc lại một mẫu 30 bài sau ≥ 24 giờ (một người thực hiện), báo tỉ lệ đồng
  thuận. Đây là giới hạn đã biết: không có người sàng lọc thứ hai.

### PRISMA

`work/prisma-counts.json`: thô theo engine, sau khử trùng lặp, loại theo mã, `maybe`, chuyển toàn văn.

## Kiểm chứng

- Không còn cặp DOI hoặc arXiv ID trùng trong `corpus.csv` (script kiểm).
- Mọi dòng `exclude` có mã lý do.
- Số trong `prisma-counts.json` cộng khớp (script kiểm).

## Rủi ro và hoàn tác

- Gộp nhầm hai bài khác nhau cùng tiêu đề ngắn → bước 4 xem tay.
- Thiên kiến một người → tự đánh giá lại có trễ và ghi hạn chế trong báo cáo.
