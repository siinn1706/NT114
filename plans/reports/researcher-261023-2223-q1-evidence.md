---
title: "Q1 evidence audit: paper core and baseline-to-improvement contract"
date: 2026-10-23
scope: "Read-only evidence review for the Q1 paper set and the single-LLM evaluation contract"
---

# Kết luận

- **Chưa có quy định cuối cùng về đúng ba bài nền tảng.** `plans/261011-1345-aiops-q1-literature-gap/plan.md` vẫn `in-progress`; tiêu chí “Hướng cuối cùng do nhóm và GVHD chọn” còn bỏ trống. Báo cáo khảo sát cũng ghi rõ **không tự chọn hướng**. Xem [plan](../261011-1345-aiops-q1-literature-gap/plan.md:87) và [survey](research-261012-q1-survey-and-directions.md:7).
- Kho hiện có là **bằng chứng ứng viên** (47 bài đọc toàn văn, 22 bài chỉ đọc tóm tắt), không phải bộ ba đã chốt. `research/02_research_directions.md` còn ghi mọi tuyên bố gap là `UNVERIFIED UNTIL LITERATURE REVIEW`.
- Hợp đồng đánh giá single-LLM đã khá tái lập, nhưng là **hạ tầng đo lường**, chưa phải hợp đồng đóng góp của bài báo: chưa có phương pháp được chọn, bộ ba bài so sánh, họ kiểm định xác nhận, preregistration, hay kết quả improvement quan sát được.

# Giao thức Q1 và giới hạn diễn giải

- Q1 cục bộ được định nghĩa là **SCImago SJR Best Quartile 2025**, khớp ISSN; quartile theo năm xuất bản không được kiểm. CSV SJR: [scimagojr-2025-nckh.csv](../261011-1345-aiops-q1-literature-gap/work/scimagojr-2025-nckh.csv), SHA-256 `6f20399957173a13e3c1729a5fb3b5821844ba75e8d640c8b3040ab19a6f7180`. Giao thức: [q1-protocol.md](../261011-1345-aiops-q1-literature-gap/work/q1-protocol.md:24).
- `q1-filter.py` giữ bài khi ISSN có Best Quartile Q1; `cs_category_q1` chỉ là cờ bổ sung. Vì vậy “Q1” không đồng nghĩa “Computer Science Q1”.
- [review-findings.md](../261011-1345-aiops-q1-literature-gap/work/review-findings.md:16) báo cáo 69/69 DOI và ISSN Q1 khớp, nhưng đây là rà soát do chính tác giả báo cáo chạy, chưa phải review độc lập.

# Bài đã có trong corpus và giá trị dùng được

| ID và bằng chứng cục bộ | Kiểm tra Q1 / nguồn công khai | Vai trò thực tế; không nên suy diễn |
|---|---|---|
| **P07 TAMO**, [read-final:8](../261011-1345-aiops-q1-literature-gap/work/read-final.csv:8), [extraction:8](../261011-1345-aiops-q1-literature-gap/work/extraction.csv:8) | IEEE TSC; SJR 1.597, `cs_category_q1=1`; [DOI](https://doi.org/10.1109/TSC.2025.3629066) | Tool-assisted multimodal RCA trên HipsterShop/SocialNetwork. LLM chủ yếu tổng hợp báo cáo; điểm localization đến từ tool, nên chưa phải baseline single-LLM trực tiếp. |
| **P57 TVDiag**, [read-final:56](../261011-1345-aiops-q1-literature-gap/work/read-final.csv:56), [extraction:34](../261011-1345-aiops-q1-literature-gap/work/extraction.csv:34) | ACM TOSEM; SJR 1.590, `cs_category_q1=1`; [DOI](https://doi.org/10.1145/3734868) | Multimodal GNN, task-oriented và view-invariant; có HR@k/F1 trên bốn bộ dữ liệu. Là candidate-generation/localization reference, không phải LLM/RAG baseline. |
| **P18**, [read-final:19](../261011-1345-aiops-q1-literature-gap/work/read-final.csv:19), [extraction:15](../261011-1345-aiops-q1-literature-gap/work/extraction.csv:15) | IEEE TDSC; SJR 1.758, `cs_category_q1=1`; [DOI](https://doi.org/10.1109/TDSC.2026.3706572) | Direct microservice RCA bằng multi-agent recursion-of-thought trên AIOps/TrainTicket/RCAEval. Phụ thuộc trace coverage; là ứng viên nền tảng mạnh, chưa được nhóm chốt. |
| **P31**, [read-final:32](../261011-1345-aiops-q1-literature-gap/work/read-final.csv:32), [extraction:20](../261011-1345-aiops-q1-literature-gap/work/extraction.csv:20) | *Complex & Intelligent Systems*; SJR 1.085, `cs_category_q1=1`; [Springer](https://link.springer.com/article/10.1007/s40747-025-02096-0) | Direct multi-agent RCA có retrieval/validation và baseline CoT, RAG top-5, RCACOPILOT, RCAgent; phù hợp nhất để làm retrieval/RCA anchor nếu được chọn. |
| **P42 Trustworthy**, [read-final:43](../261011-1345-aiops-q1-literature-gap/work/read-final.csv:43), [extraction:24](../261011-1345-aiops-q1-literature-gap/work/extraction.csv:24) | *Results in Engineering*; SJR 1.240, Best Q1 nhưng `cs_category_q1=0`; [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2590123026015252) | NeuSymRCA báo ECE, coverage, prediction-set size và MRR. Hữu ích cho calibration/uncertainty; GPT-4 API, service-level, không nên gọi unqualified là CS-Q1. |
| **P45 RunbookFX**, [read-final:46](../261011-1345-aiops-q1-literature-gap/work/read-final.csv:46), [extraction:27](../261011-1345-aiops-q1-literature-gap/work/extraction.csv:27) | PACM ICFP; SJR 0.928, `cs_category_q1=1`; [DOI](https://doi.org/10.1145/3828675) | Safety/type/effect và executable mitigation. Đây là paper về safe action synthesis, không phải baseline localization/retrieval; venue publication type cần giữ rõ khi lập “journal core”. |
| **P49**, [read-final:50](../261011-1345-aiops-q1-literature-gap/work/read-final.csv:50), [extraction:28](../261011-1345-aiops-q1-literature-gap/work/extraction.csv:28) | *Applied Artificial Intelligence*; SJR 0.792, Best Q1 nhưng `cs_category_q1=0`; [Taylor & Francis](https://doi.org/10.1080/08839514.2026.2684312) | Benchmark BM25/dense/hybrid/re-rank cho log-template và P95 latency; không đánh giá downstream LLM RCA, nên chỉ làm retrieval protocol reference. |
| **P50**, [read-final:51](../261011-1345-aiops-q1-literature-gap/work/read-final.csv:51), [extraction:29](../261011-1345-aiops-q1-literature-gap/work/extraction.csv:29) | *Results in Engineering*; Best Q1 nhưng `cs_category_q1=0`; [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2590123026041472) | Counter-evidence: dense/BM25 RAG không luôn thắng non-RAG trong metallurgical text RCA. Khác miền, text-only; issue date tháng 12/2026 cần ghi tách với online publication. |

**Phân biệt cần giữ:** các ID trên chứng minh corpus đã đọc và các thiết kế có thể tham khảo. Chúng không chứng minh nhóm đã chọn đúng ba bài, cũng không biến các baseline trong từng bài thành baseline bắt buộc của NT114.

# Hợp đồng baseline → improvement hiện có

`design/protocol-v2.md` đã cố định: một LLM và một call cho mỗi incident × condition × retrieval cell; retrieval arms `none`/`hybrid`; top-5 và censored MRR@5; B0 random, B1 max-z, B1m evidence-order, conditional B2 BARO-style, B3, L0/L1, C1/C2/C3 và oracle O; injection-level paired contrasts; cluster bootstrap, sign-flip và Holm; ngưỡng fit trên DEV rồi khóa trước test. Xem [protocol-v2](../261018-2300-single-llm-simplification-and-evaluation-hardening/design/protocol-v2.md:10).

Phần còn thiếu để gọi là contract của một bài báo:

1. Chọn **đúng ba bài nền** và ánh xạ từng bài vào baseline/setting nào; hiện P18/P31 là ứng viên mạnh, P42/P49/P50 phụ thuộc contribution.
2. Chọn một phương pháp đóng góp và comparator chính; hiện protocol chỉ nói đo lường, không tuyên bố method thắng.
3. Chốt confirmatory family, preregistration và `preregistration_sha`; thiếu SHA thì bảng bị ghi là exploratory ([plan](../261018-2300-single-llm-simplification-and-evaluation-hardening/plan.md:148)).
4. Chạy real-model grid và báo effect/CI/p-value. `SESOI = 0.05` hiện là design target, không phải improvement đã quan sát.

# Câu hỏi còn mở

- Nhóm và GVHD chọn bộ ba nào, và bài thứ ba phục vụ retrieval, calibration hay counter-evidence?
- “Q1” có cần bắt buộc `cs_category_q1=1` không?
- Baseline headline là non-LLM ranking, single-LLM no-retrieval, hay hybrid retrieval?
- Ai thực hiện independent review của DOI, category và extracted claims trước khi đóng preregistration?

Status: DONE_WITH_CONCERNS
Summary: Evidence confirms a reproducible Q1 corpus and a measurement protocol, but no final three-paper core or baseline-to-improvement contribution contract is specified.
Concerns/Blockers: The paper set, contribution, confirmatory family, preregistration, and observed improvement remain open; Best Quartile Q1 is not uniformly Computer Science Q1.
