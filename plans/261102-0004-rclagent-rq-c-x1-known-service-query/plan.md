---
title: "RQ (c) hướng X1 ở S0: cho RCLAgent truy vấn metric của dịch vụ không có span trong trace"
description: "Thử hướng X hạng 1 của RQ (b) trên Kaggle T4: hai nhánh X1 (gợi ý danh sách dịch vụ đã biết, và harness tự truy vấn mọi dịch vụ đã biết làm cận trên) trên 3 case không có span GT, cộng kiểm hồi quy nhánh chính trên 5 case có span GT; đo R@1 so với S1 v3 (mô tả, không nhân quả tổng quát)."
status: on-hold
priority: P3
effort: 20h
branch: feat/rclagent-rq-c-x1-known-service-query
tags: [rclagent, rq-c, kaggle, experimental]
blockedBy: []
blocks: []
created: 2026-11-02
---

# RQ (c), hướng X1 ở S0

## Tạm dừng (2026-11-02)

Sếp chốt đặt câu (c) chính theo trục thiếu telemetry ([plan RQ (c) chính](../261102-0035-rclagent-rq-c-metric-drop-substitutes/plan.md)); X1 là phát hiện phụ, chưa chạy. Trước khi mở lại, sửa hai điểm:
1. **Nhánh `x1_prompt` như đang viết gần như vô nghĩa.** System prompt của RCLAgent đã có danh sách "Known services" ([codebook](../reports/prereg-261031-2311-rclagent-evidence-loss-codebook.md), dòng 122), và model vẫn không hỏi GT ở cả 3 case. Gợi ý phải là một chỉ dẫn rõ (hỏi cả dịch vụ không có span trong trace), tức một can thiệp prompt, không phải "bổ sung thông tin".
2. **Tính mới của cách sửa thấp.** Quét metric mọi dịch vụ là việc nhiều agent không đi theo trace đã làm; phần có thể mới là chẩn đoán điểm mù S0. Cần tra tài liệu (phase tra cứu của plan RQ (c) chính) trước khi tốn GPU. Khi mở lại, cân nhắc gộp vào cùng gói Kaggle với X của câu (c) chính.

## Overview

RQ (b) đã khép lại ([báo cáo kết quả](../reports/analysis-261101-1023-rclagent-evidence-loss-results.md), mục 13): câu `S0_gt_span_absent` đứng hạng 1 với 3/4 dịch vụ GT. Ở ba case không có span GT (`272a47` recommendationservice, `30e3c7` emailservice, `de6a50` checkoutservice), không run `metric` nào hỏi metric của GT, và R@1 bằng 0 ở cả 9 run `metric` của S1 v2 (`K/runtime/analysis-evidence-loss-s1-v2/runs.csv`, cột `I0`, `I4`, `rank`). Kế hoạch này thử hướng X1: làm cho truy vấn metric chạm tới dịch vụ không có span, mà không sửa `upstream/`.

`K/` là `F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`.

### Quyết định sếp chốt ngày 2026-11-02

1. **Hai nhánh X1.** `x1_prompt` là nhánh chính: `adapt_payload` thêm danh sách 12 dịch vụ đã biết vào request self-state, model tự chọn có hỏi hay không. `x1_query` là cận trên: `get_tool` tự hỏi metric của mọi dịch vụ đã biết tại cùng timestamp mỗi khi model gọi `search_fluctuating_metrics`, rồi gộp các bảng không rỗng vào kết quả trả cho model.
2. **Kiểm hồi quy.** Chạy `x1_prompt` trên 5 case có span GT để xem X1 có làm hỏng case đang đúng không.
3. **Đổi khung RQ (c) cho X1.** Ba case này có R@1 bằng 0 ở cả `metric` lẫn `no_metric`, nên X1 không thu hẹp mức giảm khi bỏ metric như câu (c) gốc ([decision-261028-1104](../reports/decision-261028-1104-rclagent-missing-telemetry-rq.md), mục 1). Câu hỏi của kế hoạch này là: **X1 có khôi phục bằng chứng bị mất ở S0 trong nhánh đủ nguồn (`metric`) không.** Độ lệch so với câu gốc được ghi vào decision record ở phase 2.

### Phát hiện khi lập kế hoạch (đã đọc nguồn)

- Tool metric của nhánh `metric` là `K/metric-repair.py` (K = 100 độ lệch chuẩn, dòng 13 và 36). Codebook ghi bảng chỉ xuất hiện khi hỏi đúng dịch vụ GT ([codebook](../reports/prereg-261031-2311-rclagent-evidence-loss-codebook.md), mục 2.3). Vì vậy `x1_query` gần như đưa thẳng bảng GT cho model: nó đo phần S1 đến S4 khi bằng chứng chắc chắn tới, không phải một can thiệp thực tế. Phase 1 đo lại tính "oracle" này trên CPU trước khi chạy.
- Model tự chọn `service_name` (upstream `tools_gpt.py:67-90`, `coordinator.py:204-292`); server so khớp chuỗi con (`tool_server.py:170`, `metric-repair.py:22`), nên `frontend` cũng khớp `frontend-external`. Danh sách dịch vụ đã biết là `KNOWN_SERVICES["re2ob"]` (upstream `config.py:71-76`, 12 tên), cũng có trong system prompt (`coordinator.py:161-165`). Danh sách này không phụ thuộc nhãn.
- Hook harness: `adapt_payload` (`K/smoke-worker.py:108`), `get_tool` (`K/smoke-worker.py:338`), cờ worker `--metric` (`K/smoke-worker.py:456`), `worker_options` (`K/kaggle-runtime.py:494`), `CONDITIONS` (`K/add-condition-runs.py:16`).
- Analyzer đóng băng (`K/analyze-evidence-loss.py`) đếm mọi `tool_result` metric vào `queried_gt` và `table_received`. Nếu harness ghi truy vấn tự sinh dưới tên `tool_result`, I0 của `x1_query` đúng theo cấu trúc. Phase 3 ghi chúng dưới loại sự kiện riêng.

### Kết quả mong đợi (outcome)

1. Một báo cáo CPU về tính oracle của tool metric đã sửa trên 8 case S1 (bảng nào trả cho dịch vụ nào tại timestamp của span) và kích thước kết quả gộp của `x1_query`.
2. Một bản đăng ký trước (prereg) có hash: nhánh, case, seed, câu kết cục, so sánh, tuyên bố phơi nhiễm; cộng decision record về khung RQ (c).
3. Harness có cờ `--x1 {off,prompt,query}`, có test; `off` cho request giống từng byte với harness S1 v3.
4. Hai gói Kaggle private (A: 3 case × 2 nhánh × 3 seed = 18 run; B: 5 case × `x1_prompt` × 3 seed = 15 run), đã đẩy lên Kaggle.
5. Sau khi sếp báo xong và tải output: kiểm hash, phân tích bằng analyzer đóng băng và một script so sánh mới có test, báo cáo kết quả tiếng Việt, bàn giao, commit và PR.

### Phi mục tiêu (non-goals)

- Không sửa `upstream/`, codebook hay analyzer đóng băng.
- Không thử hướng S2, S4 hay S1/S3; không chạy `no_metric+X1`.
- Không đụng test split RE2-OB (niêm phong, D12). Không chạy replay CPU bằng model lượng tử hóa.
- Không tuyên bố X1 hiệu quả nói chung: n = 3 case cho câu chính, 3 seed gần như nhân bản.
- Không theo dõi Kaggle lâu: đẩy xong thì dừng, sếp báo khi chạy xong.

### Tiêu chí chấp nhận

- Prereg có hash được ghi trước khi đẩy gói lên Kaggle, và hash của nó còn khớp lúc phân tích.
- `--x1 off` giữ nguyên request so với S1 v3 (test so từng byte trên payload mẫu).
- Câu kết cục được tính bằng script có test từ `runs.csv` và điểm tác giả, không tính tay.
- Báo cáo kết quả nêu số k/n theo case, so với S1 v3 cùng case và seed, kèm giới hạn: mô tả, `x1_query` là cận trên có bơm bảng GT, mẫu nhỏ.

## Các giai đoạn

| Phase | Tên | Trạng thái | Phụ thuộc | Ước lượng |
|---|---|---|---|---|
| 1 | [Đo tính oracle của tool metric và kích thước gộp](./phase-01-cpu-oracle-and-size-check.md) | planned | không | 2h |
| 2 | [Đăng ký trước X1 và decision record](./phase-02-x1-prereg-and-decision.md) | planned | 1 | 2h |
| 3 | [Cờ `--x1` trong harness và test](./phase-03-harness-x1-flag-and-tests.md) | planned | 2 | 5h |
| 4 | [Dựng, kiểm và đẩy hai gói Kaggle](./phase-04-build-and-push-kaggle-packages.md) | planned | 3 | 3h |
| 5 | [Kiểm output và phân tích](./phase-05-verify-and-analyze-output.md) | planned | 4, sếp báo xong | 5h |
| 6 | [Báo cáo, bàn giao, commit và PR](./phase-06-report-handoff-and-pr.md) | planned | 5 | 3h |

## Ngân sách Kaggle

S1 v3 gói A chạy 36 trace trong 30 271,7 giây, khoảng 14 phút mỗi trace ([báo cáo S1 v3](../reports/analysis-261101-s1-v3-hashseed-and-evidence-loss-check.md)). Gói A ở đây có 18 run, khoảng 4,2 giờ T4 (nhánh `x1_query` có thể dài hơn vì kết quả tool lớn hơn); gói B có 15 run, khoảng 3,5 giờ. Cả hai nằm trong giới hạn một phiên. Số này là ước lượng từ S1 v3, chưa đo.

## Rủi ro chính

- `x1_query` có thể làm vượt ngữ cảnh 16384 (kết quả metric không có ngân sách; `K/smoke-worker.py:23-28`, guard dừng chứ không cắt ở 192-193). Phase 1 đo kích thước, phase 3 có trần cho phần gộp.
- `x1_prompt` thay prompt của mọi span, nên quỹ đạo tách khỏi S1 v3 ngay từ request đầu; so với S1 v3 là so hai quỹ đạo độc lập, không ghép cặp theo request.
- Analyzer đóng băng có thể không xử lý tên điều kiện mới (`summarise` ghép theo `no_metric`, `metric`, `metric_no_log`). Phase 3 kiểm trên dữ liệu tổng hợp; nếu không chạy được, phase 5 dùng script so sánh mới đọc thẳng `events.jsonl` và `author-score.txt` theo cùng định nghĩa I0, không sửa analyzer.

## Câu hỏi còn mở

1. Câu chữ của gợi ý `x1_prompt` được chốt trong prereg ở phase 2; sếp duyệt câu chữ đó trước khi đẩy gói.
