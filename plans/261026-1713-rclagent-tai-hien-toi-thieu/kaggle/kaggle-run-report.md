# Nhật ký chạy Kaggle GPU — 2026-10-26

Notebook private: https://www.kaggle.com/code/siinn1706/rclagent-one-trace-gpu-smoke-261026 . Dataset private: https://www.kaggle.com/datasets/siinn1706/rclagent-one-trace-smoke-261026 . Metadata đọc lại xác nhận private, GPU và Internet bật.

## Version 1: dừng trong setup, chưa có model request

- GPU thật: 2 × Tesla T4, mỗi thiết bị 15.360 MiB; chỉ chọn GPU 0. VRAM trống quan sát 14.912 MiB/thiết bị. Driver 580.178.04, compute capability 7.5.
- Host RAM: MemTotal 32.869.296 KiB, MemAvailable 31.625.160 KiB tại A. Đĩa trống `/tmp`: 1.126.141.259.776 byte; `/kaggle/working`: 20.940.472.320 byte.
- Python thật: 3.13.15, base PyTorch 2.11.0+cu128 / CUDA 12.8. Đây là base image, chưa phải môi trường vLLM cô lập.
- Notebook chọn context 16.384, FP16, một GPU, concurrency=1; các giới hạn 160 request/1.800 giây và output 512/1.024 token không đổi.
- Lỗi B: `venv.EnvBuilder(with_pip=True)` thất bại tại `python3 -m ensurepip --upgrade --default-pip`, exit 1. Chưa tới C; không tải/nạp model, không mở server inference hoặc tool server, không chạy D/E/scorer.
- Notebook đã tự xuất gói lỗi. Artifact: `kaggle-setup-v1-error-results.zip`, SHA256 `7a25a8da97f12128c29da66cd32015458b23095bcf8863b6e479388d281ed9c8`. Log đầy đủ và environment/settings nằm trong `runtime/kaggle-output-v1/`.

## Version 2: tiếp tục setup sau sửa venv

Đã sửa riêng bootstrap: tạo bare venv không gọi ensurepip, dùng [pip --python](https://pip.pypa.io/en/stable/topics/python-option/) cài pip 25.2 vào venv, rồi cài các pin như cũ. Không thay thư viện base, backbone, revision, prompt/tool/thuật toán, trace hoặc giới hạn. Đây là sửa setup trước inference, không phải retry theo nhãn/kết quả model.

Dataset version 3 và notebook version 2 đã được Kaggle chấp nhận. Kết quả thực tế: B đã qua, cài vLLM 0.10.2 / PyTorch 2.8.0+cu128 / Transformers 4.55.4 / pandas 2.2.3 trong venv, CUDA available. Model revision chính xác đã tải và hash từng file được ghi ở `run/model-files.json`.

C dừng trước server ready: SchedulerConfig của vLLM V0 từ chối `max_num_batched_tokens=2048 < max_model_len=16384` khi chưa bật chunked prefill. Đây là lỗi tham số startup của wrapper; không phải kết quả của RCLAgent hoặc backbone. `run/status.json` ghi `protocol=0`, `trace=0` model requests; scorer không chạy. `run/processes.json` xác nhận process vLLM exit 1. RSS đỉnh lấy mẫu của process startup là 1.866.383.360 byte; chưa có VRAM inference đo được, không ghi bằng 0.

Gói lỗi: `kaggle-setup-v2-error-results.zip`, SHA256 `c4cb461fed62ed70e29334865ba49cdfa740185531804520c03e4e71744d5323`. Log có thêm cảnh báo sitecustomize thiếu wrapt; cảnh báo không phải điểm abort, traceback cuối là SchedulerConfig.

## Version 3: sửa tham số startup, các trần giữ nguyên

Theo [source SchedulerConfig v0.10.2](https://github.com/vllm-project/vllm/blob/v0.10.2/vllm/config/scheduler.py), bật `--enable-chunked-prefill`. Giữ batch 2.048, context 16.384 trên T4, output 512/1.024, request 160, thời gian RCLAgent 1.800 giây và cùng một backbone/revision. Chunked prefill chia tính toán input thành khối, không bỏ hoặc cắt token. Không tăng giới hạn để vượt lỗi.

Dataset version 4, notebook version 3 đã gửi tiếp sau khi xác nhận hai phiên trước chưa có model request. Bundle SHA256 `ba347b28130ad546389d2b2d34c8fc98f7f6d6887f6e5f53cf3d6df56b052cde`; notebook SHA256 lúc thực thi `8288973dbce92d3ef781213f211aae970a0f0b25cac2aa6bf16d550761b810f2`. Telemetry, code upstream và CPU parity report không đổi.

**Kết quả cuối: dừng ở D, không chạy lại.** A/B/C đã qua, model server thực sự ready trên một T4. Request tổng hợp đầu tiên của D nhận HTTP 500 sau 52,090 giây. Traceback nằm trong `vllm/attention/ops/prefix_prefill.py` → Triton `context_attention_fwd`, báo `OutOfResources: shared memory, Required: 98304, Hardware limit: 65536`. Đây là giới hạn shared memory của kernel attention trên phần cứng được cấp; chưa có phản hồi model hợp lệ để kiểm structured tool_calls, tool-role round trip hay print_results.

- Số model request gồm retry: D = 1, E = 0. HTTP 500 được coi là fatal nên không retry. Token usage không có, giữ null.
- Thời gian C đến cleanup/export: 157,095 giây. Chưa có thời gian RCLAgent E vì E không được bắt đầu.
- Đỉnh lấy mẫu: tổng RSS các process sở hữu 10.266.951.680 byte (9,562 GiB); GPU 0 là 12.674 MiB (12,377 GiB). Không cộng VRAM GPU 1; không diễn giải shared-memory error thành thiếu global VRAM. Các giới hạn đo lấy mẫu/RSS cộng trang chia sẻ vẫn áp dụng.
- Không khởi chạy `tools-telemetry` hoặc `worker-trace`, không đọc nhãn để chấm/retry. Chỉ tool server tổng hợp đã khởi tạo.
- Cleanup đã ghi: vLLM exit 0 sau shutdown, tool server tổng hợp exit -15, worker protocol exit 1; mọi PID root được theo dõi đều có exit status. Luồng CLI đọc live log cũng đã kết thúc và đóng owned process group.
- Đã xác minh ZIP native bằng file .sha256 tải từ Kaggle, số request trong events.jsonl khớp worker-status và parent status. Input manifest cùng mọi file đã được Kaggle kiểm hash đúng.

Gói kết quả: `rclagent-kaggle-gpu-results.zip`, 24.323 byte, SHA256 `fb220dc733203da6acf564bc6b3198ffae9b48e85f4091d5c52dfe479cf84e9b`. Tóm tắt máy đọc: `kaggle-native-summary.json`. Log đầy đủ trong ZIP, gồm `run/vllm.log`, `run/protocol/events.jsonl`, status, resources, process exits, model-file hashes và pip freeze.

Notebook bàn giao được thêm ghi chú về kết quả native sau khi dừng; code cell được so nguyên văn với source version 3 tải từ Kaggle. Hash hiện tại của file có chú thích nằm trong `package-validation.json`; không xem file được chú thích là một lượt GPU mới. Không cập nhật config chạy sau lỗi D, không thay backbone, tăng trần hoặc viết text parser để vượt gate.

## Chưa xác minh sau version 3

Tool-calling thật chưa qua gate D; trace 33 span chưa chạy với LLM và scorer của ca chưa được gọi. Chưa có kết quả accuracy, Table I, H1, confidence cuối hoặc nghiên cứu thiếu telemetry. Bước tiếp theo phải giải quyết tương thích attention backend/GPU và được quyết định thành một lần thử mới; lượt này dừng theo đúng điều kiện D trong yêu cầu.

## Version 4–5: yêu cầu ak-fix tiếp theo

Theo yêu cầu sửa lỗi mới của người dùng, đã vá đúng launch tile của dependency vLLM cho Turing, giữ source gốc/diff/hash. Version 4 tái hiện lỗi kernel gốc và qua 15 kiểm số học GPU; sau đó bị chặn trước model bởi cache Python ngoài manifest. Đã sửa regression bytecode, không nới allowlist.

Version 5 qua A/B/C và gate D: 3 model requests HTTP 200, structured tool_calls/role=tool/print_results và kiểm trường request đạt. E dừng sau 2 requests (~24,943 giây), vì model yêu cầu cartservice ngoài trace/query domain đóng gói khi đang kiểm root frontendservice. Hai query đó bị chặn trước thực thi; chưa có RCA cuối hoặc chấm. Không mở rộng dữ liệu/prompt/tool hoặc đổi backbone để retry.

Archive mới: `rclagent-kaggle-repair-v5-results.zip`, SHA256 `212b8fb3058db7d11e1de1fabae0e80b93c4c1ffa06e6b69be0fe8b7e0f82141`. Toàn bộ PID root đã có exit status và log-reader đã đóng. Chi tiết nguyên nhân, bản vá, phiên bản/hash, token/resource, phạm vi review và giới hạn hiện tại ở [repair-report.md](repair-report.md); dữ liệu máy đọc ở `kaggle-repair-v5-summary.json`. Bản sửa kernel đã kiểm native; smoke end-to-end vẫn bị dừng ở E.
