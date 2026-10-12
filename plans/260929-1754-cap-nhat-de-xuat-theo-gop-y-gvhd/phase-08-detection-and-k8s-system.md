---
phase: 8
title: "Phát hiện sự cố và kiến trúc hệ thống trên K8s"
status: completed
effort: 2.5h
---

# Phase 08 — Phát hiện sự cố và kiến trúc hệ thống trên K8s

## Lý do
Người dùng quyết định giữ tên đề cương: *"Phát triển hệ thống phát hiện sự cố và phân tích nguyên nhân gốc cho microservices
trên Kubernetes sử dụng truy xuất lai và mô hình ngôn ngữ lớn"*. Proposal hiện chỉ làm service localization offline, nên cần
thêm 2 phần: **phát hiện sự cố** và **hệ thống chạy trên K8s**. Phase này làm trước các phase còn lại vì nó định nghĩa kiến trúc tổng thể.

## Nội dung cần đưa vào Proposal

**Sửa mục 1, 2 và 3 (Đặt vấn đề, Mục tiêu, Phạm vi)**
- Đổi tên đề tài trong Proposal cho khớp đề cương.
- Phạm vi gồm 3 bài toán liên tiếp: (1) **phát hiện**, tức cửa sổ thời gian này có sự cố hay không (`none`); (2) **định vị** dịch vụ gốc (xếp hạng) và phân loại loại lỗi; (3) **giải thích** có dẫn bằng chứng. Vẫn không tự động khắc phục.
- Dữ liệu: RE2-OB (RCAEval) dùng cho đánh giá định lượng có nhãn. Online Boutique triển khai trên K8s cục bộ dùng cho demo end-to-end và có thể sinh thêm một ít dữ liệu bằng Chaos Mesh.

**Mục mới 5.0 — Kiến trúc tổng thể.** Có một sơ đồ, gồm các khối:
1. *Lớp dữ liệu*: Online Boutique trên K8s (kind/minikube); telemetry thu qua Prometheus (metric), Loki hoặc file log (log), Jaeger/OpenTelemetry (trace). Chế độ offline đọc trực tiếp RE2-OB.
2. *Detector*: chạy liên tục theo cửa sổ trượt (ví dụ 1 phút, bước 30 giây). Khi phát hiện bất thường thì tạo một "sự cố" và kích hoạt bước phân tích.
3. *Analyzer*: nén telemetry thành incident card (phase 01), gọi Hybrid Retrieval (phase 02), rồi LLM open-weight sinh JSON {services, fault, explain, evidence_ids}.
4. *API và giao diện kết quả*: FastAPI; kết quả xem qua JSON hoặc một trang/dashboard đơn giản.
5. *MLOps*: DVC, MLflow và CI (phase 05).

**Thuật toán phát hiện.** So sánh 2 cách, cả hai đều dùng lại đặc trưng của phase 01:
- *Thống kê* (baseline, rẻ): robust z-score cho các metric chính (latency, error rate, CPU, memory) của từng service. Báo có sự cố khi có ít nhất m đặc trưng vượt ngưỡng |z| > τ trong ít nhất c cửa sổ liên tiếp, để giảm báo động giả. Tham số τ, m, c tinh chỉnh trên tập validation.
- *Học máy không giám sát*: Isolation Forest trên vector đặc trưng của cửa sổ, huấn luyện chỉ trên dữ liệu bình thường.
- LLM **không** dùng cho bước phát hiện, vì chạy liên tục sẽ quá tốn kém. LLM chỉ được gọi khi đã có sự cố, đây là điểm tiết kiệm chi phí cần nêu rõ.
- Dữ liệu đánh giá phát hiện: cửa sổ trước thời điểm tiêm lỗi của RE2-OB là mẫu âm, cửa sổ sau là mẫu dương.

## Các bước
1. Kiểm tra RE2-OB có đủ đoạn dữ liệu bình thường trước khi tiêm lỗi để tạo mẫu âm không, và ghi lại độ dài của đoạn này.
2. Viết lại mục 1, 2 và 3 theo phạm vi mới; viết mục 5.0 có sơ đồ kiến trúc; viết phần thuật toán phát hiện.
3. Đưa độ đo phát hiện vào phase 03 (đã chuyển thành phần lõi).

## Kiểm tra
- Mỗi cụm từ trong tên đề tài (phát hiện, RCA, microservices, K8s, truy xuất lai, LLM) đều có mục tương ứng trong Proposal.

## Rủi ro
- Đoạn dữ liệu bình thường trong RE2-OB có thể ngắn, nên số mẫu âm ít và FPR khó ước lượng chính xác. Nếu vậy thì bổ sung bằng dữ liệu bình thường thu từ cluster K8s cục bộ và ghi rõ đây là hạn chế.
