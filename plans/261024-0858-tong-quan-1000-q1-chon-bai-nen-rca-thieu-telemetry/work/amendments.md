# Thay đổi giao thức

## Trước freeze (phase 01, 24/10/2026)

| Ngày | Mục | Thay đổi | Lý do | Bằng chứng |
|---|---|---|---|---|
| 2026-10-24 | §5 D1 | `AIOps OR "artificial intelligence for IT operations"` → `"AIOps"` | Probe: 745 bản ghi, 5 tiêu đề đầu là "AI in business/pharmacy/banking operations" (stemming làm cụm từ khớp lỏng). Biến thể `"AIOps" OR "IT operations"` trả 984.389 bản ghi, cho thấy OR cấp cao nhất với cụm từ làm hỏng bộ lọc; `"AIOps"` trả 449 bản ghi đúng chủ đề | `work/query-probe.csv` (receipt `work/receipts/01-query-probe-01.json`), probe lại sau sửa: `work/query-probe-02.csv` (receipt `01-query-probe-02`); số của các biến thể thử (449; 984.389; 606) đến từ probe tạm `F:/Nam/UIT/nt114-private-attempts/261024/probe2.py`, không có receipt |
| 2026-10-24 | §5 D6 | thêm `AND (cloud OR microservice OR software OR "online service")` | Probe: 22.099 bản ghi, chủ yếu chẩn đoán lỗi máy móc công nghiệp (ngoài Population); có ràng buộc hệ thống còn 606 | như trên |
| 2026-10-24 | §4 | Thêm thuật ngữ log/vận hành vào nhóm Hệ thống; thêm nhánh `∨ Cụm mạnh`; đổi kiểm tra phase 01 bước 5 từ “sai > 1 mỗi phía trên 30+30 mẫu” sang hiệu chỉnh trên 736 bản ghi có nhãn R | Regex gốc chỉ giữ 46/58 R3 và 93/147 R2 (nhiều bản ghi thiếu abstract hoặc chỉ nói “log”); mẫu âm 30 bản ghi chọn theo từ khóa có cả bản ghi đúng Population nên không dùng được làm chuẩn | `work/regex-check.csv` (receipt `01-sjr-regex-01`), `work/regex-calibration.json` (receipt `01-regex-calibration-01`) |
| 2026-10-24 | toàn bộ (r2) | Sửa theo [review trước freeze](../research/protocol-review.md): §8 thêm nhánh 0/1 bài đạt G, ràng buộc chấm lại F, độ nhạy trên toàn T2, cờ `h1-compat`; §5 luật late-records; §6–§7 mô tả mức R/F, E7, mẫu kép R1–R3, `reserve-nonllm`, hoán vị thứ tự screening; §4 cổng sau bổ sung abstract, `needs-review-t0`, kiểm sai âm phân tầng, precision T0; §3 Q-5 mốc `to_publication_date`, Q-9 cách xác định, báo `q1_noncs`/Q-7 riêng; §10 mỗi bước một lần, N < 300 dừng, điều kiện precision; §11 khớp script (attempts, protocol hash, input hash); §2 làn Elicit đóng băng; TASK_RE `locali[sz]` | 2 lỗi chặn PR-01, PR-02 và các mục PR-03…PR-27 | `research/protocol-review.md` |
| 2026-10-24 | §5 B1, C1 | B1 thêm `LLMs`, `ChatGPT`, `"language model"`, `"foundation model"`; C1 thêm `missing metrics/logs/traces`, `limited observability`, `unobservable`, `trace sampling`, `partial telemetry`, ràng buộc hệ thống thêm `"distributed system"`, `"online service"` | PR-09 (recall hai họ quan trọng nhất của MVP) | `work/query-probe-03.csv` (receipt `01-query-probe-03`): B1 1.566 bản ghi, C1 145 |
| 2026-10-24 | §5 A2 | Bỏ `"IT operations"`, thêm `microservice` | Kiểm độ phủ mệnh đề AND trên trang 1: A2 chỉ 0,491; bản ghi trả về khớp “root cause analysis” nhưng không khớp mệnh đề hệ thống (cáp, nồi hơi, chuỗi cung ứng), cho thấy `"IT operations"` bị xử lý như khớp mọi chữ “operation” | `work/query-probe-03.csv` → `work/query-probe-04.csv` (receipt `01-query-probe-04`): A2 323 bản ghi, độ phủ 0,861; mọi truy vấn ≥ 0,85 |

## Sau freeze

| Ngày | Mục | Thay đổi | Lý do | Bản ghi bị ảnh hưởng | Chấm lại |
|---|---|---|---|---|---|
| 2026-10-24 | §4 nhóm Hệ thống (bản thực thi `SYSTEM_RE` trong `work/scripts/common.py`; văn bản protocol.md giữ nguyên hash freeze) | thêm `\bdatabases?\b`, `\bDBMS\b`, `\bAI systems?\b` | Kiểm sai âm phase 04 trên seed: 2/25 sai âm ở tầng giáp ranh (W3197917898 DBMind tự chẩn đoán root cause CSDL; W4410431126 survey phân tích lỗi/chẩn đoán lỗi hệ AI), vượt ngưỡng > 1 của §4; 0/25 ở tầng không khớp. Bằng chứng: `work/t0seed2-fn-check.json`, `work/records/t0seed2-fn-judged.csv` (receipt `04-fn-judge-seed-02`). Hiệu chỉnh in-sample trên 736 nhãn 11/10: `work/regex-calibration-04.json` (receipt `04-regex-calibration-04`) | Chưa có bản ghi nào được screening T1, nên không đổi tập đã chọn ở tầng nào | Chạy lại cổng T0 cho seed (tag `t0seed4`), rút lại mẫu sai âm trên tập loại mới |

Ghi chú quy trình: receipt `04-regex-calibration-03` và `04-build-t0-seed-03` (tag `t0seed3`) chạy **trước** khi bản sửa regex được ghi vào `common.py` (lệnh sửa dừng ở assert), nên chỉ tái tạo kết quả regex cũ; không dùng làm bằng chứng cho amendment này.

## §10 bước 2: truy vấn đồng nghĩa (soạn trước khi chạy)

Điều kiện kích hoạt: sau snowball vòng 1, N(T0) = 967 < 1.000 (`work/records/t0snow2-t0.csv`, receipt `04-t0-review-snow-01`). Mỗi truy vấn dưới đây chỉ thay thuật ngữ của một họ §5 bằng từ đồng nghĩa hoặc biến thể chính tả. Không thêm khái niệm mới, không đổi bộ lọc Q-5/Q-6/journal và không đổi cổng §3–§4. Mỗi truy vấn là một batch phase 03 (id `S1`…`S7`). Kết quả đi qua đúng cổng §3–§4 và rubric §6 như truy vấn gốc. Kiểm cú pháp dùng cùng ngưỡng phase 01: độ phủ mệnh đề AND trên trang 1 ≥ 0,80.

| ID | Họ gốc | Truy vấn |
|---|---|---|
| S1 | A1, A3 | `("root-cause" OR "root causes" OR "fault localisation" OR "failure localisation" OR "fault isolation" OR "fault identification" OR "failure attribution" OR culprit) AND (microservice OR "micro-service" OR "service mesh" OR Kubernetes OR container OR "cloud-native")` |
| S2 | A4 | `(outage OR "service failure" OR "production incident" OR "incident management" OR troubleshooting) AND ("root cause" OR diagnosis OR localization OR triage) AND (cloud OR "online service" OR microservice OR "distributed system" OR "web service")` |
| S3 | B1, B2 | `("large language model" OR "pre-trained language model" OR "generative AI" OR "LLM-based" OR "LLM agent" OR copilot) AND (troubleshooting OR outage OR "failure diagnosis" OR "fault localization" OR "incident management" OR "anomaly diagnosis")` |
| S4 | C1 | `(missing OR incomplete OR unavailable OR absent OR "lack of" OR insufficient) AND (telemetry OR observability OR monitoring OR traces) AND ("root cause" OR "fault diagnosis" OR "failure diagnosis" OR "fault localization") AND (microservice OR cloud OR "distributed system")` |
| S5 | D1 | `("intelligent operations" OR "operations and maintenance" OR "site reliability engineering" OR DevOps) AND (fault OR failure OR "root cause" OR incident OR anomaly) AND (cloud OR microservice OR software OR "online service")` |
| S6 | D4 | `("causal analysis" OR causality OR "causal reasoning" OR counterfactual OR Granger) AND ("root cause" OR "fault localization" OR "failure diagnosis") AND (microservice OR cloud OR "online service" OR "distributed system")` |
| S7 | D2 | `("log parsing" OR "system logs" OR "log data" OR "log mining") AND (anomaly OR failure OR fault OR diagnosis) AND (system OR software OR cloud)` |

Probe trang 1 (`work/query-probe-synonym-01.csv`, receipt `03-synonym-probe-01`): S4 có độ phủ 0,797 < 0,80. Mệnh đề `(diagnosis OR "root cause" OR localization)` khớp lỏng ("Disease Diagnosis", "Localized"), nên được thu về cụm của C1/A3 trước khi chạy: `("root cause" OR "fault diagnosis" OR "failure diagnosis" OR "fault localization")`. Probe lại: `work/query-probe-synonym-02.csv`.

Kết quả thực thi §10 (mỗi bước đúng một lần):

- Bước 2 (S1–S7) chạy ngày 25/10/2026, receipt `03-synonym-search-01`, tổng 2.914 dòng. Bước 1 (snowball vòng 2, hạt giống là top 100 của `work/records/all2-t1-ranked.csv`) chạy ngay sau, receipt `05-snowball-r2-01`, 1.149 dòng. Hai bước độc lập với nhau. Bước 2 truy xuất trước bước 1 nhưng không làm đổi tập T0 của bước nào.
- T0 sau cả hai bước là 1.085 bản ghi (`work/records/t0r2b-t0.csv`), tăng 118 so với 967. Phần tăng chỉ đến từ snowball vòng 2 có 5 bản ghi, chỉ đến từ truy vấn đồng nghĩa có 113 bản ghi (`work/saturation-curve.json`, receipt `05-saturation-01`).
- Điều kiện N(T0) ≥ 1.000 đạt nên ngừng thu thập. Điều kiện phụ N(T0) × precision < 500 vẫn đúng: precision T1 khoảng 0,12, nên N × precision khoảng 130. §10 không có bước thứ ba, vì vậy điều này được báo như một giới hạn và không lặp lại bước nào.

## Đính chính 2026-10-26 (phase 10)

- Dòng về điều kiện phụ §10 ở trên ghi precision khoảng 0,12 và N × precision khoảng 130; đó là ước lượng trước khi T1 chốt. Số chốt (`work/report-stats-10.json`, receipt `10-report-stats-01`): precision T0 = 121/1.085 ≈ 0,112, Wilson 95% [0,094; 0,132], N × precision ≈ 121. Kết luận không đổi: vẫn < 500, báo như giới hạn. Không đổi giao thức.

## Phát hiện sau tổng quan 2026-10-26: phản chứng bên thứ ba cho RCLAgent (không đổi tập hay điểm)

- Nguồn: tìm có mục tiêu bằng Perplexity Pro theo quyết định chủ dự án 2026-10-26; mọi dòng đối chiếu với arxiv.org, Crossref hoặc OpenAlex (`work/targeted-search-261026-dedup.csv`, receipt `10-targeted-search-dedup-01`). Ba bản preprint đều đã có trong corpus (làn prior work, không đếm vào T0) nhưng kết quả chạy lại RCLAgent của chúng chưa được dùng ở T3.
- arXiv:2601.21359 v1 (PRISM, đọc có mục tiêu toàn văn HTML): RCLAgent trên 735 sự cố RCAEval Top-1 0,10; trên RE2OB Top-1 0,18, Top-3 0,32; 79 s mỗi ca. Backbone và phiên bản RCLAgent họ dùng chưa xác định. Bài RCLAgent tự báo R@1 56,67 trên RE2-OB với Qwen-3.6-Plus.
- arXiv:2607.13548 v2: RCLAgent với GPT-5.2 trên OpenRCA Market cloudbed-1 đúng thành phần 8/70, Full 0/70; benchmark và thiết lập khác, so sánh hạn chế.
- arXiv:2608.21310 v2: trên RCABench, RCLAgent V2 53,4% so với 65–80% của các agent mở; số vòng tăng theo kích thước trace vì mỗi span một sub-agent.
- Phạm vi ảnh hưởng: không đổi cổng G, điểm F, ma trận quyết định hay đề xuất `single-eligible`; không sửa tổng quan đã chốt. Đây là bằng chứng rủi ro cho thiết kế: số đích của bài có thể không tái lập được ngoài thiết lập của tác giả, và nhánh (a) đã chọn là adaptation nên không kế thừa số liệu của bài. Chủ dự án đã chấp nhận RCLAgent có điều kiện, không khẳng định thắng ổn định; phát hiện này được nêu để chủ dự án xem, không tự đảo quyết định.
