# Kết quả vòng 2 thí nghiệm thiếu nguồn (có hỏi lại khi tool call lỗi) — 2026-10-29

**Tóm tắt.**
- **Cả hai gói đã chạy xong và chấm sạch.** 62/72 lượt pass; vòng 1 là 36/72. Không có lỗi toàn vẹn, và không summary nào bị đánh dấu `provisional`.
- **Hỏi lại khi tool call lỗi gần như xóa nhóm lỗi lớn nhất của vòng 1.** Ở vòng 1 có 30 lượt lỗi vì model viết tool call dạng text bị sai JSON. Ở vòng 2, 31 lượt có hỏi lại, và chỉ còn 1 lượt lỗi vì tool call sai sau đủ 3 lần hỏi lại.
- **Cách đọc điểm.** Theo quy tắc sàng lọc, lượt thất bại tính 0. Vì vậy R@1/MRR trên toàn bộ lượt đo hiệu quả của toàn pipeline dưới ngân sách đã đặt (trần 4 vòng tool mỗi span, 160 request, 30 phút). Con số này không phải độ đo riêng khả năng chẩn đoán.
- **Thiếu metric: pilot đủ để tiếp tục khảo sát hướng này.** Sếp đã nhận kết luận này ngày 2026-10-29, ở mức pilot. Gộp A+B cho ΔR@1 −0,250 và ΔMRR −0,321, giảm ở 3/3 seed, 5 case bị ảnh hưởng.
  - Mức giảm quan sát được gồm hai phần: lượt không hoàn tất được trong ngân sách, và xếp hạng tệ hơn ở các lượt đã hoàn tất. Chưa tách được phần đóng góp của từng cơ chế.
  - Tỷ lệ hoàn tất hợp lệ của `no_metric` là 15/24, so với 23/24 của `metric`. Cả 8 lượt dừng vì trần của harness đều là `no_metric`.
  - Kiểm độ nhạy trên 14 cặp mà cả hai lượt đều hoàn tất: ΔR@1 −0,143, ΔMRR −0,222. Chiều giảm này chủ yếu đến từ gói B. Trên 6 cặp của gói A, R@1 không đổi.
- **Bỏ log: chưa đạt tiêu chí mở hướng trong pilot này**, ở cả A, B và A+B. Điều này không có nghĩa là log không có tác dụng.
- **Phạm vi.** 8 case train, mô tả thăm dò, không kiểm định thống kê, không khẳng định tác động chung.
- **Phân tích các lượt dừng vì trần:** [analysis-261029-1629](analysis-261029-1629-rclagent-round-2-budget-stops.md).

Mọi đường dẫn tính từ `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`.

## 1. Chạy gì, ở đâu

| Gói | Kernel | Bundle | Thời gian | ZIP kết quả |
|---|---|---|---|---|
| A | `siinn1706/rclagent-missing-source-a-r2-gpu-261029` | `ddb43de4…9dac` | 24.171 giây | `c018dd9f…83cb` |
| B | `siinn1706/rclagent-missing-source-b-r2-gpu-261029` | `9514b919…eb0c` | 26.408 giây | `e8bb1317…b53d` |

- **Output** tải về `runtime/kaggle-output-{a,b}-r2-v1/`. SHA256 của mỗi ZIP khớp file `.sha256` đi kèm.
- **Phiên chạy:** cả hai `run/status.json` đều ghi `passed` ở stage F.
- **Chấm:** dùng analyzer đã sửa theo plan 261029-1128.
  - Analyzer xác nhận mỗi ZIP chạy đúng bundle của manifest `runtime/bundle-missing-source-{a,b}-r2/manifest.json`.
  - Output nằm ở `runtime/analysis-missing-source-{a-r2-v1,b-r2-v1,ab-r2}/`.
  - Mọi phép so sánh đều có `evaluable: true` và `missing_pairs` rỗng.

## 2. Kiểm toàn vẹn và lượt lỗi

**Kiểm toàn vẹn.** Sạch ở cả 72 lượt.
- Chuỗi hỏi lại được kiểm theo thứ tự trong log: seed, `retry_of` và số attempt đều đúng.
- `source` của mọi `tool_result` khớp với điều kiện của lượt.
- Không tên top-1 nào mang hậu tố `-N`.

**Hỏi lại.**
- A: 9 lượt, mỗi lượt 1 lần.
- B: 22 lượt, tổng 24 lần, nhiều nhất 3 lần trong một lượt.

**Lượt pass.**

| Gói | Vòng 1 | Vòng 2 |
|---|---|---|
| A | 22/36 | 30/36 |
| B | 14/36 | 32/36 |

**10 lượt còn lỗi.**

| Gói | Case | Điều kiện | Seed | Lý do | Nhóm |
|---|---|---|---|---|---|
| A | `emailservice_delay_3` | `no_metric` | 26, 28 | Vượt trần 4 vòng tool mỗi span | Trần harness |
| A | `currencyservice_loss_3` | `no_metric` | 28 | Vượt trần 4 vòng tool mỗi span | Trần harness |
| A | `checkoutservice_mem_1` | `no_metric` | 26, 27, 28 | Hết 160 request | Trần harness |
| B | `recommendationservice_socket_1` | `no_metric` | 28 | Vượt trần 4 vòng tool mỗi span | Trần harness |
| B | `recommendationservice_cpu_2` | `no_metric` | 28 | Vượt trần 4 vòng tool mỗi span | Trần harness |
| B | `recommendationservice_cpu_2` | `no_metric` | 26 | Tool call vẫn sai schema sau 3 lần hỏi lại (`'currencyservice' is not of type 'object'`) | Tool call |
| B | `currencyservice_disk_3` | `metric` | 27 | Agent trả JSON thiếu hoặc sai span id | Đầu ra agent |

8/10 lượt lỗi là `no_metric` chạm trần của harness. Chỉ 1 lượt lỗi rơi vào điều kiện tham chiếu `metric`, và lượt này làm case `currencyservice_disk_3` có vẻ "tăng" khi bỏ metric.

## 3. Điểm theo điều kiện

Lượt lỗi tính 0.

| Phạm vi | Điều kiện | R@1 | R@3 | MRR |
|---|---|---|---|---|
| A | `metric` | 0,417 | 0,500 | 0,512 |
| A | `no_metric` | 0,083 | 0,167 | 0,122 |
| A | `metric_no_log` | 0,417 | 0,667 | 0,574 |
| B | `metric` | 0,417 | 0,667 | 0,580 |
| B | `no_metric` | 0,250 | 0,250 | 0,328 |
| B | `metric_no_log` | 0,417 | 0,750 | 0,626 |
| A+B | `metric` | 0,417 | 0,583 | 0,546 |
| A+B | `no_metric` | 0,167 | 0,208 | 0,225 |
| A+B | `metric_no_log` | 0,417 | 0,708 | 0,600 |

## 4. Sàng lọc

Quy tắc ở mục 6.3 của `analysis-261028-1104`. Lượt lỗi tính 0.

| So sánh | Phạm vi | ΔR@1 | ΔMRR | Seed giảm | Case bị ảnh hưởng, giảm | Kết luận |
|---|---|---|---|---|---|---|
| Bỏ metric | A | −0,333 | −0,390 | 3/3 | 2 | Đạt |
| Bỏ metric | B | −0,167 | −0,252 | 3/3 | 3 | Đạt |
| Bỏ metric | A+B | −0,250 | −0,321 | 3/3 | 5 | Đạt |
| Bỏ log | A | 0,000 | +0,063 | 1/3 | 1 | Không đạt |
| Bỏ log | B | 0,000 | +0,047 | 1/3 | 0 | Không đạt |
| Bỏ log | A+B | 0,000 | +0,055 | 1/3 | 1 | Không đạt |

**Bỏ metric, gộp A+B, tách theo seed** (ΔR@1, ΔMRR):
- seed 26: −0,250 và −0,333;
- seed 27: −0,125 và −0,170;
- seed 28: −0,375 và −0,460.

**Bỏ metric, gộp A+B, các case bị ảnh hưởng và giảm:**

| Case | ΔR@1 | ΔMRR |
|---|---|---|
| `checkoutservice_mem_1` | −1,0 | −1,0 |
| `recommendationservice_socket_1` | −1,0 | −0,861 |
| `currencyservice_loss_3` | −0,333 | −0,389 |
| `emailservice_delay_1` | 0 | −0,368 |
| `recommendationservice_cpu_2` | 0 | −0,111 |

Riêng `currencyservice_disk_3` tăng (+0,333; +0,333), vì lượt `metric` ở seed 27 bị lỗi và tính 0.

Các số ở mục 3 và 4 là hiệu quả của toàn pipeline dưới ngân sách đã đặt. Chúng là kết quả chính và giữ nguyên. Mục 5–7 bổ sung để thấy phần nào đến từ việc không hoàn tất được, phần nào đến từ xếp hạng. Các mục này không thay kết quả chính.

## 5. Hoàn tất trong ngân sách

Số liệu tính bằng `analyze-completion-and-budget-stops.py`. Output nằm ở `runtime/analysis-missing-source-completion-r2/` (`completion.csv`, `pairs.json`, `cases.json`, `budget-stops.json`). Script đọc ZIP qua `load()` của analyzer, nên áp dụng cùng các kiểm SHA256, bundle và khóa trùng.

Một lượt hoàn tất hợp lệ phải pass, có điểm và sạch toàn vẹn. Lượt thiếu điểm và lượt có lỗi toàn vẹn được đếm ở cột riêng; ở vòng 2 cả hai cột đều bằng 0.

| Phạm vi | Điều kiện | Tổng lượt | Hoàn tất hợp lệ | Tỷ lệ | Trần 4 vòng tool | Hết 160 request | Tool call sai sau 3 lần hỏi lại | JSON agent sai | Thiếu điểm | Lỗi toàn vẹn |
|---|---|---|---|---|---|---|---|---|---|---|
| A | `metric` | 12 | 12 | 1,000 | 0 | 0 | 0 | 0 | 0 | 0 |
| A | `no_metric` | 12 | 6 | 0,500 | 3 | 3 | 0 | 0 | 0 | 0 |
| A | `metric_no_log` | 12 | 12 | 1,000 | 0 | 0 | 0 | 0 | 0 | 0 |
| B | `metric` | 12 | 11 | 0,917 | 0 | 0 | 0 | 1 | 0 | 0 |
| B | `no_metric` | 12 | 9 | 0,750 | 2 | 0 | 1 | 0 | 0 | 0 |
| B | `metric_no_log` | 12 | 12 | 1,000 | 0 | 0 | 0 | 0 | 0 | 0 |
| A+B | `metric` | 24 | 23 | 0,958 | 0 | 0 | 0 | 1 | 0 | 0 |
| A+B | `no_metric` | 24 | 15 | 0,625 | 5 | 3 | 1 | 0 | 0 | 0 |
| A+B | `metric_no_log` | 24 | 24 | 1,000 | 0 | 0 | 0 | 0 | 0 | 0 |

Không lượt nào dừng vì deadline 30 phút.

**R@1/MRR trên các lượt hoàn tất hợp lệ.** Mỗi điều kiện được tính trên một tập lượt khác nhau, nên đây là mô tả, không phải phép so sánh giữa các điều kiện.

| Phạm vi | Điều kiện | n | R@1 | MRR | R@1 toàn bộ lượt | MRR toàn bộ lượt |
|---|---|---|---|---|---|---|
| A | `metric` | 12 | 0,417 | 0,512 | 0,417 | 0,512 |
| A | `no_metric` | 6 | 0,167 | 0,243 | 0,083 | 0,122 |
| A | `metric_no_log` | 12 | 0,417 | 0,574 | 0,417 | 0,574 |
| B | `metric` | 11 | 0,455 | 0,633 | 0,417 | 0,580 |
| B | `no_metric` | 9 | 0,333 | 0,438 | 0,250 | 0,328 |
| B | `metric_no_log` | 12 | 0,417 | 0,626 | 0,417 | 0,626 |
| A+B | `metric` | 23 | 0,435 | 0,570 | 0,417 | 0,546 |
| A+B | `no_metric` | 15 | 0,267 | 0,360 | 0,167 | 0,225 |
| A+B | `metric_no_log` | 24 | 0,417 | 0,600 | 0,417 | 0,600 |

## 6. Cặp mà cả hai lượt đều hoàn tất (kiểm độ nhạy)

Một cặp gồm hai lượt cùng case, cùng trace và cùng seed, một lượt ở điều kiện tham chiếu `metric` và một lượt ở điều kiện bị bỏ nguồn. Chỉ giữ cặp mà cả hai lượt đều hoàn tất hợp lệ.

**Cách gộp.**
- "Trung bình cặp" lấy trung bình trên mọi cặp.
- "Trung bình case" lấy trung bình các seed trong từng case trước, rồi lấy trung bình giữa các case. Cách này để seed lặp không được tính như case độc lập.
- Lọc theo trạng thái hoàn tất có thể gây thiên lệch chọn mẫu: các lượt bị loại là những lượt khó nhất của điều kiện thiếu nguồn. Vì vậy phần này chỉ là kiểm độ nhạy và không thay kết quả trên toàn bộ lượt.

| So sánh | Phạm vi | Cặp ghép được | Cặp đều hoàn tất | Case | ΔR@1 trung bình cặp | ΔMRR trung bình cặp | ΔR@1 trung bình case | ΔMRR trung bình case |
|---|---|---|---|---|---|---|---|---|
| Bỏ metric | A | 12 | 6 | 3 | 0,000 | −0,069 | 0,000 | −0,056 |
| Bỏ metric | B | 12 | 8 | 4 | −0,250 | −0,336 | −0,250 | −0,290 |
| Bỏ metric | A+B | 24 | 14 | 7 | −0,143 | −0,222 | −0,143 | −0,189 |
| Bỏ log | A | 12 | 12 | 4 | 0,000 | +0,062 | 0,000 | +0,063 |
| Bỏ log | B | 12 | 11 | 4 | 0,000 | +0,005 | 0,000 | +0,005 |
| Bỏ log | A+B | 24 | 23 | 8 | 0,000 | +0,035 | 0,000 | +0,034 |

## 7. Theo case: mất điểm vì trần hay giảm ở các cặp hoàn tất (bỏ metric)

| Case | Gói | Δ toàn bộ lượt (R@1; MRR) | Lượt `no_metric` thất bại | Cặp đều hoàn tất | Δ trên các cặp đó (R@1; MRR) |
|---|---|---|---|---|---|
| `checkoutservice_mem_1` | A | −1,000; −1,000 | s26, s27, s28: hết 160 request | 0 | — |
| `emailservice_delay_3` | A | 0,000; −0,089 | s26, s28: trần 4 vòng tool | 1 | 0,000; 0,000 |
| `currencyservice_loss_3` | A | −0,333; −0,389 | s28: trần 4 vòng tool | 2 | 0,000; −0,083 |
| `checkoutservice_cpu_1` | A | 0,000; −0,083 | không | 3 | 0,000; −0,083 |
| `recommendationservice_socket_1` | B | −1,000; −0,861 | s28: trần 4 vòng tool | 2 | −1,000; −0,792 |
| `recommendationservice_cpu_2` | B | 0,000; −0,111 | s26: tool call sai sau 3 lần hỏi lại; s28: trần 4 vòng tool | 1 | 0,000; 0,000 |
| `emailservice_delay_1` | B | 0,000; −0,368 | không | 3 | 0,000; −0,368 |
| `currencyservice_disk_3` | B | +0,333; +0,333 | không (lượt `metric` s27 lỗi JSON agent) | 2 | 0,000; 0,000 |

**Dữ kiện quan sát được.**
- **Mất điểm hoàn toàn vì trần:** `checkoutservice_mem_1`. Cả 3 lượt `no_metric` hết request, nên không còn cặp nào để so.
- **Phần mất điểm trên toàn bộ lượt đến từ các lượt chạm trần:** `emailservice_delay_3` và `recommendationservice_cpu_2`. Trên các cặp còn lại, Δ bằng 0.
- **Vẫn giảm trên các cặp hoàn tất:**
  - R@1 giảm ở `recommendationservice_socket_1`.
  - MRR giảm ở `recommendationservice_socket_1`, `emailservice_delay_1`, `currencyservice_loss_3` và `checkoutservice_cpu_1`.

**Diễn giải.** Khi thiếu metric, xuất hiện cả hai cơ chế: không hoàn tất được trong ngân sách, và xếp hạng tệ hơn khi đã hoàn tất. Mỗi cơ chế chỉ dựa trên vài case, nên chưa đo được phần đóng góp của từng cơ chế. Cơ chế của các lượt chạm trần được phân tích riêng trong [analysis-261029-1629](analysis-261029-1629-rclagent-round-2-budget-stops.md).

**Bỏ log.** Trên toàn bộ lượt cũng như trên 23 cặp đều hoàn tất, R@1 không đổi, MRR tăng nhẹ. Pilot này chưa đạt tiêu chí mở hướng cho log. Kết quả này không cho phép kết luận log không có tác dụng: theo `analysis-261028-1104`, chỉ 3/48 case train có bằng chứng log ở service được gán nhãn.

## Câu hỏi còn mở

- ~~Có nhận kết luận "bỏ metric đạt" ở vòng 2 để mở hướng nghiên cứu thiếu nguồn metric không?~~ Sếp đã nhận ngày 2026-10-29, ở mức pilot. Đã ghi vào decision log (`plans/261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md`).
- **Q2 của audit hỏi việc công khai.** Báo cáo có nêu rõ các case chịu ảnh hưởng bởi trần, kèm phân tích độ nhạy, không? Mục 5–7 và báo cáo `analysis-261029-1629` đã làm việc này. Hai quyết định tiếp theo, ghi riêng trong decision log ngày 2026-10-29, là: giữ cách chấm (lượt thất bại tính 0) và giữ ngân sách hiện tại cho cấu hình chính.
- **Có chạy cấu hình kiểm độ nhạy ở mục 4 của `analysis-261029-1629` không?** Cấu hình gồm trần 8 vòng tool mỗi span, 320 request, deadline 2.400 s, cùng 72 lượt. Chi phí khoảng 15–16 giờ GPU T4, và phải dựng gói mới.
