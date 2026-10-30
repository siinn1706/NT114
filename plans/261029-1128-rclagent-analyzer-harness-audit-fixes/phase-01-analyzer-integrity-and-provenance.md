---
phase: 1
title: "Sửa analyzer kèm test"
status: completed
priority: P1
effort: "3h"
dependencies: []
---

# Phase 1: Sửa analyzer kèm test

## Mục tiêu

Sửa `analyze-missing-source-results.py` để analyzer:

- không báo lỗi toàn vẹn giả,
- không để thứ tự tham số hay cặp ZIP–manifest sai làm đổi kết quả,
- không âm thầm tính 0 cho lượt chưa được chấm điểm.

Giữ nguyên mọi con số của vòng 1.

## File

- Sửa: `analyze-missing-source-results.py`. Cập nhật cả docstring.
- Tạo: `test-analyze-missing-source-results.py`. Theo mẫu của `test-missing-source-conditions.py`: dùng `unittest`, load module bằng `spec_from_file_location`, dựng fixture ZIP giả trong `tempfile`.

## Các bước

1. **F10.** Ở `load()`, thay `assert` SHA256 bằng `raise SystemExit(...)`. Lỗi ghi rõ đường dẫn, hash thực tế và hash đã ghi.

2. **F4, gắn ZIP với bundle.** Trong `load()`:
   - Đọc token đầu của `manifest.parent / 'rclagent-kaggle-bundle.zip.sha256'`. Thiếu file thì `SystemExit`.
   - Yêu cầu có `run/progress.json` và `progress['bundle_sha256']` bằng token đó.
   - Yêu cầu `set(progress['traces'])` là tập con của tập `run_id` trong manifest. Có khóa thừa thì `SystemExit` và liệt kê các khóa đó.
   - Thêm cột `bundle_sha256` vào mỗi dòng.

3. **F2/F7, phiên và điểm.**
   - Trong `load()`, đọc `run/status.json` nếu có, ghi `{zip sha: status, stage, error}` vào danh sách phiên.
   - Mỗi dòng có `status == 'passed'` mà `scored` là False thì đưa vào `unscored_passed`.
   - Summary thêm ba khóa: `sessions`, `unscored_passed` (danh sách run_id) và `provisional`. `provisional` là True khi có phiên khác `passed`, có run `pending` hoặc `running`, hoặc `unscored_passed` không rỗng.
   - Không đổi khóa nào đã có.

4. **F7, dòng events hỏng.** Trong `check_run`, parse từng dòng trong `try/except json.JSONDecodeError`. Dòng hỏng thì thêm vấn đề `unparseable events line N` và tiếp tục với các dòng parse được.

5. **F1 + F6, kiểm chuỗi retry theo thứ tự.** Bỏ phép so tổng số sự kiện retry. Thay `expected_seed` bằng một hàm duyệt events theo thứ tự, lọc request ở phase `trace` cùng các sự kiện `malformed_tool_call_retry` và `fatal`.
   - **Request attempt 0.** Seed phải bằng seed của run. Request này mở chuỗi mới: `first = number`.
   - **Sự kiện retry.** Ba điều kiện:
     - `number` bằng số của request ngay trước nó.
     - `next_attempt` bằng attempt của request đó cộng 1, và không quá 3.
     - `next_seed` bằng `sha256("{seed}:{first}:{next_attempt}")[:4] & 0x7fffffff`. Công thức này viết độc lập trong analyzer, không import từ worker.
   - **Request attempt > 0.** Phải đứng ngay sau một sự kiện retry khớp: `attempt == next_attempt`, `retry_of == first`, và seed trong payload bằng `next_seed`.
   - **Sự kiện retry treo.** Một sự kiện retry không có request theo sau chỉ hợp lệ khi đó là sự kiện retry cuối cùng và sự kiện kế tiếp trong log là `fatal` với lý do bắt đầu bằng `Model request budget exhausted` hoặc `30-minute RCLAgent deadline exceeded`.
   - Mọi trường hợp khác thêm một vấn đề có mô tả cụ thể.
   - Giữ cột `retries` bằng số sự kiện retry.

6. **F3, khóa trùng.** Trong `main()`, sau khi nạp mọi dòng, đếm `run_id` và `(case, seed, condition)` bằng `Counter`. Có khóa trùng thì `SystemExit` và liệt kê.

7. **F4, thiết kế thiếu.** Trong `screen()`, với mỗi so sánh, liệt kê các cặp `(case, seed)` thiếu một trong hai điều kiện, trên tập case × seed có trong dữ liệu.
   - Thêm hai khóa: `missing_pairs` (danh sách) và `evaluable` (True khi danh sách rỗng và `seeds > 0`).
   - Khi `evaluable` là False thì `opens_direction` là `None`.
   - Các khóa số hiện có giữ nguyên cách tính.

8. **Docstring.** Cập nhật docstring cho đúng các kiểm mới.

## Test (viết trước khi sửa, xác nhận chúng thất bại trên code cũ)

| Test | Fixture | Kỳ vọng |
|---|---|---|
| Retry treo trước fatal hết ngân sách | Events: request 159 a0, retry, request 160 a1, retry, fatal budget | integrity `ok` |
| Retry treo trước fatal khác | Như trên nhưng fatal là `Invalid structured response` | Có vấn đề |
| `retry_of` sai | `retry_of=99`, seed tính theo 99 | Có vấn đề |
| Attempt nhảy cóc | Dãy 0, 2 | Có vấn đề |
| `next_seed` lệch seed thật | `next_seed=12345` | Có vấn đề |
| Chuỗi retry bị chen bởi transport retry | 503 ở attempt 1, rồi attempt 0 mới | integrity `ok` |
| Run trùng | Cùng một cặp truyền hai lần | `SystemExit` |
| Bundle lệch | `bundle_sha256` của progress khác sidecar | `SystemExit` |
| Khóa progress thừa | Progress có run ngoài manifest | `SystemExit` |
| Thiếu điều kiện | Manifest không có `no_metric` | `evaluable: False`, `opens_direction: None` |
| SHA256 sai | ZIP bị sửa | `SystemExit`, kể cả khi chạy bằng `-O` (dùng subprocess) |
| Dòng events hỏng | Dòng cuối bị cụt | Phân tích chạy hết, run có vấn đề `unparseable events line N` |
| Pass mà không có điểm, pending, phiên `failed` | `author-score.txt` là traceback; một run không có progress; `status.json` failed | `unscored_passed`, `provisional: True` |
| Đường bình thường | Run sạch, 3 điều kiện × 3 seed | integrity `ok`, `provisional: False`, `evaluable: True` |

Các fixture có thể lấy lại ý từ repro trong scratchpad của audit. Test phải tự dựng mọi fixture, không phụ thuộc file ngoài repo.

## Verification

```bash
cd "F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle"
runtime/harness-env/Scripts/python.exe -B test-analyze-missing-source-results.py -v
```

Lưu log vào `runtime/test-logs/analyze-missing-source-results-01.log`.

## Rủi ro và rollback

- Rủi ro: các kiểm mới từ chối dữ liệu vòng 1. Phase 2 bắt trường hợp này.
- Rollback: file analyzer chưa được track, nên `git checkout` không khôi phục được. Trước khi sửa, chép một bản sao vào scratchpad; khi cần rollback thì khôi phục từ bản sao đó và xóa file test mới.
