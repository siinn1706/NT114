# Kết quả chạy Kaggle thí nghiệm thiếu nguồn metric — 2026-10-29

**Tóm tắt.** Cả hai gói đều đã chạy xong: 36/72 lượt pass, kiểm toàn vẹn sạch.
- **Bỏ metric: đạt.** Theo quy tắc sàng lọc ở mục 6.3, gộp A+B cho R@1 giảm 0,167 và MRR giảm 0,215, giảm ở 3/3 seed và có 4 case bị ảnh hưởng. Khi chỉ xét các cặp mà cả hai lượt đều pass, chiều giảm vẫn giữ.
- **Bỏ log: không đạt.**
- **Điểm yếu lớn nhất.** 30 lượt lỗi vì model viết tool call dạng text bị sai JSON, tất cả ở seed 20261027 và 20261028; harness dừng lượt theo đúng thiết kế. Ngoài ra có 1 lượt lỗi schema và 5 lượt `no_metric` lỗi vì chạm trần ngân sách tool hoặc request của harness.
- Cần sếp quyết cách xử lý lỗi tool call (mục 3) trước khi chạy thêm.

Nguồn: report phân tích `analysis-261028-1104-rclagent-pilot-trace-failure-analysis.md` (mục 6.3), bàn giao `handoff-261028-1322-rclagent-missing-source-kaggle-bundles.md`. Mọi đường dẫn dưới đây tính từ `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`.

## 1. Chạy gì, ở đâu

| Gói | Kernel | Dataset | Trạng thái |
|---|---|---|---|
| A | `siinn1706/rclagent-one-trace-gpu-smoke-261026` v13 | `siinn1706/rclagent-one-trace-smoke-261026` v14 | COMPLETE, 17.559 giây |
| B | `siinn1706/rclagent-missing-source-b-gpu-261028` v1 | `siinn1706/rclagent-missing-source-b-261028` v1 | COMPLETE, 8.606 giây |

- **Lần chạy A trước bị lỗi.** Notebook A v12 lỗi ở stage B (`Expanded Kaggle manifest SHA256 mismatch`). Kernel khởi động 13 giây sau khi file của dataset v14 được tạo, nên Kaggle gắn phiên bản dataset cũ. Em đẩy lại notebook không đổi thành v13. Từ lần này, trước khi đẩy kernel em đợi dataset báo `ready` và tải manifest về đối chiếu.
- **B chạy song song.** B dùng dataset và kernel riêng, kiểm private qua API. Manifest tải từ Kaggle về khớp `74b55383…`.
- **Kết quả B.** Nằm ở `runtime/kaggle-output-b-v1/`. sha256 của ZIP kết quả là `b948dcdd…17d7`, khớp file `.sha256`.
- **Chấm.** Dùng `analyze-missing-source-results.py`. Output nằm ở `runtime/analysis-missing-source-b-v1/` (`runs.csv`, `summary.json`).

## 2. Gói B

**Kiểm toàn vẹn.** Pass hết ở các lượt có event. Seed của mọi request trong phase trace khớp với seed của lượt, `source` của mọi `tool_result` khớp với điều kiện, và không có tên top-1 nào mang hậu tố `-N`.

**Lượt hợp lệ theo seed.**

| Seed | Lượt pass | Ghi chú |
|---|---|---|
| 20261026 | 11/12 | `272a47c2` / `no_metric` lỗi ở request 17 (`'currencyservice' is not of type 'object'`) |
| 20261027 | 3/12 | chỉ `emailservice_delay_1` pass |
| 20261028 | 0/12 | |

**Điểm theo điều kiện** (lượt thất bại tính 0, mỗi điều kiện 12 lượt):

| Điều kiện | R@1 | R@3 | MRR |
|---|---|---|---|
| `metric` | 0,167 | 0,333 | 0,264 |
| `no_metric` | 0,083 | 0,083 | 0,121 |
| `metric_no_log` | 0,167 | 0,333 | 0,271 |

**Sàng lọc theo mục 6.3.**
- **Bỏ metric** (`metric` → `no_metric`):
  - R@1 giảm 0,083, dưới ngưỡng 0,125. MRR giảm 0,143, vượt ngưỡng 0,10.
  - Giảm ở 2/3 seed và có 2 case bị ảnh hưởng. Hai case đó là `recommendationservice_socket_1` (R@1 giảm 1/3, MRR giảm 0,28) và `emailservice_delay_1` (MRR giảm 0,24).
  - Quy tắc **đạt**.
- **Bỏ log** (`metric` → `metric_no_log`): không đổi, quy tắc không đạt.
- **Vì sao kết quả đạt còn yếu:**
  - Seed 20261028 không có lượt nào hợp lệ.
  - Seed 20261027 chỉ có 1 case hợp lệ, và tính "giảm" ở seed này chỉ đến từ case đó.
  - Thay đổi rõ nhất là `recommendationservice_socket_1` ở seed 20261026. Có metric thì top-1 đúng; không có metric thì top-1 là `cartservice`.
  - Khi một lượt đã pass, kết quả ít phụ thuộc seed: `emailservice_delay_1` cho cùng top-1 ở seed 26 và 27, trong cả 3 điều kiện.

**Mốc CPU** (thứ hạng service đúng, lấy từ `metric-dev-rank.csv`; ô trống nghĩa là service đúng không có trong trace):

| Trace | Case | Đếm span | Lệch metric (trong trace) |
|---|---|---|---|
| `ad1c27da` | currencyservice_disk_3 | 1 | 1 |
| `7bbfa606` | recommendationservice_socket_1 | 3 | 1 |
| `272a47c2` | recommendationservice_cpu_2 | trống | trống |
| `29583dc6` | emailservice_delay_1 | 5 | 1 |

Xếp theo độ lệch metric trên CPU đặt service đúng ở hạng 1 trong 3/3 trace có service đó. LLM ở điều kiện `metric` chỉ đúng top-1 ở 2/4 case khi seed là 20261026.

## 3. Lỗi tool call ở seed 20261027/20261028 — cần sếp quyết

- **Hiện tượng.**
  - Cả 21 lượt lỗi đều dừng ở request thứ 2, là bước self-state đầu tiên ngay sau hai kết quả tool đầu.
  - Model trả về 4 đến 6 khối `<tool_call>` dạng text, trong đó có một khối sai JSON, ví dụ `"arguments", "service_name": …` thay cho `"arguments": {…}`.
  - Parser hermes của vLLM không tách được và trả `tool_calls: []`.
  - `validate_calls` trong `smoke-worker.py` cố ý từ chối cú pháp tool rò ra dạng text (`Server failed to emit structured tool_calls`), nên lượt bị dừng. Đây là chính sách có chủ đích: không trích tool call từ text.
- **Vì sao gần như cố định theo seed.** Mỗi request mang seed cố định. Prompt ở request 2 rất giống nhau giữa các trace và các điều kiện, vì đến lúc đó chỉ có kết quả rỗng hoặc "No matching records". Cùng seed nên sampling rơi vào cùng chỗ hỏng. Retry với cùng seed sẽ lặp lại đúng output đó.
- **Lựa chọn** (em chưa làm, vì việc này đổi giao thức):
  1. Giữ giao thức và báo như hiện tại: seed 27/28 gần như toàn 0, kết luận rất yếu.
  2. Đổi bộ seed, ví dụ thử trước trên CPU hoặc Kaggle xem seed nào qua được request 2, rồi chạy lại. Cách này rẻ nhưng là chọn seed sau khi đã thấy lỗi.
  3. Khi gặp tool call sai định dạng, retry request đó với một seed con suy ra cố định từ (seed lượt, số thứ tự request, số lần thử), giới hạn 3 lần, và ghi lại mỗi lần. Cách này giữ được tính tái lập và không trích từ text. Em nghiêng về cách này, nhưng nó đổi harness, nên phải test lại và chạy lại cả A lẫn B, mất khoảng 2 đến 3 giờ GPU mỗi gói.
  4. Tắt parallel tool calls hoặc ép mỗi lượt một tool call. Cách này lệch khỏi hành vi của tác giả, nên em không khuyến nghị.

## 4. Gói A và gộp A+B

**Gói A.** Kernel v13 COMPLETE sau 17.559 giây; 22/36 lượt pass, không lượt nào chạy lại. sha256 của ZIP kết quả là `65601034…2954`, khớp file `.sha256`. Kết quả nằm ở `runtime/kaggle-output-v13/`, phần chấm ở `runtime/analysis-missing-source-a-v13/`, còn phần gộp A+B ở `runtime/analysis-missing-source-ab/`. Kiểm toàn vẹn sạch: seed và source khớp, không có hậu tố `-N`.

**Lỗi ở A khác B ở một điểm.** Ngoài lỗi tool call sai định dạng (9 lượt, rơi vào seed 27/28 của `checkoutservice_cpu_1` và seed 28 của `checkoutservice_mem_1`), còn 5 lượt lỗi vì chạm trần ngân sách. Cả 5 lượt đều thuộc `no_metric`: 3 lượt vượt quá 4 vòng tool mỗi span, 2 lượt dùng hết 160 request. Khi metric trả rỗng, model hỏi tool lặp lại cho tới khi chạm trần. Trần 4 vòng tool mỗi span do harness của mình đặt (`smoke-worker.py`, dòng 292–299), không phải của tác giả.

**Điểm theo điều kiện** (lượt thất bại tính 0):

| Điều kiện | A: R@1 / R@3 / MRR (12 lượt) | A+B: R@1 / R@3 / MRR (24 lượt) |
|---|---|---|
| `metric` | 0,333 / 0,417 / 0,408 | 0,250 / 0,375 / 0,336 |
| `no_metric` | 0,083 / 0,167 / 0,122 | 0,083 / 0,125 / 0,121 |
| `metric_no_log` | 0,250 / 0,500 / 0,408 | 0,208 / 0,417 / 0,339 |

**Sàng lọc theo mục 6.3:**

| So sánh | Phạm vi | ΔR@1 | ΔMRR | Seed giảm | Case bị ảnh hưởng (giảm) | Kết luận |
|---|---|---|---|---|---|---|
| Bỏ metric | A | −0,250 | −0,286 | 3/3 | 2 | đạt |
| Bỏ metric | A+B | −0,167 | −0,215 | 3/3 | 4 | đạt |
| Bỏ log | A | −0,083 | 0,000 | 2/3 | 1 | không đạt |
| Bỏ log | A+B | −0,042 | +0,003 | 2/3 | 1 | không đạt |

**Kiểm độ vững.** Khi chỉ xét các cặp mà cả hai lượt đều pass, tức bỏ hết ảnh hưởng của lỗi tool call và lỗi ngân sách:
- Bỏ metric còn 8 cặp trên 6 case, R@1 giảm 0,125 và MRR giảm 0,214. Chiều giảm giữ nguyên.
- Bỏ log còn 14 cặp trên 8 case, R@1 giảm 0,071, MRR gần như không đổi (+0,006).

**Đọc kết quả.**
- **Kết luận chính.** Mất metric làm kết quả giảm rõ, theo cả quy tắc đã chốt lẫn khi chỉ xét lượt pass. Mất log, khi metric vẫn chạy, gần như không ảnh hưởng. Điều này khớp với dự đoán từ CPU ở report phân tích.
- **Tính trên 8 case.** Kết luận "đạt" ở mức 8 case vững hơn kết luận chỉ dựa trên B.
- **Hạn chế.** 36/72 lượt thất bại, và seed 28 gần như chỉ còn trường hợp `currencyservice_loss_3`. Các con số trên là mô tả, không có kiểm định thống kê.
- **Hai đường mất điểm khi thiếu metric.** Một là model chọn sai service. Hai là model hỏi tool lặp lại tới khi chạm trần của harness. Đường thứ hai phụ thuộc vào trần do mình đặt, nên khi viết cần tách riêng.
- **So với mốc CPU.** Xếp theo độ lệch metric trên CPU đặt service đúng ở hạng 1 trong mọi trace có service đó. LLM ở điều kiện `metric` chỉ đạt R@1 0,25 trên A+B, nên với metric đã sửa, mốc CPU đơn giản đang vượt LLM.

## 5. Vòng 2: retry tool call sai định dạng bằng seed suy ra

Sếp chọn phương án 3 ngày 2026-10-29; quyết định đã ghi vào `decisions.md`.

**Thay đổi.**
- **`smoke-worker.py`.**
  - Khi tool call không qua `validate_calls`, harness hỏi lại tối đa 3 lần. Các trường hợp tính là không qua: cú pháp tool rò ra dạng text, sai schema, sai id.
  - Lần hỏi lại thứ k dùng seed `sha256("{seed}:{số request đầu}:{k}")[:4] & 0x7fffffff`.
  - Lần đầu vẫn dùng seed của lượt, nên lượt nào vốn đã pass sẽ gửi đúng các request như cũ.
  - Lần hỏi lại vẫn tính vào trần 160 request. Lỗi HTTP, lỗi finish_reason, hết ngân sách và quá deadline vẫn dừng lượt như trước.
  - Mỗi lần hỏi lại ghi một sự kiện `malformed_tool_call_retry`, và request ghi thêm `attempt` cùng `retry_of`.
  - Không trích tool call từ text.
- **`analyze-missing-source-results.py`.** Script tự tính lại seed của từng lần hỏi lại để kiểm, và kiểm số sự kiện retry khớp với số request hỏi lại. Chạy lại trên kết quả vòng 1 ra đúng số cũ.

**Kiểm.**
- Test: `test-kaggle-harness.py` 35/35, có 4 test mới cho seed suy ra, hết 3 lần, ngân sách và seed quay về seed của lượt; `test-missing-source-conditions.py` 14/14; `test-tool-result-budget.py` 11/11; `test-vllm-t4-compat.py` 4/4; `test-prefill-bench.py` 6/6.
- `check-tool-result-budget.py` chỉ đổi `worker_sha256`.
- `verify-package.py` pass cho cả A và B.
- Log nằm ở `runtime/test-logs/*-seeded-retry-0{1,2}.log`.

**Gói vòng 2.** Dữ liệu, trace và danh sách lượt giữ nguyên; chỉ `smoke-worker.py` đổi. Bản sao ở `runtime/bundle-missing-source-{a,b}-r2/`.

| Gói | Bundle sha256 | Manifest sha256 | Dataset (private) | Kernel |
|---|---|---|---|---|
| A | `ddb43de4…9dac` | `13199588…8fdb` | `siinn1706/rclagent-missing-source-a-r2-261029` | `siinn1706/rclagent-missing-source-a-r2-gpu-261029` |
| B | `9514b919…eb0c` | `6da6f0e8…4f41` | `siinn1706/rclagent-missing-source-b-r2-261029` | `siinn1706/rclagent-missing-source-b-r2-gpu-261029` |

**Trạng thái lúc đẩy.** Cả hai dataset đã báo `ready`, manifest tải về khớp, và đều private (kiểm qua API). Cả hai kernel đẩy lúc 07:58 ngày 2026-10-29 và đang RUNNING.

## Câu hỏi còn mở

- Sếp chọn cách nào ở mục 3? Nếu chạy lại, có giữ trần 4 vòng tool mỗi span không, hay nâng lên để tách hai đường mất điểm ở mục 4?
- Có nhận kết luận "đạt" ở mức 8 case hiện tại để mở hướng thiếu nguồn metric, hay đợi chạy lại cho đủ seed?
- Ghi chú vận hành: kagglesdk 2.2.5 chỉ làm mới OAuth token 30 phút *sau* khi token hết hạn (`kaggle_creds.py`, `access_token_has_expired`). Vì vậy khoảng 01:31–02:01 mọi lệnh Kaggle đều báo `Permission 'kernels.get' was denied`. Không có gì bị mất, nhưng đây là bẫy cần biết khi chạy qua đêm.
