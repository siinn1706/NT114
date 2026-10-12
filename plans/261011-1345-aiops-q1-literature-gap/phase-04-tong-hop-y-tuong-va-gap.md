# Giai đoạn 04 – Thẻ ý tưởng, ma trận khái niệm, gap và bước cố bác bỏ

Trạng thái: hoàn thành 12/10/2026 (chưa có người thứ hai lặp lại 3 gap), biên nhận `work/gaps.csv` `work/ideas25.csv` `work/concept-matrix.csv` `work/falsification-log.csv` `../reports/research-261012-q1-ideas-and-gaps.md` · Thực thi: nckh-cook (dùng nckh-research, nckh-evidence) · Phụ thuộc: [03](phase-03-doc-toan-van-50-bai.md) · Quay về [plan](plan.md)

Biên nhận: `work/gaps.csv` `work/ideas25.csv` `work/concept-matrix.csv` `work/falsification-log.csv` `../reports/research-261012-q1-ideas-and-gaps.md`

## Yêu cầu

- **~25 thẻ ý tưởng** (20–35): mỗi thẻ là một kỹ thuật, thiết kế thí nghiệm hoặc độ đo có thể mang về đề tài.
- **Ma trận khái niệm**: hàng là bài đã đọc, cột là các chiều trong phiếu (problem, modalities, llm, retrieval, propagation, confidence, explanation, compression_cost, số hệ thống, artifacts).
- **Gap**: tổ hợp chiều mà không bài nào (hoặc rất ít bài) làm, hoặc hạn chế mà nhiều tác giả cùng nêu.
- **Cố bác bỏ** mỗi gap trước khi giữ (D2): tìm có mục tiêu trong Q1, rồi trong hội nghị đầu ngành và arXiv 2024–2026.
- Kiểm lại 8 gap G1–G8 của báo cáo 05/10 bằng phiếu toàn văn.

Thẻ ý tưởng (`ideas25.csv`): id, ý tưởng, bài nguồn + vị trí, vấn đề nó giải, áp vào mục nào của Proposal (5.2–6.6, mã Pxxxx), chi phí ước lượng (GPU, công sức), bằng chứng hiệu quả trong bài nguồn, rủi ro khi chuyển sang dữ liệu RCAEval.

Gap (`gaps.csv`): id, phát biểu gap, ô ma trận chứng minh, bài gần nhất + vị trí và khác biệt, truy vấn cố bác bỏ (nguyên văn, nguồn, ngày, số kết quả), bài bác bỏ nếu có, trạng thái `confirmed | partially-filled | refuted`, mức chắc (`full-text` / `abstract-only`).

## Tệp

- Đọc: `work/extraction.csv`, [báo cáo gap 05/10](../reports/research-261005-2138-q1-research-gap.md) mục 4, `note/note-29-9.txt`.
- Tạo: `work/ideas25.csv`, `work/concept-matrix.csv`, `work/gaps.csv`, `work/falsification-log.csv`, báo cáo trung gian `plans/reports/research-<ngày>-q1-ideas-and-gaps.md`.

## Các bước

1. Sinh ma trận khái niệm từ `extraction.csv` bằng script; đếm số bài cho từng tổ hợp hai và ba chiều quan trọng.
2. Liệt kê ô rỗng/mỏng; gộp với hạn chế và hướng tương lai mà tác giả nêu lặp lại.
3. Lọc ý tưởng: từ phiếu, chọn ~25 bài cho ý tưởng dùng được; viết thẻ.
4. Với mỗi gap ứng viên: viết 2–4 truy vấn cố bác bỏ, chạy trên OpenAlex/Semantic Scholar (Q1) rồi trên Google Scholar/arXiv/DBLP cho ICSE, FSE, ASE, ISSRE, KDD, WWW, EuroSys, NSDI. Đọc abstract các bài trúng; bài trúng sát thì đọc phần method.
5. Gán trạng thái gap; gap `refuted` vẫn giữ trong bảng kèm bài bác bỏ.
6. Đối chiếu G1–G8: giữ, sửa phát biểu, hoặc bác bỏ, mỗi kết luận có vị trí trích.
7. Viết báo cáo trung gian: ma trận rút gọn, danh sách thẻ ý tưởng, bảng gap.

## Kiểm tra

- Mỗi gap `confirmed` có ít nhất một truy vấn cố bác bỏ ở cả Q1 và ngoài Q1 kèm số kết quả.
- Không gap nào dựa duy nhất vào abstract mà được ghi `confirmed`.
- Mỗi thẻ ý tưởng trỏ về một bài trong `extraction.csv` và một mục Proposal.
- Một thành viên khác đọc 3 gap ngẫu nhiên và lặp lại được kết luận từ log.

## Rủi ro / hoàn tác

- Gap thật ra là "không ai làm vì không đáng làm": ghi lý do có ích (dữ liệu, ứng dụng, góp ý GVHD) để Phase 05 chấm.
- arXiv có bài trùng ý tưởng: ghi `partially-filled`, nêu điểm khác (dữ liệu, mô hình nhỏ, chi phí, đánh giá) thay vì bỏ ngay.
- Hoàn tác: các bảng sinh lại được từ `extraction.csv` và log truy vấn.
