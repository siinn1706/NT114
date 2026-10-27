# Sửa guard `local_root_cause` và chạy lại pilot 5 trace, version 10 — 2026-10-27

**Kết luận:** guard đã sửa, và lỗi của version 9 không còn: 4/5 trace passed. Trace `currencyservice_mem_3`, failed ở version 9, nay passed với R@1 = 1. Model trả `local_root_cause: null` 6 lần ở 2 trace, và guard cho qua đúng như upstream. Trace 45 span (`productcatalogservice_delay_3`) vẫn failed, lần này vì một nguyên nhân mới. Nó xong cả 90 bước agent trong 1.285 giây. Request tổng hợp cuối có prompt 8.446 token, và hai lần liền vượt timeout 180 giây của upstream. Lần thử thứ ba bị deadline 1.800 giây cắt. Trên đường T4 hiện tại, thời gian prefill tăng nhanh hơn tuyến tính theo độ dài prompt. Điểm dưới đây chỉ mô tả 4 trace, không phải ước lượng accuracy.

Phạm vi theo duyệt của sếp: sửa guard cho `local_root_cause` nhận `null`, kèm test hồi quy; đóng gói lại; chạy lại pilot 5 trace với dataset và notebook private. Không đổi upstream, prompt, model, sampling, context, output, retry, số vòng tool, ngân sách, các trần, dữ liệu hay split. Không commit, không push.

## 1. Thay đổi

- **`smoke-worker.py`** (`decorate`, nhánh consolidate): `local_root_cause` được là chuỗi hoặc `null`. Guard vẫn dừng trace khi output không phải JSON, sai `span_id`, thiếu hẳn trường này, hoặc trường có kiểu khác.
- **`test-kaggle-harness.py`**: thêm 2 test.
  - `test_version9_null_local_root_cause_regression` dùng span lá paymentservice `b81ba52867406a5c` của trace `2095688a…` với một câu trả lời `null` giống version 9. Test đỏ trước khi sửa và xanh sau khi sửa.
  - `test_consolidation_without_a_local_root_cause_field_still_stops` kiểm guard vẫn dừng khi thiếu trường này hoặc trường là số.
- **Gói:** bundle `00d737bc…78b0`, manifest `a9fdc10a…4c3d`, notebook `67194c0e…6b02b6e`. So với bundle version 9, chỉ `smoke-worker.py` và `manifest.json` đổi. Bản version 9 được sao lưu ngoài repo trước khi thay.

## 2. Kiểm CPU

| Kiểm | Kết quả |
|---|---|
| `test-kaggle-harness.py` | 31/31 OK (thêm 2 test mới) |
| `test-tool-result-budget.py` | 11/11 OK |
| `test-vllm-t4-compat.py` | 4/4 OK |
| `check-tool-result-budget.py` | pass; `tool-result-budget-check.json` chỉ đổi `worker_sha256` |
| `verify-package.py` | pass: 5 trace, 3.528 phép so endpoint |

Log nằm trong `kaggle/runtime/test-logs/`: `harness-null-root-cause-{red,green,full}-01`, `tool-result-budget-null-root-cause-01`, `t4-null-root-cause-01`, `tool-result-budget-check-null-root-cause-01`, `refresh-pilot-null-root-cause-01`, `notebook-pilot-null-root-cause-01` và `verify-package-pilot-null-root-cause-01`.

## 3. Kaggle version 10

- Dataset `siinn1706/rclagent-one-trace-smoke-261026`, version 12, private. Em tải `smoke-worker.py` từ dataset về: hash `5af64ffc…3e75`, khớp bản sửa.
- Notebook `siinn1706/rclagent-one-trace-gpu-smoke-261026`, version 10, private, chạy trên một T4. Code notebook tải về khớp bản đã push.
- `check-kaggle-private.py` xác nhận cả hai vẫn private.

| Trace | Ca (nhãn) | Span | Trạng thái | E (giây) | Requests | R@1 / R@3 / MRR |
|---|---|---:|---|---:|---:|---|
| `2095688a…` | productcatalogservice_delay_3 | 45 | failed (deadline) | 1.800 | 147 | — |
| `3753f2a8…` | recommendationservice_socket_3 | 4 | passed | 246 | 17 | 0 / 0 / 0,167 |
| `c6033940…` | emailservice_socket_2 | 23 | passed | 748 | 74 | 0 / 0 / 0,125 |
| `1e527c6a…` | currencyservice_mem_3 | 25 | passed | 866 | 81 | 1 / 1 / 1,000 |
| `f6526e73…` | productcatalogservice_mem_1 | 33 | passed | 1.077 | 105 | 0 / 1 / 0,333 |

- **Guard mới.** Có 6 câu trả lời `local_root_cause: null`: 5 ở `2095688a…` và 1 ở `1e527c6a…`. Guard cho qua cả 6, và không trace nào dừng vì lỗi JSON.
- **Ngân sách.** 9 kết quả `search_logs` bị rút gọn, như ở version 9; không dòng nào bị bỏ. Không trace nào chạm trần 160 requests.
- **Kết quả xếp hạng.** Cả 4 trace passed đều liệt kê 10 service, nên R@10 luôn bằng 1 và không nói lên gì. Nhãn đứng đầu ở 1/4 trace. Ba trace còn lại cho thứ hạng y như version 9.
- **Thời gian và tài nguyên.** Toàn lượt mất 4.851,4 giây (81 phút). RSS đỉnh khoảng 9,22 GB; GPU đỉnh 13.494 MiB.
- **Dọn process.** vLLM thoát với mã 0, các tool server −15, 4 worker passed 0. Worker của trace hết giờ bị dừng với −15. Máy local không còn process nào em khởi động.
- **Artifact.** `rclagent-kaggle-repair-v10-results.zip`, SHA256 `72045188…68bd3ab`, khớp file `.sha256` của Kaggle. Tóm tắt nằm ở `kaggle/kaggle-repair-v10-summary.json`.

## 4. Trace 45 span: request tổng hợp quá chậm

- **Diễn biến.** Trace xong 45 bước self-state và 45 bước consolidation sau 1.285 giây. Request tổng hợp cuối (số 145, có tool `print_results`) có prompt 8.446 token.
  - Hai lần gửi (145 và 146) đều bị `ReadTimeout` sau 180 giây.
  - Lần thứ ba (147) bị deadline 1.800 giây cắt.
  - Timeout 180 giây là của upstream (`llm.py`, hai chỗ `timeout=180`); harness chỉ mượn lại số này.
- **Đo trên version 9 và 10.** Thời gian phản hồi tăng nhanh hơn tuyến tính theo độ dài prompt:

  | Prompt (token) | Thời gian phản hồi |
  |---|---|
  | dưới 2.000 | trung vị 9–11 giây |
  | 4.649 | 78 giây |
  | 5.411 | 101 giây |
  | 6.362 | 138 giây |
  | 8.446 | hơn 180 giây |

  Số completion token của các request dài chỉ khoảng 67, nên phần chậm nằm ở prefill.
- **Log vLLM.** Trong lúc xử lý request này, generation throughput là 0 token/s. Prompt throughput chỉ 2–234 token/s, và mỗi dòng metrics cách nhau 18–100 giây.
- **Giả thuyết, chưa kiểm.** Server chạy với `--enable-chunked-prefill --max-num-batched-tokens 2048 --enforce-eager`. Một prompt 8.446 token bị chia thành 5 khúc. Từ khúc thứ hai, vLLM 0.10.2 dùng kernel Triton prefix-prefill, mà trên T4 đã được vá xuống `BLOCK_M=64`. Kernel này có vẻ rất chậm khi phần prefix dài. Muốn xác nhận phải đo trên GPU.
- **Hệ quả.** Prompt tổng hợp lớn dần theo số span: 33 span cho 6.362 token, 45 span cho 8.446 token. Vì vậy các trace từ khoảng 40 span trở lên gần như chắc chắn hết giờ ở bước cuối, dù mọi bước trước đã xong. Ước lượng cho 240 trace train cũng phải tính đến điều này.

## 5. Hướng xử lý có thể (chưa làm, cần sếp quyết)

1. **Đổi cấu hình vLLM để prefill dài nhanh hơn trên T4.** Ví dụ tắt chunked prefill, hoặc tăng `max-num-batched-tokens`, để prompt dài được prefill một lượt mà không qua kernel prefix-prefill. Đây là cấu hình server, không phải thiết lập đóng băng của RCLAgent. Nhưng nó có rủi ro bộ nhớ trên T4 và cần một lượt GPU để đo.
2. **Giữ nguyên và ghi là giới hạn.** Trace có prompt tổng hợp vượt khoảng 7.000 token sẽ được ghi `failed`. Như vậy tập train bị lệch về các trace nhỏ.
3. **Nới timeout 180 giây.** Đây là giá trị của upstream, nên nếu đổi thì phải khai báo là sai lệch so với upstream. Nó cũng chưa chắc đủ trong deadline 1.800 giây.

## Câu hỏi còn mở

1. Sếp chọn hướng nào ở mục 5? Em đề xuất hướng 1: đo trước bằng một lượt GPU ngắn chỉ gửi các prompt dài, rồi mới chạy lại pilot.
2. Có cần đếm phân bố số span của 240 trace train để biết bao nhiêu trace bị ảnh hưởng không?
