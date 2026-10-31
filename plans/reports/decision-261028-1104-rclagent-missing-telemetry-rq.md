# Chốt câu hỏi nghiên cứu cho lượt chạy RCLAgent tiếp theo — 2026-10-28

**Kết luận:** chủ dự án chọn câu hỏi về thiếu telemetry (phương án A). Sampling giữ temperature 0,7 như cấu hình gốc, mỗi điều kiện lặp 3 lần để đo nhiễu. Kế hoạch 240 trace train (khoảng 37 giờ T4) tạm gác. Lượt chạy tới là một thí nghiệm nhỏ có đối chứng, chỉ dùng để quyết định hướng này có đáng mở rộng. Kết quả của nó không dùng để tuyên bố hiệu quả chung.

## 1. Câu hỏi

Khi một nguồn telemetry (log hoặc metric) vắng mặt:

- **(a)** R@1 và MRR của RCLAgent giảm bao nhiêu so với khi đủ nguồn, trên cùng các case?
- **(b)** Bằng chứng mất ở bước nào: kết quả tool, self-state của từng span, bước gộp đệ quy, hay bước tổng hợp cuối?
- **(c)** Một thay đổi X có thu hẹp mức giảm không? X chỉ được chốt sau khi phân tích 5 trace pilot và có điều kiện đủ nguồn để làm mốc so.

## 2. Căn cứ trong code tác giả

Code ở commit `3052e7a`, các file `tool_server.py` và `coordinator.py`.

- Bước self-state của mỗi span chỉ có hai tool là `search_logs` và `search_fluctuating_metrics` (`coordinator.py:239`). Trace là khung duyệt của phương pháp, nên không có điều kiện bỏ trace.
- Prompt self-state yêu cầu gọi cả hai tool (`coordinator.py:211-215`) và trả về hai cờ `has_error_logs` và `has_metric_anomaly` (`coordinator.py:229-230`). Hai cờ này cho đo câu (b) ở cấp span mà không phải đọc văn bản tự do.
- Prompt xếp log lỗi là dấu hiệu số 1 và metric dao động là số 2 (`coordinator.py:172-174`). Vì vậy dự đoán trước là bỏ log sẽ làm giảm nhiều hơn bỏ metric. Thí nghiệm có thể bác dự đoán này.

## 3. Thiết kế đề xuất

Các điểm dưới đây là đề xuất, chưa được duyệt.

- **Cách tạo thiếu telemetry.** Giữ nguyên tool và prompt. Chỉ tool server của harness trả về kết quả rỗng hợp lệ cho nguồn bị bỏ. Nếu gỡ tool khỏi danh sách thì prompt vẫn đòi gọi tool đó, và điều kiện sẽ lẫn với lỗi gọi tool.
- **Điều kiện.** Gồm `full`, `no_log`, `no_metric`, cộng `no_* + X` sau khi chốt X.
- **Đơn vị.** Mỗi case train lấy một error trace, chọn trước theo một quy tắc cố định, khác 5 trace pilot và phân tầng theo loại lỗi. So từng case theo cặp giữa các điều kiện.
- **Nhiễu.** Lặp 3 lần với 3 seed khác nhau. Không lặp bằng cùng một seed: pilot v9 và v10 cho câu trả lời trùng byte khi cùng cấu hình, nên 3 lần cùng seed không đo được gì.
- **Nhiễu lẫn với guard.** Điều kiện `full` cũng đang rút gọn một số kết quả `search_logs` (9 lần ở v11). Phân tích (b) phải ghi riêng các span có kết quả bị rút gọn.
- **Ngưỡng mở rộng.** Đặt trước khi chạy: mức chênh R@1 giữa điều kiện bao nhiêu, vượt dao động giữa các seed bao nhiêu thì mới mở rộng.

## 4. Ngân sách: sửa lại ước lượng 6–8 giờ

Ước lượng 6–8 giờ em đưa trong lúc hỏi là thiếu, vì chưa nhân đủ số lần lặp. Tính lại theo pilot v11, trung bình khoảng 520 giây mỗi trace, xấp xỉ 8–9 phút với trace khoảng 25 span:

| Phương án | Số lượt chạy trace | Ước giờ T4 |
|---|---:|---:|
| 8 case × 3 điều kiện (`full`, `no_log`, `no_metric`) × 3 seed, rồi 8 × 2 điều kiện `+X` × 3 seed | 72 + 48 = 120 | khoảng 16–18 |
| Chỉ bỏ nguồn mà bước 1 cho thấy quan trọng: 8 × 2 × 3, rồi 8 × 1 `+X` × 3 | 48 + 24 = 72 | khoảng 10–11 |
| Như dòng 2 nhưng chọn trace ngắn, không quá 20 span | 72 | khoảng 7–8 |

Mỗi phương án đều rẻ hơn 37 giờ và chia vừa 1–2 phiên Kaggle. Chọn trace ngắn thì tiết kiệm, nhưng kết luận khi đó chỉ đúng cho trace ngắn.

## 5. Thứ tự việc

1. Phân tích 5 trace pilot v9–v11 trên CPU, không GPU, theo các nhóm nguyên nhân: harness rút gọn hoặc guard, thiếu bằng chứng đầu vào, tool trả tín hiệu yếu, model diễn giải sai, mất ở bước gộp hoặc tổng hợp.
2. Chốt X, quy tắc chọn case, ngân sách và ngưỡng mở rộng.
3. Thêm chế độ thiếu nguồn vào tool server của harness, có test CPU. Không sửa source upstream.
4. Chạy trên Kaggle ở chế độ private, chấm theo cặp, ghi report.

## Câu hỏi còn mở

1. Chọn phương án ngân sách nào trong bảng mục 4? Nên chốt sau bước 1.
2. Có chấp nhận cách tạo thiếu telemetry bằng kết quả rỗng ở tool server như mục 3 không?
3. Ngưỡng mở rộng cụ thể là bao nhiêu?
