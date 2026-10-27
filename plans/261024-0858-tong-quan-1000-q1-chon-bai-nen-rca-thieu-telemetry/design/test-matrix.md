Đã quyết 2026-10-26: chủ dự án chấp nhận RCLAgent làm bài nền **có điều kiện** (D1, D4), xem [nhật ký quyết định](../../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md). ~~Có điều kiện: chờ chủ dự án chấp nhận bài nền RCLAgent và quyết định ở selection-memo §5.~~ (không còn áp dụng, giữ để lưu sử).

# Ma trận phép thử (phase 09, phiên bản 0.2, 2026-10-26 giờ Việt Nam)

**Thay đổi 0.2 (2026-10-26).** Theo [nhật ký quyết định](../../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md) (D2, D3, D9-D13): nhánh (a) là nhánh đã chọn và R-b không chọn; H1 giữ nguyên quần thể, ca thiếu trace được xử lý chứ không loại; sửa cách đọc kết quả khoảng tin cậy chứa 0 (mục 4); họ confirmatory chưa đóng băng, IM1 thăm dò; bootstrap `group_id` chấp nhận làm độ nhạy; niêm phong test nghiêm hơn; thêm mục 10 (đường không trace, báo cáo theo khả năng áp dụng, độ tin cậy, các arm của IM1). Số liệu MDE và số đếm không đổi.

Chỉ thiết kế, chưa chạy gì. Nền là [protocol v2](../../261018-2300-single-llm-simplification-and-evaluation-hardening/design/protocol-v2.md) (đơn vị độc lập, endpoint, kiểm định, so sánh) và [data contract](../../../nt114-rca/nt114-rca/docs/data_contract.md). Tài liệu này không sửa chúng. Khi chưa có `preregistration_sha`, mọi bảng mang tiền tố `exploratory_` (protocol v2, phần đầu).

## 1. Quy tắc bất biến cho mọi arm

1. **Không đưa nhãn của ca đang hỏi vào prompt, vào đối số tool hay vào đầu ra tool** (`llms.txt`; data contract §7). Adapter chỉ đọc `VisibleCase` và telemetry vùng visible. Tên dịch vụ ứng viên lấy từ `VisibleCase.candidates`, không dùng danh sách cứng theo dataset như `_SYSTEM_PROMPTS["re2ob"]` của code gốc.
2. **Không dùng DEV, mock hay oracle làm kết quả chính.** DEV (vai val) chỉ để chọn siêu tham số và ngưỡng; không bao giờ vào bảng kết quả. Backend mock chỉ chạy smoke. "Hạng tốt nhất qua các trace" (S-best) và mọi arm `no_precedent` là oracle: chỉ xuất hiện ở bảng đối chiếu với bài nền, ghi nhãn rõ, không vào headline; `selective` và headline guard đã từ chối hàng `oracle_store`.
3. **Retrieval = none** cho mọi arm chính (khớp quần thể H1). Arm retrieval, nếu có, là thí nghiệm riêng theo E2. Nghĩa của `retrieval = none` không đổi (D9, D11): arm có khung IM1 dùng thông tin vai train ngoài retrieval/precedent nên cần phụ lục data contract có ngày và mã arm tường minh trước khi triển khai; không đổi nghĩa `retrieval = none` âm thầm.
4. **Khung IM1** chỉ dùng cạnh gọi từ cửa sổ trước anchor của sự cố vai train, cùng hệ thống, không dùng thời lượng, mã lỗi hay nhãn. Điều kiện D11 đầy đủ: [improvement-hypotheses.md](improvement-hypotheses.md) IM1 và mục 10.
5. **Ngưỡng và prompt đóng băng trước test**, ghi hash; tinh chỉnh chỉ trên val; ngoại lệ: chẩn đoán giai đoạn 1-2 của code gốc trên RE2-OB dùng được cả sự cố vai train (48 train + 21 val RE2-OB), vì code gốc không huấn luyện. Mọi thay đổi bằng chứng/prompt đi kèm tăng version (`BUILDER_VERSION`, `PROMPT_VERSION`) để khóa cache.
6. Trần top-5, hạng > 5 bị censor, MRR@5 chỉ ở dạng censor (decisions 2026-10-18). Không báo MRR top-10 trên bundle NT114.
7. Lỗi parse tính là sai và được tabulate riêng.
8. **Chọn trace cho mọi arm trên bundle:** S-first là chính (trace có root span `duration` lớn nhất trong [anchor-60 s, anchor+300 s], hòa thì `trace_id` nhỏ nhất); S-mean (trung bình RR qua tối đa 5 trace, không dùng nhãn) là phụ. S-best chỉ ở bảng đối chiếu bài (reproduction-protocol §7).
9. **Test niêm phong trước M5:** đầu ra và độ chính xác vai test của 21 injection RE2-OB trong giai đoạn 1-2 không được đọc trước khi đóng băng (reproduction-protocol §7). *Đã quyết D12 (2026-10-26): niêm phong nghiêm; không mở kết quả test RE2-OB nào, kể cả tổng gộp 90, trước M5; phát triển dùng train/val theo vai; phải kiểm lịch sử lộ test và ghi trung thực mọi lần lộ, không mô tả là đã khôi phục tính mù.*

## 2. Đơn vị độc lập và quần thể

- Đơn vị: **injection** (`incident_uid` trong RCAEval; trọng số 1 / số bản ghi). Bootstrap theo injection, B = 10,000.
- Quần thể: RCAEval vai test. Đếm riêng (kiểm trên `incidents.jsonl` và `assignments.jsonl` của `within-rcaeval-grouped-0-e9b2c81c`, chỉ đếm):

| Tập con của RCAEval test | Injection | Có đủ metric, log, trace? | Ghi chú |
|---|---:|---|---|
| RE2-OB | 21 | cả ba | quần thể của giai đoạn 3 cho dữ liệu gốc của bài |
| RE2-TT | 18 | cả ba | |
| RE3-TT | 30 | cả ba | |
| **Có trace (tổng)** | **69** | cả ba | RCLAgent xác định được ở đây; khớp 69 của `blind_root` trong protocol v2 §5.1 |
| RE2-SS | 39 | metric và log, **không có trace** (`natural_absent`) | RCLAgent không có xương sống trace ở điều kiện `full` |
| RE1 (OB, SS, TT) | 110 | chỉ metric | RCLAgent không áp dụng |
| Tổng test | 218 | | khớp protocol v2 §5.1 |

Hệ quả: pool H1 `single_modality` có 108 injection (69 có trace cộng 39 RE2-SS); RCLAgent chỉ xác định được trên 69 injection (64% pool). 39 injection RE2-SS dưới mọi điều kiện, và `no_trace` trên 69 injection, là các ô mà bài dự đoán thoái hóa. Hai nhóm này được báo riêng, không gộp. **Đã quyết D3 (2026-10-26):** quần thể H1 không bị thu hẹp cho vừa RCLAgent; các ca thiếu trace dùng đường không trace/không khung (mục 10) và ở lại mẫu số. 69/108 (64%; 138/285 bản ghi, 48%) là độ phủ của thiết kế dựa trên trace hiện tại, không phải 69 chẩn đoán đúng; thành viên của 69 được kiểm lại trước khi cố định mẫu số.

Sự cố RE2-OB trong tập 69 là 21: không đủ để kết luận riêng cho RE2-OB (xem reproduction-protocol §5).

## 3. Điều kiện thiếu telemetry (protocol v2 §5 và §5.1, `run_grid.py`; `blind_nonroot_ev` không có trong bảng điều kiện của data contract §5)

| Điều kiện | Áp dụng cho tập 69 có trace | Mục đích |
|---|---|---|
| `full` | 69 | nền |
| `no_metric`, `no_log` | 69 (còn trace) | pool H1 |
| `no_trace` | 69 | điều kiện bài dự đoán thoái hóa; đích của IM1 |
| `blind_root` | 69 (khi gốc có span) | đích của IM2 |
| `blind_nonroot_ev` | theo ma trận điều kiện | đối chứng của IM2 |
| giao `blind_root` và `blind_nonroot_ev` | 52 (toàn RCAEval test, protocol v2 §5.1) | MDE lớn; xem mục 4 |

Điều kiện của cùng một sự cố là biến thể của một mẫu, so sánh ghép cặp trên cùng sự cố (`pair_id`).

Lưu ý hiện vật của toán tử che: `ablate.mask_service_traces` chỉ bỏ span của dịch vụ bị che; span của bên gọi và span con mồ côi còn lại. Mọi kết quả `blind_*` mang theo bảng số ứng viên mù theo từng điều kiện (cần cho IM2).

## 4. Điểm cuối, kiểm định, MDE

**Endpoint** (protocol v2 §2, không đổi): AC@1..5, MRR@5 censor; chất lượng tin cậy (Brier, ECE, overconfidence gap, AUROC/AUPRC phát hiện lỗi); selective (AURC, rủi ro ở coverage 0.5/0.7/0.9, gain_exact@0.7 so với C2); chi phí (token, **số lời gọi mỗi ô**, độ trễ LLM, giây chuẩn bị, giây đầu-cuối); strata (`named`, `same_as_full`, dữ liệu, điều kiện, nhóm coverage).

**Kiểm định** (đã có trong `contrasts.py`, `analyze.py`): khoảng tin cậy bootstrap cụm theo injection, phân vị 95%; kiểm hoán vị sign-flip ghép cặp (10,000 lần); Holm trong từng họ đã khai báo; giao ghép cặp chỉ trên các sự cố mà cả hai arm áp dụng; báo kèm bản `require_changed`. Tập dưới 100 injection: khoảng tin cậy phân vị có thể hơi hẹp (research/06, V4: độ phủ 0.930 ở n = 52).

**MDE** (research/06, V5; đây là AC@1 ghép cặp, hai phía, công suất 80%, chưa hiệu chỉnh Holm):

| Tập | d = 10% | d = 20% | d = 30% |
|---|---:|---:|---:|
| RCAEval test `full` (218) | 0.08 | 0.10 | 0.12 |
| giao `blind_root` và `blind_nonroot_ev` (52) | không đạt được | 0.18 | 0.22 |
| Nezha test `full` (97) | 0.10 | 0.14 | 0.18 |
| RCA100 test `full` (86 bản ghi, 70 injection; mốc đo gần n = 69 nhất) | 0.10 | 0.16 | 0.18 |
| **69 injection có trace** | chưa tính | chưa tính; dùng mốc RCA100 (n = 70) làm tham chiếu | chưa tính |

Dòng 69 **chưa chạy công cụ**; mốc đo gần nhất là RCA100 n = 70 (research/06 V5). Cần chạy lại bước V5 với n = 69 trước khi đóng băng họ confirmatory. Tỉ lệ bất đồng d chỉ là giả định cho tới khi có DEV pilot. Holm làm MDE cao hơn. Hệ quả: chỉ hiệu ứng cỡ 0.15 điểm tuyệt đối trở lên phát hiện được trên 69 injection, nên kết quả có khoảng tin cậy chứa 0 chỉ có nghĩa "chưa đủ bằng chứng về hiệu ứng từ cỡ MDE trở lên": đó không phải bác bỏ giả thuyết và không phải bằng chứng không có hiệu ứng (quy ước đọc ngay dưới). AUROC (IM3) trên cỡ này có khoảng tin cậy rộng (chưa tính).

**Quy ước đọc khoảng tin cậy và falsifier (2026-10-26, D13).** Khoảng tin cậy 95% chứa 0 nghĩa là bằng chứng chưa đủ để kết luận có hiệu ứng; không phải bác bỏ và không phải bằng chứng không có hiệu ứng. Mọi kết luận phân biệt ba trường hợp: (i) không phát hiện hiệu ứng (khoảng chứa 0, chưa đủ bằng chứng); (ii) bằng chứng có hại (khoảng nằm hoàn toàn dưới 0); (iii) bằng chứng loại trừ hiệu ứng có ý nghĩa thực tiễn (khoảng nằm hoàn toàn trong ±SESOI hoặc dưới ngưỡng SESOI, SESOI = 0.05 điểm tuyệt đối). Chỉ (iii) cho phép viết "không có hiệu ứng đáng kể"; với n quanh 69 điều này hiếm khi đạt.

**Họ confirmatory (đã quyết một phần 2026-10-26, D13):** H1 (`gain_exact@0.7` so với C2, SESOI 0.05) vẫn là ứng viên confirmatory chính; họ **chưa đóng băng** cho tới khi kiểm lại quần thể, đường `no_trace`, độ tin cậy, công suất/MDE và phụ thuộc giữa các tương phản; IM1 là thăm dò trong MVP đầu. Đề xuất ban đầu giữ để lưu sử (protocol v2 §9.5 vẫn là ô để mở): tối đa ba tương phản (C-1, C-2, C-3), còn lại là thăm dò.
- C-1: arm RCLAgent theo nhánh đã chọn so với L0, AC@1, tập 69, điều kiện `full`, ghép cặp.
- C-2: arm cải tiến được chọn so với arm RCLAgent nền, AC@1, trên điều kiện đích của cải tiến. *Theo D13, IM1 là thăm dò trong MVP đầu nên C-2 chạy ở dạng thăm dò (`exploratory_`) cho tới khi họ được đóng băng.*
- C-3 (H1, hướng chính): `gain_exact@0.7` so với C2 (hoãn ngẫu nhiên) cho arm RCLAgent đã chọn, trên pool `single_modality`, `retrieval = none`. RCLAgent chỉ xác định trên 69 trong 108 injection của pool (64%; 138 trong 285 bản ghi, 48%); 39 injection RE2-SS không có trace ở mọi điều kiện, và ô `no_trace` suy biến. ~~Cách tính các ô đó (loại, gán là sai, hay chạy dự phòng không trace) phụ thuộc D3 và được ghi như một phân tích tách riêng; nếu họ confirmatory không chứa H1 thì đó là quyết định của chủ dự án.~~ **Đã quyết D3/D13:** các ô đó không bị loại và không bị gán là sai; chạy đường không trace/không khung theo mục 10 và ở lại mẫu số; H1 là ứng viên confirmatory chính.

Khoảng tin cậy theo cụm có thể quá hẹp vì ba lần lặp của một ô lỗi (cùng `fault_cell`, cùng một nhóm split) tương quan. Phân tích độ nhạy đề xuất, không phải thay đổi protocol: bootstrap thêm theo `group_id` của split. **Đã quyết D10 (2026-10-26):** chấp nhận bootstrap theo `group_id` làm phân tích độ nhạy, giữ lặp trong nhóm; ba lần lặp không bao giờ coi là mẫu độc lập; phân tích chính không đổi sang bản thuận lợi hơn.

## 5. Arm và comparator

| ID | Arm | Lời gọi mỗi ô | Nhãn? | Ghi chú |
|---|---|---|---|---|
| B0 | Ngẫu nhiên (1/số ứng viên) | 0 | không | giải tích |
| B1 | max-z metric | 0 | không | `baselines.py` |
| B1m | Thứ tự bằng chứng | 0 | không | `baselines.py` |
| B2 | BARO-style | 0 | không | có điều kiện: chưa đổi tên cho tới khi qua kiểm tương đương; BARO thắng bài ở R@3, R@5 trên RE2-OB (Table I) |
| L0 | LLM một lời gọi, bằng chứng tóm tắt hiện có, prompt `v1` | 1 (n mẫu) | không | baseline chính của protocol v2 |
| L1 | LLM tự bỏ phiếu abstain | 1 | không | `abstain_vote >= 0.5` |
| R-orig | **Code gốc RCLAgent** + LLM cục bộ, đọc dữ liệu gốc RE2-OB | nhiều | không | chỉ ở giai đoạn 2; bảng tái hiện riêng, không phải headline; **chạy có LLM chưa được phép** (D6, D7, D8) |
| R-a | Nhánh (a): bằng chứng từ tool tất định, một lời gọi tổng hợp | 1 (n mẫu) | không | nhánh đã chọn (D2) |
| R-b | Nhánh (b): pipeline nhiều lời gọi trên một model | tối thiểu 2 x số span + 1 | không | **không chọn (D2)**: không chạy; giữ để lưu sử |
| R-x + IMk | R-a hoặc R-b cộng cải tiến IM1..IM4 | như R-x | không | cải tiến MVP đã chọn: IM1 (D9); IM2-IM4 mở, không triển khai |
| C1, C2, C3 | Ngưỡng coverage khớp; hoãn ngẫu nhiên; ngưỡng fit DEV | theo arm | C3: nhãn DEV | selective evaluator hiện có |
| O | Oracle (cận trên phân tích) | n/a | có | không là kết quả chính |

ARMOR (ASE 2026, W7141399328), RCA không dùng LLM cho trường hợp thiếu modality, được selection-memo §6 ghi là comparator đáng xem; chưa đọc, chưa đưa vào ma trận.

Câu hỏi chính của so sánh: cùng một LLM và cùng cửa sổ dữ liệu, bằng chứng từ tool theo kiểu RCLAgent có hơn bằng chứng tóm tắt hiện có (L0) không, và hơn B1/B1m/B2 không. Quy tắc đặc biệt: L0 và R-x dùng cùng model, cùng trần top-5, cùng schema đầu ra.

## 6. Lưới thí nghiệm

| Khối | Arm | Điều kiện | Tập | Mục đích |
|---|---|---|---|---|
| G1 | R-orig | không có (dữ liệu gốc) | 90 sự cố RE2-OB | giai đoạn 2, khả thi |
| G2 | B0, B1, B1m, L0, L1, R-x | `full` | 69 có trace; tách riêng RE2-SS (39) và RE1 (110) như phần mô tả | so sánh chính C-1 |
| G3 | L0, R-x, R-x + IM1 | `no_metric`, `no_log`, `no_trace` | 69 | H1 tương tác; IM1 |
| G4 | L0, R-x, R-x + IM2 | `blind_root`, `blind_nonroot_ev` | giao 52 | IM2 |
| G5 | R-b, R-b + IM3 | `full` và pool | 69 | IM3, chỉ khi nhánh (b) |
| G6 | R-orig, R-orig + nạp trước (IM4) | không có | 90 RE2-OB | IM4 ở giai đoạn 2 |

Mỗi khối ghi cùng một bảng chi phí.

Trạng thái 2026-10-26: G2 và G3 là khối của MVP (G3 chia theo các arm của IM1, mục 10). G1 và G6 cần chạy code gốc có LLM nên chưa được phép (D6, D7, D8). G5 chỉ thuộc nhánh (b), không chọn. G4 (IM2) và IM3, IM4 mở, không triển khai.

## 7. Quy tắc DEV -> test

1. Vai val của `within-rcaeval-grouped` (RE2-OB: 21 injection, cộng RE2-TT, RE3 và RE1) dùng để: chọn n-sigma, độ rộng cửa sổ metric, trần độ dài bằng chứng, ngưỡng abstention (C3); đo tỉ lệ bất đồng d cho MDE.
2. Mọi tham số, prompt, builder, hash đóng băng và ghi trước khi chạy test. Đầu ra vai test của giai đoạn 1-2 (21 injection RE2-OB) niêm phong cho đến sau bước này; tinh chỉnh giai đoạn 1-2 dùng 48 train + 21 val RE2-OB; tổng gộp 90 cũng niêm phong và kết luận giai đoạn 1-2 và IM4 (khối G1, G6) công bố sau M5. Theo D12, không có kết quả test RE2-OB nào (kể cả tổng gộp 90) được mở trước M5.
3. Chạy test một lần cho mỗi cấu hình đã đóng băng; không chỉnh sau khi thấy test. Dòng DEV không vào bảng báo cáo.
4. Ngưỡng fit DEV chuyển sang test theo đúng phân tầng nguồn -> đích của protocol v2 §9.

## 8. Ngân sách

Chưa đo gì, nên các con số dưới đây là công thức và ngưỡng dừng đề xuất, không phải ước lượng.

| Khoản | Công thức hoặc trạng thái |
|---|---|
| Số ô test | Khoảng (69 x 6 điều kiện) + RE2-SS 39 x (điều kiện áp dụng) cho mỗi arm; con số cuối sau khi đếm ô áp dụng |
| Nhánh (a) | 1 lời gọi x n mẫu mỗi ô (n = 10 theo hardware profile); tiền tố prompt dài khoảng 2k đến 3.5k token (`MAX_CHARS` 14,000) |
| Nhánh (b) | Tối thiểu (2 x số span + 1) lời gọi mỗi ô, nhân n nếu lấy mẫu cả pipeline. **Số span RE2-OB chưa đếm**, đếm ở giai đoạn 0. Bài báo 41-60 s mỗi truy vấn qua API với song song đến khoảng 200 lời gọi (selection-memo §5 điểm 5); trên một GPU 12 GB chưa ước lượng |
| Giai đoạn 1 | Chi phí API chưa biết: bài không công bố token hay tiền (C6). ~~Cần chủ dự án đặt trần~~ Không được phép (D6): không API trả phí, không gửi telemetry ra ngoài |
| Ngưỡng dừng đề xuất | Dừng nhánh (b) trên profile 12 GB nếu trung vị thời gian mỗi ô ở DEV pilot vượt mức chủ dự án đặt, hoặc nếu `max_model_len` 8192 buộc cắt Global Evidence Graph ở hơn 10% ô |
| GPU | Phải probe GPU và feasibility trước (llms.txt); quyết định CPU-only hiện hành phải được chủ dự án mở trước mọi lần chạy model thật. Theo D7, lượt kế tiếp không chạy GPU/model; kế hoạch nêu máy thực tế, model dự kiến, lượng tử hóa, giới hạn bộ nhớ/thời gian và cổng dừng để duyệt sau |

## 9. Kiểm tra bắt buộc trước khi tin kết quả

- Hoán vị nhãn: đầu ra tool, bằng chứng, prompt không đổi.
- Canary nhãn không xuất hiện trong prompt, đối số tool, đầu ra tool.
- Quét import: adapter không import `visibility`, `baselines`, `analyze`, `confidence`, `contrasts`, `selective`, `alignment`, `leakage_audit`.
- Tabulate tỉ lệ lỗi parse, tỉ lệ danh sách hợp lệ, số lời gọi mỗi ô và `exec_sig` duy nhất cho mỗi cấu hình.
- Khung IM1: hoán vị nhãn của train không đổi khung; khung chỉ dùng cửa sổ trước anchor.
- Kiểm `same_as_full` và `named` cho mọi tương phản điều kiện.
- Lịch sử lộ test được kiểm và ghi trung thực (D12); không mô tả lần lộ nào là đã khôi phục tính mù.
- Mẫu số: không ca nào bị loại âm thầm; bảng tách không áp dụng, lỗi thực thi và dự đoán sai (mục 10).

## 10. Bổ sung theo quyết định 2026-10-26 (D3, D9, D11, D13)

Mục này thêm, không thay các mục trên. Nguồn: [nhật ký quyết định](../../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md).

### 10.1 Quần thể H1 và đường xử lý

- Quần thể H1 (pool `single_modality`: `no_metric`, `no_log`, `no_trace`, và các hệ của nó) không bị thu hẹp cho vừa RCLAgent.
- Đường có trace: R-a như mục 5. Đường không trace (`no_trace`, và 39 RE2-SS không có trace): tool metric và log tất định, bằng chứng phẳng theo từng ứng viên, đúng một lời gọi tổng hợp.
- Quy tắc chọn đường chỉ dựa trên telemetry sẵn có của ca và được đóng băng trước đánh giá; không dựa trên nhãn, đáp án hay chất lượng đầu ra.
- Không có khung lịch sử hợp lệ cho một hệ hoặc split: dùng đường không khung đã khai báo trước. Các ca đó ở lại mẫu số; không loại âm thầm.

### 10.2 Báo cáo theo khả năng áp dụng và theo hệ

- Mọi bảng tách theo hệ và theo khả năng áp dụng (có trace / không trace / không khung).
- Ba loại kết quả không gộp: **không áp dụng**, **lỗi thực thi** (gồm lỗi parse, mục 1.7), **dự đoán sai**.

### 10.3 Độ tin cậy

Theo protocol hiện hành; không bao giờ lấy từ lời gọi LLM thứ hai; độ tin cậy tự khai bằng lời và logprob token không được giả định là hợp lệ. Vì vậy mọi nhãn "độ tin cậy lấy từ lời gọi tổng hợp" (đường IM3) phải đọc là: không thuộc MVP, mở, và nếu mở lại phải viết lại để không dựa trên lời gọi LLM thứ hai (improvement-hypotheses IM3).

### 10.4 Các arm của IM1

| Arm | Nội dung | Vai trò |
|---|---|---|
| Arm có khung | R-a cộng khung IM1; mã arm tường minh, chốt trong phụ lục data contract có ngày trước khi triển khai | arm thử nghiệm (thăm dò, D13) |
| Đối chứng không khung | cùng pipeline, đường không khung | đối chứng của IM1 |
| Khung xáo cạnh | cùng pipeline, cạnh của khung bị xáo | kiểm cơ chế |
| Arm H1 hiện có | arm H1 đang dùng (`retrieval = none`, không khung) | giữ để so sánh |

H1 được báo riêng cho arm có khung. Khung dựng theo điều kiện D11: chỉ cửa sổ trước anchor và các trường cần cho cạnh; không nhãn, loại lỗi hay telemetry val/test; theo từng hệ và split; đóng băng trước val/test; có kiểm rò rỉ.
