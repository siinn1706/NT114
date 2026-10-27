---
phase: 4
title: "Builder bằng chứng R-a và một lời gọi tổng hợp"
status: planned
owner_skills: [nckh-backend, nckh-test]
---

# Giai đoạn 04: Builder R-a, một lời gọi (M3, nhánh a)

## Yêu cầu

- Builder riêng `src/rca/rcl_evidence.py` có `BUILDER_VERSION` riêng: ghép bằng chứng theo đường (trace: phân rã theo đồ thị, bằng chứng theo nhánh; `no_trace` và `frame_free`: bằng chứng phẳng theo ứng viên từ tool metric/log). Chỉ thay khối `{evidence}` của prompt `v1`.
- Đúng **một lời gọi** LLM cho mỗi câu trả lời; `n_samples` của cùng lời gọi theo protocol hiện hành không phải lời gọi vai khác. Dùng lại `llm.py` (client, cache, parse), ánh xạ ứng viên, `RANK_CAP`, `score.py`.
- `run_grid.py`: thêm arm R-a; tính mục tiêu `blind_nonroot_ev` tương đương cho builder mới hoặc tái dùng danh sách hiện có (mvp-outline §4), kèm test.
- Phân loại kết quả: `not_applicable`, `execution_error` (gồm lỗi parse), `wrong`, `correct`; báo theo hệ và theo đường.
- `cost.py`: đếm lời gọi mỗi ô và token theo arm.

## Tệp

- Đọc: `src/rca/llm.py`, `run_grid.py` (dòng 210-259), `score.py`, `metrics.py`, `cost.py`, `tests/test_pipeline.py`, `tests/test_run_grid_canonical.py`.
- Tạo: `src/rca/rcl_evidence.py`, `tests/test_rcl_evidence.py`, `configs/exp/ra-mock.yaml`.
- Sửa có test: `run_grid.py`, `cost.py`.

## Các bước

1. Test trước: một lời gọi cho mỗi câu trả lời ở cả ba đường; phân loại kết quả; ca `no_trace` ở lại mẫu số.
2. Viết builder, nối vào `run_grid`, chạy bằng mock LLM trên dữ liệu tổng hợp.

## Kiểm tra

- Mock end-to-end exit 0; sổ chi phí ghi đúng một lời gọi cho mỗi câu trả lời (cổng **S3**).
- Không ca nào rời mẫu số: tổng bốn loại kết quả bằng số ca.
- Test hiện có không đổi kết quả; `pytest` toàn bộ exit 0.
- Mọi đầu ra và báo cáo gọi R-a là "adaptation RCLAgent không recursion-of-thought". Kết quả mock không phải kết quả mô hình.

## Rủi ro và hoàn tác

- Prompt dài vượt ngữ cảnh model nhỏ: ghi số token trên fixture; giới hạn đặt ở phase 07, không cắt bằng chứng theo nhãn.
- Hoàn tác: builder là file mới; hoàn nguyên sửa ở `run_grid.py`, `cost.py` theo diff.
