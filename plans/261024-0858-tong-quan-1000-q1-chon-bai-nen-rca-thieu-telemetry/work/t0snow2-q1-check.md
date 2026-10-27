# Kiểm tay 30 bản ghi T0 sau snowball vòng 1 (phase 04)

Mẫu: `work/records/t0snow2-q1-sample.csv` (receipt `04-q1-sample-snow-01`, seed 20261024, nguồn `work/records/t0snow2-t0.csv`, 967 bản ghi). Cột `sjr_categories` là nguyên chuỗi `Categories` của CSV SJR 2025.

Kết quả đọc tay: 30/30 đúng.

- Q-1/Q-4: cả 30 dòng có SJR `Type = journal`, và mỗi dòng có ít nhất một category CS của §3 mang `(Q1)` trong chuỗi gốc.
- Q-5: `publication_date` từ 2020-05-08 đến 2026-09-05.
- Q-6: cả 30 là article.
- `q1_weak`: 3 bản ghi IEEE Access (dòng 3, 13, 23) gắn 1. 27 dòng còn lại gắn 0. Cả hai nhóm đều đúng quy tắc.

Giới hạn: 7 bản ghi có `publication_date` = YYYY-01-01 (ngày danh nghĩa của OpenAlex). Điều này không ảnh hưởng cổng năm.
