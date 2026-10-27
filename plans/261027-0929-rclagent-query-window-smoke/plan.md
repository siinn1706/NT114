# RCLAgent: phạm vi query theo cửa sổ thời gian và smoke sau sửa

Trạng thái: các bước đã làm xong; smoke version 6 dừng ở E vì context overflow, chờ quyết định phương pháp. Kết quả: [report](../reports/fix-261027-0929-rclagent-query-window-smoke.md). Quét CPU 90 ca theo yêu cầu tiếp theo: [report](../reports/scan-261027-1010-re2ob-tool-response-overflow.md). Thiết kế ngân sách tool result: [report](../reports/design-261027-1155-tool-result-budget.md); đã duyệt, triển khai và chạy Kaggle version 7: [report](../reports/run-261027-1235-rclagent-kaggle-v7-tool-result-budget.md). Sửa guard timestamp ngoài dữ liệu đầy đủ và Kaggle version 8 chạy hết end-to-end: [report](../reports/run-261027-1330-rclagent-kaggle-v8-guard-full-data-range.md). Phạm vi do chủ dự án giao ngày 2026-10-27; không commit/push.

## Nguyên nhân đã chứng minh

Bước E version 5 dừng vì guard chỉ cho các cặp (service của span, giây) trong trace. Tool tác giả nhận mọi `service_name`/`timestamp` và phục vụ toàn bộ dữ liệu gộp; dữ liệu đầy đủ có 1.570 dòng log `cartservice` trong ±60 giây quanh root span. Query `cartservice` hợp lệ theo contract tác giả; gói thiếu phạm vi và guard chặt hơn tác giả.

## Thay đổi

1. `prepare-bundle.py`: gói mọi dòng metric trong [giây đầu trace − 1.200, giây cuối trace + 1.200] và mọi dòng log trong [giây đầu − 60, giây cuối + 60] của dữ liệu đầy đủ, không lọc service. Kiểm nguồn gốc chỉ thuộc ca `checkoutservice_cpu_2`; so byte phản hồi endpoint gốc trên lưới service × timestamp.
2. `selection.json`: thay `query_pairs` bằng `query_window` (contract nội bộ giữa bundle và worker).
3. `smoke-worker.py`: guard cho mọi service, chỉ chặn timestamp ngoài cửa sổ; kiểm lại tham số ở mức URL thực gửi tới tool server.
4. Test hồi quy cho nguyên nhân cũ và hành vi mới; validator gói kiểm `query_window`.
5. Ánh xạ RE2-OB bằng `source_incident_key` thay cho inject time.

Không đổi upstream, prompt, model/revision, sampling, context, output, retry, số vòng tool, trần E.

## Điều kiện chấp nhận

- Toàn bộ harness/T4 test qua trong venv `runtime/harness-env` (tái tạo bằng `kaggle/harness-requirements.txt`).
- `cpu-equivalence.json` pass cho mọi query trong cửa sổ; package validator pass.
- Một lượt Kaggle với cấu hình hiện tại; ghi kết quả thật, kể cả thất bại.

## Rủi ro đã biết

Kết quả log `cartservice` gốc là 274.292 byte, 124.953 token; request kế tiếp ước tính 126.089 token, vượt context 16.384. Nếu model lặp query này, guard sẽ dừng vì overflow, không cắt ngữ cảnh. Cách xử lý là quyết định phương pháp của chủ dự án.
