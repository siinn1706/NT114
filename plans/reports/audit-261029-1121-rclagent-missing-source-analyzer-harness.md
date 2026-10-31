# Audit độc lập: bộ phân tích và harness thiếu nguồn của RCLAgent, 2026-10-29

**Kết luận.** Không có lỗi nào làm sai số liệu của vòng 1. Chạy lại `analyze-missing-source-results.py` trên hai ZIP vòng 1 cho `summary.json` trùng từng byte với `runtime/analysis-missing-source-{a-v13,b-v1,ab}/`. Mọi con số ở mục 2 và 4 của báo cáo kết quả đều khớp. Vòng 1 không có retry, resume, run bị cắt hay run pass mà thiếu điểm.

Tuy vậy, có 10 lỗi tái hiện được, sẽ chạm vào vòng 2 (đang chạy) hoặc vào việc vận hành:

- Ba lỗi đáng sửa trước khi chấm vòng 2:
  - **F1.** Harness báo lỗi toàn vẹn giả khi một chuỗi retry hết ngân sách.
  - **F2.** Lượt pass nhưng không có điểm bị tính 0 mà không có cờ nào.
  - **F3.** Khi đưa trùng run vào cùng một lần chạy, kết quả sàng lọc phụ thuộc thứ tự tham số.
- Lỗi nặng nhất về dữ liệu là **F5**: tool server không kịp sẵn sàng thì không bị dừng, và run sau có thể đọc telemetry của trace trước mà không có cảnh báo. Điều kiện kích hoạt hiếm.
- 9 câu hỏi cần sếp quyết. Không câu nào đổi kết luận vòng 1. Hai câu ảnh hưởng tới cách đọc kết quả: Q1 về độ vững của kết luận "bỏ log", Q2 về biên độ của kết luận "bỏ metric".

**Phạm vi và cách làm.** Em đã đọc README, decision log (các dòng 2026-10-28 và 2026-10-29), báo cáo `results-261029-0130`, mục 6.3 của `analysis-261028-1104`, cùng các file `analyze-missing-source-results.py`, `smoke-worker.py`, `kaggle-runtime.py`, `llm.py` upstream và các test hiện có.

Audit chia theo 4 hướng, mỗi hướng một agent tìm lỗi. Mỗi finding sau đó được một agent khác cố bác bỏ và tự chạy lại repro. Cả 30 finding đều tái hiện được; một finding bị loại vì đó là hành vi đã chốt (RR-7). Em tự chạy lại repro của F1, F3, F2, F5 và F8, và tự tính lại biên MRR ở Q2.

Repro nằm trong scratchpad của phiên, chỉ dùng CPU: `C:/Users/Siinn/AppData/Local/Temp/claude/F--Nam-UIT-NT114---NCKH/c7744a1f-b9b1-4b00-978d-1610160a4631/scratchpad/audit/`. Bảng finding đầy đủ ở `results.json` và `details.txt` trong thư mục đó.

Không sửa source hay kết quả cũ; `git status` không đổi. Không gọi model hoặc GPU, không đẩy Kaggle, không commit.

Các đường dẫn dưới đây tính từ `plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/`. Dòng code lấy theo bản hiện tại (chưa commit).

## 1. Đã kiểm và đúng

- **Số liệu.** Theo mục 2 và 4 của báo cáo:
  - B: `metric` 0,167/0,333/0,264.
  - A+B: bỏ metric −0,167/−0,215, 3/3 seed, 4 case. Bỏ log −0,042/+0,003, 1 case.
  - Phân loại lỗi: 30 lỗi tool call sai định dạng, 3 lỗi trần vòng tool, 2 lỗi hết request, 1 lỗi schema.
  - Các số kiểm độ vững theo cặp pass (8 cặp, −0,125/−0,214; 14 cặp, −0,071/+0,006) tái hiện đúng khi tính trung bình gộp theo cặp.
- **Toàn vẹn vòng 1, kiểm trực tiếp trên dữ liệu thật:**
  - `bundle_sha256` trong `progress.json` khớp file `.sha256` của bundle A (`a2bccc75…`) và B (`196e38c4…`).
  - Mỗi run có đúng 1 attempt, không có thư mục `.previous-N`, không có dòng events bị cụt.
  - 578/578 (A) và 350/350 (B) phản hồi `absent` trùng byte với `ABSENT_RESPONSE`.
  - `seed` và `sources` trong `worker-status.json` khớp manifest ở 36/36 run mỗi gói.
- **Seed retry.** `expected_seed` tính lại đúng như `retry_seed` (`smoke-worker.py:44-46`). Attempt 0 dùng seed của lượt.
- **Giới hạn của retry.** Retry tính vào trần 160 request và không có request thứ 161. Sau 3 lần hỏi lại thì dừng. `HarnessStop` kế thừa `BaseException`, nên tenacity của tác giả (mặc định chỉ retry `Exception`) không retry nó. Lỗi finish_reason, HTTP khác 5xx, context overflow và query ngoài cửa sổ đều dừng ngay, không đi vào nhánh retry.
- **Resume.** Run `running` được chạy lại, phần dở được cất sang `.previous-N`. Run `passed` hoặc `failed` bị bỏ qua. Dọn process chạy ở mọi đường thoát trong `run_once`. RR-7 là hành vi đã chốt, không phải lỗi.

## 2. Lỗi, xếp theo ảnh hưởng

### F1. Sự kiện retry ghi trước khi biết retry có được gửi, nên harness báo lỗi toàn vẹn giả

- **Vị trí.** `smoke-worker.py:236-238` ghi `malformed_tool_call_retry` rồi `continue`. Ở đầu vòng lặp, `:193-195` kiểm deadline và ngân sách, có thể dừng trước khi request được gửi. `analyze-missing-source-results.py:48-50` so số sự kiện retry với số request có `attempt > 0`.
- **Điều kiện kích hoạt.** Model trả tool call sai định dạng ở request 159 hoặc 160. Vòng 1 có 2 lượt `no_metric` hết 160 request, nên đường này có thật ở vòng 2.
- **Mong đợi.** Theo dòng quyết định 2026-10-29, hết ngân sách là dừng hợp lệ và mỗi lần retry đều được ghi. Một lượt như vậy là lượt failed sạch, integrity `ok`.
- **Thực tế.** Gọi `Guard.post` thật qua session giả, bắt đầu từ count = 158. Chuỗi sự kiện: request 159, retry, request 160, retry (next_attempt = 2), fatal "budget exhausted". Kết quả `check_run`: `(2, 0, 2, ['retry events do not match retried requests'])`. Biến thể deadline chỉ xảy ra trong khoảng hẹp giữa `check()` ở `:215` và đầu vòng lặp kế tiếp.
- **Repro.** `worker-retry/repro_worker_retry.py`, kịch bản 1; `analyzer-denominator/repro/r05_retry_budget_integrity.py`.
- **Ảnh hưởng.** Điểm số không đổi, vì lượt failed tính 0. Nhưng `integrity_problems` của vòng 2 sẽ không sạch, trái với câu "kiểm toàn vẹn sạch" mà báo cáo dùng làm bằng chứng.
- **Test.** `test_malformed_tool_call_retries_count_against_the_request_budget` (`test-kaggle-harness.py:189`) tạo đúng chuỗi sự kiện này nhưng chỉ assert phía worker.

### F2. Lượt pass mà không có điểm, và lượt pending, bị tính 0 mà không có cờ

- **Vị trí.**
  - `kaggle-runtime.py:612-623`: stage F chấm điểm tuần tự với `check=True`. Một lần `evaluate.py` lỗi là dừng cả vòng, các lượt pass phía sau không có `author-score.txt`.
  - `analyze-missing-source-results.py:79` và `:88-91`: lượt thiếu điểm được gán 0, `status.json` không được đọc.
  - `:156-166`: summary không có trường đếm lượt pass mà thiếu điểm.
- **Điều kiện kích hoạt.** Scorer lỗi hoặc quá 60 giây ở một lượt; hoặc phiên dừng trước khi mọi lượt có trạng thái cuối.
- **Mong đợi.** Mục 6.3 tính 0 cho lượt failed và yêu cầu "ghi riêng". Lượt pass mà không được chấm không phải lượt failed, nên phải được đếm riêng hoặc khiến phân tích bị từ chối.
- **Thực tế.** Fixture có 4 lượt pass với scorer lỗi và 1 lượt pending:
  - Status ghi `{'passed': 26, 'pending': 1}`.
  - `integrity_problems` chỉ liệt kê lượt pending.
  - Sàng lọc bỏ log ra `opens_direction: True` (ΔR@1 −0,556), dù fixture không có hiệu ứng thật nào.
- **Repro.** `analyzer-denominator/repro/r04_unscored_pending.py`; `runtime-resume/repro_stage_f_unscored.py`.
- **Ảnh hưởng.** Vòng 1 không bị: 22/22 và 14/14 lượt pass đều có điểm. Nếu xảy ra, vì stage F chấm theo thứ tự gói, một đoạn cuối gói bị 0 sẽ tạo chênh lệch giả giữa các điều kiện. Thêm nữa, resume không sửa được: mỗi lần resume lại tốn một phiên GPU (C, D) rồi lỗi đúng chỗ cũ.
- **Test.** Không có test.

### F3. Run trùng khóa không bị từ chối, và kết quả sàng lọc phụ thuộc thứ tự tham số

- **Vị trí.** `analyze-missing-source-results.py:99`: dict `by` ghi đè khi trùng khóa. `:150` nối dòng từ mọi cặp zip+manifest. `:161-162`: `by_condition` lấy trung bình trên mọi dòng.
- **Điều kiện kích hoạt.** Chạy vòng 1 và vòng 2 của cùng một gói trong một lệnh. Manifest r1 và r2 có danh sách run giống hệt nhau (36/36 run_id), và quyết định 2026-10-29 yêu cầu báo vòng 1 cạnh vòng 2. Hoặc truyền cùng một cặp hai lần, hoặc một case có hai trace.
- **Mong đợi.** Từ chối khi `run_id` hoặc `(case, seed, condition)` bị trùng.
- **Thực tế.**
  - Thứ tự r1 rồi r2: ΔR@1 0,0, `opens_direction: False`.
  - Thứ tự r2 rồi r1: ΔR@1 −1,0, `opens_direction: True`.
  - Trong cả hai trường hợp, `by_condition` đếm 12 lượt mỗi điều kiện, gộp cả hai vòng. `integrity_problems` vẫn rỗng.
  - Khi một case có hai trace, analyzer âm thầm bỏ một trace.
- **Repro.** `analyzer-denominator/repro/r03_duplicates.py`.
- **Ảnh hưởng.** Vòng 1 không bị, vì A và B không chung case. Rủi ro gần nhất là khi so r1 với r2. Mọi ZIP đều tên `rclagent-smoke-results.zip`, nên cột `results_zip` không phân biệt được vòng hay gói.
- **Test.** Không có test.

### F4. ZIP không được gắn với manifest hoặc bundle, và thiếu điều kiện thì đọc như "không có hiệu ứng"

- **Vị trí.** `analyze-missing-source-results.py:66-79`: không đọc `progress['bundle_sha256']`; run có trong ZIP nhưng không có trong manifest bị bỏ qua. `:103-130`: thiếu cặp thì bỏ qua mà không báo.
- **Điều kiện kích hoạt.** Ghép ZIP với manifest sai, hoặc manifest thiếu một điều kiện.
- **Thực tế.**
  - ZIP A vòng 1 với manifest A-r2 (bundle `ddb43de4…`) được nhận, số liệu đúng nhưng mang nhãn vòng sai.
  - `progress.json` có `bundle_sha256` là 64 số 0 vẫn ra integrity `ok`.
  - Thiếu điều kiện `no_metric` thì so sánh bỏ metric ra `seeds: 0`, ΔR@1 0, `opens_direction: False`. Đọc như vậy giống một kết quả "không có hiệu ứng".
  - Ghép ZIP B với manifest A thì lộ rõ: 36 lượt pending, 36 dòng "no events".
- **Repro.** `analyzer-integrity/scripts/repro_wrong_manifest_and_retry_stop.py` (a2, a3) và `repro_analyzer.py` (§1, §2, §12); `analyzer-denominator/repro/r07_zip_manifest_mismatch.*`.
- **Ảnh hưởng.** Vòng 1 không bị. Đây là lỗ hổng truy nguồn cho vòng 2.

### F5. Tool server không kịp sẵn sàng thì không bị dừng, và run sau dùng nhầm dữ liệu của trace trước

- **Vị trí.** `kaggle-runtime.py:568-572`: `start_tools` gọi `proc.start` rồi `wait_ready`; nếu `wait_ready` lỗi, process không bị dừng. `:597-604`: khối try/finally dừng tool server chỉ bắt đầu sau khi `start_tools` trả về. `:285-298`: `wait_ready` không biết process nào đang trả lời.
- **Điều kiện kích hoạt.** Tool server cần quá 90 giây để trả lời `/search_span`.
- **Mong đợi.** Server lỗi bị dừng trước khi run được ghi failed.
- **Thực tế.** Dùng `wait_ready` thật:
  - Server cũ vẫn giữ cổng 5000.
  - Server của run kế tiếp không bind được cổng và thoát với mã 1.
  - Nhưng `wait_ready` nhận HTTP 200 từ server cũ, nên trả "ready". Probe trả về `DATA_ROOT=trace-OLD`.
- **Repro.** `runtime-resume/repro_tool_server_orphan.py`.
- **Ảnh hưởng.** Vòng 1 không bị: không run nào timeout lúc khởi động. Nếu xảy ra và run kế tiếp dùng trace khác, các câu trả lời `search_span` và `search_traces` sẽ âm thầm lấy từ trace sai. `validate_query` chỉ kiểm timestamp của log và metric, nên không chặn được. Mọi run sau trong lô đều thừa hưởng server cũ này.
- **Test.** Không có test.

### F6. Kiểm seed của retry tự tham chiếu, và báo cáo nói mạnh hơn những gì code kiểm

- **Vị trí.** `analyze-missing-source-results.py:33-38`, `:45`, `:48-50`.
- **Thực tế.** Seed kỳ vọng được dựng từ chính `retry_of` và `attempt` ghi trên request đó. Vì vậy các log sau vẫn ra integrity `ok`:
  - `retry_of=99` với seed tính theo 99.
  - Dãy attempt 0, 2, 5.
  - Sự kiện có `next_seed=12345` khác seed thật đã gửi.
- **Repro.** `analyzer-integrity/scripts/repro_analyzer.py` (§3–§5).
- **Ảnh hưởng.** Worker hiện ghi các trường này đúng; test `:165-180` kiểm phía worker. Đây là lỗ hổng kiểm chứng, không phải số sai. Câu "tự tính lại seed của từng lần hỏi lại để kiểm" ở mục 5 của báo cáo kết quả nói mạnh hơn khả năng thật của code.

### F7. Lệnh dừng từ bên ngoài luôn đến trước deadline của worker, và events bị cụt làm hỏng cả phân tích

- **Vị trí.**
  - `kaggle-runtime.py:598-601`: trần 1.800 giây tính cả lúc khởi động tool server.
  - `:581-585` và `:255-271`: SIGTERM rồi SIGKILL.
  - `smoke-worker.py:458`: deadline của worker tính từ lúc worker đã load tokenizer, tức trễ hơn 5,1–5,7 giây (đo trên 72 run vòng 1).
  - Worker không có handler SIGTERM.
  - `analyze-missing-source-results.py:43`: `json.loads` từng dòng, không chịu được dòng hỏng.
- **Thực tế.** Run chạm 30 phút sẽ bị giết từ ngoài. Khi đó không có `worker-status.json`, không có sự kiện `fatal`, và có thể có request không kèm response. Nếu dòng cuối của `events.jsonl` bị cụt, analyzer dừng với `JSONDecodeError` cho **mọi** gói.
- **Repro.** Phần POSIX chỉ suy luận từ code (`os.killpg` không có trên Windows). Đo thời gian: `runtime-resume/timing.py`. Dòng cụt: `analyzer-denominator/repro/r08_truncated_events.py`.
- **Ảnh hưởng.** Điểm số không đổi, vì lượt quá hạn vẫn tính 0. Mất số liệu chẩn đoán: số token, số request, lý do fatal. Run dài nhất ở vòng 1 là 1.036 giây; vòng 2 có retry nên run có thể dài hơn. Việc bị giết từ ngoài đã xảy ra một lần ở v10.

### F8. Resume bằng output notebook cũ bị từ chối

- **Vị trí.** `kaggle-runtime.py:465-470`.
- **Điều kiện kích hoạt.** Làm theo thông báo ở `:653` và gắn output notebook cũ làm input. Output đó có cả `rclagent-smoke-results.zip` lẫn `run/progress.json`, đúng như cấu trúc của `runtime/kaggle-output-v13/rclagent-smoke/`.
- **Thực tế.** Lỗi `Attach at most one earlier result set; found 2`, phát ra trước khối `try`, nên phiên đó không có `status.json`.
- **Repro.** `runtime-resume/repro_import_kaggle_output_layout.py`.
- **Ảnh hưởng.** Chỉ về vận hành, và lỗi dừng an toàn. Cách tránh: chỉ gắn ZIP. Test `:498` chỉ phủ trường hợp có ZIP.

### F9. Log của attempt bị ngắt bị ghi đè hoặc không được mang sang phiên resume

- **Vị trí.** `kaggle-runtime.py:241-242` mở log ở chế độ `'wb'`. `:480-488` chỉ import `run/traces/` và `progress.json`.
- **Thực tế.**
  - Chạy lại trong cùng phiên thì `worker-<rid>.log` (chứa traceback) bị ghi đè.
  - Phiên mới không mang theo `status.json`, `error.txt` và log của phiên trước. ZIP cuối vì vậy không tự đủ bằng chứng.
- **Repro.** `runtime-resume/repro_processes_log_truncation.py`, `repro_resume_paths.py`.

### F10. Kiểm SHA256 dùng `assert`

- **Vị trí.** `analyze-missing-source-results.py:70`.
- **Thực tế.** Chạy với `python -O`, ZIP đã bị sửa vẫn được phân tích, mã thoát 0.
- **Repro.** `analyzer-integrity/scripts/repro_analyzer.py` (§14).
- **Ảnh hưởng.** Chỉ về vận hành. Không lệnh nào trong tài liệu dùng `-O`.

**Chưa có test cho `analyze-missing-source-results.py`.** Mọi lỗi F1–F4, F6, F7 (phía analyzer) và F10 đều không được test nào phủ.

## 3. Quyết định đã chốt (không phải lỗi)

- **Lượt failed tính 0, gồm cả lượt chạm trần do harness đặt** (mục 6.3; trần 4 vòng mỗi span giữ nguyên theo quyết định 2026-10-29). Hệ quả cần ghi vào báo cáo:
  - Ở A+B, 2/4 case "bị ảnh hưởng" khi bỏ metric đến hoàn toàn từ lỗi trần: `checkoutservice_mem_1` và `currencyservice_loss_3`.
  - Bỏ các khối (case, seed) có lỗi trần thì còn ΔR@1 −0,056, ΔMRR −0,1017, 2/3 seed, đúng 2 case. Cờ vẫn "đạt" nhưng chỉ sát ngưỡng MRR 0,10 và sát ngưỡng 2 case. Em đã tự tính lại con số này.
- **Resume khi bị ngắt** (RR-7): đúng theo docstring và test.
- **Không trích tool call từ text, và retry tính vào trần 160 request**: code tuân thủ.

## 4. Câu hỏi còn thiếu bằng chứng hoặc cần sếp quyết

1. **Q1, ước lượng của phép kiểm độ vững** (AD-4).
   - Số liệu ở mục 4 là trung bình gộp theo cặp. Dùng chính ước lượng của quy tắc sàng lọc (trung bình các trung bình theo seed) trên cùng các cặp pass thì kết quả khác:
     - Bỏ log: ΔR@1 −0,208. Con số này vượt ngưỡng 0,125; cờ vẫn "không đạt" chỉ nhờ tiêu chí ít nhất 2 case.
     - Bỏ metric: ΔR@1 −0,100.
   - Câu "mất log gần như không ảnh hưởng" vì vậy phụ thuộc vào cách tính. Seed 28 chỉ có 2 cặp.
   - Phép kiểm này không có script trong repo.
   - Cả hai cách đều lọc theo kết quả, vì chỉ giữ các cặp mà cả hai lượt đều pass.
2. **Q2.** Báo cáo có nên nêu rõ những case nào bị ảnh hưởng do lỗi trần, và biên MRR −0,1017 ở mục 3 không?
3. **Q3, chiều của thay đổi khi R@1 và MRR lệch nhau** (AD-7, `analyze:114-115, :125`).
   - Một seed được tính là "giảm" khi R@1 *hoặc* MRR giảm, kể cả khi chỉ số đã kích hoạt ngưỡng lại tăng.
   - Một case có R@1 tăng nhưng MRR giảm ≥ 0,10 bị xếp là "up".
   - Mục 6.3 không nói chỉ số nào quyết định chiều. Dữ liệu vòng 1 không gặp trường hợp này.
4. **Q4.** Lượt có lỗi toàn vẹn (seed hoặc source sai) vẫn được chấm và vẫn vào phép sàng lọc (AI-6). Lượt đó nên bị loại, chặn kết luận, hay chỉ ghi lại?
5. **Q5.** Kiểm source chỉ so nhãn mà worker chép từ cờ dòng lệnh (AI-7). Có nên kiểm luôn byte của phản hồi `absent` và đối chiếu `worker-status.json` với manifest không? Vòng 1 đã được kiểm tay và sạch.
6. **Q6, lỗi mạng giữa chuỗi retry** (WR-2).
   - Khi gặp 5xx hoặc lỗi kết nối, tenacity gọi lại `post` từ attempt 0, với seed của lượt và `first_number` mới.
   - Trong trường hợp xấu nhất, một lời gọi logic tốn 12 request và 9 sự kiện retry.
   - Quyết định 2026-10-29 ghi "HTTP failures stay fatal", nhưng harness vẫn giữ 3 lần retry mạng của tác giả. Cần chốt hai lớp retry này kết hợp với nhau thế nào. Vòng 1 có 0 lỗi mạng.
7. **Q7, synthesizer không gọi `print_results`** (WR-3, `smoke-worker.py:86-87` và `:324-325`).
   - Không gọi lần nào thì được retry như tool call sai định dạng.
   - Gọi hai lần trở lên thì dừng ngay.
   - Danh sách trong quyết định (cú pháp rò ra dạng text, schema, id) không có trường hợp "không có call nào".
8. **Q8, marker `Action:` khi không có tool** (WR-4, `smoke-worker.py:100-102`).
   - Khi request không mời tool nào, một câu trả lời JSON hợp lệ có chứa chuỗi `Action:` vẫn bị hỏi lại.
   - Không nên bỏ hẳn phép kiểm khi `tools=None`, vì test `:165` cố ý phủ trường hợp `<tool_call>` rò ra lúc không có tool.
   - Vòng 1 có 0/1.034 trường hợp như vậy.
9. **Q9, vLLM chết giữa một run** (RR-6). Run đang chạy bị ghi `failed` vĩnh viễn và tính 0, dù nguyên nhân là hạ tầng chứ không phải model. Các run sau vẫn pending. Có nên để run đó chạy lại khi resume không?

## 5. Sửa tối thiểu đề xuất

Thứ tự ưu tiên cho lần chấm vòng 2 tới. Mỗi bước nên kèm một test CPU trong một file test mới cho analyzer.

1. **Analyzer, F1.** Chấp nhận đúng một sự kiện retry cuối không có request tương ứng khi sự kiện kế tiếp là `fatal` vì hết ngân sách hoặc deadline. Cách khác là chuyển việc ghi sự kiện retry trong worker xuống sau khi đã kiểm deadline và ngân sách. Cách này đổi vòng 2 đang chạy, nên ưu tiên sửa phía analyzer.
2. **Analyzer, F3, F4, F10.**
   - Từ chối khi `run_id` hoặc `(case, seed, condition)` bị trùng.
   - Yêu cầu `progress['bundle_sha256']` bằng file `.sha256` của bundle cạnh manifest, và tập khóa trong progress bằng tập `run_id` của manifest.
   - Yêu cầu đủ 3 điều kiện × 3 seed cho mỗi case, nếu không thì đánh dấu so sánh là không đánh giá được.
   - Thêm cột `bundle_sha256` vào `runs.csv`.
   - Thay `assert` bằng `raise`.
3. **Analyzer, F2, F7.** Đếm riêng `unscored_passed` và `pending`. Đọc `run/status.json` và đánh dấu kết quả sàng lọc là tạm thời khi phiên chưa `passed`. Dòng events hỏng thì ghi thành lỗi toàn vẹn của run đó, thay vì dừng cả phân tích.
4. **Analyzer, F6.** Duyệt request theo thứ tự và kiểm: `retry_of` bằng số của request attempt 0 gần nhất; `attempt` tăng liên tục và không quá 3; `next_seed` của sự kiện retry bằng seed của request kế tiếp.
5. **Runtime, F5.** Trong `start_tools`, khi `wait_ready` lỗi thì gọi `proc.stop(child)` rồi raise lại. Gọi `assert_free_port(5000)` trước mỗi lần khởi động tool server.
6. **Runtime, F2.** Chấm từng run trong try riêng, ghi trạng thái scorer của từng run, và chỉ báo stage F lỗi sau khi đã chấm hết.
7. **Runtime, F7–F9.**
   - Cho trần ngoài thêm khoảng đệm, ví dụ 30 giây, hoặc truyền deadline tuyệt đối vào worker.
   - Mở log ở chế độ append hoặc cất log cũ sang `.previous-N`.
   - Khi import, mang theo `status.json`, `error.txt` và log của phiên trước.
   - Khi gắn cả ZIP lẫn `run/` cùng thư mục cha, chỉ dùng ZIP.

Sửa runtime (bước 5–7) đổi `kaggle-runtime.py`, nên phải dựng lại gói. Không nên sửa trong lúc vòng 2 đang chạy. Sửa analyzer (bước 1–4) không đụng tới gói, có thể làm trước khi tải kết quả vòng 2.

## Câu hỏi chưa giải quyết

- Q1–Q9 ở mục 4.
- F7 và F5 chưa chạy được thật trên POSIX hoặc Kaggle. F7 dựa trên code và thời gian đo được; F5 đã tái hiện bằng process thật trên Windows, nhưng chưa kiểm hành vi giữ cổng của Linux.
- Chưa kiểm cách Kaggle gắn output notebook làm input, tức có giải nén ZIP hay không (F8).
- Vòng 2 chưa có kết quả, nên chưa biết F1 hoặc F7 có thực sự xảy ra hay không.
