# Giai đoạn 02 – Tìm, lọc Q1, xếp hạng ~100 bài

Trạng thái: hoàn thành 11/10/2026, biên nhận `work/top100.csv` `work/screened.csv` `work/prisma-counts.json` · Thực thi: nckh-cook (dùng nckh-literature) · Phụ thuộc: [01](phase-01-tu-khoa-va-giao-thuc-loc-q1.md) · Quay về [plan](plan.md)

Biên nhận: `work/top100.csv` `work/screened.csv` `work/prisma-counts.json`

## Yêu cầu

- Chạy toàn bộ `queries.csv`, gộp kết quả, bỏ trùng theo DOI (rồi theo tiêu đề chuẩn hóa).
- Lọc Q1 bằng ISSN theo `q1-protocol.md`; áp D3/D4.
- Lọc theo tiêu đề + abstract: bài phải chạm ít nhất **C1 hoặc bối cảnh gần (cloud/mạng/log hệ thống)** và ít nhất **một trong C3/C4**, hoặc là survey trực tiếp về AIOps/RCA/LLM-for-ops.
- Mở rộng bằng snowballing: tham chiếu ngược và trích dẫn xuôi của các survey Q1 và của 12 bài then chốt trong báo cáo 05/10 mục 5.
- Nhập 83 bài của báo cáo 05/10 làm hạt giống; kiểm lại Q1 bằng tệp SJR mới, không thừa hưởng kết quả cũ.
- Xếp hạng và giữ **~100 bài tốt nhất** (cho phép 80–130).

Điểm xếp hạng (ghi từng thành phần trong `top100.csv`):

| Thành phần | Cách tính | Trọng số |
|---|---|---|
| Liên quan (R) | 0–3, chấm tay theo số nhóm C khớp, ưu tiên C4+C5/C6/C8/C9 | 0,45 |
| Ảnh hưởng (I) | trích dẫn/năm kể từ xuất bản, chuẩn hóa theo phân vị trong corpus | 0,20 |
| Mới (N) | 2024–2026 = 1; 2022–2023 = 0,6; 2020–2021 = 0,3 | 0,20 |
| Tạp chí (V) | SJR của tạp chí, chuẩn hóa phân vị; cờ `q1-weak` × 0,5 | 0,15 |

Ngưỡng cứng: R ≥ 2 mới được vào top; survey trực tiếp được giữ bất kể N. Giữ cân bằng cụm: mỗi cụm B1–B6 (theo báo cáo 05/10, có thể thêm cụm mới) có ít nhất 8 bài nếu tồn tại đủ.

## Tệp

- Đọc: `work/queries.csv`, `work/q1-protocol.md`, `work/sjr-<năm>.csv`, [báo cáo gap 05/10](../reports/research-261005-2138-q1-research-gap.md).
- Tạo: `work/raw-hits.csv`, `work/screened.csv` (có cột lý do loại), `work/top100.csv`, `work/prisma-counts.json`, `work/scripts/search-openalex.py`, `work/scripts/q1-filter.py`, `work/scripts/rank-papers.py`.

## Các bước

1. Viết script truy vấn OpenAlex (API miễn phí, có `mailto`), lưu kết quả thô kèm thời điểm chạy; nguồn có giao diện web (IEEE Xplore, ScienceDirect, ACM DL) xuất CSV thủ công.
2. Bỏ trùng; lấy metadata thiếu từ Crossref.
3. Lọc Q1 bằng ISSN; ghi `quartile`, `sjr`, `sjr_year`, cờ.
4. Lọc tiêu đề + abstract, chấm R; ghi lý do loại.
5. Snowballing một vòng từ survey và 12 bài then chốt; các bài mới cũng đi qua bước 3–4.
6. Tính điểm, gán cụm, chọn top ~100 có cân bằng cụm.
7. Ghi `prisma-counts.json` và vẽ sơ đồ đếm trong báo cáo trung gian.

## Kiểm tra

- Chạy lại `q1-filter.py` trên `top100.csv` ra 100% Q1 theo tệp SJR đã băm.
- Không còn DOI trùng.
- Lấy ngẫu nhiên 10 bài bị loại ở bước 4: lý do loại đúng khi đọc lại abstract.
- 12 bài then chốt của báo cáo 05/10: hoặc có trong top, hoặc có lý do loại rõ (ví dụ không còn Q1).
- Tổng các ô PRISMA cộng khớp.

## Rủi ro / hoàn tác

- API giới hạn tốc độ: thêm thời gian chờ, cache kết quả thô, không chạy lại khi không cần.
- Abstract thiếu (OpenAlex không có): lấy từ trang nhà xuất bản; nếu vẫn thiếu, chấm R theo tiêu đề và gắn cờ `no-abstract`.
- Điểm R chủ quan: hai thành viên chấm độc lập 20 bài, ghi tỉ lệ đồng thuận; lệch nhiều thì sửa hướng dẫn chấm.
- Hoàn tác: các tệp CSV đều sinh lại được từ kết quả thô + script.
