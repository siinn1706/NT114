# Đặc tả phương pháp và prereg: agent RCA nhận biết và bù chỗ thiếu telemetry (lượt dev)

Ngày 2026-11-02. Plan: [hướng A](../261102-1000-rclagent-telemetry-gap-aware-agent/plan.md), phase 3. Trạng thái: **bản 3, sếp duyệt ngày 2026-11-02**. Hash đóng băng trong `K/telemetry-gap-prereg.json`.

Quy ước đường dẫn:
- `K/` là `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`.
- `U/` là mã tác giả, ở `F:/Nam/UIT/nt114-paper-artifacts/W7165616276/code/`.

Đây là lượt **dev trên train**. Nó chỉ dùng để quyết go/no-go cho đánh giá cuối trên test split, không dùng làm kết luận của bài. Các chỗ lệch so với plan được ghi ở [nhật ký deviation](../261102-1000-rclagent-telemetry-gap-aware-agent/deviation-log.md).

## 1. Căn cứ

- **Trace được giao không phủ dịch vụ lỗi.** 59/240 truy vấn train (24,6%) và 25/105 truy vấn val có trace không chứa span nào của dịch vụ lỗi. Dù vậy, cửa sổ quanh truy vấn có hàng trăm trace khác đi qua dịch vụ đó ([phạm vi trace](analysis-261102-rclagent-trace-coverage-and-non-llm-baselines.md)).
- **Prompt của tác giả tự hạ giá trị độ trễ ở hai chỗ.** System prompt chung ghi "High latency alone is a WEAK signal" (`U/coordinator.py:175`). Prompt self-state nhắc lại "High latency alone → WEAK signal" (`U/coordinator.py:221`). Ở RQ (c) bước 1, mọi case mất R@1 khi bỏ metric đều mất ở bước self-state ([kết quả bước 1](analysis-261102-rclagent-metric-drop-substitutes-results.md), mục 5).
- **Khi nguồn vắng, harness trả phản hồi rỗng của tác giả** (`K/smoke-worker.py:50`, `ABSENT_RESPONSE`). Model không phân biệt được "không có dữ liệu" với "khỏe"; đây là lỗi MIS1 trong 2608.21310.
- **Agent chỉ hỏi metric của dịch vụ có span trong trace.** Mỗi span có một agent, và agent đó hỏi đúng tên dịch vụ của span mình (`U/coordinator.py:204-214`). Ở truy vấn không phủ, không agent nào hỏi về dịch vụ lỗi.
- **Khám phá bộ xếp hạng cửa sổ trước truy vấn.** `K/explore-window-ranker.py` tính trên CPU, không có test, kết quả trong `K/runtime/window-ranker-300.json`. Quy tắc giống hệt bảng M3 ở mục 2. Mốc là leave-one-case-out cho train; với val, mốc là toàn bộ train.

| Tập | R@1 tổng | R@1 có phủ | R@1 không phủ | MRR tổng | top1 là `cartservice` |
|---|---|---|---|---|---|
| train (240) | 0,629 | 0,685 (181) | 0,458 (59) | 0,751 | 0 |
| val (105) | 0,343 | 0,400 (80) | 0,160 (25) | 0,532 | 0 |

- **Truy vết:** script SHA256 `badfbedc…a91790`; `window-ranker-300.json` SHA256 `2bacaceb…b61203c`.
- **Trên 25 truy vấn dev,** bộ xếp hạng đúng 12/25: 3/12 ở tầng không phủ, 9/13 ở tầng có phủ.
- **Một lượt khám phá trước đó** dùng mốc không loại case và báo từng phía riêng (p95 phía client: R@1 0,685 có phủ, 0,441 không phủ). Lượt đó dẫn tới chọn p95 và cửa sổ 300 giây. Val chưa từng được dùng để chọn quy tắc.
- **Val sụt mạnh so với train** (0,343 so với 0,629; tầng không phủ 0,160 so với 0,458), dù val dùng mốc từ toàn bộ train, không rò dữ liệu. Có hai cách hiểu:
  - quy tắc đã khớp quá mức vào train khi chọn thống kê, cửa sổ và phía;
  - các case val khó hơn.

  Lượt dev không phân biệt được hai cách hiểu này. Hệ quả cho bài: tín hiệu cửa sổ có thật nhưng yếu hơn số train cho thấy. Vì vậy câu hỏi đúng là LLM có dùng tín hiệu đó tốt hơn một quy tắc cố định hay không (H4), chứ không phải tín hiệu có tồn tại hay không.

## 2. Phương pháp

Cả ba thành phần nằm trong harness, không sửa `U/`. Chúng được chèn ở `Guard.post` (`K/smoke-worker.py:179`), trước `adapt_payload`, và trong `source_response` (`K/smoke-worker.py:155`). Prompt cần sửa được nhận diện bằng chuỗi cố định:
- `"IMPORTANT evidence ranking"` cho prompt self-state;
- `"Goal: identify the root-cause service."` cho prompt tổng hợp cuối.

Khi mọi cờ đều tắt, request phải giống từng byte với S1 v3.

**Dữ liệu chung, tính trước trên CPU** thành `window-kpi.json` cho mỗi truy vấn. File này nằm trong bundle; harness chỉ đọc nó.
- **Thời điểm truy vấn `t_q`** là timestamp sớm nhất của trace truy vấn.
- **Cửa sổ** là [`t_q` − 300 s, `t_q`). Không dùng dữ liệu sau `t_q`, không dùng `inject_ts` của truy vấn, không dùng nhãn. Không có trần số trace, vì mọi trace trong cửa sổ được gộp trước.
- **Mốc** là p50 của `duration` theo khóa (`cmdb_id`, `operation_name`), trên các cửa sổ trước lỗi [`inject_ts` − 1200 s, `inject_ts` − 60 s) của case train.
  - Chỉ lấy dòng nằm trong đúng một cửa sổ, và cửa sổ đó thuộc case train.
  - **Truy vấn dev dùng mốc bỏ chính case của nó** (leave-one-case-out). Đánh giá trên test dùng mốc của cả 48 case train.
  - Span có khóa không có mốc thì bị bỏ.
- **Tỉ lệ** của một span là `duration / p50`. Dùng `duration`, không dùng thời gian tự thân, vì span client cần mang cả thời gian của bên được gọi thì mới phản ánh được độ trễ phía gọi (ghi trong nhật ký deviation).
- **Hai phía của dịch vụ S:**
  - Phía server: span có `cmdb_id` là S và không phải span client.
  - Phía client: span client của dịch vụ khác có callee là S, dùng `callee()` và `is_client()` của bước 1.
  - Mỗi phía có p95 và trung vị, tính theo luật `sorted[min(n-1, floor(p·n))]`, kèm số span. Phía có dưới 5 span ghi `null`.

### M1: thông báo nguồn vắng (cờ `--gap-aware`)

- Khi một nguồn `absent` **và không có thành phần nào thay thế nó**, tool trả nội dung sau thay cho bảng rỗng:

  `SOURCE UNAVAILABLE: <metrics|logs> are not collected for this system in this incident. Missing data is not evidence that the service is healthy; judge from the other evidence.`

- Prompt self-state được thêm một dòng **chỉ khi ít nhất một tool của request đó thực sự trả SOURCE UNAVAILABLE**:

  `- A tool answer starting with SOURCE UNAVAILABLE means the source is missing, not that the span is normal.`

- Ở lưới dưới đây, log luôn có, nên M1 chỉ có tác dụng ở điều kiện có M1 mà không có M2.

### M2: KPI độ trễ dựng từ trace (cờ `--trace-kpi`, chỉ khi metric vắng)

- **Phản hồi tool:** `search_fluctuating_metrics(service_name, timestamp)` trả JSON:

  `{"source": "trace-derived latency KPI vs training baseline (metrics unavailable)", "<S>.trace_latency_ratio_p95.server": {"baseline_ratio": 1.0, "window_ratio": x, "spans": n}, ...}`

  - JSON gồm tối đa bốn KPI: p95 và trung vị cho mỗi phía. KPI `null` thì bỏ.
  - Nếu cả bốn đều `null` hoặc tên dịch vụ không khớp (`match()`), tool trả `{"message":"No matching records found."}`.
  - Tên trường là `baseline_ratio` và `window_ratio`, không phải `regular_mean`/`current_mean`. Nhờ vậy tool không mạo danh khuôn metric.
- **Prompt self-state:** thêm một dòng.

  `- A trace-derived latency KPI compares this service with its training baseline; window_ratio well above 1 is a measured deviation, not "latency alone".`

- **Giới hạn đã biết trước:**
  - M2 gồm cả dữ liệu mới lẫn một câu nâng hạng độ trễ. Lượt dev không tách được hai phần này.
  - M2 chỉ tới được dịch vụ có span trong trace. Vì vậy dự báo trước rằng ở tầng không phủ, M2 gần như không có tác dụng (H3).

### M3: bảng bằng chứng ngoài trace được giao (cờ `--trace-expand`)

Prompt tổng hợp cuối (`U/coordinator.py:485-498`) được nối thêm một khối, đặt ngay trước dòng "Goal:":

```
Window evidence beyond this trace (all traces in the 300 s before this query, against a training baseline):
service | in this trace | traces | server p95 ratio | incoming-call p95 ratio
...
Services absent from this trace can still be the root cause.
```

- Bảng có một dòng cho mỗi dịch vụ trong `KNOWN_SERVICES["re2ob"]` (`U/config.py:71-76`), trừ `frontend` và `frontendservice`, tức 10 dòng.
- **Dòng được xếp theo tên dịch vụ, không theo điểm.** Như vậy model phải tự đọc tỉ lệ. Bảng không phải là kết quả xếp hạng đưa sẵn, và so sánh với bộ xếp hạng ở O4 mới có nghĩa.
- Tỉ lệ `null` hiển thị là `n/a`.
- M3 luôn được thêm khi cờ bật, không có điều kiện kích hoạt (ghi trong nhật ký deviation).
- **Trần ngữ cảnh:** phase 5 phải test rằng prompt cuối có M3 còn trống ít nhất 1 000 token so với 16 384, trên mọi truy vấn dev. Nếu không đạt, bỏ các dòng có cả hai tỉ lệ `n/a`. Nếu vẫn không đạt, dừng lại và báo sếp.

## 3. Tập dev (luật cố định, viết trước khi có kết quả LLM nào)

- **Ứng viên:** 240 truy vấn train, bỏ trọn 8 case đã chạy ở S1; còn lại 40 case. Thông tin phạm vi lấy từ `K/runtime/trace-coverage/coverage.csv` (SHA256 CRLF thành LF là `18bc970d…16dd27`).
- **Khóa sắp xếp:** `sha256(("telemetry-gap-dev-v1" + id).encode())` dưới dạng hex, sắp tăng dần, không có dấu phân cách. `id` là `case_id` khi xếp case, và `trace_id` khi chọn truy vấn trong một case.
- **Tầng không phủ (12 truy vấn):**
  1. Lấy các case có ít nhất một truy vấn `none`, xếp theo khóa, chọn 12 case đầu.
  2. Mỗi case lấy truy vấn `none` có khóa nhỏ nhất.
- **Tầng có phủ (13 truy vấn):**
  1. Lấy các case còn lại có ít nhất một truy vấn không phải `none`, chia theo dịch vụ lỗi; trong mỗi nhóm, xếp theo khóa.
  2. Xoay vòng các dịch vụ theo bảng chữ cái, mỗi lượt lấy case kế tiếp của dịch vụ đó. Dịch vụ đã cạn thì bỏ qua. Dừng khi đủ 13.
  3. Mỗi case lấy truy vấn không phải `none` có khóa nhỏ nhất.
- **Kết quả** (chỉ đọc cấu trúc, chưa đọc kết quả nào): 25 truy vấn.
  - Không phủ: `8101bd60…` (emailservice_socket_1), `bafdd3ef…` (recommendationservice_delay_3), `f6d1e7fe…` (checkoutservice_disk_2), `ee90717a…` (checkoutservice_cpu_3), `0be1a511…` (checkoutservice_disk_3), `d896c60f…` (recommendationservice_cpu_1), `a4827710…` (emailservice_delay_2), `56daf164…` (emailservice_socket_2), `3753f2a8…` (recommendationservice_socket_3), `4848c518…` (checkoutservice_disk_1), `00ea068b…` (recommendationservice_delay_2), `00f6d77b…` (recommendationservice_cpu_3).
  - Có phủ: 13 trace_id đầy đủ nằm trong `K/runtime/dev-set-preview.json` (SHA256 `b526e326…196a65`). Phân bố: currencyservice 4, checkoutservice 3, productcatalogservice 3, recommendationservice 3.
- Phase 5 cài luật này thành script có test. Script phải ra đúng danh sách trên; nếu lệch, dừng lại và báo.

## 4. Lưới điều kiện và ngân sách

Tên điều kiện chỉ dùng chữ thường, số và `_`, để đường dẫn `run/traces/{trace}--{tên}--s{seed}` an toàn.

| # | Tên | Metric | Log | M1 | M2 | M3 | Seed | Để đo |
|---|---|---|---|---|---|---|---|---|
| 1 | `base_metric` | repaired | author | – | – | – | 20261026 | trần khi đủ nguồn |
| 2 | `base_nometric` | absent | author | – | – | – | 20261026 | mốc chính |
| 3 | `base_nometric_s2` | absent | author | – | – | – | 20261027 | nhiễu giữa hai lượt |
| 4 | `a_metric` | repaired | author | – | – | bật | 20261026 | M3 khi đủ nguồn; an toàn |
| 5 | `a_nometric` | absent | author | – | bật | bật | 20261026 | phương pháp đầy đủ |
| 6 | `m1m3_nometric` | absent | author | bật | – | bật | 20261026 | M2 so với chỉ thông báo vắng |
| 7 | `m2_nometric` | absent | author | – | bật | – | 20261026 | đóng góp của M3 |

- **`repaired`** là tool metric có sửa, không đọc nhãn (`K/metric-repair.py`, K = 100). Nó đo cửa sổ [t − 600 s, t + 600 s), tức **có nhìn 600 giây sau truy vấn**, và gần như chỉ báo đúng dịch vụ lỗi. Điều kiện 1 và 4 vì vậy là trần có thông tin tương lai, không phải điều kiện thực tế.
- **Đóng góp riêng của M1** (bật so với tắt, khi không có gì khác) không được đo trong lượt dev.
- **Ngân sách:**
  - S1 v3 gói A chạy 36 run trong 30 271,7 giây, khoảng 14 phút mỗi run, đã gồm khởi động ([báo cáo S1 v3](analysis-261101-s1-v3-hashseed-and-evidence-loss-check.md)).
  - 7 × 25 = 175 run, khoảng 41 giờ; cộng 15% dự phòng cho M2 và M3 là khoảng 47 giờ T4.
  - Sếp duyệt đủ 7 điều kiện ngày 2026-11-02.
- **Nơi chạy:** cả hai nơi đều dùng T4, FP16, cùng model và cùng các trần như S1 v3. Mỗi GPU chạy một run tại một thời điểm.
  - **Kaggle T4 ×2:** hai server, mỗi GPU một server, trong quota 10 giờ còn lại.
  - **Modal T4:** tối đa 10 container, mỗi container 2 core và 12 GiB, trong 30 USD credit.
- **Luật chia nơi chạy** (đặt trước khi có kết quả; theo truy vấn, nên mọi so sánh cặp đều cùng một nơi):
  1. Trong mỗi tầng, xếp truy vấn theo `sha256(("telemetry-gap-site-v1" + trace_id).encode())` tăng dần.
  2. 5 truy vấn đầu của tầng không phủ và 5 truy vấn đầu của tầng có phủ chạy trên Kaggle với cả 7 điều kiện, tức 70 run.
  3. 15 truy vấn còn lại chạy trên Modal, tức 105 run.
  4. Run Kaggle chưa xong khi hết quota thì chạy trên Modal và được ghi lại. Nơi chạy được báo cùng mọi kết quả.
- **Thứ tự trong mỗi nơi:** chạy theo truy vấn trước, rồi tới điều kiện theo thứ tự 2, 3, 5, 1, 4, 7, 6. Như vậy nếu dừng giữa chừng, các truy vấn đã chạy có đủ cặp so sánh.

## 5. Chỉ số và quy tắc tính

- **Chính:** R@1 và MRR theo truy vấn, theo điểm của tác giả (`author-score.txt`), báo theo tầng phủ và theo dịch vụ lỗi.
- **Run dừng:** run dừng vì ngân sách, deadline hay lỗi được tính R@1 = 0 và MRR = 0, giống nhau ở mọi điều kiện. Báo kèm bảng số run dừng theo điều kiện. Nếu một điều kiện có quá 3 run dừng, kết luận về điều kiện đó ghi là "không đọc được".
- **Phụ:**
  - Số truy vấn có `cartservice` là top1.
  - Số token prompt lớn nhất và trung vị mỗi run.
  - Ở điều kiện có M2: số run có ít nhất một lời gọi metric hỏi đúng dịch vụ lỗi (khớp bằng `match()`).
  - Ở điều kiện có M3: số run mà top1 là dịch vụ không có trong trace truy vấn (khớp bằng `match()`, không phân biệt hoa thường).
- **Đối chứng không dùng LLM trên cùng 25 truy vấn**, tính trên CPU:
  - **Bộ xếp hạng p95 cửa sổ trước truy vấn.** Quy tắc đóng băng ở `K/explore-window-ranker.py`: điểm là max của hai phía p95, phía `null` bị bỏ, không xếp frontend, hòa thì xếp theo tên. Bộ này biết cùng thông tin với bảng M3. **Đây là đối chứng duy nhất được dùng trong luật Go.**
  - Chỉ để mô tả, đều có gắn nhãn "biết `inject_ts`": `latency_either` cả cửa sổ lỗi, TraceRCA, MicroRank (bản RCAEval, chỉ trả 5 operation), BARO (cửa sổ khác bài RCAEval). Số lấy từ phase 4.

## 6. Giả thuyết có hướng và câu kết cục (tính bằng script có test; mô tả, n = 25)

Gọi **thắng** là truy vấn mà điều kiện X đúng R@1 còn điều kiện Y sai, **thua** là ngược lại, và **ròng** = thắng − thua.

- **N (nhiễu):** số cặp lệch R@1 giữa `base_nometric` và `base_nometric_s2`, ký hiệu `d_noise`.
- **H1 → O1 (chính):** `a_nometric` tốt hơn `base_nometric`. Báo thắng, thua, ròng và hiệu R@1.
- **H2 → O2:** trên tầng không phủ (12 truy vấn), `a_nometric` và `a_metric` có R@1 lớn hơn 0 và lớn hơn hai điều kiện base tương ứng. Báo số truy vấn đúng.
- **H3 → O3:**
  - Ở tầng không phủ, `m2_nometric` không khác `base_nometric` quá 1 truy vấn, vì M2 không tới được dịch vụ lỗi.
  - Ở tầng có phủ, `m2_nometric` tốt hơn `base_nometric`.
  - Ở cả hai tầng, `a_nometric` tốt hơn `m2_nometric`; đây là đóng góp của M3.
  - `a_nometric` so với `m1m3_nometric` cho thấy M2 có hơn việc chỉ báo nguồn vắng hay không.
- **H4 → O4:** R@1 của `a_nometric` lớn hơn hoặc bằng bộ xếp hạng p95 trên cùng 25 truy vấn.
- **O5 (an toàn):** cả hai điều kiện sau phải đúng.
  - Trên tầng có phủ, ròng của `a_metric` so với `base_metric` lớn hơn hoặc bằng −1.
  - Số truy vấn có `cartservice` là top1 ở `a_nometric` trừ số đó ở `base_nometric` nhỏ hơn hoặc bằng 2.

### Luật go/no-go (tính bằng script, không chọn sau)

- **Chưa đủ bằng chứng:** khi điều kiện 1, 2, 3, 4 hoặc 5 chưa chạy xong, hoặc một trong năm điều kiện đó "không đọc được". Đây là kết luận mặc định, không phải Go.
- **Go, bài phương pháp:** cả bốn điều kiện sau cùng đúng.
  - Ở O1: thắng ≥ 6, thua ≤ 2, và ròng ≥ `d_noise` + 3.
  - O5 đạt.
  - R@1 của `a_nometric` ≥ R@1 của bộ xếp hạng p95.
- **Go, bài đo lường:** O1 đạt điều kiện về thắng, thua và ròng như trên, nhưng `a_nometric` thua bộ xếp hạng p95. Khi đó bài nhấn vào phép đo phạm vi trace và vào việc agent LLM bỏ phí tín hiệu, không tuyên bố phương pháp LLM tốt hơn.
- **No-go:** mọi trường hợp còn lại. Báo cáo đúng như vậy, rồi đề xuất đổi trọng tâm dựa trên vị trí mất bằng chứng đo được.
- O2, O3 và các chỉ số phụ chỉ để mô tả, không vào luật.

## 7. Ngoài phạm vi lượt dev

- **Baseline "agent tự do truy vấn bảng thô"** (theo "Free to Look") được hoãn tới đánh giá cuối nếu có Go. Nó là điều kiện bắt buộc trước khi viết bài.
- **Không chạy LLM trên test split, val hay RE2-TT.** Val chỉ dùng cho bộ xếp hạng p95 trên CPU (mục 1). Nếu sau này quy tắc M2/M3 đổi, quy tắc mới phải được kiểm lại trên val bằng CPU trước khi mở test.
- **Không đổi** model, cấu hình sampling, trần ngữ cảnh 16 384, ngân sách tool hay deadline so với S1 v3.

## 8. Phơi nhiễm và giới hạn

- **Đã thấy trước khi viết prereg:**
  - Kết quả S1 (8 case, đã loại khỏi tập dev).
  - Bảng phạm vi trace.
  - Kết quả baseline không dùng LLM.
  - Hai lượt khám phá bộ xếp hạng trên 240 truy vấn train, gồm cả 25 truy vấn dev; lượt sau có mốc leave-one-case-out.
- **Hệ quả:** việc chọn p95, 300 giây và hai phía đã được tối ưu trên dữ liệu chứa tập dev. Mốc leave-one-case-out bỏ được lợi thế "mốc từ chính case", nhưng không bỏ được thiên lệch do chọn quy tắc. Số trên val (mục 1) là kiểm tra độc lập duy nhất hiện có, và nó sụt gần một nửa. Vì thế mọi con số của bộ xếp hạng trên train, gồm cả 12/25 trên tập dev, phải được coi là lạc quan.
- **Quy mô:** n = 25 truy vấn, một seed (thêm một seed cho `base_nometric` để ước nhiễu), temperature 0,7. Mọi so sánh là mô tả.
- **Gộp thành phần:** M2 gộp dữ liệu và câu nâng hạng độ trễ. Đóng góp riêng của M1 không được đo. Điều kiện 1 và 4 dùng tool metric có nhìn tương lai.

## 9. Việc của phase 5 suy ra từ đặc tả này

1. **Script chọn tập dev** và test; phải ra đúng danh sách ở mục 3.
2. **Script dựng `window-kpi.json`** (mốc leave-one-case-out cho dev) và test, gồm:
   - test không nhìn sau `t_q`;
   - test không dùng nhãn và không dùng `inject_ts` của truy vấn;
   - test hai phía;
   - test khóa không có mốc.
3. **Sửa `K/smoke-worker.py`** để thêm ba cờ và chèn ở `Guard.post` và `source_response`.
4. **Sửa `K/kaggle-runtime.py`:** `worker_options` truyền thêm ba cờ.
5. **Sửa `K/add-condition-runs.py`:** thêm 7 điều kiện, cho seed theo từng điều kiện, và cho chọn tập điều kiện theo từng kernel.
6. **Sửa `K/prepare-bundle.py`** để đưa `window-kpi.json` vào bundle.
7. **Test** giống từng byte khi tắt cờ; test dòng prompt M1 chỉ xuất hiện khi có SOURCE UNAVAILABLE; test biên ngữ cảnh 1 000 token.
8. **Script tính câu kết cục và luật go/no-go** (phase 7) có test trên dữ liệu tổng hợp, viết xong trước khi tải output.
9. **Kaggle hai GPU và runner Modal T4** theo luật chia nơi chạy ở mục 4.

## Quyết định khi duyệt (2026-11-02)

1. **Lưới:** giữ đủ 7 điều kiện, 175 run.
2. **Nơi chạy:** T4 trên Kaggle (hai GPU) và Modal. Sếp từ chối đổi sang model lớn hơn hoặc GPU khác, để giữ cùng model và cùng loại GPU với S1 v3.
3. **Ngưỡng Go:** giữ như mục 6; sếp không yêu cầu đổi.
