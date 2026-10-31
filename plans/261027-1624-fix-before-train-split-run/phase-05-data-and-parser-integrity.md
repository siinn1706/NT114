---
phase: 5
title: "Toàn vẹn dữ liệu, adapter và parse câu trả lời"
status: completed
priority: P2
effort: "1d"
dependencies: []
---

# Phase 5: Toàn vẹn dữ liệu, adapter và parse câu trả lời

## Goal
Không có thao tác nào làm hỏng store hoặc làm trôi tập train mà không báo. Thiếu dữ liệu do lỗi giải nén không được trông như telemetry vốn không có. Thời gian không phụ thuộc múi giờ của máy chạy. Câu trả lời LLM sai dạng không làm vỡ lượt chạy hay lệch xếp hạng.

## Findings (do reviewer con báo; mỗi finding cần một test đỏ trước khi sửa)
- **A4** `prep.py:362-364,401-413`: `normalize --limit/--incident` ghi đè `visible/incidents.jsonl`, `eval_only/labels.jsonl`, `quality.jsonl` và `source_index.jsonl` bằng tập con.
- **A5** Nhãn mức node (tier B: `adapters/rca100.py:194-195`, `adapters/aiops2025.py:247-248`) có `root_service_ids` rỗng, vẫn vào tập train, và luôn bị chấm là miss (`score.py:22-27`).
- **A6** `adapters/aiops2025.py:131-136,177-207,313-316`: một ngày chưa giải nén thành `natural_absent` và không có cờ WINDOW_CLIPPED.
- **A7** `adapters/rca100.py:211,256`: `fromisoformat(...).timestamp()` không kiểm múi giờ. Máy chạy ở UTC+7, dữ liệu ở UTC+8.
- **A8** `llm.py:47-59,273-297`: schema thiếu `uniqueItems`, nên Borda cộng trùng. `float(confidence)` không kiểm kiểu.
- **A9** `safe_extract.py:74,89-91`: khi chạy tiếp chỉ so kích thước member. Một member tên `.extract.json` bị file receipt ghi đè. Tên chỉ khác hoa/thường đè nhau trên NTFS.
- **A10** `analyze.py:60-84` chặn hàng `val` khỏi bảng headline nhưng không chặn hàng `train`.

## Files to Create / Modify
- Modify: `nt114-rca/nt114-rca/src/rca/prep.py`, `adapters/aiops2025.py`, `adapters/rca100.py`, `llm.py`, `safe_extract.py`, `analyze.py`, `run_grid.py` (lọc tier theo Q3)
- Modify/Create: test tương ứng trong `nt114-rca/nt114-rca/tests/` (`test_prep_driver.py`, `test_adapter_aiops2025.py`, `test_adapter_rca100.py`, `test_llm_raw.py`, `test_safe_extract.py`, `test_analyze.py`)

## Tasks & Steps
1. **A4:** khi chạy partial, ghi ra thư mục tạm, hoặc từ chối chạy trên data home dùng chung nếu không có `--output`. Test: `--limit 5` trên bản sao fixture thì store gốc phải không đổi.
2. **A5, theo Q3:** mặc định loại incident có `root_service_ids` rỗng khỏi query của `run_grid` khi `split_role: train`, đếm và ghi log số ca bị loại. Test trên fixture có một ca tier B.
3. **A6:** phân biệt ngày "không có archive" với "có archive nhưng chưa giải nén". Trường hợp thứ hai phải raise, hoặc gắn cờ `EXTRACT_MISSING` rồi loại khỏi condition matrix. Test với fixture có archive mà không có `.extract.json`.
4. **A7:**
   - Trước tiên kiểm dữ liệu RCA100 thật xem chuỗi thời gian có kèm offset không (chỉ đọc file).
   - Nếu chuỗi không có offset: gán UTC+8 tường minh, như `audit._iso_ns`.
   - Test: chạy với `TZ` khác nhau thì kết quả phải như nhau.
5. **A8:** thêm `uniqueItems` (hoặc khử trùng giữ thứ tự đầu tiên trước khi tính Borda) và kiểm kiểu `confidence`. Câu trả lời sai dạng được ghi là lỗi parse của hàng đó, không làm vỡ cả grid. Test với `["a","a","a"]`, `"85%"`, và một mảng.
6. **A9:**
   - Receipt lưu sha của archive và của từng member; khi chạy tiếp thì so sha.
   - Cấm member tên `.extract.json`.
   - Phát hiện tên trùng nhau khi bỏ qua hoa/thường.
   - Test cho từng trường hợp.
7. **A10:** chặn hàng `train` khỏi headline giống cách chặn `val`. Test với một hàng `train`.

## Verification
- `pytest -m "not realdata"` toàn bộ pass. `python -m rca.prep verify-splits` cho 16/16.
- `python -m rca.prep verify-bundle <bundle>` vẫn OK.
- A6 và A7 làm thay đổi output normalize, nên chỉ chạy lại normalize khi sếp duyệt. Sau đó phải dựng lại split và chạy `verify-splits`.

## Risk / Rollback
- A6 và A7 có thể đổi dữ liệu canonical, kéo theo digest, split và manifest. Vì vậy chỉ sửa code và test trước. Việc tái tạo release dữ liệu là một quyết định riêng của sếp.
- Phải sao lưu data home trước mọi lần normalize lại.
