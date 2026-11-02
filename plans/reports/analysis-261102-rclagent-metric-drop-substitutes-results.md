# Kết quả RQ (c) bước 1: tín hiệu thay thế khi bỏ metric

Ngày 2026-11-02. Plan: [261102-0035](../261102-0035-rclagent-rq-c-metric-drop-substitutes/plan.md). Luật: [codebook đóng băng](prereg-261102-rclagent-metric-substitute-codebook.md), cách đọc ghi ở [nhật ký deviation](../261102-0035-rclagent-rq-c-metric-drop-substitutes/deviation-log.md). `K/` là `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`. Mọi số dưới đây lấy từ `K/runtime/analysis-metric-substitutes-s1-v2/` (`pairs.csv`, `cases.csv`, `summary.json`). Đây là mô tả trên 3 case, có phơi nhiễm, không phải kết luận nhân quả.

## 1. Trả lời bằng lời thường

- Khi bỏ metric, dữ liệu agent thấy vẫn có một tín hiệu thay thế về dịch vụ lỗi, và tín hiệu đó là **độ trễ**. Ở cả 3 case của tập `D`, span chậm nhất trong trace, xét theo thời gian tự thân hoặc theo tỉ lệ so với mốc train, là span của dịch vụ lỗi hoặc span gọi tới nó. Log và `status_code` không mang tín hiệu nào.
- Tín hiệu này tới được model: mọi span của dịch vụ lỗi đều được hỏi self-state. Nó mất ở **bước self-state (`U2`)**: không span liên quan nào được đánh bất thường, ở cả 6 run của `D`. Theo cách quy `either`, cả 3 case `D` có vị trí mất đầu tiên ở cùng chỉ báo `U2`; theo `caller` riêng thì 2/3 case mất ở `U0` (mục 5).
- 4 trên 5 run vẫn đúng khi không có metric (`K`) đúng mà self-state và consolidation không nêu dịch vụ lỗi (`U2`, `U3` sai). Ở 3 trong 4 run đó (`ad1c27`), dữ liệu cũng không có tín hiệu độ trễ (`U0` sai); ở run còn lại (`99f095` s27), tín hiệu có nhưng không được dùng. Ở cả 4 run, dịch vụ lỗi đồng thời là dịch vụ có nhiều span nhất và đứng đầu kết quả. Đây là đồng xuất hiện trên 2 case, chưa kiểm.
- Hướng X hạng 1: làm cho self-state coi độ trễ bất thường là bằng chứng. Điều kiện kiểm phải gồm `7bbfa6`, case mà dịch vụ lỗi không phải dịch vụ nhiều span nhất. Cũng phải theo dõi `cartservice`, vì ở 5/8 case, span có tỉ lệ cao nhất là một lời gọi `CartService/GetCart`.

## 2. Đơn vị, tập và phơi nhiễm

- Đơn vị của câu kết cục là case. Tập `D` có 3 case, 6 run; seed trong cùng case gần như nhân bản. `99f095` là case hiệu chỉnh của RQ (b).
- Script tự xếp tập theo luật codebook mục 2 và ra đúng số cặp plan đã liệt kê: `D` 6, `R` 3, `K` 5, `excluded` 9 (3 case không có span của dịch vụ lỗi, mỗi case 3 seed), và 1 cặp không thuộc tập nào (`99f095` s26: cả hai trượt, MRR rơi 0,167, dưới ngưỡng 0,2).
- Phơi nhiễm: mọi kết cục đã được thấy trước khi viết codebook ([scout phase 1](scout-261102-rclagent-metric-substitute-signals.md)). Đóng góp của bước này là tính lại tất định theo luật cố định. Biến thể `either` của câu chính được chọn sau khi đã thấy `5f7a77`.

## 3. Theo case (`cases.csv`)

| Case | Dịch vụ lỗi | Tập | Span | Span server / client của GT | Span có tỉ lệ cao nhất | Tỉ lệ / p50 | Vượt p99 | `U0` either / callee / caller | Nhiều span nhất (bỏ frontend) |
|---|---|---|---|---|---|---|---|---|---|
| `5f7a77` | checkoutservice | D, K | 39 | 13 / 1 | checkoutservice gọi `CartService/GetCart` | 451,09 | có | đúng / sai / đúng | checkoutservice |
| `7bbfa6` | recommendationservice | D | 23 | 2 / 1 | frontendservice gọi `RecommendationService/ListRecommendations` | 500,36 | có | đúng / đúng / sai | productcatalogservice |
| `99f095` | currencyservice | D, K | 25 | 10 / 10 | frontendservice gọi `CurrencyService/GetSupportedCurrencies` | 1149,9 | có | đúng / đúng / sai | currencyservice |
| `29583d` | emailservice | R | 31 | 1 / 1 | checkoutservice gọi `CartService/GetCart` | 200,45 | có | sai / sai / sai | checkoutservice |
| `ad1c27` | currencyservice | K | 25 | 10 / 10 | frontendservice gọi `CartService/GetCart` | 98,43 | có | sai / sai / sai | currencyservice |

- Ở cả 8 case (gồm 3 case bị loại), trace chỉ có 1 trace, `status_nonzero` = 0, `gt_log_lines` = 0. Vì vậy `U0_status` và `U0_logs` sai ở mọi case.
- Ở cả 8 case, span có thời gian tự thân lớn nhất có cùng dịch vụ và operation với span có tỉ lệ cao nhất (cột `top_self_span` và `top_ratio_span`), và không có hòa. Mọi span của 8 case đều có mốc train: 25 cặp (dịch vụ, operation).
- Ở 5/8 case (`5f7a77`, `29583d`, `ad1c27`, `272a47`, `30e3c7`), span có tỉ lệ cao nhất là một lời gọi `CartService/GetCart`.

## 4. Theo run `no_metric` (`pairs.csv`)

| Tập | Case, seed | R@1 metric / no_metric | top1 | Span GT được hỏi | Span liên quan đánh bất thường | `U2` | `I2` / `I3` | rank | Mất đầu tiên (either / callee / caller) | `hit_without_substitute` |
|---|---|---|---|---|---|---|---|---|---|---|
| D | `5f7a77` s26 | 1 / 0 | shippingservice | 13/13 | 0/14 | sai | sai / sai | 1 | U2 / U0 / U2 | sai |
| D | `5f7a77` s27 | 1 / 0 | productcatalogservice | 13/13 | 0/14 | sai | sai / sai | 2 | U2 / U0 / U2 | sai |
| D | `7bbfa6` s26 | 1 / 0 | cartservice | 2/2 | 0/3 | sai | sai / sai | 5 | U2 / U2 / U0 | sai |
| D | `7bbfa6` s27 | 1 / 0 | cartservice | 2/2 | 0/3 | sai | sai / sai | 3 | U2 / U2 / U0 | sai |
| D | `7bbfa6` s28 | 1 / 0 | cartservice | 2/2 | 0/3 | sai | sai / sai | 3 | U2 / U2 / U0 | sai |
| D | `99f095` s28 | 1 / 0 | cartservice | 10/10 | 0/20 | sai | sai / sai | 2 | U2 / U2 / U0 | sai |
| R | `29583d` s26 | 0 / 0 | shippingservice | 1/1 | 0/2 | sai | sai / sai | 6 | U0 / U0 / U0 | sai |
| R | `29583d` s27 | 0 / 0 | shippingservice | 1/1 | 0/2 | sai | sai / sai | 6 | U0 / U0 / U0 | sai |
| R | `29583d` s28 | 0 / 0 | frontendservice | 1/1 | 0/2 | sai | sai / sai | 8 | U0 / U0 / U0 | sai |
| K | `5f7a77` s28 | 1 / 1 | checkoutservice | 13/13 | 1/14 | đúng | sai / sai | 0 | U3 / U0 / U3 | sai |
| K | `99f095` s27 | 1 / 1 | currencyservice | 10/10 | 0/20 | sai | sai / sai | 0 | U2 / U2 / U0 | đúng |
| K | `ad1c27` s26 | 1 / 1 | currencyservice | 10/10 | 0/20 | sai | sai / sai | 0 | U0 / U0 / U0 | đúng |
| K | `ad1c27` s27 | 0 / 1 | currencyservice | 10/10 | 0/20 | sai | sai / sai | 0 | U0 / U0 / U0 | đúng |
| K | `ad1c27` s28 | 1 / 1 | currencyservice | 10/10 | 0/20 | sai | sai / sai | 0 | U0 / U0 / U0 | đúng |

- `U1` đúng ở mọi run: mọi span server của dịch vụ lỗi đều có request self-state. "Span liên quan" gồm span server và span client gọi tới GT; mẫu số là số span liên quan có kết quả self-state.
- `U2_latency` sai ở mọi run. Span duy nhất được đánh bất thường (`5f7a77` s28, span client) không nêu từ nào về độ trễ.
- Ở cả 5 run `K`, top1 là dịch vụ nhiều span nhất (`top1_is_struct_max` đúng) và `U_struct` đúng. Ở 6 run `D`, `top1_is_struct_max` sai; top1 là `cartservice` ở 4/6 run.

## 5. Câu kết cục theo luật đóng băng (`summary.json`, `outcomes`)

| Câu | Kết quả |
|---|---|
| **O1** (chính, `D`, either) | 3/3 case có mọi run mất đầu tiên ở cùng chỉ báo, và cả 3 là `U2` |
| **O2** (`D`) | Câu "không có tín hiệu thay thế trong dữ liệu agent thấy" **không** đúng: `U0` đúng ở 3/3 case |
| **O3** (`K`) | 4/5 run có `hit_without_substitute`; cả 4 có `U_struct` và `top1_is_struct_max` đúng. Ở 1 trong 4 run (`99f095` s27), `U0` đúng. Run còn lại (`5f7a77` s28) có `U2` đúng ở một span client, nhưng lý do không nêu độ trễ, và `I2`, `I3` sai |
| **O4** (`R`) | 3 run `29583d` đều mất ở `U0`: span chậm nhất là lời gọi `CartService/GetCart` của checkoutservice; span gọi `emailservice` không đứng đầu |
| Độ nhạy `callee` | O1: 3/3 case cùng vị trí, `U2` ở 2 case, `U0` ở `5f7a77`. O2: `U0` đúng ở 2/3 case |
| Độ nhạy `caller` | O1: 3/3 case cùng vị trí, `U0` ở `7bbfa6` và `99f095`, `U2` ở `5f7a77`. O2: `U0` đúng ở 1/3 case |
| Độ nhạy bỏ `99f095` | O1: 2/2 case, cả hai `U2`. O2: `U0` đúng ở 2/2 |

Câu O1 phụ thuộc vào cách quy độ trễ: theo `either`, cả 3 case mất ở `U2`. Theo từng cách riêng, mỗi cách để một phần các case mất ở `U0`. Nghĩa là tín hiệu nằm ở bên gọi trong `5f7a77`, nhưng ở bên được gọi trong `7bbfa6` và `99f095`. Một X dựa trên độ trễ phải xét cả hai bên của lời gọi.

## 6. Kiểm lặp trên S1 v3

`pairs.csv`, `cases.csv` và `baseline.csv` của `K/runtime/analysis-metric-substitutes-s1-v3/` trùng từng byte với bản S1 v2 (`cmp` thoát 0). Không có cặp lệch, kể cả ở `U4`. Điều này nhất quán với việc `runs.csv` RQ (b) của hai bản trùng từng byte ([báo cáo S1 v3](analysis-261101-s1-v3-hashseed-and-evidence-loss-check.md)); `pairs.csv` chứa cả R@1 và top1, nên các cột đó cũng trùng. Cả hai `summary.json` có `integrity_problems` rỗng, và cờ `prereg` cùng `prereg_after_run` đều đúng.

## 7. Đối chiếu với scout phase 1

Các tỉ lệ 451, 500, 1150, 200 và 98, số span được hỏi, top1 và tử số của số span bị đánh bất thường khớp bảng của scout. Mẫu số của cột "span liên quan đánh bất thường" khác, vì scout đếm riêng span client gọi GT, còn báo cáo này đếm span server cộng span client (mục 4). Có hai chỗ khác nữa:
- Scout ghi "mọi run có `I2` và `I3` sai" và "không span GT nào được đánh bất thường" ở `K`. Cả hai vẫn đúng: span bị đánh ở `5f7a77` s28 là span client gọi GT, không phải span server, và scout cũng ghi nó (1/1 ở cột span client).
- Số dòng bị bỏ vì thuộc cửa sổ val hoặc test là 7 390 661, trong khi scout ghi 7 178 847. Script đếm mọi dòng của các dịch vụ liên quan, còn scout chỉ đếm dòng của 25 cặp (dịch vụ, operation). Số dòng train sau lọc là 9 034 993, khớp con số của bên kiểm chéo.

## 8. Xếp hạng hướng X (codebook mục 6)

"Không sửa upstream" nghĩa là dùng wrapper phía harness (`adapt_payload`, `get_tool` trong `K/smoke-worker.py`) hoặc override prompt nằm ngoài `upstream/`. Hiệu quả của mọi hướng **chưa được đo**; đo cần chạy model.

| Hạng | Hướng X | Chỉ báo nhắm | Dữ liệu nhất quán | Làm được không sửa upstream? | Tiền lệ ([tra tài liệu](research-261102-rclagent-missing-metric-and-trace-blind-spot.md)) | Điều kiện kiểm (cần model) |
|---|---|---|---|---|---|---|
| 1 | Override prompt self-state để coi độ trễ bất thường của span (so với span cùng trace, cả bên gọi lẫn bên được gọi) là bằng chứng, ngang log lỗi và metric | `U2` | O1: 3/3 case `D` mất ở `U2` theo `either` | Có: viết lại `payload.messages` của `self_state_verification` trong `adapt_payload` | Không bài nào đã đọc dùng độ trễ trace thay metric trong khung LLM-agent. Case study của RCLAgent để LLM tự so duration bên gọi và bên được gọi, không có luật | `no_metric` với override trên 3 case `D` và 5 run `K`, 3 seed; đo R@1 và `U2`. Phải gồm `7bbfa6` (GT không phải dịch vụ nhiều span nhất) và `ad1c27` (span chậm nhất không phải GT) để xem X có làm hỏng các run `K` không |
| ghi riêng (thêm nguồn) | Harness cung cấp KPI độ trễ dựng từ trace, có mốc train (ví dụ bảng `duration / p50` cho mỗi dịch vụ, theo cả hai bên của lời gọi), khi metric vắng | `U0` (đưa tín hiệu thành bảng tường minh), rồi `U2` | Theo `either`, không case `D` nào mất ở `U0`. Theo `callee` thì có 1/3, theo `caller` có 2/3. Ở `R` (`29583d`) và `ad1c27`, mốc trỏ sai sang lời gọi `CartService` | Có: wrapper `get_tool` trả bảng dựng từ trace | T-Rank và MicroRank dùng độ trễ trace ngoài khung agent (chưa đọc kỹ). Emődi et al. cho rằng chỉ trace là đủ (chỉ đọc abstract) | Như hạng 1, cộng thêm `29583d`. Cần luật chọn bên gọi hay bên được gọi trước khi chạy |
| không hạng | Can thiệp ở consolidation hoặc xếp hạng cuối | `U3`, `U4` | Không case `D` nào mất đầu tiên ở đây | - | - | - |

Cảnh báo theo codebook mục 6 (câu bắt buộc; dữ liệu chỉ cho thấy đồng xuất hiện, không phải nguyên nhân): O3 cho thấy run `K` có thể đúng nhờ hình dạng trace. Vì vậy một X làm tăng R@1 ở `no_metric` có thể chỉ đang khuếch đại thiên lệch hình dạng trace. Phép kiểm X phải gồm case mà dịch vụ lỗi không phải dịch vụ nhiều span nhất, như `7bbfa6`, và phải báo R@1 theo từng case.

Rủi ro đặc hiệu của hai hướng: ở 5/8 case, span có tỉ lệ cao nhất là lời gọi `CartService/GetCart`, và `cartservice` đã là top1 ở 4/6 run `D`. Một X đẩy độ trễ lên có thể đẩy `cartservice` thay vì dịch vụ lỗi. Bước này chưa giải thích vì sao lời gọi `CartService` chậm ở nhiều case như vậy.

## 9. Giới hạn

- Tập `D` có n = 3 case, seed gần như nhân bản, và S1 v3 là bản sao của S1 v2 (kiểm lặp chỉ chứng minh tính tất định của script, không chứng minh độ ổn định của model).
- Phơi nhiễm đầy đủ (mục 2). Cách đọc span client và span server khi quy độ trễ được chốt trước khi chạy, nhưng sau khi đã thấy dữ liệu ([deviation-log](../261102-0035-rclagent-rq-c-metric-drop-substitutes/deviation-log.md) mục 1).
- Mốc lấy cửa sổ trước khi tiêm lỗi của 48 case train. Chưa kiểm cửa sổ đó có chồng lên giai đoạn lỗi của case khác ngoài 90 case trong file vai trò không.
- `U2_latency` dùng một regex; lý do diễn đạt khác sẽ bị bỏ sót. Ở đây không có trường hợp nào bị ảnh hưởng, vì chỉ có một span bị đánh bất thường.
- Tra tài liệu đi qua tóm tắt công cụ; trích dẫn chưa đối chiếu nguyên văn.

## 10. Tái lập

Từ `K/`, với `P=runtime/harness-env/Scripts/python.exe`:

```
$P -X utf8 test-analyze-metric-substitutes.py
$P -X utf8 analyze-metric-substitutes.py runtime/analysis-metric-substitutes-s1-v2 --label s1-v2 --evidence-runs runtime/analysis-evidence-loss-s1-v2/runs.csv a runtime/kaggle-output-a-s1-v2/rclagent-smoke/rclagent-smoke-results.zip s1-v2/a/manifest.json b runtime/kaggle-output-b-s1-v2/rclagent-smoke/rclagent-smoke-results.zip s1-v2/b/manifest.json
```

Lệnh cho S1 v3 giống hệt, chỉ đổi `v2` thành `v3`. Mỗi lần chạy mất vài phút vì phải đọc file trace thô 5,2 GB.

| Thứ | SHA256 (CRLF thành LF) |
|---|---|
| Codebook | `0ed7b0d5d93c9dc32653b0add38db38fa9d0dbb6ead1afa1c0be0f114117ff06` |
| `analyze-metric-substitutes.py` | `fab09be90107b19065443d55a74e4a9012ceec87f7999094fdc5fde86f7116be` |
| `analyze-evidence-loss.py` (nạp, không sửa) | `0460964ae37a4210e277ac31070b2c67979606794a58274a3a2258d7eb70d978` |
| `pairs.csv` S1 v2 = S1 v3 | `96a656b694b12784618f38f888f5c68f318599fa148eafc402c0c36338fda0bc` |
| `cases.csv` S1 v2 = S1 v3 | `c29f520ebc7dcf10ca58f8f91cdef2aefdaaf61a705d77e5c1c23ac15a909e4c` |

Biên nhận: `K/metric-substitute-prereg.json`. Test mới thoát 0 (30 test), và 5 bộ test cũ mà script nạp cũng thoát 0.

## 11. Quyết định chờ sếp

1. Có lập plan Kaggle cho hướng X hạng 1 (override prompt self-state) không, và có gộp X1 đang tạm dừng vào cùng gói không? Nếu không, dừng RQ (c) ở bước mô tả này.
2. Nếu làm, có thêm biến thể "thêm nguồn" (KPI độ trễ dựng từ trace) làm nhánh thứ hai không? Biến thể này cần chốt luật bên gọi hay bên được gọi trước.

## Câu hỏi còn mở

1. Vì sao lời gọi `CartService/GetCart` là span chậm nhất ở 5/8 case? Đây là đặc điểm của dữ liệu RE2-OB hay của cửa sổ gói? Câu này ảnh hưởng tới tính đặc hiệu của mọi X dựa trên độ trễ.
