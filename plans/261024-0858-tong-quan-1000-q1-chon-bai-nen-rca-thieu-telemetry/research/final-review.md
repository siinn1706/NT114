# Review cuối phase 10: báo cáo tổng quan và gate matrix

Ngày 2026-10-26 (Asia/Saigon). Đối tượng: [báo cáo](../plans/reports/research-261026-0430-tong-quan-1000-q1-chon-bai-nen.md) và [gate-matrix.csv](../work/gate-matrix.csv). Phạm vi chấp nhận: [phase 10](../phase-10-ra-soat-bao-cao-ban-giao.md), [plan](../plan.md) §2 và §4, quyết định chủ dự án ở `../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md`.

## Verdict

- **Vòng 1 (báo cáo v1, gate matrix a01): PASS_WITH_FIXES.** Không có phát hiện mức high; 8 medium, 7 low. Không chỗ nào trình bày RCLAgent là bài nền đã được chấp nhận.
- **Vòng 2 (báo cáo v2, gate matrix hiện tại): PASS_WITH_FIXES, chỉ còn lỗi nhỏ.** Reviewer ngữ cảnh mới xác nhận cả 14 phát hiện của vòng 1 đã sửa (phát hiện 8 thuộc bàn giao), số khớp nguồn, tự tính lại Wilson khớp script. Năm điểm mới (1 medium, 4 low) đã xử lý sau vòng 2, xem mục dưới; không chạy vòng 3.
- Trạng thái nghiệm thu: báo cáo `ready-for-review`; bài nền `pending-personal-review`; hai xung đột quyết định `waiting-human`. Review của model không thay cho chấp nhận của chủ dự án.

Reviewer vòng 1 thay cho reviewer phiên trước, vốn dừng vì limit mà không có kết luận; phiên trước không có verdict nào được dùng.

## Cách review

- Reviewer `nckh-reviewer` ngữ cảnh mới, chỉ đọc. Brief chỉ gồm báo cáo, gate matrix, phase 10, plan §2/§4, decisions.md và danh sách file bằng chứng mở theo từng nhận định. Không giao transcript, toàn văn, corpus hay toàn bộ `work/state.json`.
- Số dẫn xuất được sinh lại bằng script thay vì tính tay: `work/scripts/report-stats.py` → `work/report-stats-10.json` (receipt `10-report-stats-01`).
- Receipt được verify lại toàn bộ: `work/receipt-verify-10-a02.csv` (receipt `10-receipt-verify-02`).

## Phát hiện vòng 1 và cách xử lý

| # | Mức | Phát hiện | Xử lý | Bằng chứng |
|---|---|---|---|---|
| 1 | medium | Tiêu chí 1 chỉ dẫn `01-freeze-01` (superseded-state) | Kiểm lại hash `protocol.md` = hash đóng băng bằng script; dẫn thêm receipt | `10-report-stats-01`, `work/report-stats-10.json` `protocol.match = true` |
| 2 | medium | Hai xung đột với quyết định chủ dự án chưa gắn `waiting-human` | Thêm vào Kết luận, tách khỏi `pending-personal-review` | báo cáo v2, Kết luận |
| 3 | medium | Thiếu giới hạn: backbone mở yếu, đích dùng API đóng, "vượt mọi SOTA" bị phản chứng, 69/108 pool H1 | Thêm 4 gạch Giới hạn; G3 ghi rõ chỉ ước lượng tĩnh | `research/selection-memo.md` mục 5–6; `design/reproduction-protocol.md` T1–T5, T10, T11; `design/test-matrix.md` C-3 |
| 4 | medium | Thiếu Wilson 95% cho precision T0 | Precision T0 0,112, Wilson [0,094; 0,132], sinh bằng script | `work/report-stats-10.json` |
| 5 | medium | Thiếu `q1_weak`/`q1_noncs`, Q-7 gộp vào cổng Q1 | Định nghĩa Q1 ở phễu; báo 160 `q1_weak`, 2.000 `Q-4-q1-noncs`, 826 `Q-7-mdpi` | `work/report-stats-10.json`; `work/records/t0r2b-summary.json` |
| 6 | medium | Ba mục "đã kiểm" không có artifact | Chuyển sang mục "attested, state note" | báo cáo v2, Bốn danh sách |
| 7 | medium | Ghi chú tiêu chí 5, bằng chứng tiêu chí 6 | Thêm `waiting-human` vào note tiêu chí 5; ghi review PASS chỉ là ghi chú state | `work/gate-matrix.csv` (bản cũ: `work/gate-matrix-a01.csv`) |
| 8 | medium | Chưa có handoff, final-review, check-plan | Tệp này; `work/handoff.md`; `check-plan.py` qua receipt `10-check-plan-01` | xem [handoff](../work/handoff.md) |
| 9 | low | Bão hòa 105 so với tăng ròng 104 | Không phải lỗi script: `new` đếm bản ghi mới; 1 bản ghi (W3005115843) rời T0 ở bước snowball-r1. Báo cáo ghi rõ 105 mới, 1 rời, ròng 104. Không sửa nguồn sinh | `work/report-stats-10.json` `saturation` |
| 10 | low | `amendments.md` còn số precision cũ | Thêm mục "Đính chính 2026-10-26" | `work/amendments.md` |
| 11 | low | "38 lệch" gộp hai loại | Tách 20 `superseded-state` và 18 `changed-later` | `work/receipt-verify-10-a02.csv` |
| 12 | low | "không phải nới cổng" quá mạnh | Ghi đúng: hai ô sang đạt, một ô sang trượt, tập đạt không đổi | `work/t3-gate-corrections-a02.csv` |
| 13 | low | "không có code" quá mạnh | "Toàn văn không nêu repo (F3_code = 0)" | `work/appraisal/f-scores.csv` |
| 14 | low | Mục Q1 năm xuất bản thiếu lưu ý | Thêm: 5 bài 2026 dùng SJR 2025 thay thế; JCR không kiểm | `work/q1-pubyear-check.csv`; `work/report-stats-10.json` `t3_pubyear` |
| 15 | low | Quota Elicit không có nguồn gốc | Dẫn `work/provider-status.csv` dòng 4 (reset 2026-11-18T16:00Z) | `work/provider-status.csv` |

Phát hiện thêm của phiên điều phối (không từ reviewer):
- 8/10 card T3 bị sửa sau khi batch phase 08 commit; hash trong `work/state.json` cũ. Input của quyết định vẫn khớp receipt `08-merge-t3-03`. Không commit lại card vì không có receipt cho các lần sửa văn bản; ghi ở báo cáo (Giới hạn) và handoff.
- 1 trong 8 receipt "other" là `04-checkpoint-full-02`, không thuộc làn seed như v1 viết; đã sửa câu.
- Trạng thái cấp phase của `work/state.json` cũ (06–09 `not-started`). Đã đồng bộ theo batch và receipt, giữ lịch sử ở `status_history` (receipt `10-sync-phase-status-01`, `work/phase-status-sync-10.csv`). Không chạy lại phase 01–09.

## Phát hiện vòng 2 và cách xử lý

| Mức | Phát hiện | Xử lý |
|---|---|---|
| medium | Báo cáo và tiêu chí 7 dẫn `10-check-plan-01` khi receipt chưa có | Receipt được tạo khi chạy `check-plan.py` lúc chốt phase 10; xem [handoff](../work/handoff.md) |
| low | Mục "review cuối phase 10" nằm ở verified trước khi vòng 2 xong | Viết lại: hai vòng, vòng 2 xác nhận, điểm nhỏ sửa sau vòng 2, không có vòng 3 |
| low | `10-report-stats-01` chạy sau `10-receipt-verify-02` | Các receipt 10-* tạo sau được kiểm riêng bằng `check-receipt.py`, ghi trong handoff |
| low | Ghi chú tiêu chí 2 còn "about 120" | Đổi thành 121, kèm Wilson và receipt |
| low | Khoảng MRR backbone mở là trên tập con AIOps2022 | Thêm cụm "đo trên các tập con AIOps2022, không phải RE2-OB" |
| ghi chú | `01-query-probe-01` changed-later với `protocol.md` | Probe chạy trước freeze, protocol được sửa trước freeze (`work/amendments.md` mục trước freeze); không đổi |

## Claim triage (nhận định chính của Kết luận và Giới hạn)

| Nhận định | Đánh giá | Locator |
|---|---|---|
| RCLAgent, TDSC 2026, DOI | supported | `work/records/t2-top10.csv` |
| Chỉ 1/10 bài qua đủ G1–G5 | supported | `work/decision-matrix.csv` cột `all_gates` |
| G1, G2, G4, G5 của RCLAgent | supported (đọc tĩnh artifact và toàn văn arXiv v1) | `research/selection-memo.md` |
| G3: có thể trỏ tới model open-weight cục bộ | partially: chỉ ước lượng tĩnh từ code; chưa có độ chính xác, VRAM, độ trễ | `research/selection-memo.md` mục 5 |
| Một mình hạng 1 ở 2/18; DiagFusion 3/18 | supported | `work/sensitivity.csv` |
| Không backbone dưới 32B; backbone mở yếu | supported (Table III của arXiv v1) | `design/reproduction-protocol.md` T10 |
| "Vượt mọi SOTA" bị phản chứng | supported | `design/reproduction-protocol.md` T11 |
| 69/108 injection pool H1 | supported (tính trên thiết kế, chưa chạy) | `design/test-matrix.md` C-3 |
| Precision T0 0,112 [0,094; 0,132] | supported | `work/report-stats-10.json` |
| Review phase 08/09 PASS; 23 dòng độ nhạy tính lại | attested, không có artifact | ghi chú `work/state.json` |
| Số liệu bản TDSC; độ chính xác 4–9B; novelty IM1–IM4 | unverified, ghi ở danh sách chưa kiểm | báo cáo v2 |

## Không kiểm trong review này

- Không đọc toàn văn, card T3, `work/artifact-audit.csv`, `work/evidence-ledger.csv`, repo RCLAgent hay `prep.yaml`.
- Không kiểm lại kappa và nội dung bên trong từng receipt ngoài verdict của `check-receipt.py`.
- Không xác minh runtime, VRAM, backbone 4–9B, số liệu bản TDSC hay tính mới.
