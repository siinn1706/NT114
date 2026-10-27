# Rà lệch bản ghi neo, screening search (s1)

Nguồn: `work/screen/search-s1-check.json` (receipt `05-merge-search-s1-01`), tham chiếu là file neo của phiên đầu tiên `anchors-seed-000-s1.csv`.

- Lệch duy nhất: neo W4391951374 (survey, không có abstract) ở 8/11 phiên (`search-001, 003, 004, 005, 006, 007, 008, 009`): `needs-review` → `context-survey`; R1 = 1 không đổi.
- Nguyên nhân: brief của vòng search (do controller viết) thêm quy ước "mọi survey là `context-survey`", va với quy tắc E6 của §6 (thiếu abstract → `needs-review`). Đây là lỗi hướng dẫn, không phải trôi tiêu chí của người chấm; các neo khác và R1 khớp ở cả 11 phiên.
- Xử lý: survey chỉ có tiêu đề được đưa về `needs-review` (E5|E6) trong `work/screen/search-resolution-a01.csv`, để đi qua làn bổ sung abstract như mọi bản ghi E6. Cả `context-survey` và `needs-review` đều không vào xếp hạng T1, nên tập chọn không đổi.
