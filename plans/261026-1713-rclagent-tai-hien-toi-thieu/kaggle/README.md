# RCLAgent: smoke test một trace trên Kaggle GPU

Phạm vi: kiểm khả năng chạy RCLAgent với một backbone thay thế, giữ suy luận theo span, gộp đệ quy và tổng hợp. Không đo độ chính xác phương pháp, không chạy cả 90 ca, không triển khai H1/IM1/R-a. Không chạy LLM trên Windows, không commit/push.

**Kết quả bản sửa:** version 5 đã qua kiểm kernel GPU và gate D với 3 model requests. E dừng sau 2 requests vì model hỏi `cartservice`, ngoài trace/domain dữ liệu đóng gói; chưa có kết quả cuối hoặc chấm. Các process đã dọn. Xem `repair-report.md`, `kaggle-repair-v5-summary.json` và `rclagent-kaggle-repair-v5-results.zip`. Notebook có chú thích kết quả; code cell khớp source version 5. Các phiên thất bại trước vẫn được giữ.

## File dùng trên Kaggle

- `rclagent-kaggle-smoke.ipynb`: notebook chạy tuần tự.
- `rclagent-kaggle-bundle.zip`: gói dữ liệu, code upstream bất biến và wrapper.
- `rclagent-kaggle-bundle.zip.sha256`: hash đối chiếu. Notebook đã nhúng hash này.
- `manifest.json`: nguồn, revision, danh sách tệp/hash/kích thước.
- `cpu-equivalence.json`: đối chiếu các endpoint tool trên CPU với dữ liệu đầy đủ.
- `package-validation.json`: kiểm cấu trúc, phạm vi dữ liệu và notebook.

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
- E: một trace, concurrency=1, tối đa 160 model requests tính cả retry, 30 phút từ lúc khởi động tool server telemetry. Client gốc có tối đa 3 attempt/lời gọi; wrapper giới hạn 4 vòng tool/span. Không tăng trần, đổi backbone hoặc chọn lại trace.

## Dữ liệu và kiểm đối chiếu

Nguồn là [RCAEval RE2-OB, Zenodo record 14590730](https://zenodo.org/records/14590730). Hash bản ZIP gốc đã đối chiếu trong lượt Claude trước được lưu lại ở manifest; lượt này đọc các file ca thô và đầu ra preprocess của tác giả, ghi hash và đối chiếu chúng.

Ca train đã chọn trước: `checkoutservice_cpu_2`. Trace `68791e1f360d910bd01428c3cd9748ef`, root span `6752e26884a7fee8`, đúng 33 span. Chọn theo trace dài nhất trong 5 trace tác giả đã chọn của ca train đã xác định trước; không dùng kết quả model hoặc nhãn để chọn.

Metric dùng toàn bộ KPI phù hợp trong baseline ±1.200 giây và cửa sổ tính ±600 giây theo code tác giả, từ `simple_metrics.csv` là mặc định preprocess upstream. Không chỉ giữ metric có vẻ bất thường. Các dòng metric được chép nguyên văn từ CSV preprocess để tránh thay đổi số thực do ghi CSV lại. Log giữ đúng lọc severity và cửa sổ ±60 giây của upstream. Không sửa lỗi hoặc bổ sung tín hiệu của tool trong lần chạy này.

`input/` chỉ chứa telemetry và một dòng error trace; không có `_case_id`, fault type hoặc groundtruth. Nhãn duy nhất ở `scoring/groundtruth.csv`. Worker inference không đọc nhãn. Scorer chỉ chạy sau khi trace hoàn tất và model server đã dừng.

Query tool được giới hạn trong các cặp service/time thực sự thuộc trace đã chọn. Nếu model hỏi ngoài miền này, wrapper dừng và ghi lỗi thay vì trả dữ liệu thiếu. Đối chiếu CPU dùng nguyên thân hàm endpoint upstream, quét toàn bộ trace/log đã preprocess và toàn bộ metric dataframe. Kiểm cả equality của toàn bộ hàng baseline và byte equality của phản hồi HTTP. Báo cáo chi tiết nằm trong `cpu-equivalence.json`.

## Wrapper và giới hạn diễn giải

Wrapper nằm ngoài upstream: chuyển trường request, đếm request/retry, kiểm context/schema, vô hiệu text fallback, chặn lỗi vận hành khỏi các `except Exception` tiếp tục chạy của tác giả, và ghi progress. Không thay system prompt, heuristic, schema tool, công thức metric/log hoặc thứ tự gộp đệ quy.

`HarnessStop` kế thừa `BaseException` để lỗi vận hành dừng xuyên qua các khối catch-and-continue upstream. Worker theo dõi executor để hủy việc còn chờ khi dừng. Parent giữ PID/process group/port/cwd, chỉ dừng các process do chính lượt này khởi tạo; không chiếm cổng khác hoặc giết process người dùng.

RAM/VRAM là đỉnh **lấy mẫu** khoảng một giây của cây process được khởi chạy, có thể bỏ lỡ đỉnh ngắn. RSS cộng các process có thể tính lặp trang nhớ dùng chung. VRAM giữ riêng từng UUID GPU; khi không lấy được thì ghi unknown, không ghi bằng 0. Kernel bị SIGKILL/Restart không cho Python chạy `finally`; lỗi và Interrupt thông thường có cleanup.

Một trace không dùng best-of-traces. Scorer một ca là kết quả mô tả của smoke test, không phải ước lượng accuracy, tái hiện Table I hoặc confidence cho H1. Model trả sai không tự chứng minh phương pháp gốc kém.

## Xác minh và kết quả thực tế

Các kết quả CPU và bản đóng gói được ghi trong `cpu-equivalence.json`, `package-validation.json` và `preparation-report.md`. Kiểm bằng fixture tổng hợp chỉ xác minh đường code, không chứng minh model thật gọi tool đúng. Kết quả Kaggle thực tế, nếu có, được ghi riêng trong `kaggle-run-report.md` cùng URL phiên và log tải về.
