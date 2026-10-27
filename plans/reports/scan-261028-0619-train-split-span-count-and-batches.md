# Đếm span tập train và chia lô Kaggle — 2026-10-28

**Kết luận:** 240 trace train chạy được với cấu hình v11 hiện tại, chia thành 5 lô, mỗi lô một phiên Kaggle. Tổng ước lượng khoảng 37 giờ T4, mỗi lô 6,1–7,9 giờ, phương án chậm nhất 7,6–9,9 giờ. Trace lớn nhất của tập train có 45 span, và chính là trace pilot v11 đã passed trong 870 giây. Nhờ vậy:

- Không trace nào dự kiến chạm deadline 1.800 giây.
- Prompt không vượt context 16.384.
- Rủi ro lớn nhất là trần 160 request ở 12 trace từ 40 span trở lên. Trace 45 span chỉ còn dư 24 request so với mức tối thiểu.

Chỉ chạy CPU, không gọi model, không đổi dữ liệu hay split, không đổi thiết lập đóng băng.

## 1. Tập train

Nguồn: `work/tool-response-scan/tool-response-scan.csv`, tức bản quét span của mọi trace lỗi, chạy trên code gốc của tác giả.

- **Quy mô:** 240 trace thuộc 48 case, tổng 6.533 span. Mỗi trace từ 4 đến 45 span, trung vị 25.
- **Phân bố:** 143 trace có đúng 23 hoặc 25 span. Có 12 trace từ 40 span trở lên: một trace 40 span, tám trace 41 span, hai trace 43 span và một trace 45 span.
- **Trace lớn nhất:** quy tắc chọn pilot lấy trace lớn nhất trước tiên (`PILOT_RULE` trong `kaggle/prepare-bundle.py`). Vì thế trace 45 span `2095688a…` vừa là trace lớn nhất tập train, vừa là trace pilot.

## 2. Mô hình chi phí, dựa trên pilot v11

**Số request.** Code gốc cần tối thiểu `3 × span + 1` request: mỗi span một lần self-state, một vòng tool và một lần consolidate, cộng một lần tổng hợp cuối. Bản quét lưu con số này ở cột `min_requests_one_tool_round`. Thực tế model thỉnh thoảng gọi thêm vòng tool.

**Công thức khớp trên 5 trace v11:**

- `requests ≈ 2,46 + 1,037 × min_requests`
- `thời gian ≈ requests × 6,17 giây`, với 6,17 giây là trung bình mỗi request ở v11.
- Mỗi phiên cộng thêm 480 giây chuẩn bị: cài môi trường, tải model, khởi động server và kiểm protocol. Ở pilot, phần này mất khoảng 461 giây.

| Trace | Span | Tối thiểu | Thực tế v11 | Ước lượng |
|---|---:|---:|---:|---:|
| `2095688a…` | 45 | 136 | 145 | 143,5 |
| `f6526e73…` | 33 | 100 | 105 | 106,2 |
| `1e527c6a…` | 25 | 76 | 81 | 81,3 |
| `c6033940…` | 23 | 70 | 74 | 75,0 |
| `3753f2a8…` | 4 | 13 | 17 | 15,9 |

Version 10 chạy chunked, khác cấu hình, nên em không dùng nó để khớp thời gian. Nhưng số request của nó gần như trùng v11, lệch tối đa 2 request mỗi trace.

## 3. Ba giới hạn đóng băng

- **Deadline 1.800 giây:** trace chậm nhất ước lượng 886 giây. Kể cả nhân 1,25 cho phương án chậm, vẫn không trace nào vượt 80% deadline.
- **Context 16.384:**
  - *Request tổng hợp* là prompt dài nhất. Độ dài của nó tăng gần tuyến tính theo số span, và đạt 8.445 token ở trace 45 span. Không trace train nào lớn hơn 45 span.
  - *Request self-state:* kết quả `search_logs` bị giới hạn 2.048 token mỗi vòng, còn kết quả metric tối đa 10 token. Bản quét budget cho thấy prompt self-state vòng 1 của tập train tối đa 1.472 token với service của chính span, và 1.697 token với service bất kỳ. Cộng thêm 3 vòng tool, mỗi vòng tối đa khoảng 2.160 token, prompt vẫn dưới khoảng 8.200 token.
  - Cả hai loại đều còn xa mức 15.360 token, tức 16.384 trừ phần 1.024 dành cho output.
- **Trần 160 request, tính cả retry:** đây là giới hạn sát nhất.
  - 12 trace từ 40 span trở lên chỉ dư dưới 40 request so với mức tối thiểu.
  - Trace 45 span dư 24 request, mà pilot đã dùng hết 9.
  - Nếu một lượt sample khiến model gọi thêm nhiều vòng tool, trace đó sẽ bị ghi failed, không chạy lại. Đây là hành vi đã đóng băng.

## 4. Các lô

Script `kaggle/plan-train-batches.py` ghi kết quả ra `kaggle/train-batches.json`, gồm mô hình, từng trace và từng lô.

- Toàn bộ trace của một case luôn nằm chung một lô.
- Các case được xếp xen kẽ theo service bị lỗi, nên mỗi lô trải trên nhiều service.
- Một lô được chốt khi phương án chậm của nó, tức ước lượng nhân 1,25, sắp vượt 10 giờ. Kaggle cho mỗi phiên tối đa 12 giờ.

| Lô | Trace | Case | Span | Ước lượng | Phương án chậm |
|---:|---:|---:|---:|---:|---:|
| 1 | 45 | 9 | 1.355 | 7,63 giờ | 9,54 giờ |
| 2 | 50 | 10 | 1.400 | 7,90 giờ | 9,88 giờ |
| 3 | 50 | 10 | 1.356 | 7,67 giờ | 9,58 giờ |
| 4 | 50 | 10 | 1.355 | 7,66 giờ | 9,58 giờ |
| 5 | 45 | 9 | 1.067 | 6,09 giờ | 7,62 giờ |
| Tổng | 240 | 48 | 6.533 | 36,96 giờ | |

- **Kích thước dữ liệu:** mỗi trace chiếm khoảng 5,5 MB dữ liệu chưa nén. Một lô 50 trace vào khoảng 275 MB chưa nén, khoảng 25 MB sau khi nén, theo tỉ lệ của gói pilot (2,4 MB cho 5 trace).
- **Chạy tiếp khi bị ngắt:** harness đã có sẵn. Mỗi lô là một bundle riêng. Nếu phiên bị ngắt, chỉ cần gắn kết quả dở dang làm input để chạy tiếp (`progress.json` của bundle đó).
- **Lệch loại lỗi:** lô 1–3 có cả 5 service. Lô 4–5 lệch về lỗi mem và socket, vì số case của mỗi service không bằng nhau. Nếu chỉ chạy xong một phần, kết quả sẽ không đều giữa các loại lỗi.

## 5. Quota Kaggle (chưa xác minh)

Em chưa kiểm quota của tài khoản. Nếu quota là 30 giờ GPU mỗi tuần như thường thấy, tuần đầu chạy được 3 lô (khoảng 23 giờ) và tuần sau chạy nốt 2 lô. Sếp xem quota thật ở trang cài đặt Kaggle.

## Hạn chế

- Mô hình khớp trên 5 trace của một lượt chạy. Hệ số 1,25 là phần dư ước chừng, không phải khoảng tin cậy.
- Thời gian dựng gói 50 trace trên CPU chưa đo. Bước này gồm cắt dữ liệu và so endpoint với dữ liệu đầy đủ; gói 5 trace của pilot chưa cho số liệu này.
- `train-batches.json` chỉ là kế hoạch. `prepare-bundle.py` chưa đọc file này để dựng gói theo lô.

## Câu hỏi còn mở

1. Có dùng lại kết quả v11 cho 5 trace pilot không? Cùng code và cấu hình thì bỏ 5 trace này đi tiết kiệm khoảng 45 phút. Script đã có cờ `--exclude-pilot` cho việc này. Nhưng như vậy 5 trace sẽ thuộc một bundle khác với phần còn lại.
2. Sếp có duyệt dựng gói lô 1 (45 trace, 9 case) trên CPU, rồi chạy trên Kaggle ở chế độ private không?
3. Có commit `plan-train-batches.py` và `train-batches.json` không?
