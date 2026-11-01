---
phase: 9
title: "Ghi chú xác nhận bằng S1 v3 (không phải phase thực thi)"
status: note
priority: P3
effort: "0.5h"
dependencies: [4]
---

# Phase 9: Ghi chú S1 v3 (chuyển thành mục trong bàn giao)

<!-- red-team: phase 9 reduced to a handoff note -->
S1 v3 chạy cùng prompt và cùng seed với S1 v2, chỉ khác thứ tự hint (hash seed cố định) và vài thay đổi harness (`validate_calls` đổi cách chấp nhận `Action: `, kiểm sống của server) [UNVERIFIED về mức ảnh hưởng tới luồng]. Nó không thêm bằng chứng độc lập, nên không còn là phase; nó là một dòng việc trong bàn giao (phase 8).

<!-- validation: required sections -->
## Requirements
- Chỉ chạy khi sếp báo S1 v3 xong và output đã tải về; không theo dõi hay thăm dò Kaggle.
- Không thêm bằng chứng độc lập, không sửa luật hay kết luận dựa trên S1 v3.

## Files
- Đọc: `runtime/kaggle-output-{a,b}-s1-v3/`, `s1-v3/{a,b}/manifest.json`, `runs.csv` của S1 v2.
- Tạo: `runtime/analysis-evidence-loss-s1-v3*` và một mục "S1 v3 như bản sao" trong báo cáo kết quả (phase 7).

## Steps
Các bước đánh số bên dưới (đợi sếp báo S1 v3 đã xong và output đã tải về).
Không theo dõi hay thăm dò Kaggle trong lúc chờ.
1. Kiểm hash zip khớp file `.sha256` và `check-hash-seed-order.py` báo thứ tự hint đúng seed 0.
2. Kiểm hash biên nhận còn khớp. Nếu không, đây không còn là xác nhận.
3. `$PY analyze-evidence-loss.py runtime/analysis-evidence-loss-s1-v3 --label s1-v3 A $ZA3 $MA3 B $ZB3 $MB3` với `ZA3=runtime/kaggle-output-a-s1-v3/rclagent-smoke/rclagent-smoke-results.zip`, `MA3=s1-v3/a/manifest.json`, tương tự B.
4. `join` `runs.csv` của S1 v3 với S1 v2 như phase 4, bước 6. Báo số cặp trùng ở I0 đến I3, I4, I5 và danh sách cặp lệch. Kỳ vọng I0 đến I3 trùng là một **giả thuyết đo được**, không phải bất biến, vì thay đổi tool-call rejection của S1 v3 có thể đổi luồng.
5. Thêm mục "S1 v3 như bản sao" vào báo cáo kết quả, nói rõ nó không thêm bằng chứng độc lập, và không sửa luật hay kết luận dựa trên nó. Lệch nhiều ở I0 đến I3 là một phát hiện về tính tất định, đáng báo.

## Verification
Hash zip khớp `.sha256`, `check-hash-seed-order.py` báo đúng thứ tự seed 0, hash biên nhận còn khớp, và số cặp trùng ở I0 đến I3, I4, I5 được báo kèm danh sách cặp lệch.

## Rollback
Xóa các thư mục đầu ra `analysis-evidence-loss-s1-v3*` và mục S1 v3 trong báo cáo.
