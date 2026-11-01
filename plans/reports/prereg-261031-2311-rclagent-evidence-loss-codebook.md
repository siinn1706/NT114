# Codebook đăng ký trước v1: đo nơi mất bằng chứng theo giai đoạn của RCLAgent khi thiếu telemetry (RQ b)

- Phiên bản: v1, đã hiệu chỉnh trên hai run (mục 13.3) và đóng băng cục bộ ngày 2026-11-01. v0 là bản nháp cùng ngày, trước hiệu chỉnh. **Đóng băng cục bộ, không có thứ tự thời gian độc lập**: sếp chưa quyết định có commit đóng băng hay không (câu hỏi mở 7 của kế hoạch), nên hash trong `K/evidence-loss-prereg.json` là bằng chứng thứ tự duy nhất; sếp có thể tự lưu hash ở nơi có dấu thời gian ngoài repo.
- Trạng thái đóng băng: chỉ có hiệu lực khi hash của file này (và của analyzer cùng các module nó nạp) nằm trong `K/evidence-loss-prereg.json`. Quy tắc băm: đọc file dạng byte, đổi mọi `\r\n` thành `\n`, UTF-8, SHA256. File này phải dùng LF.
- Kế hoạch gốc: `plans/261031-2311-rclagent-evidence-loss-analysis/plan.md`.
- Ký hiệu: `K/` là `F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`. `UP/` là `K/runtime/kaggle-dataset-check-a-s1-v3/upstream/` (md5 `coordinator.py`, `evaluate.py` giống nhau ở mọi gói dùng trong kế hoạch).
- Nhãn nguồn của mỗi con số: `[đo-cấu-trúc]` là số đếm cấu trúc (không phải nhãn theo run) người viết đo lại trên bốn zip khi soạn codebook; `[scout]` là số của báo cáo scout dữ liệu hoặc scout code; `[reviewer]` là số do reviewer tính, chưa tính lại bằng analyzer. Mọi số `[scout]` và `[reviewer]` còn là chưa xác minh cho tới khi analyzer tính lại.

## 0. Phạm vi và ràng buộc

Câu hỏi (b), sếp chốt 2026-10-28: khi thiếu một nguồn telemetry, bằng chứng mất ở giai đoạn nào của RCLAgent. Codebook này định nghĩa cách đo bằng luật tất định trên `events.jsonl` đã có, trên CPU.

Không làm trong kế hoạch này:
- không chạy lại model (kể cả CPU lượng tử hóa), không thử can thiệp X, không đo hiệu quả của X (RQ c);
- không tuyên bố nhân quả cho hành vi của LLM; chỉ phần mã tất định của tác giả (cách dựng hint) mới replay được;
- không dùng LLM-judge làm nhãn chính, không p-value suy diễn;
- không đọc hay dùng test split RE2-OB (đã niêm phong); không sửa `upstream/`.

Ngôn ngữ bắt buộc cho báo cáo: mô tả, "nhất quán với", "có mặt ở đầu vào cuối". Cấm các chữ `used`, `evidence_used`, `evidence_unused`, `decisive`, "gây ra" khi nói về hành vi của LLM. Tên nhãn kết cục và nhãn phần dư chỉ mô tả quan hệ giữa các chỉ báo, không gán ý định hay quá trình cho mô hình. Tên nhãn là "first-loss stage" (chưa có replay phản thực nên không gọi là "decisive step").

Đơn vị phân tích: **dịch vụ GT** (4 đơn vị); case (8) và seed (3 mỗi case) lồng bên trong; span lồng trong run. Không xem hàng nghìn span hay 72 run là mẫu độc lập (mô hình xác định theo prompt và seed; vòng 2 và S1 v2 là bản sao tất định của nhau).

## 1. Dữ liệu và hình dạng đã kiểm trên zip thật

### 1.1 Corpus

| Corpus | Gói | Zip (tính từ `K/runtime/`) | Manifest | Vai trò |
|---|---|---|---|---|
| S1 v2 | A | `kaggle-output-a-s1-v2/rclagent-smoke/rclagent-smoke-results.zip` | `K/s1-v2/a/manifest.json` | Chính (36 run, 70 hoàn tất trên A và B) |
| S1 v2 | B | `kaggle-output-b-s1-v2/rclagent-smoke/rclagent-smoke-results.zip` | `K/s1-v2/b/manifest.json` | Chính |
| Vòng 2 | A, B | `kaggle-output-{a,b}-r2-v1/rclagent-smoke/rclagent-smoke-results.zip` | manifest vòng 2 | Bản sao, chỉ kiểm tính tất định; 62 hoàn tất, 10 dừng |
| S1 v3 | A, B | chưa có output | | Không dùng để chỉnh luật; chỉ chạy bộ nhãn đã đóng băng khi output về |

Run: `run_id = <trace_id>--<condition>--s<seed>`, điều kiện `metric`, `metric_no_log`, `no_metric`, seed 20261026 đến 20261028. Mã case rút gọn là 6 ký tự đầu của `trace_id`.

### 1.2 Trường nguồn (đã kiểm ngày 2026-11-01 trên S1 v2 A và B)

Chỉ đọc sự kiện từ `run/traces/<run_id>/events.jsonl`. Mỗi gói còn một `run/protocol/events.jsonl` (sự kiện `request` với `phase: "protocol"`, `protocol_pass`); loại nó **theo đường dẫn**, không lọc bằng `phase`, vì chỉ sự kiện `request` mang khóa `phase`.

| Nơi | Trường | Ghi chú đã kiểm |
|---|---|---|
| Mọi dòng `events.jsonl` | `kind` (không phải `event` hay `type`), `time` | Giá trị `kind` ở trace: `request`, `response`, `tool_result`, `tool_result_budget`, `agent_complete`, `malformed_tool_call_retry`, `fatal`, `worker_error` |
| `request` | `number`, `phase`, `span_id`, `operation`, `attempt`, `retry_of`, `prompt_tokens_local`, `payload`, `adaptation` | `operation` là `self_state_verification`, `consolidate` hoặc `null` (tổng hợp cuối, `span_id` cũng `null`). `attempt` **bắt đầu từ 0**: 6822 request trace có `attempt == 0` (4858 self-state, 1894 consolidate, 70 cuối) và retry có `attempt` 1, 2, 3 là 31, 1, 1 [đo-cấu-trúc]. `payload.messages[]` có `role` `system`, `user`, `assistant`, `tool`; `payload.seed` là seed của run hoặc seed dẫn xuất khi retry |
| `response` | `number`, `status`, `elapsed_seconds`, `body` | `body` là chuỗi JSON (`json.loads`); tool call ở `choices[0].message.tool_calls[].function.{name,arguments}` |
| `tool_result` | `name`, `params`, `response`, `source`, `span_id` | `params` là **dict** `{service_name, timestamp}` ở 5283 trên 5283 sự kiện (5281 trace cộng 2 protocol); `timestamp` là chuỗi 13 chữ số mili giây. `response` là chuỗi. `source` nhận `author` (2107, toàn `search_logs`), `repaired` (1448, toàn metric), `absent` (1726 = 769 log cộng 957 metric) [đo-cấu-trúc]. Chuỗi biểu diễn của `params` chỉ là đường lùi (`ast.literal_eval`) |
| `tool_result_budget` | `name`, `params`, `delivered`, `span_id`, `budget_tokens`, `original_bytes`, `original_sha256`, `applied`, (khi nén) `original_tokens`, `notice`, `condensed_tokens`, `condensed_sha256` | **Chỉ có cho `search_logs`**: 2876 trên 2876 kết quả log; 0 trên 2405 kết quả metric [đo-cấu-trúc]. `delivered` là `null` khi `applied` sai (2654) và là chuỗi đã nén khi `applied` đúng (222). Vì vậy văn bản log mô hình thấy là `delivered` nếu `applied`, ngược lại là `tool_result.response`. Văn bản metric mô hình thấy luôn là `tool_result.response` |
| `agent_complete` | `operation`, `span_id`, `output` | `output` là chuỗi JSON. `operation` luôn là `self_state_verification` hoặc `consolidate` (chưa thấy `null`). Đầu ra cuối chỉ nằm ở `result.json` và `response.body` của request cuối |
| `malformed_tool_call_retry` | `number`, `next_attempt`, `next_seed`, `reason` | |
| `fatal` | `reason` | Lý do dừng cứng của harness |
| `run/traces/<run_id>/result.json` | `root_causes` (danh sách chuỗi, 10 phần tử trở lên) | Run dừng không có file này |
| `run/traces/<run_id>/trace-graph.json` | cây `{span_id, raw, children}` | `raw.cmdb_id`, `raw.parent_span` (`null` ở root), `raw.timestamp` (mili giây), `raw.operation_name`, `raw.duration` |
| `run/traces/<run_id>/worker-status.json` | `status` (`passed` hoặc `failed`), `phase`, `seed`, `sources`, `model_requests_including_retries`, `token_usage`, `error` (dạng repr `HarnessStop('...')`), `fatal` (chuỗi lý do) | |
| `run/progress.json` | `bundle_sha256`, `traces{run_id: {case, attempts, status, reason}}` | `reason` chỉ có khi `failed`, dạng `RuntimeError('trace failed: ...')` |
| `run/scoring/<run_id>/groundtruth.csv` | `timestamp,level,cmdb_id,failure_type`, đúng một dòng, CRLF | Run dừng không có thư mục `scoring/`; lấy GT từ run anh em cùng case |
| `run/scoring/<run_id>/author-score.txt` | Mở đầu bằng nhiễu `ModuleNotFoundError: No module named 'wrapt'` của sitecustomize, một dòng trống, dòng `Results  (...)`, rồi các dòng chỉ số có hai dấu cách, ví dụ `  R@1  : 0.0000  (0/1)` và `  MRR  : 0.1429` [đo 70 trên 70 file] | Phân tích bằng `^\s*R@1\s*:\s*([0-9.]+)\s*\((\d+)/(\d+)\)` và `^\s*MRR\s*:\s*([0-9.]+)`; MRR 4 chữ số thập phân |

Khóa KPI của bảng metric: mọi hàng ở S1 v2 có đúng hai đoạn `<dịch vụ>.<kpi>` (616 hàng; tiền tố đầu chỉ là bốn dịch vụ GT) [đo-cấu-trúc]. Bảng metric luôn bắt đầu bằng `key,`; metric rỗng là `{"message":"No matching records found."}` (NO_ROWS) hoặc `{"message":"No fluctuating metrics found."}` (NO_KPI). `search_logs` rỗng không phải `{message}` mà là bảng chỉ có dòng tiêu đề `log_id,timestamp,cmdb_id,log_name,value` (không quá một dòng).

### 1.3 Chỗ khác với giả thiết ban đầu, để analyzer không sai theo

1. Khóa loại sự kiện là `kind`.
2. `delivered` có mặt ở mọi `tool_result_budget` nhưng `null` khi không nén; đừng đọc `delivered` như "luôn là văn bản mô hình thấy".
3. `attempt == 0` là lượt đầu; retry là `attempt > 0`.
4. Không lọc `phase == "trace"` cho mọi loại sự kiện; loại protocol theo đường dẫn.
5. Không có `tool_result_budget` nào cho metric, nên "cắt bớt" không thể là nguyên nhân mất bảng metric; analyzer khẳng định điều này bằng kiểm cấu trúc.
6. Lý do dừng nằm ở ba nơi (`worker-status.json`, `progress.json`, sự kiện `fatal`); lấy nơi đầu tiên có giá trị theo thứ tự `worker-status.fatal`, `worker-status.error`, `progress.reason`, `fatal.reason`.

### 1.4 Join

Harness ép một luồng (`max_parallel = 1`), nên sự kiện tuần tự.
- `response.number` khớp request liền trước cùng `number`.
- Một response có thể mang nhiều tool call (phần lớn `tool_result` đi sau response như vậy). Ghép `tool_result` với tool call là ghép **đa tập** theo (tên, params, `span_id`), không theo vị trí "lời gọi liền trước".
- `tool_result.span_id` cho biết span nhận kết quả. Mọi `tool_result` phải khớp đúng một tool call; vi phạm là integrity problem.
- Cây: dựng từ `raw.parent_span`; mọi nút phải khớp cha. Root là nút có `parent_span == null`.
- Thời gian: `metric_query_ts_offset_s = (params.timestamp - raw.timestamp) / 1000` (đều mili giây), đơn vị giây ghi trong tên cột. Chỉ tính cho truy vấn metric đầu tiên của span (theo thứ tự log); truy vấn sau không đổi cột này, kể cả khi truy vấn đầu mang mốc thời gian sai.

## 2. Thực thể dùng chung

### 2.1 Tên dịch vụ: đúng `_label_hit` và `_k8s_service_base` của scorer

Sao chép hành vi nguyên văn từ `UP/evaluate.py` 57 đến 103. Hạng là 0-based, `-1` là không trúng.
- `match(a, b)` là `_label_hit(a, [b]) == 0`.
- `in_list(a, L)` là `_label_hit(a, L) >= 0`, `rank_of(a, L)` là `_label_hit(a, L)`.
- Chuẩn hóa tên chỉ bằng `lower()`; không gộp pod về service trước khi so (để nhãn nhất quán với R@1).

Bảng kỳ vọng của test tên dịch vụ (đã chạy trên bản `_label_hit` thật ngày 2026-11-01):

| label | ứng viên | hạng |
|---|---|---|
| `cartservice` | `[cartservice-0]` | 0 (khớp) |
| `cartservice-0` | `[cartservice]` | 0 (khớp) |
| `frontendservice` | `[frontend]` | -1 |
| `frontend` | `[frontendservice]` | -1 |
| `currencyservice` | `[currencyservice-2]` | 0 |
| `emailservice` | `[email]` | -1 |
| `emailservice` | `[emailservice2]` | -1 |
| `checkoutservice` | `[checkout-service]` | -1 |
| `checkoutservice` | `[adservice, checkoutservice]` | 1 |
| `checkoutservice` | `[checkoutservice-0, checkoutservice]` | 0 |
| `currencyservice` | `[adservice, paymentservice, currencyservice-1]` | 2 |
| `recommendationservice` | `[unknown, none, ""]` | -1 |

`cartservice` và `cartservice-0` khớp (cùng base K8s) nhưng là hai phần tử khác nhau trong `root_causes`, chiếm hai hạng.

### 2.2 GT, case, đơn vị

- `GT`: `cmdb_id` trong `groundtruth.csv` của case (mức service). Run dừng lấy GT từ run anh em cùng case.
- `gt_service`: chính `GT` (4 giá trị). Tám case train đã chạy (cấu trúc, đo từ `groundtruth.csv` và `trace-graph.json` [đo-cấu-trúc]):

| Gói | Case | GT | Loại lỗi | Span GT trong trace | Tổng span |
|---|---|---|---|---|---|
| A | 30e3c7 | emailservice | delay | 0 | 23 |
| A | 5f7a77 | checkoutservice | mem | 13 | 39 |
| A | 99f095 | currencyservice | loss | 10 | 25 |
| A | de6a50 | checkoutservice | cpu | 0 | 25 |
| B | 272a47 | recommendationservice | cpu | 0 | 25 |
| B | 29583d | emailservice | delay | 1 | 31 |
| B | 7bbfa6 | recommendationservice | socket | 2 | 23 |
| B | ad1c27 | currencyservice | disk | 10 | 25 |

- Đơn vị đếm của luật là dịch vụ GT: `checkoutservice` (5f7a77, de6a50), `emailservice` (30e3c7, 29583d), `currencyservice` (99f095, ad1c27), `recommendationservice` (272a47, 7bbfa6). Mỗi dịch vụ xuất hiện hai lần với loại lỗi khác nhau, nên không xem 8 case là 8 đơn vị.
- `gt_span_in_trace`: số span có `raw.cmdb_id` khớp GT theo `match`. Chỉ là cột chú thích, **không phải cổng loại trừ**: mô hình hỏi được metric của mọi dịch vụ trong danh sách "Known services" của system prompt, kể cả dịch vụ không có span trong trace.

### 2.3 Carrier và Ev

- `carrier span`: span có ít nhất một `tool_result` metric (`name == search_fluctuating_metrics`) mà `response` bắt đầu bằng `key,` và có khóa KPI của GT (cùng điều kiện `table_received` ở I0). Carrier không nhất thiết là span của GT (frontend có thể hỏi bảng của GT).
- `Ev` (run đủ điều kiện cho S1 đến S4): run hoàn tất (`worker-status.status == passed`, có `result.json` và `scoring/`) mà I0 đúng. Cổng vào S1 đến S4 là **I0 đúng**, không phải "có span GT trong trace". Khi I0 đúng thì I0 thắng mọi nhãn S0 khác.
- Tool metric là bản harness đã sửa (`source == repaired`, `K/metric-repair.py`, K = 100 độ lệch chuẩn) và bảng chỉ xuất hiện khi hỏi đúng dịch vụ GT. Vì vậy I0 gần như đồng nghĩa "mô hình đã hỏi GT": tool hoạt động như một oracle GT. Báo cáo ghi điều này và tách truy vấn GT khỏi truy vấn khác.

## 3. Nhãn harness và run bị cắt cụt

Lý do dừng (mục 1.3) so khớp theo chuỗi con, theo thứ tự, lấy nhãn đầu tiên khớp:

| Nhãn | Chuỗi con trong lý do dừng |
|---|---|
| `H_cap` | `Output stopped without completion` (đầu ra chạm trần token; đặt trước `H_parse` vì nằm trong thông điệp `Invalid structured response`), `Per-span tool round budget exceeded`, `Model request budget exhausted`, `RCLAgent deadline exceeded` |
| `H_context` | `Context overflow` |
| `H_query` | `Unexpected telemetry tool`, `Unsupported telemetry tool parameters`, `Telemetry timestamp is not parseable`, `outside the packaged time window` (truy vấn telemetry của mô hình bị harness từ chối) |
| `H_infra` | `Model server HTTP`, `Request/template incompatibility`, `Telemetry transport failure`, `Telemetry tool transport failure`, `Tool-result budget` (hạ tầng, không phải hành vi mô hình) |
| `H_parse` | `Invalid structured response`, `Invalid agent JSON output`, `Exactly one structured print_results call`, `Empty model output`, `Author client failed after bounded retries`, `No valid final result` |
| `H_other` | mọi lý do còn lại, kể cả thiếu `worker-status.json` hoặc lý do rỗng |

Run `worker-status.status == passed` có nhãn `none`.

**Quy tắc cắt cụt (right-censored)**: mọi chỉ báo **dương** tính được từ sự kiện đã ghi vẫn hợp lệ và được giữ (I0, I1, I3 đơn điệu: thêm span chỉ thêm bằng chứng; I2 dương cần consolidate của root nên chỉ có khi run đi tới đó). Mọi chỉ báo **âm** và mọi chỉ báo phía sau điểm dừng là `NA`. Riêng I0 âm của run cắt cụt là `NA_censored`, không phải `S0_not_queried`, vì "chưa hỏi GT" không suy ra được khi mới đi qua một phần span. Run cắt cụt không có `result.json` nên I4 và I5 là `NA`. Mẫu số của mọi bảng phễu ghi rõ số run bị loại. Báo thêm bảng độ nhạy "giả sử run cắt cụt hỏng ở chỉ báo tệ nhất", vì run bị cắt không chắc ngẫu nhiên (ví dụ `ad1c27 metric s27` thuộc case có 10 span GT và dừng vì đầu ra model sai định dạng).

Corpus chính S1 v2: 70 run hoàn tất, 2 dừng (cả hai `H_parse`) [đo-cấu-trúc]. Vòng 2: 62 hoàn tất, 10 dừng (5 `H_cap` vòng tool, 3 `H_cap` ngân sách request, 2 `H_parse`; phân loại này theo bản cũ của bảng nhãn, analyzer phân loại lại bằng bảng trên), nên 8 run chạm trần là dữ liệu bị cắt cụt, không phải mẫu hoàn tất.

Retry: `malformed_tool_call_retry` là yêu cầu lặp của cùng một lượt logic. Số request theo span chỉ tính `attempt == 0`; số retry ghi riêng. `first_request_divergence` so theo chuỗi request không-retry khi nói "không tính retry".

Nhánh chưa gặp trong dữ liệu (có chỗ sẵn, không được làm analyzer ném lỗi): nhánh fallback của self-state (mục 4, I1), `agent_complete.operation == null`, `source` ngoài ba giá trị, `kind` lạ, `params` kiểu chuỗi. Analyzer đếm các trường hợp này vào `unseen_branches` trong `summary.json` và báo, không đoán nhãn.

## 4. Chỉ báo I0 đến I5

Mỗi chỉ báo có giá trị `true`, `false`, `NA`, và riêng I0 thêm `NA_censored`. Mỗi chỉ báo được báo như một **biên riêng** theo run, case và điều kiện, không chỉ như nhãn tuần tự.

### I0: tín hiệu từ tool

- Trường nguồn: `tool_result.{name, params.service_name, response, source, span_id}`, tool metric là `search_fluctuating_metrics`.
- Ba cột độc lập: `queried_gt` (có `tool_result` metric với `match(GT, params.service_name)`), `table_received` (có `tool_result` metric có phản hồi bắt đầu bằng `key,` mà có ít nhất một khóa KPI với đoạn kề cuối khớp GT theo `match`, bất kể `service_name` được hỏi là gì; tool dùng `str.contains` dạng regex nên truy vấn không khớp tên theo scorer vẫn có thể trả bảng của GT), `gt_span_in_trace` (chú thích). **I0 = `table_received`.**
- Quy tắc ưu tiên: `source == absent` được kiểm trước mọi phân loại theo văn bản (phản hồi của nguồn đã gỡ giống từng byte `NO_ROWS`: 957 phản hồi `absent` so với 124 `NO_ROWS` thật [reviewer]). Run không có `tool_result` nào là `NA` kể cả khi bị cắt cụt (không có gì để kết luận); `NA_censored` chỉ dành cho run cắt cụt có ít nhất một `tool_result`. P1 đọc `empty_reason == absent_source` chứ không đọc I0, nên không bị `NA_censored` ảnh hưởng.
- Cột chẩn đoán: `table_key_prefixes` (tập đoạn đầu của khóa KPI trong các bảng nhận được) và `gt_kpi_in_table`; cột span `table_gt_kpi_from_nonmatching_query` đúng khi span nhận bảng có khóa của GT từ truy vấn mà `match(GT, params.service_name)` sai.
- I0 sai thì nhãn S0:
  - `S0_not_queried`: `queried_gt` sai (không `tool_result` metric nào có `service_name` khớp GT) và không có bảng chứa khóa GT. Tách tiếp theo hình dạng trace: `S0_gt_span_absent` (`gt_span_in_trace == 0`) và `S0_gt_span_present_not_queried` (`gt_span_in_trace >= 1`). Chỉ nhãn thứ hai là "không chọn hỏi GT dù GT có span"; nhãn thứ nhất lẫn hoàn toàn với hình dạng trace (cả ba case I0 sai đều không có span GT, và cả năm case có span GT đều I0 đúng [reviewer]).
  - `S0_empty_result`: có hỏi GT nhưng không có bảng chứa khóa của GT, kèm `empty_reason` cho từng lượt hỏi GT: `absent_source` (`source == absent`, kiểm trước), `no_kpi` (phản hồi sau `strip` bằng chuỗi NO_KPI), `no_rows` (bằng chuỗi NO_ROWS), `table_no_gt_kpi` (có bảng `key,` nhưng không có khóa của GT), `other`. Cột run `empty_reason` là giá trị duy nhất nếu mọi lượt giống nhau, ngược lại là `mixed`; tập đầy đủ ở `empty_reason_set`.
- `NA`: không có `tool_result` nào trong run (run dừng trước khi gọi tool). `NA_censored`: I0 âm của run cắt cụt có ít nhất một `tool_result`.
- Ví dụ (GT là `checkoutservice`):
  - đúng: `tool_result{name:"search_fluctuating_metrics", params:{service_name:"checkoutservice", timestamp:"1705738345756"}, response:"key,regular_mean,...\ncheckoutservice.cpu,0.41,...", source:"repaired", span_id:"a1"}`;
  - sai, `S0_empty_result` với `no_kpi`: cùng `params`, `response:"{\"message\":\"No fluctuating metrics found.\"}\n"`;
  - sai, `S0_not_queried`: mọi `tool_result` metric của run có `service_name` thuộc `{frontendservice, currencyservice}`.

### I1: self-state

- Trường nguồn: `agent_complete` (`operation == self_state_verification`, `span_id`, `output` parse JSON: `is_abnormal`, `has_error_logs`, `has_metric_anomaly`), `trace-graph.json` (`raw.cmdb_id` của carrier).
- Luật: I1 đúng khi tồn tại carrier mà self-state có `is_abnormal == true` (kiểu bool đúng). Ghi `carrier_count`, `carrier_abnormal_count`, `has_metric_anomaly` của từng carrier. I1 là "đã có carrier abnormal" nên gần bão hòa; báo kèm số carrier (không có tham số ngưỡng).
- Nhánh fallback: request cuối của hội thoại span (request `self_state_verification` có `attempt == 0` cuối cùng của `span_id`) có tin nhắn user cuối bắt đầu bằng `Based on all retrieved evidence above` thì self-state của span đó thiếu `has_error_logs` và `has_metric_anomaly`. Khi carrier dùng fallback và thiếu cờ thì gán `S1_not_flagged:fallback_flags_missing` chỉ khi không carrier nào có `is_abnormal == true`; nếu I1 đúng nhờ carrier khác thì I1 giữ đúng và nhánh fallback chỉ ghi vào `unseen_branches`. Nhánh này hiện 0 lần ở S1 v2 và vòng 2 [scout], nên chỉ có test tổng hợp.
- `S1_not_flagged`: I0 đúng mà mọi carrier tự đánh `is_abnormal == false`.
- I1 đúng mà I3 sai (carrier tự đánh abnormal nhưng GT không có trong hint, vì cờ gán theo `cmdb_id` của span carrier) là nhánh riêng, đã thấy ở `de6a50` `metric_no_log` s26 đến s28 [reviewer]; mục 5 gán nhãn riêng cho nhánh này.
- `misattributed`: I1 đúng chỉ nhờ carrier có `raw.cmdb_id` không khớp GT, tức là không carrier abnormal nào là span của GT (luật "tất cả đều không phải GT"; một carrier abnormal thuộc GT là đủ để `misattributed` sai).
- Ví dụ: đúng: carrier `a1` có `output` `{"span_id":"a1","service_name":"frontendservice","is_abnormal":true,"has_error_logs":false,"has_metric_anomaly":true,...}` (kèm `misattributed` vì `frontendservice` không khớp GT `checkoutservice`); sai: mọi carrier có `"is_abnormal": false`.
- `NA`: I0 sai hoặc `NA`/`NA_censored`; hoặc có carrier nhưng chưa carrier nào có self-state (run cắt cụt).

### I2: consolidation

- Trường nguồn: `agent_complete` (`operation == consolidate`, `span_id`, `output.local_root_cause`, `output.reason`), cây, `raw.parent_span`.
- Nhãn nút: lấy `local_root_cause` của consolidate của nút. Trước khi so, chuỗi nhãn được `strip()` rồi chuẩn hóa bằng bản sao của `_normalise_name` của tác giả (`UP/coordinator.py` 370; `result.json` đã qua hàm này còn `local_root_cause` thì không) để nhãn I2 và I5 cùng quy tắc với I4; nhãn thô và nhãn đã chuẩn hóa khác nhau được đếm vào `unseen_branches`, kèm biến thể `I2_raw` (không chuẩn hóa, chỉ `lower()`). Giá trị là `refusal` nếu không phải chuỗi, hoặc là chuỗi rỗng, hoặc sau `strip().lower()` thuộc `{none, unknown, null, n/a, na}`. JSON `null` thuộc `refusal` (35 trên 1894 consolidate ở S1 v2 có `local_root_cause` là JSON null [đo bằng kế hoạch, scout]; `.lower()` trên giá trị đó sẽ ném lỗi nếu không kiểm kiểu). Còn lại: `gt` nếu `match(GT, nhãn)`, ngược lại `other_service`.
- **I2 = nhãn của root là `gt`.** Root là nút `parent_span == null`.
- Ghi chuỗi: với mỗi carrier abnormal, đi từ carrier lên root theo `raw.parent_span`, ghi lớp nhãn từng nút; `chain_depth_kept` là số nút liên tiếp từ carrier trở lên có lớp `gt`; `break_class` là lớp của nút đầu tiên không phải `gt` trên đường (hoặc `none` nếu tới root vẫn `gt`); `carrier_count`. `chain_depth_kept` và `break_class` là giá trị **theo carrier**, nằm ở `spans.csv`; `runs.csv` chỉ giữ `chain_depth_kept_max` và `chains_intact_count` (số carrier abnormal có chuỗi tới root còn lớp `gt`), vì một run có tới 20 carrier với độ sâu khác nhau.
- Biến thể `I2_lenient` (độ nhạy, không phải nhãn chính): nhãn root khớp GT, hoặc `reason` của root nhắc tên GT như một từ nguyên vẹn (so trên chữ thường, biên là ký tự không thuộc `[a-z0-9_]` ở hai phía).
- Ví dụ: đúng: consolidate của root `{"span_id":"r","local_root_cause":"checkoutservice",...}`; sai: `"currencyservice"` (`other_service`), hoặc `null` hoặc `"none"` (`refusal`).
- `NA`: không có consolidate của root (run cắt cụt) hoặc output không parse được (ghi integrity problem).

### I3: hint

- Trường nguồn: self-state `output` của mọi span (đây chính là `self_evidence` mà `GlobalEvidenceGraph.record` lưu, `UP/coordinator.py` 80 đến 104), `raw.cmdb_id` của span.
- Dựng lại đúng luật chuỗi của tác giả (`UP/coordinator.py` 469 đến 483): với mỗi nút GEG có `evidence` là chuỗi: nếu `"has_error_logs"` có trong chuỗi và `'"has_error_logs": true'` có trong `evidence.lower()` thì `service_name` (là `cmdb_id` của span) vào danh sách `error_log_services`; ngược lại nếu `'"is_abnormal": true'` có trong `evidence.lower()` thì vào `metric_anomaly_services`. Danh sách là tập (tác giả dùng `set()`; thứ tự phụ thuộc hash seed nên so sánh bằng tập). `service_name` của nút GEG là `raw.cmdb_id`, nếu thiếu thì `raw.service_name`, nếu thiếu nữa thì `span_id` (`UP/coordinator.py` 442). Khi đếm `hint_list_size` và `gt_sole_entry`, "duy nhất" là chuỗi chính xác sau `lower()` (như `set()` của tác giả), nên `checkoutservice` và `checkoutservice-0` là hai phần tử; báo thêm `hint_list_size_by_base` (gộp theo `_k8s_service_base`, như `match`).
- **I3 = `in_list(GT, error_log_services)` hoặc `in_list(GT, metric_anomaly_services)`.**
- Ghi `hint_list_size` (số dịch vụ duy nhất trong hai danh sách), `gt_sole_entry` (đúng khi hai danh sách hợp lại chỉ có một dịch vụ duy nhất và nó khớp GT), biến thể `I3_strict` (đúng khi GT nằm trong một danh sách có không quá 2 dịch vụ duy nhất).
- I1 đọc cờ bằng `json.loads`, còn luật hint của tác giả khớp chuỗi `"is_abnormal": true` có đúng một dấu cách; JSON gọn như `"is_abnormal":true` qua được harness nhưng rơi khỏi hint. Analyzer đếm span có I1 `true` mà chuỗi hint sai vào `unseen_branches.parsed_true_but_hint_string_false` (hiện 0 trên 1901 self-state [reviewer]).
- **I3 phụ thuộc I1** (cùng cờ self-state, gán theo `cmdb_id` của span, không theo dịch vụ mà văn bản nói tới). Báo I1 và I3 là hai cột nhưng không diễn giải như hai giai đoạn độc lập.
- Kiểm tương đương độc lập (không vòng tròn): phân tích **dòng hint trong văn bản prompt cuối** (request `phase == trace`, `operation == null` và `attempt == 0` để không lấy nhầm retry, `payload.messages[1].content`): lấy các dòng bắt đầu đúng bằng `⚠️ Services with ERROR LOGS (strongest evidence): ` và `⚡ Services with metric anomalies only: `, tách theo `, `, so tập với tập dựng lại; ghi `hint_equivalent`. Không dùng `parse_prompt` của `K/check-hash-seed-order.py` cho phép so này (hàm đó dựng lại từ GEG bằng chính luật chuỗi nên so sánh sẽ vòng tròn).
- Ví dụ: đúng: một nút GEG của span `cmdb_id` `checkoutservice` có `evidence` chứa `"is_abnormal": true` và không có `"has_error_logs": true`, nên `metric_anomaly_services` có `checkoutservice`; sai: hai danh sách chỉ có `frontendservice`.
- `NA`: không có self-state nào (run cắt cụt rất sớm). Dương giữ nguyên ở run cắt cụt; âm là `NA`.

### I4: hạng cuối

- Trường nguồn: `result.json.root_causes`.
- Hạng = `_label_hit(GT, root_causes)`, 0-based, `-1` là không trúng. **I4 đúng khi hạng bằng 0 (R@1).** Ghi hạng, R@3 (hạng 0 đến 2), MRR = `1 / (hạng + 1)` hoặc `0` khi hạng `-1`, định dạng bằng `f"{x:.4f}"` (không dùng `round()`) để khớp 4 chữ số của `author-score.txt`.
- Kiểm tương đương: R@1 (so chính xác) và MRR (4 chữ số) tính lại phải trùng `author-score.txt` ở mọi run có chấm điểm (70 ở S1 v2, 62 ở vòng 2; run dừng không có `scoring/`). Lệch run nào là thất bại của analyzer.
- Ví dụ: `root_causes = ["currencyservice","checkoutservice",...]`, GT `checkoutservice`: hạng 1, I4 sai, R@3 đúng, MRR 0.5000; `["checkoutservice-0",...]`: hạng 0, I4 đúng.
- `NA`: không có `result.json`.

### I5: tổng hợp cuối có theo root không

- Trường nguồn: `result.json.root_causes[0]` (top-1) và nhãn root (I2).
- `final_top1_matches_root_label` có ba lớp: `refusal` (nhãn root là `refusal`), `same` (`_label_hit(nhãn_root_đã_chuẩn_hóa, [top1]) == 0`), `diff` (còn lại). Nhãn root dùng cùng chuẩn hóa với I2.
- Chỉ báo này đo việc báo cáo root và tổng hợp cuối liên hệ lỏng (prompt cuối nhận ba đường độc lập, mục 5).
- Ví dụ: root `currencyservice`, top-1 `currencyservice`: `same`; root `null`: `refusal`; root `checkoutservice`, top-1 `currencyservice`: `diff`.
- `NA`: không có `result.json` hoặc không có nhãn root.

## 5. Nhãn của run

Đường đi của bằng chứng không tuyến tính. Request tổng hợp cuối nhận ba đường độc lập: báo cáo consolidation của root (`root_level_report`), toàn bộ Global Evidence Graph (`geg.summary()`, mọi self-evidence nguyên văn) và hint dựng bằng so khớp chuỗi (`UP/coordinator.py` 465 đến 503). Một span abnormal đã vào GEG thì bằng chứng luôn tới bước cuối dù consolidation làm rơi nó. Vì vậy:

1. **Nhãn chính là vector biên I0 đến I5**, báo theo run, case và điều kiện. Chỉ báo đúng ở mọi run `Ev` ghi `saturated` (không phải điểm mất trong corpus này).
2. `first_loss_linear` (góc nhìn phụ, đúng cách phát biểu RQ b): chỉ báo sai đầu tiên theo thứ tự I0 (S0), I1 (S1), I2 (S2), I3 (S3), I4 (S4); `preserved` nếu cả năm đúng; nếu một chỉ báo `NA` đứng trước chỉ báo sai đầu tiên thì nhãn là `NA`. **Chú thích bắt buộc về thiên lệch thứ tự**: S2 đứng trước S3 là quy ước, không phải thứ tự phụ thuộc thật; khi I1 đúng mà I2 sai nhãn luôn là S2, kể cả khi run vẫn đạt R@1. S4 chỉ xuất hiện khi I0 đến I3 đều đúng. Chú thích này nằm trong `summary.json` và trong báo cáo.
3. `final_residual` (không phải nhãn cơ chế), áp theo thứ tự ưu tiên: `none` khi I4 đúng (thắng mọi nhãn khác; run đúng mà I0 sai vẫn mang cờ `hit_without_evidence` riêng); chỉ khi I4 sai: `S0` khi I0 sai; `S1` khi I0 đúng nhưng I1 sai; `reaches_final_input_not_rank1` khi I1 và I3 đều đúng (phần dư của R@1, không giải thích bởi I0 đến I3); `hint_missing_not_rank1` khi I1 đúng mà I3 sai; `NA` khi một chỉ báo cần đọc là `NA`. Phần dư `reaches_final_input_not_rank1` tách tiếp bằng I5: `top1_equals_wrong_root_label` (lớp `same`), `top1_differs_from_root_label` (lớp `diff`), `root_refusal` (lớp `refusal`). Ghi cờ `chain_weakened` (I2 sai khi I1 đúng) và `hint_weakened` (I3 sai khi I1 đúng).
4. `outcome_hit` là R@1, báo độc lập với nhãn. `hit_without_evidence` đúng khi I0 sai mà I4 đúng (run đúng mà tín hiệu từ tool không có ở đầu vào).
5. Hai nhãn song song (`first_loss_linear` và `final_residual`) và hai cờ riêng được báo cả cho run đúng lẫn sai, để nhãn "đúng" ở nhánh `hit_without_evidence` không che cơ chế.

## 6. Hai cờ méo (không thuộc nhóm "mất")

- `D1` (cấp span): span có `has_error_logs == true` trong self-state và **mọi** kết quả `search_logs` của span đó có `source != absent` và văn bản log **đã giao cho mô hình** (mục 1.2) rỗng (không quá một dòng) hoặc không có dòng nào chứa `error`, `exception`, `fail` (không phân biệt hoa thường). Mỗi span có 3 đến 4 lượt `search_logs`; luật là "mọi lượt", không phải "một lượt nào đó". Cột `d1_log_source` ghi `author`, `absent` hoặc `mixed`. Span có mọi lượt `source == absent` là `D1_na` (nguồn log đã gỡ nên rỗng do thiết kế harness: 10 trên 14 span `has_error_logs == true` thuộc `metric_no_log` [reviewer]), không tính vào D1 và báo riêng.
- Lưu ý: mọi dòng log ở S1 v2 có `severity: unknown` (298146 trên 298146 dòng log) và không có dòng nào chứa `error|exception|fail` [scout], nên mọi khai báo `has_error_logs == true` có log thật đều tự động là D1 (13 trên 14 span tất cả lượt rỗng, 1 hỗn hợp [reviewer]). D1 vì vậy trùng với "mọi khai báo error logs" và không phân biệt có log chống lưng hay không; báo cáo ghi nhận xét này.
- `D1_empty_logs` (biến thể chặt): `has_error_logs == true` khi mọi văn bản log đã giao (với `source != absent`) rỗng (không quá một dòng).
- `D2` (cấp span): `is_abnormal == true`, `has_error_logs` khác `true`, `has_metric_anomaly` là bool `false`, và span không có `tool_result` metric nào có phản hồi bắt đầu bằng `key,`. Cờ thiếu cho `NA`. `D2` cấp dịch vụ: đúng khi mọi span abnormal của dịch vụ đó đều D2. Ghi cả với dịch vụ không phải GT. (Cách đọc "mọi span của nó không nhận bảng" theo tên dịch vụ cho 26, 25 hoặc 51 trên 86 cặp dịch vụ-run tùy định nghĩa [reviewer], nên luật cấp span ở trên là định nghĩa duy nhất.)
- Cấp run: `D1` đúng khi có span D1 nào đó; `D2` đúng khi có dịch vụ D2 nào đó.

## 7. So sánh hai điều kiện

Khóa là (gói, case, seed). Mọi cặp `metric`-`no_metric` và `metric`-`metric_no_log` rẽ nhánh sớm ở chuỗi request. Đo lại bằng `compare()` của `K/compare-run-outputs.py`, chỉ số 1-based tính mọi request pha trace kể cả retry: `metric` so với `no_metric` rẽ ở request 3 (14 cặp), 4 (3), 6 (6), 7 (1) trên 24 cặp S1 v2; `metric` so với `metric_no_log` ở 3 (14) và 4 (10) trên 24 cặp [kết quả đo của kế hoạch, kiểm lại khi analyzer chạy]. Request rẽ nhánh luôn là `self_state_verification` với `attempt == 0`; bỏ retry thì là request 3, 5 hoặc 6 trong dãy `attempt == 0`. Mọi khẳng định tự động ghi cơ sở đánh số.

Hệ quả: hai đường là mẫu lấy mẫu độc lập (hỗn loạn lấy mẫu), không ghép cặp.
- Không gán nhãn ở mức cặp, không dùng `gain_class` hay `evidence_used`/`evidence_unused`. So sánh chỉ ở mức **run và case**: ba run `metric` với ba run `no_metric` của cùng case, mô tả, ghi "không ghép cặp".
- Với mỗi (case, điều kiện) ghi: chỉ báo đạt xa nhất (k lớn nhất sao cho I0 đến Ik đều đúng), hạng cuối, `first_request_divergence` (thô và gộp NO_KPI với NO_ROWS), giai đoạn của request phân kỳ đầu tiên.
- Cặp `metric` với `metric_no_log` dùng lại quỹ đạo (tỉ lệ `agent_complete` giống từng byte, scout đo 1156 trên 1249, khoảng 92,5 phần trăm [scout]); ghi là phép kiểm lặp lại, không phải đối chứng độc lập. Analyzer báo tỉ lệ này.
- `no_metric` trả NO_ROWS ("No matching records found.") còn `metric` trả NO_KPI ("No fluctuating metrics found.") khi không có KPI; phép ghép `metric` với `no_metric` vì vậy lẫn hiệu ứng câu chữ. `no_metric` hỏi rỗng tốn 3,33 request mỗi span so với 2,2 ở `metric` (span chỉ nhận kết quả rỗng, S1 v2 [scout, kiểm lại]). Tách được hiệu ứng này cần chạy GPU, ngoài phạm vi; ghi như một hạn chế.

## 8. Cột replay hint (chỉ mã của tác giả)

Các cột `hint_list_size`, `gt_sole_entry`, `d1_dropped_list_size`, `d2_dropped_list_size` (kích thước danh sách hint nếu bỏ các span D1 hoặc D2) được ghi ở `spans.csv` và `runs.csv`. Không có biến thể `oracle_carrier`. Câu giới hạn bắt buộc đi kèm: các cột này chỉ nói đầu ra của **mã tác giả** dựng hint, không nói gì về hành vi của LLM hay hiệu quả của X.

## 9. Luật xếp hạng ứng viên cho X (RQ c)

Luật này **mô tả**, không có ngưỡng đạt hay trượt (sếp quyết định 2026-11-01). Đơn vị là dịch vụ GT. Bảng chính tính trên điều kiện `metric`, **sau khi bỏ case hiệu chỉnh** (mục 13); điều kiện `no_metric` là bên đối chiếu mô tả.

### 9.1 Bước A: phép kiểm khả thi

Với mỗi câu kết cục (mục 9.3), đếm số **đơn vị có dữ liệu** `n` (định nghĩa riêng từng câu) và số đơn vị đỡ câu đó `k`. Nếu `n < 3` thì câu được ghi `not_testable` thay vì báo `k` trên `n`. Ngưỡng 3 là ngưỡng khả thi quy ước (nguồn: quy ước, không thực nghiệm), chỉ quyết định có báo hay không, không quyết định kết luận.

Với độ tương phản trong case theo giai đoạn k (bước B iii): đếm số case có đủ cả run "mất ở k" lẫn run "giữ ở k" trong `Ev`. Dưới 3 case thì giai đoạn k là `not_testable` cho độ tương phản đó.

**Phép kiểm khả thi, tính lại lần cuối trước đóng băng** từ chế độ chỉ cấu trúc của analyzer (`runtime/analysis-evidence-loss-calibration/structure-recheck/structure.csv`, trùng từng byte với `runtime/analysis-evidence-loss-structure/structure.csv`) và từ số đã phơi nhiễm (không có nhãn nào của analyzer trên `metric` hay `no_metric`). Bảng chính là điều kiện `metric`, **bỏ case hiệu chỉnh `99f095`**, nên còn 4 case có `Ev` (5f7a77, 29583d, 7bbfa6, ad1c27), mỗi dịch vụ GT một case (checkoutservice, emailservice, recommendationservice, currencyservice). Số theo case lấy từ scout (R@1, nhãn root), nhãn `[scout]`:

| Giai đoạn k | Nhóm "mất ở k" | Nhóm "giữ ở k" | Case có đủ hai nhóm | Kết luận khả thi |
|---|---|---|---|---|
| I0 | I0 sai (3 case không có span GT: 30e3c7, de6a50, 272a47; 9 run, R@1 0 trên 9 [scout]) | I0 đúng (4 case, 11 run sau khi bỏ 99f095) | 0 (không case nào có cả hai nhóm) | `not_testable` trong case; chỉ báo mô tả giữa case, lẫn hình dạng trace |
| I1 | 0 run (I1 14 trên 14 trước khi bỏ 99f095 [reviewer]) | 11 run | 0 | `not_testable` |
| I2 | 8 run (5f7a77 hai, 29583d ba, 7bbfa6 ba) | 3 run (5f7a77 một, ad1c27 hai) | 1 (5f7a77: 1 giữ, 2 mất) | `not_testable` (1 case, 1 dịch vụ GT) |
| I3 | 0 run (I3 14 trên 14 trước khi bỏ 99f095 [reviewer]) | 11 run | 0 | `not_testable` |
| I4 | chính là kết quả R@1 | | | Không áp dụng (vòng tròn); chỉ báo phần dư |

Bản có `99f095` (độ nhạy) chỉ có thêm 3 run mất ở I2 và 1 run trượt R@1, không thêm case có đủ hai nhóm, nên kết luận không đổi. Kết luận: **độ tương phản trong case không testable ở mọi giai đoạn** trên dữ liệu này, và đó là điều đã biết trước khi chạy. Bảng báo cáo vì thế dựa vào bước B (i), (ii), (iv) và các câu kết cục ở 9.3 (mô tả theo đơn vị), không dựa vào độ tương phản.

**Khả thi của từng câu kết cục (9.3)** trên bảng chính, tính từ cấu trúc và số đã phơi nhiễm (mọi số dưới đây là dự báo từ số phơi nhiễm, không phải nhãn của analyzer; lần chạy chính thức tính lại và báo từng chỗ lệch):

| Câu | `n` dự kiến (đơn vị có dữ liệu) | Khả thi |
|---|---|---|
| `S0_gt_span_absent` | 4 (cả bốn dịch vụ GT có run `metric` hoàn tất) | `testable` |
| `S0_gt_span_present_not_queried` | 4 (mỗi dịch vụ GT có một case có span GT: 5f7a77, 29583d, 7bbfa6, ad1c27) | `testable` |
| `S2_root_label_lost_hit_kept` | 3 (checkoutservice, emailservice, recommendationservice có run I1 đúng và I2 sai; currencyservice rời vì ad1c27 có I2 đúng ở mọi run `Ev`) | `testable` ở đúng ngưỡng (3); mất một đơn vị là `not_testable` |
| `S4_inputs_present_not_rank1` | 4 | `testable` |
| `label_mismatch_flags` | chưa biết: cần case có cả run `Ev` có D1 lẫn không D1, và nhãn D1 theo run chưa được tính | `not_testable` dự kiến; nếu không đủ 3 đơn vị thì ghi `not_testable` |
| `no_stage_implicated` | không áp dụng cổng `n` | đúng khi mọi câu trên là `not_testable` hoặc `k = 0` |

Các điều kiện `not_testable` đã biết khi đóng băng: độ tương phản trong case ở I0, I1, I2 và I3; `label_mismatch_flags` (dự kiến). `S2_root_label_lost_hit_kept` có `n = 3`, sát ngưỡng.

### 9.2 Bước B: báo cáo

1. Bảng biên I0 đến I5 theo (case, điều kiện), với `k` trên `n` seed.
2. Tỉ lệ `saturated` của từng chỉ báo.
3. Với giai đoạn k `testable` (nếu có): độ tương phản gộp phân tầng theo case, tức hiệu tỉ lệ trượt R@1 giữa nhóm mất và nhóm giữ trong từng case, trung bình có trọng số theo số run, kèm số case đóng góp, thuần mô tả (không p-value, không khoảng tin cậy suy diễn).
4. Phần dư `reaches_final_input_not_rank1` và tách của nó theo I5.
5. Bảng độ nhạy: có và không có run cắt cụt; có và không có case hiệu chỉnh; I2 so với `I2_lenient`; I3 so với `I3_strict`.

### 9.3 Bước C: kết cục

Kết cục là một danh sách các câu mô tả, mỗi câu kèm `k` trên `n` đơn vị và số case. Trạng thái câu: `not_testable` (khi `n < 3`) hoặc `k` trên `n` với danh sách đơn vị đỡ và đơn vị không đỡ. Không ngưỡng nào chọn câu thắng.

Vị từ cấp đơn vị (đơn vị `u` là dịch vụ GT; chỉ dùng run hoàn tất, điều kiện `metric`, bỏ case hiệu chỉnh):

| Câu | Đơn vị có dữ liệu | Đơn vị `u` đỡ câu khi | Cách đọc (không nhân quả) |
|---|---|---|---|
| `S0_gt_span_absent` | `u` có ít nhất một run hoàn tất | có một case của `u` mà mọi run hoàn tất của nó đều `S0_gt_span_absent` | Dịch vụ GT không có span trong trace và không được hỏi; lẫn hoàn toàn với hình dạng trace, tool là oracle GT; không đọc như lựa chọn truy vấn của mô hình |
| `S0_gt_span_present_not_queried` | `u` có một case có span GT và ít nhất một run hoàn tất | có một case của `u` có span GT mà mọi run hoàn tất của nó đều `S0_gt_span_present_not_queried` | Dịch vụ GT có span nhưng không được hỏi; đây mới là "không chọn hỏi GT" |
| `S2_root_label_lost_hit_kept` | `u` có ít nhất một run `Ev` với I1 đúng và I2 sai | có ít nhất một run `Ev` với I1 đúng, I2 sai, I4 đúng | Chuỗi consolidation làm rơi nhãn root nhưng GT vẫn đứng hạng 1; nhất quán với việc bằng chứng tới tổng hợp cuối qua GEG và hint |
| `S4_inputs_present_not_rank1` | `u` có ít nhất một run `Ev` | có ít nhất một run `Ev` với I1 đúng, I3 đúng, I4 sai | Bằng chứng có ở đầu vào cuối (GEG và hint) mà GT không đứng hạng 1: phần mất nằm ở tổng hợp cuối hoặc ở độ khó của case; kèm tách I5 |
| `label_mismatch_flags` | `u` có một case có cả run `Ev` có D1 lẫn không D1 | trong case đó, tỉ lệ trượt R@1 của run có D1 lớn hơn run không D1 | D1 trùng "mọi khai báo error logs"; so sánh trong case, không ngưỡng |
| `no_stage_implicated` | | mọi câu trên là `not_testable` hoặc có `k = 0` (vị từ "có ít nhất một run" dễ thỏa nên câu này khó đạt; báo kèm số run đỡ trên số run của từng đơn vị) | Không giai đoạn nào được chỉ ra bằng số đơn vị đã nêu |

(`S2_root_label_lost_hit_kept` và `S4_inputs_present_not_rank1` loại trừ nhau cho cùng một run nhưng không loại trừ nhau cho cùng một đơn vị. Cột "đơn vị có dữ liệu" và cổng `n >= 3` tính trên tập sau khi bỏ case hiệu chỉnh; mỗi câu ghi thêm, cho từng đơn vị, số run đỡ trên số run có dữ liệu, để vị từ "có ít nhất một run" không che tỉ lệ.)

**Hạng của X ứng viên**: sắp các câu `testable` có `k >= 1` theo `k/n` giảm dần rồi `k` giảm dần, luôn hiển thị `n` bên cạnh `k` (câu có `n` khác nhau không so được bằng `k` thô); câu bằng cả `k/n` lẫn `k` được ghi `ngang nhau`, không thêm luật phá hòa. Không có ngưỡng đạt hay trượt. Mỗi câu kèm hướng X tương ứng và điều kiện "cần can thiệp có model để kiểm" (hiệu quả chưa đo, chỉ RQ c đo được).

### 9.4 Hướng X ứng viên và điều kiện "thực hiện được mà không sửa upstream"

"Không sửa upstream" nghĩa là: X là một wrapper phía harness (như `adapt_payload`, `get_tool` trong `K/smoke-worker.py`, đã bọc `coordinator.chat_api` và `coordinator._get` mà không sửa byte nào của `upstream/`) hoặc một prompt override nằm trong file ngoài `upstream/`. Mọi hướng đòi sửa trực tiếp `coordinator.py` ghi "cần override bên ngoài" hoặc "không đạt".

| Hướng | Giai đoạn | Câu kết cục liên quan | Thực hiện được không sửa upstream? | Ghi chú [UNVERIFIED, chưa thử] |
|---|---|---|---|---|
| Đưa danh sách dịch vụ đã biết vào truy vấn metric, hoặc tool wrapper tự truy vấn bảng cho mọi dịch vụ đã biết | S0 | `S0_gt_span_absent`, `S0_gt_span_present_not_queried` | Đạt: wrapper `get_tool` hoặc thêm bước ở harness | Làm tool oracle GT bớt ngầm; phải nêu rõ trong RQ c |
| Kiểm chứng hoặc sửa nhãn `has_error_logs` ở self-state (ví dụ viết lại lời nhắc self-state) | S1 | `label_mismatch_flags` | Đạt nếu làm bằng viết lại `payload.messages` ở `adapt_payload` (override bên ngoài) | Sửa trực tiếp prompt trong `coordinator.py` không đạt |
| Đưa bằng chứng metric vào luật của consolidation hoặc giảm vai trò chuỗi consolidation | S2 | `S2_root_label_lost_hit_kept` | Cần override bên ngoài (viết lại payload consolidate); không đạt nếu sửa `coordinator.py` | Nếu `S2_root_label_lost_hit_kept` được đỡ thì mức lợi kỳ vọng thấp; không suy ra hiệu quả |
| Sửa luật dán nhãn hint ("metric anomalies only" cho span chỉ trễ) | S3 | `label_mismatch_flags` | Cần override bên ngoài (viết lại dòng hint trong payload cuối); luật chuỗi nằm trong thân `coordinator.py`, không thay được bằng wrapper hàm | |
| Hậu xử lý hoặc xếp lại hạng ở tổng hợp cuối | S4 | `S4_inputs_present_not_rank1` | Đạt: xử lý `result.json` ở harness | Phải tránh dùng nhãn GT |

## 10. Dự đoán và trạng thái phơi nhiễm

Mỗi dự đoán có kết quả "bị bác" hợp lệ.

| Mã | Dự đoán | Bị bác khi | Trạng thái phơi nhiễm |
|---|---|---|---|
| P1 | Ở `no_metric`, mọi run có I0 sai; mọi lượt hỏi metric tới GT có `empty_reason = absent_source` | có run `table_received` đúng, hoặc `empty_reason` khác `absent_source` ở lượt hỏi GT | Hằng đẳng theo thiết kế harness (nguồn metric bị gỡ), không phải dự đoán thực nghiệm |
| P2 | Ở `metric`, hơn một nửa số span mang bảng GT được tự đánh `is_abnormal = true` | chừng một nửa hoặc ít hơn | Scout đã thấy khoảng 94 phần trăm (92 trên 98 span GT) [scout]; **mô tả có phơi nhiễm, không phải dự đoán** |
| P3 | Nhãn root nêu GT ở dưới nửa số run `Ev` | từ nửa trở lên | Đã thấy 3 trên 14 [scout, reviewer]; mô tả có phơi nhiễm |
| P4 | Các run trượt R@1 ở nhánh có metric có D1 nhiều hơn các run đúng | tỉ lệ D1 của run trượt không lớn hơn run đúng | Khám phá có gốc từ scout (11 trên 11 run trượt mang tuyên bố `has_error_logs`, 18 trên 18 run đúng không [scout]); vì mọi khai báo `has_error_logs` đều là D1 nên gần hằng đẳng; ghi vậy |
| P5 | Một phần run đúng R@1 ở `no_metric` là `hit_without_evidence` | không run nào | Đã thấy: `ad1c27` `no_metric` đạt R@1 3 trên 3 mà không có bảng metric (currencyservice chiếm 10 trên 25 span) [scout] |

## 11. Bảng "kết cục đã biết trước"

Trên dữ liệu `metric` mà scout và reviewer đã thấy (14 run hoàn tất, nhánh `metric`; số do reviewer tính, **chưa tính lại bằng analyzer**):

| Mục | Đã thấy |
|---|---|
| I0 | 14 trên 14 run (trong 5 case có GT trong trace) |
| I1 | 14 trên 14 |
| I3 | 14 trên 14 (GT ở danh sách "metric anomalies only", không bao giờ ở danh sách ERROR LOGS) |
| I2 | 3 trên 14 |
| R@1 | 10 trên 14 |
| `first_loss_linear` | S2 ở 11 trên 14 run (trong đó 7 run vẫn R@1); S1, S3, S4 bằng 0 |
| Trong case có đủ hai nhóm S2 | chỉ 5f7a77, chênh lệch bằng 0 |
| R@1 giữa các seed | giống nhau ở 7 trên 8 case (ngoại lệ 99f095) |
| Tổng hợp cuối so nhãn root (23 run `metric` hoàn tất, gồm cả case không có GT trong trace) | `same` 8, `diff` 4, `refusal` 11 |

Số theo case (R@1 trên số run hoàn tất, run có nhãn root khớp GT) [scout]: 5f7a77 3/3, 1; 99f095 2/3, 0; 29583d 0/3, 0; 7bbfa6 3/3, 0; ad1c27 2/2, 2.

Diễn giải bắt buộc ghi trong báo cáo:
- Luật cũ với ngưỡng "tối thiểu 3 case đủ hai nhóm" **không thể thỏa** trên cỡ mẫu này (chỉ một case có đủ hai nhóm S2) và kết luận "chưa có giai đoạn nào rõ ràng" là điều đã biết. Luật mới đổi sang báo cáo mô tả có phép kiểm khả thi (mục 9.1) và nhánh `no_stage_implicated`.
- Mọi ngưỡng từng sinh từ số đã thấy (ba trên tám, 90 phần trăm, 40 phần trăm) bị bỏ hoặc gắn "mô tả có phơi nhiễm".
- **Trạng thái kết cục dự kiến từ số đã thấy**, tính theo vị từ ở 9.3 (đây là dự báo từ số phơi nhiễm, không phải kết quả; số do reviewer tính, chưa tính lại bằng analyzer). Hai phiên bản, vì bảng chính bỏ case hiệu chỉnh mà phép rút cho `99f095` (mục 13.1):
  - Trên cả năm case `Ev` (độ nhạy, có `99f095`): `S0_gt_span_absent` 3 trên 4 đơn vị (checkoutservice, emailservice, recommendationservice có một case không có span GT; currencyservice thì không); `S0_gt_span_present_not_queried` 0 trên 4; `S2_root_label_lost_hit_kept` 3 trên 4 (checkoutservice, currencyservice, recommendationservice; emailservice không vì 29583d mất cả R@1); `S4_inputs_present_not_rank1` 2 trên 4 (emailservice qua 29583d, currencyservice qua một run 99f095).
  - Trên bảng chính (bỏ `99f095`): `S0_gt_span_absent` 3 trên 4; `S0_gt_span_present_not_queried` 0 trên 4; `S2_root_label_lost_hit_kept` 2 trên 3 (checkoutservice và recommendationservice; currencyservice rời mẫu số vì `ad1c27` có I2 đúng ở mọi run `Ev`, nên không có run I1 đúng và I2 sai); `S4_inputs_present_not_rank1` 1 trên 4 (chỉ emailservice).
  - `label_mismatch_flags` dự kiến `not_testable` (D1 tập trung ở ba case, ít case có cả hai nhóm; số thật do analyzer báo).
  - Hạng X dự kiến trên bảng chính: `S0_gt_span_absent` (3 trên 4), rồi `S2_root_label_lost_hit_kept` (2 trên 3), rồi `S4_inputs_present_not_rank1` (1 trên 4); trên bản có `99f095` hai câu đầu cùng `k` = 3, luật 9.3 xếp theo `k/n` rồi `k`. `S0_gt_span_absent` lẫn hoàn toàn với hình dạng trace (I0 trùng với "có span GT trong trace" ở 8 trên 8 case [reviewer]), nên báo cáo không đọc nó như lựa chọn truy vấn của mô hình. Đây là các số đã được phơi nhiễm; đóng góp của đo này là tính lại tất định theo luật cố định và công khai các chỗ lệch, không phải khám phá mới.
- Bảng này tính trước khi đóng băng và không gán nhãn nào từ analyzer; `metric` và `no_metric` chưa được gán nhãn theo run trước đóng băng.

## 12. Tuyên bố phơi nhiễm

Đo này **không mù**. Những gì người thiết kế đã thấy trước khi đóng băng codebook:

1. **Scout dữ liệu** (mức tổng hợp): chuỗi phễu của `metric` (14 run: bảng GT 14 trên 14; span GT abnormal 92 trên 98; GT ở hint 14 trên 14; nhãn root là GT 3 trên 14; R@1 10 trên 14), `metric_no_log` (15 run: 102 trên 108 span, hint 15 trên 15, root 3, R@1 8) và `no_metric` (15 run: bảng 0, span 0 trên 108, hint 0, R@1 5, R@3 9); bảng theo case (R@1 và root); thống kê D1 (11 trên 11 run trượt R@1 có tuyên bố `has_error_logs`, 18 trên 18 run đúng không; 14 span `has_error_logs == true`, tập trung ở 99f095, 29583d và một run ad1c27); tỉ lệ self-state abnormal theo có hay không có bảng (324 trên 327 và 66 trên 1574); tỉ lệ metric rỗng theo loại; thống kê rẽ nhánh `metric` và `no_metric`; oracle nguồn (bảng KPI của GT có ở 8 trên 8 case, log không có bằng chứng nào); 222 trên 222 kết quả log không rỗng bị nén; tỉ lệ truy vấn metric tới dịch vụ không phải span (300 trên 689, 492 trên 956).
2. **Reviewer đã thấy thêm** (số theo run): phễu theo run của `metric` và `metric_no_log` ở mức I0 đến I4; `first_loss_linear` dự kiến; quan hệ nhãn root với top-1 cuối (`same` 8, `diff` 4, `refusal` 11 ở `metric`); I2 theo run; độ trùng 92,5 phần trăm `agent_complete` giữa `metric` và `metric_no_log`; chỉ số request rẽ nhánh giữa các điều kiện; số carrier mỗi run `metric` có I0 đúng (1, 2, 2, 2, 3, 3, 3, 11, 11, 12, và năm run 20 [kế hoạch đo]).
3. **Người viết codebook** (2026-11-01), khi kiểm tên trường, đã xem: các số đếm cấu trúc ở mục 1.2; phân bố tiền tố khóa KPI của 616 hàng bảng metric trên toàn S1 v2 (chỉ bốn dịch vụ GT: currencyservice 322, checkoutservice 216, recommendationservice 54, emailservice 24 hàng) và số lượt truy vấn metric theo `service_name` trên toàn S1 v2 (gộp mọi điều kiện, không theo run); bảng GT, loại lỗi và số span theo case; lý do dừng của 12 run dừng ở S1 v2 và vòng 2. Không xem nhãn theo run nào của analyzer (chưa có analyzer).
4. `metric`, `metric_no_log` và `no_metric` đều đã được thấy ở mức tổng hợp. Mọi dự đoán P2 đến P5 có phơi nhiễm; P1 là hằng đẳng. Mọi giả thuyết sinh ra từ scout (ví dụ tuyên bố `has_error_logs` bịa) gắn nhãn **khám phá có gốc từ scout, không phải xác nhận**.
5. Chưa xem: nhãn theo run của analyzer ở bất kỳ corpus nào; vòng 2 ở mức nhãn; S1 v3 (chưa có output, và không độc lập vì cùng prompt và seed với S1 v2).
6. Việc loại case `29583d` khỏi tập rút hiệu chỉnh (mục 13) dựa trên hiểu biết đã phơi nhiễm về kết quả của nó.
7. **Hiệu chỉnh** (2026-11-01): người đọc mù và analyzer đã cho nhãn I0 đến I5 trên hai run `metric_no_log` của `99f095` (mục 13.3). Hai run này và case `99f095` ở mọi điều kiện không vào bảng chính, nên phơi nhiễm này không chạm bảng chính; hai run đó vẫn là phần của độ nhạy "có case hiệu chỉnh".
8. Tên dịch vụ GT hiện ra trong gói đọc mù dưới dạng dữ liệu đo (bảng metric, self-state), nên người đọc có thể đoán GT từ C1 đến C4; ở phần C5 người đọc đã thấy GT. Ghi là hạn chế của đọc mù.

## 13. Hiệu chỉnh, đồng thuận tay và biên nhận

### 13.1 Quy tắc rút case hiệu chỉnh (tất định theo danh sách case; kết quả đã tính được từ trước)

- Điều kiện hiệu chỉnh là `metric_no_log`, **hai run** (seed 20261026 và 20261027) của **một case**. Case hiệu chỉnh không dùng làm xác nhận: bảng chính bỏ nó (cả ba điều kiện), bảng có nó chỉ là độ nhạy; hai run đó không vào luật ở mục 9 dưới bất kỳ hình thức nào.
- Tập hợp lệ: case có `gt_span_in_trace >= 1` (đo bằng chế độ chỉ cấu trúc của analyzer, không in nhãn hay điểm) **trừ `29583d`** (case trượt R@1 ở mọi seed trong điều kiện `metric`; việc loại dựa trên hiểu biết đã phơi nhiễm, mục 12.6). Theo cấu trúc đã đo, tập này là `5f7a77`, `99f095`, `7bbfa6`, `ad1c27`; bản chính thức lấy từ chế độ chỉ cấu trúc.
- **Kết quả rút đã tính được** (2026-11-01, chỉ từ `trace_id` và seed, không đọc nội dung run): danh sách sắp theo SHA256 và `random.Random(20261031).choice` cho `99f095`, dù có hay không loại `29583d`. `99f095` là case duy nhất mà R@1 khác nhau giữa các seed (mục 11), nên phép rút không mù; báo cáo ghi điều này và dùng bảng có `99f095` như độ nhạy.
- Khóa sắp xếp: SHA256 (hex, chữ thường) của chuỗi `trace_id` 32 ký tự hex, UTF-8, tăng dần. Rút đúng một lần bằng `random.Random(20261031).choice(danh_sách_đã_sắp)`.
- Thay đổi luật trong lúc hiệu chỉnh là "thay đổi hiệu chỉnh" (nằm trong bảng thay đổi ở bản v1), không phải deviation. Deviation chỉ tính từ sau đóng băng.

**Run hiệu chỉnh đã rút** (2026-11-01, trước khi đọc nội dung run; danh sách hợp lệ lấy từ `runtime/analysis-evidence-loss-structure/structure.csv`, bốn case `gt_spans >= 1` bỏ `29583d`, sắp theo SHA256 của `trace_id`: `5f7a77`, `ad1c27`, `99f095`, `7bbfa6`; `random.Random(20261031).choice` một lần cho `99f095`, trùng kết quả đã tính ở trên). Danh sách nằm ở `runtime/analysis-evidence-loss-calibration/calibration-runs.txt`:

- `99f095aeb2571c7f2ee99885e8332c8a--metric_no_log--s20261026`
- `99f095aeb2571c7f2ee99885e8332c8a--metric_no_log--s20261027`

Gói đọc mù (phần đầu không có GT, điều kiện hay nhãn của analyzer; phần "10 đầu ra cuối và GT" tách riêng, mở sau khi C1 đến C4 đã nộp) nằm ở `runtime/analysis-evidence-loss-calibration/packets/`: mã mù `272f5a` (seed 20261026) và `e5fcdf` (seed 20261027), ánh xạ ở `blind-map.json` cùng thư mục (người đọc không được mở). Tên dịch vụ GT vẫn xuất hiện trong phần đầu như dữ liệu đo (các bảng metric, self-state, consolidation) vì C1 đến C4 cần chúng; gói không chỉ ra dịch vụ nào là GT.

### 13.2 Đồng thuận tay (một lượt, mù)

- Người đọc thứ hai là **một agent mù** (LLM-coder, cùng họ model với tác giả codebook, nên đồng thuận cao có thể giả); sếp phân xử chỗ lệch. Báo là "LLM-coder" khi nêu số.
- Không dùng ngưỡng kappa, PABAK hay bootstrap. Báo đồng thuận thô theo chỉ báo và theo case, kèm kappa chỉ như số mô tả.
- Form C1 đến C5, thiết kế **không biết GT** (agent chỉ thấy dịch vụ nào có bảng, không biết đâu là GT; analyzer ghép với GT sau):
  - C1 `tool_signal`: tập dịch vụ mà mô hình nhận được bảng metric trong run (từ `tool_result.params.service_name` và phản hồi `key,`). Tương ứng I0.
  - C2 `self_state_uses_gt_evidence`: với mỗi dịch vụ trong C1, có span carrier nào tự đánh `is_abnormal == true` không. Tương ứng I1.
  - C3 `root_names_gt`: lớp của nhãn root với mỗi dịch vụ trong C1 (khớp, dịch vụ khác, từ chối). Tương ứng I2.
  - C4 `hint_supported`: mỗi dịch vụ trong C1 nằm ở danh sách hint nào của prompt cuối. Tương ứng I3.
  - C5 `first_loss_stage`: điền ở một vòng riêng, **sau khi** C1 đến C4 đã nộp, lúc đó mới mở GT và 10 đầu ra cuối; là hàm xác định của C1 đến C4 cộng bảng xếp hạng, nên đồng thuận C5 chỉ đo việc áp luật, không đo tính đúng của luật.
  - Gói của C1 đến C4 không chứa GT, tên điều kiện, vị trí GT trong đầu ra cuối hay nhãn của analyzer.

### 13.3 Kết quả hiệu chỉnh và bảng thay đổi hiệu chỉnh

Người đọc mù (LLM-coder) nộp form (`runtime/analysis-evidence-loss-calibration/form-reader.md`) với C1 đến C4 từ gói phần đầu, rồi C5 sau khi mở file đầu ra cuối. Analyzer chạy trên hai run **sau khi** form đã nộp (`--runs calibration-runs.txt`, ra `runtime/analysis-evidence-loss-calibration/rules/`; 0 vấn đề toàn vẹn, 121 trên 121 `tool_result` ghép được, R@1 và MRR trùng `author-score.txt`). Mã mù `272f5a` là seed 20261026 và `e5fcdf` là seed 20261027.

Đồng thuận thô theo chỉ báo, trên hai run (người đọc so với luật; không kappa; hai run cùng một case nên là hai đơn vị phụ thuộc, không phải hai mẫu độc lập):

| Chỉ báo | Giá trị của người đọc | Giá trị của luật | Đồng thuận |
|---|---|---|---|
| I0 (kèm tập dịch vụ nhận bảng) | đúng; tập {checkoutservice, currencyservice} | đúng; `table_key_prefixes` = {checkoutservice, currencyservice} | 2 trên 2 |
| I1 | đúng | đúng (20 trên 20 carrier abnormal) | 2 trên 2 |
| I2 | sai (root là `adservice`, `other_service`) | sai | 2 trên 2 |
| I3 | đúng (GT ở danh sách "metric anomalies only") | đúng, `hint_equivalent` đúng | 2 trên 2 |
| I4 | sai (hạng 0-based 1, R@3 đúng, MRR 0.5000) | sai, cùng hạng và MRR | 2 trên 2 |
| I5 | `same` | `same` | 2 trên 2 |
| `first_loss_linear` | S2 | S2 | 2 trên 2 |
| `final_residual` và phần tách | `reaches_final_input_not_rank1`, `top1_equals_wrong_root_label` | giống | 2 trên 2 |
| Cờ `chain_weakened`, `hint_weakened`, `hit_without_evidence` | đúng, sai, sai | đúng, sai, sai | 6 trên 6 |

Đồng thuận thô 22 trên 22 ở các chỉ báo và nhãn cấp run, không có bất đồng chưa phân loại. Hai run giống nhau về mọi nhãn (cùng GT, cùng nhãn root, cùng C5), nên đồng thuận trên hai run nói ít; đây chỉ là kiểm luật chạy đúng trên một cấu trúc. Người đọc cùng họ model với tác giả codebook.

Hai chênh lệch nhỏ giữa người đọc và dữ liệu, đã đọc lại từ gói và `spans.csv`, không chạm chỉ báo nào:
- Ở `e5fcdf` người đọc viết "mọi consolidation không phải root đều `unknown`", còn dữ liệu có 4 nút không phải root mang nhãn dịch vụ khác (`cartservice`, `adservice`, `productcatalogservice` ở hai nút) nằm ngoài chuỗi từ carrier của GT. Trên các chuỗi từ carrier abnormal lên root, `break_class` là `refusal` ở 20 trên 20, đúng như người đọc mô tả. Phân loại: lỗi đọc (nhận xét quá rộng), không đổi luật.
- Form hỏi C2 đến C4 cho **mọi** dịch vụ trong C1 (kể cả `checkoutservice`, không phải GT), còn luật chỉ tính chỉ báo cho GT. Người đọc trả lời cả hai dịch vụ; phép so chỉ dùng hàng của GT. Phân loại: mơ hồ của form (không phải của luật).

**Bảng thay đổi hiệu chỉnh** (mã chỉ nằm trong tài liệu này, không vào code hay tên test; deviation chỉ tính từ sau đóng băng):

| Mã | Phân loại | Nội dung | Thay đổi luật hoặc code | Test |
|---|---|---|---|---|
| CAL-01 | lỗi đọc của người đọc | Nhận xét "mọi consolidation không phải root đều `unknown`" quá rộng so với dữ liệu | Không | Không cần (luật đúng; chuỗi từ carrier là `refusal` ở 20 trên 20) |
| CAL-02 | mơ hồ của form | Form hỏi C2 đến C4 cho mọi dịch vụ trong C1, luật chỉ tính cho GT | Lần đọc sau đối chiếu theo hàng của GT; không đổi luật | Không cần (không đổi hành vi) |
| CAL-03 | không có lỗi luật | Không bất đồng chỉ báo nào, nên không sửa analyzer | Không | Thêm kiểm run thật đã kiểm tay (`RealRunFixtureTest`: giá trị kỳ vọng của người đọc, dữ liệu thật ở `runtime/`, thất bại khi vắng zip trừ khi `EVIDENCE_LOSS_ALLOW_NO_ZIP=1`) |

Không có thay đổi hiệu chỉnh nào đổi luật hay analyzer; hash analyzer lúc đóng băng là hash của bản đã qua test tổng hợp và test run thật.

## 14. Thiết kế cố định cho các bước sau

- Analyzer: `K/analyze-evidence-loss.py`, test `K/test-analyze-evidence-loss.py`; công cụ đối chiếu tay `K/audit-evidence-loss-labels.py` và test của nó. File `.py` mới dùng LF. Kiểu CLI giống `K/analyze-missing-source-results.py` (`sys.argv` đọc tay, chấp nhận cờ ở mọi vị trí), nạp module bằng `importlib`.
- Đầu ra: `K/runtime/analysis-evidence-loss-<nhãn>/` gồm `spans.csv`, `runs.csv`, `cases.csv`, `case-comparison.csv`, `funnel.csv`, `summary.json` (UTF-8, `indent=2`, kết thúc `\n`). Không ghi đè thư mục đã có `summary.json`; không động vào các thư mục `analysis-*` cũ.
- Hạt giống: `20261031` (rút case hiệu chỉnh, lấy mẫu kiểm toán).
- Biên nhận đóng băng: `K/evidence-loss-prereg.json` ghi phiên bản codebook, đường dẫn, SHA256 codebook (đã chuẩn hóa CRLF thành LF), SHA256 của analyzer và của mọi module analyzer nạp qua `importlib` (bốn module `check-hash-seed-order.py`, `compare-run-outputs.py`, `analyze-missing-source-results.py`, `analyze-completion-and-budget-stops.py`). `summary.json` của lần chạy chính ghi `prereg.codebook_sha_matches`, `analyzer_sha_matches`, `imports_sha_match` cùng `true`. Không có thứ tự thời gian độc lập nếu sếp không commit lúc đóng băng; báo cáo ghi điều này. Trạng thái hiện tại: **đóng băng cục bộ, không có thứ tự thời gian độc lập**; chưa commit (câu hỏi mở 7).
- Nhật ký deviation: `plans/261031-2311-rclagent-evidence-loss-analysis/deviation-log.md`. Mọi thay đổi luật sau đóng băng ghi ở đó kèm số liệu trước và sau.
- `.gitattributes` gốc cần có dòng `plans/reports/prereg-*.md text eol=lf` (hiện chỉ có dòng cho SVG; repo đặt `core.autocrlf=true`).
- Corpus: chính S1 v2; vòng 2 là bản sao tất định (62 cặp cùng hoàn tất: 48 giống hệt, 14 chỉ lệch ở response cuối do thứ tự hint; 2 cặp cùng hỏng); S1 v3 chỉ ghi chú.

## 15. Giới hạn

- n = 8 case, 4 dịch vụ GT, 3 seed gần như nhân bản (mô hình xác định theo prompt và seed). Mọi tỉ lệ là mô tả.
- Tool metric là bản đã sửa và hoạt động như oracle GT; I0 gần như đồng nghĩa "đã hỏi GT".
- Chỉ phần mã hint của tác giả replay được; hiệu quả của X chưa đo.
- Log không chứa bằng chứng nào về GT (mọi dòng `severity: unknown`), nên mọi so sánh liên quan log chỉ phản ánh khai báo của mô hình, không phản ánh bằng chứng.
- Tên "first-loss stage" thay cho "decisive step" là đề xuất, sếp chưa trả lời; đổi tên không đổi luật.

## 16. Nguồn gốc từng ngưỡng và hằng số

Không có ngưỡng nào chọn câu thắng hay quyết định đạt hay trượt (sếp quyết định 2026-11-01). Các hằng số còn lại và nguồn của chúng:

| Hằng số | Giá trị | Nguồn | Vai trò |
|---|---|---|---|
| Số đơn vị tối thiểu để báo `k` trên `n` (`FEASIBLE_UNITS`) | 3 | Quy ước, không thực nghiệm (mục 9.1) | Chỉ quyết định `not_testable` hay báo số, không quyết định kết luận |
| Số case tối thiểu cho độ tương phản trong case | 3 | Cùng quy ước | Như trên |
| `I3_strict`: danh sách hint có không quá bao nhiêu dịch vụ duy nhất | 2 | Quy ước của người viết codebook; chỉ là độ nhạy, không phải nhãn chính | Chỉ báo độ nhạy |
| Văn bản log "rỗng" | không quá 1 dòng | Hình dạng đã đo: log rỗng là bảng chỉ có dòng tiêu đề (2654 trên 2876) | Định nghĩa D1 |
| Từ khóa lỗi trong log | `error`, `exception`, `fail` (không phân biệt hoa thường) | Bộ từ phổ biến; đã đo 0 dòng nào chứa chúng ở 298146 dòng | Định nghĩa D1 |
| Độ lệch chuẩn của công cụ metric đã sửa | K = 100 | `K/metric-repair.py` của harness, không phải của đo này | Giải thích vì sao tool gần như oracle GT |
| Hạt giống rút case hiệu chỉnh và lấy mẫu kiểm toán | 20261031 | Ngày lập kế hoạch | Tất định, mục 13.1 |
| Chuỗi hint, nhãn từ chối, danh sách dịch vụ biết trước | như mục 4 | Sao chép từ mã upstream (`UP/coordinator.py`, `UP/evaluate.py`) | Tái dựng hint và nhãn tên |
| Ngưỡng 90 phần trăm, 40 phần trăm, "ba trên tám" | bỏ | Sinh từ số đã thấy (mục 11) | Không còn trong luật |
