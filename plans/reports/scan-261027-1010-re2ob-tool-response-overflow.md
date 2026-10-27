# Quét CPU kích thước phản hồi tool RCLAgent trên 90 ca RE2-OB — 2026-10-27

**Kết luận:** giữ nguyên ràng buộc (context 16.384, không truncate), cả 450 error trace của 90 ca đều có thể overflow ngay vòng tool đầu tiên, nhưng chỉ khi model hỏi `cartservice`. Ngoài ra chỉ có một ca (`recommendationservice_loss_1`) overflow khi hỏi `frontend`. Các query đúng chỉ dẫn của prompt tác giả (service và timestamp của chính span) không bao giờ overflow: lớn nhất 1.714 token. Context 32.768 cũng không giải quyết: query `cartservice` cần 45.232–135.618 token.

Không gọi model, không GPU, không đổi upstream, dữ liệu hoặc split. Không đọc nhãn hay kết quả.

## Cách đo

Script [re2ob-tool-response-scan.py](../261026-1713-rclagent-tai-hien-toi-thieu/work/scripts/re2ob-tool-response-scan.py) chạy code tác giả không sửa:

- Thân endpoint của `tool_server.py` trên dữ liệu preprocess đầy đủ. Mỗi phản hồi metric/log chỉ phụ thuộc (service, giây query) và các dòng trong ±1.200/±60 giây, nên được tính trên lát thời gian chính xác của dữ liệu đầy đủ. Xuống dòng chuẩn hóa về LF như trên Kaggle.
- `coordinator.build_trace_graph` và `DedicatedAgent.self_state_verification` thật; chỉ `chat_api` được thay bằng một model giả. Model giả gọi đúng hai tool prompt yêu cầu cho chính span, rồi script lấy prompt vòng 1 và đếm bằng chat template Qwen3-4B-Instruct-2507 đúng revision `cdbee75`, giống guard Kaggle.
- Góc nhìn thứ hai, không phụ thuộc model: lấy prompt rẻ nhất của trace cộng cặp phản hồi lớn nhất cho mọi service model có thể nêu (12 service trong system prompt cộng service của span) tại mọi giây của span.
- Overflow khi prompt + 512 token output > context.

Kiểm chứng:
- Prompt vòng 1 của root span trace smoke là 1.024 token, đúng số vLLM báo trong Kaggle version 5 và 6.
- Phản hồi log `cartservice` 272.734 byte, khớp native.
- Ước lượng cộng dồn token khớp chat template tuyệt đối trên 200 mẫu (sai số 0).
- Hai lượt quét độc lập cho cùng giá trị trên mọi cột chung.

Phạm vi: 450 trace, 12.605 span đi được từ root, 0 span con chéo trace. Mỗi trace được gán đúng một ca theo cửa sổ chọn của preprocess tác giả (inject − 60 s đến inject + 300 s). Vai lấy từ bảng ánh xạ theo `source_incident_key`.

## Kết quả

| Vai | Ca | Trace | Overflow khi query đúng chỉ dẫn | Có thể overflow (16.384) | Có thể overflow (32.768) |
|---|---:|---:|---:|---:|---:|
| train | 48 | 240 | 0 | 240 | 240 |
| val | 21 | 105 | 0 | 105 | 105 |
| test | 21 | 105 | 0 | 105 | 105 |
| Tổng | 90 | 450 | 0 | 450 | 450 |

Token lớn nhất ở vòng 1 theo service được hỏi:

| Service | Token tối đa | Số trace overflow ở 16.384 |
|---|---:|---:|
| cartservice | 135.618 | 450 |
| frontend | 35.982 | 5 (cả 5 trace của `recommendationservice_loss_1`, train) |
| productcatalogservice | 1.697 | 0 |
| checkoutservice | 1.666 | 0 |
| redis | 1.420 | 0 |
| Các service còn lại | ≤ 1.185 | 0 |

- Query `cartservice` cần ít nhất 45.232 token, trung vị 123.515. Nguyên nhân: `cartservice` ghi log `severity: unknown` (ví dụ `GetCartAsync called with userId=…`) với mật độ cao, nên không bị lọc INFO/DEBUG.
- `cartservice` không bao giờ là service của span trong trace RE2-OB; span chỉ thuộc frontendservice, productcatalogservice, currencyservice, checkoutservice, recommendationservice, paymentservice, emailservice. Model chỉ hỏi `cartservice` khi tự chọn từ danh sách trong system prompt, như ở cả hai lượt native của trace smoke. Hai lượt này cùng prompt và seed, nên không phải hai quan sát độc lập.
- Query đúng chỉ dẫn cho span frontend (5.514/12.605 span) luôn rỗng: trace ghi `frontendservice`, còn metric/log ghi `frontend`. Đây là semantics preprocess của tác giả và được giữ nguyên.
- Ngân sách requests: với đúng một vòng tool mỗi span, trace dài nhất (45 span) cần 136 requests ≤ 160. Không trace nào vượt trần chỉ vì số span; thêm vòng tool hoặc retry sẽ làm tăng số này.

## Giới hạn

- Đây là cận dưới của kích thước prompt: chỉ đo vòng tool đầu của self-state. Vòng sau, consolidation và synthesis cộng thêm token và phụ thuộc output model; chưa đo được trên CPU.
- "Có thể overflow" không phải tỷ lệ overflow thực tế. Nó cho biết trong mọi trace đều có ít nhất một query hợp lệ theo tác giả gây overflow; tần suất model thực sự chọn query đó chỉ biết khi chạy model.

## Hệ quả cho pilot val

Với ràng buộc hiện tại, mọi trace val đều có cùng "bẫy" như trace smoke. Một lượt pilot sẽ dừng ở bất kỳ trace nào mà model hỏi `cartservice`; bằng chứng duy nhất hiện có (trace smoke) là model đã hỏi ở request thứ hai. Tăng context lên 32.768 không đổi bảng trên. Vì vậy pilot val vẫn chưa đủ điều kiện nếu không có quyết định phương pháp về tool result lớn.

Artifact: [tool-response-scan.csv](../261026-1713-rclagent-tai-hien-toi-thieu/work/tool-response-scan/tool-response-scan.csv) (SHA256 `879cf8aa…bdcf`), [tool-response-scan.json](../261026-1713-rclagent-tai-hien-toi-thieu/work/tool-response-scan/tool-response-scan.json) (SHA256 `3c8c9373…0405`), chi tiết từng span trong `work/tool-response-scan/spans/`. Log: `work/logs/tool-response-scan-02.log` và `-04.log`; lượt 01 lỗi cú pháp và lượt 03 không khởi động được (lỗi đổi tên thư mục), log của cả hai được giữ. Môi trường: `kaggle/runtime/scan-env` = pin của `harness-requirements.txt` cộng transformers 4.55.4, tokenizers 0.21.4, huggingface-hub 0.34.4 (cùng bản phía Kaggle).

## Câu hỏi còn mở

Các hướng ở report trước vẫn còn, với dữ kiện mới:

1. Giữ nguyên và chạy pilot val để đo tỷ lệ model hỏi `cartservice`. Kỳ vọng nhiều trace dừng vì overflow; kết quả sẽ là thống kê thất bại, không phải accuracy.
2. Tăng context: cần khoảng 136.130 token (135.618 + 512) để mọi query vòng 1 hợp lệ; ngoài khả năng của T4.
3. Ngân sách tool result áp dụng đồng nhất (cắt hoặc gộp dòng trùng), báo như sai lệch so với tác giả. Bảng trên cho thấy chỉ `cartservice` và một trường hợp `frontend` chạm ngưỡng, nên tác động tập trung, nhưng vẫn đổi semantics.
4. Đổi backbone có context dài hơn.
