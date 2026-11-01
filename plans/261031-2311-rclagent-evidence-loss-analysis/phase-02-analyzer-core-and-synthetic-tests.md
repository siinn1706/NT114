---
phase: 2
title: "Analyzer lõi và test tổng hợp"
status: completed
priority: P1
effort: "12h"
dependencies: [1]
---

# Phase 2: Analyzer lõi và test tổng hợp

## Context links
- [Phase 1](./phase-01-codebook-draft-and-exposure.md): codebook nháp là đặc tả của analyzer, gồm hình dạng dữ liệu thật ở bước 1.
- Mẫu analyzer: `K/analyze-missing-source-results.py` (hàm `load()` dòng 129 đến 172 <!-- validation: load line range -->, CLI dòng 234 đến 239), `K/analyze-completion-and-budget-stops.py` (nạp bằng `importlib` ở dòng 28 đến 31), `K/compare-run-outputs.py` (`first_request_divergence`), `K/check-hash-seed-order.py` (tách prompt cuối).
- Mẫu test: `K/test-analyze-completion-and-budget-stops.py`, fixture zip trong `K/test-analyze-missing-source-results.py` (`make_run`, `request`, `matrix`, `write_session`). <!-- red-team: fixture lacks params --> Fixture `clean_events` ở dòng 58-60 không có `params`, `span_id`, `response`; không dùng nguyên trạng cho test mới.
- Scorer: `K/runtime/kaggle-dataset-check-a-s1-v3/upstream/evaluate.py` dòng 57 đến 103.

## Goal
Có analyzer `analyze-evidence-loss.py` biến zip kết quả thành bảng theo span, bảng theo run (vector chỉ báo I0 đến I5, `first_loss_linear`, `final_residual`), bảng theo case, bảng so sánh điều kiện mức case và `summary.json`, đúng codebook, kèm test tổng hợp và một cổng kiểm trên dữ liệu thật.

## Requirements
- <!-- validation: load returns summary rows only --> `analyze-missing-source-results.py:load()` (dòng 129 đến 172) chỉ trả các dòng tóm tắt, không trả sự kiện: gọi nó để giữ kiểm SHA256, bundle và run trùng, còn `read_run` vẫn phải tự mở zip và đọc `run/traces/<run_id>/events.jsonl`.
- Không đọc test split. Không sửa `upstream/`.
- CLI theo quy ước hiện có (đọc `sys.argv` tay): `analyze-evidence-loss.py OUT_DIR PACKAGE ZIP MANIFEST [PACKAGE ZIP MANIFEST ...]`, cộng `--runs FILE`, `--structure-only`, `--label NAME`. <!-- validation: order-independent CLI --> Bộ phân tích tay phải chấp nhận cờ ở mọi vị trí (trước, giữa hoặc sau `OUT_DIR` và các bộ ba `PACKAGE ZIP MANIFEST`): tách cờ và giá trị của cờ ra khỏi `sys.argv` trước, phần còn lại là `OUT_DIR` rồi các bộ ba. Phase 4 (`--label` giữa `OUT_DIR` và các bộ ba) và phase 2 bước 7 (`--structure-only` đứng đầu) dùng thứ tự khác nhau nên đều phải chạy được.
- Đầu ra tất định: sắp xếp theo khóa, không phụ thuộc thứ tự mục trong zip.
- Bản sao `_label_hit` và `_k8s_service_base` giữ nguyên hành vi upstream (hạng 0-based, `-1` không trúng). Không đưa số phase hay mã finding vào comment.
- Tên file kebab-case, LF. <!-- red-team: scope merge --> Gộp vào analyzer này mọi cột cần cho phase 4 (so nhãn hai corpus) và phase 5 cũ (cột hint); tách module chỉ khi file vượt khoảng 800 dòng.

## Files to Create / Modify
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/analyze-evidence-loss.py`
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/test-analyze-evidence-loss.py`
- Modify: `F:/Nam/UIT/NT114 - NCKH/.gitattributes` (thêm `plans/reports/prereg-*.md text eol=lf`, xem phase 3 bước 7)

Không sửa file nào hiện có khác. File này chủ sở hữu duy nhất của analyzer.

## Steps

1. Dựng khung với các hàm thuần (không I/O trừ `load_corpus` và `write_outputs`):
   - `import_script(name, filename)` nạp `analyze-missing-source-results.py` và `check-hash-seed-order.py`.
   - `base_of`, `label_hit`, `rank_of`: bản sao hành vi `evaluate.py`.
   - <!-- red-team: params is a dict --> `parse_params(value)` nhận **dict** (đường chính) hoặc chuỗi (đường lùi, `ast.literal_eval`); `timestamp` là chuỗi mili giây. Trả `{}` và đánh dấu integrity problem chỉ khi kiểu khác hai loại trên.
   - `read_run(zip, run_id)`: lọc `phase == "trace"`; `response.body` qua `json.loads`; trả sự kiện theo thứ tự, `trace-graph.json`, `result.json` (nếu có), `worker-status.json`, `progress.json`, GT. Dòng hỏng là integrity problem của run.
   - `join_tool_results(events)`: ghép `tool_result` với response liền trước theo đa tập (tên, params, `span_id`) <!-- red-team: multi tool-call join -->, không theo vị trí.
   - `build_span_ledger(run)`: một dòng mỗi (run, span), cột như bản cũ, thêm `table_key_prefixes`, `tool_match_rule_differs`, `gt_span_in_trace`, `hint_list_size`, `gt_sole_entry`, `d1_dropped_list_size`, `d2_dropped_list_size`; <!-- red-team: ms to s --> `metric_query_ts_offset_s` = (`params.timestamp` mili giây trừ `raw.timestamp` mili giây) chia 1000, đơn vị giây ghi trong tên cột; `log_result_class` và D1 đọc `tool_result_budget.delivered`, không đọc `response` nguyên bản.
   - `reconstruct_hint(self_evidences)`: đúng luật chuỗi tác giả. <!-- red-team: circular equivalence --> Kiểm tương đương bằng cách **phân tích các dòng hint trong văn bản prompt cuối** và so tập dịch vụ; ghi `hint_equivalent`. Không dùng `parse_prompt` của `check-hash-seed-order.py` cho phép so này.
   - `label_run(ledger, run)`: I0 đến I5, vector biên, `first_loss_linear`, `final_residual`, D1, D2, `D1_empty_logs`, các cờ, `final_top1_matches_root_label`, `empty_reason`. Refusal xử lý theo kiểu: JSON null và mọi giá trị không phải chuỗi vào lớp `refusal` <!-- red-team: null local_root_cause -->.
   - `harness_class(status_reason)` và quy tắc cắt cụt: chỉ báo dương giữ, chỉ báo âm và phía sau là `NA`; I0 âm trong run cắt cụt là `NA_censored`.
   - `case_comparison(run_rows)`: so sánh điều kiện ở mức case (mô tả, "không ghép cặp"), `first_request_divergence` thô và gộp câu chữ, tỉ lệ `agent_complete` giống từng byte giữa hai điều kiện. Không có `gain_class`.
   - `funnel(run_rows)`: đếm số run và số **dịch vụ GT** qua từng chỉ báo, cột `NA` cho run cắt cụt, và bảng độ nhạy "run cắt cụt hỏng ở chỉ báo tệ nhất".
   - `feasibility(run_rows)`: với mỗi giai đoạn, số case có đủ hai nhóm; nhãn `not_testable` khi dưới 3.
   - `summarise(...)` ghi `summary.json`: integrity, `scorer_equivalence` (R@1 so chính xác, MRR so 4 chữ số thập phân, số run so được = số run có `author-score.txt`), `join_checks`, `hint_equivalence`, phễu, `feasibility`, bảng theo case có cột `gt_service`, khối `prereg`.

2. Bất biến tích hợp (mà scout đã làm tay), ghi vào `integrity_problems` khi vi phạm: `response.number` khớp request liền trước; mỗi `tool_result` có đúng một tool call khớp đa tập; mỗi nút cây khớp cha. Vi phạm làm kết quả thành tạm thời.

3. `write_outputs`: ghi `spans.csv`, `runs.csv`, `cases.csv`, `case-comparison.csv`, `funnel.csv`, `summary.json` (UTF-8, `indent=2`, kết thúc `\n`). Từ chối ghi đè thư mục đã có `summary.json`.

4. Viết `test-analyze-evidence-loss.py` (`unittest`, `importlib`, `sys.dont_write_bytecode = True`, `tempfile.TemporaryDirectory()`). Fixture dựng từ **hình dạng sự kiện của run thật** (params dict, `delivered`, response nhiều tool call, `phase`). Nhóm test:
   - So khớp tên: `cartservice` khớp `cartservice-0` (cả hai chiều); `frontend` không khớp `frontendservice`; pod K8s về base; tiền tố có dấu `-`.
   - Từng nhãn S0 (`S0_not_queried`, `S0_empty_result` với ba `empty_reason`), **I0 đúng thắng nhãn khác kể cả khi GT không có span trong trace**, `S1_not_flagged` (kể cả `misattributed`), fallback thiếu cờ, I2 với `chain_depth_kept` và `break_class` nhiều độ sâu, nhiều carrier, I3, I4, I5 ba lớp, `final_residual` ba nhánh, `preserved`.
   - `first_loss_linear` khác `final_residual` ở run S2 đứt nhưng R@1 đạt; chú thích thiên lệch có trong `summary.json`.
   - D1 trên `delivered`, `D1_empty_logs` (log rỗng là bảng chỉ có tiêu đề, không quá một dòng; <!-- validation: empty log is header-only -->), D2; metric rỗng nhận diện bằng `{message}` trong `tool_result.response`; không có `tool_result_budget` nào cho metric.
   - Refusal: JSON null, chuỗi `none`, số, chuỗi rỗng.
   - Cắt cụt: chỉ báo dương giữ, âm thành `NA`, I0 âm thành `NA_censored`, bảng độ nhạy.
   - Retry: <!-- validation: attempt 0-based --> `attempt` 0-based; request `attempt > 0` là retry và không tính vào số request theo span (chỉ `attempt == 0` được tính; test dùng cả `attempt=0` và `attempt=1,2,3`, như `request(number, seed, attempt=0, ...)` ở `test-analyze-missing-source-results.py:48`).
   - Join đa tập; bất biến lệch tham số phải sinh `integrity_problems`.
   - `reconstruct_hint` trùng dòng hint trong prompt cuối tổng hợp mà thứ tự bị xáo.
   - <!-- validation: order-independent CLI --> CLI không phụ thuộc thứ tự: cùng một lời gọi với cờ ở đầu, giữa và cuối cho `args` đã phân tích giống hệt, và cả hai dạng dùng ở phase 2 bước 7 và phase 4 bước 2 đều được chấp nhận (test riêng).
   - Tất định (xáo thứ tự mục zip, hai lần chạy trùng từng byte); từ chối ghi đè; `--runs`; `--structure-only` không in nhãn.
   - `feasibility` trả `not_testable` khi dưới 3 case.

5. `prereg` trong `summary.json`: đọc `K/evidence-loss-prereg.json` nếu có; tính lại hash codebook (chuẩn hóa CRLF thành LF trước khi băm), hash analyzer **và hash của từng module nạp qua `importlib`**; ghi `{frozen, codebook_sha_matches, analyzer_sha_matches, imports_sha_match}`. Test: hash đúng, sai ở từng thành phần, và không có file.

6. <!-- red-team: hard real-data gate --> **Cổng dữ liệu thật** (`RealRunGateTest`, đặt ở phase 2 chứ không đợi phase 3): đọc hai zip S1 v2 thật, so số `tool_result` đã ghép với một bộ đếm dòng độc lập (đếm thô `kind == "tool_result"`), khẳng định 0 integrity problem và số request cuối (`phase == "trace"`, `operation` None) bằng số `result.json`. Thiếu zip thì **test thất bại**, trừ khi đặt biến môi trường `EVIDENCE_LOSS_ALLOW_NO_ZIP=1` (khi đó bỏ qua và in cảnh báo rõ). Không cố định con số kỳ vọng trong test; đối chiếu với bộ đếm thô.

7. Chạy `--structure-only` lên cấu trúc để chuẩn bị phase 3: `$PY analyze-evidence-loss.py --structure-only runtime/analysis-evidence-loss-structure A $ZA $MA B $ZB $MB`. Lệnh in số span, số span GT và độ sâu theo case, không in nhãn hay điểm.

## Verification
Đặt `PY="runtime/harness-env/Scripts/python.exe -X utf8"`, `ZA=runtime/kaggle-output-a-s1-v2/rclagent-smoke/rclagent-smoke-results.zip`, `MA=s1-v2/a/manifest.json`, tương tự `ZB`, `MB`.

```
cd "F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle"
runtime/harness-env/Scripts/python.exe -X utf8 test-analyze-evidence-loss.py
for t in test-analyze-missing-source-results test-analyze-completion-and-budget-stops test-compare-run-outputs test-check-hash-seed-order; do runtime/harness-env/Scripts/python.exe -X utf8 $t.py; done
! grep -q $'\r' analyze-evidence-loss.py test-analyze-evidence-loss.py && echo LF-ok
git check-attr eol analyze-evidence-loss.py
```
Kỳ vọng: test mới pass (kể cả `RealRunGateTest`); số test của bốn file cũ là 20, 4, 13, 19 (đã chạy ngày 2026-10-31, đúng); `LF-ok`; `eol: lf`.

## Success criteria
- Test tổng hợp phủ mọi chỉ báo, kể cả nhánh chưa từng gặp (fallback), refusal null, cắt cụt, retry.
- Cổng dữ liệu thật pass trên hai zip S1 v2.
- Hai lần chạy cho đầu ra trùng từng byte. Chưa chạy nhãn lên `metric` hay `no_metric`; chỉ `--structure-only` và cổng tích hợp.

## Risks
- Hàm `load()` có thể từ chối corpus có run hỏng thiếu `scoring/`. Giảm thiểu: đọc cách `load()` xử lý trước khi viết `read_run`; test dùng zip có run hỏng.
- Nhầm đặc tả giữa `is_abnormal` và các cờ phụ. Giảm thiểu: test cho từng cờ, kể cả thiếu khóa.
- Cổng dữ liệu thật phụ thuộc zip trong thư mục gitignored. Giảm thiểu: thất bại rõ ràng thay vì bỏ qua im lặng.

## Rollback
Xóa hai file mới, hoàn lại dòng `.gitattributes` mới thêm và thư mục `runtime/analysis-evidence-loss-structure/`.
