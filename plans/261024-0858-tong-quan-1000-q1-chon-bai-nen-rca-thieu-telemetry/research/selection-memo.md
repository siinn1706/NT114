# Memo chọn bài nền (phase 08), v2

- Ngày: 2026-10-26 (Asia/Saigon). Các mốc kiểm HTTP ghi theo UTC (ngày 2026-10-25 UTC tương ứng rạng sáng 2026-10-26 giờ Việt Nam).
- Giao thức: `protocol.md` frozen-261024, §8.
- v2 thay v1 (`selection-memo-v1.md`) sau review ngữ cảnh mới. Các ô cổng G sửa sau review nằm ở `work/t3-gate-corrections-a02.csv`; giá trị cũ được giữ trong cột `correction` của `work/g-gates.csv`.
- Trạng thái: **đề xuất**, chưa được chấp nhận. Nhãn `single-eligible`. Phase ở trạng thái `waiting-human` vì có ba quyết định thuộc chủ dự án (mục 5).

## 1. Đề xuất

**RCLAgent**: *Toward In-Depth Root Cause Localization for Microservices With Multi-Agent Recursion-of-Thought*, IEEE TDSC 2026, doi 10.1109/tdsc.2026.3706572, OpenAlex W7165616276.

- Hồ sơ đầy đủ: [card T3](cards/t3/W7165616276.md), [cổng G](../work/t3/W7165616276-gates.csv), [evidence](../work/t3/W7165616276-evidence.csv), [artifact](../work/t3/W7165616276-artifact.csv). Các ô cổng đã sửa (gồm h1-compat = có điều kiện) nằm ở [t3-gate-corrections-a02.csv](../work/t3-gate-corrections-a02.csv), có hiệu lực thay cho file gates riêng khi hai nơi khác nhau.
- Bản đã đọc là preprint arXiv 2605.14866v1; bản TDSC chưa có (mục 5, điểm 4).

## 2. Bảng cổng G của 10 bài T3

Nguồn: `work/decision-matrix.csv`, `work/g-gates.csv` và `work/t3/<id>-gates.csv`. Ký hiệu: ✓ đạt, ✗ trượt, † ô đã sửa sau review.

| Bài | G1 | G2 | G3 | G4 | G5 | h1-compat | F T2 → T3 | Lý do trượt chính |
|---|---|---|---|---|---|---|---|---|
| UDA-RCL (W4417508611) | ✗ | ✓ | ✓ | ✓ | ✓ | có | 25 → 24 | Repo không có file license; import module không có trong repo. |
| DiagFusion (W4382203537) | ✗ | ✓ | ✓ | ✓ | ✓ | có điều kiện† | 25 → 25 | Repo không có file license; bài chỉ trỏ mirror ẩn danh. |
| **RCLAgent (W7165616276)** | ✓ | ✓ | ✓ | ✓ | ✓ | **có điều kiện†** | 25 → 25 | — |
| ThinkFL (W4416888443) | ✗ | ✓ | ✓ | ✓ | ✓ | không | 24 → 23 | Repo chỉ có script huấn luyện; không có dữ liệu, checkpoint SFT hay code suy luận. |
| Topo-MFP (W7204187534) | ✗ | ✓† | ✓ | ✓ | ✓ | có | 23 → 24 | Không có repo; checklist thiếu. |
| CausalRCA (W4372338130) | ✓ | ✓ | ✓ | ✓ | ✗ | có | 22 → 23 | Chỉ có một modality (metric). |
| CHASE (W7203837764) | ✗† | ✓ | ✓ | ✓ | ✓ | có | 21 → 21 | File 7z không có license gốc, không có README hay lệnh chạy. |
| TAMO (W4415933773) | ✗ | ✓ | ✓ | ✓ | ✓ | có | 21 → 19 | Không có code; checklist thiếu. |
| RCRank (W4410538768) | ✗ | ✓ | ✓ | ✓† | ✓ | không | 21 → 21 | Không có file license. |
| Edge PPR (W7131638922) | ✗ | ✓ | ✓ | ✗ | ✓ | có | 18 → 18 | Không có code; đóng góp lõi (phân tán) mất khi đánh giá offline. |

Các ô sửa sau review:
- CHASE G1 trước đây là "chưa kiểm". Tôi đã tải `CHASE.7z` ra ngoài repo NT114 và chỉ liệt kê 68 mục, không giải nén, không chạy. Không có LICENSE ở gốc và không có README hay lệnh chạy, nên CHASE trượt G1 có bằng chứng. Kết quả "đúng một bài đạt" vì vậy có bằng chứng ở cả 10 bài.
- Topo-MFP G2 chuyển sang đạt. Dữ liệu AIOps 2022 công khai qua bản re-upload Zenodo 19176851 (cc-by-4.0), và chính bản này đã cho RCLAgent và ThinkFL đạt G2. Topo-MFP vẫn trượt G1.
- RCRank G4 chuyển sang đạt khi xét theo đúng câu chữ G4, bỏ lập luận dựa trên protocol v2, để nhất quán với 5 bài có lõi không-LLM khác. RCRank vẫn trượt G1.
- Edge PPR giữ G4 trượt: phần lõi được bài nêu là thực thi phân tán, không phải bộ chấm điểm.
- Cờ h1-compat của RCLAgent và DiagFusion đổi thành "có điều kiện" (mục 5, điểm 2).

Kiểm theo từng điều kiện của pool H1 chỉ làm cho bài đề xuất; cột h1-compat của các bài khác vẫn theo đánh giá ban đầu của reader. UDA-RCL, Topo-MFP, CHASE và Edge PPR cũng cần trace, nên nếu kiểm theo cách đó cờ của các bài này nhiều khả năng cũng thành có điều kiện.

Không ô nào sửa sau review làm đổi tập bài đạt đủ cổng. Bằng chứng của các ô sửa có receipt `08-gate-evidence-01` (`work/t3-gate-evidence.json`), và kết quả gộp mới nhất có receipt `08-merge-t3-03`. G1 vẫn là cổng trượt nhiều nhất (8/10). G3 đạt ở cả 10 bài nhưng chỉ là `static-estimate`.

## 3. Lý do đề xuất, theo từng tiêu chí

- **G1.** Repo LLM4AIOps/RCLAgent-V2 trả HTTP 200, license MIT, HEAD 3052e7a6 ngày 2026-06-18. README có quick start trên `sample_data/`, entry point là `tool_server.py`, `coordinator.py` và `evaluate.py`.
- **G2.** RCAEval RE2-OB đã bật trong bundle NT114 (`prep.yaml`, dòng 25). AIOps2022 có trên Zenodo 19176851.
- **G3.** Code gọi LLM qua endpoint tương thích OpenAI, nên trỏ được sang vLLM cục bộ (qwen3.5-4b/9b, qwen3-8b). Phần tool chạy trên CPU. Đây là ước lượng tĩnh.
- **G4.** Mọi agent và bộ tổng hợp dùng chung một backbone (§V-A.4). Phần lõi giữ lại:
  - phân rã trace thành ngữ cảnh mức span có kích thước giới hạn;
  - gộp bằng chứng từ dưới lên;
  - Global Evidence Graph và Root-Level Report;
  - tool metric (n-sigma) và tool log, đều tất định.
- **G5.** Có đủ trace, metric và log.
- **F theo T3 = 25:** F1 5, F2 3, F3 7, F4 4, F5 3, F6 3. Hai thay đổi khi chấm lại (`work/f-rescore-log.csv`):
  - F3_code tăng từ 2 lên 3;
  - F3_desc giảm từ 1 xuống 0.

## 4. Độ nhạy và cách áp quy tắc ổn định

Áp quy tắc `single-eligible`: chạy 18 kịch bản trọng số trên cả 10 bài T3 với cổng G bỏ qua, cộng 5 kịch bản ±1 ở các ô có lệch kiểm chéo, tổng 23 dòng. Nguồn: `work/sensitivity.csv`, receipt `08-sens-t3-01`. Ô RCRank F2 đang ở mức tối đa 5 nên chỉ có kịch bản −1.

- **Khi bỏ cổng**, bài đứng đầu theo F chấm lại là DiagFusion. DiagFusion và RCLAgent cùng 25 điểm; tie-break F1 và F3 bằng nhau, F2 là 4 so với 3.
- **DiagFusion** một mình hạng 1 ở 3/18 kịch bản: w_F2 = 1,5, w_F6 = 0,5 và w_F6 = 0.
- **RCLAgent** một mình hạng 1 ở 2/18 kịch bản: w_F2 = 0,5 và w_F6 = 1,5. Ở 13/18 kịch bản, RCLAgent bằng điểm bài đứng đầu nhưng thua tie-break: 12 lần xếp hạng 2, một lần (w_F4 = 0, bốn bài cùng 21 điểm) xếp hạng 4. Ở 3/18 kịch bản còn lại, RCLAgent xếp dưới mà không bằng điểm bài đứng đầu.
- Năm kịch bản ±1 ở ô lệch kiểm chéo không đổi bài đứng đầu.
- **Cách đọc quy tắc ≥ 15/18.** Theo §8, nhánh "đúng 1 bài đạt" chỉ yêu cầu chạy độ nhạy để báo vị trí của bài; quy tắc ổn định viết cho hạng 1 của bảng xếp hạng. Không bài nào giữ hạng 1 từ 15/18 kịch bản trở lên. Vì vậy:
  - Xét riêng điểm F, hạng 1 **không ổn định**, và top-2 là DiagFusion và RCLAgent.
  - Đề xuất RCLAgent dựa trên cổng G, cụ thể là G1, chứ không dựa trên F.
  - Có coi tình trạng không ổn định này là lý do báo top-2 thay cho một bài hay không là quyết định của chủ dự án (mục 5, điểm 3).
- Hạng 1 theo F của T2 (UDA-RCL) khác hạng 1 theo F chấm lại (DiagFusion). Quy tắc reviewer chấm lại độc lập hai bài đầu chỉ áp cho nhánh ≥ 2 bài đạt; ở đây chỉ ghi lại.
- **Pool T2 (20 bài có F, `work/sensitivity-t2-pool.csv`).** Bốn bài ngoài T3 vào top-10 ở ít nhất một kịch bản: QROOT, RPCA, BARO tăng cường và multi-agent RCA (W4415944773).
  - Theo card T2, cả bốn đều không có code (F3_code = 0), nên phải có đủ checklist mới qua G1. QROOT và BARO chỉ dùng một modality.
  - Tôi chưa đọc sâu bốn bài này. Ngân sách phiên được dùng cho phần sửa sau review; điều này được ghi như một việc còn mở, không phải kết luận.

## 5. Quyết định cần chủ dự án, rủi ro và điều kiện có thể đảo đề xuất

1. **Xung đột với bất biến một lời gọi của protocol v2 §1 (`waiting-human`).** Protocol v2 §1 ghi: "Every reported answer comes from one model's single call". RCLAgent gọi cùng một model nhiều lần: ít nhất hai lời gọi cho mỗi span, cộng các lượt dùng tool; artifact ghi tới khoảng 200 lời gọi đồng thời khi chạy song song 6 subset. Cổng G4 chỉ yêu cầu một LLM, không yêu cầu một lời gọi. Hai lựa chọn:
   - (a) giữ bất biến: thay phần đệ quy theo span bằng phân rã và tool tất định cùng một lời gọi tổng hợp. Như vậy bỏ mất phần "recursion-of-thought" của lõi.
   - (b) mở rộng bất biến cho pipeline nhiều lời gọi trên một model. Đây là thay đổi protocol v2.
2. **Cờ h1-compat có điều kiện (`waiting-human`).** Pool `single_modality` của H1 gồm `no_metric`, `no_log` và `no_trace` (protocol v2 §9).
   - Ở `no_trace`, RCLAgent mất xương sống trace và theo chính bài thì thoái hóa thành một ReAct agent, tốn hơn và kém chính xác hơn (§VI (1)). Phương pháp gốc không xác định trên một phần ba pool.
   - Độ tin cậy `r_conf_root` lấy từ lời gọi Root-Level Report, còn danh sách xếp hạng lấy từ lời gọi Synthesizer. Một quy tắc abstention dựa trên độ tin cậy này vì vậy không phải quy tắc trên đầu ra của cùng lời gọi (protocol v2 §1).
   - Ba hướng cho chủ dự án: thu H1 về hai điều kiện có trace, coi `no_trace` là điều kiện thất bại có chủ đích của bài nền, hoặc lấy độ tin cậy từ chính lời gọi tổng hợp. Tôi không tự đổi H1.
3. **Hạng 1 theo F không ổn định.** RCLAgent một mình hạng 1 ở 2/18 kịch bản, DiagFusion ở 3/18. Chủ dự án chọn nhận một bài theo cổng G, hoặc xem top-2 (DiagFusion, RCLAgent).
4. **Phiên bản đã đọc.** §9 ưu tiên bản tạp chí cho số liệu quyết định ở T3. Cần chủ dự án tải bản TDSC để đối chiếu Table I–III.
5. **Rủi ro cho tái hiện (phase 09):**
   - Bài không thử backbone nào dưới 32B. Llama-3.1-70B chỉ đạt MRR 7–19, DeepSeek-R1-Qwen-32B đạt 36–65, so với Claude 55–89 (Table III). Độ chính xác với model 4–9B chưa biết.
   - Thông lượng chưa được đánh giá. Bài báo 41–60 giây mỗi truy vấn khi chạy qua API, với tới khoảng 200 lời gọi đồng thời khi chạy 6 subset song song. Độ trễ và thông lượng của model 4–9B trên laptop 12 GB chưa được ước lượng; G3 chỉ dựa trên ước lượng tĩnh.
   - Repo chỉ đánh giá 66/263 sự cố AIOps2022 có trong danh sách (khoảng 25%), không nêu quy tắc chọn (evidence C2).
   - README §6 lấy thứ hạng tốt nhất trên mọi trace lỗi của một sự cố. Bước này có tính oracle. Khi tái hiện phải chấm trên một trace hoặc sự cố chỉ định trước.
6. **Phản chứng.**
   - Nezha thắng RCLAgent về MRR trên Train-Ticket (90,37 so với 86,47).
   - BARO thắng ở R@3 và R@5 trên RE2-OB.
   - Mức tăng trung bình 7,51 điểm bỏ qua ca Nezha thắng.
7. **Các điều kiện có thể đảo đề xuất:**
   - Ở điểm 1, chủ dự án chọn (a) và coi phần đệ quy là lõi không thể bỏ.
   - Bản TDSC có số liệu khác đáng kể so với bản arXiv.
   - Chủ dự án duyệt amendment nới G1, ví dụ chấp nhận repo không có file license. Khi đó UDA-RCL, DiagFusion, RCLAgent và RCRank đều đạt (RCRank có F 21 và h1-compat không, nên không đổi top-2), và §8 chuyển sang nhánh ≥ 2 bài đạt.
     - Hạng 1 theo F của T2 (UDA-RCL) khác hạng 1 theo F chấm lại (DiagFusion), nên phải có reviewer chấm lại độc lập hai bài đầu.
     - DiagFusion và RCLAgent hòa 25 điểm, chỉ tách nhau ở F2. Top-2 không ổn định, nên kết quả vẫn là `waiting-human` chứ không phải "DiagFusion hạng 1".
8. **Tính nhất quán của cổng G.** Mười bài được giao cho năm lần chạy reader riêng do phiên điều phối khởi chạy, mỗi lần hai bài. Receipt không ghi định danh agent, nên đây là ghi chép của phiên điều phối chứ không phải bằng chứng trong file. Card đều ký "r1" vì brief chung đặt tên như vậy.
   - G1 dùng cùng một cách đọc câu chữ: có repo, có file license, có entry point, hoặc đủ checklist.
   - G2 và G4 đã được làm nhất quán sau review (mục 2).
   - Protocol v2 không phải một phần của cổng G. Phần tương thích với v2 chỉ được xét riêng cho bài đề xuất, ở điểm 1 và 2.

## 6. Ghi chú kỹ thuật

- **Hash text.** Hash trong card T2 là SHA-256 của chuỗi LF trong bộ nhớ (`fulltext-access.py`, dòng 68). File `.txt` trên đĩa là CRLF do `write_text` trên Windows. Đổi CRLF về LF thì hash khớp ở 10/10 bài (`work/t3-text-hash-check.csv`, receipt `08-text-hash-01`). Sáu card từng ghi "không khớp" đã được thêm ghi chú này.
- **Quartile theo năm xuất bản.** 10/10 bài là tạp chí Q1 SJR ở năm xuất bản; năm 2026 dùng SJR 2025 thay thế (`work/q1-pubyear-check.csv`). UDA-RCL được ghi năm 2025 theo ngày online 2025-12-19, trong khi card trích số 2026. JCR chưa kiểm vì không có quyền.
- **Prior work.** Không thấy bản mới hơn vượt RCLAgent. AMER-RCL và SpecRCA (ICSE 2026) của cùng nhóm mới đọc abstract (`work/prior-work-t3.csv`). ARMOR (ASE 2026, W7141399328), một RCA không-LLM cho trường hợp thiếu modality, đáng xem làm comparator ở phase 09; chưa đọc.
- **Ma trận quyết định.** Mọi số trong `work/decision-matrix.csv` lấy từ `work/t3/<id>-rescore.csv` và `<id>-gates.csv`. Cột `sources` trỏ tới card và hai file đó.

## Quyết định của chủ dự án (2026-10-26)

Phần thêm sau, không sửa các mục trên. Nguồn: [nhật ký quyết định](../../261018-2300-single-llm-simplification-and-evaluation-hardening/decisions.md) (các dòng ngày 2026-10-26).

- **Chấp nhận có điều kiện (D1, D4).** RCLAgent (W7165616276, doi 10.1109/tdsc.2026.3706572) được chấp nhận làm bài nền trên kết quả single-eligible hiện tại, để phát triển thiết kế tiếp. Đây không phải khẳng định rằng nó là phương pháp tốt nhất, thắng ổn định, đã được tái hiện hay phù hợp model 4-9B. DiagFusion ở lại bảng so sánh và thảo luận chọn bài, không có nhánh triển khai; G1 không được nới để đổi lựa chọn (điểm 3 và điều kiện đảo ở điểm 7 không được kích hoạt).
- **Điểm 1: nhánh (a) (D2).** Giữ bất biến một lời gọi của protocol v2: một model, một lời gọi mỗi câu trả lời; phân rã, chọn bằng chứng và chạy tool là code tất định, LLM chỉ tổng hợp và xếp hạng ở lời gọi cuối; không đệ quy đa agent, judge hay leo thang. Nhánh (b) không chọn. Kết quả là bản thích nghi RCLAgent không có recursion-of-thought, không bao giờ gọi là tái hiện đầy đủ; phát hiện về code gốc báo riêng.
- **Điểm 2: H1 giữ nguyên (D3).** Quần thể H1 không thu hẹp; ca thiếu trace được xử lý bằng đường tool metric/log tất định và bằng chứng phẳng theo ứng viên, vẫn một lời gọi tổng hợp, và ở lại mẫu số. Độ tin cậy theo protocol hiện hành, không từ lời gọi LLM thứ hai. Ba hướng cũ ở điểm 2 không được chọn.
- **Điểm 4: phiên bản đã đọc (D5).** Kế hoạch tiếp tục trên arXiv v1 với phiên bản nêu rõ; bản TDSC vẫn là điều kiện trước khi khẳng định khớp bài đã xuất bản (còn mở).
- **Điểm 5: tài nguyên (D6-D8).** Không API trả phí, không gửi evidence ra ngoài; lượt kế tiếp chỉ lập kế hoạch triển khai và khả thi, không chạy GPU/model.
- **PR-06 giữ nguyên.** Chuẩn SJR 2025 Computer Science đã đóng băng được giữ; không thêm Engineering sau khi thấy kết quả chọn. Perplexity (tài khoản Pro của chủ dự án) thay làn Elicit đã hết cho các tìm kiếm có mục tiêu, chỉ với từ khóa, tiêu đề, DOI và mô tả phương pháp công khai; nó chỉ tìm nguồn, mọi khẳng định kiểm với bài gốc, repo chính thức hoặc nguồn xếp hạng; phễu 1,000 → 100 → 10 → 1 không chạy lại.
- **Số liệu và lựa chọn của memo này không đổi.** Các con số rà soát, bảng cổng G, độ nhạy và việc đề xuất RCLAgent giữ nguyên như đã ghi; quyết định của chủ dự án chỉ cho phép dùng RCLAgent làm bài nền có điều kiện. Thiết kế phase 09 đã cập nhật tương ứng ở `design/` (phiên bản 0.2).
