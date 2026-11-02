# Codebook: tín hiệu thay thế khi bỏ metric (RQ c bước 1)

Trạng thái: **đóng băng cục bộ.** Sếp duyệt ngày 2026-11-02, chọn `either` làm cách quy độ trễ của câu chính. Hash (SHA256 sau khi đổi CRLF thành LF) ghi ở `K/metric-substitute-prereg.json`; commit chỉ chứng minh nội dung, không chứng minh thứ tự. `K/` là `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`. Plan: [261102-0035](../261102-0035-rclagent-rq-c-metric-drop-substitutes/plan.md).

## 1. Tuyên bố phơi nhiễm

Mọi kết cục dưới đây đã được thấy trước khi viết codebook, qua [scout phase 1](scout-261102-rclagent-metric-substitute-signals.md) và lúc kiểm plan. Đóng góp của bước này là **tính lại tất định theo luật cố định** và ghi ra các con số có thể kiểm lại, không phải khám phá mù. Những gì đã thấy:
- R@1, MRR, top1 của mọi run `metric` và `no_metric` của 8 case S1 v2.
- `status_code`, dòng log theo dịch vụ, số span theo dịch vụ của 5 case có output.
- Tỉ lệ `duration / p50` theo mốc train của mọi span trong 5 case, và span đứng đầu mỗi case.
- `is_abnormal` của span GT và span client gọi GT ở 14 run `no_metric` của `D`, `R`, `K`; đọc tay self-state của 7 span.
- Giả thuyết hình dạng trace cho tập `K`.

## 2. Đơn vị và tập

- Đơn vị đếm của câu kết cục: **case** (n = 3 cho `D`). Run chỉ để mô tả.
- Tập `D`: `no_metric` R@1 = 0 và `metric` cùng case, cùng seed R@1 = 1 (theo `R@1` của `K/runtime/analysis-missing-source-{a,b}-s1-v2/runs.csv`). Tập `R`: cả hai R@1 = 0, MRR `metric` lớn hơn MRR `no_metric` ít nhất 0,2. Tập `K`: `no_metric` R@1 = 1. Ba case không có span GT (`272a47`, `30e3c7`, `de6a50`) bị loại khỏi mọi tập.
- Chỉ báo tính trên run `no_metric` của mỗi cặp.

## 3. Định nghĩa

- **Span liên quan GT:** span server (`cmdb_id` khớp GT theo hàm `match` của `K/analyze-evidence-loss.py`) hoặc span client (`cmdb_id` khác GT và `operation_name` chứa lớp dịch vụ của GT, ví dụ `RecommendationService` cho `recommendationservice`).
- **Quy về dịch vụ:** span server quy về chính nó. Span client có hai cách: `callee` (dịch vụ được gọi, suy từ `operation_name`) và `caller` (`cmdb_id` của span). Câu kết cục chính dùng `either` (đúng nếu một trong hai cách trỏ về GT); hai biến thể `callee` và `caller` được báo như độ nhạy.
- **Thời gian tự thân:** `duration` trừ tổng `duration` của span con trực tiếp, chặn dưới ở 0.
- **Mốc train:** p50 và p99 của `duration` theo (`cmdb_id`, `operation_name`) trên trace trong cửa sổ `[inject_ts - 1200 s, inject_ts - 60 s)` của 48 case có `role == train` trong `plans/261026-1713-rclagent-tai-hien-toi-thieu/work/re2ob-case-roles-by-source-key.csv`, đọc từ `F:/Nam/UIT/nt114-paper-artifacts/W7165616276/data/re2ob/trace/all/trace_jaeger-span.csv`. Dòng thuộc cửa sổ val hoặc test bị bỏ trước khi tổng hợp; dòng thuộc nhiều cửa sổ bị bỏ.

## 4. Chỉ báo

| Mã | Đúng khi | Nguồn |
|---|---|---|
| `U0_trace` | Span có thời gian tự thân lớn nhất trong trace quy về GT (theo `either`) | bundle `trace_jaeger-span.csv` |
| `U0_baseline` | Span có `duration / p50` lớn nhất trong trace quy về GT (theo `either`) **và** `duration` vượt p99 | bundle và mốc train |
| `U0` | `U0_trace` hoặc `U0_baseline` | |
| `U0_status`, `U0_logs` | Có span liên quan GT với `status_code` khác 0; có dòng log của GT. **Rỗng theo cấu tạo** ở 5 case (scout phase 1); vẫn tính và báo, không vào chuỗi | bundle |
| `U1` | Mọi span server của GT có request `self_state_verification` (`events.jsonl`, `kind == request`, `span_id` khớp) | zip output |
| `U2` | Ít nhất một span liên quan GT có `agent_complete` của `self_state_verification` với `is_abnormal == true` | zip output |
| `U2_latency` | Như `U2`, và `hypothesis` hoặc `key_symptoms` khớp regex `latenc\|duration\|slow\|delay\|took\|response time` (không phân biệt hoa thường) | zip output |
| `U3` | Cột `I2` hoặc `I3` của `K/runtime/analysis-evidence-loss-s1-v2/runs.csv` đúng; báo riêng từng cột | `runs.csv` RQ (b) |
| `U4` | Cột `rank` bằng 0 | `runs.csv` RQ (b) |
| `U_struct` | GT là dịch vụ có nhiều span nhất khi bỏ `frontendservice` (hòa thì `tie`, tính là sai) | bundle |
| `top1_is_struct_max` | Phần tử đầu của `root_causes` trong `result.json` là dịch vụ có nhiều span nhất (bỏ `frontendservice`) | zip output, bundle |

- **Vị trí mất đầu tiên:** chỉ báo đầu tiên sai theo thứ tự `U0`, `U1`, `U2`, `U3`, `U4`; `preserved` nếu cả năm đúng.
- **`hit_without_substitute`:** `U4` đúng trong khi `U2` và `U3` sai.

## 5. Câu kết cục

- **O1 (chính, `D`, n = 3 case):** số case mà mọi run có vị trí mất đầu tiên ở cùng một chỉ báo, và đó là chỉ báo nào.
- **O2 (`D`):** "không có tín hiệu thay thế trong dữ liệu agent thấy" khi `U0` sai ở mọi case `D`. Ngược lại, báo số case có `U0` đúng.
- **O3 (`K`):** số run có `hit_without_substitute`, và trong đó số run có `U_struct` và `top1_is_struct_max` đúng.
- **O4 (`R`):** mô tả vị trí mất đầu tiên của 3 run `29583d`; không xếp hạng.
- **Độ nhạy:** O1 và O2 tính lại với `callee` và `caller` thay cho `either`; và bỏ `99f095` (case hiệu chỉnh RQ b).

## 6. Luật xếp hạng hướng X

- Hướng X nhắm vào chỉ báo là vị trí mất đầu tiên của nhiều case `D` nhất đứng hạng 1; hòa thì ghi `ngang nhau`.
- Mỗi hướng kèm: có làm được mà không sửa `upstream/` không (wrapper `adapt_payload` hoặc `get_tool` trong `K/smoke-worker.py`), có tiền lệ trong [báo cáo tài liệu](research-261102-rclagent-missing-metric-and-trace-blind-spot.md) không, và điều kiện kiểm cần chạy model.
- Nếu O3 cho thấy run `K` đúng nhờ hình dạng trace, báo cáo phải ghi: một X làm tăng R@1 ở `no_metric` có thể đến từ việc khuếch đại thiên lệch hình dạng trace, nên phép kiểm X phải gồm case mà GT không phải dịch vụ nhiều span nhất (như `7bbfa6`).

## 7. Không làm

- Không ngôn ngữ nhân quả; mọi câu là mô tả trên 3 case.
- Không sửa luật sau khi chạy script; mọi thay đổi ghi `deviation-log.md` trong thư mục plan.
