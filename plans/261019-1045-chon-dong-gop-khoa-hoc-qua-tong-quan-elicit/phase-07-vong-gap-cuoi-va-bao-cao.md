---
phase: 7
title: "Vòng gap cuối và báo cáo duy nhất"
status: completed
effort: 1-1.5 ngày
depends_on: [6]
---

# Phase 07: Vòng gap cuối và báo cáo

## A. Vòng gap cuối

1. Với mỗi dòng `work/contradictions.csv`: tìm nguồn thứ ba hoặc đọc kỹ setting để giải thích (dataset,
   metric, cỡ mẫu, mô hình). Ghi `resolution` = `explained` / `unresolved` + lý do.
2. Với mỗi dòng `work/single-source-claims.csv`: chạy ≥ 1 truy vấn nhắm riêng (Elicit + một nguồn ngoài)
   để tìm xác nhận hoặc bác bỏ. Không thấy → giữ nhãn `ĐƠN-NGUỒN` trong báo cáo.
3. Lặp lại khối A và C của Phase 02 với `minYear: 2026` để bắt preprint mới; ghi ngày cắt.
4. Một truy vấn cuối cho đúng phát biểu H1 khuyến nghị (nếu H1 được chọn) hoặc hướng được chọn, dạng
   "đã có ai làm X trên Y với Z chưa".

Mọi truy vấn qua kiểm công khai ở Phase 01 và vào `search-log.csv` với `block = GAP`.

## B. Báo cáo duy nhất

File: `plans/reports/research-261019-tong-quan-elicit-chon-dong-gop-nt114.md` (tiếng Việt; tên riêng,
tên phương pháp, trích dẫn giữ nguyên tiếng Anh).

Cấu trúc:

1. **Tóm tắt quyết định** (≤ 1 trang): hướng khuyến nghị, verdict tính mới mỗi H, điều kiện đảo.
2. **Phương pháp tổng quan:** engine, ngày, khối truy vấn (tham chiếu `search-log.csv`), tiêu chí, khử
   trùng lặp, sàng lọc, độ tin cậy sàng lọc, sai lệch so với giao thức.
3. **PRISMA** (bảng số và sơ đồ văn bản).
4. **Năng lực Elicit MCP đã dùng** và giới hạn quan sát được.
5. **H1:** bài gần nhất, phần đã làm, khoảng trống còn lại, bảng phản chứng, power, thí nghiệm tối thiểu.
6. **H2:** như trên.
7. **H3 và DecompRCA:** như trên + tóm tắt hồ sơ DecompRCA và hệ quả cho V8 bước 2.
8. **So sánh hướng:** bảng `direction-scores` đầy đủ.
9. **Mâu thuẫn và khẳng định đơn nguồn:** kết quả vòng gap.
10. **Hạn chế:** một người sàng lọc, độ phủ của Elicit, toàn văn không lấy được, ngày cắt.
11. **Phụ lục phát hiện:** mọi phát hiện được dẫn, mỗi dòng đủ 11 trường ở plan.md mục 6.
12. **Đầu vào cho bước sau:** các đề xuất cho §9.5 protocol v2 (chỉ đề xuất, không sửa).

Mỗi khẳng định trong mục 1–9 có `[F-xxx]` trỏ tới phụ lục.

## Kiểm chứng

- Script CPU: mọi `[F-xxx]` trong báo cáo có trong phụ lục; mọi dòng phụ lục đủ 11 trường; mọi link
  tương đối trỏ tới file tồn tại.
- Kiểm tay: 10 `[F-xxx]` ngẫu nhiên mở nguồn và khớp vị trí.
- So với `work/git-baseline.txt`: HEAD không đổi; dòng mới trong `git status --porcelain` chỉ thuộc thư
  mục kế hoạch này và báo cáo; `git diff --stat` cho file đã track là rỗng.
- Đối chiếu từng AC1–AC12 của plan.md, đánh dấu với bằng chứng.

## Hoàn tác

Báo cáo và `work/` là file mới, chưa commit; xoá là hoàn tác. Không có thay đổi nào khác.
