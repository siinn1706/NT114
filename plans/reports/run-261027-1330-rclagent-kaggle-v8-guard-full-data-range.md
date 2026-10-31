# Sửa guard timestamp ngoài dữ liệu đầy đủ và smoke Kaggle version 8 — 2026-10-27

**Kết luận:** version 8 chạy hết end-to-end lần đầu tiên. E chạy 106 requests, tất cả HTTP 200, trong 1.332,9 giây; F chấm bằng scorer tác giả. Ở request 60, model lại gọi `search_fluctuating_metrics` với timestamp gõ sai `1808475368747`, cùng span `d700ad94e2c085ed` như version 7. Lần này guard cho qua, và tool trả `{"message":"No matching records found."}`, đúng như tool tác giả trên dữ liệu đầy đủ. Kết quả xếp `checkoutservice` đứng đầu, khớp nhãn của trace này (R@1 = 1/1). Đây chỉ là kết quả mô tả của một trace, không phải ước lượng accuracy, và có ngân sách `search_logs` (sai lệch đã khai báo), nên không so trực tiếp với Table I.

Phạm vi theo duyệt của sếp: sửa guard theo mục 5 của [report version 7](run-261027-1235-rclagent-kaggle-v7-tool-result-budget.md), thêm test hồi quy đúng query của version 7, kiểm CPU, rồi chạy smoke version 8 cùng trace `checkoutservice_cpu_2` và cùng cấu hình. Không commit/push. Không đổi upstream, prompt, model, sampling, context, output, retry, số vòng tool, ngân sách, các trần, dữ liệu hay split.

## 1. Thay đổi

- `prepare-bundle.py`: thêm `full_data_seconds()`. Hàm đọc cột `timestamp` của toàn bộ `metrics.csv` và `logs.csv` đầy đủ, rồi ghi giây đầu và giây cuối vào `selection.json` (`query_window.full_data_seconds`). Kết quả: metric [1.705.339.822, 1.708.489.861], log [1.705.339.822, 1.708.489.860]. Hai khoảng này trùng với lần đo độc lập bằng `work/scripts/re2ob-full-data-time-range.py`.
- `refresh-package.py`: nếu `selection.json` chưa có khoảng này thì tính và ghi thêm, rồi cập nhật hash trong manifest. Dữ liệu, upstream và `cpu-equivalence.json` không đổi byte.
- `smoke-worker.py`, `validate_query`: guard vẫn cho qua mọi giây trong cửa sổ trace như trước. Ngoài ra, guard cho qua cả query có cửa sổ endpoint (±1.200 giây cho metric, ±60 giây cho log) nằm hoàn toàn ngoài khoảng dữ liệu đầy đủ, vì khi đó dữ liệu đầy đủ và gói đều trả rỗng. Mọi trường hợp khác vẫn dừng. Nếu `selection.json` không có khoảng này, guard chặt như version 7.
- `verify-package.py`: kiểm khoảng trong `selection.json` bằng đúng giá trị đo độc lập, và kiểm cửa sổ trace cùng các dòng trong gói đều nằm trong khoảng đó.
- `build-notebook.py`: đổi tiêu đề ô ngân sách thành "Từ version 7"; thêm ô "Kết quả version 7" và ô mô tả bản sửa guard. Notebook vẫn có 4 ô code.

## 2. Kiểm CPU

| Kiểm | Kết quả |
|---|---|
| Harness (`test-kaggle-harness.py`) | 20/20 pass, gồm 2 test mới |
| Test biên | log 939 và 2.061 qua, 940 và 2.060 dừng; metric −201 và 3.201 qua, 3.200 dừng; giây trong khoảng dữ liệu nhưng ngoài cửa sổ trace vẫn dừng |
| Test hồi quy v7 | query `productcatalogservice`/`1808475368747` bị guard cũ chặn, guard mới cho qua; endpoint gốc chạy trên gói trả "No matching records found." (metric) và CSV chỉ có header (log) |
| Đột biến tắt nhánh mới | 5 ca hỏng (test hồi quy và 4 ca "qua" của test biên); đã khôi phục worker, hash khớp |
| Ngân sách | 9/9 pass; `tool-result-budget-check.json` chạy lại vì hash worker đổi, status pass |
| T4 compat | 4/4 pass |
| Validator gói | pass, 25 member, bundle `f270e386…c763`, manifest `685127cb…9336` |

Log ở `kaggle/runtime/test-logs/` (`harness-guard-fix-0{1,2}`, `harness-guard-fix-mutant-01`, `tool-result-budget-v8-01`, `tool-result-budget-check-v8-01`, `t4-after-guard-fix-01`, `refresh-package-v8-01`, `build-notebook-v8-01`, `verify-package-v8-01`). Gói version 7 được giữ ở `runtime/bundle-v7` và `runtime/package-v7`.

## 3. Kaggle version 8

Dataset private `siinn1706/rclagent-one-trace-smoke-261026` version 10. Notebook private `siinn1706/rclagent-one-trace-gpu-smoke-261026` version 8, một Tesla T4, context 16.384, sampling như cũ (temperature 0,7, top_p 0,8, top_k 20, seed 20261026). Notebook kiểm mọi hash member khớp manifest `685127cb…`. Code notebook tải về khớp bản đã push. `check-kaggle-private.py` xác nhận cả dataset và notebook vẫn private.

- **B:** kiểm kernel tương thích pass. **D:** pass, 3 requests HTTP 200.
- **E:** 106 requests (72 self-state, 33 consolidation, 1 synthesis), tất cả HTTP 200, 0 lỗi, 0 fatal. Tổng 108.220 prompt và 11.512 completion token.
  - Prompt lớn nhất 6.444 token, ở request synthesis cuối. Request consolidation lớn nhất 1.973 token. Context 16.384 không bị chạm.
  - 75 lần gọi tool: 38 `search_logs`, 37 `search_fluctuating_metrics`. Chỉ một kết quả bị rút gọn: `cartservice` ở root span, từ 124.953 xuống 454 token, không bỏ dòng nào, như version 7.
  - Chỉ một query nằm ngoài cửa sổ trace: query gõ sai của version 7. Nó đi qua nhánh guard mới và nhận phản hồi rỗng.
- **F:** scorer tác giả trên một trace: R@1, R@3, R@5, R@10 và MRR đều bằng 1,0000. Nhãn là `checkoutservice` (cpu).
  - Kết quả model liệt kê 10 service, `checkoutservice` đứng đầu.
  - Vì danh sách gồm gần như mọi service, R@3 trở lên không nói lên được gì. Chỉ R@1 đáng chú ý, và cũng chỉ trên một trace.
- **Thời gian và tài nguyên:** E 1.332,9 giây; toàn bộ lượt chạy 1.444,2 giây. Trần 160 requests và 1.800 giây không bị chạm, nhưng E chỉ còn dư khoảng 467 giây. RSS cây process đỉnh khoảng 9,21 GB; GPU đỉnh 13.568 MiB.
- **Cleanup:** vLLM 0, tools-synthetic −15, worker-protocol 0, tools-telemetry −15, worker-trace 0. Máy local không còn process Python hay Kaggle nào.
- **Artifact:** `rclagent-kaggle-repair-v8-results.zip`, SHA256 `29b07b58799237e3e619d118bd0626e8e571c20e749d5c6b65572642fe0a8934`, khớp file `.sha256` của Kaggle. Tóm tắt ở `kaggle-repair-v8-summary.json`.

## 4. Ghi chú về tính lặp lại

So với version 7, 28 request đầu trùng byte. Từ request 29, nội dung bắt đầu khác dù cùng seed và cùng cấu hình; em chưa tìm nguyên nhân. Query gõ sai vẫn xuất hiện ở đúng request 60 và cùng span. Vì vậy không nên coi một lượt chạy là tái lập byte-cho-byte. Nếu cần kết luận ổn định thì phải chạy nhiều lượt hoặc nhiều trace.

## Câu hỏi còn mở

1. Bước tiếp theo là gì: chạy thêm trace hay lặp lại trace này để đo độ ổn định? Với khoảng 1.333 giây cho 33 span, các trace lớn hơn có thể chạm trần 1.800 giây.
2. Có cần tìm nguyên nhân khiến request từ số 29 khác version 7 dù cùng seed không?
