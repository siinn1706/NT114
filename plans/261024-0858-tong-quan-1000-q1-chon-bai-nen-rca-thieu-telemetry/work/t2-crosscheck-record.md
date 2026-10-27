# Kiểm chéo và kiểm locator T2 (phase 07)

- Mẫu kiểm chéo: 6/34 bài có F (≥ 10%, tối thiểu 5), gồm đủ hạng 9–12 của T2 và CausalOpsBench (F cao nhưng cổng T2 = 0). Reader `r2` chấm mù, không xem điểm `r1`. Kết quả nằm ở `work/appraisal/xcheck-r2.csv`.
- Chênh lệch tổng F giữa r1 và r2:
  - RCRank (W4410538768): r1 21, r2 18, lệch 3, nên phải phân xử. Kết quả phân xử: F1 = 2 vì đầu ra chỉ xếp loại nguyên nhân cho từng truy vấn chậm, không định vị thành phần. F3_compute = 3 theo cùng quy ước với các bài dùng mô hình nhỏ (BERT-base, QueryFormer) chạy được trong 12 GB. Tổng sau phân xử là 21; chi tiết ở `work/appraisal/overrides-a01.csv`.
  - Bài phân tán edge (W7131638922): lệch +2 ở F2. Giữ điểm r1.
  - QROOT (W7202368991): lệch −1 ở F6. Giữ điểm r1.
  - RPCA (W3113082031): không lệch.
  - BARO tăng cường (W4413640138): lệch +2 (F1 +1, F2 +1). Giữ điểm r1.
  - CausalOpsBench (W7167605064): lệch +2 (F1 +1, F3 +1). Cả hai reader đều chấm cổng T2 = 0 vì đóng góp chính là benchmark, nên bài nằm ngoài T2.
- Các ô lệch nhưng dưới ngưỡng 3 được đưa vào phân tích độ nhạy ±1 ở phase 08 (`work/sensitivity-t2-pool.csv`).
- Kiểm locator: lấy ngẫu nhiên 20 locator trong các batch F và grep trong text đã băm. Cả 20/20 trỏ tới đoạn có thật: script tự kiểm khớp 7, 13 còn lại lệch định dạng và được grep tay xác nhận.
- Ghi chú phiên bản: ledger ghi RCLAgent (W7165616276) là `reuse`, nhưng text thực đọc là bản arXiv v1. Card T3 ghi đúng phiên bản đã đọc.
