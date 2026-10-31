# Sửa phạm vi query RCLAgent và smoke Kaggle version 6 — 2026-10-27

**Kết luận:** lỗi E của version 5 đã được chứng minh và sửa ở packaging/harness. Smoke sau sửa (Kaggle version 6) chạy đúng query `cartservice`, nhận đúng dữ liệu đầy đủ, rồi dừng có kiểm soát ở request thứ ba vì prompt cần 126.088 token, vượt context 16.384. Chưa có self-state đầu tiên, recursion, synthesis, kết quả cuối hoặc scorer. Đây là thất bại mới với nguyên nhân cụ thể; cách xử lý cần quyết định phương pháp.

Phạm vi: HEAD `7941e17`, working tree chỉ có report review chưa track (giữ nguyên). Không commit/push, không sửa upstream, canonical data hoặc split.

## 1. Nguyên nhân lỗi E version 5

- Tool tác giả (`tool_server.py`, `tools_gpt.py` tại `3052e7a`) nhận mọi `service_name`/`timestamp`, lọc `str.contains(service)` và cửa sổ ±60 giây (log) hoặc ±1.200 giây (metric), trên toàn bộ dữ liệu gộp. Vòng tool của `self_state_verification` cho model gọi tool lặp lại, không ràng buộc service theo span.
- Request 2 của version 5 hỏi `cartservice` tại `1708475368662` (giây của root span). Dữ liệu đầy đủ có 1.570 dòng log `cartservice` sau lọc INFO/DEBUG trong cửa sổ đó; phản hồi gốc 274.292 byte. `cartservice` có trong danh sách service của system prompt tác giả, không có span trong trace.
- Gói cũ chỉ chứa dòng của các cặp (service của span, giây), và guard chỉ cho các cặp đó. Kết luận: query hợp lệ theo tác giả; gói thiếu phạm vi và guard hạn chế hơn code tác giả. Không phải query sai, lỗi HTTP hoặc lỗi schema.
- Tái hiện: guard của HEAD chặn đúng query này trên gói v5; guard mới cho qua trên gói mới (`kaggle/runtime/test-logs/old-vs-new-guard.log`).

## 2. Thay đổi

- [prepare-bundle.py](../261026-1713-rclagent-tai-hien-toi-thieu/kaggle/prepare-bundle.py): gói mọi dòng metric trong [1708474168, 1708476569] và mọi dòng log được tool phục vụ trong [1708475308, 1708475429], tức ±1.200/±60 giây quanh hai giây của trace, mọi service. Kiểm: dòng trong cửa sổ của dữ liệu gộp bằng đúng dòng của ca `checkoutservice_cpu_2` (không ca val/test nào chồng thời gian). 66.846 dòng metric, 1.747 dòng log.
- `selection.json`: thay `query_pairs` bằng `query_window` (contract nội bộ giữa bundle và worker).
- [smoke-worker.py](../261026-1713-rclagent-tai-hien-toi-thieu/kaggle/smoke-worker.py): mọi service được phép; chỉ chặn giây ngoài cửa sổ, parse như endpoint gốc. Kiểm lại tham số ở URL thực gửi tới tool server vì client tác giả nối chuỗi không encode.
- `verify-package.py` kiểm cửa sổ, phạm vi dòng và nguồn ca; `build-notebook.py` cập nhật mô tả; [harness-requirements.txt](../261026-1713-rclagent-tai-hien-toi-thieu/kaggle/harness-requirements.txt) ghi môi trường CPU.
- Giữ nguyên: upstream, prompt, model/revision, sampling, context 16.384, output 512/1.024, retry 3, 4 vòng tool/span, 160 requests, 1.800 giây, concurrency 1, không truncate. Gói v5 được giữ ở `kaggle/runtime/package-v5` và `kaggle/runtime/bundle-v5`.

## 3. Kiểm CPU

Môi trường: `kaggle/runtime/harness-env`, Python 3.12.10, không dùng site-packages hệ thống, ghim theo phía Kaggle (pandas 2.2.3, numpy 2.2.6, Flask 3.1.2, requests 2.32.5, tenacity 9.1.2, jsonschema 4.25.1, psutil 7.0.0). Venv cũ `runtime/cpu-env` bật system site-packages nên không dùng.

| Kiểm | Kết quả |
|---|---|
| Harness trước sửa, venv mới | 14/14 pass (lỗi 9/14 trước đây chỉ do thiếu jsonschema) |
| Harness sau sửa | 18/18 pass, gồm hồi quy v5, cửa sổ, URL injection, tool result quá context |
| T4 compat | 4/4 pass |
| Equivalence endpoint | 822 so sánh khớp byte: 21 service × 32 timestamp cho log, × 4 cho metric (full 9,4 triệu dòng), cùng 66 span/children |
| Package validator | pass; hash, allowlist 24 member, notebook, nhãn chỉ ở `scoring/` |

Log ở `kaggle/runtime/test-logs/`. Chưa kiểm trên CPU: cleanup process group Linux (chỉ có bằng chứng native). Không chạy lại test split/leakage vì không đổi code hoặc split của project.

Dự báo trước GPU bằng tokenizer Qwen đúng revision: request 2 = 1.024 token (khớp server version 5), request 3 sẽ là 126.089 token nếu model lặp query.

## 4. Kaggle version 6

Notebook private `siinn1706/rclagent-one-trace-gpu-smoke-261026` version 6, dataset private version 8, bundle SHA256 `1a3dcf92…63fa`, một Tesla T4, context 16.384.

- B: kernel gốc tái hiện lỗi, bản vá qua 15 kiểm số học.
- D: pass, 3 requests HTTP 200, 858 prompt + 140 completion token.
- E: 2 requests HTTP 200, 1.925 prompt + 170 completion token, không retry. Request 1 gọi tool cho `frontendservice` (log rỗng, metric "No matching records found." như dữ liệu đầy đủ). Request 2 gọi lại `cartservice`; tool trả 272.734 byte, khớp phản hồi dữ liệu đầy đủ sau chuẩn hóa xuống dòng (pandas dùng CRLF trên Windows, LF trên Linux). Request 3 bị chặn trước khi gửi: `Context overflow: input=126088, reserved_output=512, context=16384; no truncation`.
- Thời gian: E tới cleanup 25,04 giây; C tới cleanup 132,60 giây. Trần 160 requests/1.800 giây không bị chạm.
- Tài nguyên lấy mẫu: RSS cây process đỉnh 9.176.907.776 byte; GPU 13.232 MiB.
- Cleanup: vLLM 0, tools-synthetic −15, worker-protocol 0, tools-telemetry −15, worker-trace 1. Scorer không chạy, archive không chứa groundtruth.
- Archive `rclagent-kaggle-repair-v6-results.zip`, SHA256 `091a1975abe2faeabc117023ae56d39e51f2b335617b96f3e2cb65d2712bd8b9`, khớp file `.sha256` Kaggle xuất; tổng hợp ở `kaggle-repair-v6-summary.json`. Code notebook khớp source tải lại; metadata private.

## 5. Ánh xạ RE2-OB

Hai UID của `checkoutservice_cpu_1` có cùng inject time vì `rcaeval.24e078fc27784c41` lấy từ thư mục `RE2-OB/checkoutservice_cpu/multi-source-data` (REJECT `DUPLICATE`, không có vai), còn `rcaeval.2bfb7e2fe0813f3e` lấy từ `RE2-OB/checkoutservice_cpu/1` (ACCEPT, train). Preprocess tác giả bỏ qua `multi-source-data`. Join bằng `source_incident_key` cho 90/90 ca một-một, không lệch inject time: train 48, val 21, test 21; 87 ACCEPT, 3 ACCEPT_WITH_WARNINGS. Bảng mới ở `work/re2ob-case-roles-by-source-key.csv` (script `work/scripts/re2ob-case-roles-by-source-key.py`); bảng cũ giữ nguyên. Không đổi split hoặc canonical.

## 6. Trạng thái

| Mục | Trạng thái |
|---|---|
| CPU validated | Có, trong phạm vi bảng mục 3 |
| GPU smoke completed | Chưa: dừng ở E, request 3, context overflow |
| Scoring completed | Chưa chạy |
| Batch val/test | Chưa chạy |
| Fine-tuning | Chưa triển khai, ngoài nhánh này |

**Pilot val chưa đủ điều kiện.** Blocker: dưới tool contract tác giả và context 16.384 không cắt ngữ cảnh, chỉ một query service hợp lệ cũng có thể đưa vào prompt khoảng 125 nghìn token. Chưa đo tần suất trên các ca khác, nên chưa biết đây là ngoại lệ hay phổ biến.

## Câu hỏi còn mở

Cần quyết định cách xử lý tool result vượt context, vì mỗi cách đổi một ràng buộc đã chốt:

1. Giữ nguyên ràng buộc, ghi kết quả này là giới hạn của cấu hình 4B/T4 với phương pháp gốc. Trước pilot, quét CPU kích thước phản hồi tool trên các trace của 90 ca để biết tỷ lệ ca chắc chắn overflow.
2. Tăng context: 126.088 + 512 token vượt sức chứa KV cache của một T4; cần GPU khác ngoài Kaggle T4 hoặc cấu hình khác. Đổi phần cứng/giới hạn.
3. Đặt ngân sách cho tool result (ví dụ cắt hoặc gộp dòng trùng), áp dụng đồng nhất mọi ca và báo như một sai lệch so với tác giả. Đổi semantics và vi phạm quy tắc không truncate hiện tại.
4. Đổi backbone có context dài hơn. Đổi model.
