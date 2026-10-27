# Review toàn repo trước ultrareview — 2026-10-27

**Kết luận:** chưa nên chạy tập train. Không thấy bí mật bị commit, không thấy nhãn rò vào prompt, không thấy lỗi path traversal. Nhưng có hai lối chạy tập train và cả hai đều chưa sẵn sàng:

- Harness Kaggle RCLAgent chỉ chạy được một trace (xem [review 1400](review-261027-1400-rclagent-train-batch-readiness.md)).
- Pipeline `nt114-rca` (`run_grid`) sẽ dừng ngay khi chạy với `split_role: train` mà vẫn bật retrieval, hoặc khi dùng lại một `evidence_dir` cũ.

README gốc cũng đã lỗi thời so với kết quả version 8.

Phạm vi: nhánh `feat/rclagent-harness-budget-guard` @ `d3e91e7` (đã chứa toàn bộ `main` @ `7941e17`). Đã đọc `nt114-rca/nt114-rca/src/rca` và `scripts/datasets` (qua một reviewer con), harness Kaggle và README gốc, và quét bí mật trên mọi file tracked.

**Giới hạn:** chưa chạy bộ test `nt114-rca` lần này, vì hook của sếp chặn mọi lệnh Bash có `.venv`, và em không lách hook đó. Lần chạy gần nhất ([review 0912](review-261027-0912-training-data-readiness.md)): `test_splits.py` và `test_leakage.py` 25 pass, `verify-splits` 16/16 OK. Ngoài ra chưa review các script nghiên cứu và xuất bản trong `plans/*` (literature, publish).

## Findings

Mọi finding dưới đây đã đối chiếu với source. Hai finding High em tự đọc lại code.

**High: chặn chạy tập train qua `run_grid`**

1. **Retrieval không chạy được trên tập train.** `run_grid.py:193-197`: kho retrieval là toàn bộ incident train. Còn `:470-476` raise khi một incident trong kho cũng là query. Lấy `configs/canonical_pilot.yaml` (`retrieval: [none, bm25, dense, hybrid]`) và đổi `split_role: train` là lỗi ngay. Cần kho kiểu leave-one-group-out, hoặc chỉ dùng `retrieval: [none]`.
2. **Một file evidence lạc làm hỏng cả lượt.** `run_grid.py:418-432` kiểm mọi `*.json` trong `evidence_dir` trước khi lọc incident được chọn. Một file của dataset khác gây `KeyError`; một file test có digest cũ gây "stale evidence". Cách tạm: dùng `evidence_dir` mới.

**Medium**

3. **`run_grid.py:116-146` không kiểm split và condition matrix có khớp build hiện tại không.** Chỉ `verify-splits` phát hiện được điều này. Nếu normalize lại, tập train trôi đi một cách lặng lẽ.
4. **`prep normalize --limit/--incident` ghi đè toàn bộ store canonical bằng tập con** (`prep.py:362-364,401-413`).
5. **Nhãn mức node (tier B, RCA100/AIOps2025) không có `root_service_ids`.** Các ca này vẫn vào tập train và luôn bị chấm là miss (`score.py:22-27`), tốn lượt LLM mà làm giảm điểm gộp.
6. **AIOps2025: một ngày chưa giải nén trông giống telemetry vốn không có** (`adapters/aiops2025.py:131-136,177-207,313-316`). Ngày đó bị đánh dấu `natural_absent` và không có cảnh báo WINDOW_CLIPPED.

**Low**

7. **`llm.py:47-59,273-297`:** schema không có `uniqueItems`, nên một candidate lặp lại bị cộng Borda nhiều lần. Ngoài ra `float(confidence)` không kiểm kiểu, có thể làm dừng giữa grid.
8. **`safe_extract.py:74,89-91`:** khi chạy lại, chỉ so kích thước member, không so hash.
9. **`analyze.py:60-84`** chặn hàng `val` khỏi bảng headline nhưng không chặn hàng `train`. **`im1_frame.py:101-136`** dựng frame từ mọi incident train, nên trên tập train là in-sample.
10. **Tài liệu lỗi thời.** `README.md:6,53-54` vẫn ghi "dừng ở bước E", "38.048 dòng metric", "0 dòng log". Version 8 đã chạy hết đầu-cuối với 66.846 dòng metric và 1.747 dòng log. Ngoài ra prompt ultrareview trước em ghi nhầm upstream là `LLM4AIOps/RCL`; đúng là `LLM4AIOps/RCLAgent-V2`.

**Đã kiểm, ổn:**
- `VisibleCase` và prompt không chứa nhãn.
- Phần chia split (union-find, `grouped_fill` có seed, `verify_split`).
- `safe_join` và chặn link/traversal khi giải nén.
- AUROC/AUPRC khi có hòa, Holm, MRR@5 có kiểm duyệt.
- Không có token hay khóa nào trong file tracked.

## Năm vùng dễ lỗi nhất cho ultrareview

1. Vòng đời `run_grid` trên tập train: kho retrieval chồng với query, `evidence_dir`, ghim split vào build.
2. Harness Kaggle RCLAgent: bất biến "query được guard cho qua phải trả đúng như dữ liệu đầy đủ", ngân sách `search_logs`, `HarnessStop` bị nuốt, và mọi chỗ cứng một trace.
3. Thời gian trong adapter: `rca100.py:211,256` gọi `fromisoformat` mà không kiểm múi giờ (máy chạy UTC+7, dữ liệu UTC+8), cùng ánh xạ tên file AIOps2025.
4. `selective.py`/`confidence.py`: coverage khi hòa, ngưỡng fit trên DEV, biên của `risk_exact@c`.
5. `evidence.py`/`ablate.py` dưới `blind_root`: span con mồ côi hoặc chữ "Not available" có làm lộ service bị che hay không.

## Câu hỏi còn mở

1. "Chạy train" là chạy harness Kaggle RCLAgent hay `run_grid` của `nt114-rca`? Hai lối có điều kiện sẵn sàng khác nhau.
2. Retrieval có được tắt cho tập train không, hay cần kho loại trừ nhóm của chính query?
3. Chuỗi thời gian thật của RCA100 có kèm offset không?
