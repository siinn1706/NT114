---
phase: 7
title: "Phân tích và báo cáo kết cục"
status: completed
priority: P1
effort: "5h"
dependencies: [4, 6]
---

# Phase 7: Phân tích và báo cáo kết cục

## Context links
- [Phase 4](./phase-04-confirmatory-run-and-replication.md), [Phase 6](./phase-06-manual-audit.md): đầu vào số liệu. (Phase 5 đã gộp.)
- Codebook v1 đã đóng băng: `F:/Nam/UIT/NT114 - NCKH/plans/reports/prereg-261031-2311-rclagent-evidence-loss-codebook.md`, gồm luật xếp hạng ứng viên, bảng kết cục đã biết và danh sách dự đoán P1 đến P5.
- Báo cáo mẫu về phong cách: [results-261031-1715](../reports/results-261031-1715-rclagent-s1-v2-budget-sensitivity.md), [results-261029-1448](../reports/results-261029-1448-rclagent-missing-source-round-2.md).

## Goal
Viết báo cáo kết quả trả lời RQ (b) ở mức mô tả: bảng chỉ báo theo giai đoạn và theo case, kết cục theo luật đã đóng băng, và xếp hạng hướng X ứng viên cho RQ (c) kèm điều kiện cần can thiệp có model để kiểm.

## Requirements
- Ngôn ngữ mô tả. Không p-value, không "có ý nghĩa thống kê". <!-- red-team: unit is GT service/case --> Đơn vị là dịch vụ GT (4) và case (8), seed lồng trong case, span lồng trong run. Mọi bảng chính báo "k trên n" kèm số đơn vị, không phần trăm trên run. Mọi số theo run có cột "R@1 của cùng case ở `no_metric`" làm đường cơ sở độ khó.
- Báo cả `metric_no_log` và `no_metric`, cả run đúng (`preserved`, `hit_without_evidence`). Bảng chính **bỏ case hiệu chỉnh**; bảng có case đó là độ nhạy.
- Kết quả trái dự đoán báo nguyên vẹn. Mỗi dự đoán P1 đến P5 một dòng "xác nhận, bác bỏ hoặc không kết luận" kèm số và trạng thái phơi nhiễm.
- <!-- red-team: causal wording --> Từ "bằng chứng ủng hộ" thay bằng "nhất quán với"; mệnh đề cơ chế là "định vị mô tả; cơ chế chưa chứng minh, cần can thiệp có model (RQ c)"; không dùng "used" cho hai điều kiện, và nhắc `metric` với `no_metric` là hai quỹ đạo độc lập, không ghép cặp.
- <!-- red-team: plotter removed --> Không viết bộ vẽ SVG. Dùng bảng Markdown (cột chồng bằng bảng số hoặc thanh ASCII). Nếu sếp muốn hình, dựng một Artifact tĩnh từ `runs.csv` ở cuối, ngoài phạm vi kế hoạch.

## Files to Create / Modify
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/reports/analysis-261101-1023-rclagent-evidence-loss-results.md` (đã viết; thêm `runtime/analysis-evidence-loss-decision/` gồm `outcome-sentences.csv`, `predictions.csv`, `x-direction-ranking.csv`)

Không tạo script nào.

## Steps

1. Dựng các bảng từ `runs.csv`, `cases.csv`, `funnel.csv`, `case-comparison.csv`, `summary.json` của `runtime/analysis-evidence-loss-s1-v2/` (luật đóng băng), cộng `-amended` nếu phase 6 có deviation. Bộ bảng rút gọn:
   - T1: corpus, hoàn tất theo điều kiện, run `H_*` và điểm dừng; bảng độ nhạy "run cắt cụt hỏng ở chỉ báo tệ nhất".
   - T2: S0 cho 8 case: `queried_gt`, `table_received`, `gt_span_in_trace`, `empty_reason`, `tool_match_rule_differs`, `table_key_prefixes`; truy vấn GT tách khỏi truy vấn khác. Ghi nhận tool metric là bản harness đã sửa và gần như oracle GT.
   - T3: phễu theo điều kiện, đếm run và dịch vụ GT qua I0 đến I5 (biên riêng, cột `NA`), cùng tỉ lệ `saturated`.
   - T4: `first_loss_linear` (kèm chú thích thiên lệch thứ tự) và `final_residual` với tách theo I5, gồm run đúng.
   - T5: ma trận case: chỉ báo đạt xa nhất, k trên 3 seed, R@1 cùng case ở `no_metric`, số seed hiệu dụng khi có run cắt cụt.
   - T6: so sánh điều kiện mức case (không ghép cặp), điểm phân kỳ thô và gộp câu chữ, tỉ lệ `agent_complete` giống từng byte giữa `metric` và `metric_no_log` (phép kiểm lặp lại), cảnh báo nhiễu câu chữ.
   - T7: D1, D2 (nêu D1 trùng mọi khai báo `has_error_logs`), `D1_empty_logs`, so sánh trong case; đoạn hint (kích thước danh sách, dịch vụ không phải GT) kèm câu giới hạn "chỉ phần mã".
   - T8: bảng khả thi và độ tương phản gộp phân tầng theo case cho từng giai đoạn, với `not_testable` ghi rõ.
   - T9: đồng thuận kiểm toán (phase 6) và nhật ký deviation.
   - Một đoạn độ nhạy ngắn: `I2_lenient`, `I3_strict`, bỏ lần lượt từng dịch vụ GT, có và không có case hiệu chỉnh, vòng 2 như phép kiểm tất định, luật sửa so luật đóng băng.

2. Áp dụng luật xếp hạng đã đóng băng (sắp theo `k/n` giảm dần rồi `k` giảm dần, luôn hiển thị `n`), ghi số thật: bảng biên, bước khả thi, độ tương phản gộp ở giai đoạn testable, rồi chọn **một** câu kết cục mô tả (`S0_gt_span_absent`, `S0_gt_span_present_not_queried`, `S2_root_label_lost_hit_kept`, `S4_inputs_present_not_rank1`, `label_mismatch_flags`, `no_stage_implicated`; có thể nhiều câu độc lập nếu đều đủ điều kiện). Nêu rõ phần dữ liệu không cho phép kết luận gì. Chạy lại cho luật sửa (nếu có) và báo nếu kết cục đổi.

3. Mục "hướng X ứng viên": xếp hạng, mỗi hướng kèm dữ liệu nhất quán với nó, giới hạn, và điều kiện kiểm. <!-- red-team: define X without editing upstream --> "Không sửa upstream" nghĩa là wrapper phía harness hoặc prompt override nằm ngoài `upstream/`. Hướng khởi điểm từ scout: (i) kiểm chứng hoặc loại khai báo `has_error_logs` không có log chống lưng và sửa cách dán nhãn hint (cần override bên ngoài luật chuỗi của upstream); (ii) đưa tín hiệu metric vào luật consolidation (override prompt consolidate); (iii) đưa danh sách dịch vụ đã biết vào truy vấn metric (S0; hướng wrapper). Ứng viên nào dữ liệu không nhất quán với nó thì ghi "không có dữ liệu nhất quán". Báo cáo nêu thẳng: kế hoạch dừng ở "khuyến nghị ứng viên, hiệu quả chưa đo"; mọi đo hiệu quả cần chạy model (RQ c). Không đề xuất replay CPU bằng model lượng tử hóa.

4. Phần "không làm, cần quyết định của sếp": replay một giai đoạn LLM với input oracle hoặc input `metric` (cần GPU Kaggle cùng model và kernel để so được với corpus), và chạy lại `no_metric` với câu NO_KPI để tách hiệu ứng câu chữ (cần GPU).

5. Viết báo cáo bằng tiếng Việt: tóm tắt (tối đa 8 dòng, trả lời thẳng (b)); thiết kế và định nghĩa rút gọn (link tới codebook đóng băng, hash, tuyên bố phơi nhiễm, bảng kết cục đã biết); T1 đến T9; mục kết cục; hướng X ứng viên; hạn chế (n = 8 case, 4 dịch vụ GT, mẫu hiệu dụng do tính tất định, nhiễu câu chữ, run cắt cụt, một LLM-coder, tool đã sửa gần như oracle, định vị tài liệu "không tìm thấy" chứ không khẳng định "chưa ai làm", trích dẫn chưa xác minh); danh sách deviation; mục tái lập (lệnh, hash, đường dẫn, phiên bản).

6. Mọi con số phải truy được về một file trong `runtime/analysis-evidence-loss-*`; phụ lục "số, file nguồn, cột". Nội dung chưa xác minh gắn [UNVERIFIED].

## Verification
```
cd "F:/Nam/UIT/NT114 - NCKH/plans/reports"
grep -n "TODO\|TBD\|bằng chứng ủng hộ\|evidence_used" analysis-261101-1023-rclagent-evidence-loss-results.md
grep -n "\[UNVERIFIED" analysis-261101-1023-rclagent-evidence-loss-results.md | head
```
Kỳ vọng: không `TODO`, `TBD`, cụm bị cấm; mọi `[UNVERIFIED]` còn lại là cố ý.

## Success criteria
- Báo cáo trả lời (b) bằng câu đúng với luật đóng băng, kể cả `no_stage_implicated`, và nói rõ phần nào là mô tả có phơi nhiễm.
- Mỗi dự đoán P1 đến P5 có kết cục. Mỗi điều kiện của luật có số đơn vị đóng góp hoặc `not_testable`.
- Hướng X là danh sách xếp hạng kèm điều kiện kiểm, không tuyên bố đích.

## Risks
- Kết quả rơi giữa các ngưỡng. Giảm thiểu: luật mô tả, không hạ ngưỡng sau khi thấy số.
- Cám dỗ diễn giải nhân quả. Giảm thiểu: câu mẫu "nhãn là mô tả theo trace, không phải nhân quả" ở đầu mục kết quả và kết cục.
- Báo cáo dài. Giảm thiểu: tóm tắt đầu, chi tiết xuống phụ lục.

## Rollback
Xóa báo cáo. Số liệu trong `runtime/` giữ nguyên.
