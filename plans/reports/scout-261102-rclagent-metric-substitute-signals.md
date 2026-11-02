# Kiểm kê tín hiệu không phải metric khi bỏ metric (phase 1)

Ngày 2026-11-02. Phase 1 của [plan RQ (c) bước 1](../261102-0035-rclagent-rq-c-metric-drop-substitutes/plan.md). `K/` là `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`. Đây là **khám phá**: mọi điều dưới đây đã được thấy trước khi viết codebook, và codebook phải ghi chúng vào tuyên bố phơi nhiễm. Chỉ CPU, chỉ đọc; không chạy model.

## Kết luận

1. **Tín hiệu thay thế có trong dữ liệu, agent nhận được, nhưng bỏ qua.** Ở cả 3 case của tập `D` (`5f7a77`, `7bbfa6`, `99f095`), trong trace có một span liên quan GT chậm hơn trung vị của chính operation đó trên dữ liệu train từ 451 đến 1150 lần, và là span có tỉ lệ cao nhất trong trace. Span của GT đều được đưa vào prompt self-state (prompt chứa `duration`). Nhưng ở cả 6 run `D`, **không span nào của GT, và không span client nào gọi GT, được tự đánh `is_abnormal = true`**. Đọc tay hai run (`7bbfa6` s26, `5f7a77` s26): model ghi nhận độ trễ cao rồi kết luận bình thường vì không có log lỗi và không có metric dao động. Vị trí mất là **giai đoạn self-state (U2)**, không phải dữ liệu hay đầu vào.
2. **Log và `status_code` không mang tín hiệu nào.** Ở cả 5 case có output (`D`, `R`, `K`), bundle chỉ có một trace, mọi `status_code` bằng 0, và log chỉ có `cartservice`, `frontend` (và `redis` ở ba case); không có dòng nào của GT.
3. **Các run `K` đúng nhờ hình dạng trace, không nhờ bằng chứng.** Ở 5/5 run `no_metric` vẫn đúng R@1, GT là dịch vụ có nhiều span nhất khi bỏ `frontendservice`, top1 trùng dịch vụ đó, không span GT nào được đánh bất thường, và `I2`, `I3` đều sai. Ở 6/6 run `D`, top1 không bao giờ là dịch vụ nhiều span nhất; top1 là `cartservice` ở 4/6 run, dù `cartservice` là dịch vụ có nhiều dòng log nhất và không có span trong trace của `7bbfa6`, `99f095`.
4. **Tín hiệu độ trễ không đặc hiệu tuyệt đối.** Quy tắc "dịch vụ được gọi bởi span chậm nhất so với mốc" trúng GT ở `7bbfa6` và `99f095`, nhưng ở `5f7a77` span chậm nhất là `checkoutservice` gọi `CartService/GetCart`: quy về bên gọi thì trúng GT, quy về bên được gọi thì ra `cartservice`. Ở `29583d` và `ad1c27`, span chậm nhất là lời gọi `CartService/GetCart`, không phải GT.

Hệ quả cho X: hướng hợp lý nhất là làm cho self-state coi độ trễ bất thường là bằng chứng (override prompt self-state, hoặc harness cung cấp KPI độ trễ dựng từ trace có mốc). Cách quy độ trễ về dịch vụ (bên gọi hay bên được gọi) là quyết định thiết kế chính, vì nó quyết định `5f7a77`.

## Số liệu

### Theo case (bundle `K/s1-v2/{a,b}/rclagent-kaggle-bundle.zip`)

| Case | GT | Tập | Trace | Span | `status_code` khác 0 | Dòng log của GT | Dịch vụ nhiều span nhất (bỏ frontend) |
|---|---|---|---|---|---|---|---|
| `5f7a77` | checkoutservice | D, K | 1 | 39 | 0 | 0 | checkoutservice (13) |
| `7bbfa6` | recommendationservice | D | 1 | 23 | 0 | 0 | productcatalogservice (7) |
| `99f095` | currencyservice | D, K | 1 | 25 | 0 | 0 | currencyservice (10) |
| `29583d` | emailservice | R | 1 | 31 | 0 | 0 | checkoutservice (9) |
| `ad1c27` | currencyservice | K | 1 | 25 | 0 | 0 | currencyservice (10) |

### Span chậm nhất so với mốc train (theo `duration / p50`)

| Case | Span có tỉ lệ cao nhất | Tỉ lệ | Liên quan GT? |
|---|---|---|---|
| `7bbfa6` | frontendservice gọi `RecommendationService/ListRecommendations` | 500 | Có, bên được gọi là GT |
| `99f095` | frontendservice gọi `CurrencyService/GetSupportedCurrencies` | 1150 | Có, bên được gọi là GT |
| `5f7a77` | checkoutservice gọi `CartService/GetCart` | 451 | Bên gọi là GT, bên được gọi không |
| `29583d` | checkoutservice gọi `CartService/GetCart` | 200 | Không (span gọi GT đứng thứ 2, tỉ lệ 52) |
| `ad1c27` | frontendservice gọi `CartService/GetCart` | 98 | Không (9 span gọi GT đứng thứ 2 đến 9, tỉ lệ 21 đến 43) |

Mốc: 48 cửa sổ case train, mỗi cửa sổ `[inject_ts - 1200 s, inject_ts - 60 s)`, theo file vai trò `plans/261026-1713-rclagent-tai-hien-toi-thieu/work/re2ob-case-roles-by-source-key.csv`, trên `F:/Nam/UIT/nt114-paper-artifacts/W7165616276/data/re2ob/trace/all/trace_jaeger-span.csv`. 25 cặp (dịch vụ, operation) đều có mốc (n từ 15 077 đến 919 412).

### Theo run `no_metric` (zip S1 v2)

| Tập | Case, seed | R@1 | top1 | top1 là dịch vụ nhiều span nhất? | Span GT được hỏi self-state | Span GT đánh bất thường | Span client gọi GT đánh bất thường |
|---|---|---|---|---|---|---|---|
| D | `5f7a77` s26 | 0 | shippingservice | không | 13/13 | 0 | 0/1 |
| D | `5f7a77` s27 | 0 | productcatalogservice | không | 13/13 | 0 | 0/1 |
| D | `7bbfa6` s26 | 0 | cartservice | không | 2/2 | 0 | 0/1 |
| D | `7bbfa6` s27 | 0 | cartservice | không | 2/2 | 0 | 0/1 |
| D | `7bbfa6` s28 | 0 | cartservice | không | 2/2 | 0 | 0/1 |
| D | `99f095` s28 | 0 | cartservice | không | 10/10 | 0 | 0/10 |
| R | `29583d` s26 | 0 | shippingservice | không | 1/1 | 0 | 0/1 |
| R | `29583d` s27 | 0 | shippingservice | không | 1/1 | 0 | 0/1 |
| R | `29583d` s28 | 0 | frontendservice | không | 1/1 | 0 | 0/1 |
| K | `5f7a77` s28 | 1 | checkoutservice | có | 13/13 | 0 | 1/1 (lý do không nhắc độ trễ) |
| K | `99f095` s27 | 1 | currencyservice | có | 10/10 | 0 | 0/10 |
| K | `ad1c27` s26 | 1 | currencyservice | có | 10/10 | 0 | 0/10 |
| K | `ad1c27` s27 | 1 | currencyservice | có | 10/10 | 0 | 0/10 |
| K | `ad1c27` s28 | 1 | currencyservice | có | 10/10 | 0 | 0/10 |

Mọi run ở bảng này có `I2` và `I3` sai (`K/runtime/analysis-evidence-loss-s1-v2/runs.csv`).

## Cách làm và file

- Script nháp (không vào repo) và mọi output: `K/runtime/analysis-metric-substitutes-inventory/` (`cases.csv`, `gt-spans.csv`, `runs.csv`, `all-spans-vs-baseline.csv`, `baseline.csv`, `summary.json`, bản sao `signal_inventory.py`; SHA256 script `3810f02c…ac9f`). Chạy bằng `K/runtime/harness-env/Scripts/python.exe -X utf8`.
- "Span client gọi GT": span có `cmdb_id` khác GT mà `operation_name` chứa lớp dịch vụ của GT (ví dụ `RecommendationService`). "Đánh bất thường": `is_abnormal == true` trong `agent_complete` của `self_state_verification`.
- Đọc tay: self-state của span GT ở `7bbfa6` s26 (3 span), `5f7a77` s26 (2 span), `ad1c27` s26 (2 span), và `result.json` của ba run đó.
- Script đọc kiểu dòng nên có hai lần chạy hỏng được sửa trước khi có số: lần 1 sai đường dẫn file vai trò, lần 2 tráo cột `operation_name` và `duration` khi giải nén chunk (mốc ra 0 dòng). Cả hai không sinh số nào được dùng.

## Kiểm chéo độc lập

Bốn agent kiểm chéo tự viết code đọc thẳng file thô, không dùng script của phase 1, mỗi agent được giao bác bỏ một nhóm khẳng định. Kết quả: không nhóm nào bị bác, không nhóm nào chưa kết luận.

| Khẳng định | Kết quả kiểm chéo |
|---|---|
| Một trace, `status_code` bằng 0, không có log của GT, số span theo case | Khớp ở cả 5 case |
| Không span liên quan GT nào bị đánh bất thường ở 6 run `D`; mọi span GT có request self-state | Khớp. Mọi span liên quan GT đều có request và có kết quả (`5f7a77`: 14, `7bbfa6`: 3, `99f095`: 20 mỗi run). Model gạt độ trễ đi ngay trong lý do, ví dụ "High latency alone is not sufficient to indicate a root cause" (`5f7a77` s27) |
| Run `K` đúng nhờ dịch vụ nhiều span nhất; top1 của run `D` không bao giờ là dịch vụ đó, và là `cartservice` ở 4/6 | Khớp, không có hòa |
| Ba tỉ lệ mốc (500, 1150, 451) và vị trí đứng đầu theo tỉ lệ | Khớp. 48 cửa sổ train không chồng nhau; 9 034 993 dòng thuộc cửa sổ train |

Ghi chú của bên kiểm: xếp theo `duration` thô thì span gốc `frontend` luôn đứng đầu, nên chỉ báo độ trễ phải dùng thời gian tự thân hoặc tỉ lệ theo mốc, không dùng `duration` thô. Script kiểm chéo nằm ở scratchpad của phiên, không vào repo.

## Giới hạn

- Tập `D` chỉ có 3 case, 6 run; seed gần như nhân bản. `99f095` là case hiệu chỉnh của RQ (b).
- Để lọc theo cửa sổ, script phải đọc qua cả dòng thuộc cửa sổ val và test (7 178 847 dòng bị loại ngay, không tổng hợp, không xem). Không có nhãn hay kết quả test nào được đọc.
- Mốc chỉ lấy trước thời điểm tiêm lỗi của case train; chưa kiểm cửa sổ đó có chồng lên giai đoạn lỗi của case khác không.
- Không đo xem model có thấy span client gọi GT hay không trong prompt của chính span GT; chỉ đo self-state của từng span.
- Nhận xét về `cartservice` ở mục Kết luận 3 là quan sát, chưa kiểm.

## Câu hỏi còn mở

1. Codebook nên quy độ trễ về bên gọi, bên được gọi, hay báo cả hai? Lựa chọn này quyết định kết quả của `5f7a77` và đã bị phơi nhiễm.
