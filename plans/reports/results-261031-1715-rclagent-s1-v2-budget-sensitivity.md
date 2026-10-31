# Kết quả kiểm độ nhạy ngân sách S1 v2 của thí nghiệm thiếu nguồn — 2026-10-31

**Tóm tắt.**
- **S1 v2 là một lần kiểm độ nhạy, không thay kết luận pilot đã nhận.** Cấu hình S1 chỉ nâng ba giới hạn của harness so với vòng 2: trần vòng tool mỗi span từ 4 lên 8, trần request mỗi lượt từ 160 lên 320, trần thời gian mỗi lượt từ 1.800 s (30 phút) lên 2.400 s (40 phút). Kết luận pilot ngày 2026-10-29 vẫn tính trên vòng 2.
- **Cả 8 lượt từng chạm trần ở vòng 2 đều chạy xong và pass ở S1.** Tổng số lượt lỗi giảm từ 10/72 xuống 2/72. Hai lượt còn lỗi đều là gói B, lỗi giao thức, và đã hỏng ở cả hai vòng với cùng lý do.
- **Các lượt không chạm trần cho điểm giống vòng 2.** Cả 64 cặp không chạm trần có R@1, MRR và top-1 bằng nhau (50 cặp đầu ra model giống hệt, 14 cặp chỉ khác response cuối). 8 lượt từng chạm trần có đầu ra vòng 2 là tiền tố đúng của đầu ra S1. Không có điểm nào thay đổi ngoài 8 lượt này.
- **Bỏ metric vẫn giảm ở S1, nhỏ hơn vòng 2.** Gộp A+B: ΔR@1 −0,208 (vòng 2: −0,250), ΔMRR −0,203 (vòng 2: −0,321), giảm ở 3/3 seed, 4 case bị ảnh hưởng và giảm (vòng 2: 5). Phần chênh giữa hai vòng chỉ nằm ở 8 lượt từng chạm trần. Đây là kiểm độ nhạy trên 8 case, không phải ước lượng độ chính xác.
- **Bỏ log giữ nguyên kết quả vòng 2:** ΔR@1 0,000 và ΔMRR +0,055, giảm ở 1/3 seed. Chưa đạt tiêu chí mở hướng.
- **Một quan sát phụ về độ lặp lại.** 20 cặp không chạm trần khác nhau ở request cuối cùng (prompt tổng hợp), nơi danh sách service có bất thường metric được liệt kê theo thứ tự khác nhau. Điểm không đổi ở cả 20 cặp. Mục 6, mục 8 và câu hỏi mở nêu hướng xử lý.

Mọi đường dẫn tính từ `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`. Số liệu lấy từ `runtime/analysis-missing-source-{a,b,ab}-s1-v2/`, `runtime/analysis-missing-source-completion-s1-v2/`, `runtime/analysis-missing-source-r2-vs-s1-v2/` và các thư mục tương ứng của vòng 2 (`-r2-v1`, `-ab-r2`, `-completion-r2`). Phân tích các lượt dừng vì trần ở vòng 2 nằm ở [analysis-261029-1629](analysis-261029-1629-rclagent-round-2-budget-stops.md); kết quả vòng 2 ở [results-261029-1448](results-261029-1448-rclagent-missing-source-round-2.md).

## 1. Chạy gì, ở đâu, do ai

| Gói | Kernel | Bundle | ZIP kết quả | Thời gian | Lượt |
|---|---|---|---|---|---|
| A | `svuittri/rclagent-missing-source-a-s1-gpu-261030` | `024e877a…e41e` | `7514fce2…0a24` | 25.387 s (khoảng 7,05 giờ) | 36 pass |
| B | `svuittri/rclagent-missing-source-b-s1-gpu-261030` | `a076518f…74a9` | `3d4b6d22…5f24` | 16.135 s (khoảng 4,48 giờ) | 34 pass, 2 lỗi |

- **Tài khoản chạy:** `svuittri`, chạy kernel GPU T4 trên hai dataset `siinn1706/rclagent-missing-source-{a,b}-s1-261029` (phiên bản 2). Output do `siinn1706` tải về bằng `kaggle kernels output` vào `runtime/kaggle-output-{a,b}-s1-v2/`. Thư mục `*-s1-v1` không bị ghi đè.
- **Kiểm nguồn gốc:** SHA256 mỗi ZIP khớp file `.sha256`. SHA256 bundle khớp bản S1 v2 đã commit. Manifest `1e0f3150…20d9` (A) và `702b89de…9121` (B) có `all_member_hashes_verified` bằng true. Cell của cả hai notebook trên Kaggle bằng cell của notebook S1 v2 đã commit. Giới hạn ghi trong manifest là 8 / 320 / 2.400 s ở cả hai gói. Mọi mục này nằm ở [`runtime/kaggle-provenance-s1-v2.json`](../261026-1713-rclagent-tai-hien-toi-thieu/kaggle/runtime/kaggle-provenance-s1-v2.json).
- **Quyền riêng tư:** theo API, cả hai kernel và cả hai dataset đều `is_private: true`. Kernel đọc được bằng `kaggle kernels pull -m` từ tài khoản `siinn1706`. Dataset kiểm bằng `KaggleApi.dataset_list(mine=True)`. Chi tiết ở [`runtime/kaggle-private-status-s1-v2.json`](../261026-1713-rclagent-tai-hien-toi-thieu/kaggle/runtime/kaggle-private-status-s1-v2.json).
- **Thời gian chạy so với ước tính.** Ước tính trong [analysis-261029-1629](analysis-261029-1629-rclagent-round-2-budget-stops.md) mục 4 là khoảng 7,5–8 giờ mỗi gói. Thực tế A mất 7,05 giờ và B mất 4,48 giờ. Vòng 2 mất 24.171 s (A) và 26.408 s (B). Chưa tìm nguyên nhân B chạy nhanh hơn rõ rệt ở S1.
- **Chấm:** cùng analyzer và cùng quy tắc với vòng 2. Cả ba phạm vi (A, B, A+B) có `evaluable: true` và `missing_pairs` rỗng. Không có lỗi toàn vẹn nào, và không tên top-1 nào mang hậu tố `-N`.

## 2. Tỷ lệ hoàn tất hợp lệ, vòng 2 cạnh S1

Một lượt hoàn tất hợp lệ phải pass, có điểm và sạch toàn vẹn. Số liệu lấy từ `completion.csv` của hai thư mục `analysis-missing-source-completion-{r2,s1-v2}`.

| Phạm vi | Điều kiện | Tổng | Hoàn tất hợp lệ, vòng 2 | Hoàn tất hợp lệ, S1 | Tỷ lệ, vòng 2 | Tỷ lệ, S1 | Lý do hỏng ở S1 |
|---|---|---|---|---|---|---|---|
| A | `metric` | 12 | 12 | 12 | 1,000 | 1,000 | Không |
| A | `no_metric` | 12 | 6 | 12 | 0,500 | 1,000 | Không |
| A | `metric_no_log` | 12 | 12 | 12 | 1,000 | 1,000 | Không |
| B | `metric` | 12 | 11 | 11 | 0,917 | 0,917 | 1 JSON agent thiếu hoặc sai span id |
| B | `no_metric` | 12 | 9 | 11 | 0,750 | 0,917 | 1 tool call sai (structured response sai kiểu) |
| B | `metric_no_log` | 12 | 12 | 12 | 1,000 | 1,000 | Không |
| A+B | `metric` | 24 | 23 | 23 | 0,958 | 0,958 | 1 JSON agent sai |
| A+B | `no_metric` | 24 | 15 | 23 | 0,625 | 0,958 | 1 tool call sai |
| A+B | `metric_no_log` | 24 | 24 | 24 | 1,000 | 1,000 | Không |

- Ở S1 không còn lượt nào dừng vì trần vòng tool, hết request hay hết trần thời gian. Cột "trần 4 vòng tool" (5 lượt) và "hết 160 request" (3 lượt) của vòng 2 đều về 0. Không có lượt thiếu điểm hay lỗi toàn vẹn.
- Ở vòng 2 có 10 lượt lỗi (A 6, B 4); ở S1 có 2 lượt lỗi (A 0, B 2).

## 3. R@1 và MRR

### 3.1 Toàn bộ lượt (lượt lỗi tính 0)

| Phạm vi | Điều kiện | R@1, vòng 2 | R@1, S1 | MRR, vòng 2 | MRR, S1 |
|---|---|---|---|---|---|
| A | `metric` | 0,417 | 0,417 | 0,512 | 0,512 |
| A | `no_metric` | 0,083 | 0,167 | 0,122 | 0,323 |
| A | `metric_no_log` | 0,417 | 0,417 | 0,574 | 0,574 |
| B | `metric` | 0,417 | 0,417 | 0,580 | 0,580 |
| B | `no_metric` | 0,250 | 0,250 | 0,328 | 0,363 |
| B | `metric_no_log` | 0,417 | 0,417 | 0,626 | 0,626 |
| A+B | `metric` | 0,417 | 0,417 | 0,546 | 0,546 |
| A+B | `no_metric` | 0,167 | 0,208 | 0,225 | 0,343 |
| A+B | `metric_no_log` | 0,417 | 0,417 | 0,600 | 0,600 |

R@3 gộp A+B: `no_metric` 0,208 ở vòng 2 và 0,375 ở S1; `metric` và `metric_no_log` giữ 0,583 và 0,708 (`summary.json` của `analysis-missing-source-ab-{r2,s1-v2}`). Hai điều kiện `metric` và `metric_no_log` không đổi ở bất kỳ chỉ số nào giữa hai vòng, đúng với việc không lượt nào của chúng chạm trần.

### 3.2 Chỉ trên các lượt hoàn tất hợp lệ

Mỗi điều kiện tính trên một tập lượt khác nhau, nên đây là mô tả, không phải phép so sánh giữa các điều kiện.

| Phạm vi | Điều kiện | n, vòng 2 | R@1, vòng 2 | MRR, vòng 2 | n, S1 | R@1, S1 | MRR, S1 |
|---|---|---|---|---|---|---|---|
| A | `no_metric` | 6 | 0,167 | 0,243 | 12 | 0,167 | 0,323 |
| B | `no_metric` | 9 | 0,333 | 0,438 | 11 | 0,273 | 0,396 |
| A+B | `metric` | 23 | 0,435 | 0,570 | 23 | 0,435 | 0,570 |
| A+B | `no_metric` | 15 | 0,267 | 0,360 | 23 | 0,217 | 0,358 |
| A+B | `metric_no_log` | 24 | 0,417 | 0,600 | 24 | 0,417 | 0,600 |

Trên các lượt hoàn tất hợp lệ, MRR của `no_metric` gần như không đổi (0,360 và 0,358), còn R@1 thấp hơn (0,267 và 0,217) vì 8 lượt mới hoàn tất có R@1 thấp (xem mục 5). Các điều kiện `metric` và `metric_no_log` của A và B không có dòng riêng vì không có lượt lỗi hay lượt chạm trần, nên số liệu giống bảng ở mục 3.1.

### 3.3 Sàng lọc theo quy tắc mục 6.3 của `analysis-261028-1104`

Lượt lỗi tính 0, so `metric` với điều kiện bị bỏ nguồn.

| So sánh | Phạm vi | Cấu hình | ΔR@1 | ΔMRR | Seed giảm | Case bị ảnh hưởng, giảm | Kết luận |
|---|---|---|---|---|---|---|---|
| Bỏ metric | A | Vòng 2 | −0,333 | −0,390 | 3/3 | 2 | Đạt |
| Bỏ metric | A | S1 | −0,250 | −0,189 | 3/3 | 2 | Đạt |
| Bỏ metric | B | Vòng 2 | −0,167 | −0,252 | 3/3 | 3 | Đạt |
| Bỏ metric | B | S1 | −0,167 | −0,217 | 3/3 | 2 | Đạt |
| Bỏ metric | A+B | Vòng 2 | −0,250 | −0,321 | 3/3 | 5 | Đạt |
| Bỏ metric | A+B | S1 | −0,208 | −0,203 | 3/3 | 4 | Đạt |
| Bỏ log | A+B | Vòng 2 | 0,000 | +0,055 | 1/3 | 1 | Không đạt |
| Bỏ log | A+B | S1 | 0,000 | +0,055 | 1/3 | 1 | Không đạt |

Bỏ log ở A và B riêng lẻ cũng giữ nguyên: A ΔR@1 0,000, ΔMRR +0,062; B ΔR@1 0,000, ΔMRR +0,047, ở cả hai vòng.

**Bỏ metric, gộp A+B, tách theo seed** (ΔR@1; ΔMRR):

| Seed | Vòng 2 | S1 |
|---|---|---|
| 20261026 | −0,250; −0,333 | −0,250; −0,255 |
| 20261027 | −0,125; −0,170 | −0,125; −0,128 |
| 20261028 | −0,375; −0,460 | −0,250; −0,226 |

**Bỏ metric, theo case, trên toàn bộ lượt** (ΔR@1; ΔMRR):

| Case | Gói | Vòng 2 | S1 |
|---|---|---|---|
| `checkoutservice_mem_1` | A | −1,000; −1,000 | −0,667; −0,389 |
| `currencyservice_loss_3` | A | −0,333; −0,389 | −0,333; −0,278 |
| `emailservice_delay_3` | A | 0,000; −0,089 | 0,000; −0,006 |
| `checkoutservice_cpu_1` | A | 0,000; −0,083 | 0,000; −0,083 |
| `recommendationservice_socket_1` | B | −1,000; −0,861 | −1,000; −0,778 |
| `recommendationservice_cpu_2` | B | 0,000; −0,111 | 0,000; −0,056 |
| `emailservice_delay_1` | B | 0,000; −0,368 | 0,000; −0,368 |
| `currencyservice_disk_3` | B | +0,333; +0,333 | +0,333; +0,333 |

Case chỉ khác nhau giữa hai vòng ở các case có lượt từng chạm trần (`checkoutservice_mem_1`, `currencyservice_loss_3`, `emailservice_delay_3`, `recommendationservice_cpu_2`, `recommendationservice_socket_1`). Case `currencyservice_disk_3` vẫn "tăng" ở cả hai vòng vì lượt `metric` seed 20261027 lỗi và tính 0; đó là hiệu ứng của một lượt lỗi, không phải bằng chứng bỏ metric có lợi. Ở S1, `recommendationservice_cpu_2` không còn bị tính là case bị ảnh hưởng, vì lượt `no_metric` seed 20261028 đã có điểm.

## 4. Cặp mà cả hai lượt đều hoàn tất (kiểm độ nhạy)

Cách ghép và cách gộp như mục 6 của [results-261029-1448](results-261029-1448-rclagent-missing-source-round-2.md). Số liệu lấy từ `pairs.json` trong hai thư mục `analysis-missing-source-completion-{r2,s1-v2}`.

| So sánh | Phạm vi | Cặp ghép được | Cặp đều hoàn tất, vòng 2 | Cặp đều hoàn tất, S1 | ΔR@1 trung bình cặp, S1 | ΔMRR trung bình cặp, S1 | ΔR@1 trung bình case, S1 | ΔMRR trung bình case, S1 |
|---|---|---|---|---|---|---|---|---|
| Bỏ metric | A | 12 | 6 | 12 | −0,250 | −0,189 | −0,250 | −0,189 |
| Bỏ metric | B | 12 | 8 | 10 | −0,300 | −0,344 | −0,250 | −0,286 |
| Bỏ metric | A+B | 24 | 14 | 22 | −0,273 | −0,259 | −0,250 | −0,238 |
| Bỏ log | A | 12 | 12 | 12 | 0,000 | +0,062 | 0,000 | +0,063 |
| Bỏ log | B | 12 | 11 | 11 | 0,000 | +0,005 | 0,000 | +0,005 |
| Bỏ log | A+B | 24 | 23 | 23 | 0,000 | +0,035 | 0,000 | +0,034 |

Với phép bỏ metric gộp A+B, vòng 2 cho ΔR@1 −0,143 và ΔMRR −0,222 trên 14 cặp (trung bình cặp). Ở S1, 14 cặp đó có điểm y hệt, và có thêm 8 cặp mới (8 lượt `no_metric` từng chạm trần). Tám cặp mới này có ΔR@1 trung bình −0,500 và ΔMRR trung bình −0,325, tính từ `runs.csv` của `analysis-missing-source-{a,b}-s1-v2` (trong 8 cặp này, 5/8 lượt `metric` đối ứng có R@1 bằng 1, so với 1/8 lượt `no_metric`). Vì vậy mức giảm trên cặp hoàn tất lớn hơn ở S1 so với vòng 2 (R@1: −0,273 ở S1 so với −0,143 ở vòng 2). Đây là hệ quả của việc 8 cặp khó nhất trước đây bị loại khỏi mẫu, đúng với cảnh báo thiên lệch chọn mẫu ở vòng 2. Đây không phải thay đổi của cùng một tập cặp.

## 5. Tám lượt từng chạm trần ở vòng 2

Tất cả đều là `no_metric`. "Vòng tool" của một span là số lời gọi `self_state_verification` có kèm kết quả tool trong hội thoại của span đó. Cột "span bị dừng" chỉ có ý nghĩa với 5 lượt dừng vì trần vòng tool ở vòng 2; ba lượt hết request dừng khi đang ở bước `consolidate`, không span nào chạm trần vòng tool. Số vòng tính từ `run/traces/<run_id>/events.jsonl` trong ZIP S1, bằng cùng hàm `run_profile` của `analyze-completion-and-budget-stops.py`. Thời gian chạy của 8 lượt ở S1 từ 482 s đến 1.125 s, không lượt nào gần trần thời gian 2.400 s. Khoảng này đo từ mốc thời gian của event đầu đến event cuối trong `events.jsonl`.

| Case (gói), run, seed | Lý do dừng ở vòng 2 | Request, vòng 2 | Trạng thái S1 | Request, S1 | Vòng tool của span từng bị dừng, S1 | Vòng tool lớn nhất của một span bất kỳ, S1 | R@1, S1 | MRR, S1 |
|---|---|---|---|---|---|---|---|---|
| `emailservice_delay_3` (A), `30e3c732…`, 26 | Trần 4 vòng tool | 10 | pass | 106 | 5 | 5 | 0,000 | 0,125 |
| `emailservice_delay_3` (A), `30e3c732…`, 28 | Trần 4 vòng tool | 10 | pass | 107 | 7 | 7 | 0,000 | 0,125 |
| `currencyservice_loss_3` (A), `99f095ae…`, 28 | Trần 4 vòng tool | 12 | pass | 109 | 6 | 6 | 0,000 | 0,333 |
| `recommendationservice_socket_1` (B), `7bbfa606…`, 28 | Trần 4 vòng tool | 26 | pass | 111 | 5 | 5 | 0,000 | 0,250 |
| `recommendationservice_cpu_2` (B), `272a47c2…`, 28 | Trần 4 vòng tool | 12 | pass | 110 | 8 | 8 | 0,000 | 0,167 |
| `checkoutservice_mem_1` (A), `5f7a7727…`, 26 | Hết 160 request | 160 | pass | 172 | không áp dụng | 4 | 0,000 | 0,500 |
| `checkoutservice_mem_1` (A), `5f7a7727…`, 27 | Hết 160 request | 160 | pass | 168 | không áp dụng | 4 | 0,000 | 0,333 |
| `checkoutservice_mem_1` (A), `5f7a7727…`, 28 | Hết 160 request | 160 | pass | 170 | không áp dụng | 4 | 1,000 | 1,000 |

Nguồn: lý do dừng và số request vòng 2 từ `runtime/analysis-missing-source-completion-r2/budget-stops.json`; trạng thái, số request và điểm S1 từ `runs.csv` (số request S1 trùng với số tính lại từ log).

**Dữ kiện quan sát được.**
- **Năm lượt dừng vì trần vòng tool:** ở S1 span từng bị dừng dùng 5, 5, 6, 7 và 8 vòng tool rồi kết luận. Cả 5 vượt trần cũ 4. Không lượt nào dùng vượt trần mới 8. Lượt `272a47c2…--no_metric--s20261028` dùng đúng 8 vòng, lời gọi thứ 9 không kèm tool call nên pass; nếu span này cần thêm một vòng thì lượt đã dừng ở trần mới.
- **Ba lượt hết request:** tổng request ở S1 là 172, 168 và 170, bằng đúng mức "request cần tối thiểu" đã ước tính ở vòng 2 (172, 168, 170; [analysis-261029-1629](analysis-261029-1629-rclagent-round-2-budget-stops.md) mục 3). Không span nào dùng quá 4 vòng tool, nên trần mỗi span không ràng buộc ở ba lượt này; chỉ trần request quyết định.
- **Điểm của 8 lượt:** 1/8 lượt có R@1 bằng 1 (`checkoutservice_mem_1` seed 28). MRR trung bình của 8 lượt là 0,354, R@1 trung bình là 0,125. Các điểm này mô tả, không dùng để suy ra khả năng chẩn đoán của điều kiện `no_metric`.
- **Hoàn tất không có nghĩa là đúng.** Khi được chạy tiếp, 8 lượt đều hoàn tất, nhưng 7/8 lượt vẫn có top-1 sai (R@1 bằng 0).

## 6. Kiểm điều kiện: lượt không chạm trần phải giống vòng 2

Phương pháp nằm trong docstring của `compare-run-outputs.py` (13 test trong `test-compare-run-outputs.py` pass). Các lượt ghép theo `(trace_id, condition, seed)`. "Đầu ra model" là nội dung và tool call của các response theo thứ tự log, bỏ id ngẫu nhiên, thời gian và usage. Output ở `runtime/analysis-missing-source-r2-vs-s1-v2/` (`pairs.csv`, `summary.json`). Cả 72 lượt ghép được, không lượt nào chỉ có một phía.

| Nhóm | Số cặp | Giống hệt | Chỉ khác response cuối | Tiền tố đúng của S1 | Điểm bằng nhau | Trạng thái ở hai vòng |
|---|---|---|---|---|---|---|
| Không chạm trần, gói A | 30 | 25 | 5 | 0 | 30/30 | 30 lượt pass ở cả hai vòng |
| Không chạm trần, gói B | 34 | 25 | 9 | 0 | 34/34 | 32 lượt pass ở cả hai vòng, 2 lượt lỗi ở cả hai vòng |
| Không chạm trần, A+B | 64 | 50 | 14 | 0 | 64/64 | 62 lượt pass ở cả hai vòng, 2 lượt lỗi ở cả hai vòng |
| Chạm trần ở vòng 2, A+B | 8 | 0 | 0 | 8 | 0/8 | 8 lượt lỗi ở vòng 2 và pass ở S1 |

- **64 cặp không chạm trần:** số request bằng nhau ở cả 64 cặp, và R@1, MRR, top-1 đều bằng nhau.
- **Khác biệt duy nhất ở 20 cặp:** số request bằng nhau nhưng nội dung request khác nhau ở 20 cặp (14 cặp response cuối cũng khác, 6 cặp response vẫn giống hệt). Ở cả 20 cặp, request đầu tiên khác nhau chính là request cuối cùng của lượt, tức prompt tổng hợp. Ở prompt đó, dòng "Services with metric anomalies only" liệt kê cùng một nhóm service theo thứ tự khác nhau. Ví dụ, lượt `5f7a7727…--metric--s20261026` có "frontendservice, checkoutservice" ở vòng 2 và "checkoutservice, frontendservice" ở S1; hai prompt cùng độ dài và cùng bộ ký tự. Hai prompt chỉ khác nhau ở thứ tự liệt kê, nên khác biệt này không đến từ việc đổi trần. Nguyên nhân thứ tự đổi có thể là việc lặp trên một tập không có thứ tự ở upstream, nhưng chưa đọc mã để xác nhận, xem mục 8.
- **Phân bố theo điều kiện của 20 cặp:** 11 cặp `metric` và 9 cặp `metric_no_log`; gói A có 6 cặp, gói B có 14 cặp. Không cặp `no_metric` không chạm trần nào có khác biệt.
- **8 lượt chạm trần:** đầu ra vòng 2 là tiền tố đúng của đầu ra S1. Nói cách khác, cho đến điểm vòng 2 dừng, model sinh đúng cùng nội dung như ở S1, rồi S1 chạy tiếp.
- **Điều không kết luận được:** các điểm khác nhau giữa hai vòng chỉ xuất hiện ở 8 lượt này. Chúng được tạo ra bởi việc lượt được chạy tiếp, không phải bằng chứng cho bất kỳ tác động nào khác của việc đổi trần. Chưa có phép thử riêng tách tác động của từng giới hạn (vòng tool, request, thời gian).

## 7. Hai lượt B hỏng ở cả hai vòng

| Run | Điều kiện, seed | Lý do ở vòng 2 | Lý do ở S1 | Request, vòng 2 và S1 |
|---|---|---|---|---|
| `272a47c2…` (`recommendationservice_cpu_2`) | `no_metric`, 20261026 | `malformed_tool_call` | `malformed_tool_call` | 20 và 20 |
| `ad1c27da…` (`currencyservice_disk_3`) | `metric`, 20261027 | `agent_output` (thiếu span id) | `agent_output` (thiếu span id) | 11 và 11 |

Cả hai lượt giống nhau về lý do ở hai vòng và về số request. Đó là lỗi giao thức lặp lại (tool call hoặc structured response sai ở lượt đầu, hoặc agent không trả span id), không phải do trần: không lượt nào chạm trần ở vòng 2 và cả hai đều dừng sớm. Hai lượt này nằm trong 64 cặp không chạm trần ở mục 6 (dòng gói B và dòng A+B, cột trạng thái, ghi 2 lượt lỗi ở cả hai vòng).

## 8. Giới hạn

- **n nhỏ.** 8 case train, 3 seed, 3 điều kiện, 72 lượt mỗi vòng. Seed lặp trên cùng một case không phải mẫu độc lập; vì vậy các số theo case ở mục 3.3 và 4 quan trọng hơn số theo lượt.
- **Tính tất định của vLLM không được đảm bảo.** Ở 64 cặp không chạm trần, 50 cặp có đầu ra model giống hệt và 14 cặp chỉ khác response cuối; sự khớp này không phải bảo đảm cho lần chạy sau. Với 8 lượt chạm trần, việc đầu ra vòng 2 là tiền tố của S1 cũng chỉ là quan sát, không phải bảo đảm.
- **S1 là kiểm độ nhạy, không phải ước lượng độ chính xác.** Các số ở đây cho biết kết luận pilot đổi như thế nào khi nới ba giới hạn, trên đúng 8 case này. Chúng không phải ước lượng hiệu quả chung của hệ thống khi thiếu metric.
- **Lượt lỗi tính 0.** R@1/MRR trên toàn bộ lượt đo hiệu quả của toàn pipeline dưới ngân sách đã đặt. Dưới S1 ngân sách rộng hơn, nên con số này cao hơn ở `no_metric`. Cả hai cách đọc (toàn bộ lượt và lượt hoàn tất hợp lệ) đều được trình bày để thấy cả hai phía.
- **Thiên lệch chọn mẫu ở các cặp hoàn tất.** Số cặp đều hoàn tất khác nhau giữa hai vòng (14 và 22), nên mức giảm trên cặp hoàn tất không so trực tiếp được giữa hai vòng.
- **Ba giới hạn đổi cùng lúc.** S1 đổi đồng thời vòng tool, request và thời gian. Không thể quy phần khác biệt cho riêng giới hạn nào. Với ba lượt hết request, chỉ có trần request ràng buộc (mục 5). Với 5 lượt còn lại, trần vòng tool ràng buộc.
- **Nguyên nhân thứ tự khác nhau ở prompt tổng hợp** được xác định qua một cặp mẫu (cùng độ dài, cùng bộ ký tự, hoán vị tên service) và việc cả 20 cặp khác nhau đều chỉ khác ở request cuối. Chưa đọc mã upstream để xác nhận nguồn của tính không tất định, và chưa so nội dung prompt của 19 cặp còn lại.
- **S1 không thay kết luận pilot đã nhận** ngày 2026-10-29 ở mức pilot (decision log `plans/261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md`). Cả hai quyết định sau đó (cách chấm lượt lỗi tính 0 và ngân sách của cấu hình chính) vẫn có hiệu lực. Báo cáo này chỉ bổ sung bằng chứng độ nhạy.

## Câu hỏi còn mở

- **Có sửa tính không tất định về thứ tự service trong prompt tổng hợp cho các lần chạy sau không?** Hiện nó làm 20/64 cặp không chạm trần khác nhau ở request cuối, không đổi điểm, nhưng làm giảm khả năng kiểm tra "cùng đầu vào cho cùng đầu ra". Cách sửa nằm ở upstream hoặc ở lớp harness; chưa chọn. Việc này chỉ nên làm với lần chạy mới, không sửa kết quả cũ.
- **Q1–Q9 của audit vẫn chờ chủ dự án.** Báo cáo này không trả lời câu nào; mục 5–7 chỉ bổ sung dữ kiện cho Q2 (công khai các case chịu ảnh hưởng bởi trần).
- **Có merge [PR #2](https://github.com/siinn1706/NT114/pull/2) không?** Merge ngay sau khi commit báo cáo này, hay chờ quyết định Q1–Q9.
- **Hai lượt B lỗi giao thức lặp lại ở cả hai vòng** (mục 7) có cần xử lý trong harness hay chấp nhận như hiện nay? Một lượt là tool call sai sau đủ lần hỏi lại, một lượt là agent không trả span id.
- **Có chạy thêm gì để tách tác động của từng giới hạn không?** Hiện chỉ có kết quả đổi đồng thời ba giới hạn. Một lần chạy khác sẽ cần GPU và dựng gói mới.
