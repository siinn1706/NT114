# Kiểm tay 30 bản ghi T0 đầy đủ (seed + search, phase 04)

Mẫu: `work/t0full2-q1-sample.csv` (receipt `04-q1-sample-full-01`, seed 20261024, nguồn `work/records/t0full2-t0.csv`, 863 bản ghi). Cột `sjr_categories` lấy nguyên chuỗi `Categories` của CSV SJR 2025.

Kết quả đọc tay: 30/30 đúng.

- Q-1/Q-4: cả 30 dòng SJR `Type = journal` và có ít nhất một category CS của §3 mang `(Q1)`. Dòng 14 (Journal of Reliable Intelligent Environments) đạt nhờ Computer Networks and Communications (Q1), các category CS khác của tạp chí này là Q2.
- Q-5: `publication_date` từ 2020-05-12 đến 2026-07-15.
- Q-6: 30 article.
- `q1_weak`: không bản ghi nào trong mẫu thuộc IEEE Access hoặc Scientific Reports; cả 30 đều gắn 0, đúng quy tắc.

Giới hạn: 4 bản ghi có `publication_date` = YYYY-01-01 (ngày danh nghĩa của OpenAlex), không ảnh hưởng cổng năm.
