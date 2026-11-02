# Bàn giao: RQ (c) bước 1, tín hiệu thay thế khi bỏ metric

Ngày 2026-11-02. Plan: [261102-0035](../261102-0035-rclagent-rq-c-metric-drop-substitutes/plan.md). Kết quả: [báo cáo](analysis-261102-rclagent-metric-drop-substitutes-results.md). `K/` là `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`.

## Trạng thái

| Phase | Trạng thái | Biên nhận |
|---|---|---|
| 1 Kiểm kê tín hiệu | xong | [scout](scout-261102-rclagent-metric-substitute-signals.md) |
| 2 Tra tài liệu | xong (đọc qua tóm tắt công cụ) | [research](research-261102-rclagent-missing-metric-and-trace-blind-spot.md) |
| 3 Codebook | xong, sếp duyệt 2026-11-02 | [codebook](prereg-261102-rclagent-metric-substitute-codebook.md), `K/metric-substitute-prereg.json` |
| 4 Script và test | xong | `K/analyze-metric-substitutes.py`, `K/test-analyze-metric-substitutes.py` |
| 5 Chạy S1 v2, kiểm lặp S1 v3 | xong; hai bản trùng từng byte | `K/runtime/analysis-metric-substitutes-s1-v{2,3}/` (gitignored) |
| 6 Báo cáo và bàn giao | xong, trừ commit, push và PR | báo cáo ở trên |

## Kết luận một dòng

Tín hiệu độ trễ về dịch vụ lỗi có trong dữ liệu ở cả 3 case `D` và tới được model. Nó mất ở bước self-state: không span liên quan nào được đánh bất thường. Ở 4/5 run `K`, run đúng mà không có `U2`, `U3`, và dịch vụ lỗi đồng thời là dịch vụ nhiều span nhất. Hướng X hạng 1 là override prompt self-state.

## File mới hoặc đã sửa (chưa commit)

- `plans/261102-0035-rclagent-rq-c-metric-drop-substitutes/` (plan, các phase, `deviation-log.md`) và `plans/261102-0004-rclagent-rq-c-x1-known-service-query/` (đang tạm dừng).
- `plans/reports/`: codebook, scout, research, báo cáo kết quả, bàn giao này.
- `K/analyze-metric-substitutes.py`, `K/test-analyze-metric-substitutes.py`, `K/metric-substitute-prereg.json`, `K/README.md` (thêm một mục).
- Không sửa `upstream/`, analyzer RQ (b) hay codebook RQ (b). Hash `K/evidence-loss-prereg.json` vẫn khớp; test `test_rq_b_receipt_still_matches` kiểm điều này.

## Tái lập và kiểm

Lệnh ở mục 10 của báo cáo. Kiểm hash đóng băng: `summary.json` có bốn cờ `prereg` đều `true`; test `FreezeReceiptTest` kiểm cùng điều đó.

## Việc còn lại

1. Commit, push và mở PR trên nhánh `feat/rclagent-rq-c-metric-drop-substitutes`. Việc này chưa làm vì sếp đã từ chối lệnh tạo nhánh lúc bắt đầu. Hiện mọi thay đổi chưa commit trên `docs/rclagent-s1-v3-check`. Không commit `K/runtime/`.
2. Quyết định của sếp: có lập plan Kaggle cho hướng X hạng 1 không, có gộp X1 không, có thêm nhánh "KPI độ trễ dựng từ trace" không (mục 11 của báo cáo).
3. Còn mở từ trước, ngoài phạm vi plan này: báo cáo kết quả RQ (b) chưa có mục S1 v3, và trạng thái phase 9 của plan RQ (b) vẫn ghi "note".
