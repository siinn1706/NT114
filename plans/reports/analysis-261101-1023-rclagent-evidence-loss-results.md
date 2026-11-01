# Kết quả đo nơi mất bằng chứng theo giai đoạn của RCLAgent khi thiếu nguồn metric (RQ b)

- Ngày: 2026-11-01. Chỉ CPU, không gọi LLM, không Kaggle, không đụng test split RE2-OB.
- Quy ước đường dẫn: `K/` là `F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`. Số liệu nằm ở `K/runtime/analysis-evidence-loss-s1-v2/` (`runs.csv`, `spans.csv`, `cases.csv`, `case-comparison.csv`, `funnel.csv`, `summary.json`), bản sao tất định ở `-r2/` và `-r2-vs-s1-v2/`, hiệu chỉnh ở `-calibration/`, kiểm toán ở `-audit/`. Số suy ra từ luật xếp hạng (không có sẵn trong file của analyzer) ở `K/runtime/analysis-evidence-loss-decision/` (`outcome-sentences.csv`, `predictions.csv`, `x-direction-ranking.csv`).
- Luật: codebook v1 đóng băng, `plans/reports/prereg-261031-2311-rclagent-evidence-loss-codebook.md`, SHA256 `f06077a1a3eb2ab0301f605edbe7e48ef5d94a80b7a99fcd0f5fb3a6f73fc769`, biên nhận `K/evidence-loss-prereg.json`. Analyzer `K/analyze-evidence-loss.py` SHA256 `0460964ae37a4210e277ac31070b2c67979606794a58274a3a2258d7eb70d978`, không sửa; `summary.json` ghi `prereg.codebook_sha_matches`, `analyzer_sha_matches` và `imports_sha_match` cùng `true` ở cả hai corpus.
- **Đóng băng cục bộ, không có thứ tự thời gian độc lập** (chưa commit, câu hỏi mở Q7). Hash là bằng chứng thứ tự duy nhất.
- Nhãn trong báo cáo là **mô tả theo trace, không phải nhân quả**. Mọi so sánh giữa điều kiện là mô tả, không ghép cặp, không kiểm định.

## 1. Trả lời RQ (b) bằng lời thường

1. Khi bỏ nguồn metric (`no_metric`), mô hình không bao giờ nhận được bảng metric nào: I0 là 0/20 trên bảng chính (hằng đẳng theo thiết kế của harness, vì nguồn bị gỡ). R@1 ở nhánh này là 4/20 so với 8/20 ở nhánh có metric (bảng chính, hai nhánh là hai quỹ đạo độc lập, không ghép cặp). Cả bốn run đúng ở `no_metric` đều đúng mà không có bảng metric (`hit_without_evidence` 4/4).
2. Ở nhánh có metric, theo luật đóng băng, câu kết cục có tỉ lệ k/n cao nhất là `S0_gt_span_absent` (3 trên 4 dịch vụ GT): dịch vụ GT không có span trong trace nên không bao giờ được hỏi. Câu này **lẫn hoàn toàn với hình dạng trace** (tool metric gần như oracle GT), không đọc như lựa chọn truy vấn của mô hình.
3. Câu thứ hai là `S2_root_label_lost_hit_kept` (2 trên 3 dịch vụ GT): nhãn root của consolidation mất tên GT nhưng GT vẫn đứng hạng 1. Câu thứ ba là `S4_inputs_present_not_rank1` (1 trên 4). `S0_gt_span_present_not_queried` là 0 trên 4; `label_mismatch_flags` là `not_testable`.
4. Vì `S0_gt_span_absent`, `S2_root_label_lost_hit_kept` và `S4_inputs_present_not_rank1` đều có `k` từ 1 trở lên, nhánh `no_stage_implicated` **không** được kích hoạt. Tuy nhiên độ tương phản trong case không testable ở mọi giai đoạn của nhánh `metric`, nên dữ liệu **không cho phép** nói giai đoạn nào là nơi mất bằng chứng theo nghĩa nhân quả; chỉ có danh sách ứng viên cho RQ (c).
5. Mọi kết cục này đã được phơi nhiễm trước khi đóng băng (mục 2): đóng góp của đo này là tính lại tất định theo luật cố định, không phải khám phá mới. Mọi dòng của bảng ở mục 2 khớp số đã thấy trước, không có chỗ lệch (riêng P4 hai bên đếm khác định nghĩa, xem mục 14).
6. Ở `metric_no_log` (nguồn bị gỡ thứ hai là log), nhãn `first_loss_linear` ở bảng chính trải ra S0 6, S1 1, S2 10, S3 1, preserved 3 (mục 6); ở `metric` bảng chính, biên là I2 3/20 và `first_loss_linear` S0 9, S2 8, preserved 3 (mục 5 và 6). Đây là mô tả, không phải đối chứng, vì hai điều kiện dùng lại phần lớn cùng quỹ đạo.

## 2. Thiết kế rút gọn, phơi nhiễm và kết cục đã biết trước

- Đơn vị là dịch vụ GT (4: checkoutservice, emailservice, currencyservice, recommendationservice); 8 case, mỗi dịch vụ hai case khác loại lỗi; 3 seed lồng trong case và gần như là bản nhân bản (mô hình xác định theo prompt và seed); span lồng trong run. Mọi tỉ lệ là "k trên n" mô tả, không phần trăm trên run, không p-value.
- Bảng chính: S1 v2 (72 run, 70 hoàn tất), điều kiện `metric`, **bỏ case hiệu chỉnh `99f095`** ở cả ba điều kiện. Hai cột độ nhạy: "cả 8 case" và "chỉ bỏ 2 run hiệu chỉnh" (hai run `metric_no_log` của `99f095`, `K/runtime/analysis-evidence-loss-calibration/calibration-runs.txt`). Hai run hiệu chỉnh thuộc `metric_no_log` nên với điều kiện `metric` và `no_metric` cột "chỉ bỏ 2 run" trùng cột "cả 8 case".
- Analyzer không có cờ loại trừ nên `runs.csv` giữ đủ 72 run; mọi bảng dưới đây lọc theo case ở bước đọc.
- **Tuyên bố phơi nhiễm** (codebook mục 12): đo này không mù. Người thiết kế đã thấy ở mức tổng hợp phễu của cả ba điều kiện, R@1 và nhãn root theo case, thống kê D1; reviewer đã thấy thêm số theo run của `metric` và `metric_no_log`; người viết codebook đã thấy phân bố khóa KPI và số span theo case. Chưa thấy nhãn theo run của analyzer ở bất kỳ corpus nào, trừ hai run hiệu chỉnh `99f095` `metric_no_log` đã được người đọc mù và analyzer gán nhãn (codebook mục 12.7; ngoài bảng chính). Tên dịch vụ GT hiện ra trong gói đọc mù dưới dạng dữ liệu đo nên người đọc có thể đoán GT (codebook mục 12.8). Việc rút case hiệu chỉnh `99f095` dựa trên hiểu biết đã phơi nhiễm. Mọi giả thuyết sinh ra từ scout (ví dụ khai báo `has_error_logs` không có log chống lưng) là **khám phá có gốc từ scout, không phải xác nhận**.
- **Bảng "kết cục đã biết trước" so với tính lại** (số của codebook mục 11 là số reviewer tính trước khi có analyzer; cột phải là số analyzer, nhánh `metric`, cả 8 case, 14 run `Ev` = hoàn tất với I0 đúng):

| Mục | Đã thấy trước (codebook mục 11) | Analyzer (`runs.csv`, `funnel.csv`) | Lệch |
|---|---|---|---|
| I0, I1, I3 trên `Ev` | 14/14 mỗi chỉ báo | I0 14/14 trong 5 case có span GT; I1 14/14; I3 14/14 | không |
| I2 | 3/14 | 3/14 | không |
| R@1 trên `Ev` | 10/14 | 10/14 | không |
| `first_loss_linear` S2 | 11/14 (7 vẫn R@1) | 11/14; trong đó 4 run R@1 sai, 7 đúng; S1, S3, S4 bằng 0 | không |
| Tách I5 (23 run `metric` hoàn tất) | same 8, diff 4, refusal 11 | same 8, diff 4, refusal 11 | không |
| Độ tương phản trong case ở S2 | chỉ `5f7a77`, chênh 0 | chỉ `5f7a77`, chênh 0,00 | không |
| Câu kết cục, bảng chính | `S0_gt_span_absent` 3/4; `S0_gt_span_present_not_queried` 0/4; `S2_root_label_lost_hit_kept` 2/3; `S4_inputs_present_not_rank1` 1/4; `label_mismatch_flags` `not_testable` | giống từng câu (mục 12.2) | không |

## 3. T1: corpus, hoàn tất theo điều kiện, run dừng

| Điều kiện | Run | Hoàn tất | Run dừng (nhãn harness, số request) |
|---|---|---|---|
| `metric` | 24 | 23 | ad1c27 s27 H_parse (10 request) |
| `metric_no_log` | 24 | 24 | - |
| `no_metric` | 24 | 23 | 272a47 s26 H_parse (17 request) |

- S1 v2: 70 hoàn tất, 2 dừng (cả hai `H_parse`): `K/runtime/analysis-evidence-loss-s1-v2/summary.json` (`completed`, `censored`, `harness_class`).
- Vòng 2 (`-r2/summary.json`): 62 hoàn tất, 10 dừng (`H_cap` 8, `H_parse` 2), `metric` 23, `metric_no_log` 24, `no_metric` 15 hoàn tất. Chi tiết 8 run `H_cap` ở mục 13.
- Bất biến: `integrity_problems` rỗng, `unseen_branches` rỗng, scorer trùng 70/70 (S1 v2) và 62/62 (vòng 2), `tool_results_joined` 5281/5281 và 4910/4910, `hint_equivalence` 70 true và 2 `NA` (S1 v2). Kiểm chéo độc lập từ zip thô ở `plans/reports/verify-261101-rclagent-evidence-loss-p4.md`.
- **Độ nhạy "run cắt cụt hỏng ở chỉ báo tệ nhất"**: chỉ có một run `metric` bị dừng, `ad1c27` s27 (`H_parse`, 10 request; I0 đúng, I1 đúng, I3 chưa đọc được), thuộc case có hai run còn lại đều `preserved`.
  - Gán I2 sai, I3 đúng, I4 sai: `S2_root_label_lost_hit_kept` thành 2/4 và `S4_inputs_present_not_rank1` thành 2/4 (hai câu bằng cả `k/n` lẫn `k`, ghi `ngang nhau`), `S0_gt_span_absent` giữ 3/4 đứng đầu.
  - Gán I2 sai, I3 đúng, I4 đúng: `S2_root_label_lost_hit_kept` thành 3/4 (ngang `S0_gt_span_absent`) và `S4_inputs_present_not_rank1` giữ 1/4.
  - Trong cả hai kịch bản `S0_gt_span_absent` vẫn đứng đầu hoặc ngang đầu. Nguồn: `outcome-sentences.csv` (hai dòng "run cat cut"); các kịch bản khác (ví dụ I2 đúng) chưa tính và không cần cho kết luận.
  - Run `no_metric` bị dừng (`272a47` s26) không ảnh hưởng gì: `table_received` sai ở 24/24 run `no_metric`.

## 4. T2: S0 theo case (truy vấn GT tách khỏi truy vấn khác)

| Case | Điều kiện | GT | Span GT | `queried_gt` | `table_received` | `empty_reason_set` (số run) | span `tool_match_rule_differs` | `table_key_prefixes` |
|---|---|---|---|---|---|---|---|---|
| 272a47 | `metric` | recommendationservice | 0 | 0/3 | 0/3 | - | 0 | - |
| 272a47 | `no_metric` | recommendationservice | 0 | 0/2 | 0/2 | - | 0 | - |
| 29583d | `metric` | emailservice | 1 | 3/3 | 3/3 | - | 0 | emailservice |
| 29583d | `no_metric` | emailservice | 1 | 3/3 | 0/3 | absent_source 3 | 0 | - |
| 30e3c7 | `metric` | emailservice | 0 | 0/3 | 0/3 | - | 0 | - |
| 30e3c7 | `no_metric` | emailservice | 0 | 0/3 | 0/3 | - | 0 | - |
| 5f7a77 | `metric` | checkoutservice | 13 | 3/3 | 3/3 | - | 0 | checkoutservice |
| 5f7a77 | `no_metric` | checkoutservice | 13 | 3/3 | 0/3 | absent_source 3 | 0 | - |
| 7bbfa6 | `metric` | recommendationservice | 2 | 3/3 | 3/3 | - | 0 | recommendationservice |
| 7bbfa6 | `no_metric` | recommendationservice | 2 | 3/3 | 0/3 | absent_source 3 | 0 | - |
| 99f095 | `metric` | currencyservice | 10 | 3/3 | 3/3 | - | 0 | currencyservice |
| 99f095 | `no_metric` | currencyservice | 10 | 3/3 | 0/3 | absent_source 3 | 0 | - |
| ad1c27 | `metric` | currencyservice | 10 | 2/2 | 2/2 | - | 0 | currencyservice |
| ad1c27 | `no_metric` | currencyservice | 10 | 3/3 | 0/3 | absent_source 3 | 0 | - |
| de6a50 | `metric` | checkoutservice | 0 | 0/3 | 0/3 | - | 0 | - |
| de6a50 | `no_metric` | checkoutservice | 0 | 0/3 | 0/3 | - | 0 | - |

- `tool_match_rule_differs` bằng 0 ở mọi span (`spans.csv`): không có truy vấn nào mà tên theo luật của tool khác tên theo scorer.
- Nhánh `metric` có 150 span có bảng, đúng bằng 150 span `queried_gt`; mọi bảng nhận được chỉ chứa khóa KPI của dịch vụ GT của case (cột `table_key_prefixes`). Nhánh `no_metric` có 170 span đã hỏi GT và 0 bảng (`spans.csv`: `queried_gt`, `metric_tables`).
- Case có `gt_span_in_trace` bằng 0 (`272a47`, `30e3c7`, `de6a50`) là các case duy nhất mà `metric` có I0 sai: I0 trùng "có span GT trong trace" ở 8 trên 8 case. Riêng `de6a50` ở `metric_no_log` I0 đúng 3/3 dù không có span GT: một span `frontendservice` mỗi run (3 run) nhận bảng GT (`runs.csv`, cột `queried_gt`, `table_received`).
- Tool metric là bản harness đã sửa (`K/metric-repair.py`) và gần như oracle GT: bảng chỉ xuất hiện khi hỏi đúng dịch vụ GT; I0 vì vậy gần như đồng nghĩa "đã hỏi GT".

## 5. T3: bảng biên I0 đến I4 và I5 theo điều kiện

`k/n` trên run hoàn tất; I1 có `n` là số run I0 đúng (I1 là `NA` khi I0 sai), I2 và I3 và I4 đọc trên mọi run hoàn tất. Run bị dừng không vào mẫu số (một run `metric`, một run `no_metric`).

| Điều kiện | Bảng | Run (hoàn tất) | I0 | I1 | I2 | I3 | I4 (R@1) | I2 lenient | I3 strict | I5 same / diff / refusal |
|---|---|---|---|---|---|---|---|---|---|---|
| `metric` | bảng chính (bỏ 99f095) | 21 (20) | 11/20 | 11/11 | 3/20 | 11/20 | 8/20 | 8/20 | 8/20 | 7 / 4 / 9 |
| `metric` | cả 8 case | 24 (23) | 14/23 | 14/14 | 3/23 | 14/23 | 10/23 | 9/23 | 11/23 | 8 / 4 / 11 |
| `metric` | chỉ bỏ 2 run hiệu chỉnh | 24 (23) | 14/23 | 14/14 | 3/23 | 14/23 | 10/23 | 9/23 | 11/23 | 8 / 4 / 11 |
| `metric_no_log` | bảng chính (bỏ 99f095) | 21 (21) | 15/21 | 14/15 | 4/21 | 12/21 | 10/21 | 10/21 | 9/21 | 13 / 3 / 5 |
| `metric_no_log` | cả 8 case | 24 (24) | 18/24 | 17/18 | 4/24 | 15/24 | 10/24 | 10/24 | 12/24 | 16 / 3 / 5 |
| `metric_no_log` | chỉ bỏ 2 run hiệu chỉnh | 22 (22) | 16/22 | 15/16 | 4/22 | 13/22 | 10/22 | 10/22 | 10/22 | 14 / 3 / 5 |
| `no_metric` | bảng chính (bỏ 99f095) | 21 (20) | 0/20 | 0/0 | 0/20 | 0/20 | 4/20 | 3/20 | 0/20 | 5 / 0 / 15 |
| `no_metric` | cả 8 case | 24 (23) | 0/23 | 0/0 | 0/23 | 0/23 | 5/23 | 4/23 | 0/23 | 7 / 0 / 16 |
| `no_metric` | chỉ bỏ 2 run hiệu chỉnh | 24 (23) | 0/23 | 0/0 | 0/23 | 0/23 | 5/23 | 4/23 | 0/23 | 7 / 0 / 16 |

- `no_metric`: I0 bằng 0 theo thiết kế (nguồn metric bị gỡ), I1 không có mẫu số (`0/0`).
- `I2_lenient` và `I3_strict` là độ nhạy, không phải nhãn chính (codebook mục 4).
- Tỉ lệ `saturated` (đúng ở mọi run `Ev`, trên cả 72 run, `funnel.csv`):

| Điều kiện | Chỉ báo | true | false | NA | Dịch vụ GT có chỉ báo đúng | `saturated` |
|---|---|---|---|---|---|---|
| `metric` | I0 | 15 | 9 | 0 | 4/4 | true |
| `metric` | I1 | 15 | 0 | 9 | 4/4 | true |
| `metric` | I2 | 3 | 20 | 1 | 2/4 | false |
| `metric` | I3 | 14 | 9 | 1 | 4/4 | true |
| `metric` | I4 | 10 | 13 | 1 | 3/4 | false |
| `metric_no_log` | I0 | 18 | 6 | 0 | 4/4 | true |
| `metric_no_log` | I1 | 17 | 1 | 6 | 4/4 | false |
| `metric_no_log` | I2 | 4 | 20 | 0 | 2/4 | false |
| `metric_no_log` | I3 | 15 | 9 | 0 | 4/4 | false |
| `metric_no_log` | I4 | 10 | 14 | 0 | 3/4 | false |
| `no_metric` | I0 | 0 | 23 | 0 | 0/4 | false |
| `no_metric` | I1 | 0 | 0 | 24 | 0/4 | false |
| `no_metric` | I2 | 0 | 23 | 1 | 0/4 | false |
| `no_metric` | I3 | 0 | 23 | 1 | 0/4 | false |
| `no_metric` | I4 | 5 | 18 | 1 | 2/4 | false |

- I0, I1, I3 bão hòa ở `metric`; I2 và I4 không bão hòa. Ở `metric_no_log` chỉ I0 bão hòa: I1 không bão hòa vì `de6a50` s28 có I1 sai, I3 không bão hòa vì cả ba run `de6a50` có I3 sai.

## 6. T4: `first_loss_linear`, `final_residual` và cờ

| Điều kiện | Bảng | `first_loss_linear` | `final_residual` | Tách I5 của `reaches_final_input_not_rank1` | `chain_weakened` / `hint_weakened` / `hit_without_evidence` |
|---|---|---|---|---|---|
| `metric` | bảng chính (bỏ 99f095) | S0 9, S2 8, preserved 3 | S0 9, none 8, reaches_final_input_not_rank1 3 | top1_equals_wrong_root_label 3 | 8 / 0 / 0 |
| `metric` | cả 8 case | S0 9, S2 11, preserved 3 | S0 9, none 10, reaches_final_input_not_rank1 4 | top1_equals_wrong_root_label 4 | 11 / 0 / 0 |
| `metric` | chỉ bỏ 2 run hiệu chỉnh | S0 9, S2 11, preserved 3 | S0 9, none 10, reaches_final_input_not_rank1 4 | top1_equals_wrong_root_label 4 | 11 / 0 / 0 |
| `metric_no_log` | bảng chính (bỏ 99f095) | S0 6, S1 1, S2 10, S3 1, preserved 3 | S0 6, S1 1, none 10, reaches_final_input_not_rank1 4 | top1_equals_wrong_root_label 4 | 10 / 2 / 0 |
| `metric_no_log` | cả 8 case | S0 6, S1 1, S2 13, S3 1, preserved 3 | S0 6, S1 1, none 10, reaches_final_input_not_rank1 7 | top1_equals_wrong_root_label 7 | 13 / 2 / 0 |
| `metric_no_log` | chỉ bỏ 2 run hiệu chỉnh | S0 6, S1 1, S2 11, S3 1, preserved 3 | S0 6, S1 1, none 10, reaches_final_input_not_rank1 5 | top1_equals_wrong_root_label 5 | 11 / 2 / 0 |
| `no_metric` | bảng chính (bỏ 99f095) | S0 20 | S0 16, none 4 | - | 0 / 0 / 4 |
| `no_metric` | cả 8 case | S0 23 | S0 18, none 5 | - | 0 / 0 / 5 |
| `no_metric` | chỉ bỏ 2 run hiệu chỉnh | S0 23 | S0 18, none 5 | - | 0 / 0 / 5 |

- **Chú thích bắt buộc về thiên lệch thứ tự** (`summary.json`, `first_loss_linear_note`): S2 đứng trước S3 là quy ước, không phải thứ tự phụ thuộc thật; khi I1 đúng mà I2 sai nhãn luôn là S2, kể cả khi run vẫn đạt R@1. S4 chỉ xuất hiện khi I0 đến I3 đều đúng. Vector biên I0 đến I5 (mục 5) là kết quả chính; `first_loss_linear` là góc nhìn phụ.
- Phần dư `reaches_final_input_not_rank1` luôn tách ra `top1_equals_wrong_root_label` (3 ở bảng chính `metric`; 4 ở `metric` 8 case và `metric` chỉ bỏ 2 run; ở `metric_no_log`: 4 bảng chính, 7 cả 8 case, 5 chỉ bỏ 2 run), không run nào là `top1_differs_from_root_label` hay `root_refusal`. Nghĩa là ở các run này tổng hợp cuối đặt đúng dịch vụ mà nhãn root nêu ở hạng 1, và nhãn root đó không phải GT.
- Cờ: `chain_weakened` (I2 sai khi I1 đúng), `hint_weakened` (I3 sai khi I1 đúng), `hit_without_evidence` (I4 đúng mà I0 sai). `hit_without_evidence` chỉ xuất hiện ở `no_metric` (4 ở bảng chính, 5 ở cả 8 case): đúng R@1 mà không có bảng metric nào ở đầu vào.
- Run đúng được báo cùng run sai: ở bảng chính `metric`, 8 run có `first_loss_linear = S2`; 5 trong số đó có `final_residual = none` (nhãn root mất GT nhưng R@1 đúng: `5f7a77` hai run, `7bbfa6` ba run) và 3 run còn lại (`29583d`) là `reaches_final_input_not_rank1`.

## 7. T5: ma trận case

Mỗi ô: R@1 trên số run hoàn tất; "xa nhất" là chỉ báo xa nhất mà một seed nào đó đạt liên tiếp từ I0 (`leading_true`, tính cả run bị dừng nếu chỉ báo dương đã thấy). Cột `no_metric` là đường cơ sở độ khó của cùng case.

| Case | GT | Span GT | `metric` | `metric_no_log` | `no_metric` (cơ sở độ khó) |
|---|---|---|---|---|---|
| 272a47 | recommendationservice | 0 | R@1 0/3; xa nhất: không qua I0 | R@1 0/3; xa nhất: không qua I0 | R@1 0/2; xa nhất: không qua I0 |
| 29583d | emailservice | 1 | R@1 0/3; xa nhất: qua I0 đến I1 | R@1 0/3; xa nhất: qua I0 đến I1 | R@1 0/3; xa nhất: không qua I0 |
| 30e3c7 | emailservice | 0 | R@1 0/3; xa nhất: không qua I0 | R@1 0/3; xa nhất: không qua I0 | R@1 0/3; xa nhất: không qua I0 |
| 5f7a77 | checkoutservice | 13 | R@1 3/3; xa nhất: qua I0 đến I4 | R@1 3/3; xa nhất: qua I0 đến I4 | R@1 1/3; xa nhất: không qua I0 |
| 7bbfa6 | recommendationservice | 2 | R@1 3/3; xa nhất: qua I0 đến I1 | R@1 3/3; xa nhất: qua I0 đến I1 | R@1 0/3; xa nhất: không qua I0 |
| 99f095 | currencyservice | 10 | R@1 2/3; xa nhất: qua I0 đến I1 | R@1 0/3; xa nhất: qua I0 đến I1 | R@1 1/3; xa nhất: không qua I0 |
| ad1c27 | currencyservice | 10 | R@1 2/2; xa nhất: qua I0 đến I4 | R@1 2/3; xa nhất: qua I0 đến I4 | R@1 3/3; xa nhất: không qua I0 |
| de6a50 | checkoutservice | 0 | R@1 0/3; xa nhất: không qua I0 | R@1 2/3; xa nhất: qua I0 đến I2 | R@1 0/3; xa nhất: không qua I0 |

- Số seed hiệu dụng: `ad1c27` `metric` có 2 trên 3 run hoàn tất (s27 dừng); `272a47` `no_metric` có 2 trên 3.
- Cùng case, hai nhánh là quỹ đạo độc lập: `5f7a77` đúng 3/3 ở `metric` và 1/3 ở `no_metric`; `7bbfa6` 3/3 và 0/3; `ad1c27` 2/2 và 3/3 (đúng ở `no_metric` mà không có bảng nào); `29583d`, `272a47`, `30e3c7`, `de6a50` bằng 0 ở `metric` (bốn case, `de6a50` đạt 2/3 ở `metric_no_log`). Tức là R@1 theo case không đơn điệu theo việc có metric.

## 8. T6: so sánh điều kiện mức case (không ghép cặp)

- Khóa (case, seed). Mọi cặp `metric`-`no_metric` và `metric`-`metric_no_log` rẽ nhánh sớm (`case-comparison.csv`, cột `pairing` ghi `independent trajectories, not paired`). Đánh số request 1-based, tính cả retry.
- `metric` với `metric_no_log`: tỉ lệ `agent_complete` giống từng byte là 1156/1249 (0,9255; từng cặp từ 0,6667 đến 0,9744); điểm phân kỳ thô ở request 3 (14 cặp) và 4 (10 cặp), luôn là `self_state_verification`. Đây là phép kiểm lặp lại về quỹ đạo, không phải đối chứng độc lập. Vòng 2 cho đúng cùng con số 1156/1249 (`-r2/summary.json`).
- `metric` với `no_metric`: giống từng byte 10/1249 (0,0080; vòng 2 là 7/1249).
  - Điểm phân kỳ thô: request 3 (14 cặp), 4 (3), 6 (6), 7 (1).
  - **Sau khi gộp câu chữ NO_KPI với NO_ROWS** (`first_request_divergence_merged`): không cặp nào phân kỳ ở request 3; điểm sớm nhất là request 4 (3 cặp), rồi 5 (4), 6 (3), 7 (5), 8 (7), 11 (1), 12 (1).
  - Cảnh báo nhiễu câu chữ: `no_metric` trả "No matching records found." còn `metric` trả "No fluctuating metrics found." khi không có KPI, nên phân kỳ thô ở request 3 lẫn hiệu ứng câu chữ; tách được cần chạy lại bằng GPU (Q9, mục 14). Con số gộp ghi nhận phần lớn phân kỳ sớm nhất nhất quán với khác biệt câu chữ, nhưng không chứng minh điều đó.
- Số request trung bình mỗi run: `metric` 83,4; `metric_no_log` 86,7; `no_metric` 114,1 (`runs.csv`, cột `requests`, cả run dừng): `no_metric` tốn nhiều request hơn, nhất quán với việc hỏi rỗng tốn thêm lượt (chưa tách được cơ chế).

## 9. T7: D1, D2, hint

- **D1** (khai báo `has_error_logs` mà log đã giao không có chữ lỗi): có 14 span khai báo `has_error_logs = true`, tất cả là `frontendservice`; 4 span là D1 (đều `metric`), 10 span là `D1_na` (đều `metric_no_log`, nguồn log đã gỡ nên rỗng do thiết kế harness). **D1 trùng với mọi khai báo `has_error_logs` có log thật**: mọi dòng log ở S1 v2 đều `severity: unknown` và không dòng nào chứa `error`, `exception`, `fail` (298146 dòng; `plans/reports/verify-261101-rclagent-evidence-loss-p4.md`), nên D1 không phân biệt có log chống lưng hay không. Chỉ phản ánh khai báo của mô hình, không phản ánh bằng chứng.
- **D2** (`is_abnormal` mà không có cờ lỗi log, không có cờ metric và không có bảng): 52 span, tập trung ở `frontendservice` (34) và `checkoutservice` (12) (`spans.csv`).
- Theo run (bảng bên dưới): D1 chỉ có ở `metric` (3 run bảng chính, đều là `29583d`; 4 run ở cả 8 case, thêm `99f095` s26) và tất cả các run D1 đều trượt R@1; D1 không có ở run đúng nào. `D1_empty_logs` (biến thể chặt) là 3 trong 4 run D1. Trong case, không có case nào có cả run D1 lẫn không D1 ở bảng chính, nên `label_mismatch_flags` không testable ở bảng chính; ở bản 8 case chỉ `99f095` (D1 trượt 1/1; không D1 trượt 0/2), 1 đơn vị.

| Bảng | Điều kiện | Run có D1 | D1 trong run trượt R@1 | D1 trong run đúng R@1 | D1_empty_logs | Run có D2 | D2 trong run trượt | D2 trong run đúng |
|---|---|---|---|---|---|---|---|---|
| bảng chính | `metric` | 3/20 | 3/12 | 0/8 | 3/20 | 8/20 | 7/12 | 1/8 |
| bảng chính | `metric_no_log` | 0/21 | 0/11 | 0/10 | 0/21 | 7/21 | 6/11 | 1/10 |
| bảng chính | `no_metric` | 0/20 | 0/16 | 0/4 | 0/20 | 6/20 | 5/16 | 1/4 |
| cả 8 case | `metric` | 4/23 | 4/13 | 0/10 | 3/23 | 8/23 | 7/13 | 1/10 |
| cả 8 case | `metric_no_log` | 0/24 | 0/14 | 0/10 | 0/24 | 7/24 | 6/14 | 1/10 |
| cả 8 case | `no_metric` | 0/23 | 0/18 | 0/5 | 0/23 | 8/23 | 7/18 | 1/5 |

- Đoạn hint (chỉ mã dựng hint của tác giả, không nói gì về hành vi của LLM hay hiệu quả của bất kỳ hướng X nào): trong 70 run hoàn tất, GT chưa bao giờ là mục duy nhất của danh sách hint (`gt_sole_entry` 0 ở mọi điều kiện); khi GT có trong hint (I3 đúng) danh sách có từ 2 đến 4 dịch vụ (ở `metric`: 2 dịch vụ ở 10 run, 3 ở 2 run, 4 ở 2 run), phần còn lại là dịch vụ không phải GT. `hint_equivalent` đúng 70/70 và 2 `NA` (run dừng): dòng hint trong prompt cuối trùng tập dựng lại.

| Điều kiện | Kích thước danh sách hint (số dịch vụ duy nhất, run hoàn tất, cả 8 case) | `gt_sole_entry` | `I3_strict` |
|---|---|---|---|
| `metric` | 0 dịch vụ: 4 run, 1 dịch vụ: 5 run, 2 dịch vụ: 10 run, 3 dịch vụ: 2 run, 4 dịch vụ: 2 run | 0/23 | 11/23 |
| `metric_no_log` | 1 dịch vụ: 9 run, 2 dịch vụ: 11 run, 3 dịch vụ: 2 run, 4 dịch vụ: 2 run | 0/24 | 12/24 |
| `no_metric` | 0 dịch vụ: 15 run, 1 dịch vụ: 8 run | 0/23 | 0/23 |


## 10. T8: phép kiểm khả thi và độ tương phản gộp

Cổng: giai đoạn k chỉ `testable` cho độ tương phản khi có ít nhất 3 case chứa cả run "mất ở k" lẫn run "giữ ở k" (codebook mục 9.1). `Ev` là run hoàn tất có I0 đúng (giai đoạn I0 tính trên mọi run hoàn tất).

| Bảng | Điều kiện | Giai đoạn | Run mất | Run giữ | Số case đủ hai nhóm | Case | Số dịch vụ GT | Khả thi |
|---|---|---|---|---|---|---|---|---|
| bảng chính | `metric` | I0 | 9 | 11 | 0 | - | 0 | not_testable |
| bảng chính | `metric` | I1 | 0 | 11 | 0 | - | 0 | not_testable |
| bảng chính | `metric` | I2 | 8 | 3 | 1 | 5f7a77 | 1 | not_testable |
| bảng chính | `metric` | I3 | 0 | 11 | 0 | - | 0 | not_testable |
| bảng chính | `metric_no_log` | I0 | 6 | 15 | 0 | - | 0 | not_testable |
| bảng chính | `metric_no_log` | I1 | 1 | 14 | 1 | de6a50 | 1 | not_testable |
| bảng chính | `metric_no_log` | I2 | 11 | 4 | 3 | 5f7a77, ad1c27, de6a50 | 2 | testable |
| bảng chính | `metric_no_log` | I3 | 3 | 12 | 0 | - | 0 | not_testable |
| bảng chính | `no_metric` | I0 | 20 | 0 | 0 | - | 0 | not_testable |
| bảng chính | `no_metric` | I1 | 0 | 0 | 0 | - | 0 | not_testable |
| bảng chính | `no_metric` | I2 | 0 | 0 | 0 | - | 0 | not_testable |
| bảng chính | `no_metric` | I3 | 0 | 0 | 0 | - | 0 | not_testable |
| cả 8 case | `metric` | I0 | 9 | 14 | 0 | - | 0 | not_testable |
| cả 8 case | `metric` | I1 | 0 | 14 | 0 | - | 0 | not_testable |
| cả 8 case | `metric` | I2 | 11 | 3 | 1 | 5f7a77 | 1 | not_testable |
| cả 8 case | `metric` | I3 | 0 | 14 | 0 | - | 0 | not_testable |
| cả 8 case | `metric_no_log` | I0 | 6 | 18 | 0 | - | 0 | not_testable |
| cả 8 case | `metric_no_log` | I1 | 1 | 17 | 1 | de6a50 | 1 | not_testable |
| cả 8 case | `metric_no_log` | I2 | 14 | 4 | 3 | 5f7a77, ad1c27, de6a50 | 2 | testable |
| cả 8 case | `metric_no_log` | I3 | 3 | 15 | 0 | - | 0 | not_testable |
| cả 8 case | `no_metric` | I0 | 23 | 0 | 0 | - | 0 | not_testable |
| cả 8 case | `no_metric` | I1 | 0 | 0 | 0 | - | 0 | not_testable |
| cả 8 case | `no_metric` | I2 | 0 | 0 | 0 | - | 0 | not_testable |
| cả 8 case | `no_metric` | I3 | 0 | 0 | 0 | - | 0 | not_testable |

- Nhánh `metric` (điều kiện chính): **không giai đoạn nào testable** cho độ tương phản trong case, ở cả bảng chính và bản 8 case. Đó là điều đã biết trước khi chạy (codebook mục 9.1). `summary.json` (`feasibility`, bản 8 case) khớp bảng này.
- Ngoại lệ duy nhất: `metric_no_log` ở I2, 3 case (`5f7a77`, `ad1c27`, `de6a50`) từ 2 dịch vụ GT. Độ tương phản gộp phân tầng theo case (hiệu tỉ lệ trượt R@1 giữa run mất I2 và run giữ I2, trọng số theo số run `Ev`, thuần mô tả): `5f7a77` 0,00 (0/2 trượt so với 0/1), `ad1c27` 1,00 (1/1 so với 0/2), `de6a50` 0,50 (1/2 so với 0/1); trung bình có trọng số 0,50 trên 3 case. Bảng chính và bản 8 case cho cùng giá trị. Hạn chế: `metric_no_log` dùng lại 92,5 phần trăm quỹ đạo của `metric` nên không độc lập với `metric`; chỉ hai dịch vụ GT; `de6a50` là case không có span GT mà vẫn nhận bảng GT; nhãn root đi vào prompt tổng hợp cuối nên I2 và I4 không độc lập. Không suy ra nhân quả.
- Độ tương phản `metric` ở I2 (chỉ `5f7a77`): 0,00, trùng bảng "đã biết trước".

## 11. T9: kiểm toán và nhật ký deviation

- Kiểm toán đọc mù (`plans/reports/audit-261101-rclagent-evidence-loss-blind.md`): 12 run, 6 case; **không bất đồng nhãn nào** giữa người đọc và luật (I0 12/12, I1 12/12, I2 7/7, I3 7/7, hạng 12/12 sau khi đổi hệ đếm, `first_loss_linear` 12/12); 6 điểm cách hiểu hoặc phạm vi (B1 đến B6). Sếp phân xử ngày 2026-11-01: chấp nhận toàn bộ đề xuất lớp, `rule_error` 0, `analyzer_error` 0, nên **không mở deviation** và không chạy lại; B4: S4 giữ theo R@1; B5: trong dữ liệu này chỉ R@1 phân biệt được, vì top-10 chứa gần như mọi dịch vụ của ứng dụng.
- Giới hạn bắt buộc của kiểm toán: người đọc là **một LLM-coder cùng họ model với tác giả codebook** nên đồng thuận cao có thể giả; kiểm toán chỉ kiểm I0 đến I3 và `first_loss_linear`, **không kiểm `misattributed`, I5 hay `final_residual`**, nên báo cáo này không trích kiểm toán làm bằng chứng cho ba mục đó. Phần tách `S0_gt_span_absent` và `S0_empty_result` được kiểm máy độc lập ở phase chạy chính thức (số span GT theo case khớp); I5 và `final_residual` là phép so chuỗi có test và khớp 62/62 giữa hai corpus.
- Nhật ký deviation (`plans/261031-2311-rclagent-evidence-loss-analysis/deviation-log.md`): không có deviation về luật hay code. Có một erratum chữ (xem mục 13).

## 12. Kết cục theo luật đóng băng

Nhãn là mô tả theo trace, không phải nhân quả. Luật không có ngưỡng đạt hay trượt (codebook mục 9).

### 12.1 Bước khả thi: n theo từng câu (cổng n >= 3 trên tập sau khi bỏ `99f095`)

| Câu | n (đơn vị có dữ liệu) | Khả thi |
|---|---|---|
| `S0_gt_span_absent` | 4 (cả bốn dịch vụ GT có run `metric` hoàn tất) | `testable` |
| `S0_gt_span_present_not_queried` | 4 (mỗi dịch vụ GT có một case có span GT) | `testable` |
| `S2_root_label_lost_hit_kept` | 3 (checkoutservice, emailservice, recommendationservice; currencyservice không có run I1 đúng và I2 sai) | `testable` ở đúng ngưỡng |
| `S4_inputs_present_not_rank1` | 4 | `testable` |
| `label_mismatch_flags` | 0 (không case nào có cả run D1 lẫn không D1) | `not_testable` |
| `no_stage_implicated` | không áp dụng cổng n | đánh giá ở 12.3 |

`S2_root_label_lost_hit_kept` sát ngưỡng: bỏ bất kỳ một dịch vụ GT nào trong ba dịch vụ có dữ liệu ra khỏi bảng chính thì n tụt xuống 2 và câu thành `not_testable` (`outcome-sentences.csv`, các dòng "main bo dich vu GT").

### 12.2 `k/n`, xếp hạng theo (k/n, k), n luôn hiển thị

Bảng chính (điều kiện `metric`, bỏ `99f095`):

| Câu | n | k | k/n | Đơn vị đỡ | Đơn vị không đỡ | Run đỡ trên run có dữ liệu, từng đơn vị |
|---|---|---|---|---|---|---|
| `S0_gt_span_absent` | 4 | 3 | 3/4 | checkoutservice, emailservice, recommendationservice | currencyservice | checkoutservice=3/6; currencyservice=0/2; emailservice=3/6; recommendationservice=3/6 |
| `S0_gt_span_present_not_queried` | 4 | 0 | 0/4 | - | checkoutservice, currencyservice, emailservice, recommendationservice | checkoutservice=0/3; currencyservice=0/2; emailservice=0/3; recommendationservice=0/3 |
| `S2_root_label_lost_hit_kept` | 3 | 2 | 2/3 | checkoutservice, recommendationservice | emailservice | checkoutservice=2/2; emailservice=0/3; recommendationservice=3/3 |
| `S4_inputs_present_not_rank1` | 4 | 1 | 1/4 | emailservice | checkoutservice, currencyservice, recommendationservice | checkoutservice=0/3; currencyservice=0/2; emailservice=3/3; recommendationservice=0/3 |
| `label_mismatch_flags` | 0 | 0 | `not_testable` | - | - | - |


Thứ hạng mô tả (chỉ các câu `testable` có `k >= 1`):

1. `S0_gt_span_absent`: 3 trên n = 4.
2. `S2_root_label_lost_hit_kept`: 2 trên n = 3.
3. `S4_inputs_present_not_rank1`: 1 trên n = 4.

Không xếp hạng: `S0_gt_span_present_not_queried` (0 trên 4, `k = 0`), `label_mismatch_flags` (`not_testable`, n = 0). Không có hòa ở bảng chính. Lưu ý: `first_loss_linear` không có nhãn S4 nào (mục 6) vì các run `29583d` mang nhãn S2 theo thứ tự quy ước; câu `S4_inputs_present_not_rank1` dùng vị từ riêng (I1 và I3 đúng, I4 sai, không đọc I2) nên vẫn đếm `29583d`. Bản độ nhạy:

| Câu | n | k | k/n | Đơn vị đỡ | Đơn vị không đỡ | Run đỡ trên run có dữ liệu, từng đơn vị |
|---|---|---|---|---|---|---|
| `S0_gt_span_absent` | 4 | 3 | 3/4 | checkoutservice, emailservice, recommendationservice | currencyservice | checkoutservice=3/6; currencyservice=0/5; emailservice=3/6; recommendationservice=3/6 |
| `S0_gt_span_present_not_queried` | 4 | 0 | 0/4 | - | checkoutservice, currencyservice, emailservice, recommendationservice | checkoutservice=0/3; currencyservice=0/5; emailservice=0/3; recommendationservice=0/3 |
| `S2_root_label_lost_hit_kept` | 4 | 3 | 3/4 | checkoutservice, currencyservice, recommendationservice | emailservice | checkoutservice=2/2; currencyservice=2/3; emailservice=0/3; recommendationservice=3/3 |
| `S4_inputs_present_not_rank1` | 4 | 2 | 2/4 | currencyservice, emailservice | checkoutservice, recommendationservice | checkoutservice=0/3; currencyservice=1/5; emailservice=3/3; recommendationservice=0/3 |
| `label_mismatch_flags` | 1 | 1 | `not_testable` | currencyservice | - | currencyservice=case 99f095: D1 trượt 1/1; không D1 trượt 0/2 |


Bản 8 case (và bản "chỉ bỏ 2 run hiệu chỉnh", trùng vì hai run đó thuộc `metric_no_log`): `S0_gt_span_absent` 3/4 và `S2_root_label_lost_hit_kept` 3/4 **bằng cả `k/n` lẫn `k`**, ghi `ngang nhau` (không thêm luật phá hòa), rồi `S4_inputs_present_not_rank1` 2/4. Vòng 2 (`-r2/runs.csv`) cho cùng kết quả ở cả hai bản. Các độ nhạy khác (bỏ từng dịch vụ GT, bỏ run cắt cụt hỏng nhất, `I2_lenient`) nằm ở mục 12.4.

### 12.3 `no_stage_implicated` và phần dữ liệu không cho phép kết luận

- `no_stage_implicated` đúng khi mọi câu là `not_testable` hoặc có `k = 0`. Ở bảng chính có ba câu `testable` với `k >= 1`, nên **điều kiện này không thỏa**; vị từ "có ít nhất một run" dễ thỏa nên câu này khó đạt, và bảng "run đỡ trên run có dữ liệu" ở trên (ví dụ `S4` của emailservice 3/3 nhưng của ba dịch vụ còn lại 0) cho thấy vị từ không che tỉ lệ.
- Dữ liệu **không cho phép** kết luận: (a) giai đoạn nào là nơi mất bằng chứng theo nghĩa nhân quả (độ tương phản trong case không testable ở `metric`); (b) mô hình "chọn không hỏi GT" (`S0_gt_span_absent` lẫn hoàn toàn với hình dạng trace, `S0_gt_span_present_not_queried` là 0/4); (c) hiệu quả của bất kỳ can thiệp nào; (d) vai trò của log (log không có bằng chứng GT nào, nên `label_mismatch_flags` chỉ phản ánh khai báo của mô hình); (e) cơ chế ở S1 và S3: I1 đúng 11/11 và I3 đúng 11/11 trên `Ev` bảng chính nên không có run mất ở hai giai đoạn này trong nhánh `metric` (ở 8 case, I3 đúng 14/14 `Ev` nên không run `metric` nào mất GT ở S3, không hơn; `frontendservice` là dịch vụ duy nhất khai báo `has_error_logs`, mục 9; chỉ `metric_no_log` có 1 run mất I1 và 3 run mất I3, thuộc `de6a50`, nhãn của nó dựa trên khóa gán carrier mà kiểm toán không kiểm).
- Chỉ R@1 phân biệt được ở S4: danh sách top-10 chứa gần như mọi dịch vụ của ứng dụng nên "GT không ở top-10" gần như không xảy ra: 6 trên 70 run hoàn tất, cả sáu thuộc `de6a50` (case không có span GT; `runs.csv`, cột `rank` bằng -1).

### 12.4 Độ nhạy (một đoạn)

Nguồn: `outcome-sentences.csv`, `runs.csv`, `-r2/runs.csv`.

| Biến thể | Thứ hạng câu `testable` có `k >= 1` (k/n; khác cột `n` thì không so được bằng k thô) |
|---|---|
| Bảng chính (bỏ `99f095`) | `S0_gt_span_absent` 3/4 > `S2_root_label_lost_hit_kept` 2/3 > `S4_inputs_present_not_rank1` 1/4 |
| Cả 8 case (= chỉ bỏ 2 run hiệu chỉnh) | `S0_gt_span_absent` 3/4 **ngang nhau** `S2_root_label_lost_hit_kept` 3/4 > `S4_inputs_present_not_rank1` 2/4 |
| Vòng 2, bảng chính | `S0_gt_span_absent` 3/4 > `S2_root_label_lost_hit_kept` 2/3 > `S4_inputs_present_not_rank1` 1/4 |
| Vòng 2, cả 8 case | `S0_gt_span_absent` 3/4 **ngang nhau** `S2_root_label_lost_hit_kept` 3/4 > `S4_inputs_present_not_rank1` 2/4 |
| Bảng chính, bỏ dịch vụ GT checkoutservice | `S0_gt_span_absent` 2/3 > `S4_inputs_present_not_rank1` 1/3 |
| Bảng chính, bỏ dịch vụ GT currencyservice | `S0_gt_span_absent` 3/3 > `S2_root_label_lost_hit_kept` 2/3 > `S4_inputs_present_not_rank1` 1/3 |
| Bảng chính, bỏ dịch vụ GT emailservice | `S0_gt_span_absent` 2/3 |
| Bảng chính, bỏ dịch vụ GT recommendationservice | `S0_gt_span_absent` 2/3 > `S4_inputs_present_not_rank1` 1/3 |
| 8 case, bỏ dịch vụ GT checkoutservice | `S0_gt_span_absent` 2/3 **ngang nhau** `S2_root_label_lost_hit_kept` 2/3 **ngang nhau** `S4_inputs_present_not_rank1` 2/3 |
| 8 case, bỏ dịch vụ GT currencyservice | `S0_gt_span_absent` 3/3 > `S2_root_label_lost_hit_kept` 2/3 > `S4_inputs_present_not_rank1` 1/3 |
| 8 case, bỏ dịch vụ GT emailservice | `S2_root_label_lost_hit_kept` 3/3 > `S0_gt_span_absent` 2/3 > `S4_inputs_present_not_rank1` 1/3 |
| 8 case, bỏ dịch vụ GT recommendationservice | `S0_gt_span_absent` 2/3 **ngang nhau** `S2_root_label_lost_hit_kept` 2/3 **ngang nhau** `S4_inputs_present_not_rank1` 2/3 |
| Bảng chính, run `ad1c27` s27 gán I2 sai, I3 đúng, I4 sai | `S0_gt_span_absent` 3/4 > `S2_root_label_lost_hit_kept` 2/4 **ngang nhau** `S4_inputs_present_not_rank1` 2/4 |
| Bảng chính, run `ad1c27` s27 gán I2 sai, I3 đúng, I4 đúng | `S0_gt_span_absent` 3/4 **ngang nhau** `S2_root_label_lost_hit_kept` 3/4 > `S4_inputs_present_not_rank1` 1/4 |

Khi bỏ một dịch vụ GT khỏi bảng chính, `S2_root_label_lost_hit_kept` mất tính `testable` ở ba trong bốn lần bỏ (chỉ bỏ currencyservice giữ n = 3); `S0_gt_span_absent` đứng đầu hoặc ngang đầu ở mọi biến thể trên, trừ một ngoại lệ: bỏ emailservice khỏi bản 8 case thì `S2_root_label_lost_hit_kept` 3/3 đứng trên `S0_gt_span_absent` 2/3 (n chỉ còn 3 đơn vị).

- `I2_lenient` (reason của root nhắc tên GT) cho 8/11 run `Ev` bảng chính so với I2 chặt 3/11: kết luận về nhãn root phụ thuộc định nghĩa; mục P3 bên dưới báo cả hai.
- `I3_strict` (hint có không quá 2 dịch vụ): 8/20 ở `metric` bảng chính so với I3 11/20.
- Vòng 2 là phép kiểm tất định, không độc lập: 62/62 cặp cùng hoàn tất trùng ở mọi cột so (`-r2-vs-s1-v2/summary.json`, `both_completed_pairs_with_any_difference` rỗng).
- Luật sửa so luật đóng băng: không có luật sửa (không deviation), nên không có kết cục nào đổi.

## 13. Hướng X ứng viên cho RQ (c)

Định nghĩa "không sửa upstream": wrapper phía harness (như `adapt_payload`, `get_tool` trong `K/smoke-worker.py`) hoặc prompt override nằm ngoài `upstream/`. **Kế hoạch dừng ở "khuyến nghị ứng viên, hiệu quả chưa đo"**: mọi đo hiệu quả cần chạy model (RQ c). Không đề xuất replay CPU bằng model lượng tử hóa. Các hướng là ứng viên theo thứ tự câu kết cục, không phải đích.

| Hạng | Hướng X | Giai đoạn | Câu kết cục và số | Dữ liệu nhất quán với hướng | Thực hiện được không sửa upstream? | Điều kiện kiểm (cần can thiệp có model) |
|---|---|---|---|---|---|---|
| 1 | Đưa danh sách dịch vụ đã biết vào truy vấn metric, hoặc wrapper tự truy vấn bảng cho mọi dịch vụ đã biết | S0 | `S0_gt_span_absent` 3/4 | Ở 3 case không có span GT, run `metric` không bao giờ hỏi GT (S0), trong khi mọi case có span GT đều I0 đúng | Đạt: wrapper `get_tool` hoặc thêm bước ở harness | Chạy lại ba case không có span GT (`272a47`, `30e3c7`, `de6a50`) với truy vấn bổ sung và đo R@1; phải nêu rõ làm tool oracle GT bớt ngầm; câu này lẫn với hình dạng trace |
| 2 | Đưa tín hiệu metric vào luật consolidation, hoặc giảm vai trò chuỗi consolidation | S2 | `S2_root_label_lost_hit_kept` 2/3 | Ở `5f7a77` và `7bbfa6` nhãn root mất GT nhưng R@1 vẫn đúng | Cần override bên ngoài (viết lại payload consolidate); không đạt nếu sửa `coordinator.py` | Chạy với override prompt consolidate; không có dữ liệu về lợi ích; ở các run đó GT vẫn hạng 1 |
| 3 | Hậu xử lý hoặc xếp lại hạng ở tổng hợp cuối | S4 | `S4_inputs_present_not_rank1` 1/4 | Chỉ `29583d` (emailservice): cả ba run có I1 và I3 đúng mà GT không đứng hạng 0 (R@1) ở cả 3 run (cột `rank` bằng 1, tức vị trí thứ hai, `runs.csv`) | Đạt: xử lý `result.json` ở harness, tránh dùng nhãn GT | Chạy lại `29583d` với bước xếp lại hạng; một case, ba seed gần như nhân bản |
| không hạng | Kiểm chứng hoặc sửa khai báo `has_error_logs`; sửa nhãn hint cho span chỉ trễ | S1, S3 | `label_mismatch_flags` `not_testable` (n = 0 bảng chính; n = 1 ở 8 case) | **Không có dữ liệu nhất quán** để xếp hạng: D1 chỉ ở `29583d` (bảng chính), trùng mọi khai báo `has_error_logs` có log thật, không có case so được trong case | Đạt nếu viết lại `payload.messages` ở `adapt_payload` (override bên ngoài); sửa luật chuỗi trong `coordinator.py` thì không đạt | Cần trước hết một case có cả run D1 lẫn không D1; sau đó chạy với override |
| không hạng | Hướng nhắm S0 cho case có span GT mà không được hỏi | S0 | `S0_gt_span_present_not_queried` 0/4 | Không có dữ liệu nhất quán (`k = 0`): cả năm case có span GT đều I0 đúng ở `metric` | Không cần | - |

CSV: `K/runtime/analysis-evidence-loss-decision/x-direction-ranking.csv`.

## 14. Dự đoán P1 đến P5

Các kết cục dưới đây đã được phơi nhiễm trước khi đóng băng (codebook mục 10 và 12; bảng "kết cục đã biết trước" ở mục 2): chúng không phải dự đoán thực nghiệm theo nghĩa kiểm định mù. Cột "bác khi" là nguyên văn từ codebook mục 10. CSV: `predictions.csv`.

| Mã | Dự đoán | Bác khi (nguyên văn) | Số (nguồn) | Kết cục | Phơi nhiễm |
|---|---|---|---|---|---|
| P1 | Ở `no_metric`, mọi run có I0 sai; mọi lượt hỏi metric tới GT có `empty_reason = absent_source` | "có run `table_received` đúng, hoặc `empty_reason` khác `absent_source` ở lượt hỏi GT" | I0 sai ở 20/20 run hoàn tất bảng chính (23/23 ở 8 case); `table_received` sai ở 21/21 run bảng chính (24/24 ở 8 case); 12/12 run bảng chính (15/15 ở 8 case) có hỏi GT đều chỉ có `absent_source` (`runs.csv`) | supported (không bị bác) | Hằng đẳng theo thiết kế harness (nguồn metric bị gỡ), không phải dự đoán thực nghiệm |
| P2 | Ở `metric`, hơn một nửa số span mang bảng GT được tự đánh `is_abnormal = true` | "chừng một nửa hoặc ít hơn" | Span mang bảng chứa khóa GT, run hoàn tất bảng chính: 88/89 (8 case: 148/149); span của dịch vụ GT trong trace: 62/68 (8 case: 92/98) (`spans.csv`) | supported | Scout đã thấy 92/98 [scout]: mô tả có phơi nhiễm |
| P3 | Nhãn root nêu GT ở dưới nửa số run `Ev` | "từ nửa trở lên" | I2 đúng 3/11 `Ev` bảng chính (3/14 ở 8 case). **Độ nhạy: `I2_lenient` 8/11 (9/14), từ nửa trở lên** | supported theo I2 đã đóng băng (3/11, dưới nửa); **bị bác nếu đọc theo `I2_lenient` (8/11, từ nửa trở lên)**, nên phụ thuộc định nghĩa | Đã thấy 3/14 [scout, reviewer]: mô tả có phơi nhiễm |
| P4 | Các run trượt R@1 ở nhánh có metric có D1 nhiều hơn các run đúng | "tỉ lệ D1 của run trượt không lớn hơn run đúng" | `metric` bảng chính, hoàn tất: D1 3/12 run trượt so với 0/8 run đúng (trên `Ev`: 3/3 so với 0/8; 8 case: 4/13 so với 0/10) | supported (hẹp: cả ba run D1 thuộc `29583d`, một case, ba seed gần như nhân bản; trong case không testable) | Khám phá có gốc từ scout; D1 trùng mọi khai báo `has_error_logs` có log thật nên gần hằng đẳng. Số scout của codebook (mục 10 và 12: 11/11 run trượt mang khai báo `has_error_logs`, 18/18 run đúng không) đếm khai báo; D1 theo codebook loại `D1_na`, nên hai số đếm khác định nghĩa và không nối được với nhau |
| P5 | Một phần run đúng R@1 ở `no_metric` là `hit_without_evidence` | "không run nào" | 4/20 run hoàn tất bảng chính đúng R@1, cả 4 là `hit_without_evidence` (8 case: 5/23, cả 5); theo case: `ad1c27` 3/3, `5f7a77` 1/3 (cộng `99f095` 1/3 ở 8 case) | supported | Đã thấy `ad1c27` 3/3 [scout]; gần hằng đẳng với P1 (I0 luôn sai ở `no_metric`) |

Không dự đoán nào thuộc loại "refuted" hay "not testable" theo định nghĩa đóng băng. Phần "supported" của P3 là chỗ nhạy nhất: đọc "nhãn root nêu GT" theo nghĩa rộng (lý do của root nhắc tên GT) thì chiều ngược lại.

## 15. Các thứ riêng cần ghi

### 15.1 Cắt cụt `H_cap` (8 run `no_metric` ở vòng 2)

Cả tám run đều `no_metric` ở vòng 2 và là dữ liệu bị cắt cụt, không phải mẫu hoàn tất (`-r2/runs.csv`, `harness_class` `H_cap`, I0 `NA_censored`); ở S1 v2 chính tám run đó hoàn tất (`-r2-vs-s1-v2/summary.json`, nhóm `s1v2_completed_r2_censored`: 8):

| Case, seed | Số request lúc dừng |
|---|---|
| `272a47` s28 | 11 |
| `30e3c7` s26 | 10 |
| `30e3c7` s28 | 10 |
| `5f7a77` s26 | 160 |
| `5f7a77` s27 | 160 |
| `5f7a77` s28 | 159 |
| `7bbfa6` s28 | 25 |
| `99f095` s28 | 12 |

Vì I0 sai ở mọi run `no_metric` (`table_received` sai 24/24 ở S1 v2) nên tám run bị cắt không đổi nhãn I0; chúng chỉ làm đường cơ sở R@1 `no_metric` ở vòng 2 là 4/15 thay vì 5/23 của S1 v2. Không nhãn nào của bảng chính dùng vòng 2.

### 15.2 NO_ROWS và dấu thời gian

- Mỗi điều kiện `metric` và `metric_no_log` có đúng 8 truy vấn (span) nhận phản hồi NO_ROWS cho `productcatalogservice`, ở cả S1 v2 và vòng 2 (`spans.csv`: `metric_empty_reasons`, `cmdb_id`): `30e3c7` 3, `5f7a77` 3, `de6a50` 2 (hai seed). Thêm 54 truy vấn NO_ROWS cho `frontendservice` mỗi điều kiện, có dấu thời gian đúng (`metric_query_ts_offset_s` bằng 0; vấn đề tên metric `frontend`, không phải dấu thời gian).
- Cột `metric_query_ts_offset_s` của 8 truy vấn này là -300000000 giây ở `30e3c7` và `5f7a77` (6 truy vấn mỗi điều kiện) và -100000000 giây ở `de6a50` (2): mô hình gõ dấu thời gian mili giây 13 chữ số (codebook mục 1.2) với hai chữ số đầu là 14 hoặc 16 thay vì 17, nên cửa sổ truy vấn không chạm dữ liệu. Kiểm độc lập trên `metrics.csv` của case (cửa sổ ±1200 giây theo `tool_server.py`): 10087, 8646 và 10087 dòng khớp tên dịch vụ tại dấu thời gian của span, 0 dòng tại dấu thời gian mô hình gõ (`plans/reports/verify-261101-rclagent-evidence-loss-p4.md`). Chữ NO_KPI tại dấu thời gian của span chỉ được xác nhận gián tiếp (có dòng trong cửa sổ thì không thể ra NO_ROWS); chưa chạy lại tool để thấy chữ đó [UNVERIFIED].
- Cả 8 truy vấn đều ở dịch vụ không phải GT (GT của ba case là emailservice, checkoutservice, checkoutservice), nên không nhãn I0 hay `S0_empty_result` nào bị ảnh hưởng.

### 15.3 Erratum `de6a50`

Codebook v1 mục 4 (đoạn I1) viết `de6a50` `metric_no_log` s26 đến s28 có I1 đúng và I3 sai. Sự kiện thô: s28 có carrier duy nhất là span `frontendservice` với `is_abnormal=false`, nên I1 sai. Nhãn analyzer (đúng): s26 `S3`, s27 `S2`, s28 `S1`; vòng 2 giống hệt. Codebook không sửa, hash không đổi, không nhãn nào đổi (`deviation-log.md`, Erratum 1). Báo cáo này dùng nhãn của analyzer.

## 16. Hạn chế

- n = 8 case, 4 dịch vụ GT, mỗi dịch vụ hai case; 3 seed là bản nhân bản gần như xác định (mô hình xác định theo prompt và seed), nên số run lớn hơn số đơn vị độc lập nhiều lần. Mọi tỉ lệ là mô tả.
- Kết cục đã **phơi nhiễm** trước khi đóng băng (mục 2): đo này là tính lại tất định theo luật cố định, không phải kiểm định mù và không phải khám phá mới. Hash codebook chỉ đóng băng cục bộ, không có thứ tự thời gian độc lập.
- Kiểm toán chỉ có **một LLM-coder cùng họ model với tác giả codebook** (đồng thuận cao có thể giả), mẫu 12 run, 6 case, 5 run S0 chỉ kiểm được C1; người đọc có thể đoán GT từ tên dịch vụ trong dữ liệu đo (codebook mục 12.8); **không phủ `misattributed`, I5 và `final_residual`**; C5 chỉ đo việc áp luật. Báo cáo kiểm toán đã bày nhãn luật cạnh form đọc.
- Run cắt cụt: 2 run dừng ở S1 v2 (`H_parse`, mục 3) và 8 run `H_cap` ở vòng 2 (mục 15.1); độ nhạy cho run `metric` bị dừng nằm ở mục 3.
- **Top-10 không phân biệt**: danh sách `root_causes` có 10 phần tử và gần như là toàn bộ dịch vụ của ứng dụng, nên chỉ R@1 phân biệt được ở S4 và hạng cuối; R@3 và "GT trong top-10" không mang thông tin.
- Hiệu ứng câu chữ NO_KPI với NO_ROWS **chưa được tách** (Q9): so sánh `metric` với `no_metric` lẫn câu chữ; cần chạy lại bằng GPU.
- Tool metric là bản harness đã sửa và gần như oracle GT (I0 gần như đồng nghĩa "đã hỏi GT"); `S0_gt_span_absent` lẫn hoàn toàn với hình dạng trace.
- Log không chứa bằng chứng nào về GT (mọi dòng `severity: unknown`), nên mọi so sánh liên quan log chỉ phản ánh khai báo của mô hình.
- Không có replay LLM nào: cột hint chỉ mô tả đầu ra của mã tác giả, hiệu quả của mọi hướng X chưa đo.
- Nhãn S1 đến S4 phụ thuộc quy ước thứ tự (S2 trước S3); vector biên là kết quả chính. I3 phụ thuộc I1 (cùng cờ self-state gán theo `cmdb_id` của span carrier).
- Độ nhạy: `S2_root_label_lost_hit_kept` chỉ có n = 3 ở bảng chính, mất một đơn vị là `not_testable`; kết quả đổi thứ hạng (hòa) khi thêm `99f095`.
- Định vị tài liệu là "không tìm thấy" chứ không khẳng định "chưa ai làm"; trích dẫn chưa xác minh [UNVERIFIED].
- Báo cáo không chứa hình; nếu sếp muốn hình, dựng một Artifact tĩnh từ `runs.csv` (ngoài phạm vi kế hoạch).

## 17. Việc không làm, cần quyết định của sếp

1. Replay một giai đoạn LLM với input oracle hoặc input `metric` (cần GPU Kaggle cùng model và kernel để so được với corpus). Cần cho mọi đo hiệu quả của hướng X (RQ c).
2. Chạy lại `no_metric` với câu NO_KPI để tách hiệu ứng câu chữ (cần GPU; Q9).
3. Q7: có commit điểm đóng băng không (mặc định chỉ hash cục bộ).
4. Có cần một lượt đọc thứ hai, hoặc một người đọc khác họ model, không (mặc định một coder).
5. Có muốn một hình tĩnh (Artifact) từ `runs.csv` không.

## 18. Tái lập

- Python: `K/runtime/harness-env/Scripts/python.exe -X utf8`. Analyzer chạy trên `rclagent-smoke-results.zip` của gói A và B (S1 v2 và vòng 2); lệnh và đối số đã ghi ở báo cáo `plans/reports/analysis-261101-0431-rclagent-evidence-loss-recompute-vs-scout.md`; 124 test của `K/test-analyze-evidence-loss.py` đạt (`verify-261101-rclagent-evidence-loss-p4.md`).
- Bảng biên, nhãn và cờ: đọc trực tiếp `runs.csv` (lọc `completed == true`, bỏ case `99f095` cho bảng chính). Câu kết cục: áp vị từ của codebook mục 9.3 lên `runs.csv`; kết quả ở `K/runtime/analysis-evidence-loss-decision/outcome-sentences.csv` (kèm các dòng độ nhạy). Ba CSV quyết định dựng lại bằng `K/decide-evidence-loss-outcomes.py` (có theo dõi, đọc `runs.csv` và `spans.csv` của analyzer; `K/runtime/harness-env/Scripts/python.exe -X utf8 decide-evidence-loss-outcomes.py`, đầu ra mặc định ở `K/runtime/analysis-evidence-loss-decision/`); `K/test-decide-evidence-loss-outcomes.py` kiểm từng vị từ và so từng byte ba CSV dựng lại với file đã lưu. Script không phải analyzer đóng băng và không nằm trong biên nhận đóng băng. Bản dựng bằng script thay một chỗ của bản tay: ở P1, số `table_received` sai của bảng chính ghi 21/21 (24/24 ở 8 case), không còn ghi số 8 case ở ô bảng chính.
- Trạng thái git: không commit, không push.

## Phụ lục: số, file nguồn, cột

| Số trong báo cáo | File | Cột hoặc khóa |
|---|---|---|
| Bảng biên I0 đến I5, `I2_lenient`, `I3_strict` | `analysis-evidence-loss-s1-v2/runs.csv` | `I0..I4`, `I5`, `I2_lenient`, `I3_strict`, `completed`, `case`, `condition` |
| Tỉ lệ `saturated`, run đúng ở mọi `Ev` | `analysis-evidence-loss-s1-v2/funnel.csv` | `saturated`, `true`, `false`, `NA` |
| `first_loss_linear`, `final_residual` và tách, cờ | `runs.csv` | `first_loss_linear`, `final_residual`, `final_residual_split`, `chain_weakened`, `hint_weakened`, `hit_without_evidence` |
| Ma trận case, R@1 `no_metric` cơ sở | `runs.csv` (và `cases.csv`) | `I4`, `leading_true`, `rank` |
| T2: truy vấn GT, bảng, `empty_reason`, `tool_match_rule_differs` | `runs.csv`, `spans.csv` | `queried_gt`, `table_received`, `empty_reason_set`, `table_key_prefixes`, `metric_tables`, `tool_match_rule_differs` |
| Điểm phân kỳ, giống từng byte | `case-comparison.csv`, `summary.json` | `first_request_divergence`, `first_request_divergence_merged`, `agent_complete_same_bytes`, `condition_comparison` |
| D1, D2, `D1_na`, hint | `spans.csv`, `runs.csv` | `D1`, `D1_na`, `D2`, `D1_empty_logs`, `self_has_error_logs`, `hint_list_size`, `gt_sole_entry`, `hint_equivalent` |
| Khả thi, độ tương phản | `runs.csv`; `summary.json` | `feasibility` (bản 8 case) |
| Câu kết cục, hạng, độ nhạy | `analysis-evidence-loss-decision/outcome-sentences.csv` | tất cả cột |
| P1 đến P5 | `predictions.csv`; `runs.csv`, `spans.csv` | xem cột nguồn trong CSV |
| Hạng X | `x-direction-ranking.csv` | tất cả cột |
| `H_cap`, `NO_ROWS` | `analysis-evidence-loss-r2/runs.csv`, `-r2-vs-s1-v2/summary.json`, `spans.csv` | `harness_class`, `requests`, `metric_empty_reasons`, `metric_query_ts_offset_s` |
| Kiểm toán | `plans/reports/audit-261101-rclagent-evidence-loss-blind.md` | mục 3, 4, 8 |
| Erratum | `plans/261031-2311-rclagent-evidence-loss-analysis/deviation-log.md` | Erratum 1 |

## Quyết định của sếp sau báo cáo

Sếp chốt ngày 2026-11-01, sau phase 8 (theo đề xuất của agent):

1. Q7: commit ngay lên nhánh `feat/rclagent-evidence-loss-analysis`, cùng toàn bộ kết quả. Commit chỉ chứng minh nội dung, không chứng minh thứ tự: nhãn đã sinh ra sau khi đóng băng, nên báo cáo vẫn ghi "đóng băng cục bộ, không có thứ tự thời gian độc lập".
2. Q9: không chạy lại; hiệu ứng câu chữ NO_KPI ghi là hạn chế.
3. Replay LLM: chưa làm; để sang RQ (c) khi thiết kế X. Nếu làm, bắt đầu ở S2 (consolidation làm mất tên GT khỏi nhãn root).
4. Người đọc thứ hai khác họ model: không; `misattributed`, I5 và `final_residual` giữ là phần chưa kiểm tay, trừ khi sau này đưa chúng vào bài như khẳng định.
5. Hai script tính câu kết cục: chuyển vào `kaggle/` (có theo dõi), đọc thẳng `runs.csv`, có test, để reviewer chạy lại được ba CSV quyết định.
6. Hình tĩnh từ `runs.csv`: không đưa ra hỏi lần này; mặc định không làm.

## Câu hỏi còn mở (trước khi sếp chốt)

- Q7: commit điểm đóng băng hay giữ hash cục bộ (ảnh hưởng đến việc báo cáo có thể nói "đóng băng có thứ tự độc lập").
- Q9: có chạy GPU để tách hiệu ứng câu chữ NO_KPI không.
- Có thực hiện replay một giai đoạn LLM (mục 17) để chuyển từ ứng viên sang đo hiệu quả, và dùng hướng nào làm thí nghiệm đầu tiên.
- Có cần người đọc thứ hai (khác họ model) cho `misattributed`, I5 và `final_residual`, các mục kiểm toán không phủ.
- Có muốn một hình tĩnh từ `runs.csv`.
- Ghi chú dòng mới: cây làm việc Windows có `core.autocrlf=true` nên analyzer, test, codebook và biên nhận hiện là CRLF; hash dùng chuẩn hóa CRLF thành LF nên không ảnh hưởng. `.gitattributes` đã có dòng cho `prereg-*.md`; `kaggle/*.py` chưa có thuộc tính tương tự, quyết định ngoài phạm vi báo cáo này.
