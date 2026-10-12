# Khảo sát tài liệu Q1 cho NCKH AIOps và các hướng nghiên cứu ứng viên (12/10/2026)

Báo cáo cuối của [plan khảo sát Q1](../261011-1345-aiops-q1-literature-gap/plan.md). Dữ liệu và script nằm ở
`plans/261011-1345-aiops-q1-literature-gap/work/`. Báo cáo trung gian về gap:
[research-261012-q1-ideas-and-gaps.md](research-261012-q1-ideas-and-gaps.md).

**Báo cáo này không chọn hướng.** Nhóm và GVHD chọn; mục "Quyết định" để trống chờ ghi lại.

## Kết quả chính

| Bước | Số bài |
|---|---|
| Bản ghi tìm được | 3.600 |
| Sau bỏ trùng | 2.218 |
| Bài Q1 giữ lại (tìm kiếm + snowball) | 736 |
| Đủ điều kiện (R ≥ 2) | 205 |
| Top | 100 |
| Đọc toàn văn | 47 |
| Chỉ đọc tóm tắt | 22 |
| Thẻ ý tưởng (từ 26 bài) | 32 |
| Gap kiểm | 11 |

**Gap sau bước cố bác bỏ:**

| Trạng thái | Số gap | Gap |
|---|---|---|
| confirmed | 3 | G2, N1, N2 |
| partially-filled | 5 | G3, G4, G6, G7, N3 |
| refuted | 3 | G1, G5, G8 |

**Hai hướng giữ top 3 dưới cả bốn cách đặt trọng số:**

| Mã | Hướng |
|---|---|
| **DA** | Truy hồi lai được chặn theo độ tin cậy cho định vị nguyên nhân gốc bằng LLM |
| **DB** | Nghiên cứu thực nghiệm về thiết kế truy hồi cho LLM-RCA |

DB là bước đầu của DA. Vị trí thứ ba đổi giữa **DC** (LLM open-weight được hiệu chỉnh và biết từ chối) và **DD**
(LLM-RCA khi thiếu modality) tùy cách đặt trọng số.

**Báo cáo 05/10 đánh giá quá mức độ trống:** "LLM cho RCA microservice" đã có ít nhất 7 bài Q1 đọc toàn văn. Gap còn
lại hẹp hơn và nằm ở cách đánh giá, không nằm ở việc "chưa ai dùng LLM".

## 1. Phương pháp tìm

- **Từ khóa:** 34 từ khóa trong 9 nhóm C1–C9 (`keywords.csv`); mỗi từ khóa trỏ về đoạn Proposal (mã P0001–P0202).
- **Truy vấn:** 22 truy vấn OpenAlex trên title + abstract, chạy ngày 11/10/2026 (`queries.csv`), cộng một vòng snowball.
- **Giao thức Q1** ([q1-protocol.md](../261011-1345-aiops-q1-literature-gap/work/q1-protocol.md)):
  - Q1 tính theo **SJR Best Quartile năm 2025** từ scimagojr.com (D1). Tệp CSV đầy đủ 11.253.130 byte, sha256 `6f20399957173a13e3c1729a5fb3b5821844ba75e8d640c8b3040ab19a6f7180`, tải ngày 11/10/2026.
  - Chỉ tính tạp chí, năm 2020–2026 (D7). Loại MDPI (D4).
  - IEEE Access và Scientific Reports gắn cờ `q1_weak` (D3); top 100 có 9 bài mang cờ này.
- **Hội nghị và arXiv** chỉ dùng để cố bác bỏ gap, không tính vào corpus (D2).
- **IEEE Xplore:** không dùng để lấy toàn văn theo quyết định của người dùng; 5 bài IEEE trong danh sách đọc chỉ được tính ở mức tóm tắt.
- **Toàn văn:** lấy từ bản OA hoặc qua Chrome (mạng UIT). Người dùng tự qua CAPTCHA. PDF lưu ở `private/fulltext/`, không phân phối lại (D6).

## 2. Sơ đồ PRISMA

```text
Tìm OpenAlex (22 truy vấn)  3.600 bản ghi  ──►  bỏ trùng 2.218
   ├─ không Q1: 1.556   ├─ MDPI: 61   └─► Q1 giữ: 601
Snowball 1 vòng  279 bản ghi ──► mới 175 ── không Q1 38, MDPI 2 ──► Q1 giữ: 135
Q1 sàng lọc tiêu đề/tóm tắt: 736
   ├─ R0 loại 420   ├─ R1 loại 111   └─► đủ điều kiện (R2 147 + R3 58) = 205
Top ~100 (cân bằng cụm): 100
Đọc: kế hoạch 50 ──► toàn văn 28 + 19 bài thay thế = 47; chỉ tóm tắt 22 (gồm 5 IEEE bỏ qua); 5 ứng viên thay thế bị bỏ
Ý tưởng: 32 thẻ từ 26 bài; gap: 11 kiểm, 3 confirmed
```

Các con số lấy từ `prisma-counts.json`; lý do loại từng bài ở `screened.csv` và `read-final.csv`.

## 3. Phân loại bài đã đọc theo cụm

| Cụm | Nội dung | Top 100 | Toàn văn | Chỉ tóm tắt |
|---|---|---|---|---|
| SV | Survey, review | 25 | 7 | 0 |
| B1 | Phát hiện bất thường microservice | 8 | 5 | 5 |
| B2 | Định vị nguyên nhân gốc không dùng LLM | 23 | 8 | 7 |
| B3 | LLM cho RCA/AIOps | 23 | 15 | 7 |
| B4 | LLM cho log | 8 | 4 | 1 |
| B5 | Truy hồi lai, RAG | 8 | 6 | 1 |
| B6 | Kubernetes, chaos, đo đạc | 5 | 2 | 1 |
| **Tổng** | | **100** | **47** | **22** |

Phiếu trích của 47 bài toàn văn có ở `extraction.csv`; mỗi ô có vị trí trích, ô không có thông tin ghi `not-reported`.

## 4. Ma trận khái niệm rút gọn

Ma trận sinh từ phiếu bằng `scripts/build-concept-matrix.py`. Số đếm chỉ tính 39 bài nghiên cứu gốc.

| Tổ hợp | Số bài | Bài |
|---|---|---|
| microservice & LLM sinh | 7 | P07 P09 P18 P30 P31 P42 P45 |
| microservice & LLM & so sánh kiểu truy hồi | **0** | — |
| microservice & LLM & độ tin cậy được hiệu chỉnh | 1 | P42 |
| microservice & LLM & lan truyền | 4 | P07 P09 P18 P42 |
| microservice & LLM & đánh giá giải thích | 2 | P30 P45 |
| microservice & LLM & báo cáo chi phí | 6 | P07 P09 P18 P31 P42 P45 |
| LLM open-weight & RCAEval | **0** | — |
| LLM & truy hồi & RCAEval | **0** | — |

## 5. Gap

| Gap | Phát biểu | Trạng thái | Mức chắc | Bài gần nhất / điểm khác |
|---|---|---|---|---|
| G1 | LLM-RCA microservice ít bài Q1 | refuted | full-text | 7 bài Q1 (bảng 4) |
| G2 | Chưa đo thiết kế truy hồi ảnh hưởng AC@k | **confirmed** | full-text | P49 chỉ đo truy hồi; P50 trên văn bản (RAG gây hại); P31 dùng top-k tĩnh |
| G3 | Độ tin cậy được hiệu chỉnh cho LLM-RCA | partially-filled | full-text | P42 dùng ECE/coverage với GPT-4, chủ yếu một hệ thống |
| G4 | Chi phí theo ngân sách nén | partially-filled | full-text | P18, P45 chỉ báo một điểm vận hành |
| G5 | LLM-RCA bỏ qua lan truyền | refuted | full-text | P18, P42; phần còn lại là kiểm đường lan truyền |
| G6 | Chuyển giao giữa hệ thống | partially-filled | abstract-only | UDA-RCL (không LLM, chỉ tóm tắt) |
| G7 | Độ trung thực của giải thích | partially-filled | full-text | P30 (BLEU, người chấm); P45 (đúng do cách xây) |
| G8 | Chưa chạy K8s + tiêm lỗi | refuted | full-text | P42 P57 P29 P55 P63 |
| N1 | LLM-RCA khi thiếu modality | **confirmed** | full-text | P18, P08 nêu là hạn chế; P63 làm nhưng không dùng LLM |
| N2 | Truy hồi bật theo độ tin cậy | **confirmed** | full-text | P50, P31 nêu là future work |
| N3 | Cascade mô hình nhỏ → lớn cho RCA | partially-filled | full-text | P67 làm cho log |

Truy vấn cố bác bỏ (nguyên văn, nguồn, ngày, số kết quả) ở `falsification-log.csv`. Bảng đầy đủ gồm ô ma trận, vị trí
trích và bài ngoài Q1 ở `gaps.csv`.

## 6. Thẻ ý tưởng

| Id | Ý tưởng | Bài | Mục Proposal |
|---|---|---|---|
| I01 | Đo riêng truy hồi (MRR@10, nDCG@10, độ trễ P95) | P49 | 6.4 |
| I02 | Ablation không truy hồi / BM25 / dense / hybrid với McNemar | P50 | 5.4, 6.6 |
| I03 | Chỉ bật RAG khi bộ chẩn đoán không chắc | P50 | 5.4, 5.5 |
| I04 | Chia 50/50 làm kho ca lịch sử, so truy hồi ngữ nghĩa với từ khóa | P31 | 5.4, 6.1 |
| I05 | Số ca truy hồi thích ứng thay cho top-k tĩnh | P31 | 5.4 |
| I06 | ECE, kích thước tập dự đoán, coverage, đường cong few-shot | P42 | 6.3, 6.5 |
| I07 | Độ bất định từ nhiều lần lấy mẫu ở nhiều nhiệt độ | P42 | 5.5 |
| I08 | Mô hình nhỏ có độ bất định Bayes quyết định khi nào gọi LLM | P67 | 5.5 |
| I09 | Kho ca lỗi của mô hình rẻ làm gợi ý cho LLM | P67 | 5.4 |
| I10 | Giới hạn ngữ cảnh cho từng đơn vị suy luận | P18 | 5.3 |
| I11 | Kiểm tra khi thiếu trace hoặc có dịch vụ mù | P18 | 6.6 |
| I12 | Độ đúng của bằng chứng được trích | P45 | 6.5 |
| I13 | Báo số lần gọi, token, thời gian; Wilcoxon + Holm | P45 | 6.6 |
| I14 | Điểm kiểm của người; người chấm thay cho BLEU | P30 | 6.5 |
| I15 | RL (GRPO) nhiều giai đoạn cho mô hình 3B | P09 | 5.5 |
| I16 | HEval: chỉ tính đúng khi lập luận hợp lý | P03 | 6.5 |
| I17 | Truy hồi đường đi trên đồ thị tri thức | P51 | 5.4 |
| I18 | Text-to-PromQL với đồ thị ngữ cảnh hệ thống | P55 | 5.3, 5.5 |
| I19 | Điểm nguyên nhân giải thích được từ lỗi tái tạo upstream/downstream | P08 | 6.3, 6.5 |
| I20 | Giải thích phản thực tế bằng mẫu bình thường | P29 | 6.5 |
| I21 | Học đồ thị lan truyền với topology làm tiên nghiệm mềm | P37 | 6.3 |
| I22 | Mô phỏng thiếu metric theo khối và theo điểm, đến 40% | P63 | 6.6 |
| I23 | Hợp nhất ba modality thành cảnh báo; học modality nào giúp tác vụ nào | P57 | 5.3 |
| I24 | Baseline rẻ: tương quan Spearman giữa điểm bất thường trace và metric | P56 | 5.2, 6.3 |
| I25 | Gộp trước dữ liệu có cấu trúc (frequent item-set + lift) | P59 | 5.3 |
| I26 | Tách lỗi truy hồi khỏi lỗi sinh; tỷ lệ ảo giác với judge đã kiểm | P44 | 6.4, 6.5 |
| I27 | Cho phép trả lời "Unknown"; theo dõi tỷ lệ dài dòng | P34 | 5.5, 6.5 |
| I28 | Phân tích đường găng trên trace RPC | P71 | 6.3 |
| I29 | Khối bằng chứng chuẩn hóa + giám sát đường quyết định | P11 | 5.5 |
| I30 | Truy hồi dense rồi LLM rerank danh sách ngắn | P69 | 5.4 |
| I31 | Cache câu trả lời LLM, báo token | P12 | 5.5 |
| I32 | Cây quyết định thay thế để giải thích điểm nơ-ron | P10 | 6.5 |

Mã đoạn, chi phí, bằng chứng trong bài nguồn và rủi ro khi chuyển sang RCAEval ở `ideas25.csv`. Có 3 thẻ (I03, I05,
I11) mà bài nguồn chỉ đề xuất, chưa thử.

## 7. Chấm điểm hướng

**Cách chấm:**
- 7 hướng ứng viên ghi ở `direction-candidates.csv`. Mỗi hướng ghép gap `confirmed` hoặc `partially-filled` với thẻ ý tưởng.
- Bỏ hướng "kiểm đường lan truyền" vì gap gốc G5 đã bị bác bỏ.
- Điểm 1–5. Mỗi điểm có lý do và nguồn trong `direction-scores.csv`.
- Điểm tính bằng `scripts/score-directions.py`; chạy hai lần cho cùng kết quả (hash tệp đầu ra trùng nhau).

**Trọng số:**

| Cách | Độ mới | Khả thi | Đánh giá được | Tận dụng Proposal | Khớp GVHD | Đăng Q1 |
|---|---|---|---|---|---|---|
| plan | 0,25 | 0,20 | 0,15 | 0,15 | 0,15 | 0,10 |
| equal | 1/6 | 1/6 | 1/6 | 1/6 | 1/6 | 1/6 |
| feasibility_first | 0,15 | 0,35 | 0,20 | 0,10 | 0,10 | 0,10 |
| novelty_first | 0,40 | 0,15 | 0,15 | 0,05 | 0,15 | 0,10 |

**Kết quả:**

| Hướng | Độ mới | Khả thi | Đánh giá | Proposal | GVHD | Q1 | plan | equal | khả thi trước | độ mới trước | Top 3 cả bốn |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DA Truy hồi chặn theo độ tin cậy | 5 | 4 | 4 | 5 | 4 | 4 | 4,40 (#1) | 4,33 (#1) | 4,25 (#2) | 4,45 (#1) | có |
| DB Ablation thiết kế truy hồi | 4 | 5 | 5 | 5 | 3 | 3 | 4,25 (#2) | 4,17 (#2) | 4,45 (#1) | 4,10 (#2) | có |
| DC LLM hiệu chỉnh + từ chối | 3 | 4 | 5 | 4 | 5 | 4 | 4,05 (#3) | 4,17 (#3) | 4,15 (#4) | 3,90 (#4) | không |
| DD Thiếu modality | 4 | 5 | 5 | 3 | 3 | 3 | 3,95 (#4) | 3,83 (#4) | 4,25 (#3) | 4,00 (#3) | không |
| DE Cascade nhỏ → lớn | 3 | 4 | 4 | 3 | 3 | 4 | 3,45 (#5) | 3,50 (#5) | 3,65 (#5) | 3,40 (#5) | không |
| DF Đánh giá độ trung thực giải thích | 3 | 3 | 2 | 4 | 4 | 3 | 3,15 (#6) | 3,17 (#6) | 3,00 (#7) | 3,05 (#7) | không |
| DG Chuyển giao giữa hệ thống | 3 | 3 | 4 | 2 | 4 | 3 | 3,15 (#7) | 3,17 (#7) | 3,20 (#6) | 3,25 (#6) | không |

**Đọc kết quả:**
- Hạng 1–2 ổn định dưới cả bốn cách đặt trọng số. Hạng 3 không ổn định: DC và DD đổi chỗ khi tăng trọng số khả thi hoặc độ mới.
- Điểm hiện là bản nháp của một người chấm (`scorer = claude-draft`). Bước hai thành viên chấm độc lập và ghi các điểm lệch ≥ 2 **chưa làm**.
- Thiên vị Proposal (chấm "tận dụng" cao cho DA và DB) đã được kiểm bằng cách novelty_first, trong đó "tận dụng" chỉ nặng 0,05; DA và DB vẫn giữ hạng.

## 8. Hồ sơ các hướng tốt

Thông tin về RCAEval dùng bên dưới đến từ các bài đã đọc (P18, P45: 735 ca, 3 hệ thống microservice) và từ tài liệu
dataset. Trước khi chạy cần kiểm lại cấu trúc RE1/RE2/RE3 và danh sách baseline có sẵn trong repo RCAEval.

### DA. Truy hồi lai được chặn theo độ tin cậy cho định vị nguyên nhân gốc bằng LLM

- **Đóng góp (một câu):** chỉ ra khi nào truy hồi giúp và khi nào làm hại độ chính xác định vị của một LLM open-weight trên nhiều hệ thống RCAEval, rồi chỉ bật truy hồi khi độ tin cậy đã hiệu chỉnh của bộ chẩn đoán thấp.
- **Điểm khác so với bài gần nhất:** P42 hiệu chỉnh độ tin cậy với GPT-4 trên chủ yếu một hệ thống và không dùng độ tin cậy để quyết định truy hồi. P50 cho thấy RAG có thể gây hại nhưng làm trên văn bản và không thử chặn. P31 dùng top-5 tĩnh. G3 chỉ `partially-filled`, nên **không được viết "chưa ai làm hiệu chỉnh"**.
- **RQ:**
  1. Trên 3 hệ thống, so với không truy hồi, BM25, dense và hybrid làm AC@1/AC@3 thay đổi bao nhiêu?
  2. Độ tin cậy của LLM 7–8B (lấy mẫu nhiều lần, hoặc tự đánh giá) có hiệu chỉnh được không, đo bằng ECE?
  3. Bật truy hồi theo ngưỡng độ tin cậy có cho AC@k bằng hoặc cao hơn "luôn truy hồi" với ít token hơn không?
- **Giả thuyết:** truy hồi giúp ở ca khó (độ tin cậy thấp) và gây hại ở ca dễ, nên chặn theo độ tin cậy cho AC@1 không thấp hơn "luôn truy hồi" và tiết kiệm token.
- **Dữ liệu và chia tập chống rò rỉ:**
  - RCAEval, 3 hệ thống.
  - Kho ca lịch sử là 50% số ca mỗi hệ thống, chia theo thời gian hoặc theo ca tiêm lỗi (I04); 50% còn lại để đánh giá.
  - Không để ca đánh giá lọt vào kho truy hồi.
  - Ngưỡng độ tin cậy chọn trên một tập validation tách riêng.
- **Baseline:**
  - LLM không truy hồi.
  - Luôn truy hồi (BM25, dense, hybrid RRF).
  - Baseline không LLM có sẵn trong RCAEval.
  - Tái hiện cấu hình RAG top-5 của P31.
  - Kết quả công bố của P45 trên RE2+RE3 (Sec 9.1 Table 1) chỉ dùng để tham chiếu, không so trực tiếp; giá trị cần lấy lại từ bài vì phiếu chưa ghi.
- **Độ đo:**
  - AC@1, AC@3, Avg@5.
  - ECE, đường cong độ chính xác theo coverage.
  - Token và thời gian mỗi ca (I13).
  - McNemar/Wilcoxon + Holm.
  - Chất lượng truy hồi MRR@10 (I01).
- **Thí nghiệm tối thiểu (4 tuần):**
  - Tuần 1: tải RCAEval và chạy một baseline không LLM.
  - Tuần 2: chạy LLM 7–8B không truy hồi và với BM25 trên 1 hệ thống, lấy 5 mẫu mỗi ca.
  - Tuần 3: thêm dense, hybrid và tính ECE.
  - Tuần 4: chặn theo ngưỡng; chạy McNemar trên 1 hệ thống.
  - Chỉ cần dữ liệu công khai.
- **Tạp chí đích:**

  | Tạp chí | SJR 2025 | Bài cùng loại trong corpus |
  |---|---|---|
  | Complex and Intelligent Systems | Q1 | P31 |
  | Results in Engineering | Q1 | P42, P50 |
  | ACM TOSEM | Q1 | P30, P67 |

- **Rủi ro:**
  - LLM nhỏ có độ tin cậy phẳng hoặc quá tự tin.
  - Kho ca của mỗi hệ thống ít.
  - Lấy mẫu nhiều lần làm tăng chi phí.
- **Điều kiện dừng:** nếu ở tuần 3 cả BM25, dense lẫn hybrid đều không đổi AC@1 quá ±2 điểm % trên hệ thống đầu tiên, và ECE > 0,25 sau hiệu chỉnh nhiệt độ, thì chuyển sang DB (chỉ báo cáo ablation) hoặc DD.

### DB. Thiết kế truy hồi ảnh hưởng thế nào đến LLM-RCA (nghiên cứu thực nghiệm)

- **Đóng góp:** ablation có kiểm định về truy hồi (không truy hồi, BM25, dense, hybrid, có/không rerank) cho định vị nguyên nhân gốc bằng LLM trên 3 hệ thống.
- **Điểm khác:** P50 làm ablation tương tự trên văn bản phân tích hỏng hóc kim loại; P49 chỉ đo chất lượng truy hồi log, không đo kết quả LLM.
- **RQ:**
  1. Kiểu truy hồi nào cho AC@k cao nhất trên từng hệ thống?
  2. Chất lượng truy hồi (MRR@10) có dự báo được AC@k không?
  3. Lỗi sai đến từ truy hồi hay từ phần sinh (I26)?
- **Giả thuyết:** hybrid không luôn tốt nhất, và có cấu hình RAG làm giảm AC@1 so với không truy hồi (theo P50).
- **Dữ liệu và chia tập:** như DA.
- **Baseline:** như DA, bỏ phần chặn theo độ tin cậy.
- **Độ đo:**
  - AC@k.
  - MRR@10, nDCG@10, độ trễ P95.
  - McNemar.
- **Thí nghiệm tối thiểu:** tuần 1–3 của DA. DB là bước "chạy được khung" theo góp ý GVHD; DA là bước nâng cấp.
- **Tạp chí đích:**

  | Tạp chí | SJR 2025 | Bài cùng loại trong corpus |
  |---|---|---|
  | Applied Artificial Intelligence | Q1 | P49 |
  | Results in Engineering | Q1 | P50 |
  | Journal of Systems and Software | Q1 | không có bài cùng loại; chỉ thấy JSS 2026 SHARE-RAG ở bước cố bác bỏ, lĩnh vực lỗi mã nguồn |

- **Rủi ro:**
  - Độ mới hẹp, vì reviewer có thể coi là "chỉ là ablation".
  - Phải dựng tài liệu để truy hồi cho RCAEval.
- **Điều kiện dừng:** nếu mọi cấu hình cho AC@1 không khác biệt có ý nghĩa (McNemar p > 0,05 trên cả 3 hệ thống), báo cáo kết quả âm và gộp vào DA hoặc DC.

### DC. LLM open-weight được hiệu chỉnh và biết từ chối cho định vị nguyên nhân gốc (đồng hạng ba với DD)

- **Đóng góp:** biến con số "độ chính xác bao nhiêu %" thành con số tin được: ECE, độ chính xác theo coverage, cho phép trả lời "không đủ bằng chứng", trên 3 hệ thống.
- **Điểm khác:** P42 đã làm ECE/coverage với GPT-4; ở đây khác là mô hình open-weight, nhiều hệ thống và dự đoán chọn lọc. Gap G3 chỉ `partially-filled`.
- **RQ:**
  1. LLM 7–8B có quá tự tin khi định vị không?
  2. Hiệu chỉnh nhiệt độ hoặc lấy mẫu nhiều lần giảm ECE bao nhiêu?
  3. Ở coverage 80%, AC@1 tăng bao nhiêu?
- **Giả thuyết:** cho phép từ chối ở coverage 80% làm AC@1 tăng rõ, và ECE giảm sau hiệu chỉnh.
- **Dữ liệu:** RCAEval, chia validation riêng để hiệu chỉnh.
- **Baseline:**
  - LLM không hiệu chỉnh.
  - Baseline không LLM có điểm xếp hạng.
  - Cách gộp độ bất định của P42 (tái hiện một phần).
- **Độ đo:**
  - ECE, reliability diagram.
  - Đường cong độ chính xác theo coverage.
  - AC@k.
  - Độ đúng của bằng chứng (I12).
- **Thí nghiệm tối thiểu (4 tuần):**
  - Tuần 1–2: chạy LLM trên 1 hệ thống, 5 mẫu mỗi ca.
  - Tuần 3: hiệu chỉnh nhiệt độ.
  - Tuần 4: vẽ đường cong coverage.
- **Tạp chí đích:**

  | Tạp chí | SJR 2025 | Bài cùng loại trong corpus |
  |---|---|---|
  | Results in Engineering | Q1 | P42 |
  | ACM TOSEM | Q1 | P30 |
  | IEEE Transactions on Services Computing | Q1 | P07 |

- **Rủi ro:** độ mới thấp nhất trong ba hướng, vì gần P42.
- **Điều kiện dừng:** nếu ở coverage 80% AC@1 tăng dưới 3 điểm %, gộp phần hiệu chỉnh vào DA như một thành phần.

**DD** (thiếu modality, N1 `confirmed`) đứng hạng 3 khi ưu tiên khả thi hoặc ưu tiên độ mới. Đây là phương án thay thế
cho DC nếu nhóm ưu tiên điểm mới hơn khả năng tận dụng Proposal. Thí nghiệm tối thiểu: bỏ trace/log/metric theo tỷ lệ
(I11, I22) trên RCAEval và đo AC@k giảm bao nhiêu.

## 9. Tóm tắt một trang gửi GVHD

1. **DA – Truy hồi lai được chặn theo độ tin cậy.** Gap G2 và N2 `confirmed`, G3 `partially-filled`. Câu hỏi: truy hồi giúp hay hại định vị trên 3 hệ thống RCAEval, và có nên chỉ truy hồi khi mô hình không chắc? Dùng lại 5.4, 5.5, 6.4, 6.5 của Proposal. Trả lời "bao nhiêu %, vì sao tin con số đó" bằng ECE. Đích: Complex and Intelligent Systems, Results in Engineering, TOSEM (Q1, SJR 2025). Điểm 4,40 (hạng 1).
2. **DB – Ablation thiết kế truy hồi.** Gap G2 `confirmed`. Đây là phần "chạy khung trước" của DA và rủi ro thấp nhất. Có thể ra kết quả âm (RAG không giúp), như P50 đã gặp ở lĩnh vực khác. Đích: Applied Artificial Intelligence, Results in Engineering, JSS. Điểm 4,25 (hạng 2).
3. **DC – LLM open-weight được hiệu chỉnh và biết từ chối.** Gap G3 `partially-filled` (P42 đã làm với GPT-4). Khớp nhất với câu hỏi "tại sao ra con số đó" của GVHD. Hạng 3 không ổn định; **DD** (thiếu modality, N1 `confirmed`) là phương án thay thế. Điểm 4,05 / 3,95.

## 10. Quyết định của nhóm và GVHD

| Ngày | Người quyết | Hướng chọn | Lý do |
|---|---|---|---|
| (chưa có) | | | |

Khi đã chọn hướng, mở plan mới cho giai đoạn nghiên cứu. Không làm trong plan này.

## 11. Hạn chế của khảo sát

- **Một nguồn tìm chính (OpenAlex).** Bài trên Scopus/WoS mà OpenAlex index thiếu có thể bị sót. Snowball một vòng chỉ bù được một phần.
- **22/69 bài chỉ đọc tóm tắt.** Trong đó có bài then chốt P16, P22, P23, P24, P25. P24 (LLM + diễn giải chuyên gia, TSC 2026) có thể làm thay đổi G2; P23 (UDA-RCL) quyết định G6.
- **Bỏ IEEE Xplore** theo quyết định của người dùng. 5 bài IEEE trong danh sách đọc chỉ ở mức tóm tắt.
- **Bước cố bác bỏ ngoài Q1** chỉ dùng arXiv API. Chưa tìm Google Scholar/DBLP cho các hội nghị (cần CAPTCHA). N3 có 97 kết quả arXiv nhưng mới đọc 25.
- **Một người chấm.** Phiếu trích, mã hóa ma trận và điểm hướng đều do một người làm (bản nháp). Chưa có hai thành viên chấm độc lập 20 bài, chưa đọc chéo 5 phiếu, chưa có người khác lặp lại 3 gap từ log.
- **Phiếu P68 và P69** dựng từ bản Just Accepted, có thể khác bản chính thức.
- **P42 có chỗ lệch nội bộ:** caption Table 1 ghi Train Ticket, phần text ghi AIOps Challenge. Độ chính xác Top-k của P42 chưa được ghi vào phiếu; cần đọc lại Sec 4.2 trước khi dùng làm tham chiếu.
- **Ma trận mã hóa bằng regex.** Các ô dùng làm căn cứ gap đã được đối chiếu tay; các ô khác có thể lệch.
- **Năm trong danh mục tham khảo:** P13 và P34 mang năm 2027 vì Crossref ghi năm của số in.

## 12. Tài liệu tham khảo (IEEE)

Chỉ gồm bài đã đọc, có ghi mức đọc. 69/69 DOI phân giải được qua Crossref ngày 12/10/2026. Tiêu đề Crossref khớp tiêu
đề đã ghi (tỷ lệ ≥ 0,84; thấp nhất là P69 do khác dấu cách quanh dấu hai chấm). Mọi tạp chí có quartile Q1 trong tệp
SJR 2025 đã băm. Kết quả kiểm từng bài ở `references.csv`; danh mục sinh bằng `scripts/build-references.py`.

Dataset và công cụ dùng theo D5 (không phải căn cứ khoa học Q1): RCAEval, Loghub, Chaos Mesh, Train Ticket, Online
Boutique, Sock Shop.

[1] L. Zhang et al., “A Survey of AIOps in the Era of Large Language Models,” *ACM Computing Surveys*, vol. 58, no. 2, pp. 1-35, 2025, doi: 10.1145/3746635. (P01, đọc toàn văn)

[2] R. Xin, J. Wang, P. Chen, and Z. Zhao, “Trustworthy AI-based Performance Diagnosis Systems for Cloud Applications: A Review,” *ACM Computing Surveys*, vol. 57, no. 5, pp. 1-37, 2025, doi: 10.1145/3701740. (P02, đọc toàn văn)

[3] X. Zhou et al., “D-Bot: Database Diagnosis System using Large Language Models,” *Proceedings of the VLDB Endowment*, vol. 17, no. 10, pp. 2514-2527, 2024, doi: 10.14778/3675034.3675043. (P03, đọc toàn văn)

[4] N. Fu, G. Cheng, Y. Teng, G. Dai, S. Yu, and Z. Chen, “Intelligent Root Cause Localization in MicroService Systems: A Survey and New Perspectives,” *ACM Computing Surveys*, vol. 57, no. 12, pp. 1-37, 2025, doi: 10.1145/3736755. (P04, đọc toàn văn)

[5] S. Zhang et al., “Failure Diagnosis in Microservice Systems: A Comprehensive Survey and Analysis,” *ACM Transactions on Software Engineering and Methodology*, vol. 35, no. 1, pp. 1-55, 2025, doi: 10.1145/3715005. (P05, đọc toàn văn)

[6] J. Soldani and A. Brogi, “Anomaly Detection and Failure Root Cause Analysis in (Micro) Service-Based Cloud Applications: A Survey,” *ACM Computing Surveys*, vol. 55, no. 3, pp. 1-39, 2022, doi: 10.1145/3501297. (P06, đọc toàn văn)

[7] X. Zhang et al., “TAMO:Fine-Grained Root Cause Analysis via Tool-Assisted LLM Agent With Multi-Modality Observation Data in Cloud-Native Systems,” *IEEE Transactions on Services Computing*, vol. 18, no. 6, pp. 4221-4233, 2025, doi: 10.1109/tsc.2025.3629066. (P07, đọc toàn văn)

[8] Y. Sun et al., “Interpretable Failure Localization for Microservice Systems Based on Graph Autoencoder,” *ACM Transactions on Software Engineering and Methodology*, vol. 34, no. 2, pp. 1-28, 2025, doi: 10.1145/3695999. (P08, đọc toàn văn)

[9] L. Zhang et al., “ThinkFL: Self-Refining Failure Localization for Microservice Systems via Reinforcement Fine-Tuning,” *ACM Transactions on Software Engineering and Methodology*, vol. 35, no. 9, pp. 1-44, 2026, doi: 10.1145/3789262. (P09, đọc toàn văn)

[10] K. Xv et al., “Making Fault Localization in Online Service Systems More Actionable and Interpretable,” *ACM Transactions on Software Engineering and Methodology*, vol. 34, no. 6, pp. 1-26, 2025, doi: 10.1145/3714466. (P10, đọc toàn văn)

[11] H. Zhou, M. Kulkarni, H. Chen, Y. Xin, and C. J. Zhang, “Large Language Models (LLMs) for Telecom Root Cause Analysis (RCA): A Structured Reasoning Framework for Evidence-Grounded Diagnosis,” *IEEE Wireless Communications*, pp. 1-10, 2026, doi: 10.1109/mwc.2026.3734923. (P11, đọc toàn văn)

[12] F. Hadadi, Q. Xu, D. Bianculli, and L. Briand, “LLM Meets ML: Data-efficient Anomaly Detection on Unstable Logs,” *ACM Transactions on Software Engineering and Methodology*, vol. 35, no. 8, pp. 1-48, 2026, doi: 10.1145/3771283. (P12, đọc toàn văn)

[13] M. Bilal, J. Crowcroft, R. Wang, X. Xu, and S. Dustdar, “Large language models for agentic NetOps and AIOps: Architectures, evaluation, and safety,” *Computer Science Review*, vol. 63, Art. no. 101075, 2027, doi: 10.1016/j.cosrev.2026.101075. (P13, đọc toàn văn)

[14] Z. Chang et al., “CausalDX: Diagnosing Long-Tail and Cascading Cloud Incidents With LLM-Guided Causal Reasoning,” *IEEE Transactions on Knowledge and Data Engineering*, vol. 38, no. 10, pp. 6424-6438, 2026, doi: 10.1109/tkde.2026.3722256. (P14, đọc tóm tắt)

[15] Y. He, Y. Yang, L. Rui, and C. Wu, “Hyperbolic Spatio-Temporal Graph Learning With Agent Reasoning for Root Cause Localization in Cloud-Edge Microservices,” *IEEE Transactions on Cognitive Communications and Networking*, vol. 12, pp. 10810-10825, 2026, doi: 10.1109/tccn.2026.3715900. (P15, đọc tóm tắt)

[16] N. Fu, G. Cheng, X. Qiu, and R. Zhao, “Separating the Wheat from the Chaff: A Robust Failure Diagnosis for Microservice Systems via Uncertainty-Aware Multimodal Fusion,” *IEEE Transactions on Dependable and Secure Computing*, pp. 1-16, 2026, doi: 10.1109/tdsc.2026.3732582. (P16, đọc tóm tắt)

[17] X. Tian, S. Ying, T. Li, N. Li, C. Shi, and D. Xiao, “DCGFI: Robust and Interpretable Failure Identification Using Dual Causal Graph for Microservices on Multimodal Observability Data,” *IEEE Transactions on Dependable and Secure Computing*, vol. 23, no. 4, pp. 8685-8698, 2026, doi: 10.1109/tdsc.2026.3687558. (P17, đọc tóm tắt)

[18] L. Zhang et al., “Toward In-Depth Root Cause Localization for Microservices With Multi-Agent Recursion-of-Thought,” *IEEE Transactions on Dependable and Secure Computing*, vol. 23, no. 5, pp. 10702-10719, 2026, doi: 10.1109/tdsc.2026.3706572. (P18, đọc toàn văn)

[19] Y. Sun et al., “A Comprehensive Benchmark and Empirical Study of Trace Anomaly Detection,” *IEEE Transactions on Services Computing*, vol. 18, no. 6, pp. 3364-3377, 2025, doi: 10.1109/tsc.2025.3622122. (P19, đọc tóm tắt)

[20] G. Tan et al., “LLMRCA: Multilevel Root Cause Analysis for LLM Applications Using Multimodal Observability Data,” *ACM Transactions on Software Engineering and Methodology*, Art. no. 3806200, 2026, doi: 10.1145/3806200. (P20, đọc toàn văn)

[21] B. Żurkowski and K. Zieliński, “Root Cause Analysis for Cloud-Native Applications,” *IEEE Transactions on Cloud Computing*, vol. 12, no. 1, pp. 232-250, 2024, doi: 10.1109/tcc.2024.3358823. (P21, đọc tóm tắt)

[22] H. Dou, S. Guo, L. Zou, Y. Zhang, P. Chen, and Z. Zheng, “Uncertainty-Aware Multimodal Anomaly Detection for Microservice Systems With Active Learning,” *IEEE Transactions on Services Computing*, vol. 19, no. 3, pp. 2562-2575, 2026, doi: 10.1109/tsc.2026.3672587. (P22, đọc tóm tắt)

[23] X. Huang et al., “UDA-RCL: Unsupervised Domain Adaptation for Microservice Root Cause Localization Utilizing Multimodal Data,” *IEEE Transactions on Services Computing*, vol. 19, no. 2, pp. 1661-1672, 2026, doi: 10.1109/tsc.2025.3646329. (P23, đọc tóm tắt)

[24] Z. Zhong et al., “LLM-Enhanced Failure Localization in Microservices: Integrating Multi-Modal Data and Expert Interpretation,” *IEEE Transactions on Services Computing*, vol. 19, no. 3, pp. 2275-2288, 2026, doi: 10.1109/tsc.2026.3676262. (P24, đọc tóm tắt)

[25] D. F. Pedroso, L. Almeida, L. E. G. Pulcinelli, W. A. A. Aisawa, I. Dutra, and S. M. Bruschi, “Anomaly Detection and Root Cause Analysis in Cloud-Native Environments Using Large Language Models and Bayesian Networks,” *IEEE Access*, vol. 13, pp. 77550-77564, 2025, doi: 10.1109/access.2025.3565220. (P25, đọc tóm tắt)

[26] J. Yang, Y. Guo, Y. Chen, and Y. Zhao, “MicroNet: Operation Aware Root Cause Identification of Microservice System Anomalies,” *IEEE Transactions on Network and Service Management*, vol. 21, no. 4, pp. 4255-4267, 2024, doi: 10.1109/tnsm.2024.3387552. (P26, đọc tóm tắt)

[27] T. Wang, G. Qi, and T. Wu, “KGroot: A knowledge graph-enhanced method for root cause analysis,” *Expert Systems with Applications*, vol. 255, Art. no. 124679, 2024, doi: 10.1016/j.eswa.2024.124679. (P27, đọc tóm tắt)

[28] J. Owotogbe, I. Kumara, W. J. Heuvel, and D. Tamburri, “Chaos Engineering: A Multi-Vocal Literature Review,” *ACM Computing Surveys*, vol. 58, no. 7, pp. 1-44, 2025, doi: 10.1145/3777375. (P28, đọc toàn văn)

[29] X. Tian, S. Ying, T. Li, C. Shi, and D. Xiao, “CRFD: Causal and Interpretable Fault Diagnosis Using Counterfactual Reasoning for Microservices on Multi-source Observability Data,” *ACM Transactions on Software Engineering and Methodology*, vol. 35, no. 10, pp. 1-33, 2026, doi: 10.1145/3796706. (P29, đọc toàn văn)

[30] M. Hui et al., “ChatRCA: A Root Cause Analysis Method via LLMs-based Multi-Agent with Human-in-the-Loop,” *ACM Transactions on Software Engineering and Methodology*, Art. no. 3842744, 2026, doi: 10.1145/3842744. (P30, đọc toàn văn)

[31] F. Fu, H. Ding, Y. Qin, J. Yu, and D. Xu, “Leveraging multi-agent framework for root cause analysis,” *Complex & Intelligent Systems*, vol. 12, no. 1, Art. no. 4, 2025, doi: 10.1007/s40747-025-02096-0. (P31, đọc toàn văn)

[32] Z. Zhang, S. Li, L. Zhang, J. Ye, C. Hu, and L. Yan, “LLM-LADE: Large language model-based log anomaly detection with explanation,” *Knowledge-Based Systems*, vol. 326, Art. no. 114064, 2025, doi: 10.1016/j.knosys.2025.114064. (P32, đọc tóm tắt)

[33] J. Li and S. Ying, “TCRCA: Topology-Guided Causal Inference for Root Cause Analysis in Microservices,” *IEEE Transactions on Software Engineering*, pp. 1-20, 2026, doi: 10.1109/tse.2026.3715410. (P33, đọc tóm tắt)

[34] I. Lera, J. Martinez-Gil, and C. Guerrero, “SOAR: Evaluating the reasoning capabilities of large language models on IT operational data,” *Future Generation Computer Systems*, vol. 187, Art. no. 108757, 2027, doi: 10.1016/j.future.2026.108757. (P34, đọc toàn văn)

[35] P. Wang, X. Zhang, and Z. Cao, “Anomaly detection for microservice system via augmented multimodal data and hybrid graph representations,” *Information Fusion*, vol. 118, Art. no. 103017, 2025, doi: 10.1016/j.inffus.2025.103017. (P35, đọc tóm tắt)

[36] H. Liu et al., “UAC-AD: Unsupervised Adversarial Contrastive Learning for Anomaly Detection on Multi-Modal Data in Microservice Systems,” *IEEE Transactions on Services Computing*, vol. 17, no. 6, pp. 3887-3900, 2024, doi: 10.1109/tsc.2024.3411481. (P36, đọc tóm tắt)

[37] P. Zhang, J. Wu, H. He, L. Yan, and W. Li, “Topo-MFP: Topology-aware multimodal propagation learning for fault detection and root cause localization in microservice systems,” *Journal of King Saud University Computer and Information Sciences*, vol. 38, no. 7, Art. no. 780, 2026, doi: 10.1007/s44443-026-01193-5. (P37, đọc toàn văn)

[38] Y. Wang et al., “Graph Structure-Enhanced Large Language Model for Optical Network Fault Diagnosis: An Explainable Alarm Root Cause Localization Approach,” *IEEE Internet of Things Journal*, vol. 12, no. 15, pp. 31493-31510, 2025, doi: 10.1109/jiot.2025.3573056. (P38, đọc tóm tắt)

[39] P. Wang, X. Zhang, Y. Chen, and Z. Cao, “Unsupervised microservice system anomaly detection via contrastive multi-modal representation clustering,” *Information Processing & Management*, vol. 62, no. 3, Art. no. 104013, 2025, doi: 10.1016/j.ipm.2024.104013. (P39, đọc tóm tắt)

[40] H. Chen, P. Chen, G. Yu, X. Li, and Z. He, “MicroFI: Non-Intrusive and Prioritized Request-Level Fault Injection for Microservice Applications,” *IEEE Transactions on Dependable and Secure Computing*, vol. 21, no. 5, pp. 4921-4938, 2024, doi: 10.1109/tdsc.2024.3363902. (P40, đọc tóm tắt)

[41] G. No, Y. Lee, H. Kang, and P. Kang, “Training-free retrieval-based log anomaly detection with pre-trained language model considering token-level information,” *Engineering Applications of Artificial Intelligence*, vol. 133, Art. no. 108613, 2024, doi: 10.1016/j.engappai.2024.108613. (P41, đọc toàn văn)

[42] H. Zhang, Y. Zhang, Q. Ni, T. Li, and Y. Zou, “Trustworthy root cause analysis for distributed systems via neurosymbolic fusion,” *Results in Engineering*, vol. 30, Art. no. 110491, 2026, doi: 10.1016/j.rineng.2026.110491. (P42, đọc toàn văn)

[43] N. P. Tran, B. Jaumard, O. Delgado, T. Glatard, K. Premkumar, and K. Ni, “LLM-Augmented Knowledge Base Construction for Root Cause Analysis,” *IEEE Access*, vol. 14, pp. 16802-16816, 2026, doi: 10.1109/access.2026.3658655. (P43, đọc toàn văn)

[44] C. S. Mala, G. Gezici, and F. Giannotti, “Disentangling Faithfulness Hallucinations in Retrieval-Augmented Generation: A Systematic Benchmark and Analysis,” *Machine Learning*, vol. 115, no. 8, Art. no. 187, 2026, doi: 10.1007/s10994-026-07121-y. (P44, đọc toàn văn)

[45] Y. Xiao, S. Li, and Y. Ge, “RunbookFX: Type- and Effect-Safe LLM Synthesis for Executable Incident Diagnosis and Mitigation,” *Proceedings of the ACM on Programming Languages*, vol. 10, no. ICFP, pp. 66-99, 2026, doi: 10.1145/3828675. (P45, đọc toàn văn)

[46] W. Choi et al., “LogRAIL: A Retrieval-Augmented LLM Reverification Layer for Log Anomaly Detection,” *IEEE Access*, vol. 14, pp. 65899-65911, 2026, doi: 10.1109/access.2026.3688834. (P46, đọc tóm tắt)

[47] S. Jang, T. Park, H. Yi, and C. Choi, “CausalOpsBench: A Reproducible Interventional-Replay Benchmark for Topology-Aware Operational Incident Response,” *IEEE Access*, vol. 14, pp. 107820-107838, 2026, doi: 10.1109/access.2026.3710824. (P47, đọc tóm tắt)

[48] R. Kapoor and M. Kas, “Breaking the Observability Tax: Dynamic Resolution Anomaly Detection via Topology-Aware Active LLM Agents,” *IEEE Access*, vol. 14, pp. 43552-43568, 2026, doi: 10.1109/access.2026.3675074. (P48, đọc tóm tắt)

[49] M. A. R. Mustafa and Q. Mamun, “Quality–Latency Benchmarking of Log-Template Retrieval for GenAI-Assisted Operational RCA,” *Applied Artificial Intelligence*, vol. 40, no. 1, Art. no. 2684312, 2026, doi: 10.1080/08839514.2026.2684312. (P49, đọc toàn văn)

[50] A. R. Fauzi, S. N. Pratama, A. Purqon, Y. Z. Ramadhan, and M. Ardiansyah, “When RAG hurts: Retrieval-augmented generation degrades performance in metallurgical root cause analysis,” *Results in Engineering*, vol. 32, Art. no. 113136, 2026, doi: 10.1016/j.rineng.2026.113136. (P50, đọc toàn văn)

[51] W. Zhou et al., “DBAIOps: A Reasoning LLM-Enhanced Database Operation and Maintenance System using Knowledge Graphs,” *Proceedings of the VLDB Endowment*, vol. 19, no. 6, pp. 1319-1331, 2026, doi: 10.14778/3797919.3797937. (P51, đọc toàn văn)

[52] J. Ahmed Khan, M. Molan, and A. Bartolini, “EXASAGE: The first data center operational data analysis assistant,” *Future Generation Computer Systems*, vol. 176, Art. no. 108185, 2026, doi: 10.1016/j.future.2025.108185. (P53, đọc toàn văn)

[53] C. Zhang et al., “PromCopilot: Simplifying Prometheus Metric Querying in Cloud Native Online Service Systems via Large Language Models,” *ACM Transactions on Software Engineering and Methodology*, vol. 35, no. 10, pp. 1-30, 2026, doi: 10.1145/3797910. (P55, đọc toàn văn)

[54] Z. Zhu, C. Lee, X. Tang, and P. He, “HeMiRCA: Fine-Grained Root Cause Analysis for Microservices with Heterogeneous Data Sources,” *ACM Transactions on Software Engineering and Methodology*, vol. 33, no. 8, pp. 1-25, 2024, doi: 10.1145/3674726. (P56, đọc toàn văn)

[55] S. Xie et al., “TVDiag: A Task-oriented and View-invariant Failure Diagnosis Framework for Microservice-based Systems with Multimodal Data,” *ACM Transactions on Software Engineering and Methodology*, vol. 35, no. 2, pp. 1-39, 2026, doi: 10.1145/3734868. (P57, đọc toàn văn)

[56] J. Chen et al., “MTG_CD: Multi-scale learnable transformation graph for fault classification and diagnosis in microservices,” *Journal of Cloud Computing*, vol. 13, no. 1, Art. no. 103, 2024, doi: 10.1186/s13677-024-00666-0. (P58, đọc toàn văn)

[57] F. Lin, K. Muzumdar, N. P. Laptev, M. V. Curelea, S. Lee, and S. Sankar, “Fast Dimensional Analysis for Root Cause Investigation in a Large-Scale Service Environment,” *Proceedings of the ACM on Measurement and Analysis of Computing Systems*, vol. 4, no. 2, pp. 1-23, 2020, doi: 10.1145/3392149. (P59, đọc toàn văn)

[58] H. Gao, R. Xin, P. Chen, X. Li, N. Lu, and P. You, “Memory-augment graph transformer based unsupervised detection model for identifying performance anomalies in highly-dynamic cloud environments,” *Journal of Cloud Computing*, vol. 14, no. 1, Art. no. 40, 2025, doi: 10.1186/s13677-025-00766-5. (P62, đọc toàn văn)

[59] Z. Zhang, J. Wang, B. Li, L. Zhang, Y. Liu, and P. Hung, “ADmM: Anomaly Detection for Microservice Systems with Incomplete Metrics,” *ACM Transactions on the Web*, vol. 20, no. 2, pp. 1-35, 2026, doi: 10.1145/3801729. (P63, đọc toàn văn)

[60] W. Gu et al., “Identifying Performance Issues in Cloud Service Systems Based on Relational-Temporal Features,” *ACM Transactions on Software Engineering and Methodology*, vol. 34, no. 3, pp. 1-31, 2025, doi: 10.1145/3702978. (P64, đọc toàn văn)

[61] I. Kohyarnejadfard, D. Aloise, S. V. Azhari, and M. R. Dagenais, “Anomaly detection in microservice environments using distributed tracing data analysis and NLP,” *Journal of Cloud Computing*, vol. 11, no. 1, Art. no. 25, 2022, doi: 10.1186/s13677-022-00296-4. (P65, đọc toàn văn)

[62] Z. Zhang, Z. Zhu, C. Xu, J. Zhang, and S. Xu, “Towards accurate anomaly detection for cloud system via graph-enhanced contrastive learning,” *Complex & Intelligent Systems*, vol. 11, no. 1, Art. no. 23, 2024, doi: 10.1007/s40747-024-01659-x. (P66, đọc toàn văn)

[63] L. Ma et al., “AdaptiveLog: An Adaptive Log Analysis Framework with the Collaboration of Large and Small Language Model,” *ACM Transactions on Software Engineering and Methodology*, vol. 35, no. 5, pp. 1-42, 2026, doi: 10.1145/3749840. (P67, đọc toàn văn)

[64] L. Ma et al., “LogReasoner: Empowering LLMs with Expert-like Coarse-to-Fine Reasoning for Automated Log Analysis,” *ACM Transactions on Software Engineering and Methodology*, Art. no. 3801747, 2026, doi: 10.1145/3801747. (P68, đọc toàn văn)

[65] M. A. A. Mamun and G. Uddin, “BLAgent : Agentic RAG for File-Level Bug Localization,” *ACM Transactions on Software Engineering and Methodology*, Art. no. 3830238, 2026, doi: 10.1145/3830238. (P69, đọc toàn văn)

[66] X. Li, G. Li, J. Dong, Y. Kong, W. Hu, and T. Wang, “A Fault Diagnosis-Oriented Data-Driven Embedding Fine-Tuning and Domain-Aware Hybrid Retrieval Method for Intelligent Operation and Maintenance,” *Journal of Dynamics, Monitoring and Diagnostics*, 2026, doi: 10.37965/jdmd.2026.1505. (P70, đọc toàn văn)

[67] I. T. A. Lee, Z. Zhang, A. Parwal, and M. Chabbi, “The Tale of Errors in Microservices,” *Proceedings of the ACM on Measurement and Analysis of Computing Systems*, vol. 8, no. 3, pp. 1-36, 2024, doi: 10.1145/3700436. (P71, đọc toàn văn)

[68] C. Cao, F. Wang, L. Lindley, and Z. Wang, “Managing Linux servers with LLM-based AI agents: An empirical evaluation with GPT4,” *Machine Learning with Applications*, vol. 17, Art. no. 100570, 2024, doi: 10.1016/j.mlwa.2024.100570. (P73, đọc toàn văn)

[69] M. De la Cruz Cabello, T. P. Sales, and M. R. Machado, “AIOps for log anomaly detection in the era of LLMs: A systematic literature review,” *Intelligent Systems with Applications*, vol. 28, Art. no. 200608, 2025, doi: 10.1016/j.iswa.2025.200608. (P74, đọc toàn văn)

