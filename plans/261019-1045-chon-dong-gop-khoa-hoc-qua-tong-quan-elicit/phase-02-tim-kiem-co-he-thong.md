---
phase: 2
title: "Tìm kiếm có hệ thống"
status: completed
effort: 1 ngày
depends_on: [1]
---

# Phase 02: Tìm kiếm có hệ thống

## Bối cảnh

Tìm phạm vi cho thấy semantic search trôi miền và keyword (Lucene) mode chính xác thấp, không nhận
filter ([hồ sơ](research/elicit-mcp-capability-record.md) mục 3–4). Vì vậy mỗi khối dùng **nhiều bộ
từ đồng nghĩa**, cả hai chế độ, và một nguồn đối chiếu ngoài Elicit cho các bài then chốt.

## Khối truy vấn (bản nháp, đóng băng ở Phase 01)

Mặc định: corpus `elicit`, semantic, `minYear: 2020`, `maxYear: 2026`, `retracted: exclude`,
`excludeKeywords: [patient, clinical, hospital, nursing, healthcare]`, `maxResults` theo trần đo ở Phase 01
(mặc định 200). Keyword mode: cùng chuỗi Lucene, không filter.

| Khối | Mục tiêu | Truy vấn semantic (mỗi dòng là một truy vấn) | Truy vấn keyword (Lucene) |
|---|---|---|---|
| **A. H1 lõi** | LLM-RCA + confidence/abstention | 1. confidence estimation for LLM root cause analysis of cloud incidents · 2. calibrated uncertainty and abstention in LLM-based fault localization for microservices · 3. selective prediction risk-coverage for AIOps incident diagnosis · 4. when should an LLM refuse to diagnose an incident, insufficient evidence | `("root cause" OR "fault localization" OR incident) AND (LLM OR "language model") AND (confidence OR calibration OR abstain* OR uncertainty)` |
| **B. H1 + thiếu telemetry** | Cắt modality có kiểm soát + confidence | 1. root cause analysis with missing traces logs or metrics robustness · 2. multimodal RCA under missing modality ablation microservice · 3. LLM diagnosis degraded observability incomplete telemetry | `("root cause" OR RCA) AND (missing OR incomplete OR absent) AND (trace OR log OR metric) AND modality` |
| **C. H1 phản chứng** | Confidence LLM không đáng tin, abstention không giúp | 1. verbalized confidence of LLMs does not track correctness · 2. LLM overconfidence calibration failure reasoning tasks · 3. selective prediction with LLMs fails under distribution shift · 4. self-consistency versus verbal confidence versus token probability comparison · 5. abstention benchmark LLMs fail to abstain | `(LLM OR "language model") AND (overconfiden* OR miscalibrat*) AND (abstention OR "selective prediction")` |
| **D. H1 phương pháp** | Conformal, risk control, AURC | 1. conformal prediction abstention large language models risk control · 2. area under risk coverage curve evaluation selective classification · 3. conformal prediction for root cause or fault localization | `conformal AND (abstention OR "risk control") AND (LLM OR "language model")` |
| **E. H2** | Thu thập bằng chứng có ngân sách | 1. budget-aware evidence acquisition for incident diagnosis · 2. cost-aware adaptive telemetry retrieval for root cause analysis · 3. LLM agent tool calls cost accuracy trade-off for RCA · 4. active information gathering value of information fault diagnosis software systems | `("root cause" OR incident) AND (budget OR cost-aware OR "value of information") AND (telemetry OR observability OR tool)` |
| **F. H3** | Sinh ứng viên vs xếp hạng | 1. retrieval reranking decomposition root cause analysis failures · 2. candidate generation versus ranking error analysis fault localization · 3. where root cause analysis fails error taxonomy LLM · 4. two-stage candidate shortlist root cause service localization | `("root cause" OR "fault localization") AND (rerank* OR "candidate generation" OR shortlist OR decomposition)` |
| **G. Benchmark và protocol** | Độ tin cậy đánh giá, leakage, cỡ mẫu | 1. benchmark for root cause analysis in microservices RCAEval · 2. evaluation pitfalls data leakage in AIOps root cause benchmarks · 3. retrieval augmented RCA historical incidents leakage similar incidents · 4. statistical significance and sample size in RCA evaluation | `("root cause" OR AIOps) AND benchmark AND (leakage OR reproducib* OR "data split")` |
| **H. Hạt giống** | Tìm đúng bài đã biết | Tiêu đề chính xác của: DecompRCA, PACE-LM, LM-PACE, TraceBudget, VerifyRCA, PRISM, RCAEval, Nezha, P18/P31/P42/P50 (file `plans/261011-1345-aiops-q1-literature-gap/work/extraction.csv` chỉ có DOI, không có tiêu đề → tra tiêu đề từ DOI qua Crossref trước) | — |

Khối C có trọng số ngang khối A: số truy vấn C ≥ số truy vấn A.

## Nguồn đối chiếu ngoài Elicit

Elicit có thể thiếu preprint mới và metadata hội nghị. Với mỗi khối A, C, E, F, chạy **một** truy vấn
tương đương trên ít nhất một nguồn công khai: arXiv API, Semantic Scholar API, OpenAlex hoặc DBLP. Ghi
cùng định dạng vào `work/search-log.csv` với cột `engine`. Đây là truy vấn công khai, cùng quy tắc ở
Phase 01.

## Systematic review của Elicit (đã chọn: `thorough`, `useFigures: true`)

Một review cho mỗi nhóm {A+B+C+D}, {E}, {F+G}, tối đa 20 truy vấn mỗi review, tiêu chí sàng lọc lấy
nguyên văn từ Phase 01, câu hỏi trích xuất lấy từ schema Phase 04. Nêu rõ thiết lập trước mỗi lệnh gọi.
Chạy review đầu tiên, đọc `percentUsed`; nếu vượt 20 % thì dừng và hỏi chủ dự án trước hai review còn lại. Kết quả xuất CSV qua `get_systematic_review` và coi như
một nguồn thô nữa; quyết định sàng lọc của Elicit được **kiểm lại thủ công** trên mẫu ở Phase 03.

## Ghi chép

`work/search-log.csv`: `query_id, block, engine, mode, query_string, filters_json, max_results,
run_at_utc, n_returned, raw_file, public_check, percent_used_before, percent_used_after`.
Mỗi lệnh lưu JSON thô vào `work/raw/<query_id>.json`.

## Kiểm chứng

- Mỗi khối A–G có ≥ 3 truy vấn semantic và 1 keyword đã chạy; khối C có ≥ 5.
- Không có truy vấn nào có `public_check` khác `pass`.
- Tổng `percentUsed` ≤ 30 %.
- Nếu một truy vấn trả 0 kết quả hoặc > 80 % lạc miền khi xem 20 đầu: ghi, sửa một lần, ghi sai lệch.

## Rủi ro và hoàn tác

- Trần `maxResults` thấp → chia truy vấn hẹp hơn thay vì tăng số.
- Không có gì cần hoàn tác ngoài xoá `work/raw/`.
