# Thẻ ý tưởng, ma trận khái niệm và gap đã qua bước cố bác bỏ (báo cáo trung gian, 12/10/2026)

Thuộc [plan khảo sát Q1](../261011-1345-aiops-q1-literature-gap/plan.md), giai đoạn 04. Dữ liệu nằm trong
`plans/261011-1345-aiops-q1-literature-gap/work/`.

## Kết quả chính

- **Còn 3 gap `confirmed`** (cả ba dựa trên phiếu đọc toàn văn và có truy vấn cố bác bỏ ở cả Q1 lẫn arXiv):
  - **G2:** chưa bài Q1 nào đo việc chọn cách truy hồi (không truy hồi / BM25 / dense / hybrid / rerank) làm thay đổi độ chính xác định vị dịch vụ gốc (AC@k) ra sao.
  - **N1:** LLM-RCA khi thiếu modality hoặc có dịch vụ không được instrument.
  - **N2:** truy hồi được bật/tắt theo độ tin cậy của bộ chẩn đoán.
- **5 gap `partially-filled`:** G3 (độ tin cậy được hiệu chỉnh), G4 (chi phí theo ngân sách token), G6 (chuyển giao giữa hệ thống, chỉ ở mức tóm tắt), G7 (độ trung thực của giải thích), N3 (cascade mô hình nhỏ → lớn).
- **3 gap `refuted`:** G1, G5, G8. Khung "LLM cho RCA microservice" đã có ít nhất 7 bài Q1 đọc toàn văn; "bỏ qua lan truyền" và "chưa chạy trên Kubernetes" cũng không còn đúng.
- **32 thẻ ý tưởng** lấy từ 26 bài, mỗi thẻ gắn với một mục Proposal (5.2–6.6) và mã đoạn Pxxxx.

## Ma trận khái niệm rút gọn

Ma trận sinh bằng `scripts/build-concept-matrix.py` từ `extraction.csv`. Mỗi chiều được mã 0/1 bằng quy tắc regex ghi
trong script nên kiểm lại được. Số đếm chỉ tính 39 bài nghiên cứu gốc; 8 survey/review được giữ trong ma trận nhưng
không tính. Toàn bộ tổ hợp 1–3 chiều (469 dòng) nằm ở `concept-combos.csv`.

| Chiều | Số bài | Tổ hợp then chốt | Số bài | Bài |
|---|---|---|---|---|
| LLM sinh | 22 | microservice & LLM | 7 | P07 P09 P18 P30 P31 P42 P45 |
| Truy hồi | 16 | microservice & LLM & so sánh kiểu truy hồi | **0** | — |
| So sánh sparse/dense/hybrid | 4 | LLM & so sánh kiểu truy hồi & ≥2 hệ thống | **0** | — |
| Độ tin cậy được hiệu chỉnh | 2 | microservice & LLM & hiệu chỉnh | 1 | P42 |
| Lan truyền | 17 | microservice & LLM & lan truyền | 4 | P07 P09 P18 P42 |
| Đánh giá giải thích | 9 | microservice & LLM & đánh giá giải thích | 2 | P30 P45 |
| Báo cáo chi phí | 28 | microservice & LLM & chi phí | 6 | P07 P09 P18 P31 P42 P45 |
| ≥2 hệ thống benchmark | 11 | LLM open-weight & RCAEval | **0** | — |
| Dùng RCAEval | 2 | LLM & truy hồi & RCAEval | **0** | P18, P45 dùng RCAEval nhưng không có truy hồi |

Mã hóa bằng regex có thể sai ở vài ô. Mỗi ô dùng để chứng minh gap ở dưới đều đã được đối chiếu tay với phiếu.

## Bảng gap

Truy vấn nguyên văn, ngày chạy và số kết quả ghi ở `falsification-log.csv`; các bài trúng nằm ở `falsification-hits.csv`.
Tất cả truy vấn chạy ngày 12/10/2026. Nguồn Q1 là OpenAlex (chỉ tạp chí, 2020–2026, gắn cờ Q1 theo SJR 2025); nguồn
ngoài Q1 là arXiv 2024–2026.

| Gap | Phát biểu ngắn | OpenAlex (Q1 trong top 50) | arXiv | Bài gần nhất (Q1) | Trạng thái | Mức chắc |
|---|---|---|---|---|---|---|
| G1 | LLM-RCA microservice ít bài Q1 | 56 (12) | 18 | P07 P09 P18 P30 P31 P42 P45 | refuted | full-text |
| G2 | Kiểu truy hồi ảnh hưởng AC@k chưa được đo | 25 (5) | 13 | P49 (chỉ đo truy hồi), P50 (văn bản, RAG có hại), P31 (top-k tĩnh) | **confirmed** | full-text |
| G3 | Độ tin cậy được hiệu chỉnh | 23 (11, phần lớn lạc đề) | 35 | P42 (ECE, coverage, GPT-4, chủ yếu Train Ticket) | partially-filled | full-text |
| G4 | Đường cong chi phí và độ chính xác theo ngân sách nén | 10 (2) | 79 | P18, P45 (một điểm vận hành) | partially-filled | full-text |
| G5 | LLM-RCA bỏ qua lan truyền | 11 (4, lĩnh vực khác) | 27 | P18, P42 | refuted | full-text |
| G6 | Chuyển giao từ hệ thống A sang B | 6 (1: UDA-RCL) | 3 | P23 UDA-RCL (chỉ tóm tắt) | partially-filled | abstract-only |
| G7 | Độ trung thực của giải thích | 12 (10, phần lớn lĩnh vực khác) | 32 | P30 (BLEU, người chấm), P45 (đúng do cách xây) | partially-filled | full-text |
| G8 | Chưa chạy trên K8s có tiêm lỗi | 6 (1) | 1 | P42 P57 P29 P55 P63 | refuted | full-text |
| N1 | LLM-RCA khi thiếu modality | 6 (0) | 6 | P18 Threats, P08 Sec 8, P63 (không LLM) | **confirmed** | full-text |
| N2 | Truy hồi bật theo độ tin cậy | 8 (0) | 3 | P50 Sec 6, P31 Conclusions (đều là future work) | **confirmed** | full-text |
| N3 | Cascade mô hình nhỏ → lớn cho RCA | 3 (1: SLMFL, lỗi mã nguồn) | 97 | P67 (log), P01 Sec 7.1 | partially-filled | full-text |

Bài ngoài Q1 trúng sát (chỉ đọc tóm tắt, dùng để thu hẹp phát biểu, không dùng làm căn cứ):

| Bài | Liên quan |
|---|---|
| arXiv 2609.14762 TriCalRAG | G2: so sánh zero/few-shot/RAG cho phát hiện bất thường log, không phải định vị dịch vụ |
| arXiv 2609.36686 | G2: phân rã lỗi truy hồi và rerank cho cảm biến, không dùng LLM |
| arXiv 2606.19407 JustDiag | G3, G7 |
| arXiv 2609.19825 EviRCA | G4, G7 |
| arXiv 2603.25538 ARMOR | N1: thiếu modality, không dùng LLM |
| arXiv 2403.18998 TraFaultDia | G6 |
| arXiv 2608.21310 | G5: phần còn lại là kiểm đường lan truyền |

## Đối chiếu G1–G8 của báo cáo 05/10

- **G1 bị bác bỏ.** Báo cáo 05/10 chỉ dựa trên tóm tắt nên đếm thiếu. Phần còn lại (LLM open-weight nhỏ chạy trên nhiều hệ thống RCAEval) được gộp vào các hướng ở Phase 05, không giữ thành gap riêng.
- **G2 giữ, phát biểu hẹp lại.** Phát biểu mới là "ảnh hưởng của thiết kế truy hồi lên AC@k", không còn là "chưa ai dùng hybrid retrieval".
- **G3, G4 và G7 sửa thành `partially-filled`.** Mỗi gap có điểm khác biệt ghi trong `gaps.csv`.
- **G5 bị bác bỏ.** Phần còn lại là kiểm đường lan truyền với ground truth mức cạnh. P37 nêu thiếu ground truth này ở Sec 8.2.
- **G6 không xác nhận được.** Bài gần nhất (UDA-RCL, IEEE) chỉ đọc được tóm tắt.
- **G8 bị bác bỏ.** Chỉ còn là yêu cầu kỹ thuật, không còn là điểm mới.

## Thẻ ý tưởng (32 thẻ, chi tiết ở `ideas25.csv`)

| Mục Proposal | Thẻ |
|---|---|
| 5.2 Phát hiện | I24 |
| 5.3 Nén, biến đổi telemetry | I10 I18 I23 I25 |
| 5.4 Hybrid retrieval | I02 I03 I04 I05 I09 I17 I30 |
| 5.5 LLM và sinh kết quả | I03 I07 I08 I15 I18 I27 I29 I31 |
| 6.1 Thiết lập thực nghiệm | I04 |
| 6.3 Định vị và phân loại lỗi | I06 I19 I21 I24 I28 |
| 6.4 Chất lượng truy hồi | I01 I26 |
| 6.5 Đánh giá giải thích | I06 I12 I14 I16 I19 I20 I26 I27 I32 |
| 6.6 Baseline, thống kê, phân tích lỗi | I02 I11 I13 I22 |

Một số thẻ được ghi ở nhiều mục. Ba thẻ chưa có bằng chứng hiệu quả trong bài nguồn vì tác giả chỉ đề xuất mà chưa thử:
I03 (RAG được bật theo độ tin cậy), I05 (top-k thích ứng) và I11 (kiểm tra khi có dịch vụ mù).

## Lệch so với plan

- **Nguồn ngoài Q1:** chỉ dùng arXiv qua API. Chưa truy vấn Google Scholar, DBLP hay Semantic Scholar cho ICSE/FSE/ASE/ISSRE/KDD/WWW/EuroSys/NSDI vì Google Scholar cần CAPTCHA và ngân sách OpenAlex còn thấp. Bài hội nghị có bản arXiv đã nằm trong phạm vi tìm.
- **N3:** arXiv trả 97 kết quả với từ khóa rộng nhưng mới đọc top 25. Đây là lý do N3 chỉ ghi `partially-filled`, không ghi `confirmed`.
- **Lặp lại kết luận:** chưa có thành viên thứ hai đọc lại 3 gap ngẫu nhiên từ log như bước kiểm tra của plan yêu cầu.
- **Bài then chốt chỉ đọc tóm tắt** (P16, P22, P23, P24, P25) có thể làm thay đổi G3, G6 và N1. Ví dụ, P24 (LLM + diễn giải chuyên gia, TSC 2026) có thể có phần truy hồi; nếu có thì G2 cần kiểm lại.

## Câu hỏi còn mở

1. Có ai trong nhóm truy cập được toàn văn P24 (TSC 2026) và P23 (UDA-RCL) qua thư viện UIT không? Nếu được, có thể nâng G6 lên mức `full-text` và kiểm lại G2.
2. Thành viên nào đọc lại 3 gap ngẫu nhiên (đề xuất G2, N1, G7) để kiểm khả năng lặp lại?
