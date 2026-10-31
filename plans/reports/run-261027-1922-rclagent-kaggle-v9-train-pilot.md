# Pilot 5 trace train trên Kaggle, version 9 — 2026-10-27

**Kết luận:** lượt chạy xong với 3/5 trace passed và 2/5 failed. Cả hai trace failed dừng vì cùng một lý do, và lý do này nằm ở guard của harness chứ không ở model hay upstream. Ở bước consolidation của một span lá không có bằng chứng, model trả `"local_root_cause": null`. Upstream nhận output này như mọi chuỗi khác. Guard của `smoke-worker.py` thì đòi trường này phải là chuỗi, nên dừng cả trace. Batch runner làm đúng thiết kế: ghi trace lỗi vào `progress.json`, rồi chuyển sang trace kế tiếp. Điểm dưới đây chỉ mô tả 3 trace, không phải ước lượng accuracy.

Phạm vi theo duyệt của sếp: tải bundle pilot lên dataset private, rồi chạy notebook private. Không đổi upstream, prompt, model, sampling, context, output, retry, số vòng tool, ngân sách, các trần, dữ liệu hay split. Không commit, không push.

## 1. Cấu hình

- Dataset `siinn1706/rclagent-one-trace-smoke-261026` (private) chứa bundle `bf069dba…3110`. Kaggle tự giải nén ZIP thành 61 file, có đủ 5 thư mục `traces/<id>/`.
- Notebook `siinn1706/rclagent-one-trace-gpu-smoke-261026` (private) version 9, chạy trên một Tesla T4.
- `check-kaggle-private.py` xác nhận dataset và notebook vẫn private. `summarize-repair-run.py` xác nhận code notebook tải về khớp bản đã push.
- Model Qwen3-4B-Instruct-2507 rev `cdbee75f`, context 16.384, temperature 0,7, top_p 0,8, top_k 20, seed 20261026. Trần mỗi trace là 160 requests và 1.800 giây.

## 2. Kết quả theo trace

| Trace | Ca (nhãn) | Span | Trạng thái | E (giây) | Requests | Rút gọn `search_logs` | R@1 / R@3 / MRR |
|---|---|---:|---|---:|---:|---|---|
| `2095688a…` | productcatalogservice_delay_3 | 45 | failed | 1.177 | 109 | 1/50 | — |
| `3753f2a8…` | recommendationservice_socket_3 | 4 | passed | 220 | 17 | 2/8 | 0 / 0 / 0,167 |
| `c6033940…` | emailservice_socket_2 | 23 | passed | 909 | 74 | 2/27 | 0 / 0 / 0,125 |
| `1e527c6a…` | currencyservice_mem_3 | 25 | failed | 796 | 69 | 2/30 | — |
| `f6526e73…` | productcatalogservice_mem_1 | 33 | passed | 1.302 | 105 | 2/37 | 0 / 1 / 0,333 |

- Cả 374 requests của 5 trace đều trả HTTP 200. Phần protocol D có thêm 3 requests, cũng pass. Không trace nào chạm trần requests hay deadline.
- Có 9 kết quả `search_logs` bị rút gọn, từ 75–129 nghìn token xuống khoảng 450 token mỗi kết quả, và không dòng nào bị bỏ.
- Ở cả 3 trace passed, danh sách kết quả liệt kê 10 service, tức gần như mọi service. Vì vậy R@10 luôn bằng 1 và không nói lên gì. Không trace nào có nhãn đúng ở vị trí đầu.
- Trace `3753f2a8…` trả tên pod (`productcatalogservice-0`, …). Scorer vẫn khớp được nhãn service ở vị trí 6.
- Toàn bộ lượt chạy mất 4.517,7 giây (75 phút), gồm cài đặt và nạp model; riêng E mất 4.404 giây. RSS đỉnh khoảng 9,23 GB, GPU đỉnh 13.494 MiB.
- Mọi worker và tool server đã dừng (tool server −15, vLLM 0). Hai worker failed có exit 1. Máy local không còn process nào em khởi động.
- Artifact `rclagent-kaggle-repair-v9-results.zip`, SHA256 `76089108…96d3fb`, khớp file `.sha256` của Kaggle. Tóm tắt ở `kaggle/kaggle-repair-v9-summary.json`; output thô ở `kaggle/runtime/kaggle-output-v9/`.

## 3. Nguyên nhân hai trace failed

- **Lỗi cụ thể.** `2095688a…` dừng ở request 109, khi consolidation span `b81ba52867406a5c` (paymentservice). `1e527c6a…` dừng ở request 69, khi consolidation span `914e95bd69410302` (cartservice). Cả hai là span lá, không có span con và không có log lỗi. Model trả JSON hợp lệ, đúng `span_id`, nhưng có `"local_root_cause": null`.
- **Guard chặt hơn upstream.** Guard trong `smoke-worker.py` (`decorate`, nhánh consolidate) đòi `local_root_cause` phải là `str`, nên gọi `guard.stop` và dừng cả trace. Upstream `coordinator.py` không đọc trường này. Output consolidation chỉ được chuyển nguyên văn lên span cha, và bước tổng hợp cuối đọc Global Evidence Graph. Chỗ duy nhất upstream nhắc đến trường này là mẫu JSON trong prompt.
- **Model trả "không có nguyên nhân" theo hai kiểu.** Ở các consolidation đã xong, model nhiều lần trả một chuỗi như `"none"` (41 lần trên 5 trace), và guard cho qua. Chỉ hai lần model trả `null` mới làm dừng trace.
- **Trace 45 span.** Lúc dừng, trace này đã xong 45/45 bước self-state và 9/45 bước consolidation, sau 1.177 giây. Mỗi bước consolidation tốn khoảng 10 giây. Với 36 bước còn lại, E ước khoảng 1.540 giây, dưới deadline 1.800 giây. Ước lượng 1.820 giây trước đây là quá cao.

## 4. Đề xuất sửa (chưa làm)

- **Sửa guard.** Cho `local_root_cause` nhận `str` hoặc `null`. Guard vẫn dừng khi output không phải JSON, sai `span_id`, thiếu hẳn trường này, hoặc trường có kiểu khác. Thêm test hồi quy dùng đúng hai output của version 9.
- **Kiểm và đóng gói lại.** Sửa này làm đổi hash worker, nên phải chạy lại test harness, budget và T4; dựng lại bundle; chạy `verify-package`; rồi tải lên một dataset version mới.
- **Chạy lại pilot.** Cần sếp duyệt lần chạy Kaggle mới. Bundle mới có sha256 khác, nên `progress.json` của version 9 không dùng để chạy tiếp được. Lần chạy lại sẽ chạy cả 5 trace, mất khoảng 75 phút.
- Không đổi thiết lập đóng băng nào: upstream, prompt và cách tính điểm giữ nguyên.

## 5. Ghi chú

- Log của scorer có dòng `Error in sitecustomize … No module named 'wrapt'`. Dòng này có cả ở version 8; nó đến từ `sitecustomize` của Kaggle trong env chấm điểm và không ảnh hưởng điểm.
- Ba trace passed chưa đủ để nói gì về accuracy. Tập train còn là adaptation (backbone 4B, context 16k, ngân sách tool result), nên không so trực tiếp với Table I.

## Câu hỏi còn mở

1. Sếp có duyệt sửa guard như mục 4 không? Nếu có, sếp có duyệt chạy lại pilot 5 trace trên Kaggle với dataset và notebook private không?
