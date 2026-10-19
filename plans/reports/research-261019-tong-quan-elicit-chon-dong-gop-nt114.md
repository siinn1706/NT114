---
title: "Tổng quan tài liệu (Elicit + nguồn công khai) để chọn đóng góp khoa học của NT114"
date: 2026-10-19
plan: ../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/plan.md
status: final (sửa theo review 261019-1441)
cutoff: 2026-10-19T06:58Z; vòng thách thức Perplexity 2026-10-19T08:05–08:50Z
revised: 2026-10-19
---

> **Bản sửa 2026-10-19 (chiều).** Sửa bốn điểm của
> [review 261019-1441](review-261019-1441-tong-quan-elicit-va-huong-h1.md):
> 1. Bỏ cổng AUROC ≥ 0.75; thay bằng power tính trên estimator thật.
> 2. Tách endpoint coverage cố định khỏi ngưỡng DEV đóng băng.
> 3. Hạ verdict H2.
> 4. Sửa sổ sàng lọc, PRISMA và các AC bị đánh dấu quá tay.
>
> Bằng chứng và script nằm ở [kế hoạch sửa 261019-1501](../261019-1501-sua-review-h1-power-va-sang-loc/plan.md).

# Tổng quan tài liệu để chọn đóng góp khoa học của NT114

Ngày cắt tìm kiếm: **2026-10-19T06:58Z**. Mọi khẳng định có mã `[F-xxx]` trỏ tới
[Phụ lục phát hiện](#11-phụ-lục-phát-hiện). Bảng gốc nằm trong
[work/](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/work/).

## 1. Tóm tắt quyết định

**Khuyến nghị:** giữ **H1, thu hẹp lại** làm **ứng viên ưu tiên** để kiểm trên DEV, chưa phải hướng đã
chọn. H1 chỉ lên confirmatory nếu qua quy tắc DEV pilot ở §12. Câu hỏi nghiên cứu:

> Trên benchmark RCA có nhãn fault-injection công khai, abstention bằng một quy tắc tất định trên
> confidence của chính lời gọi LLM có giảm tỉ lệ chẩn đoán sai mà tự tin, so với deferral ngẫu
> nhiên ở **cùng coverage**, khi telemetry bị bỏ có kiểm soát không? Kết quả phải được báo cáo cạnh
> các baseline đơn giản.

H3 chỉ giữ một phần nhỏ, như phân tích phụ của H1 (abstain khi root bị loại khỏi shortlist). H2 không
được ưu tiên vì hai lý do tách khỏi tính mới: chính sách thu thập do model chọn vi phạm protocol v2 §1
[F-040], và power thấp. Verdict tính mới của H2 chỉ là "dấu hiệu chồng lấn mạnh, chưa xác nhận".

| Hướng | Tính mới | Lý do chính |
|---|---|---|
| H1 | **Chồng lấn một phần**. Ô chính xác ở trên chưa thấy | Confidence cho LLM-RCA đã có, nhưng chỉ đo ECE trên dữ liệu nội bộ [F-001]. Che telemetry + abstention đã có trên trace agent tổng hợp [F-004] và hồ sơ điều tra liên ngành [F-005]. Abstention trong RCA mạng đã triển khai nhưng không dùng LLM [F-007]. Ngưỡng confidence của LLM đã dùng để điều khiển tìm kiếm trong RCA microservice, nhưng không để abstain [F-057]. Bỏ từng modality cho LLM-RCA đã có [F-055]. Trong 58 bài RCA mà SR1 trích xuất, không bài nào báo selective risk ở cùng coverage [F-009]; vòng Perplexity cũng không thấy |
| H2 | **Có dấu hiệu chồng lấn mạnh; chưa đạt điều kiện "chồng lấn có" của kế hoạch** | Không bài peer-reviewed relevance 2 nào được đọc toàn văn: TraceBudget, VerifyRCA, BudgetSRE chỉ có tóm tắt (bản OA trên ResearchGate bị chặn bởi kiểm tra bot) [F-033–F-035]. SADE đọc toàn văn nhưng là trần 20 lượt cố định trong RCA mạng [F-037]. EviRCA là preprint [F-036] |
| H3 | **Chồng lấn có** | DecompRCA (NeurIPS 2026) đã tách retrieval/reranking trên chính RE1 [F-041, F-042]. Ở NT114 `in_candidates = 1` nên phép tách suy biến thành xếp hạng [F-046] |

**Rủi ro lớn nhất của H1 là độ mạnh tín hiệu consensus chưa biết, không phải tính mới.**

- Verbal confidence chỉ phân biệt đúng/sai ở AUROC 0.51–0.65 [F-014, F-054]. Consensus (mức đồng
  thuận của nhiều mẫu) có thể tốt hơn hẳn, ví dụ 54.8 % → 92.7 % trên GSM8K, nhưng tuỳ tác vụ
  [F-054]. Self-agreement chỉ tương quan yếu với tính đúng [F-050]. Chưa có số đo nào trên RCA.
- Power đã được tính lại bằng chính estimator, có cụm injection và confidence đồng hạng (§5.4,
  [F-056]). Gain nhỏ nhất phát hiện được ở coverage 0.7 là khoảng 0.05–0.06 trên RCAEval và
  AIOps2025, chứ không phải 0.12. Đây là mô phỏng dưới giả định, không phải kết quả.

**Điều kiện làm đảo khuyến nghị:**

1. **DEV pilot không qua quy tắc §12.** Quy tắc dựa trên gain và CI của nó, không dùng AUROC làm
   cổng. Nếu cận trên 95 % của gain trên DEV nhỏ hơn SESOI, H1 thành một đánh giá phủ định có kiểm
   soát. Nếu power ở cận dưới 80 % chưa đủ, H1 chỉ ở mức thăm dò.
2. **Bị scoop.** Một bài xuất hiện đúng ô H1 trên RCAEval hoặc Nezha sẽ làm H1 mất tính mới.
3. **Thêm nhánh shortlist.** Nếu chủ dự án chấp nhận một nhánh shortlist mới, H3 phần B có thể
   thành câu hỏi riêng về "abstain khi ứng viên đúng vắng mặt" (§7).

## 2. Phương pháp tổng quan

- **Giao thức** đóng băng lúc 04:20Z
  ([search-protocol.md](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/work/search-protocol.md)),
  áp dụng tiêu chí I1–I5 / E1–E6 của Phase 01.
- **Engine:**
  - Elicit MCP: một systematic review SR1 (16 truy vấn × 100, sàng lọc abstract và toàn văn ở chế
    độ thorough) và `search_papers`.
  - arXiv API, OpenAlex (search và cited-by), Crossref, HTTP trực tiếp.
  - Perplexity Pro, chế độ Deep Research. Có 2 truy vấn công khai trong vòng thách thức H1 (bản
    sửa). Chỉ dùng để phát hiện bài; số liệu luôn lấy từ bài gốc
    ([nhật ký](../261019-1501-sua-review-h1-power-va-sang-loc/research/perplexity-challenge-log.md)).
- **Truy vấn:** 93 dòng, theo khối A–H, SR1, GAP, SNOWBALL, H-seed và planning. Mỗi dòng có chuỗi
  truy vấn, filter, giới hạn, thời điểm, số kết quả và file raw
  ([search-log.csv](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/work/search-log.csv)).
  Elicit chỉ nhận truy vấn công khai bằng tiếng Anh; không có dữ liệu, nhãn hay bằng chứng nào của
  repo được gửi đi.
- **Khử trùng lặp:** theo DOI chuẩn hoá, arXiv ID không phiên bản, rồi tiêu đề chuẩn hoá với năm
  lệch ±1. Cặp LM-PACE / PACE-LM khác tiêu đề nên được gộp tay.
- **Sàng lọc:**
  - SR1 do Elicit sàng lọc (AI) theo tiêu chí của giao thức.
  - 699 công trình ngoài SR1 **chỉ** qua một luật từ khoá trên tiêu đề (ghi trong
    `prisma-counts.json`); 279 qua luật. Không có quyết định include/exclude hay relevance H1/H2/H3
    thủ công cho từng bài như Phase 03 yêu cầu. Người thực thi chỉ đọc kỹ các bài quyết định (17 bài
    trích xuất và các bài có phát hiện).
  - Sổ sàng lọc theo từng công trình, kèm phương pháp và trạng thái cuối:
    [screening.csv](../261019-1501-sua-review-h1-power-va-sang-loc/work/out/screening.csv).
- **Độ tin cậy sàng lọc:** người thực thi kiểm tay quyết định của Elicit.
  - Mẫu seed 127 bản ghi (95 giữ, 32 loại), bổ sung 7 bản ghi bị loại (seed riêng) để đủ 10 % của
    390 bản ghi bị loại. Tổng 134.
  - Đồng thuận 126/134 (94.0 %), Cohen κ = 0.864. Cả 8 bất đồng đều là Elicit nhận thừa. Ở nhóm bị
    loại: 0/39 bất đồng, dưới ngưỡng 10 % nên không phải sàng lọc lại toàn nhóm.
  - Chi tiết: [screening-check.csv](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/work/screening-check.csv),
    [bổ sung](../261019-1501-sua-review-h1-power-va-sang-loc/work/out/screening-check-supplement.csv).
  - **Sàng lọc lại có trễ ≥ 24 giờ: chưa làm.** Mẫu 30 bài, che quyết định cũ, đã được rút sẵn
    ([delayed-rescreen-sample.csv](../261019-1501-sua-review-h1-power-va-sang-loc/work/out/delayed-rescreen-sample.csv)).
    Chỉ hợp lệ từ **2026-10-20 13:42 (giờ VN)**.
- **Trích xuất:** làm tay từ toàn văn
  ([extraction.csv](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/work/extraction.csv),
  17 bài quyết định). Bảng trích xuất của Elicit chỉ được dùng cho đếm tổng hợp [F-009].
- **Sai lệch so với giao thức:**

  | ID | Sai lệch |
  |---|---|
  | D1 | `maxResults` 50 thay vì 200 |
  | D2 | File raw dạng CSV rút gọn |
  | D3 | Không có `useFigures` |
  | D4 | Chỉ một systematic review |
  | D5 | Export tải bằng script, không in URL có token |
  | D6 | Hết hạn mức Elicit; phần còn lại chạy trên nguồn ngoài |
  | D7 | Trích xuất tay thay cho bảng Elicit |
  | D8 | Phát hiện nội bộ dùng `repo:<đường dẫn>` thay URL `http` |
  | D9 | Sàng lọc ngoài SR1 chỉ bằng luật tiêu đề; không có relevance 0/1/2 theo từng bài (Phase 03) |
  | D10 | Vòng thách thức H1 bổ sung dùng Perplexity Deep Research (bản sửa) |

## 3. PRISMA

| Bước | Số |
|---|---:|
| Bản ghi tìm được | **2,255** |
| ↳ Elicit systematic review SR1 | 1,267 |
| ↳ Elicit `search_papers` (E-S1, F-S1) | 60 |
| ↳ arXiv API (khối A–H, tra tiêu đề, GAP) | 286 |
| ↳ OpenAlex search (khối A–G, GAP) | 360 |
| ↳ Snowball OpenAlex (ngược 134, xuôi 101) | 235 |
| ↳ Hạt giống từ kế hoạch 261011 | 47 |
| Trùng lặp bị loại | 297 |
| **Công trình duy nhất** | **1,958** = 1,259 có nguồn SR1 + 699 ngoài SR1 |

Từ bước này, số **bản ghi** (dòng export) và số **công trình** (sau khử trùng lặp) được tách riêng.
Bản trước ghép thẳng 1,267 bản ghi SR1 với 699 công trình, nên thừa 8.

| Bước SR1 | Bản ghi | Công trình |
|---|---:|---:|
| Đầu vào SR1 | 1,267 | 1,259 (8 bản ghi trùng trong SR1; 2 trong số đó là biến thể tiêu đề gộp tay: PACE/LM-PACE, I-CALM) |
| Loại ở abstract (kèm tiêu chí) | 390 | 389 |
| Chuyển sang toàn văn | 877 | 870 |
| ↳ **Không lấy được toàn văn** (Elicit ghi "Full text not available") | **286** | 284 |
| ↳ Đánh giá toàn văn | 591 | 586 |
| ↳ Loại ở toàn văn, kèm lý do | 40 (21 thiếu đánh giá định lượng, 11 ngoài miền, 4 chỉ phát hiện + ngoài miền, 4 chỉ phát hiện) | 40 |
| ↳ **Giữ** | **551** | 546 |
| Có dữ liệu trích xuất của Elicit | 144 / 551 (review dừng vì hết hạn mức) | — |

Bản trước nói "310 bản ghi loại ở toàn văn không ghi tiêu chí". Thực ra cột `Exclusion reason` của
export có ghi: 286 là "Full text not available" (theo PRISMA: *reports not retrieved*, **không** phải
loại theo nội dung), và 24 có lý do nội dung. Chúng chỉ không nằm ở cột `Criteria not met`.

| Ngoài SR1 (công trình) | Số |
|---|---:|
| Tổng | 699 |
| Qua luật từ khoá tiêu đề, **chưa sàng lọc tay từng bài** | 279 |
| Không qua luật tiêu đề | 420 |

| Khác | Số |
|---|---:|
| Toàn văn người thực thi tự đọc | 38 file (35 + 3 trong bản sửa: 2306.13063, 2605.04530, 2608.08968) |
| Thêm từ snowballing | 196 công trình chỉ đến từ snowball; **0** bài relevance 2 mới |
| Phát hiện trong báo cáo | 57 (53 + F-054–F-057) |

Sơ đồ dạng văn bản:

```text
Elicit SR1 1,267 ┐
Elicit search 60 ├─► 2,255 bản ghi ─► khử trùng lặp (−297) ─► 1,958 công trình
arXiv 286        │     ├─ SR1: 1,267 bản ghi = 1,259 công trình
OpenAlex 360     │     │     ─abstract─► 877 bản ghi ─┬─ không lấy được toàn văn 286
Snowball 235     │     │                              ├─ loại toàn văn có lý do 40
Seed 47          ┘     │                              └─ giữ 551 ─trích xuất Elicit─► 144
                       └─ ngoài SR1: 699 công trình ─luật tiêu đề─► 279 (chưa sàng lọc tay)
                       đọc toàn văn: 38 ─► 57 phát hiện
```

Số liệu máy đọc:
[prisma-flow.json](../261019-1501-sua-review-h1-power-va-sang-loc/work/out/prisma-flow.json) (bản sửa),
[prisma-counts.json](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/work/prisma-counts.json) (bản đầu),
[corpus.csv](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/work/corpus.csv).

## 4. Năng lực Elicit MCP đã dùng và giới hạn quan sát được

Chi tiết trong [hồ sơ năng lực](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/research/elicit-mcp-capability-record.md)
và [usage-log.csv](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/work/usage-log.csv).

| Năng lực | Quan sát |
|---|---|
| `search_papers` | Chế độ semantic và keyword. Trần `maxResults` 300. Không làm tăng `percentUsed`, nhưng **bị chặn khi hạn mức đã hết** |
| `create_systematic_review` | Chạy được. `useFigures: true` bị từ chối (`figure_extraction_required`). Một review thorough dùng **0 → 24 % → 100 %** hạn mức tháng |
| Export của review | CSV qua URL S3 pre-signed có token, tải bằng script và không in URL |
| Toàn văn trong thư viện | Có cho PDF arXiv; DecompRCA không có |
| Citation API | Không có. Snowball chạy trên OpenAlex |

**Chặn truy cập:**

- Hạn mức Elicit hết lúc 06:29Z. SR1 dừng ở trạng thái `pausedForInsufficientQuota`, giai đoạn
  trích xuất.
- Mọi lệnh Elicit sau đó thất bại (`insufficient_quota`). Hạn mức đặt lại lúc **2026-11-18T16:00Z**.
- Vì vậy vòng gap (§9) chạy trên arXiv và OpenAlex. Phase 07 mục A.2 yêu cầu chạy cả trên Elicit;
  phần đó không thực hiện được.

## 5. H1: confidence, abstention và telemetry bị thiếu

### 5.1 Bài gần nhất và phần đã làm

| Bài | Đã làm | Chưa làm (so với H1) |
|---|---|---|
| LM-PACE (FSE Companion 2024) [F-001, F-002] | Confidence GPT-4 cho RCA sự cố cloud; ECE và reliability diagram; 121,308 sự cố Microsoft | Không có selective risk, không bỏ telemetry có kiểm soát, nhãn là pseudo-label, dữ liệu kín |
| TelemetrySuffBench (arXiv 08/2026) [F-004] | Mặt nạ 7 yếu tố telemetry; abstention an toàn; 5 LLM frontier; evidence gating giảm câu trả lời không có căn cứ 12.5–48.6 pp ở 3 model, 2 model không bao giờ abstain | Trace agent tổng hợp, không phải microservice; không có risk ở cùng coverage |
| Nautil (arXiv 10/2026) [F-005, F-006] | Bỏ căn cứ của kết luận một cách phản thực, so với đối chứng ghép cặp; tỉ lệ đóng hồ sơ chỉ giảm 6–7 điểm ở model gốc và frontier | Chủ yếu là báo cáo tai nạn; ca server không có root cause chuẩn; không có coverage |
| CoreSec (arXiv 08/2026) [F-007] | Đại số abstention trong RCA mạng Azure, đang chạy production | Không dùng LLM, không có số selective |
| AutoCrashFL (ICSE SEIP 2025) [F-003] | Confidence từ nhiều lần chạy; point-biserial 0.23; Brier 0.357 → 0.199 sau Platt | Định vị crash, không có risk–coverage |
| JustDiag [F-025] | Non-closure có hiệu chỉnh; outcome 51.0 → 57.7; completion 65/66 → 62/66 | 66 sự cố kín, không so ở cùng coverage |
| GALA+ (ASE 2026) [F-057] | LLM sinh confidence cho từng ứng viên microservice; ngưỡng θ ≈ 0.6 quyết định dừng hay mở rộng tìm kiếm trên đồ thị | Không abstain, không calibration, không risk–coverage |
| Holdout modality cho LLM-RCA (FORGE@ICSE 2026) [F-055] | Bỏ từng modality: bỏ metric mất nhiều localisation nhất (ΔLA −0.155), bỏ log hại fault type, bỏ trace có khi *tốt hơn* | Không đo confidence hay abstention |
| Missing-modality RCA không dùng LLM [F-010–F-013] | Thiếu modality hoặc metric có kiểm soát (ARMOR, TopoRCA-Lite 0–60 % trên RCAEval, PORCA, ReconRCA) | Không đo confidence |
| Conformal RCA [F-008] | Tập tin cậy hợp lệ với mẫu hữu hạn cho root-cause index (CROC) | Thống kê, không dùng LLM |
| Remediation an toàn [F-052] | CMDP giới hạn tỉ lệ remediation sai | Phía remediation, không phải chẩn đoán |
| Partial Evidence Bench [F-048] | Agent bị giới hạn quyền truy cập bằng chứng nhưng đầu ra trông vẫn đầy đủ | Bối cảnh agent doanh nghiệp, không phải RCA |

### 5.2 Khoảng trống còn lại

Đếm trên bảng trích xuất SR1, với 58 bài có tiêu đề về RCA, fault localisation hay incident [F-009]:

- 0 bài báo selective prediction ở cùng coverage; 4 bài báo một phần.
- 42 bài không có nguồn confidence nào.
- 16 bài bỏ modality có kiểm soát.
- Chỉ 3 bài có cả hai: AutoCrashFL, Eadro và TVDiag. Không bài nào dùng verbal confidence hay
  consensus của LLM.

Vòng gap với ngày cắt 2026 [F-050–F-053] không tìm thấy bài nào đúng ô này. Vòng thách thức bằng
Perplexity Deep Research (hai truy vấn, 2026-10-19) cũng không. Nó chỉ thêm GALA+ [F-057] và bài
holdout modality [F-055], cả hai đã được đối chiếu toàn văn. Đây vẫn là kết luận vắng mặt: vắng mặt
trong tìm kiếm không chứng minh tính mới.

Phần đóng góp NT114 còn nhận được:

1. **Thước đo.** Selective risk và AURC của confidence của chính lời gọi, so với deferral ngẫu
   nhiên (C2) và ngưỡng ghép coverage (C1).
2. **Thao tác.** Bỏ modality có kiểm soát (`metrics_only`, `no_log`, `no_trace`) và `blind_root`
   trên nhãn fault-injection công khai (RCAEval, Nezha, AIOps2025).
3. **Baseline.** Baseline đơn giản (B1 max-z) là bắt buộc, vì heuristic theo luật đã ngang SOTA trên
   chính Nezha và RCAEval [F-031, F-032].
4. **Thao tác so với lỗi tự nhiên.** Bỏ telemetry được đóng khung là **stress test có kiểm soát**,
   không phải nguyên nhân chính của lỗi tự nhiên: trên OpenRCA, phần lớn lỗi là reasoning gap
   [F-027].

### 5.3 Bảng phản chứng (bắt buộc theo AC8)

| Hàng bắt buộc | Bằng chứng | Hướng | Transfer |
|---|---|---|---|
| Verbal confidence không theo tính đúng | VC có AUROC 0.51–0.65, so với 0.62–0.80 của log-prob đã hiệu chỉnh; VC dự đoán abstention độc lập với tính đúng [F-014]. GPT-4 verbal trung bình 62.7 % [F-054]. Reranker LLM quá tự tin [F-016]. Evidence tool gây quá tự tin [F-051]. **Giới hạn của phản chứng:** estimator chính của H1 là consensus, không phải verbal; consistency 5 mẫu tăng AUROC GSM8K từ 54.8 % lên 92.7 % [F-054] | contradicts verbal; chưa quyết định cho consensus | out-of-domain / adjacent |
| Entropy hoặc tín hiệu đơn không đủ | Có vùng "confidently wrong" với entropy thấp [F-015]. Self-agreement chỉ có rho 0.20–0.59 [F-050]. Hiệu chỉnh hậu kỳ không cải thiện khả năng phân biệt [F-024] | contradicts | out-of-domain / adjacent |
| Abstention thất bại khi thông tin bị bỏ hoặc dưới shift | Confidence không nhạy với việc bỏ đáp án (MedMCQA) [F-017]. Bỏ gold context [F-018]. AbstentionBench: reasoning fine-tuning làm abstention giảm 24 % [F-019]. Detection-to-abstention gap [F-021]. Bất định gần ngẫu nhiên khi câu hỏi mơ hồ [F-022]. Nautil: model frontier gần như không phản ứng khi căn cứ bị bỏ [F-005] | contradicts tự-abstention; supports dùng quy tắc tất định | out-of-domain / adjacent |
| Lợi ích biến mất ở cùng coverage | Không có nghiên cứu RCA nào đo [F-009]. Mô phỏng thiết kế §5.4: tín hiệu cỡ AUROC 0.55–0.62 cho gain khoảng 0.02–0.05, nằm quanh hoặc dưới MDE [F-056]. AUROC không xác định duy nhất gain | chưa có bằng chứng trực tiếp; rủi ro trung bình | — |
| Lỗi tự nhiên không do thiếu dữ liệu | Trên OpenRCA, bằng chứng cần thiết có mặt trong phần lớn ca lỗi [F-027] | thách thức động cơ | in-domain |
| Hỗ trợ tiền đề | PACE: COE thấp dẫn tới ước lượng quá cao root cause sai [F-002]. Model lớn hơn ít né câu hỏi hơn nhưng trả lời sai nhiều hơn [F-020]. OpenSec: 82.5 % false positive [F-026]. TelemetrySuffBench: gating có ích ở 3/5 model [F-004] | supports | in-domain / adjacent |

Một ý tưởng hiệu quả nhưng **không dùng được**: dùng bất đồng giữa nhiều model làm tín hiệu
[F-023]. Cách này vi phạm §1 của protocol v2 [F-040].

### 5.4 Cỡ mẫu và power

Bản trước suy power bằng cách chia MDE của AC@1 cho √coverage. Từ đó nó đặt ngưỡng AUROC ≈ 0.75–0.78
làm cổng. Cách này sai estimator. MDE 0.10 của research/06 thuộc phép so sánh AC@1 ghép cặp giữa hai
arm. Contrast H1 là lỗi nền trừ selective risk trên **cùng** mẫu, có covariance và phương sai khác hẳn.
Cổng đó bị bỏ. Phần dưới thay bằng mô phỏng thiết kế
([chi tiết](../261019-1501-sua-review-h1-power-va-sang-loc/research/h1-endpoint-va-power.md), [F-056]).
Mô phỏng dùng các thành phần thật:
- estimator thật của `rca.metrics` và `rca.selective`;
- cụm injection thật;
- consensus 11 mức, có đồng hạng;
- percentile cluster bootstrap;
- α đơn lẻ và α Holm (0.05/3).

- **Cỡ mẫu độc lập (test):**
  - RCAEval `full`: 218.
  - **RCAEval gộp single-modality: 108 injection / 285 bản ghi.** 110/218 injection test chỉ có metric
    tự nhiên, nên không bỏ modality được.
  - Giao `blind_root` ∩ `blind_nonroot_ev`: 52.
  - Nezha: 97.
  - RCA100: 70 injection (86 bản ghi).
  - AIOps2025: 318, bảng riêng.
- **Hai phép đánh giá khác nhau, phải tách:**
  - **E1, coverage cố định:** trả lời đúng 70 % trọng số có score cao nhất. Nhóm đồng hạng ở biên
    được tính theo kỳ vọng tie-break ngẫu nhiên của C1. So với C2 giải tích (risk của C2 = lỗi nền ở
    mọi coverage).
  - **E2, ngưỡng DEV đóng băng:** `tau` fit trên DEV, áp lên test. Báo coverage thực, rồi so với C2
    ở chính coverage đó.
  - Nếu trả lời trọn nhóm đồng hạng (`selective_risk_at` hiện tại), coverage thực trong mô phỏng là
    ≈ 0.77, không phải 0.7.
- **MDE của E1** (gain ở c = 0.7, power 0.80, α 0.05; Holm k = 3 trong ngoặc):

  | Tập | Lỗi nền 0.2 | 0.35 | 0.5 |
  |---|---:|---:|---:|
  | RCAEval `full` | 0.055 (0.061) | 0.064 (0.072) | 0.060 (0.072) |
  | RCAEval gộp single-modality | 0.046 (0.056) | 0.052 (0.065) | 0.053 (0.065) |
  | AIOps2025 | 0.046 (0.053) | 0.050 (0.060) | 0.050 (0.057) |
  | Nezha | 0.080 | 0.090 | 0.093 |
  | RCA100 | 0.088 | 0.102 | 0.102 |
  | Giao 52 | > 0.09 | > 0.11 | > 0.11 |

- **Đọc kết quả:**
  - Lỗi loại I dưới H0 ở α 0.05 là 0.009–0.026 (danh nghĩa một phía 0.025), nên phép thử đúng mức
    hoặc bảo thủ.
  - Với bộ sinh này, MDE trên RCAEval và AIOps2025 tương ứng tín hiệu cỡ AUROC 0.61–0.67. Đây
    **không** phải ngưỡng: hai thứ tự có cùng AUROC 13/21 cho risk 1/7 và 2/7 ở c = 0.7 (test
    `test_same_auroc_different_selective_risk`).
  - Nếu consensus chỉ mạnh như verbal confidence trong tài liệu [F-014, F-054], gain trong bộ sinh này
    chỉ khoảng 0.02–0.05 (AUROC 0.55–0.62), quanh hoặc dưới MDE, và H1 thiếu power. Nếu consensus tách lỗi tốt như trong [F-054], H1 đủ power trên
    RCAEval và AIOps2025.
  - E2 có power thấp hơn E1. Coverage thực trên test có khoảng 90 % là 0.65–0.82.
  - Contrast "thiếu telemetry làm abstention hữu ích hơn" (DiD gain gộp − gain `full`, 108 injection)
    có power ≤ 0.46 ngay cả với khác biệt tín hiệu lớn. Nó chỉ ở mức thăm dò.
  - Nezha, RCA100 và giao 52 chỉ ở mức thăm dò.
- **Bảng binormal cũ**
  ([selective-gain-table.txt](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/work/selective-gain-table.txt))
  giữ lại làm sensitivity về độ lớn gain, không dùng cho power.
- **AC@1 ghép cặp** (MDE 0.10 / 0.18 / 0.14 / 0.16 / 0.08 [F-047]) vẫn áp dụng cho các contrast
  accuracy, không áp dụng cho H1.
- **Manipulation check (research/05):**
  - Điều kiện single-modality luôn thay đổi bằng chứng.
  - `blind_nonroot` giữ nguyên bằng chứng ở 80–98 % bản ghi, nên dùng `blind_nonroot_ev`.
  - `blind_root` trên RCA100 chỉ đổi 3/86 bản ghi, nên loại khỏi H1.

### 5.5 Thí nghiệm tối thiểu

| Thành phần | Thiết kế |
|---|---|
| Tập | Chính: RCAEval test gộp `no_metric`/`no_log`/`no_trace` (108 injection, 285 bản ghi). Phụ: RCAEval `full` (218). AIOps2025 (318) là bản lặp lớn. Nezha là phụ. DEV (78 injection gộp, 143 `full`) cho quy tắc pilot và ngưỡng E2 |
| Arm | Model chính, n = 10, T = 0.7, `retrieval ∈ {none, hybrid}` (phân tầng theo arm, xem [F-051]) |
| Estimator | consensus (chính); verbal (phụ); token probability (thăm dò, cho tới khi được kiểm trên DEV) |
| Quy tắc abstain | E1: xếp hạng theo consensus ở coverage 0.7 chọn trước, không fit. E2: ngưỡng tất định fit trên DEV, đóng băng trước test (protocol v2 §1), báo coverage thực |
| Baseline | B0, B1 max-z, L0, L1, deferral ngẫu nhiên C2, ngưỡng ghép coverage C1 |
| Endpoint | Chính: gain E1 ở c = 0.7 (§12). Phụ: lỗi nền − AURC; E2 kèm coverage thực; selective risk ở 0.5 và 0.9; confidently-wrong ở cùng coverage; Brier; AUROC/AUPRC (positive = sai); từng điều kiện riêng [F-055]; bảng shift |
| Công sức | 2–4 ngày-người phân tích trên lưới E1, không thêm lời gọi model thật ngoài E1 (research/02) |

## 6. H2: thu thập bằng chứng theo ngân sách

Hướng này được chấm trước H1 (thứ tự chấm ghi trong `direction-scores.csv`).

- **Bài gần nhất:**
  - TraceBudget: chính sách UCB và điểm dừng theo bất định; 180 sự cố; top-1 76.2 %, kém full 3.1
    pp với ít hơn 36 % token [F-033].
  - VerifyRCA: ngân sách B; top-1 0.72 trên RE2-OB ở B = 10; giảm kết luận sai mà tự tin [F-034].
  - BudgetSRE trên AIOpsLab [F-035]. SADE (LCN 2026, **đã đọc toàn văn**): tách thu thập bằng chứng
    khỏi chốt giả thuyết, trong trần cố định 20 lượt. F1 tăng 36.9 pp trên 523 sự cố mạng NIKA. Trần
    cố định này không phải chính sách thu thập tối ưu theo ngân sách [F-037]. Budget-Aware Tool Use [F-038];
    EviRCA dùng ít hơn 15–26 lần token [F-036]. TELEOS chỉ là tín hiệu yếu (venue chất lượng thấp,
    dữ liệu tổng hợp) [F-039].
  - Nghiên cứu có kiểm soát về thiết kế công cụ RCA, 10/2026 [F-053].
- **Chất lượng nguồn:**
  - TraceBudget và VerifyRCA chung tác giả.
  - Danh sách tham khảo của VerifyRCA có bài lạc đề, và các bài trích dẫn xuôi đều lạc đề [F-049].
  - Chỉ đọc được tóm tắt [F-033, F-034, F-035].
    - OpenAlex ghi cả ba có bản truy cập mở qua DOI ResearchGate. Bản trước ghi "IEEE kín, không có
      arXiv"; ghi như vậy chưa đủ chính xác.
    - Khi thử mở, ResearchGate hiện kiểm tra bot của Cloudflare. Người thực thi không giải CAPTCHA,
      nên toàn văn vẫn `unavailable`.
    - Chủ dự án có thể tự tải về `private/fulltext/261019/` để hoàn tất xác minh.
- **Protocol v2:** không tương thích trực tiếp. Chính sách thu thập do model chọn vi phạm §1
  [F-040]. Chỉ chấp nhận được dạng replay offline với một quy tắc tất định trên consensus.
  Endpoint accuracy–budget chưa có trong protocol.
- **Power:** khoảng 69 sự cố có trace; MDE từ 12 pp trở lên, trong khi khác biệt kỳ vọng chỉ vài
  điểm [F-033, F-047].
- **Đối chiếu quy tắc của kế hoạch (§5).** "Chồng lấn có" cần ≥ 1 bài peer-reviewed, relevance 2, có
  kết quả so sánh được và đã đọc toàn văn.
  - TraceBudget, VerifyRCA, BudgetSRE: peer-reviewed nhưng chỉ có tóm tắt.
  - SADE: đã đọc toàn văn nhưng khác miền (RCA mạng), và ngân sách là trần cố định. Relevance 1.
  - EviRCA: đã đọc toàn văn nhưng là preprint; giảm chi phí không đồng nghĩa với chính sách thu thập
    có ngân sách.
  - Vì vậy điều kiện **chưa đạt**.
- **Kết luận novelty:** có dấu hiệu chồng lấn mạnh, chưa xác nhận theo kế hoạch. Không nói "H2 đã
  có người làm".
- **Kết luận chọn hướng** (tách khỏi novelty): không ưu tiên H2, vì hai lý do:
  - protocol v2 §1 cấm model chọn bằng chứng theo từng incident;
  - thiếu power (khoảng 69 sự cố có trace).

  Dấu hiệu chồng lấn chỉ làm rủi ro bị scoop cao thêm.

## 7. H3 và DecompRCA

Tóm tắt [hồ sơ DecompRCA](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/research/decomprca-dossier.md):

1. **Xuất bản:** poster NeurIPS 2026 (trang hội nghị trả HTTP 200) và arXiv v1. OpenReview bị chặn
   bởi trang xác minh. Tóm tắt arXiv và tóm tắt NeurIPS lệch nhau (C1) [F-041].
2. **Artifact:** repo trả 404 cả ở web lẫn API (kiểm 06:54Z) [F-044].
3. **Phương pháp:** top@k = Retrieval@K × Rerank@k.
   - Retrieval@15 với magnitude: 1.00 / 1.00 / 0.98; với +stc: 0.98 / 1.00 / 0.91.
   - Tỉ lệ lỗi retrieval 0.00–0.09, lỗi reranking 0.10–0.26 [F-041, F-042].
4. **Dữ liệu:** RE1 125 sự cố mỗi hệ, tiền xử lý `main-ase.py`, gpt-oss-120b chạy n = 3 [F-043].
   Không khớp với tiền xử lý `main.py` của NT114.
5. **Confidence / abstention:** không đo, nên không chồng lấn H1.
6. **H3:**
   - Với `in_candidates = 1` [F-046], phép tách không còn gì để tách.
   - Phân rã giai đoạn và taxonomy lỗi cũng đã có [F-045, F-028, F-029, F-030].
   - Phần còn lại: nhánh shortlist bỏ root với K = 5 (khoảng 300 prompt) để xem model có abstain khi
     ứng viên đúng vắng mặt không. Đây thực chất là một contrast của H1, cần một arm phân tích mới.
7. **V8 bước 2 (kế hoạch 261018):** vẫn bị chặn. Khuyến nghị đổi tiêu chí sang "khớp quy trình":
   thêm biến thể theo `main-ase.py` và so với BARO 0.784 / 0.856 / 0.560.

**Power:** phần mô tả không cần kiểm định; contrast trên giao 52 sự cố có MDE 0.18 [F-047].
**Kết luận:** chồng lấn có. Chỉ giữ phần B như một phân tích phụ thăm dò của H1.

## 8. So sánh hướng

Thang 0–3 cho mỗi tiêu chí, không có trọng số ẩn; điểm cao hơn là tốt hơn cho NT114. Định nghĩa
thang ở đầu script tạo
[direction-scores.csv](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/work/direction-scores.csv).
Thứ tự chấm: H2, H3, rồi H1.

| Tiêu chí | H1 | H2 | H3 | Phát hiện |
|---|---|---|---|---|
| Tính mới | 2 (chồng lấn một phần) | 1 (dấu hiệu mạnh, chưa xác nhận; chấm lại) | 0 | F-001, F-004, F-005, F-009, F-033, F-034, F-037, F-041, F-057 |
| Phản chứng | 1 | 2 | 1 | F-014, F-015, F-017, F-027, F-042, F-054 |
| Tương thích protocol v2 | 3 | 1 | 2 | F-040, F-046 |
| Power so với MDE | 2 (chấm lại theo mô phỏng; phụ thuộc tín hiệu consensus) | 0 | 1 | F-014, F-033, F-047, F-056 |
| Manipulation check | 2 | 2 | 1 | F-047, research/05 |
| Công sức | 3 | 2 | 2 | research/02 |
| Rủi ro bị scoop | 1 | 0 | 0 | F-004, F-005, F-033, F-041, F-053, F-057 |
| **Tổng (chỉ để đọc)** | **14** | **8** | **7** | |

Hai ô được chấm lại sau review: Power của H1, và Tính mới của H2. Điểm chấm lại được ghi trong CSV.
Thứ hạng không đổi.

**Phương án kết hợp:**

- **H1 + H3 phần B** có cơ sở. Nó dùng cùng endpoint selective, và DecompRCA không đo abstention.
- **"Không hướng nào đủ mới, đóng góp là một đánh giá có kiểm soát"** có cơ sở một phần.
  - Bằng chứng: benchmark quá đơn giản và thiếu baseline đơn giản [F-031]; nhãn sự cố không tái lập
    được [F-006].
  - Đây là phương án dự phòng nếu DEV pilot rơi vào nhánh futility của quy tắc §12.

## 9. Mâu thuẫn và khẳng định đơn nguồn (vòng gap)

Vòng gap chạy trên arXiv và OpenAlex, giới hạn năm 2026: GAP-A1, A2, C1, H1, X1, X2, ngày cắt
06:58Z. Không chạy được trên Elicit (§4).

| ID | Mâu thuẫn | Giải quyết |
|---|---|---|
| C1 | DecompRCA: "79–100 %, tới +12" (arXiv) so với "78–100 %, +2 đến +26 / +9 đến +13" (NeurIPS) | **unresolved** (khác phiên bản). Trích số kèm phiên bản [F-041] |
| C2 | Retrieval@15 trên RE1-TT: 0.98 hay 0.91 | **explained**: hai biến thể retriever; pipeline dùng +stc (0.91). Ghi chú cũ của NT114 nói 0.98–1.00 đã được sửa [F-041] |
| C3 | Cỡ dữ liệu LM-PACE: 121,308 so với 103,308 | **unresolved**, gắn nhãn [F-001] |
| C4 | Thiếu bằng chứng có gây lỗi RCA không | **explained**: lỗi tự nhiên phần lớn là reasoning gap, còn bỏ telemetry là stress test [F-002, F-027] |
| C5 | Confidence LLM có hữu ích cho abstention không | **explained**: phụ thuộc tín hiệu và model; đăng ký trước consensus là chính [F-014, F-016, F-004] |
| C6 | Số sàng lọc SR1 (333/934 so với 877/390) | **explained**: ghi chú cũ sai, export là chuẩn |
| C7 | 310 bản ghi "loại ở toàn văn không ghi tiêu chí" | **explained** (bản sửa): cột `Exclusion reason` ghi 286 "Full text not available" (không lấy được, không phải loại theo nội dung) và 24 lý do nội dung |
| C8 | Ngưỡng AUROC ≈ 0.75 làm cổng so với power theo estimator | **explained** (bản sửa): ngưỡng cũ suy từ MDE của AC@1; mô phỏng với estimator E1 thay thế [F-056] |

| ID | Khẳng định đơn nguồn có hệ quả | Kết quả vòng gap |
|---|---|---|
| SS1 | Chưa ai làm đúng ô H1 [F-009] | Vẫn chưa thấy sau 6 truy vấn GAP và 2 truy vấn Perplexity Deep Research (thêm [F-055, F-057], không pre-empt). Nhãn: **ĐƠN-NGUỒN (vắng mặt)**, "chưa thấy trong corpus tính đến 2026-10-19" |
| SS2 | Số liệu của TraceBudget / VerifyRCA [F-033, F-034] | Không có bản arXiv; OpenAlex ghi bản OA trên ResearchGate nhưng người thực thi bị chặn bởi kiểm tra bot; có cờ chất lượng [F-049]. Nhãn: **ĐƠN-NGUỒN**; không dựa vào số |
| SS3 | Tỉ lệ đóng hồ sơ của model frontier chỉ giảm 7 điểm [F-005] | Được xác nhận định tính bởi [F-004, F-021] |
| SS4 | AUROC của VC là 0.51–0.65 [F-014] | Được xác nhận cho verbal bởi [F-054] (toàn văn, ICLR 2024), [F-016, F-003, F-050]. Không chuyển được sang consensus: [F-054] cho thấy consistency có thể tốt hơn nhiều. NT114 vẫn phải tự đo |
| SS5 | Lỗi RE1 chủ yếu do reranking [F-042] | Được xác nhận bởi bằng chứng nội bộ [F-046] |
| SS6 | Heuristic ngang SOTA trên Nezha / RCAEval [F-031] | Được xác nhận bởi [F-032] |

Bảng đầy đủ:
[contradictions.csv](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/work/contradictions.csv),
[single-source-claims.csv](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/work/single-source-claims.csv).

## 10. Hạn chế

- **Một người thực thi, sàng lọc chưa đủ theo Phase 03.**
  - Độ tin cậy chỉ đo được trên quyết định của Elicit ở SR1 (134 bản ghi, κ = 0.864).
  - 699 công trình ngoài SR1 chỉ qua luật tiêu đề. 279 bài ứng viên chưa có quyết định tay, và
    relevance 0/1/2 theo từng H chưa được gán cho bài nào.
  - Sàng lọc lại có trễ 24 giờ chưa làm vì chưa tới thời điểm hợp lệ.
- **Elicit:** chỉ một systematic review. Trích xuất có dữ liệu cho 144/551 bài, nên đếm tổng hợp
  [F-009] có thể bỏ sót. 286 bản ghi không lấy được toàn văn (C7). Hạn mức hết, nên vòng gap không
  có Elicit. Không có `useFigures`.
- **Toàn văn không lấy được:**
  - TraceBudget, VerifyRCA, BudgetSRE: có bản OA trên ResearchGate theo OpenAlex, nhưng bị kiểm tra
    bot chặn.
  - TopoRCA-Lite, ReconRCA: IEEE.
  - OpenReview bị chặn.
  - Các phát hiện từ những nguồn này có `verified_full_text = no` hoặc `unavailable`.
  - SADE đã đọc được qua arXiv 2605.04530 trong bản sửa.
- **Snowball.** OpenAlex không có danh sách tham khảo cho phần lớn preprint 2026. Snowball ngược
  cho các bài này làm từ toàn văn theo luật từ khoá, nên số "mới" là cận trên.
- **Power** ở §5.4 là mô phỏng thiết kế trên dữ liệu tổng hợp, có cấu trúc cụm thật. Phân bố consensus,
  ICC và đường tín hiệu là giả định (binomial-logit, ICC 0.5), chưa đo. Tỉ lệ discordance của AC@1
  vẫn là giá trị giữ chỗ (research/06).
- **Perplexity** chỉ là công cụ phát hiện. Hai claim nó nêu nhưng chưa được đối chiếu với bài gốc
  không được dùng (xem nhật ký).
- **Ngày cắt:** 2026-10-19T06:58Z. Mảng này ra bài hằng tuần (TelemetrySuffBench 08/2026, Nautil và
  [F-053] 10/2026).

## 11. Phụ lục phát hiện

Mỗi phát hiện có đủ 11 trường ở plan.md mục 6, cộng `work_id`. Nguồn máy đọc:
[findings.csv](../261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/work/findings.csv).
`FT` là `private/fulltext/261019/` (git ignore).

<!-- FINDINGS-APPENDIX -->

- **[F-001]** LM-PACE estimates GPT-4 confidence for cloud-incident root-cause generation on 121,308 internal Microsoft incidents and evaluates it with ECE and reliability diagrams only; labels are GPT-4 pseudo-labels (similarity >= 2.3)
  - `source_url`: https://doi.org/10.1145/3663529.3663858 · `work_id`: W00001 · `pub_status`: peer-reviewed: FSE Companion 2024 pp. 388-398 (Crossref); preprint arXiv 2309.05833
  - `evidence_location`: private/fulltext/261019/pace-lm-2309.05833.md L133-137 · `verified_full_text`: yes (arXiv version)
  - `uncertainty`: Split sizes (98,308 / 2,000 / 3,000) do not sum to the stated total; FSE version not read; data private
  - `decision_relevance`: Closest in-domain prior: LLM-RCA confidence is not new. H1 must claim selective risk at matched coverage under controlled telemetry removal on public fault-injection labels, none of which LM-PACE has
  - `hypothesis`: H1 · `direction`: novelty-overlap (partial) · `transfer`: in-domain
- **[F-002]** With low confidence-of-evaluation (little historical evidence) the model tends to overestimate incorrect root causes
  - `source_url`: https://arxiv.org/abs/2309.05833 · `work_id`: W00001 · `pub_status`: peer-reviewed: FSE Companion 2024
  - `evidence_location`: private/fulltext/261019/pace-lm-2309.05833.md L153 · `verified_full_text`: yes
  - `uncertainty`: Qualitative distribution reading, not a controlled ablation
  - `decision_relevance`: Supports the H1 premise that scarce evidence produces confidently wrong RCA outputs
  - `hypothesis`: H1 · `direction`: supports-premise · `transfer`: in-domain
- **[F-003]** AutoCrashFL confidence (max suspiciousness over R runs) correlates weakly with correctness (point-biserial 0.23 vs 0.57 in AutoFL); Brier 0.357 is worse than the naive 0.25 and Platt scaling brings it to 0.199
  - `source_url`: https://arxiv.org/abs/2510.22530 · `work_id`: W00074 · `pub_status`: peer-reviewed: ICSE SEIP 2025 (OpenAlex)
  - `evidence_location`: private/fulltext/261019/2510.22530.txt L444-447 · `verified_full_text`: yes
  - `uncertainty`: Crash-stack localisation at SAP HANA, not service-level RCA; single industrial system
  - `decision_relevance`: Raw LLM-derived confidence is poorly calibrated in software fault localisation; recalibration fitted on DEV is required before any abstention claim (protocol v2 already allows DEV-fit rules)
  - `hypothesis`: H1 · `direction`: counterevidence (raw confidence) / method · `transfer`: adjacent
- **[F-004]** TelemetrySuffBench masks seven telemetry factors on agent traces and tests safe abstention: evidence gating cuts unsupported unique-origin answers by 12.5-48.6 pp for three of five frontier models, while two models still answer every ambiguous case
  - `source_url`: https://arxiv.org/abs/2608.07899 · `work_id`: W01302 · `pub_status`: preprint (arXiv, Aug 2026); code at anonymous.4open.science
  - `evidence_location`: private/fulltext/261019/2608.07899.txt L18 (abstract), L27-28 · `verified_full_text`: yes
  - `uncertainty`: Synthetic delayed-binding faults in LLM-agent workflows, not microservice incidents; anonymous artifact
  - `decision_relevance`: Closest design neighbour of H1 (telemetry masking + abstention + frontier LLMs). Narrows H1 novelty to microservice RCA with fault-injection ground truth and matched-coverage selective risk
  - `hypothesis`: H1 · `direction`: novelty-overlap (partial) · `transfer`: adjacent
- **[F-005]** Nautil (731 cases incl. production server incidents) tests evidence dependence by removing a conclusion's grounds: closure falls 26 points for the fine-tuned 9B model but only 6 (base) and 7 (frontier) points; a frontier model with 84% correct causes overstates in 91% of answers and closes 17 of 41 'cause undetermined' cases
  - `source_url`: https://arxiv.org/abs/2610.03190 · `work_id`: W01214 · `pub_status`: preprint (arXiv, 2 Oct 2026); dataset and models on Hugging Face
  - `evidence_location`: private/fulltext/261019/2610.03190.txt L23-27 · `verified_full_text`: yes
  - `uncertainty`: Mostly accident reports; host incidents lack ground-truth root causes; judged with LLM judges
  - `decision_relevance`: Counterfactual evidence removal + abstention already exists outside microservice RCA; also shows prompting alone barely reacts to removed evidence, which supports measuring H1 with a deterministic rule rather than model self-abstention
  - `hypothesis`: H1 · `direction`: novelty-overlap (partial) / supports-premise · `transfer`: adjacent
- **[F-006]** Host (server-incident) labels do not reproduce: re-investigating, a frontier model closed only 5 of 39 host cases labelled should-close
  - `source_url`: https://arxiv.org/abs/2610.03190 · `work_id`: W01214 · `pub_status`: preprint (arXiv)
  - `evidence_location`: private/fulltext/261019/2610.03190.txt L1680 (Table 13) · `verified_full_text`: yes
  - `uncertainty`: Appendix result on 39 cases
  - `decision_relevance`: Incident labels from operator closure markers are unreliable; NT114's fault-injection labels are a methodological advantage worth stating
  - `hypothesis`: H1 · `direction`: method · `transfer`: adjacent
- **[F-007]** CoreSec replaces weighted score fusion with a PAM-style abstention algebra for datacenter-network RCA, giving deterministic decisions and explicit abstention when evidence is ambiguous
  - `source_url`: https://arxiv.org/abs/2608.21412 · `work_id`: W01298 · `pub_status`: preprint (arXiv, Aug 2026); Microsoft production experience
  - `evidence_location`: private/fulltext/261019/2608.21412.txt L22-23 · `verified_full_text`: yes
  - `uncertainty`: Experience paper; no public data or selective-risk numbers located
  - `decision_relevance`: Abstention for RCA under partial telemetry is deployed practice (non-LLM, rule-based); H1 cannot claim abstention in RCA as new, only its measured effect for LLMs
  - `hypothesis`: H1 · `direction`: novelty-overlap (low) · `transfer`: adjacent
- **[F-008]** CROC builds finite-sample valid conformal confidence sets for the root-cause index in multi-stream data, assuming independent streams and exchangeable pre/post-change samples
  - `source_url`: https://arxiv.org/abs/2605.21627 · `work_id`: W00765 · `pub_status`: preprint (arXiv, 2026)
  - `evidence_location`: private/fulltext/261019/2605.21627.txt L18-23 · `verified_full_text`: yes
  - `uncertainty`: Statistical change-point setting, not LLM, not microservice benchmarks
  - `decision_relevance`: A distribution-free set-valued alternative to thresholded abstention exists for RCA; usable as a related-work contrast and possibly as a non-LLM set baseline
  - `hypothesis`: H1 · `direction`: method · `transfer`: adjacent
- **[F-009]** Of 58 SR1-extracted papers whose title is RCA / fault localisation / incident, 0 report selective prediction at matched coverage ('yes'), 4 report it partially, 42 have no confidence source, 16 use controlled modality removal, and only 3 combine controlled removal with any confidence signal (AutoCrashFL, Eadro, TVDiag; none LLM-verbal or consensus)
  - `source_url`: repo:plans/261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit/work/raw/sr1/extract.csv · `work_id`: — · `pub_status`: mixed (SR1 corpus)
  - `evidence_location`: work/raw/sr1/extract.csv (title regex in the report, section 3) · `verified_full_text`: no (Elicit extraction, spot-checked for AutoCrashFL, Nezha, Eadro)
  - `uncertainty`: Elicit extracted only 144 of 551 included papers; extraction values unverified except spot checks
  - `decision_relevance`: Supports that the exact H1 cell (LLM confidence x controlled telemetry removal x matched-coverage risk on RCA benchmarks) is unfilled in the reviewed corpus
  - `hypothesis`: H1 · `direction`: supports-novelty · `transfer`: in-domain
- **[F-010]** ARMOR targets RCA under missing modality and argues unified multimodal frameworks unrealistically assume complete data; evaluated on two datasets (D1, D2)
  - `source_url`: https://arxiv.org/abs/2603.25538 · `work_id`: W00099 · `pub_status`: peer-reviewed: ASE 2026 (OpenAlex DOI 10.1145/3832783.3834338)
  - `evidence_location`: private/fulltext/261019/2603.25538.txt L41, L64, L395 · `verified_full_text`: yes
  - `uncertainty`: No confidence or abstention measured
  - `decision_relevance`: Missing-modality RCA is an active non-LLM line; H1's telemetry manipulation needs this related work and cannot claim missing-telemetry robustness itself as new
  - `hypothesis`: H1 · `direction`: novelty-overlap (manipulation only) · `transfer`: in-domain
- **[F-011]** TopoRCA-Lite evaluates RCA on RCAEval (735 cases) with missing rates from 0 to 60%
  - `source_url`: https://doi.org/10.1109/MLISE70044.2026.11607564 · `work_id`: W00183 · `pub_status`: published: IEEE MLISE 2026 (6th Int. Conf.)
  - `evidence_location`: abstract (OpenAlex/Elicit record) · `verified_full_text`: no
  - `uncertainty`: Abstract only; venue cluster shared with VeriTrail-RCA (see F-033)
  - `decision_relevance`: Same benchmark and manipulation family as NT114; a direct related-work item for H1 manipulations, not for confidence
  - `hypothesis`: H1 · `direction`: novelty-overlap (manipulation only) · `transfer`: in-domain
- **[F-012]** PORCA formulates root cause analysis with partially observed data, addressing unobserved confounders and heterogeneity
  - `source_url`: https://arxiv.org/abs/2407.05869 · `work_id`: W00391 · `pub_status`: peer-reviewed: ICDE 2026 (OpenAlex DOI 10.1109/ICDE65706.2026.00087)
  - `evidence_location`: private/fulltext/261019/2407.05869.txt L66 · `verified_full_text`: yes
  - `uncertainty`: Causal-statistical method; no LLM, no confidence
  - `decision_relevance`: Related work for 'missing telemetry' framing
  - `hypothesis`: H1 · `direction`: method · `transfer`: in-domain
- **[F-013]** ReconRCA performs microservice RCA with incomplete metrics
  - `source_url`: https://doi.org/10.1109/ICWS67624.2025.00024 · `work_id`: W00159 · `pub_status`: published: IEEE ICWS 2025
  - `evidence_location`: abstract (Elicit record) · `verified_full_text`: no
  - `uncertainty`: Abstract only
  - `decision_relevance`: Related work for missing-metric robustness
  - `hypothesis`: H1 · `direction`: method · `transfer`: in-domain
- **[F-014]** Verbal confidence tracks correctness weakly (correctness AUROC 0.51-0.65) versus calibrated log-probability (0.62-0.80) and predicts abstention independently of correctness evidence
  - `source_url`: https://arxiv.org/abs/2606.29490 · `work_id`: W00710 · `pub_status`: preprint (arXiv, 2026)
  - `evidence_location`: private/fulltext/261019/2606.29490.txt L56-58 · `verified_full_text`: yes
  - `uncertainty`: Multiple-choice and QA benchmarks (SimpleQA, MMLU-Pro, SuperGPQA, HLE)
  - `decision_relevance`: Counterevidence for verbal confidence as the abstention signal; H1 should pre-register consensus (and token probability once validated) as primary and verbal as secondary
  - `hypothesis`: H1 · `direction`: counterevidence · `transfer`: out-of-domain
- **[F-015]** Entropy-based UQ effectiveness is model-dependent and has a 'confidently wrong regime' of low-entropy hallucinations; selective prediction is evaluated with E-AURC
  - `source_url`: https://arxiv.org/abs/2603.21172 · `work_id`: W00236 · `pub_status`: preprint (arXiv, 2026)
  - `evidence_location`: private/fulltext/261019/2603.21172.txt L31, L57 · `verified_full_text`: yes
  - `uncertainty`: QA tasks
  - `decision_relevance`: Abstention may not reduce confidently wrong answers when errors are low-entropy; H1 must report the confidently-wrong share at matched coverage, not only AURC
  - `hypothesis`: H1 · `direction`: counterevidence · `transfer`: out-of-domain
- **[F-016]** LLM rerankers cannot verbalise their ranking performance and are severely overconfident; metric-specific self-consistency is competitive and better calibrated
  - `source_url`: https://arxiv.org/abs/2606.03535 · `work_id`: W01397 · `pub_status`: preprint (arXiv, 2026)
  - `evidence_location`: private/fulltext/261019/2606.03535.txt L49, L238 · `verified_full_text`: yes
  - `uncertainty`: TREC DL19-22 passage ranking
  - `decision_relevance`: NT114's LLM is a ranker over candidate services; supports consensus over verbal confidence
  - `hypothesis`: H1 · `direction`: counterevidence (verbal) / supports (consensus) · `transfer`: adjacent
- **[F-017]** On 500 MedMCQA questions, in an answer-removal setting that requires abstention, accuracy falls but confidence stays misaligned with accuracy, so unsafe confident errors (UCER) rise substantially
  - `source_url`: https://doi.org/10.1109/ICDH72779.2026.00043 · `work_id`: W00339 · `pub_status`: published: IEEE ICDH 2026, pp. 315-323
  - `evidence_location`: private/fulltext/261019/2608.09080.txt L21-22, L39, L75-83 (arXiv 2608.09080) · `verified_full_text`: yes
  - `uncertainty`: Medical MCQ; answer removal is option removal, not evidence removal
  - `decision_relevance`: Closest out-of-domain analogue of the H1 design; predicts that confidence may not drop when telemetry is removed
  - `hypothesis`: H1 · `direction`: counterevidence · `transfer`: out-of-domain
- **[F-018]** Studies LLM abstention in science QA when the context is perturbed, including removal of gold context
  - `source_url`: https://arxiv.org/abs/2404.12452 · `work_id`: W00369 · `pub_status`: preprint (arXiv 2404.12452); venue not verified
  - `evidence_location`: abstract · `verified_full_text`: no
  - `uncertainty`: Abstract only; venue claim from Elicit metadata not verified
  - `decision_relevance`: Design analogue (context removal -> abstention) in QA
  - `hypothesis`: H1 · `direction`: counterevidence / method · `transfer`: out-of-domain
- **[F-019]** Across 20 datasets and 20 frontier LLMs abstention is unsolved, scaling helps little, and reasoning fine-tuning degrades abstention by 24% on average
  - `source_url`: https://arxiv.org/abs/2506.09038 · `work_id`: W00307 · `pub_status`: peer-reviewed: NeurIPS 2025 (OpenAlex); arXiv 2506.09038
  - `evidence_location`: abstract (OpenAlex) · `verified_full_text`: no
  - `uncertainty`: Abstract-level; QA, not RCA
  - `decision_relevance`: General counterevidence that LLMs do not abstain unprompted
  - `hypothesis`: H1 · `direction`: counterevidence · `transfer`: out-of-domain
- **[F-020]** Early models often avoid questions, whereas scaled-up, shaped-up models more often give an apparently sensible but wrong answer
  - `source_url`: https://doi.org/10.1038/s41586-024-07930-y · `work_id`: W00212 · `pub_status`: peer-reviewed: Nature 2024
  - `evidence_location`: abstract (pp. 61-68) · `verified_full_text`: no
  - `uncertainty`: Abstract-level
  - `decision_relevance`: Scale does not fix confident errors; motivates H1
  - `hypothesis`: H1 · `direction`: supports-premise · `transfer`: out-of-domain
- **[F-021]** Reasoning models often detect that a problem is under-specified yet still produce an unsupported final answer (detection-to-abstention gap)
  - `source_url`: https://arxiv.org/abs/2605.28070 · `work_id`: W01303 · `pub_status`: preprint (arXiv, 2026)
  - `evidence_location`: private/fulltext/261019/2605.28070.txt L39 · `verified_full_text`: yes
  - `uncertainty`: Missing-premise math/medical QA
  - `decision_relevance`: Self-abstention is unreliable; supports protocol v2's choice of a deterministic abstention rule on the call's own outputs
  - `hypothesis`: H1 · `direction`: supports-premise · `transfer`: out-of-domain
- **[F-022]** LLM uncertainty estimators that work without ambiguity degrade to close-to-random performance on ambiguous QA data
  - `source_url`: https://arxiv.org/abs/2511.04418 · `work_id`: W00290 · `pub_status`: preprint (arXiv 2511.04418)
  - `evidence_location`: abstract (OpenAlex) · `verified_full_text`: no
  - `uncertainty`: Abstract-level
  - `decision_relevance`: Telemetry removal creates ambiguity; UQ may degrade exactly there
  - `hypothesis`: H1 · `direction`: counterevidence · `transfer`: out-of-domain
- **[F-023]** Cross-model disagreement is proposed as a label-free correctness signal for confident errors
  - `source_url`: https://arxiv.org/abs/2603.25450 · `work_id`: W01392 · `pub_status`: preprint (arXiv, 2026)
  - `evidence_location`: private/fulltext/261019/2603.25450.txt L24 · `verified_full_text`: yes
  - `uncertainty`: QA tasks
  - `decision_relevance`: Effective idea but incompatible with protocol v2 section 1 (no gating on another model's output); usable only as an excluded alternative
  - `hypothesis`: H1 · `direction`: protocol-conflict · `transfer`: out-of-domain
- **[F-024]** For code predictions, post-hoc calibration reduces probability misalignment but does not improve discrimination between correct and incorrect outputs
  - `source_url`: https://arxiv.org/abs/2605.19369 · `work_id`: W00350 · `pub_status`: peer-reviewed per DOI 10.1145/3786582.3786845 (venue not verified)
  - `evidence_location`: private/fulltext/261019/2605.19369.txt L23 · `verified_full_text`: yes
  - `uncertainty`: Code tasks
  - `decision_relevance`: Recalibration (Platt) will not by itself improve AURC; H1's gain must come from a discriminative signal
  - `hypothesis`: H1 · `direction`: counterevidence · `transfer`: adjacent
- **[F-025]** JustDiag adds calibrated non-closure to RCA: on 66 proprietary incidents the outcome score rises 51.0 -> 57.7 while completion falls 65/66 -> 62/66
  - `source_url`: https://arxiv.org/abs/2606.19407 · `work_id`: W00083 · `pub_status`: preprint (arXiv, 2026)
  - `evidence_location`: private/fulltext/261019/2606.19407.txt L42 · `verified_full_text`: yes
  - `uncertainty`: 66 private incidents; no CIs located
  - `decision_relevance`: In-domain evidence that abstention trades coverage for quality, but no matched-coverage comparison
  - `hypothesis`: H1 · `direction`: supports-premise / novelty-overlap (low) · `transfer`: in-domain
- **[F-026]** Over 40 standard-tier adversarial IR episodes per model, GPT-5.2 executes containment in 100% of episodes with an 82.5% false-positive rate, acting at step 4 before gathering sufficient evidence
  - `source_url`: https://arxiv.org/abs/2601.21083 · `work_id`: W00017 · `pub_status`: preprint (arXiv, 2026)
  - `evidence_location`: abstract (OpenAlex) · `verified_full_text`: no
  - `uncertainty`: Security incident response; 40 episodes per model
  - `decision_relevance`: Over-triggering shows confident wrong actions are common in IR agents
  - `hypothesis`: H1 · `direction`: supports-premise · `transfer`: adjacent
- **[F-027]** On OpenRCA, reverse reasoning finds the required evidence present in the vast majority of failures: the binding constraint is reasoning, not data access
  - `source_url`: https://arxiv.org/abs/2607.13548 · `work_id`: W01299 · `pub_status`: preprint (arXiv, 2026)
  - `evidence_location`: private/fulltext/261019/2607.13548.txt L30 · `verified_full_text`: yes
  - `uncertainty`: One benchmark; their own pipeline
  - `decision_relevance`: Challenges H1's motivation in natural telemetry: most errors are reasoning gaps. H1 should frame telemetry removal as a controlled stress test, not as the main natural cause of error
  - `hypothesis`: H1 · `direction`: counterevidence (motivation) · `transfer`: in-domain
- **[F-028]** 48,000 simulated failure scenarios (228 days) yield a taxonomy of 16 RCA reasoning failures
  - `source_url`: https://doi.org/10.1145/3793655.3793732 · `work_id`: W00645 · `pub_status`: peer-reviewed: FORGE@ICSE 2026; arXiv 2601.22208
  - `evidence_location`: private/fulltext/261019/2601.22208.txt L40-41 · `verified_full_text`: yes
  - `uncertainty`: LLM-as-judge annotation
  - `decision_relevance`: Error-taxonomy work is crowded; H3-style taxonomies are not new
  - `hypothesis`: H1;H3 · `direction`: context · `transfer`: in-domain
- **[F-029]** Running OpenRCA across five LLMs (1,675 runs) gives a taxonomy of 12 pitfall types for RCA agents
  - `source_url`: https://arxiv.org/abs/2602.09937 · `work_id`: W00669 · `pub_status`: preprint (arXiv, 2026)
  - `evidence_location`: private/fulltext/261019/2602.09937.txt L37 · `verified_full_text`: yes
  - `uncertainty`: Single benchmark
  - `decision_relevance`: Process-level failure analysis already exists
  - `hypothesis`: H3 · `direction`: novelty-overlap · `transfer`: in-domain
- **[F-030]** A trajectory-level study analyses 5,000 RCA-agent trajectories using fault-propagation paths as a causal reference for evidence navigation and use
  - `source_url`: https://arxiv.org/abs/2608.21310 · `work_id`: W00348 · `pub_status`: preprint (arXiv, 2026)
  - `evidence_location`: private/fulltext/261019/2608.21310.txt L48-49 · `verified_full_text`: yes
  - `uncertainty`: Agentic RCA; not single-call
  - `decision_relevance`: Evidence-use analysis of RCA agents exists; NT114 single-call ranking differs
  - `hypothesis`: H1;H3 · `direction`: context · `transfer`: in-domain
- **[F-031]** Simple rule-based methods match or beat SOTA RCA models on four widely used public benchmarks, suggesting the benchmarks are oversimplified
  - `source_url`: https://doi.org/10.1145/3797100 · `work_id`: W01300 · `pub_status`: peer-reviewed: PACMSE (FSE) 2026
  - `evidence_location`: private/fulltext/261019/2510.04711.txt L58, L156-158, L164 (arXiv 2510.04711) · `verified_full_text`: yes
  - `uncertainty`: The four benchmarks include Nezha and RCAEval RE2/RE3 (RE1 excluded as unimodal); SimpleRCA counts rule-based alerts per service; new dataset of 1,430 cases
  - `decision_relevance`: Nezha and RCAEval (both NT114 datasets) are among the benchmarks where a rule-based heuristic matches SOTA: B1 (max-z) and similar simple baselines are mandatory and every H1/H2/H3 effect must be reported against them
  - `hypothesis`: H1;H2;H3 · `direction`: protocol · `transfer`: in-domain
- **[F-032]** Across nine causal-discovery and 21 RCA methods, no method stands out in all situations
  - `source_url`: https://doi.org/10.1145/3691620.3695065 · `work_id`: W00153 · `pub_status`: peer-reviewed: ASE 2024
  - `evidence_location`: abstract (OpenAlex) · `verified_full_text`: no
  - `uncertainty`: Abstract-level
  - `decision_relevance`: Supports reporting per-dataset results and simple baselines (RCAEval authors)
  - `hypothesis`: H1;H3 · `direction`: protocol · `transfer`: in-domain
- **[F-033]** TraceBudget casts diagnosis as budgeted acquisition (UCB-style source policy, uncertainty-gated stop); on 180 labelled incidents it reaches 76.2% top-1 with 8.6 retrieval steps, 3.1 pp below full retrieval with 36% fewer tokens
  - `source_url`: https://doi.org/10.1109/CISAT71030.2026.11682084 · `work_id`: W00567 · `pub_status`: published: IEEE CISAT 2026, pp. 1167-1171
  - `evidence_location`: abstract (Elicit/OpenAlex) · `verified_full_text`: unavailable
  - `uncertainty`: high: Open-access copy listed by OpenAlex (ResearchGate DOI 10.13140/rg.2.2.15499.04644); the agent was stopped by a Cloudflare bot check on 2026-10-19 and does not solve CAPTCHAs, so the full text stays unread. Abstract only; shared authors with VerifyRCA (F-049)
  - `decision_relevance`: Budget-aware acquisition with uncertainty stopping for RCA is published: H2 novelty is low
  - `hypothesis`: H2 · `direction`: novelty-overlap · `transfer`: in-domain
- **[F-034]** VerifyRCA has an LLM propose top-k hypotheses and a non-LLM verifier check them under a query budget B; on RCAEval RE2-OB (90 cases) it reports 0.72 top-1 at B = 10 and substantially fewer overconfident incorrect conclusions (no number in the abstract)
  - `source_url`: https://doi.org/10.1109/ICETIS70504.2026.11633469 · `work_id`: W01267 · `pub_status`: published: IEEE ICETIS 2026, pp. 322-327
  - `evidence_location`: abstract (Elicit/OpenAlex) · `verified_full_text`: unavailable
  - `uncertainty`: high: Open-access copy listed by OpenAlex (ResearchGate DOI 10.13140/rg.2.2.28829.88803); the agent was stopped by a Cloudflare bot check on 2026-10-19 and does not solve CAPTCHAs, so the full text stays unread. Abstract only; off-topic references (F-049)
  - `decision_relevance`: Overlaps H2 directly and touches H1 (overconfident wrong conclusions) on the same benchmark family; must be cited and contrasted
  - `hypothesis`: H2;H1 · `direction`: novelty-overlap · `transfer`: in-domain
- **[F-035]** BudgetSRE treats tokens, tool calls and action depth as a budget, invoking a specialist agent only under high diagnostic uncertainty; on AIOpsLab it stays within 4-6 pp of an unconstrained oracle at medium budget
  - `source_url`: https://doi.org/10.1109/IPMML71439.2026.11682590 · `work_id`: W00052 · `pub_status`: published: IEEE IPMML 2026
  - `evidence_location`: abstract (Elicit record; pp. 221-226) · `verified_full_text`: unavailable
  - `uncertainty`: high: Open-access copy listed by OpenAlex (ResearchGate DOI 10.13140/rg.2.2.29081.17765); the agent was stopped by a Cloudflare bot check on 2026-10-19 and does not solve CAPTCHAs, so the full text stays unread. Abstract only
  - `decision_relevance`: H2 space is crowded
  - `hypothesis`: H2 · `direction`: novelty-overlap · `transfer`: in-domain
- **[F-036]** EviRCA reaches 40.6-43.9% Correct on OpenRCA while cutting token use 15-26x and time 3-20x
  - `source_url`: https://arxiv.org/abs/2609.19825 · `work_id`: W01432 · `pub_status`: preprint (arXiv, 2026)
  - `evidence_location`: private/fulltext/261019/2609.19825.txt L29 · `verified_full_text`: yes
  - `uncertainty`: One benchmark
  - `decision_relevance`: Cost-accuracy trade-offs are now a standard reported axis in LLM-RCA; H2's cost axis is not new
  - `hypothesis`: H2 · `direction`: novelty-overlap · `transfer`: in-domain
- **[F-037]** SADE separates evidence acquisition from hypothesis commitment with a phase-gated workflow under a fixed 20-turn budget and improves root-cause F1 by 36.9 pp over the NIKA-native ReAct + GPT-5 baseline (21.5 pp over a same-backbone Claude-Code baseline) on 523 held-out network-troubleshooting incidents; the budget is a fixed cap, not a learned acquisition policy
  - `source_url`: https://doi.org/10.1109/LCN67947.2026.11660797 · `work_id`: W01595 · `pub_status`: peer-reviewed: IEEE LCN 2026; arXiv 2605.04530
  - `evidence_location`: private/fulltext/261019/2605.04530.txt L13-25 (abstract), L460-513 (Table II, 20-turn budget, F1), L779-782 · `verified_full_text`: yes
  - `uncertainty`: medium: network troubleshooting (NIKA), not microservice RCA; fixed turn cap rather than budget-optimal acquisition
  - `decision_relevance`: Staged evidence acquisition is published in adjacent RCA
  - `hypothesis`: H2 · `direction`: novelty-overlap · `transfer`: adjacent
- **[F-038]** Raising the tool-call budget alone hits a ceiling; budget awareness (Budget Tracker, BATS) gives better cost-performance curves for web-search agents
  - `source_url`: https://arxiv.org/abs/2511.17006 · `work_id`: W01275 · `pub_status`: preprint (arXiv 2511.17006)
  - `evidence_location`: abstract (OpenAlex) · `verified_full_text`: no
  - `uncertainty`: Abstract-level, general agents
  - `decision_relevance`: General budgeted-agent methods supply H2 baselines; H2's method novelty would be low
  - `hypothesis`: H2 · `direction`: method · `transfer`: out-of-domain
- **[F-039]** TELEOS proposes value-aware adaptive telemetry for agentic AI observability, evaluated on synthetic data
  - `source_url`: https://doi.org/10.30574/wjarr.2025.27.3.3148 · `work_id`: W01264 · `pub_status`: published: WJARR 2025 (low-quality venue)
  - `evidence_location`: abstract · `verified_full_text`: no
  - `uncertainty`: Low-quality venue, synthetic data
  - `decision_relevance`: Weak signal only
  - `hypothesis`: H2 · `direction`: weak-signal · `transfer`: adjacent
- **[F-040]** Protocol v2 forbids retrieval chosen per incident by a model; every abstention is a deterministic rule on the same call's outputs
  - `source_url`: repo:plans/261018-2300-single-llm-simplification-and-evaluation-hardening/design/protocol-v2.md#1-single-llm-invariant · `work_id`: — · `pub_status`: internal (protocol v2)
  - `evidence_location`: protocol-v2.md section 1 · `verified_full_text`: yes
  - `uncertainty`: None (frozen document)
  - `decision_relevance`: H2 is admissible only as offline replay with a deterministic DEV-fitted acquisition rule over existing condition cells; a model-driven acquisition policy would violate the invariant
  - `hypothesis`: H2 · `direction`: protocol · `transfer`: in-domain
- **[F-041]** DecompRCA decomposes top@k into Retrieval@K x Rerank@k; on RCAEval RE1 (125 cases per system) magnitude-only Retrieval@15 is 1.00 / 1.00 / 0.98 (OB/SS/TT), and the +stc retriever used downstream reaches 0.98 / 1.00 / 0.91
  - `source_url`: https://arxiv.org/abs/2609.36686 · `work_id`: W00418 · `pub_status`: accepted: NeurIPS 2026 poster (https://neurips.cc/virtual/2026/poster/139698); arXiv preprint
  - `evidence_location`: private/fulltext/261019/2609.36686.txt L460-541 (Table 1), L573-636 (Table 2) · `verified_full_text`: yes
  - `uncertainty`: OpenReview page blocked; camera-ready may differ (see C1)
  - `decision_relevance`: The generation-vs-ranking decomposition is published on the same benchmark NT114 uses: H3 novelty is low
  - `hypothesis`: H3 · `direction`: novelty-overlap · `transfer`: in-domain
- **[F-042]** Reranking failures dominate: BARO vs LLM top@1 0.784/0.875 (OB), 0.856/0.872 (SS), 0.560/0.653 (TT); retrieval-failure share 0.02/0.00/0.09 vs reranking-failure share 0.10/0.13/0.26
  - `source_url`: https://arxiv.org/abs/2609.36686 · `work_id`: W00418 · `pub_status`: accepted: NeurIPS 2026 poster
  - `evidence_location`: private/fulltext/261019/2609.36686.txt L573-636 (Table 2) · `verified_full_text`: yes
  - `uncertainty`: n = 3 runs at T = 1.0, no seed; Rerank@1 0.90 / 0.87 / 0.72
  - `decision_relevance`: With NT114's in_candidates = 1, RE1 errors are ranking errors; the decomposition adds little
  - `hypothesis`: H3 · `direction`: novelty-overlap · `transfer`: in-domain
- **[F-043]** Preprocessing reproduces RCAEval main-ase.py (drop time and constant columns, keep common columns, *_mem bytes to MB, keep raw latency quantiles); reranker gpt-oss-120b, K = 15
  - `source_url`: https://arxiv.org/abs/2609.36686 · `work_id`: W00418 · `pub_status`: accepted: NeurIPS 2026 poster
  - `evidence_location`: private/fulltext/261019/2609.36686.txt L1403-1423 · `verified_full_text`: yes
  - `uncertainty`: None for the text; code unavailable
  - `decision_relevance`: Defines the alignment gap between DecompRCA and NT114 RE1 inputs (NT114 does not use main-ase.py)
  - `hypothesis`: H3 · `direction`: protocol · `transfer`: in-domain
- **[F-044]** The DecompRCA repository linked from the paper is not public; the organisation exists and hosts RCAEval
  - `source_url`: https://github.com/cruiseresearchgroup/DecompRCA · `work_id`: W00418 · `pub_status`: artifact: repository returns 404 (checked 2026-10-19)
  - `evidence_location`: HTTP check 2026-10-19 · `verified_full_text`: yes
  - `uncertainty`: May be released later
  - `decision_relevance`: Results cannot be reproduced from code; contrast must rely on the paper
  - `hypothesis`: H3 · `direction`: quality-flag · `transfer`: in-domain
- **[F-045]** STAR attributes RCA-agent failures to stages (evidence collection, hypothesis formation, ...) and repairs them
  - `source_url`: https://arxiv.org/abs/2605.15581 · `work_id`: W01289 · `pub_status`: peer-reviewed: IEEE ICWS 2026 (OpenAlex DOI 10.1109/ICWS72778.2026.00057)
  - `evidence_location`: private/fulltext/261019/2605.15581.txt L28 · `verified_full_text`: yes
  - `uncertainty`: Agentic setting
  - `decision_relevance`: Stage-level failure attribution is published; another pre-emption of H3
  - `hypothesis`: H3 · `direction`: novelty-overlap · `transfer`: in-domain
- **[F-046]** Every NT114 record has in_candidates = 1, so the true root is always in the candidate list
  - `source_url`: repo:research/04_evidence_visibility_results.md · `work_id`: — · `pub_status`: internal (research/04)
  - `evidence_location`: research/04 lines 50, 175 · `verified_full_text`: yes
  - `uncertainty`: None
  - `decision_relevance`: H3 reduces to a ranking analysis unless a shortlist arm is added
  - `hypothesis`: H3 · `direction`: protocol · `transfer`: in-domain
- **[F-047]** Paired AC@1 MDE at 80% power, 20% discordance: RCAEval 0.10, blind_root x blind_nonroot_ev intersection 0.18 (unreachable at 10%), Nezha 0.14, RCA100 0.16, AIOps2025 0.08
  - `source_url`: repo:research/06_statistics_validation.md#v5--minimum-detectable-effects · `work_id`: — · `pub_status`: internal (research/06)
  - `evidence_location`: research/06 lines 74-109 · `verified_full_text`: yes
  - `uncertainty`: Discordance values are placeholders until a DEV pilot
  - `decision_relevance`: Sets the detectable-effect floor for every direction; selective-risk contrasts at coverage c use about c x n answered units, so their MDE is larger
  - `hypothesis`: H1;H2;H3 · `direction`: power · `transfer`: in-domain
- **[F-048]** Partial Evidence Bench measures how agents behave when access control limits the evidence they can see, so outputs can look complete while evidence is partial
  - `source_url`: https://arxiv.org/abs/2605.05379 · `work_id`: W01330 · `pub_status`: preprint (arXiv, 2026)
  - `evidence_location`: private/fulltext/261019/2605.05379.txt L16 · `verified_full_text`: yes
  - `uncertainty`: Enterprise agent setting
  - `decision_relevance`: Adjacent framing for 'evidence present but incomplete'; related work for H1
  - `hypothesis`: H1 · `direction`: context · `transfer`: adjacent
- **[F-049]** VerifyRCA's indexed reference list includes off-topic 2026 conference papers (diffusion ad-creative reward modelling, privacy-aware RAG routing, multilingual LLM-judge calibration); TraceBudget and VerifyRCA share authors (Wenrui Ma, Zirui Liu)
  - `source_url`: https://doi.org/10.1109/ICETIS70504.2026.11633469 · `work_id`: W01267 · `pub_status`: published: IEEE ICETIS 2026
  - `evidence_location`: OpenAlex referenced_works of W7165784816 (work/raw/snowball/), authorships of W7165784816 and W7162792847 · `verified_full_text`: no (metadata only)
  - `uncertainty`: Metadata pattern, not proof of misconduct
  - `decision_relevance`: Treat TraceBudget/VerifyRCA as real but low-confidence prior art: cite them for H2 overlap, do not rely on their numbers
  - `hypothesis`: H2;H1 · `direction`: quality-flag · `transfer`: in-domain
- **[F-050]** Across 53 runners x 50 samples (265,000 samples) on GPQA Diamond and AIME, self-agreement is a positive but weak predictor of correctness (rho 0.20-0.59) whose usefulness is regime-dependent
  - `source_url`: https://arxiv.org/abs/2607.08065 · `work_id`: W01715 · `pub_status`: preprint (arXiv, 2026)
  - `evidence_location`: abstract (OpenAlex record, gap round GAP-C1) · `verified_full_text`: no
  - `uncertainty`: Abstract-level; reasoning QA
  - `decision_relevance`: Consensus (vote share) is H1's planned primary estimator; its AUROC must be measured on DEV before the confirmatory family is fixed
  - `hypothesis`: H1 · `direction`: counterevidence · `transfer`: out-of-domain
- **[F-051]** In tool-use agents, evidence tools such as web search induce severe verbal overconfidence because retrieved information is noisy, whereas verification tools mitigate miscalibration
  - `source_url`: https://doi.org/10.18653/v1/2026.acl-long.520 · `work_id`: W01721 · `pub_status`: peer-reviewed: ACL 2026
  - `evidence_location`: abstract (OpenAlex record, gap round GAP-C1) · `verified_full_text`: no
  - `uncertainty`: Abstract-level
  - `decision_relevance`: NT114's hybrid retrieval arm may raise overconfidence; H1 contrasts must be stratified by retrieval arm (already a fixed arm in protocol v2)
  - `hypothesis`: H1 · `direction`: counterevidence / protocol · `transfer`: adjacent
- **[F-052]** Safe remediation is cast as a constrained MDP that maximises repair success subject to a bounded false-remediation rate, with epistemic uncertainty as one risk dimension and a human-in-the-loop gate
  - `source_url`: https://arxiv.org/abs/2607.20005 · `work_id`: W01729 · `pub_status`: preprint (arXiv, 2026)
  - `evidence_location`: abstract (OpenAlex record, gap round GAP-H1) · `verified_full_text`: no
  - `uncertainty`: Abstract-level; remediation, not diagnosis
  - `decision_relevance`: Risk-bounded deferral exists for remediation in microservices; H1 is the diagnosis-side analogue and should cite it
  - `hypothesis`: H1 · `direction`: novelty-overlap (low) · `transfer`: in-domain
- **[F-053]** A controlled study of 24 RCA tools on 375 failure cases from three microservice systems finds tool configuration changes localisation and type identification differently (L3 tools 82.8% vs L0 85.4% top-1 at under half the time), and agents sometimes override correct diagnostic recommendations
  - `source_url`: https://arxiv.org/abs/2610.05009 · `work_id`: W01462 · `pub_status`: preprint (arXiv, Oct 2026)
  - `evidence_location`: abstract (arXiv API, gap round GAP-X1) · `verified_full_text`: no
  - `uncertainty`: Abstract-level; 375 cases suggests RCAEval RE1 but not verified
  - `decision_relevance`: Controlled cost-accuracy studies of evidence access are appearing in Oct 2026; adds to H2 scoop risk
  - `hypothesis`: H2 · `direction`: novelty-overlap · `transfer`: in-domain
- **[F-054]** Vanilla verbalized confidence is a weak failure predictor (GPT-4 mean AUROC 62.7%, close to chance), while sample consistency with 5 responses outperforms it, e.g. GSM8K AUROC 54.8% -> 92.7%
  - `source_url`: https://arxiv.org/abs/2306.13063 · `work_id`: — · `pub_status`: peer-reviewed: ICLR 2024; arXiv 2306.13063
  - `evidence_location`: private/fulltext/261019/2306.13063.txt L429-440 (Sec. 5.1, Table 2), L524-536 (Table 3, Fig. 7) · `verified_full_text`: yes
  - `uncertainty`: medium: QA/reasoning tasks, GPT-3.5/GPT-4; gains are task-dependent (largest on arithmetic)
  - `decision_relevance`: H1 power prior: the literature AUROC 0.51-0.65 concerns verbal confidence; the H1 primary score is consensus (sample agreement, n = 10), which can separate errors much better or not at all; only a DEV pilot can tell
  - `hypothesis`: H1 · `direction`: context · `transfer`: out-of-domain
- **[F-055]** Withholding one modality during alert unification changes LLM RCA unevenly: removing metrics costs most localisation (e.g. Qwen 3 4B Delta LA = -0.155), removing logs mainly hurts fault-type accuracy (Delta TA = -0.128), and removing traces can improve propagation-path and hypothesis accuracy (up to +0.28 / +0.06)
  - `source_url`: https://doi.org/10.1145/3793655.3793732 · `work_id`: W00645 · `pub_status`: peer-reviewed: FORGE@ICSE 2026; arXiv 2601.22208
  - `evidence_location`: private/fulltext/261019/2601.22208.txt L878-893 (RQ2 holdout experiments) · `verified_full_text`: yes
  - `uncertainty`: medium: GAIA and OpenRCA, six open models; no confidence or abstention measured
  - `decision_relevance`: H1 design: controlled modality removal on LLM RCA is established (not novel by itself) and its effect is heterogeneous, so a pooled single-modality endpoint must be reported per condition too
  - `hypothesis`: H1 · `direction`: overlaps · `transfer`: in-domain
- **[F-056]** With the actual E1 estimator, injection clustering, 11-level consensus ties and percentile cluster bootstrap, the fixed-coverage (0.7) gain MDE at 80% power is about 0.05-0.06 on RCAEval full and the pooled single-modality set, 0.05 on AIOps2025 and 0.08-0.10 on Nezha / RCA100 (alpha 0.05), under a binomial-logit generator
  - `source_url`: repo:plans/261019-1501-sua-review-h1-power-va-sang-loc/research/h1-endpoint-va-power.md · `work_id`: — · `pub_status`: internal (design simulation, 2026-10-19)
  - `evidence_location`: plans/261019-1501-sua-review-h1-power-va-sang-loc/work/out/h1-mde.csv; h1-power-grid.csv · `verified_full_text`: yes
  - `uncertainty`: high: depends on the assumed consensus distribution and ICC 0.5; synthetic, replaced by DEV-informed parameters later
  - `decision_relevance`: Replaces the AUROC >= 0.75 gate and the MDE/sqrt(c) approximation; H1 is not underpowered by construction
  - `hypothesis`: H1 · `direction`: context · `transfer`: in-domain
- **[F-057]** GALA+ has an LLM investigator emit a root-cause confidence in [0, 1] per microservice candidate and uses a threshold (best near 0.6) only to stop or extend graph exploration; no abstention, calibration or risk-coverage evaluation is reported
  - `source_url`: https://arxiv.org/abs/2608.08968 · `work_id`: W01612 · `pub_status`: peer-reviewed: ASE 2026 (DOI 10.1145/3832783.3834335); arXiv 2608.08968
  - `evidence_location`: private/fulltext/261019/2608.08968.txt L413-430 (consolidated confidence), L480-496 (stop rule), L1139-1142 (theta sweep) · `verified_full_text`: yes
  - `uncertainty`: low for what is reported; confidence is a search-control signal of an agent pipeline, not a deferral rule
  - `decision_relevance`: H1 novelty: closest in-domain use of LLM confidence thresholds in microservice RCA; does not pre-empt matched-coverage abstention; surfaced by the Perplexity challenge round
  - `hypothesis`: H1 · `direction`: overlaps · `transfer`: in-domain

<!-- /FINDINGS-APPENDIX -->

## 12. Đầu vào cho bước sau (đề xuất cho §9.5 của protocol v2; không sửa protocol)

Mọi mục dưới đây là **đề xuất**; protocol v2 chưa bị sửa. Chi tiết, mô phỏng và test:
[h1-endpoint-va-power.md](../261019-1501-sua-review-h1-power-va-sang-loc/research/h1-endpoint-va-power.md).

1. **Endpoint chính (H1-primary).**
   - **Tập:** RCAEval split `within-rcaeval-grouped-0-e9b2c81c`, vai test; model chính, prompt v1,
     `retrieval = none`. Gộp `no_metric`, `no_log`, `no_trace`: 108 injection, 285 bản ghi, trọng số
     1/số bản ghi của injection. Score là `conf_consensus`, xếp hạng chung trên toàn tập gộp.
   - **Estimator:** `G_0.7 = lỗi nền − selective risk ở coverage chính xác 0.7` (nhóm biên trả lời
     một phần, bằng kỳ vọng tie-break của C1), so với C2 giải tích.
   - **Kiểm định:** H0: G_0.7 ≤ 0. Percentile cluster bootstrap theo injection, B = 10,000; bác bỏ
     khi cận dưới của CI 95 % > 0.
   - **SESOI:** 0.05, chờ chủ dự án xác nhận.
   - **Báo cáo kèm:** từng điều kiện riêng [F-055]; coverage thực; baseline B1 max-z.
2. **Tách hai phép đánh giá.** E1 (coverage cố định, không fit) và E2 (ngưỡng DEV đóng băng, báo
   coverage thực, so với C2 ở coverage đó) là hai endpoint khác nhau. Chúng không được trộn trong một
   dòng "risk tại 0.7, ngưỡng fit DEV" như bản trước.
3. **Họ confirmatory (nếu cần nhiều hơn một test, Holm k = 3):**
   - H1-primary;
   - lỗi nền − AURC trên cùng tập;
   - E1 trên RCAEval `full` (218).

   Ngoài họ: E2; AIOps2025 (bản lặp, bảng riêng); Nezha, RCA100 và giao 52 (thăm dò).
   - **Bỏ (c) cũ.** Đó là hiệu thô confidently-wrong giữa `full` và `metrics_only`, nó lẫn thay đổi
     độ khó với lợi ích abstention.
   - Câu hỏi "thiếu telemetry làm abstention có ích hơn không" được thay bằng DiD của gain trên 108
     injection. Contrast đó thiếu power (≤ 0.46), nên chỉ ở mức thăm dò.
4. **Quy tắc DEV pilot** (cài trong `pilot_decision`; chỉ dùng nhãn DEV, 78 injection gộp):
   - **Futility:** cận trên 95 % của G_0.7(DEV) < SESOI.
   - **Confirmatory:** cả hai điều kiện sau phải đạt.
     - Power trên test tại `max(cận dưới 80 %, 0)` đạt ≥ 0.80 ở α Holm.
     - Ngưỡng E2 cross-fit hai fold trong DEV cho coverage lệch ≤ 0.10.
   - **Exploratory:** mọi trường hợp còn lại.
   - AUROC chỉ được báo cáo kèm CI, không làm cổng.
   - Trước khi đóng băng: chạy lại mô phỏng với phân bố consensus và ICC đo trên DEV.
5. **Thăm dò:** verbal và token probability; shortlist bỏ root (H3 phần B); phân tầng theo arm
   retrieval.
6. **Bỏ khỏi H1:** `blind_nonroot` (thay bằng `blind_nonroot_ev`) và `blind_root` trên RCA100.
7. **Báo cáo bắt buộc:** baseline B1 max-z cạnh mọi kết quả [F-031]; nhãn "external reference, not
   directly comparable" cho mọi số của DecompRCA.
8. **Theo dõi:** chạy lại GAP-H1 trên Elicit sau 2026-11-18 và trước khi đóng băng preregistration.
   Hoàn tất sàng lọc lại có trễ sau 2026-10-20 13:42 (giờ VN).

## 13. Câu hỏi còn mở

- SESOI cho G_0.7 có phải 0.05 không? Đây là quyết định của chủ dự án.
- Chủ dự án muốn một endpoint chính duy nhất (α 0.05) hay họ k = 3 (α Holm)?
- Có tải tay toàn văn TraceBudget, VerifyRCA, BudgetSRE để chốt verdict H2 không?
