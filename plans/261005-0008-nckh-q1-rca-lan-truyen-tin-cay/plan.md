---
title: "Kế hoạch NCKH hướng Q1: RCA microservices theo lan truyền, có bằng chứng và độ tin cậy hiệu chỉnh"
description: "Mở rộng đề tài NT114 (phát hiện sự cố + RCA bằng Hybrid Retrieval và LLM) thành một bài báo tạp chí Q1, focus vào định vị theo lan truyền, giải thích bám bằng chứng và độ tin cậy hiệu chỉnh trên ba hệ thống."
status: cancelled
note: "Hủy 2026-10-05: hướng đi do AI tự chọn, chưa được người dùng duyệt và dựa trên nguồn không phải Q1. Thay bằng plans/reports/research-261005-2138-q1-research-gap.md."
priority: P1
effort: "~6 tháng (10/2026 – 03/2027), chờ người dùng chốt mốc nộp"
branch: n/a (không phải git repo)
tags: [nckh, q1, aiops, rca, llm, calibration, microservices, kubernetes]
blockedBy: []
blocks: []
created: 2026-10-05
---

# Kế hoạch NCKH hướng Q1

## Outcome

Một bài báo tạp chí Q1 có một đóng góp khoa học rõ, không chỉ là ghép khối kỹ thuật:

> Chẩn đoán nguyên nhân gốc **theo lan truyền**, có **bằng chứng kiểm được** và **độ tin cậy hiệu chỉnh**, bằng LLM
> open-weight cỡ nhỏ dưới ngân sách token cố định, đánh giá trên **ba hệ thống** microservice (Online Boutique, Sock
> Shop, Train Ticket của RCAEval RE2).

Lý do chọn focus và các mảng đã cân nhắc: [báo cáo bản đồ mảng tiềm năng](../reports/research-261005-0008-ban-do-mang-tiem-nang.md).

## Đầu vào và quyết định đã có

| Chủ đề | Hiện trạng | Nguồn |
|---|---|---|
| Pipeline nền | Detector → incident card ~4k token → Hybrid Retrieval (BM25 + bge-m3, RRF) → LLM 7–8B → JSON có `evidence_ids` → đánh giá hai tầng | Proposal_v2 mục 5–6 |
| Mô hình | Chỉ open-weight, chạy trên Kaggle/Colab hoặc máy cá nhân | Plan 260929, quyết định 29/09 |
| Đánh giá trên nhiều ứng dụng | Ít nhất 2–3 ứng dụng, có bảng so sánh | note 29/09 dòng 1–2 |
| Tìm nơi phát sinh trên đường lan truyền | a→b, hoặc b của a→c; backend/frontend | note 29/09 dòng 4–5 |
| Thứ tự làm | Hiểu trước, chạy khung trước, rồi nâng cấp | note 29/09 dòng 7 |
| Giải thích con số | Độ chính xác bao nhiêu %, vì sao chẩn đoán như vậy, vì sao ra con số đó | note 29/09 dòng 9 |

Đồ án NT114 (hạn tạm 20/10/2026) **chính là Phase 2** của kế hoạch này: khung baseline chạy được. Bài Q1 là phần nâng cấp.

## Câu hỏi nghiên cứu dự kiến (chốt ở Phase 1)

- **RQ1 – Định vị theo lan truyền:** kiểm giả thuyết dọc cạnh đồ thị gọi có giảm nhầm lẫn "nơi biểu hiện ↔ nơi phát sinh" so với xếp hạng bất thường và LLM một lượt không? (AC@1/3/5, Avg@5, MRR; tỉ lệ nhầm sang dịch vụ upstream)
- **RQ2 – Độ tin cậy hiệu chỉnh:** độ tin cậy hệ thống báo ra có khớp tần suất đúng thực tế không, và cho phép từ chối có kiểm soát không? (ECE, Brier, đường selective accuracy–coverage)
- **RQ3 – Giải thích bám bằng chứng:** giải thích có trích bằng chứng hợp lệ, và bỏ bằng chứng then chốt thì kết luận có đổi không? (tỉ lệ trích dẫn hợp lệ, độ nhạy phản thực, rubric hai tầng)
- **RQ4 – Chuyển giao và chi phí:** kết quả có giữ được khi đổi hệ thống và khi giảm ngân sách token không? (train/truy hồi trên một hệ thống, kiểm trên hệ thống khác; token, độ trễ)

## Phases

| Phase | Tên | Trạng thái | Thời gian dự kiến | Phụ thuộc |
|---|---|---|---|---|
| [01](phase-01-khao-sat-va-ho-so-bai.md) | Khảo sát toàn văn, định vị khoảng trống, dựng hồ sơ bài | pending | 05/10 – 19/10/2026 | — |
| [02](phase-02-chay-khung-baseline.md) | Chạy khung baseline trên 3 hệ thống (= đồ án NT114) | pending | 05/10 – 20/10/2026 | song song 01 |
| [03](phase-03-dinh-vi-theo-lan-truyen.md) | Định vị theo lan truyền (RQ1) | pending | 21/10 – 30/11/2026 | 01, 02 |
| [04](phase-04-do-tin-cay-va-bang-chung.md) | Độ tin cậy hiệu chỉnh và bằng chứng kiểm được (RQ2, RQ3) | pending | 01/11 – 15/12/2026 | 02; ghép với 03 |
| [05](phase-05-thuc-nghiem-day-du.md) | Thực nghiệm đầy đủ, ablation, chuyển giao, thống kê (RQ4) | pending | 15/12/2026 – 20/01/2027 | 03, 04 |
| [06](phase-06-viet-bai-va-ra-soat.md) | Viết bài, rà nhiều vòng, nộp | pending | 20/01 – 03/2027 | 05 |

Phase 01 và 02 chạy song song: 02 không cần biết đóng góp mới là gì, chỉ cần khung chạy được và số baseline thật.

## Acceptance criteria

- [ ] Có bảng định vị (Phase 1) chứng minh bằng toàn văn rằng tổ hợp lan truyền + bằng chứng + hiệu chỉnh chưa được công trình nào làm trọn; nếu đã có, đã chuyển sang phương án dự phòng (hiệu chỉnh + chuyển giao) và ghi lý do.
- [ ] Hồ sơ bài (`profiles/<tên-bài>/ho-so.md`) có đủ các mục quy chuẩn NCKH mục 0.2, được mentor duyệt khung section và RQ trước khi viết chi tiết.
- [ ] Baseline chạy được end-to-end trên RE2-OB, RE2-SS, RE2-TT, có bảng so sánh với BARO/RCD/CIRCA từ RCAEval.
- [ ] Mỗi RQ có câu trả lời bằng số, kèm khoảng tin cậy bootstrap 95% và kiểm định cặp.
- [ ] Mỗi chẩn đoán trả về độ tin cậy, và độ tin cậy đó có ECE báo cáo được; trả lời được "vì sao 82%".
- [ ] Mọi tài liệu tham khảo đã đọc toàn văn và kiểm metadata; không MDPI.
- [ ] Code, cấu hình, nguồn dữ liệu ghi trong README từ ngày đầu; mọi lần chạy có trong MLflow.

## Rủi ro chung

- **Trùng ý tưởng.** EviRCA, GALA, SpecRCA (arXiv 2026) gần với hướng này. Phải đọc toàn văn trong tuần đầu; nếu trùng, dùng phương án dự phòng thay vì cố giữ.
- **Dữ liệu ít.** RE2 mỗi hệ thống ~90 sự cố. Báo khoảng tin cậy, không khẳng định "vượt trội" khi khoảng tin cậy chồng nhau; gộp 3 hệ thống để tăng cỡ mẫu cho phần hiệu chỉnh.
- **Rò rỉ nhãn** khi truy hồi sự cố lịch sử: chia fold theo lần lặp như Proposal_v2 mục 5.4; thêm thiết lập chéo hệ thống.
- **GPU giới hạn.** Giữ mô hình 7–8B lượng tử hóa 4-bit; mọi output LLM được cache để chạy lại đánh giá không tốn GPU.
- **Hạn NT114 sát.** Phase 2 chỉ nhắm khung tối thiểu (Proposal_v2 mục 7); phần K8s demo và LoRA không chặn bài Q1.

## Câu hỏi còn mở (cần người dùng trả lời trước khi chốt Phase 1)

1. Tạp chí mục tiêu và mốc nộp bài?
2. Mentor/đồng tác giả chính, và bài viết bằng LaTeX trên Overleaf (export hay đồng bộ git)?
3. Có dùng thêm RCAEval RE1 (metric-only) và RE3 (lỗi mức code) không?
4. Bài có phải công bố code và dữ liệu không?
