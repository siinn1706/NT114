# Tổng quan 1.000 bài Q1 và chọn bài nền cho MVP RCA thiếu telemetry, v2

Ngày 2026-10-26 (Asia/Saigon). Kế hoạch: `plans/261024-0858-tong-quan-1000-q1-chon-bai-nen-rca-thieu-telemetry/`. Giao thức: `protocol.md`, đóng băng ngày 2026-10-24, SHA-256 ca65919f…

v2 sửa theo review cuối phase 10 ([final-review.md](../../research/final-review.md)); bản v1 giữ ở [research-261026-0430-tong-quan-1000-q1-chon-bai-nen-v1.md](research-261026-0430-tong-quan-1000-q1-chon-bai-nen-v1.md). Mọi đường dẫn `work/...`, `research/...`, `design/...` trong backtick tính từ thư mục kế hoạch. Số dẫn xuất (precision, Wilson, `q1_weak`, bão hòa, hash giao thức) lấy từ `work/report-stats-10.json` (receipt `10-report-stats-01`).

## Kết luận

- **Bài nền đề xuất: RCLAgent.** Tên bài: *Toward In-Depth Root Cause Localization for Microservices With Multi-Agent Recursion-of-Thought*, IEEE TDSC 2026, doi 10.1109/tdsc.2026.3706572.
  - Nhãn `single-eligible`: trong 10 bài đọc sâu, chỉ bài này qua đủ năm cổng G1–G5.
  - Trạng thái là `pending-personal-review`: việc chấp nhận bài nền thuộc chủ dự án.
  - Hai xung đột với quyết định của chủ dự án đang ở `waiting-human` (plan §2), tách khỏi việc chấp nhận bài: (1) phương pháp gọi model nhiều lần, trái bất biến "một lời gọi" của protocol v2 §1; (2) với `no_trace` phương pháp thoái hóa, ảnh hưởng H1. Báo cáo không tự chọn nhánh nào.
- **Lý do chọn.** Bài có repo công khai với license MIT, README có lệnh chạy và dữ liệu mẫu (G1). Dữ liệu đánh giá RCAEval RE2-OB đã có trong bundle NT114 (G2). Code gọi LLM qua endpoint tương thích OpenAI, nên về mặt giao diện có thể trỏ tới một model open-weight cục bộ (G3); đây chỉ là ước lượng tĩnh từ code, chưa có độ chính xác hay độ trễ nào với backbone mở nhỏ. Mọi agent dùng chung một backbone (G4). Bài dùng cả trace, metric và log (G5).
- **Giới hạn.**
  - Về điểm F, RCLAgent chỉ ngang nhóm đầu: một mình hạng 1 ở 2/18 kịch bản độ nhạy, còn DiagFusion ở 3/18.
  - Bài chưa thử backbone nào dưới 32B. Với backbone mở, kết quả kém hẳn: Llama-3.1-70B đạt MRR 7–19 và DeepSeek-R1-Qwen-32B 36–65, so với Claude 55–89, đo trên các tập con AIOps2022, không phải RE2-OB (Table III; `research/selection-memo.md` mục 5; `design/reproduction-protocol.md` T10).
  - Số đích chính trên RE2-OB (Table I) dùng Qwen-3.6-Plus qua API đóng (`design/reproduction-protocol.md` T1–T5).
  - Tuyên bố "vượt mọi SOTA" bị phản chứng: BARO thắng R@3 và R@5 trên RE2-OB, Nezha thắng MRR trên Train-Ticket (`design/reproduction-protocol.md` T11, verdict contradicted).
  - Phương pháp gọi model nhiều lần cho mỗi span.
  - Khi không có trace (`no_trace`), phương pháp thoái hóa thành một ReAct agent. Trên pool H1, RCLAgent chỉ xác định được ở 69/108 injection (64%) (`design/test-matrix.md`, C-3).
  - Bản đã đọc là preprint arXiv v1.
- **Điều kiện có thể đảo đề xuất:**
  - chủ dự án giữ bất biến "một lời gọi" của protocol v2 và coi phần đệ quy là lõi không thể bỏ;
  - bản TDSC có số liệu khác đáng kể so với arXiv v1 (chưa định nghĩa dung sai bằng số; chủ dự án quyết khi có bản TDSC);
  - G1 được nới bằng amendment, khi đó §8 chuyển sang nhánh ≥ 2 bài đạt và top-2 không ổn định.

Chi tiết lập luận: [selection-memo.md](../../research/selection-memo.md) v2. Trạng thái từng tiêu chí chấp nhận của plan §4 kèm receipt: [gate-matrix.csv](../../work/gate-matrix.csv). Bàn giao: [handoff.md](../../work/handoff.md).

## Phễu (PRISMA)

| Bước | Số | Nguồn |
|---|---|---|
| Bản ghi duy nhất từ seed, tìm kiếm và snowball sau khử trùng | 14.422 | `work/records/t0r2b-summary.json` |
| Loại ở cổng Q1, quy tắc Q-7, năm, loại tài liệu, chủ đề và ngôn ngữ | 13.007 | cùng file, `exclude_reasons_multi` |
| Giữ tự động | 1.053 | cùng file |
| Cần xem tiêu đề, sau đó giữ | 362, giữ 32 | `work/records/t0r2b-t0-review-decisions.csv` |
| **T0** | **1.085** | `work/records/t0r2b-t0.csv` |
| Quyết định screening: include / exclude / needs-review / context-survey | 121 / 741 / 152 / 71 | `work/records/final-t1.json` |
| **T1** (include với R1 ≥ 2, lấy 100 đầu) | **100** | `work/records/t1-top100.csv` |
| Có toàn văn | 34 (22 bản tạp chí, 12 preprint) | `work/access-ledger-final.csv` |
| Qua cổng T2 trong 34 bài có điểm F | 20 | `work/appraisal/f-scores.csv` |
| **T2 → T3** | **10** | `work/records/t2-top10.csv` |
| Qua đủ G1–G5 | 1 | `work/decision-matrix.csv` |

- Định nghĩa Q1 (protocol §3): tạp chí (`Type == journal`) có quartile **SJR 2025 của tạp chí** là Q1 ở ít nhất một trong 13 category CS (Q-4); không theo quartile năm xuất bản, không phải JCR.
- Lý do loại không loại trừ nhau, nên tổng các mã lớn hơn 13.007. Ba mã lớn nhất: không có ISSN trong SJR (7.419), lệch chủ đề theo metadata (4.470), không phải Q1 (2.716).
- Báo riêng theo Q-4/Q-7: 2.000 lượt loại `Q-4-q1-noncs` (Q1 nhưng không ở category CS); 826 lượt loại `Q-7-mdpi` (quy tắc publisher, không phải "không Q1"); trong T0 1.085 có 160 bản ghi `q1_weak = 1` (IEEE Access, Scientific Reports).
- Đường bão hòa (`work/saturation-curve.json`): seed cho 338 bản ghi; tìm kiếm thêm 525; snowball vòng 1 có 105 bản ghi mới và 1 bản ghi rời T0 (W3005115843), tăng ròng 104; snowball vòng 2 cùng truy vấn đồng nghĩa thêm 118, đưa tổng lên 1.085. Trường `new` của file đếm bản ghi mới, không phải tăng ròng.
- Precision T0 = 121/1.085 ≈ 0,112, khoảng Wilson 95% [0,094; 0,132], nên N × precision ≈ 121, dưới ngưỡng 500 của §10. Giới hạn này đã ghi trong `work/amendments.md` (số 0,12 và 130 ở đó là ước lượng trước khi T1 chốt; đính chính có ghi ngày 2026-10-26).

## Giao thức và amendment

- Giao thức đóng băng lúc 2026-10-24T02:34:10Z (`work/protocol-freeze.json`). Hash `protocol.md` trên đĩa ngày 2026-10-26 vẫn trùng hash đóng băng (receipt `10-report-stats-01`).
- Amendment sau freeze (`work/amendments.md`):
  1. Ngày 2026-10-24, thêm từ khóa cho nhóm Hệ thống của regex chủ đề (`SYSTEM_RE`) sau khi kiểm sai âm thấy 2/25 sai âm ở seed.
  2. Bảng truy vấn đồng nghĩa S1–S7 cho §10 bước 2, soạn trước khi chạy. Mệnh đề chẩn đoán của S4 được siết sau probe-01 (độ phủ 0,797).
- Sau review, phase 08 sửa một số ô cổng G cho nhất quán, ghi ở `work/t3-gate-corrections-a02.csv`. Câu chữ cổng không đổi; hai ô chuyển sang đạt (Topo-MFP G2 nhờ bản re-upload của cộng đồng trên Zenodo; RCRank G4), một ô chuyển sang trượt (CHASE G1). Tập bài qua đủ cổng không đổi.

## Mười ứng viên T3

| Bài | G1 | G2 | G3 | G4 | G5 | F T2 → T3 | Hạng F T3 (khi bỏ cổng) |
|---|---|---|---|---|---|---|---|
| DiagFusion (TSC 2023) | ✗ | ✓ | ✓ | ✓ | ✓ | 25 → 25 | 1 |
| **RCLAgent (TDSC 2026)** | ✓ | ✓ | ✓ | ✓ | ✓ | 25 → 25 | 2 |
| UDA-RCL (TSC 2025) | ✗ | ✓ | ✓ | ✓ | ✓ | 25 → 24 | 3 |
| Topo-MFP (JKSU-CIS 2026) | ✗ | ✓ | ✓ | ✓ | ✓ | 23 → 24 | 4 |
| CausalRCA (JSS 2023) | ✓ | ✓ | ✓ | ✓ | ✗ | 22 → 23 | 5 |
| ThinkFL (TOSEM 2026) | ✗ | ✓ | ✓ | ✓ | ✓ | 24 → 23 | 6 |
| CHASE (TBDATA 2026) | ✗ | ✓ | ✓ | ✓ | ✓ | 21 → 21 | 7 |
| RCRank (PVLDB 2024) | ✗ | ✓ | ✓ | ✓ | ✓ | 21 → 21 | 8 |
| TAMO (TSC 2025) | ✗ | ✓ | ✓ | ✓ | ✓ | 21 → 19 | 9 |
| Edge PPR (TSC 2026) | ✗ | ✓ | ✓ | ✗ | ✓ | 18 → 18 | 10 |

- Nguồn: `work/decision-matrix.csv`. Card từng bài ở `research/cards/t3/`; artifact ở `work/artifact-audit.csv`; evidence ở `work/evidence-ledger.csv`; prior work ở `work/prior-work-t3.csv`.
- G1 là cổng trượt nhiều nhất (8/10): repo không có file license, hoặc không có code và checklist thiếu.
- G3 đạt ở cả 10 bài nhưng chỉ là ước lượng tĩnh.
- Mười bài đều là tạp chí Q1 SJR ở năm xuất bản; với bài năm 2026, dùng SJR 2025 thay thế (`work/q1-pubyear-check.csv`).

## Ma trận và độ nhạy

- Chạy 18 kịch bản trọng số cộng 5 kịch bản ±1 ở các ô có lệch kiểm chéo, trên cả 10 bài với cổng G bỏ qua (`work/sensitivity.csv`).
- Không bài nào giữ hạng 1 từ 15/18 kịch bản trở lên. Vì vậy hạng 1 theo F không ổn định; top-2 là DiagFusion và RCLAgent.
- Ở 13/18 kịch bản, RCLAgent bằng điểm bài đứng đầu và chỉ thua ở tie-break.
- Trên pool 20 bài của T2 (`work/sensitivity-t2-pool.csv`), bốn bài ngoài T3 vào top-10 ở ít nhất một kịch bản: QROOT, RPCA, BARO tăng cường và W4415944773. Toàn văn của cả bốn không nêu repo (F3_code = 0); chưa ai tìm repo và chưa đọc sâu.

## Thiết kế sau khi chọn (có điều kiện)

Bốn tài liệu ở `design/` đều mở đầu bằng điều kiện "chờ chủ dự án chấp nhận". Mỗi tài liệu đã qua hai vòng review ngữ cảnh mới.

- [reproduction-protocol.md](../../design/reproduction-protocol.md): tái hiện theo bốn giai đoạn, từ CPU không có LLM, tới code gốc, tới một LLM cục bộ, rồi bundle NT114.
  - Số đích là Table I trên RE2-OB.
  - Kết quả chính chấm theo `S-first`, tức một trace chỉ định trước. Cách chấm theo trace tốt nhất của tác giả (`S-best`) có tính oracle và chỉ dùng để so với bài.
  - 21 injection test được niêm phong tới mốc M5.
- [improvement-hypotheses.md](../../design/improvement-hypotheses.md): bốn giả thuyết.
  - IM1: khung phụ thuộc tĩnh dựng từ trace lịch sử, dùng khi `no_trace`.
  - IM2: thêm "blind node" cho service không có span.
  - IM3: lấy độ tin cậy từ chính lời gọi tổng hợp.
  - IM4: tool evidence lấy trước bằng code cho backbone 4–9B.
  - Kết quả tìm prior work trong 12 truy vấn OpenAlex/arXiv ngày 2026-10-25 UTC (`work/prior-work-improvements.csv`): IM3 "chưa thấy"; IM1, IM2, IM4 "trùng một phần". Đây không phải khẳng định tính mới.
- [test-matrix.md](../../design/test-matrix.md): đơn vị độc lập là injection; điều kiện thiếu telemetry theo protocol v2; dùng C-3 cho H1; MDE lấy theo anchor RCA100 với n = 70.
- [mvp-outline.md](../../design/mvp-outline.md): mốc M0–M5 và các quyết định D1–D13 của chủ dự án.

## Giới hạn của tổng quan

- Chỉ 34/100 bài T1 có toàn văn; trong top-30 chỉ 13/30. Có 17 bài top-30 cần chủ dự án tải tay, nên T2 có thể đổi khi có các bài này.
- 152 bản ghi needs-review thiếu abstract (E6), vì Elsevier dùng CAPTCHA và Springer cần đăng nhập.
- Precision của corpus thấp (N × precision ≈ 121). Làn Elicit không chạy vì hết quota, reset 2026-11-18T16:00Z (`work/provider-status.csv` dòng 4).
- Cổng G được áp bởi năm lần chạy reader riêng; sau review, cách áp đã được làm nhất quán. Điều này dựa trên ghi chép của phiên điều phối (`research/selection-memo.md` mục 8), không có receipt định danh agent. G3 chưa được đo thật.
- Về receipt (`work/receipt-verify-10-a02.csv`, receipt `10-receipt-verify-02`): 264/310 verify được (gồm cả `10-receipt-verify-01`); 20 chỉ lệch `work/state.json` do checkpoint về sau (`superseded-state`); 18 lệch vì input/output được cập nhật về sau có ghi ngày (`changed-later`); 8 receipt checkpoint ở phase 04–05 (7 của làn seed, 1 là `04-checkpoint-full-02`) là lệnh ghép không ghi exit của từng đoạn. Các receipt 10-* tạo sau lần verify này (`10-sync-phase-status-01`, `10-report-stats-01`, `10-check-plan-01`) được kiểm riêng bằng `check-receipt.py` (ghi ở `work/handoff.md`).
- 8/10 card T3 (`research/cards/t3/*.md`) được sửa sau khi batch phase 08 commit, nên hash trong `work/state.json` cũ; các input của quyết định (`work/t3/*.csv`, `work/t3-gate-corrections-a02.csv`) vẫn khớp receipt `08-merge-t3-03`. Văn bản hiện tại của card không có receipt riêng. *Cập nhật 2026-10-26 (sau v2):* đối chiếu với transcript phiên trước cho thấy phần đổi chỉ là ghi chú điều phối nối vào cuối card (ghi chú hash và ghi chú sửa cổng); bỏ các ghi chú đó thì 8/8 card khớp đúng hash đã commit (`work/t3-card-delta-10.csv`, receipt `10-card-delta-01`). Các batch card được commit lại thành attempt a02, giữ a01.

## Bốn danh sách trạng thái

**Có sẵn trước attempt (existing-before-attempt).** Các nguồn này chỉ được đọc, không sửa:
- corpus và full text từ hai lần tổng quan trước: plan 261011 và plan 19/10 (`work/reuse-inventory.csv`);
- SJR 2025 CSV (hash 6f203999…);
- bundle và cấu hình `nt114-rca`;
- protocol v2 và `decisions.md` của plan 261018-2300.

**Tạo trong attempt này (created-this-attempt):**
- `protocol.md`, `work/` (records, screen, appraisal, t3, receipts, state) và `research/cards/t2|t3`;
- `research/selection-memo.md` v2 (giữ bản v1) và `design/*.md` (4 tài liệu);
- `work/gate-matrix.csv` và báo cáo này;
- trong phiên phase 10 ngày 26/10 (sau khi phiên trước chạm limit): `research/final-review.md`, `work/handoff.md`, `work/report-stats-10.json`, `work/receipt-verify-10-a02.csv`, `work/phase-status-sync-10.csv`, script `work/scripts/report-stats.py` và `sync-phase-status.py`, các receipt `10-report-stats-01`, `10-receipt-verify-02`, `10-sync-phase-status-01`, `10-check-plan-01`;
- file full text ở `private/fulltext/261024/` (gitignored) và file artifact ở `F:/Nam/UIT/nt114-paper-artifacts/`, cả hai nằm ngoài phần được theo dõi của repo.

**Đã kiểm trong attempt này (verified-this-attempt):**
- 264/310 receipt verify được (`work/receipt-verify-10-a02.csv`, receipt `10-receipt-verify-02`; lần đầu `10-receipt-verify-01` cho 263/309);
- T1 và T2 tất định: chạy lại cho hash giống hệt (receipt `10-rerun-t1-01`, `10-rerun-t2-01`);
- hash text của 10/10 bài T3 khớp sau khi đổi CRLF về LF (`08-text-hash-01`);
- hash `protocol.md` trùng hash đóng băng; precision T0, khoảng Wilson, `q1_weak` và đường bão hòa sinh bằng script (`10-report-stats-01`);
- CS Q1 ở năm xuất bản đạt ở 10/10 bài T3 (`work/q1-pubyear-check.csv`); với 5 bài năm 2026, dùng SJR 2025 thay thế vì chưa có ấn bản SJR năm xuất bản; JCR không kiểm (không có quyền truy cập);
- review cuối phase 10 ngữ cảnh mới, hai vòng: vòng 1 PASS_WITH_FIXES trên v1; vòng 2 xác nhận 14 phát hiện đã sửa trên v2 và nêu năm điểm nhỏ, đã xử lý trong v2 sau vòng 2 mà không có vòng review thứ ba ([final-review.md](../../research/final-review.md));

**Được ghi nhận nhưng không có artifact riêng (attested, state note):**
- review ngữ cảnh mới cho phase 08 đạt PASS ở vòng hai và cho phase 09 đạt PASS ở cả hai vòng: chỉ có ghi chú trong `work/state.json`, không có file output của reviewer. Năm phát hiện A–E vòng hai của phase 09 đã sửa và qua kiểm cơ học (`09-design-check-04`), chưa có vòng review thứ ba;
- 23 dòng độ nhạy được reviewer tính lại tay và khớp: không có file ghi phép tính lại.
- Review của model, kể cả khi PASS, không thay cho việc chủ dự án chấp nhận.

**Chưa kiểm (unverified):**
- G3 của mọi bài, vì chỉ có ước lượng tĩnh;
- số liệu bản TDSC của RCLAgent;
- độ chính xác của RCLAgent với backbone 4–9B;
- prior work của IM1–IM4 và của các follow-up AMER-RCL/SpecRCA, vì mới đọc abstract;
- tập 156 ca AIOps2022 của Topo-MFP so với bản trên Zenodo;
- con số 21 injection test của RE2-OB, mới khớp qua tính nhất quán, chưa join `source_index`;
- bốn bài ngoài T3 trong pool độ nhạy, chưa đọc sâu;
- JCR, vì không có quyền truy cập.

## Câu hỏi mở cho chủ dự án

1. Có chấp nhận RCLAgent làm bài nền không?
2. Về protocol v2 §1: giữ bất biến một lời gọi (nhánh a, bỏ phần đệ quy) hay mở rộng cho pipeline nhiều lời gọi (nhánh b)?
3. H1 xử lý thế nào với điều kiện `no_trace` và với độ tin cậy lấy từ một lời gọi khác?
4. Hạng 1 theo F không ổn định: nhận một bài theo cổng G, hay xem top-2?
5. Các quyết định D1–D13 trong `design/mvp-outline.md`. Trong đó có dùng API trả phí, cho dữ liệu ra ngoài, mở GPU, quy tắc niêm phong test, và có đưa H1 vào nhóm kiểm định xác nhận không.
6. Tải bản TDSC của RCLAgent và 17 PDF top-30. Với 152 abstract thiếu: dán vào, hay chấp nhận loại theo `E6-no-abstract`?
7. Quyết định PR-06 về category Engineering.
