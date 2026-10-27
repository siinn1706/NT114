# Kiểm lịch sử tiếp xúc test RE2-OB (D12), bản a01

- Ngày kiểm: 2026-10-26 (Asia/Saigon). Máy: máy của phiên này (i5-14400F, AMD RX 5600 XT, không CUDA). Không gọi model, không chạy GPU.
- Cách kiểm: đọc config, manifest, tên tệp, mốc thời gian, mã nguồn tạo bảng, nhật ký quyết định, và tài liệu research/plan có trích số. **Không** mở bảng kết quả, tệp kết quả từng ca hay tệp nhãn chỉ để chứng minh chúng chưa bị mở. Các tệp `results_*/table_*.csv`, `baselines.jsonl`, `evidence_visibility.jsonl`, `leakage_near_duplicates*.{jsonl,csv}`, `canonical/v1/rcaeval/eval_only/` chỉ được liệt kê (tên, kích thước, thời gian), không đọc nội dung.
- Ba mức được tách theo yêu cầu: (1) quyền truy cập hoặc sự tồn tại; (2) bằng chứng đã đọc nhãn hoặc kết quả; (3) bằng chứng đã dùng chúng để chọn phương pháp hay tinh chỉnh.
- Quy mô RE2-OB trong split `within-rcaeval-grouped-0-e9b2c81c`: 21 injection vai test (test-matrix §2; khớp đếm `02-h1-membership-03`). Mọi bảng tổng gộp của vai test RCAEval (218 injection) **có chứa** 21 injection này.

## Kết luận ngắn

- **Kết quả LLM hay R-a trên test: chưa thấy lộ trên máy này.** Không có lần chạy LLM thật nào trên dữ liệu thật; chỉ có mock và fixture.
- **Kết quả riêng của RE2-OB test: không thấy bằng chứng đã đọc. Đầy đủ thì không xác định được.** Không tài liệu nào chứa số riêng RE2-OB, và bảng tóm tắt không tách theo hệ. Nhưng tệp kết quả từng ca có chứa các ca RE2-OB test, và không có nhật ký truy cập để loại trừ việc chúng từng bị mở.
- **Tổng gộp vai test RCAEval có chứa 21 ca RE2-OB: đã lộ.** Đây là kết quả của baseline không-LLM và của các audit đọc nhãn, đọc ngày 2026-10-18 đến 2026-10-20, trước quyết định D12 (2026-10-26). Một phần đã được dùng để chọn **hướng nghiên cứu** (ưu tiên câu hỏi 4 thấp hơn H1). Chưa thấy chúng được dùng để chọn hay tinh chỉnh prompt, builder, ngưỡng, comparator hay cải tiến IM1/R-a.
- Theo D12, lần lộ này được ghi đúng như trên và **không** được mô tả là đã khôi phục tính mù. Đây là phát hiện thuộc cổng S1; phương án xử lý ở mục 4.

## 1. Mức 1: quyền truy cập và sự tồn tại

| Nguồn | Vai | Nội dung | Bằng chứng |
|---|---|---|---|
| `nt114-rca/nt114-rca/data/canonical/v1/rcaeval/eval_only/labels.jsonl` | mọi vai | nhãn | tồn tại trên đĩa, đọc được bởi mọi tiến trình trong phiên; vùng eval-only theo data contract §2 |
| `data/splits/within-rcaeval-grouped-0-e9b2c81c/split.json` | test | số ca theo tầng `hệ \| họ lỗi` của vai test (suy từ nhãn) | khối `counts.test.by_stratum`, đọc thấy khi xem cấu trúc split trong lượt này |
| `results_baselines_rcaeval/baselines.jsonl` (4,1 MB, 2026-10-19 02:38) | val, test | kết quả từng ca của B0, B1, B1m, B3, BARO-style | `configs/exp/baselines-rcaeval.yaml`: `split_roles: [val, test]`, mọi điều kiện |
| `results_visibility/rcaeval/evidence_visibility.jsonl` (2026-10-18 23:31) | val, test | gốc có được nêu tên trong bằng chứng (đọc nhãn) | `configs/exp/visibility-rcaeval.yaml`: `split_roles: [val, test]`, ghi "label-reading" |
| `results_store/rcaeval/leakage_near_duplicates.jsonl` (2026-10-19 09:24) | val, test | ca store gần nhất có cùng (gốc, lỗi) với ca truy vấn không (đọc nhãn) | `configs/exp/store-rcaeval-grouped.yaml`; data contract §7.6 |
| `results/canonical_pilot/` (2026-10-14) | test (`within-rcaeval-grouped-0`, RE2+RE3, 10 ca mỗi hệ) | chỉ `ablation_log.jsonl` và `evidence/`; **không** có tệp kết quả LLM | `configs/canonical_pilot.yaml`; `results/llm_cache.sqlite` 12.288 byte (SQLite rỗng); `phase-09-11-audit-splits-integration.md:94` ghi "prepare ... no LLM call" |
| Các lưới có LLM: `results_smoke*/`, `results_v7/nezha/`, `plans/review-runtime-261019-2254/**` | — | mock và fixture | `manifest.json` của smoke ghi backend `mock`; `results_v7` theo `configs/exp/v7-nezha-mock.yaml`; review-runtime là thư mục pytest |
| `results_dev_pilot/`, `results_dev_sampling/` | val | — | không tồn tại; config ghi "NOT RUN YET" |

## 2. Mức 2: bằng chứng đã đọc nhãn hoặc kết quả

| Đã đọc | Phạm vi | Bằng chứng | Có số riêng RE2-OB? |
|---|---|---|---|
| AC@1 của baseline không-LLM trên vai test RCAEval | 218 injection, `full` và vài điều kiện | `research/05_evidence_instrument_audit.md` §V3 (vd. B1m 148/218; B1 traces 16/69; B1m `no_metric` 15/108); bảng BARO-style vs B1 cho test `full`, `blind_root`, `blind_nonroot_ev` | Không: `baselines.py:193,221` gom theo `dataset × split_role × condition`; grep `RE2-OB` và `online-boutique` trong `research/*.md` không có kết quả |
| Tỷ lệ gốc được nêu tên trên vai test RCAEval | 218 và 108 bản ghi | `research/04_evidence_visibility_results.md`; `plans/reports/research-261019-1629-de-xuat-huong-cau-4-cho-nam-xem.md` (vd. 216/218 ở `full`, 42/108 không nêu tên ở `no_metric`) | Không: `visibility.py:123` gom theo `dataset × split_id × split_role × condition` |
| Cờ gần trùng văn bản (có so nhãn) trên vai test | theo vai × điều kiện | `research/05` §V6; `leakage_audit.py:86` gom theo `split_role × condition` | Không |
| Cấu trúc cụm của vai test (số bản ghi, số injection) | RCAEval, Nezha, RCA100, AIOps2025 | `research/06_statistics_validation.md` ghi "The outcomes are simulated; the structure is real" | Không dùng kết quả; chỉ cấu trúc |
| Kết quả từng ca của baseline hay audit nói trên | — | **Không xác định được.** Không có nhật ký truy cập tệp; transcript các phiên trước không được rà toàn bộ trong lượt này | — |
| Kết quả bất kỳ trên máy GPU hay máy khác | — | **Không xác định được.** Chỉ kiểm được máy này. `configs/hardware/rtx4080-laptop-12gb.yaml` ghi "owner-reported, not yet probed" và các config DEV ghi "NOT RUN YET", nhưng đó là ghi chú, không phải bằng chứng là chưa chạy | — |

Các số khớp chuỗi `0.679` và `148/218` trong `plans/261019-1045-*/work/h1-candidates.csv` và `plans/261024-0858-*/work/records/search-D7-a01.csv` là trùng ký tự ngẫu nhiên (ECE 0.6797 của một bài; một bản ghi OpenAlex), không phải trích số test.

## 3. Mức 3: bằng chứng đã dùng để chọn phương pháp hay tinh chỉnh

| Quyết định | Có dùng kết quả hay nhãn vai test? | Bằng chứng |
|---|---|---|
| Thêm comparator B1m | **Không thấy**: B1m được thêm ngày 2026-10-18, trước khi chạy baseline V3 ngày 2026-10-19 | `decisions.md` dòng 2026-10-18 "Protocol v2 skeleton written ... (B1m added ...)"; `phase-05-leakage-and-baseline-fairness.md` định nghĩa B1m theo cấu trúc bằng chứng; mốc tệp `results_baselines_rcaeval` 2026-10-19 |
| Câu hỏi 4 xếp sau H1; P1 bắt buộc, P2 thăm dò, P3 không triển khai (2026-10-20) | **Có, ở mức hướng nghiên cứu**: đề xuất dùng tỷ lệ nêu tên trên vai test RCAEval (2/218 thiếu tên ở `full`) để lập luận câu hỏi 4 ít quan trọng trên bộ chính | `research-261019-1629-de-xuat-huong-cau-4-cho-nam-xem.md` dòng 13, 56, 66; `decisions.md` các dòng 2026-10-20 |
| Tiêu chí và ngưỡng P2 | **Không**: chốt trên DEV | `decisions.md` dòng 2026-10-20 "P2 criteria ... frozen on RCAEval DEV" |
| Chọn RCLAgent, nhánh (a), IM1 | **Không thấy**: chọn từ tổng quan tài liệu (phễu T0 → T3) và số đếm độ phủ modality | kế hoạch `261024-0858-*`; 69/108 là số đếm modality, kiểm lại không nhãn ở `02-h1-membership-03` |
| MDE và power | Cấu trúc vai test, kết quả mô phỏng | `research/06` |
| Prompt, builder, ngưỡng, độ tin cậy | **Không thấy**: chưa có lần chạy LLM thật; prompt `v1`, `BUILDER_VERSION = 3` không đổi theo kết quả test nào được ghi | protocol v2; `evidence.py` |
| Nhận định "kết quả LLM trên RCAEval phải đọc so với 148/218" | Dùng số test làm **mốc đọc**, chưa là quyết định | `research/05` §V3; cổng S4 của plan này so với B1m trên **DEV**, không trên test |

## 4. Phương án xử lý (cổng S1; chủ dự án chọn, tôi không tự áp dụng)

1. **Ghi nhận và tiếp tục.** Ghi lần lộ ở mức tổng gộp baseline không-LLM và audit đọc nhãn vào hồ sơ M5 và phần giới hạn của bài. Giữ 21 injection RE2-OB test trong mẫu số. Mọi kết quả từ nay theo D12 nghiêm. Không mô tả là đã khôi phục tính mù.
2. **Như (1), cộng một kiểm độ nhạy khai báo trước.** Báo kết quả H1 và C-1 cả có và không có RE2-OB test như phân tích độ nhạy, không thay phân tích chính. Không đổi split.
3. **Dựng lại split hoặc đổi tập test.** Không khuyến nghị: tổng gộp đã lộ trải trên cả 218 ca test, nên đổi riêng RE2-OB không giải quyết; còn đổi toàn bộ split sau khi đã thấy số thì đó là chọn split theo kết quả. Theo yêu cầu, tôi không tự đổi split hay loại ca.

Phương án tôi đề xuất là (1). Lần lộ chỉ gồm baseline không-LLM và audit đọc nhãn, không có kết quả của phương pháp sẽ kiểm. Thêm (2) chỉ khi chủ dự án muốn báo riêng phần RE2-OB.

## 5. Giới hạn của lần kiểm này

- Chỉ kiểm máy này và các tệp hiện có. Không có nhật ký truy cập tệp nên "không thấy bằng chứng đã đọc" không phải "chưa từng đọc".
- Không rà toàn bộ transcript các phiên trước. Chỉ dùng tài liệu, config, manifest và mốc tệp.
- Không mở nội dung bảng hay tệp kết quả để kiểm phần ở trên.
