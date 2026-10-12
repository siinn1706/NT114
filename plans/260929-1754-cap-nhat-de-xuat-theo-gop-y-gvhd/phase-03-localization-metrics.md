---
phase: 3
title: "Bộ độ đo phát hiện và service localization"
status: completed
effort: 1h
---

# Phase 03 — Bộ độ đo phát hiện và service localization

## Góp ý gốc
> Service localization: nên nêu rõ sẽ dùng độ đo cụ thể, ví dụ Top-1, Top-3, Top-5 Accuracy, MRR, hoặc MAP.

## Mục tiêu
Viết lại **mục 6 Cách đánh giá** thành 6.1 Localization, 6.2 Phân loại lỗi và phát hiện, 6.3 Truy hồi (lấy từ phase 02),
6.4 Giải thích (lấy từ phase 04), 6.5 Baseline và kiểm định. Sửa câu trong mục 4.2 (Rank và score) để trỏ sang các độ đo này.

## Nội dung cần đưa vào

Ký hiệu: có N sự cố; với sự cố i, R_i là tập dịch vụ gốc thật và rank_i(s) là thứ hạng hệ thống gán cho dịch vụ s.

- **AC@k (Top-k Accuracy)**, với k ∈ {1, 3, 5}: AC@k = (1/N) Σ_i 1[∃ s ∈ R_i : rank_i(s) ≤ k].
- **Avg@5** = (1/5) Σ_{k=1..5} AC@k. Đây là độ đo tổng hợp mà RCAEval dùng, nên đưa vào để so sánh trực tiếp với các baseline của benchmark.
- **MRR** = (1/N) Σ_i 1 / min_{s∈R_i} rank_i(s). Nếu dịch vụ gốc không có trong danh sách thì tính là 0.
- **MAP** = (1/N) Σ_i AP_i, với AP_i = (1/|R_i|) Σ_{s∈R_i} Precision@rank_i(s).
  Cần ghi rõ: RE2-OB mỗi sự cố chỉ có 1 dịch vụ gốc, tức |R_i| = 1, nên AP_i = 1/rank và **MAP trùng MRR**.
  MAP vẫn được báo cáo để dùng khi mở rộng sang sự cố có nhiều dịch vụ liên quan, và để đánh giá truy hồi (nhiều tài liệu liên quan).
- **Phân loại lỗi (Fault):** accuracy và macro-F1 trên 6 lớp, kèm confusion matrix.
- **Phát hiện (`none` hay có lỗi)** — nay là phần lõi (xem phase 08): precision, recall, F1 và false positive rate trên các cửa sổ bình thường (trước khi tiêm lỗi) và cửa sổ bất thường; thêm **thời gian phát hiện** (khoảng cách từ lúc tiêm lỗi đến lúc báo). So sánh z-score với Isolation Forest.
- **Chi phí:** latency và số token cho mỗi sự cố.

**Baseline.** Các phương pháp RCA có sẵn trong RCAEval (ví dụ BARO, RCD, CIRCA; danh sách cụ thể kiểm tra lại
trong repo RCAEval), một baseline heuristic đơn giản (xếp hạng theo max z-score), và LLM không dùng retrieval.

**Kiểm định thống kê.** Chỉ có 90 sự cố nên cần báo khoảng tin cậy 95% bằng bootstrap (1000 lần lấy mẫu lại).
So sánh từng cặp phương pháp bằng paired bootstrap hoặc McNemar cho AC@1.

**Phân tích lỗi.** Giữ nội dung Proposal hiện có và phân loại các ca sai thành: thiếu dữ liệu / lan truyền triệu chứng / nén làm mất bằng chứng / retrieval sai / LLM suy luận sai.

## Các bước
1. Kiểm tra lại cách RCAEval định nghĩa AC@k và Avg@5, cùng danh sách baseline, trong paper và repo.
2. Viết mục 6.1, 6.2 và 6.5 kèm công thức. Dùng Equation trong Word hoặc viết công thức dạng văn bản rõ ràng.

## Kiểm tra
- Có đủ Top-1/3/5, MRR và MAP như GVHD nêu, kèm công thức.
- Có giải thích vì sao MAP = MRR khi chỉ có một nhãn.
