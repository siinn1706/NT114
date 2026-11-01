---
title: "Đo nơi mất bằng chứng theo giai đoạn của RCLAgent khi thiếu telemetry (RQ b)"
description: "Đo tất định từng lượt chạy S1 v2 bằng vector chỉ báo I0 đến I5 theo giai đoạn của chuỗi bằng chứng, kiểm toán thủ công một lượt, rồi xếp hạng hướng X ứng viên cho RQ (c) hoặc kết luận không giai đoạn nào được chỉ ra (mô tả, không nhân quả)."
status: completed
priority: P1
effort: 32h
branch: feat/rclagent-evidence-loss-analysis
tags: [rclagent, analysis, research, experimental]
blockedBy: []
blocks: []
created: 2026-10-31
---

# Đo nơi mất bằng chứng theo giai đoạn (RQ b)

## Overview

Câu hỏi (b) do sếp chốt ngày 2026-10-28 trong [decision-261028-1104](../reports/decision-261028-1104-rclagent-missing-telemetry-rq.md): khi thiếu một nguồn telemetry, bằng chứng mất ở giai đoạn nào của RCLAgent. Kế hoạch này chỉ dùng CPU và dữ liệu đã có. Nó không chạy Kaggle, không chạy GPU, không đụng test split của RE2-OB (D12).

Nguồn đầu vào là ba báo cáo nghiên cứu cùng ngày: [scout dữ liệu](../reports/scout-261031-2311-rclagent-evidence-loss-data.md), [scout code](../reports/scout-261031-2311-rclagent-evidence-loss-code.md) và [nghiên cứu phương pháp](../reports/research-261031-2311-evidence-loss-attribution-methods.md). Mọi con số trích từ scout trong kế hoạch này mang nhãn [UNVERIFIED] cho tới khi analyzer ở phase 4 tính lại chúng.

Các đường dẫn tương đối trong các phase tính từ `F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`, gọi tắt là `K/`.

### Kết quả mong đợi (outcome)

1. Một codebook đóng băng (có hash) định nghĩa từng chỉ báo giai đoạn bằng luật tất định trên `events.jsonl`, kèm luật xếp hạng ứng viên cho X có phép kiểm khả thi và bảng "kết cục đã biết trước".
2. Một analyzer có test (gồm cổng kiểm trên dữ liệu thật), tạo bảng theo span, bảng theo run (vector I0 đến I5), bảng theo case, bảng so sánh điều kiện mức case, và `summary.json`.
3. Một lượt kiểm toán thủ công mù có đồng thuận thô được báo cáo, cùng nhật ký deviation cho mọi thay đổi luật sau khi đóng băng.
4. Một báo cáo kết quả bằng tiếng Việt trả lời (b) ở mức mô tả trên 8 case (4 dịch vụ GT), kèm xếp hạng hướng X ứng viên và điều kiện kiểm, hoặc kết luận `no_stage_implicated`.

### Phi mục tiêu (non-goals)

- Không chạy lại model, không thử X, không đo hiệu quả của X (đó là RQ c).
- Không tuyên bố nhân quả cho hành vi của LLM. Chỉ phần mã tất định của tác giả (cách dựng hint) mới có thể replay trên CPU.
- Không dùng LLM-judge làm nhãn chính. Không tính p-value suy diễn.
- Không sửa mã nguồn upstream. Không commit khi chưa có yêu cầu của sếp.

## Quyết định thiết kế đã rút ra khi lập kế hoạch

1. **Đường đi của bằng chứng không tuyến tính.** Request tổng hợp cuối nhận ba đường độc lập: báo cáo consolidation của root, toàn bộ Global Evidence Graph (self-evidence nguyên văn của mọi span) và hint dựng bằng so khớp chuỗi (`coordinator.py` 465 đến 503). Vì vậy một span abnormal đã vào GEG thì bằng chứng luôn tới được bước cuối dù consolidation làm rơi nó. Kế hoạch vì vậy lấy **vector chỉ báo biên I0 đến I5** làm nhãn chính, `first_loss_linear` (đúng cách phát biểu RQ b, nhưng thiên lệch thứ tự: S2 luôn đứng trước S3) làm góc nhìn phụ, và `final_residual` (phần dư của R@1 không giải thích bởi I0 đến I3, tách tiếp bằng I5 theo tổng hợp cuối có theo root không) thay cho `effective_loss`. Không làm vậy thì S2 bị gán tội quá mức và S4 chỉ là phần dư. <!-- red-team: first-loss bias -->
2. **Các corpus không phải mẫu độc lập.** Model xác định theo (prompt, seed). Theo [kết quả so vòng 2 với S1 v2](../261026-1713-rclagent-tai-hien-toi-thieu/kaggle/runtime/analysis-missing-source-r2-vs-s1-v2/summary.json), 64 cặp không chạm trần gồm 62 cặp cùng hoàn tất và 2 cặp cùng hỏng; 50 cặp có đầu ra model trùng, 14 cặp chỉ lệch ở response cuối do thứ tự hint. Vì thế vòng 2 và S1 v3 chỉ là phép kiểm tính tất định, không thêm bằng chứng độc lập (cặp hoàn tất: 48 giống hệt, 14 lệch ở response cuối). Mẫu hiệu dụng là 8 case, mỗi case 3 seed, và chỉ **4 dịch vụ GT** (mỗi dịch vụ xuất hiện hai lần với loại lỗi khác nhau); đơn vị đếm của luật là dịch vụ GT. <!-- red-team: cases not independent -->
3. **Các điều kiện rẽ nhánh sớm** <!-- validation: request index basis --> (request thứ 3 đến 7 theo `first_request_divergence` 1-based của `compare-run-outputs.py`, đo lại trên 24 cặp S1 v2; không cặp nào rẽ ở request 1 hay 2), nên so sánh giữa điều kiện là so hai quỹ đạo lấy mẫu độc lập, không ghép cặp. `metric` và `metric_no_log` giống từng byte ở 92,5 phần trăm `agent_complete` nên `metric_no_log` là phép kiểm lặp lại, không phải xác nhận độc lập và không phải tập hiệu chỉnh tách rời. Kế hoạch dùng `metric` làm nhánh chính; hiệu chỉnh chỉ hai run của một case `metric_no_log`, và case đó bị loại khỏi bảng chính. <!-- red-team: calibration contamination -->
4. **Scout và red team đã thấy số tổng hợp**, gồm phễu `metric` và `metric_no_log` mức I0 đến I4. Kế hoạch không tuyên bố mù. Codebook có mục "tuyên bố phơi nhiễm" liệt kê những số đã thấy, và các giả thuyết sinh ra từ scout (ví dụ tuyên bố `has_error_logs` bịa) được gắn nhãn "khám phá có gốc từ scout", không phải xác nhận.
5. **Nhiễu câu chữ giữa hai điều kiện.** `no_metric` trả "No matching records found.", còn `metric` trả "No fluctuating metrics found." khi không có KPI. Phép ghép cặp `metric` với `no_metric` vì vậy lẫn hiệu ứng câu chữ. Tách được hiệu ứng này cần chạy GPU, nên đó là quyết định tiếp theo của sếp, không nằm trong kế hoạch.

## Bảng nhãn giai đoạn (tóm tắt, định nghĩa đầy đủ ở phase 1)

| Nhãn | Ý nghĩa | Quy tắc ngắn gọn |
|---|---|---|
| `H_cap`, `H_context`, `H_parse`, `H_other` | Run dừng do harness | Lý do trong `worker-status.json` hoặc `progress.json` |
| (chú thích) `gt_span_in_trace` | Trace có span của GT hay không | Đếm span có cmdb_id khớp GT theo scorer; **không còn là nhãn loại trừ**, vì mô hình hỏi được metric của mọi dịch vụ đã biết (de6a50 `metric_no_log` nhận bảng GT 3/3 dù 0 span GT) |
| `S0_not_queried` (tách `S0_gt_span_absent` và `S0_gt_span_present_not_queried`) | Không tool metric nào hỏi GT (I0 sai) | Không `tool_result` metric nào có service_name khớp GT; tách theo `gt_span_in_trace` bằng 0 hay từ 1 trở lên |
| `S0_empty_result` | Có hỏi GT nhưng tool không trả bảng | Mọi kết quả metric cho GT đều không bắt đầu bằng `key,`; kèm lý do `absent_source`, `no_kpi` hoặc `no_rows` |
| `S1_not_flagged` | Mọi span nhận bảng GT đều tự đánh `is_abnormal=false` | Đọc `agent_complete` self-state; ghi riêng trường hợp rơi vào nhánh fallback |
| `S2` (`first_loss_linear`) | `local_root_cause` ở root không nêu GT (I2 sai) | So khớp theo scorer; ghi vị trí đứt trên đường từ span mang bảng lên root |
| `S3` (`first_loss_linear`) | GT không có trong cả hai danh sách hint (I3 sai) | Dựng lại hint bằng đúng luật chuỗi của tác giả, đối chiếu với prompt cuối |
| `S4` (`first_loss_linear`) và `reaches_final_input_not_rank1` (`final_residual`) | Bằng chứng có ở đầu vào cuối nhưng GT không đứng hạng 1 | Hạng 0-based theo `_label_hit`; chỉ là phần dư, tách tiếp bằng I5 thành `top1_equals_wrong_root_label`, `top1_differs_from_root_label`, `root_refusal` |
| `preserved` | Mọi chỉ báo đạt và GT đứng hạng 1 | |

Hai nhãn bổ sung không phải "mất": cờ méo (`D1` tuyên bố `has_error_logs` không có log chống lưng, `D2` hint dán nhãn "metric anomalies only" cho span chỉ trễ) và cờ `hit_without_evidence` cho run đúng R@1 mà bằng chứng không bao giờ tới.

## Vai trò các corpus

| Corpus | Vai trò | Cách xử lý |
|---|---|---|
| S1 v2 (A và B, 72 run, 70 hoàn tất theo scout) | Chính | Mọi bảng chính tính trên corpus này |
| Vòng 2 (72 run, 62 hoàn tất theo scout) | Bản sao, phép kiểm tính tất định | Không gộp vào bảng chính; chỉ báo độ khớp I0 đến I5 trên 62 cặp cùng hoàn tất (kiểm tất định, không độc lập) và xem 8 run chạm trần như dữ liệu bị cắt cụt |
| S1 v3 (hash seed cố định) | Tùy chọn, chỉ khi đã có output | Ghi chú trong bàn giao (phase 9): chạy bộ gán nhãn đã đóng băng, I0 đến I3 trùng là giả thuyết đo được; không dùng để chỉnh luật |
| Test split RE2-OB | Bị niêm phong (D12) | Không đọc, không dùng |

## Phases

| # | Phase | Status | Effort | Phụ thuộc | Quyết định chặn (mặc định nếu sếp chưa trả lời) |
|---|---|---|---|---|---|
| 1 | [Codebook nháp, tuyên bố phơi nhiễm, bảng kết cục đã biết](./phase-01-codebook-draft-and-exposure.md) | Completed | 4h | không | không |
| 2 | [Analyzer lõi, test tổng hợp và cổng dữ liệu thật](./phase-02-analyzer-core-and-synthetic-tests.md) | Completed | 12h | 1 | Q8: fixture chỉ ở `runtime/`, cổng thất bại khi thiếu zip trừ khi `EVIDENCE_LOSS_ALLOW_NO_ZIP=1` |
| 3 | [Hiệu chỉnh nhỏ (2 run) và đóng băng](./phase-03-calibration-and-freeze.md) | Completed | 3h | 2 | Q5 (nguồn ngưỡng): giữ luật mô tả; Q7 (commit đóng băng): mặc định chỉ hash cục bộ, ghi "không có thứ tự độc lập" |
| 4 | [Chạy chính thức và đối chiếu bản sao](./phase-04-confirmatory-run-and-replication.md) | Completed | 2h | 3 | không |
| 5 | [Replay hint (đã gộp vào phase 2 và 4)](./phase-05-hint-code-replay.md) | Cancelled-merged | 0h | 4 | không |
| 6 | [Kiểm toán thủ công một lượt](./phase-06-manual-audit.md) | Completed | 4h | 4 | Q1: mặc định một agent mù, sếp phân xử (cần trước phase 6, không phải phase 3) |
| 7 | [Phân tích và báo cáo kết cục](./phase-07-analysis-and-decision.md) | Completed | 5h | 4, 6 | không |
| 8 | [Tài liệu, bàn giao và chính sách commit](./phase-08-docs-handoff-and-commit-policy.md) | Completed | 2h | 7 | không |
| 9 | [Ghi chú S1 v3 (mục trong bàn giao)](./phase-09-optional-s1-v3-confirmation.md) | Note | 0.5h | 4, khi S1 v3 đã có output | không |

Tổng 32h cho các phase bắt buộc (khoảng 4 ngày làm việc, chưa tính thời gian chờ sếp trả lời Q7), cộng 0,5h cho ghi chú S1 v3. Phase 2 là điểm tắc chính của đường găng. Phase 6 chạy được ngay sau phase 4 nên không còn song song với phase 5. Phase 8 sửa tài liệu không chờ GPU hay S1 v3.

## Tiêu chí chấp nhận cả kế hoạch

- Codebook (hash sau khi chuẩn hóa CRLF thành LF), analyzer và mọi module nó nạp có hash được ghi trong `K/evidence-loss-prereg.json` trước khi chạy bộ gán nhãn trên nhánh `metric` và `no_metric`; `summary.json` của lần chạy chính ghi `prereg.codebook_sha_matches`, `analyzer_sha_matches` và `imports_sha_match` cùng `true`.
- R@1 (so chính xác) và MRR (4 chữ số thập phân) tính lại bằng bản sao của `_label_hit` trùng `author-score.txt` ở mọi run có chấm điểm (70 ở S1 v2, 62 ở vòng 2; run hỏng không có `scoring/`), không lệch run nào.
- Mọi con số trong báo cáo kết quả truy được về một file trong `runtime/analysis-evidence-loss-*`.
- Báo cáo nêu rõ n = 8 case và 4 dịch vụ GT, dùng ngôn ngữ mô tả, và chứa mục kết cục áp dụng đúng luật đã đóng băng (kể cả `no_stage_implicated`), kèm bảng "kết cục đã biết trước" và mọi điều kiện `not_testable`.
- Test mới pass (kể cả cổng dữ liệu thật), bộ test hiện có không hỏng, hai file `.py` mới và hai file test dùng LF.

## Ràng buộc

- Chỉ CPU. Test và analyzer chạy bằng `runtime/harness-env/Scripts/python.exe -X utf8` (venv có pandas, numpy; không có matplotlib).
- Không sửa `upstream/`. Không ghi đè thư mục `runtime/analysis-*` cũ.
- Test split niêm phong. Chỉ 8 case train đã chạy.
- Không đưa mã kế hoạch, số phase, mã finding vào comment code, tên test hay thông điệp commit. Mô tả bất biến hoặc hành vi trực tiếp.
- Commit và push chỉ khi sếp yêu cầu. Thông điệp commit theo conventional commits và không có dòng ghi công AI, theo quy tắc phát triển của sếp.
- In dữ liệu có emoji thì đặt `PYTHONIOENCODING=utf-8`.

## Rủi ro chính và điểm tự phản biện

| Rủi ro | Tác động | Giảm thiểu |
|---|---|---|
| Một LLM-coder cùng họ model với tác giả codebook | Đồng thuận cao giả | Ghi rõ "LLM-coder"; mù với kết cục; sếp phân xử trước khi mở nhãn luật |
| Nhãn "đúng" ở nhánh `hit_without_evidence` che mất cơ chế | Hiểu sai nguyên nhân | Hai nhãn song song và cờ riêng, báo cả run đúng lẫn sai |
| Kappa méo trên mẫu nhỏ | Số đồng thuận vô nghĩa | Bỏ ngưỡng kappa, PABAK và bootstrap; báo đồng thuận thô theo chỉ báo và theo case |
| 8 case nhưng 4 dịch vụ GT, seed gần như nhân bản | Giai đoạn "nổi bật" thực ra là hiệu ứng một case hay một dịch vụ | Đơn vị là dịch vụ GT; luật mô tả với phép kiểm khả thi và `not_testable`; bỏ lần lượt từng dịch vụ GT |
| Số liệu scout có thể lệch khi tính lại | Kết luận sai | Phase 4 tái tính toàn bộ và nêu từng chỗ lệch |
| Câu hỏi mở về `reason` so với `local_root_cause` | Chỉ báo I2 đổi theo định nghĩa | Chốt định nghĩa chính (nhãn) trước khi đóng băng, báo `I2_lenient` như độ nhạy |
| Tool metric là bản harness đã sửa, bảng chỉ có khi hỏi đúng GT | I0 gần như đồng nghĩa "đã hỏi GT" (oracle) | Ghi vào codebook và báo cáo; tách truy vấn GT khỏi truy vấn khác; ghi `tool_match_rule_differs` |

## Câu hỏi còn mở (cho sếp)

1. (Sếp chốt 2026-11-01) Phase 6 dùng một agent mù đọc theo codebook, sếp phân xử chỗ lệch.
2. (Sếp chốt 2026-11-01) Không chờ S1 v3. Khi output S1 v3 về, chạy lại analyzer đã đóng băng và so `runs.csv` như kiểm tính tất định (phase 9).
3. (Sếp chốt 2026-11-01) Không replay LLM trong kế hoạch này, kể cả replay CPU bằng model lượng tử hóa. Chỉ có các cột dựng lại hint tất định; hiệu ứng của X ghi là chưa đo.
4. Có chấp nhận tên "first-loss stage" thay cho "decisive step" không? Kế hoạch dùng "first-loss stage" vì chưa có replay phản thực.
5. (Sếp chốt 2026-11-01) Luật chọn giai đoạn cho X giữ dạng mô tả, không thêm ngưỡng đạt hay trượt.
6. (Đã giải quyết bởi red team) Cổng vào S1 đến S4 là I0 đúng, không phải "có span GT trong trace"; case GT vắng khỏi trace không còn bị loại. Sếp có thể bác.
7. Sếp có muốn một commit đóng băng codebook (để có thứ tự thời gian chống chối cãi) trước khi chạy chính thức không, và nhánh `feat/rclagent-evidence-loss-analysis` cắt từ nhánh hiện tại `feat/rclagent-s1-v3-checks-and-vllm-probe` hay từ `main`? `check-hash-seed-order.py` đã có trên `main` từ khi merge PR #4 (`df64e21`), nên cắt từ `main` mới nhất cũng được. Mặc định không commit; đóng băng chỉ có hash cục bộ và báo cáo ghi "không có thứ tự thời gian độc lập".
8. Fixture từ một run thật có thể commit dưới dạng bản rút gọn không, hay chỉ lưu trong `runtime/` (gitignored)? Mặc định chọn phương án thứ hai, và test dữ liệu thật **thất bại** khi thiếu zip trừ khi đặt `EVIDENCE_LOSS_ALLOW_NO_ZIP=1`.
9. Có chạy lại điều kiện `no_metric` với câu NO_KPI trên GPU để tách hiệu ứng câu chữ không? Mặc định là chỉ ghi nhận như một hạn chế.
10. Ablation theo modality trong bài RCLAgent gốc chưa được đọc [UNVERIFIED]; cần đọc bản gốc trước khi viết phần định vị trong bài báo. Các trích dẫn ARMOR (venue), Lost in the Middle, McHugh 2012, Byrt 1993, Sim và Wright 2005, OpenRCA 2.0 và AgenTracer cũng chưa được xác minh.

### Quyết định sau phase 8

Sếp chốt ngày 2026-11-01, sau phase 8 (theo đề xuất của agent):

1. Q7: commit ngay lên nhánh `feat/rclagent-evidence-loss-analysis`, cùng toàn bộ kết quả. Commit chỉ chứng minh nội dung, không chứng minh thứ tự: nhãn đã sinh ra sau khi đóng băng, nên báo cáo vẫn ghi "đóng băng cục bộ, không có thứ tự thời gian độc lập".
2. Q9: không chạy lại; hiệu ứng câu chữ NO_KPI ghi là hạn chế.
3. Replay LLM: chưa làm; để sang RQ (c) khi thiết kế X. Nếu làm, bắt đầu ở S2 (consolidation làm mất tên GT khỏi nhãn root).
4. Người đọc thứ hai khác họ model: không; `misattributed`, I5 và `final_residual` giữ là phần chưa kiểm tay, trừ khi sau này đưa chúng vào bài như khẳng định.
5. Hai script tính câu kết cục: chuyển vào `kaggle/` (có theo dõi), đọc thẳng `runs.csv`, có test, để reviewer chạy lại được ba CSV quyết định.
6. Hình tĩnh từ `runs.csv`: không đưa ra hỏi lần này; mặc định không làm.

## Red Team Review

Bốn reviewer (Assumption Destroyer, Failure Mode Analyst, Scientific Validity Critic, Scope & Complexity Critic) nộp 32 phát hiện; sau khi gộp trùng còn 16 nhóm. Mọi nhóm đều có bằng chứng file hoặc số đo từ zip. Tôi tự kiểm lại ba điểm nền tảng trên zip S1 v2: 5283 `tool_result` đều có `params` là dict; `_label_hit` coi `cartservice` và `cartservice-0` là khớp; case `de6a50` điều kiện `metric_no_log` nhận bảng metric của `checkoutservice` ở 3 trên 3 seed dù không có span GT. Tôi cũng đọc `summary.json` của so sánh vòng 2 với S1 v2: `identical` 50 gồm 2 cặp `failed->failed`. Các số phễu khác do reviewer tính và còn là [reviewer-computed] cho tới khi analyzer tính lại.

| # | Phát hiện (nguồn, mức) | Xử lý | Lý do | Phase đã sửa |
|---|---|---|---|---|
| 1 | Luật quyết định không thể thỏa, kết cục định sẵn (AD1, FM2, SV1, SC1; Critical) | Chấp nhận | `first_loss_linear` luôn gán S2 trước S4; chỉ 5f7a77 có đủ hai nhóm S2, chênh lệch 0. Thay bằng luật xếp hạng mô tả, phép kiểm khả thi, bảng kết cục đã biết, kết cục `no_stage_implicated` hợp lệ | 1, 3, 7, plan |
| 2 | Tiền đề hình dạng dữ liệu sai: `params` là dict, `delivered`, join đa tập, `protocol` events, mili giây (AD5, FM1; Critical) | Chấp nhận | Đã kiểm 5283 trên 5283 là dict; fixture cũ không có `params`. Sửa đặc tả, thêm cổng dữ liệu thật thất bại khi thiếu zip | 1, 2, 3 |
| 3 | Thiên lệch thứ tự S2 trước S3, S4 là phần dư, I3 phụ thuộc I1 (AD2, SV3; High) | Chấp nhận một phần: giữ I1 và I3 là hai cột nhưng ghi phụ thuộc, không gộp | Vector biên làm nhãn chính, thêm I5 (top-1 theo root), `final_residual` tách ba lớp | 1, 2, 7 |
| 4 | Cổng "evaluable = có span GT" sai (AD3, FM3; High) | Chấp nhận | Đã kiểm de6a50 `metric_no_log` 3 trên 3 nhận bảng GT. Cổng là I0 đúng; Q6 được giải quyết | 1, 2, plan |
| 5 | Cắt cụt, run hỏng, mẫu số, đơn vị dịch vụ GT, case phụ thuộc (AD4, FM4, SV4; High) | Chấp nhận | Chỉ báo dương giữ, âm thành `NA`; I0 âm là `NA_censored`; mẫu số 70 và 62; đơn vị 4 dịch vụ GT; bảng độ nhạy run cắt cụt | 1, 2, 4, 7 |
| 6 | Hiệu chỉnh trùng nhánh xác nhận, rút RNG mơ hồ, đọc không mù (AD6, FM7, SV2, SC3, SV7 phần mù; High) | Chấp nhận | `metric_no_log` giống 92,5 phần trăm `agent_complete` với `metric`. Hiệu chỉnh còn 2 run một case, rút từ case có span GT và loại 29583d (ghi là phơi nhiễm), case bị loại khỏi bảng chính, đọc mù C1 đến C4 trước | 3, 6, 7 |
| 7 | Tool metric là bản đã sửa, gần như oracle GT, so tên khác scorer (AD7; Medium) | Chấp nhận | Thêm cột `table_key_prefixes`, `tool_match_rule_differs`, nêu trong rủi ro và báo cáo | 1, 7, plan |
| 8 | `metric` với `no_metric` không ghép cặp được, `gain_class` hàm ý nhân quả, số 20 và 42 sai (AD8, SV6; Medium) | Chấp nhận | Bỏ ghép cặp mức cặp; so sánh mức case; số đúng là 48 giống hệt và 14 lệch cuối; vòng 2 là kiểm tất định | 1, 2, 4, 7 |
| 9 | Biên nhận đóng băng yếu: CRLF, thiếu hash module, thiếu `analyzer_sha_matches`, ngưỡng không nguồn gốc (FM6, SV8; Medium) | Chấp nhận một phần | Chuẩn hóa LF, `.gitattributes`, hash module nạp, thêm hai cờ, ghi nguồn gốc từng ngưỡng. **Bác**: bắt buộc commit đóng băng (trái quy tắc "commit chỉ khi sếp yêu cầu"; để ở Q7 với mặc định hash cục bộ) và bác phân tích công suất (n = 8, mô tả) | 2, 3, 8 |
| 10 | Kiểm tương đương hint vòng tròn; phase 5 không thể đổi gì; replay không nói gì về LLM (FM5, SV5, SC5; Medium) | Chấp nhận | Kiểm bằng dòng hint trong prompt cuối; phase 5 gộp thành cột; bỏ `oracle_carrier`; "nhất quán với" thay "ủng hộ" | 1, 2, 5, 7 |
| 11 | Ca biên của labeller: JSON null, hạng 0-based, MRR 4 chữ số, mili giây sang giây, retry, S1 v3 là giả thuyết (FM8; Medium) | Chấp nhận | Đã thêm vào đặc tả và test | 1, 2, 4, 9 |
| 12 | Kiểm toán quá nặng: kappa, PABAK, bootstrap, sinh gói (SC2, SV7; High) | Chấp nhận một phần | Cắt phase 6 còn một lượt 10 đến 14 run, đồng thuận thô và kappa mô tả. **Bác** hợp nhất phase 3 vào phase 2 (đóng băng là một ranh giới đăng ký trước riêng) và bác bootstrap theo case (đã bỏ bootstrap) | 3, 6 |
| 13 | Phase 7 quá rộng: 11 bảng, bộ vẽ SVG (SC7; Medium) | Chấp nhận | Bỏ `plot-evidence-loss-figures.py` và test, còn T1 đến T9 bằng bảng Markdown | 7 |
| 14 | Mệnh đề "X không sửa upstream" không định nghĩa, replay CPU suy đoán (SC4; High) | Chấp nhận | Định nghĩa wrapper hoặc override ngoài `upstream/`; bỏ gợi ý replay CPU lượng tử hóa; ghi "hiệu quả chưa đo" | 1, 7, plan |
| 15 | Script so nhãn riêng và phase 9 dư (SC6; Medium) | Chấp nhận | Phép join trong phụ lục; phase 9 thành ghi chú bàn giao | 4, 9, 8 |
| 16 | Ước lượng giờ và quyết định chặn không có mặc định (SC8; Medium) | Chấp nhận | Thêm cột quyết định chặn kèm mặc định; phase 2 thành 12h; tổng 32h | plan |

Tổng: 14 nhóm chấp nhận, 2 nhóm chấp nhận một phần (nhóm 9 và 12, cộng 3 mệnh đề nhỏ bị bác), 0 nhóm bác hoàn toàn. Không phát hiện nào bị loại do thiếu bằng chứng.

### Whole-Plan Consistency Sweep

Đã đối chiếu và sửa:
- Tổng giờ 38h thành 32h (4, 12, 3, 2, 0, 4, 5, 2) ở frontmatter và bảng phase; phase 9 còn 0,5h dạng ghi chú.
- Danh sách script: từ năm script mới còn hai (`analyze-evidence-loss.py`, `audit-evidence-loss-labels.py`) và hai test; đã sửa ở phase 2, 6, 8 và README. Không còn `compare-evidence-loss-labels.py`, `replay-evidence-hint.py`, `plot-evidence-loss-figures.py`.
- Phụ thuộc: phase 7 phụ thuộc 4 và 6 (bỏ 5); phase 6 không còn song song với phase 5; công cụ `audit-evidence-loss-labels.py` chuyển từ phase 3 sang phase 6.
- Thuật ngữ: `S0_gt_not_in_trace` và "evaluable case" bỏ ở plan.md, phase 1, 2, 3, 7; "luật chọn đích" đổi thành "luật xếp hạng ứng viên"; `effective_loss` đổi thành `final_residual`; `gain_class` bỏ.
- Số liệu: số cặp vòng 2 với S1 v2 sửa thành 48 giống hệt và 14 lệch cuối; mẫu số chấm điểm 70 và 62 thay cho "72 run"; "5 evaluable case" thay bằng 4 dịch vụ GT.
- Mặc định commit nhất quán: không commit tự động ở plan.md Q7, phase 3 và phase 8.
- Q6 đã giải quyết; Q1, Q3, Q5, Q7, Q8 cập nhật theo thiết kế mới.

Mâu thuẫn chưa giải quyết:
- Bảng "kết cục đã biết trước" dùng số do reviewer tính (I2 3 trên 14, `first_loss_linear` S2 11 trên 14, root khớp top-1 8 trên 23); chưa có analyzer tính lại. Phase 1 gắn nhãn [reviewer-computed] và phase 4 tái tính; nếu số lệch thì ghi nhận sau. Phase 4 tái tính; số lệch được ghi vào `deviation-log.md` như ghi chú về bảng phơi nhiễm, không đổi luật đã đóng băng. Không tính nhãn `metric` trước đóng băng, để giữ ràng buộc "chưa gán nhãn trước đóng băng".
- Việc loại 29583d khỏi tập rút hiệu chỉnh dựa trên hiểu biết đã phơi nhiễm về kết quả; đã ghi, nhưng sếp có thể muốn rút không loại.
- Bác "bắt buộc commit đóng băng" làm thứ tự đăng ký trước yếu hơn; chỉ sếp quyết định (Q7).
- Số `tool_result`: reviewer ghi 5281, tôi đếm 5283 trên S1 v2 (A và B); cổng dữ liệu thật vì thế dùng bộ đếm thô thay vì số cứng.
- Tên file phase giữ nguyên (`phase-05-hint-code-replay.md`, `phase-09-optional-s1-v3-confirmation.md`) dù nội dung đã đổi, để link không gãy.


## Validation Log

### Verification Results

Ngày kiểm: 2026-10-31. Tier: Full (Fact Checker, Contract Verifier, Feasibility, Consistency). Cách làm: đọc cả 10 file của kế hoạch, rồi đo lại bằng Python (`runtime/harness-env/Scripts/python.exe -X utf8`) trên bốn zip thật (S1 v2 và vòng 2, gói A và B), chạy lại chín bộ test hiện có và chạy `check-plan.py` của skill lập kế hoạch. Phase chỉ bị sửa ở các thẻ `[UNVERIFIED]` đã kiểm được (xem cuối mục).

Số liệu tổng: khoảng 150 khẳng định cụ thể đã kiểm (phase 1 khoảng 34, phase 2 khoảng 22, phase 3 khoảng 16, phase 4 khoảng 19, phase 6 khoảng 15, phase 7 khoảng 14, phase 8 khoảng 17, phase 5 và 9 mỗi phase khoảng 6), **đúng khoảng 133, sai 11, chưa kiểm được 6**. Phase 7 sát ngưỡng 15 vì chủ yếu mô tả bảng chưa tồn tại; phase 5 và 9 dưới ngưỡng vì chỉ còn là ghi chú.

Đã khớp thực tế (chọn lọc, đo bằng zip hoặc đọc file):
- Đường dẫn: mọi file và thư mục được trích dẫn có thật (ba báo cáo scout và research, decision 261028 và 261031, results vòng 2 và S1 v2, `decisions.md`, `llms.txt`, README của `kaggle/`, hai `manifest.json` vòng 2, `s1-v2/{a,b}/manifest.json`). `runtime/harness-env/Scripts/python.exe` là Python 3.12.10, có pandas 2.2.3 và numpy 2.2.6, không có matplotlib. `runtime/` bị git bỏ qua (`check-ignore`); `evidence-loss-prereg.json`, hai script mới, codebook và `deviation-log.md` không bị bỏ qua. `git check-attr eol` trả `lf` cho file `.py` mới. `core.autocrlf=true`; `*.py text eol=lf` nằm ở `kaggle/.gitattributes`, còn `.gitattributes` gốc chỉ có dòng SVG, nên dòng `prereg-*.md` cần thêm ở gốc đúng như phase 2 và 3 viết.
- Mã upstream: `coordinator.py` GEG 80-104, self-state 204-292 (fallback 280-292), consolidate 296-330, `inspect_trace` 424-536, hint 469-483, prompt cuối 485-501 đúng; hint dựng bằng `'"has_error_logs": true'` rồi `elif '"is_abnormal": true'` đúng. `evaluate.py` 57-103 đúng; chạy thật bản `_label_hit`: `cartservice` khớp `cartservice-0` (hạng 0), `frontend` không khớp `frontendservice` (-1). `smoke-worker.py:344` ghi `params=params`; `metric-repair.py:13` (K = 100) và 22-24 (`str.contains` cộng nhánh node-level) đúng. Các chuỗi lý do dừng (`Per-span tool round budget exceeded`, `Model request budget exhausted`, `RCLAgent deadline exceeded`, `Context overflow`, `Invalid structured response`, `Invalid agent JSON output`) có trong `smoke-worker.py`.
- Dữ liệu S1 v2 (A cộng B): 74 file `events.jsonl` (72 trace cộng 2 protocol); `tool_result` 5281 ở pha trace và 2 ở protocol (tổng 5283), mọi `params` là dict, `params.timestamp` là chuỗi mili giây, `raw.timestamp` trong `trace-graph.json` cũng mili giây. `tool_result.source`: `author` 2107, `repaired` 1448, `absent` 1726. `agent_complete` 3795 (self-state 1901, consolidate 1894), không có `operation` None. Run hoàn tất 70 (có `result.json` và `author-score.txt` 70); vòng 2 là 62. Hai run hỏng ở S1 v2 (`272a47...--no_metric--s20261026`: Invalid structured response; `ad1c27...--metric--s20261027`: Invalid agent JSON output) đều là H_parse. Vòng 2 có 10 run hỏng: 5 vượt vòng tool, 3 hết ngân sách request, 2 H_parse, nên 8 run chạm trần đúng. `malformed_tool_call_retry` 33 sự kiện trong 31 run. `local_root_cause` JSON null 35 trên 1894. 298146 dòng log đều có `severity: unknown`, 0 dòng chứa error, exception hay fail. Nhánh fallback tự đánh giá: 0 lần ở cả hai corpus. Ghép đa tập `tool_result` với lời gọi trong response trước đó theo (tên, params): 5281 trên 5281 khớp, không lệch `number` giữa request và response; 3029 response có tool call, trong đó 2258 có từ hai lời gọi.
- Số của scout và reviewer tính lại đúng: 10191 `tool_result` pha trace (5281 cộng 4910 của vòng 2); 3888 nút cây (1944 mỗi corpus); 3642 consolidate; mẫu số chấm điểm 70 và 62 qua `load()` (36 cộng 34, 30 cộng 32); chỉ báo của `metric` (14 run hoàn tất có bảng GT, I2 là 3 trên 14, R@1 là 10 trên 14, GT nằm ở danh sách "metric anomalies only" 14 trên 14 và không bao giờ ở danh sách ERROR LOGS); nhãn root so top-1 cuối `same` 8, `diff` 4, `refusal` 11 trên 23 run `metric` hoàn tất; 1156 trên 1249 `agent_complete` giống từng byte giữa `metric` và `metric_no_log` (92,55 phần trăm); `de6a50` `metric_no_log` nhận bảng GT 3 trên 3 seed dù 0 span GT; số span GT theo case 13, 10, 10, 2, 1 và 0 ở ba case còn lại; 4 dịch vụ GT; run `30e3c7...--no_metric--s20261026` có 82 self-state, 23 consolidate, 1 cuối, metric rỗng 39, log rỗng 42 trên 51. Số 5281 của reviewer và 5283 của người lập kế hoạch cùng đúng (5283 gồm 2 protocol), và 10191 của scout là 5281 cộng 4910, nên mâu thuẫn "chưa giải quyết" trong Red Team Review đã được giải quyết, không có sai lệch.
- Vòng 2 so với S1 v2: 64 cặp không chạm trần, 62 cùng hoàn tất, 2 cùng hỏng, 50 giống hệt gồm 2 cặp hỏng (chạy `compare()` thật, cả hai là `identical`), nên 48 cặp hoàn tất giống hệt và 14 chỉ lệch ở response cuối.
- Công cụ: `load()` chạy được cả bốn corpus với các đường manifest trong kế hoạch và chịu được run hỏng (`scored` là False, không từ chối). Số test cũ chạy lại: 59, 14, 11, 4, 6, 20, 4, 13, 19, tất cả OK. Fixture `clean_events` ở `test-analyze-missing-source-results.py:58-60` không có `params`, `span_id`, `response`. `first_request_divergence` có trong `compare-run-outputs.py` (khóa của kết quả, không phải hàm). Phụ thuộc giữa các phase không có vòng (1, 2, 3, 4; 6 sau 4; 7 sau 4 và 6; 8 sau 7); giờ 4 cộng 12 cộng 3 cộng 2 cộng 0 cộng 4 cộng 5 cộng 2 bằng 32, khớp frontmatter và bảng phase. `check-plan.py` không báo lỗi liên kết hay trạng thái ở `plan.md`.

Thất bại (11), kèm bằng chứng:
1. **High, sai số thứ tự `attempt`.** `phase-01-codebook-draft-and-exposure.md:58` viết "chỉ tính `attempt == 1`" và `phase-02-analyzer-core-and-synthetic-tests.md:64` viết "`attempt > 1` không tính". Dữ liệu: `attempt` bắt đầu từ 0. S1 v2 có 4858 request self-state đầu tiên, 1894 consolidate và 70 request cuối đều `attempt == 0`; retry là `attempt` 1 (31), 2 (1), 3 (1), tổng 33 khớp 33 sự kiện retry. Với `== 1` thì mọi request cuối và gần mọi request thường bị loại, và cổng dữ liệu thật (số request cuối bằng số `result.json`) sẽ thất bại. Hàm test hiện có `request(number, seed, attempt=0, ...)` (`test-analyze-missing-source-results.py:48`) cũng dùng 0 cho lượt đầu. Sửa: tính `attempt == 0`, retry là `attempt > 0`.
2. **Medium, `tool_result_budget` chỉ có cho `search_logs`.** `phase-01...:38` ("mọi phép đo mô hình thấy gì đọc `delivered`"), `phase-01...:57` ("kết quả metric của GT có `tool_result_budget.applied`, kỳ vọng bằng 0") và `phase-04...:43`. Đo: 2876 sự kiện budget trên 2876 `search_logs`, 0 cho `search_fluctuating_metrics` (2405 kết quả). Kiểm "metric bị cắt" luôn bằng 0 một cách vô nghĩa, và văn bản mô hình thấy của bảng metric nằm ở `tool_result.response` (hoặc ở tin nhắn tool của request kế tiếp), không ở `delivered`. Cần ghi rõ nguồn của I0 và thêm kiểm "không có sự kiện budget nào cho metric". Cùng chỗ: kết quả `search_logs` rỗng là bảng chỉ có dòng tiêu đề (2654 trên 2876), không phải `{"message": ...}`; chỉ metric rỗng mới dùng hai câu thông báo. `D1_empty_logs` và `log_result_class` phải định nghĩa rỗng là không quá một dòng.
3. **Medium, kế hoạch không qua kiểm cấu trúc của chính skill lập kế hoạch.** `check-plan.py plans/261031-2311-rclagent-evidence-loss-analysis` trả `FAILED` với 9 phát hiện. Các phase 1, 2, 3, 4, 6, 7, 8 đặt tiêu đề "Tasks & Steps" (ví dụ `phase-01...:33`, `phase-03...:40`) mà bảng alias ở `core/plan_check.py:21-23` chỉ chấp nhận "Steps", "Implementation Steps", "Các bước"; phase 5 và 9 là bản ghi chú nên thiếu các nhóm requirements, files, steps, risk-rollback. Sửa: đổi tiêu đề thành "Steps" ở bảy phase, còn phase 5 và 9 thì thêm mục tối thiểu hoặc chấp nhận cảnh báo đã biết.
4. **Medium, `phase-01...:62` sai số carrier.** Kế hoạch ghi 11 đến 20 carrier mỗi run. Đo theo định nghĩa ở bước 2 (span có `tool_result` metric của GT trả bảng), 15 run `metric` có carrier cho 1, 2, 2, 2, 3, 3, 3, 11, 11, 12, 20, 20, 20, 20, 20; 7 trên 15 run dưới 11, nên mức "gần bão hòa" của I1 phụ thuộc case. Đã sửa tại chỗ khi gỡ thẻ `[UNVERIFIED]`.
5. **Low, `phase-01...:56` gọi `ad1c27` là case có nhiều span GT nhất.** `ad1c27` có 10 span GT, `5f7a77` có 13.
6. **Low, `phase-03...:23` nói `29583d` là "case duy nhất trượt R@1 ở mọi seed".** Đúng trong nhóm có span GT với điều kiện `metric`; nhưng ở `metric_no_log` (điều kiện hiệu chỉnh) `99f095` cũng 0/0/0 và không bị loại, nên lý do loại một case vì "đã biết kết quả quyết định" áp dụng yếu hơn ở điều kiện này.
7. **Low, `phase-01...:40` "Mỗi run có thêm `run/protocol/events.jsonl`".** Đó là một file cho mỗi gói (hai file ở mỗi corpus), không phải mỗi run. Chỉ `request` có khóa `phase`; `tool_result`, `response`, `agent_complete` không có, nên cách loại protocol phải dựa vào đường dẫn `run/traces/<run_id>/`, không dựa vào lọc `phase == "trace"` cho mọi sự kiện.
8. **Low, mơ hồ "request chỉ số 1".** `plan.md:42` và `phase-01...:78`. Đo: `metric` so với `no_metric` rẽ nhánh ở request không-retry thứ hai ở 24 trên 24 cặp, tức giá trị 2 theo quy ước 1-based của `first_request_divergence` (`compare-run-outputs.py:17`). Phải ghi rõ cơ sở đánh số, nếu không một khẳng định tự động sẽ lệch một đơn vị.
9. **Low, "đọc zip chỉ qua `load()`" (`phase-02...:22`).** `load()` (`analyze-missing-source-results.py:129-172`, không phải 120-175) chỉ trả các dòng tóm tắt, không trả sự kiện; `read_run` vẫn phải mở zip, nên chỉ phần kiểm SHA256 và bundle được tái dùng. Thêm nữa, `check-hash-seed-order.py:70` nạp `compare-run-outputs.py`, và file đó nạp analyzer cũ (`compare.analyzer`), nên chuỗi module phải băm là ba file, không phải "nếu có nạp" như phase 3 viết.
10. **Low, hai chi tiết đếm.** "3,35 so với 2,0 request/span" đo lại thành 3,33 so với 2,2 (span chỉ nhận kết quả rỗng, S1 v2); lệch do định nghĩa span, không đổi kết luận. Phase 4 bước 4 nói số `tool_result` "red team đếm 5283" cần kiểm lại: không cần, 5283 gồm 2 protocol.
11. **Low, CLI.** Phase 2 mô tả `OUT_DIR PACKAGE ZIP MANIFEST ...` rồi `--runs`, `--structure-only`, `--label`, còn phase 4 đặt `--label` giữa `OUT_DIR` và các bộ ba; bộ phân tích tay (`sys.argv`) phải chấp nhận cờ ở mọi vị trí và test cần phủ điều này.

Chưa kiểm được (giữ thẻ hoặc chỉ nêu, kèm lý do):
- `plan.md:119` (S1 v3 chỉ xác nhận tính tất định): chưa có output S1 v3 (`runtime/kaggle-output-{a,b}-s1-v3/` chưa tồn tại).
- `phase-09...:13` (mức ảnh hưởng của đổi `validate_calls` lên luồng): chỉ biết được khi có output S1 v3.
- `phase-06...:22` (10 đến 14 run mẫu kiểm toán): chỉ biết sau khi analyzer tạo `runs.csv`.
- `plan.md:127` (ablation theo modality trong bài RCLAgent gốc, ARMOR, Lost in the Middle, McHugh 2012, Byrt 1993, Sim và Wright 2005, OpenRCA 2.0, AgenTracer): chưa đọc bản gốc, không kiểm được offline.
- `first_loss_linear` S2 11 trên 14 và "chỉ 5f7a77 có đủ hai nhóm S2": hệ quả của I2 3 trên 14 (đã đúng) nhưng chưa tính lại theo định nghĩa đầy đủ; phase 4 sẽ tái tính.
- D1 11 trên 11 run trượt, 8 lượt `productcatalogservice` NO_ROWS, 324 trên 327 và 66 trên 1574: chưa tính lại (tổng 327 bảng và 1574 bằng 1901 trừ 327 nhất quán).

Thẻ `[UNVERIFIED]` đã gỡ sau khi kiểm (sửa tại chỗ, không đổi thiết kế): phase 1 dòng 24 (fallback 0 lần), 58 (33 sự kiện trong 31 run), 62 (carrier, đã sửa số), 63 (35 trên 1894), 75 (298146 trên 298146), 82 (3,33 so với 2,2); phase 2 dòng 86 (số test 20, 4, 13, 19); phase 4 dòng 37 (hai manifest vòng 2 có thật); phase 8 dòng 64 (số test của handoff). Còn lại ba thẻ ở `plan.md` (dòng 20, 119, 127) và một ở phase 9; phase 6 dòng 22 vẫn chờ `runs.csv`.

### Validation interview questions (cho sếp)

1. **Người đọc tay thứ hai (phase 6, Q1 của kế hoạch).** Một LLM-coder cùng họ model với tác giả codebook cho đồng thuận cao giả; có cần người thứ hai không?
   - Một agent mù, sếp phân xử bất đồng (30 đến 60 phút của sếp) (Recommended)
   - Sếp tự đọc mẫu 10 đến 14 run (khoảng 2 đến 3 giờ), không dùng agent
   - Hai agent độc lập (một cùng họ, một khác họ model hoặc prompt) cộng sếp phân xử
2. **Chờ S1 v3 trước khi viết báo cáo (Q2).** S1 v3 chạy cùng prompt và seed, chỉ khác thứ tự hint; chưa có output.
   - Không chờ; viết báo cáo từ S1 v2, thêm S1 v3 như mục kiểm tính tất định khi output về (Recommended)
   - Chờ S1 v3 xong rồi viết một lần
3. **Phạm vi replay trên CPU (Q3).** Chỉ phần mã hint của tác giả replay được; mọi replay của LLM cần GPU.
   - Không replay LLM; chỉ giữ cột hint trong analyzer, ghi rõ đó chỉ là mã tác giả (Recommended)
   - Thêm phase replay bằng model lượng tử hóa trên CPU (chậm, không cùng kernel vLLM nên không so được)
   - Hoãn: chuẩn bị một gói replay Kaggle cho RQ (c), chưa chạy
4. **Ngưỡng quyết định X (Q5).** Luật hiện chỉ mô tả, có phép kiểm khả thi (dưới 3 đơn vị thì `not_testable`) và có kết cục hợp lệ `no_stage_implicated`.
   - Giữ luật mô tả, không thêm ngưỡng nào (Recommended)
   - Thêm ngưỡng "tối thiểu 3 dịch vụ GT cùng chiều" (ngưỡng quy ước, nguồn gốc ghi là tùy ý)
   - Sếp tự đặt ngưỡng trước khi đóng băng
5. **Commit đóng băng codebook và nhánh làm việc (Q7).** Analyzer mới dùng `check-hash-seed-order.py`, chỉ có ở nhánh `feat/rclagent-s1-v3-checks-and-vllm-probe`.
   - Cắt nhánh `feat/rclagent-evidence-loss-analysis` từ nhánh hiện tại; không tự commit, hash đóng băng lưu cục bộ và sếp có thể tự lưu ngoài repo (Recommended)
   - Cắt từ `main` sau khi nhánh hiện tại được merge (phải chờ merge)
   - Cho phép một commit đóng băng codebook trước khi chạy chính thức (thứ tự thời gian mạnh nhất, cần sếp bảo rõ)
6. **Fixture từ run thật (Q8).**
   - Chỉ lưu trong `runtime/` (gitignored); test dữ liệu thật thất bại khi thiếu zip, trừ khi đặt `EVIDENCE_LOSS_ALLOW_NO_ZIP=1` (Recommended)
   - Commit một bản rút gọn đã làm sạch (một run, vài trăm KB) để test chạy được ở máy khác
7. **Ngôn ngữ và định khung báo cáo cho reviewer Q1.** Báo cáo kết quả viết tiếng Việt như các báo cáo cũ; bài nộp có thể cần tiếng Anh.
   - Viết báo cáo tiếng Việt; thêm bản tóm tắt phương pháp tiếng Anh một trang cho phần cơ chế sau khi có kết cục (Recommended)
   - Viết thẳng bằng tiếng Anh theo khung bài báo (thêm khoảng 3 đến 4 giờ)
   - Chỉ tiếng Việt, dịch sau khi chốt venue
8. **Tách hiệu ứng câu chữ NO_KPI (Q9).** `no_metric` trả "No matching records found." còn `metric` trả "No fluctuating metrics found."; tách được cần chạy GPU.
   - Chỉ ghi nhận như hạn chế trong báo cáo, không chạy (Recommended)
   - Xếp vào RQ (c) như một lần chạy nhỏ trên Kaggle sau khi có kết cục RQ (b)

### Fixes applied
<!-- validation: fixes log -->
Mỗi sửa được đánh dấu `<!-- validation: ... -->` ở chỗ sửa; số liệu đã đo lại trên bốn zip S1 v2 (gói A và B) và bằng mã `compare-run-outputs.py`.
1. `attempt` 0-based (High): phase 1 bước 1 và phase 2 viết lại thành `attempt == 0` là lượt đầu, `attempt > 0` là retry. Đo lại: 6822 request trace `attempt == 0` (4858 self-state đầu, 1894 consolidate, 70 cuối), retry `attempt` 1/2/3 = 31/1/1 = 33 khớp 33 sự kiện `malformed_tool_call_retry`. Test phase 2 dùng `attempt=0` và `attempt=1,2,3`.
2. Metric và log (Medium): `tool_result_budget` chỉ có cho `search_logs` (2876 trên 2876; 0 trên 2405 metric; protocol thêm 2). Văn bản metric lấy từ `tool_result.response`; metric rỗng là `{message}` (2078 trên 2405); log rỗng là bảng chỉ có tiêu đề, không quá một dòng (2654 trên 2876, 0 là message). Phase 1 (bước 1, cắt bớt, D1, `D1_empty_logs`), phase 2 (test D1) và phase 4 (khẳng định bất biến) đã sửa; kiểm "metric bị cắt" thành kiểm cấu trúc "không có sự kiện budget cho metric".
3. `check-plan.py` (Medium): tiêu đề "Tasks & Steps" đổi thành "Steps" ở phase 1, 2, 3, 4, 6, 7, 8; phase 5 thêm Requirements, Files, Steps, Risks and Rollback; phase 9 thêm Requirements, Files, Steps, Verification.
4. Carrier 11 đến 20 (Medium): đã sửa trước đó; không đổi.
5. `ad1c27` (Low): có 10 span GT; `5f7a77` có 13 và là nhiều nhất. Sửa ở phase 1.
6. `29583d` (Low): phase 3 nêu rõ chỉ đúng ở điều kiện `metric`; ở `metric_no_log` `99f095` cũng 0/0/0.
7. Sự kiện protocol (Low): một `run/protocol/events.jsonl` mỗi gói, chỉ `request` có `phase`; loại bằng đường dẫn `run/traces/<run_id>/`. Phase 1.
8. "Request chỉ số 1" (Low): đo lại bằng `compare()` thật cho kết quả khác cả kế hoạch (1) lẫn bản ghi kiểm (2). Chỉ số 1-based tính mọi request trace kể cả retry: `metric` so với `no_metric` rẽ ở 3 (14 cặp), 4 (3), 6 (6), 7 (1); `metric` so với `metric_no_log` ở 3 (14) và 4 (10); request rẽ nhánh luôn là `self_state_verification` `attempt == 0` (bỏ retry thì là 3, 5 hoặc 6). Phase 1 và `plan.md` mục 3 đã sửa và nêu cơ sở đánh số.
9. `load()` và băm module (Low): `load()` dòng 129 đến 172, chỉ trả dòng tóm tắt nên `read_run` tự mở zip; băm bốn module (`check-hash-seed-order.py`, `compare-run-outputs.py`, `analyze-missing-source-results.py`, `analyze-completion-and-budget-stops.py`) cùng analyzer mới. Phase 2 và 3 (cả lệnh `sha256sum`).
10. Đếm (Low): 3,33 so với 2,2 request/span giữ nguyên; 5283 = 5281 trace cộng 2 protocol, ghi chú kiểm lại ở phase 4 bước 4 được bỏ.
11. CLI (Low): phase 2 yêu cầu bộ phân tích chấp nhận cờ ở mọi vị trí (cờ và giá trị của cờ tách khỏi `sys.argv` trước) và thêm test chạy cùng lời gọi với cờ ở đầu, giữa, cuối, gồm hai dạng ở phase 2 bước 7 và phase 4 bước 2.

### Owner decisions (2026-11-01)

Sếp trả lời bốn câu hỏi xác nhận, cả bốn theo phương án khuyến nghị:
- Người đọc tay thứ hai ở phase 6 là một agent mù, sếp phân xử.
- Không chờ S1 v3; S1 v3 chỉ dùng làm phép kiểm tính tất định khi có output.
- Không replay LLM trong kế hoạch này.
- Luật chọn giai đoạn cho X giữ dạng mô tả, không ngưỡng.

Còn mở: Q4 (tên "first-loss stage"), Q7 (commit đóng băng và gốc nhánh), Q8 (fixture), Q9 (tách hiệu ứng câu chữ NO_KPI), Q10 (đọc bài gốc và xác minh trích dẫn). Các câu này đều có mặc định trong plan và không chặn phase 1 đến 4.
