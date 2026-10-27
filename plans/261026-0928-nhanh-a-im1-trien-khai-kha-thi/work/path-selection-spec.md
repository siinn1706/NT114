# Đặc tả quy tắc chọn đường (bản a01)

- Ngày: 2026-10-26 (Asia/Saigon). Bản **a01**, chưa được duyệt. Hash SHA-256 của tệp này nằm trong receipt `02-spec-hash-01`; tệp không chứa hash của chính nó.
- Cơ sở: D3 (quy tắc chỉ dựa trên telemetry sẵn có, đóng băng trước đánh giá), D11 (đường không khung khi không có khung hợp lệ), [test-matrix.md](../../261024-0858-tong-quan-1000-q1-chon-bai-nen-rca-thieu-telemetry/design/test-matrix.md) §10.1.
- Đặc tả này không phụ thuộc phụ lục IM1 về nội dung khung. Nó chỉ cần biết khung của khóa có hợp lệ hay không và hash của nó. Khóa (K1/K2) do chủ dự án chọn khi duyệt phụ lục; với `ra`, quy tắc không đọc khung.
- Mã nguồn hiện thực ở phase 03 (`src/rca/rcl_path.py`) phải khớp đặc tả này; mọi thay đổi đặc tả sau khi chốt là phiên bản mới có hash mới, ghi trước mọi đánh giá.

## 1. Đầu vào (chỉ những trường này)

| Đầu vào | Nguồn | Ghi chú |
|---|---|---|
| `has_spans` | Bảng trace của ca **sau khi áp điều kiện** (`no_trace` bỏ toàn bộ trace) đọc qua vùng visible | `true` khi có ít nhất một span với `span_id` và `service_id` khác rỗng, và `service_id` thuộc danh sách ứng viên của ca. Trạng thái `natural_absent` và `empty` cho `false` |
| `has_metrics`, `has_logs` | Bảng metric và log của ca sau khi áp điều kiện | Không đổi đường; chỉ quyết tool nào chạy trong đường đã chọn |
| `uses_frame` | Thuộc tính của arm trong [arm-ids.csv](arm-ids.csv) | `false` với `ra`; `true` với `ra_im1`, `ra_im1_shuf` |
| `frame_valid`, `frame_sha256` | Tệp khung đã đóng băng của khóa của ca, theo phụ lục | Khóa không có khung hợp lệ: `frame_valid = false` |

Không đầu vào nào là nhãn, gốc, loại lỗi, đáp án, đầu ra model, điểm hay chất lượng đầu ra. Quy tắc không nhận `incident_uid`, vai split hay hệ ngoài việc tra khung của khóa.

## 2. Hàm

```text
select_path(has_spans, uses_frame, frame_valid) -> "trace" | "no_trace" | "frame_free"
    if has_spans:                      return "trace"
    if uses_frame and frame_valid:     return "no_trace"
    return "frame_free"
```

- `trace`: phân rã theo đồ thị trace, tool metric/log/trace tất định, một lời gọi tổng hợp.
- `no_trace`: không có span; tool metric và log chạy theo khung (thứ tự và láng giềng lấy từ cạnh của khung, giới hạn trong danh sách ứng viên của ca), một lời gọi tổng hợp. Tool trace không được gọi.
- `frame_free`: không có span và không dùng khung; bằng chứng phẳng theo từng ứng viên từ tool metric và log, một lời gọi tổng hợp. Tool trace không được gọi.
- Ca thiếu cả metric lẫn log vẫn có đường (`frame_free` hoặc `no_trace`). Trong pool H1 trường hợp này không xảy ra, vì điều kiện chỉ áp dụng khi còn một modality (data contract §5). Ca như vậy ở ngoài pool sẽ được ghi `not_applicable`, không bị bỏ khỏi bảng.
- Mỗi bản ghi kết quả mang `path` và (nếu có) `frame_sha256`.

## 3. Đường dự kiến trên pool H1 (đếm không nhãn, receipt `02-h1-membership-03`)

Bản ghi = injection × điều kiện áp dụng trong `no_metric`, `no_log`, `no_trace`. Bảng chỉ dùng membership và số ca train có trace của [h1-membership-recheck.csv](h1-membership-recheck.csv). Đây là phép đếm theo đặc tả, chưa có code.

| Vai | Arm | `trace` | `no_trace` | `frame_free` | Tổng |
|---|---|---:|---:|---:|---:|
| test | `ra` | 138 | 0 | 147 | 285 |
| test | `ra_im1`, `ra_im1_shuf`, khóa K1 | 138 | 69 | 78 | 285 |
| test | `ra_im1`, `ra_im1_shuf`, khóa K2 | 138 | 39 | 108 | 285 |
| val | `ra` | 108 | 0 | 102 | 210 |
| val | `ra_im1`, `ra_im1_shuf`, K1 hoặc K2 | 108 | 54 | 48 | 210 |

- `trace` = bản ghi `no_metric` và `no_log` của ca có trace (test 69 × 2, val 54 × 2).
- `frame_free` ở arm có khung = toàn bộ bản ghi sock-shop (test 39 × 2; val 24 × 2), cộng 30 bản ghi `no_trace` của RE3-TT test khi chọn K2.
- Đếm này dựa trên trạng thái trace tự nhiên và giả định khung của RE2-OB, RE3-OB, RE2-TT đều đạt ngưỡng hợp lệ (48, 15, 54 ca train có trace, đều ≥ 3). Ngưỡng tính trên **số ca góp cạnh** chỉ biết được sau khi dựng khung ở phase 05.
- Tổng mỗi dòng bằng mẫu số của pool: không bản ghi nào rời mẫu số vì đường được chọn.

## 4. Kiểm cho phase 03 (`tests/test_rcl_path.py`)

1. Bảng chân trị đủ 2 × 2 × 2 tổ hợp đầu vào cho đúng một đường như mục 2.
2. Chữ ký hàm chỉ có ba tham số trên; quét import: `rcl_path.py` không import module đọc nhãn (data contract §7.7) hay client LLM.
3. Hoán vị nhãn và canary trên fixture: đường được chọn không đổi.
4. Với điều kiện `no_trace`, hàm không bao giờ trả `trace`. Nó trả `no_trace` khi arm dùng khung và khóa có khung hợp lệ, ngược lại trả `frame_free`. Câu "bộ chọn đường trả `no_trace`" trong phase 03 được đọc theo nghĩa này (xem lịch sử sửa trong [phase-03](../phase-03-thanh-phan-chung-va-tool-tat-dinh.md)).
5. Trạng thái trace `empty` cho `has_spans = false`.
