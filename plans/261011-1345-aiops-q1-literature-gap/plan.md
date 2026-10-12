---
title: "Khảo sát tài liệu Q1 cho NCKH AIOps: từ khóa → ~100 bài → đọc ~50 → ý tưởng ~25 → hướng chưa ai làm"
description: "Kế hoạch khảo sát có hệ thống các bài tạp chí Q1 (SCImago SJR) liên quan đề tài NT114, tìm và kiểm chứng research gap, rồi chấm điểm các hướng nghiên cứu để nhóm và GVHD chọn."
status: in-progress
priority: P1
effort: "~4 tuần (12/10 – 12/11/2026), ước lượng"
plan_location: "F:/Nam/UIT/NT114 - NCKH/plans/261011-1345-aiops-q1-literature-gap/"
branch: n/a (không phải git repo)
tags: [nckh, aiops, rca, llm, rag, literature-review, q1, scimago]
blockedBy: []
blocks: []
created: 2026-10-11
---

# Khảo sát tài liệu Q1 cho NCKH AIOps

## Outcome

Một báo cáo khảo sát có thể kiểm lại được, trả lời: **trong các bài tạp chí Q1, hướng nào gần đề tài NT114 mà chưa ai làm,
và hướng nào đáng làm nhất với nguồn lực của nhóm.** Chuỗi đầu ra:

1. Bộ từ khóa và chuỗi truy vấn rút ra từ Proposal, kèm giao thức lọc Q1 theo SCImago.
2. Danh sách **~100 bài Q1 tốt nhất** (có điểm xếp hạng và lý do giữ/loại).
3. Phiếu trích xuất cho **~50 bài đọc toàn văn**, mỗi ô có vị trí trích (trang/mục).
4. **~25 thẻ ý tưởng** lấy được từ các bài, gắn với mục tương ứng của Proposal.
5. Ma trận khái niệm → danh sách gap, mỗi gap đã qua bước "cố bác bỏ".
6. Bảng chấm điểm các hướng, đề xuất 2–3 hướng tốt nhất kèm RQ, thí nghiệm tối thiểu và tạp chí đích.

Các con số 100/50/25 là mục tiêu tương đối theo yêu cầu, được phép lệch nếu có lý do ghi lại.

## Đầu vào và hiện trạng

| Nguồn | Hiện trạng | Ghi chú |
|---|---|---|
| `Proposal.docx` | sha256 `70be642e…26a6` (đo 11/10/2026, khớp bản trích) | Đã trích thành [proposal-paragraphs.txt](source-review/proposal-paragraphs.txt), mã đoạn P0001–P0202 |
| Báo cáo gap 05/10 | [research-261005-2138-q1-research-gap.md](../reports/research-261005-2138-q1-research-gap.md) | 83 bài Q1 từ OpenAlex + SJR 2025, **chỉ đọc abstract**; 8 gap ứng viên G1–G8. Dùng làm hạt giống, chưa được coi là đã kiểm |
| Bản đồ mảng 05/10 | [research-261005-0008-ban-do-mang-tiem-nang.md](../reports/research-261005-0008-ban-do-mang-tiem-nang.md) | Tham khảo; nguồn không chỉ Q1 |
| Plan Q1 05/10 | [plan đã hủy](../261005-0008-nckh-q1-rca-lan-truyen-tin-cay/plan.md) | Hủy vì hướng do AI tự chọn. Bài học: **nhóm và GVHD chọn hướng**, plan này chỉ đưa bằng chứng và bảng điểm |
| Góp ý GVHD 29/09 | `note/note-29-9.txt` | 2–3 ứng dụng + bảng so sánh; tìm nơi phát sinh trên đường lan truyền; chạy khung trước rồi nâng cấp; độ chính xác bao nhiêu %, vì sao |
| Bảng xếp hạng | https://www.scimagojr.com/journalrank.php | Tiêu chí lọc Q1 do người dùng chỉ định |

## Quyết định (D1, D2 người dùng chốt 11/10/2026; còn lại là mặc định, đổi được)

| Mã | Quyết định | Mặc định | Lý do |
|---|---|---|---|
| D1 | Định nghĩa "Q1" | **Đã chốt 11/10.** Tạp chí có **SJR Best Quartile = Q1** trong năm SJR mới nhất trên scimagojr.com (dự kiến 2025); ghi thêm quartile theo đúng chuyên ngành CS liên quan | Thống nhất với báo cáo 05/10; người dùng chỉ định SCImago |
| D2 | Hội nghị (ICSE/FSE/ASE/KDD/WWW/EuroSys), arXiv | **Đã chốt 11/10.** **Không tính** vào 100/50/25. Chỉ dùng ở bước "cố bác bỏ gap" (Phase 04) và ghi riêng | Đúng tiêu chí "chỉ Q1", nhưng gap "chưa ai làm" mà đã có ở ICSE/arXiv thì reviewer Q1 sẽ bắt |
| D3 | IEEE Access, Scientific Reports | Giữ (đạt Q1 theo SJR) nhưng gắn cờ `q1-weak` | Báo cáo 05/10 câu hỏi mở 1 |
| D4 | MDPI | Loại | Kế thừa báo cáo 05/10; người dùng có thể bỏ |
| D5 | Dataset/công cụ không Q1 (RCAEval, AIOpsLab, Drain, BM25…) | Được dùng làm dữ liệu/công cụ, không tính là bài khảo sát | Tiêu chí Q1 áp cho tài liệu làm căn cứ khoa học |
| D6 | Nơi lưu PDF toàn văn | `private/fulltext/` ở gốc dự án, không chia sẻ, không đưa vào plans/ | Quyền truy cập ≠ quyền phân phối lại |
| D8 | Tạp chí đích | Chưa có (người dùng, 11/10). Phase 05 đề xuất 2–3 tạp chí Q1 cho mỗi hướng dựa trên nơi các bài cùng loại trong corpus đã đăng; không cộng trọng số ưu tiên tạp chí | Người dùng chưa chọn |
| D7 | Khoảng năm | 2020 – 2026; survey kinh điển trước 2020 chỉ dùng làm bối cảnh | Hướng LLM/RAG chủ yếu từ 2023 |

## Các giai đoạn

| Giai đoạn | Tên | Trạng thái | Thời gian (ước lượng) | Phụ thuộc | Skill thực thi |
|---|---|---|---|---|---|
| [01](phase-01-tu-khoa-va-giao-thuc-loc-q1.md) | Rút từ khóa, viết truy vấn, giao thức lọc Q1 | hoàn thành 11/10 | 12/10 – 13/10 | — | nckh-cook + nckh-literature |
| [02](phase-02-tim-va-xep-hang-100-bai.md) | Tìm, lọc Q1, xếp hạng ~100 bài | hoàn thành 11/10 | 14/10 – 19/10 | 01 | nckh-cook + nckh-literature |
| [03](phase-03-doc-toan-van-50-bai.md) | Chọn và đọc toàn văn ~50 bài, phiếu trích xuất | hoàn thành 12/10 (47 toàn văn + 22 tóm tắt) | 20/10 – 02/11 | 02 | nckh-cook + nckh-research |
| [04](phase-04-tong-hop-y-tuong-va-gap.md) | ~25 thẻ ý tưởng, ma trận khái niệm, gap + cố bác bỏ | hoàn thành 12/10 (32 thẻ, 11 gap) | 03/11 – 07/11 | 03 | nckh-cook + nckh-research + nckh-evidence |
| [05](phase-05-danh-gia-va-xep-hang-huong.md) | Chấm điểm và xếp hạng hướng nghiên cứu | hoàn thành 12/10, bản nháp một người chấm | 08/11 – 10/11 | 04 | nckh-cook + nckh-research |
| [06](phase-06-ra-soat-va-ban-giao.md) | Rà soát, viết báo cáo cuối, bàn giao GVHD chọn hướng | in-progress: chờ rà soát độc lập và GVHD | 11/11 – 12/11 | 05 | nckh-review + nckh-cook |

Phase 03 trùng tuần nộp NT114 (hạn tạm 20/10/2026). Nếu bị dồn, đẩy Phase 03 lùi một tuần thay vì giảm số bài đọc.

Báo cáo cuối: [research-261012-q1-survey-and-directions.md](../reports/research-261012-q1-survey-and-directions.md).
Báo cáo trung gian: [research-261012-q1-ideas-and-gaps.md](../reports/research-261012-q1-ideas-and-gaps.md).

## Tệp làm việc (tạo trong lúc thực thi)

Toàn bộ dữ liệu trung gian nằm trong `work/` của thư mục plan này: `keywords.csv`, `queries.csv`, `sjr-<năm>.csv` (+ sha256),
`raw-hits.csv`, `screened.csv`, `top100.csv`, `read50.csv`, `extraction.csv`, `ideas25.csv`, `concept-matrix.csv`,
`gaps.csv`, `direction-scores.csv`, `prisma-counts.json`, và `scripts/` (Python chạy bằng `python -X utf8`).
Báo cáo Markdown đặt ở `plans/reports/`.

## Acceptance criteria

- [x] Mỗi từ khóa truy được về ít nhất một đoạn Proposal (mã Pxxxx); mỗi truy vấn có số kết quả và ngày chạy.
- [x] Tệp SJR tải trực tiếp từ scimagojr.com, ghi năm SJR, ngày tải và sha256; mọi bài trong `top100.csv` khớp ISSN với tệp đó và có quartile.
- [x] Có sơ đồ đếm kiểu PRISMA: tìm được → bỏ trùng → lọc Q1 → lọc tiêu đề/abstract → top ~100 → đọc ~50 → ý tưởng ~25; mọi bài bị loại có lý do.
- [x] Không bài nào trong ~50 bài được ghi nhận xét về phương pháp/kết quả nếu chưa đọc toàn văn; mỗi ô phiếu trích có vị trí trang/mục.
- [x] Mỗi gap có: bài gần nhất (Q1) kèm vị trí trích, kết quả tìm cố bác bỏ (Q1 + hội nghị/arXiv theo D2), và trạng thái `confirmed | partially-filled | refuted`. Ngoài Q1 mới dùng arXiv API, chưa dùng Google Scholar/DBLP (ghi ở mục hạn chế của báo cáo cuối).
- [x] 2–3 hướng đề xuất, mỗi hướng có RQ, giả thuyết, dữ liệu, baseline, độ đo, thí nghiệm tối thiểu, tạp chí đích Q1 (đã kiểm SJR), rủi ro và điều kiện dừng.
- [x] Xếp hạng hướng giữ ổn định khi đổi trọng số (kiểm độ nhạy); nếu không ổn định thì ghi rõ.
- [ ] Hướng cuối cùng do nhóm và GVHD chọn; báo cáo không tự chốt.

## Rủi ro chung

- **Q1-only bỏ sót công trình mạnh nhất.** Nhiều bài LLM-RCA nằm ở ICSE/FSE/ASE/arXiv. Xử lý theo D2: không tính vào corpus nhưng bắt buộc dùng để cố bác bỏ gap.
- **Kết luận từ abstract.** Báo cáo 05/10 chỉ dựa abstract. Mọi gap kế thừa phải qua đọc toàn văn trước khi dùng.
- **Không lấy được toàn văn.** Dùng OA (OpenAlex/Unpaywall), thư viện UIT, bản tác giả; bài không lấy được thì thay bằng bài kế tiếp cùng cụm và ghi lại.
- **Năm SJR lệch.** Quartile đổi theo năm; ghi rõ năm SJR dùng và quartile năm xuất bản nếu khác.
- **Lặp lại lỗi plan 05/10** (tự chọn hướng). Phase 05 chỉ xếp hạng có bằng chứng; Phase 06 trao quyền chọn cho nhóm và GVHD.

## Câu hỏi còn mở

Không còn câu hỏi chặn. D3–D7 là mặc định; đổi thì ghi lại trong bảng quyết định trước khi chạy Phase 01.
