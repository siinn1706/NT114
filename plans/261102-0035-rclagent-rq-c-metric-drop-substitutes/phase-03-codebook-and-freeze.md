---
phase: 3
title: "Codebook ngắn và đóng băng"
status: completed
priority: P1
effort: "2h"
dependencies: [1]
---

# Phase 3: Codebook ngắn và đóng băng

Biên nhận: [codebook đóng băng](../reports/prereg-261102-rclagent-metric-substitute-codebook.md), hash ở `K/metric-substitute-prereg.json`.

## Context
- Báo cáo scout của phase 1.
- Mẫu: [codebook RQ (b)](../reports/prereg-261031-2311-rclagent-evidence-loss-codebook.md) (cách viết chỉ báo, tuyên bố phơi nhiễm, hash CRLF thành LF) và biên nhận `K/evidence-loss-prereg.json`.

## Requirements
- Codebook ngắn (không quá 200 dòng), viết trước khi script chạy trên dữ liệu thật.
- Chỉ báo theo run `no_metric` của từng cặp (định nghĩa cuối cùng chốt theo phase 1; dự thảo):
  - `U0_data`: độ trễ của span GT nổi bật trong cùng trace. Codebook chốt một phép đo (thời gian tự thân của span GT, hoặc tỉ lệ duration span client gọi GT so với span server của GT, chọn theo phase 1) và một ngưỡng cố định. `status_code` và log **không** là nhánh của U0: ở cả 7 case mọi `status_code` bằng 0 và không có dòng log nào của GT, nên codebook ghi hai nguồn này là rỗng theo cấu tạo dữ liệu, kèm số đếm của phase 1.
  - `U0_baseline`: duration span GT so với mốc từ trace bình thường của case train ngoài bundle (luật lọc ở phase 1, mục 4); ngưỡng cố định trong codebook. Chỉ có khi phase 1 dựng được mốc; nếu không, ghi `NA_no_baseline`.
  - `U_struct`: GT là dịch vụ chiếm nhiều span nhất trong trace, không tính `frontendservice` (hòa thì ghi `tie`). Đi kèm cột `top1_is_struct_max`: dịch vụ hạng 0 ở kết quả cuối có trùng dịch vụ chiếm nhiều span nhất không. Chỉ báo này không phải "tín hiệu lỗi"; nó tách các run đúng nhờ hình dạng trace khỏi run đúng nhờ bằng chứng.
  - `U1_delivered`: tín hiệu `U0_data` có trong input của model (span JSON trong prompt self-state, hoặc kết quả `search_logs`).
  - `U2_flagged`: self-state của span GT (hoặc span cha gọi GT) đánh bất thường và lý do nêu độ trễ, lỗi hoặc log.
  - `U3_root`: cột `I2` (nhãn root nêu GT) và `I3` (hint nêu GT) của `K/runtime/analysis-evidence-loss-s1-v2/runs.csv`. Analyzer RQ (b) đã tính hai cột này cho run `no_metric` (giá trị `true`/`false`, không phải NA; ví dụ `7bbfa6` và `ad1c27`), nên đọc thẳng, không tính lại.
  - `U4_rank`: cột `rank` (0-based) của cùng `runs.csv`; R@1 đối chiếu với `author-score.txt` qua cột `R@1` của `K/runtime/analysis-missing-source-{a,b}-s1-v2/runs.csv`.
  - Vị trí mất đầu tiên: chỉ báo đầu tiên sai theo thứ tự U0, U1, U2, U3, U4. Run có R@1 đúng mà U0 đến U3 đều sai được gắn cờ `hit_without_substitute`, và tách theo `U_struct`.
- Câu kết cục cho tập `D` (đơn vị là case, n = 3): số case mà mọi cặp mất ở cùng một chỉ báo; và câu riêng "không có tín hiệu thay thế trong dữ liệu agent thấy" khi `U0_data` sai ở mọi cặp `D`.
- Đối chứng `K`: cùng chỉ báo, để thấy run đúng R@1 khi không có metric đi qua chỉ báo nào; câu kết cục riêng: số run `K` có `hit_without_substitute` và trong đó số run có `U_struct` đúng.
- Tuyên bố phơi nhiễm: các số R@1, MRR trong plan; việc đã thấy `status_code`, log và hình dạng trace của 7 case khi duyệt plan (gồm giả thuyết hình dạng trace của `ad1c27`, `99f095`, `de6a50`); mọi thứ phase 1 đã thấy.

## Files
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/reports/prereg-261102-rclagent-metric-substitute-codebook.md` (LF).
- Create: `K/metric-substitute-prereg.json` (hash codebook; hash script thêm ở phase 4).

## Steps
1. Viết codebook từ dự thảo trên và số liệu phase 1.
2. Sếp đọc và duyệt; ghi ngày duyệt trong codebook.
3. Tính hash, ghi biên nhận.

## Checks
- Hash trong biên nhận khớp hash tính lại.
- Mỗi chỉ báo chỉ ra trường và file nguồn.

## Risk / Rollback
- Sửa sau khi đóng băng phải ghi `deviation-log.md` trong thư mục plan này.
- Rollback: xóa codebook và biên nhận.
