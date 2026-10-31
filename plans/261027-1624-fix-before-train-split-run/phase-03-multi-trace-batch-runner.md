---
phase: 3
title: "Batch runner nhiều trace"
status: completed
priority: P1
effort: "2d"
dependencies: [1]
---

# Phase 3: Batch runner nhiều trace

## Goal
Harness chạy được một danh sách trace thuộc tập train. Mỗi trace có gói đã kiểm equivalence, artifact riêng, và trạng thái pass hoặc fail ghi nhận độc lập. Lượt chạy tiếp được sau khi session Kaggle bị ngắt. Các trần và thiết lập đóng băng giữ nguyên cho từng trace.

## Những chỗ đang cứng một trace
- `prepare-bundle.py:28-30` (`RAW`, `TRACE_ID`), `:111-113,135` (33 span), `:161,207,212` (`checkoutservice_cpu_2`), `:266` (partition)
- `smoke-worker.py:400` (`assert len(nodes) == 33`)
- `verify-package.py:36,71` (trace_id và tiền tố `log_id`)
- `selection.json`: một `query_window` và một `root_span_id`
- `kaggle-runtime.py:471,483`: dừng cả lượt khi trace lỗi; một deadline 1.800 giây cho một trace

## Files to Create / Modify
- Modify: `.../kaggle/prepare-bundle.py`: nhận danh sách ca và trace (từ `work/re2ob-case-roles-by-source-key.csv` và `error_traces`). Dựng một gói con cho mỗi trace. Kiểm CPU equivalence theo ca, quét dữ liệu đầy đủ một lần cho mỗi ca.
- Modify: `.../kaggle/smoke-worker.py`: lấy số span kỳ vọng từ `selection.json`, không dùng hằng số 33.
- Modify: `.../kaggle/verify-package.py`: kiểm từng gói con với trace_id và tiền tố của chính nó, `full_data_seconds`, và không có nhãn trong `input/`.
- Modify: `.../kaggle/kaggle-runtime.py`: vòng lặp trace, mỗi trace có worker, deadline 1.800 giây và trần 160 requests riêng.
  - Trace thất bại (HarnessStop, deadline, lỗi HTTP) được ghi `failed` kèm lý do rồi chuyển sang trace kế tiếp. Không retry và không đổi cấu hình.
  - Artifact ghi theo `run/<trace_id>/`.
  - File `progress.json` để bỏ qua các trace đã xong khi chạy lại.
- Modify: `.../kaggle/summarize-repair-run.py`, `.../kaggle/build-notebook.py`: tóm tắt nhiều trace; notebook vẫn giữ 4 ô code.
- Modify: `.../kaggle/test-kaggle-harness.py`: test cho các bước trên.

## Tasks & Steps
1. **Test đỏ:**
   - Gói 2 trace của 2 ca khác nhau.
   - Một trace bị ép HarnessStop thì trace còn lại vẫn chạy (dùng worker giả, không có model).
   - Chạy tiếp sau khi ngắt giữa chừng thì bỏ qua trace đã xong.
   - Số span lấy từ selection.
2. Tổng quát hóa `prepare-bundle.py` theo ca. Chạy lại cho `checkoutservice_cpu_2` một mình: dữ liệu và `cpu-equivalence.json` phải trùng với gói v8 (trừ thứ tự hoặc metadata đã ghi rõ).
3. Sửa worker, validator và runtime như trên. Chạy trên CPU với worker giả cho 3 trace.
4. Chọn danh sách pilot khoảng 5 trace train, phân tầng theo số span, gồm trace 45 span (ước khoảng 1.818 giây, có thể chạm deadline). Chỉ dựng gói và kiểm CPU; chưa chạy GPU.
5. Ước thời gian và quota GPU cho pilot và cho cả 240 trace, đưa vào report.

## Verification
- Test harness cũ và mới đều pass. `verify-package` pass cho từng gói con.
- CPU equivalence pass cho mọi ca của pilot.
- Gói của `checkoutservice_cpu_2` sinh lại khớp v8 (log so sánh lưu ở `runtime/test-logs/`).
- Kaggle pilot chỉ chạy khi sếp duyệt riêng (theo Q4).

## Risk / Rollback
- Đây là thay đổi rộng nhất. Giữ `runtime/package-v7` và `bundle-v7` để quay lại.
- Equivalence theo ca dễ sai khi cửa sổ ±1.200 giây của hai ca chồng nhau. Phải giữ assert "dòng trong cửa sổ đầy đủ đều thuộc đúng ca"; nếu assert hỏng thì dừng, không nới.
