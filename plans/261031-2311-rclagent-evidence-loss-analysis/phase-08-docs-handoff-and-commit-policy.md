---
phase: 8
title: "Tài liệu, bàn giao và chính sách commit"
status: completed
priority: P2
effort: "2h"
dependencies: [7]
---

# Phase 8: Tài liệu, bàn giao và chính sách commit

## Context links
- Quy tắc tài liệu: `C:/Users/Siinn/.claude/rules/documentation-management.md` (đọc tài liệu trước khi sửa, chỉ cập nhật bề mặt sở hữu nhỏ nhất, kiểm liên kết và khẳng định sau khi sửa).
- Nhật ký quyết định: `F:/Nam/UIT/NT114 - NCKH/plans/261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md` (bảng, cột: ngày, quyết định, nguồn, người quyết; dòng cuối là quyết định ngày 2026-10-31).
- Chỉ mục: `F:/Nam/UIT/NT114 - NCKH/llms.txt` (mục "Tái hiện RCLAgent trên Kaggle", dòng 49 trở đi).
- Bàn giao hiện hành: [handoff-261030-1156](../reports/handoff-261030-1156-rclagent-s1-continue-on-github.md).

## Goal
Ghi kết quả và các quyết định bền vững vào đúng bề mặt tài liệu, để người sau tiếp tục từ báo cáo và `llms.txt` mà không cần đọc lại cuộc hội thoại, và ghi rõ chính sách commit.

## Requirements
- Chỉ cập nhật tài liệu khi hành vi, lệnh, kiến trúc hoặc quyết định bền vững thay đổi. Hoàn tất phase không tự nó là lý do.
- Đọc từng tài liệu trước khi sửa; sau khi sửa, kiểm liên kết và khẳng định với nguồn.
- Không sao chép chi tiết của script hay manifest vào tài liệu; chỉ liên kết tới script, codebook và báo cáo.
- Không commit, không push trừ khi sếp bảo.

## Files to Create / Modify
- Modify: `F:/Nam/UIT/NT114 - NCKH/plans/261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md` (thêm một dòng cuối)
- Create: `F:/Nam/UIT/NT114 - NCKH/plans/reports/handoff-261031-2311-rclagent-evidence-loss.md` (bàn giao ngắn; đặt ngày thực tế khi viết)
- Modify: `F:/Nam/UIT/NT114 - NCKH/plans/reports/handoff-261030-1156-rclagent-s1-continue-on-github.md` (chỉ một dòng con trỏ tới bàn giao mới)
- Modify: `F:/Nam/UIT/NT114 - NCKH/llms.txt` (các mục mới trong phần RCLAgent)
- Modify: `F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/README.md` (một đoạn ngắn liệt kê hai script mới, `analyze-evidence-loss.py` và `audit-evidence-loss-labels.py`, và cách chạy test) <!-- red-team: scripts cut from five to two -->
- Modify: `F:/Nam/UIT/NT114 - NCKH/plans/261031-2311-rclagent-evidence-loss-analysis/plan.md` và các phase (cập nhật trạng thái, dùng `ak plan` nếu có)

## Steps

1. Đọc `decisions.md` đoạn cuối và `llms.txt` phần RCLAgent để khớp định dạng. Thêm một dòng vào `decisions.md`, văn xuôi tiếng Anh như các dòng quanh nó, ghi: (i) first-loss stage được định nghĩa bằng luật tất định trên `events.jsonl`, không dùng LLM-judge; (ii) codebook đóng băng có hash và deviation log; (iii) S1 v2 là corpus chính, vòng 2 và S1 v3 là bản sao xác nhận tính tất định và không được gộp; (iv) kết luận của RQ (b) theo luật xếp hạng đã đóng băng (nêu đúng câu kết cục mô tả: `S0_gt_span_absent`, `S0_gt_span_present_not_queried`, `S2_root_label_lost_hit_kept`, `S4_inputs_present_not_rank1`, `label_mismatch_flags` hoặc `no_stage_implicated`, ghi là mô tả có phơi nhiễm, không phải nhân quả); (v) những gì không làm và cần quyết định (replay LLM, tách nhiễu câu chữ; không có replay CPU); (vi) nguồn là báo cáo kết quả và quyết định của sếp ngày 2026-10-28. Cột người quyết định điền đúng theo thực tế (sếp hay agent theo ủy quyền).

2. Viết `handoff-...-rclagent-evidence-loss.md`: trạng thái từng phase; các file mới và chủ sở hữu; nơi lưu đầu ra không có trên GitHub (thư mục `runtime/analysis-evidence-loss-*`, gói kiểm toán); cách tái lập (lệnh chạy analyzer, kiểm hash đóng băng, test); các quyết định đang chờ sếp; việc cần làm khi S1 v3 có output (chép nguyên các bước ở ghi chú phase 9); ràng buộc LF và test split niêm phong. Thêm một dòng con trỏ trong handoff cũ. Bàn giao nêu rõ đóng băng cục bộ hay có commit, và nếu chưa commit thì hash biên nhận do ai lưu.

3. Cập nhật `llms.txt`: thêm các dòng cho báo cáo kết quả, codebook (đóng băng), báo cáo kiểm toán, bàn giao mới và plan này; mỗi dòng theo mẫu hiện có (liên kết, một câu mô tả có ích). Kiểm tất cả liên kết trỏ tới file tồn tại.

4. Thêm vào `kaggle/README.md` một đoạn ngắn: hai script mới (`analyze-evidence-loss.py`, `audit-evidence-loss-labels.py`), lệnh test, và nhắc rằng đầu ra nằm ở `runtime/` và không được ghi đè.

5. Chạy bộ test đầy đủ và kiểm LF toàn thư mục `kaggle/` để chắc không làm hỏng gì: xem phần Verification.

6. Chính sách commit (thực hiện chỉ khi sếp yêu cầu):
   - Kiểm trạng thái làm việc và nhánh trước. Nhánh `feat/rclagent-evidence-loss-analysis` cắt theo câu trả lời của sếp ở câu hỏi mở số 7 của plan.md. Biên nhận và dòng `.gitattributes` `prereg-*.md text eol=lf` vào commit trước codebook.
   - Không đưa vào commit: `runtime/` (gitignored), dữ liệu run, biên nhận chứa dữ liệu, thông tin xác thực. Biên nhận `evidence-loss-prereg.json` chỉ chứa hash, được commit.
   - Chia commit theo chủ đề, theo conventional commits và không có dòng ghi công AI: một commit cho analyzer và test (`feat(reproduction): ...`), một cho script kiểm toán và test của nó, một cho tài liệu (`docs(reports): ...`) gồm codebook, báo cáo, bàn giao, `llms.txt`, README và `decisions.md`.
   - Push và PR chỉ khi sếp yêu cầu; mô tả PR nêu corpus chính, kết cục của luật quyết định và các hạn chế.

7. Dọn tiến trình: kế hoạch không mở server hay tiến trình nền dài; nếu có tiến trình nào được mở khi chạy thử thì dừng nó trước khi kết thúc.

## Verification
```
cd "F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle"
for t in test-kaggle-harness test-missing-source-conditions test-tool-result-budget test-vllm-t4-compat test-prefill-bench test-analyze-missing-source-results test-analyze-completion-and-budget-stops test-compare-run-outputs test-check-hash-seed-order test-analyze-evidence-loss test-audit-evidence-loss-labels; do echo "== $t"; runtime/harness-env/Scripts/python.exe -X utf8 $t.py 2>&1 | tail -3; done
! grep -lq $'\r' *.py && echo LF-all-ok
cd "F:/Nam/UIT/NT114 - NCKH"
grep -o "](plans/[^)]*)" llms.txt | tr -d '()]' | sed 's/^\[//' | while read p; do [ -e "$p" ] || echo "missing: $p"; done
git status --short
```
Kỳ vọng: số test cũ giữ nguyên (59, 14, 11, 4, 6, 20, 4, 13, 19 theo handoff, đã chạy lại ngày 2026-10-31 và đúng), test mới pass, không dòng `missing:` nào mới, `LF-all-ok`, `git status` chỉ chứa các file thuộc kế hoạch này.

## Success criteria
- Một dòng `decisions.md` mới, đúng định dạng, nêu đúng kết cục.
- `llms.txt` có các mục mới và mọi liên kết còn sống.
- Bàn giao đủ để người khác tái lập mà không cần hội thoại.
- Không có commit nào được tạo khi sếp chưa yêu cầu.

## Risks
- `llms.txt` hoặc `decisions.md` đã bị sửa song song ở nhánh khác. Giảm thiểu: đọc lại ngay trước khi sửa và sửa ở dòng cuối.
- Viết kết luận bền vững quá sớm trong `decisions.md` khi kết cục là "chưa có giai đoạn nào rõ ràng". Giảm thiểu: ghi nguyên văn kết cục này như một kết quả hợp lệ.

## Rollback
Hoàn lại từng file bằng `git checkout -- <file>` chỉ khi sếp đồng ý (các file này có thể có thay đổi khác của sếp); file mới thì xóa. Không dùng thao tác phá hủy rộng.

## Kết quả thực hiện (2026-11-01)

- Đã sửa: `decisions.md` (một dòng cuối, tiếng Anh), `llms.txt` (năm mục mới đầu phần RCLAgent), `kaggle/README.md` (mục "Đo nơi mất bằng chứng (RQ b)" gồm `--label`, `--runs`, `--structure-only`, biên nhận và quy tắc hash), bàn giao cũ (một dòng con trỏ). Đã tạo [handoff-261101-1045](../reports/handoff-261101-1045-rclagent-evidence-loss.md) với bước S1 v3 chép từ phase 9. Ba file có đuôi dòng CRLF ở cây làm việc (chỉ mục là LF) giữ nguyên CRLF.
- Sai khác so với bản nháp phase: không có `audit-evidence-loss-labels.py` hay test của nó (kiểm toán dùng script dựng gói trong `runtime/analysis-evidence-loss-audit/`, không vào repo), nên README chỉ nêu analyzer và test của nó, và danh sách test ở bước Verification bỏ `test-audit-evidence-loss-labels`.

### Chính sách commit (không commit trong phase này)

Q7 vẫn mở với mặc định: đóng băng chỉ có hash cục bộ, không có thứ tự thời gian độc lập; không commit, không push. Khi sếp yêu cầu commit, nhánh `feat/rclagent-evidence-loss-analysis` cắt theo trả lời Q7; commit conventional, không dòng ghi công AI.

Nên vào commit (đường dẫn tính từ gốc repo, `K/` là `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`):
- `.gitattributes` (dòng `plans/reports/prereg-*.md text eol=lf`) và `K/evidence-loss-prereg.json`, vào commit trước codebook.
- `K/analyze-evidence-loss.py`, `K/test-analyze-evidence-loss.py` (một commit `feat(reproduction): ...`).
- `K/decide-evidence-loss-outcomes.py`, `K/test-decide-evidence-loss-outcomes.py` (cùng chủ đề, commit riêng sau analyzer).
- `plans/reports/prereg-261031-2311-rclagent-evidence-loss-codebook.md`.
- Toàn bộ `plans/261031-2311-rclagent-evidence-loss-analysis/` (plan, phase, `deviation-log.md`).
- Báo cáo: `analysis-261101-0431-...`, `analysis-261101-1023-...`, `audit-261101-...`, `verify-261101-...`, `research-261031-2311-...`, `scout-261031-2311-...` (hai file), `handoff-261101-1045-...`, và bản sửa của `handoff-261030-1156-...`.
- `plans/journals/2026-10-31-rq-b-evidence-loss-plan.md`.
- Bản sửa của `llms.txt`, `K/README.md` và `plans/261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md` (cùng commit tài liệu `docs(reports): ...`).

Không được vào commit:
- Mọi thứ dưới `K/runtime/` (đã `.gitignore`: đầu ra analyzer, gói kiểm toán và `blind-map.json`, output Kaggle, ba CSV quyết định ở `analysis-evidence-loss-decision/`, dựng lại được bằng `decide-evidence-loss-outcomes.py`), mọi `*.zip` và `*.zip.sha256` ở `K/`.
- `.claude/` và `__pycache__/`.
- Dữ liệu run, thông tin xác thực, dotenv, token.

Hash codebook v1 `f06077a1a3eb2ab0301f605edbe7e48ef5d94a80b7a99fcd0f5fb3a6f73fc769` do biên nhận `K/evidence-loss-prereg.json` giữ; chưa ai lưu hash ngoài repo.
