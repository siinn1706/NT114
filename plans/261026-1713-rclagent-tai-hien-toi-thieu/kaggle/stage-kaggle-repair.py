"""Validate and stage only the scoped private Kaggle deliverables."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for name in ('test-vllm-t4-compat.py', 'refresh-package.py', 'build-notebook.py', 'verify-package.py'):
    subprocess.run([sys.executable, '-X', 'utf8', str(HERE / name)], check=True)
for directory, filename in [('kaggle-dataset-upload', 'rclagent-kaggle-bundle.zip'),
                            ('kaggle-kernel-upload', 'rclagent-kaggle-smoke.ipynb')]:
    target = HERE / 'runtime' / directory
    metadata = 'dataset-metadata.json' if 'dataset' in directory else 'kernel-metadata.json'
    assert {p.name for p in target.iterdir()} == {metadata, filename}
    if metadata == 'kernel-metadata.json':
        assert json.loads((target / metadata).read_text())['is_private'] is True
    shutil.copyfile(HERE / filename, target / filename)
state = json.loads((HERE / 'fix-state.json').read_text())
for row in state['phases']:
    if row['name'] in ('diagnose', 'implement'):
        row['status'] = 'completed'
    elif row['name'] == 'verify-prevent':
        row['status'] = 'in-progress'
state['diagnosis'] = {'native_version': 3, 'stage': 'D', 'requests': 1,
    'trace_requests': 0, 'exception': 'Triton shared memory required 98304 > T4 limit 65536',
    'path': 'XFORMERS -> PagedAttention.forward_prefix -> prefix_prefill._fwd_kernel',
    'released_source_sha256': '8055f9dc80be1727ac9255ac8a2e565ef08e3572325e0b69e170b2249b4b789a',
    'cause': 'non-ALiBi launch hardcodes BLOCK_M=128 on SM75; num_stages already 1',
    'repair': 'Turing-only BLOCK_M=64; hash-bound original backup and unified patch; no RCLAgent changes',
    'pending': 'real GPU before/after numerical and full localhost tool gate'}
(HERE / 'fix-state.json').write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
print('Scoped upload folders staged; no credentials, project tree or previous results included.')
