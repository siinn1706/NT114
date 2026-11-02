# Nhật ký deviation: RQ (c) bước 1

Codebook: [prereg-261102](../reports/prereg-261102-rclagent-metric-substitute-codebook.md), hash ở `K/metric-substitute-prereg.json`.

## 1. Cách đọc "span server" và "span client" khi quy độ trễ (ghi trước khi chạy script trên dữ liệu thật, 2026-11-02)

- Vấn đề: mục 3 của codebook dùng "span server" theo hai nghĩa. Dòng "Span liên quan GT" gọi mọi span có `cmdb_id` khớp GT là span server. Dòng "Quy về dịch vụ" tách span server và span client để chọn `callee` hoặc `caller`. Reviewer độc lập của script nêu: span `checkoutservice` gọi `hipstershop.CartService/GetCart` có `cmdb_id` là GT, nên theo nghĩa thứ nhất phải quy về GT dưới mọi cách.
- Cách script đọc: dữ liệu không có cột phân biệt client và server (`type` luôn là `rpc`), nên script coi một span là span client khi `operation_name` có dạng `pkg.Service/Method` và dịch vụ đó khác `cmdb_id`. Hệ quả:
  - `U1`, `U2` và số span liên quan GT dùng nghĩa thứ nhất (`cmdb_id` khớp GT là span server).
  - Quy độ trễ (`U0_*`) dùng hướng gọi: span client quy về bên được gọi (`callee`), bên gọi (`caller`) hoặc một trong hai (`either`).
- Lý do: câu hỏi mở của [scout phase 1](../reports/scout-261102-rclagent-metric-substitute-signals.md) (mục Kết luận 4 và Câu hỏi còn mở) và lựa chọn sếp duyệt nói đúng trường hợp này: với `5f7a77`, quy về bên được gọi thì ra `cartservice`. Theo cách đọc của reviewer, biến thể `callee` sẽ trùng `either` ở mọi span của GT, và phép độ nhạy mất ý nghĩa. Câu kết cục chính dùng `either` nên không đổi theo cách đọc nào. Chỉ biến thể độ nhạy `callee` phụ thuộc vào lựa chọn này.
- Test ghi lại cách đọc: `test_rules_split_on_a_client_span_of_the_faulty_service` trong `K/test-analyze-metric-substitutes.py`.

## 2. Chi tiết triển khai không có trong codebook

- Phân vị: `sorted[min(n-1, floor(p*n))]`, giống script nháp phase 1.
- Hòa ở span đứng đầu (theo thời gian tự thân hoặc theo tỉ lệ): lấy span đứng trước trong file; số span hòa ghi ở `cases.csv` (`top_self_ties`, `top_ratio_ties`).
- R@1 và MRR lấy từ `analyze-missing-source-results.py` `load()`, chính hàm đã sinh `runs.csv` mà codebook mục 2 nêu; script đối chiếu R@1 với `rank` của `runs.csv` RQ (b), lệch thì ghi vào `integrity`.
- Ba case không có span GT được nhận diện bằng số span có `cmdb_id` khớp GT bằng 0 (`set = excluded`).
