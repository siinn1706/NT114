---
title: "Cập nhật đề xuất & đề cương NT114 theo góp ý GVHD"
description: "Bổ sung 5 nội dung GVHD góp ý và mở rộng phạm vi theo tên đề tài (phát hiện sự cố + RCA trên Kubernetes) vào Proposal.docx, rồi điền Đề cương chi tiết NT114."
status: completed
priority: P1
effort: 20h
branch: n/a (không phải git repo)
tags: [docs, proposal, aiops, rca, rag, mlops, kubernetes]
blockedBy: []
blocks: []
created: 2026-09-29
---

# Cập nhật đề xuất & đề cương NT114 theo góp ý GVHD

## Outcome

Proposal.docx trả lời được cụ thể cả 5 góp ý của ThS. Lê Anh Tuấn và có phạm vi khớp với tên đề cương:
**phát hiện sự cố và phân tích nguyên nhân gốc cho microservices trên Kubernetes, dùng truy xuất lai và LLM**.
Sau đó nội dung đã chốt được dùng để điền `DeCuongChiTiet_NT114.R11-MinhTri-VanNam.docx`, gồm: nội dung đề tài,
kế hoạch và phân công, tài liệu tham khảo theo chuẩn IEEE.

## Quyết định đã chốt (từ người dùng, 2026-09-29)

| Chủ đề | Quyết định |
|---|---|
| Tài liệu đích | Sửa cả hai: Proposal trước, Đề cương sau (dùng lại nội dung Proposal) |
| Tên đề tài và phạm vi | Giữ tên đề cương. Mở rộng Proposal theo tên: thêm **phát hiện sự cố** (có lỗi hay `none`) vào lõi, RCA gồm dịch vụ gốc, loại lỗi và giải thích, và **hệ thống chạy trên Kubernetes** |
| DevOps/MLOps | Lõi: MLflow, DVC, Docker, GitHub Actions, và triển khai hệ thống phân tích cùng Online Boutique lên cluster K8s cục bộ (kind/minikube) để demo end-to-end. Hướng mở rộng: cluster production-like, CD tự động kích hoạt từ Alertmanager, continuous evaluation. Quyết định này thay cho lựa chọn trước đó (K8s chỉ là hướng mở rộng), vì người dùng đã yêu cầu mở rộng theo tên đề tài |
| Mô hình | Chỉ dùng **open-weight**, cả mô hình sinh lẫn judge, chạy trên Kaggle/Colab hoặc máy cá nhân. Không dùng API trả phí |
| Tầng 2 đánh giá giải thích | GVHD và 1–2 người có kinh nghiệm vận hành, chấm theo cùng rubric |
| Thời gian thực hiện | Tạm tính 29/09/2026 – 20/10/2026 (khoảng 3 tuần) |

## Ánh xạ góp ý → phase → mục trong Proposal

| # | Góp ý / yêu cầu | Phase | Mục Proposal bị ảnh hưởng |
|---|---|---|---|
| 1 | Chiến lược nén/tổng hợp/biến đổi telemetry | [01](phase-01-telemetry-compression.md) | 4.1, 5.1 |
| 2 | Kỹ thuật và thuật toán Hybrid Retrieval | [02](phase-02-hybrid-retrieval.md) | 5.2, 6 |
| 3 | Độ đo phát hiện và service localization: Top-k, MRR, MAP | [03](phase-03-localization-metrics.md) | 4.2, 6 |
| 4 | Khung đánh giá giải thích đa tầng | [04](phase-04-explanation-eval-framework.md) | 4.2 (Explain), 6 |
| 5 | DevOps/MLOps và K8s | [05](phase-05-devops-mlops.md) | 5.3, 7, 9 |
| — | Mở rộng theo tên đề tài: phát hiện sự cố và kiến trúc hệ thống trên K8s | [08](phase-08-detection-and-k8s-system.md) | 1, 2, 3, 5.0 |
| — | Ghép vào Proposal.docx | [06](phase-06-update-proposal-docx.md) | Toàn văn |
| — | Điền Đề cương NT114 | [07](phase-07-fill-de-cuong-nt114.md) | Đề cương |

## Phases

| Phase | Tên | Trạng thái | Effort | Phụ thuộc |
|---|---|---|---|---|
| 08 | Phát hiện sự cố và kiến trúc hệ thống trên K8s | completed | 2.5h | — |
| 01 | Chiến lược nén và biến đổi telemetry | completed | 2h | 08 (cửa sổ phát hiện) |
| 02 | Đặc tả Hybrid Retrieval | completed | 2h | 01 (định dạng incident card) |
| 03 | Bộ độ đo phát hiện và localization | completed | 1h | 08 |
| 04 | Khung đánh giá giải thích đa tầng | completed | 2h | 03 |
| 05 | Quy trình DevOps/MLOps và K8s | completed | 2h | 01–04, 08 |
| 06 | Cập nhật Proposal.docx | completed | 3.5h | 01–05, 08 |
| 07 | Điền Đề cương chi tiết NT114 | completed | 5h | 06 |

Phase 08 được đánh số sau cùng vì thêm vào sau, nhưng nên làm đầu tiên vì nó định nghĩa kiến trúc tổng thể mà các
phase khác gắn vào. Các phase 02, 03 và 05 có thể soạn song song sau khi xong 08 và 01. Phase 06 và 07 sửa file .docx
nên phải làm tuần tự.

## Acceptance criteria

- [x] Mỗi góp ý có một mục riêng trong Proposal, trả lời bằng kỹ thuật, tham số và công thức cụ thể, không chỉ liệt kê tên công nghệ.
- [x] Phạm vi Proposal khớp tên đề cương: có đủ phát hiện sự cố, RCA (dịch vụ gốc, loại lỗi, giải thích) và hệ thống chạy trên K8s.
- [x] Mục 6 (Đánh giá) có độ đo phát hiện (precision, recall, F1, FPR, thời gian phát hiện) và công thức AC@k (k=1,3,5), Avg@5, MRR, MAP, kèm cách xử lý trường hợp chỉ có 1 dịch vụ gốc (khi đó MAP = MRR).
- [x] Hybrid Retrieval nêu rõ BM25, dense embedding, thuật toán fusion (RRF và weighted sum), reranker tùy chọn và các ablation để so sánh.
- [x] Có ngân sách token cụ thể và tỷ lệ nén đo được cho đầu vào LLM.
- [x] Khung đánh giá giải thích có rubric kèm trọng số, ngưỡng chuyển xuống tầng 2, cách đo độ đồng thuận, và judge là mô hình open-weight khác họ với mô hình sinh.
- [x] DevOps/MLOps tách rõ phần làm trong đồ án (gồm K8s cục bộ) và phần hướng mở rộng.
- [x] Đề cương NT114 được điền đủ 3 phần, với kế hoạch trong khoảng 29/09–20/10/2026. Tài liệu tham khảo theo IEEE và từng mục đã được kiểm chứng là có thật.
- [x] File gốc được giữ nguyên, bản sửa lưu thành `_v2.docx`. Mở bằng Word/LibreOffice không lỗi định dạng.

## Rủi ro chung

- **Phạm vi lớn so với 3 tuần.** Phạm vi đã mở rộng (phát hiện, RCA, retrieval, đánh giá hai tầng, MLOps, K8s) trong khi chỉ có khoảng 22 ngày. Kế hoạch ở phase 07 xếp theo thứ tự ưu tiên: lõi đánh giá offline trên RE2-OB làm trước; demo K8s và fine-tune đặt sau và là phần có thể cắt nếu trễ. Đề cương nên ghi rõ các mốc tối thiểu.
- **Tài nguyên cho mô hình open-weight.** GPU Kaggle/Colab có giới hạn thời gian dùng, nên chọn mô hình khoảng 7–8B lượng tử hóa 4-bit. Judge phải khác họ với mô hình sinh, ví dụ sinh bằng Qwen2.5-7B-Instruct và chấm bằng Llama-3.1-8B-Instruct; tên mô hình cụ thể chốt khi chạy thử. Trên K8s cục bộ có thể không chạy được LLM, khi đó service phân tích gọi endpoint suy luận bên ngoài (Ollama hoặc vLLM trên máy có GPU).
- **Rò rỉ nhãn khi retrieval dùng incident lịch sử.** Phải chia tập dữ liệu theo lần lặp (repetition), không dùng chung sự cố đang đánh giá. Chi tiết ở phase 02.
- **Tài liệu tham khảo bịa.** Mọi trích dẫn phải được kiểm bằng DOI/arXiv trước khi đưa vào, xem phase 07.

## Câu hỏi còn mở

1. Khoảng 29/09–20/10 là thời gian của cả đồ án hay chỉ của giai đoạn đầu (đề cương và prototype)? Nếu là cả đồ án, nên xác nhận với GVHD mức tối thiểu cần đạt, vì phạm vi đầy đủ rất dày cho 3 tuần.
