# Kiểm tay 30 bản ghi T0 seed (phase 04)

Mẫu: `work/t0seed4-q1-sample.csv` (receipt `04-q1-sample-seed-01`, seed 20261024, nguồn `work/records/t0seed4-t0.csv`). Cột `sjr_categories` lấy nguyên chuỗi `Categories` của CSV SJR 2025 (hash đóng băng), không qua bảng đã parse của cổng.

Kết quả đọc tay: 30/30 đúng.

- Q-1/Q-4: cả 30 dòng SJR `Type = journal` và có ít nhất một category CS trong danh sách §3 mang `(Q1)`; danh sách category CS của cổng trùng với chuỗi gốc.
- Q-5: `publication_date` từ 2020-04-01 đến 2026-09-23, nằm trong 2020-01-01…2026-10-24.
- Q-6: 28 article, 2 review.
- `q1_weak`: 5 bài IEEE Access đều gắn 1; không bài nào khác bị gắn.

Giới hạn: 5 bản ghi IEEE Access có `publication_date` = 2026-01-01 (ngày danh nghĩa của OpenAlex cho số tạp chí), không ảnh hưởng cổng năm.
