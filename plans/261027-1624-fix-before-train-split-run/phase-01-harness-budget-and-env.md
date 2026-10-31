---
phase: 1
title: "Ngân sách, môi trường và nguồn service của harness"
status: completed
priority: P1
effort: "0.5d"
dependencies: []
---

# Phase 1: Ngân sách, môi trường và nguồn service của harness

## Goal
Đóng 4 finding ultrareview trong `kaggle/` mà không đổi hành vi trên các trace đã chạy.

## Findings
- **U1** `smoke-worker.py:22-25`: ngân sách tính theo từng kết quả `search_logs`, trong khi comment khẳng định 4 vòng tool vừa context. Điều này chỉ đúng khi mỗi lượt có tối đa một `search_logs`, còn `validate_calls` thì cho phép nhiều call song song.
- **U2** `harness-requirements.txt:4-30`: thiếu `transformers==4.55.4`, `tokenizers==0.21.4` và `huggingface-hub==0.34.4` (PINS ở `kaggle-runtime.py:30-31`). Hệ quả là `check-tool-result-budget.py:36` không chạy được trong môi trường dựng theo README.
- **U3** `tool-result-budget.py:168-187`: `ladder()` gọi `parse` và `merge_template` hai lần.
- **U5** `prepare-bundle.py:36-39`: `KNOWN_SERVICES` chép tay, trong khi upstream lấy từ `config.get_known_services()` (`coordinator.py:368`).

## Files to Create / Modify
- Modify: `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/smoke-worker.py` (U1, theo quyết định Q1)
- Modify: `.../kaggle/tool-result-budget.py` (U3)
- Modify: `.../kaggle/harness-requirements.txt` (U2)
- Modify: `.../kaggle/prepare-bundle.py` (U5)
- Modify: `.../kaggle/test-tool-result-budget.py`, `.../kaggle/test-kaggle-harness.py` (test hồi quy)
- Regenerate: `.../kaggle/tool-result-budget-check.json` (hash worker và module đổi)

## Tasks & Steps
1. **U1, test đỏ trước:** một response có 2 call `search_logs`, mỗi kết quả lớn khoảng 2.048 token. Chứng minh request kế tiếp vượt phép tính an toàn.
2. **U1, sửa theo Q1:**
   - Phương án khuyến nghị: chia ngân sách giữa các `search_logs` trong cùng response, mỗi call nhận ⌊2.048 / n⌋. Với n = 1 thì giữ đúng 2.048, nên trace v7/v8 không đổi byte nào.
   - Nếu sếp chọn giữ nguyên cách tính theo từng kết quả: chỉ sửa comment, design report và README cho đúng phạm vi bảo đảm, và thêm test chứng minh guard dừng sạch.
   - Kết quả metric: giữ nguyên, không tính vào ngân sách. Quét 450 trace cho thấy phản hồi metric trên RE2-OB tối đa 10 token. Ghi rõ giới hạn này trong comment.
3. **U3:** sửa `ladder()` để parse một lần, dựng nhóm template một lần, rồi truyền vào hàm render. Test: so output với bản hiện tại trên lưới 48 query của `check-tool-result-budget.py` và trên request 3 của v6; phải trùng byte.
4. **U2:** thêm 3 pin còn thiếu, đúng phiên bản của Kaggle. Dựng một môi trường sạch trong scratch theo đúng lệnh trong file, rồi chạy `check-tool-result-budget.py`.
5. **U5:** lấy danh sách service từ `config.get_known_services()` của bản upstream đã ghim. Nếu không import được ở bước đóng gói thì `assert` hai danh sách khớp nhau. Test: thêm một service giả vào bản sao upstream thì assert phải hỏng.
6. Chạy lại `check-tool-result-budget.py`, `refresh-package.py`, `build-notebook.py` và `verify-package.py`.

## Verification
- `runtime/harness-env/Scripts/python.exe -X utf8 -m unittest test-kaggle-harness test-tool-result-budget` cho kết quả 20+ và 9+ test, tất cả pass.
- `test-vllm-t4-compat.py` pass 4/4. `verify-package.py` cho status pass.
- `tool-result-budget-check.json`: các query giữ nguyên byte và các query bị rút gọn trùng với bản trước sửa (trừ hash).
- Đột biến: tắt phần chia ngân sách thì test của bước 1 phải đỏ.

## Risk / Rollback
U1 đổi một sai lệch đã duyệt, nên chỉ làm sau khi sếp trả lời Q1. Nếu cần rollback, khôi phục bản v8 từ `runtime/bundle-v7` hoặc từ git.
