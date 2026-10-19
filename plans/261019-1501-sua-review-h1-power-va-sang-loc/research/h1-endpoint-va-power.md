# H1: endpoint chính, power theo estimator thật và quy tắc DEV pilot (đề xuất)

Ngày 2026-10-19. Chỉ CPU, dữ liệu tổng hợp; không có output model, không dùng nhãn hay hàng test của
NT114. Đây là **đề xuất**, không sửa protocol v2. H1 vẫn chỉ là ứng viên.

Nguồn máy đọc: [h1_power.py](../work/h1_power.py), [test_h1_power.py](../work/test_h1_power.py),
[h1-power-grid.csv](../work/out/h1-power-grid.csv), [h1-mde.csv](../work/out/h1-mde.csv),
[h1-power-interaction.csv](../work/out/h1-power-interaction.csv),
[h1-power-run.json](../work/out/h1-power-run.json).

## 1. Hai phép đánh giá phải tách riêng

| Ký hiệu | Câu hỏi | Định nghĩa | Coverage |
|---|---|---|---|
| **E1** (đề xuất chính) | Confidence có xếp lỗi xuống cuối tốt hơn ngẫu nhiên không? | `G_c = lỗi nền − risk khi trả lời đúng c phần trọng số có score cao nhất`. Nhóm đồng hạng ở biên được trả lời một phần, bằng kỳ vọng của tie-break ngẫu nhiên có seed trong `selective.coverage_matched_threshold` (C1). C2 có risk kỳ vọng bằng lỗi nền ở mọi coverage nên dùng giá trị giải tích | Đúng bằng c (0.7), cả trên test |
| E1t | Như E1, nhưng trả lời trọn nhóm đồng hạng (`metrics.selective_risk_at`) | Coverage thực ≥ c | Với consensus n = 10 trong mô phỏng, coverage thực ≈ 0.77 thay vì 0.7; gain nhỏ hơn E1 khoảng 20 % |
| **E2** | Ngưỡng đóng băng từ DEV có chuyển sang test không? | `tau = selective.fit_threshold(DEV, coverage = 0.7)`; trên test, `G_tau = lỗi nền − risk(score ≥ tau)`; so với C2 ở **coverage thực tế** (hợp lệ vì risk của C2 không phụ thuộc coverage) | Báo cáo coverage thực kèm CI, không ép bằng 0.7 |
| E3 | Toàn đường cong | `lỗi nền − AURC` (`metrics.aurc_w`) | Không có coverage cố định |

E1 không fit gì trên DEV (c chọn trước), nên không có độ lạc quan do fit. E2 thì có; trong DEV phải
cross-fit theo injection (§4).

## 2. Mô hình mô phỏng

- **Cấu trúc cụm thật.**
  - RCAEval `full`: test 218, DEV 143 (một bản ghi mỗi injection).
  - Gộp single-modality (`no_metric`, `no_log`, `no_trace`) trên RCAEval: test 108 injection, 285
    bản ghi (69 × 3, 39 × 2); DEV 78 injection, 210 bản ghi. Số liệu đếm từ
    `data/reports/condition-matrix-rcaeval.json` và split `within-rcaeval-grouped-0-e9b2c81c`. Chỉ đọc
    cờ `applicable` và vai split, không đọc kết quả.
  - Ngoài ra: `blind_root` ∩ `blind_nonroot_ev` 52; Nezha 97; RCA100 86 bản ghi / 70 injection; AIOps2025 318.
- **Hệ quả quan trọng.** 110/218 injection test của RCAEval chỉ có metric tự nhiên. H1 "dưới
  telemetry bị thiếu" trên RCAEval vì vậy chỉ có **108** cụm độc lập, không phải 218.
- **Bộ sinh.**
  - Biến ẩn mỗi bản ghi có thành phần injection chung (ICC 0.5).
  - Đúng/sai được ngưỡng hoá theo lỗi nền ∈ {0.2, 0.35, 0.5}.
  - Consensus là số trên 10 mẫu đồng ý, chia 10. Đây là 11 mức, có đồng hạng như estimator thật.
  - Tín hiệu ρ ∈ {0, 0.15, 0.3, 0.45, 0.6}; ρ = 0 là giả thuyết không.
- **Kiểm định.**
  - Percentile cluster bootstrap theo injection, như `contrasts.py` với metric không phân rã.
  - Bác bỏ H0: G ≤ 0 khi cận dưới của CI hai phía (1 − α) > 0.
  - Hai mức: α = 0.05 (endpoint đứng một mình) và α = 0.05/3 (bước đầu của Holm với họ 3).
  - 1,000 lần lặp × 1,999 lần bootstrap mỗi kịch bản; seed 20261019; 682 giây CPU.

## 3. Kết quả

**Kiểm soát lỗi loại I.** Ở ρ = 0, tỉ lệ CI loại 0 về phía dương là 0.009–0.026 (RCAEval, AIOps2025),
và 0.009–0.022 trên các tập nhỏ. Danh nghĩa một phía là 0.025, nên phép thử đúng mức hoặc hơi bảo thủ.

**MDE của E1 ở coverage 0.7 (power 0.80):**

| Tập (cụm test) | Lỗi nền 0.2 | 0.35 | 0.5 | Với Holm k = 3 |
|---|---:|---:|---:|---:|
| RCAEval `full` (218) | 0.055 | 0.064 | 0.060 | 0.061–0.072 |
| RCAEval gộp single-modality (108 / 285) | 0.046 | 0.052 | 0.053 | 0.056–0.065 |
| AIOps2025 (318) | 0.046 | 0.050 | 0.050 | 0.053–0.060 |
| Nezha (97) | 0.080 | 0.090 | 0.093 | 0.103 trở lên |
| RCA100 (70 / 86) | 0.088 | 0.102 | 0.102 | > 0.11 |
| `blind_root` ∩ `blind_nonroot_ev` (52) | > 0.089 | > 0.112 | > 0.113 | không đạt |

**So với báo cáo cũ.**
- Báo cáo cũ suy MDE selective ≈ 0.10/√0.7 ≈ 0.12, rồi suy ngược ra ngưỡng AUROC 0.74–0.78. Cả hai
  bước đều sai hướng.
- Contrast với C2 giải tích có phương sai nhỏ hơn nhiều. SD của ước lượng E1 trên RCAEval `full` là
  0.018–0.022, khớp với SD 0.020 mà review tự tính.
- Vì vậy MDE thực, **dưới mô hình sinh này**, chỉ khoảng một nửa con số cũ.
- AUROC tương ứng với MDE trong mô hình này (α 0.05) là khoảng 0.61–0.67 cho RCAEval và AIOps2025,
  và 0.70–0.76 cho Nezha và RCA100. Nhưng AUROC **không** xác định duy
  nhất gain: phản ví dụ 13/21 trong `test_same_auroc_different_selective_risk` cho cùng AUROC mà risk
  là 1/7 và 2/7. Do đó **không dùng AUROC làm cổng go/no-go**.

**Chuyển ngưỡng DEV → test (E2).**
- Với DEV 143 và test 218, coverage thực trên test có khoảng 90 % là 0.65–0.82. Khoảng 7–14 % số lần
  lặp lệch hơn 0.10 khỏi 0.7 (10–14 % với RCAEval `full`, 7–11 % với tập gộp).
- Power của E2 thấp hơn E1. Ví dụ RCAEval `full`, lỗi nền 0.35, ρ = 0.3 (AUROC 0.62): E2 0.49, E1 0.53
  (α Holm). E2 vì vậy là endpoint phụ, báo cáo kèm coverage thực.

**E3 (AURC).** E3 có power cao hơn E1 ở cùng tín hiệu (ví dụ 0.81 so với 0.69 ở RCAEval `full`, lỗi
nền 0.35, ρ = 0.3, α 0.05). Nhưng E3 không trả lời câu hỏi "ở cùng coverage". Đề xuất dùng nó làm
endpoint thứ hai trong họ, không thay E1.

**Tương tác thiếu telemetry × abstention (DiD).** Đây là contrast `G(gộp single-modality) − G(full)`
trên 108 injection, mỗi lần bootstrap rút lại cùng các injection cho cả hai arm.

| ρ_full → ρ_missing | DiD thật | Power (α 0.05) |
|---|---:|---:|
| 0.3 → 0.3 | 0.007 | 0.026 |
| 0.3 → 0.45 | 0.034 | 0.155 |
| 0.3 → 0.6 | 0.064 | 0.457 |

Contrast này thiếu power. Nó chỉ dùng được ở mức thăm dò. §12(c) cũ (hiệu thô của confidently-wrong
giữa `full` và `metrics_only`) bị bỏ, vì nó lẫn thay đổi độ khó với lợi ích abstention.

**Giới hạn của mô phỏng.**
- Phân bố consensus thật, ICC và đường cong tín hiệu chưa biết.
- Mô hình binomial-logit là một giả định thiết kế, không phải kết quả.
- MDE trên chỉ đúng cho bộ sinh này; DEV pilot sẽ thay các giả định bằng số đo.

## 4. Đề xuất endpoint chính (chưa đăng ký trước)

> **H1-primary.**
> - **Phạm vi:** RCAEval, split `within-rcaeval-grouped-0-e9b2c81c`, vai `test`; model chính, prompt
>   v1, `retrieval = none`.
> - **Tập:** gộp ba điều kiện `no_metric`, `no_log`, `no_trace`. Đó là 108 injection, 285 bản ghi,
>   trọng số 1/số bản ghi của injection. Score là `conf_consensus` (n = 10), xếp hạng chung trên toàn
>   bộ tập gộp.
> - **Estimator:** `G_0.7 = lỗi nền − risk ở coverage chính xác 0.7` (E1, nhóm biên trả lời một
>   phần), so với C2 giải tích.
> - **Kiểm định:** H0: G_0.7 ≤ 0. Percentile cluster bootstrap theo injection, B = 10,000, CI hai phía
>   95 %; bác bỏ khi cận dưới > 0.
> - **SESOI:** 0.05, chờ chủ dự án xác nhận.

- **Lý do chọn tập gộp single-modality:** đúng phát biểu H1; điều kiện luôn đổi bằng chứng
  (manipulation check research/05); power tương đương hoặc tốt hơn `full` dù ít cụm hơn.
- **Rủi ro của tập gộp:** gộp nhiều điều kiện giả định một thang confidence chung. arXiv 2601.22208
  cho thấy bỏ trace đôi khi *cải thiện* chẩn đoán còn bỏ metric làm hại nhiều nhất, nên tác dụng có thể
  không đồng nhất. Vì vậy phải báo cáo từng điều kiện như phân tích phụ.
- **Họ confirmatory (nếu chủ dự án muốn nhiều hơn một test), Holm k = 3:**
  1. H1-primary;
  2. E3 (lỗi nền − AURC) trên cùng tập;
  3. E1 trên RCAEval `full`.
- **Ngoài họ:**
  - E2 với coverage thực.
  - DiD thiếu telemetry, ở mức thăm dò.
  - AIOps2025 là bản lặp, bảng riêng vì set-scored.
  - Nezha, RCA100 và giao 52 ở mức thăm dò.
  - Verbal và token probability ở mức thăm dò.

## 5. Quy tắc quyết định của DEV pilot (đề xuất, cài trong `pilot_decision`)

Chỉ dùng nhãn DEV (vai `val`), trên chính tập gộp single-modality của DEV (78 injection):

1. Tính `G_0.7(DEV)` với CI 80 % và 95 % bằng cluster bootstrap (B = 4,000).
2. **Futility:** cận trên 95 % < SESOI. Khi đó H1 không lên confirmatory; báo cáo như kết quả phủ
   định có kiểm soát ở mức thăm dò.
3. **Confirmatory:** cả hai điều kiện sau phải đạt.
   - Power trên test tại `δ = max(cận dưới 80 %, 0)` đạt ≥ 0.80 ở α Holm (0.05/3). Power đọc từ đường
     `true_gain_exact` → `power_E1_a05_holm3` của `rcaeval_missing_pool`, ở lỗi nền gần nhất với lỗi
     nền DEV.
   - Ngưỡng E2 cross-fit hai fold theo injection trong DEV cho coverage thực lệch ≤ 0.10 khỏi 0.7 ở
     cả hai fold.
4. **Exploratory:** mọi trường hợp còn lại. H1 vẫn được chạy và báo cáo kèm CI, không có claim
   confirmatory.
5. Trước khi đóng băng preregistration: chạy lại `h1_power.py`, thay bộ sinh bằng phân bố consensus và
   ICC đo trên DEV. Phân bố đo được dùng làm tham số; bản thân hàng DEV không được dùng.

Dùng cận dưới 80 % thay cho ước lượng điểm vì lý do sau. DEV chỉ có 78 cụm, nên ước lượng điểm lạc
quan với xác suất cao. Cận dưới 80 % là một mức thận trọng vừa phải, không phải mức "chắc chắn".

## 6. Kiểm tra đã chạy

- `python -m pytest -q -p no:cacheprovider test_h1_power.py` → **8 passed** (venv phân tích, numpy 2.5.4).
  Các test gồm:
  - exact-coverage bằng kỳ vọng tie-break của C1 (sai số ≤ 0.004 với 4,000 draws);
  - E1t khớp `metrics.selective_risk_at`;
  - E3 khớp `metrics.aurc_w`;
  - phản ví dụ AUROC 13/21;
  - ví dụ chuyển ngưỡng của review (tau 0.9, coverage DEV 0.8, coverage test 0.9);
  - hàng 0 của bootstrap là ước lượng điểm;
  - null không có gain;
  - các nhánh của `pilot_decision`.
- `python -I h1_power.py out --reps 1000 --boot 1999` → xong sau 682 giây, exit 0.
