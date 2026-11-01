# Kiểm S1 v3: thứ tự hint theo hash seed và nhãn mất bằng chứng

Ngày 2026-11-01. `K/` là `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`. Một lượt kiểm chéo độc lập bằng script riêng đọc thẳng zip (không import analyzer, `check-hash-seed-order.py` hay `compare-run-outputs.py`) khớp mọi số dưới đây; số traceback vLLM đã sửa theo lần đếm lại. Việc "không có server khởi động lại" chỉ suy gián tiếp: mỗi trace đúng 1 lần thử, không có OOM, `progress.json` không có cờ `server_died`.

## Kết quả
1. Hash seed cố định có tác dụng. 70/70 prompt cuối của S1 v3 có đúng thứ tự service của seed 0, và `check-hash-seed-order.py` thoát mã 0 với `verified: true`. S1 v2 chỉ 54/70 khớp, 16 lệch seed (`K/runtime/analysis-hash-seed-s1-v3/summary.json`).
2. 72 cặp gồm 62 `identical` (2 trong số đó là hai trace B thất bại ở cả hai lần chạy, không có phản hồi cuối để so), 10 `order_only`, 0 `unexplained`. `same_order_different_output` rỗng. Cả 10 cặp `order_only` chỉ khác ở phản hồi cuối (`final_response_only`), đúng bằng các run S1 v2 lệch seed, và R@1, MRR, top-1 của chúng bằng nhau (`pairs.csv`).
3. `runs.csv` của S1 v3 và S1 v2 trùng từng byte, SHA256 `67ebbb8e…dedd08`. I0 đến I5, `rank`, `first_loss_linear`, `final_residual`, D1, D2 trùng 72/72 cặp, 0 lệch. `cases.csv`, `funnel.csv`, `spans.csv`, `case-comparison.csv` cũng trùng từng byte.
4. Ba CSV quyết định tính lại với S1 v3 trùng từng byte với `runtime/analysis-evidence-loss-decision/`. Bảng chính (bỏ `99f095`) giữ nguyên: `S0_gt_span_absent` 3/4, `S2_root_label_lost_hit_kept` 2/3, `S4_inputs_present_not_rank1` 1/4, `S0_gt_span_present_not_queried` 0/4, `label_mismatch_flags` không kiểm được.
5. Biên nhận đóng băng còn khớp. `codebook_sha_matches`, `analyzer_sha_matches` và `imports_sha_match` đều `true`, `integrity_problems` rỗng. Điểm tác giả 70/70 không lệch, `tool_results_joined` 5281 bằng `tool_results_raw` 5281.

## Tải output

| | A | B |
|---|---|---|
| Thư mục | `K/runtime/kaggle-output-a-s1-v3/` | `K/runtime/kaggle-output-b-s1-v3/` |
| Số file | 480 | 468 |
| Zip (`rclagent-smoke/rclagent-smoke-results.zip`) | 3 683 013 byte | 3 222 874 byte |
| SHA256 zip, khớp `.sha256` | `b88cfaa943e4d6776ffc7d322ce2d87de0ca5144a0470972f79985d7bb695d57` | `0b09c68055ddccc035acbc48adf43468f7c6e4be9ca93211553d70e802fca707` |
| `bundle_sha256` trong `run-once.json` | bằng `s1-v3/a/rclagent-kaggle-bundle.zip` | bằng `s1-v3/b/rclagent-kaggle-bundle.zip` |
| Trace | 36 passed | 34 passed, 2 failed |
| Thời gian chạy | 30 271,7 giây (8,41 giờ) | 23 461,2 giây (6,52 giờ) |
| Python Kaggle (`environment-before.json`) | 3.13.15 | 3.13.15 |

- **GPU và số lần thử:** cả hai chạy Tesla T4, mỗi trace đúng 1 lần thử.
- **Hai trace B thất bại:**
  - `272a47c2…--no_metric--s20261026` (case `recommendationservice_cpu_2`): `Invalid structured response: 'currencyservice' is not of type 'object'`.
  - `ad1c27da…--metric--s20261027` (case `currencyservice_disk_3`): `Invalid agent JSON output: Span identifier missing or mismatched`.
  - Cả hai là lớp `H_parse`, và thất bại giống hệt S1 v2 (`pairs.csv`). `H_cap` và `H_infra` đều 0.
- **Server:** không có server chết, không có OOM. `vllm.log` có 10 traceback ở A (9 thuộc `hermes_tool_parser`) và 22 ở B (21 thuộc `hermes_tool_parser`), là lỗi phân tích tool-call của model. Các dòng `No module named 'wrapt'` trong log kernel là cảnh báo môi trường, có ở cả hai bên.

## Kiểm thứ tự hint (lệnh đúng mục 5 handoff S1, S1 v3 là bên mới, S1 v2 là bên cũ)
- Python dự đoán là 3.13.18, cùng minor với Kaggle.
- `order_sensitive` là 29 ở cả hai bên. `order_sensitive_match` là 29 ở v3 và 13 ở v2.
- Cặp theo bên: A 32 `identical` + 4 `order_only`, B 30 `identical` + 6 `order_only`.
- Hai run `no_final_prompt` là hai trace B thất bại.
- Handoff S1 cảnh báo sửa Q8 có thể đẩy cặp vào `unexplained`. Kết quả không có cặp nào như vậy trong 72 lượt này.

## Giới hạn
- Đây là bản sao, không độc lập. Khớp 72/72 không tăng cỡ mẫu.
- Kết quả vẫn là mô tả có phơi nhiễm, không phải nhân quả.
- Khớp byte của `runs.csv` chỉ cho thấy analyzer cho kết quả giống nhau. Việc hai bộ prompt tương đương do phép kiểm thứ tự và `pairs.csv` đảm nhận.
- Analyzer không đọc phản hồi cuối của 10 run `order_only`. `misattributed`, I5 và `final_residual` vẫn là phần chưa kiểm tay.

## Câu hỏi còn mở
1. Sếp muốn ghi 10 cặp `order_only` thành một dòng trong báo cáo kết quả chính, hay giữ ở báo cáo này?
2. Hai trace B `H_parse` giống hệt ở hai lần chạy: coi là tính tất định của lỗi định dạng (mô tả), hay không đưa vào bài?
3. Có muốn thêm nhãn rõ ràng cho sự kiện khởi động lại server trong harness, để lần sau kiểm trực tiếp?
