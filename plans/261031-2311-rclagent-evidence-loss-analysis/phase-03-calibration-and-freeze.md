---
phase: 3
title: "Hiệu chỉnh nhỏ và đóng băng"
status: completed
priority: P1
effort: "3h"
dependencies: [2]
---

# Phase 3: Hiệu chỉnh nhỏ và đóng băng

## Context links
- [Phase 1](./phase-01-codebook-draft-and-exposure.md) (codebook v0) và [Phase 2](./phase-02-analyzer-core-and-synthetic-tests.md) (analyzer).
- [Nghiên cứu phương pháp](../reports/research-261031-2311-evidence-loss-attribution-methods.md), mục 4: vòng hiệu chỉnh, sửa định nghĩa, rồi khóa.
- Quy tắc điều phối agent: `C:/Users/Siinn/.claude/rules/orchestration-protocol.md`.

## Goal
Hiệu chỉnh codebook bằng đọc tay hai run của một case, rồi đóng băng codebook và analyzer bằng hash và bắt đầu nhật ký deviation.

## Requirements
<!-- red-team: calibration contaminates confirmation; cut machinery -->
- Hiệu chỉnh nhỏ: **hai run** (seed 20261026 và 20261027) của điều kiện `metric_no_log` thuộc **một case** do rút tất định. Không còn 6 run, không còn hai coder, không kappa và bootstrap ở phase này (6 run của 2 case chỉ là 2 đơn vị độc lập, kappa vô nghĩa).
- Cách rút (ghi trong codebook trước khi đọc nội dung run): lấy danh sách case sắp xếp theo mã băm, **chỉ gồm case có ít nhất một span GT trong trace và loại `29583d`** (<!-- validation: 29583d scope --> case duy nhất trượt R@1 ở mọi seed trong điều kiện `metric`; ở `metric_no_log` `99f095` cũng 0/0/0 và không bị loại, nên lý do loại yếu hơn ở điều kiện hiệu chỉnh; rút trúng nó biến hiệu chỉnh thành xem trước kết quả quyết định; việc loại này dựa trên hiểu biết đã phơi nhiễm và được ghi vậy). Gọi `random.Random(20261031).choice(danh_sách)` đúng một lần. Danh sách lấy từ `--structure-only` của phase 2.
- Case hiệu chỉnh **không dùng làm xác nhận**: báo cáo ở phase 7 lấy bảng bỏ case hiệu chỉnh làm chính, và bảng có case đó làm độ nhạy. Hai run hiệu chỉnh không vào luật của phase 7 dưới bất kỳ hình thức nào.
- Nhãn của `metric` và `no_metric` chưa được gán trước khi đóng băng. Ghi rõ trong codebook rằng hai điều kiện này đã được thấy ở mức tổng hợp (phase 1, bước 10), nên không tuyên bố mù.
- Người đọc tay không thấy nhãn của analyzer, không thấy báo cáo scout hay phân tích tổng hợp, và <!-- red-team: coder blindness --> **không thấy GT, điều kiện lẫn 10 đầu ra cuối** khi điền C1 đến C4; chỉ khi C1 đến C4 đã nộp mới mở phần đầu ra cuối để điền C5.
- Thay đổi luật trong giai đoạn hiệu chỉnh là "thay đổi hiệu chỉnh" (calibration change), không phải deviation. Deviation chỉ tính từ sau khi đóng băng.

## Files to Create / Modify
- Modify: `F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/test-analyze-evidence-loss.py` (thêm test từ run thật đã kiểm tay)
- Modify: `F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/analyze-evidence-loss.py` (chỉ để sửa theo kết quả hiệu chỉnh)
- Modify: `F:/Nam/UIT/NT114 - NCKH/plans/reports/prereg-261031-2311-rclagent-evidence-loss-codebook.md` (v0 thành v1, bảng thay đổi hiệu chỉnh)
- Modify: `F:/Nam/UIT/NT114 - NCKH/.gitattributes` (nếu chưa có ở phase 2: `plans/reports/prereg-*.md text eol=lf`)
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/evidence-loss-prereg.json` (biên nhận đóng băng)
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/261031-2311-rclagent-evidence-loss-analysis/deviation-log.md`
- Create (gitignored): `K/runtime/analysis-evidence-loss-calibration/` (danh sách run, form đọc tay, nhãn của luật)

Phase này không tạo script mới; công cụ kiểm toán nằm ở phase 6.

## Steps

1. Rút case hiệu chỉnh từ `runtime/analysis-evidence-loss-structure/` theo cách rút ở Requirements. Ghi `calibration-runs.txt` (2 `run_id`) vào thư mục hiệu chỉnh và vào codebook trước khi đọc nội dung run.

2. Chuẩn bị gói đọc tay thủ công (tạo bằng đoạn lệnh ngắn, không đưa vào repo) cho hai run: tóm tắt trace, mọi kết quả metric (cắt tối đa 40 dòng), self-state JSON của các carrier, chuỗi consolidation từ carrier lên root, khối hint từ prompt cuối. Không có GT, điều kiện hay nhãn của analyzer ở phần đầu; phần "10 đầu ra cuối và GT" nằm trong file riêng mở sau.

3. Một người đọc (agent một mình, mù, nhận gói và codebook v0 theo giao thức điều phối, hoặc sếp nếu sếp muốn) điền form: C1 `tool_signal`, C2 `self_state_uses_gt_evidence`, C3 `root_names_gt`, C4 `hint_supported`, rồi mở file cuối và điền C5 `first_loss_stage`. Lời nhắc nêu nhiệm vụ, file được đọc, file được ghi, tiêu chí chấp nhận, ràng buộc (không chạy analyzer, không đọc `analysis-*`), cờ phạm vi và giao thức trạng thái.

4. Chạy analyzer trên hai run (`--runs`, ra `runtime/analysis-evidence-loss-calibration/rules`) **sau khi** form đã nộp. So từng chỉ báo giữa form và luật; mỗi bất đồng đọc lại từ gói và xếp vào lỗi đọc, mơ hồ của codebook, hoặc lỗi luật. Mỗi mơ hồ hoặc lỗi dẫn tới thay đổi hiệu chỉnh ghi vào bảng của codebook (mã `CAL-01`, ...: chỉ trong tài liệu, không đưa vào code hay tên test), kèm sửa analyzer và test. Báo đồng thuận thô theo chỉ báo; không tính kappa.

5. Kiểm tay một run thành test: người đọc ghi giá trị kỳ vọng của I0 đến I5 cho một trong hai run, thêm `RealRunFixtureTest` vào `test-analyze-evidence-loss.py`, đọc zip thật và **thất bại** khi vắng zip trừ khi đặt `EVIDENCE_LOSS_ALLOW_NO_ZIP=1` (cùng cơ chế phase 2). Giá trị kỳ vọng nằm trong test, dữ liệu thì không.

6. Phép kiểm khả thi của luật (phase 1, bước 8, bước A) được tính lại lần cuối từ `--structure-only` và số đã phơi nhiễm; mọi điều kiện `not_testable` được ghi trong codebook v1.

7. Đóng băng:
   - Cập nhật codebook thành v1 (luật xếp hạng, nguồn gốc từng ngưỡng, danh sách dự đoán, bảng kết cục đã biết, bảng thay đổi hiệu chỉnh, danh sách run hiệu chỉnh).
   - <!-- red-team: freeze receipt fragile under CRLF --> Bảo đảm `.gitattributes` có `plans/reports/prereg-*.md text eol=lf` (vì `core.autocrlf=true` và hiện chỉ có `*.py text eol=lf`). Hash codebook tính **sau khi chuẩn hóa CRLF thành LF**, và quy tắc chuẩn hóa ghi trong biên nhận.
   - Ghi vào `K/evidence-loss-prereg.json`: `codebook_version`, đường dẫn codebook, SHA256 codebook (đã chuẩn hóa), SHA256 `analyze-evidence-loss.py` **và SHA256 của từng module analyzer nạp qua `importlib`** (bốn module, <!-- validation: hash four modules --> vì `check-hash-seed-order.py:70` nạp `compare-run-outputs.py`, file đó nạp analyzer cũ `analyze-missing-source-results.py`: `check-hash-seed-order.py`, `compare-run-outputs.py`, `analyze-missing-source-results.py`, `analyze-completion-and-budget-stops.py`), thời điểm cục bộ (Asia/Saigon) và hạt giống.
   - Khởi tạo `deviation-log.md` (cột: mã deviation, ngày, nội dung, lý do, tác động trước và sau, hash codebook mới).
   - Hỏi sếp có muốn commit đóng băng không (câu hỏi mở 7). Không tự commit. Nếu sếp không muốn, biên nhận hash cục bộ là bằng chứng thứ tự và báo cáo ghi "đóng băng cục bộ, không có thứ tự thời gian độc lập"; sếp có thể tự lưu hash ở nơi có dấu thời gian ngoài repo.

## Verification
```
cd "F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle"
runtime/harness-env/Scripts/python.exe -X utf8 test-analyze-evidence-loss.py
sha256sum analyze-evidence-loss.py analyze-missing-source-results.py check-hash-seed-order.py compare-run-outputs.py
tr -d '\r' < "../../reports/prereg-261031-2311-rclagent-evidence-loss-codebook.md" | sha256sum
runtime/harness-env/Scripts/python.exe -X utf8 -c "import json;print(json.load(open('evidence-loss-prereg.json')))"
```
Mọi hash in ra phải trùng giá trị trong `evidence-loss-prereg.json`. Chạy lại analyzer với `--runs` trên hai run hiệu chỉnh phải cho `prereg.codebook_sha_matches`, `analyzer_sha_matches` và `imports_sha_match` cùng `true`.

## Success criteria
- Có đồng thuận thô theo chỉ báo trên hai run, và không bất đồng nào chưa phân loại. Mỗi thay đổi hiệu chỉnh có test hoặc lý do không cần test.
- Biên nhận đóng băng có hash khớp ở cả codebook, analyzer và module nạp.
- Nhãn `metric` và `no_metric` chưa được gán trước thời điểm này.

## Risks
- Hai run của một case chỉ chứng minh luật chạy đúng trên một cấu trúc. Giảm thiểu: phase 6 kiểm toán trên run của các case còn lại; ghi hạn chế.
- Agent đọc cùng họ model với agent viết codebook. Giảm thiểu: gắn nhãn "LLM-coder", sếp phân xử khi cần.
- Đã phơi nhiễm tổng hợp trước khi đóng băng. Giảm thiểu: tuyên bố phơi nhiễm trong codebook; luật chỉ mô tả.

## Rollback
Trước khi đóng băng: đặt lại codebook về v0, xóa `runtime/analysis-evidence-loss-calibration/`. Sau khi đóng băng: không rollback im lặng; mọi thay đổi đi qua `deviation-log.md`.

## Kết quả (2026-11-01)
- Hiệu chỉnh: người đọc mù và luật đồng thuận 22 trên 22 chỉ báo và nhãn cấp run trên hai run `99f095` `metric_no_log` (hai run cùng một case, nên chỉ kiểm luật chạy đúng trên một cấu trúc); hai chênh lệch nhỏ đã phân loại (một lỗi đọc, một mơ hồ của form), không đổi luật. Bảng thay đổi hiệu chỉnh ở mục 13.3 của codebook.
- Đã thêm `RealRunFixtureTest`; khả thi tính lại ở mục 9.1 của codebook (độ tương phản trong case `not_testable` ở mọi giai đoạn; `S2_root_label_lost_hit_kept` có `n = 3` sát ngưỡng).
- Đóng băng cục bộ codebook v1: `K/evidence-loss-prereg.json`, `deviation-log.md` đã khởi tạo. Chưa commit (Q7 còn mở), nên không có thứ tự thời gian độc lập.
