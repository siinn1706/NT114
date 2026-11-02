---
title: "RQ (c) bước 1: khi bỏ metric, RCLAgent còn tín hiệu thay thế nào về GT và mất nó ở đâu"
description: "Phân tích CPU trên S1 v2 các cặp case-seed mà R@1 rơi khi bỏ metric: tín hiệu không phải metric nào về GT có trong dữ liệu, có tới model không, bị mất ở giai đoạn nào; từ đó xếp hạng hướng X để thu hẹp mức giảm (mô tả, không nhân quả)."
status: in-progress
priority: P1
effort: 18h
branch: feat/rclagent-rq-c-metric-drop-substitutes
tags: [rclagent, rq-c, analysis, research, cpu-only]
blockedBy: []
blocks: []
created: 2026-11-02
---

# RQ (c) bước 1: tín hiệu thay thế khi bỏ metric

## Overview

Câu (c) gốc ([decision-261028-1104](../reports/decision-261028-1104-rclagent-missing-telemetry-rq.md), mục 1): một thay đổi X có thu hẹp mức giảm khi thiếu telemetry không. Ở S1 v2, bỏ metric làm R@1 gộp A+B giảm 0,208 ([kết quả S1 v2](../reports/results-261031-1715-rclagent-s1-v2-budget-sensitivity.md), mục 3.3); bỏ log không làm giảm R@1. Kế hoạch này là bước 1 của (c): trước khi chọn X, tìm xem ở các cặp bị rơi, agent còn tín hiệu nào khác về GT và tín hiệu đó mất ở đâu. Chỉ dùng CPU và dữ liệu đã có. Việc chạy X trên Kaggle là một plan sau, chỉ lập khi bước này cho ra ứng viên.

Hướng X1 ở S0 (điểm mù dịch vụ không có span) đã [tạm dừng](../261102-0004-rclagent-rq-c-x1-known-service-query/plan.md) như phát hiện phụ.

`K/` là `F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`.

### Các tập cặp (đọc lần này từ `K/runtime/analysis-missing-source-{a,b}-s1-v2/runs.csv`, cột `R@1`, `MRR`)

| Tập | Định nghĩa | Cặp (case, seed) | Vai trò |
|---|---|---|---|
| `D` | `metric` R@1 = 1, `no_metric` R@1 = 0 | `5f7a77` (checkoutservice_mem_1) s26, s27; `7bbfa6` (recommendationservice_socket_1) s26, s27, s28; `99f095` (currencyservice_loss_3) s28 | Câu hỏi chính: 6 cặp, 3 case, 3 dịch vụ GT |
| `R` | Cả hai trượt R@1 nhưng MRR rơi, trừ ba case bị loại bên dưới | `29583d` (emailservice_delay_1) s26, s27, s28 (MRR 0,5 xuống 0,11 đến 0,14) | Phụ: rơi hạng, không rơi R@1 |
| `K` | `no_metric` vẫn đúng R@1 | `5f7a77` s28; `99f095` s27; `ad1c27` (currencyservice_disk_3) s26, s27, s28 | Đối chứng: không có metric mà vẫn đúng thì dựa vào gì |
| loại | Không có span GT trong trace | `272a47`, `30e3c7`, `de6a50` (kể cả `de6a50` s27, MRR 0,25 xuống 0) | Thuộc điểm mù S0, ngoài phạm vi |

`99f095` là case hiệu chỉnh của RQ (b); ở đây được dùng nhưng báo riêng.

### Phát hiện khi lập kế hoạch (đã đọc nguồn lần này)

- Ở `no_metric`, model chỉ còn hai nguồn: span JSON trong prompt self-state (trường `duration`, `status_code`, `operation_name`, `parent_span`; ví dụ `trace-graph.json` của `7bbfa6` `no_metric` s26) và tool `search_logs`.
- Ở cả 7 case của `D`, `R`, `K`, bundle chỉ có **một trace**, mọi `status_code` bằng `0`, và `logs.csv` chỉ có `cartservice`, `frontend` (và `redis` ở ba case), không có dòng nào của GT (`K/s1-v2/{a,b}/rclagent-kaggle-bundle.zip`, `traces/<trace>/input/`; đếm lại khi kiểm plan ngày 2026-11-02). RQ (b) cũng ghi log không chứa bằng chứng nào về GT (mọi dòng `severity: unknown`). Vậy trong những gì agent thấy, tín hiệu thay thế khả dĩ duy nhất là **độ trễ của span GT so với span khác trong cùng trace**; không có mốc độ trễ từ trace khác. Nếu độ trễ cũng không tách được GT, kết luận là: khi bỏ metric, RCLAgent không còn đường lui trong dữ liệu nó được thấy, và X phải thêm một nguồn mới (ví dụ KPI độ trễ dựng từ trace), không chỉ sửa cách dùng nguồn cũ.
- Ba run `ad1c27` ở `no_metric` đúng R@1 dù `I2`, `I3` sai và danh sách hint rỗng (`K/runtime/analysis-evidence-loss-s1-v2/runs.csv`). Trace của `ad1c27`, `99f095` và `de6a50` có cùng hình dạng (14 span `frontendservice`, 10 `currencyservice`, 1 `productcatalogservice`), nên một giả thuyết là agent chọn dịch vụ chiếm nhiều span nhất ngoài frontend. Plan đo điều này bằng chỉ báo `U_struct` (phase 3); đây là khám phá từ lúc kiểm plan, không phải xác nhận.

### Kết quả mong đợi (outcome)

1. Bảng kiểm kê tín hiệu không phải metric về GT cho từng case trong `D`, `R`, `K`: có trong dữ liệu bundle không, có trong dữ liệu RE2-OB train ngoài bundle không (mốc độ trễ), có tới input của model không.
2. Báo cáo tra tài liệu ngắn: RCLAgent gốc và bài nối tiếp ([arXiv 2601.02732](https://arxiv.org/pdf/2601.02732)) có xử lý thiếu metric hay dùng độ trễ trace làm tín hiệu thay thế không; điểm mù S0 đã có ai báo chưa.
3. Một codebook ngắn đóng băng (có hash) cho chỉ báo U0 đến U4 và câu kết cục, kèm tuyên bố phơi nhiễm.
4. Script phân tích có test, chạy trên S1 v2 và kiểm lặp trên S1 v3.
5. Báo cáo tiếng Việt trả lời: khi bỏ metric, tín hiệu thay thế về GT có tồn tại không, tới đâu thì mất; kèm xếp hạng hướng X để thu hẹp mức giảm và điều kiện kiểm (cần chạy model).

### Phi mục tiêu (non-goals)

- Không chạy Kaggle, không chạy model, không replay CPU bằng model lượng tử hóa.
- Không sửa `upstream/`, codebook hay analyzer đóng băng của RQ (b).
- Không đụng test split RE2-OB (niêm phong, D12). Mốc độ trễ, nếu dùng, chỉ lấy từ dữ liệu train.
- Không tuyên bố nhân quả: n = 3 case cho tập `D`, seed gần như nhân bản.

### Tiêu chí chấp nhận

- Mỗi cặp trong `D`, `R`, `K` có một dòng chỉ báo U0 đến U4 tính bằng script, không gán tay.
- Codebook có hash trước khi chạy script trên dữ liệu thật; hash còn khớp lúc viết báo cáo.
- Kết quả trên S1 v3 trùng S1 v2 ở mọi cột chỉ báo, hoặc mọi chỗ lệch được liệt kê.
- Báo cáo nêu rõ khi nào kết luận là "không có tín hiệu thay thế trong dữ liệu agent thấy".

## Các giai đoạn

| Phase | Tên | Trạng thái | Phụ thuộc | Ước lượng |
|---|---|---|---|---|
| 1 | [Kiểm kê tín hiệu không phải metric](./phase-01-signal-inventory.md) | completed, biên nhận [scout](../reports/scout-261102-rclagent-metric-substitute-signals.md) | không | 3h |
| 2 | [Tra tài liệu](./phase-02-literature-check.md) | completed, biên nhận [research](../reports/research-261102-rclagent-missing-metric-and-trace-blind-spot.md) (đọc qua tóm tắt công cụ, trích dẫn chưa đối chiếu nguyên văn) | không | 3h |
| 3 | [Codebook ngắn và đóng băng](./phase-03-codebook-and-freeze.md) | completed, biên nhận [codebook](../reports/prereg-261102-rclagent-metric-substitute-codebook.md) và `K/metric-substitute-prereg.json` (sếp duyệt 2026-11-02, chọn `either`) | 1 | 2h |
| 4 | [Script phân tích và test](./phase-04-analyzer-and-tests.md) | completed, biên nhận [kết quả mục 10](../reports/analysis-261102-rclagent-metric-drop-substitutes-results.md) (30 test thoát 0; hash ở `K/metric-substitute-prereg.json`) | 3 | 5h |
| 5 | [Chạy trên S1 v2, kiểm lặp S1 v3](./phase-05-run-and-replicate.md) | completed, biên nhận [kết quả mục 6](../reports/analysis-261102-rclagent-metric-drop-substitutes-results.md) (hai bản trùng từng byte) | 4 | 1h |
| 6 | [Báo cáo, xếp hạng X, bàn giao và PR](./phase-06-report-x-ranking-and-pr.md) | waiting-human: [báo cáo](../reports/analysis-261102-rclagent-metric-drop-substitutes-results.md) và [bàn giao](../reports/handoff-261102-rclagent-rq-c-step-1.md) xong; commit, push, PR chờ sếp | 2, 5 | 4h |

Phase 1 và 2 độc lập, làm song song được.

## Rủi ro chính

- Tập `D` chỉ có 3 case. Một case có tín hiệu thay thế khác thường đủ làm lệch kết luận; báo theo case, không gộp tỉ lệ.
- Phơi nhiễm: các số R@1, MRR ở bảng trên đã thấy khi lập kế hoạch; phase 1 còn thấy dữ liệu thô. Codebook ghi phơi nhiễm, và các kết luận sinh ra từ phase 1 gắn nhãn "khám phá".
- Mốc độ trễ ngoài bundle có thể không có hoặc lẫn với test split. Nếu không tách chắc chắn được dữ liệu train, bỏ chỉ báo mốc ngoài và ghi lại.

## Câu hỏi còn mở

1. Nếu phase 1 cho thấy không có tín hiệu thay thế nào trong dữ liệu agent thấy, sếp có muốn thêm hướng X "nguồn mới dựng từ trace" (KPI độ trễ) vào xếp hạng dù nó vượt khỏi "chỉ sửa cách dùng nguồn cũ" không? Mặc định: có, ghi riêng là hướng thêm nguồn.
