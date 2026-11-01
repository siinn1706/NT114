---
phase: 6
title: "Kiểm toán thủ công một lượt"
status: completed
priority: P1
effort: "4h"
dependencies: [4]
---

# Phase 6: Kiểm toán thủ công một lượt

## Context links
- [Phase 3](./phase-03-calibration-and-freeze.md): codebook v1 đã đóng băng, form C1 đến C5.
- [Nghiên cứu phương pháp](../reports/research-261031-2311-evidence-loss-attribution-methods.md), mục 4: hai lớp (luật tất định, kiểm toán người).
- Quy tắc điều phối agent: `C:/Users/Siinn/.claude/rules/orchestration-protocol.md`.

## Goal
Kiểm tra nhãn do luật gán bằng một lượt đọc tay mù trên một mẫu nhỏ run, báo đồng thuận thô theo chỉ báo, phân xử bất đồng và đưa lỗi luật thành deviation có nhật ký.

## Requirements
<!-- red-team: audit machinery cut to one pass; blindness strengthened -->
- Khung lấy mẫu: run hoàn tất của `metric`, `metric_no_log` và `no_metric`, **trừ case hiệu chỉnh**. Mẫu phân tầng theo (điều kiện, `first_loss_linear`) với hạt giống `20261031`: mỗi tầng không rỗng một run, cộng mọi run analyzer đánh dấu `needs_review` (nhiều carrier mâu thuẫn, nhãn dựa nhánh hiếm, thiếu sự kiện), cộng 2 run `no_metric` ngẫu nhiên. Ước tính 10 đến 14 run [UNVERIFIED; biết chính xác sau khi có `runs.csv`]. Chỉ run có I0 đúng cần kiểm S1 đến S4; run S0 chỉ cần kiểm C1.
- Người đọc mặc định: **một agent mù** (một LLM-coder); sếp phân xử. Hai coder chỉ khi sếp chọn ở câu hỏi mở 1. Báo cáo ghi rõ "LLM-coder" và rằng coder cùng họ model với tác giả codebook.
- **Mù với kết cục**: gói cho C1 đến C4 không chứa GT, tên điều kiện, vị trí GT trong đầu ra cuối hay nhãn của analyzer; C5 (`first_loss_stage`) đọc trong một vòng riêng sau khi C1 đến C4 đã nộp, lúc đó mới mở 10 đầu ra cuối và GT. C5 là hàm xác định của C1 đến C4 cộng bảng xếp hạng, nên đồng thuận C5 chỉ đo việc áp luật, không đo tính đúng của luật; báo vậy.
- Sếp phân xử **trước**, rồi mới mở nhãn của luật, để phân xử không bị neo vào nhãn luật. Agent không tự quyết bất đồng.
- Không kappa có ngưỡng, không PABAK, không bootstrap: với 10 đến 14 run thuộc ít case, các giá trị này không mang thông tin. Báo đồng thuận thô theo chỉ báo và theo case, kèm kappa Cohen chỉ như số mô tả (kèm cảnh báo khi một giá trị chiếm hơn 80 phần trăm). Báo riêng tập con quyết định (điều kiện có metric, I0 đúng).

## Files to Create / Modify
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/audit-evidence-loss-labels.py` (hai lệnh con: `packets`, `agreement`; `agreement` chỉ tính đồng thuận thô và kappa mô tả)
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/test-audit-evidence-loss-labels.py`
- Create (gitignored): `K/runtime/analysis-evidence-loss-audit/` (`sample.csv`, gói mù, `blind-key.csv`, form, `agreement/`, `adjudication.tsv`)
- Modify (nếu có lỗi luật): `analyze-evidence-loss.py`, `test-analyze-evidence-loss.py` (chỉ qua deviation)
- Modify: `F:/Nam/UIT/NT114 - NCKH/plans/261031-2311-rclagent-evidence-loss-analysis/deviation-log.md`
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/reports/audit-261031-2311-rclagent-evidence-loss-label-agreement.md` (đặt ngày thực tế khi viết)

## Steps

1. Viết `audit-evidence-loss-labels.py` và test: `packets OUT_DIR PACKAGE ZIP MANIFEST [...] --runs FILE --seed N` tạo gói mù (`packet-<mã mù>.md`, `blind-key.csv`) với phần C1 đến C4 và phần C5 tách thành hai file; `agreement FORM1 [FORM2] RULE_LABELS OUT_DIR` tính đồng thuận thô và kappa mô tả theo chỉ báo và theo case. Test: gói không chứa tên nhãn của analyzer, không chứa GT hay tên điều kiện ở phần C1 đến C4; mã mù ổn định theo seed; đồng thuận thô và kappa khớp giá trị tính tay.
2. Rút mẫu theo Requirements, ghi `sample.csv` (run_id, tầng, lý do chọn).
3. Tạo gói mù và kiểm bằng `grep` không có `S0_` đến `S4_`, `preserved`, `final_residual`, tên điều kiện trong phần C1 đến C4.
4. Gọi người đọc theo giao thức điều phối (nhiệm vụ, file được đọc: gói và codebook v1, file được ghi: form riêng, tiêu chí chấp nhận, ràng buộc: không chạy analyzer, không đọc `analysis-*`, trạng thái). Vòng 1 điền C1 đến C4; vòng 2 điền C5.
5. Sếp phân xử bất đồng giữa người đọc và (sau đó) luật; mỗi bất đồng xếp vào lỗi coder, mơ hồ codebook hoặc lỗi luật, ghi vào `adjudication.tsv`.
6. Mỗi lỗi luật hay mơ hồ sau đóng băng mở một deviation (mã `DEV-01`, ... chỉ trong tài liệu), sửa analyzer và test, chạy lại S1 v2 ra `runtime/analysis-evidence-loss-s1-v2-amended/`, lưu cả hai. Phase 7 trình bày luật đóng băng làm chính và luật sửa làm độ nhạy; nếu kết cục khác nhau giữa hai phiên bản thì kết cục báo cáo là `no_stage_implicated` kèm cả hai.
7. Viết báo cáo kiểm toán ngắn bằng tiếng Việt: thiết kế mẫu, đồng thuận, các nhóm bất đồng và kết cục, deviation, hạn chế (một LLM-coder cùng họ model, mẫu nhỏ, run cùng case tương quan).

## Verification
```
cd "F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle"
runtime/harness-env/Scripts/python.exe -X utf8 test-audit-evidence-loss-labels.py
! grep -q $'\r' audit-evidence-loss-labels.py test-audit-evidence-loss-labels.py && echo LF-ok
grep -rlE "S[0-4]_|preserved|final_residual" runtime/analysis-evidence-loss-audit/packets || echo "packets-blind-ok"
runtime/harness-env/Scripts/python.exe -X utf8 test-analyze-evidence-loss.py
```
Kỳ vọng: test pass, `LF-ok`, `packets-blind-ok`.

## Success criteria
- Mỗi run trong mẫu có form đầy đủ và một dòng phân xử khi bất đồng.
- Báo cáo kiểm toán có đồng thuận thô theo chỉ báo và theo case.
- Mọi thay đổi luật sau đóng băng nằm trong `deviation-log.md` kèm số liệu trước và sau.

## Risks
- Một LLM-coder cùng họ model nên đồng thuận cao giả. Giảm thiểu: gắn nhãn, sếp phân xử, so với luật.
- Mẫu nhỏ. Giảm thiểu: chỉ báo đồng thuận thô, không đặt ngưỡng cứng.
- Sếp không có thời gian phân xử. Giảm thiểu: gom bất đồng thành danh sách ngắn kèm trích dẫn; không tự quyết thay sếp.

## Rollback
Xóa `runtime/analysis-evidence-loss-audit/` và `runtime/analysis-evidence-loss-s1-v2-amended/`. Với deviation đã ghi: giữ nhật ký, đánh dấu "bị hủy", khôi phục analyzer về bản đóng băng bằng hash.
