# RCLAgent: smoke test và chạy theo lô trên Kaggle GPU

Phạm vi: kiểm khả năng chạy RCLAgent với một backbone thay thế, giữ suy luận theo span, gộp đệ quy và tổng hợp. Không đo độ chính xác phương pháp, không chạy cả 90 ca, không triển khai H1/IM1/R-a. Không chạy LLM trên Windows, không commit/push.

**Kết quả mới nhất (version 8, 2026-10-27):** chạy hết end-to-end. Guard nay cho qua query có cửa sổ endpoint nằm hoàn toàn ngoài khoảng dữ liệu đầy đủ (ghi trong `selection.json`); query gõ sai của version 7 lặp lại ở request 60 và nhận phản hồi rỗng như tool tác giả. E chạy 106 requests HTTP 200 trong 1.332,9 giây, prompt lớn nhất 6.444 token; scorer tác giả trên một trace cho R@1 = 1/1 (`checkoutservice`). Đây là kết quả mô tả một trace, có ngân sách `search_logs`, không so trực tiếp với Table I. Xem `kaggle-repair-v8-summary.json`, `rclagent-kaggle-repair-v8-results.zip` và [report](../../reports/run-261027-1330-rclagent-kaggle-v8-guard-full-data-range.md).

**Version 7 (2026-10-27):** có ngân sách `search_logs` 2.048 token. Query `cartservice` ở root span được rút gọn từ 124.953 xuống 454 token, và E chạy tiếp 60 requests (27/33 span qua self-state, prompt lớn nhất 1.719 token). E dừng ở request 60 vì model gõ timestamp metric `1808475368747`, ngoài cửa sổ gói; guard chặn, dù tool tác giả trên dữ liệu đầy đủ sẽ trả "No matching records found.". Chưa có kết quả cuối hoặc chấm; process đã dọn. Xem `kaggle-repair-v7-summary.json`, `rclagent-kaggle-repair-v7-results.zip` và [report](../../reports/run-261027-1235-rclagent-kaggle-v7-tool-result-budget.md).

**Version 6 (2026-10-27):** gói theo cửa sổ thời gian đã cho query `cartservice` chạy và trả đúng dữ liệu đầy đủ. E dừng sau 2 requests vì request thứ ba cần 126.088 token, vượt context 16.384; không cắt ngữ cảnh. Chưa có kết quả cuối hoặc chấm; process đã dọn. Xem `kaggle-repair-v6-summary.json`, `rclagent-kaggle-repair-v6-results.zip` và [report](../../reports/fix-261027-0929-rclagent-query-window-smoke.md). Version 5 dừng ở guard cặp service/giây cũ (`repair-report.md`, `kaggle-repair-v5-summary.json`). Các phiên thất bại trước vẫn được giữ.

**Chạy nhiều trace train (chưa chạy GPU).** Gói nay có thể chứa nhiều trace, mỗi trace một thư mục con `traces/<trace_id>/` với dữ liệu riêng, `selection.json`, `cpu-equivalence.json` và nhãn chấm `scoring/groundtruth.csv`. Mỗi gói con được đối chiếu endpoint gốc với dữ liệu đầy đủ như version 6–8.

- Dựng: `prepare-bundle.py NAME --pilot` (hoặc `prepare-bundle.py NAME TRACE_ID...`) ghi vào `runtime/package-NAME`, không đụng bản đang dùng. `refresh-package.py runtime/package-NAME` chép wrapper, ghi manifest và đưa gói đó thành `rclagent-kaggle-bundle.zip`, `manifest.json`; sau đó chạy `build-notebook.py` và `verify-package.py`.
- Pilot: 5 trace train, mỗi ca một trace, chọn theo phân vị số span (trừ trace smoke). Quy tắc chọn ghi trong manifest.
- Chạy: mỗi trace có tool server, trần 160 requests và 30 phút riêng. Trace dừng (guard, deadline, lỗi HTTP) được ghi `failed` kèm lý do trong `run/progress.json`, rồi lượt sang trace kế tiếp. Model server chết thì cả lượt dừng; các trace còn lại chờ. Chạy lại cell C–F, hoặc gắn ZIP kết quả cũ làm input, sẽ chạy tiếp các trace chưa xong của **cùng** bundle; trace đã xong không chạy lại.
- Chấm: scorer tác giả chạy riêng cho từng trace đã qua, trong `run/scoring/<trace_id>/`. `summarize-repair-run.py` đọc cả lượt một trace lẫn lượt theo lô.
- Ước lượng từ version 8 (40 giây/span): pilot 130 span cần khoảng 90 phút cho E. Trace 45 span ước khoảng 1.820 giây, sát hoặc vượt deadline 30 phút; nếu vượt, nó được ghi `failed`, không nới trần.

## File dùng trên Kaggle

- `rclagent-kaggle-smoke.ipynb`: notebook chạy tuần tự.
- `rclagent-kaggle-bundle.zip`: gói dữ liệu, code upstream bất biến và wrapper.
- `rclagent-kaggle-bundle.zip.sha256`: hash đối chiếu. Notebook đã nhúng hash này.
- `manifest.json`: nguồn, revision, danh sách tệp/hash/kích thước.
- `cpu-equivalence.json`: đối chiếu các endpoint tool trên CPU với dữ liệu đầy đủ cho trace của version 8. Gói theo lô có một file như vậy cho mỗi trace, trong `traces/<trace_id>/`.
- `package-validation.json`: kiểm cấu trúc, phạm vi dữ liệu và notebook.
- `tool-result-budget-check.json`: kiểm CPU ngân sách `search_logs` trên gói và trên request đã làm version 6 dừng (`check-tool-result-budget.py`).

Chỉ tải notebook và ZIP lên Kaggle. Không tải cả thư mục dự án hoặc `runtime/`. Các script chạy Kaggle cần thiết, gồm patch và kiểm kernel, đã có sẵn trong ZIP và notebook.

## Chạy trong giao diện Kaggle

1. Tạo một **Dataset Private**, chỉ tải `rclagent-kaggle-bundle.zip` lên. Kaggle có thể tự giải nén ZIP; notebook hỗ trợ cả ZIP và dataset đã giải nén, kiểm hash manifest đã nhúng rồi kiểm mọi file bên trong. Không công khai dataset.
2. Import `rclagent-kaggle-smoke.ipynb` thành **Notebook Private**. Add Input dataset vừa tạo.
3. Bật **Internet** để tải thư viện và model từ nguồn chính thức. Notebook kiểm thiết bị được cấp, compute capability và VRAM từng GPU. Với T4 ×2, notebook chỉ dùng một T4; không cộng VRAM hai GPU. Cell B kiểm kernel gốc/bản vá trên dữ liệu tổng hợp trước khi cho phép C.
4. Chạy từ trên xuống: Bootstrap → A → B → C–F. B tạo venv trong `/tmp`, không thay gói có sẵn của Kaggle. C–F nằm cùng một cell để bảo đảm `finally` dọn process khi thành công, lỗi hoặc Interrupt thông thường.
5. Tải `/kaggle/working/rclagent-smoke/rclagent-smoke-results.zip` và file `.sha256` trong Output/Files. Khi A/B lỗi, vẫn có gói lỗi chuẩn bị. Khi C–F lỗi, gói chứa phần đã hoàn thành.

Notebook tạo `run-once.json` trước C. Không xóa marker để chạy lại hoặc đổi model sau khi xem nhãn/kết quả. Mọi lần chạy tiếp theo cần một quyết định mới. Nếu chưa chạy tới C và Kaggle cấp GPU không phù hợp, dừng tại A; chưa có model request nào.

## Cấu hình đã chọn

- Upstream: [LLM4AIOps/RCLAgent-V2](https://github.com/LLM4AIOps/RCLAgent-V2), commit `3052e7a6a9598d984ba1482f3dc41123c8823a99`. Các file đóng gói lấy trực tiếp từ Git object, giữ LICENSE MIT. Không có patch source upstream.
- Model: [Qwen/Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507), revision `cdbee75f17c01a7cc42f958dc650907174af0554`. Đây là bản Instruct non-thinking của tài khoản Qwen chính thức, không phải tên tag Ollama suy đoán.
- Server: vLLM `0.10.2`, engine V0, FP16, parser Hermes chính thức, localhost `127.0.0.1:8000`, một GPU, `max_num_seqs=1`. Bật chunked prefill với khối tối đa 2.048 token, không cắt ngữ cảnh; context giữ nguyên 16.384/32.768 theo VRAM. [Tài liệu tool calling v0.10.2](https://docs.vllm.ai/en/v0.10.2/features/tool_calling.html).
- Tương thích T4: chỉ đổi `BLOCK_M` của non-ALiBi prefix prefill trong vLLM thành 64 trên Turing; kiến trúc khác giữ 128. Ghim hash source wheel, giữ source gốc và diff trong `compatibility/` của ZIP kết quả. Cell B bắt buộc qua kiểm kernel GPU tổng hợp; source RCLAgent bất biến. Chặn bytecode cache để package giữ nguyên allowlist.
- Context: 16.384 token nếu VRAM thiết bị <22.000 MiB, 32.768 nếu ≥22.000 MiB. Output tối đa 512 token cho self-state/consolidation và 1.024 cho synthesizer. Input cộng phần output dự phòng vượt context sẽ dừng; không cắt ngữ cảnh.
- Sampling cố định: temperature 0,7; top_p 0,8; top_k 20; min_p 0; seed 20261026. Không hứa tái lập bit-for-bit giữa GPU/runtime.
- D: tối đa 8 model requests trên dữ liệu tổng hợp, tối đa 8 phút. Kiểm client gốc nhận structured tool_calls, thực thi search_logs, trả role=tool và print_results ≥10 mục. Đầu vào `enable_thinking=False` được chuyển thành `chat_template_kwargs`; trường lạ bị chặn trước server. D thất bại thì không nạp telemetry benchmark vào tool server.
- E: lần lượt từng trace của gói, concurrency=1, mỗi trace tối đa 160 model requests tính cả retry, 30 phút từ lúc khởi động tool server telemetry của trace đó. Client gốc có tối đa 3 attempt/lời gọi; wrapper giới hạn 4 vòng tool/span. Không tăng trần, đổi backbone hoặc chọn lại trace.

## Dữ liệu và kiểm đối chiếu

Nguồn là [RCAEval RE2-OB, Zenodo record 14590730](https://zenodo.org/records/14590730). Hash bản ZIP gốc đã đối chiếu trong lượt Claude trước được lưu lại ở manifest; lượt này đọc các file ca thô và đầu ra preprocess của tác giả, ghi hash và đối chiếu chúng.

Ca train đã chọn trước: `checkoutservice_cpu_2`. Trace `68791e1f360d910bd01428c3cd9748ef`, root span `6752e26884a7fee8`, đúng 33 span. Chọn theo trace dài nhất trong 5 trace tác giả đã chọn của ca train đã xác định trước; không dùng kết quả model hoặc nhãn để chọn.

Metric gồm mọi KPI của mọi service trong ±1.200 giây quanh các giây của trace (baseline của tool tác giả; cửa sổ tính ±600 giây nằm trong đó), từ `simple_metrics.csv` là mặc định preprocess upstream. Không chọn theo service hoặc theo độ bất thường. Các dòng metric được chép nguyên văn từ CSV preprocess để tránh thay đổi số thực do ghi CSV lại. Log gồm mọi dòng được tool tác giả phục vụ (sau lọc INFO/DEBUG) trong ±60 giây quanh các giây đó. Dữ liệu đầy đủ trong các cửa sổ này chỉ thuộc ca `checkoutservice_cpu_2`. Không sửa lỗi hoặc bổ sung tín hiệu của tool.

`input/` chỉ chứa telemetry và một dòng error trace; không có `_case_id`, fault type hoặc groundtruth. Nhãn duy nhất ở `scoring/groundtruth.csv`. Worker inference không đọc nhãn. Scorer chỉ chạy sau khi trace hoàn tất và model server đã dừng.

Query tool nhận mọi `service_name` như tool tác giả; chỉ giây của timestamp (cách parse của endpoint gốc) phải nằm trong khoảng giây của trace đã chọn (`selection.json`, `query_window`). Endpoint gốc chỉ trả hàng trong ±1.200/±60 giây quanh giây đó, nên mọi service đều nhận đúng phản hồi của dữ liệu đầy đủ. Timestamp ngoài khoảng này làm wrapper dừng thay vì trả dữ liệu thiếu; tham số được kiểm cả ở URL thực gửi tới tool server. Đối chiếu CPU dùng nguyên thân hàm endpoint upstream, quét toàn bộ trace/log đã preprocess và toàn bộ metric dataframe, so equality toàn bộ hàng trong cửa sổ và byte của phản hồi HTTP trên lưới service × timestamp. Báo cáo chi tiết nằm trong `cpu-equivalence.json`.

Version 5 dừng vì bản trước chỉ cho các cặp service/giây của span; query `cartservice` hợp lệ theo tool tác giả bị chặn. Môi trường CPU để chạy harness và dựng gói: `runtime/harness-env` (Python 3.12.10, không dùng site-packages hệ thống, ghim theo phía Kaggle; lệnh tạo lại và danh sách đầy đủ ở `harness-requirements.txt`).

## Wrapper và giới hạn diễn giải

Wrapper nằm ngoài upstream: chuyển trường request, đếm request/retry, kiểm context/schema, vô hiệu text fallback, chặn lỗi vận hành khỏi các `except Exception` tiếp tục chạy của tác giả, áp ngân sách kết quả `search_logs`, và ghi progress. Không thay system prompt, heuristic, schema tool, công thức metric/log hoặc thứ tự gộp đệ quy.

**Ngân sách kết quả `search_logs` (sai lệch so với tác giả, từ version 7).** Dưới ràng buộc context 16.384 không cắt ngữ cảnh, mọi trace của 90 ca RE2-OB đều có query hợp lệ (`cartservice`) vượt context ngay vòng tool đầu. Theo quyết định của chủ dự án ngày 2026-10-27, `smoke-worker.py` áp [`tool-result-budget.py`](tool-result-budget.py) (phương án bậc thang) cho mọi kết quả `search_logs`. Kết quả ≤ 2.048 token, đếm bằng tokenizer đúng revision, được trả nguyên byte. Khi một phản hồi của model gọi n lần `search_logs`, mỗi kết quả nhận ⌊2.048 / n⌋ token, nên tổng một vòng vẫn ≤ 2.048; với n = 1 (mọi lượt version 7 và 8) không có gì đổi. Kết quả lớn hơn được rút gọn theo bước đầu tiên vừa ngân sách: gộp dòng trùng hệt, rồi gộp theo mẫu thông điệp, cuối cùng cắt theo ưu tiên severity, có dòng thông báo cho model. Bản gốc và bản model nhận đều ghi trong `events.jsonl` (`tool_result`, `tool_result_budget`). Metric không bị áp. Body không nhận dạng được hoặc không xếp vừa thì dừng. Thiết kế và số đo trên 450 trace: [report](../../reports/design-261027-1155-tool-result-budget.md). Kết quả của bản này không so trực tiếp với Table I.

`HarnessStop` kế thừa `BaseException` để lỗi vận hành dừng xuyên qua các khối catch-and-continue upstream. Worker theo dõi executor để hủy việc còn chờ khi dừng. Parent giữ PID/process group/port/cwd, chỉ dừng các process do chính lượt này khởi tạo; không chiếm cổng khác hoặc giết process người dùng.

RAM/VRAM là đỉnh **lấy mẫu** khoảng một giây của cây process được khởi chạy, có thể bỏ lỡ đỉnh ngắn. RSS cộng các process có thể tính lặp trang nhớ dùng chung. VRAM giữ riêng từng UUID GPU; khi không lấy được thì ghi unknown, không ghi bằng 0. Kernel bị SIGKILL/Restart không cho Python chạy `finally`; lỗi và Interrupt thông thường có cleanup.

Một trace không dùng best-of-traces. Scorer một ca là kết quả mô tả của smoke test, không phải ước lượng accuracy, tái hiện Table I hoặc confidence cho H1. Model trả sai không tự chứng minh phương pháp gốc kém.

## Xác minh và kết quả thực tế

Các kết quả CPU và bản đóng gói được ghi trong `cpu-equivalence.json`, `package-validation.json` và `preparation-report.md`. Kiểm bằng fixture tổng hợp chỉ xác minh đường code, không chứng minh model thật gọi tool đúng. Kết quả Kaggle thực tế, nếu có, được ghi riêng trong `kaggle-run-report.md` cùng URL phiên và log tải về.
