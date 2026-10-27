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
    traces = json.loads((HERE / 'manifest.json').read_text())['traces']
    listed = '\n'.join(f"- `{t['trace_id']}` ({t['case']}, {t['span_count']} span)" for t in traces)
    markdown('''# RCLAgent: ''' + (f'{len(traces)} trace train' if len(traces) > 1 else 'một trace') + ''' trên Kaggle GPU

Notebook smoke test với backbone thay thế. Giữ nguyên code/prompt/tool tác giả tại
`3052e7a6a9598d984ba1482f3dc41123c8823a99`; giữ suy luận theo span và gộp đệ quy.
Chưa tái hiện Table I, chưa đo độ chính xác, chưa chạy H1/IM1/R-a.

**Trước khi chạy:** để notebook **Private**, tạo một dataset **Private** chỉ chứa
`rclagent-kaggle-bundle.zip`, rồi Add Input dataset đó. Bật **Internet** và GPU.
Cấu hình cố định này hỗ trợ GPU compute capability ≥7.5, ít nhất 13.000 MiB VRAM trống
trên **một** thiết bị; không hỗ trợ P100. Nếu được T4 ×2, chỉ dùng một T4.

Chạy các cell từ trên xuống. Cell C–F chạy mỗi trace **đúng một lần**; lỗi sẽ dừng và xuất log.
Nếu phiên bị ngắt, chạy lại cell C–F, hoặc gắn ZIP kết quả cũ làm input của phiên mới,
để chạy tiếp các trace còn lại. Trace đã xong, kể cả thất bại, không chạy lại.
Không tự xóa run-once.json hay progress.json để thử lại, đổi model hoặc tăng trần.
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
để chọn đáp án trong lượt đó.
''')
        markdown('''## Version 6: phạm vi query theo cửa sổ thời gian

Chẩn đoán sau version 5: tool tác giả nhận mọi service_name/timestamp và phục vụ
toàn bộ dữ liệu gộp; dữ liệu đầy đủ có log cartservice trong ±60 giây quanh root span.
Query đó hợp lệ theo contract tác giả; gói cũ chỉ chứa các cặp service/giây của span
nên guard chặt hơn tác giả. Bản này đóng gói mọi dòng metric trong ±1.200 giây và mọi
dòng log trong ±60 giây quanh các giây của trace, mọi service, đều thuộc đúng ca này;
phản hồi endpoint gốc khớp byte với dữ liệu đầy đủ (cpu-equivalence.json). Guard cho
mọi service, chỉ chặn timestamp ngoài cửa sổ. Không đổi prompt, tool, model hoặc trần.

Rủi ro đã biết trước khi chạy: kết quả log cartservice gốc khoảng 125 nghìn token.
Nếu model gọi lại query này, request tiếp theo vượt context và lượt chạy dừng vì
overflow, không cắt ngữ cảnh.
''')
    v6_path = HERE / 'kaggle-repair-v6-summary.json'
    if v6_path.exists():
        v6 = json.loads(v6_path.read_text())
        assert v6['status']['status'] == 'failed' and v6['status']['stage'] == 'E'
        markdown('''## Kết quả version 6

D đạt. E dừng sau 2 model requests: model hỏi cartservice, tool trả đúng dữ liệu đầy đủ
(272.734 byte), và request thứ ba cần 126.088 token, vượt context 16.384. Guard dừng
trước khi gửi, không cắt ngữ cảnh. Chưa có kết quả cuối hoặc điểm chấm; process đã dọn.
Quét CPU 450 error trace của 90 ca RE2-OB: mọi trace đều có query search_logs hợp lệ
(cartservice) vượt context ngay vòng tool đầu.
''')
        markdown('''## Từ version 7: ngân sách kết quả search_logs (sai lệch so với tác giả)

Theo quyết định của chủ dự án, wrapper ngoài upstream đặt ngân sách **2.048 token**
(tokenizer Qwen đúng revision) cho mỗi kết quả `search_logs`, áp như nhau cho mọi ca.
Kết quả trong ngân sách được trả **nguyên byte**. Kết quả lớn hơn được rút gọn theo bậc,
chọn bước đầu tiên vừa ngân sách: gộp dòng trùng hệt (giữ số lần, giây đầu/cuối),
rồi gộp theo mẫu thông điệp (che UUID và từ có chữ số thành `<*>`, giữ số lần và giá trị
nguyên văn đầu tiên), cuối cùng mới cắt theo ưu tiên severity, có ghi rõ `truncated`.
Model thấy một dòng thông báo `[harness tool-result budget ...]` ở đầu kết quả.
Từ bản batch, các `search_logs` trong cùng một lượt trả lời của model chia đều ngân sách:
mỗi kết quả nhận ⌊2.048 / n⌋ token. Khi lượt chỉ có một `search_logs` (mọi lượt của
version 7 và 8), ngân sách vẫn là 2.048 và kết quả không đổi byte nào.
Kết quả metric, prompt, model, sampling, context, output, retry, số vòng tool và các trần
giữ nguyên; guard vẫn dừng khi vượt context, không cắt ngữ cảnh.

Kiểm CPU trước khi chạy: query đúng chỉ dẫn của prompt không đổi byte nào trên 450 trace;
không bỏ dòng log hay dòng ERROR nào; tái dựng request thứ ba của version 6 từ 126.088
còn 1.589 token. Kết quả của notebook này là của bản thích nghi có ngân sách,
không so trực tiếp với Table I.
''')
    v7_path = HERE / 'kaggle-repair-v7-summary.json'
    if v7_path.exists():
        v7 = json.loads(v7_path.read_text())
        assert v7['status']['status'] == 'failed' and v7['status']['stage'] == 'E'
        markdown('''## Kết quả version 7

Ngân sách hoạt động: root span lại hỏi cartservice, phản hồi 124.953 token được gộp
còn 454 token, không bỏ dòng nào. E chạy 60 requests HTTP 200 trong 620,7 giây,
27/33 span qua self-state, prompt lớn nhất 1.719 token. Lượt chạy dừng ở request 60:
model gọi search_fluctuating_metrics với timestamp `1808475368747` (sai một chữ số),
guard chặn vì ngoài cửa sổ trace. Chưa có kết quả cuối hoặc điểm chấm; process đã dọn.
''')
        markdown('''## Từ version 8: timestamp ngoài toàn bộ dữ liệu

Trên dữ liệu đầy đủ, tool tác giả trả rỗng cho query của version 7 vì mọi dòng metric/log
nằm trong giây [1.705.339.822, 1.708.489.861]; gói cũng trả rỗng, nên guard version 7
chặt hơn tác giả. Guard nay cho qua thêm query có cửa sổ endpoint (±1.200 giây metric,
±60 giây log) nằm hoàn toàn ngoài khoảng dữ liệu đầy đủ, ghi trong `selection.json`.
Mọi timestamp khác ngoài cửa sổ trace vẫn bị chặn. Không đổi prompt, tool, model,
ngân sách hay các trần; cùng trace và cấu hình với version 7.
''')
    v8_path = HERE / 'kaggle-repair-v8-summary.json'
    if v8_path.exists():
        v8 = json.loads(v8_path.read_text())
        assert v8['status']['status'] == 'passed' and v8['phases']['trace']['request_count'] == 106
        markdown('''## Kết quả version 8

Chạy trọn A–F trên một T4: 106 model requests trong 1.332,9 giây, 38 kết quả search_logs
(1 kết quả được rút gọn), có kết quả cuối và điểm chấm của tác giả cho trace này.
Đây là một trace smoke, không phải ước lượng độ chính xác.
''')
        markdown('''## Bản này: chạy nhiều trace train

Gói chứa một thư mục con cho mỗi trace (`traces/<trace_id>/`): dữ liệu của riêng trace,
`selection.json`, báo cáo tương đương CPU và nhãn chấm điểm. Mỗi gói con được đối chiếu
endpoint gốc với dữ liệu đầy đủ như version 6–8. Các trace của lượt này:

''' + listed + '''

Thứ tự chạy theo gói; mỗi trace có tool server, trần và deadline riêng. Không đổi prompt,
tool, model, sampling, context, output, retry, số vòng tool hay các trần.
''')
        markdown('''## Từ version 11: server không chunked prefill

Đến version 10, server prefill theo khối 2.048 token. Trên T4, prompt tổng hợp 8.446 token
của trace 45 span cần khoảng 232 giây, vượt timeout 180 giây của upstream. Từ version 11,
server prefill cả prompt trong một bước (`--max-num-batched-tokens` bằng context, không
`--enable-chunked-prefill`). Lượt đo riêng cho prompt đó còn 9,4 giây, và câu trả lời của
5 prompt đo được giống hệt cấu hình cũ. Cell C dừng nếu log vLLM cho thấy chunked prefill
vẫn bật. Đây là thay đổi cấu hình server, không đổi các thiết lập đóng băng.
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
    markdown('''## C–F. Server localhost → gate tổng hợp → từng trace → xuất kết quả và dọn process

Các bước C–F nằm trong cùng một cell có `try/finally` để dọn process cả khi lỗi hoặc
người dùng Interrupt. Không có server nào được giữ lại giữa các cell.

**C:** tải một revision, nạp FP16 trên một GPU; vLLM V0 + parser Hermes chính thức,
chỉ lắng nghe localhost. Không paid/cloud API, tunnel hay backbone thứ hai.

**D:** dùng telemetry tổng hợp: structured tool_calls qua client gốc, thực thi
search_logs, trả kết quả bằng role=tool, gọi print_results theo schema ≥10 mục.
Chuyển enable_thinking sang chat_template_kwargs; chặn trường lạ. D thất bại thì
không khởi động tool server trên dữ liệu benchmark; không có parser văn bản vá lỗi.

**E:** lần lượt từng trace trong `manifest.json` của gói. Mỗi trace có tool server riêng
trên dữ liệu của chính nó, trần 160 model requests **tính cả retry** và 30 phút riêng,
concurrency=1, tối đa 4 vòng tool/span; retry client gốc tối đa 3 attempt.
Output tối đa 512 token cho self-state/consolidation, 1.024 cho synthesizer.
Input+output vượt context, output bị cắt, OOM, sai schema hoặc không có kết quả hợp lệ
đều dừng. Query tool cho mọi service được trả như dữ liệu đầy đủ; timestamp ngoài các giây
của trace dừng vì gói không bao phủ. Kết quả search_logs trên 2.048 token được rút gọn
theo ngân sách ở trên; bản gốc và bản model nhận đều được ghi trong events.jsonl.
Không cắt context, không tự tăng giới hạn, không chạy lại để chọn đáp án.
Một trace dừng (guard, deadline, lỗi HTTP) được ghi `failed` kèm lý do trong
`run/progress.json`, rồi lượt chuyển sang trace kế tiếp, không retry. Nếu model server
chết thì cả lượt dừng; các trace còn lại giữ trạng thái chờ để chạy tiếp.

**F:** lưu request/response, lỗi, số lời gọi, token khi server trả usage, thời gian,
RAM/VRAM đỉnh lấy mẫu (~1 giây). Chỉ sau khi E kết thúc và đã tắt model server mới
mở nhãn của từng trace đã qua rồi chạy scorer tác giả cho trace đó. File ZIP được xuất cả khi thất bại.
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
Trong ZIP: `run/status.json`, `run/progress.json` (trạng thái và lý do của từng trace),
`run/traces/<trace_id>/worker-status.json`, `events.jsonl`, `result.json` (nếu có),
`run/scoring/<trace_id>/author-score.txt` (chỉ trace đã qua), resource-peaks.json,
resources.jsonl và log server/process. Marker protocol_pass nằm trong
`run/protocol/events.jsonl`. Thất bại luôn được giữ, không loại khỏi báo cáo.

Log tool có thể rỗng theo cách lọc upstream; không bổ sung tín hiệu. Mỗi trace được chấm
riêng, không dùng best-of-traces. Đầu ra cuối không cung cấp confidence cho H1. Kết quả đúng/sai
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
