# Harness cho thí nghiệm thiếu nguồn metric (phương án A) — 2026-10-28

**Kết luận:** harness đã có seed theo từng lượt, chế độ thiếu nguồn và metric đã sửa (X_m). Toàn bộ test CPU mới đều qua.

- Bộ test cũ còn đúng một lỗi, ở `test_expanded_kaggle_dataset_hash_verification`. Test này so `kaggle-runtime.py` với bản trong bundle hiện có, mà bundle chưa được dựng lại sau khi runtime đổi, nên lỗi đúng như dự kiến. Lỗi sẽ hết khi dựng gói mới.
- Chưa dựng gói, chưa chạy GPU, chưa commit.

Phạm vi theo quyết định của sếp ngày 2026-10-28, ghi ở `decisions.md`, gồm ba điều kiện:
- `no_metric`: không có metric.
- `metric`: metric chạy qua X_m.
- `metric_no_log`: metric qua X_m, không có log.

Mỗi điều kiện chạy với ba seed 20261026, 20261027 và 20261028. Thiết kế lấy theo [report phân tích](analysis-261028-1104-rclagent-pilot-trace-failure-analysis.md).

## 1. Thay đổi

Mọi đường dẫn tính từ `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`.

- **`metric-repair.py`** (file mới, nằm trong danh sách `WRAPPERS`). Module giữ đúng cách lọc dòng, khóa nhóm KPI, cách làm tròn và định dạng phản hồi của endpoint tác giả, chỉ đổi ba điểm:
  - giữ các nhóm có `node_id` NaN;
  - lấy baseline trong [t−1.200, t−600), cần ít nhất 31 dòng;
  - chỉ báo KPI khi trung bình cửa sổ lệch ít nhất K = 100 độ lệch chuẩn.
- **`smoke-worker.py`.**
  - Thêm ba cờ `--seed`, `--logs author|absent` và `--metric author|absent|repaired`.
  - Seed được truyền vào payload request. Không có cờ thì giữ seed 20261026 như trước.
  - Nguồn `absent` được harness trả lời thay, không hỏi tool server. Log trả về `log_id,timestamp,cmdb_id,log_name,value\n`; metric trả về `{"message":"No matching records found."}\n`. Cả hai là đúng byte endpoint tác giả trả khi không có dòng nào.
  - Mỗi sự kiện `tool_result` ghi thêm trường `source`. `worker-status.json` ghi seed và nguồn của lượt chạy.
  - Phase protocol luôn dùng tool của tác giả.
- **`kaggle-runtime.py`.**
  - Hàm `run_entries` đọc `manifest['runs']`. Nếu không có `runs`, mỗi trace thành một lượt với `run_id` bằng `trace_id`, nên gói cũ chạy như trước.
  - Hàm `worker_options` chuyển các cờ của từng lượt cho worker.
  - Progress, `run/traces/<run_id>/` và `run/scoring/<run_id>/` đều dùng `run_id` làm khóa.
- **`add-condition-runs.py`** (file mới). Script thêm `runs` và `condition_design` vào một gói đã dựng, kèm sha256 của file chọn trace. Thứ tự chạy là theo seed, trong mỗi seed theo trace, trong mỗi trace đủ cả ba điều kiện. Nhờ vậy một phiên bị cắt ngang vẫn để lại các khối (trace, seed) có đủ ba điều kiện. Script từ chối gói có trace nằm ngoài danh sách đã chọn.
- **`README.md` (kaggle)** có thêm mục mô tả lượt chạy theo điều kiện.

## 2. Kiểm CPU

| Kiểm | Kết quả |
|---|---|
| `test-missing-source-conditions.py` (mới) | 14/14 OK |
| `test-kaggle-harness.py` | 30/31. Lỗi còn lại là `test_expanded_kaggle_dataset_hash_verification`, với thông báo `Notebook runtime differs from hashed package runtime` (runtime đã đổi so với bundle hiện có) |
| `test-tool-result-budget.py` | 11/11 OK |
| `test-vllm-t4-compat.py` | 4/4 OK |
| `test-prefill-bench.py` | 6/6 OK |
| `check-tool-result-budget.py` (tokenizer `cdbee75f`) | pass; trong `tool-result-budget-check.json` chỉ hash của worker đổi |

Test mới kiểm các điểm sau:
- Phản hồi cho nguồn `absent` trùng byte với endpoint tác giả chạy trên dữ liệu rỗng; trên Windows, xuống dòng `\r\n` của pandas được chuẩn hóa thành `\n` như trên Linux.
- Endpoint tác giả không báo KPI nào trên dữ liệu thật của trace `1e527c6a`.
- X_m báo `currencyservice.mem` trên trace đó, đúng định dạng của tác giả.
- Ngưỡng 100σ được kiểm bằng dữ liệu tổng hợp: lệch 80σ thì không báo, lệch 120σ thì báo.
- Nguồn `absent` và `repaired` không gọi tool server.
- Truy vấn có timestamp ngoài cửa sổ vẫn dừng ở mọi điều kiện.
- Seed đi vào request.
- Ma trận lượt chạy và runtime truyền đúng cờ cho từng lượt.

Log test nằm ở `runtime/test-logs/*-missing-source-01.log`.

**Đối chiếu X_m với mô phỏng trên 240 trace train.** X_m gắn cờ service đúng ở 235/240 trace (97,9%), và gắn cờ 190/2.400 cặp trace × service khác (7,9%). Mô phỏng dùng để chọn K cho 97,1% và 8,4% trên 35 case dùng để chọn ngưỡng. Ở cả 8 trace đã chọn, X_m đều gắn cờ service đúng. Tuy vậy 3 trace trong số đó không chứa service đúng, nên model chỉ thấy tín hiệu này nếu nó tự truy vấn service đó.

## 3. Việc tiếp theo

1. Chốt số case. Với 8 case (72 lượt), ước cao là 13,8 giờ. Với 6 case (54 lượt), ước cao là 10,3 giờ.
2. Dựng gói bằng `prepare-bundle.py NAME <trace_id...>`. Mỗi gói một nửa số case để vừa một phiên Kaggle, trace chép từ `pilot-selection.json`. Sau đó chạy `add-condition-runs.py`, rồi `refresh-package.py`, `verify-package.py` và chạy lại bộ test để test hash qua.
3. Đẩy lên Kaggle ở chế độ private và chạy.

## Câu hỏi còn mở

1. Giữ 8 case với ước cao 13,8 giờ, hay giảm còn 6 case?
2. Có báo cho tác giả về lỗi `node_id`/`dropna` không?
