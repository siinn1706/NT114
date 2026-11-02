---
phase: 1
title: "Kiểm kê tín hiệu không phải metric"
status: planned
priority: P1
effort: "3h"
dependencies: []
---

# Phase 1: Kiểm kê tín hiệu không phải metric

## Context
- Bundle: `K/s1-v2/{a,b}/rclagent-kaggle-bundle.zip`, mỗi trace có `input/trace/all/trace_jaeger-span.csv`, `input/log/all/logs.csv`, `input/metric/all/metrics.csv`.
- Output S1 v2: `K/runtime/kaggle-output-{a,b}-s1-v2/rclagent-smoke/rclagent-smoke-results.zip` (`events.jsonl` có `request`, `response`, `tool_result`, `tool_result_budget`, `agent_complete`; `trace-graph.json`; `result.json`).
- Tập cặp `D`, `R`, `K` trong [plan.md](./plan.md).
- Nguồn dữ liệu RE2-OB đầy đủ để tìm mốc độ trễ: `F:/Nam/UIT/nt114-paper-artifacts/W7165616276/data/re2ob` (hằng `FULL`, `K/prepare-bundle.py:28`) và dữ liệu thô theo case ở `.../W7165616276/data/raw/RE2-OB/<dịch vụ>_<lỗi>/<số>` (`raw_dir`, `K/prepare-bundle.py:112-114`). Vai trò train/test của từng case: `F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/work/re2ob-case-roles-by-source-key.csv` (hằng `ROLES`, `K/prepare-bundle.py:29`; cột `case_id`, `role`, `inject_ts`). `select_traces` (`K/prepare-bundle.py:117-131`) là mẫu luật gán trace vào case theo cửa sổ `inject_ts`.
- `data/re2ob` chứa cả case test. Mọi đọc ở đó phải lọc theo file vai trò trước (D12, [decisions.md](../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md) dòng 37).

## Requirements
- Chỉ đọc. Không mở `K/runtime/analysis-evidence-loss-audit/blind-map.json`, không đọc test split.
- Với mỗi case trong `D`, `R`, `K` (7 case), ghi:
  1. Span của GT trong trace: số span, `duration`, vị trí (cha, con), so với span khác cùng trace: thời gian tự thân (duration trừ tổng duration của span con) và tỉ lệ duration của span client gọi GT so với span server của GT. `status_code` và log của GT đã kiểm khi duyệt plan (mọi `status_code` bằng 0, không có dòng log nào của GT ở cả 7 case); chỉ đếm lại để xác nhận, không phân tích thêm.
  2. Hình dạng trace: số span theo dịch vụ; GT có phải dịch vụ chiếm nhiều span nhất ngoài `frontendservice` không; và dịch vụ đứng hạng 0 ở kết quả cuối của run `no_metric` có trùng dịch vụ đó không (đầu vào cho `U_struct`).
  3. Ở run `no_metric` của các seed liên quan: span JSON của span GT có trong prompt self-state không (đã thấy ở `7bbfa6` s26: có `duration`, `status_code`), `search_logs` cho GT trả gì, self-state cuối (`agent_complete`) của span GT đánh `is_abnormal` thế nào và nêu lý do gì.
  4. Mốc độ trễ ngoài bundle: các trace trong `data/re2ob` cùng dịch vụ và `operation_name` với span GT, **chỉ lấy trace có timestamp nằm trong cửa sổ của một case `role == train` và trước `inject_ts` của case đó** (thời gian bình thường). Trace không gán được duy nhất vào một case train thì bỏ. Ghi số trace mốc theo (dịch vụ, operation).
- Ghi rõ đây là khám phá: những gì thấy ở đây sẽ được ghi vào tuyên bố phơi nhiễm của codebook.

## Files
- Create (gitignored, nháp): `K/runtime/analysis-metric-substitutes-inventory/` (CSV theo case).
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/reports/scout-261102-rclagent-metric-substitute-signals.md`.

## Steps
1. Viết một script nháp trong scratchpad (không vào repo) đọc bundle và zip output; in bảng theo case.
2. Đọc tay self-state cuối của span GT ở một run `D` và một run `K` để kiểm script đọc đúng trường.
3. Dựng mốc độ trễ ngoài bundle theo luật ở mục 4 của Requirements: đọc file vai trò trước, chỉ mở dữ liệu của cửa sổ thuộc case train; ghi danh sách case train đã dùng.
4. Viết báo cáo scout: bảng theo case và danh sách tín hiệu thay thế khả dĩ.

## Checks
- Số span và số dòng log in ra khớp đếm độc lập bằng `csv` trên ít nhất một case (ghi lệnh và kết quả).
- Mỗi dòng của báo cáo có đường dẫn file nguồn.
- Mọi trace dùng làm mốc thuộc một case có `role == train` trong file vai trò, kiểm bằng một assert trong script và in số trace bị bỏ.

## Risk / Rollback
- Nếu không tìm được dữ liệu train ngoài bundle, chỉ báo mốc độ trễ ngoài bị bỏ; ghi lý do.
- Rollback: xóa thư mục nháp và báo cáo scout.
