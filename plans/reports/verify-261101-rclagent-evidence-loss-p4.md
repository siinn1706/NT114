# Kiểm chứng đối kháng đầu ra phase 4 (RQ b, đo mất bằng chứng của RCLAgent)

Ngày: 2026-11-01. Chỉ CPU, không gọi LLM, không Kaggle. Không sửa analyzer, codebook, mô-đun nạp, biên nhận. Không chạm git.

## Kết luận

Phase 4 đạt. Không có số nào trong báo cáo phase 4 lệch với file đã ghi. Ba việc kiểm đều qua: biên nhận đóng băng, 124 test, và tính lại độc lập từ zip thô. Có 5 ghi chú nhỏ (không ghi chú nào đổi nhãn hay kết luận), nêu ở mục "Phát hiện".

## 1. Biên nhận đóng băng và test

- Hash chuẩn hóa CRLF thành LF khớp `evidence-loss-prereg.json` cho cả 6 file: codebook (`f06077a1...fc769`), analyzer (`0460964a...d978`) và bốn mô-đun nạp (`check-hash-seed-order`, `compare-run-outputs`, `analyze-missing-source-results`, `analyze-completion-and-budget-stops`).
- Biên nhận chỉ có các trường gốc, không bị ghi đè. Chưa có mảng `deviations`, đúng vì chưa có deviation nào; chỉ có Erratum 1 trong `deviation-log.md`.
- `test-analyze-evidence-loss.py`: 124 test, OK (2,9 giây).
- Erratum 1 tự kiểm lại bằng CSV: `de6a50 metric_no_log` s26/s27/s28 có nhãn `S3`, `S2`, `S1`; I1 là true, true, false; I3 sai cả ba. Khớp erratum, cả hai corpus.

## 2. Tính lại độc lập từ zip thô

Script riêng (`scratchpad/verify.py`, không import analyzer) đọc `rclagent-smoke-results.zip` của gói A và B cho S1 v2 và r2. Nó tự cài lại `_label_hit` và `_k8s_service_base` từ `upstream/evaluate.py`. I0 theo định nghĩa codebook: có `tool_result` metric, `source` khác `absent`, phản hồi bắt đầu `key,` và đoạn kề cuối của khóa KPI (tách theo dấu chấm) khớp GT.

| Hạng mục | Tự tính | CSV analyzer | Kết quả |
|---|---|---|---|
| Tập run | 72 S1 v2, 72 r2 | 72, 72, cùng tập id | khớp |
| Run theo điều kiện | 24 / 24 / 24 | 24 / 24 / 24 | khớp |
| Hoàn tất S1 v2 (`metric` / `metric_no_log` / `no_metric`) | 23 / 24 / 23 | 23 / 24 / 23 | khớp |
| Hoàn tất r2 | 23 / 24 / 15 | 23 / 24 / 15 | khớp |
| R@1 S1 v2 | 10 / 10 / 5 | 10 / 10 / 5 | khớp |
| R@1 r2 | 10 / 10 / 4 | 10 / 10 / 4 | khớp |
| I0 true (mọi run) S1 v2 | 15 / 18 / 0 | 15 / 18 / 0 | khớp |
| I0 cho cả 72 run mỗi corpus (không chỉ 8 run) | không lệch run nào | | khớp |
| I4 và `rank` cho mọi run hoàn tất, cả hai corpus | 0 lệch | | khớp |
| R@1 của `author-score.txt` so với I4 | 0 lệch | | khớp |
| Bảng chính (bỏ `99f095`) S1 v2: hoàn tất / R@1 / I0 | 20 / 8 / 11, 21 / 10 / 15, 20 / 4 / 0 | giống | khớp |
| 8 run ngẫu nhiên (seed 7) cho I0 | 8 trên 8 trùng, kể cả một run `NA_censored` (không bảng) | | khớp |

Ghi chú: kiểm I0 trên cả hai corpus ra 0 lệch, nên mẫu 8 run chỉ là phần thừa so với yêu cầu.

### Tuyên bố 8 truy vấn NO_ROWS của `productcatalogservice`

- Đếm từ sự kiện thô: mỗi điều kiện `metric` và `metric_no_log` có đúng 8 phản hồi `No matching records found.` (nguồn `repaired`) cho `productcatalogservice`, ở cả S1 v2 và r2. Phân theo run: `30e3c7` 3 seed, `5f7a77` 3 seed, `de6a50` s26 và s27. Tổng NO_ROWS thật mỗi điều kiện: 54 `frontendservice` cộng 8, khớp báo cáo.
- Timestamp mô hình gõ so với timestamp của chính span: `30e3c7` và `5f7a77` lệch 300000000 giây (14xxxxxxxx thay vì 17xxxxxxxx); `de6a50` lệch 100000000 giây (16xxxxxxxx thay vì 17xxxxxxxx). Khớp báo cáo.
- GT của ba case là emailservice, checkoutservice, checkoutservice, nên cả 8 truy vấn đều ở dịch vụ không phải GT. Khớp báo cáo.
- Kiểm bằng pandas trên `metrics.csv` của case, cửa sổ ±1200 giây theo `tool_server.py`: tại timestamp của span có 10087, 8646, 10087 dòng khớp tên dịch vụ; tại timestamp mô hình gõ có 0 dòng. Khớp "8646 đến 10087 dòng". Tôi chưa chạy lại tool để thấy chữ `NO_KPI`; nhưng có dòng trong cửa sổ thì không thể ra NO_ROWS, nên chỉ còn nhánh NO_KPI hoặc bảng. Phần "trả NO_KPI" của báo cáo vì vậy chỉ được xác nhận gián tiếp.

### Các số thô khác trong báo cáo phase 4

| Số | Tự tính từ zip | Kết quả |
|---|---|---|
| `response.number` khớp request đứng trước | 6855/6855 (S1 v2), 6352/6352 (r2) | khớp |
| `tool_result` đã nối | 5281 (S1 v2) và 4910 (r2), tổng 10191, bằng số `tool_result` thô | khớp |
| `tool_result_budget` của bảng metric | 0 | khớp |
| Prompt consolidate | 1894 + 1748 = 3642 | khớp |
| Nút cây | 1944 span mỗi corpus, tổng 3888 | khớp |
| Dòng log | 222 và 200 kết quả log không rỗng; 298146 và 267295 dòng; tất cả `severity: unknown`; không dòng nào chứa `error`, `exception`, `fail` | khớp |
| Trùng `agent_complete` `metric` với `metric_no_log` | 1156/1249 (cả hai corpus); chiều ngược lại 1156/1296 | khớp 92,5 phần trăm |

## 3. Đối chiếu từng số của báo cáo phase 4 với file đã ghi

Nguồn: `runtime/analysis-evidence-loss-s1-v2/`, `-r2/`, `-r2-vs-s1-v2/` (`runs.csv`, `spans.csv`, `funnel.csv`, `summary.json`, `joined.csv`).

- **Bất biến:** `integrity` là `ok` ở 72 trên 72 run mỗi corpus; `score_check` là `match` 70 và 62, còn lại `no_author_score`; `hint_equivalent` S1 v2 là 70 true và 2 NA, r2 là 62 true và 10 NA; `fallback_used` bằng 0 ở mọi span; `summary.json` có `integrity_problems` rỗng, `unseen_branches` rỗng. Tất cả khớp.
- **Bảng biên S1 v2:** cả 6 hàng (3 điều kiện, bảng chính và 8 case) khớp từng ô I0 đến I5 và `I5 same/diff/refusal`; I2 lenient 9/23, 10/24, 4/23 và I3 strict 11/23, 12/24, 0/23 khớp.
- **`first_loss_linear` và `final_residual`:** khớp cả 12 ô. `reaches_final_input_not_rank1` tách toàn bộ ra `top1_equals_wrong_root_label` (3, 4, 4, 7).
- **Cờ:** `chain_weakened` 11 / 13 / 0, `hint_weakened` 0 / 2 / 0, `hit_without_evidence` 0 / 0 / 5. Khớp.
- **8 run `H_cap` (r2 `no_metric`):** số request lúc dừng 11, 10, 10, 160, 160, 159, 25, 12 khớp từng run; I0 là `NA_censored`. Khớp.
- **Phễu `metric`:** `spans.csv` cho 92 span GT abnormal trên 98 span GT có self-state; GT trong hint 14; root là GT 3; R@1 10. `no_metric` 0 trên 108 span GT. Tỷ lệ abnormal: 324/327 span có bảng, 66/1574 không có bảng. Khớp.
- **D1:** 14 span `has_error_logs`, tất cả `frontendservice`; 4 `D1` (đều `metric`), 10 `D1_na` (đều `metric_no_log`). Với 29 run `metric` và `metric_no_log` có span GT trong trace: 11/11 run trượt mang tuyên bố, 0/18 run đúng; theo `D1` là 4/11 và 0/18. Khớp.
- **Phép so r2 với S1 v2:** 62 cặp cùng hoàn tất, 2 cùng cắt cụt, 8 hoàn tất ở S1 v2 và cắt cụt ở r2. 62 trên 62 trùng ở mọi cột so (tôi so riêng 14 cột nhãn từ hai `runs.csv`: 0 lệch). Khớp, và vượt kỳ vọng kế hoạch (cho phép lệch I4 và I5 tới 14 cặp).
- **Dự báo xem trước (`S0_gt_span_absent` 3/4 và các câu khác):** là phần ngoài phạm vi phase này, không kiểm.

## 4. Phát hiện

Không có phát hiện chặn. Các ghi chú theo mức:

1. **Thấp, thiếu phạm vi cho số D1.** "11/11 và 0/18" chỉ đúng trong tập 29 run `metric` + `metric_no_log` có span GT trong trace và hoàn tất. Trên mọi run hoàn tất của hai điều kiện đó (47 run) thì là 14/27 run trượt và 0/20 run đúng. Số vẫn đúng; báo cáo chỉ nên ghi tập mẫu số. Tôi tính được 29 run chỉ nhờ đối chiếu với scout; báo cáo phase 4 không tự nêu.
2. **Thấp, mẫu số "92/98".** 98 là số span GT có self-state, trong 108 span GT của 15 run `metric` có I0 đúng (14 hoàn tất cộng `ad1c27` s27 bị cắt cụt). Báo cáo ghi "metric funnel (14 runs)" cạnh số này, nên dễ hiểu nhầm là 14 run. Không đổi số.
3. **Thấp, từ ngữ "8 productcatalogservice NO_ROWS cases".** Là 8 truy vấn (span) mỗi điều kiện, từ 3 case; 16 dòng sự kiện cho hai điều kiện, chưa tính hai corpus. Nên đổi chữ "cases" thành "truy vấn".
4. **Trung bình, báo cáo `.md` của phase 4 chưa được lưu.** Không có file `analysis-261101-0431-...-recompute-vs-scout.md` trong `plans/reports/`; `plan.md` dòng 29 đã ghi rõ điều này. Phụ lục A (đoạn nối nhãn) chỉ còn trong scratchpad của phiên trước. Vì không có file prose nào của báo cáo phase 4, tôi không sửa lỗi chính tả nào. Nội dung đã kiểm ở trên có thể dùng để ghi lại file đó, và bản kiểm này đã gồm các bảng số chính.
5. **Thông tin, xuống dòng.** Cây làm việc có CRLF ở analyzer (1128 dòng), file test, codebook và biên nhận; các mô-đun nạp có sẵn cũng CRLF (ví dụ `compare-run-outputs.py`). Quy tắc "giữ LF" của lệnh giao không đúng nghĩa đen trên cây làm việc Windows với `core.autocrlf=true`; hash dùng quy tắc chuẩn hóa CRLF nên không bị ảnh hưởng, và `.gitattributes` đã thêm dòng `plans/reports/prereg-*.md text eol=lf` (chưa commit) để codebook thành LF trong index. Analyzer và test chưa có thuộc tính tương tự, nên khi commit sẽ theo `autocrlf`. Nếu sếp muốn LF cho `kaggle/*.py` trong repo thì cần thêm thuộc tính, không phải việc của phase này.

## 5. Giới hạn của lần kiểm này

- Script độc lập tự cài lại I0 và I4 theo chữ của codebook, nên lỗi hiểu codebook (nếu có) sẽ lặp ở cả hai. Nó không phát hiện sai khác về diễn giải; nó chỉ chứng minh analyzer thi hành đúng chữ định nghĩa. Các chỉ báo I1, I2, I3, I5 và nhãn S chưa được tính lại độc lập (ngoài `first_loss_linear` của `de6a50` theo erratum); chúng dựa vào 124 test và việc đối chiếu hai corpus.
- r2 trùng S1 v2 62/62 là kiểm tính tất định, không phải độc lập.

Script: `C:\Users\Siinn\AppData\Local\Temp\claude\C--Users-Siinn--claude-spares-spare-JUfm50\8ac89638-bf0c-4a31-b930-7d87d9e0f888\scratchpad\verify.py`, cùng thư mục có `tables.py`, `spans.py`, `raw2.py`.
