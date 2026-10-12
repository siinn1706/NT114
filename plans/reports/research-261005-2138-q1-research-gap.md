# Research gap từ bài báo tạp chí Q1 cho đề tài NT114

Ngày: 2026-10-05. Người chọn hướng: nhóm và mentor. Báo cáo này chỉ đưa bằng chứng và các phương án.

**Mức chắc:** mọi nhận xét về từng bài ở đây dựa trên **abstract** lấy từ OpenAlex, chưa đọc toàn văn. Một gap chỉ được coi
là thật sau khi đã đọc toàn văn các bài trong nhóm đó (bước 5).

## 1. Tách tên đề tài thành cụm từ

Tên đề tài: *Phát triển hệ thống phát hiện sự cố và phân tích nguyên nhân gốc cho microservices trên Kubernetes sử dụng
truy xuất lai và mô hình ngôn ngữ lớn.*

| Mã | Cụm từ (tiếng Việt) | Cụm từ tìm kiếm (tiếng Anh) |
|---|---|---|
| K1 | Phát hiện sự cố | anomaly detection, failure detection, incident detection |
| K2 | Phân tích nguyên nhân gốc | root cause analysis, root cause localization, fault localization, failure diagnosis |
| K3 | Microservices (dữ liệu metric, log, trace) | microservice, multimodal / multi-source telemetry, distributed tracing |
| K4 | Kubernetes | Kubernetes, cloud-native, container |
| K5 | Truy xuất lai | hybrid retrieval, BM25 + dense retrieval, retrieval-augmented generation (RAG) |
| K6 | Mô hình ngôn ngữ lớn | large language model, LLM agent, AIOps, incident management |

## 2. Cách tìm và lọc

- **Truy vấn:** 22 truy vấn ghép các cụm trên (K1+K2, K2+K3, K2+K4, K2+K6, K6+AIOps, K5+K6, K1+K4, K2+lan truyền, K2+giải thích,
  K2+benchmark, …). Danh sách truy vấn nằm trong script `oa_search.py` ở scratchpad của phiên này.
- **Nguồn:** OpenAlex, chỉ lấy `type=article` đăng trên `journal`, từ 2020; mỗi truy vấn lấy 100 kết quả đầu theo độ liên quan.
- **Lọc Q1:** đối chiếu ISSN với bảng **SCImago SJR 2025** (tải trực tiếp từ scimagojr.com ngày 05/10/2026). Tiêu chí người dùng
  đã chọn: hạng tốt nhất (SJR Best Quartile) là Q1.
- **Loại MDPI** theo quy chuẩn NCKH (Sensors, Electronics, Applied Sciences, Future Internet, …), dù một số tạp chí MDPI có Q1.
- **Kết quả:** 888 bài (vòng 1) → 222 bài trên tạp chí Q1 (bỏ MDPI) → thêm 57 bài từ vòng 2 → **83 bài liên quan trực tiếp**
  sau khi đọc tiêu đề và abstract. Các bài lạc đề (IDS mạng, y tế, khai mỏ, …) bị loại.

**Hai lưu ý về tiêu chí "chỉ Q1":**
1. SJR 2025 xếp **IEEE Access** và **Scientific Reports** vào Q1 (hạng tốt nhất). Chúng nằm trong danh sách vì đạt tiêu chí,
   nhưng nhiều hội đồng không coi đây là nơi nộp mạnh. Cần mentor quyết có giữ hay không.
2. Các hội nghị đầu ngành (ICSE, FSE, ASE, KDD, WWW, EuroSys) và *Proc. ACM Softw. Eng.* **không có hạng Q trong SJR**,
   nên bị loại theo tiêu chí. Hệ quả là RCAEval (WWW'25 Companion), BARO (FSE'24), RCACopilot (EuroSys'24) — những công trình
   Proposal_v2 đang dựa vào — **không được trích làm cơ sở** nếu giữ đúng tiêu chí. Gần như toàn bộ 16 tài liệu khoa học
   trong Proposal_v2 là hội nghị hoặc arXiv. Đây là điểm phải sửa nếu nhắm Q1.

## 3. Gom bài theo bài toán

Mỗi bài có thể nằm ở nhiều bài toán. Năm, tạp chí và DOI lấy từ OpenAlex/Crossref.

### B1. Phát hiện bất thường trong microservice (K1+K3)
| Bài | Tạp chí, năm | Dữ liệu dùng | Ghi chú từ abstract |
|---|---|---|---|
| TraceGra | Computer Communications 2023, 10.1016/j.comcom.2023.03.028 | trace | GNN trên trace |
| ServiceAnomaly | JSS 2023, 10.1016/j.jss.2023.111917 | trace + profiling metric | |
| TraceDAE | TNSM 2025, 10.1109/tnsm.2025.3583213 | trace | autoencoder đôi GAT+LSTM |
| DALAD | TSC 2025, 10.1109/tsc.2025.3649198 | trace | bất thường toàn cục và cục bộ |
| TraceHG | TSC 2026, 10.1109/tsc.2026.3667576 | trace + log | hypergraph |
| TraceDiff | TDSC 2026, 10.1109/tdsc.2026.3712748 | trace | diffusion |
| TADBench | TSC 2025, 10.1109/tsc.2025.3622122 | trace | benchmark trace AD |
| MUAD | TSC 2026, 10.1109/tsc.2026.3672587 | metric+log+trace | **bất định trong và giữa modal**, active learning |
| MGFusion | TSC 2026, 10.1109/tsc.2026.3665382 | metric+log+trace | Grassmann manifold |
| ADmM | ACM TWEB 2026, 10.1145/3801729 | metric+log+trace | metric bị thiếu |
| Hybrid-graph AD | Information Fusion 2025, 10.1016/j.inffus.2025.103017 | đa modal | |
| Context-aware AD, dynamic KG | TNSM 2026, 10.1109/tnsm.2026.3652304 | tài nguyên + mạng | topology thay đổi theo thời gian |
| OTel empirical study | IEEE Access 2026, 10.1109/access.2026.3705430 | OTel trace+metric+log | F1 cao mà AUC gần ngẫu nhiên, cảnh báo về độ đo |
| Instance-level fault detection | Sci. Reports 2026, 10.1038/s41598-026-49746-y | trace + metric | |
| Monitoring data mapping study | TOSEM 2025, 10.1145/3744556 | tổng quan 104 bài | |

### B2. Định vị nguyên nhân gốc (K2+K3), không dùng LLM
| Bài | Tạp chí, năm | Hướng | Ghi chú từ abstract |
|---|---|---|---|
| ServiceRank | TDSC 2021, 10.1109/tdsc.2021.3083671 | đồ thị tác động | sự cố thật IBM Bluemix |
| CausalRCA | JSS 2023, 10.1016/j.jss.2023.111724 | nhân quả | định vị mức metric |
| TrinityRCL | TSE 2023, 10.1109/tse.2023.3241299 | đa nguồn | định vị nhiều mức, tới mức code |
| DiagFusion | TSC 2023, 10.1109/tsc.2023.3290018 | GNN đa modal | định vị + loại lỗi |
| DeepHunt | TOSEM 2024, 10.1145/3695999 | graph autoencoder | điểm root cause dùng quan hệ upstream–downstream, diễn giải được |
| MicroNet | TNSM 2024, 10.1109/tnsm.2024.3387552 | mức operation | nêu rõ "nhiễu do lan truyền bất thường" |
| Multilayered Transformer | TR 2024, 10.1109/tr.2024.3356717 | đa tầng | service, container, máy vật lý, mạng |
| RCA for cloud-native apps | TCC 2024, 10.1109/tcc.2024.3358823 | tương quan triệu chứng | tái dựng **quỹ đạo lỗi** từ gốc tới hệ quả |
| MTG_CD | J. Cloud Computing 2024, 10.1186/s13677-024-00666-0 | GCN | phân loại + chẩn đoán |
| UniDiag | TSC 2024, 10.1109/tsc.2024.3489444 | temporal KG | phát hiện + phân loại |
| TVDiag | TOSEM 2025, 10.1145/3734868 | đa modal theo tác vụ | định vị + loại lỗi |
| HG-PAD | TSC 2025, 10.1109/tsc.2025.3603218 | đồ thị dị thể | |
| CARE | TSE 2025, 10.1109/tse.2025.3645143 | spectrum + trace | TrainTicket 224 ca, top-1 72–89% |
| UDA-RCL | TSC 2025, 10.1109/tsc.2025.3646329 | domain adaptation | **chuyển giao từ hệ thống cũ sang hệ thống mới** |
| Enhanced BARO | IEEE Access 2025, 10.1109/access.2025.3602962 | thống kê | trên RCAEval, Avg@5 0.77 → 0.92 |
| MetricSifter | IEEE Access 2024, 10.1109/access.2024.3374334 | giảm đặc trưng | lọc metric trước định vị |
| CRFD | TOSEM 2026, 10.1145/3796706 | phản thực + SCM | nhân quả, diễn giải được |
| TCRCA | TSE 2026, 10.1109/tse.2026.3715410 | nhân quả theo topology | (OpenAlex không có abstract) |
| CHASE | TBD 2026, 10.1109/tbdata.2026.3725931 | causal hypergraph | (OpenAlex không có abstract) |
| Topo-MFP | JKSU-CIS 2026, 10.1007/s44443-026-01193-5 | lan truyền đa modal | nêu rõ khó **tách dịch vụ gốc khỏi dịch vụ bị ảnh hưởng phía sau** |
| GRAFlow | JAISCR 2026, 10.2478/jaiscr-2026-0017 | GAT đa tỉ lệ | phát hiện + định vị |
| MODIFy | JSS 2026, 10.1016/j.jss.2026.112844 | diffusion fusion | |
| Uncertainty-aware fusion | TDSC 2026, 10.1109/tdsc.2026.3732582 | fusion có bất định | (chưa có abstract) |
| FRL-MFPG | IST 2022, 10.1016/j.infsof.2022.107083 | propagation-aware | (chưa có abstract) |

### B3. LLM cho RCA và AIOps (K2+K6)
| Bài | Tạp chí, năm | Bối cảnh | Ghi chú từ abstract |
|---|---|---|---|
| LocaleXpert | TSC 2026, 10.1109/tsc.2026.3676262 | microservice | metric/log/trace → mô tả ngôn ngữ tự nhiên; agent chuyên gia cho từng modal; giải thích; chạy trên AIOpsLab |
| MA-RCA | Complex & Intelligent Systems 2025, 10.1007/s40747-025-02096-0 | cloud-native + đo điện | đa agent để giảm ảo giác |
| LLM + Bayesian network | IEEE Access 2025, 10.1109/access.2025.3565220 | **Kubernetes + Istio, Chaos Mesh** | chủ yếu dựa trên log |
| NeuSymRCA | Results in Engineering 2026, 10.1016/j.rineng.2026.110491 | hệ lưu trữ phân tán | LLM + biểu tượng; **định lượng độ tin cậy dự đoán** |
| Telecom LLM RCA | IEEE Wireless Comm. 2026, 10.1109/mwc.2026.3734923 | mạng viễn thông | suy luận có cấu trúc bám bằng chứng |
| LEMON | TSC 2026, 10.1109/tsc.2026.3679374 | orchestration microservice | SLM fine-tune phân loại ý định |
| PromCopilot | TOSEM 2026, 10.1145/3797910 | cloud-native | text-to-PromQL bằng LLM + KG |
| Survey LLM4AIOps | ACM CSUR 2025, 10.1145/3746635 | tổng quan 183 bài | |
| Agentic NetOps/AIOps | Computer Science Review 2026, 10.1016/j.cosrev.2026.101075 | tổng quan | nêu khoảng cách năng lực–bảo đảm |
| Agent System Operations | TSE 2026, 10.1109/tse.2026.3732207 | tổng quan | |

### B4. LLM cho phát hiện bất thường log (K1+K6)
CoLA (PVLDB 2025, mô hình nhỏ lọc + LLM xác minh), FlexLog (TOSEM 2025, ML + LLM + **RAG**, log không ổn định), LLM-LADE (KBS 2025,
có giải thích), LogRAIL (IEEE Access 2026, LLM **có truy hồi** chỉ xét lại các cửa sổ gần ngưỡng), Semantics over statistics
(ESWA 2026), LogPhi (Neurocomputing 2026), FRLog (JAISCR 2026), LogFiT (TNSM 2024).

### B5. Truy xuất lai và RAG (K5)
| Bài | Tạp chí, năm | Ghi chú từ abstract |
|---|---|---|
| Log-template retrieval for GenAI RCA | Applied AI 2026, 10.1080/08839514.2026.2684312 | **so BM25, dense, hybrid RRF, rerank** làm bằng chứng RCA trên Loghub (BGL, HDFS, Thunderbird); dense mạnh nhất; đo cả độ trễ đuôi. Chỉ đo truy hồi, chưa đo ảnh hưởng tới kết quả RCA |
| Faithfulness hallucinations in RAG | Machine Learning 2026, 10.1007/s10994-026-07121-y | LLM open-weight 2–8B, so sparse/dense/hybrid và fusion theo điểm/theo hạng; tách lỗi truy hồi khỏi lỗi sinh |
| NCERT-RAG-Eval | Sci. Reports 2026, 10.1038/s41598-026-71757-y | hybrid RRF tốt nhất (miền giáo dục) |
| LLM-augmented KB for RCA | IEEE Access 2026, 10.1109/access.2026.3658655 | dựng kho tri thức từ ticket hỗ trợ cho RCA mạng |
| Surveys RAG | ACM CSUR 2026 (×2), AI Review 2026, ACM TOIS 2023 (dense retrieval) | |

### B6. Kubernetes / cloud-native (K4)
Ngoài bài LLM + BN (IEEE Access 2025) và RCA for cloud-native (TCC 2024), các bài K4 tìm được chủ yếu về autoscaling,
bảo mật, triển khai; không phải RCA.

### Tổng quan (survey) dùng để định hình
ACM CSUR 2022 (AD + RCA microservice, 253 trích dẫn), ACM CSUR 2025 (root cause localization microservice), Cluster Computing
2026 (117 bài, nêu hạn chế về khả năng mở rộng, **khả năng giải thích**, thời gian thực), ACM TIST 2021 (AIOps failure management).

## 4. Research gap ứng viên (từ abstract, cần xác minh bằng toàn văn)

Mỗi gap ghi rõ bằng chứng hiện có và bài phải đọc toàn văn để xác nhận hoặc bác bỏ.

| # | Gap ứng viên | Bằng chứng hiện có | Bài phải đọc toàn văn để kiểm |
|---|---|---|---|
| G1 | **RCA microservice bằng LLM trên tạp chí Q1 còn rất ít.** Tìm thấy 3 bài đúng bối cảnh: LocaleXpert, MA-RCA, LLM+BN. Chưa thấy bài nào so trên **nhiều hệ thống công khai** với độ đo AC@k/MRR | 22 truy vấn chỉ ra 3 bài; LocaleXpert chạy trên AIOpsLab | LocaleXpert, MA-RCA, LLM+BN |
| G2 | **Truy xuất lai chưa được đo theo ảnh hưởng tới kết quả RCA microservice.** Bài Q1 duy nhất so BM25/dense/RRF cho RCA chỉ đo chất lượng truy hồi trên log Loghub, không đo định vị dịch vụ gốc | Applied AI 2026; FlexLog và LogRAIL dùng RAG cho **phát hiện** log, không cho định vị | Log-template retrieval (AAI 2026), FlexLog, LogRAIL |
| G3 | **Độ tin cậy của kết quả RCA dạng LLM chưa được định lượng ở microservice.** Bất định mới có ở phát hiện bất thường (MUAD) và fusion (TDSC 2026); NeuSymRCA có định lượng độ tin cậy nhưng ở hệ lưu trữ | MUAD, TDSC 2026, NeuSymRCA | 3 bài này + LocaleXpert, MA-RCA |
| G4 | **Chi phí/ngân sách ngữ cảnh khi đưa telemetry vào LLM chưa được nghiên cứu riêng.** LocaleXpert chuyển telemetry thành văn bản nhưng abstract không nói về chi phí token; LEMON có đánh đổi cỡ mô hình–độ trễ nhưng cho phân loại ý định | LocaleXpert, LEMON, MetricSifter (giảm metric, không dùng LLM) | LocaleXpert, LEMON |
| G5 | **Tách nơi phát sinh khỏi nơi biểu hiện (lan truyền)** đã được nhiều bài không dùng LLM giải (DeepHunt, MicroNet, Topo-MFP, CARE, TCC 2024, FRL-MFPG). Ở nhóm LLM chưa thấy bài Q1 nào làm rõ điều này | nhiều bài B2 nêu trực tiếp; B3 không nêu | Topo-MFP, DeepHunt, TCC 2024, LocaleXpert |
| G6 | **Chuyển giao giữa các hệ thống (ứng dụng khác nhau)** chỉ có UDA-RCL (không dùng LLM). Chưa thấy bài LLM-RCA Q1 nào đánh giá chéo 2–3 ứng dụng (đúng yêu cầu note 29/09) | UDA-RCL | UDA-RCL, LocaleXpert |
| G7 | **Giải thích được tuyên bố nhưng ít được đo.** DeepHunt, CRFD, MTG_CD, LocaleXpert, LLM-LADE đều nói "interpretable"; abstract không cho thấy có độ đo định lượng cho chất lượng giải thích | abstract các bài trên | CRFD, LocaleXpert, LLM-LADE |
| G8 | **Thiếu đánh giá trên Kubernetes thật với tiêm lỗi.** Chỉ LLM+BN (IEEE Access) dựng K8s + Istio + Chaos Mesh, và chủ yếu dựa trên log | LLM+BN | LLM+BN |

**Gap đã bị lấp, không nên chọn:** phát hiện bất thường đa modal không dùng LLM (B1 rất dày, nhiều bài TSC/TDSC 2025–2026)
và định vị theo đồ thị/nhân quả không dùng LLM (B2 dày).

## 5. Bước tiếp theo để chốt gap (trước khi chọn hướng)

1. Đọc toàn văn **khoảng 12 bài then chốt:** LocaleXpert, MA-RCA, LLM+BN, NeuSymRCA, MUAD, TDSC 2026 uncertainty fusion,
   UDA-RCL, Topo-MFP, DeepHunt, CRFD, Log-template retrieval (AAI 2026), FlexLog. Với mỗi bài điền đủ các cột: bài toán,
   dữ liệu/benchmark, có LLM không (cỡ, open-weight hay API), có truy hồi không, có độ tin cậy không, có giải thích được đo
   không, số hệ thống đánh giá, chi phí. Mỗi ô kèm câu trích.
2. Cập nhật bảng gap: gap nào còn đứng sau khi đọc toàn văn thì giữ, gap nào bị bác thì ghi lý do.
3. Bạn và mentor chọn hướng từ các gap còn đứng.

## 6. Các hướng có thể chọn (để bạn quyết, chưa xếp hạng)

| Hướng | Ghép gap | Phần Proposal_v2 dùng lại được | Cần thêm |
|---|---|---|---|
| H-a | G1 + G2: LLM-RCA microservice có truy xuất lai, đo ảnh hưởng của từng cách truy hồi tới AC@k trên nhiều hệ thống | gần như toàn bộ (5.3, 5.4, 6.3, 6.4) | thêm 2 hệ thống |
| H-b | G1 + G3: LLM-RCA kèm độ tin cậy định lượng, cho phép từ chối khi không chắc | 5.3, 5.5, 6.3 | phần hiệu chỉnh độ tin cậy |
| H-c | G1 + G4: nén telemetry dưới ngân sách token cho LLM nhỏ, đường cost–accuracy | 5.3 (incident card) | đo chi phí có hệ thống |
| H-d | G1 + G5: LLM-RCA có xét lan truyền, tách nơi phát sinh khỏi nơi biểu hiện | 5.3 (đồ thị gọi) | cơ chế kiểm theo cạnh |
| H-e | G6 + G1: LLM-RCA đánh giá chéo 3 ứng dụng, đo khả năng chuyển giao | 6.1 | thêm 2 hệ thống |
| H-f | G7: khung đo chất lượng giải thích cho RCA | 6.5 | nhãn giải thích, người chấm |

Các hướng ghép được với nhau. Proposal_v2 hiện chạm nhẹ vào G1, G2, G4, G7 nhưng chưa có hướng nào là điểm mới chính.

## Câu hỏi còn mở

1. Có giữ IEEE Access và Scientific Reports trong danh sách Q1 không?
2. Bộ dữ liệu RCAEval (hội nghị, không Q1) vẫn được dùng làm **dữ liệu** chứ? Tiêu chí "chỉ Q1" áp cho tài liệu được trích làm
   căn cứ khoa học, hay áp cả cho nguồn dữ liệu và công cụ?
3. Có cho mở rộng tìm sang hội nghị hạng A* (CORE) không? Nhiều bài LLM-RCA mạnh nhất hiện ở ICSE/FSE/ASE và sẽ được reviewer
   Q1 hỏi tới nếu bài không nhắc.
