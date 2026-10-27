# Tiến độ phase 01–08: tổng quan 1.000 bài Q1, chọn bài nền RCA thiếu telemetry

Ngày 2026-10-26 (Asia/Saigon). Báo cáo này thay `cook-261024-1002-tien-do-phase-01-05.md`.

## Kết quả

Phễu đã chạy hết đến bước chọn một bài:

| Tầng | Kết quả |
|---|---|
| T0 | 1.085 bản ghi |
| T1 | 100 bài |
| Toàn văn | 34/100 bài |
| T2 | 10 bài |
| T3 | 1 bài đạt đủ cổng G |

Bài được đề xuất là RCLAgent (W7165616276, IEEE TDSC 2026), nhãn `single-eligible`. Đây mới là đề xuất. Phase 08 dừng ở `waiting-human` vì ba quyết định thuộc chủ dự án (mục cuối).

## Từng phase

| Phase | Trạng thái | Bằng chứng chính |
|---|---|---|
| 01 | done | `protocol.md` đóng băng, SHA ca65919f…; `work/protocol-freeze.json` |
| 02–04 | done | T0 = `work/records/t0r2b-t0.csv` (1.085 bản ghi); §10 đã chạy snowball vòng 2 (+5) và truy vấn đồng nghĩa (+113); `work/saturation-curve.json` |
| 05 | done | T1 = `work/records/t1-top100.csv`; κ = 1,0 / 0,871 / 0,881; 152 bản ghi needs-review vẫn chờ |
| 06 | done | `work/access-ledger-final.csv`: 34 bài toàn văn, 66 không truy cập được; 17 PDF top-30 chờ tải tay (`work/manual-download-request.md`) |
| 07 | done | `work/records/t2-top10.csv`; kiểm chéo 6 bài và locator 20/20 (`work/t2-crosscheck-record.md`) |
| 08 | waiting-human | `research/selection-memo.md` v2; `work/decision-matrix.csv`; `work/sensitivity.csv`; 10 card ở `research/cards/t3/` |

## Phase 08 tóm tắt

- **Cổng G.** Chỉ RCLAgent qua cả G1–G5.
  - G1 là cổng trượt nhiều nhất (8/10), chủ yếu do repo thiếu file license hoặc không có code.
  - CausalRCA chỉ trượt G5, vì chỉ dùng metric.
- **Độ nhạy.** Khi bỏ cổng G, DiagFusion và RCLAgent hòa 25 điểm F; không bài nào giữ hạng 1 từ 15/18 kịch bản trở lên. Đề xuất dựa trên khả năng tái hiện (G1), không dựa trên F.
- **Review ngữ cảnh mới.** Vòng đầu có 1 phát hiện chặn (h1-compat) và 7 phát hiện mức major, tất cả đã sửa trong memo v2 và `work/t3-gate-corrections-a02.csv`. Vòng rà lại cho kết quả PASS, kèm 1 phát hiện major về provenance (timestamp và receipt kiểm CHASE.7z) và 3 phát hiện minor; tất cả đã sửa (receipt `08-gate-evidence-01` và `08-merge-t3-03`).
- **Lệch hash text giữa T2 và T3.** Nguyên nhân là ký tự xuống dòng CRLF/LF; nội dung không đổi (`work/t3-text-hash-check.csv`).

## Ràng buộc đã giữ

- Không sửa source, protocol v2, prompt, split hay bundle.
- Không chạy model, không commit.
- Mã của bài báo chỉ được đọc tĩnh, đặt ngoài repo (`F:/Nam/UIT/nt114-paper-artifacts/`).
- Không có key hay email trong file kết quả.

## Câu hỏi chưa giải quyết (cần chủ dự án)

1. RCLAgent gọi cùng một model nhiều lần, xung đột với bất biến "một lời gọi" của protocol v2 §1. Giữ bất biến (bỏ phần đệ quy) hay mở rộng protocol v2?
2. H1 với pool `single_modality`: ở điều kiện `no_trace`, phương pháp gốc không chạy đúng, và độ tin cậy lấy từ một lời gọi khác. Chủ dự án chọn hướng xử lý H1 nào?
3. Hạng 1 theo F không ổn định. Nhận một bài theo cổng G, hay xem top-2 (DiagFusion, RCLAgent)?
4. Tải bản TDSC của RCLAgent để đối chiếu số liệu, và tải 17 PDF top-30.
5. Với 152 bản ghi thiếu abstract: dán abstract, hay chấp nhận loại theo `E6-no-abstract`?
6. Quyết định PR-06 (category Engineering). Precision thấp (N × precision khoảng 120, dưới ngưỡng 500). Quota Elicit hết đến 18/11.
