---
phase: 5
title: "Khung IM1 từ trace vai train, khung xáo cạnh, đường không khung, kiểm rò rỉ"
status: planned
owner_skills: [nckh-backend, nckh-security]
---

# Giai đoạn 05: Khung IM1 và kiểm rò rỉ

## Yêu cầu

- Phụ lục đã quyết là [a02](work/data-contract-addendum-im1-a02.md). Bước đầu: chép nguyên phần A của a02 vào `docs/data_contract.md` §7 (quy tắc 8).
- Khóa K2, ngưỡng 3 ca train góp cạnh (cố định), khung xáo cạnh một seed lấy từ sha256 khung thật, ghi tỷ lệ cạnh thật giữ lại (trên 0,5: không thông tin). Đo **độ phủ thật** sau khi dựng khung trên dữ liệu train (CPU, không nhãn) và báo thay cho số dự kiến; khóa không đạt ngưỡng đi `frame_free`, không đổi ngưỡng.
- `src/rca/im1_frame.py`: dựng đồ thị phụ thuộc dịch vụ từ trace **vai train**, chỉ cửa sổ trước anchor, chỉ trường cần cho cạnh; theo hệ và split; ghi file khung kèm hash, đóng băng trước val/test.
- Khung xáo cạnh: hoán vị cạnh với seed ghi trước, giữ số nút và số cạnh.
- Không có khung hợp lệ cho hệ hoặc split: bộ chọn đường trả `frame_free`; ca ở lại mẫu số.
- Arm theo mã đã duyệt ở phase 01; H1 báo riêng cho arm có khung; IM1 là thăm dò (D13).

## Tệp

- Đọc: phụ lục đã duyệt, `src/rca/splits.py`, `store.py`, `rcl_trace_graph.py`, `rcl_path.py`.
- Tạo: `src/rca/im1_frame.py`, `tests/test_im1_frame.py`, `tests/test_im1_leakage.py`.
- Sửa: `docs/data_contract.md` (chép phụ lục đã duyệt), `rcl_evidence.py` (nhận khung cho đường `no_trace`), `run_grid.py` (arm IM1).

## Các bước

1. Test rò rỉ trước: builder khung chỉ mở bản ghi vai train; đưa ca val/test vào phải ném lỗi.
2. Viết builder khung, khung xáo cạnh, nối vào đường `no_trace`.
3. Chạy mock end-to-end cho bốn arm IM1.

## Kiểm tra

- Rò rỉ: hoán vị nhãn không đổi khung; canary nhãn và fault type không có trong khung; bản ghi sau anchor bị loại; ca val/test không vào khung; hash khung không đổi sau khi dựng dữ liệu val/test.
- Khung xáo cạnh khác khung thật (tỷ lệ cạnh trùng dưới ngưỡng ghi trước), cùng số nút và số cạnh.
- `frame_free` khi thiếu khung; tổng loại kết quả bằng số ca.
- Cổng **S2** khi bất kỳ test rò rỉ nào thất bại.

## Rủi ro và hoàn tác

- Khung train trùng cấu trúc test vì cùng hệ: đây là thông tin cấu trúc được phép theo D11, nhưng phải báo; không coi là bằng chứng hiệu quả.
- Hoàn tác: file mới; bỏ arm IM1 khỏi `run_grid.py`; hoàn nguyên phụ lục trong `docs/data_contract.md` nếu chủ dự án rút quyết định.
