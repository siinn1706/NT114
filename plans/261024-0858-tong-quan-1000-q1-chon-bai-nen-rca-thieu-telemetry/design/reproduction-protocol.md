Đã quyết 2026-10-26: chủ dự án chấp nhận RCLAgent làm bài nền **có điều kiện** (D1, D4), xem [nhật ký quyết định](../../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md). ~~Có điều kiện: chờ chủ dự án chấp nhận bài nền RCLAgent và quyết định ở selection-memo §5.~~ (không còn áp dụng, giữ để lưu sử).

# Giao thức tái hiện RCLAgent (phase 09, phiên bản 0.2, 2026-10-26 giờ Việt Nam)

**Thay đổi 0.2 (2026-10-26).** Theo [nhật ký quyết định](../../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md) (D1-D8, D12): thêm mục 0 (tên gọi sản phẩm là bản thích nghi RCLAgent không có recursion-of-thought, không phải tái hiện đầy đủ; tách kết luận về code gốc khỏi kết luận về bản thích nghi); nhánh (a) đã chọn, nhánh (b) không chọn; giai đoạn 1 (API trả phí) không được phép; giai đoạn 2-3 chưa được phép chạy; niêm phong test nghiêm hơn (D12). Số đích, locator, verdict evidence và quan sát tĩnh không đổi.

Tài liệu này chỉ thiết kế. Chưa chạy code, chưa gọi model, không sửa protocol v2 hay `decisions.md`. ~~Nếu chủ dự án không chấp nhận bài nền thì tài liệu chuyển sang `stale` (phase-09, mục Rủi ro).~~ Chủ dự án đã chấp nhận bài nền có điều kiện ngày 2026-10-26 (D1, D4) nên điều kiện `stale` không xảy ra.

## 0. Tên gọi sản phẩm và phạm vi (quyết định 2026-10-26)

- Sản phẩm của MVP là **một bản thích nghi RCLAgent không có recursion-of-thought** (nhánh (a), D2), **không bao giờ được gọi là tái hiện đầy đủ RCLAgent**. Tiêu đề "Giao thức tái hiện" của tài liệu này chỉ là tên lịch sử của file; giai đoạn 1 (tái hiện nguyên bản) không được phép chạy.
- Giai đoạn phụ thuộc API (giai đoạn 1: backbone Qwen-3.6-Plus qua API đóng, trả phí) **không được phép** (D6): không API trả phí, không gửi telemetry hay evidence ra nhà cung cấp ngoài. Kết quả thích nghi cục bộ không bao giờ thay cho bằng chứng về backbone của bài.
- Số đích ở mục 2 là của **arXiv v1** đã đọc (2605.14866v1). Cần bản TDSC trước khi khẳng định khớp với bài đã xuất bản hoặc dùng số đã xuất bản làm đích (D5); bản TDSC còn mở.
- Kết luận về code gốc (phân tích tĩnh, kiểm CPU không LLM, nếu được lập kế hoạch riêng, D8) và kết luận về bản thích nghi được **báo riêng, không trộn**.
- Lượt kế tiếp chỉ lập kế hoạch triển khai và khả thi: không chạy GPU/model, không thuê cloud, không benchmark dài (D7). Không có ngoại lệ nhiều lời gọi cho kết quả NT114 (D8); chạy phương pháp nhiều lời gọi gốc cần phạm vi duyệt riêng.
- Niêm phong test nghiêm theo D12 (mục 7, cuối).

## 1. Bài nền, bản đã đọc, code

| Mục | Giá trị | Nguồn |
|---|---|---|
| Bài | RCLAgent, *Towards In-Depth Root Cause Localization for Microservices With Multi-Agent Recursion-of-Thought*, IEEE TDSC 2026, doi 10.1109/tdsc.2026.3706572, OpenAlex W7165616276 | selection-memo §1 |
| Bản đã đọc | arXiv v1 2605.14866v1 (14/05/2026). **Mọi số đích dưới đây là "arXiv v1, cần đối chiếu bản TDSC".** Bản TDSC chưa có (selection-memo §5 điểm 4) | `research/cards/t3/W7165616276.md` |
| Toàn văn đã dùng | `private/fulltext/261024/W7165616276.txt` (sha256 byte thô 32cba9cc561466740ddeddacb9ef8ddeb42876b0f44d2adbb7aa929f3934bb32). Locator dạng "dòng N" trong tài liệu này là số dòng của file đó | card T3 |
| Code | https://github.com/LLM4AIOps/RCLAgent-V2, giấy phép MIT, commit **3052e7a6a9598d984ba1482f3dc41123c8823a99** (2026-06-18). Đã kiểm lại bằng GitHub API ngày 2026-10-25 (UTC): HEAD của `main` vẫn là commit này | `work/t3/W7165616276-artifact.csv`; kiểm lại trong phiên này |
| Điểm vào | `tool_server.py` (Flask, 4 endpoint), `coordinator.py`, `evaluate.py`, `final_eval.sh`, `preprocess/preprocess_re2ob.py` | README §5, §9 |

Mọi lần chạy phải ghim commit trên. Nếu repo đổi, ghi commit thay thế và lý do trước khi dùng.

## 2. Số liệu đích, locator và verdict evidence

Chỉ hàng "đích chính" quyết định kết quả tái hiện. Hàng "tham chiếu" không nằm trong bundle NT114 hoặc không chạy được với model cục bộ, chỉ dùng để đối chiếu.

"Verdict" lấy từ `work/t3/W7165616276-evidence.csv` (cột `verdict`, mã C1..C8) hoặc từ kiểm tra riêng của phiên này (ghi "kiểm riêng").

| ID | Số liệu | Locator | Verdict evidence | Vai trò |
|---|---|---|---|---|
| T1 | RE2-OB, RCLAgent (Qwen-3.6-Plus): R@1 = 56.67 | Table I, hàng RCLAgent (Qwen-3.6-Plus) ở dòng 1184, cột RCAEval; README §7.3 | supported (C1); kiểm riêng: 56.67% = 51/90 | **đích chính** |
| T2 | R@3 = 80.00 | như T1 | supported (C1); kiểm riêng: 72/90 | **đích chính** |
| T3 | R@5 = 86.67 | như T1 | supported (C1); kiểm riêng: 78/90 | **đích chính** |
| T4 | R@10 = 100.00 | như T1 | supported (C1); kiểm riêng: 90/90 | **đích chính** |
| T5 | MRR = 71.03 | như T1; Eq. 11 | supported (C1). Kiểm riêng: từ R@k ở T1..T4, MRR chỉ có thể nằm trong [67.1, 72.2]; 71.03 nằm trong khoảng nên không mâu thuẫn. MRR không tính lại được nếu thiếu hạng từng sự cố | **đích chính** |
| T6 | RE2-OB, RCLAgent (Claude-3.5-Sonnet): 52.31 / 63.15 / 79.39 / 85.96 / MRR 62.97 | Table I | **chưa có dòng trong evidence CSV**; kiểm riêng: chép đúng Table I, nhưng các giá trị không phải bội của 1/90 (ví dụ 52.31% x 90 = 47.08) nên có thể là trung bình nhiều lần chạy; chưa đối chiếu được với README | tham chiếu (cần API Anthropic, không dùng) |
| T7 | AIOps2022, Qwen-3.6-Plus: 65.15 / 78.79 / 86.36 / 95.45 / MRR 73.24 | Table I; README §7.1 | insufficient (C2: 66 trong 263 sự cố liệt kê, bài không nêu |A|; C3: README §6 lấy hạng tốt nhất qua các trace). Kiểm riêng: 43/66, 52/66, 57/66, 63/66 khớp | tham chiếu; AIOps2022 **không** có trong `prep.yaml` nên không vào bundle NT114 |
| T8 | Augmented-TrainTicket (Nezha-30), Qwen-3.6-Plus: 82.35 / 88.24 / 94.12 / 94.12 / MRR 86.47 | Table I; README §7.2 | không có dòng riêng trong evidence CSV (C4 nói Nezha thắng MRR 90.37). Kiểm riêng: 14/17, 15/17, 16/17, 16/17 khớp | tham chiếu; 17 sự cố, chưa căn chỉnh với 45 sự cố Train Ticket của nguồn `nezha` trong bundle |
| T9 | Độ trễ RCAEval 49.79 s/truy vấn (RCLAgent), CoT 85.77 s | Table II (dòng 1287) | supported (C5) | tham chiếu; phần cứng và API khác nên không dùng làm tiêu chí |
| T10 | Phụ thuộc backbone: Claude 54.88-88.67, DeepSeek-R1-Qwen-32B 36.13-65.13, Llama-3.1-70B 7.09-19.42 (MRR theo subset AIOps2022) | Table III (dòng 1378) | insufficient (C8): không có model dưới 32B | tham chiếu; lý do có giai đoạn 2 |
| T11 | Tuyên bố "vượt mọi SOTA", trung bình +7.51 MRR | §V-B, Table I | **contradicted** (C4): Nezha thắng MRR trên Train-Ticket (90.37 so với 86.47), BARO thắng R@3 và R@5 trên RCAEval (92.22 và 100 so với 80.00 và 86.67) | không phải đích; ghi để không tái hiện nhầm |
| T12 | Kiểm định Wilcoxon p = 0.012 cho MRR so với mABC và GALA | §V-B | chưa đối chiếu: bài không cho số liệu từng sự cố | không phải đích |

Ghi chú về T1..T5: 90 sự cố là 5 dịch vụ x 6 loại lỗi x 3 lần chạy (README §3.3), tức 30 ô lỗi x 3 lần lặp. Ba lần lặp của một ô tương quan với nhau.

## 3. Quan sát tĩnh từ code ảnh hưởng đến việc tái hiện

Đây là kiểm riêng của phiên này trên `coordinator.py`, `evaluate.py`, `preprocess_re2ob.py` tại commit 3052e7a6 (chỉ đọc, không chạy).

1. **Số lời gọi.** Mỗi span có `self_state_verification` (vòng gọi tool do LLM chọn, cộng một lời gọi dự phòng) và `consolidate` (một lời gọi). Tối thiểu 2 lời gọi mỗi span. Cuối cùng một lời gọi `print_results` cho bảng xếp hạng. Số span mỗi trace của RE2-OB chưa được đếm; đây là việc đầu của giai đoạn 0 (mục 7).
2. **Tool do LLM chọn.** `self_state_verification` đưa `search_logs` và `search_fluctuating_metrics` dưới dạng function calling. Model nhỏ có thể không gọi tool. Đây là cơ sở của giả thuyết IM4.
3. **Độ tin cậy.** Trường `confidence` nằm trong JSON của `consolidate`, tức nằm trong Root-Level Report. Lời gọi `print_results` cuối chỉ trả danh sách `root_causes`. Đây là điểm 2 của selection-memo §5.
4. **Chọn trace và oracle.** Với RE2-OB, `preprocess_re2ob.py` (dòng 260-272) lấy tối đa 5 root span có `duration` lớn nhất trong cửa sổ [inject-60 s, inject+300 s], dự phòng 3 span lớn nhất toàn bộ. `evaluate.py` lấy **hạng tốt nhất qua các trace của một sự cố** (README §6). Bước lấy hạng tốt nhất của `evaluate.py` dùng nhãn để chọn trace nên có tính oracle.
5. **Prompt gắn với dataset.** `_SYSTEM_PROMPTS["re2ob"]` liệt kê tên dịch vụ cố định, và `_normalise_results` chuẩn hóa tên theo danh sách đó. Danh sách là tập ứng viên, không phải nhãn, nhưng bài không mô tả bước này.
6. **Ngưỡng lỗi.** Code dùng `DURATION_THRESHOLD_US` mặc định 10 s; bài định nghĩa lỗi là độ trễ span vào lớn hơn 100 lần trung bình (card, mục Problem). Hai định nghĩa khác nhau (đã ghi ở T3 rescore).
7. **Cửa sổ metric.** README mô tả tool metric là cửa sổ ±10 phút; bài nêu δ = 60 s và n = 3 (§V-A.4). Cần đọc `tool_server.py` ở giai đoạn 0 để biết giá trị thực.
8. **Nhiệt độ và seed.** `llm.py` và `config.py` không đặt temperature hay seed. Kết quả phụ thuộc mặc định của nhà cung cấp.
9. **Tên model.** Bảng ghi "Qwen-3.6-Plus", README mặc định `qwen-plus` trên DashScope. Cần ghi định danh model mà nhà cung cấp báo về lúc chạy.

## 4. Hai nhánh cho quyết định 1 của selection-memo §5

~~Quyết định 1 chưa được chủ dự án quyết. Giao thức trình bày cả hai nhánh cạnh nhau. **Tài liệu này không chọn nhánh nào.**~~ **Đã quyết 2026-10-26 (D2): nhánh (a).** Nhánh (b) không chọn; cột (b) giữ để lưu sử. Giai đoạn 0 và 1 (code gốc) không phụ thuộc nhánh; giai đoạn 2 và 3 phụ thuộc.

| | Nhánh (a): giữ protocol v2 §1 — **đã chọn** | Nhánh (b): mở rộng bất biến cho pipeline nhiều lời gọi — **không chọn** |
|---|---|---|
| Ý tưởng | Phân rã trace thành span và chạy tool của RCLAgent bằng code tất định để tạo bằng chứng. **Một** lời gọi (n mẫu) tổng hợp bảng xếp hạng | Giữ pipeline nhiều lời gọi trên một model: agent theo span, hợp nhất bottom-up, Root-Level Report, Global Evidence Graph, Synthesizer |
| Phần cốt lõi của bài | **Bỏ recursion-of-thought**: hợp nhất bottom-up bằng quy tắc code thay cho các lời gọi LLM theo span. Giữ phân rã span, tool metric/log, bằng chứng gom từ dưới lên | Giữ đủ |
| Cần sửa protocol v2? | Không | Có: chủ dự án phải sửa §1 ("one model's single call") thành một pipeline nhiều lời gọi, nêu rõ lời gọi nào là câu trả lời được báo cáo |
| Prompt và schema | Giữ prompt `v1` và schema hiện có; chỉ thay nội dung khối `{evidence}` bằng bằng chứng từ tool (một builder bằng chứng riêng, có `BUILDER_VERSION` riêng) | Cần prompt riêng cho từng vai (span, hợp nhất, tổng hợp); là một bộ prompt thêm, không đụng `v1` |
| Số lời gọi mỗi ô | 1 (n mẫu, ví dụ n = 10 theo hardware profile) | Tối thiểu 2 x số span + 1, nhân với số mẫu nếu lấy mẫu cả pipeline. Số span chưa đo |
| Độ tin cậy và abstention | Lấy từ chính lời gọi đó (registry `confidence.py`) nên tương thích bất biến §1 | Hai lựa chọn chưa quyết (selection-memo §5 điểm 2): `r_conf_root` từ lời gọi riêng, hoặc độ tin cậy lấy từ lời gọi Synthesizer |
| Rủi ro | Mất phần được cho là đóng góp lõi; không kiểm được ablation RLDR/GEG theo cách gốc; kết quả không còn là "tái hiện RCLAgent" mà là "builder bằng chứng lấy cảm hứng từ RCLAgent" | Chi phí và độ trễ trên profile 12 GB (qwen3.5-4b fp8, qwen3.5-9b nf4, qwen3-8b awq) chưa đo; ngữ cảnh 8192 token có thể không chứa GEG của trace lớn; function calling của model nhỏ chưa kiểm |
| Trạng thái đo | Chưa chạy | Chưa chạy |

~~Giả định cần chủ dự án xác nhận: bảng tái hiện của giai đoạn 1 và 2 là bảng tham chiếu riêng, không phải bảng kết quả headline nên bất biến §1 không áp cho chúng.~~ **Đã quyết (D8):** không có ngoại lệ nhiều lời gọi cho kết quả NT114. Phân tích tĩnh và kiểm CPU không LLM của code gốc có thể lập kế hoạch riêng; chạy phương pháp nhiều lời gọi gốc cần phạm vi duyệt riêng. Giai đoạn 2 chỉ còn ý nghĩa đo tính khả thi, và chưa được phép chạy (D7).

## 5. Căn chỉnh dataset với bundle NT114

Kiểm riêng bằng cách đọc `data/canonical/v1/rcaeval/visible/incidents.jsonl` và `data/splits/within-rcaeval-grouped-0-e9b2c81c/assignments.jsonl` (chỉ đếm, không đọc nhãn, không chạy model).

| Khía cạnh | RCLAgent (README, code) | Bundle NT114 | Hành động |
|---|---|---|---|
| Nguồn | RCAEval RE2-OB, 90 sự cố (5 dịch vụ x 6 lỗi x 3 lần) | `rcaeval`, `dataset_subset = RE2`, `system = online-boutique`: 91 thư mục, 1 bị REJECT (trùng `checkoutservice_cpu`), còn **90** vào split (train 48, val 21, **test 21**). Cả 91 có đủ metrics, logs, traces (`present`) | Số sự cố khớp 90 = 90. Ghi: chỉ **21** nằm ở vai test |
| ID sự cố | Thư mục `RE2-OB/<dịch vụ>_<lỗi>/<lần>` | `incident_uid` = hash `rcaeval.<16 hex>`, không mang nhãn. Liên kết về thư mục gốc nằm trong `eval_only/source_index.jsonl` | Ánh xạ ID gốc sang `incident_uid` chỉ ở vùng eval-only; không đưa vào prompt |
| Preprocessing | `preprocess_re2ob.py`: metrics dạng "simple" (mặc định `use_simple_metrics=True`), logs lọc bỏ INFO/DEBUG, trace lỗi = top 5 root span theo `duration` quanh `inject_time` | Canonical: Parquet, log giữ mọi mức (270 sự cố trong toàn RCAEval thiếu mức log), cửa sổ bằng chứng [t-600 s, t+300 s], `inject_time` làm anchor (không xuất hiện trong text) | Khác nhau có chủ đích; mọi khác biệt ghi vào báo cáo giai đoạn 3 |
| Tên dịch vụ | `frontendservice` (trace) và `frontend` (metric, log), prompt liệt kê cả hai | Alias `frontendservice` -> `frontend` (`configs/service_aliases.yaml`, 91 sự cố); ứng viên 12 dịch vụ dạng `ad, cart, checkout, currency, email, frontend, frontendexternal, payment, productcatalog, recommendation, redis, shipping` | Đầu ra của adapter phải enum-ràng buộc theo `VisibleCase.candidates`; không dùng danh sách cứng trong prompt |
| Granularity | Dịch vụ, pod và node; pod đúng thì dịch vụ được tính đúng (§V-A.3) | Nhãn mức dịch vụ; ứng viên không có hạ tầng (`is_infra`) | Chấm ở mức dịch vụ. Không còn cần quy tắc pod -> dịch vụ |
| Candidate set | Mọi thực thể bài trả về; xếp hạng >= 10 | 12 ứng viên, trần top-5 (prompt `v1`), hạng > 5 bị censor | R@10 gần như vô nghĩa với 12 ứng viên. Giai đoạn 3 báo AC@1..5 và MRR@5 censor, **không so MRR top-10 của bài** |
| Split | Không có split (training-free); tinh chỉnh siêu tham số trên AIOps2022-A | `within-rcaeval-grouped`: nhóm theo ô lỗi nên 3 lần lặp của một ô cùng một split | Siêu tham số chỉ chỉnh trên val (DEV); test chỉ chạy sau khi đóng băng |
| Đơn vị độc lập | Sự cố (fault) | Injection (`incident_uid`), trọng số 1/số bản ghi | Khớp. Rủi ro: 3 lần lặp của một ô tương quan (xem test-matrix, mục 6) |

Hệ quả chính: với RE2-OB, phép đo trên bundle NT114 chỉ có **21 injection test**. Không đủ để xác nhận con số 56.67 của bài (khoảng tin cậy rộng cỡ ±20 điểm, ước tính thô theo p(1-p)/n, chưa tính bằng công cụ). Vì vậy việc "tái hiện số của bài" chỉ làm ở giai đoạn 1 trên dữ liệu gốc đủ 90 sự cố, còn giai đoạn 3 là một phép đo riêng trên bundle, không phải so khớp số.

## 6. Môi trường

| Giai đoạn | Môi trường | Ghi chú |
|---|---|---|
| 0 | CPU, Python >= 3.10 (README §1), Linux (Windows chưa kiểm), venv riêng ngoài NT114, `requirements.txt` của repo gốc | Không gọi LLM |
| 1 | Như giai đoạn 0, thêm endpoint tương thích OpenAI của nhà cung cấp mà bài dùng (DashScope, Qwen-3.6-Plus) | ~~Cần quyền chạy API trả phí và quyền gửi telemetry RE2-OB ra ngoài~~ **Không được phép (D6)**: không API trả phí, không gửi span, log, metric ra nhà cung cấp ngoài (`llms.txt` ghi "không gửi evidence ra ngoài"); không dùng khóa nào trong tài liệu này |
| 2 | vLLM cục bộ trên RTX 4080 Laptop 12 GB, profile `qwen35-4b-fp8` (chính), `qwen3-4b-2507-fp8`, `qwen35-9b-nf4`, `qwen3-8b-awq` (replication), `max_model_len` 8192, `configs/hardware/rtx4080-laptop-12gb.yaml` | Cần probe GPU và feasibility trước. Quyết định "CPU-only" trong `decisions.md` (2026-10-18) phải được chủ dự án mở; theo D7 lượt kế tiếp chỉ lập kế hoạch khả thi, **chưa được phép chạy GPU/model**. Function calling cần bật tool parser trong vLLM, chưa kiểm |
| 3 | Như giai đoạn 2 trên bundle NT114 (`RCA_DATA_HOME` trỏ `parts/` của bundle đã kiểm chứng) | Chạy qua `rca.run_grid`; phụ thuộc nhánh (a) hoặc (b) |

## 7. Thứ tự và điều kiện đạt

### Cách chấm định trước (áp cho mọi giai đoạn)

Chấm theo **từng sự cố** với một trace chỉ định trước, không dùng "hạng tốt nhất qua các trace" làm kết quả chính.

- **S-first (kết quả chính của NT114):** trace có root span `duration` lớn nhất trong cửa sổ [anchor-60 s, anchor+300 s]; hòa thì lấy `trace_id` nhỏ nhất theo thứ tự chữ. Quy tắc tất định, không dùng nhãn.
- **S-best (chỉ để so với bài):** hạng tốt nhất qua tối đa 5 trace của sự cố, đúng như `evaluate.py`. Gắn nhãn "oracle, chỉ dùng đối chiếu với bài nền", không đưa vào bảng headline.
- **S-mean (phụ):** trung bình RR qua các trace, không dùng nhãn để chọn trace.
- Báo cáo kèm chênh lệch S-best trừ S-first để đo mức phồng do oracle.

### Sai số chấp nhận được, định trước

Bài không công bố phương sai giữa các lần chạy, nên dùng xấp xỉ nhị thức trên 90 sự cố: ±1.96 x sqrt(p(1-p)/90) với p là giá trị của bài. Xấp xỉ này **không thận trọng**: nó bỏ qua tương quan của ba lần lặp mỗi ô lỗi (khoảng 30 ô hiệu dụng) và phương sai giữa các lần chạy LLM. Với n hiệu dụng = 30, sai số rộng hơn (R@1 ±17.7, R@3 ±14.3, R@5 ±12.2, MRR khoảng ±14). Ngưỡng "đạt" giữ theo n = 90 (đã đóng băng); một lần lệch nằm trong dải n = 30 chỉ được kết luận tối đa "một phần" và được ghi là mơ hồ.

| Số đích | Giá trị bài | Sai số | Ngưỡng dưới để "đạt" |
|---|---|---|---|
| R@1 (T1) | 56.67 | ±10.2 | >= 46.5 |
| R@3 (T2) | 80.00 | ±8.3 | >= 71.7 |
| R@5 (T3) | 86.67 | ±7.0 | >= 79.7 |
| R@10 (T4) | 100.00 | p = 1 nên công thức suy biến; ngưỡng cố định | >= 86/90 |
| MRR (T5) | 71.03 | ±8 (giả định SD của RR khoảng 0.38, chưa đo) | >= 63.0 |

Chỉ xét phía dưới. Giá trị cao hơn bài hơn sai số không làm hỏng điều kiện đạt nhưng phải kèm ghi chú kiểm tra chấm điểm và rò rỉ. Các ngưỡng được đóng băng trước khi chạy; không đổi sau khi thấy kết quả.

### Giai đoạn 0: chuẩn bị, không gọi LLM

*Trạng thái 2026-10-26: chỉ phân tích tĩnh và kiểm CPU không LLM của code gốc; có thể là kế hoạch riêng (D8). Kết luận về code gốc báo riêng với kết luận về bản thích nghi.*

1. Dựng môi trường, ghim commit 3052e7a6, chạy quick start `sample_data/` chỉ ở bước `evaluate.py sample_data result` trên kết quả có sẵn (README §2 bước 4): kỳ vọng R@1 = 1.0 (1/1). Bước này chỉ kiểm đường chấm điểm.
2. Chạy `preprocess_re2ob.py` trên RE2-OB gốc (CPU) và đếm: số sự cố (kỳ vọng 90), số trace lỗi mỗi sự cố, số span mỗi trace, số span tổng. Số span quyết định ước lượng chi phí nhánh (b) và ngân sách giai đoạn 1.
3. Đọc `tool_server.py` để chốt cửa sổ metric (±10 phút hay 60 s) và quy tắc lọc log.
4. Kiểm danh sách sự cố RE2-OB của README khớp 91 thư mục (1 trùng) của bundle.

Điều kiện qua: bước 1 ra đúng 1.0; bước 2 ra 90 sự cố; chi phí giai đoạn 1 ước lượng được bằng số span đã đếm.

### Giai đoạn 1: tái hiện nguyên bản (backbone của bài)

**Trạng thái 2026-10-26: không được phép (D6).** Đòi hỏi API trả phí của backbone đóng và gửi telemetry ra ngoài. Không chạy; không có kết luận "đạt", "một phần" hay "không đạt" nào được ghi. Kết quả thích nghi cục bộ không thay cho bằng chứng về backbone của bài. Nội dung dưới đây giữ để lưu sử và cho trường hợp chủ dự án cấp phạm vi mới.

Chạy code gốc, backbone Qwen-3.6-Plus qua API tương thích OpenAI, trên đủ 90 sự cố RE2-OB, tối đa 5 trace mỗi sự cố, báo S-best (để so với bài) và S-first. Tối thiểu hai lần chạy độc lập (số lần cuối do chủ dự án đặt cùng ngân sách). Quy tắc nhiều lần chạy, định trước: kết luận dùng **trung bình các lần chạy** cho từng số đích; báo cáo **mọi** lần chạy; không bao giờ chọn lần tốt nhất; nếu một lần riêng lẻ có MRR S-best dưới 55.11 thì kết luận tối đa là "một phần".

| Kết luận | Điều kiện |
|---|---|
| **Đạt** | S-best đạt đủ năm ngưỡng ở bảng trên, tỉ lệ trace cho danh sách hợp lệ >= 90%, và đã ghi định danh model nhà cung cấp trả về |
| **Một phần** | MRR S-best >= 55.11 (MRR của BARO trên cột RCAEval, Table I) nhưng không đủ năm ngưỡng; hoặc đạt ngưỡng nhưng danh sách hợp lệ < 90% |
| **Không đạt** | MRR S-best < 55.11, hoặc lần chạy không hoàn tất vì lỗi của code gốc đã ghi nhận |
| **Không kiểm được** | Chủ dự án không cho chạy API trả phí, nhà cung cấp không còn phục vụ model tương đương, hoặc bản TDSC có bất kỳ số đích T1..T5 lệch quá sai số ở bảng trên so với arXiv v1 và chưa tính lại đích theo bản TDSC. **Đây không phải "không đạt"** |

### Giai đoạn 2: một LLM cục bộ, code gốc

**Trạng thái 2026-10-26: chưa được phép chạy (D7, D8).** Chạy code gốc nhiều lời gọi cần phạm vi duyệt riêng; lượt kế tiếp chỉ lập kế hoạch khả thi (máy thực tế, model dự kiến, lượng tử hóa, giới hạn bộ nhớ/thời gian, cổng dừng).

Chạy cùng code (sửa tối thiểu: `LLM_API_URL` trỏ vLLM) trên cùng 90 sự cố RE2-OB với một model của profile 12 GB (chính: `qwen35-4b-fp8`). Không có số đích của bài (không có model dưới 32B trong Table III), nên **đây không phải tái hiện số**, mà là kiểm tính khả thi:

| Kết luận | Điều kiện (đặt trước) |
|---|---|
| **Khả thi** | >= 90% trace cho danh sách hợp lệ; chạy xong 90 sự cố với S-first trong ngân sách thời gian chủ dự án đặt; tỉ lệ span agent gọi được cả hai tool được ghi nhận |
| **Một phần** | 50% đến dưới 90% danh sách hợp lệ |
| **Không khả thi** | Dưới 50% hoặc không hoàn tất |

Độ chính xác (S-first, S-best) chỉ được báo cáo, kèm B0 (12 ứng viên, R@1 ngẫu nhiên khoảng 8.3%), B1 và B1m trên cùng sự cố. Không đặt ngưỡng độ chính xác vì không có tiền lệ để căn cứ. Khoảng cách giữa giai đoạn 1 và giai đoạn 2 là quan sát, không có ngưỡng "đạt".

### Giai đoạn 3: bundle NT114

Chạy adapter theo nhánh (a) (đã chọn; (b) không chọn) trên vai test, theo test-matrix. Chạy thật với model cục bộ chưa được phép trong lượt kế tiếp (D7). Giai đoạn này không có tiêu chí "tái hiện đạt". Điều kiện qua là kiểm căn chỉnh:

1. Đếm sự cố RE2-OB khớp 90 (21 test) và ánh xạ ID gốc -> `incident_uid` đủ 90.
2. Adapter đọc chỉ vùng visible; kiểm hoán vị nhãn cho đầu ra tool và prompt giống hệt; quét import (không import `visibility`, `baselines`, `analyze`...); canary nhãn không xuất hiện.
3. Với cùng sự cố và cùng trace S-first, số lỗi parse và độ hợp lệ danh sách được tabulate.
4. Danh sách khác biệt preprocessing (mục 5) được điền đủ.

### Niêm phong 21 injection test trước M5

Giai đoạn 1 và 2 chạy trên đủ 90 sự cố RE2-OB, trong đó có 21 injection là vai test của NT114. Để không lộ test trước khi đóng băng (M5 trong mvp-outline). **Đã quyết D12 (2026-10-26): niêm phong nghiêm.** Không mở kết quả test RE2-OB nào, kể cả tổng gộp 90, trước M5; phát triển dùng train/val theo vai; phải kiểm lịch sử lộ test và ghi trung thực mọi lần lộ, không mô tả là đã khôi phục tính mù (kiểm lịch sử: còn mở). Quy tắc mặc định dưới đây được chọn; phương án khác bị gạch là không chọn:

Vì tổng gộp 90 trừ kết quả từng sự cố của 48 train + 21 val RE2-OB nhìn thấy được sẽ lộ kết quả 21 test, quy tắc đề xuất mặc định (an toàn hơn) niêm phong cả tổng gộp:

- Đầu ra từng sự cố, độ chính xác theo vai, **và tổng gộp 90** được lưu nhưng niêm phong: không đọc, không tabulate, không dùng để quyết định prompt, builder, ngưỡng hay chọn cải tiến, cho đến sau M5.
- **Kết luận đạt/một phần/không đạt của giai đoạn 1, kết luận khả thi của giai đoạn 2 và kết luận IM4 chỉ được công bố sau M5.**
- Trước M5 chỉ được xem chẩn đoán từng sự cố trên **48 train + 21 val RE2-OB** (không nhầm với 69 injection test có trace), cùng tỉ lệ hợp lệ và lỗi parse. Sự cố vai train của RE2-OB được phép dùng cho chẩn đoán giai đoạn 1-2 vì code gốc không huấn luyện.
- Mọi lựa chọn thiết kế trước M5 (kể cả IM4) dựa trên 48 train + 21 val RE2-OB.
- ~~Phương án khác cho chủ dự án (D12): chỉ lộ tổng gộp 90, không có kết quả từng sự cố hay từng tập con trên train+val, và chẩn đoán trên một tập con rời nhau.~~ Không chọn.
- ~~Quy tắc cần chủ dự án xác nhận (D12 trong mvp-outline).~~ Đã xác nhận 2026-10-26. Lưu ý: câu "sự cố vai train của RE2-OB được phép dùng cho chẩn đoán giai đoạn 1-2" ở trên là thiết kế cũ cho code gốc không huấn luyện; D12 nói dùng train/val theo vai của chúng, nên cách dùng vai train này cần được xác nhận lại trước khi chạy code gốc (hiện chưa có lần chạy nào được phép).

## 8. Quyết định mở và rủi ro

1. ~~Nhánh (a) hay (b); phạm vi áp bất biến §1 cho bảng tái hiện (mục 4).~~ Đã quyết 2026-10-26: nhánh (a); không có ngoại lệ nhiều lời gọi cho kết quả NT114 (D2, D8).
2. ~~Quyền chạy API trả phí và quyền gửi telemetry RE2-OB ra dịch vụ ngoài cho giai đoạn 1 (D6).~~ Đã quyết 2026-10-26: không cấp; giai đoạn 1 không được phép (không phải kết luận "không kiểm được" của một lần chạy).
3. Mở quyết định CPU-only cho giai đoạn 2 và 3: **còn mở**; D7 chỉ cho lập kế hoạch khả thi, chưa cho chạy.
4. Bản TDSC chưa có: mọi số đích dựa trên arXiv v1 (D5: còn mở; cần trước khi khẳng định khớp bài đã xuất bản).
5. Rủi ro dữ liệu: chỉ 21 injection test cho RE2-OB; README tính hạng tốt nhất qua trace; 66/263 sự cố AIOps2022 (không dùng ở đây).
6. Rủi ro phương pháp: model nhỏ chưa được kiểm; ngữ cảnh 8192 token có thể không chứa Global Evidence Graph của trace lớn, nếu phải cắt bớt thì phải ghi là sai khác so với bài.
7. Hai bản ghi OpenAlex cho cùng một bài (W7165616276 và W7161299676) xuất hiện khi tra prior work; cần gộp ở phase 10.
