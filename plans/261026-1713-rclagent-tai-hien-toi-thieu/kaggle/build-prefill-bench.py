"""Build the private prefill-bench dataset and notebook from a downloaded pilot run.

Usage: build-prefill-bench.py RESULTS_ZIP [CONFIG ...]

With CONFIG labels the notebook measures only those servers of prefill-bench.CONFIGS.

The longest request of each trace in RESULTS_ZIP is copied verbatim into prefill-bench-payloads.json.
Those prompts hold train-trace telemetry, so everything is written under runtime/ (not tracked) and goes
only to a private dataset. The notebook reuses the pilot notebook's bootstrap, A and B cells unchanged,
so the same pinned environment and T4 kernel check run before the measurement.
"""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'runtime/prefill-bench'
OWNER = 'siinn1706'
SLUG = 'rclagent-t4-prefill-bench-261027'
TITLE = 'RCLAgent T4 Prefill Bench 261027'
# A kernel cannot share its slug with the owner's dataset: the push is refused with 409 Conflict.
KERNEL_SLUG = 'rclagent-t4-prefill-bench-run-261027'
KERNEL_TITLE = 'RCLAgent T4 Prefill Bench Run 261027'
PILOT_DATASET = OWNER + '/rclagent-one-trace-smoke-261026'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def longest_requests(results_zip):
    payloads = {}
    with zipfile.ZipFile(results_zip) as zipped:
        for name in sorted(zipped.namelist()):
            if not (name.startswith('run/traces/') and name.endswith('/events.jsonl')):
                continue
            events = [json.loads(line) for line in zipped.read(name).decode('utf-8').splitlines()]
            requests = [e for e in events if e.get('kind') == 'request']
            top = max(requests, key=lambda e: e['prompt_tokens_local'])
            trace = name.split('/')[2]
            payloads[f"{trace[:8]}-request{top['number']}-{top['prompt_tokens_local']}tok"] = top['payload']
    return payloads


def code(source):
    return {'cell_type': 'code', 'execution_count': None, 'metadata': {}, 'outputs': [],
            'source': source.splitlines(keepends=True)}


def markdown(source):
    return {'cell_type': 'markdown', 'metadata': {}, 'source': source.splitlines(keepends=True)}


def main(results_zip, only):
    pilot = json.loads((HERE / 'rclagent-kaggle-smoke.ipynb').read_text(encoding='utf-8'))
    pilot_code = [c for c in pilot['cells'] if c['cell_type'] == 'code']
    bootstrap, cell_a, cell_b = pilot_code[0], pilot_code[1], pilot_code[2]
    if 'rcl.environment()' not in ''.join(cell_a['source']) or 'rcl.install(' not in ''.join(cell_b['source']):
        raise SystemExit('pilot notebook cells changed; check A and B before reusing them')

    payloads = longest_requests(results_zip)
    payload_bytes = json.dumps(payloads, ensure_ascii=False, indent=1).encode('utf-8')
    bench_bytes = (HERE / 'prefill-bench.py').read_bytes()
    dataset, kernel = OUT / 'dataset', OUT / 'kernel'
    for folder in (dataset, kernel):
        folder.mkdir(parents=True, exist_ok=True)
    (dataset / 'prefill-bench-payloads.json').write_bytes(payload_bytes)
    (dataset / 'prefill-bench.py').write_bytes(bench_bytes)
    (dataset / 'dataset-metadata.json').write_text(json.dumps({
        'id': f'{OWNER}/{SLUG}', 'title': TITLE, 'licenses': [{'name': 'other'}],
        'description': 'Private. Long prompts replayed from a private RCLAgent pilot run on RE2-OB train traces, '
                       'to time vLLM prefill on one T4. No labels. RCAEval: https://zenodo.org/records/14590730 .'},
        indent=2), encoding='utf-8')

    bench_cell = f"""# C. Đo prefill prompt dài; không chạy RCLAgent, tool server hay scorer.
BENCH_SHA256 = '{sha(bench_bytes)}'
PAYLOADS_SHA256 = '{sha(payload_bytes)}'
def only(name):
    found = list(Path('/kaggle/input').rglob(name))
    assert len(found) == 1, (name, found)
    return found[0]
bench_path, payloads_path = only('prefill-bench.py'), only('prefill-bench-payloads.json')
assert hashlib.sha256(bench_path.read_bytes()).hexdigest() == BENCH_SHA256
assert hashlib.sha256(payloads_path.read_bytes()).hexdigest() == PAYLOADS_SHA256
spec = importlib.util.spec_from_file_location('prefill_bench', bench_path)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)
archive = bench.run(rcl, payloads_path, only={only!r})
print(archive, hashlib.sha256(archive.read_bytes()).hexdigest())
"""
    cells = [
        markdown('# Đo prefill prompt dài trên một T4\n\n'
                 'So server vLLM của pilot (chunked prefill, 2.048 token mỗi bước) với cùng server không chunked '
                 'prefill (16.384 token mỗi bước). Mỗi prompt là một request thật của pilot version 10, gửi lại '
                 'nguyên văn một lần và một lần với `max_tokens=1`. Không chạy RCLAgent, tool server hay scorer.\n'),
        bootstrap, markdown('## A. Kiểm môi trường thật\n'), cell_a,
        markdown('## B. Kiểm hash, cài môi trường cô lập, kiểm kernel T4\n'), cell_b,
        markdown('## C. Đo\n'), code(bench_cell)]
    notebook = dict(pilot, cells=cells)
    (kernel / 'prefill-bench.ipynb').write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding='utf-8')
    (kernel / 'kernel-metadata.json').write_text(json.dumps({
        'id': f'{OWNER}/{KERNEL_SLUG}', 'title': KERNEL_TITLE, 'code_file': 'prefill-bench.ipynb', 'language': 'python',
        'kernel_type': 'notebook', 'is_private': True, 'enable_gpu': True, 'enable_internet': True,
        'machine_shape': 'NvidiaTeslaT4', 'dataset_sources': [PILOT_DATASET, f'{OWNER}/{SLUG}'],
        'competition_sources': [], 'kernel_sources': [], 'model_sources': []}, indent=2), encoding='utf-8')
    print(json.dumps({'only': only, 'payloads': {k: len(json.dumps(v)) for k, v in payloads.items()},
                      'payloads_sha256': sha(payload_bytes), 'bench_sha256': sha(bench_bytes),
                      'notebook_sha256': sha((kernel / 'prefill-bench.ipynb').read_bytes())}, indent=2))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:] or None)
