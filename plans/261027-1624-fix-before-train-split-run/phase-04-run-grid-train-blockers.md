---
phase: 4
title: "Gỡ chặn run_grid trên tập train"
status: completed
priority: P1
effort: "1d"
dependencies: []
---

# Phase 4: Gỡ chặn run_grid trên tập train

## Goal
`run_grid` chạy được với `split_role: train` mà không vô tình đưa chính query vào kho truy hồi. Lượt chạy không vỡ vì file evidence cũ, và tự dừng khi split hoặc condition matrix lệch build.

## Findings
- **A1 (High, đã xác minh):** `run_grid.py:193-197` dùng mọi incident train làm kho. `:470-476` raise khi một incident trong kho cũng là query. Vì vậy mọi retrieval khác `none` đều hỏng trên tập train.
- **A2 (High, đã xác minh):** `run_grid.py:418-432` kiểm mọi `*.json` trong `evidence_dir` trước khi lọc incident được chọn.
- **A3 (Medium):** `run_grid.py:116-146` đọc `assignments.jsonl` và `condition-matrix-*.json` mà không so với `_build.json`.

## Files to Create / Modify
- Modify: `nt114-rca/nt114-rca/src/rca/run_grid.py`
- Modify: `nt114-rca/nt114-rca/tests/test_run_grid_canonical.py` (hoặc thêm test cạnh nó)
- Có thể sửa: `nt114-rca/nt114-rca/configs/*.yaml` (thêm cấu hình train mẫu nếu sếp chọn)

## Tasks & Steps
1. **Test đỏ** trên fixture synthetic (`data_synth_home`), mỗi finding một test:
   - A1: `split_role: train` cộng `retrieval: [bm25]` thì raise.
   - A2: một file evidence lạc trong `evidence_dir` thì lượt chạy vỡ.
   - A3: split có `dataset_digest` khác build hiện tại thì lượt chạy vẫn đi tiếp, không báo gì.
2. **A1, theo Q2:**
   - Khuyến nghị: kho leave-one-group-out. Với mỗi query, loại khỏi kho mọi incident cùng group (dùng phần loại nhóm đã có ở `:499-504`). Giữ nguyên assert cho các role khác.
   - Nếu sếp chọn không dùng retrieval trên tập train: raise rõ ràng khi `split_role: train` và retrieval khác `none`, kèm thông báo hướng dẫn.
3. **A2:** chỉ load và kiểm các file của incident được chọn. Các file khác được đếm và ghi log, không raise. Thiếu file của incident được chọn thì vẫn raise như cũ.
4. **A3:** khi `run` khởi động, so `split.json` `builds[].dataset_digest` và `build_id` của matrix với `_build.json`. Lệch thì raise và gợi ý chạy `verify-splits`.

## Verification
- `pytest -m "not realdata" tests/test_run_grid_canonical.py tests/test_leakage.py tests/test_leakage_audit.py` pass.
- `python -m rca.prep verify-splits` cho 16/16 OK.
- `leakage_audit` chạy trên cấu hình train mới không báo query nằm trong kho của chính nó.

## Risk / Rollback
Leave-one-group-out đổi tập precedent so với cấu hình test hiện tại, nên chỉ áp khi `split_role: train`. Đường test và val phải trùng hành vi cũ, có test khóa lại.
