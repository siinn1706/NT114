# Phase 02 — Chạy khung baseline trên 3 hệ thống (trùng với đồ án NT114)

## Mục tiêu
"Chạy cho được cái khung" (note 29/09): pipeline Proposal_v2 chạy end-to-end, có số baseline thật trên ba ứng dụng và bảng
so sánh — làm nền để đo phần cải thiện của Phase 3–4.

## Việc làm
1. Tải RCAEval RE2 (OB, SS, TT) từ Hugging Face; quản lý bằng DVC; README ghi nguồn và phiên bản dữ liệu.
2. Khảo sát dữ liệu từng hệ thống: số dịch vụ, độ sâu đồ thị gọi, số chuỗi metric, khối lượng log/trace, phân bố loại lỗi.
   Đây là bảng so sánh 3 ứng dụng mà note yêu cầu, và giải thích về sau vì sao một hệ thống khó hơn.
3. Chạy baseline RCAEval có sẵn: BARO, RCD, CIRCA, heuristic max|z|.
4. Dựng pipeline Proposal_v2 tối thiểu: incident card (z-score, Drain3, cạnh trace), pre-ranking top-M, LLM 7–8B một lượt
   không retrieval, rồi có Hybrid Retrieval. Cache toàn bộ output LLM.
5. Đo: AC@1/3/5, Avg@5, MRR, macro-F1 loại lỗi, token, độ trễ; bootstrap CI 95%; độ phủ top-M của pre-ranking.
6. **Phân tích lỗi ban đầu:** với các ca sai, đánh dấu ca nào hệ thống chọn một dịch vụ upstream/downstream của root cause
   thật trên đồ thị gọi. Tỉ lệ này là bằng chứng định lượng cho động cơ của RQ1.
7. Ghi thêm độ tin cậy thô mà LLM nói ra (verbalized) và xác suất token, để Phase 4 có dữ liệu so sánh.

## Kiểm tra
- Số BARO/RCD/CIRCA tái lập gần với số trong bài RCAEval; lệch nhiều thì tìm nguyên nhân trước khi đi tiếp.
- Không rò rỉ nhãn: sự cố đang đánh giá không có trong kho truy hồi (kiểm bằng assert trong code).
- Mọi lần chạy ghi vào MLflow với đủ tham số.

## Đầu ra
Bảng baseline 3 hệ thống × các phương pháp; bảng đặc điểm 3 ứng dụng; tỉ lệ nhầm theo vị trí trên đường lan truyền;
đồ án NT114 nộp được ở mức tối thiểu của Proposal_v2 mục 7.

## Rủi ro
Một số sự cố RE2-SS/TT có thể thiếu log hoặc trace ở vài dịch vụ; ghi rõ và xử lý thống nhất cho mọi phương pháp.
