---
phase: 5
title: "Snowballing và hồ sơ DecompRCA"
status: completed
effort: 1-1.5 ngày
depends_on: [4]
---

# Phase 05: Snowballing và hồ sơ DecompRCA

## A. Citation snowballing

**Hạt giống:** mọi bài relevance 2 sau Phase 04, cộng cố định: DecompRCA, PACE-LM/LM-PACE, PRISM
(arXiv 2601.21359), TraceBudget, VerifyRCA, RCAEval, P18, P31, P42, P50.

- **Ngược (backward):** danh sách tài liệu tham khảo của hạt giống.
- **Xuôi (forward):** bài trích dẫn hạt giống, qua Semantic Scholar hoặc OpenAlex (Elicit không có
  API trích dẫn trong danh mục công cụ đã thấy).
- Ứng viên mới qua cùng khử trùng lặp và sàng lọc như Phase 03; bài relevance 2 qua Phase 04.
- **Dừng:** một vòng đầy đủ; vòng hai chỉ cho bài mới có relevance 2. Dừng khi một vòng không thêm bài
  relevance 2 nào.

`work/snowball-log.csv`: `seed_work_id, direction, engine, run_at_utc, n_candidates, n_new_after_dedup,
n_included, n_relevance2`.

## B. Hồ sơ DecompRCA (`research/decomprca-dossier.md`)

DecompRCA là hạt giống của H3 và là chặn duy nhất của V8 bước 2 trong kế hoạch 261018-2300.

Phải trả lời, mỗi câu có nguồn và ngày kiểm:

1. **Trạng thái xuất bản:** "NeurIPS 2026 poster" xác minh qua OpenReview / trang NeurIPS; có arXiv không;
   phiên bản nào.
2. **Artifact:** `github.com/cruiseresearchgroup/DecompRCA` còn 404 không (kiểm lại bằng HTTP HEAD, ghi
   mã); có mirror, supplementary hay Zenodo không. **Không** dựa vào bài mạng xã hội để kết luận repo có.
3. **Phương pháp:** định nghĩa retrieval và reranking; tỉ lệ lỗi mỗi giai đoạn; metric.
4. **Dữ liệu:** dataset, cách tiền xử lý (`main-ase.py`), 125 sự cố mỗi hệ ở RE1; khác gì inventory RE1 của
   NT114 (research/05) — chỉ so ở mức metadata công khai, không gửi inventory của NT114 ra ngoài.
5. **Confidence/abstention:** DecompRCA có đo không? Nếu có → chồng lấn H1.
6. **Hệ quả cho H3:** với `in_candidates = 1` ở NT114 (research/04 dòng 50, 175), phân rã của DecompRCA
   có áp dụng được không, hay cần nhánh shortlist mới? Nhánh đó có đụng tới protocol v2 không?
7. **Hệ quả cho V8 bước 2:** vẫn chặn, mở được, hay nên đổi tiêu chí. Chỉ khuyến nghị; không sửa kế hoạch 261018.

## Kiểm chứng

- Snowball log đủ cho mọi hạt giống, cả hai chiều (hoặc ghi lý do bỏ).
- Hồ sơ DecompRCA trả lời đủ 7 câu, mỗi câu có `source_url` và ngày.

## Rủi ro

- API trích dẫn ngoài có giới hạn tốc độ → chạy tuần tự, cache JSON trong `work/raw/snowball/`.
- Bài NeurIPS 2026 có thể chưa có trong chỉ mục trích dẫn → ghi "forward = 0 do mới".
