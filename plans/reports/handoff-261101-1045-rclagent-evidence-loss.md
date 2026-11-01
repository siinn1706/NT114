# Bàn giao: đo nơi mất bằng chứng của RCLAgent khi bỏ nguồn metric (RQ b) — 2026-11-01

Viết cho người tiếp quản hoặc AI của người đó. Chỉ CPU, không gọi LLM, không Kaggle, không đụng test split RE2-OB (niêm phong, D12). Đường dẫn `K/` là `F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`. Kết quả là **mô tả có phơi nhiễm, không phải nhân quả**.

## Đang ở đâu

| Việc | Trạng thái |
|---|---|
| Codebook v1, tuyên bố phơi nhiễm, bảng kết cục đã biết trước | Xong, đóng băng cục bộ 2026-11-01T03:50:04+07:00 |
| Analyzer `K/analyze-evidence-loss.py` và 124 test | Xong, đóng băng |
| Hiệu chỉnh trên hai run `metric_no_log` của case `99f095` | Xong |
| Chạy chính thức S1 v2, bản sao vòng 2, so hai corpus | Xong, `integrity_problems` rỗng, ba cờ hash khớp. Kiểm chéo ở [verify](verify-261101-rclagent-evidence-loss-p4.md) và [tính lại so với scout](analysis-261101-0431-rclagent-evidence-loss-recompute-vs-scout.md) |
| Replay hint | Hủy, đã gộp vào analyzer |
| Kiểm toán đọc mù (12 run, 6 case) | Xong, không bất đồng nhãn; sếp phân xử, `rule_error` 0, `analyzer_error` 0. [Báo cáo](audit-261101-rclagent-evidence-loss-blind.md) |
| Báo cáo kết quả | Xong, đã review: [analysis-261101-1023](analysis-261101-1023-rclagent-evidence-loss-results.md) |
| Tài liệu, bàn giao, chính sách commit | Xong (file này); **chưa commit** |
| S1 v3 như bản sao | Ghi chú, chờ output (xem cuối file) |

Kết cục theo luật đóng băng trên bảng chính (`metric`, bỏ `99f095`): `S0_gt_span_absent` 3/4, `S2_root_label_lost_hit_kept` 2/3, `S4_inputs_present_not_rank1` 1/4, `S0_gt_span_present_not_queried` 0/4, `label_mismatch_flags` không kiểm được; `no_stage_implicated` không được kích hoạt. Con số và giới hạn đọc ở báo cáo kết quả, không chép lại ở đây.

## File mới và chủ sở hữu

| File | Vai trò |
|---|---|
| `K/analyze-evidence-loss.py`, `K/test-analyze-evidence-loss.py` | Analyzer và test; đóng băng, sửa chỉ qua deviation |
| `K/decide-evidence-loss-outcomes.py`, `K/test-decide-evidence-loss-outcomes.py` | Dựng ba CSV quyết định (câu kết cục, hạng hướng X, dự đoán) từ output analyzer; có test; không đóng băng |
| `K/evidence-loss-prereg.json` | Biên nhận hash (codebook, analyzer, bốn module nạp) |
| `plans/reports/prereg-261031-2311-rclagent-evidence-loss-codebook.md` | Codebook v1; `.gitattributes` có dòng `plans/reports/prereg-*.md text eol=lf` |
| `plans/261031-2311-rclagent-evidence-loss-analysis/` | Plan, các phase, `deviation-log.md` (không deviation, một erratum chữ) |
| `plans/reports/analysis-261101-1023-...`, `analysis-261101-0431-...`, `audit-261101-...`, `verify-261101-...`, `research-261031-2311-...`, `scout-261031-2311-...` (hai file) | Báo cáo kết quả, tính lại, kiểm toán, kiểm chéo, nghiên cứu, scout |
| `plans/journals/2026-10-31-rq-b-evidence-loss-plan.md` | Nhật ký phiên |

Không có script kiểm toán nhãn riêng: lượt đọc mù dùng các script dựng gói trong `K/runtime/analysis-evidence-loss-audit/`, không đi vào repo.

## Những gì không có trên GitHub

`K/runtime/` nằm trong `.gitignore`. Các thư mục sau chỉ có trên máy này:
- `runtime/analysis-evidence-loss-s1-v2/` (kết quả chính), `-r2/`, `-r2-vs-s1-v2/`, `-calibration/`, `-structure/`: `runs.csv`, `spans.csv`, `cases.csv`, `case-comparison.csv`, `funnel.csv`, `summary.json`.
- `runtime/analysis-evidence-loss-audit/`: gói kiểm toán, `blind-map.json` và `sample.csv`. **Không mở `blind-map.json` khi cần giữ người đọc mù.**
- `runtime/analysis-evidence-loss-decision/`: `outcome-sentences.csv`, `predictions.csv`, `x-direction-ranking.csv`. Ba file này dựng lại được bằng `K/decide-evidence-loss-outcomes.py` (có trên GitHub) từ hai thư mục analyzer ở trên; test của nó so từng byte với chúng.
- Output Kaggle S1 v2 và vòng 2: `runtime/kaggle-output-{a,b}-s1-v2/` và `runtime/kaggle-output-{a,b}-r2-v1/`.

## Tái lập

```
cd "F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle"
PY="runtime/harness-env/Scripts/python.exe -X utf8"
ZA=runtime/kaggle-output-a-s1-v2/rclagent-smoke/rclagent-smoke-results.zip; MA=s1-v2/a/manifest.json
ZB=runtime/kaggle-output-b-s1-v2/rclagent-smoke/rclagent-smoke-results.zip; MB=s1-v2/b/manifest.json
$PY analyze-evidence-loss.py runtime/analysis-evidence-loss-s1-v2-again --label s1-v2 A $ZA $MA B $ZB $MB
```

Ba CSV quyết định (mặc định đọc `runtime/analysis-evidence-loss-s1-v2` và `-r2`, ghi `runtime/analysis-evidence-loss-decision`; thêm `--out DIR` để ghi chỗ khác):
```
$PY decide-evidence-loss-outcomes.py
```

Vòng 2: cùng lệnh analyzer với `--label r2`, zip ở `runtime/kaggle-output-{a,b}-r2-v1/...` và manifest ở `runtime/bundle-missing-source-{a,b}-r2/manifest.json`. Analyzer từ chối ghi vào thư mục đã có `summary.json`, nên dùng thư mục mới.

Kiểm hash đóng băng (hash là SHA256 của byte file sau khi đổi mọi CRLF thành LF; so với `evidence-loss-prereg.json`):
```
$PY -c "import json;d=json.load(open('runtime/analysis-evidence-loss-s1-v2/summary.json',encoding='utf-8'));print(d['prereg'],d['scorer_equivalence'],d.get('integrity_problems'))"
```
Ba cờ `codebook_sha_matches`, `analyzer_sha_matches`, `imports_sha_match` phải cùng `true`.

Test: `$PY test-analyze-evidence-loss.py` (124 test), `$PY test-decide-evidence-loss-outcomes.py` (62 test; bước so từng byte cần `runtime/`, đặt `EVIDENCE_LOSS_ALLOW_NO_ZIP=1` để bỏ qua khi không có) và chín bộ test cũ (59, 14, 11, 4, 6, 20, 4, 13, 19). `test-check-hash-seed-order` mất vài phút.

## Đóng băng và commit

Đóng băng **cục bộ**: chưa commit, nên không có thứ tự thời gian độc lập; hash codebook v1 `f06077a1a3eb2ab0301f605edbe7e48ef5d94a80b7a99fcd0f5fb3a6f73fc769`. Biên nhận nằm ở `K/evidence-loss-prereg.json` (chưa tracked); chưa ai lưu hash ngoài repo. Sếp có thể tự lưu hash ở nơi có dấu thời gian ngoài repo. Danh sách file nên vào commit sau này và file không được vào ở [phase 8](../261031-2311-rclagent-evidence-loss-analysis/phase-08-docs-handoff-and-commit-policy.md).

## Quyết định của sếp sau phase 8

Sếp chốt ngày 2026-11-01, sau phase 8 (theo đề xuất của agent):

1. Q7: commit ngay lên nhánh `feat/rclagent-evidence-loss-analysis`, cùng toàn bộ kết quả. Commit chỉ chứng minh nội dung, không chứng minh thứ tự: nhãn đã sinh ra sau khi đóng băng, nên báo cáo vẫn ghi "đóng băng cục bộ, không có thứ tự thời gian độc lập".
2. Q9: không chạy lại; hiệu ứng câu chữ NO_KPI ghi là hạn chế.
3. Replay LLM: chưa làm; để sang RQ (c) khi thiết kế X. Nếu làm, bắt đầu ở S2 (consolidation làm mất tên GT khỏi nhãn root).
4. Người đọc thứ hai khác họ model: không; `misattributed`, I5 và `final_residual` giữ là phần chưa kiểm tay, trừ khi sau này đưa chúng vào bài như khẳng định.
5. Hai script tính câu kết cục: chuyển vào `kaggle/` (có theo dõi), đọc thẳng `runs.csv`, có test, để reviewer chạy lại được ba CSV quyết định.
6. Hình tĩnh từ `runs.csv`: không đưa ra hỏi lần này; mặc định không làm.

Danh sách cũ dưới đây giữ lại để đối chiếu; mọi mục đã được chốt như trên.


1. Q7: commit điểm đóng băng hay giữ hash cục bộ (mặc định giữ hash cục bộ).
2. Q9: có chạy GPU để tách hiệu ứng câu chữ NO_KPI không.
3. Có làm replay một giai đoạn LLM (cần GPU Kaggle, không có replay CPU) để chuyển từ ứng viên sang đo hiệu quả, và hướng nào làm đầu tiên.
4. Có cần người đọc thứ hai, khác họ model, cho `misattributed`, I5 và `final_residual` (kiểm toán không phủ ba mục này).
5. Có muốn một hình tĩnh dựng từ `runs.csv` không.

## Khi S1 v3 có output (chỉ khi sếp báo xong và đã tải về; không thăm dò Kaggle)

S1 v3 cùng prompt và seed với S1 v2, chỉ khác thứ tự hint (hash seed cố định) và vài thay đổi harness, nên là bản sao, không thêm bằng chứng độc lập và không dùng để chỉnh luật hay kết luận.
1. Kiểm hash zip khớp file `.sha256` và `check-hash-seed-order.py` báo thứ tự hint đúng seed 0.
2. Kiểm hash biên nhận còn khớp. Nếu không, đây không còn là xác nhận.
3. `$PY analyze-evidence-loss.py runtime/analysis-evidence-loss-s1-v3 --label s1-v3 A $ZA3 $MA3 B $ZB3 $MB3` với `ZA3=runtime/kaggle-output-a-s1-v3/rclagent-smoke/rclagent-smoke-results.zip`, `MA3=s1-v3/a/manifest.json`, tương tự B.
4. `join` `runs.csv` của S1 v3 với S1 v2 như so vòng 2 với S1 v2. Báo số cặp trùng ở I0 đến I3, I4, I5 và danh sách cặp lệch. I0 đến I3 trùng là một giả thuyết đo được, không phải bất biến, vì thay đổi tool-call rejection của S1 v3 có thể đổi luồng; lệch nhiều là một phát hiện về tính tất định.
5. Thêm mục "S1 v3 như bản sao" vào báo cáo kết quả.

## Ràng buộc

- Codebook, analyzer và bốn module nạp bị đóng băng; một vấn đề luật đóng băng thì dừng và báo, không sửa im lặng.
- Chỉ báo, so sánh và câu kết cục đều mô tả; không dùng ngôn ngữ nhân quả. Kiểm toán không được trích cho `misattributed`, I5 hay `final_residual`; người đọc cùng họ model với tác giả codebook.
- File mới dùng LF. Cây làm việc Windows có `core.autocrlf=true`, nên file văn bản đã tracked như `llms.txt`, `decisions.md` và `kaggle/README.md` là CRLF ở cây làm việc và LF ở chỉ mục. `kaggle/*.py` (`kaggle/.gitattributes`) và codebook (`.gitattributes`, dòng `prereg-*.md`) có `eol=lf`; biên nhận `.json` không có thuộc tính `eol`. Hash chuẩn hóa CRLF thành LF nên không bị ảnh hưởng.
- Test split RE2-OB niêm phong; không đọc, không dùng.
