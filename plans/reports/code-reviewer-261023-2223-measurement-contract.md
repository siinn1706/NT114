# Review hợp đồng đo lường — NT114/RCA

## Scope

- Đọc `llms.txt`, protocol v2, decision log, `analyze.py`, `llm.py`, `confidence.py`, `selective.py`, `configs/exp/dev-pilot.yaml` và audit `review-261019-2254-pretrain-final-audit.md`.
- Review chỉ đọc; không chạy lại probe/test, không sửa source hoặc frozen input.
- Mục tiêu: kiểm tra xem estimator/guard hiện tại có đủ để nói “tốt hơn phương pháp gốc” hay chưa, và xác định ranh giới H1 với mục tiêu AIOps 24/24.

## Kết luận

Checkout hiện tại là hạ tầng đo lường cho một thí nghiệm single-LLM RCA offline. `llms.txt:3,7-11` và `dev-pilot.yaml:1-18,28-37` xác nhận zero-shot, một model, DEV RCAEval, pilot chưa chạy; đây chưa phải trainer hay vòng monitor–detect–repair–verify–rollback. H1 hiện là **đánh giá thực nghiệm về selective risk của các score có sẵn**, chưa phải một phương pháp mới: decision log cấm triển khai H1 trước literature review (`decisions.md:7-10`), phase 03 nói rõ “implements none of their methods” (`phase-03-evaluation-core.md:20-24`), và protocol vẫn để H1 là candidate, novelty chưa xác minh (`protocol-v2.md:153-166`). Fixed-coverage `gain_exact@0.7` là endpoint đã được owner chấp nhận; vấn đề cần giữ rõ là ranh giới diễn giải với policy threshold fit trên DEV.

## Findings

### P1 — Headline có thể dùng nguồn DEV không tương thích

`selective_table` chỉ ghép DEV/test theo dataset, granularity, set-scored, model, condition, retrieval và store mode (`analyze.py:249-293`); không kiểm tra backend, revision, `server_fp`, `exec_sig` hay sampling. Sau khi tách `val`, `guard_headline` chỉ kiểm tra `main` (`analyze.py:395-406`). Audit trước đã tái hiện DEV mock/revision khác vẫn được dùng để fit threshold; không cần lặp probe (`review-261019-2254-pretrain-final-audit.md:23-31`).

**Impact:** một threshold được fit từ nguồn không tương thích không đại diện cho policy chuyển từ DEV sang test.

**Fix:** lưu và so khớp identity đầy đủ của source DEV với target test; mismatch phải thành `no_source`/hard fail. Thêm negative tests cho backend, revision, sampling, prompt và server fingerprint.

### P1 — Bảng baseline chính trộn DEV vào test

Nhánh `joint_baselines` đã loại `split_role=val`, nhưng `table_baselines` đọc toàn bộ baseline có điểm rồi group theo dataset/model/condition, không lọc `split_role`, granularity hoặc `excluded_from_primary` (`analyze.py:306-314,317-328,433-436`). Audit trước đã tái hiện DEV AC@1=1 và test AC@1=0 bị xuất thành 0.5 (`review-261019-2254-pretrain-final-audit.md:33-41`).

**Impact:** baseline trong headline không còn là cùng population với LLM test, nên không thể dùng làm comparator cho claim “better than baseline/original”.

**Fix:** áp dụng cùng population mask của `main` trước khi tạo bảng baseline, giữ split/granularity trong output và thêm regression test DEV/test mixed.

### P2 — Ranh giới diễn giải của score `verbal`

Prompt yêu cầu mỗi completion báo xác suất `ranking[0]` đúng (`llm.py:26-33`). Nhưng `aggregate` tạo đáp án cuối bằng Borda (`llm.py:291-300`) rồi lấy trung bình confidence của các completion (`llm.py:296-302`). Registry lại đánh dấu `verbal` là probability (`confidence.py:38-46`), và `cell_table`/`confidence_endpoints` tính Brier, ECE, gap của score đó với correctness của **Borda winner** (`analyze.py:135-153`).

**Impact:** Brier/ECE/overconfidence gap của `verbal` trộn hai estimand: xác suất cho từng sample top-1 và xác suất cho đáp án aggregate. Đây là giới hạn diễn giải, chưa phải lỗi khiến score không được đo: kết quả hiện tại có thể được báo cáo như một score thực nghiệm, nhưng không tự động là xác suất đã calibrated cho Borda winner.

**Action:** nếu dùng từ “calibration”, phải ghi rõ target là per-sample hay aggregate winner; nếu không, gọi đây là empirical confidence/error-detection score và giữ `consensus` là estimator riêng.

### Claim boundary — fixed-coverage estimand và DEV-fit policy

Decision log đóng H1 ở `gain_exact@0.7` (`decisions.md:24-26`). Hàm `gain_exact` xếp score trên chính test cell, cắt tie group theo phần trọng số và tính risk bằng nhãn (`selective.py:364-376,407-413`). Ngược lại, threshold DEV được fit rồi áp vào test, với coverage thực tế có thể khác mục tiêu (`selective.py:251-280,283-302`; `analyze.py:249-303`).

**Boundary:** `gain_exact@0.7` kiểm tra khả năng xếp hạng confidence ở coverage cố định; fractional tie là phần của owner contract và không cần đảo. Nó không phải bằng chứng rằng threshold cố định từ DEV đạt đúng 0.7 khi chạy test. Hai kết quả trả lời hai câu hỏi khác nhau: ranking quality và transfer/deployability.

**Action:** giữ `gain_exact@0.7` như endpoint H1 đã chấp nhận; báo riêng coverage đạt được, risk/CIs, C2 trên cùng cell và mọi `no_source`/shift cho DEV-fit policy. Không gộp hai diễn giải thành một claim triển khai.

### P2 candidate — Parser có thể cho phép ranking trùng lặp

JSON schema giới hạn `maxItems: 5` nhưng không có `uniqueItems` (`llm.py:47-59`). `parse` chỉ lọc token thuộc candidates, không kiểm tra trùng lặp (`llm.py:271-283`); `aggregate` cộng Borda cho mọi phần tử (`llm.py:291-306`).

**Status:** đây là candidate contract risk, chưa phải finding đã tái hiện trên output vLLM trong lượt này. Nếu output thực tế có duplicate, điểm Borda/confidence có thể bị tăng giả.

**Action:** thêm test parser duplicate và kiểm tra một mẫu raw real-model trước khi nâng mức finding; không suy ra từ điểm này rằng L1 phải abstain cho mọi parse failure.

## Claim boundary và đường xuất bản

- Comparator hiện có là B0/B1/B1m/BARO-style/B3 và L0/L1/C1/C2/C3/O (`protocol-v2.md:61-75`). BARO còn là baseline có điều kiện; DecompRCA là related work/H3 boundary, số công bố không được đặt cùng cột nếu chưa khớp incident IDs, preprocessing, split, granularity và candidate set (`decisions.md:12,17-18`; `protocol-v2.md:162-166`). PACE-LM/LM-PACE là prior gần cho confidence, nên H1 chỉ có thể tuyên bố ô giao mới sau khi kiểm literature, không tuyên bố confidence-RCA mới hoàn toàn.
- Đường publishable tối thiểu: sửa hai lỗi population P1, làm rõ target của `verbal`, giữ fixed-coverage H1 theo owner contract, rồi chạy real DEV pilot theo config đã ghim → chốt estimator, population, family và preregistration trước test → chạy test riêng từng dataset/stratum, baseline cùng split, CI/multiplicity và transfer threshold → báo cáo là empirical evaluation nếu không thêm policy/estimator mới.
- Nếu mục tiêu là AIOps 24/24, cần một workstream khác cho alert ingestion/detection, online retrieval, typed proposal/action, authorization, post-change health gate và rollback. Các bảng hiện tại chỉ trả lời RCA/abstention trên dữ liệu đã có, không chứng minh vòng vận hành đó.

## Overall assessment

Chưa có cơ sở để gọi kết quả hiện tại là “tốt hơn phương pháp gốc”. Old Jev đã bị loại bỏ (`decisions.md:7`), chưa có before/after run; H1 chưa phải method implementation, và hai P1 population contracts còn cho phép comparator/threshold sai estimand. Fixed-coverage H1 vẫn là owner-approved empirical endpoint; score `verbal` và parser duplicate cần diễn giải/kiểm chứng đúng mức. Sau khi P1s được sửa và real-model DEV/test chạy đúng, H1 có thể thành một bài đánh giá selective confidence có điều kiện; novelty vẫn phải giữ trạng thái chưa xác minh cho tới khi literature/preregistration và kết quả thực nghiệm hoàn tất.

### Unresolved questions

- “Phương pháp gốc” là Jev cũ hay một baseline công bố (BARO/LLM/evidence-order)? Mỗi cách cần comparator và claim khác nhau.
- H1 muốn chứng minh ranking confidence ở coverage cố định hay policy threshold chuyển từ DEV? Không được dùng một endpoint cho cả hai.

Status: DONE_WITH_CONCERNS
Summary: H1 hiện là measurement/evaluation study, chưa là novel method; hai P1 population gaps đã được xác nhận, còn verbal/parser issues là interpretation or candidate risks.
Concerns/Blockers: Real-model DEV/test và preregistered confirmatory family chưa có trong checkout; 24/24 operational coverage nằm ngoài scope code hiện tại.
