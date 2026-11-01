---
phase: 4
title: "Chạy chính thức và đối chiếu bản sao"
status: completed
priority: P1
effort: "2h"
dependencies: [3]
---

# Phase 4: Chạy chính thức và đối chiếu bản sao

## Context links
- [Phase 3](./phase-03-calibration-and-freeze.md): biên nhận đóng băng `K/evidence-loss-prereg.json`.
- Kết quả so vòng 2 với S1 v2: `K/runtime/analysis-missing-source-r2-vs-s1-v2/summary.json`. <!-- red-team: wrong replicate numbers --> Đã đọc: 72 cặp; `passed->passed` 62, `failed->failed` 2, `failed->passed` 8 (8 run chạm trần ở vòng 2, đều hoàn tất ở S1 v2); nhóm `all`: `identical` 50 (gồm 2 cặp `failed->failed`, tức **48** cặp hoàn tất giống hệt), `final_response_only` 14, `strict_prefix` 8. Số cặp có request cuối khác là **14**, không phải 20.
- [Scout dữ liệu](../reports/scout-261031-2311-rclagent-evidence-loss-data.md): các con số cần tái tính ở bước 4.

## Goal
Chạy bộ gán nhãn đã đóng băng trên toàn bộ S1 v2 và vòng 2, tái tính các con số của scout, và báo độ ổn định nhãn giữa hai vòng mà không gộp vòng 2 vào bảng chính.

## Requirements
- Chỉ chạy sau khi `evidence-loss-prereg.json` tồn tại và mọi hash (codebook, analyzer, module nạp) khớp.
- Không gộp vòng 2 vào bảng chính. Mỗi (case, điều kiện, seed) chỉ tính một lần ở bảng chính, lấy từ S1 v2.
- Không ghi đè thư mục `runtime/analysis-*` cũ.
- Mọi chỗ lệch giữa số của scout và số tính lại được liệt kê, không im lặng thay thế.
- <!-- red-team: scope cut --> Không tạo script so nhãn riêng: phép so hai `runs.csv` là một đoạn `join` ngắn đặt trong phụ lục của báo cáo tái tính (kèm lệnh), và kiểm đầu ra mô hình giống hệt đã có `compare-run-outputs.py` cùng `analysis-missing-source-r2-vs-s1-v2/summary.json`.

## Files to Create / Modify
- Create (gitignored): `K/runtime/analysis-evidence-loss-s1-v2/`, `K/runtime/analysis-evidence-loss-r2/`, `K/runtime/analysis-evidence-loss-r2-vs-s1-v2/` (kết quả join)
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/reports/analysis-261101-0431-rclagent-evidence-loss-recompute-vs-scout.md` (bảng lệch với scout)

Không sửa analyzer ở phase này. Lỗi analyzer đi theo quy trình deviation (bước 6).

## Steps

1. Kiểm điều kiện: biên nhận tồn tại, mọi hash khớp, chưa có thư mục `runtime/analysis-evidence-loss-s1-v2`.

2. Chạy chính thức trên S1 v2: `$PY analyze-evidence-loss.py runtime/analysis-evidence-loss-s1-v2 --label s1-v2 A $ZA $MA B $ZB $MB`. Tương tự vòng 2 với `--label r2` ra `runtime/analysis-evidence-loss-r2/`; manifest vòng 2 ở `runtime/bundle-missing-source-a-r2/manifest.json` và `...-b-r2/manifest.json` (đã kiểm bằng `ls` và `load()` chạy được với cả hai manifest).

3. Kiểm bất biến trong `summary.json` của cả hai corpus:
   - <!-- red-team: scored-run denominators --> `scorer_equivalence`: số run so được bằng số run **có chấm điểm** (70 ở S1 v2, 62 ở vòng 2 theo scout; run hỏng không có `scoring/` và `result.json` nên không nằm trong mẫu số, và đây là định nghĩa thống nhất với kế hoạch, không phải "72 run"); R@1 so chính xác, MRR so 4 chữ số thập phân; số lệch bằng 0.
   - `join_checks` và `hint_equivalence` (so với dòng hint trong prompt cuối): khớp 100 phần trăm ở run hoàn tất; mọi ngoại lệ được liệt kê.
   - `integrity_problems` rỗng; nếu không thì kết quả là tạm thời và dừng lại điều tra.
   - Khẳng định tường minh: <!-- validation: budget only for search_logs --> số sự kiện `tool_result_budget` của metric bằng 0 (budget chỉ có cho `search_logs`; văn bản metric đọc từ `tool_result.response`); số span dùng nhánh fallback bằng 0 (hoặc nêu đúng số khác 0).

4. Tái tính các con số của scout và lập bảng lệch. Mỗi hàng: tên số, giá trị của scout, giá trị tính lại, chênh lệch, nguồn trong `runtime/analysis-evidence-loss-s1-v2`. Danh sách tối thiểu: 144 run và 100 phần trăm join; số `tool_result` khớp (scout 10191 = 5281 trace cộng 4910 vòng 2; S1 v2 riêng 5283 = 5281 trace cộng 2 protocol, nên không cần kiểm lại) <!-- validation: 5283 count moot -->; 3888 nút cây; 3642 prompt consolidate; số run hoàn tất 70 và 62; số span GT theo case (13, 10, 1, 2, 10; 0 ở ba case còn lại); chuỗi phễu của `metric` (14 run, tool có bảng GT 14, span GT abnormal 92 trên 98, hint chứa GT 14, root nêu GT 3, R@1 10); `no_metric` (15 run, span abnormal 0 trên 108, R@1 5); `metric_no_log` (15 run, 8 R@1); tỉ lệ self-state abnormal có bảng (324 trên 327) và không có bảng (66 trên 1574); số span D1; 11 trên 11 run trượt mang D1 và 18 trên 18 run đúng không mang; 222 trên 222 kết quả log không rỗng bị cô đọng; 8 lượt `productcatalogservice` NO_ROWS. Thêm các số red team: I2 3 trên 14; `first_loss_linear` S2 11 trên 14; quan hệ nhãn root với top-1 (`same` 8, `diff` 4, `refusal` 11); độ trùng `agent_complete` giữa `metric` và `metric_no_log` (1156 trên 1249); 298146 dòng log đều `severity: unknown`. Mọi số ngoài sai khác chấp nhận (một đơn vị đếm) được gắn nhãn và giải thích.

5. Điều tra 8 lượt `productcatalogservice` NO_ROWS: từ `spans.csv` lấy `metric_query_ts_offset_s`, `empty_reason`, `tool_match_rule_differs`, đối chiếu oracle ở giây span gốc. Kết luận một trong ba: timestamp do model đặt lệch; tên dịch vụ lệch tên metric (luật `str.contains` của tool); hoặc nguyên nhân khác. Nếu là timestamp thì nhãn `S0_empty_result` phản ánh lựa chọn truy vấn của model, không phải nguồn rỗng.

6. So nhãn hai corpus bằng `join` trên khóa (trace_id, condition, seed), đặt lệnh trong phụ lục của báo cáo tái tính. Với 62 cặp cùng hoàn tất (48 giống hệt, 14 lệch ở response cuối) kỳ vọng I0 đến I3 trùng 62 trên 62 vì prompt tới thời điểm đó trùng từng byte; I4 và I5 có thể lệch ở tối đa 14 cặp. <!-- red-team: determinism check not independent --> Ghi rõ đây là **phép kiểm tính tất định**, không phải độ ổn định nhãn độc lập và không phải bằng chứng thứ hai.

7. Xử lý sai khác: cặp lệch ở I0 đến I3 mà kỳ vọng là trùng là lỗi bất biến cần giải thích. Nếu do lỗi luật hoặc analyzer thì dừng, ghi một deviation, chạy lại cả hai phiên bản, báo cả hai. Bảng phase 7 lấy luật đóng băng làm chính và luật sửa làm độ nhạy.

8. Tách 8 run chạm trần của vòng 2 khỏi mọi phép đếm gộp: ghi là dữ liệu bị cắt cụt `H_cap`, chỉ nêu điểm dừng; không đưa vào bảng chính.

## Verification
```
cd "F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle"
runtime/harness-env/Scripts/python.exe -X utf8 test-analyze-evidence-loss.py
runtime/harness-env/Scripts/python.exe -X utf8 -c "import json;d=json.load(open('runtime/analysis-evidence-loss-s1-v2/summary.json',encoding='utf-8'));print(d['prereg'],d['scorer_equivalence'],d.get('integrity_problems'))"
```
Kỳ vọng: `prereg.frozen`, `codebook_sha_matches`, `analyzer_sha_matches`, `imports_sha_match` đều đúng; `scorer_equivalence` không lệch; `integrity_problems` rỗng.

## Success criteria
- `runs.csv` của S1 v2 có một dòng cho mỗi run; run bị cắt cụt mang chỉ báo dương và `NA` đúng quy tắc.
- Bảng lệch với scout hoàn chỉnh, mọi chỗ lệch có lời giải thích.
- Báo độ khớp I0 đến I5 giữa S1 v2 và vòng 2 trên 62 cặp kèm danh sách cặp lệch, gắn nhãn "kiểm tính tất định".

## Risks
- Số tính lại lệch lớn so với scout. Giảm thiểu: bảng lệch minh bạch; kết luận theo số mới.
- Lỗi analyzer chỉ lộ khi chạy toàn bộ. Giảm thiểu: quy trình deviation, báo cả hai phiên bản luật.
- Nhãn lệch giữa hai vòng ở I0 đến I3 cho thấy dữ liệu không tất định như giả định: đó là phát hiện cần báo.

## Rollback
Xóa ba thư mục đầu ra mới trong `runtime/`. Biên nhận đóng băng giữ nguyên.
