# Tra tài liệu: thiếu metric và điểm mù "dịch vụ lỗi không có span"

Ngày 2026-11-02. Phase 2 của [plan RQ (c) bước 1](../261102-0035-rclagent-rq-c-metric-drop-substitutes/plan.md). Người đọc là một subagent nckh-researcher; controller lưu báo cáo vào file vì subagent không có công cụ ghi. Không đọc kết quả test split RE2-OB, không mở `runtime/analysis-evidence-loss-audit/`.

**Giới hạn quan trọng nhất:** mọi bài được đọc qua WebFetch, tức trang được chuyển thành markdown rồi một mô hình nhỏ trả lời theo câu hỏi. Trích dẫn và số mục dưới đây là do công cụ trả về, **chưa đối chiếu với bản gốc** [UNVERIFIED]. Phải kiểm lại nguyên văn trước khi đưa vào bài.

## 1. Bài đã đọc

| Bài | URL | Phần đã đọc | Mức truy cập |
|---|---|---|---|
| RCLAgent (Multi-Agent Recursion-of-Thought) | https://arxiv.org/html/2605.14866v1 | Sec. IV, V, VI, Appendix A đến C; hết trang, hai lượt | HTML đầy đủ, qua tóm tắt công cụ |
| Agentic Memory Enhanced Recursive Reasoning | https://arxiv.org/html/2601.02732v1 (PDF https://arxiv.org/pdf/2601.02732 không đọc được) | Sec. 4, 5 (gồm 5.5, 5.6), 7 | HTML v1, qua tóm tắt; có thể khác bản cuối |
| Why Do AI Agents Systematically Fail at Cloud RCA | https://arxiv.org/html/2602.09937v1 | Sec. 2, 4.1, Table 3, Sec. 5, theo câu hỏi | Một phần |
| Beyond Fault Localization (trajectory-level) | https://arxiv.org/html/2608.21310 | Sec. 3.3, 4.1, 5.2, 5.3, Table 3; 100000 trên 119467 ký tự | Một phần |
| Emődi et al., trace-only slowdown attribution (SAMI 2026) | https://science-cloud.hu/publikaciok/root-cause-analysis-latency-slowdowns-distributed-microservice-applications | Metadata và abstract | Chỉ abstract |

Chỉ thấy ở mức đoạn tìm kiếm, chưa mở, không dùng làm bằng chứng: GALA (arXiv 2508.12472, 2608.08968), MicroRCA-Agent, QPIAI 2607.13548, survey 2407.01710, MicroRank, ICPE 2024 p40, trang vendor OpenTelemetry và Coralogix.

## 2. Câu trả lời

### Q1. Bài nào đo RCLAgent hoặc agent đi theo trace khi thiếu một nguồn telemetry?

Không tìm thấy trong các bài đã đọc bài nào gỡ một nguồn telemetry có kiểm soát rồi đo độ chính xác của RCLAgent hay agent đi theo trace.

- **RCLAgent gốc:** ablation duy nhất bỏ Root-Level Diagnosis Report và Global Evidence Graph (Sec. V-E, Fig. 7); siêu tham số quét là cửa sổ metric δ từ 10 đến 120 giây (Sec. V-F, Fig. 8). Thiếu trace chỉ được nói định tính ở Sec. VI(1). Appendix C ghi log không dùng được trên AIOPS 2022 vì log không có SpanID; đó là thiếu do dữ liệu, không phải gỡ có kiểm soát.
- **Bài nối tiếp (2601.02732):** ablation gồm w/o Mem, w/o FR, w/o CR & FR (Sec. 5.5, Table 4); không ablate nguồn telemetry. Log và metric dùng để kiểm chéo (Sec. 4.3.1), hiệu quả không được đo.
- **2602.09937:** pitfall "Limited Telemetry Coverage" (Sec. 4.1, Table 3) là agent không dùng hết nguồn có sẵn, không phải nguồn bị mất; bài dùng OpenRCA, không phải agent đi theo trace.
- **2608.21310:** không đo như biến kiểm soát; taxonomy Table 3 (Sec. 5.3) có MIS1 (im lặng hoặc thiếu dữ liệu bị đọc thành "khỏe") và GEN3 (kênh bằng chứng bị bỏ sau lỗi tool hoặc kết quả rỗng); Sec. 5.2 nói run sai gặp truy vấn rỗng nhiều hơn. Đây là quan sát hành vi.

Hệ quả: phép gỡ metric của dự án (R@1 giảm 0,208 trên 8 case) có vẻ là phép đo gỡ nguồn đầu tiên cho dòng RCLAgent **trong phạm vi các bài đã đọc**. MIS1 của 2608.21310 gần với điều phase 1 thấy (thiếu bằng chứng log, metric bị đọc thành bình thường) và nên được trích khi viết.

### Q2. Bài nào dùng độ trễ trace làm tín hiệu thay thế khi thiếu metric, hoặc dựng KPI từ trace?

Không tìm thấy trong các bài đã đọc bài nào làm điều này trong khung LLM-agent.

- **RCLAgent gốc:** Trace Tool trả duration và status code của span con (Sec. IV-A1, Eq. 2); request lỗi được định nghĩa bằng độ trễ entry span vượt 100 lần mức bình thường (Sec. II-C); case study Sec. III-B dựa vào so sánh duration phía caller và callee, là suy luận của LLM, không có công thức. Metric Tool riêng, n-sigma (Sec. IV-A2). Không có đường thay metric bằng độ trễ trace.
- **Bài nối tiếp:** cạnh có thuộc tính `call_latency` (Eq. 2, Sec. 4.1.1), nhưng hàm chấm điểm để trừu tượng; không nói độ trễ đi vào chấm điểm thế nào.
- **Ngoài khung agent (chưa đọc kỹ):** Emődi et al. cho rằng chỉ dữ liệu trace là đủ để quy slowdown về thành phần (abstract). Survey 2407.01710 (đoạn tìm kiếm) nhắc T-Rank (kiểm 3-sigma trên độ trễ trace) và MicroRank. Hướng "độ trễ trace đứng một mình" có tiền lệ ngoài LLM-agent; cần đọc kỹ trước khi trích.

### Q3. Điểm mù "dịch vụ lỗi không có span trong trace" đã có ai báo chưa?

RCLAgent thừa nhận định tính; không tìm thấy trong các bài đã đọc bài nào đo hay đặc tả điểm mù này.

- **RCLAgent gốc, Sec. VI(2):** span thiếu có thể ngăn agent tới thành phần lỗi thật; không có giảm thiểu hay phép đo. Phát biểu này nhẹ hơn điểm mù S0 của dự án, vốn đã đo được rằng agent không bao giờ truy vấn metric của dịch vụ lỗi khi nó không có span.
- **Bài nối tiếp, 2602.09937:** không đề cập.
- **2608.21310 Sec. 3.3:** bộ RCA100 chỉ giữ case có đường lan truyền được telemetry hỗ trợ từng chặng, tức lọc bỏ thay vì phân tích các case thiếu trace.
- **Ngoài học thuật:** tài liệu Coralogix (đoạn tìm kiếm) nói dịch vụ chưa instrument chỉ suy ra được từ span của caller.

## 3. Nhật ký truy vấn (một lượt, 2026-11-02)

| # | Công cụ | Truy vấn | Kết quả dùng |
|---|---|---|---|
| 1 | WebSearch | LLM agent root cause analysis missing telemetry incomplete observability microservices modality dropout | GALA, 2602.09937, QPIAI 2607.13548, MicroRCA-Agent (đoạn tìm kiếm) |
| 2 | WebSearch | trace-derived latency as metric substitute root cause localization without metrics microservices traces only | Emődi (SAMI 2026), survey 2407.01710, MicroRank, ICPE 2024 p40 |
| 3 | WebSearch | root cause service absent from traces uninstrumented service missing spans microservice root cause analysis | Chỉ trang vendor và blog OpenTelemetry |

Kèm 4 lượt WebFetch theo URL được giao, 2 lượt cho bản HTML của 2601.02732, 1 lượt đọc phần sau của 2605.14866, 1 lượt mở trang Emődi. Trước đó, controller đã chạy hai lượt WebSearch khi trả lời sếp (cùng phiên), ra 2605.14866, 2601.02732, 2602.09937, 2608.21310 và LATS-RCA (2605.03505).

## 4. Giới hạn

- Đọc qua tóm tắt bằng mô hình nhỏ; số mục, số bảng và trích dẫn chưa đối chiếu nguyên văn, nhất là Sec. VI(2) của RCLAgent.
- PDF 2601.02732 không đọc được; HTML v1 có thể khác bản cuối. Không có số trang.
- 2608.21310 còn 19467 ký tự cuối chưa đọc; 2602.09937 chỉ đọc theo câu hỏi.
- Chỉ ba truy vấn, kết quả ở mức đoạn tóm tắt. GALA, MicroRank, survey và QPIAI chưa mở, nên không loại trừ chúng có thí nghiệm thiếu telemetry.
- Mọi câu "không tìm thấy" chỉ đúng trong phạm vi trên.

## Câu hỏi còn mở

1. Có cần một lượt đọc nguyên văn (tải PDF, đọc trực tiếp) cho Sec. VI(2) của RCLAgent và cho T-Rank/MicroRank trước khi chọn X không? Nếu X là KPI độ trễ dựng từ trace, T-Rank và MicroRank là tiền lệ trực tiếp.
