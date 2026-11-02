---
phase: 3
title: "Đặc tả phương pháp và prereg"
status: completed
priority: P1
effort: "6h"
dependencies: [1, 2]
---

# Phase 3: Đặc tả phương pháp và prereg

## Context
- Đầu vào:
  - Ma trận tính mới của phase 1.
  - Bảng phạm vi trace của phase 2.
  - [Kết quả RQ (c) bước 1](../reports/analysis-261102-rclagent-metric-drop-substitutes-results.md): self-state bỏ qua độ trễ; tín hiệu nằm ở bên gọi hay bên được gọi tùy case; có rủi ro `cartservice`.
- Hook có sẵn: `adapt_payload` (`K/smoke-worker.py:108`), `get_tool` (`K/smoke-worker.py:338`), các cờ điều kiện trong `K/kaggle-runtime.py` và `K/add-condition-runs.py`.

## Requirements
- **Đặc tả M1, M2, M3.**
  - M1: input, chỉ dẫn prompt, và cách báo nguồn vắng.
  - M2: công thức KPI (độ trễ tự thân, tỉ lệ so với p50 train, cả bên gọi lẫn bên được gọi), định dạng bảng trả về, trần số dòng.
  - M3:
    - Điều kiện kích hoạt.
    - Cách lấy trace trong cửa sổ, chỉ dùng dữ liệu tới thời điểm truy vấn: không nhìn trước, không dùng nhãn.
    - Tóm tắt theo dịch vụ.
    - Trần số trace và số token.
- **Tập dev phân tầng** từ train: đủ 5 dịch vụ lỗi, có cả truy vấn có và không có span GT. Ghi luật chọn trước khi chọn.
- **Lưới điều kiện:**
  - Tối thiểu: RCLAgent gốc và phương pháp đầy đủ, mỗi bên chạy ở hai chế độ, đủ nguồn và `no_metric`.
  - Thêm các ablation bỏ từng thành phần, tùy ngân sách.
  - Tổng GPU dự kiến không quá khoảng 34 giờ.
- **Giả thuyết và câu kết cục**, mỗi câu tính bằng script.
- **Chỉ số chính:** R@1 và MRR, báo theo dịch vụ lỗi và theo nhóm phạm vi trace.
- **Chỉ số phụ:** tỉ lệ `cartservice` bị đẩy lên top1; số token mỗi truy vấn.
- **Baseline:** RCLAgent gốc; TraceRCA, MicroRank và BARO (từ phase 4); bộ xếp hạng chỉ theo độ trễ; tùy chọn harness ReAct đơn giản.
- Tuyên bố phơi nhiễm, và nhận rõ đây là dev trên train, không phải kết luận cuối.

## Files
- Create: `plans/reports/prereg-261102-rclagent-telemetry-gap-method.md`, `K/telemetry-gap-prereg.json` (hash).

## Steps
1. Viết đặc tả và prereg.
2. Cho một reviewer độc lập soi prereg (nckh-review).
3. **Cổng sếp:** sếp duyệt prereg. Chỉ khi đó mới đóng băng hash.

## Checks
- Prereg có đủ: luật chọn tập dev, lưới điều kiện, ngân sách GPU, câu kết cục, tuyên bố phơi nhiễm.
- Hash được ghi trong `K/telemetry-gap-prereg.json`.

## Risk / Rollback
- Ngân sách vượt quota: cắt ablation trước, giữ cặp gốc và phương pháp đầy đủ.
- Rollback: xóa prereg chưa đóng băng.
