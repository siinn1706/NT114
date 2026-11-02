---
phase: 4
title: "Dựng, kiểm và đẩy hai gói Kaggle"
status: planned
priority: P1
effort: "3h"
dependencies: [3]
---

# Phase 4: Dựng, kiểm và đẩy hai gói Kaggle

## Context
- Chuỗi dựng gói (đều trong `K/`): `prepare-bundle.py` (`select_traces` 117 chỉ nhận case train), `add-condition-runs.py STAGE SELECTION`, `refresh-package.py STAGE`, `build-notebook.py`, `verify-package.py`; `stage-kaggle-repair.py` gộp các bước test, refresh, notebook, verify.
- Gói mẫu: `K/s1-v3/{a,b}/` (manifest giống S1 v2 ở mục `runs`; khác kernel, hash seed cố định). Pin: model `Qwen/Qwen3-4B-Instruct-2507`, revision và vLLM `0.10.2` ở `K/kaggle-runtime.py:24-27`; `harness_limits` trong manifest S1 (8 vòng tool mỗi span, 320 request, 2400 giây).
- Trace: `272a47c2…`, `30e3c732…`, `de6a503b…` (không span GT); `29583dc6…`, `99f095ae…` và ba case còn lại của S1 (`5f7a77`, `7bbfa6`, `ad1c27`) có span GT. Trace id đầy đủ lấy từ `K/s1-v2/{a,b}/manifest.json`.
- Quyền: đẩy và tải Kaggle không cần hỏi lại (memory `kaggle-autonomy-approved`); dừng và báo nếu hết token. Không theo dõi Kaggle sau khi đẩy.

## Requirements
- Gói A (`K/x1/a/`): 3 trace không span GT × `metric_x1p`, `metric_x1q` × seed 20261026, 20261027, 20261028 = 18 run.
- Gói B (`K/x1/b/`): 5 trace có span GT × `metric_x1p` × 3 seed = 15 run.
- Cùng model, revision, vLLM, `harness_limits`, hash seed cố định và notebook như S1 v3; chỉ khác tập run và cờ `--x1`.
- File selection mới chứa đúng 8 trace trên, có hash trong manifest (`condition_design.selection_sha256`).
- Kernel private. Thêm hash `smoke-worker.py` và hash bundle vào `K/x1-prereg.json` trước khi đẩy.

## Files
- Create: `K/x1/{a,b}/` (manifest, bundle, notebook, `kernel-metadata.json`), file selection X1.
- Modify: `K/x1-prereg.json`.
- Create (gitignored): `K/runtime/kaggle-*-x1*` (biên nhận upload).

## Steps
1. Dựng stage A và B bằng `prepare-bundle.py` với danh sách trace, rồi `add-condition-runs.py` với tập điều kiện X1.
2. `refresh-package.py`, `build-notebook.py`, `verify-package.py` cho từng gói.
3. So manifest X1 với S1 v3: mọi khóa ngoài `runs`, `condition_design` và tên kernel phải giống; in diff.
4. Kiểm sống trên CPU nếu harness có đường chạy không cần model (như các lần đóng gói trước); nếu không có, ghi rõ là chưa kiểm.
5. Cập nhật `K/x1-prereg.json`; kiểm hash prereg còn khớp.
6. Đẩy hai kernel private; kiểm trạng thái private bằng `check-kaggle-private.py`.
7. Ghi bàn giao ngắn: tên kernel, thời điểm đẩy, ước lượng giờ chạy; rồi dừng.

## Checks
- `verify-package.py` thoát 0 cho cả hai gói.
- Số run trong manifest: A 18, B 15; `run_id` đúng mẫu.
- `check-kaggle-private.py` xác nhận kernel private.

## Risk / Rollback
- Hết quota GPU tuần: dừng sau bước 5, báo sếp.
- Gói A vượt giờ (nhánh `x1_query` dài hơn ước lượng): thứ tự run theo seed rồi trace (`add-condition-runs.py`) giữ các khối (trace, seed) trọn vẹn khi bị cắt.
- Rollback: xóa kernel trên Kaggle (sếp làm) và thư mục `K/x1/`.
