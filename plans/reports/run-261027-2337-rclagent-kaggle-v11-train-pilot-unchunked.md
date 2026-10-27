# Pilot 5 trace train với server không chunked prefill, version 11 — 2026-10-27

**Kết luận:** lần đầu tiên cả 5/5 trace pilot đều passed. Trace 45 span hết deadline ở version 10, nay xong sau 870 giây. Request tổng hợp 8.445 token của nó trả lời trong 9,7 giây; ở version 10, cùng request này vượt timeout 180 giây. Toàn lượt chạy mất 45 phút, so với 81 phút của version 10. Đổi server cũng làm câu trả lời đổi: từ một request khoảng 1.000 token ở giữa mỗi trace, câu trả lời đã khác version 10. Vì vậy kết quả version 11 không so được theo từng byte với các version 8–10. Điểm dưới đây chỉ mô tả 5 trace, không phải ước lượng accuracy.

Phạm vi theo duyệt của sếp: đổi server pilot sang không chunked prefill (`--max-num-batched-tokens 16384`), kiểm CPU, đóng gói lại và chạy lại pilot 5 trace, với dataset và notebook private. Không đổi upstream, prompt, model, sampling, context, output, retry, số vòng tool, ngân sách, các trần, dữ liệu hay split. Không commit, không push.

## 1. Thay đổi

- **`kaggle-runtime.py`.**
  - Server bỏ `--enable-chunked-prefill`, và `--max-num-batched-tokens` lấy theo `settings['max_num_batched_tokens']`, bằng context. Trên T4 giá trị này là 16.384. Nếu GPU lớn hơn và context là 32.768 thì nó là 32.768, vì vLLM V0 không nhận số token mỗi bước nhỏ hơn context khi tắt chunked prefill.
  - `settings.json` ghi `enable_chunked_prefill: false` cho khớp.
  - Sau khi server sẵn sàng, cell C dừng nếu log vLLM có dòng báo chunked prefill đang bật.
- **`build-notebook.py`.** Notebook có thêm ô "Từ version 11: server không chunked prefill".
- **`README.md` (kaggle).** Mô tả cấu hình mới, dẫn link tới [report đo](bench-261027-2232-t4-prefill-chunked-vs-unchunked.md), và ghi rằng ước lượng thời gian cũ tính theo chunked.
- **`test-prefill-bench.py`.** Test so cờ server nay khẳng định server của pilot chính là cấu hình `unchunked-16384`. Cấu hình `chunked-2048` chỉ khác ở phần scheduling.
- **`test-kaggle-harness.py`.** `test_expanded_kaggle_dataset_hash_verification` trước đây đọc `runtime/package`, tức gói một trace cũ của version 8. Test này chỉ pass vì `kaggle-runtime.py` chưa đổi từ đó. Nay test đọc gói con có manifest khớp với bundle đang dùng.
- **Gói.** Bundle `af27179a…2a91`, manifest `dad835cb…7a40`, notebook `7e34d784…78e3`. So với bundle version 10, chỉ `kaggle-runtime.py` và `manifest.json` đổi. Bản version 10 được sao lưu ngoài repo trước khi thay.

## 2. Kiểm CPU

| Kiểm | Kết quả |
|---|---|
| `test-kaggle-harness.py` | 31/31 OK. Lần chạy trước khi sửa test đường dẫn gói có 1 lỗi, như mục 1 |
| `test-tool-result-budget.py` | 11/11 OK |
| `test-vllm-t4-compat.py` | 4/4 OK |
| `test-prefill-bench.py` | 6/6 OK |
| `check-tool-result-budget.py` | pass |
| `verify-package.py` | pass: 5 trace, 3.528 phép so endpoint |

Log nằm trong `kaggle/runtime/test-logs/`: `*-unchunked-0{1,2,3}`, `refresh-pilot-unchunked-01`, `notebook-pilot-unchunked-01` và `verify-package-pilot-unchunked-01`.

## 3. Kaggle version 11

- **Dataset.** `siinn1706/rclagent-one-trace-smoke-261026` version 13, private. Em tải `kaggle-runtime.py` từ dataset về: hash `7acc731a…7edd7`, khớp bản mới.
- **Notebook.** `siinn1706/rclagent-one-trace-gpu-smoke-261026` version 11, private, một T4. Code notebook tải về khớp bản đã push.
- **Cấu hình server thật.** `settings.json` ghi `enable_chunked_prefill: false` và `max_num_batched_tokens: 16384`. Log vLLM không có dòng báo chunked prefill.
- **Bộ nhớ.** KV cache 1.598 block (3,51 GiB), đủ cho 1,56 request dài 16.384 token, như lượt đo riêng.

| Trace | Ca (nhãn) | Span | Trạng thái | E version 10 → 11 (giây) | Requests | R@1 / R@3 / MRR |
|---|---|---:|---|---|---:|---|
| `2095688a…` | productcatalogservice_delay_3 | 45 | passed | 1.800 (hết deadline) → 870 | 145 | 0 / 0 / 0,250 |
| `3753f2a8…` | recommendationservice_socket_3 | 4 | passed | 246 → 108 | 17 | 0 / 0 / 0,143 |
| `c6033940…` | emailservice_socket_2 | 23 | passed | 748 → 460 | 74 | 0 / 0 / 0,000 |
| `1e527c6a…` | currencyservice_mem_3 | 25 | passed | 866 → 527 | 81 | 1 / 1 / 1,000 |
| `f6526e73…` | productcatalogservice_mem_1 | 33 | passed | 1.077 → 639 | 105 | 1 / 1 / 1,000 |

- **Thời gian.** Cả 422 requests đều trả HTTP 200, không lần nào bị retry hay timeout. E tổng cộng 2.604 giây (khoảng 20 giây mỗi span), toàn lượt 2.715,9 giây.
  - Request có prompt dưới 2.000 token: trung vị 5,5–6,5 giây, so với 8,8–11,2 giây ở version 9 và 10.
  - Request tổng hợp từ 4.648 đến 8.445 token: 6,4 đến 9,7 giây.
- **Ngân sách và guard.** 9 kết quả `search_logs` bị rút gọn, như các lượt trước. Có 6 câu trả lời `local_root_cause: null`, và guard cho qua cả 6.
- **Kết quả xếp hạng.**
  - Nhãn đứng đầu ở 2/5 trace.
  - Ở `c6033940…`, danh sách 10 service không có `emailservice`, nên MRR bằng 0.
  - Trace `2095688a…` có kết quả lần đầu; `productcatalogservice` đứng thứ 4.
  - Năm trace chưa đủ để nói gì về accuracy.
- **Tài nguyên.** RSS đỉnh khoảng 9,20 GB; GPU đỉnh 13.366 MiB.
- **Dọn process.** vLLM và cả 6 worker thoát với mã 0; các tool server −15. Máy local không còn process nào em khởi động.
- **Artifact.** `rclagent-kaggle-repair-v11-results.zip`, SHA256 `737df376…51f69c`, khớp file `.sha256` của Kaggle. Tóm tắt ở `kaggle/kaggle-repair-v11-summary.json`.

## 4. Đổi server làm đổi câu trả lời

Em so từng request và câu trả lời của các lượt, bỏ qua mã tool call vì mã này ngẫu nhiên mỗi lượt:

- **Version 9 so với version 10** (cùng chunked, khác máy): request và câu trả lời trùng hoàn toàn, tới điểm version 9 dừng. Vậy với cùng cấu hình, một lượt chạy tái lập được giữa các phiên Kaggle.
- **Version 10 so với version 11:** câu trả lời đầu tiên khác nhau là ở request 7–43, tùy trace. Request đó luôn là một bước self-state khoảng 1.041–1.047 token, và các request trước nó không quá 1.720 token. Đổi đường tính attention đã làm số học lệch đủ để token được sample khác đi. Từ đó các bước sau khác dần theo.
- **Lượt đo riêng.** 5 prompt dài cho câu trả lời giống hệt giữa hai cấu hình. Đó chỉ là trùng hợp trên 5 request, không phải bảo đảm.
- **Hệ quả.** Kết quả từ version 11 thuộc một cấu hình server mới. Report và bảng tổng hợp phải ghi rõ cấu hình này và không gộp với các lượt version 8–10.

## 5. Ước lượng cho tập train

Với khoảng 20 giây mỗi span (130 span trong 2.604 giây), ước lượng cũ 73 giờ T4 cho 240 trace train, vốn tính theo 40 giây mỗi span, giảm còn khoảng 36 giờ. Đây là phép ngoại suy từ 5 trace. Nó chưa tính trace nào có prompt dài hơn 16.384 token, vì em chưa đếm phân bố số span của tập train.

## Câu hỏi còn mở

1. Bước tiếp theo là gì: chạy lô train lớn hơn với cấu hình này, hay lặp lại pilot để đo độ ổn định của kết quả?
2. Có cần đếm số span của 240 trace train để biết trace nào có thể chạm context 16.384 hoặc deadline 1.800 giây không?
3. Có commit loạt thay đổi từ version 9 tới nay (guard `null`, công cụ đo prefill, server không chunked) lên nhánh `feat/rclagent-harness-budget-guard` không?
