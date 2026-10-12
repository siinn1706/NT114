---
phase: 7
title: "Điền Đề cương chi tiết NT114"
status: completed
effort: 4.5h
---

# Phase 07 — Điền Đề cương chi tiết NT114

## Mục tiêu
Điền ba phần còn trống của `DeCuongChiTiet_NT114.R11-MinhTri-VanNam.docx` dựa trên Proposal_v2: Nội dung đề tài,
Kế hoạch thực hiện, Tài liệu tham khảo (IEEE).

## Tệp
- Đọc: `D:/NT114/Proposal_v2.docx`, `D:/NT114/DeCuongChiTiet_NT114.R11-MinhTri-VanNam.docx`
- Ghi: `D:/NT114/DeCuongChiTiet_NT114.R11-MinhTri-VanNam_v2.docx`

## Nội dung

**1. Nội dung đề tài**, theo 5 ý mà mẫu yêu cầu:
- Mục tiêu: tóm tắt mục 2 của Proposal.
- Phạm vi: phát hiện sự cố → định vị dịch vụ gốc và phân loại lỗi → giải thích có dẫn bằng chứng. Đánh giá định lượng trên RE2-OB (RCAEval); demo end-to-end trên K8s cục bộ. Không tự động khắc phục.
- Đối tượng: telemetry (metric, log, trace), tài liệu vận hành, LLM.
- Phương pháp: phát hiện bằng z-score/Isolation Forest → nén telemetry → Hybrid Retrieval (BM25 + dense, RRF) → LLM open-weight sinh kết quả có cấu trúc → đánh giá (AC@k, MRR, MAP; giải thích đa tầng) → MLOps (DVC, MLflow, Docker, GitHub Actions) và triển khai trên K8s.
- Kết quả mong đợi: lấy từ mục 7 của Proposal_v2.

**2. Kế hoạch và phân công.** Thời gian thực hiện là 29/09/2026 – 20/10/2026, khoảng 3 tuần. Điền vào ô "Thời gian thực hiện".
Thứ tự ưu tiên: phần đánh giá offline trên RE2-OB phải xong trước, vì đây là mốc tối thiểu. Các mục có dấu (*) có thể cắt nếu trễ.
Phân công dưới đây là gợi ý, cần nhóm xác nhận.

| Thời gian | Công việc | Trí | Nam | Sản phẩm |
|---|---|---|---|---|
| 29/09 – 05/10 | Khảo sát tài liệu, phân tích RE2-OB; pipeline tiền xử lý và nén (incident card); dựng DVC | ✓ | | incident card cho 90 sự cố |
| 29/09 – 05/10 | Bộ phát hiện (z-score, Isolation Forest); chạy baseline RCAEval; bộ tính metric | | ✓ | kết quả phát hiện và baseline |
| 29/09 – 05/10 | Dựng kind/minikube với Online Boutique, Prometheus, Loki, Jaeger | | ✓ | cluster chạy được |
| 06/10 – 12/10 | Hybrid Retrieval (BM25, dense, RRF/weighted), corpus và runbook, ablation retrieval | | ✓ | bảng Recall/nDCG |
| 06/10 – 12/10 | LLM open-weight: prompt, output có cấu trúc; tích hợp MLflow; thí nghiệm localization và ablation nén | ✓ | | bảng AC@k, MRR, MAP |
| 13/10 – 17/10 | Đánh giá giải thích: tầng 1 judge open-weight, gửi các ca cần duyệt cho GVHD và chuyên gia | ✓ | | điểm rubric, κ |
| 13/10 – 17/10 | FastAPI, Docker, GitHub Actions; triển khai lên K8s và demo bằng Chaos Mesh (*) | | ✓ | image, manifest, demo |
| 13/10 – 17/10 | Fine-tune LoRA nhẹ (*) | ✓ | | adapter và kết quả so sánh |
| 18/10 – 20/10 | Phân tích lỗi, kiểm định bootstrap, viết báo cáo và slide | ✓ | ✓ | báo cáo, slide |

Kết quả chấm của chuyên gia ở tầng 2 phụ thuộc vào thời gian của GVHD. Cần gửi các ca trước 15/10 để kịp đưa vào báo cáo.

**3. Tài liệu tham khảo (IEEE).** Gồm khoảng 10–15 mục, mỗi mục **phải được kiểm chứng** (DOI, arXiv hoặc trang của hội nghị)
bằng skill `nature-ref-verifier` hoặc `nature-academic-search`. Nhóm tài liệu cần có:
- RCAEval, bộ benchmark và dataset.
- Các phương pháp RCA trên microservice dùng làm baseline (BARO, RCD, CIRCA…).
- LLM cho RCA và AIOps (ví dụ RCACopilot, các khảo sát về LLM trong AIOps).
- BM25 (Robertson & Zaragoza), RRF (Cormack et al., SIGIR 2009), Dense Passage Retrieval, RAG (Lewis et al., 2020).
- Drain, phương pháp trích template log (He et al., ICWS 2017).
- LLM-as-a-Judge (Zheng et al., 2023).
- Isolation Forest (Liu et al., ICDM 2008).
- Tài liệu chính thức của MLflow, DVC, Online Boutique, Chaos Mesh và Kubernetes (IEEE dạng online).

## Các bước
1. Sao lưu, sau đó điền 3 phần vào đúng ô của mẫu, giữ nguyên style.
2. Tra cứu và kiểm chứng từng tài liệu tham khảo, định dạng theo IEEE, và đối chiếu các trích dẫn [n] trong phần Nội dung.
3. Điền thời gian thực hiện 29/09/2026 – 20/10/2026. Để trống ô chữ ký và ngày ký.
4. Chuyển sang PDF và xem từng trang.

## Kiểm tra
- 100% tài liệu tham khảo có DOI hoặc URL đã được xác minh. Không có trích dẫn [n] nào bị treo.
- Phạm vi trong đề cương khớp với Proposal_v2 và bảng kế hoạch nằm trong khoảng 29/09–20/10.

## Rủi ro
- 3 tuần là rất ngắn cho phạm vi này. Nếu trễ thì cắt các mục (*) trước, và ghi chúng vào phần hướng mở rộng thay vì bỏ hẳn.
