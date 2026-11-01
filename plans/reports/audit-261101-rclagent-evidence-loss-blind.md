# Báo cáo kiểm toán đọc mù: nhãn mất bằng chứng của RCLAgent (RQ b)

- Ngày: 2026-11-01. Trạng thái: **chờ sếp phân xử** (agent chỉ đề xuất lớp, không quyết).
- Phạm vi: so form đọc mù `K/runtime/analysis-evidence-loss-audit/form-reader.md` (12 gói, C1 đến C5) với nhãn của analyzer trên đúng 12 run đó. `K/` là `F:/Nam/UIT/NT114 - NCKH/plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`.
- Nhãn analyzer lấy từ `K/runtime/analysis-evidence-loss-s1-v2/runs.csv` và `spans.csv` (analyzer chưa chạy lại; sha256 `analyze-evidence-loss.py` hiện tại `0460964a...d978` trùng biên nhận đóng băng; file kết quả tạo 04:32, trước form 04:48; người đọc không mở chúng). Không đổi nhãn, codebook hay analyzer.
- Người đọc là **một LLM-coder, cùng họ model với tác giả codebook**, nên đồng thuận cao có thể giả.
- Gói mù qua kiểm `grep -rlE "S[0-4]_|preserved|final_residual"` trên `runtime/analysis-evidence-loss-audit/packets`: không có file nào (packets-blind-ok).

## 1. Kết luận ngắn

1. **Không có bất đồng nhãn nào** giữa người đọc và luật trên 12 run (đồng thuận thô 100 phần trăm ở mọi chỉ báo so được).
2. Có **6 điểm chưa khớp về cách hiểu hoặc phạm vi** (mục 4) cần sếp xếp lớp; không điểm nào đổi một nhãn. Đề xuất của agent: không có lỗi luật, không có lỗi analyzer, nên **chưa cần mở deviation**.
3. Đồng thuận này nói ít: 12 run chỉ thuộc 6 case, 5 run là S0 (chỉ kiểm được C1), 3 run cùng case `de6a50`, và C5 là hàm của C1 đến C4 nên chỉ đo việc áp luật. Nhãn S1 đến S4 do người đọc tự định nghĩa (không có trong mục 13 của codebook), nên C5 đồng thuận chưa chứng minh bảng nhãn của analyzer đúng ở S4.

## 2. Mẫu

12 run hoàn tất, loại case hiệu chỉnh `99f095`, rút phân tầng theo (điều kiện, `first_loss_linear`) với hạt giống 20261031, cộng run mixed_carriers, run rare_branch_misattributed và 2 run `no_metric` ngẫu nhiên (`sample.csv`). Cách rút nằm trong `draw-sample.py`; báo cáo này không kiểm lại việc rút mẫu.

## 3. Đồng thuận

### 3.1 Theo chỉ báo (người đọc so với luật)

| Mục form | Chỉ báo luật | So được | Đồng thuận thô | Ghi chú |
|---|---|---|---|---|
| C1 tập dịch vụ có bảng | I0 (`table_received`, `table_key_prefixes`) | 12 | 12/12 | Tập dịch vụ cũng khớp (`emailservice`, `checkoutservice`, `currencyservice` hoặc rỗng). Kiểm lại từ `events.jsonl`: số bảng `key,` và tập tiền tố khóa KPI trùng 12/12. |
| C2 carrier tự đánh `is_abnormal` | I1 | 12 (7 có giá trị, 5 cùng `NA`/n/a) | 12/12 | Đếm carrier trùng: 2/2, 11/12, 11/12, 20/20, 1/1, 1/1, 0/1 (kiểm lại từ `events.jsonl`). |
| C3 lớp nhãn root | I2 (`root_class`) | 7 | 7/7 | 5 run S0 không so được (mục 4, B1). |
| C4 dòng hint | I3 | 7 | 7/7 | Dòng hint trong gói trùng `hint_list_size` và `hint_equivalent` ở 12/12; 5 run S0 không so được (B1). |
| Hạng GT cuối (người đọc ghi 1-based) | I4 (rank 0-based, R@1) | 12 | 12/12 sau khi đổi hệ đếm | Người đọc 7, 8, 6, 2, 9, 8, 1, 1, 1, 1, 1, không có; luật 6, 7, 5, 1, 8, 7, 0, 0, 0, 0, 0, -1. So không đổi hệ đếm sẽ lệch giả (B2). I4 đúng khi hạng 0: trùng 12/12. |
| C5 `first_loss_stage` | `first_loss_linear` | 12 | 12/12 | S0 x5, S2 x2, S3 x1, S1 x1, preserved x3 ở cả hai bên. |

Tập con quyết định (điều kiện có metric, I0 đúng, 7 run: `bdb4a6`, `829ce1`, `df812e`, `94ab18`, `c934c3`, `865243`, `69e2b5`): C2, C3, C4, C5 đều 7/7.

Kappa Cohen, chỉ là số mô tả: bằng 1,00 ở C1 (7 đúng, 5 sai), C2 (trên 7 run có giá trị), C3, C4 và C5, vì đồng thuận thô 100 phần trăm và mỗi mục có hơn một giá trị. Cảnh báo: C2 trên 7 run có 6 run "có" (86 phần trăm, trên ngưỡng 80), nên kappa của C2 gần như không mang thông tin. Không dùng ngưỡng, PABAK hay bootstrap.

### 3.2 Theo case

| Case | Run (mã mù) | C1 đến C5 và hạng khớp |
|---|---|---|
| 272a47 | d9443c, d1007e, 3d7c17 | 3/3 run khớp hết (cả ba S0) |
| 29583d | bdb4a6, 2f99da | 2/2 (S2 và S0) |
| 30e3c7 | 532dc2 | 1/1 (S0) |
| 5f7a77 | 829ce1, df812e | 2/2 (preserved, carrier hỗn hợp 11/12) |
| ad1c27 | 94ab18 | 1/1 (preserved) |
| de6a50 | c934c3, 865243, 69e2b5 | 3/3 (S3, S2, S1) |

6/6 case khớp hoàn toàn. Hai run `829ce1` và `df812e` cùng case và gần như giống nhau, nên không phải hai mẫu độc lập.

### 3.3 Bảng từng run

| Mã mù | Run (điều kiện, seed) | GT | C1 = I0 | C2 = I1 | C3 = I2 | C4 = I3 | Hạng (đọc / luật) | C5 = luật |
|---|---|---|---|---|---|---|---|---|
| d9443c | 272a47 metric_no_log s27 | recommendationservice | rỗng / sai | n/a / NA | n/a / sai (root `refusal`) | n/a / sai (hint chỉ `frontendservice`) | 7 / 6 | S0 / S0 |
| d1007e | 272a47 no_metric s27 | recommendationservice | rỗng / sai | n/a / NA | n/a / sai (root `refusal`) | n/a / sai (hint rỗng) | 8 / 7 | S0 / S0 |
| 3d7c17 | 272a47 no_metric s28 | recommendationservice | rỗng / sai | n/a / NA | n/a / sai (root `refusal`) | n/a / sai (hint rỗng) | 6 / 5 | S0 / S0 |
| bdb4a6 | 29583d metric s27 | emailservice | có / đúng | có / đúng | khác / sai (checkoutservice) | metric-only / đúng | 2 / 1 | S2 / S2 |
| 2f99da | 29583d no_metric s28 | emailservice | rỗng / sai | n/a / NA | n/a / sai (root `refusal`) | n/a / sai (hint rỗng) | 9 / 8 | S0 / S0 |
| 532dc2 | 30e3c7 metric s28 | emailservice | rỗng / sai | n/a / NA | n/a / sai (root `refusal`) | n/a / sai (hint rỗng) | 8 / 7 | S0 / S0 |
| 829ce1 | 5f7a77 metric s28 | checkoutservice | có / đúng | có (11/12) / đúng | khớp / đúng | metric-only / đúng | 1 / 0 | preserved / preserved |
| df812e | 5f7a77 metric_no_log s28 | checkoutservice | có / đúng | có (11/12) / đúng | khớp / đúng | metric-only / đúng | 1 / 0 | preserved / preserved |
| 94ab18 | ad1c27 metric_no_log s28 | currencyservice | có / đúng | có (20/20) / đúng | khớp / đúng | metric-only / đúng | 1 / 0 | preserved / preserved |
| c934c3 | de6a50 metric_no_log s26 | checkoutservice | có / đúng | có (1/1) / đúng | khớp / đúng | không có / sai | 1 / 0 | S3 / S3 |
| 865243 | de6a50 metric_no_log s27 | checkoutservice | có / đúng | có (1/1) / đúng | khác (paymentservice) / sai | không có / sai | 1 / 0 | S2 / S2 |
| 69e2b5 | de6a50 metric_no_log s28 | checkoutservice | có / đúng | không / sai | khác (cartservice) / sai | không có / sai | không có / -1 | S1 / S1 |

(Mỗi ô: giá trị người đọc / giá trị luật.)

## 4. Điểm chưa khớp và đề xuất lớp (chờ sếp)

Không có bất đồng nhãn. Sáu mục dưới đây là chỗ hai bên đọc khác nhau hoặc form và luật không cùng phạm vi. Cột "Đề xuất" là ý kiến của agent; cột cuối để trống cho sếp.

| Mã | Mô tả và bằng chứng từ sự kiện thô | Ảnh hưởng nhãn | Đề xuất | Lý do | Sếp phân xử |
|---|---|---|---|---|---|
| B1 | Form quy định C2 đến C4 là n/a khi C1 rỗng, còn luật vẫn gán I2 và I3 cho cả run. 5 run S0 (`d9443c`, `d1007e`, `3d7c17`, `2f99da`, `532dc2`): người đọc n/a; luật I2 sai (nhãn root là `refusal` ở cả 5) và I3 sai (`hint_list_size` 1 ở `d9443c`, 0 ở bốn run còn lại). 10 ô không so được; `d9443c` có dòng hint `frontendservice` dù không có bảng metric, đúng với luật (hint dựng từ cờ span). | Không (I1 là `NA` ở cả hai bên, nên chuỗi S0 không đổi) | ambiguous | Phạm vi form hẹp hơn phạm vi luật: C3 và C4 định nghĩa theo dịch vụ trong C1, I2 và I3 định nghĩa theo GT. Không phải lỗi của luật hay người đọc. || Đồng ý: giới hạn phạm vi của form, không phải bất đồng. |
| B2 | Người đọc ghi hạng GT 1-based (7, 8, 6, 2, 9, 8, 1...), luật ghi 0-based (6, 7, 5, 1, 8, 7, 0...) và `-1` cho không trúng. So thẳng sẽ lệch 11 trên 12 run; đổi hệ đếm thì 12/12. | Không | ambiguous | Hệ đếm của form không nêu trong codebook (mục 4, I4 dùng 0-based). Vô hại nếu form ghi rõ. || Đồng ý: bỏ qua, chỉ khác hệ đếm. |
| B3 | `69e2b5`: mục A ghi C3 là "dịch vụ khác (root = cartservice)", mục B ghi C3 là "n/a (cartservice)". Sự kiện thô: nhãn root của consolidate là `cartservice`, luật I2 sai (`other_service`). | Không | reader_error | Người đọc ghi không nhất quán giữa hai mục (mục B bỏ C3 vì C2 đã "không"); hai mục không mâu thuẫn về dữ kiện. || Đồng ý: reader_error. |
| B4 | Người đọc tự định nghĩa S4 là "GT không nằm trong 10 đầu ra cuối", còn codebook định nghĩa I4 đúng khi hạng 0 (R@1), nên S4 của luật là "I0 đến I3 đúng mà GT không ở hạng 0". Trong mẫu không run nào khác nhau giữa hai định nghĩa (ba run `preserved` đều hạng 0; `bdb4a6` mất ở S2 trước), nhưng với run I0 đến I3 đúng và hạng 1 đến 9, người đọc sẽ gán `preserved` còn luật gán S4. | Không (trong mẫu này) | reader_error | Mục 13 của codebook không định nghĩa S0 đến S4 cho người đọc; người đọc tự suy (đã nêu ở concern của họ). Hậu quả: C5 chỉ kiểm cách áp luật theo cách hiểu của người đọc, không kiểm S4 của analyzer. Câu hỏi thiết kế (R@1 hay top-k cho S4) là quyết định của sếp, không phải của audit này. || Đồng ý: reader_error; S4 giữ theo R@1 như codebook (top-10 gần như chứa đủ mọi dịch vụ nên không phân biệt). |
| B5 | Người đọc kết luận ở 5 run S0: GT vẫn nằm top-10 ở hạng 6 đến 9 "nên bằng chứng đến từ chỗ khác (trace, prior tên dịch vụ)". Sự kiện thô: `root_causes` ở mọi run đều có 10 phần tử và gần như là toàn bộ dịch vụ của ứng dụng (cùng bộ `adservice`, `cartservice`, `checkoutservice`, `currencyservice`, `emailservice`, `frontendservice`, `paymentservice`, `productcatalogservice`, `recommendationservice`, `shippingservice`, `redis`). | Không | reader_error | Suy luận quá mức: GT có mặt trong top-10 gần như chắc chắn dù không có bằng chứng, nên không chứng tỏ có đường bằng chứng khác. Hệ quả cho luật: "GT không ở top-10" gần như không xảy ra (chỉ `69e2b5`), nên trong dữ liệu này chỉ R@1 mới phân biệt được. || Đồng ý: reader_error; ghi vào phase 7 là chỉ R@1 phân biệt được trên dữ liệu này. |
| B6 | Cách gán carrier cho dịch vụ: người đọc đọc theo `service_name` trong self-state, luật theo `cmdb_id` của span carrier (khớp cách dựng hint của tác giả). Hai khóa này khác nhau: `bdb4a6` span `152ebdd7` (cmdb `checkoutservice`, self-state nói `emailservice`); `829ce1`/`df812e` span `803f243d` (cmdb `frontendservice`, self-state nói `checkoutservice`); `c934c3` và `865243` span `fecaffcc` (cmdb `frontendservice`, self-state nói `checkoutservice`, `is_abnormal` true) nên hint chỉ liệt kê `frontendservice`. Luật gán `misattributed` đúng cho `c934c3` và `865243`; form không có mục nào hỏi điều này. | Không (C2 trùng I1; cơ chế S3 của `c934c3` cũng khớp) | ambiguous | Câu C2 "carrier tự đánh `is_abnormal`" không nêu khóa gán dịch vụ. Hai bên trùng nhãn nhưng đồng thuận C2 không kiểm `misattributed`, nên không nên trích nó như bằng chứng cho `misattributed`. || Đồng ý: ambiguous; phase 7 không trích audit làm bằng chứng cho `misattributed`. |

Tóm đề xuất theo lớp: rule_error 0, analyzer_error 0, reader_error 3 (B3, B4, B5), ambiguous 3 (B1, B2, B6).

## 5. Việc form không đo

- Nhãn con của S0: luật tách `S0_gt_span_absent` (4 run: `d9443c`, `d1007e`, `3d7c17`, `532dc2`) và `S0_empty_result` (1 run: `2f99da`, đã hỏi GT, `empty_reason` là `absent_source`, 49 phản hồi nguồn `absent`). Form chỉ có "C1 rỗng", nên phần tách này chưa được kiểm tay.
- I5, `final_residual`, `chain_weakened`, `hint_weakened`, `hit_without_evidence` và các biến thể (`I2_lenient`, `I3_strict`): không có trong form.
- Nhánh hiếm: không có run nào trong mẫu đi qua nhánh fallback của self-state hay các `unseen_branches`.

## 6. Hạn chế

- Một LLM-coder cùng họ model với tác giả codebook; đồng thuận có thể cao giả.
- Mẫu nhỏ (12 run, 6 case, 5 run S0 chỉ kiểm C1, 3 run cùng một case); số liệu mô tả, không suy diễn.
- C5 là hàm của C1 đến C4 và dùng bảng nhãn do người đọc tự suy (B4), nên chỉ đo việc áp luật.
- Báo cáo này đã bày nhãn của luật cạnh form đọc, trái thứ tự "sếp phân xử trước, mở nhãn luật sau" của kế hoạch. Vì không có bất đồng nhãn nên rủi ro neo thấp; nếu sếp muốn phân xử sạch thì nên đọc cột "Mô tả và bằng chứng" của mục 4 trước và bỏ qua cột "Đề xuất".
- Agent không kiểm lại việc rút mẫu và không chạy lại analyzer.

## 7. Việc sau khi sếp phân xử

- Điền cột "Sếp phân xử" ở mục 4.
- Chỉ khi sếp xếp một mục là `rule_error` hoặc `analyzer_error` mới mở deviation (ghi `deviation-log.md`, số liệu trước và sau, hash mới, mảng `deviations` trong biên nhận, chạy lại test, chạy lại S1 v2 ra `runtime/analysis-evidence-loss-s1-v2-amended/`). Đề xuất hiện tại không có mục nào như vậy.
- Phase 6 giữ trạng thái "in-review (chờ sếp phân xử)".

## 8. Phân xử của sếp (2026-11-01)

Sếp chấp nhận toàn bộ đề xuất lớp của agent ở mục 4 (rule_error 0, analyzer_error 0), nên không mở deviation và không chạy lại. Không làm lượt đọc thứ hai: phần tách `S0_gt_span_absent` đã được kiểm máy độc lập ở phase 4 (số span GT theo case khớp), còn I5 và `final_residual` là phép so chuỗi đã có test và khớp 62/62 giữa hai corpus. Hai giới hạn chuyển sang báo cáo phase 7: (1) audit chỉ kiểm I0 đến I3 và `first_loss_linear`, không kiểm `misattributed`, I5 hay `final_residual`; (2) người đọc mù cùng họ model với tác giả codebook nên đồng thuận có thể cao giả.

## Câu hỏi còn mở

- B4: S4 nên theo R@1 (như codebook) hay theo top-k? Codebook không đổi; chỉ ghi để sếp biết người đọc đã hiểu khác.
- Có cần một lượt đọc thứ hai (hoặc người đọc khác họ model) không? Kế hoạch mặc định một coder; sếp chọn.
