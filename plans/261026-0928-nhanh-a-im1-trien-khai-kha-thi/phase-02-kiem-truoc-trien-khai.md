---
phase: 2
title: "Kiểm trước triển khai: lộ test, membership H1, đặc tả quy tắc chọn đường"
status: done
receipt: work/receipts/02-h1-membership-04.json
owner_skills: [nckh-data, nckh-statistics]
---

> Cập nhật 2026-10-26: cổng S1 được chủ dự án quyết "ghi nhận và tiếp tục, có giới hạn" (decision log, dòng "Gate S1"); split và mẫu số giữ nguyên; M5 phải ghi lịch sử tiếp xúc; không gọi đánh giá trên split này là xác nhận độc lập. Đặc tả đường bản a02: [path-selection-spec-a02.md](work/path-selection-spec-a02.md) (K2, số đường là dự kiến).
>
> Trạng thái trước đó: ba kiểm đã xong. Membership H1 khớp thiết kế ([csv](work/h1-membership-recheck.csv), `02-h1-membership-04`). Đặc tả quy tắc chọn đường a01 có hash (`02-spec-hash-02`). Kiểm lộ test ([báo cáo](work/test-exposure-audit.md), `02-exposure-audit-hash-02`) thấy tổng gộp vai test RCAEval đã lộ, nên cổng **S1** mở và chờ chủ dự án chọn phương án. Phụ thuộc vào phase 01 đã bỏ (plan.md §8).

# Giai đoạn 02: Kiểm trước triển khai (CPU, không LLM)

## Yêu cầu

- **Lịch sử tiếp xúc test (D12):** tìm mọi lần đọc kết quả hoặc nhãn test RE2-OB trong repo, thư mục kết quả cũ (`results_*`), báo cáo và log của các kế hoạch. Ghi thật một trong ba: đã lộ, chưa thấy lộ, không xác định được. Không gọi việc niêm phong lại là khôi phục tính mù.
- **Membership H1 (D3):** đếm lại pool `single_modality` theo split hiện hành: số injection, số có trace, số RE2-SS không trace, theo hệ. Đối chiếu 69/108 và 39 của test-matrix; ghi chênh lệch.
- **Đặc tả quy tắc chọn đường:** hàm thuần chỉ nhận cờ telemetry sẵn có của ca (có span hợp lệ, có metric, có log) và trạng thái khung (có hay không, hash); trả về `trace`, `no_trace` hoặc `frame_free`. Đóng băng bằng hash trước mọi đánh giá.

## Tệp

- Đọc: `nt114-rca/nt114-rca/src/rca/splits.py`, `ablate.py`, `eval_units.py`, `store.py`, `configs/eval_exclusions.yaml`, manifest split trong data home. Cột nhãn chỉ dùng trong script đếm membership, không ghi ra file dùng làm đầu vào model.
- Tạo trong thư mục kế hoạch: `work/test-exposure-audit.md`, `work/h1-membership-recheck.csv`, `work/path-selection-spec.md`, receipt cho từng lệnh.

## Các bước

1. Tìm dấu vết tiếp xúc test RE2-OB; ghi từng nguồn và kết luận.
2. Script đếm membership (CPU) có receipt; so với 69/108.
3. Viết đặc tả quy tắc chọn đường; ghi hash.

## Kiểm tra

- Receipt v2 cho mọi lệnh đếm, exit 0, có hash đầu vào.
- Đặc tả quy tắc không tham chiếu nhãn, đáp án hay đầu ra model.
- Cổng **S1**: test đã lộ hoặc membership lệch thiết kế → dừng trước khi cố định mẫu số, báo chủ dự án.

## Rủi ro và hoàn tác

- Script đếm chạm cột nhãn: giới hạn trong script, ghi rõ trong receipt.
- Hoàn tác: chỉ tạo file báo cáo trong kế hoạch.
