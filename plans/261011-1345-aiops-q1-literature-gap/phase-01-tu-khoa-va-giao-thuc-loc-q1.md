# Giai đoạn 01 – Rút từ khóa, viết truy vấn, giao thức lọc Q1

Trạng thái: hoàn thành 11/10/2026, biên nhận `work/keywords.csv` `work/queries.csv` `work/q1-protocol.md` · Thực thi: nckh-cook (dùng nckh-literature) · Quay về [plan](plan.md)

Biên nhận: `work/keywords.csv` `work/queries.csv` `work/q1-protocol.md`

## Yêu cầu

- Rút từ khóa từ **toàn bộ Proposal**, không chỉ tên đề tài: bài toán, dữ liệu, phương pháp, đánh giá, MLOps.
- Mỗi từ khóa ghi: mã nhóm, thuật ngữ tiếng Anh, từ đồng nghĩa/biến thể, đoạn Proposal nguồn (Pxxxx).
- Viết truy vấn theo cú pháp của từng nguồn; ghi lại nguyên văn.
- Viết giao thức lọc Q1 theo D1–D7 trong [plan](plan.md) và cố định trước khi tìm.

Nhóm từ khóa hạt giống (Phase 01 hoàn chỉnh và có thể sửa):

| Nhóm | Ý | Thuật ngữ hạt giống | Nguồn Proposal |
|---|---|---|---|
| C1 | Bối cảnh hệ thống | microservice, cloud-native, Kubernetes, container, cloud service, distributed system | P0003, P0008 |
| C2 | Telemetry | metric, log, trace, multimodal / multi-source telemetry, observability, OpenTelemetry | P0012, P0030–P0033 |
| C3 | Phát hiện | anomaly detection, incident detection, failure detection, Isolation Forest | P0013, P0049–P0052 |
| C4 | RCA | root cause analysis / localization, fault localization, failure diagnosis, fault type classification | P0016, P0022 |
| C5 | LLM | large language model, LLM agent, AIOps, incident management, in-context learning, LoRA fine-tuning | P0009, P0076 |
| C6 | Truy hồi | retrieval-augmented generation, hybrid retrieval, BM25, dense retrieval, rank fusion, case-based reasoning, historical incident, runbook, knowledge base | P0015, P0064–P0074 |
| C7 | Nén/biểu diễn | telemetry summarization, log parsing, log template, context compression, token budget, feature selection | P0014, P0054–P0062 |
| C8 | Giải thích/tin cậy | explainability, interpretability, evidence-grounded, faithfulness, hallucination, LLM-as-a-judge, uncertainty, calibration | P0017, P0119–P0143 |
| C9 | Lan truyền | fault propagation, call graph, service dependency graph, causal inference, causal discovery | P0057, note 29/09 |
| C10 | Vận hành/đánh giá | MLOps, benchmark, chaos engineering, fault injection, reproducibility | P0018, P0078–P0082 |

Mẫu truy vấn: `(C1) AND (C3 OR C4) AND (Cx)` với x ∈ {2, 5, 6, 7, 8, 9}; thêm `(C5) AND (C4)` và `(C6) AND (C4 OR C5)` không ràng buộc C1 để bắt bài ở bối cảnh gần (cloud, mạng, log).

## Tệp

- Đọc: [proposal-paragraphs.txt](source-review/proposal-paragraphs.txt), [báo cáo gap 05/10](../reports/research-261005-2138-q1-research-gap.md) mục 1–2.
- Tạo: `work/keywords.csv`, `work/queries.csv`, `work/sjr-<năm>.csv`, `work/sjr-<năm>.sha256`, `work/q1-protocol.md`.

## Các bước

1. Đọc lại Proposal theo mã đoạn, liệt kê mọi khái niệm kỹ thuật; gộp vào C1–C10, thêm nhóm mới nếu cần.
2. Với mỗi thuật ngữ, thêm biến thể (số ít/nhiều, gạch nối, viết tắt: RCA, AD, RAG, LLM).
3. Viết `queries.csv`: id, nguồn (OpenAlex, Scopus nếu có quyền qua trường, IEEE Xplore, ACM DL, ScienceDirect, Semantic Scholar), chuỗi nguyên văn, bộ lọc (journal, article/review, 2020–2026).
4. Tải bảng SJR từ scimagojr.com/journalrank.php (nút Download data), xác định năm mới nhất có trên site, lưu CSV và sha256, ghi ngày tải.
5. Viết `q1-protocol.md`: định nghĩa Q1 theo D1, cách khớp ISSN (cả print và electronic, chuẩn hóa bỏ gạch), xử lý tạp chí đổi tên, D3/D4 cờ và loại, D7 năm.
6. Chạy thử 3 truy vấn để đo số kết quả; chỉnh nếu quá rộng (>3.000) hoặc quá hẹp (<20).

## Kiểm tra

- Mỗi dòng `keywords.csv` có mã đoạn Proposal hoặc ghi chú GVHD.
- Mọi nhóm C1–C10 xuất hiện trong ít nhất một truy vấn.
- sha256 của tệp SJR tính lại khớp với tệp `.sha256`.
- Kiểm 5 tạp chí đã biết (ví dụ IEEE TSC, ACM TOSEM, JSS, IEEE TNSM, một MDPI) ra đúng quartile/cờ theo giao thức.

## Rủi ro / hoàn tác

- Site SJR chặn tải tự động: tải thủ công qua trình duyệt, ghi lại cách tải. Không dùng bản SJR chép lại từ nguồn thứ ba.
- Từ khóa quá rộng làm nổ số kết quả: siết bằng bắt buộc C1 hoặc C4.
- Hoàn tác: xóa `work/` của giai đoạn này; không chạm vào Proposal hay báo cáo cũ.
