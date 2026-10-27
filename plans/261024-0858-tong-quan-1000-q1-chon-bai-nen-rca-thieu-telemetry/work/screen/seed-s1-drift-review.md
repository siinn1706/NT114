# Rà lệch bản ghi neo, screening seed (s1)

Nguồn: `work/screen/seed-s1-check.json` (receipt `05-merge-seed-s1-01`).

- Lệch duy nhất: phiên `seed-001`, neo W3183619936 (survey phân tích log tự động), R1 = 2; 6 phiên còn lại và phiên tham chiếu `seed-000` chấm R1 = 1. Quyết định giống nhau ở cả 7 phiên (`context-survey`).
- Đối chiếu mô tả mức §6: abstract là tổng quan phân tích log (nén, parse, phát hiện bất thường, dự báo lỗi, "facilitate diagnosis"); không nêu RCA/định vị ở mức hệ phân tán làm tác vụ chính → R1 = 1 đúng. Giá trị trong bảng gộp lấy từ dòng của batch chứa bản ghi (`seed-000`, R1 = 1).
- Ảnh hưởng: bản ghi là `context-survey`, không vào xếp hạng T1, nên tập chọn không đổi.
- Rà phiên `seed-001`: 23 dòng R1 ≥ 2, đọc lại tiêu đề và điểm; không thấy xu hướng chấm cao có hệ thống (mật độ R1 = 3 cao vì batch chứa nhiều bài RCA microservice). Hai dòng giáp ranh cần chấm kép: W7214070872 (GHA-Agent, R2 = 2 dù tác vụ chính là parse log CI) và W7166559410 (ORACL, tác vụ chính autoscaling). Cả hai được thêm bắt buộc vào mẫu kép.
- Ghi chú quy trình từ báo cáo người chấm: phiên `seed-001` in một phần batch trước khi ghi file neo (người chấm báo đã quyết định neo trước); phiên `seed-003` sửa R5 và trích dẫn của neo W4378194859 trước khi đọc batch, quyết định và R1 không đổi.
