# Phase 01 — Khảo sát toàn văn, định vị khoảng trống, dựng hồ sơ bài

## Mục tiêu
Biết chắc bài mình mới ở đâu trước khi xây phần nâng cấp, và có hồ sơ bài để mọi bước sau bám vào.

## Việc làm
1. **Đọc toàn văn nhóm sát nhất** (đọc trước, theo thứ tự rủi ro trùng): EviRCA (2609.19825), GALA (2608.08968), SpecRCA
   (2601.02736), trajectory study (2608.21310), OpenRCA 2.0 (2606.27154), RCAEval, RCACopilot, TAMO, ThinkFL.
   Với mỗi bài ghi: bài toán, dữ liệu, mô hình (open-weight hay API), có đo độ tin cậy không, có chấm đường lan truyền không,
   có kiểm bằng chứng tất định không, có chéo hệ thống không, kết quả trên RE2 nếu có. Ghi câu nguyên văn làm căn cứ.
2. **Dựng bảng so sánh công trình** (quy chuẩn mục 15): cột gợi ý — đa nguồn; propagation-aware; bằng chứng tất định;
   độ tin cậy hiệu chỉnh/từ chối; LLM open-weight ≤8B; ngân sách token; đánh giá ≥3 hệ thống. Định nghĩa từng cột trong
   hồ sơ bài, mỗi ô có câu trích. Cột phải phân biệt được các bài, không chỉnh để chỉ bài mình có ✓.
3. **Quyết định focus:** nếu tổ hợp lan truyền + bằng chứng + hiệu chỉnh đã có trọn ở một bài → chuyển phương án dự phòng
   (hiệu chỉnh + chuyển giao chéo hệ thống, dạng empirical study). Ghi quyết định và lý do vào hồ sơ.
4. **Dựng hồ sơ bài** theo quy chuẩn mục 0.2 trong `~/.claude/skills/nckh-quy-chuan/profiles/<tên-bài>/`: nơi nộp, template,
   giới hạn trang, kiểu trích dẫn, ai viết phần nào, cách đồng bộ Overleaf, có công bố code không, nguồn chuẩn cho từng loại
   khẳng định, bảng thuật ngữ và ký hiệu, `invariants.json`, quyết định mentor đã chốt (kèm ngày, lời gốc).
5. **Dàn ý bài** (quy chuẩn mục 0.5): khung section theo mục 6.1, Problem Statement dạng ánh xạ một sự cố
   `(telemetry X, đồ thị gọi G, kho tri thức D) ↦ (danh sách xếp hạng, loại lỗi, đường lan truyền, độ tin cậy, bằng chứng)`,
   mỗi mục tiêu có chỗ đáp (RQ hoặc mệnh đề). Học cấu trúc bài mẫu, không chép.
6. Đưa mentor duyệt dàn ý + RQ trước khi sang viết chi tiết.

## File tạo/sửa
- `plans/reports/` : báo cáo khảo sát toàn văn, bảng so sánh công trình.
- Hồ sơ bài trong thư mục skill (sau khi người dùng trả lời câu hỏi mở ở plan.md).

## Kiểm tra
- Mỗi bài trong bảng đã mở toàn văn; metadata kiểm qua Crossref/OpenAlex; không MDPI (DOI `10.3390`).
- Bảng truy vết thách thức → mục tiêu → cơ chế → RQ không có ô trống (quy chuẩn mục 7.3).

## Rủi ro
Đọc lướt rồi kết luận "chưa ai làm" là rủi ro lớn nhất của cả bài. Không bỏ bước 1 để chạy code sớm.
