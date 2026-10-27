# Đo prefill prompt dài trên T4: chunked và không chunked — 2026-10-27

**Kết luận:** chunked prefill (2.048 token mỗi bước) là nguyên nhân làm request dài chậm. Khi tắt chunked prefill và để 16.384 token mỗi bước, prompt tổng hợp 8.446 token của trace 45 span chỉ mất 9,4 giây thay vì 232 giây. Prompt độn tới 13.948 token mất 13,2 giây thay vì 596 giây. Với cả 5 prompt, câu trả lời của hai cấu hình giống hệt nhau, cả nội dung lẫn lời gọi tool. Server không chunked vẫn đủ KV cache cho một request dài trọn 16.384 token. Em chưa đổi cấu hình pilot và chưa chạy lại pilot.

Phạm vi theo duyệt của sếp: một lượt Kaggle ngắn, private, chỉ đo thời gian prefill prompt dài với cấu hình vLLM hiện tại và với cấu hình không chunked prefill. Lượt này không chạy RCLAgent, tool server hay scorer. Không đổi upstream, prompt, model, sampling, dữ liệu hay split. Không commit, không push.

## 1. Cách đo

- **Prompt.** Đây là request dài nhất của mỗi trace trong pilot version 10, gửi lại nguyên văn: 1.709, 4.649, 5.411, 6.362 và 8.446 token. Bốn prompt dài là request tổng hợp cuối, có tool `print_results`. Em thêm một prompt chỉ để đo prefill: lấy prompt 8.446 token rồi độn lên 13.948 token. Không prompt nào chứa nhãn.
- **Hai chế độ gửi.** Mỗi prompt được gửi một lần nguyên văn, với sampling đóng băng và tối đa 1.024 token output. Thêm một lần với `max_tokens=1`, để thời gian đo được gần như chỉ là prefill.
- **Hai cấu hình server.** Mọi cờ khác giữ y như pilot; `test-prefill-bench.py` so trực tiếp với lệnh trong `kaggle-runtime.py`. Dòng log vLLM xác nhận chunked prefill bật hay tắt đúng như ý.
  - `chunked-2048`: `--max-num-batched-tokens 2048 --enable-chunked-prefill`, như pilot.
  - `unchunked-16384`: `--max-num-batched-tokens 16384`, bỏ `--enable-chunked-prefill`. Với `max_model_len` 16.384, vLLM 0.10.2 V0 khi đó để chunked prefill tắt.
- **Môi trường.** Notebook dùng lại nguyên các ô bootstrap, A và B của pilot, gồm môi trường cô lập, bản vá kernel T4 và model `cdbee75f`. Máy là một Tesla T4, context 16.384, `--enforce-eager`.
- **Kaggle.** Dataset là `siinn1706/rclagent-t4-prefill-bench-261027`, notebook là `siinn1706/rclagent-t4-prefill-bench-run-261027`, cả hai private. Kernel phải có slug khác dataset, vì Kaggle trả 409 khi trùng.

## 2. Kết quả

| Prompt (token) | Chunked: prefill | Chunked: nguyên văn | Không chunked: prefill | Không chunked: nguyên văn | Câu trả lời giống nhau |
|---:|---:|---:|---:|---:|---|
| 1.709 | 13,8 s | 17,9 s | 0,8 s | 5,9 s | có |
| 4.649 | 74,4 s | 78,8 s | 2,4 s | 5,2 s | có |
| 5.411 | 98,3 s | 102,4 s | 2,8 s | 5,7 s | có |
| 6.362 | 134,4 s | 138,6 s | 3,6 s | 6,9 s | có |
| 8.446 | 227,5 s | 232,0 s | 5,5 s | 9,4 s | có |
| 13.948 (độn) | 596,0 s | — | 13,2 s | — | — |

- **Chunked prefill.** Thời gian tăng nhanh hơn tuyến tính theo độ dài prompt. Các số đo khớp với pilot version 9 và 10: 78, 101 và 138 giây cho các prompt 4.649, 5.411 và 6.362 token.
  - Prompt 8.446 token cần 232 giây, nên timeout 180 giây của upstream chắc chắn bị vượt.
  - Prompt 1.709 token chỉ có một bước mà vẫn mất 13,8 giây. Vậy cả bước đầu cũng chậm, không chỉ các bước có prefix dài. Em chưa xác định đó là kernel nào.
- **Không chunked.** Prefill gần tuyến tính, khoảng 1.000–1.600 token mỗi giây.
- **Phần sinh token** tốn khoảng 3–5 giây cho khoảng 66 token, như nhau ở cả hai cấu hình.
- **Câu trả lời** trùng khớp hoàn toàn ở cả 5 request nguyên văn: cùng số completion token, cùng nội dung và cùng lời gọi tool.
- **Bộ nhớ:**

  | | Chunked | Không chunked |
  |---|---|---|
  | Activation đỉnh lúc profile | 0,16 GiB | 1,21 GiB |
  | KV cache | 4,57 GiB (2.078 block) | 3,51 GiB (1.598 block) |
  | Sức chứa | 2,03 request × 16.384 token | 1,56 request × 16.384 token |

  Pilot chỉ chạy một request mỗi lúc, nên cấu hình không chunked vẫn đủ chỗ.

## 3. Sự cố trong lúc đo

- **Lượt đầu** (kernel version 1) đo xong cấu hình chunked. Đến cấu hình không chunked thì dừng với lỗi `Address already in use`: ngay sau khi server đầu bị tắt, cổng 8000 chưa bind lại được.
- **Nguyên nhân** là script đo của em kiểm cổng đúng một lần mà không chờ.
- **Đã sửa.** `wait_port_free` chờ tối đa 300 giây và không đổi sang cổng khác. Nếu hết giờ, script ghi lại process đang giữ cổng và ghi lỗi cho cấu hình đó, không dừng cả lượt. Thêm tùy chọn `only` để chỉ đo cấu hình được chọn.
- **Lượt hai** (kernel version 2) chỉ đo cấu hình không chunked. Cổng rảnh ngay (chờ 0 giây), vì đây là phiên mới.
- **Hệ quả cho bảng ở mục 2.** Hai cấu hình được đo ở hai phiên Kaggle khác nhau, trên hai máy T4 khác nhau. Số đo chunked khớp với cả pilot version 9 và 10, nên sai lệch giữa các phiên nhỏ hơn rất nhiều so với chênh lệch giữa hai cấu hình.

## 4. Kiểm và artifact

- `test-prefill-bench.py` pass 6/6 với một server giả. Các test gồm: timeout được ghi lại mà không dừng lượt, log server không khớp cấu hình thì không đo, hết ngân sách thời gian thì bỏ qua các prompt còn lại, chờ cổng, cổng không bao giờ rảnh, và cờ server khớp với pilot. Log ở `kaggle/runtime/test-logs/prefill-bench-0{1,2,3}.log`; lần 01 đỏ vì lỗi trong chính test, đã sửa.
- Output lượt 1: `kaggle/runtime/prefill-bench/output-run1/`, ZIP SHA256 `2cc12e59…c142f`.
- Output lượt 2: `kaggle/runtime/prefill-bench/output-run2/`, ZIP SHA256 `7edd50bb…3b8f7`.
- Cả hai hash khớp file `.sha256` của Kaggle. Các server vLLM đều thoát với mã 0. Máy local không còn process nào em khởi động.
- Code mới, chưa commit: `prefill-bench.py`, `build-prefill-bench.py` và `test-prefill-bench.py`. Prompt chứa telemetry của các trace train, nên chỉ nằm trong `runtime/` (không track) và trong dataset private.

## 5. Đề xuất (chưa làm)

- **Đổi cấu hình server của pilot sang không chunked.** Trong `kaggle-runtime.py`, đặt `--max-num-batched-tokens 16384` và bỏ `--enable-chunked-prefill`; cập nhật `settings.json` cho khớp. Sau đó chạy lại các test CPU, đóng gói lại và chạy lại pilot 5 trace.
- **Lợi ích.** Prompt tổng hợp 8.446 token sẽ nằm gọn trong timeout 180 giây của upstream. E của mỗi trace cũng ngắn đi nhiều, vì mọi request dài hơn khoảng 2.000 token đều chậm. Ước lượng 73 giờ T4 cho 240 trace train cũng phải tính lại.
- **Các thiết lập đóng băng không đổi:** upstream, prompt, model, sampling, context, output, retry và các trần.
- **Phải khai báo.** Cấu hình scheduling của vLLM khác với các lượt từ version 8 đến 10. Trên 5 prompt này, câu trả lời không đổi, nhưng điều đó không bảo đảm mọi request sẽ giống byte.

## Câu hỏi còn mở

1. Sếp có duyệt đổi server của pilot sang không chunked như mục 5, kèm kiểm CPU và đóng gói lại không? Nếu có, sếp có duyệt chạy lại pilot 5 trace trên Kaggle, dataset và notebook vẫn private, không?
