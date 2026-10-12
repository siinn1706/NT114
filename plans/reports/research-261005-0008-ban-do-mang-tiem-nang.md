# Bản đồ mảng tiềm năng cho bài NCKH hướng Q1: RCA microservices bằng LLM

Ngày: 2026-10-05. Đầu vào: `Proposal_v2.docx`, `note/note-29-9.txt`, tìm kiếm web nhanh (chưa đọc toàn văn).

> **Mức chắc:** các công trình 2026 dưới đây mới được thấy qua tiêu đề và tóm tắt trên kết quả tìm kiếm. Theo quy chuẩn
> NCKH mục 14, chưa được trích vào bài cho tới khi đã đọc toàn văn và kiểm metadata (Crossref/OpenAlex). Danh sách này
> là chỉ đường, không phải nguồn chuẩn.

## 1. Đề tài hiện tại đứng ở đâu

Proposal_v2 là một pipeline kỹ thuật tốt cho đồ án NT114: Detector (z-score, Isolation Forest) → nén telemetry thành
incident card ~4k token → Hybrid Retrieval (BM25 + bge-m3, RRF) → LLM 7–8B open-weight → JSON (dịch vụ xếp hạng, loại lỗi,
giải thích có `evidence_ids`) → đánh giá hai tầng. Dữ liệu: RE2-OB (90 sự cố, 1 hệ thống).

Với một bài Q1, pipeline này **chưa có điểm mới đủ mạnh**, vì từng khối đã có tiền lệ: RCACopilot (EuroSys'24) đã dùng
LLM + sự cố lịch sử; Hybrid BM25 + dense + RRF là kỹ thuật IR chuẩn; incident card gần với các "diagnostic bundle" của
nhiều bài 2026. Reviewer Q1 sẽ hỏi: "đóng góp khoa học là gì ngoài việc ghép các khối?". Ngoài ra chỉ một hệ thống,
90 sự cố là quá hẹp để khẳng định tổng quát.

## 2. Ghi chú buổi 29/09 nói gì (đọc thành yêu cầu nghiên cứu)

| Ghi chú | Diễn giải thành yêu cầu |
|---|---|
| "ít nhất 2-3 ứng dụng để kiểm tra kỹ hơn → bảng so sánh" | Đánh giá trên ≥3 hệ thống (Online Boutique, Sock Shop, Train Ticket — cả ba có trong RCAEval RE2) và có bảng so sánh giữa hệ thống, giữa phương pháp |
| "tìm nguyên nhân: server a→b, hoặc từ b của a→c; backend, frontend…" | Phân biệt **nơi phát sinh** với **nơi biểu hiện** trên đường lan truyền, và xác định **tầng** lỗi (service, pod/node, code). Đây là bài toán propagation-aware localization |
| "làm hiểu trước, chạy cho được cái khung → nâng cấp" | Thứ tự làm: dựng khung baseline chạy được end-to-end trước, sau đó mới thêm cơ chế mới |
| "tìm ra lỗi → độ chính xác bao nhiêu %? tại sao chẩn đoán như thế? tại sao ra con số đó?" | Ba yêu cầu riêng: (i) độ chính xác có khoảng tin cậy, (ii) giải thích bám bằng chứng kiểm được, (iii) **độ tin cậy (confidence) của từng chẩn đoán phải hiệu chỉnh được** — con số "82%" phải có nghĩa thống kê |

## 3. Bức tranh nghiên cứu 2024–2026 (theo nhóm)

| Nhóm | Đại diện (cần đọc toàn văn) | Điều đã làm | Khoảng trống còn lại |
|---|---|---|---|
| Benchmark | RCAEval (WWW'25 Companion, 735 sự cố, 3 hệ thống); OpenRCA (ICLR'25, 335 sự cố); AIOpsLab; ITBench; SREGym; OpenRCA 2.0 (arXiv 2606.27154, nhãn quá trình nhân quả) | Có dữ liệu chung, metric chung | Benchmark mới bắt đầu chấm **quá trình** (đường lan truyền) chứ không chỉ nhãn cuối |
| Agent LLM cho RCA | RCAgent, mABC, TAMO, Flow-of-Action; trajectory study (arXiv 2608.21310); "Why do AI agents systematically fail" (arXiv 2602.09937) | Agent gọi công cụ đọc telemetry | Agent hay "bịa diễn giải dữ liệu" và khám phá thiếu; tốn token; chỉ ~20% khôi phục đúng tập root cause trên các mô hình frontier |
| Đồ thị + LLM | GALA (arXiv 2608.08968), Recursion-of-Thought đa agent (arXiv 2605.14866), RC-LLM (arXiv 2602.08804) | Đi theo cạnh lan truyền, gộp đa nguồn | Phần lớn dùng LLM lớn qua API; ít đo độ tin cậy; ít kiểm chuyển giao giữa hệ thống |
| Giả thuyết – kiểm chứng | SpecRCA / Hypothesize-Then-Verify (arXiv 2601.02736), ThinkFL (arXiv 2504.18776, RL fine-tune) | LLM nhỏ kiểm từng giả thuyết song song | Chưa gắn với hiệu chỉnh độ tin cậy và đảm bảo bằng chứng |
| Tách bằng chứng khỏi suy luận | EviRCA (arXiv 2609.19825) | Trích bằng chứng tất định, rồi mới suy luận | **Rất gần hướng của nhóm — phải đọc kỹ để định vị** |
| RAG sự cố lịch sử | RCACopilot (EuroSys'24); multimodal RAG cho cloud (arXiv 2505.21419) | Truy hồi sự cố tương tự | Ít bài đo rò rỉ nhãn và ảnh hưởng của truy hồi lên chuyển giao chéo hệ thống |
| Hiệu chỉnh độ tin cậy của LLM | MetaFaith (EMNLP'25), các bài về faithful confidence | Đo độ khớp giữa độ tin cậy nói ra và bất định nội tại | **Gần như chưa áp vào RCA microservice** — khoảng trống rõ nhất |

## 4. Các mảng tiềm năng và đánh giá

Thang 1–5. "Khả thi" xét nhóm 2 sinh viên, GPU Kaggle/Colab, mô hình 7–8B open-weight.

| # | Mảng | Mới | Khả thi | Khớp note 29/09 | Khớp proposal | Rủi ro trùng |
|---|---|---|---|---|---|---|
| A | **Độ tin cậy hiệu chỉnh + khả năng từ chối** cho chẩn đoán RCA (ECE, Brier, đường selective accuracy–coverage; con số % có nghĩa thống kê) | 5 | 4 | 5 (câu "bao nhiêu %, tại sao") | 4 | Thấp |
| B | **Định vị theo lan truyền**: phân biệt nơi phát sinh và nơi biểu hiện trên đồ thị gọi, kiểm giả thuyết dọc cạnh, chấm cả đường lan truyền | 4 | 4 | 5 (câu "a→b, b của a→c") | 4 (đã có cạnh trace, "đầu chuỗi lan truyền") | Trung bình (GALA, SpecRCA) |
| C | **Giải thích bám bằng chứng kiểm được** (evidence_ids tất định + kiểm phản thực: bỏ bằng chứng thì kết luận có đổi không) | 4 | 5 | 4 | 5 | Trung bình (EviRCA) |
| D | Chuyển giao chéo hệ thống (OB → SS → TT), đánh giá ≥3 ứng dụng | 3 | 5 | 5 | 3 | Thấp, nhưng một mình không đủ thành đóng góp |
| E | Nén telemetry dưới ngân sách token cho LLM nhỏ (cost–accuracy frontier) | 3 | 5 | 2 | 5 | Trung bình |
| F | Hybrid Retrieval runbook + sự cố lịch sử | 2 | 5 | 2 | 5 | Cao |
| G | Fine-tune LLM nhỏ (LoRA/RL) cho RCA | 3 | 2 | 2 | 3 | Cao (ThinkFL) |
| H | Detector chi phí thấp kích hoạt LLM | 2 | 5 | 2 | 5 | Cao |

## 5. Đề xuất focus

**Một đóng góp lõi gộp A + B + C, dùng D làm thiết kế thực nghiệm, E/F/H làm hạ tầng (không tuyên bố là đóng góp):**

> *Chẩn đoán nguyên nhân gốc theo lan truyền, có bằng chứng kiểm được và độ tin cậy hiệu chỉnh, bằng LLM open-weight cỡ nhỏ
> dưới ngân sách token cố định, đánh giá trên ba hệ thống microservice.*

Lý do chọn:

1. Trả lời trực tiếp cả ba câu của note 29/09: nhiều ứng dụng (D), lỗi lan từ đâu (B), "bao nhiêu % và tại sao" (A + C).
2. Khoảng trống A gần như trống trong RCA microservice; B và C có bài gần nhưng ghép với hiệu chỉnh độ tin cậy thì chưa thấy.
3. Giữ được gần như toàn bộ pipeline Proposal_v2 làm khung chạy trước ("chạy khung → nâng cấp"): incident card, call graph,
   evidence_ids, retrieval đều được dùng lại; phần mới chỉ nằm ở lớp suy luận và đánh giá.
4. Chạy được bằng mô hình 7–8B, không cần API trả phí — đây cũng là điểm khác biệt so với các bài dùng LLM frontier.

Phương án dự phòng nếu khi đọc toàn văn thấy EviRCA/GALA/SpecRCA đã làm phần lớn A + B + C: thu về **A + D**
(nghiên cứu thực nghiệm có hệ thống về độ tin cậy hiệu chỉnh của chẩn đoán LLM trên ba hệ thống) — vẫn là một đóng góp
đủ cho tạp chí kiểu empirical study.

## 6. Nơi nộp Q1 có thể nhắm (người dùng tự tra SCImago, không tự khẳng định hạng)

Journal of Systems and Software (Elsevier), Information and Software Technology, IEEE Transactions on Network and
Service Management, IEEE Transactions on Services Computing, Future Generation Computer Systems, Empirical Software
Engineering. Chọn nơi nộp quyết định giới hạn trang, template và kiểu trích dẫn trong hồ sơ bài.

## Câu hỏi còn mở

1. Nơi nộp mục tiêu và mốc thời gian nộp bài Q1 (khác với hạn NT114 20/10/2026)?
2. Ai là mentor/đồng tác giả chính của bài báo (ThS. Lê Anh Tuấn?), và bài viết LaTeX trên Overleaf hay Word?
3. Có được dùng RCAEval RE1/RE3 (metric-only, code-level) ngoài RE2 không, hay chỉ RE2 đa nguồn?
4. Có cần công bố code và dữ liệu kèm bài không?

## Nguồn đã thấy qua tìm kiếm (chưa đọc toàn văn)

- RCAEval: https://arxiv.org/pdf/2412.17015
- OpenRCA (ICLR 2025): https://netman.aiops.org/wp-content/uploads/2025/05/13411_OpenRCA_Can_Large_Langua.pdf
- OpenRCA 2.0: https://arxiv.org/html/2606.27154v2
- Why Do AI Agents Systematically Fail at Cloud RCA?: https://arxiv.org/html/2602.09937v2
- Multi-Dataset Benchmark for LLM Agents in Microservice Failure Diagnosis: https://arxiv.org/html/2606.29193v1
- SREGym: https://arxiv.org/pdf/2605.07161
- ARGUS (MCP-grounded RCA for Kubernetes): https://arxiv.org/pdf/2608.23084
- Self-Evolving Harness for RCA: https://arxiv.org/pdf/2608.25661
- Hypothesize-Then-Verify (SpecRCA): https://arxiv.org/pdf/2601.02736
- Agentic Memory Recursive Reasoning: https://arxiv.org/pdf/2601.02732
- ThinkFL: https://arxiv.org/pdf/2504.18776
- Trajectory-Level Study of LLM Agents for RCA: https://arxiv.org/pdf/2608.21310
- Multi-Agent Recursion-of-Thought: https://arxiv.org/pdf/2605.14866
- RC-LLM (residual connection): https://arxiv.org/abs/2602.08804
- GALA: https://arxiv.org/html/2608.08968
- EviRCA: https://arxiv.org/pdf/2609.19825
- Multimodal RAG for cloud instability: https://arxiv.org/pdf/2505.21419
- MetaFaith (EMNLP 2025): https://aclanthology.org/2025.emnlp-main.1505.pdf
- RCACopilot: https://arxiv.org/pdf/2305.15778
