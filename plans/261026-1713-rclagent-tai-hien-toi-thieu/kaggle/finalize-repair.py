"""Close the bounded repair record without upgrading the stopped smoke to pass."""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
summary = json.loads((HERE / 'kaggle-repair-v5-summary.json').read_text())
validation = json.loads((HERE / 'package-validation.json').read_text())
assert validation['code_cells_identical_to_latest_downloaded_native'] is True
assert summary['compatibility']['status']['status'] == 'passed'
assert summary['phases']['protocol']['worker']['status'] == 'passed'
assert summary['phases']['trace']['worker']['status'] == 'failed'
assert summary['status']['stage'] == 'E' and summary['status']['status'] == 'failed'
assert not summary['scoring_ran'] and summary['result'] is None
assert all(p['exit'] is not None for p in summary['processes'])
code = 'F:/Nam/UIT/nt114-paper-artifacts/W7165616276/code'
revision = subprocess.run(['git', '-C', code, 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
assert revision == '3052e7a6a9598d984ba1482f3dc41123c8823a99'
subprocess.run(['git', '-C', code, 'diff', '--exit-code', 'HEAD', '--', '.'], check=True)
body = '''Kernel vLLM 0.10.2 non-ALiBi prefix prefill dùng BLOCK_M=128 trên T4, cần 96 KiB shared memory trong giới hạn 64 KiB. Patch có kiểm hash đổi tile thành 64 riêng Turing; giữ source gốc/diff và RCLAgent bất biến.

Kaggle native: kernel gốc tái hiện lỗi, bản vá qua 15 dense-reference cases. Đã sửa regression helper tạo bytecode ngoài manifest, thêm kiểm red/green. 4 kiểm patch/cache và 14 kiểm harness qua.

Version 5 qua D (3 requests), E dừng sau 2 requests vì Qwen hỏi cartservice ngoài trace/domain đóng gói. Chưa có RCA cuối/chấm; không mở rộng dữ liệu, sửa prompt/tool hoặc retry theo kết quả. Mọi process sở hữu đã dừng. Lỗi GPU đã sửa; smoke end-to-end vẫn dừng ở E.

Artifact và bằng chứng: plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle/repair-report.md, kaggle-repair-v5-summary.json, rclagent-kaggle-repair-v5-results.zip. Không chạy LLM trên Windows, không commit/push. AgentWiki publish skipped.
'''
record = subprocess.run(['C:/Users/Siinn/bin/ak.exe', 'journal', 'create',
    'RCLAgent Kaggle T4 prefix kernel repair', '--summary',
    'GPU kernel fixed and tool gate passed; trace stopped on out-of-package cartservice query',
    '--stdin', '--date', '2026-10-26', '--json'],
    input=body, encoding='utf-8', capture_output=True, check=True,
    cwd=HERE.parents[2])
state_path = HERE / 'fix-state.json'
state = json.loads(state_path.read_text())
for phase in state['phases']:
    phase['status'] = 'completed'
state['diagnosis']['pending'] = None
state['outcome'] = {'original_gpu_error': 'resolved-and-native-verified',
    'helper_cache_regression': 'resolved-and-native-verified',
    'protocol_D': 'passed', 'smoke_E': 'stopped-out-of-package-cartservice-query',
    'full_trace_completed': False, 'scoring_ran': False,
    'model_or_prompt_or_data_domain_changed_after_E_stop': False,
    'review': 'same-session ak-code-review; no independent reviewer',
    'journal_cli_output': record.stdout.strip(), 'AgentWiki': 'publish skipped'}
state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(record.stdout.strip())
print('Repair verified; full smoke remains stopped at E. AgentWiki publish skipped.')
