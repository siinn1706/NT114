# Research: phương pháp phân tích cơ chế mất bằng chứng (evidence-loss attribution) cho RCLAgent thiếu telemetry

Ngày: 2026-10-31. Phạm vi: RQ (b) của kế hoạch, chỉ CPU. Mức xác minh ghi từng mục: [V] đã đọc nội dung qua WebFetch, [S] chỉ thấy abstract/kết quả tìm kiếm, [?] chưa xác minh được. Mọi con số lấy từ nguồn ghi bên cạnh; chưa đối chiếu bản PDF đầy đủ nếu ghi [S].

## 1. Failure attribution trong LLM multi-agent system

| Công trình | Năm/nơi | Điều dùng được | Mức |
|---|---|---|---|
| Zhang et al., "Which Agent Causes Task Failures and When?" (Who&When) https://arxiv.org/abs/2505.00212 ; PMLR 267:76583 https://proceedings.mlr.press/v267/zhang25cq.html | ICML 2025 | Định nghĩa decisive error theo phản thực: lỗi của agent i tại bước t là "decisive" nếu sửa nó (và điều chỉnh các bước sau) đổi kết quả từ fail sang success; nhiều lỗi decisive thì lấy lỗi sớm nhất. 127 hệ thống. 3 người gán nhãn 3 vòng (độc lập, thảo luận ca không chắc, chéo kiểm); KHÔNG báo kappa, chỉ báo giờ công và tỷ lệ "uncertain" 15-30%. Ba phương pháp: all-at-once (agent tốt nhất, step kém), step-by-step (step tốt nhất, agent kém), binary search (trung gian). Tốt nhất 53,5% agent, 14,2% step. | [V] qua bản HTML v3 (tóm tắt của WebFetch) |
| Cemri et al., "Why Do Multi-Agent LLM Systems Fail?" (MAST) https://arxiv.org/abs/2503.13657 | NeurIPS 2025 (Datasets&Benchmarks, theo listing) | 14 failure mode, 3 nhóm (specification, inter-agent misalignment, task verification). Xây bằng grounded theory (150 trace, 6 annotator, bão hòa), rồi 3 chuyên gia gán độc lập 5 trace/vòng x 3 vòng, sửa định nghĩa sau mỗi vòng, kappa cuối 0,88; kiểm ngoài miền 0,79. LLM-annotator (o1 + few-shot) đạt kappa 0,77 so với người. Số trace 1000+ / 1600+ / 1642 khác nhau giữa các bản. | [V] một phần (đọc 100k/160k ký tự) |
| Zhu et al., AgentErrorTaxonomy / AgentErrorBench / AgentDebug https://arxiv.org/abs/2509.25370 | arXiv 2025-09; listing ICML 2026 | Phân loại lỗi theo module (memory, reflection, planning, action, system); tập trung "cascading failure" từ một lỗi gốc; quy trình 3 bước: phân tích mịn, phát hiện lỗi tới hạn, sửa lặp. | [S] |
| Deshpande et al., TRAIL https://arxiv.org/abs/2505.08638 | arXiv 2025 | 148 trace, 841 lỗi, 3 nhóm reasoning/execution/planning; định vị bước + phân loại lỗi; LLM tốt nhất ~11%. | [S] |
| Zhang et al., AgenTracer https://arxiv.org/abs/2509.03312 | ICLR 2026 | Gán nhãn decisive step bằng counterfactual replay (thay hành động bằng hướng dẫn oracle) và fault injection có lập trình; TracerTraj. | [S] chi tiết quy trình chưa đọc |
| Causal Agent Replay https://arxiv.org/abs/2606.08275 | arXiv 2026-06 | Mô hình SCM, do-operation tại một bước, chạy lại phía sau; xấp xỉ Shapley. Chỉ kiểm trên dữ liệu tổng hợp. | [S], độ tin cậy thấp |
| OpenRCA 2.0 (Fang et al.) https://arxiv.org/abs/2606.27154 | arXiv 2026-06 | Nhãn quy trình theo bước dựng từ can thiệp fault-injection; khái niệm "ungrounded diagnosis" (đúng service nhưng không nối được đường lan truyền). Gần RQ nhất nhưng chưa đọc bản gốc. | [S] qua listing thứ cấp, arXiv ID chưa fetch trực tiếp |

Nhận định áp dụng:
- Reviewer sẽ hỏi "first error / decisive step" định nghĩa thế nào. Đề xuất mượn tinh thần Who&When nhưng đổi sang **first-loss stage** vì pipeline này là chuỗi tuyến tính cố định (tool -> self-state -> consolidation -> synthesis), không phải hội thoại nhiều agent: với mỗi cặp (case, seed) bị mất bằng chứng, nhãn là giai đoạn SỚM NHẤT tại đó bằng chứng-metric (có ở ground truth hoặc ở điều kiện `metric`) không còn hiện diện/không được dùng. Nêu rõ đây là định nghĩa tiến-tới-đầu-ra theo dữ liệu, không phải decisive-step phản thực; chỉ gọi "decisive" cho phần có replay.
- Bài học từ Who&When/TRAIL: (i) LLM-judge gán bước rất kém (<15%), vì vậy KHÔNG dùng LLM làm nhãn chính; dùng luật tất định trên log. (ii) Who&When không báo kappa và bị chỉ trích gián tiếp vì thiếu độ tin cậy: ta nên báo kappa/đồng thuận, tốt hơn họ.
- MAST cho khuôn quy trình codebook: vòng calibrate nhỏ độc lập, sửa định nghĩa, rồi mới gán chính thức; báo kappa theo vòng.

## 2. Information-flow / evidence-propagation và can thiệp phản thực

Nguồn tìm được (chất lượng hỗn hợp, đa số [S]):
- Barrak, "Traceability and Accountability in Role-Specialized Multi-Agent LLM Pipelines" https://arxiv.org/abs/2510.07614 (2025): định nghĩa "repair" và "harm" giữa các stage tuần tự. Dùng được làm từ vựng: stage nào *bảo toàn / làm mất / bịa thêm* bằng chứng. [S]
- "From Spark to Fire" https://arxiv.org/abs/2603.04474 (2026) và AgentAsk https://arxiv.org/abs/2510.07593 (2025): lỗi lan truyền qua từng handoff giữa agent; ghi nhận handoff là điểm mất. [S]
- Liu et al., "Lost in the Middle" (TACL 2024): suy giảm khi dùng thông tin ở giữa ngữ cảnh dài, liên quan tới bước synthesis đọc toàn bộ GEG. Chưa xác minh trong phiên này [?]; cần kiểm tra citation trước khi đưa vào bài.
- Blog thực hành (Redis 2026, tianpan.co 2026) nói tóm tắt làm rơi dead-ends và chuẩn hóa chuỗi chính xác: KHÔNG dùng làm trích dẫn học thuật.
- Chưa tìm thấy công trình đo trực tiếp "mất bằng chứng qua chuỗi tóm tắt đệ quy" cho RCA; đây là khoảng trống có thể nêu như đóng góp, nhưng phải ghi là "không tìm thấy", không khẳng định "chưa ai làm".

Khả thi CPU-only từ log vs cần suy luận lại:

| Phép phân tích | Cần gì | CPU/log? |
|---|---|---|
| Đối soát từng lượt: tool_result có rỗng không (đã có `tool_result_budget`, kích thước, sha) | events.jsonl | Có |
| Self-state có phản ánh đúng tool_result (is_abnormal / has_metric_anomaly / has_error_logs) so với bằng chứng thật trong response | Luật tất định + so khớp chuỗi/số | Có |
| Consolidation có giữ/bỏ span bất thường (đối chiếu agent_complete của span con với đầu ra consolidate cha) | Duyệt cây span | Có |
| Synthesis: xếp hạng cuối so với (a) hint, (b) GEG, (c) ground truth | Final prompt + output | Có (check-hash-seed-order.py đã dựng lại hint) |
| Replay luật tất định: tính lại `evidence_hint` (khớp chuỗi con trên self-evidence, coordinator.py 469-483) với self-state bị sửa theo oracle | Chạy lại đúng đoạn mã tác giả với input sửa | Có, không cần LLM; chỉ phản ánh phần mã, không phản ánh phản ứng LLM |
| Replay stage LLM với input oracle (ví dụ thay tool_result rỗng bằng dữ liệu thật; ép self-state đúng) | Suy luận lại Qwen3-4B trên vLLM | KHÔNG (cần GPU; ngoài phạm vi). Ghi là phần còn lại cho RQ (c) |
| So sánh cặp `metric` vs `no_metric` cùng case và seed theo cùng span_id | Hai bộ events | Có; là "can thiệp tự nhiên" (ablation nguồn) cho phép gán sai khác tới stage, nhưng chú ý LLM không tất định hoàn toàn (xem S1 v3, hash seed) |

Khuyến nghị: khẳng định nhân quả chỉ ở mức "trace-consistent" (không phải can thiệp) cho các nhãn từ log; chỉ dùng chữ "gây ra" cho phép replay mã tất định hoặc cặp ablation, và nêu giới hạn.

## 3. LLM-based RCA microservice với modality thiếu

- RCAEval, Pham et al., WWW 2025 companion, https://arxiv.org/abs/2412.17015 : 735 ca, 3 hệ thống, RE1 (chỉ metrics) / RE2 (metrics+logs+traces) / RE3 (code-level). Là nguồn dữ liệu của ta; chứa dữ liệu thiếu nguồn "theo cấu trúc" (RE1) nhưng không phải nghiên cứu cơ chế thiếu modality. [S]
- ARMOR, Qian et al., https://arxiv.org/abs/2603.25538 (arXiv 2026-03; trang PDF ghi ASE '26 nhưng DOI placeholder, venue chưa xác nhận): RCA tự giám sát với mặt nạ quan sát, encoder theo modality, fusion có cổng. Không phải LLM; không đọc được thân bài nên không biết nó báo cơ chế gì. [S, venue ?]
- TORAI https://arxiv.org/abs/2604.13522 ; DynaCausal https://arxiv.org/abs/2510.22613 (nhấn mạnh mỗi modality có điểm mù; service lệch mạnh nhất có thể bị xếp trước nguyên nhân thật = misattribution); CHASE https://arxiv.org/abs/2406.19711 ; Eadro https://arxiv.org/abs/2302.05092 . [S]
- OpenRCA, Xu et al., ICLR 2025 https://openreview.net/forum?id=M4qNIzQYpd (đường dẫn proceedings: https://proceedings.iclr.cc/paper_files/paper/2025/file/d29b8d53678015079e1d245c023e49d2-Paper-Conference.pdf ): 335 lỗi, >68 GB telemetry, yêu cầu agent tự xử lý dữ liệu; số liệu chính xác thấp (Claude 3.5 với RCA-agent 11,34% theo kết quả tìm kiếm). [S]
- MicroRCA-Agent https://arxiv.org/abs/2509.15635 (2025): ablation theo modality cho thấy metrics đơn lẻ mạnh nhất (42,78), logs đơn lẻ yếu nhất (23,59); tổ hợp logs+metrics (51,27) hơi cao hơn đủ ba (50,71). Đây là kết quả ablation gần nhất với (a) và khớp hướng phát hiện của ta (bỏ logs ít hại). Chỉ báo mức hiệu năng, không phân tích cơ chế. [S]
- mABC https://arxiv.org/abs/2404.12135 : ablation thành phần kiến trúc, không phải modality. [S]
- Không tìm thấy bài ablation modality của chính RCLAgent hay RCAgent trong phiên tìm kiếm này [?]; cần đọc paper RCLAgent gốc trực tiếp.

Kết luận mục này: các công trình chủ yếu báo "hiệu năng giảm bao nhiêu khi thiếu modality", rất ít bóc cơ chế theo từng stage của pipeline LLM. Điều này làm RQ (b) có giá trị, nhưng cũng nghĩa là ta không có phương pháp chuẩn để so sánh: phải tự định nghĩa và công khai.

## 4. Độ chặt chẽ cho nghiên cứu mô tả cỡ mẫu nhỏ

Tài liệu:
- Kerr, "HARKing: Hypothesizing After the Results are Known", Personality and Social Psychology Review 1998 (gốc thuật ngữ) [S, qua nguồn thứ cấp]. Nosek et al., "The preregistration revolution", PNAS 115(11):2600-2606, 2018 [S, chỉ citation]. Haven & Van Grootel, "Preregistering qualitative research", Accountability in Research 2019 [S, chỉ citation].
- González-Prieto et al., "Reliability in software engineering qualitative research through inter-coder agreement", J. Systems and Software 2023, https://arxiv.org/abs/2008.00977 : hướng dẫn Krippendorff alpha; ngưỡng quy ước 0,80 tin cậy, 0,667 cho kết luận tạm. [S]
- Byrt, Bishop & Carlin 1993 (PABAK); Sim & Wright 2005; McHugh 2012 [? chưa mở được; cần xác minh trước khi trích]. Từ tài liệu phần mềm thống kê: CI Wald của kappa kém với mẫu nhỏ, nên dùng percentile bootstrap; báo kèm tỷ lệ đồng thuận thô và PABAK khi biên mất cân bằng.

Khuyến nghị quy trình:
1. Đăng ký trước (commit) codebook + luật nhãn + định nghĩa first-loss-stage + danh sách kết quả mong đợi/không mong đợi TRƯỚC khi chạy nhãn lên toàn bộ dữ liệu; ghi hash commit. Phân biệt "xác nhận" (đã định trước) với "khám phá" (sinh ra sau khi xem); mọi sửa đổi sau đó vào bảng deviation log có lý do.
2. Hai lớp: (A) luật tất định chạy bằng mã trên events.jsonl (tái lập 100%); (B) kiểm toán thủ công mẫu có phân tầng (mọi ca bất đồng giữa luật và người + mẫu ngẫu nhiên có seed). Đo: đồng thuận luật vs người, và người-1 vs người-2 (hai coder độc lập; nếu chỉ có chủ đề tài + một coder thứ hai là LLM thì ghi rõ LLM-coder, kappa LLM-người của MAST là 0,77 làm tham chiếu).
3. Chỉ số: Cohen kappa (2 coder, nhãn rời rạc) kèm CI bootstrap, tỷ lệ đồng thuận thô, PABAK nếu một nhãn chiếm đa số (rất có thể: "tool rỗng" áp đảo). Dùng Krippendorff alpha nếu >2 coder hoặc dữ liệu thiếu. Không đặt ngưỡng cứng; báo cả khi thấp và sửa codebook theo vòng (kiểu MAST), vòng calibrate dùng một case riêng và loại khỏi phần báo cáo chính.
4. Đơn vị phân tích: case (n=8), seed lồng trong case, span lồng trong run. Báo cáo ở mức case (nhiều/ít seed cùng cơ chế) và đếm cụm, không xem 36 run hoặc hàng nghìn span là mẫu độc lập; không p-value suy diễn. Báo khoảng/range, từng case, bảng đếm, bản "mỗi case một dòng".
5. Chặn HARKing: tách bảng "dự đoán trước" (ví dụ: tool rỗng gần như hoàn toàn cho metric trong no_metric; stage mất chính là chỗ dựng hint) khỏi phát hiện phụ. Giữ nguyên tác động âm (kết quả trái dự đoán).
6. Nhất quán với D12: không chạm test split; không dùng dữ liệu S1 v3 để chỉnh luật nhãn nếu đã khóa codebook; v3 dùng như tập xác nhận lại (replicate).

## Tóm tắt khuyến nghị (15 dòng cho kế hoạch)

1. Định nghĩa đầu ra: first-loss-stage trên chuỗi tool -> self-state -> consolidate -> synthesis, theo tinh thần "earliest decisive error" của Who&When (https://arxiv.org/abs/2505.00212), nhưng gọi đúng tên và nêu không phải phản thực.
2. Nhãn chính bằng luật tất định chạy trên events.jsonl (tái lập được); không dùng LLM-judge làm nhãn, vì họ này đạt <15% ở mức step (Who&When, TRAIL).
3. Ledger theo span: một dòng mỗi (run, span) với cờ tool_empty, self_state_flags, đã-consolidate-giữ/bỏ, hiện diện trong final prompt, xếp hạng cuối; giữ bảng này làm nguồn duy nhất cho mọi con số.
4. Chuẩn hóa từ vựng stage: preserved / dropped / mislabeled (gồm lỗi hint "latency-only gắn nhãn metric") / hallucinated, mượn ý repair/harm (Barrak 2025, [S]).
5. Phần CPU-only có thể khẳng định nhân quả: replay mã tác giả (evidence_hint 469-483, consolidation tổng hợp theo cây) với self-state sửa oracle; ghi giới hạn rằng LLM không được chạy lại.
6. Cặp metric vs no_metric theo case và seed là "can thiệp tự nhiên": căn theo span_id và so sánh stage; chú ý không tất định (hash seed, S1 v3).
7. Replay stage LLM với input oracle cần GPU: ghi là việc của RQ (c), đừng làm trong kế hoạch này.
8. Đăng ký trước (commit hash) codebook, định nghĩa, dự đoán xác nhận vs khám phá; deviation log công khai (Kerr 1998; Nosek 2018, [S]).
9. Quy trình codebook kiểu MAST: vòng calibrate độc lập trên một case riêng, sửa định nghĩa, rồi khóa; báo kappa theo vòng (https://arxiv.org/abs/2503.13657).
10. Kiểm toán thủ công: mọi bất đồng luật-người cộng mẫu ngẫu nhiên có seed; hai coder độc lập; nếu coder 2 là LLM thì ghi rõ (tham chiếu kappa 0,77 của MAST).
11. Báo Cohen kappa + bootstrap CI + đồng thuận thô + PABAK (nhãn mất cân bằng chắc chắn xảy ra); không ngưỡng cứng, ngưỡng 0,667/0,80 chỉ tham khảo (González-Prieto 2023).
12. Đơn vị phân tích là case (n=8) với seed/span lồng nhau; báo từng case và số cụm cùng cơ chế, không p-value suy diễn.
13. Dùng S1 v2 làm corpus chính, round 2 làm replicate, S1 v3 làm xác nhận sau khóa luật; không đụng test split (D12).
14. Định vị với tài liệu RCA: chỉ có ablation hiệu năng (MicroRCA-Agent 2509.15635 cho thấy logs yếu, metrics mạnh) và robust-modality không-LLM (ARMOR 2603.25538); ghi "không tìm thấy" phân tích cơ chế theo stage, không khẳng định "chưa ai làm".
15. Cần xác minh trước khi trích: venue của ARMOR, nội dung Liu 2024 (Lost in the Middle), McHugh 2012/Byrt 1993/Sim-Wright 2005, OpenRCA 2.0 (2606.27154), AgenTracer chi tiết quy trình.

## Câu hỏi chưa giải quyết

- Có chủ đề tài hay người thứ hai làm coder độc lập, hay dùng LLM-coder? Quyết định cách báo kappa.
- Có muốn gọi nhãn cuối là "first-loss stage" (đề xuất) thay vì "decisive step"?
- Cần đọc paper RCLAgent gốc để xem ablation modality của tác giả (không tìm thấy qua search).
