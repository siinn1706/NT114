# Review định hướng nghiên cứu và nền tảng bài báo NT114

Ngày kiểm tra: 23/10/2026, Asia/Saigon. Revision: `1fe2b8bed9c45b1a1109cfe76e21c9b064f7c4a2`, nhánh `main`.

## Kết luận

**Code hiện tập trung vào thí nghiệm RCA offline bằng một LLM khi thiếu telemetry, có retrieval tùy chọn và đánh giá confidence/abstention. Chưa có vòng phát hiện–chẩn đoán–sửa–kiểm chứng chạy liên tục, chưa chốt ba bài Q1 làm nền phương pháp và chưa có kết quả LLM thật chứng minh cải tiến so với bài gốc.**

Đã có phần chuẩn bị nghiên cứu dùng được: canonical data, split, provenance, masking, evidence, baseline, raw-output capture, confidence registry, thống kê theo injection và tái tạo bảng. Những phần này là nền thực nghiệm; chúng chưa xác lập một phương pháp mới hoặc khả năng vận hành 24/24.

Phạm vi lượt này là review code và hợp đồng nghiên cứu; giữ nguyên source, config, protocol, dữ liệu và các quyết định đã chấp nhận. Không chạy model, tải trọng số, fine-tune, commit hoặc push. Các nhận định không đồng nghĩa với quyết định bỏ H1 hay thu hẹp mục tiêu hệ thống của chủ dự án.

## 1. Trọng tâm hiện hành

Nguồn ưu tiên là [llms.txt](../../llms.txt), [decision log](../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md) và [protocol v2](../261018-2300-single-llm-simplification-and-evaluation-hardening/design/protocol-v2.md).

Luồng code hiện tại:

```text
telemetry đã lưu + mốc sự cố có sẵn
  -> tạo điều kiện thiếu telemetry
  -> tóm tắt evidence
  -> tùy chọn lấy ca lịch sử thuộc train
  -> một LLM xếp hạng dịch vụ nghi gây lỗi
  -> confidence / trả lời hoặc từ chối, đánh giá offline
  -> accuracy, risk–coverage, chi phí, CI và bảng kết quả
```

- H1 hiện là hướng chính theo quyết định ngày 20/10: đánh giá liệu confidence của chính LLM có giúp giảm lỗi trên những ca được trả lời, so với từ chối ngẫu nhiên ở cùng coverage, dưới điều kiện bỏ telemetry có kiểm soát. P1/P2 về root-name visibility là phân tích phụ; P3 oracle chưa được triển khai.
- H1 có endpoint cụ thể: `gain_exact@0.7`, SESOI 0.05 trên RCAEval, `retrieval=none`, pool `single_modality`. Đây là mục tiêu thiết kế, chưa phải mức cải thiện đã đo. Tên pool này chứa `no_metric/no_log/no_trace`: mỗi điều kiện bỏ một modality, không nhất thiết chỉ còn một modality.
- `selective.py:1-13` phân tích lựa chọn trên các ô đã cache. Đây chưa phải controller thực thi hành động ngoài hệ thống.
- `llm.py:47-58` trả `ranking`, `reason`, `confidence`, `insufficient_evidence`, `next_check`; `next_check` là văn bản gợi ý kiểm tra, chưa phải bản vá hoặc lệnh khắc phục.
- [Kế hoạch single-LLM](../261018-2300-single-llm-simplification-and-evaluation-hardening/plan.md) ghi rõ xây measurement layer và chưa triển khai phương pháp riêng cho H1/H2/H3 như risk control, acquisition policy hoặc shortlist arm. Các confidence score và threshold cơ bản hiện đã có; chưa có bằng chứng chúng tạo thành cải tiến phương pháp mới.

Việc bỏ Jev/escalation là quyết định đã ghi của owner ngày 18/10. Bản [sơ đồ 24/24 ngày 16/10](docs-261016-2303-pipeline-van-hanh-24x7.md) thuộc thiết kế mục tiêu cũ, có các đường dẫn tới module đã bị xóa. Không dùng sơ đồ đó để mô tả runtime hiện hành.

## 2. Code dựa trên những bài nào?

| Công trình | Vai trò đã xác minh trong NT114 | Giới hạn |
|---|---|---|
| **RCAEval**, WWW Companion 2025, DOI [10.1145/3701716.3715290](https://doi.org/10.1145/3701716.3715290) | Benchmark, telemetry, nhãn và nguồn code tham chiếu. | Dùng benchmark không đồng nghĩa tái hiện một phương pháp chẩn đoán của bài gốc. |
| **BARO**, Proc. ACM Softw. Eng. 1(FSE), 2024, DOI [10.1145/3660805](https://doi.org/10.1145/3660805) | `baro.py` tái hiện nhánh preprocessing và robust scoring/ranking của RCAEval, đối chiếu fixture bản chính thức. | BARO gốc có anomaly detection bằng multivariate BOCPD. Bản NT114 nhận mốc tiêm lỗi đã có, không tái hiện toàn bộ detector của BARO. |
| **Where Root Cause Analysis Fails: A Retrieval-Reranking Decomposition**, accepted NeurIPS 2026, [arXiv:2609.36686](https://arxiv.org/abs/2609.36686) | Prior work giới hạn tính mới của H3; đã có bản toàn văn và code kiểm kê/đối chiếu RE1. | Chưa triển khai DecompRCA, chưa đối chiếu một-một đủ điều kiện để lấy số bài báo so trực tiếp. Repo riêng của bài trả 404 khi kiểm tra. |
| **PACE-LM / LM-PACE**, FSE Companion 2024, DOI [10.1145/3663529.3663858](https://doi.org/10.1145/3663529.3663858) | Prior work sát H1 về confidence của LLM cho cloud-incident RCA. | Là tài liệu đối chiếu; NT114 chưa tái hiện phương pháp này thành baseline chạy được. Bản [arXiv](https://arxiv.org/abs/2309.05833) có tên PACE-LM; không đếm hai tên thành hai bài. |

**Chưa tìm thấy hợp đồng chọn ba bài Q1**, gồm ba phương pháp gốc, phiên bản code, benchmark phù hợp, kết quả tái hiện và phần thay đổi của NT114. Các công trình hội nghị ở trên không được tự động tính là ba bài tạp chí Q1. Một số ấn phẩm ACM có mô hình công bố gắn hội nghị/tạp chí; phải kiểm tra theo quy định của nơi nộp.

[Khảo sát Q1 ngày 12/10](research-261012-q1-survey-and-directions.md) có nhiều bài được trích xuất và xếp hạng, nhưng tự ghi rằng báo cáo không chọn hướng. [Tổng quan ngày 19/10](research-261019-tong-quan-elicit-chon-dong-gop-nt114.md) tiếp tục đề nghị H1 có điều kiện, không chứng minh tính mới hoặc hiệu quả đã đạt.

Ví dụ corpus cũ có TAMO (IEEE TSC), TVDiag (ACM TOSEM) và RunbookFX (PACMPL/ICFP). Những tên này xuất hiện trong bảng trích xuất; chúng chưa được chọn thành ba phương pháp gốc được tái hiện trong source. [Audit Q1 riêng](researcher-261023-2223-q1-evidence.md) ghi cụ thể DOI, role và cờ ngành cho các ứng viên. Lượt review này không chứng nhận lại toàn bộ nội dung toàn văn hoặc xếp hạng độc lập của corpus.

Giao thức Q1 cũ dùng **SJR Best Quartile 2025 theo ISSN**, không kiểm quartile theo năm xuất bản. Không được chuyển nhãn đó thành “JCR Q1”, “Q1 đúng chuyên ngành” hoặc “ba bài phù hợp nhất”. Việc chỉ dùng corpus tạp chí cho giai đoạn đầu cũng không đủ để loại trừ prior work ở hội nghị/preprint; vòng ngày 19/10 đã bổ sung các nguồn này.

## 3. So với hệ thống toàn diện 24/24

| Khối người dùng mong muốn | Code hiện có | Bằng chứng và giới hạn |
|---|---|---|
| Thu thập và giám sát liên tục | Chưa có đường chạy live trong source được review. | `run_grid` đọc các ca đã lưu và duyệt lưới hữu hạn. |
| Tự phát hiện lỗi | Chưa có detector online. | `evidence.py:225` dùng `case.inject_time`; data contract §anchor nêu mốc thường lấy từ nhãn, RCA100 lấy alert quan sát được. |
| Truy xuất bằng chứng và ca cũ | Có cho thí nghiệm offline. | Evidence builder và train-only case store; chưa nối nguồn telemetry/runbook live. |
| Phân tích nguyên nhân | Có mã inference và scoring. | Một LLM xếp hạng root service; chưa có kết quả real-model ở các grid tìm thấy. |
| Đưa phương án khắc phục | Mới có `next_check` dạng text. | Chưa có hợp đồng action, precondition và hậu điều kiện phục hồi. |
| Sửa lỗi | Chưa có. | Chưa có công cụ thực thi thay đổi cấu hình/code/hạ tầng. |
| Kiểm tra hồi quy/phục hồi | Có test và tái tạo artifact nghiên cứu. | Chưa có kiểm thử hậu khắc phục, health verification hoặc rollback. |
| Điều phối vòng chạy 24/24 | Chưa có. | Resume lưới thí nghiệm không phải vòng điều phối incident liên tục. |

Đây là khoảng cách giữa scope code hiện hành và mục tiêu mới được nhấn mạnh, không phải lỗi vì một framework RCA offline chưa làm các tác vụ ngoài hợp đồng của nó.

## 4. Findings cần xử lý trước kết quả chính

### [P1] DEV-fit có thể dùng output mock hoặc khác execution identity cho test thật

Vị trí: `analyze.py:249-301`, `analyze.py:399-406`, `analyze.py:114-116`.

`guard_headline` chỉ kiểm `main`; source DEV được chọn bằng strata không có backend/revision/prompt/execution identity. Probe in-memory trong lượt này đọc fixture tổng hợp cũ, target `vllm`, DEV `mock` và khác revision/server/signature: guard chấp nhận main và tạo **2 dòng `dev_fit`, `no_source=false`**. Không có request tới model.

Tác động: ngưỡng dùng cho đánh giá chính có thể được fit từ môi trường/mô hình không tương thích. Cần ràng buộc identity phù hợp của DEV–test và lưu provenance source trước khi dùng threshold trong bài báo.

### [P1] Bảng baseline có thể gộp DEV và test

Vị trí: `analyze.py:306-314`, `analyze.py:433-436`.

`baselines_table` group theo dataset/model/condition; nhánh gọi bảng này chưa lọc DEV như `joint_baselines`. Probe tổng hợp in-memory đặt DEV AC@1=1.0, test AC@1=0.0: bảng trả **0.5**, mất cột `split_role`.

Tác động: nếu input baseline chứa nhiều role, bảng dùng để so phương pháp có thể không phải test-only. Finding không có nghĩa các CSV baseline hiện có đều sai: CSV baseline riêng đang giữ role; lỗi nằm ở đường gộp của analysis.

### [P1] Resume retrieval bỏ qua `top_k`

Vị trí: `run_grid.py:633-641`, `llm.py::execution()`.

Key hoàn tất được kiểm trước khi truy hồi, không chứa `top_k` hoặc digest prompt sau retrieval. [Review 19/10](review-261019-2254-pretrain-final-audit.md) đã có probe đổi top-k nhưng giữ 18 row cũ và ghi config mới. Lượt này xác nhận source/config/scripts/tests không thay đổi từ revision review đó tới HEAD bằng `git diff`; không chạy lại probe ghi output.

Tác động: so sánh thiết kế retrieval có thể dùng lại nhầm kết quả cũ. Các lỗi condition filtering và launcher trong review cũ cũng chưa được sửa trong cây source đối chiếu; không lặp toàn bộ bài test launcher ở lượt này.

## 5. Các giới hạn khoa học phải giữ khi kết luận

1. **Giảm selective risk không tự chứng minh tăng accuracy trên mọi incident.** Từ chối một phần ca làm thay đổi coverage; phải so cùng coverage và báo tỷ lệ ca còn phải xử lý. Chưa có số MTTR, recovery success hoặc tỷ lệ bản vá an toàn.
2. **Evidence đã mang heuristic ranking.** `evidence.py:230-246` xếp dịch vụ theo điểm metric. CSV baseline hiện có cho RCAEval test/full: B1 và B1m AC@1=148/218≈67.89%; BARO-style=116/218≈53.21%. Đây là số baseline đã lưu, chưa rerun; không so trực tiếp với số của bài gốc và không chuyển thành hiệu quả LLM. B1m là đối chứng quan trọng cho tuyên bố reasoning.
3. **Masking theo root là can thiệp thí nghiệm.** `blind_root` dùng nhãn để chọn dịch vụ che, không gửi root của ca hỏi vào prompt. Đây không phải chính sách phát hiện thiếu telemetry triển khai được và không tự là leakage bug.
4. **Precedent có nhãn train là thiết kế case-based reasoning có chủ đích.** Cùng root khác fault còn truy cập được trong split hiện tại; kết quả retrieval không đủ để kết luận khái quát sang root chưa gặp. Không gọi đó là test-label leakage khi chưa có bằng chứng.
5. **Kế hoạch và novelty claim chưa phải bằng chứng khoa học.** H1 đã có câu hỏi/endpoint nhưng vẫn thiếu real-model pilot, chốt phương pháp cải tiến, baseline sát prior work và protocol kết quả chính. SFT/QLoRA mới là phần mở rộng có điều kiện; exporter/trainer nêu trong `llms.txt` chưa tồn tại.

## 6. Kiểm chứng lượt review

- 47 test trong `test_confidence.py`, `test_score.py`, `test_selective.py`, `test_baro.py`: **47 passed in 20.93s** bằng Python của `.venv`.
- Hai lần đầu bị quyền thư mục tạm của sandbox Windows: lần đầu 45 passed/2 setup errors; lần hai workspace basetemp cũng bị từ chối. Lần kiểm chứng hợp lệ dùng basetemp mới với quyền thực thi ngoài sandbox. Không quy lỗi môi trường thành lỗi source.
- Kiểm kê `results*/**/grid.jsonl` trong Python project: 312 row smoke, 106 row canonical smoke, 752 row Nezha; **1.170/1.170 row có backend `mock`**. Không suy ra trạng thái run trên máy khác từ kiểm kê này.
- CPU baseline, visibility, leakage và statistics artifacts tồn tại riêng; không gọi chúng là kết quả LLM giả.
- Hai probe mới về DEV-fit và baseline pooling chạy trong bộ nhớ trên fixture tổng hợp; không ghi database, không gọi API/model.
- Không thay đổi tracked source/config/tests; không chạy lại toàn suite, GPU/runtime production hoặc toàn bộ literature review.

## 7. Cần chốt sau review

Mục tiêu hệ thống 24/24 được giữ nguyên. Trước khi tiếp tục mở rộng code, cần xác định hợp đồng nghiên cứu: **bài nền → phần tái hiện → hạn chế cần sửa → phương pháp cải tiến → phép so công bằng → kết quả cần đo**.

Nếu dùng ba bài, ba vai trò phù hợp với mục tiêu là phát hiện, RCA/retrieval và khắc phục/kiểm chứng. Tích hợp ba khối là giá trị hệ thống; phần đóng góp khoa học vẫn cần một giả thuyết và phép đo phân biệt được cải tiến với thay đổi model, dữ liệu, prompt hoặc ngân sách. Có thể có nhiều đóng góp, nhưng phải kiểm chứng riêng từng phần và toàn chuỗi.

Các quyết định còn mở:

- Chọn ba bài nào, theo SJR hay JCR, năm và chuyên ngành nào, cùng khả năng tái hiện artifact.
- H1 tiếp tục là đóng góp chính hay là đánh giá hỗ trợ cho cải tiến khác; không tự đảo quyết định H1 trong lượt review.
- “Sửa lỗi” gồm mitigation vận hành như restart/rollback/config hay cả tạo bản vá source; hai phạm vi cần benchmark và phép đánh giá khác nhau.
- “Hồi quy” là kiểm thử hồi quy sau bản vá hay phân tích diễn biến lỗi; code hiện có mới bảo vệ tính nhất quán của artifact nghiên cứu.

## Tài liệu kiểm tra chi tiết

- [Paper/code provenance](researcher-261023-2223-paper-provenance.md).
- [Runtime scope](code-reviewer-261023-2223-runtime-scope.md).
- [Q1 evidence](researcher-261023-2223-q1-evidence.md).
