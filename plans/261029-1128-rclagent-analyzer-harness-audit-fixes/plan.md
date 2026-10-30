---
title: "Sửa các lỗi đã tái hiện trong audit analyzer và harness thiếu nguồn RCLAgent"
description: "Sửa analyzer trước khi chấm vòng 2 và sửa runtime cho gói dựng sau vòng 2, theo audit 261029-1121."
status: completed
priority: P1
effort: 5.5h
branch: feat/rclagent-harness-budget-guard
tags: [rclagent, kaggle, analysis, harness, integrity]
blockedBy: []
blocks: []
created: 2026-10-29
---

# Sửa lỗi audit analyzer và harness thiếu nguồn

## Overview

Plan này sửa các lỗi đã tái hiện trong [audit 261029-1121](../reports/audit-261029-1121-rclagent-missing-source-analyzer-harness.md):

- Phần analyzer phải xong trước khi chấm kết quả vòng 2. Vòng 2 đang chạy trên Kaggle.
- Phần runtime chỉ áp dụng cho gói dựng sau vòng 2. Hai gói vòng 2 đã đẩy lên thì giữ nguyên, kể cả bản sao trong `runtime/bundle-missing-source-{a,b}-r2/`.

Các đường dẫn file tính từ `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`.

## Kết quả mong đợi

| # | Kết quả | Finding |
|---|---|---|
| 1 | Một run hợp lệ, dừng vì hết request hoặc quá deadline ngay sau một sự kiện retry, có integrity `ok`. Chuỗi retry được kiểm theo thứ tự, không tự tham chiếu | F1, F6 |
| 2 | Analyzer từ chối khi khóa run bị trùng, khi ZIP không thuộc bundle của manifest, hoặc khi SHA256 sai. Thiết kế thiếu điều kiện hay seed thì được đánh dấu là không đánh giá được | F3, F4, F10 |
| 3 | Lượt pass mà không có điểm, lượt pending, phiên chưa `passed` và dòng events hỏng đều hiện trong summary. Không dòng nào bị âm thầm tính 0, và không lỗi nào làm hỏng cả lần phân tích | F2, F7 (phía analyzer) |
| 4 | Tool server không kịp sẵn sàng thì bị dừng. Một server còn chiếm cổng 5000 sẽ làm run lỗi ngay, không trả lời thay cho server mới | F5 |
| 5 | Stage F chấm từng run độc lập và ghi lỗi scorer theo từng run | F2 (phía runtime) |

## Phases

| # | Phase | Status | Effort | Phụ thuộc |
|---|---|---|---|---|
| 1 | [Sửa analyzer kèm test](./phase-01-analyzer-integrity-and-provenance.md) | Completed | 3h | — |
| 2 | [Kiểm hồi quy trên vòng 1](./phase-02-round-one-regression-gate.md) | Completed | 0.5h | 1 |
| 3 | [Sửa runtime kèm test](./phase-03-runtime-tool-server-and-scoring.md) | Completed | 2h | — |

Phase 1 và 3 sửa các file khác nhau và có thể làm độc lập. Lệnh chạy toàn bộ test ở cuối phase 3 phủ cả hai phase.

## Ràng buộc

- Chỉ dùng CPU. Không gọi model hay GPU, không đẩy Kaggle, không commit, không push.
- Không sửa kết quả cũ (`runtime/kaggle-output-*`, `runtime/analysis-missing-source-*`). Output chạy lại ghi vào thư mục mới.
- Không sửa `smoke-worker.py`, vì vòng 2 đang chạy đúng bản này. F1 được sửa ở phía analyzer.
- Không dựng lại notebook hay bundle trong plan này.
- Không mở lại H1/IM1.
- Test dùng `runtime/harness-env/Scripts/python.exe`.

## Ngoài phạm vi

- Q1–Q9 trong mục 4 của audit, đang chờ sếp quyết.
- F7 phía runtime (khoảng đệm cho trần ngoài, handler SIGTERM), F8 (resume khi gắn cả ZIP lẫn `run/`), F9 (log của attempt bị ngắt).

## Tiêu chí hoàn tất

- [x] Test analyzer mới pass. Mỗi lỗi F1–F4, F6, F7 (phía analyzer) và F10 có ít nhất một test thất bại trên code cũ và pass trên code mới.
- [x] Chạy lại trên vòng 1 (A, B, A+B) cho mọi trường số trong summary bằng bản đã lưu: `by_condition`, `screening`, `status`, `suffixed_top1`, `cpu_baselines_by_trace`. `integrity_problems` vẫn rỗng và summary không bị đánh dấu `provisional`.
- [x] Toàn bộ suite cũ pass: `test-kaggle-harness.py`, `test-missing-source-conditions.py`, `test-tool-result-budget.py`, `test-vllm-t4-compat.py`, `test-prefill-bench.py`. Ngoại lệ có chủ đích: `test_expanded_kaggle_dataset_hash_verification` (37/38), xem mục Rủi ro.
- [x] `git status` chỉ thay đổi ở các file mà phase khai báo.

## Rủi ro

- Phase 3 đổi `kaggle-runtime.py`. `verify-package.py:134` so mã nguồn runtime nhúng trong notebook với file hiện tại, nên sẽ báo lệch với notebook ở thư mục `kaggle/` cho tới lần dựng gói sau. Đây là lệch có chủ đích. Gói vòng 2 có bản sao riêng và không bị ảnh hưởng.
- Cùng lý do, `test_expanded_kaggle_dataset_hash_verification` trong `test-kaggle-harness.py` lỗi (37/38 pass): `unpack()` so hash `kaggle-runtime.py` của gói đã stage (`777b8c37…`, đúng bằng bản trước khi sửa) với file đang chạy (`931fec99…`). Test sẽ pass lại khi dựng gói sau; không nới test.
- Lệch so với phase 3: cổng 5000 được kiểm bằng `connect` (`assert_unserved`) thay vì `assert_free_port` (`bind`). Sau khi tool server trước bị dừng, socket TIME_WAIT trên cổng 5000 làm `bind` không có `SO_REUSEADDR` thất bại trên Linux, sẽ chặn mọi trace sau trace đầu.
- Analyzer sẽ chặt hơn: thiếu file `.sha256` của bundle cạnh manifest thì từ chối, thay vì bỏ qua. Cả 4 thư mục bundle hiện đều có file này.

## Câu hỏi còn mở

- Đến lần dựng gói sau, dựng lại `rclagent-kaggle-smoke.ipynb` cùng lúc hay tách thành một bước riêng?

<!-- slug: 261029-1128-rclagent-analyzer-harness-audit-fixes -->
