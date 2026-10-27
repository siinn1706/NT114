# Yêu cầu tải tay toàn văn (phase 06)

Theo protocol §7, phase 06 phải yêu cầu chủ dự án tải tay mọi bài trong top-30 (thứ tự §6) chưa có bản open access. Hiện T1 có 34/100 bài có toàn văn, đạt ngưỡng 30, nên phase 07 vẫn chạy trên các bài đã có. Các bài dưới đây giữ trạng thái `waiting-human`. Bài nào sếp tải được sẽ được chấm F, miễn là việc chấm diễn ra trước khi chốt T2.

Cách nộp: lưu PDF vào `private/fulltext/261024/<openalex_id>.pdf` (thư mục gốc repo, đã gitignore). Ghi rõ bản tạp chí hay bản accepted. Tôi sẽ hash file, trích text và cập nhật `work/access-ledger-final.csv`.

| Hạng R | openalex_id | DOI | Tạp chí | Tiêu đề | Lý do tự động thất bại |
|---|---|---|---|---|---|
| 2 | W7170083585 | [10.1109/tccn.2026.3715900](https://doi.org/10.1109/tccn.2026.3715900) | IEEE Transactions on Cognitive Communications and Networking | Hyperbolic Spatio-Temporal Graph Learning With Agent Reasoning for Root Cause Localization in Cloud-Edge Microservices | no open-access location found |
| 3 | W7139938267 | [10.1109/tsc.2026.3676262](https://doi.org/10.1109/tsc.2026.3676262) | IEEE Transactions on Services Computing | LLM-Enhanced Failure Localization in Microservices: Integrating Multi-Modal Data and Expert Interpretation | no open-access location found |
| 6 | W7204603481 | [10.1145/3842744](https://doi.org/10.1145/3842744) | ACM Transactions on Software Engineering and Methodology | ChatRCA: A Root Cause Analysis Method via LLMs-based Multi-Agent with Human-in-the-Loop | no open-access location found |
| 8 | W7151880451 | [10.1016/j.jss.2026.112890](https://doi.org/10.1016/j.jss.2026.112890) | Journal of Systems and Software | LMAT: An adaptive tracing approach based on efficient system behavior analysis using language models | no open-access location found |
| 9 | W4405778637 | [10.1109/tsc.2024.3521675](https://doi.org/10.1109/tsc.2024.3521675) | IEEE Transactions on Services Computing | Towards Close-to-Zero Runtime Collection Overhead: Raft-Based Anomaly Diagnosis on System Faults for Distributed Storage System | no open-access location found |
| 10 | W4313591680 | [10.1109/tdsc.2022.3233915](https://doi.org/10.1109/tdsc.2022.3233915) | IEEE Transactions on Dependable and Secure Computing | DyCause: Crowdsourcing to Diagnose Microservice Kernel Failure | no open-access location found |
| 15 | W7117292294 | [10.1109/jiot.2025.3648858](https://doi.org/10.1109/jiot.2025.3648858) | IEEE Internet of Things Journal | ARM: Autonomous Remediation and Management With LLM Agents for Intent-Driven Control | openalex HTTP 0;publisher-oa:ieee-stamp HTTP 202 |
| 18 | W7171925589 | [10.1109/tetc.2026.3713344](https://doi.org/10.1109/tetc.2026.3713344) | IEEE Transactions on Emerging Topics in Computing | CARAF: Root Cause Analysis Through Granger Causal Graphs With Ambiguous Residual Factors in Microservice Systems | no open-access location found |
| 19 | W7168376871 | [10.1109/tsc.2026.3713967](https://doi.org/10.1109/tsc.2026.3713967) | IEEE Transactions on Services Computing | MicroInspect: A Progressive Framework for Metric-Level Root Cause Localization in Microservices | no open-access location found |
| 20 | W4417439110 | [10.1109/tse.2025.3645143](https://doi.org/10.1109/tse.2025.3645143) | IEEE Transactions on Software Engineering | CARE: Context Aware Root Cause Identification Using Distributed Traces and Profiling Metrics | no open-access location found |
| 21 | W4387546413 | [10.1109/jiot.2023.3323620](https://doi.org/10.1109/jiot.2023.3323620) | IEEE Internet of Things Journal | Fast Anomaly Detection for IoT Services Based on Multisource Log Fusion | no open-access location found |
| 22 | W4412837182 | [10.1109/tsc.2025.3594870](https://doi.org/10.1109/tsc.2025.3594870) | IEEE Transactions on Services Computing | E-Log: Fine-Grained Elastic Log-Based Anomaly Detection and Diagnosis for Databases | no open-access location found |
| 23 | W7203626983 | [10.1145/3828675](https://doi.org/10.1145/3828675) | Proceedings of the ACM on Programming Languages | RunbookFX: Type- and Effect-Safe LLM Synthesis for Executable Incident Diagnosis and Mitigation | no open-access location found;publisher-oa:acm HTTP 403 |
| 24 | W7168139741 | [10.1109/tdsc.2026.3712748](https://doi.org/10.1109/tdsc.2026.3712748) | IEEE Transactions on Dependable and Secure Computing | TraceDiff: Anomaly Detection on Microservice Traces Through Frequency-Aware Conditional Diffusion Model | no open-access location found |
| 28 | W7222783047 | [10.1186/s13677-026-01009-x](https://doi.org/10.1186/s13677-026-01009-x) | Journal of Cloud Computing Advances Systems and Applications | DeCoR: decoupled multiplex causal ranking for microservice root cause analysis | no open-access location found;publisher-oa:springer HTTP 200 non-PDF |
| 29 | W4414399681 | [10.1016/j.jss.2025.112626](https://doi.org/10.1016/j.jss.2025.112626) | Journal of Systems and Software | Multivariate anomaly detection and root cause analysis of energy issues in microservice-based systems | no open-access location found |
| 30 | W4413754729 | [10.1109/tsc.2025.3603218](https://doi.org/10.1109/tsc.2025.3603218) | IEEE Transactions on Services Computing | HG-PAD: Heterogeneous Graph Structure Learning Aided Performance Anomaly Diagnosis in Microservice Systems | no open-access location found |

Tỉ lệ toàn văn theo tầng R: hạng 1–30 là 13/30, hạng 31–60 là 6/30, hạng 61–100 là 15/40.

Ngoài top-30 còn 49 bài `no-access`. Chúng không bắt buộc tải tay vì đã đạt ngưỡng 30 bài. Danh sách đầy đủ nằm trong `work/access-ledger-final.csv`.
