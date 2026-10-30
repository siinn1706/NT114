# Bàn giao: hai gói Kaggle cho thí nghiệm thiếu nguồn metric — 2026-10-28

**Trạng thái:** hai gói đã dựng và verify. Mỗi gói có 4 case × 3 điều kiện × 3 seed = 36 lượt chạy. Toàn bộ test CPU qua, 66/66. Chưa commit.

**Cập nhật 13:40 ngày 2026-10-28:** gói A đã lên Kaggle. Trước khi đẩy, em chạy lại `verify-package.py` và kết quả pass (log `runtime/test-logs/verify-package-missing-source-a-push-01.log`).
- Dataset `siinn1706/rclagent-one-trace-smoke-261026` ở version 14, private, bundle sha256 `a2bccc75…f821a`.
- Notebook `siinn1706/rclagent-one-trace-gpu-smoke-261026` ở version 12, private, chạy trên T4; lúc ghi đang ở trạng thái RUNNING.
- `check-kaggle-private.py` xác nhận dataset private.
- Kết quả sẽ tải về `runtime/kaggle-output-v12`, source về `runtime/kaggle-source-v12`.
- Gói B chưa đẩy.

Thiết kế và quyết định ở [report phân tích](analysis-261028-1104-rclagent-pilot-trace-failure-analysis.md), [report triển khai](impl-261028-1228-rclagent-missing-source-conditions.md) và dòng ngày 2026-10-28 trong `decisions.md`. Sếp chọn giữ 8 case, chia 2 phiên. Tách case theo thứ tự trong `pilot-selection.json`: 4 case đầu vào gói A, 4 case sau vào gói B.

## 1. Hai gói

Mọi đường dẫn tính từ `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`.

| Gói | Trace (case) | Bundle sha256 | Ước điểm / ước cao |
|---|---|---|---|
| A, đang là bundle dùng | `de6a503b` (checkoutservice_cpu_1), `30e3c732` (emailservice_delay_3), `5f7a7727` (checkoutservice_mem_1), `99f095ae` (currencyservice_loss_3) | `a2bccc75…f821a` | 5,6 giờ / 7,1 giờ |
| B | `ad1c27da` (currencyservice_disk_3), `7bbfa606` (recommendationservice_socket_1), `272a47c2` (recommendationservice_cpu_2), `29583dc6` (emailservice_delay_1) | `196e38c4…0ab7c` | 5,2 giờ / 6,6 giờ |

- **Ước lượng.** Lấy tổng số giây ước cho từng trace trong `train-batches.json`, nhân với 9 lượt (3 điều kiện × 3 seed). Ước cao nhân thêm 1,25 và cộng 480 giây setup. Cả hai gói đều dưới giới hạn 12 giờ của một phiên Kaggle.
- **Bản sao.** Mỗi gói có một bản sao đầy đủ (bundle, sha256, manifest, notebook, `package-validation.json`) ở `runtime/bundle-missing-source-a/` và `runtime/bundle-missing-source-b/`. Notebook trong mỗi thư mục đã nhúng sẵn hash của đúng gói đó.
- **Bundle v11 cũ.** Được sao lưu ở `runtime/bundle-v11-backup/` (sha256 `af27179a…2a91`).
- **Gói đã dựng.** Nằm ở `runtime/package-missing-source-a` và `runtime/package-missing-source-b`. Gói A có 2.846 phép so endpoint trên CPU, gói B có 2.602; tất cả pass.

## 2. Kiểm

| Kiểm | Kết quả |
|---|---|
| `verify-package.py` cho A và B | pass, mỗi gói 53 file. Script có thêm `check_runs`, kiểm các điểm sau: mỗi trace có đủ mọi điều kiện và mọi seed; `run_id` không trùng; nguồn của mỗi lượt khớp với điều kiện; sha256 của `pilot-selection.json` vẫn khớp; `metric-repair.py` trong bundle trùng với bản gốc |
| `test-kaggle-harness.py` | 31/31 OK. Test hash cũ đã qua lại nhờ bundle mới |
| `test-missing-source-conditions.py` | 14/14 OK |
| `test-tool-result-budget.py`, `test-vllm-t4-compat.py`, `test-prefill-bench.py` | 11/11, 4/4, 6/6 OK |

Log nằm ở `runtime/test-logs/*-missing-source-02.log`, cùng các log `prepare-`, `refresh-`, `notebook-` và `verify-package-missing-source-{a,b}-01.log`.

Sửa thêm trong lượt này:
- `verify-package.py` có hàm `check_runs` và so `metric-repair.py` trong bundle với bản gốc.
- `build-notebook.py` ghi số lượt chạy, các điều kiện và các seed vào phần mô tả của notebook.

## 3. Chạy trên Kaggle

1. **Phiên A.** Tạo dataset private chỉ chứa `rclagent-kaggle-bundle.zip` của gói A, rồi chạy notebook `rclagent-kaggle-smoke.ipynb` ở chế độ private với một GPU T4.
2. **Phiên B.** Chép 4 file trong `runtime/bundle-missing-source-b/` ra thư mục `kaggle/`, chạy lại `verify-package.py`, rồi lặp lại bước 1 với gói B.
3. **Nếu một phiên bị cắt.** Gắn ZIP kết quả của phiên đó làm input cho phiên mới. Runtime chỉ chạy tiếp các lượt chưa xong; lượt đã xong, kể cả lượt thất bại, không chạy lại.
4. **Sau mỗi phiên.**
   - Tải kết quả về và kiểm sha256.
   - Kiểm trong `events.jsonl` rằng seed của request khớp với seed của lượt.
   - Kiểm rằng mọi sự kiện `tool_result` ghi `source` đúng với điều kiện.
   - Chấm theo mục 6.3 của report phân tích.

**Cập nhật 22:45 ngày 2026-10-28:** notebook version 12 kết thúc ở trạng thái ERROR sau 27 giây, ở stage B (`Expanded Kaggle manifest SHA256 mismatch`), chưa chạy model. Nguyên nhân là kernel khởi động lúc 06:32:46 UTC, chỉ 13 giây sau khi file của dataset v14 được tạo (06:32:33), nên Kaggle gắn phiên bản dataset cũ. Dataset hiện ở trạng thái `ready`, và manifest tải về khớp `51ed1f1b…`. Bundle và notebook không lỗi. Output lỗi nằm ở `runtime/kaggle-output-v12`. Em chạy lại `verify-package.py` (pass, log `verify-package-missing-source-a-push-02.log`) rồi đẩy lại notebook không đổi thành version 13. Từ đây kết quả tải về `runtime/kaggle-output-v13`. Lần đẩy sau (gói B) phải đợi `kaggle datasets status` báo `ready` rồi mới đẩy kernel.

**Cập nhật 03:55 ngày 2026-10-29:** cả A (v13) và B (v1) đã xong và đã tải về: A ở `runtime/kaggle-output-v13`, B ở `runtime/kaggle-output-b-v1`. Phần chấm và kết luận nằm ở [report kết quả](results-261029-0130-rclagent-missing-source-kaggle-runs.md). Các file ở cấp `kaggle/` hiện là của gói B.

**Cập nhật 22:55 ngày 2026-10-28:** gói B chạy song song với A, dùng dataset và kernel riêng nên input của A không bị đụng.
- Đã chép 5 file của gói B vào `kaggle/`, nên các file ở cấp `kaggle/` giờ là của B; bản A vẫn còn ở `runtime/bundle-missing-source-a/`. `verify-package.py` pass, log ở `verify-package-missing-source-b-push-01.log`.
- Dataset `siinn1706/rclagent-missing-source-b-261028` ở version 1, private (đã kiểm qua API), bundle sha256 `196e38c4…0ab7c`. Manifest tải về từ Kaggle khớp `74b55383…` và có đúng 4 trace của B. Thư mục upload là `runtime/kaggle-dataset-upload-b`.
- Kernel `siinn1706/rclagent-missing-source-b-gpu-261028` ở version 1, private, chạy trên T4, lúc đẩy ở trạng thái RUNNING. Thư mục upload là `runtime/kaggle-kernel-upload-b`. Kết quả sẽ tải về `runtime/kaggle-output-b-v1`.
- Script chấm `analyze-missing-source-results.py`: nhận các cặp ZIP kết quả và manifest; kiểm sha256, seed của request, `source` của tool_result và tên top-1 có hậu tố; áp quy tắc sàng lọc ở mục 6.3; kèm hai mốc CPU lấy từ `metric-dev-rank.csv`. Đã thử trên một ZIP tổng hợp.

**Cập nhật 14:10 ngày 2026-10-28:** lỗi `node_id`/`dropna` đã được báo cho tác giả qua tài khoản `siinn1706`, ở issue [LLM4AIOps/RCLAgent-V2#2](https://github.com/LLM4AIOps/RCLAgent-V2/issues/2).
