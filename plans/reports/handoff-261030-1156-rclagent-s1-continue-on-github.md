# Bàn giao để tiếp tục trên GitHub: RCLAgent, kiểm độ nhạy trần S1 — 2026-10-30

Tài liệu này viết cho người tiếp quản, hoặc cho AI của người đó, khi bắt đầu từ một bản clone mới của nhánh `feat/rclagent-harness-budget-guard`. Đọc file này trước, rồi mới đọc các report được dẫn.

## Đang ở đâu

| Việc | Trạng thái |
|---|---|
| Vòng 1 và vòng 2 thiếu nguồn (72 lượt, 4 trace × 3 điều kiện × 3 seed, chia hai gói A và B) | Đã chạy và phân tích. Xem [results vòng 2](results-261029-1448-rclagent-missing-source-round-2.md) và [phân tích dừng vì ngân sách](analysis-261029-1629-rclagent-round-2-budget-stops.md) |
| Sửa analyzer và harness theo audit | Xong. Xem [plan 261029-1128](../261029-1128-rclagent-analyzer-harness-audit-fixes/plan.md) |
| Mã kiểm độ nhạy S1 (8 vòng tool mỗi span, 320 request, 2.400 s mỗi lượt) | Xong và đã test. Xem [handoff S1](handoff-261029-1710-rclagent-budget-sensitivity-s1.md) |
| Chạy S1 v1 trên Kaggle | Hỏng ở ô B do lệch hash runtime (CRLF). Không chạy lượt nào |
| Sửa lỗi CRLF và dựng gói S1 v2 | Xong. Dataset v2 đã lên Kaggle và đã kiểm trùng từng byte |
| Chạy S1 v2 trên Kaggle | Xong ngày 2026-10-31, tài khoản `svuittri` chạy hai kernel `svuittri/rclagent-missing-source-{a,b}-s1-gpu-261030`. Output ở `runtime/kaggle-output-{a,b}-s1-v2/` |
| Phân tích S1 và báo cáo cạnh vòng 2 | Xong. Xem [results S1 v2](results-261031-1715-rclagent-s1-v2-budget-sensitivity.md) và [plan 261031-1655](../261031-1655-rclagent-s1-v2-analysis-and-pr2/plan.md) |
| Quyết Q1–Q9 và cố định thứ tự service trong prompt | Xong ngày 2026-10-31. Xem [quyết định 261031-1839](decision-261031-1839-rclagent-audit-q1-q9.md) |

Phần "Cập nhật 2026-10-30" trong [handoff S1](handoff-261029-1710-rclagent-budget-sensitivity-s1.md) ghi chi tiết nguyên nhân lỗi v1, cách sửa, các hash của v2 và kết quả kiểm.

## Những gì không có trên GitHub

`plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/runtime/` nằm trong `.gitignore`. Bản clone sẽ không có các thứ sau:
- `harness-env/`: venv dùng để chạy test và các script.
- `hf-cache/`: tokenizer Qwen3-4B, revision `cdbee75f…`.
- Thư mục stage `package-*` và bản lưu `bundle-*`, gồm cả `bundle-missing-source-{a,b}-s1-v2/`.
- `kaggle-output-*` (output tải từ Kaggle) và `analysis-*` (output analyzer).
- Thư mục đẩy `kaggle-dataset-upload-*` và `kaggle-kernel-upload-*`.

Ở cấp `kaggle/`, các file `manifest.json`, `rclagent-kaggle-smoke.ipynb` và `package-validation.json` là gói B dựng lại ngày 2026-10-31 từ stage `runtime/package-missing-source-b-hashseed` (giới hạn S1, thêm hash seed cố định và sửa Q8, Q9; chưa chạy trên Kaggle) và có commit. Bản B-S1 v2 đã chạy nằm nguyên trong `kaggle/s1-v2/b/`. `rclagent-kaggle-bundle.zip` ở cấp `kaggle/` thì không có trên GitHub, nhưng ZIP của cả A lẫn B đều có trong `kaggle/s1-v2/`. Cách dựng lại môi trường và dữ liệu RE2-OB nằm ở [handoff train split](handoff-261028-0630-rclagent-train-split-kaggle-batches.md), mục điều kiện ngoài repo, và ở [README CPU](../261026-1713-rclagent-tai-hien-toi-thieu/README.md).

## Việc tiếp theo

### 1. Chạy S1 v2

Có hai cách, tùy người chạy có bản `runtime/` của máy gốc hay không.

**Cách 1: tài khoản `siinn1706`, trên máy gốc.** Dataset v2 đã sẵn sàng, chỉ cần đợi quota được làm mới rồi đẩy:

```bash
kaggle kernels push -p runtime/kaggle-kernel-upload-a-s1-v2
kaggle kernels push -p runtime/kaggle-kernel-upload-b-s1-v2
```

Chạy hai lệnh này từ thư mục `kaggle/`. Mỗi gói cần khoảng 7,5–8 giờ T4, trường hợp xấu nhất khoảng 9,8 giờ. Hai gói cộng lại có thể vượt quota một tuần, nên có thể phải đẩy A và B vào hai tuần khác nhau.

**Cách 2: một tài khoản Kaggle khác.** Hai dataset `siinn1706/rclagent-missing-source-{a,b}-s1-261029` đang ở chế độ private.

Cập nhật 2026-10-30 12:10: tài khoản `svuittri` đã được thêm làm collaborator, quyền READER, cho cả hai dataset. Metadata đọc lại từ Kaggle xác nhận hai dataset vẫn private. Gói A và B đã có sẵn trên GitHub, trong [`kaggle/s1-v2/`](../261026-1713-rclagent-tai-hien-toi-thieu/kaggle/s1-v2/). Mỗi thư mục `a/` và `b/` có:
- notebook;
- `kernel-metadata.json` cho `svuittri`: kernel private, T4, có internet, gắn dataset của `siinn1706`;
- bundle ZIP, `.sha256`, `manifest.json` và `package-validation.json` của bản v2.

File `.gitattributes` giữ nguyên từng byte của các file này khi clone. Các bước chạy:

```bash
kaggle config view   # username phải là svuittri
cd plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle
sha256sum s1-v2/a/rclagent-kaggle-bundle.zip   # phải là 024e877a…; với B là a076518f…
kaggle kernels push -p s1-v2/a
kaggle kernels push -p s1-v2/b   # nếu quota tuần còn đủ, xem dưới
kaggle kernels status svuittri/rclagent-missing-source-a-s1-gpu-261030
```

Lưu ý khi chạy:
- Không cần venv hay tokenizer để đẩy kernel. Mọi thứ khác đều chạy trên Kaggle.
- Mỗi gói cần khoảng 7,5–8 giờ, nên cả hai gói gần hết quota 30 giờ của một tuần.
- Không tự theo dõi suốt thời gian chạy. Khi xong thì làm tiếp bước 2.

Chọn một trong hai hướng:
- Chủ tài khoản thêm người chạy làm collaborator của hai dataset trên Kaggle. Sau đó chỉ cần đổi `id` trong `kernel-metadata.json` sang tên của tài khoản mới, còn `dataset_sources` giữ nguyên.
- Tạo dataset mới từ đúng file ZIP v2 bằng `kaggle datasets create`, giữ private. Sau đó sửa `id` trong `dataset-metadata.json`, và sửa `id` cùng `dataset_sources` trong `kernel-metadata.json`. Cách này cần ZIP của máy gốc, hoặc phải dựng lại gói (xem bước 4).

Notebook không chứa tên tài khoản. Nó chỉ kiểm SHA256 của bundle và manifest: A là `024e877a…` / `1e0f3150…`, B là `a076518f…` / `702b89de…`. Vì vậy dùng tài khoản khác không làm đổi notebook.

Trước khi đẩy kernel:
- Tải dataset về một thư mục riêng và so từng byte với 53 thành viên của ZIP. Khi version mới còn đang xử lý, Kaggle có thể đã báo `ready` nhưng tải về vẫn lỗi 404.
- Kiểm qua API rằng dataset và kernel đều private, rồi ghi kết quả như trong `runtime/kaggle-private-status-s1.json`.

### 2. Tải kết quả

Khi kernel xong, tải output vào `runtime/kaggle-output-{a,b}-s1-v2/` bằng `kaggle kernels output <owner>/<kernel> -p <dir>`. Không ghi đè thư mục `kaggle-output-*-s1-v1`, vì đó là bằng chứng của lỗi v1.

### 3. Phân tích và báo cáo

Làm theo mục "Việc khi có kết quả" trong [handoff S1](handoff-261029-1710-rclagent-budget-sensitivity-s1.md):
1. Chạy `analyze-missing-source-results.py` cho A, B và A+B, và chạy `analyze-completion-and-budget-stops.py` cho A và B. Ghi output vào các thư mục `runtime/analysis-missing-source-*-s1*` mới.
2. Viết report đặt S1 cạnh vòng 2. S1 không thay kết luận pilot đã nhận. Report cần có:
   - tỷ lệ hoàn tất theo điều kiện;
   - R@1 và MRR trên toàn bộ lượt và trên các lượt hợp lệ, kèm mẫu số;
   - các cặp mà cả hai lượt đều hoàn tất;
   - 8 lượt từng chạm trần ở vòng 2.
3. Kiểm điều kiện: các lượt không chạm trần ở vòng 2 phải có đầu ra model giống vòng 2. Phần nào khác thì ghi lại.

### 4. Nếu phải dựng lại gói S1 từ đầu

Thứ tự lệnh, chạy trong `kaggle/` bằng Python của `runtime/harness-env`:
1. `prepare-bundle.py` tạo stage.
2. `add-condition-runs.py STAGE ../work/pilot-trace-analysis/pilot-selection.json` thêm các lượt chạy.
3. Thêm khóa sau vào `manifest.json` của stage. Không script nào thêm khóa này; ở S1 nó được thêm bằng tay:
   ```json
   "harness_limits": {"max_model_requests_including_retry": 320, "rcl_deadline_seconds": 2400, "max_tool_rounds_per_span": 8}
   ```
4. Dựng và kiểm gói: `refresh-package.py STAGE`, `build-notebook.py`, rồi `verify-package.py`.

Nếu sửa `smoke-worker.py` hoặc `tool-result-budget.py`, phải chạy lại `check-tool-result-budget.py TOKENIZER_DIR` trước `verify-package.py`.

## Ràng buộc cần giữ

- **File `.py` trong `kaggle/` phải dùng LF.** Repo đặt `core.autocrlf=true`, nên công cụ sửa file trên Windows có thể ghi lại CRLF. Nay `build-notebook.py` sẽ từ chối dựng, và `verify-package.py` cùng test `test_notebook_runtime_matches_packaged_runtime` sẽ báo lỗi nếu hash lệch. Nếu gặp lỗi đó, đưa file về LF rồi chạy lại `refresh-package.py`.
- Vượt context là lỗi dừng, không được cắt ngữ cảnh.
- Không sửa kết quả cũ. Không ghi đè bundle, manifest hay log của các vòng trước. Output mới luôn ghi vào thư mục mới.
- Không mở lại H1/IM1. Các câu Q1–Q9 trong [audit](audit-261029-1121-rclagent-missing-source-analyzer-harness.md) đã được quyết ngày 2026-10-31 theo ủy quyền của sếp, xem [quyết định 261031-1839](decision-261031-1839-rclagent-audit-q1-q9.md).
- Mọi test chỉ chạy CPU. Lệnh chạy toàn bộ test, trong `kaggle/`:
  ```bash
  for t in test-kaggle-harness test-missing-source-conditions test-tool-result-budget test-vllm-t4-compat test-prefill-bench test-analyze-missing-source-results test-analyze-completion-and-budget-stops; do runtime/harness-env/Scripts/python.exe -X utf8 $t.py; done
  ```
  Kết quả mong đợi: 44, 14, 11, 4, 6, 16 và 4 test pass. `test-kaggle-harness`, `test-missing-source-conditions` và `test-vllm-t4-compat` đọc dữ liệu trong `runtime/`, nên trên bản clone mới sẽ lỗi nếu chưa dựng lại `runtime/`. Lỗi đó không có nghĩa là mã sai.

## Câu hỏi còn mở

- Dùng tài khoản Kaggle nào để chạy S1 v2? Nếu dùng tài khoản khác thì chọn chia sẻ dataset hay tạo dataset mới?
- Đẩy A và B cùng tuần, hay tách ra để không vượt quota?
