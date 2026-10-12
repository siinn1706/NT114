# Phase 05 — Thực nghiệm đầy đủ, ablation, chuyển giao, thống kê (RQ4)

## Việc làm
1. Chạy cấu hình cuối trên RE2-OB, RE2-SS, RE2-TT; 3 fold theo lần lặp; gộp và tách từng hệ thống.
2. **Chuyển giao chéo hệ thống:** kho truy hồi và bộ hiệu chỉnh fit trên một hệ thống, kiểm trên hai hệ thống còn lại.
3. **Chi phí:** ngân sách token 1k/2k/4k/8k; độ trễ; số lần gọi LLM; đường cost–accuracy.
4. **Ablation tổng:** bỏ từng nguồn telemetry; bỏ retrieval; bỏ kiểm cạnh; bỏ hiệu chỉnh; đổi mô hình (≥2 họ open-weight 7–8B).
5. **Phân tích lỗi** theo loại: thiếu dữ liệu, lan truyền, nén làm mất bằng chứng, truy hồi sai, LLM suy luận sai
   (Proposal_v2 mục 6.6), thêm cột "theo hệ thống" và "theo loại lỗi".
6. (Tùy chọn) Demo trên cụm Kubernetes với Chaos Mesh để minh họa, không dùng làm số chính.

## Kiểm tra
- Mọi số trong bài sinh từ script có trong repo và MLflow run id; không sửa tay.
- So chênh lệch với CI trước khi viết "cao hơn".
- Khẳng định tổng quát phải đúng ở cả ba hệ thống; hệ thống nào ngược thì ghi rõ.
