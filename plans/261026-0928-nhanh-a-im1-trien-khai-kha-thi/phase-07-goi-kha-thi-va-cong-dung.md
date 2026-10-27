---
phase: 7
title: "Gói khả thi không chạy, cổng dừng và yêu cầu cấp quyền chạy"
status: planned
owner_skills: [nckh-experiment]
---

# Giai đoạn 07: Gói khả thi (không chạy model)

## Yêu cầu

- Ghi **cấu hình máy thực đo**: máy của phiên lập kế hoạch (Intel Core i5-14400F 10 nhân/16 luồng, RAM 31,8 GB, AMD Radeon RX 5600 XT, không có `nvidia-smi`; đo bằng CIM/WMI ngày 2026-10-26) và máy GPU dự kiến (RTX 4080 Laptop 12 GB, chủ dự án báo, chưa probe). Chủ dự án xác nhận máy sẽ chạy; nếu là máy RTX, chạy `scripts/gpu_probe.py` trên máy đó (không tải model) và dán khối `hardware` vào cấu hình.
- Model và lượng tử hóa dự kiến: chính Qwen3.5-4B (bf16 hoặc fp8), dự phòng Qwen3-4B-Instruct-2507; tùy chọn Qwen3-8B AWQ4 và Qwen3.5-9B NF4 theo `configs/hardware/rtx4080-laptop-12gb.yaml`. Ước lượng VRAM bằng `python -m rca.capacity` trên CPU (không tải trọng số), dùng số token prompt đo từ mock R-a và IM1 ở phase 04–05.
- Trần ghi trước khi chạy: VRAM không quá `gpu_memory_utilization` 0,90 của bộ nhớ đo được; prompt không quá `max_model_len` đo được; trung vị thời gian mỗi câu trả lời và tổng giờ cho DEV pilot 12 sự cố (`configs/exp/gpu-feasibility.yaml`).
- Cổng dừng **S4**: R-a trên model 4–9B không vượt B1m trên DEV → quyết định dừng, không tinh chỉnh vào test, không trích số DEV làm kết quả. OOM hoặc vượt trần thời gian → dừng profile, không nâng trần khi đang chạy.
- Yêu cầu cấp quyền chạy: danh sách lệnh, máy, model, số sự cố DEV, trần thời gian, dữ liệu không rời máy, không API.

## Tệp

- Đọc: `configs/hardware/rtx4080-laptop-12gb.yaml`, `configs/exp/gpu-feasibility.yaml`, `docs/gpu_deployment.md`, `src/rca/capacity.py`, `src/rca/feasibility.py`.
- Tạo trong thư mục kế hoạch: `work/feasibility-pack.md`, `work/run-authorization-request.md`; receipt cho lệnh `rca.capacity`.

## Các bước

1. Chạy `rca.capacity` trên CPU với số token đo từ mock; lưu receipt.
2. Viết gói khả thi và yêu cầu cấp quyền.
3. Đặt `waiting-human`.

## Kiểm tra

- Không lệnh nào tải trọng số, mở GPU, gọi API hay thuê cloud trong phase này.
- Mọi con số trong gói có receipt hoặc ghi rõ là ước lượng.

## Rủi ro và hoàn tác

- Máy RTX không sẵn sàng: gói ghi `blocked`. Máy AMD hiện tại không thay được vì cấu hình vLLM/CUDA không hỗ trợ; dùng ROCm hay llama.cpp trên CPU là quyết định riêng của chủ dự án.
- Hoàn tác: chỉ tài liệu.
