# Tổng quan 1.000 bài Q1 và chọn bài nền cho MVP RCA thiếu telemetry, v1

Ngày 2026-10-26 (Asia/Saigon). Kế hoạch: `plans/261024-0858-tong-quan-1000-q1-chon-bai-nen-rca-thieu-telemetry/`. Giao thức: `protocol.md`, đóng băng ngày 2026-10-24, SHA-256 ca65919f…

## Kết luận

- **Bài nền đề xuất: RCLAgent.** Tên bài: *Toward In-Depth Root Cause Localization for Microservices With Multi-Agent Recursion-of-Thought*, IEEE TDSC 2026, doi 10.1109/tdsc.2026.3706572.
  - Nhãn `single-eligible`: trong 10 bài đọc sâu, chỉ bài này qua đủ năm cổng G1–G5.
  - Trạng thái là `pending-personal-review`: việc chấp nhận bài nền thuộc chủ dự án.
- **Lý do chọn.** Bài có repo công khai với license MIT, README có lệnh chạy và dữ liệu mẫu (G1). Dữ liệu đánh giá RCAEval RE2-OB đã có trong bundle NT114 (G2). Code gọi LLM qua endpoint tương thích OpenAI, nên chạy được với một model open-weight cục bộ, theo ước lượng tĩnh (G3). Mọi agent dùng chung một backbone (G4). Bài dùng cả trace, metric và log (G5).
- **Giới hạn.**
  - Về điểm F, RCLAgent chỉ ngang nhóm đầu: một mình hạng 1 ở 2/18 kịch bản độ nhạy, còn DiagFusion ở 3/18.
  - Bài chưa thử backbone nào dưới 32B.
  - Phương pháp gọi model nhiều lần cho mỗi span.
  - Khi không có trace (`no_trace`), phương pháp thoái hóa thành một ReAct agent.
  - Bản đã đọc là preprint arXiv v1.
- **Điều kiện có thể đảo đề xuất:**
  - chủ dự án giữ bất biến "một lời gọi" của protocol v2 và coi phần đệ quy là lõi không thể bỏ;
  - bản TDSC có số liệu lệch ngoài dung sai;
  - G1 được nới bằng amendment, khi đó §8 chuyển sang nhánh ≥ 2 bài đạt và top-2 không ổn định.

Chi tiết lập luận: [selection-memo.md](../../research/selection-memo.md) v2.

## Phễu (PRISMA)

| Bước | Số | Nguồn |
|---|---|---|
| Bản ghi duy nhất từ seed, tìm kiếm và snowball sau khử trùng | 14.422 | `work/records/t0r2b-summary.json` |
| Loại ở cổng Q1, năm, loại tài liệu, chủ đề và ngôn ngữ | 13.007 | cùng file, `exclude_reasons_multi` |
| Giữ tự động | 1.053 | cùng file |
| Cần xem tiêu đề, sau đó giữ | 362, giữ 32 | `work/records/t0r2b-t0-review-decisions.csv` |
| **T0** | **1.085** | `work/records/t0r2b-t0.csv` |
| Quyết định screening: include / exclude / needs-review / context-survey | 121 / 741 / 152 / 71 | `work/records/final-t1.json` |
| **T1** (include với R1 ≥ 2, lấy 100 đầu) | **100** | `work/records/t1-top100.csv` |
| Có toàn văn | 34 (22 bản tạp chí, 12 preprint) | `work/access-ledger-final.csv` |
| Qua cổng T2 trong 34 bài có điểm F | 20 | `work/appraisal/f-scores.csv` |
| **T2 → T3** | **10** | `work/records/t2-top10.csv` |
| Qua đủ G1–G5 | 1 | `work/decision-matrix.csv` |

- Lý do loại không loại trừ nhau, nên tổng các mã lớn hơn 13.007. Ba mã lớn nhất: không có ISSN trong SJR (7.419), lệch chủ đề theo metadata (4.470), không phải Q1 (2.716).
- Đường bão hòa (`work/saturation-curve.json`): seed cho 338 bản ghi; tìm kiếm thêm 525; snowball vòng 1 thêm 105; snowball vòng 2 cùng truy vấn đồng nghĩa thêm 118, đưa tổng lên 1.085.
- Precision ở T1 xấp xỉ 121/1.085 ≈ 0,11, nên N × precision ≈ 120, dưới ngưỡng 500 của §10. Giới hạn này đã ghi trong `work/amendments.md`.

## Giao thức và amendment

- Giao thức đóng băng lúc 2026-10-24T02:34:10Z (`work/protocol-freeze.json`). Hash `protocol.md` trên đĩa ngày 2026-10-26 vẫn trùng hash đóng băng.
- Amendment sau freeze (`work/amendments.md`):
  1. Ngày 2026-10-24, thêm từ khóa cho nhóm Hệ thống của regex chủ đề (`SYSTEM_RE`) sau khi kiểm sai âm thấy 2/25 sai âm ở seed.
  2. Bảng truy vấn đồng nghĩa S1–S7 cho §10 bước 2, soạn trước khi chạy. Mệnh đề chẩn đoán của S4 được siết sau probe-01 (độ phủ 0,797).
- Sau review, phase 08 có thêm các ô cổng G được sửa, ghi ở `work/t3-gate-corrections-a02.csv`. Đây là sửa cách áp cổng cho nhất quán, không phải nới cổng.

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
- Trên pool 20 bài của T2 (`work/sensitivity-t2-pool.csv`), bốn bài ngoài T3 vào top-10 ở ít nhất một kịch bản: QROOT, RPCA, BARO tăng cường và W4415944773. Cả bốn đều không có code; chưa đọc sâu.

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
  - Kết quả tìm prior work là "chưa thấy" hoặc "trùng một phần" trong các tìm kiếm ngày 2026-10-25 UTC (`work/prior-work-improvements.csv`).
- [test-matrix.md](../../design/test-matrix.md): đơn vị độc lập là injection; điều kiện thiếu telemetry theo protocol v2; dùng C-3 cho H1; MDE lấy theo anchor RCA100 với n = 70.
- [mvp-outline.md](../../design/mvp-outline.md): mốc M0–M5 và các quyết định D1–D13 của chủ dự án.

## Giới hạn của tổng quan

- Chỉ 34/100 bài T1 có toàn văn; trong top-30 chỉ 13/30. Có 17 bài top-30 cần chủ dự án tải tay, nên T2 có thể đổi khi có các bài này.
- 152 bản ghi needs-review thiếu abstract (E6), vì Elsevier dùng CAPTCHA và Springer cần đăng nhập.
- Precision của corpus thấp (N × precision ≈ 120). Làn Elicit bị chặn vì hết quota tới 18/11.
- Cổng G được áp bởi năm lần chạy reader riêng; sau review, cách áp đã được làm nhất quán. G3 chưa được đo thật.
- Về receipt (`work/receipt-verify-10.csv`): 263/309 verify được; 38 lệch do các file được cập nhật về sau có ghi ngày; 8 receipt checkpoint ở giai đoạn seed không ghi exit của từng đoạn lệnh.

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
- file full text ở `private/fulltext/261024/` (gitignored) và file artifact ở `F:/Nam/UIT/nt114-paper-artifacts/`, cả hai nằm ngoài phần được theo dõi của repo.

**Đã kiểm trong attempt này (verified-this-attempt):**
- 263 receipt verify được (`work/receipt-verify-10.csv`, receipt `10-receipt-verify-01`);
- T1 và T2 tất định: chạy lại cho hash giống hệt (receipt `10-rerun-t1-01`, `10-rerun-t2-01`);
- hash text của 10/10 bài T3 khớp sau khi đổi CRLF về LF (`08-text-hash-01`);
- 23 dòng độ nhạy được reviewer tính lại tay và khớp;
- Q1 theo năm xuất bản đạt ở 10/10 bài;
- review ngữ cảnh mới cho phase 08 đạt PASS ở vòng hai;
- review ngữ cảnh mới cho phase 09 đạt PASS ở cả hai vòng. Năm phát hiện A–E của vòng hai đã sửa và qua kiểm cơ học (`09-design-check-04`), nhưng chưa có vòng review thứ ba.

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
