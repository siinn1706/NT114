---
phase: 3
title: "Sửa runtime kèm test"
status: completed
priority: P2
effort: "2h"
dependencies: []
---

# Phase 3: Sửa runtime kèm test

## Mục tiêu

Hai thay đổi trong `kaggle-runtime.py`, áp dụng cho gói dựng sau vòng 2:

- **F5.** Một tool server không kịp sẵn sàng không còn được tiếp tục phục vụ run sau.
- **F2.** Một lần scorer lỗi không còn làm các run phía sau mất điểm.

## File

- Sửa: `kaggle-runtime.py`.
- Sửa: `test-kaggle-harness.py`. Chỉ thêm test, không đổi test cũ.

## Các bước

1. **F5.** Tách hàm lồng `start_tools` trong `run_once` (khoảng dòng 568-572) thành hàm cấp module `start_tool_server(proc, name, argv, env, probe_url, timeout)`. Hàm làm theo thứ tự:
   1. Gọi `assert_free_port(5000)`. Nếu gặp `OSError`, raise `RuntimeError('Port 5000 still held by another process; refusing to start a tool server')`.
   2. Gọi `child = proc.start(...)`.
   3. Gọi `wait_ready(child, probe_url, timeout)` bên trong `try`. Gặp `BaseException` thì gọi `proc.stop(child)` rồi `raise`.

   `run_once` gọi hàm mới; argv, env và timeout 90 giây giữ nguyên.

2. **F2.** Tách vòng chấm điểm của stage F (khoảng dòng 612-623) thành hàm `score_runs(package, result, progress, python, env)`.
   - Mỗi run `passed` được chấm trong một `try` riêng.
   - Mỗi run ghi `scoring/<run_id>/scorer-status.json` dạng `{'exit': code, 'error': repr | None}`.
   - Hàm trả về danh sách các run chấm lỗi.
   - Trong `run_once`, nếu danh sách khác rỗng thì raise `RuntimeError` sau vòng lặp, kèm danh sách. Phiên vẫn kết thúc `failed` ở stage F như cũ, nhưng mọi run khác đã được chấm.
   - `rmtree` thư mục scoring, các file chép sang và `timeout=60` giữ nguyên.

3. Không đổi gì khác trong `run_once`: thứ tự stage, việc dừng vLLM trước khi đọc nhãn, chính sách resume.

## Test (thêm vào `test-kaggle-harness.py`)

| Test | Cách làm | Kỳ vọng |
|---|---|---|
| Server không sẵn sàng bị dừng | `proc` giả ghi lại lời gọi `start`/`stop`; `child` giả có `poll()` trả `None`; `probe_url` trỏ tới cổng đóng; timeout 1 giây | Raise `TimeoutError`, và `stop` được gọi với đúng `child` đó |
| Cổng đang bị giữ | Test tự bind `127.0.0.1:5000` rồi gọi `start_tool_server` | Raise `RuntimeError`, `proc.start` không được gọi |
| Scorer lỗi ở một run | Gói giả có `upstream/evaluate.py` thoát mã 1 khi thư mục chứa `bad`, còn lại in `R@1 : 1.0`, `R@3 : 1.0`, `MRR : 1.0`; ba run `passed`, run giữa là `bad`; python là `sys.executable` | Hai run còn lại có `author-score.txt`; run `bad` có `scorer-status.json` với exit 1; hàm trả về `['…bad…']` |

`Processes.stop` dùng `os.killpg`, hàm này không có trên Windows. Vì vậy test F5 dùng `proc` giả và chỉ kiểm thứ tự gọi, không kiểm việc giết process thật.

## Verification

```bash
cd "F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle"
PY=runtime/harness-env/Scripts/python.exe
$PY -B test-kaggle-harness.py
$PY -B test-missing-source-conditions.py
$PY -B test-tool-result-budget.py
$PY -B test-vllm-t4-compat.py
$PY -B test-prefill-bench.py
$PY -B test-analyze-missing-source-results.py
```

Suite cũ phải giữ đủ số test pass như trước: 35, 14, 11, 4 và 6. Cộng thêm 3 test mới, nên `test-kaggle-harness.py` phải ra 38/38. Lưu log vào `runtime/test-logs/*-audit-fixes-01.log`.

Không chạy `verify-package.py` trên thư mục `kaggle/` để lấy kết quả pass. Nó sẽ báo `RUNTIME_SOURCE` lệch notebook cho tới lần dựng gói sau. Đây là lệch có chủ đích, đã ghi ở mục rủi ro của plan.

## Rủi ro và rollback

- Rủi ro: tách hàm làm đổi hành vi của `run_once`. Chỉ dời code; argv, env, timeout và thông báo lỗi giữ nguyên.
- Rollback: `git checkout -- kaggle-runtime.py test-kaggle-harness.py`. Hai file này đang có thay đổi chưa commit từ trước, nên phải chép bản sao vào scratchpad trước khi sửa, rồi khôi phục từ bản sao chứ không dùng `git checkout`.
