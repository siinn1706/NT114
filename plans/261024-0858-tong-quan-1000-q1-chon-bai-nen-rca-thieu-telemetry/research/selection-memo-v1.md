# Memo chọn bài nền (phase 08), v1

- Ngày: 2026-10-26 (Asia/Saigon). Giao thức: `protocol.md` frozen-261024, §8.
- Trạng thái: **đề xuất**, chưa được chấp nhận. Chấp nhận bài nền thuộc chủ dự án.
- Nhãn: `single-eligible` vì đúng một bài trong T3 qua cả năm cổng G1–G5.
- Có hai xung đột cần chủ dự án quyết (mục 5), nên trạng thái phase là `waiting-human`.

## 1. Đề xuất

**RCLAgent**: *Toward In-Depth Root Cause Localization for Microservices With Multi-Agent Recursion-of-Thought*, IEEE TDSC 2026, doi 10.1109/tdsc.2026.3706572, OpenAlex W7165616276.

- Hồ sơ đầy đủ: [card T3](cards/t3/W7165616276.md), [cổng G](../work/t3/W7165616276-gates.csv), [evidence](../work/t3/W7165616276-evidence.csv), [artifact](../work/t3/W7165616276-artifact.csv).
- Bản đã đọc là preprint arXiv 2605.14866v1. Chưa có toàn văn bản TDSC; xem mục 5, điểm 3.

## 2. Bảng cổng G của 10 bài T3

Nguồn: `work/decision-matrix.csv` và `work/g-gates.csv`. Bằng chứng và locator của từng ô nằm trong `work/t3/<id>-gates.csv`.

| Bài | G1 | G2 | G3 | G4 | G5 | h1-compat | F T2 → T3 | Lý do trượt chính |
|---|---|---|---|---|---|---|---|---|
| UDA-RCL (W4417508611) | ✗ | ✓ | ✓ | ✓ | ✓ | có | 25 → 24 | Repo không có file license và import module không có trong repo. |
| DiagFusion (W4382203537) | ✗ | ✓ | ✓ | ✓ | ✓ | có (có điều kiện) | 25 → 25 | Repo không có file license; bài chỉ trỏ tới mirror ẩn danh. |
| **RCLAgent (W7165616276)** | ✓ | ✓ | ✓ | ✓ | ✓ | có (có điều kiện) | 25 → 25 | — |
| ThinkFL (W4416888443) | ✗ | ✓ | ✓ | ✓ | ✓ | không | 24 → 23 | Repo chỉ có script huấn luyện; thiếu dữ liệu, checkpoint SFT và code suy luận. |
| Topo-MFP (W7204187534) | ✗ | ✗ | ✓ | ✓ | ✓ | có | 23 → 24 | Không có repo; checklist thiếu; dataset không tải được. |
| CausalRCA (W4372338130) | ✓ | ✓ | ✓ | ✓ | ✗ | có | 22 → 23 | Chỉ dùng một modality (metric). |
| CHASE (W7203837764) | ✗ | ✓ | ✓ | ✓ | ✓ | có | 21 → 21 | Code chỉ có dạng file 7z trên Drive; checklist thiếu. |
| TAMO (W4415933773) | ✗ | ✓ | ✓ | ✓ | ✓ | có | 21 → 19 | Không có code; checklist thiếu. |
| RCRank (W4410538768) | ✗ | ✓ | ✓ | ✗ | ✓ | không | 21 → 21 | Không có license; bài thuộc miền CSDL và không có vai trò LLM để rút về. |
| Edge PPR (W7131638922) | ✗ | ✓ | ✓ | ✗ | ✓ | có | 18 → 18 | Không có code; đóng góp chính (phân tán) không ảnh hưởng độ chính xác offline. |

- G1 là cổng trượt nhiều nhất (8/10). Repo thiếu file license là lý do trượt của UDA-RCL, DiagFusion và RCRank.
- G3 đạt ở cả 10 bài nhưng chỉ là `static-estimate`, chưa đo thật.
- Cổng không được nới sau khi đã biết bài nào đạt.

## 3. Lý do đề xuất, theo từng tiêu chí

- **G1.** Repo LLM4AIOps/RCLAgent-V2 trả HTTP 200, license MIT, HEAD 3052e7a6 ngày 2026-06-18. README có quick start chạy trên `sample_data/`, entry point là `tool_server.py`, `coordinator.py` và `evaluate.py` (kiểm 2026-10-25).
- **G2.** Bài dùng RCAEval RE2-OB, bộ đã bật trong bundle NT114 (`prep.yaml`). AIOps2022 tải được từ Zenodo 19176851 (HTTP 200).
- **G3.** Code gọi LLM qua endpoint tương thích OpenAI, nên có thể trỏ sang vLLM cục bộ chạy qwen3.5-4b/9b hoặc qwen3-8b. Phần tool chạy trên CPU. Đây là ước lượng tĩnh.
- **G4.** Mọi agent và bộ tổng hợp dùng cùng một backbone (§V-A.4), không có hệ nhiều model. Phần lõi giữ lại:
  - phân rã trace thành ngữ cảnh mức span có kích thước giới hạn;
  - gộp bằng chứng từ dưới lên;
  - Global Evidence Graph và Root-Level Report;
  - các tool metric (n-sigma) và log, đều tất định.
- **G5.** Dùng trace, metric và log. Phần giới hạn (§VI) nêu thẳng hai failure mode trùng điều kiện thiếu telemetry của NT114: không có trace, và span không được lấy mẫu.
- **F theo T3 = 25:** F1 5, F2 3, F3 7, F4 4, F5 3, F6 3. Chi tiết chấm lại ở `work/f-rescore-log.csv`:
  - F3_code tăng từ 2 lên 3 vì đã thấy license và hướng dẫn chạy;
  - F3_desc giảm từ 1 xuống 0 vì thiếu prompt của bộ tổng hợp và thiết lập decoding, và ngưỡng lỗi trong bài khác trong code.
- **h1-compat = có, kèm điều kiện.** Đầu ra là danh sách top-10, và report gốc có độ tin cậy dạng lời trong [0,1] (§IV-C.1). File kết quả phát hành chỉ lưu danh sách, nên cần sửa nhỏ để ghi lại độ tin cậy.

## 4. Độ nhạy và vị trí của bài

Áp quy tắc `single-eligible`: chạy 18 kịch bản trên cả 10 bài T3 với cổng G bỏ qua. Kết quả ở `work/sensitivity.csv`, receipt `08-sens-t3-01`.

- Khi bỏ cổng, bài đứng đầu theo F chấm lại là DiagFusion. DiagFusion và RCLAgent cùng 25 điểm; tie-break F1 và F3 bằng nhau, F2 là 4 so với 3.
- RCLAgent một mình hạng 1 ở 2/18 kịch bản (w_F2 = 0,5 và w_F6 = 1,5).
- Ở 12/18 kịch bản, RCLAgent hòa điểm với bài đứng đầu và xếp thứ 2 do tie-break.
- Ở 4/18 kịch bản còn lại, RCLAgent đứng hạng 2 đến 4 mà không hòa điểm hạng 1.
- Ô lệch kiểm chéo ±1 (5 kịch bản) không đổi bài đứng đầu.
- Kết luận: về điểm F, RCLAgent ngang nhóm đầu chứ không vượt trội. Đề xuất dựa trên cổng G, cụ thể là khả năng tái hiện (G1), không dựa trên F.
- Hạng 1 theo F của T2 (UDA-RCL) khác hạng 1 theo F chấm lại (DiagFusion). Quy tắc chấm lại độc lập hai bài đầu chỉ áp cho nhánh ≥ 2 bài đạt, nhưng tôi vẫn ghi lại để minh bạch.
- Độ nhạy trên toàn bộ 20 bài có F ở T2 (`work/sensitivity-t2-pool.csv`) cho thấy 4 bài ngoài T3 vào top-10 ở ít nhất một kịch bản: QROOT, RPCA, BARO tăng cường và bài multi-agent RCA W4415944773. Theo card T2, cả bốn đều không có code (F3_code = 0); QROOT và BARO chỉ dùng một modality. Vì vậy chúng khó qua G1 và G5. Đây là sàng nhanh từ card T2, chưa đọc sâu.

## 5. Rủi ro, xung đột và điều kiện có thể đảo đề xuất

1. **Xung đột với bất biến của protocol v2 (`waiting-human`).** Protocol v2 §1 ghi: "Every reported answer comes from one model's single call". RCLAgent gọi cùng một model nhiều lần: ít nhất hai lời gọi cho mỗi span, cộng thêm các lượt dùng tool (`coordinator.py`). Cổng G4 của §8 chỉ yêu cầu một LLM, không yêu cầu một lời gọi, nên bài vẫn qua G4. Nhưng dùng RCLAgent làm bài nền thì phải chọn một trong hai:
   - (a) giữ bất biến v2. Phần đệ quy theo span sẽ bị thay bằng phân rã và tool tất định cùng một lời gọi tổng hợp. Như vậy bỏ mất phần "recursion-of-thought" của đóng góp lõi.
   - (b) mở rộng bất biến v2 cho pipeline nhiều lời gọi trên một model. Đây là thay đổi protocol v2, thuộc quyền chủ dự án.
   Tôi không tự đổi protocol v2.
2. **Sức mạnh của backbone.** Bài không thử backbone nào dưới 32B. Llama-3.1-70B chỉ đạt MRR 7–19 và DeepSeek-R1-Qwen-32B đạt 36–65, trong khi Claude đạt 55–89 (Table III). Độ chính xác với model 4–9B chạy trong 12 GB chưa được kiểm chứng; đây là rủi ro lớn nhất cho tái hiện ở phase 09.
3. **Bản đã đọc.** Bản đọc là arXiv v1; bản TDSC chưa truy cập được. §9 ưu tiên bản tạp chí cho các số liệu quyết định ở T3, nên cần chủ dự án tải bản TDSC để đối chiếu Table I–III.
4. **Đánh giá trong repo khác với bài.**
   - README §6 lấy thứ hạng tốt nhất trên mọi trace lỗi của một sự cố. Bước này có tính oracle và có thể làm tăng Recall và MRR.
   - Số sự cố được đánh giá chỉ có trong README (66/17/90), không có trong bài.
   - Khi tái hiện phải chấm theo một trace hoặc một sự cố được chỉ định trước.
5. **Phản chứng về kết quả.**
   - Trên Train-Ticket, Nezha thắng RCLAgent về MRR (90,37 so với 86,47).
   - Trên RE2-OB, BARO thắng RCLAgent ở R@3 và R@5.
   - Mức tăng trung bình 7,51 điểm của bài bỏ qua ca Nezha thắng.
6. **Các điều kiện có thể đảo đề xuất:**
   - Chủ dự án giữ (a) và coi phần đệ quy là lõi không thể bỏ. Khi đó bài không còn hợp làm bài nền.
   - Chủ dự án duyệt amendment nới G1, chẳng hạn chấp nhận repo không có file license khi chỉ đọc hoặc tái hiện nội bộ. Khi đó DiagFusion và UDA-RCL qua đủ cổng, và theo quy tắc ≥ 2 bài đạt, DiagFusion đứng hạng 1. Lưu ý thêm: DiagFusion cần 80–160 sự cố có nhãn cho mỗi hệ, và repo có code lệch mô tả trong bài.
   - Bản TDSC có số liệu khác đáng kể so với bản arXiv.
7. **Cảnh báo về tính nhất quán của cổng G.** Năm reader khác nhau áp cổng G (mỗi reader 2 bài). G1 được áp cùng một quy tắc chữ: có repo, có file license, có entry point, hoặc đủ checklist. G4 với lõi không-LLM là phán đoán: được tính đạt khi lõi ghép được với một LLM, nhưng RCRank và Edge PPR trượt vì lý do riêng nêu trong bảng.

## 6. Ghi chú kỹ thuật

- Hash text trong card T2 là SHA-256 của chuỗi LF trong bộ nhớ (`fulltext-access.py` dòng 68), còn file `.txt` trên đĩa là CRLF do `write_text` trên Windows. Đã kiểm 10/10 file: đổi CRLF về LF thì hash khớp. Nội dung không đổi.
- Quartile theo năm xuất bản: 10/10 bài thuộc tạp chí Q1 SJR ở năm xuất bản; năm 2026 dùng SJR 2025 thay thế (`work/q1-pubyear-check.csv`). JCR chưa kiểm vì không có quyền truy cập.
- Prior work: không thấy bản mới hơn vượt RCLAgent. Nhóm tác giả có AMER-RCL và SpecRCA (ICSE 2026), nhưng mới đọc abstract (`work/prior-work-t3.csv`). Reader cũng nêu ARMOR (ASE 2026, W7141399328), một RCA không-LLM thiết kế cho trường hợp thiếu modality. Bài này đáng xem cho phase 09 như comparator, chưa đọc.
