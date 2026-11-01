---
phase: 5
title: "Replay mã dựng hint (đã gộp vào phase 2 và 4)"
status: cancelled-merged
priority: P3
effort: "0h"
dependencies: [4]
---

# Phase 5: Replay mã dựng hint (đã gộp, không còn là phase riêng)

<!-- red-team: phase 5 merged into analyzer columns -->
## Lý do gộp
- Ở dữ liệu đã thấy, GT nằm trong danh sách hint ở 14 trên 14 run `metric`, luôn ở danh sách "metric anomalies only" [reviewer đo, chưa tính lại bằng analyzer]. Vì vậy `drop_d1` và `relabel_d2` chỉ đổi kích thước và thành phần danh sách, không thể làm GT xuất hiện hay biến mất; `oracle_carrier` luôn làm GT có mặt nên chỉ cho một chặn trên hiển nhiên. Tiêu đề "GT xuất hiện hay biến mất" bị bỏ.
- Bản kiểm tương đương cũ (so với `parse_prompt` của `check-hash-seed-order.py`) là vòng tròn vì hàm đó dựng lại từ GEG bằng chính luật chuỗi. Kiểm thật nằm ở phase 2: phân tích dòng hint trong văn bản prompt cuối.
- Replay chạy lại một hàm chuỗi con và không nói gì về phản ứng của LLM. Giai đoạn S2 (consolidation do LLM làm) không có can thiệp nào ở đây, nên mệnh đề cơ chế phải là "định vị mô tả"; cơ chế cần can thiệp có model ở RQ (c).

## Phần còn giữ
- Cột `hint_list_size`, `gt_sole_entry`, `d1_dropped_list_size`, `d2_dropped_list_size` trong `spans.csv` và `runs.csv` (phase 2), cùng kiểm `hint_equivalence` ở phase 4.
- Báo cáo (phase 7) có một đoạn ngắn: mã tác giả tự tạo ra bao nhiêu lỗi dán nhãn trong hint (kích thước danh sách và dịch vụ không phải GT như `frontendservice` ở danh sách ERROR LOGS); câu giới hạn bắt buộc: chỉ phần mã, không phải hành vi LLM; kết luận cho S3 là "S3 không làm mất GT ở 14 trên 14 run", không hơn.

## Bỏ
`replay-evidence-hint.py`, `test-replay-evidence-hint.py`, thư mục `analysis-evidence-loss-hint-replay-s1-v2/`, biến thể `oracle_carrier`. Không file nào của phase này được tạo.

<!-- validation: required sections -->
## Requirements
Không có yêu cầu thực thi: phase đã hủy và gộp vào phase 2 và 4. Yêu cầu còn giữ nằm ở các cột hint của analyzer (phase 2) và kiểm `hint_equivalence` (phase 4).

## Files
Không tạo hay sửa file nào trong phase này (xem mục Bỏ).

## Steps
Không có bước. Công việc tương ứng là các bước của phase 2 (cột hint) và phase 4 (`hint_equivalence`).

## Verification
Không có. Phase 2 và 4 chứa kiểm tương đương hint.

## Risks and Rollback
Rủi ro: hiểu nhầm phase này vẫn còn việc. Phase đã hủy, không có thay đổi để hoàn tác; không file nào được tạo.
