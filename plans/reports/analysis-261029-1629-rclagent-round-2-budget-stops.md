# Phân tích các lượt vòng 2 dừng vì trần ngân sách của harness — 2026-10-29

**Tóm tắt.**
- **8 lượt dừng vì trần, cả 8 đều là `no_metric`.** Tổng số lượt thất bại là 10.
  - 5 lượt dừng vì trần 4 vòng tool mỗi span.
  - 3 lượt dừng vì hết 160 request.
- **Hai loại trần có cơ chế khác nhau.** Đây là quan sát, không phải kết luận nhân quả.
  - **Trần 4 vòng tool:** cả 5 lượt dừng ở cùng một kiểu span: `frontendservice` gọi `ProductCatalogService` (`GetProduct` hoặc `ListProducts`), trên 4 trace thuộc cả hai gói. Ở điều kiện `metric`, span này kết thúc sau 1 vòng tool. Ở `no_metric`, model đi lần lượt qua log của các service khác, và từ vòng 3 trở đi không còn nhận được dòng dữ liệu mới nào.
  - **Trần 160 request:** cả 3 lượt thuộc trace 39 span của `checkoutservice_mem_1`. Không span nào chạm trần vòng tool. Lượt hết request khi đang ở bước consolidation, và cần ít nhất 168–172 request mới chạy xong. Vì vậy tăng trần mỗi span không cứu được nhóm này.
- **Có nên thử ngân sách cao hơn: nên, dưới dạng một lần chạy kiểm độ nhạy riêng.** Cấu hình đề xuất ở mục 4; chưa chạy.
- **Cơ sở cho đề xuất:**
  - Hai trần này giải thích 8/10 lượt thất bại, và toàn bộ phần thua của A ở phép bỏ metric.
  - Seed cố định cho ra đầu ra lặp lại được. Cả 36 lượt pass ở cả hai vòng đều có điểm và top-1 trùng khớp. Vì vậy một lần chạy chỉ đổi trần sẽ cô lập được tác động của trần.

Nguồn: `runtime/kaggle-output-{a,b}-r2-v1/rclagent-smoke/rclagent-smoke-results.zip`. SHA256 là `c018dd9f…83cb` và `e8bb1317…b53d`, khớp file `.sha256`. Mọi đường dẫn tính từ `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`.

Số liệu được tính bằng `analyze-completion-and-budget-stops.py`. Output nằm ở `runtime/analysis-missing-source-completion-r2/budget-stops.json`. Log của từng lượt là `run/traces/<run_id>/events.jsonl` trong ZIP.

## 1. Cách đọc log

**Quy ước đếm.**
- **Lời gọi logic:** một request có `attempt` 0. Các request có `attempt` lớn hơn 0 là lần hỏi lại vì tool call sai (malformed). Chúng được đếm riêng, không tính là agent tiếp tục truy vấn.
- **Vòng tool:** một lời gọi logic mà response có tool call, kèm các `tool_result` theo sau.
- **Hội thoại span:** các lời gọi cùng `span_id` và `operation`.

**Cách upstream chạy và các trần của harness.**
- Upstream chạy `self_state_verification` cho mọi span, sau đó `consolidate` mỗi span một lần, rồi một lời gọi tổng hợp cuối (`coordinator.py`, hàm `inspect_trace`).
- Vòng lặp tool của upstream không có trần. Nó chỉ dừng khi model trả lời không kèm tool call, hoặc khi lặp lại đúng nguyên bộ tool call đã gửi trước đó (`coordinator.py:243-264`).
- Trần 4 vòng mỗi span là của harness (`smoke-worker.py`, hàm `chat`): response thứ 5 trong một hội thoại span mà vẫn có tool call thì lượt dừng.
- Trần 160 request (tính cả hỏi lại) và deadline 30 phút cũng là của harness (`smoke-worker.py:458-459`).

**Tiêu chí phân loại một vòng tool trong hội thoại.** Đây là tiêu chí cơ học, không đánh giá giá trị chẩn đoán.
- `new_rows`: có ít nhất một kết quả có dòng dữ liệu, với nội dung (sha256) chưa xuất hiện trước đó.
- `repeated_query`: mọi truy vấn `(tool, service, timestamp)` đều đã có trong hội thoại.
- `new_query_no_rows`: truy vấn mới nhưng không trả về dòng nào.

## 2. Năm lượt dừng vì trần 4 vòng tool mỗi span

| Gói | Run | Span dừng | Request của hội thoại |
|---|---|---|---|
| A | `30e3c732…--no_metric--s20261026` (`emailservice_delay_3`) | `f9a14c4b7dff1d98`, frontend → `GetProduct` | 6–10 |
| A | `30e3c732…--no_metric--s20261028` | `f9a14c4b7dff1d98`, frontend → `GetProduct` | 6–10 |
| A | `99f095ae…--no_metric--s20261028` (`currencyservice_loss_3`) | `e67675c47ea19aec`, frontend → `ListProducts` | 8–12 |
| B | `7bbfa606…--no_metric--s20261028` (`recommendationservice_socket_1`) | `e3e7fd70315e4e56`, frontend → `GetProduct` | 22–26 |
| B | `272a47c2…--no_metric--s20261028` (`recommendationservice_cpu_2`) | `c40c45fb06f6f6aa`, frontend → `ListProducts` | 8–12 |

**Dữ kiện quan sát được.**
- **Thứ tự truy vấn giống nhau ở cả 5 hội thoại:**
  1. Vòng 1: log và metric của `productcatalogservice`. Cả hai rỗng, vì metric bị bỏ và log không có dòng.
  2. Vòng 2: log `cartservice`, có dòng dữ liệu (`new_rows`).
  3. Vòng 3: log `checkoutservice`, rỗng.
  4. Vòng 4: log `paymentservice`, rỗng.
- **Response thứ 5 vẫn gọi tool, nên harness dừng lượt:**
  - 3 lượt hỏi log `shippingservice`, là truy vấn mới;
  - 2 lượt hỏi lại metric `productcatalogservice` ở vòng 1 (A s26 và B `7bbfa606` s28). Đây là truy vấn lặp, nhưng bộ tool call khác vòng 1 (chỉ metric, không kèm log), nên điều kiện dừng do lặp của upstream không bắt được.
- **Không có lần hỏi lại vì tool call sai trong 5 hội thoại này.** Hai lượt B có 1 lần hỏi lại, nhưng ở span khác.
- **Cùng span, khác điều kiện và seed:**
  - Ở `metric`, span này chỉ dùng 2 lời gọi (1 vòng tool rồi kết luận) ở cả 3 seed, cả 4 trace.
  - Ở `no_metric`, span này dùng 3–5 lời gọi. Mọi lượt dùng tới lời gọi thứ 5 đều bị dừng.
- **Phân bố số lời gọi self-state mỗi span, gộp mọi lượt:**
  - A, `no_metric`: 2 lời gọi ở 6 span, 3 ở 196, 4 ở 56, 5 ở 14.
  - A, `metric`: 2 lời gọi ở 298 span, 3 ở 23, 4 ở 5, 5 ở 10.
  - B có cùng xu hướng.
  - Vậy ở `no_metric`, model gọi thêm vòng tool trên phần lớn các span, không chỉ ở span bị dừng.

**Diễn giải, chưa được kiểm chứng.**
- Khi metric trả về rỗng, model có vẻ chuyển sang dò log của các service dọc chuỗi gọi checkout.
- Bằng chứng mới thực sự xuất hiện ở vòng 2 (`cartservice`). Hai vòng sau không có dòng dữ liệu.
- Response thứ 5 vừa có truy vấn mới vừa có truy vấn lặp. Vì vậy chưa xác định được agent đang thu thập thông tin hữu ích hay đang lặp vòng.
- Log không cho biết nếu được chạy tiếp, model sẽ tự kết luận sau bao nhiêu vòng, hoặc có tìm ra service gốc không. Root cause của các case này không nằm trong các service đã hỏi, nhưng điều đó không cho phép suy ra kết quả nếu chạy tiếp.

## 3. Ba lượt dừng vì hết 160 request

Cả 3 lượt là `5f7a7727…--no_metric--s2026102{6,7,8}` (`checkoutservice_mem_1`, trace 39 span, gói A).

| Seed | Lời gọi self-state | Consolidation xong / 39 | Hỏi lại | Request cần tối thiểu | `metric` cùng seed | Thời gian |
|---|---|---|---|---|---|---|
| 26 | 132 (3,38/span) | 28 | 0 | 172 | pass, 123 request | 1.021 s |
| 27 | 128 (3,28/span) | 32 | 0 | 168 | pass, 123 request | 1.028 s |
| 28 | 129 (3,31/span) | 30 | 1 | 170 | pass, 122 request | 1.064 s |

**Dữ kiện quan sát được.**
- Cả 39 span đã xong `self_state_verification`. Lượt dừng ở request 160, đang ở bước `consolidate`; mỗi consolidation chỉ là 1 lời gọi, không có tool.
- Không span nào vượt trần 4 vòng; nhiều nhất là 5 lời gọi trên một span.
- "Request cần tối thiểu" = số request đã dùng + số consolidation còn lại + 1 lời gọi tổng hợp cuối, với giả định không phải hỏi lại thêm lần nào.
- Ở `metric` cùng seed, trace này dùng trung bình 2,1 lời gọi mỗi span và 122–123 request.
- **Truy vấn trong 3 lượt `no_metric`:**
  - 142–148 kết quả tool, trong đó 126–134 truy vấn khác nhau và 14–20 truy vấn lặp.
  - Chỉ 11–12 kết quả có dòng dữ liệu, và chúng chỉ gồm 2 nội dung khác nhau.
  - Phần lớn vòng tool thêm vào trả về rỗng.

**Tăng trần mỗi span có giúp được không.** Không. Trần mỗi span không ràng buộc ở 3 lượt này, và nâng nó chỉ cho phép thêm vòng tool, tức là tốn thêm request. Lượt hết request vì tổng số lời gọi cần cho 39 span: ước tính 39 × 3,3 + 39 + 1 ≈ 169 > 160. Muốn các lượt này chạy xong thì phải nâng trần request. Ngay cả khi nâng, log cũng không cho biết lượt có ra đáp án đúng hay không.

## 4. Đề xuất một cấu hình kiểm độ nhạy (chưa chạy)

**Thay đổi.** Chỉ đổi ba giới hạn, áp dụng như nhau cho cả ba điều kiện:

| Giới hạn | Vòng 2 | Kiểm độ nhạy | Căn cứ |
|---|---|---|---|
| Vòng tool mỗi span | 4 | 8 | Mọi lượt chạm trần đều dừng ngay vòng kế tiếp. Nâng gấp đôi để thấy span có tự kết thúc hay không. |
| Request mỗi lượt (tính hỏi lại) | 160 | 320 | Cần tối thiểu 168–172 cho trace 39 span. 320 cho phép trung bình khoảng 7,2 lời gọi mỗi span ở trace lớn nhất (39 × c + 40 ≤ 320). |
| Deadline mỗi lượt | 1.800 s | 2.400 s | Quan sát khoảng 6,5 s mỗi request, nên 320 request mất khoảng 2.080 s. |

**Giữ nguyên:**
- 8 case, cùng trace, cùng 3 seed, 3 điều kiện, tổng 72 lượt;
- model Qwen3-4B, vLLM 0.10.2, context 16k, temperature 0,7;
- prompt, `metric-repair.py`, ngân sách kết quả tool;
- chính sách hỏi lại (tối đa 3 lần, seed suy ra);
- điều kiện dừng của upstream khi lặp nguyên bộ tool call.

**Thay đổi runtime cần làm khi dựng gói.**
- Trần vòng tool hiện viết cứng trong `smoke-worker.py` (hàm `chat`, các so sánh `> 4` và `>= 4`); 160 và 1.800 viết cứng ở `smoke-worker.py:458-459`.
- 1.800 còn được viết cứng ở `kaggle-runtime.py:98, :645`.
- Ba giá trị này nên thành tham số, ghi vào `settings.json` và manifest.
- Gói mới cũng mang theo các sửa F5/F2 của runtime, và notebook dựng lại cùng lúc.

**Chi phí dự kiến.**
- Vòng 2 mất 24.028 s (A) và 26.276 s (B) thời gian chạy trace.
- Các lượt không chạm trần dự kiến cho kết quả y hệt nhau (xem mục 5).
- Phần tăng thêm đến từ 8 lượt từng chạm trần:
  - 3 lượt hết request: khoảng +100–150 s mỗi lượt nếu dừng gần 170 request;
  - 5 lượt chạm trần vòng tool: từ 50–200 s lên khoảng 800–1.100 s, bằng một lượt đầy đủ.
- Ước tính mỗi gói khoảng 7,5–8 giờ T4, hai kernel chạy song song, tổng khoảng 15–16 giờ GPU T4.
- Trường hợp xấu nhất, khi 8 lượt đều chạy tới deadline 2.400 s: gói A khoảng 9,8 giờ, vẫn dưới giới hạn 12 giờ của Kaggle.

**Điều kiện dừng.**
- Mỗi lượt vẫn dừng theo các trần mới, deadline mới, hoặc lỗi giao thức như hiện nay, và ghi `failed` kèm lý do.
- Server model chết thì dừng phiên.
- Không chạy lại lượt đã xong. Không đổi giới hạn sau khi đã thấy kết quả.

**So sánh và báo cáo.**
- Báo riêng thành cấu hình kiểm độ nhạy, đặt cạnh vòng 2, không thay kết quả hay kết luận pilot đã nhận.
- **Chỉ số so sánh:**
  - tỷ lệ hoàn tất hợp lệ theo điều kiện;
  - R@1/MRR trên toàn bộ lượt (lượt lỗi tính 0);
  - R@1/MRR trên lượt hoàn tất hợp lệ, kèm mẫu số;
  - các cặp mà cả hai lượt đều hoàn tất;
  - riêng 8 lượt từng chạm trần: trạng thái, số request, số vòng của span từng bị dừng.
- **Kiểm điều kiện:** các lượt không chạm trần ở vòng 2 phải có đầu ra model giống vòng 2. Nếu khác thì ghi lại, và không quy phần khác biệt cho thay đổi trần.

## 5. Độ lặp lại giữa vòng 1 và vòng 2

Có 36 lượt pass ở cả hai vòng. Cả 36 có R@1, MRR và top-1 giống hệt nhau.
- Với 30/36 lượt, mọi nội dung và tool call của model trùng nhau, so sau khi bỏ id ngẫu nhiên.
- 6 lượt còn lại chỉ khác ở response cuối cùng, nhưng điểm vẫn như nhau.
- Chưa rõ nguyên nhân của 6 khác biệt này.

Đây là cơ sở để kỳ vọng một lần chạy chỉ đổi trần sẽ giữ nguyên các lượt không bị trần ảnh hưởng. Đó vẫn là kỳ vọng, không phải điều chắc chắn: tính tất định của vLLM khi sampling có seed không được đảm bảo chính thức.
