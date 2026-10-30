# Phân tích 5 trace pilot RCLAgent trên CPU và đề xuất thí nghiệm thiếu nguồn — 2026-10-28

**Kết luận:** trên RE2-OB, RCLAgent bản tác giả gần như không nhận được bằng chứng nào từ metric và log.

- **Metric luôn rỗng do lỗi bộ lọc trong tool**, không phải do dữ liệu, cửa sổ truy vấn hay ánh xạ service/node. Preprocess của tác giả ghi `node_id` rỗng ở mọi dòng. Khi đọc CSV, giá trị rỗng thành NaN, và `groupby` mặc định bỏ mọi nhóm có NaN, nên vòng tìm spike không bao giờ chạy.
- **Log chỉ có bằng chứng cho service đúng ở 3/48 case train**, đều là `recommendationservice_loss_*`.
- **Hệ quả ở 5 trace pilot.** Mọi self-state đều trả "không bất thường", trừ 5 span: 4 span ở `2095688a` và 1 span ở `3753f2a8`. Top-1 cuối cùng trùng với service (không tính frontend) có nhiều span nhất trong trace ở cả 5/5 trace. Heuristic đếm span đó, không dùng GPU, đạt R@1 = 98/240 trên train.

Vì vậy bỏ log (`no_log`) gần như chỉ bỏ nhiễu. Không case nào trong 8 case chọn cho thí nghiệm có bằng chứng log của service đúng. Em đề nghị đổi nguồn cần thử sang metric (mục 6). Sếp quyết định.

Phạm vi: chỉ CPU, đọc artifact v9–v11 và dữ liệu đã preprocess. Không GPU, không sửa harness hay upstream, không commit. Nhãn chỉ dùng để chấm và phân tầng, không dùng để chọn trace theo kết quả. Script và đầu ra ở [`work/pilot-trace-analysis/`](../261026-1713-rclagent-tai-hien-toi-thieu/work/pilot-trace-analysis/).

## 1. Vì sao metric luôn rỗng

Phản hồi metric ở v11: em đếm từ `events.jsonl` (`tool_result`) được 131 lần "No fluctuating metrics found." và 15 lần "No matching records found.", tổng 146. Sếp đếm được 129/17. Tổng khớp, còn cách tách khác 2 phản hồi; em chưa rõ vì sao.

| Giả thuyết | Kết quả kiểm | Bằng chứng |
|---|---|---|
| Đặc điểm dữ liệu | Loại trừ. Mỗi KPI của service đúng lệch rất lớn sau lúc tiêm lỗi, ví dụ `currencyservice.mem` lệch 521σ so với trước lúc tiêm | `metric-gt-kpis.csv` |
| Cửa sổ truy vấn | Loại trừ. Gói dữ liệu chứa đủ ±1.200 giây, và đã được đối chiếu từng hàng với dữ liệu đầy đủ (`cpu-equivalence.json`). Mỗi truy vấn có dữ liệu khớp gồm 6–8 nhóm KPI | `metric-queries.csv` |
| Ánh xạ service/node | Không phải nguyên nhân chính. `service_node_map.pkl` rỗng (`{}`), nên nhánh lọc theo node không bao giờ chạy. 10 phản hồi "No matching" là do trace gọi `frontendservice` còn metric gọi `frontend` | `metric-queries.csv` |
| **Bộ lọc của tool** | **Nguyên nhân.** `preprocess_re2ob.py:158` gán `node_id = ""` cho 9.409.001/9.409.001 dòng. `tool_server.py:189` gọi `groupby(["kpi_name","node_id","service_name"])` với `dropna=True` mặc định, nên còn 0 nhóm. Endpoint vì thế luôn trả "No fluctuating metrics found." khi có dòng khớp | chạy lại endpoint: 0 nhóm; với `dropna=False` thì có 72–76 nhóm |

5 phản hồi "No matching" còn lại là do model gõ sai timestamp, lệch từ 3×10⁸ đến 4×10⁸ giây.

**Sửa riêng lỗi `dropna` vẫn chưa đủ.** Baseline ±1.200 giây của tác giả chứa luôn cửa sổ có lỗi. Một bước nhảy kéo dài vì thế làm phình độ lệch chuẩn, và độ lệch cực đại của các KPI thuộc service đúng chỉ còn 1,0–9,7σ.

Em mô phỏng ba cách trên 240 trace train, chỉ xét các service có trong trace:

| Cách | Gắn cờ service đúng | Gắn cờ service khác | Service đúng đứng đầu duy nhất |
|---|---:|---:|---:|
| Tool như tác giả viết | 0% | 0% | 0% |
| Chỉ sửa `dropna` | 80% | 590/610 (97%) | 7,5% |
| Baseline trước cửa sổ [ts−1.200, ts−600), xếp theo độ lệch | 100% | không áp dụng | 155/240 |

Xếp theo độ lệch trên cả 11 service thì R@1 = 216/240. Theo trace, mọi trace train nằm trong khoảng −49 đến +299 giây quanh lúc tiêm lỗi. Nhờ vậy baseline trước cửa sổ là sạch mà không cần đọc nhãn. Đây là tính chất của RE2-OB, chưa chắc đúng ở bộ dữ liệu khác.

## 2. Log

| Kiểm | Kết quả |
|---|---|
| Log được tool trả về, sau bộ lọc INFO/DEBUG của tác giả | Ở 5 gói pilot chỉ còn `cartservice` (khoảng 1.000–1.600 dòng `severity: unknown, GetCartAsync...`) và `frontend` |
| Log của service đúng trong 600 giây sau lúc tiêm lỗi | Có ở 9/90 case, đều là lỗi `loss`. Với train là 3/48 case (`recommendationservice_loss_1..3`) |
| Model thực nhận | Với `cartservice`, 167–286 KB bị ngân sách rút gọn còn 2.048 token. Với service khác, chỉ có header CSV dài 40 byte. Log `frontend` không bao giờ đến được model, vì model truy vấn tên `frontendservice` |

## 3. Chuỗi suy luận của 5 trace (v11)

| Trace | Nhãn | Hạng | Nhóm nguyên nhân | Chi tiết |
|---|---|---:|---|---|
| `1e527c6a` | currencyservice mem | 1 | Đúng nhờ đếm span | Cả 25 self-state đều "không bất thường". Bước gộp cuối kết luận `none` với confidence 0. Bước tổng hợp chọn service có nhiều span nhất (currency, 10 span) |
| `f6526e73` | productcatalogservice mem | 1 | Đúng nhờ đếm span, dao động | Như trên (prodcat 9 span so với currency 5). Ở v10, cùng trace này có top-1 là `frontendservice`; chỉ đổi cấu hình server mà kết quả đổi từ sai sang đúng |
| `2095688a` | productcatalogservice delay | 4 | Model diễn giải sai, cộng đếm span | Self-state của span `9077b868…` ghi `has_error_logs: true` cho `checkoutservice` dù cả 6 phản hồi tool đều rỗng. Bước gộp lấy `checkoutservice` (16 span, nhiều hơn prodcat 15) với confidence 0,95 |
| `3753f2a8` | recommendationservice socket | không có | Đầu vào thiếu, cộng nhiễu log | Trace có 4 span, không span nào của service đúng. Span client `CartService/AddItem` khiến model truy vấn `cartservice` và nhận 286 KB nhiễu. Kết quả có hậu tố `-0` (`productcatalogservice-0`), nên scorer không khớp được |
| `c6033940` | emailservice socket | không có | Đầu vào thiếu | `emailservice` không có trong `cmdb_id` hay `operation_name` của trace. Model không truy vấn service này lần nào |

Trên 240 trace train:
- **Trace thiếu service đúng.** 59 trace (25%) không có service đúng ở cả `cmdb_id` lẫn `operation_name`.
- **Heuristic đếm span** đạt R@1 98/240 và MRR 0,528. Đây là mốc so tối thiểu, không cần GPU.
- **Dao động giữa các lượt.** Từ v10 sang v11, 1/4 trace có top-1 đổi đúng/sai, nên cần đo nhiễu bằng 3 seed.

Mất bằng chứng xảy ra **ở tầng tool**: metric bị bộ lọc bỏ hết, còn log thì dữ liệu không có. Bước gộp và tổng hợp chỉ truyền tiếp cái rỗng đó. Lỗi diễn giải chỉ gặp 1 lần nhưng đủ đổi kết quả.

## 4. Mô phỏng thiếu nguồn bằng phản hồi rỗng hợp lệ

Tool và prompt giữ nguyên. Model không được báo riêng rằng một nguồn bị mất.

| Điều kiện | Phản hồi của nguồn bị bỏ | Phân biệt với nguồn còn chạy nhưng không thấy bất thường |
|---|---|---|
| `no_log` | `log_id,timestamp,cmdb_id,log_name,value\n`, đúng byte endpoint gốc trả khi không có dòng nào; guard ngân sách không chạy | Model không phân biệt được. Hiện 143/152 truy vấn log ở 5 trace đã nhận đúng chuỗi này |
| `no_metric` | `{"message":"No matching records found."}`, đúng câu endpoint gốc trả khi không có dòng metric | Khác với tình trạng hiện tại ("No fluctuating metrics found.", nghĩa là có dữ liệu nhưng không có spike). Model không được giải thích hai câu này khác nhau ra sao |

Report kết quả sẽ ghi rõ: đây là tình huống mất nguồn mà không ai báo, khác với tình huống nguồn còn hoạt động nhưng không thấy bất thường.

## 5. Seed

`smoke-worker.py:95` ghi cứng `seed=20261026`. Cần thêm tham số seed theo lượt chạy và truyền thật vào payload. Seed phải được ghi trong `events.jsonl`, để kiểm trên artifact rằng nó thật sự được gửi đi. Bộ seed đề xuất là {20261026, 20261027, 20261028}, dùng chung cho mọi điều kiện. v9 và v10 trùng nhau từng byte khi cùng seed, nên lặp mà không đổi seed thì không đo được dao động.

## 6. Đề xuất thí nghiệm

### 6.1 Case và trace (chốt trước, không xem kết quả)

Quy tắc ở `select-pilot-cases.py` (salt `nt114-rclagent-missing-source-pilot-261028`):
1. Bỏ 5 case pilot.
2. Sắp case theo sha256.
3. Lấy mỗi loại lỗi một case, rồi thêm 2 case. Không service nào quá 2 case.
4. Trong mỗi case, lấy trace theo lần lượt các nhóm độ dài ngắn/vừa/dài; trong nhóm, chọn trace có sha256 nhỏ nhất.

Tập train có 143/240 trace dài 23–25 span, nên kết quả nghiêng về trace ngắn. `pilot-selection.json` có sha256 `87b505ca…27c8`.

| Case | Trace | Span | Ước giây |
|---|---|---:|---:|
| checkoutservice_cpu_1 | `de6a503b…` | 25 | 502 |
| emailservice_delay_3 | `30e3c732…` | 23 | 463 |
| checkoutservice_mem_1 | `5f7a7727…` | 39 | 771 |
| currencyservice_loss_3 | `99f095ae…` | 25 | 502 |
| currencyservice_disk_3 | `ad1c27da…` | 25 | 502 |
| recommendationservice_socket_1 | `7bbfa606…` | 23 | 463 |
| recommendationservice_cpu_2 | `272a47c2…` | 25 | 502 |
| emailservice_delay_1 | `29583dc6…` | 31 | 617 |

3/8 trace không chứa service đúng. Không case nào trong 8 case có bằng chứng log của service đúng.

### 6.2 Hai phương án

**A (em đề xuất): thử nguồn metric.** Gồm 8 case × 3 điều kiện × 3 seed = 72 lượt.
- **Ba điều kiện:**
  - `no_metric`: hành vi hiện tại. Metric đang mất mà không ai báo, chỉ đổi câu trả lời rỗng cho đúng định dạng ở mục 4.
  - `metric`: metric chạy được nhờ X_m.
  - `metric + no_log`.
- **X_m gồm ba phần:**
  - Giữ các nhóm có `node_id` NaN.
  - Lấy baseline trong [ts−1.200, ts−600), cửa sổ [ts−600, ts+600].
  - Chỉ trả KPI có |trung bình cửa sổ − trung bình baseline| ≥ k·σ_baseline, giữ đúng định dạng CSV của tác giả.
- **Chọn k = 100.** Đây là k nhỏ nhất trong {10, 20, 50, 100, 150} để tỷ lệ service khác bị gắn cờ dưới 10%. k chọn trên 35 case train nằm ngoài cả 5 case pilot lẫn 8 case thí nghiệm. Với k này, 97,1% trace có service đúng vượt ngưỡng, và 8,4% service khác bị gắn cờ.
- **Phương án trả lời được:**
  - (a) mất metric thì kết quả giảm bao nhiêu (`metric` so với `no_metric`);
  - (b) mất ở bước nào: ở `no_metric` đã biết là tầng tool, còn ở `metric` sẽ đọc từ các cờ;
  - tác động của `no_log` khi đã có một nguồn chạy được.
- **X_m làm đổi hành vi khi đủ nguồn.** Nó chính là phần định nghĩa điều kiện `metric`, không được trình bày như một cách khắc phục thiếu nguồn.
- **Không có X bù thiếu nguồn ở vòng này.** X đó chỉ nên chốt sau khi thấy bằng chứng mất ở đâu khi metric chạy được.
- **Lệch so với code tác giả.** Điều kiện `metric` không còn là RCLAgent nguyên bản, report phải ghi rõ.

**B: giữ nguyên kế hoạch ban đầu (`full`, `no_log`, `no_log + X_g`).** X_g là kiểm cờ theo bằng chứng: harness đặt `has_error_logs` hoặc `has_metric_anomaly` về `false` khi các phản hồi tool của span đó không có dòng dữ liệu. X_g gắn với lỗi ở `2095688a`.
- X_g cũng đổi hành vi khi đủ nguồn, nên cần thêm `full + X_g`: 4 điều kiện × 6 case × 3 seed = 72 lượt.
- Dự đoán từ CPU: `no_log` không bỏ bằng chứng nào của service đúng ở 8/8 case. Thay đổi nếu có sẽ đến từ việc bỏ nhiễu `cartservice` hoặc từ sampling.
- Ngưỡng mở hướng thiếu nguồn vì vậy gần như chắc không đạt. Tốn khoảng 11 giờ để xác nhận điều CPU đã cho thấy.

### 6.3 Cách chấm

- **Mỗi lượt:** dùng scorer của tác giả trên một trace để lấy R@1, R@3, MRR.
- **Lượt thất bại:** lượt failed hoặc hết deadline tính 0, ghi riêng và không chạy lại.
- **Tên có hậu tố.** Tên kiểu `-0` vẫn chấm theo scorer, và đếm riêng số lần xuất hiện.
- **So theo cặp.** So cùng case và cùng seed giữa các điều kiện.
- **Ngưỡng sàng lọc của sếp:**
  - Mở hướng thiếu nguồn khi R@1 giảm ≥ 12,5 điểm phần trăm hoặc MRR giảm ≥ 0,10, cùng chiều ở ít nhất 2/3 seed, và có ít nhất 2 case bị ảnh hưởng.
  - Một case tính là bị ảnh hưởng khi trung bình 3 seed của nó đổi ít nhất 1/3 điểm R@1, hoặc ít nhất 0,10 MRR, theo cùng chiều.
- **Báo kèm hai mốc so:** heuristic đếm span (CPU) và xếp theo độ lệch metric (CPU), để biết LLM thêm được gì.
- **Không kiểm định thống kê.**

### 6.4 Thời gian

Ước theo `plan-train-batches.py`: thời gian mỗi request lấy từ pilot v11, setup 480 giây mỗi phiên, hệ số an toàn 1,25.

| Phương án | Lượt | Ước điểm | Ước cao gồm setup |
|---|---:|---:|---:|
| A: 8 case × 3 điều kiện × 3 seed | 72 | 10,8 giờ | 13,8 giờ (2 phiên) |
| A rút gọn: 6 case đầu × 3 điều kiện × 3 seed | 54 | 8,0 giờ | 10,3 giờ (2 phiên) |
| B: 6 case đầu × 4 điều kiện × 3 seed | 72 | 10,7 giờ | 13,6 giờ (2 phiên) |

Ước điểm của 72 lượt vừa ngân sách 10–11 giờ, nhưng ước cao vượt khoảng 3 giờ. Chỉ phương án A rút gọn có ước cao nằm trong ngân sách. Với A còn hai rủi ro: bảng metric dài hơn làm prompt dài hơn, và model có thể gọi thêm vòng tool. Hai yếu tố này chưa có trong ước lượng.

## Câu hỏi còn mở

1. Chọn phương án A (thử metric) hay B (giữ `no_log`)?
2. Nếu chọn A, sếp có chấp nhận X_m (baseline trước cửa sổ, k = 100) làm định nghĩa của điều kiện `metric`, dù nó lệch so với code tác giả?
3. Giữ 8 case và chấp nhận ước cao 13,8 giờ, hay giảm xuống 6 case để vừa 10–11 giờ?
4. Có báo cho tác giả về lỗi `node_id`/`dropna` không? Lỗi này có thể ảnh hưởng tới kết quả RE2-OB trong bài báo.
