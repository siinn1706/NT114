# Giai đoạn 06 – Rà soát, báo cáo cuối, bàn giao để chọn hướng

Trạng thái: in-progress: báo cáo cuối và tự rà soát xong; chờ rà soát độc lập và quyết định của nhóm, GVHD. Tệp: `../reports/research-261012-q1-survey-and-directions.md` `work/review-findings.md` · Thực thi: nckh-review rồi nckh-cook · Phụ thuộc: [05](phase-05-danh-gia-va-xep-hang-huong.md) · Quay về [plan](plan.md)

## Yêu cầu

- Một báo cáo cuối `plans/reports/research-<ngày>-q1-survey-and-directions.md`, gồm: phương pháp tìm (từ khóa, truy vấn, giao thức Q1, năm SJR), sơ đồ PRISMA, phân loại các bài theo cụm, ma trận khái niệm rút gọn, bảng gap với trạng thái, ~25 thẻ ý tưởng (bảng gọn), bảng điểm hướng + độ nhạy, hồ sơ 2–3 hướng tốt, hạn chế của khảo sát.
- Rà soát độc lập trước khi đưa GVHD.
- Nhóm và GVHD chọn hướng; báo cáo ghi lựa chọn và lý do, không tự chốt thay.
- Danh sách tài liệu tham khảo theo IEEE, kèm DOI, chỉ gồm bài đã đọc (ghi mức đọc).

## Tệp

- Đọc: mọi tệp `work/` của Phase 01–05, báo cáo trung gian Phase 04.
- Tạo: báo cáo cuối ở `plans/reports/`, `work/review-findings.md` nếu rà soát có phát hiện.
- Sửa: `plan.md` (trạng thái từng giai đoạn kèm đường dẫn biên nhận), không sửa Proposal.

## Các bước

1. Chạy nckh-review trên báo cáo nháp: đối chiếu mỗi khẳng định về bài với `extraction.csv`, mỗi gap với `falsification-log.csv`, mỗi quartile với tệp SJR.
2. Sửa các phát hiện; phát hiện không sửa được thì ghi vào phần hạn chế.
3. Gửi GVHD báo cáo + 1 trang tóm tắt (3 hướng, mỗi hướng 5 dòng).
4. Ghi quyết định của nhóm và GVHD vào báo cáo; nếu chọn hướng, mở plan mới cho giai đoạn nghiên cứu (không làm trong plan này).

## Kiểm tra

- Mọi DOI trong tài liệu tham khảo phân giải được (Crossref) và khớp tiêu đề.
- Mọi tạp chí trong tài liệu tham khảo có quartile Q1 trong tệp SJR đã băm (trừ dataset/công cụ theo D5, ghi riêng).
- Các con số trong báo cáo (số bài mỗi bước, điểm hướng) khớp với `prisma-counts.json` và `direction-scores.csv`.
- Chạy `check-plan.py` trên thư mục plan sau khi cập nhật trạng thái.

## Rủi ro / hoàn tác

- GVHD không chọn hướng nào trong top: ghi lại tiêu chí GVHD dùng, quay lại Phase 05 với tiêu chí mới thay vì làm lại tìm kiếm.
- Báo cáo quá dài: tách phụ lục (bảng 100 bài, phiếu 50 bài) thành tệp CSV đính kèm, báo cáo chính dưới 800 dòng.
- Hoàn tác: báo cáo là tệp mới; bản cũ giữ nguyên khi sửa.
