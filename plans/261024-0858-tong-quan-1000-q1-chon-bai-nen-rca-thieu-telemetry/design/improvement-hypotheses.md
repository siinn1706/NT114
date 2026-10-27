Đã quyết 2026-10-26: chủ dự án chấp nhận RCLAgent làm bài nền **có điều kiện** (D1, D4), xem [nhật ký quyết định](../../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md). ~~Có điều kiện: chờ chủ dự án chấp nhận bài nền RCLAgent và quyết định ở selection-memo §5.~~ (không còn áp dụng, giữ để lưu sử).

# Giả thuyết cải tiến trên RCLAgent (phase 09, phiên bản 0.2, 2026-10-26 giờ Việt Nam)

**Thay đổi 0.2 (2026-10-26).** Theo [nhật ký quyết định](../../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md) (D2, D9, D11, D13): IM1 được chọn cho MVP như một giả thuyết cần kiểm (không phải cải tiến đã chứng minh hay mới), kèm các điều kiện D11; IM2, IM3, IM4 mở và không triển khai; IM3 không được dựa trên lời gọi LLM thứ hai; mọi câu falsifier được viết lại theo quy ước đọc khoảng tin cậy chứa 0 (mục 1). Phát biểu, cơ chế và phần prior work giữ nguyên.

Chỉ thiết kế. Các giả thuyết là dự đoán có thể kiểm định, chưa có kết quả nào. Không giả thuyết nào sửa protocol v2. *Đã quyết 2026-10-26: nhánh (a) giữ bất biến một lời gọi (D2); H1 giữ nguyên (D3); chọn IM1 (D9). Các chỗ "quyết định mở" bên dưới về H1, bất biến một lời gọi và D11 nay đã quyết, ghi ở từng giả thuyết.*

## 1. Nguồn của các giả thuyết

Mỗi giả thuyết xuất phát từ một giới hạn đã quan sát (card T3, `work/t3/W7165616276-evidence.csv`, quan sát tĩnh `coordinator.py` ở commit 3052e7a6) hoặc từ lớp đo của NT114.

| Giới hạn quan sát được | Locator | Giả thuyết |
|---|---|---|
| Không có trace thì RCLAgent thoái hóa thành agent ReAct, tốn hơn và có thể kém chính xác hơn | Bài §VI (1); selection-memo §5 điểm 2 | IM1 |
| Span mù (không có instrumentation, bị lấy mẫu mất) làm agent dừng ở triệu chứng thượng nguồn hoặc quy lỗi cho dịch vụ lân cận | Bài §VI (2) | IM2 |
| Độ tin cậy `r_conf_root` nằm trong lời gọi Root-Level Report, danh sách nằm trong lời gọi Synthesizer | Bài §IV-C.1, Eq. 7b; `coordinator.py` `consolidate` và `print_results`; selection-memo §5 điểm 2 | IM3 |
| Hiệu năng phụ thuộc mạnh vào backbone; model 70B mở chỉ đạt MRR 7-19; chưa thử model dưới 32B; tool do LLM chọn qua function calling | Table III, §V-D; C8; `self_state_verification` | IM4 |

**Quy ước đọc falsifier (2026-10-26, D13).** Khoảng tin cậy 95% chứa 0 nghĩa là bằng chứng chưa đủ để kết luận có hiệu ứng; không phải bác bỏ giả thuyết và không phải bằng chứng không có hiệu ứng. Mỗi falsifier dưới đây phân biệt: (i) không phát hiện hiệu ứng (khoảng chứa 0, chưa đủ bằng chứng); (ii) bằng chứng có hại (khoảng nằm hoàn toàn dưới 0); (iii) bằng chứng loại trừ hiệu ứng có ý nghĩa thực tiễn (khoảng nằm hoàn toàn trong ±SESOI hoặc dưới ngưỡng SESOI, SESOI = 0.05). Chỉ (iii) cho phép viết "không có hiệu ứng đáng kể". "Không được ủng hộ" trong tài liệu này luôn nghĩa là (i) hoặc (ii), chưa bao giờ nghĩa là đã bị bác bỏ.

Ký hiệu H1 trong tài liệu này là H1 của chủ dự án: hướng chính, giảm selective risk khi thiếu telemetry, SESOI = 0.05 điểm tuyệt đối so với C2 ở coverage 0.7, trên pool `single_modality` của RCAEval với `retrieval = none` (`decisions.md`, 2026-10-19). Câu 4 (thiếu telemetry so với mất ở bước tóm tắt) là thứ cấp so với H1 (`decisions.md`, 2026-10-20).

## 2. Bốn giả thuyết

### IM1. Khung phụ thuộc tĩnh thay cho trace bị thiếu

- **Trạng thái 2026-10-26: được chọn cho MVP (D9), như một giả thuyết cần kiểm.** Không phải cải tiến đã được thiết lập và không khẳng định là mới (prior work ở mục 3 chỉ là tìm kiếm hạn chế). Là thăm dò trong MVP đầu (D13).

- **Phát biểu.** Khi điều kiện `no_trace`, thay đồ thị trace bằng một khung phụ thuộc dịch vụ tĩnh (chỉ gồm cạnh gọi người gọi -> người được gọi) học từ cửa sổ **trước anchor** của các sự cố vai train cùng hệ thống, rồi chạy tool metric và log theo khung đó, thì AC@1 và AC@3 cao hơn cấu hình `no_trace` không khung và cao hơn L0. **Cấu hình không khung (đối chứng) được định nghĩa và đóng băng trước khi chạy, theo nhánh:** ở (a), bằng chứng tool phẳng theo từng ứng viên (chạy tool metric và log cho mọi ứng viên, không có đồ thị); ~~ở (b), hành vi thoái hóa ReAct mà bài mô tả (§VI (1)), tức agent tự gọi tool metric và log không có hướng dẫn đồ thị~~ (nhánh (b) không chọn). Theo D2/D9, đối chứng là cùng pipeline ở đường không khung, và có thêm khung xáo cạnh làm kiểm cơ chế.
- **Cơ chế.** Khung khôi phục "xương sống" mà bài nói là cái RCLAgent cần. Nó không dùng thời lượng, mã lỗi hay nhãn, chỉ dùng sự tồn tại của cạnh trong giai đoạn bình thường. Tool vẫn tất định.
- **Dự đoán phân biệt.** (i) Cải thiện ở `no_trace` so với đối chứng không khung (ở `full` giả thuyết không dự đoán gì vì khung không được dùng, nên không tính là bằng chứng), (ii) khung thật hơn khung bị **xáo ngẫu nhiên** cạnh (kiểm cơ chế, mục dưới), (iii) mô tả: cải thiện tập trung ở các sự cố mà gốc không phải lá của khung.
- **Falsifier.** Giả thuyết **không được ủng hộ** nếu, trên các injection có trace của vai test, hiệu AC@1 ghép cặp (IM1 trừ cùng pipeline không khung) ở `no_trace` có khoảng tin cậy 95% chứa 0 (chưa đủ bằng chứng; không phải bác bỏ và không phải bằng chứng không có hiệu ứng) hoặc nằm hoàn toàn dưới 0 (bằng chứng có hại), **hoặc** hiệu so với L0 ở `no_trace` rơi vào cùng hai trường hợp. Chỉ khi cả khoảng nằm trong ±0.05 hoặc dưới ngưỡng này mới là bằng chứng loại trừ hiệu ứng có ý nghĩa thực tiễn. Vì MDE lớn (test-matrix, mục 4), khoảng chứa 0 chỉ có nghĩa "chưa đủ bằng chứng về hiệu ứng từ cỡ MDE trở lên".
- **Kiểm cơ chế (báo cáo, không phải falsifier).** So khung thật với khung xáo cạnh. Chỉ khi khoảng tin cậy 95% của hiệu AC@1 nằm hoàn toàn trong ±0.05 thì được viết "cải thiện không do cấu trúc"; với 69 injection điều này khó đạt, nên kết quả thường là "không phân biệt được", không phải "tương đương".
- **Chi phí.** Thấp. CPU, thêm phần dựng khung từ Parquet train (chỉ các cột `service_id`, `parent_span_id`, `span_id` trong cửa sổ trước anchor). Không thêm lời gọi LLM.
- **Rủi ro rò rỉ và điều kiện D11 (đã quyết 2026-10-26).** Khung dùng dữ liệu vai train trong quần thể `retrieval = none`; data contract §7.3 và `llms.txt` chỉ cho thông tin train đi vào qua retrieval/precedent. ~~Có cho phép hay không là quyết định của chủ dự án.~~ Chủ dự án cho phép cấu trúc không nhãn từ vai train về nguyên tắc, với các điều kiện: (1) chỉ cửa sổ trước anchor và các trường cần để dựng cạnh; (2) không nhãn, không loại lỗi, không telemetry val/test để dựng hay tinh chỉnh khung; (3) dựng riêng cho từng hệ và split, đóng băng trước val/test; (4) có kiểm rò rỉ (kể cả hoán vị nhãn của train không đổi khung); (5) có đối chứng không khung cùng pipeline; (6) có kiểm cơ chế bằng khung xáo cạnh; (7) có đường không khung khai báo trước khi không có khung hợp lệ. Đây là cách dùng thông tin train mới so với data contract hiện hành: cần phụ lục data contract có ngày và mã arm tường minh trước khi triển khai; nghĩa của `retrieval = none` không đổi âm thầm; arm H1 hiện có giữ để so sánh và H1 được báo riêng cho arm có khung. Giả định hiệu lực ngoài: khung chỉ có ý nghĩa nếu trace từng có sẵn trong lịch sử nhưng vắng lúc xảy ra sự cố.
- **Quan hệ với H1.** *Độc lập, có tương tác.* H1 đo selective risk, còn IM1 đổi tỉ lệ lỗi nền ở `no_trace` (một trong ba điều kiện của pool H1). Tỉ lệ lỗi nền thấp hơn có thể thu hẹp hoặc đổi chỗ mà abstention cứu được, nên phải báo H1 cho từng arm. Không xung đột với protocol v2.
- **Điều kiện nhánh.** Dùng được ở cả (a) và (b); nhánh (a) đã chọn (D2).

### IM2. Nút mù: đưa dịch vụ không có span vào bằng chứng như nút tường minh

- **Trạng thái 2026-10-26: mở, không triển khai trong MVP (D9).** Nội dung dưới đây giữ nguyên để lưu sử.

- **Phát biểu.** Với các ứng viên không có span nào trong trace được chọn (mù), chạy tool metric và log theo tên dịch vụ và anchor, rồi đưa kết quả vào bằng chứng như các nút "không quan sát được trong trace" (gắn vào người gọi theo khung IM1 nếu có, nếu không thì gắn phẳng). Dưới `blind_root`, gốc thật bị mất span nhưng vẫn còn metric và log, nên hạng của gốc cải thiện và tỉ lệ quy lỗi sang dịch vụ lân cận giảm.
- **Cơ chế.** Bài nói agent đi theo topology quan sát được nên dừng ở hàng xóm. Nút mù cho phép bằng chứng của dịch vụ vắng mặt trong trace vào Global Evidence Graph.
- **Dự đoán phân biệt.** (i) Cải thiện ở `blind_root`, (ii) **không** cải thiện ở đối chứng `blind_nonroot_ev` (nếu cải thiện cả ở đó thì cơ chế chỉ là "thêm bằng chứng nói chung"), (iii) tỉ lệ top-1 là hàng xóm trong khung của gốc giảm, (iv) mô tả (không phải kiểm cơ chế): báo hiệu ứng tách theo stratum `named` theo phân tích P1 của câu 4; P1 chỉ cho biết lỗi rơi ở đâu, không cho biết nguyên nhân.
- **Falsifier.** Điểm cuối chính là AC@1 (thống nhất với họ confirmatory và MDE); AC@3 là điểm cuối phụ mô tả, vì quy lỗi sang hàng xóm có thể đẩy gốc xuống hạng 2-3 thay vì ra ngoài danh sách. Không được ủng hộ (theo quy ước đọc falsifier ở mục 1: khoảng chứa 0 là chưa đủ bằng chứng, không phải bác bỏ; khoảng dưới 0 là bằng chứng có hại) nếu trên giao `blind_root` và `blind_nonroot_ev` (52 injection ở vai test), hiệu AC@1 ghép cặp (IM2 trừ không IM2) có khoảng tin cậy 95% chứa 0 hoặc nằm dưới 0, **hoặc** hiệu ở `blind_nonroot_ev` không nhỏ hơn hiệu ở `blind_root` (chênh hai hiệu có khoảng tin cậy chứa 0, chưa đủ bằng chứng về khác biệt, hoặc nghiêng về nonroot), **hoặc** tỉ lệ quy lỗi sang hàng xóm không giảm (không phát hiện giảm), **hoặc** (kiểm hiện vật của toán tử che) dưới `blind_nonroot_ev` tỉ lệ top-1 trùng dịch vụ non-root bị che **tăng** khi có IM2 (khoảng tin cậy ghép cặp nằm trên 0, bằng chứng của hiện vật). Lý do: `ablate.mask_service_traces` (`ablate.py` dòng 22-28) chỉ bỏ span của dịch vụ bị che; span của bên gọi và các span con mồ côi vẫn còn, nên "nút mù" có thể chỉ làm lộ dấu vết của chính phép che chứ không sửa mù thật. Cấu trúc span mồ côi là hiện vật của toán tử che, không phải tính chất của dịch vụ mù thật. Phải tabulate số ứng viên mù theo từng điều kiện. Chú ý MDE của giao 52 là 0.18 ở discordance 20% và không đạt ở 10% (research/06), nên giả thuyết này chỉ phát hiện được hiệu ứng lớn; khoảng chứa 0 ở đây không phải bằng chứng không có hiệu ứng.
- **Chi phí.** Thấp đến vừa. Tối đa 12 ứng viên mỗi ô, chạy tool bằng code; thêm độ dài bằng chứng (kiểm giới hạn `MAX_CHARS` 14,000 của builder hiện có). Không thêm lời gọi LLM ở nhánh (a); ở nhánh (b) có thể thêm một agent mỗi nút mù.
- **Giới hạn của phép đo.** `blind_root` của NT114 chỉ xóa span của gốc, không xóa metric và log của gốc. Dịch vụ mù thật có thể mất cả ba. Do đó giả thuyết kiểm "nút mù khi metric và log còn", không kiểm mù hoàn toàn.
- **Quan hệ với H1.** *Độc lập* với H1 (pool H1 không chứa `blind_root`). Liên quan câu 4 thứ cấp qua stratum `named`.
- **Điều kiện nhánh.** Dùng được ở (a) và (b).

### IM3. Độ tin cậy lấy từ chính lời gọi tổng hợp

- **Trạng thái 2026-10-26: mở, không triển khai trong MVP (D9).** Theo D3, độ tin cậy theo protocol hiện hành, không bao giờ từ lời gọi LLM thứ hai; độ tin cậy tự khai bằng lời và logprob token không được giả định là hợp lệ. Phát biểu dưới đây (so nguồn `r_conf_root` với lời gọi Synthesizer ở nhánh (b)) dựa trên pipeline nhiều lời gọi nên **không còn áp dụng ở nhánh (a) đã chọn**; nếu mở lại phải viết lại để không dựa trên lời gọi LLM thứ hai. Văn bản gốc giữ để lưu sử.

- **Phát biểu.** Trong pipeline nhiều lời gọi (nhánh (b)), đặt độ tin cậy và abstention lên đầu ra của **lời gọi Synthesizer** (n mẫu: đồng thuận và tự khai của các mẫu, theo registry `confidence.py`) thay cho `r_conf_root` từ Root-Level Report, thì chất lượng phát hiện lỗi (AUROC, lớp dương là câu trả lời sai) không thấp hơn quá 0.05 so với `r_conf_root`, và selective risk ở coverage 0.7 không tệ hơn.
- **Cơ chế.** Một quy tắc abstention chỉ hợp lệ theo protocol v2 §1 nếu nó là quy tắc tất định trên đầu ra của cùng lời gọi tạo ra câu trả lời. Chuyển nguồn tin cậy về lời gọi tổng hợp sửa điểm 2 của selection-memo §5 mà không đổi H1.
- **Dự đoán phân biệt.** AUROC của độ đồng thuận lời gọi tổng hợp >= AUROC của `r_conf_root` - 0.05, trên cùng ô.
- **Falsifier.** Không chứng minh được "không kém hơn" (chưa đủ bằng chứng; không phải bác bỏ) nếu cận dưới của khoảng tin cậy 95% (bootstrap theo injection) của hiệu AUROC (lời gọi tổng hợp trừ `r_conf_root`) nhỏ hơn -0.05, hoặc cận trên của hiệu selective risk tại coverage 0.7 (nguồn tổng hợp trừ `r_conf_root`) lớn hơn 0.05 theo cùng khoảng tin cậy. Nếu cả khoảng nằm dưới -0.05 (AUROC) hoặc trên +0.05 (selective risk) thì đó là bằng chứng có hại. Với khoảng 69 injection có trace, khoảng tin cậy của AUROC rộng (chưa tính); kết luận chủ yếu là thăm dò, mang tiền tố `exploratory_`.
- **Chi phí.** Không thêm lời gọi LLM ngoài n mẫu của lời gọi tổng hợp (đã là mặc định `n_samples: 10`); cần sửa code để xuất độ tin cậy ở cả hai nguồn.
- **Điều kiện nhánh.** **Chỉ có nghĩa ở nhánh (b)** (và trên code gốc ở giai đoạn 1-2, nơi `r_conf_root` tồn tại). Ở nhánh (a), độ tin cậy vốn đã lấy từ lời gọi duy nhất nên không có đối chứng "lời gọi riêng"; giả thuyết rỗng ở nhánh đó.
- **Quan hệ với H1.** *Hỗ trợ.* ~~Đây là điều kiện để RCLAgent đạt `h1-compat` mà không sửa H1, tương ứng với lựa chọn thứ ba của selection-memo §5 điểm 2.~~ Lựa chọn thứ ba đó không được chọn (D3); H1 giữ nguyên và độ tin cậy theo protocol hiện hành. IM3 chỉ giải quyết **nửa nguồn của độ tin cậy** trong selection-memo §5 điểm 2; nửa còn lại (phương pháp gốc không xác định ở `no_trace`, một phần ba pool H1) vẫn mở. Nó không chọn thay chủ dự án giữa ba lựa chọn đó.

### IM4. Nạp trước bằng chứng của tool bằng code thay cho tool do LLM chọn, cho model nhỏ

- **Trạng thái 2026-10-26: mở, không triển khai trong MVP (D9).** Kiểm trên code gốc cần chạy model cục bộ, chưa được phép (D6-D8), và chịu niêm phong test (D12).

- **Phát biểu.** Với backbone 4-9B (profile 12 GB), việc để code chạy sẵn cả `search_logs` và `search_fluctuating_metrics` cho mỗi span rồi đưa kết quả vào ngữ cảnh làm tăng tỉ lệ span có bằng chứng đầy đủ và tăng MRR so với để model tự gọi tool qua function calling trong cùng pipeline.
- **Cơ chế.** Table III và bài nói hiệu năng phụ thuộc "căn chỉnh nhiệm vụ, tương tác tool ổn định". Nạp trước loại bỏ yêu cầu model nhỏ phải gọi tool đúng lúc, đúng tham số.
- **Dự đoán phân biệt.** (i) Với model nhỏ, tỉ lệ span agent gọi được cả hai tool (khi để model chọn) thấp hơn nhiều so với 100%; (ii) nạp trước nâng tỉ lệ này lên 100% theo cấu trúc và nâng MRR; (iii) mức nâng giảm dần khi backbone mạnh hơn (không kiểm được với API Claude, chỉ quan sát qua 4B so với 9B).
- **Falsifier.** Không được ủng hộ nếu tỉ lệ span có gọi đủ hai tool ở cấu hình gốc đã >= 90% (không có lỗi để sửa), hoặc hiệu MRR hay R@1 ghép cặp (nạp trước trừ gốc) trên 90 sự cố RE2-OB có khoảng tin cậy 95% chứa 0 (chưa đủ bằng chứng, không phải bác bỏ) hoặc nằm dưới 0 (bằng chứng có hại). Ngưỡng 90% cố định, không tinh chỉnh bằng dữ liệu nào. Trước M5 chỉ chẩn đoán trên 48 train + 21 val RE2-OB; kết luận trên 90 sự cố (gồm 21 test) chỉ công bố sau M5 (niêm phong, reproduction-protocol §7).
- **Chi phí.** Thấp về code (sao một bản `coordinator.py` đã patch, ở giai đoạn 2); giảm số lời gọi vì bỏ vòng tool. Chạy trên GPU nên cần chủ dự án mở CPU-only.
- **Điều kiện nhánh.** Ở nhánh (a) nạp trước là cấu trúc của chính nhánh, nên giả thuyết trở thành so sánh (a) với (b)-gốc ở cùng model. Ở nhánh (b) là một ablation trong pipeline. Kiểm trên code gốc ở giai đoạn 2 độc lập với nhánh.
- **Quan hệ với H1.** *Độc lập.* Nó đổi độ chính xác nền và giảm lỗi parse (lỗi parse tính là sai trong endpoint), không đổi cách đo H1. Không xung đột.

## 3. Kiểm prior work

Đã kiểm theo yêu cầu: 3 truy vấn cho mỗi giả thuyết (OpenAlex 2 truy vấn, arXiv 1 truy vấn), ngày **2026-10-25 UTC** (rạng sáng 2026-10-26 giờ Việt Nam), toàn bộ dòng trong `work/prior-work-improvements.csv` (12 dòng). Chỉ đọc tiêu đề và, với năm bài liên quan nhất, tóm tắt. **Không đọc toàn văn.** Cột `relation` là quan hệ của kết quả hạng 1 với giả thuyết (same-problem, adjacent, unrelated, none). Giới hạn: từ khóa tiếng Anh, hai chỉ mục, không tìm thủ công theo trích dẫn, nên "chưa thấy" chỉ có nghĩa trong phạm vi tìm kiếm này.

| Giả thuyết | Kết quả theo giả thuyết | Bài liên quan đã thấy (chỉ tóm tắt) |
|---|---|---|
| IM1 | **Có chồng lấn một phần.** Chưa thấy trong tìm kiếm OpenAlex và arXiv tại 2026-10-25 UTC một phương pháp dùng khung phụ thuộc học từ trace train để thay trace bị thiếu cho agent LLM | TORAI (arXiv 2604.13522): RCA không dùng đồ thị gọi cho dịch vụ mù, không dùng LLM |
| IM2 | **Có chồng lấn một phần.** Chưa thấy trong tìm kiếm tại cùng ngày một cách đưa dịch vụ vắng trong trace vào bằng chứng của agent LLM như nút tường minh. Chồng lấn: cùng vấn đề "dịch vụ mù" | TORAI (cùng bài trên) |
| IM3 | Chưa thấy trong tìm kiếm tại 2026-10-25 UTC một nghiên cứu so sánh nguồn độ tin cậy (lời gọi riêng so với lời gọi tổng hợp) cho agent RCA | Không có bài sát; kết quả hạng 1 phần lớn không liên quan (27 và 664 kết quả OpenAlex, 1 kết quả arXiv) |
| IM4 | **Có chồng lấn một phần.** Chưa thấy trong tìm kiếm tại cùng ngày so sánh trực tiếp nạp trước tool tất định với tool do LLM chọn cho model 4-9B. Chồng lấn: hướng giảm phụ thuộc model lớn và nghiên cứu thiết kế tool | SpecRCA (W7118827999, cùng nhóm tác giả RCLAgent); *Rethinking Tool Design for Agentic RCA* (W7220686518): báo cáo Qwen3-8B hiếm khi gọi tool chẩn đoán |

Ghi chú: các lần tìm này không chứng minh rằng chưa ai làm. IM3 và IM4 nằm gần tài liệu về hiệu chuẩn LLM và về thiết kế tool mà truy vấn RCA hẹp có thể bỏ sót; nên mở rộng truy vấn (từ khóa "uncertainty", "self-consistency", "selective prediction" không kèm RCA) trước khi viết bất kỳ khẳng định nào về việc chưa ai làm trong bài báo.

## 4. Tóm tắt so sánh

| ID | Điều kiện đo chính | Cần nhánh | Lời gọi LLM thêm | Quan hệ H1 | Prior work | Trạng thái 2026-10-26 |
|---|---|---|---|---|---|---|
| IM1 | `no_trace` | (a) hoặc (b) | 0 | độc lập, có tương tác | chồng lấn một phần (TORAI) | **Chọn cho MVP** (giả thuyết cần kiểm; thăm dò) |
| IM2 | `blind_root` so với `blind_nonroot_ev` | (a) hoặc (b) | 0 ở (a); thêm ở (b) | độc lập (liên quan câu 4) | chồng lấn một phần (TORAI) | Mở, không triển khai |
| IM3 | mọi điều kiện, tập có trace | (b) | 0 | hỗ trợ | chưa thấy trong tìm kiếm | Mở, không triển khai; không dựa trên lời gọi LLM thứ hai |
| IM4 | 90 sự cố RE2-OB, model 4-9B | độc lập | giảm | độc lập | chồng lấn một phần (SpecRCA, tool design) | Mở, không triển khai |

Không giả thuyết nào xung đột trực tiếp với H1 hoặc protocol v2. ~~Chọn giả thuyết nào làm "một cải tiến" của MVP là việc của `mvp-outline.md` và của chủ dự án.~~ Đã quyết 2026-10-26 (D9): IM1; xem [mvp-outline.md](mvp-outline.md).
