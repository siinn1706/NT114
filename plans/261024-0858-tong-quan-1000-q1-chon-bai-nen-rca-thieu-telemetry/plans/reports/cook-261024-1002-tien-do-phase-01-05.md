# Tiến độ nckh-cook --auto: phase 01–05 (24/10/2026)

Kế hoạch: [plan.md](../../plan.md), giao thức [protocol.md](../../protocol.md), frozen-261024, SHA-256 `ca65919f18ecc443548b2fea38c9b57a4e08ab1fbeeb86859a42243c0f36005d`; văn bản protocol không đổi sau freeze. State: `work/state.json`.

## Kết quả

Phễu mới chạy được trên seed, tức corpus cũ đã xác minh lại. Chiến dịch tìm kiếm (phase 03) bị chặn vì OpenAlex hết hạn mức, nên chưa có T0 đầy đủ và chưa thể chốt T1. Phase 06–10 chưa bắt đầu, có chủ đích: theo luật late-record (§5), chấm F trên T1 tạm sẽ khóa các bài từ search ra khỏi T1.

| Phase | Trạng thái | Số liệu chính | Receipt |
|---|---|---|---|
| 01 | xong | Protocol freeze, SJR 2025 là ấn bản mới nhất | `01-freeze-01` |
| 02 | xong | Seed 4.049 dòng, 141 không tìm thấy (135 DOI arXiv) | `02-reuse-seed-01`, `02-reuse-extras-01` |
| 03 | blocked | Chỉ có trang 1 của A1, chưa commit | `03-search-01..03` (exit 1) |
| 04 | một phần (seed) | T0 seed = 338 bản ghi | `04-build-t0-seed-04`, `04-t0-review-seed-02` |
| 05 | một phần (seed) | 338 bản ghi đã screening; T1 tạm có 85 bài đủ điều kiện | `05-merge-seed-s1-01`, `05-kappa-seed-01`, `05-rank-seed-01` |
| 06–10 | chưa bắt đầu | Phụ thuộc T1 cuối | — |

## Đã xác minh

- **Kiểm sai âm cổng chủ đề §4.**
  - Lần 1: 2/25 ở tầng giáp ranh (DBMind; survey phân tích lỗi hệ AI), 0/25 ở tầng không khớp. Vượt ngưỡng nên phải sửa regex. Bằng chứng: `work/t0seed2-fn-check.json`.
  - Amendment sau freeze (`work/amendments.md`) thêm `databases?`, `DBMS`, `AI systems?` vào `SYSTEM_RE`.
  - Hiệu chỉnh lại: R3 55/58 và R2 129/147 không đổi; R0 lọt 80 → 94 (`work/regex-calibration-04.json`).
  - Kiểm lại trên tập loại mới: 0/25 và 0/25; cận trên Clopper-Pearson 95% là 0,137 cho mỗi tầng (`work/t0seed4-fn-check.json`).
- **Kiểm tay Q1 trên 30 bản ghi T0 ngẫu nhiên:** 30/30 đúng journal, category CS-Q1, năm và loại bài (`work/t0seed4-q1-check.md`).
- **Dossier nckh-literature:** 9 file × tối đa 40 bản ghi (trần import của công cụ), tổng 338. `check-literature.py` exit 0 cả 9 file, trạng thái `pass-for-structure-and-bindings`.
- **Screening s1:** 7 phiên nckh-maker, mỗi phiên một batch 50 bản ghi.
  - Kết quả: include 85, exclude 162, needs-review 58, context-survey 33.
  - File đúng định dạng và đủ bản ghi (`work/screen/seed-s1-check.json`).
  - Bản ghi neo có 1 lệch R1 (survey phân tích log, phiên seed-001). Đã rà lại, không thấy lệch có hệ thống (`work/screen/seed-s1-drift-review.md`).
- **Mẫu kép s2, blind, n = 90:**
  - κ include trên 32 dòng có abstract = 1,0, đạt ngưỡng 0,7.
  - Khớp tuyệt đối R1 0,93, R2 0,98, R3 0,99.
  - 1 bất đồng; đọc lại thì giữ `context-survey` theo E5 (`work/screen/kappa-seed.json`).
- **T1 tạm (`work/records/seed-t1-ranked.csv`):** 85 bài include có R1 ≥ 2; không cần bù `fill-r1`; không có bài nào đủ điều kiện `reserve-nonllm` vì toàn bộ đã nằm trong top.
  - 22 bài có R2 ≥ 1; 10 bài có R1 = 3 và R2 = 2.
  - 10 bài có R3 ≥ 1.
  - 43 bài có `oa_url`.
- **Receipt:** 39/49 receipt phase 04–05 qua `check-receipt.py verify`. 10 receipt fail, tất cả có lý do đã biết:
  - 8 receipt checkpoint ghi `work/state.json`, file này đổi ở các lần checkpoint sau.
  - Đối số `--note` chứa dấu `;` nên checker coi là lệnh ghép, dù lệnh chạy dạng argv với `shell=False`.
  - `04-checkpoint-seed-01/02` exit 1 thật: lỗi so sánh kiểu exit_status, đã sửa và chạy lại thành `-03/-04`.
  - `04-regex-calibration-03` và `04-build-t0-seed-03` chạy trước khi bản sửa regex được ghi vào code, nên chỉ tái tạo kết quả regex cũ; không dùng làm bằng chứng (đã ghi trong amendments).

## Chưa chắc chắn và giới hạn

- T1 là tạm, chỉ phủ seed. Thứ hạng sẽ đổi khi có bản ghi từ search, snowball và khi 58 needs-review có abstract.
- κ = 1,0 tính trên mẫu nhỏ (32 dòng có abstract), hai người chấm cùng họ mô hình; protocol yêu cầu ghi đây là giới hạn.
- Chưa áp được mục "hạng 90–110" của mẫu kép vì mới có 85 bài đủ điều kiện.
- Có sai khác giữa protocol §4 (sai âm > 1 ở tầng giáp ranh thì amendment) và phase-04 (≤ 2/50). Tôi áp theo protocol vì protocol chặt hơn và là nguồn quy tắc chính.
- Lệch quy trình từ báo cáo của người chấm: phiên seed-001 thấy một phần batch trước khi ghi file neo; phiên seed-003 sửa R5 của một neo trước khi đọc batch. Cả hai đều không đổi quyết định hay R1 của neo.
- Screening chia theo nhóm nguồn: seed trước, bản ghi search sẽ thành batch mới (script bỏ qua ID đã chấm). Thứ tự này là hoán vị seeded trong từng nhóm, không phải một hoán vị duy nhất trên toàn T0.

## Waiting-human (làm sau, theo plan §7)

1. **OpenAlex.** Cursor paging cần API key (lỗi 401); hạn mức không key của ngày 24/10 đã hết (429, Retry-After khoảng 21 giờ tính từ khoảng 09:55). Có hai cách: chủ dự án cung cấp API key miễn phí, hoặc chạy lại `search-openalex-cursor.py` sau khi hạn mức reset (script tự bỏ qua batch đã commit). Snowball cũng cần OpenAlex.
2. **58 bản ghi needs-review thiếu abstract (E6).** Gồm 50 bài Elsevier, 6 Springer, 2 IEEE CS. ScienceDirect hiện CAPTCHA, tôi không vượt; Springer chuyển hướng sang trang xác thực. Cần chủ dự án dán abstract, hoặc mở trang để tôi đọc. Không làm được thì các bản ghi này bị loại `E6-no-abstract` theo §6. Một số tiêu đề đúng chủ đề rõ ràng (KGroot, SinkFlow, TCRCA, MODIFy).
3. **Elicit:** hết quota đến 18/11/2026.
4. **Các mục treo từ trước:** tải tay PDF sau paywall (phase 06), quyết định PR-06 về category Engineering, cờ `h1-compat`.

## Tiếp tục ở phiên sau

1. Khi OpenAlex khả dụng: chạy phase 03 hết 17 truy vấn.
2. Chạy lại phase 04 với `search-*.csv`: abstract fill, review title-only, kiểm sai âm và Q1 trên tập mới, dossier.
3. `make-screen-batches.py <T0> search`, screening các batch mới, mẫu kép bổ sung, snowball vòng 1, rồi §10 nếu N(T0) < 1.000.
4. Xếp hạng lại; chỉ sang phase 06–07 khi T1 đã chốt.
