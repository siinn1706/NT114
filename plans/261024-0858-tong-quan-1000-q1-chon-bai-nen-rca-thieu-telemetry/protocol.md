---
title: "Giao thức tổng quan 1.000 → 100 → 10 → 1"
revision: "frozen-261024"
mode: scoping (thu thập và sàng lọc) + đọc sâu có cấu trúc (T2–T3)
as_of: 2026-10-24 Asia/Saigon
---

# Giao thức tổng quan

Phase 01 đóng băng bản này trước bản ghi screening đầu tiên. Sau freeze, mọi thay đổi là amendment trong `work/amendments.md` (ngày, lý do, mục, bản ghi bị ảnh hưởng, chấm lại hay không). Amendment làm thay đổi tập bài được chọn ở T1/T2/T3 sau khi đã thấy kết quả của tầng đó cần chủ dự án duyệt trước khi áp dụng. Bản r2 sửa theo [review trước freeze](research/protocol-review.md).

Đây là tổng quan **scoping có giao thức đóng băng**, không gọi là systematic review: người chấm chính và người chấm thứ hai đều là mô hình cùng họ, nguồn chính là OpenAlex.

## 1. Câu hỏi

**Q:** Trong các bài tạp chí Q1 (định nghĩa §3) từ 2020, bài nào là nền phù hợp nhất để **tái hiện, đào sâu và cải tiến** cho MVP “RCA microservice bằng một LLM khi thiếu telemetry”, xét theo độ khớp bài toán, khả năng tái hiện trên hạ tầng NT114 và dư địa cải tiến kiểm chứng được?

Câu hỏi không hỏi “hướng nào mới”. Tính mới của cải tiến chỉ được đánh giá ở phase 09, giới hạn bởi tìm kiếm đã chạy.

PCC: **Population** hệ thống phần mềm vận hành (microservice, cloud-native, dịch vụ trực tuyến, hệ phân tán, mạng data center/cloud phục vụ dịch vụ); **Concept** chẩn đoán lỗi (RCA, định vị lỗi, chẩn đoán sự cố, phát hiện bất thường phục vụ định vị), ưu tiên LLM và telemetry thiếu/không đầy đủ; **Context** nghiên cứu có đánh giá thực nghiệm.

## 2. Nguồn

| Làn | Vai trò | Trạng thái 24/10 |
|---|---|---|
| OpenAlex Works API | Nguồn tìm kiếm chính T0, snowball | gọi được |
| Crossref REST | Xác minh DOI, ISSN, retraction (`update-to`, `relation`), bổ sung abstract | gọi được |
| Semantic Scholar Graph | Bổ sung abstract | 429 không key; tùy chọn |
| Elicit MCP `search_papers` | Làn phát hiện bổ sung: đúng 17 chuỗi §5 (bỏ cú pháp boolean nếu Elicit không nhận, ghi chuỗi đã gửi), tối đa 50 kết quả mỗi chuỗi, một lượt; `origin: elicit:<query>`; chỉ bản ghi tìm được trên OpenAlex theo DOI mới vào T0 | có tool |
| arXiv, Unpaywall, `best_oa_location` | Tìm bản toàn văn | — |
| SCImago SJR CSV 2025 | Cổng Q1 | dùng file đã hash |
| Corpus 11/10 và 19/10 | Seed, lấy lại metadata hiện hành ở phase 02 | đọc được |

Hội nghị, preprint, luận văn: chỉ làn prior work (phase 08–09), không đếm vào T0.

## 3. Chuẩn Q1

| Mã | Quy tắc |
|---|---|
| Q-1 | Hệ: SCImago SJR, ấn bản **2025** (ấn bản mới nhất ngày 24/10/2026, [kiểm](work/sjr-edition-check.md)); file `../261011-1345-aiops-q1-literature-gap/work/scimagojr-2025-nckh.csv`, SHA-256 `6f20399957173a13e3c1729a5fb3b5821844ba75e8d640c8b3040ab19a6f7180` |
| Q-2 | `Type == journal` trong SJR (loại `book series`, `conference and proceedings`, `trade journal`) |
| Q-3 | Khớp ISSN print hoặc electronic (bỏ gạch, chữ hoa) từ OpenAlex `primary_location.source.issn`/`issn_l`; đổi tên/ISSN không còn trong SJR 2025 → không Q1 |
| Q-4 | **Chuyên ngành:** Q1 ở ít nhất một category trong 13 category ở `CS_CATEGORIES` (`work/scripts/common.py`): Artificial Intelligence; Computer Networks and Communications; Software; Information Systems; Computer Science Applications; Hardware and Architecture; Computational Theory and Mathematics; Computer Science (miscellaneous); Computer Vision and Pattern Recognition; Human-Computer Interaction; Signal Processing; Theoretical Computer Science; Computer Graphics and Computer-Aided Design. Ghi chú: “Theoretical Computer Science” (ASJC 2614) thuộc nhóm Mathematics trong ASJC; giữ trong danh sách vì liên tục với giao thức 11/10 |
| Q-5 | **Năm:** OpenAlex `publication_date` ∈ [2020-01-01, `to_publication_date`]; `to_publication_date` = ngày bắt đầu phase 03, áp dụng cho mọi làn (seed, search, Elicit, snowball, late-records) |
| Q-6 | OpenAlex `type` ∈ {`article`, `review`} |
| Q-7 | Giữ D3/D4 của [giao thức 11/10](../261011-1345-aiops-q1-literature-gap/work/q1-protocol.md): loại publisher MDPI; IEEE Access, Scientific Reports gắn `q1_weak=1`. Q-7 là quy tắc thêm ngoài SJR; số bị loại theo Q-7 và số `q1_weak` được báo riêng, không gọi là “không Q1” |
| Q-8 | Loại bản rút/withdrawn (OpenAlex `is_retracted`; Crossref `update-to` cho T1); giữ bản đính chính kèm cờ |
| Q-9 | OpenAlex `language == "en"`; `language` rỗng → giữ nếu tiêu đề là tiếng Anh (ASCII ≥ 90%), ghi trong `q1_rule_trace` |

Quartile áp dụng là quartile **SJR 2025 của tạp chí**, không phải quartile năm xuất bản. Với các bài T3, phase 08 tra thêm quartile năm xuất bản (và JCR nếu có quyền); lệch thì ghi cờ, không loại. Best Q1 ngoài CS ghi `Q-4-q1-noncs`, không đếm, không làm bài nền; báo số bản ghi `q1_noncs` qua cổng chủ đề theo tạp chí, và phase 05 chấm R cho chúng để liệt kê các bài lẽ ra vào top-100 (dữ kiện cho chủ dự án quyết định thêm Engineering). Không viết “JCR Q1” hay “Q1 đúng chuyên ngành” ngoài phạm vi Q-4.

## 4. Cổng chủ đề T0 (metadata)

Cổng chạy **sau** làn bổ sung abstract của phase 04. Bản ghi qua cổng khi tiêu đề + abstract thỏa **(Hệ thống ∧ Tác vụ) ∨ Cụm mạnh** (regex, không phân biệt hoa thường; bản thực thi: `SYSTEM_RE`, `TASK_RE`, `STRONG_RE` trong `work/scripts/common.py`):

- **Hệ thống:** `microservice|cloud|cloud-native|online service|web service|distributed system|data ?center|software system|IT operation|AIOps|kubernetes|container|serverless|large-scale system|service system|\blogs?\b|log-based|log analysis|intelligent operation|operation and maintenance|\bO&M\b|IT service`
- **Tác vụ lỗi:** `root.?cause|fault|failure|incident|anomal|diagnos|outage|trouble|alert|locali[sz]|triage|degradation`
- **Cụm mạnh:** `root.?cause (analysis|locali[sz]ation|diagnosis|identification)|fault locali[sz]ation|failure (diagnosis|locali[sz]ation)|incident management|AIOps|log pars|log anomaly|log analysis`

Bản ghi chỉ có tiêu đề (không abstract sau mọi làn bổ sung) mà trượt cổng → `needs-review-t0`, đọc tiêu đề + venue để quyết định, không loại thẳng.

Đây là cổng **ưu tiên recall**. Hiệu chỉnh **in-sample** trên 736 bản ghi có nhãn R của corpus 11/10: giữ 55/58 R3, 129/147 R2, cho lọt 80/420 R0 ([regex-calibration.json](work/regex-calibration-02.json)). Hệ quả: T0 chứa bản ghi ngoài Population. **Chỉ tiêu 1.000 đo trên T0 metadata**; báo cáo luôn nêu N(T0), N(include = I1∧I2∧I3) và precision T0 ước lượng = N(include)/N(T0 đã screening) kèm khoảng Wilson 95%; không gọi T0 là “1.000 bài về RCA”.

Kiểm sai âm (phase 04): “đúng ra phải giữ” = bản ghi sẽ nhận I1∧I2 theo §6. Mẫu phân tầng (seed 20261024) từ bản ghi bị loại vì `T-off-topic-metadata`: 25 bản ghi khớp đúng một trong SYSTEM_RE/TASK_RE (giáp ranh) và 25 bản ghi không khớp cái nào. > 1 sai âm ở tầng giáp ranh hoặc > 0 ở tầng không khớp → amendment regex, chạy lại cổng. Báo cận trên Clopper-Pearson 95% cho từng tầng.

## 5. Truy vấn (OpenAlex `title_and_abstract.search`, lọc Q-5, Q-6, `primary_location.source.type:journal`)

| ID | Họ | Truy vấn |
|---|---|---|
| A1 | RCA lõi | `"root cause" AND (microservice OR microservices OR "cloud-native" OR "cloud native")` |
| A2 | RCA lõi | `"root cause analysis" AND (cloud OR "distributed system" OR "online service" OR AIOps OR microservice)` |
| A3 | RCA lõi | `("fault localization" OR "failure localization" OR "fault diagnosis" OR "failure diagnosis") AND (microservice OR cloud OR "distributed system")` |
| A4 | RCA lõi | `incident AND ("root cause" OR diagnosis OR triage) AND (cloud OR "online service" OR microservice)` |
| B1 | LLM | `("language model" OR LLM OR LLMs OR GPT OR ChatGPT OR "foundation model") AND ("root cause" OR incident OR AIOps OR "fault diagnosis")` |
| B2 | LLM | `("retrieval-augmented" OR RAG OR agent OR agentic) AND ("root cause" OR incident OR "fault diagnosis") AND (cloud OR microservice OR software)` |
| C1 | Thiếu telemetry | `("missing modality" OR "missing data" OR "missing metrics" OR "missing logs" OR "missing traces" OR "incomplete" OR "partial observability" OR "limited observability" OR "unobservable" OR "trace sampling" OR "partial telemetry" OR "sparse" OR "noisy") AND ("root cause" OR "fault diagnosis" OR "anomaly detection") AND (microservice OR cloud OR "distributed system" OR "online service")` |
| C2 | Đa modality | `(multimodal OR "multi-modal" OR "multi-source") AND (metric OR log OR trace) AND ("root cause" OR "fault diagnosis" OR "anomaly detection")` |
| C3 | Observability | `(observability OR telemetry OR "distributed tracing") AND (microservice OR "cloud-native") AND (diagnosis OR "root cause" OR anomaly)` |
| D1 | AIOps rộng | `"AIOps"` |
| D2 | Log | `("log anomaly detection" OR "log-based anomaly detection" OR "log analysis") AND (system OR software OR cloud)` |
| D3 | Bất thường | `"anomaly detection" AND (microservice OR "cloud-native" OR "online service" OR "cloud service")` |
| D4 | Nhân quả | `("causal discovery" OR "causal inference" OR "causal graph") AND ("root cause" OR fault OR failure) AND (service OR system)` |
| D5 | Trace | `trace AND (anomaly OR diagnosis OR "root cause") AND microservice` |
| D6 | Độ tin cậy | `(confidence OR uncertainty OR calibration OR abstention OR "selective prediction") AND ("root cause" OR incident OR "fault diagnosis" OR AIOps) AND (cloud OR microservice OR software OR "online service")` |
| D7 | Dự báo sự cố | `("failure prediction" OR "incident prediction" OR "alert") AND (cloud OR "online service" OR "data center")` |
| D8 | Mạng DC/cloud | `("fault diagnosis" OR "root cause") AND ("data center network" OR "cloud network" OR "software-defined network")` |

Mỗi truy vấn chạy **hết mọi trang** (cursor, `per-page=200`); một truy vấn là một batch. **Kiểm cú pháp tất định (phase 01):** trên trang đầu (≤ 200 bản ghi) của mỗi truy vấn, tỉ lệ bản ghi có tiêu đề + abstract chứa ít nhất một từ của **mỗi** mệnh đề AND (so khớp không phân biệt hoa thường, gốc từ) phải ≥ 80% trong số bản ghi có abstract; dưới ngưỡng → kiểm lại cú pháp trước freeze.

**Snowball** (OpenAlex `referenced_works` + `cites`): vòng 1 luôn chạy ở phase 05, hạt giống là T1 tạm (100 bài sau screening search + seed). Bản ghi snowball qua cùng cổng §3–§4, vào T0, được screening bằng cùng rubric; sau đó T1 được xếp lại **một lần** theo §6 rồi chốt.

**Late-records** (tìm thấy sau khi T1 chốt, kể cả từ tài liệu tham khảo khi đọc T2/T3): chấm R theo §6. Một late-record chỉ vào T1 khi (i) hạng tất định của nó ≤ 100 **và** (ii) chưa có điểm F nào được ghi; khi đó nó thay bài hạng 100 hiện tại theo đúng thứ tự §6. Sau khi điểm F đầu tiên được ghi, late-record chỉ được báo trong `late-records` và dùng cho kiểm prior work, không làm bài nền. Ngoại lệ chỉ hợp lệ bằng amendment được chủ dự án duyệt **trước** khi đọc toàn văn bài đó. Luôn báo số late-record lẽ ra lọt top-100.

## 6. Sàng lọc T1 (metadata + abstract)

Mỗi bản ghi T0 nhận đúng một quyết định. Thứ tự screening là hoán vị của `openalex_id` với seed 20261024.

| Mã | Nhận khi |
|---|---|
| I1 | Đối tượng là vận hành hệ phần mềm (Population, gồm mạng data center/cloud phục vụ dịch vụ) |
| I2 | Tác vụ chính là RCA/định vị lỗi/chẩn đoán sự cố, hoặc phát hiện bất thường có đầu ra định vị/chẩn đoán |
| I3 | Đề xuất phương pháp hoặc nghiên cứu thực nghiệm có đánh giá |

| Mã | Loại khi |
|---|---|
| E1 | RCA ngoài miền phần mềm (sản xuất, cơ khí, điện, năng lượng, y tế, mạng vô tuyến/viễn thông truy nhập, xe) |
| E2 | Chỉ an ninh/xâm nhập |
| E3 | Chỉ phần cứng/thiết bị vật lý (đĩa, máy chủ ở mức linh kiện, cảm biến) |
| E4 | Không có đánh giá thực nghiệm (position, vision, lý thuyết diagnosability của đồ thị mạng) |
| E5 | Survey/review: không loại khỏi T0, ghi `context-survey`, không vào xếp hạng T1 |
| E6 | Thiếu abstract sau mọi làn bổ sung: `needs-review`, quyết định từ tiêu đề + trang publisher; không đủ thì loại `E6-no-abstract` |
| E7 | Phát hiện bất thường thuần (không định vị/chẩn đoán) trên hệ phần mềm: I2 không đạt, loại `E7-detection-only` nhưng vẫn chấm R |

**Rubric R (0–10), mô tả mức:**

| Mã | Tiêu chí | Mức |
|---|---|---|
| R1 | Khớp tác vụ | 0 = ngoài Population hoặc tác vụ không liên quan lỗi; 1 = phát hiện bất thường/phân tích log/dự báo sự cố trên hệ phần mềm, không định vị; 2 = RCA/định vị/chẩn đoán trên hệ phân tán, cloud, mạng DC, cơ sở dữ liệu, hoặc job/hạ tầng, nhưng không ở mức dịch vụ microservice; 3 = RCA/định vị root cause ở mức service/pod/instance của microservice hoặc cloud-native |
| R2 | LLM | 0 = không LLM; 1 = LLM phụ trợ (tóm tắt, parse log, sinh báo cáo) hoặc mô hình ngôn ngữ nhỏ; 2 = LLM là lõi suy luận chẩn đoán/xếp hạng root cause |
| R3 | Telemetry thiếu | 0 = không nêu, hoặc chỉ chữ “noise/noisy” chung chung; 1 = abstract nêu telemetry/dữ liệu thiếu, không đầy đủ, nhiễu, lấy mẫu hoặc thiếu modality như **một điều kiện của bài toán**; 2 = điều kiện đó là trọng tâm thiết kế hoặc có đánh giá riêng |
| R4 | Đa modality | 1 khi abstract nêu ≥ 2 trong {metric, log, trace, event/alert, topology} được dùng làm đầu vào |
| R5 | Benchmark công khai | 1 khi abstract nêu tên benchmark/dataset công khai (RCAEval, Train-Ticket, Online Boutique, Sock Shop, AIOps challenge, Nezha, Loghub, HDFS, BGL…) |
| R6 | Tín hiệu artifact | 1 khi abstract/metadata nêu code hoặc dataset công khai (link, “open-source”, “publicly available”) |

**Chọn 100:** đủ điều kiện = include (I1∧I2∧I3, không E) và R1 ≥ 2. Xếp R giảm dần; hòa: R1, R3, R2, `q1_weak=0` trước, năm mới hơn, DOI chuẩn hóa (thiếu thì `openalex_id`) theo thứ tự từ điển. Lấy 100 đầu. Nếu < 100 đủ điều kiện: lấy hết, bù theo cùng thứ tự từ include có R1 = 1, gắn `fill-r1`, báo số bù.

**Dự phòng bài không-LLM:** đếm bài include có R1 = 3 ∧ R5 = 1 ∧ R6 = 1 nằm ngoài top-100; tối đa 10 bài (theo thứ tự §6) vào T2 với nhãn `reserve-nonllm`, được chấm F như các bài khác.

**Mẫu kép:** reviewer ngữ cảnh mới chấm độc lập (không thấy quyết định/điểm của người chấm 1) mẫu phân tầng 10% T0 (seed 20261024) + mọi `needs-review` + hạng 90–110. Báo: κ include/exclude (yêu cầu ≥ 0,7; dưới ngưỡng → sửa mô tả bằng amendment, chấm lại toàn bộ) và tỉ lệ khớp tuyệt đối R1, R2, R3. Bất đồng: include/exclude giải bằng đọc lại abstract (ghi cả hai quyết định, cột `final_decision` là quyết định sau đọc lại); ở hạng 90–110, điểm R dùng **điểm thấp hơn** trong hai người chấm. Người chấm thứ hai cùng họ mô hình: ghi là giới hạn.

**Chống trôi:** mỗi phiên screening chấm lại 5 bản ghi neo cố định (chọn ở batch đầu, seed 20261024) trước batch mới; lệch quyết định hoặc lệch R1 → dừng, rà lại.

## 7. Thẩm định toàn văn T2 (100 [+ reserve] → 10)

Chỉ chấm F khi có toàn văn đọc được. Bài không truy cập được toàn văn giữ nhãn `abstract-only`, không vào T3. Phase 06 luôn yêu cầu chủ dự án tải tay mọi bài không có bản OA nằm trong top-30 theo R (thứ tự §6); nếu số bài có toàn văn trong T1 < 30, yêu cầu mở rộng cho toàn bộ T1. Báo tỉ lệ truy cập toàn văn theo tầng R (hạng 1–30, 31–60, 61–100).

**Rubric F (0–30), mô tả mức, đóng băng trước bài đọc đầu tiên:**

| Mã | Tiêu chí | Mức |
|---|---|---|
| F1 | Khớp MVP (0–5) | 5 = RCA microservice, đầu ra xếp hạng service/pod, đánh giá bằng AC@k/top-k/MRR; 4 = như 5 nhưng đầu ra là loại lỗi/metric hoặc chỉ top-1; 3 = RCA hệ phân tán/cloud chung có đầu ra định vị; 2 = chẩn đoán sự cố mức incident (triage, phân loại) không định vị thành phần; 1 = chỉ phát hiện bất thường; 0 = khác |
| F2 | Thiếu telemetry (0–5) | 5 = có thí nghiệm có kiểm soát bỏ/nhiễu/giảm mẫu một modality hoặc nguồn telemetry và báo kết quả theo điều kiện; 4 = có phân tích robust với dữ liệu thiếu nhưng không theo modality; 3 = dùng ≥ 2 modality, kiến trúc cho phép cắt có kiểm soát nhưng không thí nghiệm; 1 = một modality chính, modality phụ tùy chọn; 0 = một modality |
| F3 | Tái hiện (0–10) | code: 3 = repo công khai + license + hướng dẫn chạy, 2 = repo không license hoặc thiếu hướng dẫn, 1 = “available on request”/link chết, 0 = không; dữ liệu: 2 = dataset công khai, 1 = công khai một phần, 0 = riêng; tính toán: 3 = CPU hoặc ≤ 12 GB VRAM với mô hình mở, 2 = cần API LLM đóng nhưng thay được bằng mô hình mở, 1 = cần GPU lớn hơn, 0 = không thực hiện được; mô tả: 2 = đủ thuật toán, siêu tham số, prompt, tiền xử lý, 1 = thiếu một mục, 0 = thiếu ≥ 2 |
| F4 | Chất lượng đánh giá (0–4) | +1 cho mỗi: baseline mạnh gần đây (≥ 2), ≥ 2 dataset, metric định nghĩa rõ kèm mẫu số, có lặp/độ bất định/kiểm định |
| F5 | Dư địa cải tiến (0–3) | 3 = limitation/failure mode cụ thể, có thể đo trên bundle NT114; 2 = limitation cụ thể nhưng khó đo; 1 = limitation chung chung; 0 = không nêu |
| F6 | Tương thích NT114 (0–3) | +1: dùng một trong RCAEval/Nezha/RCA100/AIOps2025 hoặc hệ Online Boutique/Sock Shop/Train-Ticket; +1: metric chuyển được sang AC@k/MRR; +1: đầu vào là telemetry đã lưu (không cần môi trường live) |

**Cổng T2:** toàn văn đã đọc; đóng góp chính là phương pháp RCA/định vị có đánh giá. Tổng = Σ wᵢ·Fᵢ với wᵢ = 1. Xếp giảm dần; hòa: F1, F3, F2, R, DOI/openalex_id. Lấy 10 (bài `reserve-nonllm` cạnh tranh cùng bảng). Mỗi điểm F trỏ tới locator (trang/mục/bảng).

**Kiểm chéo F:** reviewer ngữ cảnh mới chấm độc lập ≥ 10% bài có F (tối thiểu 5 bài, luôn gồm hạng 9–12). Lệch tổng ≥ 3 điểm ở một bài → người chấm chính rà lại bài đó với locator của cả hai; ghi điểm cuối và lý do.

## 8. Phân tích sâu và chọn 1 (T3)

**Cổng G (đạt/không, kèm bằng chứng tĩnh):**

| Mã | Cổng |
|---|---|
| G1 | Repo truy cập được + có file license + có entry point (script/notebook chạy được theo README); hoặc, nếu không có code, bài có đủ checklist {thuật toán, siêu tham số, prompt (nếu dùng LLM), tiền xử lý} |
| G2 | Ít nhất một dataset đánh giá công khai tải được (HEAD/landing page kiểm ngày) hoặc nằm trong bundle NT114 |
| G3 | Ước lượng tĩnh (`static-estimate`) từ bài và repo: chạy được trên hồ sơ [rtx4080-laptop-12gb](../../nt114-rca/nt114-rca/configs/hardware/rtx4080-laptop-12gb.yaml) hoặc CPU; thành phần LLM thay được bằng một LLM open-weight cục bộ |
| G4 | Rút về **một LLM** mà không bỏ đóng góp lõi, hoặc lõi không-LLM ghép được với một LLM; ghi rõ phần lõi giữ lại |
| G5 | Dùng ≥ 2 modality, để điều kiện thiếu telemetry có nghĩa |

Không được nới cổng sau khi đã biết bài nào sẽ đạt.

- **≥ 2 bài đạt mọi cổng:** chấm lại F bằng bằng chứng sâu. Mỗi thay đổi điểm ghi vào `work/f-rescore-log.csv` (bài, tiêu chí, điểm cũ, điểm mới, locator, lý do) **trước** khi tính bảng xếp hạng. Báo cả hạng theo F của T2 lẫn hạng theo F chấm lại; nếu hạng 1 khác nhau giữa hai bảng, reviewer ngữ cảnh mới chấm lại độc lập hai bài đầu và cả hai kết quả được báo.
- **Đúng 1 bài đạt:** đề xuất bài đó với nhãn `single-eligible`; độ nhạy chạy trên cả 10 bài T3 khi bỏ cổng G để báo bài này đứng đâu.
- **0 bài đạt:** không đề xuất; báo bảng G; `waiting-human`. Lựa chọn cho chủ dự án: nới đúng một cổng nêu tên bằng amendment (ghi trước khi chấm lại), hoặc mở rộng sang hạng 11–20 của T2 theo thứ tự F.

**Độ nhạy:** tổng = Σ wᵢ·Fᵢ. 18 kịch bản: wᵢ ∈ {0,5; 1,5} cho từng i (12) và wᵢ = 0 cho từng i (6). Hòa ở hạng 1 trong một kịch bản tính là không giữ hạng. Hạng 1 ổn định khi giữ hạng 1 ở ≥ 15/18 kịch bản; không ổn định → báo top-2, `waiting-human`. Cùng 18 kịch bản chạy trên **toàn bộ bài có F ở T2**: bài nào vào top-10 ở bất kỳ kịch bản nào mà chưa ở T3 được liệt kê (và đọc sâu nếu còn ngân sách phiên). Thêm kịch bản ±1 điểm trên các ô F mà kiểm chéo phase 07 lệch. Ghi chú: đa modality được tính ở R4, F2 và G5 một cách có chủ đích; kịch bản w₂ = 0 cho thấy ảnh hưởng của nó.

**Cờ `h1-compat`** (không cộng vào điểm): “có” khi đầu ra của phương pháp là xếp hạng ≥ top-5 và có điểm số hoặc độ tin cậy dùng được cho phân tích selective (H1: `gain_exact@0.7`, retrieval=none, pool `single_modality`). Cờ “không” ở bài hạng 1 → ghi `waiting-human` cho chủ dự án (không tự đổi H1).

Mỗi ứng viên T3 có kiểm prior work làn hội nghị/preprint (ICSE/FSE/ASE/WWW/NeurIPS/KDD/ISSRE/arXiv) để biết bài nền có bị vượt bởi công trình mới hơn.

## 9. Toàn văn, quyền và trích dẫn

- Thứ tự tìm: OpenAlex `best_oa_location` → Unpaywall → arXiv/bản tác giả cùng nội dung (ghi khác biệt phiên bản) → chủ dự án tải tay qua quyền truy cập của mình (không tự động SSO, không vượt paywall).
- Ghi: PDF SHA-256, kích thước, phiên bản (publisher/accepted/preprint), extractor + version, text SHA-256, số trang. Lý do tải tay thất bại ghi vào ledger.
- Bản preprint thay cho bản tạp chí chỉ được dùng khi nội dung tương ứng được ghi rõ; số liệu cho quyết định T3 ưu tiên bản tạp chí.
- Trích dẫn nguyên văn chỉ từ văn bản đã đọc; OCR cần đối chiếu trang ảnh.

## 10. Không đủ 1.000 bản ghi hợp lệ

“Hợp lệ” = qua §3–§4. Bộ truy vấn §5, làn Elicit, seed phase 02 và snowball vòng 1 luôn chạy hết. Sau đó, nếu N(T0) < 1.000 **hoặc** N(T0) × precision ước lượng < 500, chạy tiếp, mỗi bước đúng một lần:

1. Snowball vòng 2 từ T1 sau vòng 1.
2. Truy vấn bổ sung chỉ gồm biến thể từ đồng nghĩa của §5 (ghi trong amendment trước khi chạy).

Tỉ lệ bản ghi mới hợp lệ của mỗi bước được báo (đường cong bão hòa), không phải điều kiện lặp. Nếu vẫn N(T0) < 1.000: dừng thu thập, báo N thực, đường cong bão hòa, phân bố theo truy vấn; tiếp tục phễu 100 → 10 → 1 với N thực nếu N ≥ 300; N < 300 → dừng phễu, `waiting-human`. Lựa chọn mở rộng cho chủ dự án: thêm tier `q1_noncs`, category Engineering, hoặc năm 2018–2019. Không nới §3–§4 khi chưa có amendment được chủ dự án duyệt. Không thêm bản ghi ngoài chủ đề để đủ số.

## 11. Batch, checkpoint và resume

`work/state.json` (bản thực thi: `load_state`, `batch_done`, `commit_batch` trong `work/scripts/common.py`):

```json
{"protocol_sha256": "...", "phases": {"03": {"status": "running",
  "batches": {"A1": {"status": "committed", "attempt": "A1-a01", "protocol_sha256": "...",
    "inputs": [{"path": "...", "sha256": "..."}],
    "outputs": [{"path": "work/records/search-A1-a01.csv", "sha256": "..."}],
    "receipt": "work/receipts/03-search-01.json", "count": 0,
    "attempts": [{"attempt": "A1-a01", "status": "committed", "at": "..."}]}}}}}
```

- Kích thước batch: tìm kiếm 1 truy vấn; lấy lại metadata seed 50 ID; khử trùng/cổng 1 lần toàn bộ (tất định); screening 50 bản ghi; truy cập toàn văn 10 bài; thẩm định 4 bài; đọc sâu 1 bài.
- Batch chỉ `committed` khi output đầy đủ và hash ghi vào state; receipt ghi exit của lệnh chạy batch (một receipt có thể phủ nhiều batch của cùng một lệnh).
- Resume (`batch_done`): batch được bỏ qua chỉ khi `status == committed`, `protocol_sha256` của batch bằng `protocol_sha256` hiện hành, hash mọi input và output khớp đĩa. Lệch → chạy attempt mới; attempt cũ giữ trong `attempts[]` và file của nó không bị xóa.
- Output batch bất biến: tên file chứa mã attempt (`-aNN`), không ghi đè; tổng hợp sinh lại từ các batch đã commit (attempt mới nhất).

## 12. Provenance tối thiểu mỗi bản ghi

`openalex_id, doi, arxiv, title, year, publication_date, venue, source_type, issn_l, issns, publisher, type, language, first_author, cited_by, is_retracted, oa_url, abstract, abstract_source, origin(s) (search:<query>:<page> | reuse:<file>:<row> | elicit:<query> | snowball:<seed>), raw_sha256, retrieved_at_utc, q1_rule_trace, sjr_cs_q1, sjr_cs_categories, q1_weak, dup_group, exclude_reason`.
