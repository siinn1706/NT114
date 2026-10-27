# Thiết kế ngân sách tool result cho RCLAgent — 2026-10-27

**Kết luận:** đề xuất phương án C (rút gọn theo bậc thang), ngân sách 2.048 token mỗi phản hồi `search_logs`, áp trong wrapper của harness, không sửa upstream. Trên 450 error trace của 90 ca, phương án này đưa prompt vòng 1 lớn nhất từ 135.618 xuống 1.697 token mà không bỏ một dòng log nào, không bỏ dòng ERROR/EXCEPTION nào, và không đổi byte nào của các query đúng chỉ dẫn. Cái giá là sai lệch có hệ thống so với tác giả: khi model hỏi `cartservice` hoặc `frontend`, phản hồi bị đổi ở **mọi** trace, không chỉ ở `recommendationservice_loss_1` như dự kiến ban đầu. Chưa sửa harness, chưa chạy Kaggle; chờ sếp duyệt.

Phạm vi lượt này: chỉ CPU, không gọi model hay GPU, không đọc nhãn hay kết quả. Không đổi upstream, dữ liệu, split hoặc gói Kaggle. Không commit/push. Working tree chưa commit của phiên trước được giữ nguyên.

## 1. Sự kiện nền đã kiểm lại

- Tool tác giả (`tool_server.py`, commit `3052e7a`) trả `search_logs` dưới dạng CSV thô của mọi dòng non-INFO/DEBUG trong ±60 giây, lọc service bằng `str.contains`. Không có giới hạn kích thước.
- Kết quả tool chỉ đi vào prompt của `self_state_verification`. `consolidate` và synthesis chỉ nhận output của model (≤512 token mỗi span), nên ngân sách tool result không chạm hai bước đó.
- Lượt đo mới tái tạo đúng lượt quét trước: 450/450 trace khớp `own_max_tokens`, `any_max_tokens` và token theo từng service trong `tool-response-scan.csv`.
- `search_fluctuating_metrics` lớn nhất chỉ 10 token trên mọi (service, giây) đã đo, tức luôn là thông báo "không có dữ liệu". Vì vậy ngân sách chỉ cần cho `search_logs`.
- Log trong cửa sổ overflow rất lặp. Mỗi cửa sổ `cartservice` chỉ có tối đa 4 mẫu thông điệp (`GetCartAsync called with userId=…`, `AddItemAsync …`, `EmptyCartAsync …`, `Checking CartService Health`). Mỗi cửa sổ `frontend` có tối đa 3 thông điệp khác nhau, trong đó có `severity: error, message: request error`.

## 2. Nơi áp dụng (chung cho mọi phương án)

- Vị trí: wrapper `get_tool` trong [smoke-worker.py](../261026-1713-rclagent-tai-hien-toi-thieu/kaggle/smoke-worker.py). Ngân sách chạy sau `original_get` và sau kiểm `[tool error]`, trước khi trả kết quả cho upstream. Tool server, endpoint, prompt và vòng tool của tác giả giữ nguyên.
- Endpoint: chỉ `search_logs`. Metric không bị áp vì tối đa 10 token, áp vào sẽ không đổi phản hồi nào. Nếu metric vượt context, guard hiện tại vẫn dừng.
- Kích hoạt: phản hồi ≤ B token (tokenizer Qwen đúng revision mà guard đã nạp) được trả **nguyên byte**. Chỉ phản hồi > B mới bị rút gọn. Quy tắc chỉ đọc nội dung phản hồi và giây được hỏi; không dùng tên service, ca, nhãn hay kết quả.
- An toàn: phản hồi không đúng định dạng CSV log của tác giả thì không bị viết lại. Nếu phản hồi như vậy vượt B, hoặc phương án không xếp vừa, harness dừng (`HarnessStop`) thay vì đoán. Phản hồi có dòng không bao giờ bị biến thành rỗng hay "không tìm thấy".
- Ghi vết: mỗi lần kích hoạt ghi vào `events.jsonl` SHA256, byte và token của phản hồi gốc cùng phản hồi đã rút gọn và dạng rút gọn, để kiểm lại sau.

Code các phương án: [tool-result-budget.py](../261026-1713-rclagent-tai-hien-toi-thieu/work/scripts/tool-result-budget.py), hàm thuần (body, giây, B, bộ đếm token).

## 3. Ba phương án

**A. Cắt dòng (`cap`).** Giữ nguyên văn các dòng CSV gốc theo thứ tự ưu tiên xác định: severity error/fatal/critical, rồi warning, rồi dòng khác có chữ "error"/"exception", rồi phần còn lại. Nếu ngang hạng thì ưu tiên dòng gần giây được hỏi hơn, rồi theo thứ tự gốc. Dòng được giữ in theo thứ tự gốc. Dòng đầu ghi `truncated: X of Y rows shown`, kèm số dòng bị bỏ theo severity.

**B. Gộp theo mẫu (`template`).** Gộp các dòng cùng (cmdb_id, log_name, severity, thông điệp đã che phần biến). UUID và mọi từ có chữ số được che thành `<*>`. Mỗi nhóm giữ số lần, giây đầu/cuối, số giá trị khác nhau và giá trị nguyên văn đầu tiên. Bỏ `log_id`. Nếu vẫn vượt B thì dừng, không cắt.

**C. Bậc thang (`ladder`), đề xuất.** Chọn bước ít mất thông tin nhất mà vừa ngân sách:
1. Gộp dòng **trùng hệt** (cùng cmdb_id, log_name, value), giữ số lần và giây đầu/cuối. Chỉ mất `log_id` và giây của từng dòng.
2. Nếu bước 1 chưa vừa, gộp theo mẫu như B.
3. Nếu bước 2 vẫn chưa vừa, giữ các mẫu theo thứ tự ưu tiên của A và ghi rõ `truncated`. Trên RE2-OB, bước này không bao giờ xảy ra; nó chỉ là chốt an toàn.

Model thấy một dòng đầu trong ngoặc vuông, rồi đến CSV. Ví dụ đúng request đã làm v6 dừng (`cartservice`, giây `1708475368`, gốc 1.557 dòng, 124.953 token):

```text
[harness tool-result budget 2048 tokens: 1557 rows merged into 4 message templates (variable parts (UUIDs and words containing digits) masked as <*>); count, first/last second, distinct values and the first verbatim value kept; log_id omitted; no row omitted]
cmdb_id,log_name,severity,message_template,count,first_timestamp,last_timestamp,distinct_values,first_value
cartservice,log_cartservice,unknown,GetCartAsync called with userId=<*>,1306,1708475308,1708475428,50,"severity: unknown, message: GetCartAsync called with userId=51123fda-…"
...
```

Kết quả: 454 token. Với `frontend` ở `recommendationservice_loss_1` (771 dòng, 34.963 token), bước 1 đủ: 3 dòng, 192 token, giữ nguyên văn cả 3 thông điệp. Mẫu đầy đủ nằm trong `work/tool-result-budget-impact/samples/`.

Dòng thông báo là cần thiết. Nếu thiếu, model có thể đọc `count` thành một dòng log, hoặc tưởng đó là đầu ra gốc của tool. Dòng này không nhắc "sai lệch so với tác giả", vì điều đó không giúp model suy luận.

## 4. Chọn ngân sách

Số đo trên 12.605 span: prompt self-state khi chưa có vòng tool tối đa 932 token. Một vòng có hai lời gọi tool (phần khung, kết quả rỗng) thêm tối đa 103 token. Metric tối đa 10 token. Model có thể viết tối đa 512 token văn bản kèm lời gọi tool ở mỗi vòng. Trường hợp xấu nhất của self-state, với 4 vòng và phản hồi log ở đúng mức B:

932 + 4 × (103 + 512 + B + 10) + 512 ≤ 16.384 ⇒ B ≤ 3.110.

| B | Trường hợp xấu nhất 4 vòng | Vừa 16.384? |
|---:|---:|---|
| 1.024 | 8.040 | có |
| **2.048** | **12.136** | **có, dư 4.248** |
| 4.096 | 20.328 | không |
| 8.192 | 36.712 | không, chỉ bảo đảm khoảng 1 vòng |

Chọn 2.048 vì đây là lũy thừa 2 lớn nhất vẫn bảo đảm đủ 4 vòng. Với phương án C, phản hồi đã rút gọn lớn nhất chỉ 461 token, nên B thực chất là ngưỡng: phản hồi nào vẫn được giữ nguyên byte. Giữa 1.024 và 2.048 không có phản hồi nào, nên hai mức đổi đúng cùng một tập phản hồi. Còn một rủi ro không chặn hết được: model gọi nhiều `search_logs` trong cùng một vòng. Ví dụ 2 lời gọi × 2.048 × 4 vòng vẫn có thể vượt context. Khi đó guard dừng như hiện nay, không cắt.

## 5. Tác động đo trên CPU

Cách đo giống [lượt quét trước](scan-261027-1010-re2ob-tool-response-overflow.md): thân endpoint gốc trên dữ liệu preprocess đầy đủ, `build_trace_graph` và `self_state_verification` thật với `chat_api` giả, đếm bằng chat template Qwen `cdbee75`. Có 1.560 phản hồi log khác nhau vượt 1.024 token (780 `cartservice`, 780 `frontend`). Cả 1.560 phản hồi đều đọc/ghi lại CSV khớp byte, nên phần giữ nguyên văn đúng là dữ liệu gốc.

**Query đúng chỉ dẫn:** 0 phản hồi bị đổi, ở mọi phương án và mọi B. Phản hồi được trả nguyên byte vì lớn nhất chỉ khoảng 800 token (prompt vòng 1 tối đa 1.714).

**Token vòng 1 lớn nhất theo service được hỏi (B = 2.048):**

| Service | Gốc | A cắt dòng | B mẫu | C bậc thang |
|---|---:|---:|---:|---:|
| cartservice | 135.618 | 3.066 | 1.476 | 1.476 |
| frontend | 35.982 | 3.063 | 1.265 | 1.211 |
| productcatalogservice | 1.697 | 1.697 | 1.697 | 1.697 |
| các service khác | ≤ 1.666 | không đổi | không đổi | không đổi |
| Trace còn có thể overflow ở 16.384 | 450 | 0 | 0 | 0 |

**Phạm vi thay đổi**, đếm theo số trace mà ít nhất một giây của span cho phản hồi bị đổi nếu model hỏi service đó:

| B | cartservice | frontend | Ca bị chạm |
|---:|---:|---:|---:|
| 1.024 / 2.048 | 450 | 450 | 90/90 |
| 4.096 | 450 | 445 | 90/90 |
| 8.192 | 450 | 114 (train 55, val 17, test 42) | 90/90 |

Dự kiến "chỉ `frontend` ở `recommendationservice_loss_1`" không đúng với ngân sách 2.048. Phản hồi `frontend` có trung vị 7.436 token, nhỏ nhất 2.301: không gây overflow vòng 1, nhưng vượt ngân sách 4 vòng. Chính trace smoke cũng có phản hồi `frontend` 7.888 token bị đổi nếu model hỏi `frontend` (lượt v6 hỏi `frontendservice`, phản hồi rỗng, nên không bị đổi).

**Thông tin giữ lại trên 1.560 phản hồi bị đổi (B = 2.048):**

| | A cắt dòng | B mẫu | C bậc thang |
|---|---:|---:|---:|
| Dòng gốc | 1.210.188 | 1.210.188 | 1.210.188 |
| Dòng được đại diện (nguyên văn hoặc qua số lần của nhóm) | 50.981 (4,2%) | 1.210.188 | 1.210.188 |
| Dòng ERROR/EXCEPTION gốc | 1.231 | 1.231 | 1.231 |
| Dòng ERROR/EXCEPTION bị bỏ | **807** (ở 5 phản hồi) | 0 | 0 |
| Thông điệp lỗi khác nhau không còn nguyên văn | 0/22 | 0/22 | 0/22 |
| Dạng | cắt 1.560 | mẫu 1.560 | trùng hệt 780 (`frontend`), mẫu 780 (`cartservice`), cắt 0 |
| Token lớn nhất sau rút gọn | 2.048 | 461 | 461 |

- A làm mất tín hiệu lỗi thật. Ví dụ `frontend` tại giây `1705389232` có 241 dòng `request error` trên 280 dòng; A ở B = 2.048 bỏ 196 trong 241 dòng đó. Thông điệp vẫn còn, nhưng mất tần suất. A còn tốn ngân sách cho các dòng gần như giống hệt nhau.
- B và C giữ đủ mọi dòng theo số lần. Với `frontend`, C chỉ mất `log_id` và giây của từng dòng, còn giây đầu/cuối và số lần; B còn che phần biến không cần thiết.
- Với `cartservice`, B và C mất giá trị cụ thể của userId/productId/quantity. Chỉ còn số giá trị khác nhau và giá trị đầu tiên.

## 6. Tác động phương pháp

- **Đây là sai lệch so với RCLAgent gốc.** Tác giả đưa CSV thô không giới hạn vào context. Với `cartservice` và `frontend`, model của ta thấy bản tóm tắt thay cho dòng thô, ở mọi ca. Mọi ràng buộc khác giữ nguyên: upstream, prompt, model/revision, sampling, context 16.384, output 512/1.024, retry 3, 4 vòng tool/span, 160 requests, 1.800 giây, concurrency 1, recursion-of-thought, một backbone, nhãn chỉ ở scoring. Guard không cắt context vẫn giữ.
- **So với Table I:** số đích RE2-OB (RCLAgent, Qwen-3.6-Plus, R@1 56,67 = 51/90) dùng backbone API đóng, context dài, không có ngân sách. Theo [giao thức](../261024-0858-tong-quan-1000-q1-chon-bai-nen-rca-thieu-telemetry/design/reproduction-protocol.md) §0 và giai đoạn 2, kết quả 4B/T4 đã là bản thích nghi để kiểm tính khả thi, không phải tái hiện số. Ngân sách thêm một nguồn khác biệt nữa, nên không được so trực tiếp với Table I. Không thể tách riêng tác động của ngân sách trên cấu hình này, vì không có lượt đối chứng không ngân sách nào chạy hết được (450/450 trace có thể overflow).
- **Hướng tác động:** không rõ dấu. Tóm tắt có thể giúp model 4B, vì cấu trúc lỗi dễ thấy hơn CSV dài. Nó cũng có thể làm hại, khi mất thời điểm từng dòng hoặc giá trị userId. Không được coi là hiệu quả của phương pháp.
- **Cách ghi:** trong báo cáo/paper, mục Implementation deviations, ghi kiểu "search_logs results longer than 2,048 tokens (backbone tokenizer) were deterministically condensed by the harness — exact-duplicate merge, then message-template merge, with an explicit notice to the model; instructed queries were never altered; see Appendix for impact on 450 traces". Mỗi lượt chạy ghi số lần kích hoạt và tỉ lệ span có tool result đã rút gọn, lấy từ `events.jsonl`. Nhãn kết quả: "RCLAgent adaptation (4B, 16k context, tool-result budget)".

## 7. Đề xuất và kế hoạch triển khai (chưa thực hiện)

Đề xuất **C (bậc thang), B = 2.048, chỉ `search_logs`**.

File sẽ sửa:
1. Chuyển `work/scripts/tool-result-budget.py` vào `kaggle/tool-result-budget.py` làm nguồn duy nhất, chỉ giữ hàm của C; script đo trong `work/` import từ đó.
2. `kaggle/smoke-worker.py`: trong `get_tool`, áp C cho `search_logs` với bộ đếm từ `guard.tokenizer`, ghi event `tool_result_budget`, dừng khi kết quả là `None`. Hằng số B = 2.048.
3. `kaggle/prepare-bundle.py`: chép module vào bundle, thêm `tool_result_budget` (quy tắc, B, hash module) vào manifest. Ghi `tool-result-budget-check.json`: trên lưới service × giây của trace smoke, phản hồi ≤ B giữ nguyên byte, còn lại ghi dạng và token.
4. `kaggle/verify-package.py`: thêm module vào allowlist (24 → 25 member), kiểm hash và file kiểm.
5. `kaggle/build-notebook.py` → `rclagent-kaggle-smoke.ipynb`, `kaggle/README.md`, `summarize-repair-run.py`: mô tả sai lệch, tóm tắt số lần kích hoạt.

Test hồi quy (`kaggle/test-tool-result-budget.py` mới, cùng vài case trong `test-kaggle-harness.py`):
- Phản hồi ≤ B giữ nguyên byte, gồm CSV chỉ có header và JSON "No matching records found.".
- Fixture kiểu `cartservice` (UUID, nhiều dòng) cho bậc mẫu ≤ B, tổng `count` bằng số dòng, có dòng thông báo.
- Fixture dòng trùng cho bậc trùng hệt, giữ nguyên văn mọi thông điệp gồm dòng `severity: error`.
- Fixture nhiều mẫu khác nhau buộc bậc cắt: mẫu error/warning được giữ trước, có `truncated`.
- Body không phải CSV log và vượt B thì dừng, không bị viết lại. `[tool error]` vẫn dừng trước bước ngân sách. Metric không bao giờ bị đổi.
- Hồi quy v6: phản hồi `cartservice` tại `1708475368` thành 454 token. Request 3 dự kiến khoảng 1.589 token (126.088 − 124.953 + 454), guard cho qua.
- Tính xác định: cùng đầu vào cho cùng byte đầu ra. Guard context vẫn dừng nếu tổng prompt vượt.
- Chạy lại đủ 18 harness test, 4 T4 compat, kiểm endpoint equivalence và validator gói trong `runtime/harness-env`.

Smoke Kaggle lần sau (version 7, chỉ sau khi sếp duyệt):
- Cùng notebook private, dataset version mới, trace `checkoutservice_cpu_2` (`68791e1f…`, 33 span), cùng Qwen3-4B-Instruct-2507 `cdbee75`, vLLM 0.10.2, một T4, context 16.384, mọi trần như v6. Marker `run-once` cần quyết định mới; lượt duyệt này là quyết định đó.
- Điều kiện định trước: thành công khi E chạy xong và scorer chạy sau khi server dừng. Nếu dừng vì lý do khác (vượt vòng tool, overflow do nhiều lời gọi, JSON sai, trần thời gian/requests), ghi đúng lý do. Không chạy lại hoặc đổi trace dựa trên kết quả.
- Ghi thêm: số lần kích hoạt ngân sách, dạng, token trước/sau, và tỉ lệ span có tool result đã rút gọn.

## 8. Artifact và lần chạy

- Script: [tool-result-budget.py](../261026-1713-rclagent-tai-hien-toi-thieu/work/scripts/tool-result-budget.py) (SHA256 `dfb730c6…fcee3`), [re2ob-tool-result-budget-impact.py](../261026-1713-rclagent-tai-hien-toi-thieu/work/scripts/re2ob-tool-result-budget-impact.py) (`0cb0492c…5da5`).
- Kết quả: `work/tool-result-budget-impact/`: `tool-result-budget-impact.json` (`0043873f…bc46`), `trace-impact.csv` (`24fe7398…eb9`), `changed-responses.json` (`c66a051f…3873`), `samples/`.
- Lần chạy: `logs/tool-result-budget-impact-check-01.log` là lượt kiểm 2 trace, B ∈ {1.024, 2.048, 4.096}, kết quả trong `tool-result-budget-impact-check-01/`. `logs/tool-result-budget-impact-02.log` là lượt đủ 450 trace, 2.211 giây, exit 0. Không có lượt nào lỗi.
- Môi trường: `kaggle/runtime/scan-env`, tokenizer ở `kaggle/runtime/hf-cache`. Không còn process nào do lượt này khởi động.

## Câu hỏi cần sếp quyết định

1. Duyệt phương án C, B = 2.048, chỉ `search_logs`?
2. Chấp nhận rằng `frontend` cũng bị rút gọn ở mọi trace (chỉ mất `log_id` và giây từng dòng)? Phương án khác là B = 8.192: chỉ đổi `frontend` ở 114 trace, nhưng mất bảo đảm 4 vòng tool trong 16.384.
3. Giữ nguyên văn dòng thông báo cho model như mẫu mục 3?
4. Cho phép sửa các file ở mục 7 và chạy một smoke Kaggle version 7 trên `checkoutservice_cpu_2`?
5. Ngoài phạm vi: `search_fluctuating_metrics` không trả dữ liệu cho bất kỳ query nào trên RE2-OB (tối đa 10 token), nên tín hiệu "#2 indicator" của prompt tác giả không bao giờ có. Sếp có muốn mở một lượt kiểm riêng xem đây là semantics gốc hay lỗi preprocess không?
