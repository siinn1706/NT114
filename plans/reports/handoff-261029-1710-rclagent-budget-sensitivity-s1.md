# Bàn giao: chạy kiểm độ nhạy trần ngân sách (S1) — 2026-10-29 17:10

Sếp đồng ý chạy cấu hình đề xuất ở mục 4 của `analysis-261029-1629-rclagent-round-2-budget-stops.md`. Hai kernel GPU đã được đẩy lên và đang chạy. Chưa có kết quả.

## Cấu hình

| Giới hạn | Vòng 2 (cấu hình chính) | S1 |
|---|---|---|
| Vòng tool mỗi span | 4 | 8 |
| Request mỗi lượt, tính cả hỏi lại | 160 | 320 |
| Deadline mỗi lượt | 1.800 s | 2.400 s |

Các phần giữ nguyên:
- 72 lượt như vòng 2 (A và B, mỗi gói 36 lượt). Danh sách `runs` trong manifest trùng từng byte với vòng 2.
- Model, prompt, tool, sampling, context 16k, giới hạn output, chính sách hỏi lại, `metric-repair.py` và ngân sách kết quả tool.

Vượt context vẫn là lỗi dừng, không cắt ngữ cảnh. Lỗi này được đếm thành nguyên nhân riêng (`context_overflow`). Rủi ro này có thật: với 8 vòng, các kết quả `search_logs`, mỗi kết quả tối đa 2.048 token, có thể cộng dồn vượt 16k. Ở vòng 2, prompt self-state lớn nhất chỉ 1.924 token.

## Thay đổi mã (chưa commit)

- `smoke-worker.py`:
  - Thêm cờ `--tool-rounds`, `--max-requests` và `--deadline-seconds`. Mặc định là 4, 160 và 1.800, nên các gói cũ chạy như trước.
  - Thông báo dừng ghi đúng trần đang dùng, ví dụ "Per-span tool round budget exceeded (8)" và "40-minute RCLAgent deadline exceeded".
- `kaggle-runtime.py`:
  - `HARNESS_LIMITS` chứa giá trị mặc định. `harness_limits(manifest)` đọc `harness_limits` trong manifest và từ chối khóa lạ hoặc giá trị không phải số nguyên dương.
  - `run_once` ghi các giới hạn vào `settings.json`. `run_trace` dùng deadline của gói và truyền cờ cho worker.
- `verify-package.py`: kiểm `harness_limits` và ghi kết quả vào `package-validation.json`.
- `build-notebook.py`: viết các trần trong notebook theo manifest. Khi khác cấu hình chính, notebook thêm đoạn "Cấu hình kiểm độ nhạy về trần".
- Hai analyzer:
  - Dừng vì deadline được nhận theo chuỗi con "RCLAgent deadline exceeded", vì thông báo nay có độ dài deadline ở đầu.
  - `analyze-completion-and-budget-stops.py` có thêm nguyên nhân `context_overflow`.
- `test-kaggle-harness.py`:
  - Thêm 5 test: trần vòng theo guard, thông báo deadline, giá trị mặc định, ghi đè từ manifest và từ chối giá trị sai.
  - Fixture có thêm mode `tool-call`.
- `tool-result-budget-check.json`: chạy lại, và chỉ `worker_sha256` thay đổi.

Kiểm tra:
- Các bộ test: `test-kaggle-harness` 43/43, gồm cả test hash gói nay đã qua; missing-source-conditions 14/14; tool-result-budget 11/11; vllm-t4-compat 4/4; prefill-bench 6/6; analyzer 16/16; completion 4/4. Log nằm ở `runtime/test-logs/*-sensitivity-limits-01.log` và `*-s1-02.log`.
- Chạy lại hai analyzer trên dữ liệu vòng 2:
  - `summary.json`, `runs.csv`, `pairs.json`, `cases.json` và `budget-stops.json` giống từng byte.
  - `completion.csv` chỉ thêm cột `failed_context_overflow`, toàn bộ giá trị là 0.

## Gói và Kaggle

| | A | B |
|---|---|---|
| Stage | `runtime/package-missing-source-a-s1/` | `runtime/package-missing-source-b-s1/` |
| Bản lưu | `runtime/bundle-missing-source-a-s1/` | `runtime/bundle-missing-source-b-s1/` |
| Bundle SHA256 | `45e3dd20436f06ec…` | `cdbe98d54126b33f…` |
| Manifest SHA256 | `933b817b0c42b20a…` | `d48a26e516bf0100…` |
| Dataset (private, v1) | `siinn1706/rclagent-missing-source-a-s1-261029` | `siinn1706/rclagent-missing-source-b-s1-261029` |
| Kernel (private, T4, v1) | `siinn1706/rclagent-missing-source-a-s1-gpu-261029` | `siinn1706/rclagent-missing-source-b-s1-gpu-261029` |

- So với gói vòng 2, manifest chỉ khác ở khóa `harness_limits` và hash của `kaggle-runtime.py` và `smoke-worker.py`.
- Chỉ đẩy kernel sau khi cả hai dataset ở trạng thái `ready`. Bản Kaggle giải nén trùng từng byte với 53 thành viên của ZIP, không có tệp thừa.
- Trạng thái riêng tư đã kiểm qua API và ghi ở `runtime/kaggle-private-status-s1.json`.
- Các tệp ở cấp `kaggle/` (`manifest.json`, `rclagent-kaggle-bundle.zip`, `rclagent-kaggle-smoke.ipynb`, `package-validation.json`) nay là bản B-S1. Bản B vòng 2 vẫn còn ở `runtime/bundle-missing-source-b-r2/`. Không ghi đè ZIP, manifest hay log của các vòng trước.

## Chi phí và theo dõi

- Ước tính mỗi gói khoảng 7,5–8 giờ T4. Trường hợp xấu nhất khoảng 9,8 giờ, vẫn dưới trần 12 giờ của Kaggle.
- Em không theo dõi suốt thời gian chạy. Khi sếp báo xong thì tải về `runtime/kaggle-output-{a,b}-s1-v1/`.

## Việc khi có kết quả

1. Chạy `analyze-missing-source-results.py` cho A, B và A+B, và `analyze-completion-and-budget-stops.py` cho A và B. Ghi vào các thư mục `runtime/analysis-missing-source-*-s1*` mới.
2. Báo cáo theo mục 4 của `analysis-261029-1629`, đặt S1 cạnh vòng 2 và không thay kết luận pilot đã nhận. Các mục cần có:
   - tỷ lệ hoàn tất theo điều kiện;
   - R@1/MRR trên toàn bộ lượt và trên các lượt hợp lệ, kèm mẫu số;
   - các cặp mà cả hai lượt đều hoàn tất;
   - 8 lượt từng chạm trần ở vòng 2.
3. Kiểm điều kiện: các lượt không chạm trần ở vòng 2 phải có đầu ra model giống vòng 2. Phần nào khác thì ghi lại, và không quy cho việc đổi trần.

## Cập nhật 2026-10-30 09:40: S1 v1 hỏng, đã dựng lại v2, chưa đẩy kernel

**S1 v1 lỗi ngay ô B, không chạy lượt nào.** Cả hai kernel đều dừng với `RuntimeError: Notebook runtime differs from hashed package runtime`. Log nằm ở `runtime/kaggle-output-{a,b}-s1-v1/`.
- Nguyên nhân: khi sửa cho S1, `kaggle-runtime.py` bị ghi lại với dòng CRLF. `refresh-package.py` băm byte thô (`c3cc3689…`). Còn `build-notebook.py` nhúng nguồn đọc bằng `read_text()`, vốn đã chuẩn hóa về LF (`326800ab…`).
- `verify-package.py` không bắt được lỗi vì chỉ so notebook với text đã chuẩn hóa, không so với hash trong manifest.
- Vòng 2 không gặp lỗi này vì mọi file khi đó đều là LF.

**Sửa:**
- `build-notebook.py` nhúng đúng byte của runtime và từ chối dựng nếu hash khác manifest. Ô notebook ghi runtime bằng `write_bytes`.
- `verify-package.py` kiểm hash nguồn nhúng bằng hash runtime trong manifest, đúng phép kiểm `unpack()` chạy trên Kaggle.
- Thêm test `test_notebook_runtime_matches_packaged_runtime`. Test này lỗi trên notebook v1 và pass trên v2.
- Đưa 6 file CRLF về LF. Nội dung không đổi, và `git diff` không thấy khác.
- Chạy lại `tool-result-budget-check.json`: chỉ `worker_sha256` đổi.

**Kiểm tra:**
- Test: harness 44/44, missing-source-conditions 14/14, tool-result-budget 11/11, vllm-t4-compat 4/4, prefill-bench 6/6, analyzer 16/16, completion 4/4. Log ở `runtime/test-logs/*-s1-v2.log`.
- Đã giả lập các phép kiểm hash của Kaggle trên v2: runtime, bundle, manifest và từng thành viên đều khớp.
- So với vòng 2, manifest chỉ khác `harness_limits` và hash/bytes của `kaggle-runtime.py` và `smoke-worker.py`. `runs` giống hệt vòng 2.
- Hai reviewer độc lập không thấy lỗi chặn. Lưu ý: runtime v1 lẫn v2 đều mang các sửa audit 261029-1128 (F5 tool server, F2 chấm từng run), nên mã runtime không giống hệt vòng 2. Các sửa này chỉ đổi cách xử lý lỗi, không đổi trần hay metric.

| | A | B |
|---|---|---|
| Bản lưu v2 | `runtime/bundle-missing-source-a-s1-v2/` | `runtime/bundle-missing-source-b-s1-v2/` |
| Bundle SHA256 | `024e877a5fd2508f…` | `a076518f58484dc5…` |
| Manifest SHA256 | `1e0f3150c97bcb9b…` | `702b89ded0470645…` |
| Dataset | version mới đã tải lên. Bản tải về trùng từng byte với 53 thành viên (`runtime/kaggle-dataset-check-{a,b}-s1-v2/`) | như A |
| Kernel | **chưa đẩy**, thư mục đẩy là `runtime/kaggle-kernel-upload-a-s1-v2/` | **chưa đẩy**, thư mục đẩy là `runtime/kaggle-kernel-upload-b-s1-v2/` |

**Chặn:** `kaggle kernels push` trả về `Maximum weekly GPU quota of 30.00 hours reached`. Khi quota được làm mới, đẩy bằng lệnh `kaggle kernels push -p runtime/kaggle-kernel-upload-{a,b}-s1-v2`. Hai lượt chạy cần khoảng 15–20 giờ T4, nên có thể phải đẩy A và B vào hai tuần khác nhau. Sau khi đẩy, ghi lại trạng thái riêng tư như ở v1. Các tệp cấp `kaggle/` hiện là bản B-S1 v2.

## Cập nhật 2026-10-31: S1 v2 đã chạy và phân tích

Tài khoản `svuittri` đã chạy hai kernel S1 v2 trên dataset của `siinn1706`. Gói A pass 36/36 lượt. Gói B pass 34/36 lượt, và hai lượt lỗi là lỗi giao thức đã xảy ra y như vậy ở vòng 2. Cả 8 lượt từng chạm trần ở vòng 2 đều pass. Các lượt không chạm trần cho điểm giống vòng 2. Kết quả, kiểm điều kiện và giới hạn nằm ở [results S1 v2](results-261031-1715-rclagent-s1-v2-budget-sensitivity.md).
