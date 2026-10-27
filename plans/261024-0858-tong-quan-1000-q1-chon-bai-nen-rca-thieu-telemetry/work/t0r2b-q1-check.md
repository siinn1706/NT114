# Kiểm tay 30 bản ghi T0 sau §10 (snowball vòng 2 và truy vấn đồng nghĩa, phase 04)

Mẫu: `work/records/t0r2b-q1-sample.csv` (receipt `04-q1-sample-r2-01`, seed 20261024, nguồn `work/records/t0r2b-t0.csv`, 1.085 bản ghi). Cột `sjr_categories` là nguyên chuỗi `Categories` của CSV SJR 2025.

Kết quả đọc tay: 30/30 đúng.

- Q-1/Q-4: cả 30 dòng có SJR `Type = journal`. Mỗi dòng có ít nhất một category CS của §3 mang `(Q1)`. Dòng 2 (Journal of Manufacturing Systems) và dòng 26 (Mechanical Systems and Signal Processing) đạt nhờ Hardware and Architecture (Q1) và Computer Science Applications (Q1). Cổng Q1 đúng, còn chủ đề do §4/§6 xử lý.
- Q-5: `publication_date` từ 2020-01-01 đến 2026-10-15.
- Q-6: cả 30 là article.
- `q1_weak`: 4 bản ghi IEEE Access (dòng 3, 4, 8, 21) gắn 1, 26 dòng còn lại gắn 0, đúng quy tắc.

Giới hạn: 7 bản ghi có `publication_date` = YYYY-01-01, là ngày danh nghĩa của OpenAlex. Dòng 4 có ngày 2020-01-01, nằm đúng mốc dưới của Q-5, và metadata không cho biết năm thật của bài.
