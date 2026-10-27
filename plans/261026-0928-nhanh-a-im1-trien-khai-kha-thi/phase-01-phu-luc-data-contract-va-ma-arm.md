---
phase: 1
title: "Phụ lục data contract cho IM1, mã arm và ràng buộc quyết định"
status: done
receipt: work/receipts/01-a02-hash-01.json
owner_skills: [nckh-method]
---

> Cập nhật 2026-10-26 (sau quyết định chủ dự án): bản **a02** ([phụ lục](work/data-contract-addendum-im1-a02.md), [mã arm](work/arm-ids-a02.csv), [bảng quyết định](work/decision-check-map-a02.csv)) hiện thực các quyết định K2, `trace_id`, ngưỡng 3, khung xáo cạnh một seed, trường `arm`; kiểm 18/18 PASS (`01-a02-hash-01`); quyết định và hash a02 ghi trong decision log. a01 không được duyệt nguyên trạng.
>
> Trạng thái trước đó: bản nháp a01 đã soạn ([phụ lục](work/data-contract-addendum-im1-draft.md), [mã arm](work/arm-ids.csv), [quyết định → kiểm tra](work/decision-check-map.csv)), tự kiểm cơ học 15/15 PASS (`01-consistency-01`). **Chưa được chủ dự án duyệt.** Phụ lục mục D nêu năm điểm cần chủ dự án quyết.

# Giai đoạn 01: Phụ lục data contract và mã arm

## Yêu cầu

- Soạn phụ lục có ngày cho `nt114-rca/nt114-rca/docs/data_contract.md` §7 (Leakage rules), dạng bản nháp trong thư mục kế hoạch: quyền mới dùng cấu trúc không nhãn từ vai train cho khung IM1 (D11).
- Nội dung bắt buộc: chỉ cửa sổ trước anchor; chỉ các trường cần dựng cạnh (`service_id`, `span_id`, `parent_span_id`, thời gian); cấm nhãn, fault type và telemetry val/test; dựng theo hệ và split; đóng băng (hash) trước val/test; kiểm rò rỉ; đường không khung khi không có khung hợp lệ.
- Bảng mã arm: R-a (adaptation, không khung), R-a có khung IM1, R-a khung xáo cạnh, đối chứng không khung cùng pipeline, arm H1 hiện có (`retrieval = none`). Ghi rõ `retrieval = none` không đổi nghĩa; arm có khung không được gộp vào `retrieval = none` theo nghĩa cũ.
- Bảng ràng buộc quyết định → kiểm thử: mỗi quyết định D2, D3, D6, D7, D8, D10, D11, D12, D13 trỏ tới một check cụ thể ở phase sau.

## Tệp

- Đọc: [decisions.md](../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md) (các dòng 2026-10-26), [protocol-v2.md](../261018-2300-single-llm-simplification-and-evaluation-hardening/design/protocol-v2.md), `nt114-rca/nt114-rca/docs/data_contract.md` §5–§7, [test-matrix.md](../261024-0858-tong-quan-1000-q1-chon-bai-nen-rca-thieu-telemetry/design/test-matrix.md) §10.4.
- Tạo trong thư mục kế hoạch: `work/data-contract-addendum-im1-draft.md`, `work/arm-ids.csv`, `work/decision-check-map.csv`.
- Không sửa: `docs/data_contract.md`, protocol v2. Chép phụ lục đã duyệt vào repo là bước đầu của phase 05.

## Các bước

1. Đọc §7 data contract; liệt kê quy tắc hiện tại về thông tin vai train (retrieval/precedent).
2. Soạn phụ lục, bảng mã arm, bảng ràng buộc.
3. Đặt `waiting-human`: chủ dự án duyệt phụ lục và mã arm, gắn hash bản nháp.

## Kiểm tra

- Mỗi điều kiện D11 có trong phụ lục và có test tương ứng ở phase 05.
- Không câu nào đổi nghĩa `retrieval = none`.
- Việc duyệt được chủ dự án ghi vào decision log, gắn hash bản phụ lục.

## Rủi ro và hoàn tác

- Chủ dự án từ chối phụ lục: IM1 không triển khai; phase 05 bị bỏ, phase 03–04 vẫn làm được.
- Hoàn tác: chỉ là tài liệu nháp trong kế hoạch; thay bằng phiên bản mới, giữ bản cũ.
