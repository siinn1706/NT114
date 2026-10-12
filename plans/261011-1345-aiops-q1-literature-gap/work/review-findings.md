# Rà soát báo cáo cuối (12/10/2026)

Rà soát bằng script do chính người viết báo cáo chạy. **Chưa phải rà soát độc lập.** Phase 06 yêu cầu một người khác
(thành viên nhóm hoặc reviewer) đọc lại trước khi gửi GVHD.

## Các kiểm tra đã chạy

| Kiểm tra | Cách | Kết quả |
|---|---|---|
| Số bài mỗi bước PRISMA | So bảng và sơ đồ trong báo cáo với `prisma-counts.json` | Khớp |
| Điểm hướng và độ nhạy | Script so từng ô bảng mục 7 với `direction-ranking.csv` và `sensitivity.csv` | 7/7 hướng khớp |
| Bảng điểm chạy lại | Chạy `score-directions.py` hai lần, so sha256 | Trùng |
| Con số trong `ideas25.csv` | Mỗi số ở cột bằng chứng phải có trong bản ghi `extraction.jsonl` của bài nguồn | Khớp sau khi sửa |
| Thẻ ý tưởng | Bài nguồn có trong `extraction.csv`; có mục Proposal và mã Pxxxx | 32/32 |
| Gap `confirmed` | Mức chắc `full-text`; có truy vấn ở cả OpenAlex (Q1) và arXiv | 3/3 |
| DOI tham khảo | Crossref phân giải; tỷ lệ khớp tiêu đề; ISSN Q1 trong SJR 2025 | 69/69 phân giải, tỷ lệ khớp thấp nhất 0,843 (P69, chỉ khác dấu cách), 69/69 Q1 |
| Tạp chí đích | Tra quartile trong `scimagojr-2025-nckh.csv` | Mọi tạp chí đích đều Q1 |

## Phát hiện và cách xử lý

1. **Hai con số không truy được về phiếu.** Đó là "Top-1 82,4%" của P42 và "Top-1 64%" của P45, lấy từ ghi chú đọc chứ không có trong `extraction.csv`. Đã xóa khỏi `ideas25.csv` và báo cáo, thay bằng vị trí bảng trong bài và ghi chú "giá trị chưa ghi vào phiếu".
2. **Mã hóa ma trận bằng regex sai ở lần chạy đầu**, đã sửa trong script:
   - P18 bị tính là dùng LLM open-weight (Qwen-plus là API).
   - P29 bị tính là có truy hồi (thư viện mẫu bình thường, không phải truy hồi văn bản).
   - P45 bị tính là có độ tin cậy được hiệu chỉnh.
   - P42 bị gán AIOps 2022 thay cho AIOps Challenge.
3. **Chưa sửa được, đã đưa vào mục Hạn chế của báo cáo:**
   - Còn 22 bài chỉ đọc tóm tắt.
   - Chưa tìm Google Scholar/DBLP cho các hội nghị.
   - Toàn bộ do một người chấm.
   - Phiếu P68 và P69 dựng từ bản Just Accepted.
   - P42 có chỗ lệch caption/text.
