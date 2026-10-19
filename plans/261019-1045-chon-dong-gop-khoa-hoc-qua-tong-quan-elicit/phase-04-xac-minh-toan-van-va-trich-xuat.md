---
phase: 4
title: "Xác minh toàn văn và trích xuất có cấu trúc"
status: completed
effort: 2-3 ngày
depends_on: [3]
---

# Phase 04: Xác minh toàn văn và trích xuất

## Thứ tự đọc

1. Mọi bài relevance 2 với bất kỳ H nào (bắt buộc).
2. Mọi bài khối C (phản chứng) có relevance ≥ 1 với H1.
3. Bài relevance 1 có dataset trùng với NT114 (RCAEval, Nezha, RCA100, AIOps2025) hoặc có thí nghiệm cắt modality.
4. `maybe` còn lại, theo citedByCount giảm dần, tới khi hết thời gian của phase.

## Nguồn toàn văn

Theo thứ tự: `fullTextUrl` của Elicit → `get_library_source_full_text` (nếu Phase 01 xác nhận chạy
được) → arXiv / OpenReview / trang tác giả / ACM/IEEE truy cập mở → `private/fulltext/` cục bộ cho bài
261011. Bản tải mới lưu ở `private/fulltext/261019/` (đã git ignore). Không lấy được → `verified_full_text = unavailable` kèm lý do, và mọi phát hiện từ bài đó giữ
`evidence_location = abstract-only`, `uncertainty ≥ medium`.

Tuỳ chọn: `create_report` với `maxExtractPapers ≤ 80` trên tập relevance 2, dùng cùng câu hỏi trích xuất,
**chỉ để đối chiếu**. Mỗi ô Elicit trích ra phải được kiểm với toàn văn trước khi vào `findings.csv`.

## Schema trích xuất

Giữ toàn bộ cột của research/03 (paper_id, venue_type, peer_reviewed, rq, dataset, n_incidents,
modalities, missingness_manipulation, method_family, llm, candidate_generation, confidence_estimator,
abstention, acquisition/cost, eval mode, split_protocol, leakage_controls, baselines, metrics, ablation,
stage_wise_errors, code/data, relevance_H1–H3, overlap_note, quote, extractor, verified_full_text) và thêm:

| Cột mới | Ý nghĩa |
|---|---|
| `work_id`, `source_url`, `pub_status`, `pub_status_checked_at` | Từ Phase 03 |
| `n_independent_units` | Số đơn vị độc lập thật (injection/fault, không phải bản ghi); "unknown" nếu không rõ |
| `coverage_matched` | Có so ở cùng coverage hoặc báo risk–coverage/AURC không (`yes/no/partial`) |
| `confidence_source` | verbal / token-prob / self-consistency / vote share / learned / conformal / none |
| `confidence_discrimination` | AUROC, ECE hoặc tương đương, kèm giá trị |
| `missing_control` | Thiếu telemetry do thiết kế thí nghiệm có kiểm soát, tự nhiên, hay không có |
| `stat_test` | Kiểm định thống kê và CI có báo không |
| `protocol_v2_compat` | Kết quả có so được trực tiếp với endpoint của protocol v2 không (AC@k, MRR@5 censored, selective, cost) |
| `evidence_location` | Mục/bảng/hình/trang cho từng khẳng định chính |
| `uncertainty` | low/medium/high + lý do |

Mỗi khẳng định đủ quan trọng để vào báo cáo → một dòng `work/findings.csv` theo schema plan.md mục 6.

## Câu hỏi bắt buộc với mỗi bài relevance 2 cho H1

1. Confidence của ai (chính LLM hay mô hình phụ)? Có so với baseline không phải LLM không?
2. Có báo risk ở coverage cố định / AURC, hay chỉ ECE / accuracy tổng?
3. Thiếu telemetry có được tạo có kiểm soát không? Modality nào?
4. Bao nhiêu đơn vị độc lập? Có CI không?
5. Kết quả có đi ngược H1 ở điều kiện nào không?

## Kiểm chứng

- Mọi bài relevance 2 có `verified_full_text ∈ {yes, unavailable}`.
- Script kiểm `findings.csv`: 11 trường bắt buộc không rỗng; `evidence_location ≠ ""`; mọi `source_url`
  bắt đầu bằng `http`.
- Mẫu 10 dòng ngẫu nhiên của `findings.csv` mở lại nguồn và xác nhận claim khớp vị trí.

## Rủi ro và hoàn tác

- Elicit trích sai → không bao giờ chép trực tiếp vào findings.
- Quá nhiều bài → giữ thứ tự ưu tiên, ghi số bài chưa đọc vào hạn chế.
