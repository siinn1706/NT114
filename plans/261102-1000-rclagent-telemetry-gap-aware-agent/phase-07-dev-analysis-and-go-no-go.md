---
phase: 7
title: "Phân tích dev và go/no-go"
status: planned
priority: P1
effort: "6h"
dependencies: [6]
---

# Phase 7: Phân tích dev và go/no-go

## Context
- Output dev ở phase 6, baseline ở phase 4, prereg ở phase 3.
- Hướng tiếp theo từng kết cục đã chốt trước trong [phụ lục dự phòng](../reports/prereg-261102-rclagent-telemetry-gap-fallback-addendum.md) (hash trong `K/telemetry-gap-fallback-prereg.json`); bước 4 áp luật R1–R6 của phụ lục.
- Analyzer có thể tái dùng: `K/analyze-missing-source-results.py`, và `K/analyze-evidence-loss.py` (nạp, không sửa).

## Requirements
- Tính câu kết cục bằng script có test, không tính tay.
- Báo theo dịch vụ lỗi và theo nhóm phạm vi trace, có ablation, so với baseline. Báo tỉ lệ `cartservice` lên top1.
- **Đề xuất go/no-go cho đánh giá cuối:**
  - Có mở niêm phong test split RE2-OB không (D12).
  - Có chạy RE2-TT không, kèm ngân sách GPU ước tính.
  - Thêm baseline nào.
- Báo cáo tiếng Việt, bàn giao, commit và PR khi sếp đồng ý.

## Files
- Create: `K/analyze-telemetry-gap-dev.py`, `K/test-analyze-telemetry-gap-dev.py`.
- Create: `plans/reports/analysis-<ngày>-rclagent-telemetry-gap-dev.md`, cùng bàn giao.

## Steps
1. Kiểm hash prereg.
2. Viết analyzer có test, chạy.
3. Viết báo cáo, cho reviewer soi.
4. **Cổng sếp:** quyết go/no-go.

## Checks
- Test thoát 0; hash prereg khớp.
- Mọi số trong báo cáo truy được về output của script.

## Risk / Rollback
- Kết quả không ủng hộ phương pháp: báo đúng như vậy; đề xuất đổi trọng tâm dựa trên chỗ mất bằng chứng đo được.
- Rollback: xóa báo cáo và analyzer.
