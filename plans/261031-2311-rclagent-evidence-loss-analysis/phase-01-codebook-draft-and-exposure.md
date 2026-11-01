---
phase: 1
title: "Codebook nháp và tuyên bố phơi nhiễm"
status: completed
priority: P1
effort: "4h"
dependencies: []
---

# Phase 1: Codebook nháp và tuyên bố phơi nhiễm

## Context links
- [scout code](../reports/scout-261031-2311-rclagent-evidence-loss-code.md): bảng ranh giới giai đoạn, `file:line` của upstream.
- [scout dữ liệu](../reports/scout-261031-2311-rclagent-evidence-loss-data.md): cấu trúc `events.jsonl`, join, ground truth.
- [nghiên cứu phương pháp](../reports/research-261031-2311-evidence-loss-attribution-methods.md): first-loss stage, quy trình codebook kiểu MAST, đăng ký trước.
- Upstream: `K/runtime/kaggle-dataset-check-a-s1-v3/upstream/coordinator.py` (80 đến 104, 204 đến 292, 296 đến 332, 424 đến 538) và `evaluate.py` (57 đến 103).

## Goal
Viết bản nháp codebook định nghĩa mọi chỉ báo bằng luật tất định trên trường của `events.jsonl`, cách báo kết quả theo case, luật xếp hạng ứng viên cho X và tuyên bố phơi nhiễm, chỉ dựa trên đọc code và đọc cấu trúc dữ liệu.

## Requirements
- Mỗi chỉ báo là một hàm của các trường có tên cụ thể. Không chỉ báo nào cần đọc hiểu văn bản tự do.
- Tên dịch vụ so khớp theo đúng `_label_hit` và `_k8s_service_base` của scorer. <!-- red-team: cartservice claim wrong --> `frontend` và `frontendservice` không khớp. `cartservice` và `cartservice-0` khớp (cùng base K8s, scorer trả đúng một lần trúng ở vị trí ứng viên đó); bảng kỳ vọng của test tên dịch vụ phải ghi như vậy. Hạng của scorer là 0-based, `-1` là không trúng.
- Có sẵn chỗ cho trường hợp chưa gặp trong dữ liệu (ví dụ nhánh fallback của self-state, hiện đếm được 0 lần: đã đo 0 request tự-đánh-giá kết thúc bằng lời nhắc fallback ở cả S1 v2 và vòng 2).
- <!-- red-team: unsatisfiable rule --> Một luật không thể thỏa trên cỡ mẫu có thật thì không được đăng ký trước. Mọi điều kiện trong luật phải đi kèm phép kiểm khả thi (bước 8).
- Luật quyết định cho phép kết quả "chưa có giai đoạn nào được chỉ ra".

## Files to Create / Modify
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/reports/prereg-261031-2311-rclagent-evidence-loss-codebook.md` (codebook nháp v0, đóng băng ở phase 3)

Không sửa file nào khác.

## Steps

1. Đọc lại các đoạn upstream đã nêu và `smoke-worker.py` (kiểm `agent_complete`, `tool_result`, `tool_result_budget`, `worker-status.json`). Ghi tên trường chính xác. <!-- red-team: data-shape premise false --> Hình dạng dữ liệu thật, đã kiểm trên S1 v2 (5283 `tool_result` trong 74 file `events.jsonl`, mọi `params` đều là dict):
   - `tool_result.params` là **dict**, không phải chuỗi. `timestamp` trong đó là chuỗi mili giây. `smoke-worker.py:344` ghi `params=params`. Chuỗi biểu diễn chỉ chấp nhận như đường lùi (`ast.literal_eval`), không phải đường chính.
   - `response.body` là chuỗi JSON (cần `json.loads`). <!-- validation: metric text and empty log shape --> văn bản metric mô hình thấy nằm ở `tool_result.response`. Metric rỗng là `{"message":"No matching records found."}` hoặc `{"message":"No fluctuating metrics found."}` (2078 trên 2405 kết quả metric ở S1 v2 là message); bảng metric bắt đầu bằng `key,`. Kết quả `search_logs` rỗng KHÔNG phải `{message}` mà là bảng chỉ có dòng tiêu đề (2654 trên 2876, 0 là message): rỗng nghĩa là không quá một dòng.
   - <!-- validation: budget only for search_logs --> `tool_result_budget` chỉ tồn tại cho `search_logs` (2876 trên 2876 kết quả log, cộng 2 ở protocol; 0 trên 2405 kết quả metric) và có `delivered` (bản mô hình thực sự nhìn thấy, đã cô đọng và bỏ `log_id`), `applied`, `original_bytes`, `original_sha256`. Phép đo "mô hình thấy gì" của log đọc `delivered`; của metric đọc `tool_result.response` (không có `delivered`).
   - `tool_result.source` nhận `author`, `repaired` hoặc `absent`; `request` có `span_id`, `operation`, `number`, `attempt`, `retry_of`, `phase`; `agent_complete.output` là chuỗi JSON; `agent_complete` không bao giờ có `operation: None`, nên đầu ra cuối chỉ nằm trong `result.json` và `response.body` của request cuối.
   - <!-- validation: protocol events by path --> Mỗi gói (không phải mỗi run; hai file ở mỗi corpus) có một `run/protocol/events.jsonl` (request `phase: "protocol"`, sự kiện `protocol_pass`). Chỉ sự kiện `request` mang khóa `phase`; `tool_result`, `response`, `agent_complete` thì không. Vì vậy mọi phân tích chỉ đọc sự kiện từ đường dẫn `run/traces/<run_id>/events.jsonl` và loại `run/protocol/` theo đường dẫn, không lọc bằng `phase == "trace"` cho mọi loại sự kiện (S1 v2: 5281 `tool_result` trace cộng 2 protocol).
   - Một response có thể mang nhiều tool call (phần lớn `tool_result` đi sau response như vậy), nên ghép `tool_result` với response là ghép **đa tập** theo (tên, params, span_id), không ghép theo vị trí "lời gọi liền trước".
   - `trace-graph.json` là cây `{span_id, raw, children}` với `raw.cmdb_id`, `raw.parent_span`, `raw.timestamp` (mili giây, kiểm lại khi viết analyzer).
   - Lý do dừng nằm ở `worker-status.json` (khóa `error`, `fatal`, chuỗi kiểu repr) và `progress.json` (khóa `reason`).

2. Định nghĩa các thực thể dùng chung:
   - `GT`: giá trị `cmdb_id` trong `groundtruth.csv` của case. Run hỏng không có `scoring/`, lấy GT từ run anh em cùng case. Mỗi case ghi thêm `gt_service` (4 dịch vụ GT cho 8 case; <!-- red-team: cases not independent --> đơn vị đếm của luật là **dịch vụ GT**, không phải case, vì mỗi dịch vụ xuất hiện hai lần với loại lỗi khác nhau).
   - `match(a, b)`: bằng `_label_hit(a, [b]) == 0`.
   - `carrier span`: span có ít nhất một `tool_result` metric với `service_name` khớp GT và phản hồi là bảng. Carrier không nhất thiết là span của GT.
   - <!-- red-team: evaluable gate contradicts data --> **Bỏ khái niệm "evaluable case = có span GT trong trace".** Mô hình truy vấn được metric của mọi dịch vụ trong danh sách "Known services" của system prompt, kể cả dịch vụ không có span trong trace. Cổng vào S1 đến S4 là **I0 đúng** (đã nhận bảng metric của GT). `gt_span_in_trace` chỉ là cột chú thích. Khi I0 đúng thì I0 thắng mọi nhãn S0 khác; S0 `gt_not_in_trace` không còn là nhãn loại trừ.

3. Định nghĩa nhãn harness (đứng trước mọi chỉ báo):
   - `H_cap`: lý do dừng chứa `Per-span tool round budget exceeded`, `Model request budget exhausted` hoặc `RCLAgent deadline exceeded`.
   - `H_context`: `Context overflow`.
   - `H_parse`: `Invalid structured response`, `Invalid agent JSON output` hoặc lỗi tool call sai định dạng.
   - `H_other`: mọi lý do còn lại, kể cả thiếu `worker-status.json`.
   - <!-- red-team: censoring rule --> Run dừng bị cắt cụt (right-censored): mọi chỉ báo **dương** tính được từ sự kiện đã ghi vẫn hợp lệ và được giữ; mọi chỉ báo **âm** và mọi chỉ báo phía sau điểm dừng là `NA`. Đặc biệt I0 âm của run cắt cụt là `NA_censored`, không phải `S0_not_queried`, vì "chưa hỏi GT" không suy ra được khi mới đi qua 3 trên 25 span. Run cắt cụt không có `result.json`, không có `scoring/`; mẫu số của mọi bảng phễu ghi rõ số run bị loại. Báo bảng độ nhạy "giả sử run cắt cụt hỏng ở chỉ báo tệ nhất" bên cạnh bảng loại khỏi mẫu số, vì run bị cắt không chắc ngẫu nhiên (<!-- validation: GT span counts --> ad1c27 `metric` s27 thuộc case có 10 span GT, còn `5f7a77` có 13 là nhiều nhất, và hỏng vì đầu ra model sai định dạng).
   - Cắt bớt kết quả: <!-- validation: budget only for search_logs --> `tool_result_budget` không tồn tại cho metric (0 trên 2405), nên cắt bớt không thể là nguyên nhân mất bảng metric; analyzer khẳng định "không có sự kiện `tool_result_budget` nào cho metric" (kiểm cấu trúc, không phải kỳ vọng giá trị 0 vô nghĩa). Cắt bớt chỉ đo ở `search_logs` (`applied`), phục vụ D1.
   - Retry: `malformed_tool_call_retry` (33 sự kiện trong 31 run S1 v2: đã đo) là yêu cầu lặp của cùng một lượt logic. <!-- validation: attempt 0-based --> `attempt` bắt đầu từ 0: đếm request theo span chỉ tính `attempt == 0` (lượt đầu); `attempt > 0` là retry (S1 v2: 6822 request trace `attempt == 0` = 4858 self-state đầu + 1894 consolidate + 70 cuối; retry `attempt` 1/2/3 = 31/1/1 = 33, khớp 33 sự kiện retry); số retry ghi riêng; `first_request_divergence` so theo chuỗi request không-retry.

4. <!-- red-team: first-loss order bias, S4 residual --> Viết chỉ báo I0 đến I4 cho mỗi run, **báo từng chỉ báo như một biên riêng** (không chỉ nhãn tuần tự):
   - **I0 (tín hiệu từ tool)**: ba cột độc lập: `queried_gt` (có `tool_result` metric với `service_name` khớp GT theo scorer), `table_received` (có phản hồi bắt đầu bằng `key,` cho GT), `gt_span_in_trace` (chú thích). I0 = `table_received`. Nếu I0 sai: `S0_not_queried` (không hỏi GT), hoặc `S0_empty_result` kèm `empty_reason`: `absent_source` (`source=absent`), `no_kpi` ("No fluctuating metrics found."), `no_rows` ("No matching records found."). Ghi `tool_match_rule_differs` cho lượt `no_rows` khi tên dịch vụ khớp theo scorer nhưng tool dùng `str.contains` và đường node-level (`metric-repair.py:22-24`), nên "không có hàng" có thể là luật so tên của tool chứ không phải nguồn rỗng. Ghi `table_key_prefixes` (khóa KPI có tiền tố GT hay chỉ node-level).
   - **I1 (self-state)**: tồn tại carrier mà `agent_complete` self-state có `is_abnormal == true`; ghi `has_metric_anomaly` của carrier. Nhánh fallback (request cuối bắt đầu bằng "Based on all retrieved evidence above") thiếu `has_error_logs` và `has_metric_anomaly`: gán `S1_not_flagged:fallback_flags_missing` khi carrier dùng fallback và thiếu cờ. Ghi `misattributed` khi I1 đúng nhờ carrier có `cmdb_id` không khớp GT. I1 là "đã có carrier abnormal", nên gần bão hòa (đã đo lại theo định nghĩa carrier ở bước 2: 1 đến 20 carrier mỗi run `metric` có I0 đúng, 7 trên 15 run dưới 11, không phải 11 đến 20); báo kèm số carrier.
   - **I2 (consolidation)**: `agent_complete` consolidate của root có `local_root_cause` khớp GT theo scorer. <!-- red-team: labeller edge cases --> Kiểm kiểu: JSON null, chuỗi `none`, `unknown`, `null`, chuỗi rỗng và mọi giá trị không phải chuỗi đều thuộc lớp `refusal` (35 trên 1894 consolidate có `local_root_cause` là JSON null: đã đo ở S1 v2; `.lower()` trên giá trị đó sẽ ném lỗi). Với mỗi carrier abnormal, đi từ carrier lên root theo `raw.parent_span`, ghi lớp nhãn từng nút (`gt`, `other_service`, `refusal`); ghi `chain_depth_kept`, `break_class`, `carrier_count`. Biến thể `I2_lenient`: nhãn root khớp GT hoặc `reason` nhắc tên GT như từ nguyên vẹn.
   - **I3 (hint)**: dựng lại `evidence_hint` đúng luật chuỗi của tác giả (coordinator.py 469-483). I3 đúng khi GT nằm trong ít nhất một danh sách. Ghi `hint_list_size`, `gt_sole_entry`, và biến thể `I3_strict` (GT trong danh sách không quá 2 mục). **I3 phụ thuộc I1** (cùng cờ self-state, gán theo `cmdb_id` của span), nên báo I1 và I3 là hai cột nhưng không diễn giải như hai giai đoạn độc lập. Kiểm tương đương độc lập: phân tích **dòng hint trong văn bản prompt cuối** ("Services with ERROR LOGS ...", "metric anomalies only") và so tập dịch vụ, không so với `check-hash-seed-order.py:parse_prompt` (hàm đó dựng lại từ GEG bằng chính luật chuỗi nên so sánh sẽ vòng tròn).
   - **I4 (hạng cuối)**: hạng 0-based của GT trong `root_causes` của `result.json` theo `_label_hit`; I4 đúng khi hạng bằng 0 (R@1). Ghi hạng, R@3 và MRR tính bằng 4 chữ số thập phân như `author-score.txt`.
   - <!-- red-team: root vs final synthesis link --> **I5 (tổng hợp cuối có theo root không)**: `final_top1_matches_root_label` với lớp `same`, `diff`, `refusal` (root `none`/`unknown`/null), so top-1 của `result.json` với `local_root_cause` của root bằng `_label_hit`. Chỉ báo này đo trực tiếp việc báo cáo root và tổng hợp cuối liên hệ lỏng.

5. <!-- red-team: first-loss order bias --> Nhãn mỗi run:
   - **Nhãn chính là vector biên**: I0 đến I5 báo riêng, theo case và theo điều kiện. Chỉ báo đúng ở mọi run đủ điều kiện ghi `saturated` (không phải điểm mất trong corpus này).
   - `first_loss_linear` (góc nhìn phụ, đúng cách phát biểu RQ b): chỉ báo sai đầu tiên theo thứ tự S0, S1, S2, S3, S4. **Chú thích bắt buộc về thiên lệch thứ tự**: S2 đứng trước S3 là quy ước, không phải thứ tự phụ thuộc thật, vì prompt cuối nhận ba đường độc lập (`geg.summary()`, `root_level_report`, `evidence_hint`; `coordinator.py:485-503`); khi I1 đúng mà I2 sai thì nhãn luôn là S2, kể cả khi run vẫn đạt R@1. S4 chỉ xuất hiện khi I0 đến I3 đều đúng.
   - `effective_loss` đổi tên thành `final_residual` và **không phải một nhãn cơ chế**: `S0` khi I0 sai; `S1` khi I0 đúng nhưng I1 sai; `reaches_final_input_not_rank1` khi I1 đúng mà I4 sai (phần dư của R@1, không giải thích bởi I0 đến I3). Phần dư này tách tiếp bằng I5: `top1_equals_wrong_root_label` (top-1 = nhãn root khác GT), `top1_differs_from_root_label` (top-1 khác nhãn root), `root_refusal`. Ghi cờ `chain_weakened` (I2 sai khi I1 đúng) và `hint_weakened` (I3 sai khi I1 đúng).
   - Ghi `outcome_hit` (R@1) độc lập với nhãn, và `hit_without_evidence` khi I0 sai mà I4 đúng.

6. Viết hai cờ méo, không thuộc nhóm mất:
   - <!-- red-team: D1 reads delivered --> `D1`: span tuyên bố `has_error_logs=true` mà kết quả `search_logs` **đã giao cho mô hình** (`delivered`) rỗng (không quá một dòng, tức chỉ có dòng tiêu đề) hoặc không có dòng nào chứa dấu hiệu lỗi (`error`, `exception`, `fail`). Lưu ý: mọi dòng log đều có `severity: unknown` (298146 trên 298146 dòng log ở S1 v2: đã đo) và 0 lần xuất hiện `error|exception|fail`, nên mọi khai báo `has_error_logs=true` đều tự động là D1. Do đó D1 trùng với "mọi khai báo error logs" và không phân biệt có log chống lưng hay không; báo thêm `D1_empty_logs` (khai báo khi kết quả `delivered` rỗng, định nghĩa rỗng là không quá một dòng; <!-- validation: empty log is header-only -->) như biến thể chặt, và ghi rõ nhận xét này trong báo cáo.
   - `D2`: dịch vụ đứng trong danh sách "metric anomalies only" mà mọi span của nó có `has_metric_anomaly=false` và không nhận bảng metric nào. Ghi cả với dịch vụ không phải GT.

7. <!-- red-team: pairing is not true pairing --> Viết định nghĩa so sánh hai điều kiện. Khóa là (package, case, seed). Mọi cặp `metric`-`no_metric` và `metric`-`metric_no_log` rẽ nhánh sớm ở chuỗi request (<!-- validation: request index basis --> đo lại bằng `compare()` của `compare-run-outputs.py`, chỉ số 1-based tính mọi request pha trace kể cả retry, `compare-run-outputs.py:17,84`: `metric` so với `no_metric` rẽ nhánh ở request 3 (14 cặp), 4 (3), 6 (6), 7 (1) trên 24 cặp; `metric` so với `metric_no_log` ở 3 (14) và 4 (10) trên 24 cặp; request rẽ nhánh luôn là `self_state_verification` với `attempt == 0`; bỏ retry thì là request 3, 5 hoặc 6 trong dãy `attempt == 0`; mọi khẳng định tự động phải ghi cơ sở đánh số), từ đó hai đường là mẫu độc lập (hỗn loạn lấy mẫu). Vì vậy:
   - Không gán nhãn ở mức cặp và không dùng `gain_class` hàm ý nhân quả (`evidence_used`, `evidence_unused` bị cấm trong báo cáo, và từ "used" bị cấm). So sánh chỉ ở mức **run và case**: ba run `metric` với ba run `no_metric` của cùng case, mô tả, ghi "không ghép cặp".
   - Với mỗi case và điều kiện ghi: chỉ báo đạt xa nhất, hạng cuối, `first_request_divergence` (thô và gộp NO_KPI với NO_ROWS), giai đoạn của request phân kỳ đầu tiên.
   - Cặp `metric` với `metric_no_log` dùng lại quỹ đạo (1156 trên 1249 `agent_complete` giống từng byte [reviewer đo]); ghi là phép kiểm lặp lại, **không phải đối chứng độc lập**. Analyzer báo tỉ lệ `agent_complete` giống từng byte giữa hai điều kiện.
   - Ghi rõ trong báo cáo: <!-- validation: per-span request counts --> `no_metric` hỏi rỗng tốn 3,33 request/span so với khoảng 2,2 của `metric` ở span chỉ nhận kết quả rỗng (đã đo lại trên S1 v2; số 3,35 và 2,0 lệch nhẹ do định nghĩa span), nên chênh lệch có lẫn hiệu ứng câu chữ.

7b. <!-- red-team: replay folded --> Quy tắc replay được gộp vào analyzer (phase 2), không còn phase riêng. Các cột `hint_list_size`, `gt_sole_entry`, `d1_dropped_list_size`, `d2_dropped_list_size` (kích thước danh sách hint nếu bỏ span D1 hoặc D2) được ghi trong `spans.csv` và `runs.csv`. Bỏ biến thể `oracle_carrier`. Câu giới hạn bắt buộc: các cột này chỉ nói đầu ra của mã tác giả, không nói hành vi của LLM.

8. <!-- red-team: decision rule rewritten --> Viết **luật xếp hạng ứng viên** (thay cho luật chọn đích). Đơn vị là dịch vụ GT (4), với số case đóng góp nêu bên cạnh. Mọi ngưỡng ghi nguồn gốc (thực nghiệm, quy ước, tùy ý) và mọi phép tính ghi số đơn vị đóng góp. Không dùng phần trăm trên run làm điều kiện.
   - **Bước A, phép kiểm khả thi (tính trước khi đóng băng, chỉ từ cấu trúc và từ số đã phơi nhiễm)**: với mỗi giai đoạn k, đếm số case có đủ cả run "mất ở k" lẫn run "giữ ở k" trong `Ev` (run có I0 đúng, hoàn tất). Điều kiện nào có số khả thi dưới 3 case thì codebook ghi `not_testable` thay vì vẫn đặt ngưỡng.
   - **Bước B, báo cáo**: (i) bảng biên I0 đến I5 theo (case, điều kiện) với k trên n seed; (ii) tỉ lệ `saturated` của từng chỉ báo; (iii) với giai đoạn k testable: độ tương phản gộp phân tầng theo case, tức hiệu tỉ lệ trượt R@1 giữa nhóm mất và nhóm giữ trong từng case, trung bình có trọng số theo số run, kèm số case đóng góp, thuần mô tả; (iv) phần dư `reaches_final_input_not_rank1` và tách của nó theo I5.
   - **Bước C, kết cục (một trong các câu mô tả, không phải "đích")**:
     - `S4_inputs_present_not_rank1`: có run `Ev` với I1 đúng, I3 đúng, I4 sai → "phần mất nằm ở tổng hợp cuối, hoặc ở độ khó của case"; kèm I5.
     - `S2_root_label_lost_hit_kept`: có run `Ev` với I1 đúng, I2 sai, I4 đúng (nhãn root rơi nhưng GT vẫn hạng 1; nhất quán với việc GEG và hint đưa bằng chứng tới prompt cuối). Câu này ghi cụ thể số run.
     - `S0_gt_span_absent` và `S0_gt_span_present_not_queried`: hai câu tách của `S0_not_queried`; chỉ câu thứ hai là "không chọn hỏi GT dù GT có span", câu thứ nhất lẫn với hình dạng trace.
     - `label_mismatch_flags`: D1 hoặc D2 thay đổi nội dung hint ở nhiều run; so sánh trong cùng case (có D1, không D1) mô tả theo từng case, không ngưỡng.
     - `no_stage_implicated`: không câu nào trên đỡ được bằng số case đã nêu.
   - Hạng X ứng viên cho RQ (c) là danh sách có thứ tự (sắp các câu `testable` có `k >= 1` theo `k/n` giảm dần rồi `k` giảm dần, luôn hiển thị `n` bên cạnh `k`; bằng cả hai thì ghi `ngang nhau`) kèm điều kiện "cần can thiệp có model để kiểm". Điều kiện **"X thực hiện được mà không sửa upstream"** định nghĩa: X là một wrapper phía harness hoặc một prompt override nằm trong file ngoài `upstream/`, không sửa byte nào của `upstream/`. Codebook liệt kê hướng nào của scout đạt, hướng nào không; hướng đòi sửa luật chuỗi hint hay prompt consolidate của upstream được ghi "cần override bên ngoài".
   - Mục "kết cục luật đã biết trước trên dữ liệu đã thấy" (bước 9b) là bắt buộc trong codebook.

9. Viết danh sách dự đoán, mỗi dự đoán kèm trạng thái phơi nhiễm:
   - P1: ở `no_metric`, mọi run có I0 sai với `empty_reason = absent_source`. Trạng thái: hằng đẳng theo thiết kế harness.
   - P2: ở `metric`, phần lớn span mang bảng GT được tự đánh `is_abnormal=true`. Trạng thái: scout đã thấy khoảng 94 phần trăm; **mô tả có phơi nhiễm, không phải dự đoán**.
   - P3: nhãn root nêu GT ở dưới nửa số run `Ev`. Trạng thái: đã thấy khoảng 21 phần trăm; mô tả có phơi nhiễm.
   - P4: các run trượt R@1 ở nhánh có metric có D1 nhiều hơn các run đúng. Trạng thái: khám phá có gốc từ scout (11 trên 11 run trượt mang D1); và vì mọi khai báo `has_error_logs` đều là D1 (bước 6) nên P4 gần như hằng đẳng; ghi vậy.
   - P5: một phần run đúng R@1 ở `no_metric` là `hit_without_evidence`. Trạng thái: đã thấy case ad1c27.
   - Mỗi dự đoán có kết quả "bị bác" hợp lệ.

9b. <!-- red-team: foregone outcome table --> Thêm bảng **"kết cục đã biết trước"** vào codebook: liệt kê, trên dữ liệu `metric` mà scout và reviewer đã thấy (14 run hoàn tất, nhánh `metric`; số do reviewer tính, chưa tính lại bằng analyzer): I0 14 trên 14, I1 14 trên 14, I3 14 trên 14, I2 3 trên 14, R@1 10 trên 14; `first_loss_linear` cho S2 ở 11 trên 14 (trong đó 7 run vẫn R@1), S1 S3 S4 bằng 0; chỉ một case (5f7a77) có đủ hai nhóm S2 và chênh lệch bằng 0; R@1 giống nhau giữa các seed ở 7 trên 8 case; tổng hợp cuối khớp nhãn root ở 8 trên 23 run `metric`. Ghi thẳng: luật cũ có ngưỡng "tối thiểu 3 case đủ hai nhóm" không thể thỏa, và kết luận "chưa có giai đoạn nào rõ ràng" là điều đã biết, nên luật mới đổi sang báo cáo mô tả có phép kiểm khả thi. Mọi ngưỡng sinh từ số đã thấy (3 trên 8, 90 phần trăm, 40 phần trăm) bị bỏ hoặc gắn "mô tả có phơi nhiễm".

10. Viết **tuyên bố phơi nhiễm**: liệt kê các số tổng hợp mà scout đã thấy (chuỗi phễu của `metric`, tỉ lệ self-state abnormal, tỉ lệ nhãn root, thống kê D1, tỉ lệ rẽ nhánh). <!-- red-team: reviewer exposure --> Bổ sung các phân bố mà red team đã thấy: phễu theo run của `metric` và `metric_no_log` ở mức I0 đến I4, `first_loss_linear` dự kiến, quan hệ nhãn root với top-1 cuối (`same` 8, `diff` 4, `refusal` 11 ở `metric`), I2 theo run, độ trùng 92,5 phần trăm `agent_complete` giữa `metric` và `metric_no_log`, `metric` và `no_metric` rẽ nhánh ở request chỉ số 1. Ghi: `metric`, `metric_no_log` và `no_metric` đều đã được thấy ở mức tổng hợp; mọi dự đoán P2 đến P5 có phơi nhiễm; chỉ S1 v3 chưa xem và nó không độc lập.

11. Ghi các thiết kế cố định cho phase sau: tên file analyzer, quy ước đầu ra, hạt giống `20261031`, nơi lưu `deviation-log.md`. Thêm: biên nhận đóng băng ghi hash của codebook (sau khi chuẩn hóa CRLF thành LF) và hash của mọi module analyzer nạp qua `importlib`.

12. Gửi bản nháp cho sếp xem các ngưỡng còn lại và nguồn gốc của chúng. Việc sếp chưa phản hồi không chặn phase 2; chỉ chặn phase 3.

## Verification
- Mỗi chỉ báo I0 đến I5 trong codebook có: tên trường nguồn, luật, giá trị `NA`, và một ví dụ tổng hợp (đúng, sai).
- Codebook không chứa số lấy từ nhãn theo run của analyzer; chỉ có số của scout và red team trong mục phơi nhiễm và bảng kết cục đã biết, có nhãn nguồn.
- Mọi điều kiện của luật có số đơn vị khả thi hoặc nhãn `not_testable`.
- `grep -n "TODO\|TBD" "F:/Nam/UIT/NT114 - NCKH/plans/reports/prereg-261031-2311-rclagent-evidence-loss-codebook.md"` không có kết quả.

## Success criteria
- Một người chưa đọc scout vẫn gán được chỉ báo cho một run bằng cách đọc codebook và các trường được nêu.
- Luật không chứa điều kiện không thể thỏa; có nhánh `no_stage_implicated`.
- Mục phơi nhiễm và bảng kết cục đã biết liệt kê đủ những gì đã thấy.

## Risks
- Định nghĩa carrier bỏ sót bằng chứng nằm ở span nhận bảng nhưng sau đó xóa hết trong self-state. Giảm thiểu: I1 đo chính hiện tượng này.
- So khớp chuỗi con trên self-evidence trong I3 phụ thuộc định dạng JSON. Giảm thiểu: kiểm tương đương bằng dòng hint của prompt cuối (phase 2).
- Tool metric là bản harness đã sửa (`source=repaired`, ngưỡng K = 100 độ lệch chuẩn, `metric-repair.py:13`) và bảng chỉ xuất hiện khi hỏi đúng GT, nên I0 gần như đồng nghĩa "mô hình đã hỏi GT": tool hoạt động như oracle GT. Ghi vào codebook và báo cáo; phân biệt truy vấn GT với truy vấn khác.

## Rollback
Xóa file nháp `prereg-261031-2311-rclagent-evidence-loss-codebook.md`. Chưa có thay đổi nào ở nơi khác.
