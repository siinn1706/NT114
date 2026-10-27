# Đặc tả quy tắc chọn đường (bản a02)

- Ngày: 2026-10-26 (Asia/Saigon). Bản **a02** thay [a01](path-selection-spec.md) (giữ nguyên làm lịch sử) theo quyết định của chủ dự án ngày 2026-10-26: khóa khung K2; các con số đường xử lý là dự kiến; kết quả chính trên toàn pool. Hàm chọn đường và đầu vào không đổi so với a01. Hash nằm trong receipt `01-a02-hash-01`.
- Cơ sở: D3, D11, [phụ lục a02](data-contract-addendum-im1-a02.md), [arm-ids-a02.csv](arm-ids-a02.csv).
- Hiện thực ở phase 03 (`src/rca/rcl_path.py`) phải khớp đặc tả này. Thay đổi sau khi chốt là phiên bản mới có hash mới, ghi trước mọi đánh giá.

## 1. Đầu vào (chỉ những trường này)

| Đầu vào | Nguồn | Ghi chú |
|---|---|---|
| `has_spans` | Bảng trace của ca **sau khi áp điều kiện** (`no_trace` bỏ toàn bộ trace), đọc qua vùng visible | `true` khi có ít nhất một span có `span_id` và `service_id` khác rỗng, và `service_id` thuộc danh sách ứng viên của ca. Trạng thái `natural_absent` và `empty` cho `false` |
| `has_metrics`, `has_logs` | Bảng metric và log của ca sau khi áp điều kiện | Không đổi đường; chỉ quyết tool nào chạy trong đường đã chọn |
| `uses_frame` | Thuộc tính của arm | `false` với `l0`, `ra`; `true` với `ra_im1`, `ra_im1_shuf` |
| `frame_valid`, `frame_sha256` | Tệp khung đã đóng băng của khóa `(dataset, dataset_subset, system, split)` | Khóa không có khung hợp lệ (ít hơn 3 ca train góp cạnh): `frame_valid = false` |

Không đầu vào nào là nhãn, gốc, loại lỗi, đáp án, đầu ra model, điểm hay chất lượng đầu ra.

## 2. Hàm

```text
select_path(has_spans, uses_frame, frame_valid) -> "trace" | "no_trace" | "frame_free"
    if has_spans:                      return "trace"
    if uses_frame and frame_valid:     return "no_trace"
    return "frame_free"
```

- `trace`: phân rã theo đồ thị trace; tool metric, log và trace tất định; một lời gọi tổng hợp.
- `no_trace`: không có span. Tool metric và log chạy theo khung: thứ tự và láng giềng lấy từ cạnh của khung, giới hạn trong danh sách ứng viên của ca. Một lời gọi tổng hợp; tool trace không được gọi.
- `frame_free`: không có span và không dùng khung. Bằng chứng phẳng theo từng ứng viên từ tool metric và log; một lời gọi tổng hợp; tool trace không được gọi.
- Ca thiếu cả metric lẫn log vẫn có đường. Trong pool H1 trường hợp này không xảy ra (data contract §5). Ngoài pool, ca như vậy được ghi `not_applicable`, không bị bỏ khỏi bảng.
- Mỗi bản ghi kết quả mang `arm`, `path` và (nếu có) `frame_sha256`.

## 3. Đường **dự kiến** trên pool H1 (chưa phải độ phủ thật)

Đếm theo membership không nhãn (receipt `02-h1-membership-04`) và số ca train **có trace** theo khóa K2: RE2-OB 48, RE3-OB 15, RE2-TT 54, RE3-TT 0, sock-shop 0. Số ca train có trace chưa chứng minh đủ số ca **góp cạnh**; phase 05 dựng khung và kiểm ngưỡng thật. Khóa không đạt ngưỡng đi `frame_free`, và độ phủ thật được báo thay cho bảng này. Ngưỡng không được chỉnh cho khớp số dự kiến.

| Vai | Arm | `trace` | `no_trace` (tối đa) | `frame_free` (tối thiểu) | Tổng |
|---|---|---:|---:|---:|---:|
| test | `ra` | 138 | 0 | 147 | 285 |
| test | `ra_im1`, `ra_im1_shuf` | 138 | 39 | 108 | 285 |
| val | `ra` | 108 | 0 | 102 | 210 |
| val | `ra_im1`, `ra_im1_shuf` | 108 | 54 | 48 | 210 |

- `no_trace` của arm có khung trên test: RE2-OB 21 và RE2-TT 18 bản ghi điều kiện `no_trace`. RE3-TT (30) và mọi bản ghi sock-shop đi `frame_free`.
- Tổng mỗi dòng bằng mẫu số của pool: không bản ghi nào rời mẫu số vì đường được chọn.

## 4. Báo cáo

- Kết quả chính của mỗi arm tính trên **toàn pool đã khai báo** (test 108 injection / 285 bản ghi), gồm cả bản ghi `frame_free`.
- Phân tích trên nhóm có khung hợp lệ là thăm dò và báo riêng; không thay kết quả toàn pool. IM1 không được mô tả là bao phủ toàn bộ H1.

## 5. Kiểm cho phase 03 (`tests/test_rcl_path.py`)

1. Bảng chân trị đủ 2 × 2 × 2 tổ hợp đầu vào, mỗi tổ hợp cho đúng một đường như mục 2.
2. Chữ ký hàm chỉ có ba tham số trên. Quét import: `rcl_path.py` không import module đọc nhãn hay client LLM.
3. Hoán vị nhãn và canary trên fixture không đổi đường được chọn.
4. Với điều kiện `no_trace`, hàm không bao giờ trả `trace`: trả `no_trace` khi arm dùng khung và khóa có khung hợp lệ, ngược lại trả `frame_free`.
5. Trạng thái trace `empty` cho `has_spans = false`.
