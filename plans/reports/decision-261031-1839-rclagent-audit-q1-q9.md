# Quyết định Q1–Q9 của audit RCLAgent và sửa thứ tự service trong prompt, 2026-10-31

**Kết luận.** Ngày 2026-10-31, sếp giao em tự quyết Q1–Q9 trong [audit 261029-1121](audit-261029-1121-rclagent-missing-source-analyzer-harness.md) theo hướng có lợi nhất cho sếp, và duyệt sửa thứ tự service trong prompt tổng hợp. Em quyết theo ba nguyên tắc:

- giữ nguyên số liệu và kết luận đã nhận;
- không cần chạy GPU thêm;
- chỉ sửa code khi có một kiểu lỗi thật và cách sửa nhỏ.

Kết quả:

- **Không quyết định nào đổi số liệu hay kết luận** của vòng 1, vòng 2 hoặc S1 v2. Chạy lại analyzer mới trên cả ba vòng cho `runs.csv` trùng từng byte. Trong `summary.json` chỉ khác dòng `note`, và `provisional` vẫn là false.
- **Có code mới (4 thay đổi):**
  - cố định hash seed cho tiến trình con;
  - Q4 trong analyzer;
  - Q8 và Q9 trong harness.
- **Chỉ ghi lại (6 câu):** Q1, Q2, Q3, Q5, Q6, Q7.
- **Dựng lại gói hiện hành.** Ba thay đổi trong harness nằm trong các file được đóng vào bundle, nên em đã dựng lại gói. Gói S1 v2 đã chạy trong `s1-v2/` giữ nguyên.

Các đường dẫn file dưới đây tính từ `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`.

**Cách làm.**
- Gom bằng chứng: ba agent gom bằng chứng và đếm trên các ZIP kết quả, ba agent khác cố bác bỏ từng đề xuất.
- Tự kiểm: em chạy lại các script tính số của Q1–Q3 và so với số đã nhận trong decision log.
- Review code: ba agent review độc lập theo ba hướng (đúng sai, nguồn gốc gói, độ trung thực với code tác giả).
- Không gọi model hay GPU.

## 1. Thứ tự service trong prompt tổng hợp (đã sửa)

**Nguyên nhân.** Hàm tổng hợp của tác giả ghép danh sách service bằng `', '.join(set(...))` ở `upstream/coordinator.py:481` và `:483`. Thứ tự của một `set` chuỗi đổi theo hash seed mà Python chọn ngẫu nhiên cho mỗi tiến trình. Mỗi lượt chạy trong một worker riêng, nên mỗi lượt có một thứ tự riêng.

**Bằng chứng.**
- Trong 64 cặp có cùng số request giữa vòng 2 và S1 v2, 20 cặp khác nhau ở request cuối.
- Ở cả 20 cặp, khác biệt duy nhất là thứ tự của dòng "Services with metric anomalies only". Dòng lỗi log không cặp nào lệch.
- Điểm bằng nhau ở cả 20 cặp. Điều này chỉ cho thấy mẫu này không đổi điểm, không chứng minh thứ tự không bao giờ ảnh hưởng.

**Sửa.**
- `clean_env()` trong `kaggle-runtime.py` thêm `PYTHONHASHSEED='0'`.
- Mọi tiến trình con đều lấy môi trường từ hàm này: vLLM, tool server, worker, bước tải model và scorer của tác giả.
- Code tác giả giữ nguyên từng byte, như `prepare-bundle.py` vẫn kiểm.
- Biến này chỉ cố định thứ tự hash của chuỗi; seed lấy mẫu của vLLM là tham số riêng.

**Test.** `test_children_get_a_fixed_hash_seed`:
- biến vẫn bằng `'0'` khi môi trường ngoài đặt giá trị khác;
- 5 tiến trình con in cùng một thứ tự.

**Lưu ý khi so sánh.**
- Vòng 1, vòng 2 và S1 đều chạy với thứ tự ngẫu nhiên. Từ gói này trở đi, thứ tự cố định.
- Vì thế, so prompt giữa lượt mới và lượt cũ phải nêu khác biệt này.
- Decision log ghi S1 "giữ cùng prompt". Câu đó đúng về nội dung, còn thứ tự liệt kê ngẫu nhiên ở cả hai vòng.

## 2. Q1–Q9

| Câu | Quyết định | Sửa |
|---|---|---|
| Q1 | Ước lượng chính là của quy tắc sàng lọc (trung bình các trung bình theo seed); báo kèm ước lượng gộp theo cặp | Chỉ ghi lại |
| Q2 | Đã trả lời ở mục 5–7 của báo cáo vòng 2 và ở S1; thêm biên khi bỏ các khối chạm trần, chỉ là độ nhạy | Chỉ ghi lại |
| Q3 | Giữ cách đọc hiện tại; ghi rõ luật phân xử | Chỉ ghi lại |
| Q4 | Lượt có lỗi toàn vẹn làm kết quả thành tạm thời, trừ lượt failed dừng trước khi ghi event | Analyzer |
| Q5 | Không thêm kiểm byte vào analyzer; ghi lại kết quả kiểm bằng script | Chỉ ghi lại |
| Q6 | Giữ hai lớp retry; ghi rõ cách chúng kết hợp | Chỉ ghi lại |
| Q7 | Giữ: không có call thì hỏi lại như output sai, hai call trở lên thì dừng | Chỉ ghi lại |
| Q8 | `Action: ` chỉ tính là cú pháp tool rò ra khi đứng đầu dòng và request có mời tool, giống code tác giả | Worker |
| Q9 | Lượt bị cắt vì vLLM chết được chạy lại một lần khi resume | Runtime |

### Q1. Ước lượng của phép kiểm độ vững

Số liệu chỉ tính trên các cặp mà cả hai lượt đều pass (A+B), ghi theo dạng ΔR@1 / ΔMRR:

| Vòng | Phép bỏ | Số cặp | Gộp theo cặp | Trung bình theo seed (quy tắc sàng lọc) |
|---|---|---|---|---|
| 1 | Bỏ log | 14 | −0,071 / +0,006 | −0,208 / −0,078 |
| 2 | Bỏ metric | 14 | −0,143 / −0,222 | −0,122 / −0,209 |
| 2 | Bỏ log | 23 | 0,000 / +0,035 | 0,000 / +0,035 |
| S1 v2 | Bỏ metric | 22 | −0,273 / −0,259 | −0,274 / −0,261 |
| S1 v2 | Bỏ log | 23 | 0,000 / +0,035 | 0,000 / +0,035 |

**Đọc bảng.**
- **Bỏ metric:** kết luận "mở hướng" đứng vững ở mọi cách tính, nhờ ΔMRR vượt ngưỡng 0,10 khoảng gấp đôi. ΔR@1 thì có cách tính cho −0,122, dưới ngưỡng 0,125, nên kết luận dựa vào MRR chứ không dựa vào R@1.
- **Bỏ log, vòng 2 và S1:** cách nói hiện hành ("không đạt tiêu chí, không phải bằng chứng log vô ích") đúng với cả hai cách tính.
- **Bỏ log, vòng 1:** câu "mất log gần như không ảnh hưởng" trong [báo cáo vòng 1](results-261029-0130-rclagent-missing-source-kaggle-runs.md) phụ thuộc cách tính. Theo ước lượng của quy tắc sàng lọc, ΔR@1 là −0,208, và con số này phần lớn đến từ seed 20261028, nơi chỉ có 2 cặp. Câu đó đã được thay bằng cách nói của vòng 2.
- **Chung cho mọi số trong bảng:** chỉ giữ cặp mà cả hai lượt đều pass tức là đã lọc theo kết quả.

### Q2. Case bị ảnh hưởng bởi trần

Mục 5–7 của [báo cáo vòng 2](results-261029-1448-rclagent-missing-source-round-2.md) đã nêu tên các case chịu ảnh hưởng của trần. S1 v2 cũng đã chạy lại với trần nới. Phần còn thiếu là biên của kết quả khi bỏ mọi khối (case, seed) có lượt chạm trần:

| Vòng | Số khối bỏ | ΔR@1 | ΔMRR | Seed giảm | Case giảm |
|---|---|---|---|---|---|
| 1 | 5 | −0,056 | −0,102 | 2/3 | 2 |
| 2 | 8 | −0,056 | −0,145 | 3/3 | 2, đúng mức tối thiểu |
| S1 v2 | 0 | −0,208 | −0,203 | 3/3 | 4 |

- Ở vòng 2, sau khi bỏ khối, tiêu chí ít nhất 2 case vừa đạt, không dư case nào.
- S1 v2 không có lượt chạm trần mà vẫn có 4 case giảm, nên hiệu ứng bỏ metric không phụ thuộc vào lượt bị dừng vì trần.
- Đây là phân tích độ nhạy có lọc theo kết quả. Nó không thay mẫu số đã nhận.

### Q3. Chiều thay đổi khi R@1 và MRR lệch nhau

Luật hiện tại trong `analyze-missing-source-results.py` là:
- **case:** "giảm" khi R@1 giảm, hoặc R@1 không đổi và MRR giảm;
- **seed:** "giảm" khi R@1 hoặc MRR giảm.

Em giữ luật này. Bằng chứng:
- Trên cả 6 phép so sánh (3 vòng × 2 phép bỏ), không seed hay case nào có ΔR@1 và ΔMRR trái dấu.
- Một cách đọc chặt hơn (chỉ xét chỉ số đã vượt ngưỡng) cho cùng cờ ở cả 6 phép so sánh.
- Đổi luật sau khi đã nhận kết quả là sửa quy tắc sau khi đã thấy kết quả, nên em không đổi.

### Q4. Lượt có lỗi toàn vẹn

**Quyết định.** Lượt có lỗi toàn vẹn (seed sai, source sai, chuỗi retry sai, dòng event hỏng) làm `summary.json` thành `provisional`. Kết luận phải chờ người xem xét lượt đó.

**Lý do.**
- Loại lượt khỏi phân tích sẽ đổi mẫu số một cách âm thầm.
- Tính 0 sẽ biến lỗi hạ tầng thành dự đoán sai.
- Cả hai cách trên đều trái quyết định đã có. Đánh dấu tạm thời giữ nguyên số và buộc người đọc xem lại.

**Ngoại lệ.** Lượt failed dừng trước khi ghi event (`no events`) vẫn giữ kết quả cuối, vì lượt failed đã tính 0 và được báo riêng theo nguyên nhân. Lượt passed mà không có event vẫn là lỗi toàn vẹn.

**Sửa.** Một điều kiện trong `analyze-missing-source-results.py`, kèm ba test mới trong `test-analyze-missing-source-results.py`:
- lượt seed sai làm kết quả thành tạm thời;
- lượt failed không có event vẫn là kết quả cuối;
- lượt passed không có event làm kết quả thành tạm thời.

**Ảnh hưởng tới kết quả cũ.** Chưa xảy ra: `integrity_problems` rỗng ở cả ba vòng.

### Q5. Kiểm byte của phản hồi `absent`

Em không thêm kiểm này vào analyzer. Lý do:
- Byte trả về được cố định bằng hằng số trong `smoke-worker.py` và `metric-repair.py`.
- Các hằng số đó có unit test riêng.
- Analyzer đã buộc mỗi ZIP vào đúng bundle bằng hash.
- Chép hằng số sang analyzer sẽ tạo bản sao phải giữ đồng bộ; nếu lệch, nó báo động giả và, sau Q4, chặn cả kết luận.

Kiểm một lần bằng script trên sáu bộ kết quả (vòng 1, vòng 2, S1 v2; mỗi vòng A và B):
- 4.231/4.231 phản hồi `absent` đúng byte "không có dòng" của endpoint tác giả.
- Seed và source trong `worker-status.json` khớp manifest ở 216/216 lượt.

### Q6. Hai lớp retry

Cách hai lớp hoạt động, được ghi lại như phần làm rõ của quyết định 2026-10-29 (không phải quyết định mới):
- **Lớp ngoài, của tác giả.** Tenacity thử lại tối đa 3 lần khi gặp lỗi kết nối hoặc HTTP 502/503/504.
- **Lớp trong, của harness.** Hỏi lại tối đa 3 lần khi tool call sai định dạng, với seed dẫn xuất.
- **Lỗi khác dừng ngay.** Mọi lỗi HTTP khác, `finish_reason` sai, hết ngân sách hay hết hạn đều dừng ngay.
- **Trường hợp xấu nhất.** Một lời gọi tốn 12 request, và tất cả đều tính vào trần request.
- **Khi tenacity gọi lại** sau một retry sai định dạng, chuỗi bắt đầu lại từ seed của lượt. Bước này phí 1–2 request và lặp lại output đầu.
- **Khi vLLM treo,** mỗi lần thử có thể chờ tới 180 giây. Thời gian này vẫn nằm trong deadline của lượt.

**Trong dữ liệu:** 13.207 request của vòng 2 và S1 v2 đều trả 200, nên chưa có lần thử lại mạng nào.

### Q7. Synthesizer không gọi hoặc gọi nhiều lần `print_results`

Giữ nguyên:
- **Không có call:** hỏi lại như output sai định dạng, tối đa 3 lần, rồi dừng.
- **Hai call trở lên:** dừng ngay; lượt tính 0 và được báo theo nguyên nhân riêng.
- Text không bao giờ được đọc thành dự đoán.

Code tác giả dễ dãi hơn (lấy call đầu, rồi đọc JSON từ text). Harness chặt hơn có chủ đích, vì nếu sai thì chỉ làm giảm điểm, không làm tăng.

**Trong dữ liệu:** 132/132 phản hồi của synthesizer có đúng một call.

### Q8. `Action:` khi request không mời tool

**Quyết định.** Chuỗi `Action: ` trong text chỉ bị coi là cú pháp tool rò ra khi nó đứng đầu một dòng và request có mời tool. Đây đúng là điều kiện để code tác giả đọc tool từ text (`llm.py`, `get_tool_from_content`, chỉ chạy khi có tool). Vì vậy một câu như "Corrective Action: restart" không còn bị hỏi lại.

Hai marker `<tool_call>` và `✿FUNCTION✿` vẫn bị chặn ở mọi vị trí, kể cả khi không mời tool. Cách này chặt hơn code tác giả nhưng có chủ đích, vì nếu sai thì chỉ làm giảm điểm.

**Sửa.** `validate_calls` trong `smoke-worker.py`, kèm test `test_action_text_without_offered_tools_is_an_answer`. Test này phủ ba trường hợp: không mời tool, `Action:` giữa câu khi có tool, và hai marker luôn bị chặn.

**Ảnh hưởng tới kết quả cũ.** Không: 0/3.642 phản hồi không mời tool có chứa `Action:`.

**Vì sao sửa ngay dù chưa xảy ra.** Gói phải dựng lại cho phần hash seed, nên đưa luôn vào không tốn thêm một lần dựng.

### Q9. vLLM chết giữa một lượt

**Quyết định.** Khi lượt lỗi và tiến trình vLLM đã chết:
- lượt đó được ghi `interrupted` và giữ trạng thái `running`;
- batch dừng lại;
- khi resume, lượt đó chạy lại từ đầu, phần output dở được cất sang bên.

Lỗi phía model khi server còn sống vẫn là kết quả cuối, đúng luật mỗi lượt chạy một lần.

Lượt chỉ được chạy lại một lần. Nếu vLLM lại chết trong chính lượt đó, lượt bị ghi failed kèm nguyên nhân. Nhờ vậy, một prompt làm server crash theo cách lặp lại được sẽ không chặn cả batch sau mỗi lần resume.

**Sửa.** `run_traces` trong `kaggle-runtime.py`, kèm hai test: `test_trace_cut_off_by_a_dying_model_server_runs_again_on_resume` và `test_a_second_server_death_in_the_same_trace_is_final`.

**Giới hạn.**
- Phép kiểm chỉ nhận ra tiến trình đã chết. Một vLLM treo mà tiến trình vẫn sống vẫn bị ghi failed. Muốn bắt trường hợp này cần thêm health probe, việc lớn hơn mà em chưa làm.
- Phép kiểm chạy ngay sau khi worker báo lỗi. Nếu tiến trình vLLM chưa kịp thoát hẳn, lượt vẫn có thể bị ghi failed.

**Ảnh hưởng tới kết quả cũ.** Chưa xảy ra: cả bốn phiên vòng 2 và S1 v2 đều kết thúc với vLLM thoát bình thường, và 16 lượt failed đều có nguyên nhân phía model hoặc do trần.

## 3. Gói mới và kiểm tra

- **Stage mới.** `runtime/package-missing-source-b-hashseed` là bản chép của stage S1 v2 B. Stage này được làm mới bằng `refresh-package.py`, sau đó em chạy `build-notebook.py` và `verify-package.py`.
  - Bundle: `bdd13d71…d14a`.
  - Manifest: `0b43d32a…ed2b`.
  - Notebook: `feef1462…6705`.
  - So với bundle S1 v2 B, chỉ `kaggle-runtime.py`, `smoke-worker.py` và `manifest.json` khác. Mọi file của tác giả trùng từng byte. `runs`, `condition_design` và `harness_limits` không đổi.
  - Gói này chưa được đẩy lên Kaggle.
- **Phép kiểm ngân sách.** `check-tool-result-budget.py` đã chạy lại với tokenizer `cdbee75f…`. Trong `tool-result-budget-check.json`, chỉ hash của worker đổi.
- **Test.** Tám bộ test đều pass: 48, 11, 14, 4, 6, 20, 4 và 13 test.
- **Review độc lập theo ba hướng.**
  - Không có lỗi mức cao.
  - Có một lỗi mức trung bình: một prompt làm vLLM crash theo cách lặp lại được sẽ khiến lượt đó chạy lại mãi. Đã sửa bằng giới hạn một lần chạy lại.
  - Có bốn chỗ test để lọt mutant. Đã bổ sung test, và em đã chạy lại sáu mutant: cả sáu đều bị test bắt.
  - Reviewer đề nghị cho `Action: ` khớp theo đầu dòng như code tác giả. Đã sửa.
  - Reviewer kiểm thấy `PYTHONHASHSEED` không đổi gì khác trong vLLM 0.10.2 (V0), tokenizer, pandas, tool server hay scorer, ngoài thứ tự tên service trong prompt tổng hợp.

## Câu hỏi còn mở

- Một vLLM treo mà tiến trình vẫn sống vẫn bị ghi failed. Có cần thêm health probe trước lần chạy GPU tới không?
- Gói mới chưa chạy trên Kaggle. `PYTHONHASHSEED` chưa được kiểm trên T4 thật.
- Gói mới chỉ dựng cho B. Lần chạy tới cần dựng gói A tương ứng từ stage A với cùng code.
