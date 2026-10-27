Đã quyết 2026-10-26: chủ dự án chấp nhận RCLAgent làm bài nền **có điều kiện** (D1, D4), xem [nhật ký quyết định](../../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md). ~~Có điều kiện: chờ chủ dự án chấp nhận bài nền RCLAgent và quyết định ở selection-memo §5.~~ (không còn áp dụng, giữ để lưu sử).

# Đề cương MVP (phase 09, phiên bản 0.2, 2026-10-26 giờ Việt Nam)

**Thay đổi 0.2 (2026-10-26).** Ghi các quyết định D1-D13 của chủ dự án (xem [nhật ký quyết định](../../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md)): thêm cột trạng thái ở §1; §3 chọn IM1; §4-§7 phản ánh nhánh (a) đã chọn, nhánh (b) không chọn (giữ để lưu sử), lượt kế tiếp chỉ lập kế hoạch triển khai và khả thi, nhánh tái hiện cần API không được phép. Các phần chưa đổi giữ nguyên; số liệu và bằng chứng không đổi.

Chỉ thiết kế. Không code, không chạy model. MVP là phạm vi tối thiểu chứng minh được hai việc: (1) tái hiện RCLAgent đến mức đo được, (2) một cải tiến có kiểm falsifier. *Đã quyết 2026-10-26: việc (1) là một bản thích nghi RCLAgent không có recursion-of-thought, không bao giờ gọi là tái hiện đầy đủ; việc (2) là IM1.* Tài liệu đi cùng: [reproduction-protocol.md](reproduction-protocol.md), [improvement-hypotheses.md](improvement-hypotheses.md), [test-matrix.md](test-matrix.md).

## 1. Quyết định của chủ dự án phải có trước

| # | Quyết định | Chặn mốc | Trạng thái 2026-10-26 |
|---|---|---|---|
| D1 | Chấp nhận RCLAgent làm bài nền (selection-memo §5). Nếu không: phase 09 thành `stale` | mọi mốc | **Đã quyết (chấp nhận có điều kiện).** Chấp nhận RCLAgent (W7165616276) làm bài nền trên kết quả single-eligible hiện tại để phát triển thiết kế tiếp. Không khẳng định: là phương pháp tốt nhất, thắng ổn định, đã được tái hiện, hay phù hợp model 4-9B |
| D2 | Nhánh (a) hay (b) cho bất biến một lời gọi (§5 điểm 1) | M3 trở đi | **Đã quyết: nhánh (a).** Giữ bất biến một lời gọi của protocol v2: một model, một lời gọi mỗi câu trả lời; phân rã, chọn bằng chứng và chạy tool là code tất định, LLM chỉ tổng hợp và xếp hạng ở lời gọi cuối; không đệ quy đa agent, không judge hay leo thang. Nhánh (b): không chọn. Kết quả là bản thích nghi RCLAgent không có recursion-of-thought, không bao giờ gọi là tái hiện đầy đủ; phát hiện về code gốc báo riêng với phát hiện về bản thích nghi |
| D3 | Cách xử lý `h1-compat` có điều kiện: thu H1, coi `no_trace` là thất bại có chủ đích, hay lấy độ tin cậy từ lời gọi tổng hợp (§5 điểm 2) | M5; IM3 chỉ có nghĩa nếu chọn cách thứ ba ở nhánh (b) | **Đã quyết: giữ H1, xử lý chứ không loại.** Quần thể H1 không thu hẹp; `no_trace` dùng tool metric/log tất định, bằng chứng phẳng theo ứng viên, một lời gọi tổng hợp; quy tắc chọn đường chỉ dựa trên telemetry sẵn có và đóng băng trước đánh giá; không có khung hợp lệ thì dùng đường không khung, ca vẫn trong mẫu số; báo cáo tách theo khả năng áp dụng và hệ; độ tin cậy theo protocol hiện hành, không từ lời gọi LLM thứ hai. Ba cách cũ (thu H1, coi `no_trace` là thất bại, độ tin cậy từ lời gọi tổng hợp): không chọn |
| D4 | Bài đứng hạng 1 theo cổng G hay xem top-2 DiagFusion/RCLAgent (§5 điểm 3) | D1 | **Đã quyết (chấp nhận có điều kiện).** RCLAgent là bài nền theo cổng G, cùng điều kiện như D1. DiagFusion chỉ ở bảng so sánh và thảo luận chọn bài, không có nhánh triển khai; G1 không nới để đổi lựa chọn |
| D5 | Tải bản TDSC để đối chiếu Table I-III (§5 điểm 4) | kết luận giai đoạn 1 | **Đã quyết một phần.** Kế hoạch tiếp tục trên arXiv v1 đã đọc, nêu rõ phiên bản. Bản TDSC là điều kiện trước khi khẳng định khớp bài đã xuất bản hoặc dùng số đã xuất bản làm đích. **Còn mở:** chưa có bản TDSC (tìm bản tác giả/OA hợp pháp). 17 PDF top-30 và 152 abstract thiếu ở lại sổ truy cập/thiếu dữ liệu |
| D6 | Quyền chạy API trả phí cho giai đoạn 1, trần chi phí, **và quyền gửi telemetry RE2-OB (span, log, metric) ra nhà cung cấp ngoài** (`llms.txt` ghi "không gửi evidence ra ngoài") | M1b (giai đoạn 1) | **Đã quyết: không cấp.** Không API trả phí, không gửi telemetry hay evidence ra nhà cung cấp ngoài. Nhánh tái hiện phụ thuộc API (giai đoạn 1) là **không được phép**; kết quả thích nghi cục bộ không thay cho bằng chứng về backbone của bài |
| D7 | Mở quyết định CPU-only, probe GPU, feasibility profile 12 GB | M4 trở đi | **Đã quyết: lượt kế tiếp chỉ lập kế hoạch triển khai và khả thi.** Không chạy GPU/model, không thuê cloud, không benchmark dài. Kế hoạch phải nêu máy thực tế, model dự kiến, lượng tử hóa, giới hạn bộ nhớ/thời gian và cổng dừng để chủ dự án duyệt sau. Mở quyết định CPU-only để chạy thật: chưa cấp |
| D8 | Xác nhận bảng tái hiện (giai đoạn 1-2) nằm ngoài bất biến §1 | giai đoạn 2 | **Đã quyết: không có ngoại lệ nhiều lời gọi cho kết quả NT114.** Phân tích tĩnh và kiểm CPU không LLM của code gốc có thể lập kế hoạch riêng; chạy phương pháp nhiều lời gọi gốc cần phạm vi duyệt riêng |
| D9 | Chọn một cải tiến cho MVP (mục 3) | M3 | **Đã quyết: IM1** (khung phụ thuộc dịch vụ lịch sử từ trace vai train để hỗ trợ `no_trace`). IM2-IM4: mở, không triển khai trong MVP. IM1 là giả thuyết cần kiểm, không phải cải tiến đã chứng minh hay mới |
| D10 | Chấp nhận bootstrap độ nhạy theo nhóm split (ba lần lặp của một ô) | M5 | **Đã quyết: chấp nhận.** Bootstrap theo `group_id` của split là phân tích độ nhạy, giữ lặp trong nhóm; ba lần lặp không bao giờ coi là mẫu độc lập; phân tích chính không đổi sang bản thuận lợi hơn |
| D11 | Cho phép khung phụ thuộc không nhãn từ vai train trong quần thể `retrieval = none` (data contract §7.3, `llms.txt` chỉ cho thông tin train qua retrieval/precedent). Nếu từ chối: IM1 không chạy được, và IM2 dùng cách gắn phẳng nút mù (không khung); nếu cho phép: áp cho cả IM1 và biến thể gắn khung của IM2 | IM1, IM2 | **Đã quyết: cho phép có điều kiện** (điều kiện ở [improvement-hypotheses.md](improvement-hypotheses.md) IM1). Là cách dùng thông tin train mới so với data contract hiện hành, nên cần phụ lục data contract có ngày và mã arm tường minh trước khi triển khai; nghĩa của `retrieval = none` không đổi âm thầm. Nhánh "từ chối" ở cột trái: không chọn |
| D12 | Quy tắc niêm phong 21 injection test của RE2-OB cho tới M5. **Đề xuất mặc định:** niêm phong cả tổng gộp 90; kết luận giai đoạn 1-2 và IM4 chỉ công bố sau M5; trước M5 chỉ chẩn đoán từng sự cố trên 48 train + 21 val RE2-OB. **Phương án khác:** chỉ lộ tổng gộp 90, không có kết quả từng sự cố hay từng tập con trên train+val, chẩn đoán trên tập con rời nhau (reproduction-protocol §7) | M1b, M4 | **Đã quyết: niêm phong nghiêm.** Không mở kết quả test RE2-OB nào, kể cả tổng gộp 90, trước M5; phát triển dùng train/val theo vai; phải kiểm lịch sử lộ test và ghi trung thực mọi lần lộ, không mô tả là đã khôi phục tính mù. Phương án khác (chỉ lộ tổng gộp 90): không chọn. **Còn mở:** kiểm lịch sử lộ test |
| D13 | Họ confirmatory có chứa H1 (`gain_exact@0.7` so với C2 trên `single_modality`) hay không, và cách xử lý các ô RE2-SS/`no_trace` (liên quan D3) | M5 | **Đã quyết một phần.** H1 (`gain_exact@0.7` so với C2, SESOI 0.05) vẫn là ứng viên confirmatory chính; họ confirmatory **chưa đóng băng** cho tới khi kiểm lại quần thể, đường `no_trace`, độ tin cậy, công suất/MDE và phụ thuộc; IM1 là thăm dò trong MVP đầu. Ô RE2-SS/`no_trace` xử lý theo D3 |

Tài liệu này không chọn thay chủ dự án ở D2, D3, D4. Cả ba đã được chủ dự án quyết ngày 2026-10-26 (cột trạng thái); các ô còn mở theo chủ dự án: bản TDSC (D5), kiểm lịch sử lộ test (D12), họ confirmatory chưa đóng băng (D13), IM2-IM4, chạy GPU/model.

## 2. Phạm vi tối thiểu

**Một câu:** chạy được code gốc RCLAgent trên RE2-OB (giai đoạn 0-2) và có một adapter đọc bundle NT114 để đo, trên 69 injection có trace của RCAEval, hiệu của bằng chứng theo kiểu RCLAgent so với L0, cộng đúng một cải tiến (mục 3) đối chiếu với falsifier đã định, theo nhánh đã chọn ở D2. Cho tới khi D2 được quyết, chỉ làm M1 và M2 (không phụ thuộc nhánh); M3 trở đi chờ D2, và nhánh (b) chỉ chạy được sau khi chủ dự án sửa protocol v2 §1. **Đã quyết 2026-10-26:** nhánh (a) được chọn nên không sửa protocol v2 §1 và nhánh (b) không chọn. Lượt kế tiếp chỉ lập kế hoạch triển khai và khả thi (D7), không chạy model; "chạy được code gốc RCLAgent" ở giai đoạn 0-2 nay chỉ còn là phân tích tĩnh và kiểm CPU không LLM, có thể lập kế hoạch riêng (D8). Không có lần chạy code gốc có LLM nào được phép.

Không nằm trong MVP: AIOps2022, Nezha/Train-Ticket nguyên bản của bài, backbone Claude, retrieval, fine-tuning, các arm oracle, mọi lần chạy ngoài RCAEval.

## 3. Chọn cải tiến cho MVP

~~Chưa chọn.~~ **Đã quyết 2026-10-26 (D9): chọn IM1**; IM2, IM3, IM4 mở và không triển khai trong MVP. IM1 là giả thuyết cần kiểm, không phải cải tiến đã chứng minh hay mới. Tiêu chí kèm đánh giá thô dưới đây giữ để lưu sử:

| Tiêu chí | IM1 khung tĩnh | IM2 nút mù | IM3 tin cậy từ lời gọi tổng hợp | IM4 nạp trước tool |
|---|---|---|---|---|
| Dùng được ở cả (a) và (b) | có | có | **không** (chỉ (b)) | độc lập nhánh |
| Thêm lời gọi LLM | 0 | 0 hoặc thêm ở (b) | 0 | giảm |
| Chạm quần thể H1 | có (`no_trace`) | không | có | không |
| Công suất thống kê | 69 injection (chưa tính; mốc gần nhất RCA100 n = 70: 0.16 ở d = 20%) | 52 injection (MDE 0.18, không đạt ở d = 10%) | AUROC rộng, thăm dò | 90 sự cố RE2-OB, gốc dữ liệu của bài |
| Cần GPU | có | có | có | có |
| Prior work | chồng lấn một phần (TORAI) | chồng lấn một phần (TORAI) | chưa thấy trong tìm kiếm | chồng lấn một phần |

Quan sát (không phải quyết định): IM1 và IM2 là hai cải tiến duy nhất vừa không thêm lời gọi LLM vừa dùng được ở cả hai nhánh nên không bị chặn bởi D2. IM1 chạm quần thể H1; IM2 có MDE cao hơn.

## 4. Thành phần cần viết thêm, đối chiếu module hiện có

Module trong `nt114-rca/nt114-rca/src/rca/`. "Dùng lại" nghĩa là không sửa; "mở rộng" cần sửa nhỏ và thử lại; "viết thêm" là file hoặc hàm chưa tồn tại.

| Chức năng | Module hiện có | Hành động |
|---|---|---|
| Đọc telemetry vùng visible | `store.py`, `legacy_view.py` (`legacy_telemetry`, `visible_case`) | Dùng lại. Parquet traces có `span_id`, `parent_span_id`, `service_id`, `duration_ns`; logs có `span_id`, `level`; metrics dài |
| Dựng đồ thị trace, chọn trace S-first | không có | Viết thêm (module riêng, ví dụ `rcl_trace_graph`) |
| Tool trace, metric (n-sigma), log, tất định, đọc trực tiếp từ store thay Flask `tool_server` | `evidence.py` (z-score MAD, tóm tắt log/trace) có ý tưởng gần | Viết thêm. Không sửa `evidence.py` (chạy `BUILDER_VERSION = 3`, cache theo fingerprint) |
| Đường xử lý theo telemetry sẵn có (có trace / `no_trace` / không khung), bằng chứng phẳng theo ứng viên (D3) | không có | Viết thêm; quy tắc chọn đường đóng băng trước đánh giá, chỉ dựa trên telemetry sẵn có |
| Builder bằng chứng kiểu RCLAgent cho nhánh (a) | `evidence.build` | Viết thêm, builder riêng, `BUILDER_VERSION` riêng; giữ prompt `v1`, chỉ thay khối `{evidence}` |
| ~~Điều phối nhiều lời gọi cho nhánh (b)~~ (không chọn, D2) | `llm.py` (client, cache, parse, aggregate) | Viết thêm lớp điều phối; tái sử dụng client và cache; thêm bộ prompt cho vai span, hợp nhất, tổng hợp (không sửa `v1`). Cần ghi từng lời gọi vào sổ chi phí |
| Ánh xạ đầu ra sang tập ứng viên, trần top-5, censor | `llm.py` (`schema`, `parse`), `metrics.py` (`RANK_CAP`), `score.py` | Dùng lại |
| Độ tin cậy, abstention | `confidence.py`, `selective.py` | Dùng lại. ~~IM3 thêm nguồn thứ hai `r_conf_root`~~: IM3 mở, không triển khai; độ tin cậy không lấy từ lời gọi LLM thứ hai (D3) |
| Điều kiện thiếu telemetry | `ablate.py`, `run_grid.py` | `ablate.py` dùng lại. `run_grid.py` cần mở rộng: mục tiêu `blind_nonroot_ev` được tính từ văn bản evidence của `evidence.build` (`run_grid.py` dòng 210-259), nên adapter đi vòng `evidence.py` phải tự tính mục tiêu tương đương hoặc tái dùng danh sách đó, kèm test |
| Baseline | `baselines.py`, `baro.py` | Dùng lại |
| Thống kê | `contrasts.py`, `analyze.py`, `reproduce.py` | Dùng lại; thêm bootstrap theo nhóm split (D10 đã chấp nhận, làm độ nhạy) |
| Chi phí | `cost.py` | Mở rộng: số lời gọi mỗi ô, token theo vai |
| Khung IM1 | không có | Viết thêm (IM1 đã chọn; cần phụ lục data contract có ngày trước khi triển khai) |
| Nút mù IM2 | không có | Không làm trong MVP (IM2 mở) |
| Kiểm rò rỉ cho adapter | `tests/test_leakage.py`, `audit.py` | Mở rộng test: hoán vị nhãn, canary, quét import cho các module viết thêm |
| Code gốc để tái hiện | không có | Clone repo ngoài NT114 (commit 3052e7a6), không vendor vào repo; venv riêng. Chỉ cho phân tích tĩnh và kiểm CPU không LLM trong kế hoạch riêng (D8) |

Điểm lệch cần chú ý: evidence của NT114 là văn bản tóm tắt (ví dụ vài dòng mỗi dịch vụ), còn RCLAgent cần đọc span, log, metric thô. Adapter đọc thẳng từ `store.py` ở vùng visible, nên không đi qua `evidence.py`.

## 5. Mốc và cổng

| Mốc | Nội dung | Cổng qua (đo được) | Phụ thuộc |
|---|---|---|---|
| M0 | Chủ dự án quyết D1, D2, D3, D4, D9; mở D6, D7 nếu cần. *Đã quyết 2026-10-26; D6 không cấp, D7 chỉ cho phép lập kế hoạch* | Ghi vào `decisions.md` bởi chủ dự án (agent không tự ghi) | D1 |
| M1 | Giai đoạn 0 của reproduction-protocol: dựng code gốc, chấm mẫu, đếm 90 sự cố và số span (chỉ phân tích tĩnh và kiểm CPU không LLM; kế hoạch riêng, D8) | Quick start chấm đúng 1.0; đếm 90 sự cố; số span ghi vào báo cáo; đọc xong `tool_server.py` | D1 |
| M1b | **Không được phép (D6)**: giai đoạn 1 chạy code gốc, API trả phí, S-best và S-first | Kết luận đạt/một phần/không đạt/không kiểm được theo reproduction-protocol §7, công bố sau M5 (niêm phong) | D5, D6 |
| M2 | Thành phần chung: đồ thị trace, chọn S-first, tool tất định, ánh xạ ứng viên, test rò rỉ | Test pass: tất định (hash đầu ra tool ổn định), hoán vị nhãn, canary, quét import; chưa gọi LLM | M0 |
| M3 | Adapter nhánh đã chọn (a: builder bằng chứng; ~~b: điều phối nhiều lời gọi~~ không chọn) và cải tiến đã chọn (IM1) | Smoke bằng mock trên dữ liệu tổng hợp (không phải kết quả); sổ chi phí ghi đủ số lời gọi | M2, D2, D9 |
| M4 | **Chưa được phép chạy (D7); chỉ lập kế hoạch khả thi**: giai đoạn 2 và feasibility GPU, code gốc với model cục bộ; DEV pilot trên val | Kết luận khả thi theo reproduction-protocol §7; trung vị thời gian mỗi ô và tỉ lệ cắt ngữ cảnh đo được; ước tính d cho MDE; chạy lại V5 với n = 69 | M1, D7 |
| M5 | Đóng băng prompt, builder, ngưỡng, họ confirmatory, hash | `preregistration_sha` ghi; chủ dự án chấp nhận họ confirmatory (protocol v2 §9.5) | M3, M4, D3, D10, D13 |
| M6 | Chạy test một lần theo test-matrix, chạy `analyze` | Bảng `exploratory_` hoặc theo prereg; `reproduce` tái tạo bảng; headline guard qua | M5 |
| M7 | Review bằng ngữ cảnh sạch và báo cáo | Không còn phát hiện chặn | M6 |

Cổng dừng: nếu M4 cho kết luận "không khả thi" ở nhánh (b), MVP chuyển sang nhánh (a) chỉ khi chủ dự án quyết (D2). Nếu nhánh (a) trên model 4-9B không vượt B1m trên DEV, đó là một **quyết định dừng** của M4 (DEV không phải kết quả báo cáo): ghi lý do dừng, không tinh chỉnh vào test, không trích số DEV làm kết quả. *Đã quyết 2026-10-26: nhánh (b) không chọn nên phần chuyển nhánh không còn áp dụng; cổng dừng DEV cho nhánh (a) giữ nguyên và chỉ có hiệu lực khi chủ dự án sau này duyệt chạy model.*

## 6. Cả hai nhánh, cạnh nhau

| | Nhánh (a) — **đã chọn (D2)** | Nhánh (b) — **không chọn** (giữ để lưu sử) |
|---|---|---|
| M2 | giống nhau | giống nhau |
| M3 | Builder bằng chứng cộng một lời gọi tổng hợp. Mất recursion-of-thought (nói rõ trong báo cáo) | Lớp điều phối nhiều lời gọi; **cần chủ dự án sửa protocol v2 §1 trước** |
| Cải tiến khả dụng | IM1, IM2, IM4 (rỗng IM3) | IM1, IM2, IM3, IM4 |
| Rủi ro chi phí trên 12 GB | thấp, 1 lời gọi (n mẫu) mỗi ô | cao, tối thiểu 2 x số span + 1; chưa đo; có thể buộc cắt ngữ cảnh |
| Ý nghĩa kết quả | "bằng chứng theo kiểu RCLAgent có hơn bằng chứng tóm tắt hiện có không" | "RCLAgent chạy trên model cục bộ có hơn L0 không" |
| Chi phí code | thấp đến vừa | vừa đến cao |

## 7. Việc cần kế hoạch nckh-plan riêng

Phase 09 chỉ thiết kế. Các việc sau cần kế hoạch triển khai riêng, sau khi chủ dự án trả lời D1, D2, D9 (đã trả lời 2026-10-26). Kế hoạch kế tiếp chỉ lập kế hoạch triển khai và khả thi, không chạy GPU/model (D7):

1. Triển khai M2 đến M3 (code, test, sổ chi phí) — một plan có phase theo nhánh. *Nhánh (a) và IM1 đã chọn; nhánh (b) không chọn.*
2. ~~Giai đoạn 1 tái hiện bằng API trả phí — phase riêng vì cần quyền chi trả (D6).~~ **Không được phép (D6)**: không API trả phí, không gửi telemetry ra ngoài; không lập thành phase.
3. Probe GPU, feasibility, DEV pilot cho profile 12 GB (M4) — chung với plan single-LLM nếu chủ dự án muốn dùng lại hạ tầng. *Theo D7 chỉ lập kế hoạch khả thi: nêu máy thực tế, model dự kiến, lượng tử hóa, giới hạn bộ nhớ/thời gian và cổng dừng để chủ dự án duyệt sau; không chạy.*
4. Chạy lại V5 với n = 69 và đóng băng họ confirmatory (M5) — thuộc nckh-statistics. *Họ confirmatory chưa đóng băng (D13).*
5. Mở rộng prior work (từ khóa không kèm RCA cho IM3, IM4; đọc toàn văn TORAI, SpecRCA, *Rethinking Tool Design for Agentic RCA*) trước khi viết khẳng định nào về việc chưa ai làm. Có thể dùng Perplexity (tài khoản Pro của chủ dự án) chỉ để tìm nguồn bằng từ khóa, tiêu đề, DOI và mô tả phương pháp công khai; mọi khẳng định vẫn kiểm với bài gốc, repo chính thức hoặc nguồn xếp hạng; không phải phụ thuộc chặn (PR-06).
6. Phân tích tĩnh và kiểm CPU không LLM của code gốc: có thể là kế hoạch riêng (D8); chạy phương pháp nhiều lời gọi gốc cần phạm vi duyệt riêng.

## 8. Rủi ro tổng

- Chỉ 21 injection test cho RE2-OB, 69 cho tập có trace: khoảng tin cậy rộng nên khoảng chứa 0 chỉ là chưa đủ bằng chứng, không phải bác bỏ hay bằng chứng không có hiệu ứng (test-matrix §4).
- Số liệu đích từ arXiv v1; bản TDSC chưa đối chiếu (D5: còn mở, cần trước khi khẳng định khớp bài đã xuất bản).
- 39 injection RE2-SS và 110 injection RE1 nằm ngoài miền xác định của RCLAgent; H1 chỉ được phủ 64% pool theo injection (69/108) và 48% theo bản ghi (138/285). 69/108 là độ phủ của thiết kế dựa trên trace hiện tại, không phải 69 chẩn đoán đúng; thành viên được kiểm lại trước khi cố định mẫu số (D3).
- ~~Nếu D1 không được chấp nhận, toàn bộ phase 09 `stale`.~~ D1 đã được chấp nhận có điều kiện ngày 2026-10-26 nên điều kiện `stale` không xảy ra; điều kiện chấp nhận ở cột trạng thái §1.
- Hai bản ghi OpenAlex trùng của cùng bài (W7165616276 và W7161299676) cần gộp ở phase 10.
