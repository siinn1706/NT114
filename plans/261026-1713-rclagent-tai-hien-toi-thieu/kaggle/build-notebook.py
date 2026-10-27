"""Generate a self-contained Kaggle notebook bound to the actual bundle SHA256."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    archive = HERE / 'rclagent-kaggle-bundle.zip'
    bundle_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest_hash = hashlib.sha256((HERE / 'manifest.json').read_bytes()).hexdigest()
    source = (HERE / 'kaggle-runtime.py').read_text(encoding='utf-8')
    runtime_hash = hashlib.sha256(source.encode()).hexdigest()
    cells = []
    def markdown(text):
        cells.append({'cell_type': 'markdown', 'metadata': {}, 'source': text.splitlines(keepends=True)})
    def code(text):
        cells.append({'cell_type': 'code', 'metadata': {}, 'execution_count': None,
                      'outputs': [], 'source': text.splitlines(keepends=True)})
    markdown('''# RCLAgent: một trace trên Kaggle GPU

Notebook smoke test với backbone thay thế. Giữ nguyên code/prompt/tool tác giả tại
`3052e7a6a9598d984ba1482f3dc41123c8823a99`; giữ suy luận theo span và gộp đệ quy.
Chưa tái hiện Table I, chưa đo độ chính xác, chưa chạy H1/IM1/R-a.

**Trước khi chạy:** để notebook **Private**, tạo một dataset **Private** chỉ chứa
`rclagent-kaggle-bundle.zip`, rồi Add Input dataset đó. Bật **Internet** và GPU.
Cấu hình cố định này hỗ trợ GPU compute capability ≥7.5, ít nhất 13.000 MiB VRAM trống
trên **một** thiết bị; không hỗ trợ P100. Nếu được T4 ×2, chỉ dùng một T4.

Chạy các cell từ trên xuống. Cell C–F chỉ chạy **một lần**; lỗi sẽ dừng và xuất log.
Không tự xóa run-once.json để thử lại, đổi model hoặc tăng trần.
''')
    native_path = HERE / 'kaggle-native-summary.json'
    if native_path.exists():
        native = json.loads(native_path.read_text())
        markdown('''## Kết quả Kaggle thực tế đã ghi nhận

Version 3 đã nạp model trên **một Tesla T4**, qua A/B/C nhưng dừng ở D:
request tổng hợp đầu tiên nhận HTTP 500 do Triton attention kernel cần 98.304 byte
shared memory, phần cứng giới hạn 65.536 byte. Có **1 request tổng hợp, 0 request
trên trace benchmark**. Chưa xác minh tool_calls/round trip/print_results; chưa chạy E
hoặc scorer. Process đã được dọn và log đã xuất.

Theo yêu cầu sửa lỗi tiếp theo, bản này bổ sung patch tương thích vLLM có kiểm hash:
tile truy vấn 64 cho Turing, giữ 128 trên kiến trúc khác. Không sửa RCLAgent.
Cell B tái hiện lỗi kernel gốc rồi kiểm bản vá với dense attention FP32 trên GPU,
15 trường hợp gồm ranh giới tile và cached context. Chỉ qua kiểm này mới nạp model.
Kết quả version 3 là lịch sử thất bại. Kết quả bản sửa được ghi riêng khi có output native.
''')
    repair_path = HERE / 'kaggle-repair-v5-summary.json'
    if repair_path.exists():
        repair = json.loads(repair_path.read_text())
        assert repair['compatibility']['status']['status'] == 'passed'
        assert repair['phases']['protocol']['worker']['status'] == 'passed'
        assert repair['status']['status'] == 'failed' and repair['status']['stage'] == 'E'
        markdown('''## Kết quả bản sửa: Kaggle version 5

Đã kiểm thật trên một T4: kernel gốc tái hiện lỗi 96/64 KiB, bản vá qua 15 kiểm
dense attention FP32; lỗi cache Python của version 4 đã sửa. A/B/C và **D đạt**:
3 request tổng hợp HTTP 200, structured tool_calls, role=tool, print_results và
kiểm trường request đều qua.

**E dừng sau 2 model requests, khoảng 24,94 giây.** Khi đang kiểm root span
frontendservice, model yêu cầu search_logs và search_fluctuating_metrics cho
cartservice tại timestamp 1708475368662. Cartservice không thuộc trace/domain
đóng gói; guard chặn trước thực thi query. Chưa có kết quả cuối hoặc điểm chấm.
Server/process đã dọn; log và phần đã hoàn thành được giữ trong ZIP.

Đây là kết quả smoke bị dừng ở E, không phải pass end-to-end hoặc kết luận
về accuracy/phương pháp gốc. Không mở rộng dữ liệu, sửa prompt/tool hay chạy lại
để chọn đáp án. Code cell bên dưới khớp source version 5 đã chạy; chỉ thêm ghi chú.
''')
    code('''# Bootstrap chuẩn thư viện Python; chưa cài hay chạy model.
import hashlib, importlib.util, json
from pathlib import Path
EXPECTED_BUNDLE_SHA256 = ''' + repr(bundle_hash) + '''
EXPECTED_MANIFEST_SHA256 = ''' + repr(manifest_hash) + '''
RUNTIME_SOURCE = ''' + repr(source) + '''
assert hashlib.sha256(RUNTIME_SOURCE.encode()).hexdigest() == ''' + repr(runtime_hash) + '''
runtime_path = Path('/tmp/rclagent-kaggle-runtime.py')
runtime_path.write_text(RUNTIME_SOURCE, encoding='utf-8')
spec = importlib.util.spec_from_file_location('rclagent_kaggle_runtime', runtime_path)
rcl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rcl)
print('Expected bundle SHA256:', EXPECTED_BUNDLE_SHA256)
''')
    markdown('''## A. Kiểm môi trường thật

Ghi riêng từng GPU, VRAM, RAM, đĩa, Python/PyTorch/CUDA và driver. Chọn thiết bị
đầu tiên đáp ứng yêu cầu; không cộng VRAM. Context: 16.384 token khi VRAM <22.000 MiB,
32.768 token khi VRAM ≥22.000 MiB. Mọi cấu hình được lưu trong settings.json.
''')
    code('''try:
    settings = rcl.environment()
except BaseException:
    rcl.preparation_failure('A')
    raise
''')
    markdown('''## B. Kiểm hash, cài môi trường cô lập và ghi phiên bản

Ghim vLLM 0.10.2, Transformers 4.55.4 và các thư viện trực tiếp; pip ghi phiên bản
phụ thuộc thực tế. Venv và model cache ở /tmp, không thay thư viện Kaggle sẵn có.
Model duy nhất là `Qwen/Qwen3-4B-Instruct-2507`, revision
`cdbee75f17c01a7cc42f958dc650907174af0554` từ tài khoản Qwen chính thức.
Không cần API key hoặc HF token. Cài đặt có thể mất vài phút; xem install.log nếu lỗi.

Sau cài đặt, chạy kiểm kernel tổng hợp trên GPU (không nạp model/telemetry):
bản gốc phải tái hiện lỗi shared memory trên T4, bản vá phải khớp dense causal
attention FP32 (atol/rtol 1e-3) cho 15 trường hợp. Lưu source gốc, unified diff,
hash và kết quả số học trong compatibility/. Sai source/hash hoặc kiểm thất bại thì dừng.
''')
    code('''try:
    package = rcl.install(EXPECTED_BUNDLE_SHA256, EXPECTED_MANIFEST_SHA256)
except BaseException:
    rcl.preparation_failure('B')
    raise
''')
    markdown('''## C–F. Server localhost → gate tổng hợp → một trace → xuất kết quả và dọn process

Các bước C–F nằm trong cùng một cell có `try/finally` để dọn process cả khi lỗi hoặc
người dùng Interrupt. Không có server nào được giữ lại giữa các cell.

**C:** tải một revision, nạp FP16 trên một GPU; vLLM V0 + parser Hermes chính thức,
chỉ lắng nghe localhost. Không paid/cloud API, tunnel hay backbone thứ hai.

**D:** dùng telemetry tổng hợp: structured tool_calls qua client gốc, thực thi
search_logs, trả kết quả bằng role=tool, gọi print_results theo schema ≥10 mục.
Chuyển enable_thinking sang chat_template_kwargs; chặn trường lạ. D thất bại thì
không khởi động tool server trên dữ liệu benchmark; không có parser văn bản vá lỗi.

**E:** đúng trace `68791e1f360d910bd01428c3cd9748ef` / root `6752e26884a7fee8`,
33 span. Trần 160 model requests **tính cả retry**, 30 phút từ lúc bắt đầu E,
concurrency=1, tối đa 4 vòng tool/span; retry client gốc tối đa 3 attempt.
Output tối đa 512 token cho self-state/consolidation, 1.024 cho synthesizer.
Input+output vượt context, output bị cắt, OOM, sai schema hoặc không có kết quả hợp lệ
đều dừng. Query tool ngoài cặp service/time của trace cũng dừng vì gói không bao phủ.
Không cắt context, không tự tăng giới hạn, không chạy lại để chọn đáp án.

**F:** lưu request/response, lỗi, số lời gọi, token khi server trả usage, thời gian,
RAM/VRAM đỉnh lấy mẫu (~1 giây). Chỉ sau khi E kết thúc và đã tắt model server mới
mở scoring/groundtruth.csv rồi chạy scorer tác giả. File ZIP được xuất cả khi thất bại.
SIGKILL/khởi động lại kernel không cho Python thực hiện finally; lỗi và Interrupt thông thường có cleanup.
''')
    code('''from IPython.display import display, FileLink
try:
    result_zip = rcl.run_once(EXPECTED_BUNDLE_SHA256, EXPECTED_MANIFEST_SHA256)
except BaseException:
    if not (rcl.ROOT / 'rclagent-smoke-results.zip').exists():
        rcl.preparation_failure('C')
    raise
finally:
    archive = rcl.ROOT / 'rclagent-smoke-results.zip'
    if archive.exists():
        display(FileLink('rclagent-smoke/rclagent-smoke-results.zip'))
        print('Tải file ZIP này trong Output/Files; chứa cả phần đã hoàn thành khi lỗi.')
''')
    markdown('''## Đọc kết quả

Tải `/kaggle/working/rclagent-smoke/rclagent-smoke-results.zip` và file .sha256.
Trong ZIP: `run/status.json`, `run/trace/worker-status.json`, `run/trace/events.jsonl`,
`run/trace/result.json` (nếu có), `run/scoring/author-score.txt` (chỉ khi hoàn thành),
resource-peaks.json, resources.jsonl và log server/process. Marker protocol_pass nằm
trong `run/protocol/events.jsonl`. Thất bại luôn được giữ, không loại khỏi báo cáo.

Log tool có thể rỗng theo cách lọc upstream; không bổ sung tín hiệu. Một trace không
dùng best-of-traces. Đầu ra cuối không cung cấp confidence cho H1. Kết quả đúng/sai
của backbone 4B này không tự chứng minh chất lượng phương pháp gốc.

Chuẩn bị CPU đã đối chiếu tool với dữ liệu đầy đủ; xem cpu-equivalence.json trong
bundle. Kết quả native mới nhất, nếu có, được ghi ở đầu notebook. Các mục chưa qua
gate D/E vẫn chưa được xác minh; không suy pass từ fixture hoặc server health.

Nguồn: [RCLAgent upstream](https://github.com/LLM4AIOps/RCLAgent-V2),
[RCAEval benchmark](https://zenodo.org/records/14590730),
[Qwen model](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507),
[vLLM 0.10.2 tool calling](https://docs.vllm.ai/en/v0.10.2/features/tool_calling.html).
''')
    notebook = {'nbformat': 4, 'nbformat_minor': 5, 'metadata': {
        'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python'},
        'kaggle': {'accelerator': 'gpu', 'isInternetEnabled': True, 'isGpuEnabled': True,
                   'language': 'python', 'sourceType': 'notebook'}}, 'cells': cells}
    for i, cell in enumerate(cells):
        cell['id'] = 'rclagent-' + str(i)
        if cell['cell_type'] == 'code':
            compile(''.join(cell['source']), '<notebook-cell-' + str(i) + '>', 'exec')
    destination = HERE / 'rclagent-kaggle-smoke.ipynb'
    destination.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'notebook': str(destination), 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
                      'bundle_sha256': bundle_hash, 'cells': len(cells), 'code_cells': sum(c['cell_type']=='code' for c in cells)}, indent=2))


if __name__ == '__main__':
    main()
