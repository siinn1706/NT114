# Sửa lỗi kernel prefix attention trên Kaggle T4

Trạng thái cuối: đã sửa lỗi kernel trên Kaggle T4 và lỗi cache do helper mới. Version 5 qua A/B/C/D; E dừng sau 2 requests vì model hỏi service ngoài domain của trace. Chưa có kết quả RCA cuối hoặc chấm. 4 kiểm nguồn, 14 kiểm harness và 15 kiểm số học GPU qua.

## Chẩn đoán

1. Lỗi thực tế của native version 3: `triton.runtime.errors.OutOfResources: out of resource: shared memory, Required: 98304, Hardware limit: 65536.` Request tổng hợp đầu tiên ở D nhận HTTP 500; E có 0 request.
2. Đường tái hiện: Tesla T4 SM75, FP16, vLLM 0.10.2 V0, XFORMERS, chunked prefill 2.048 token, Qwen3-4B-Instruct-2507 revision đã ghim; gửi request chat đầu tiên sau khi server báo ready.
3. Mong đợi: model trả structured tool_calls để client tác giả thực thi tool. Thực tế: kernel dừng trước khi trả bất kỳ phản hồi model hợp lệ nào.
4. Nguyên nhân: file `vllm/attention/ops/prefix_prefill.py` của wheel phát hành, dòng 920, đặt `BLOCK_M=128` cho nhánh không ALiBi; kernel này cần 96 KiB shared memory trên cấu hình T4 chỉ có giới hạn 64 KiB/block. `num_stages` vốn đã bằng 1, nên giảm stage không phải bản sửa khả dụng. Đây là giới hạn shared memory của kernel, không phải thiếu tổng VRAM để chứa model.
5. Điều kiện làm lộ lỗi: T4 chọn backend XFORMERS; chunked prefill đi qua `PagedAttention.forward_prefix` rồi kernel trên. Model nạp thành công không kiểm được kernel này vì bản chạy dùng eager và chưa sinh token ở health check.
6. Phạm vi ảnh hưởng: prefix prefill không ALiBi trên Turing trong venv riêng của notebook. RCLAgent, prompt/tool, dữ liệu, công thức baseline, context, sampling, retry và trần vận hành không đổi.

Đã đọc source đúng wheel PyPI, không dùng source tag khác làm bằng chứng thay thế: wheel SHA256 `e0cba6110483d9bf25c4402d8655cf78d366dd13e4155210980cc3480ed98b7b`; file kernel SHA256 `8055f9dc80be1727ac9255ac8a2e565ef08e3572325e0b69e170b2249b4b789a`. Wheel có 928 dòng; source tag GitHub có khác biệt nên patch buộc khớp hash wheel.

## Bản sửa và kiểm tra

`vllm-t4-compat.py` đổi duy nhất biểu thức launch thành `BLOCK_M=64 if IS_TURING else 128`. Grid đã tính `ceil(max_input_len/BLOCK_M)`, nên vẫn bao phủ mọi token. Giữ `BLOCK_N=64`, `num_stages=1` và toàn bộ kernel math. Lưu source gốc, unified diff và before/after hash vào `compatibility/` trong ZIP kết quả. Không sửa bản upstream RCLAgent.

`verify-t4-prefix-kernel.py` chỉ chạy GPU ở Kaggle, không nạp model hoặc telemetry. Một subprocess chạy kernel nguyên bản để tái hiện đúng lỗi 96/64 KiB trên T4; subprocess mới chạy bản vá và so với dense causal attention FP32. Có 15 trường hợp FP16, head size 128, GQA 32/8: query 1/63/64/65/127/128/129 với cached context 0/17, và query 2.048 với cached context 2.048; atol/rtol 1e-3, kiểm mọi hàng output hữu hạn. Dừng nếu lỗi không tái hiện như chẩn đoán, nguồn khác hash hoặc bản vá không qua số học.

3 kiểm nguồn chứng minh AST chỉ đổi một biểu thức, Turing dùng 64/kiến trúc khác dùng 128, source lạ bị từ chối, backup/diff đúng và patch idempotent. 14 kiểm harness cũ qua. CPU parity của telemetry giữ byte-identical, 86 endpoint responses khớp; không chạy LLM trên Windows.

## Lần kiểm native mới

Người dùng yêu cầu phân tích và dùng ak-fix sửa lỗi sau native version 3; version 4 là lần kiểm bản sửa trong cùng phạm vi được yêu cầu. Một model/revision, một trace, concurrency 1, E ≤160 requests gồm retry và ≤1.800 giây. D phải qua trước khi khởi động tool server benchmark. Không dùng kết quả/nhãn để chọn lại đáp án.

Notebook version 4 dùng bundle SHA256 `8612fd6a01f56f5bb666369720bf3f3a4f99b606d1df7879e39c2bfc4efc9c4c`, notebook SHA256 `2a056dbd0c04dd9b9d4faf23eca0e0961440d0fcd0b8a8a21dd98be834faf12b`. Dataset hiện version 6 và private; lần upload đầu báo lỗi đường dẫn upload-state của CLI Windows, lần dùng native Windows path thành công. Notebook tự kiểm hash manifest và mọi member; không tin version number thay cho nội dung.

Version 4: kernel nguyên bản tái hiện đúng lỗi shared memory; bản vá qua cả 15 trường hợp, sai số tuyệt đối lớn nhất `0.0002480149269104004` so với dense FP32, không có hàng output NaN. CUDA allocator peak của probe: allocated 415.894.016 byte, reserved 478.150.656 byte. Đây là bộ nhớ probe tổng hợp, không phải peak inference model.

Sau B, helper import tạo `package/__pycache__/vllm-t4-compat.cpython-313.pyc`. C gọi kiểm manifest lần nữa và đúng thiết kế từ chối file ngoài allowlist. Đây là regression do helper mới, xảy ra trước tải/nạp model: D=0, E=0 requests. Đã sửa bằng `sys.dont_write_bytecode=True` trong helper và `PYTHONDONTWRITEBYTECODE=1` cho process con; không nới manifest hoặc xóa cache để che lỗi. Test mới chứng minh bản cũ tạo cache và fail, bản sửa giữ nguyên tập file và pass.

Archive version 4: `rclagent-kaggle-repair-v4-results.zip`, SHA256 `4e1ab9d7462013640f000768ca4efb1261c19253c8102204575327c0a7873066`. Chi tiết `kaggle-repair-v4-summary.json`. Một native repair attempt thất bại được giữ trong `fix-state.json`, không reset bộ đếm.

Version 5 dùng dataset private version 7; bundle SHA256 `d26df6d13743f23e8b481aa09dea8920329b790effd2493f84fd62168a717f21`, notebook lúc thực thi SHA256 `f069cb20a05c83b02b41508495d6f13dfed0bbc589a015d76e8afdf2f036beeb`. Source version 5 đã tải lại từ Kaggle, code cell khớp nguyên văn file bàn giao và metadata xác nhận private/GPU/Internet. Notebook bàn giao sau đó chỉ thêm Markdown về kết quả, code không đổi; hash mới nằm trong `package-validation.json`.

## Kết quả native version 5

- Kernel: gốc tái hiện đúng lỗi, bản vá qua 15 kiểm số học. Lỗi shared memory ban đầu không còn tái hiện ở cả probe và model requests.
- D: passed, đúng 3 requests HTTP 200. Client gốc nhận structured tool_calls, gọi search_logs tổng hợp, model nhận role=tool và gọi print_results đúng schema. Chuyển enable_thinking và từ chối trường lạ qua kiểm.
- E: bắt đầu đúng graph 33 span. Request đầu gọi log/metric cho root frontendservice, nhận log rỗng và metric `No matching records found.` theo tool gốc. Request thứ hai yêu cầu hai tool cho `cartservice` tại timestamp `1708475368662`; cartservice không có trong trace/query domain đã đóng gói. Guard phát `Tool request outside the packaged service/time domain; refusing incomplete evidence` trước khi thực thi hai query ngoài domain. Không phải HTTP/backend lỗi, cũng không phải schema tool-call sai.
- E có 2 requests HTTP 200, dùng 1.925 prompt tokens + 170 completion tokens; thời gian từ E tới cleanup 24,943 giây. D có 858 prompt + 140 completion tokens. Tổng D+E 5 requests, 2.783 prompt + 310 completion tokens, không retry. C tới cleanup/export 134,822 giây. Các trần 160 requests/1.800 giây không bị tăng hoặc chạm.
- Chưa hoàn thành self-state đầu tiên, chưa gộp đệ quy với model tới kết quả cuối; chưa chạy scorer hoặc mở groundtruth để chấm. Fixture cũ chứng minh đường đệ quy, không chứng minh E native hoàn tất.
- Đỉnh lấy mẫu C–E: RSS cây process 9.158.025.216 byte (~8,529 GiB), GPU 0 là 13.232 MiB (~12,922 GiB). Không cộng VRAM GPU thứ hai. Phép đo khoảng 1 giây có thể bỏ lỡ peak ngắn; RSS có thể đếm lặp trang chia sẻ.
- Cleanup: vLLM exit 0, tools-synthetic -15, worker-protocol 0, tools-telemetry -15, worker-trace 1. Log-reader Windows exit 0 và owned process group đã đóng. Không để server/tunnel chạy nền.

Archive `rclagent-kaggle-repair-v5-results.zip`, SHA256 `212b8fb3058db7d11e1de1fabae0e80b93c4c1ffa06e6b69be0fe8b7e0f82141`; hash được so với file .sha256 xuất từ Kaggle. `kaggle-repair-v5-summary.json` đối chiếu request events/worker/parent counts, process exits, input hashes và code source đã tải lại. Hai native repair attempts được giữ nguyên, không reset hoặc biến phiên dừng thành pass.

Không sửa prompt/tool, đổi backbone, thêm text parser, mở rộng domain dữ liệu hoặc retry theo nhãn/kết quả để vượt lỗi E. Lỗi GPU đã sửa; smoke end-to-end chưa đạt. Một yêu cầu query ngoài domain của backbone thay thế không tự chứng minh phương pháp RCLAgent gốc kém.

## Review phạm vi sửa

Đã dùng ak-code-review trong cùng phiên, review source snapshot của patch/probe/runtime, packaging/build/validator, test và các caller legacy XFORMERS → PagedAttention → prefix kernel. Không có reviewer độc lập. AST regression xác nhận chỉ đổi biểu thức tile, API/schema và kernel math giữ nguyên; native D xác nhận client/tool protocol. Bytecode regression được tái hiện và sửa, manifest allowlist không nới. Không còn finding chưa xử lý trong phạm vi lỗi tương thích đã sửa; E dừng ngoài domain và GPU khác T4 chưa được chạy native là giới hạn xác minh được giữ rõ.
