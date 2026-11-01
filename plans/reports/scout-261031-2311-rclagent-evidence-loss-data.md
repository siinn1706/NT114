# Scout dữ liệu: đo mất bằng chứng theo giai đoạn (RQ b) trên corpus round 2 và S1 v2

Ngày 2026-10-31. Phạm vi: chỉ đọc dữ liệu đã log (CPU, không chạy Kaggle, không đụng test split RE2-OB). Đây là báo cáo scout: nó nói đo gì là khả thi và số liệu thô thấy được gì, chưa phải kết luận cơ chế. Các câu "thấy" dưới đây là mô tả trên 8 case train, 3 seed, nên chỉ có giá trị mô tả.

## 0. Tóm tắt các điều quyết định thiết kế đo

1. Join không mơ hồ. Harness ép `ThreadPoolExecutor(1)` (`kaggle/smoke-worker.py` `TrackedPool`, dòng 363-367) nên mỗi run là một luồng tuần tự. Trong 144 run, 100% cặp request/response khớp `number`, 10191/10191 `tool_result` khớp đúng tool call của response ngay trước nó (tên và tham số) và cùng `span_id`, 3888/3888 node trong `trace-graph.json` có `raw.parent_span` khớp cây, 3642/3642 prompt consolidate chứa đúng self-evidence của span và đúng output consolidate của các con.
2. Mô hình xác định theo (prompt, seed). Sampling cố định `temperature 0.7, top_p 0.8, top_k 20, seed = seed của run` trên mọi request (retry dùng seed dẫn xuất). Round 2 và S1 v2 cùng seed cho luồng sự kiện giống hệt từng byte cho đến request tổng hợp cuối, nơi chỉ khác thứ tự dịch vụ trong hint do hash seed (62 cặp cùng cấu hình mà cả hai lần đều hoàn tất: 42 cặp giống hệt toàn bộ, 20 cặp chỉ lệch đúng tại request cuối). Hệ quả: đối chứng ghép cặp sạch cho giai đoạn 1-2, nhưng mọi thay đổi nhỏ trong prompt làm lệch toàn bộ đường lấy mẫu phía sau (chaos), nên "một thay đổi tối thiểu" không tồn tại ở mức token.
3. Nguồn log không chứa bằng chứng nào trong 8 case. Mọi dòng log không rỗng (298.146 dòng trong S1 v2) đều có `severity: unknown`, và chỉ thuộc `cartservice`, `frontend`, `redis`. Không có ERROR log và không có log của bất kỳ dịch vụ GT nào. Điều này giải thích vì sao bỏ logs không làm giảm điểm. Kèm theo, 100% kết quả log không rỗng (222/222) vượt ngân sách 2048 token và bị harness cô đọng thành template.
4. Nguồn metric có bằng chứng ở 8/8 case (kiểm bằng oracle chạy `metric-repair.py` trên dữ liệu input): truy vấn dịch vụ GT tại thời điểm root span luôn trả về bảng KPI của chính dịch vụ GT (chi tiết mục 5.2). Vậy mất bằng chứng KHÔNG nằm ở nguồn.
5. Dịch vụ GT có mặt trong trace được duyệt ở 5/8 case. 3/8 case (A 30e3c7 emailservice, A de6a50 checkoutservice, B 272a47 recommendationservice) không có span nào của GT; agent chỉ truy vấn dịch vụ xuất hiện trong trace, nên bằng chứng metric của GT không bao giờ được truy xuất (trừ A de6a50 `metric_no_log`, 3/3 run model tự gọi `checkoutservice`). Đây là giai đoạn mất bằng chứng thứ 0 (chọn truy vấn), nằm trước chuỗi tool, self-state, consolidation, synthesis.
6. Chuỗi 4 giai đoạn đo được ở 5 case có GT trong trace (S1 v2, run hoàn tất, điều kiện `metric`, n = 14): tool trả bảng cho GT 14/14; span GT tự đánh abnormal 92/98 (94%); GT có trong danh sách hint "metric anomalies only" 14/14; consolidation cấp root nêu GT chỉ 3/14 (21%); điểm cuối R@1 = 10/14 (71%). Điều kiện `no_metric` cùng 15 run: tool trả bảng 0, span GT abnormal 0/108, hint chứa GT 0/15, R@1 = 5/15 (nhờ cấu trúc trace, ví dụ currencyservice chiếm 10/25 span).
7. Điểm gãy lớn nhất khi có metric không phải mất bảng metric mà là bằng chứng bị gán nhãn sai ở self-state và bị consolidation làm loãng. Trong `metric` và `metric_no_log` với GT trong trace (29 run), 11/11 run trượt R@1 có tuyên bố `has_error_logs=true` bịa (hint "ERROR LOGS: frontendservice"), 18/18 run đúng R@1 không có tuyên bố đó. Giả thuyết cần kiểm, vì tuyên bố tập trung ở 3 case (A 99f095, B 29583d, 1 run B ad1c27) nên nhiễu bởi case.
8. Có một nhiễu thiết kế điều kiện: câu trả lời rỗng của `no_metric` là `{"message":"No matching records found."}` (NO_ROWS) còn của `metric` là `{"message":"No fluctuating metrics found."}` (NO_KPI). Sau khi gộp hai câu chữ này, `metric` và `no_metric` vẫn rẽ nhánh ở response của model (event thứ 9-28, trung vị 15) trước khi có bảng thật nào xuất hiện trong 12/15 run có bảng, và rẽ nhánh sớm trong cả 9 run không có bảng nào. Span không có bảng: `metric` (NO_KPI) 2,0 request/span, `no_metric` (NO_ROWS) 3,35 request/span. Vậy một phần khác biệt quá trình giữa hai điều kiện là hiệu ứng câu chữ, không phải thiếu bằng chứng.

## 1. Dữ liệu và cách đọc

Bốn zip (đã đọc bằng `zipfile`, không giải nén vào repo):

| Corpus | Package | Zip |
|---|---|---|
| round 2 (r2) | A | `kaggle/runtime/kaggle-output-a-r2-v1/rclagent-smoke/rclagent-smoke-results.zip` |
| round 2 (r2) | B | `kaggle/runtime/kaggle-output-b-r2-v1/rclagent-smoke/rclagent-smoke-results.zip` |
| S1 v2 | A | `kaggle/runtime/kaggle-output-a-s1-v2/rclagent-smoke/rclagent-smoke-results.zip` |
| S1 v2 | B | `kaggle/runtime/kaggle-output-b-s1-v2/rclagent-smoke/rclagent-smoke-results.zip` |

Mỗi zip có 36 run (4 case x 3 điều kiện x 3 seed) với các thành viên `run/traces/<case>--<cond>--s<seed>/{events.jsonl,result.json,trace-graph.json,worker-status.json}`, `run/scoring/<run>/{groundtruth.csv,author-score.txt,scorer-status.json,error_traces.txt,result/conversation_trace_1.txt}`, `run/tools-<run>.log`, `run/worker-<run>.log`. Run thất bại không có thư mục `scoring/` (không có `groundtruth.csv` trong zip, GT vẫn lấy được từ run anh em cùng case). Dữ liệu input của từng case (metric, log, trace) nằm ở `kaggle/runtime/kaggle-dataset-check-{a,b}-s1-v3/traces/<trace_id>/input/` và dùng cho oracle ở mục 5.2.

Tám case: A = 30e3c7 (GT emailservice, delay), 5f7a77 (checkoutservice, mem), 99f095 (currencyservice, loss), de6a50 (checkoutservice, cpu); B = 272a47 (recommendationservice, cpu), 29583d (emailservice, delay), 7bbfa6 (recommendationservice, socket), ad1c27 (currencyservice, disk). Mỗi case có đúng một dòng `groundtruth.csv`.

## 2. Yêu cầu 1: đếm theo run

### 2.1 Hoàn tất và dừng

| Corpus | Hoàn tất / 72 | Run dừng | Lý do dừng |
|---|---|---|---|
| r2 | 62 | 10 | 3 (A, `no_metric`) hết 160 request; 5 vượt 4 vòng tool/span; 1 (B 272a47 `no_metric` s26) `print_results` sai kiểu (`'currencyservice' is not of type 'object'`); 1 (B ad1c27 `metric` s27) span_id sai trong JSON agent |
| S1 v2 | 70 | 2 | đúng hai lỗi cuối ở trên (cả hai tái hiện y hệt từ round 2) |

Hai run dừng ở S1 v2 là xác định (deterministic) và là lỗi định dạng của model, không phải do ngân sách. Chúng làm B `metric` và B `no_metric` có 11/12 run hoàn tất.

### 2.2 Đếm sự kiện, S1 v2, gộp A+B theo điều kiện (12 run mỗi dòng cho mỗi package)

| Điều kiện | Run hoàn tất/24 | Span | request self_state | request consolidate | request cuối | retry tool-call lỗi | agent_complete self | agent_complete consolidate | `print_results` |
|---|---|---|---|---|---|---|---|---|---|
| metric | 23 | 648 | 1366 | 623 | 23 | 10 | 626 | 623 | 23 |
| metric_no_log | 24 | 648 | 1419 | 648 | 24 | 10 | 648 | 648 | 24 |
| no_metric | 23 | 648 | 2106 | 623 | 23 | 13 | 627 | 623 | 23 |

Cột span là tổng span của 24 run, kể cả run dừng giữa chừng, nên `agent_complete` nhỏ hơn span ở run dừng. Round 2 cho cùng số liệu cho `metric` và `metric_no_log` (luồng giống hệt), còn `no_metric` r2: 15/24 hoàn tất, 1757 request self_state, 477 consolidate, 520 self_state hoàn tất.

### 2.3 Phân tích đầu ra agent (S1 v2, tất cả run, tính trên `agent_complete`)

| Điều kiện | self-state parse JSON | self-state thuộc nhánh fallback (thiếu `has_error_logs`/`has_metric_anomaly`) | `is_abnormal=true` | `has_metric_anomaly=true` | `has_error_logs=true` | consolidate parse + có `local_root_cause` | `local_root_cause` là `null` |
|---|---|---|---|---|---|---|---|
| metric | 626/626 | 0 | 168 | 149 | 4 | 623/623 | 4 |
| metric_no_log | 648/648 | 0 | 213 | 175 | 10 | 648/648 | 4 |
| no_metric | 627/627 | 0 | 9 | 0 | 0 | 623/623 | 27 |

Giải thích cần lưu ý. Tỉ lệ parse 100% là do harness: `smoke-worker.py` dòng 380-392 gọi `guard.stop` khi JSON agent sai hoặc thiếu `is_abnormal` boolean hoặc `local_root_cause`, nên chỉ output hợp lệ mới được ghi `agent_complete`. Do đó "parse được" không phải thước đo mất bằng chứng; chỉ hai lần dừng vì JSON sai ở mục 2.1 là phần "không parse" thật sự. Nhánh fallback của tác giả (`coordinator.py` 274-292, không có hai khoá còn lại) không bao giờ chạy: không request nào trong 144 run có tin nhắn cuối bắt đầu bằng "Based on all retrieved evidence above". Ngoài `null`, consolidation còn trả chuỗi `"none"` và `"unknown"` rất nhiều (xem 6.3), nên đếm `null` đơn thuần đánh giá thấp số lần consolidation từ chối nêu nguyên nhân.

Request cuối và kết quả: mọi run hoàn tất có đúng một request tổng hợp cuối, response 200, gọi `print_results`, và `result.json` có `root_causes` (số phần tử 10 hoặc hơn). Prompt cuối dài 4711 đến 8202 token (trung vị 5594).

### 2.4 Tool result rỗng theo tool và điều kiện (S1 v2, gộp A+B)

Nguồn rỗng được định nghĩa: log là header-only (`log_id,timestamp,cmdb_id,log_name,value`), metric là mọi thứ không bắt đầu bằng `key,`.

| Điều kiện | `search_logs` gọi | log không rỗng | `search_fluctuating_metrics` gọi | metric bảng | metric NO_KPI | metric NO_ROWS | `tool_result_budget` applied |
|---|---|---|---|---|---|---|---|
| metric | 744 | 48 | 691 | 150 | 479 | 62 | 48 |
| metric_no_log | 769 | 0 (nguồn vắng, `source=absent`) | 757 | 177 | 518 | 62 | 0 |
| no_metric | 1363 | 174 | 957 | 0 (nguồn vắng, 957 NO_ROWS) | 0 | 957 | 174 |

Hai điểm đáng nêu. Một, `applied` trùng đúng số log không rỗng ở mọi điều kiện (48, 0, 174): 222/222 kết quả log không rỗng bị cô đọng (`budget_tokens` 2048; ví dụ 1537 dòng cartservice, 124.451 token gốc thành 444 token, 4 template). Cô đọng giữ số lượng, giây đầu và cuối, giá trị khác biệt và giá trị đầu, "no row omitted". Hai, 62 NO_ROWS trong `metric` là truy vấn `frontendservice` (54) và `productcatalogservice` (8). `frontendservice` luôn NO_ROWS vì tên dịch vụ trong metric là `frontend` và `frontend-external` (oracle ở 5.2), nên mọi span frontend nhận đúng câu trả lời của nguồn vắng trong cả ba điều kiện. Chưa giải thích được 8 NO_ROWS của `productcatalogservice` (oracle tại giờ root cho NO_KPI), xem mục 8.

## 3. Yêu cầu 2: join, truy vết và cây

| Câu hỏi | Kết quả | Cơ chế / bằng chứng |
|---|---|---|
| Request/response join được với `span_id` và `operation` không | Có, không mơ hồ | `request` mang `span_id`, `operation` (self_state_verification, consolidate, None = tổng hợp cuối), `number`, `attempt`, `retry_of`. `response.number` khớp request ngay trước (0 vi phạm trong 144 run). Concurrency = 1 (`TrackedPool` dừng nếu `max_parallel != 1`; `Guard.post` tăng `count` tuần tự) |
| Tool result gắn với hội thoại self_state | Có | 10191/10191 `tool_result` khớp tên và tham số với tool call của response ngay trước, cùng `span_id`. Trong request kế tiếp, tin nhắn `role=tool` mang `tool_call_id` (15316/15316) và nội dung bằng đúng chuỗi harness giao (bản cô đọng nếu `applied`; kiểm trọn vẹn trên một run). `tool_result_budget` ghép 1-1 với `tool_result` của `search_logs` (khớp `span_id` và tham số) |
| Dựng lại cây cha-con | Có | `trace-graph.json` là cây `{span_id, raw, children}`; 3888/3888 node có `raw.parent_span` bằng cha trong cây. Prompt consolidate ghi "Downstream evidences from N child span(s)": N khớp số con trong cây ở 3642/3642 request, và danh sách downstream bằng đúng output consolidate của các con (3642/3642) |
| Self-evidence có đi nguyên văn vào consolidation | Có | 3642/3642: khối "Your own self-evidence" bằng đúng output `agent_complete` self_state của span |
| Thứ tự consolidation | Từ lá lên gốc theo độ sâu | 144/144 run có thứ tự giảm dần độ sâu |
| Retry | Join được qua `retry_of`/`attempt` | 66 sự kiện `malformed_tool_call_retry` (33 mỗi corpus); request thử lại dùng seed dẫn xuất `retry_seed` |

Lưu ý: tool result không có khoá riêng tới `tool_call_id`; liên kết dựa trên thứ tự và khớp (tên, tham số). Điều này đủ vì chạy tuần tự, nhưng sẽ vỡ nếu sau này bật concurrency.

Cấu trúc kiểm soát bằng chứng của tác giả cần nhớ khi đo từng giai đoạn: (a) bằng chứng mỗi span đi tới tổng hợp cuối theo HAI đường độc lập: qua chuỗi consolidation (chỉ "root-level report") và trực tiếp qua toàn bộ Global Evidence Graph (`GlobalEvidenceGraph.summary()` đưa mọi self-evidence nguyên văn vào prompt cuối, `coordinator.py` 80-104, 485-503); (b) hint "ERROR LOGS" và "metric anomalies only" xây bằng so khớp chuỗi con trên self-evidence, gán theo `cmdb_id` của span chứ không theo dịch vụ mà văn bản nói tới.

## 4. Yêu cầu 3: ground truth

Định dạng `groundtruth.csv`: `timestamp,level,cmdb_id,failure_type`, đúng một dòng, `level=service`, `cmdb_id` là tên dịch vụ thuần (không phải pod), CRLF.

Ánh xạ sang tên dịch vụ trong span: `cmdb_id` của span trong `trace-graph.json` cũng là tên dịch vụ thuần (`frontendservice`, `checkoutservice`, ...), nên `_k8s_service_base` của `evaluate.py` 57-73 là no-op và khớp là so sánh bằng. Không có tên pod hay hậu tố số trong 8 case. Tên metric `service_name` khác tên span ở một chỗ: frontend là `frontend` và `frontend-external` (không có `frontendservice`).

| Package | Case | GT | Span GT trong trace | Độ sâu span GT | Tổng span | Dịch vụ trong trace (số span) | Lệch giờ trace so với GT (giây) |
|---|---|---|---|---|---|---|---|
| A | 30e3c7 | emailservice (delay) | 0 | | 23 | frontend 12, productcatalog 7, currency 2, recommendation 2 | 286,8 |
| A | 5f7a77 | checkoutservice (mem) | 13 | 2, 3x12 | 39 | frontend 9, checkout 13, productcatalog 12, payment 1, email 1, recommendation 2, currency 1 | 42,2 |
| A | 99f095 | currencyservice (loss) | 10 | 2 | 25 | frontend 14, currency 10, productcatalog 1 | 294,0 |
| A | de6a50 | checkoutservice (cpu) | 0 | | 25 | frontend 14, currency 10, productcatalog 1 | 80,6 |
| B | 272a47 | recommendationservice (cpu) | 0 | | 25 | frontend 14, currency 10, productcatalog 1 | 129,9 |
| B | 29583d | emailservice (delay) | 1 | 4 | 31 | frontend 9, checkout 9, productcatalog 8, payment 1, email 1, recommendation 2, currency 1 | 192,9 |
| B | 7bbfa6 | recommendationservice (socket) | 2 | 2, 3 | 23 | frontend 12, productcatalog 7, currency 2, recommendation 2 | 61,0 |
| B | ad1c27 | currencyservice (disk) | 10 | 2 | 25 | frontend 14, currency 10, productcatalog 1 | 37,6 |

Kết luận: GT xuất hiện trong trace được duyệt ở 5/8 case (A 5f7a77, A 99f095, B 29583d, B 7bbfa6, B ad1c27), vắng ở 3/8. Case có GT trong trace nhưng chỉ 1-2 span (B 29583d: một span `SendOrderConfirmation` dài 402 micro-giây, ở độ sâu 4; B 7bbfa6: hai span) là trường hợp bằng chứng thưa; case 10-13 span (A 5f7a77, A 99f095, B ad1c27) là trường hợp bằng chứng dày. Hai case A de6a50 và B 272a47 có hình trace gần như trùng với A 99f095 và B ad1c27 (frontend + currency + 1 productcatalog), nên GT không thể suy ra từ cấu trúc trace. Lệch giờ 37-294 giây giữa timestamp GT và span gốc nằm trong cửa sổ metric (±1200 s) nhưng có thể nằm ngoài cửa sổ log (±60 s quanh span), điều này không quan trọng ở đây vì log rỗng bằng chứng (mục 5.2).

## 5. Yêu cầu 5 trước, vì nó chi phối: đối chứng ở điều kiện `metric`

Đặt ở đây vì kết quả định hình cách đọc yêu cầu 4.

### 5.1 Chuỗi bốn giai đoạn quan sát được (S1 v2, run hoàn tất, theo điều kiện)

"GT trong trace" = 5 case. Số liệu theo run (n) hoặc theo span.

| Điều kiện | n | Run có bảng metric của GT | Span GT abnormal / tổng span GT | Run có nhãn nguyên nhân consolidation tại bất kỳ tổ tiên nào = GT | `local_root_cause` cấp root = GT | GT nằm trong hint "metric anomalies only" | R@1 | R@3 |
|---|---|---|---|---|---|---|---|---|
| metric | 14 | 14 | 92/98 | 5 | 3 | 14 | 10 | 14 |
| metric_no_log | 15 | 15 | 102/108 | 6 | 3 | 15 | 8 | 15 |
| no_metric | 15 | 0 | 0/108 | 7 | 0 | 0 | 5 | 9 |

Với `metric`, nhãn `local_root_cause` cấp root của 14 run phân loại: 3 GT, 7 dịch vụ khác, 4 `none`/`unknown`/`null`. "GT nằm trong hint" cần đọc thận trọng vì hint liệt kê mọi dịch vụ có span abnormal và gần như luôn có `frontendservice`.

Với "GT vắng trong trace" (3 case, 9 run mỗi điều kiện có dữ liệu): không có span GT, nên các giai đoạn 2-4 không đo được theo định nghĩa; R@1 = 0/9 (metric), 2/9 (metric_no_log, cả hai thành công đều ở A de6a50 khi model tự gọi `checkoutservice` và nhận bảng), 0/8 (no_metric).

Theo case (R@1 hoàn tất / số run, root `local_root_cause` = GT):

| Case | metric | metric_no_log | no_metric |
|---|---|---|---|
| A 5f7a77 (checkout, 13 span) | 3/3, 1 | 3/3, 1 | 1/3, 0 |
| A 99f095 (currency, 10 span) | 2/3, 0 | 0/3, 0 | 1/3, 0 |
| B 29583d (email, 1 span) | 0/3, 0 | 0/3, 0 | 0/3, 0 |
| B 7bbfa6 (recommendation, 2 span) | 3/3, 0 | 3/3, 0 | 0/3, 0 |
| B ad1c27 (currency, 10 span) | 2/2, 2 | 2/3, 2 | 3/3, 0 |

B ad1c27 `no_metric` đạt 3/3 mà không có bất kỳ bằng chứng metric, vì currencyservice chiếm 10/25 span; đây là baseline "chỉ cấu trúc trace" cần trừ ra khi đánh giá mức giảm do mất metric.

### 5.2 Oracle nguồn: có bằng chứng không, độc lập với việc agent có hỏi

Chạy `metric-repair.py` (công cụ metric thực của harness) trên dữ liệu input từng case, hỏi từng dịch vụ tại giây của span gốc:

- GT luôn trả bảng KPI của chính nó, 8/8: ví dụ A 5f7a77 `checkoutservice.cpu 0,41 sang 10,09; latency-90 0,24 sang 1,24; mem 1,14e7 sang 1,29e8`; B ad1c27 `currencyservice.mem 4,4e7 sang 1,5e8`; A de6a50 `checkoutservice.cpu 0,44 sang 10,52`; B 29583d `emailservice.latency-90 0,0 sang 0,14`.
- Ít dương tính giả: mọi dịch vụ khác trả NO_KPI, trừ A 99f095 (checkoutservice latency-90, recommendationservice latency-90) và B ad1c27 (emailservice latency-50 0,0 sang 0,0, hiển nhiên là nhiễu).
- `frontendservice` luôn NO_ROWS (tên metric là `frontend`).
- Nguồn log: trong cửa sổ ±60 giây quanh span gốc có 1002-1767 dòng/case, toàn bộ `severity: unknown`, `cmdb_id` chỉ `cartservice` (913-1606), `frontend` (84-170), `redis` (0-5). Không có log của GT ở case nào. Trên toàn cửa sổ đóng gói, 100% dòng đều `unknown`.

Hệ quả: với metric, điều kiện cần (nguồn có bằng chứng) thoả ở 8/8; việc agent không tới được bằng chứng ở 3 case GT vắng và ở các run `no_metric` là do chọn truy vấn và do điều kiện bị tắt, không do nguồn. Với log thì đối chứng cho thấy kênh này rỗng bằng chứng về GT, vì vậy RQ (a) phần "bỏ logs không giảm" được giải thích ở mức nguồn, chưa cần tới cơ chế của model.

### 5.3 Self-state: tool result có chuyển thành `is_abnormal` không (S1 v2, tất cả span có self-state)

| Điều kiện | Có bảng metric trong hội thoại span | `is_abnormal` | `has_metric_anomaly` | Số span |
|---|---|---|---|---|
| metric | có | true | true | 149 |
| metric | có | false | false | 1 |
| metric | không | true | false | 19 |
| metric | không | false | false | 457 |
| metric_no_log | có | true | true | 175 |
| metric_no_log | có | false | false | 2 |
| metric_no_log | không | true | false | 38 |
| metric_no_log | không | false | false | 433 |
| no_metric | không | true | false | 9 |
| no_metric | không | false | false | 618 |

Khi có bảng, 324/327 span (99%) tự đánh abnormal với `has_metric_anomaly=true`; khi không có bảng, 66/1574 span (4%) vẫn abnormal (chỉ từ độ trễ, nhãn `has_metric_anomaly=false`). Giai đoạn tool sang self-state ở mức span dường như bảo toàn tốt; mất mát không nằm ở đây. Nhưng 19+38 span abnormal không bảng chính là nguồn của danh sách "metric anomalies only" sai nhãn (hint dán nhãn mọi `is_abnormal` còn lại là "metric anomalies only").

Tuyên bố `has_error_logs=true` (14 span trong S1 v2, đều là span `frontendservice`) là bịa: mười trong mười bốn nằm ở `metric_no_log` nơi log hoàn toàn vắng; văn bản như "Error logs in adservice indicate failure during ad retrieval" tham chiếu một dịch vụ khác với dịch vụ của span, trong khi toàn bộ log trong corpus chỉ thuộc cartservice/frontend/redis với severity unknown. Hint dán nhãn "ERROR LOGS" theo `cmdb_id` của span, nên hint nói "frontendservice" trong khi lời tuyên bố nhắm tới adservice hay checkoutservice.

Ngoài ra model gọi `search_fluctuating_metrics` cho dịch vụ không phải dịch vụ của span ở 300/689 lượt (`metric`) và 492/956 lượt (`no_metric`); tức là một tỉ lệ lớn truy vấn không nằm trên đường của span. Bằng chứng GT vì thế có thể tới từ span của dịch vụ khác (và ngược lại).

## 6. Yêu cầu 4: rẽ nhánh `metric` so với `no_metric`, và tính xác định

### 6.1 Điểm rẽ nhánh đầu tiên (24 cặp S1 v2: cùng case, cùng seed)

Luồng sự kiện đã chuẩn hoá: bỏ `tool_call_id` và các id ngẫu nhiên của chat.completion, so request (messages), response (content và tool_calls) và tool_result.

| Cách so | Kết quả |
|---|---|
| Thô | 24/24 cặp rẽ nhánh tại một `tool_result` ở vị trí 7-12: câu trả lời metric đầu tiên khác chữ (NO_KPI/NO_ROWS hoặc bảng/NO_ROWS) |
| Gộp NO_KPI và NO_ROWS thành một dấu "rỗng" | 21/24 cặp rẽ nhánh ở response của model (vị trí 9 đến 28, trung vị 15, min 9, max 28) dù mọi metric vẫn rỗng cho model; 3/24 cặp (A 5f7a77 s28, B ad1c27 s27 và s28) rẽ nhánh ở một bảng metric thật ở vị trí 12-18 |
| So với lúc bảng thật đầu tiên xuất hiện | 9 run (A 30e3c7, A de6a50, B 272a47, mỗi run 3 seed) không có bảng nào trong cả luồng `metric`, vẫn rẽ nhánh; trong 15 run còn lại, rẽ nhánh xảy ra trước bảng thật đầu tiên ở 12 run, đúng lúc ở 3 run, sau ở 0 |
| `metric` so với `metric_no_log` | 24/24 cặp rẽ nhánh tại `tool_result` (log vắng thay cho log thật) |

Tức là tín hiệu của câu chữ ("No fluctuating metrics found" so với "No matching records found") đủ làm model lấy mẫu khác ngay ở lượt đầu. Sức ảnh hưởng đo được lên quá trình: ở các span không có bảng, số request self_state/span là 2,00 với NO_KPI (`metric` 419 span, `metric_no_log` 421 span), 3,84-4,00 khi trộn NO_KPI và NO_ROWS (50 span mỗi điều kiện) và 3,35 với NO_ROWS của `no_metric` (627 span). Loại trừ frontend để tránh nhiễu nhóm: `no_metric` 3,61 (frontend) và 3,14 (khác) so với `metric` 2,44 và 2,03.

Điều đó có nghĩa là `no_metric` mô phỏng đúng "nguồn thiếu" mà model không biết nguồn thiếu (theo thiết kế tài liệu trong `impl-261028-1228-rclagent-missing-source-conditions.md`), nhưng cũng làm model thử lại nhiều hơn. Đây là quan trắc chứ chưa phải lỗi: harness cố tình dùng đúng byte của tác giả cho "không có dòng nào", còn điều kiện `metric` dùng câu NO_KPI của bản metric sửa (một deviation đã ghi: `kaggle/metric-repair.py` và `NO_KPI`).

### 6.2 Tính xác định

- Cấu hình lấy mẫu có trong payload gửi vLLM (không có trong `llm.py`/`config.py` của tác giả, vốn không đặt sampling): `adapt_payload` (`smoke-worker.py` 108-120) đặt `temperature=0.7, top_p=0.8, top_k=20, min_p=0.0, seed=<seed run>, max_tokens=512 (1024 cho print_results), chat_template_kwargs.enable_thinking=false`; kiểm trên toàn bộ request: r2 6352 request, S1 v2 6855 request, chỉ có hai biến thể là seed bằng seed run (6.319 và 6.822) hoặc seed dẫn xuất khi retry (33 mỗi corpus). vLLM chạy `--generation-config vllm` (`kaggle-runtime.py` dòng 667). Mọi request trong một run dùng CÙNG một seed.
- Thực nghiệm: so r2 với S1 v2 cùng case, cùng điều kiện, cùng seed (hai lần chạy Kaggle độc lập): 62 cặp mà cả hai hoàn tất: 42 cặp giống hệt toàn bộ luồng, 20 cặp giống hệt từng byte tới trước request cuối và chỉ lệch ở request cuối (thứ tự dịch vụ trong hint, hash seed ngẫu nhiên; `check-hash-seed-order.py` đã xử lý). Không có cặp nào lệch trong giai đoạn self_state hoặc consolidate.
- Hệ quả cho phân tích: giai đoạn 1-3 là hàm xác định của prompt; round 2 và S1 v2 là bản sao đối với `metric`/`metric_no_log` (r2 và S1 v2 chỉ khác nhau ở 10 run vượt ngân sách của r2 và ở thứ tự hint). Đồng thời không thể "đổi một yếu tố, giữ mọi thứ khác" bằng phát lại: mọi thay đổi prompt cho một đường lấy mẫu mới.

## 7. Hệ quả: đo gì khả thi, đo gì không

| Phép đo | Khả thi trên corpus | Giới hạn |
|---|---|---|
| G0a. Nguồn có bằng chứng GT không | Có (oracle CPU, đã làm ở 5.2, 8/8 metric, 0/8 log) | Chỉ tại giây span gốc; chưa quét theo từng span |
| G0b. GT có trong trace được duyệt | Có (5/8) | |
| G0c. Agent có truy vấn GT không | Có, từ `tool_result.params` | 3 case GT vắng gần như không bao giờ truy vấn |
| G1. Tool result sang self-state (span GT abnormal khi nhận bảng) | Có | 94% (92/98) ở `metric`; sai nhãn có sẵn: 19+38 span abnormal không bảng, 14 tuyên bố `has_error_logs` bịa |
| G2. Self-state sang consolidation (nhãn nguyên nhân giữ GT dọc đường lên) | Có (cây dựng lại được) | Chỉ 5 case có span GT; nhãn `none`, `unknown`, `null` là lớp phổ biến, nên cần phân loại 4 lớp (GT, dịch vụ khác, từ chối, chính nó) |
| G3. Consolidation sang tổng hợp cuối (root report so với GEG so với hint, rồi rank) | Có | Tổng hợp thấy cả root report lẫn toàn bộ GEG, nên "bỏ qua" không đồng nghĩa với mất; cần phân biệt hai đường |
| So sánh `metric` với `no_metric` theo từng lượt | Có nhưng bị nhiễu câu chữ (mục 6.1) | Không tách được hiệu ứng thiếu bằng chứng khỏi hiệu ứng NO_ROWS so với NO_KPI nếu không chạy thêm |
| Can thiệp phản thực tế (thay đổi đầu ra một giai đoạn, giữ phần còn lại) | Không bằng phát lại log | Lấy mẫu chaotic; cần chạy lại model (GPU hoặc CPU rất chậm) |
| Bằng chứng log theo giai đoạn | Không có ý nghĩa | Log không chứa tín hiệu GT, `severity` luôn `unknown` |

Số case đủ cho phân tích giai đoạn đầy đủ là 5, trong đó 3 case dày (10-13 span GT) và 2 case thưa (1-2 span GT). Mọi tỉ lệ ở trên là mô tả, không có kiểm định.

### 7.1 Quan trắc sơ bộ về nơi mất (cần kiểm định ở bước phân tích, chưa phải kết luận)

Trên chuỗi `metric` (5 case, 14 run): tool 14/14 sang self-state 94% sang consolidation root 21% (3/14) sang rank 1 là 71% (10/14). Phần phục hồi từ 21% lên 71% chỉ có thể đến từ đường trực tiếp GEG và hint. Các run trượt R@1 trong `metric`/`metric_no_log` có GT trong trace (11/29) đồng thời mang tuyên bố `has_error_logs` bịa, 18/18 run đúng thì không. Ứng viên giai đoạn mục tiêu cho X: (i) sửa hoặc kiểm chứng nhãn `has_error_logs` ở self-state và cách dán nhãn hint (không thuộc nhóm "mất" mà thuộc nhóm "gán sai"); (ii) giảm vai trò của chuỗi consolidation hoặc đưa metric anomaly vào luật của consolidation (hiện luật chỉ nêu ERROR LOGS, `coordinator.py` 296-332); (iii) với 3 case GT vắng, chọn truy vấn (đưa danh sách dịch vụ đã biết vào tìm kiếm metric). Ba hướng này chỉ là ứng viên, cần phép đo G1-G3 ở bước sau.

## 8. Bất thường và câu hỏi mở

Bất thường đã gặp:

1. Hai run luôn dừng vì lỗi định dạng của model (B 272a47 `no_metric` s26, B ad1c27 `metric` s27) ở cả hai corpus; thiếu 2 run làm mất cân bằng một ô (11/12) nhưng không đổi kết luận.
2. 8 NO_ROWS của `productcatalogservice` trong `metric` và `metric_no_log` chưa được giải thích: oracle ở giây gốc cho NO_KPI cho dịch vụ này ở cả 8 case. Có thể do timestamp do model tự đặt khác span (model truyền chuỗi timestamp tuỳ ý, `validate_query` chỉ kiểm tra cửa sổ đóng gói). Cần tra `tool_result.params.timestamp` của 8 lượt này.
3. Hint dùng `cmdb_id` của span, không phải dịch vụ mà văn bản tự đánh giá nói tới; vì vậy mọi nhãn "ERROR LOGS: frontendservice" đều thuộc loại gán sai tác giả (ở mã tác giả, không do harness).
4. `has_metric_anomaly=true` luôn đi kèm bảng metric trong hội thoại (324/327 có bảng, 0 span không bảng có `has_metric_anomaly=true`); tức self-state không bịa tín hiệu metric, nhưng bịa tín hiệu log (14 span).
5. Dòng dữ liệu cũ: số "39/39 header-only" trong mô tả task cho một run `no_metric` thực ra là câu NO_ROWS (`{"message":"No matching records found."}`), không phải CSV có header; log rỗng mới là header-only.
6. S1 v3 (hash seed cố định) chưa có; mọi so sánh thứ tự hint ở đây dùng r2 và S1 v2 ngẫu nhiên.

Câu hỏi mở cho bước kế:

1. Hiệu ứng câu chữ NO_ROWS so với NO_KPI có thể tách bằng một lần chạy `no_metric` với câu NO_KPI (tức "nguồn có nhưng không dị thường")? Cần quyết định có chạy lại hay chỉ ghi nhận hạn chế (không chạy được trong phạm vi CPU-only hiện tại).
2. Có nên định nghĩa "mất" ở giai đoạn consolidation theo nhãn nguyên nhân (`local_root_cause`), theo confidence, hay theo việc GT còn xuất hiện trong văn bản `reason`? Nhãn hiện cho 21% ở root; văn bản có thể cao hơn.
3. Với 3 case GT vắng trong trace, báo cáo giai đoạn cho nhóm này như thế nào: tính là mất ở giai đoạn 0 (chọn truy vấn) hay loại khỏi mẫu? Quyết định ảnh hưởng mẫu 8 sang 5.
4. Tuyên bố `has_error_logs` bịa có phụ thuộc case (A 99f095 liên quan span `GetAds`, B 29583d liên quan span `PlaceOrder`) hay phụ thuộc điều kiện? Chỉ có 3 case mang nó nên chưa thể tách.

## 9. Tái lập

Các script phân tích viết trong thư mục tạm (không đưa vào repo): `C:\Users\Siinn\AppData\Local\Temp\claude\C--Users-Siinn--claude-spares-spare-JUfm50\8ac89638-bf0c-4a31-b930-7d87d9e0f888\scratchpad\` gồm `load.py` (đọc 4 zip sang `corpus.pkl`), `a1.py` (đếm theo run), `a2.py` (kiểm join và cây), `a3.py` (GT), `a4.py` đến `a6.py` và `a12.py` (rẽ nhánh và tính xác định), `a7.py`, `a9.py`, `a13.py` (chuỗi giai đoạn), `a10.py` (log và ngân sách), `a11.py` (retry, thất bại, loại nhãn consolidation, `has_error_logs`), `oracle.py` (chạy bằng `kaggle/runtime/harness-env/Scripts/python.exe`). Nếu muốn giữ lại để chạy lại, cần đưa vào `kaggle/` dưới dạng một script `analyze-evidence-loss-*.py` có kiểm thử, theo mẫu `analyze-missing-source-results.py`.
