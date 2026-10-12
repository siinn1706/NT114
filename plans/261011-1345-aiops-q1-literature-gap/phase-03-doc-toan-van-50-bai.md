# Giai đoạn 03 – Chọn và đọc toàn văn ~50 bài

Trạng thái: hoàn thành 12/10/2026 (47 toàn văn, 22 chỉ tóm tắt; chưa chấm độc lập 20 bài, chưa đọc chéo 5 phiếu), biên nhận `work/extraction.csv` `work/read-final.csv` `work/access-log.csv` · Thực thi: nckh-cook (dùng nckh-research) · Phụ thuộc: [02](phase-02-tim-va-xep-hang-100-bai.md) · Quay về [plan](plan.md)

Biên nhận: `work/extraction.csv` `work/read-final.csv` `work/access-log.csv`

## Yêu cầu

- Chọn ~50 bài (40–60) từ `top100.csv`:
  - bắt buộc: các bài then chốt còn Q1 trong 12 bài của báo cáo 05/10, và mọi bài LLM/RAG cho RCA hoặc AIOps;
  - 3–5 survey Q1 mới nhất để có khung phân loại;
  - phần còn lại theo điểm, có hạn mức theo cụm để không dồn vào một cụm.
- Đọc **toàn văn**; nhận xét về phương pháp/kết quả chỉ dựa trên phần đã đọc, kèm vị trí (trang, mục, bảng).
- Ghi riêng phần "hạn chế" và "hướng tương lai" do chính tác giả nêu: đây là nguồn gap trực tiếp nhất.

Phiếu trích xuất (`extraction.csv`, mỗi bài một dòng):

| Cột | Nội dung |
|---|---|
| id, doi, venue, year, quartile | định danh |
| problem | phát hiện / định vị / phân loại lỗi / giải thích / khác |
| system_context | microservice, cloud, mạng, log hệ thống… |
| datasets | benchmark và hệ thống dùng (Online Boutique, Sock Shop, Train Ticket, AIOpsLab, dữ liệu công nghiệp…), số hệ thống |
| modalities | metric / log / trace / kết hợp |
| method_family | thống kê, đồ thị, nhân quả, GNN, LLM, LLM-agent, RAG… |
| llm | tên, cỡ, open-weight hay API, có fine-tune không |
| retrieval | không / sparse / dense / hybrid; truy hồi cái gì (runbook, sự cố cũ, code) |
| propagation | có tách nơi phát sinh khỏi nơi biểu hiện không, bằng cách nào |
| confidence | có độ tin cậy/bất định không; có đo hiệu chỉnh (ECE, Brier) không |
| explanation | có giải thích không; có độ đo cho giải thích không; ai chấm |
| compression_cost | có xử lý giới hạn ngữ cảnh/chi phí token, độ trễ không |
| metrics | độ đo báo cáo (AC@k, MRR, F1…) |
| artifacts | code/dữ liệu công khai không |
| limitations, future_work | nguyên văn ngắn + vị trí |
| locators | trang/mục cho từng ô ở trên |

## Tệp

- Đọc: `work/top100.csv`, PDF trong `private/fulltext/` (D6).
- Tạo: `work/read50.csv` (danh sách chọn + lý do), `work/extraction.csv`, `work/access-log.csv` (nguồn lấy toàn văn, bài không lấy được).

## Các bước

1. Chọn danh sách theo yêu cầu, ghi lý do chọn từng bài.
2. Lấy toàn văn: OA qua OpenAlex/Unpaywall, thư viện UIT, bản tác giả. Ghi nguồn vào `access-log.csv`. Bài không lấy được thì thay bằng bài kế tiếp cùng cụm.
3. Chia đọc giữa hai thành viên theo cụm; mỗi người đọc chéo 5 bài của người kia để kiểm độ nhất quán của phiếu.
4. Điền phiếu theo từng bài; ô không có thông tin ghi `not-reported`, không đoán.
5. Mỗi 10 bài, rà nhanh phiếu: cột nào hay bị bỏ trống thì làm rõ định nghĩa.

## Kiểm tra

- Mọi ô khác `not-reported` trong các cột phương pháp/kết quả có vị trí trích.
- 5 bài đọc chéo: các cột llm, retrieval, propagation, confidence, explanation khớp giữa hai người; lệch thì đọc lại và sửa.
- Không có PDF hay đoạn trích dài nằm trong `plans/`.
- Số bài đọc được và số bài thay thế ghi trong `prisma-counts.json`.

## Rủi ro / hoàn tác

- Trùng tuần nộp NT114: lùi giai đoạn một tuần, không giảm chất lượng phiếu.
- Toàn văn sau paywall: hỏi thư viện UIT hoặc email tác giả; nếu vẫn không có, thay bài và ghi lại.
- Đọc quá nhanh, phiếu nông: ưu tiên 25–30 bài sát nhất được đọc kỹ; các bài còn lại có thể đọc theo mục (abstract, method, experiment, limitation) nhưng phải ghi mức đọc.
- Hoàn tác: phiếu là tệp CSV có lịch sử; giữ bản cũ khi sửa.
