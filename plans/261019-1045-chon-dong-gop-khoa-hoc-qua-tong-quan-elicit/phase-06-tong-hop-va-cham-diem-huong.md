---
phase: 6
title: "Tổng hợp và chấm điểm H1/H2/H3"
status: completed
effort: 1 ngày
depends_on: [4, 5]
---

# Phase 06: Tổng hợp và chấm điểm hướng

## Yêu cầu

Với mỗi H1, H2, H3, điền một cột trong `work/direction-scores.csv` và một mục trong bản nháp báo cáo.
Mọi ô dẫn tới `finding_id`.

| Tiêu chí | Cách đánh giá | Nguồn trong repo |
|---|---|---|
| **Tính mới** | `chồng lấn có` / `chồng lấn có khả năng` / `chồng lấn một phần` (nêu chiều nào đã làm) / `chưa thấy` theo quy tắc plan.md mục 5. Liệt kê bài gần nhất và **khác biệt cụ thể còn lại** | `findings.csv` |
| **Phản chứng** | Bảng supports / contradicts; với H1 bắt buộc có hàng cho: verbal confidence không theo correctness, entropy không đủ, abstention fail dưới shift, lợi ích biến mất ở cùng coverage | Khối C |
| **Tương thích protocol v2** | Thí nghiệm có dùng được endpoint cố định (AC@1–5, MRR@5 censored, confidence, selective, cost, strata) mà không sửa protocol? Nếu cần endpoint mới, nêu tên — chỉ đề xuất | protocol-v2.md |
| **Cỡ mẫu độc lập** | Số injection độc lập theo dataset và điều kiện cho thí nghiệm tối thiểu | research/02, research/06 |
| **Power** | So hiệu ứng mà tài liệu báo với MDE: RCAEval 0.10, giao 52 sự cố 0.18, Nezha 0.14, RCA100 0.16, AIOps2025 0.08 (20 % discordance; Holm làm tăng MDE, research/06 dòng 97). Ghi rõ: hiệu ứng tài liệu < MDE → thí nghiệm thiếu power | research/06 |
| **Manipulation check** | Điều kiện thiếu telemetry có thật sự làm thay đổi bằng chứng không (`blind_nonroot` không đổi 80–98 % bản ghi; RCA100 `blind_root` chỉ đổi 3/86) → H nào phụ thuộc điều kiện yếu | research/05 |
| **Công sức** | Ngày-người, có cần code mới không, có cần model thật không, chi phí API ước tính | research/02 mục từng H |
| **Thí nghiệm tối thiểu** | Tập thí nghiệm nhỏ nhất trả lời được câu hỏi, kèm arm, baseline, endpoint, dataset, n | research/02 |
| **Rủi ro bị scoop** | Số bài 2025–2026 cùng hướng; preprint mới nhất | `corpus.csv` |

Cho điểm 0–3 mỗi tiêu chí với rubric ghi trong file; **không** cộng trọng số ẩn. Khuyến nghị cuối viết
bằng lời, kèm "điều kiện làm đảo khuyến nghị".

Cũng xét **phương án kết hợp** (ví dụ H1 dùng tín hiệu của H3) và phương án "không hướng nào đủ mới →
đóng góp là đánh giá/benchmark có kiểm soát". Chỉ đưa vào nếu có bằng chứng ủng hộ.

## Kiểm chứng

- Không ô nào trong `direction-scores.csv` rỗng hoặc thiếu `finding_id`.
- Mọi so sánh power dẫn đúng số của research/06.
- Danh sách khẳng định đơn nguồn có hệ quả được xuất ra `work/single-source-claims.csv` cho Phase 07.
- Danh sách mâu thuẫn giữa nguồn xuất ra `work/contradictions.csv`.

## Rủi ro

- Thiên kiến ưu tiên H1 → chấm H2, H3 trước H1; ghi thứ tự chấm.
