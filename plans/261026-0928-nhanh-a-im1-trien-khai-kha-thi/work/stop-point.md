# Điểm dừng thực tế (2026-10-26)

Kế hoạch tạm hoãn theo quyết định của chủ dự án ngày 2026-10-26 (decisions.md, ba dòng cuối). Không xóa, không reset, chưa commit. Trạng thái trong các file phase 03–08 (`planned`) không được cập nhật theo tiến độ; file này là nguồn đúng.

R-a là adaptation từ RCLAgent: không phải bản tái hiện đầy đủ, đã bỏ cơ chế recursion-of-thought trung tâm. Việc bỏ cơ chế đó không tự chứng minh một đóng góp mới.

## Đã viết code (repo `nt114-rca/nt114-rca`, working tree)

- Module mới: `src/rca/rcl_path.py`, `rcl_trace_graph.py`, `rcl_tools.py`, `rcl_evidence.py`, `im1_frame.py`.
- Mở rộng theo arm: `run_grid.py`, `llm.py`, `score.py`, `selective.py`, `cost.py`, `analyze.py`, `contrasts.py`; `docs/data_contract.md` §7 quy tắc 8; `configs/exp/ra-mock.yaml`.
- Test mới: `test_rcl_path.py`, `test_rcl_trace_graph.py`, `test_rcl_tools.py`, `test_rcl_evidence.py`, `test_ra_pipeline.py`, `test_im1_frame.py`, `test_im1_leakage.py`, `test_group_bootstrap.py`; sửa `test_analyze.py`, `test_leakage.py`.

## Đã kiểm bằng CPU / mock / dữ liệu tổng hợp

- Full pytest: 402 trước khi sửa (`03-pytest-baseline-02`), 425 sau phase 03 (`03-pytest-full-01`), 443 sau phase 04 (`04-pytest-full-01`), đều exit 0.
- Code phase 05–06 (IM1, arm keys, group bootstrap, ci_reading) chỉ qua bộ test hẹp; **chưa chạy full suite sau phase 05–06**.

## Đã đo trên dữ liệu thật, không gọi model

- Độ phủ khung IM1 trên split grouped (`05-im1-coverage-01`, `work/im1-frame-coverage.{json,csv}`): khung hợp lệ RE2-OB, RE3-OB, RE2-TT; test 285 bản ghi → 39 đi `no_trace` ở arm có khung.
- Mô phỏng MDE H1 (`06-h1-mde-01`, `work/h1-mde-simulation.csv`): chạy xong exit 0, **chưa đọc, chưa viết ghi chú**.

## Chưa kiểm thực nghiệm

- Chưa có lời gọi model thật nào cho bất kỳ arm nào; không có kết quả độ chính xác.

## Dang dở (không tiếp tục)

- Ghi chú MDE (`work/h1-mde-recheck.md`), full pytest sau phase 05–06.
- Phase 07: prepare DEV (lệnh `07-dev-prepare-01` bị chủ dự án từ chối, không chạy), đo prompt bằng `rca.capacity`, gói khả thi, yêu cầu cấp quyền chạy.
- Phase 08: review code/wording, gate matrix, handoff.

## Dùng lại sau này

- `rcl_tools` / `rcl_trace_graph` để đối chiếu với tool của bài gốc; hạ tầng `run_grid`/`score`/`selective` và kiểm rò rỉ cho thí nghiệm thiếu telemetry; arm `ra` làm biến thể đối chiếu "không đệ quy" nếu chủ dự án cần.
