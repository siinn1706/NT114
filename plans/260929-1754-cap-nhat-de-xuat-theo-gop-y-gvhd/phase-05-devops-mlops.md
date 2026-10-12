---
phase: 5
title: "Quy trình DevOps/MLOps"
status: completed
effort: 1.5h
---

# Phase 05 — Quy trình DevOps/MLOps

## Góp ý gốc
> Hướng mở rộng đề tài: tích hợp quy trình DevOps và MLOps để hoàn thiện giải pháp AIOps toàn diện. Ví dụ: áp dụng MLOps
> (MLflow, DVC) để theo dõi lịch sử thử nghiệm, quản lý phiên bản dữ liệu/mô hình và đóng gói API suy luận; kết hợp DevOps
> (Docker, GitHub Actions) để tự động hóa pipeline kiểm thử và triển khai giải pháp phân tích sự cố lên môi trường Kubernetes thực tế.

## Quyết định
Theo tên đề tài, K8s thuộc phần lõi. Làm trong đồ án: MLflow, DVC, Docker, GitHub Actions, và triển khai lên K8s cục bộ (kind/minikube) để demo end-to-end. Hướng mở rộng: cluster production-like, CD tự động, continuous evaluation.

## Nội dung cần đưa vào

**5.3 Quy trình MLOps/DevOps (làm trong đồ án)**
- **DVC**: quản lý phiên bản dữ liệu RE2-OB gốc, incident card đã xử lý và chỉ mục retrieval. Dùng `dvc.yaml` để định nghĩa các stage
  `preprocess → build_index → infer → evaluate`, nên chạy `dvc repro` là tái lập được toàn bộ thí nghiệm.
- **MLflow Tracking**: mỗi lần chạy ghi lại params (mô hình, phiên bản prompt, cấu hình nén W/K/N/M và ngân sách token, cấu hình fusion
  α hoặc k của RRF, có dùng rerank hay không), metrics (AC@1/3/5, Avg@5, MRR, MAP, nDCG@5, điểm giải thích, số token, latency) và artifacts
  (prediction JSON, confusion matrix). Dùng MLflow Model Registry cho adapter LoRA nếu có fine-tune.
- **API suy luận**: FastAPI với endpoint `POST /analyze`, nhận telemetry của một sự cố và trả về JSON {services[rank, score], fault, explain, evidence_ids}. Đóng gói bằng Docker.
- **GitHub Actions CI**: chạy lint và unit test cho bước tiền xử lý và các hàm tính metric; chạy regression eval trên một tập nhỏ khoảng 5 sự cố
  với ngưỡng AC@3 không được giảm; build Docker image và push lên GHCR khi merge vào main.

**Triển khai trên K8s (lõi)**
- Cluster kind/minikube chạy Online Boutique, cùng Prometheus, Loki và Jaeger/OpenTelemetry Collector.
- Detector và Analyzer (phase 08) triển khai bằng manifest hoặc Helm chart. LLM open-weight chạy ngoài cluster nếu máy không có GPU; Analyzer gọi endpoint Ollama hoặc vLLM qua biến cấu hình.
- Dùng Chaos Mesh tiêm 2–3 loại lỗi (CPU, memory, network delay) để demo luồng: phát hiện → phân tích → kết quả.

**9. Hướng mở rộng (mục mới)**
- Cluster production-like (nhiều node hoặc cloud), workflow CD tự động triển khai lên K8s, Analyzer kích hoạt từ Alertmanager.
- Mở rộng sang hệ thống hoặc dataset khác trong RCAEval (Sock Shop, Train Ticket).
- Theo dõi drift và đánh giá lại định kỳ trên sự cố mới (continuous evaluation).

## Các bước
1. Viết mục 5.3, khoảng 0,75–1 trang, có một sơ đồ: DVC pipeline → MLflow → Docker → CI → K8s.
2. Viết mục 9 Hướng mở rộng.
3. Cập nhật mục 7 Kết quả dự kiến: thêm "repo có pipeline tái lập (DVC), lịch sử thí nghiệm (MLflow), API suy luận đóng gói Docker, CI tự động".

## Kiểm tra
- Tách rõ phần cam kết làm (gồm K8s cục bộ) và phần mở rộng. Các params/metrics ghi vào MLflow khớp với phase 01–04.

## Rủi ro
- Chạy LLM trong CI tốn chi phí. Regression eval trong CI có thể dùng output đã cache hoặc mô hình nhỏ, và phải ghi rõ lựa chọn này.
