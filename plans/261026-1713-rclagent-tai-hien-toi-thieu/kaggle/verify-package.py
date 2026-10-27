"""Validate deliverable hashes, allowlisted members, notebook syntax and data scope."""
import ast
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    bundle = HERE / 'rclagent-kaggle-bundle.zip'
    notebook_path = HERE / 'rclagent-kaggle-smoke.ipynb'
    with zipfile.ZipFile(bundle) as zipped:
        manifest = json.loads(zipped.read('manifest.json'))
        expected = set(manifest['files']) | {'manifest.json'}
        assert len(zipped.namelist()) == len(expected)
        assert set(zipped.namelist()) == expected
        for name, row in manifest['files'].items():
            data = zipped.read(name)
            assert sha(data) == row['sha256'] and len(data) == row['bytes'], name
            assert not any(part in name.lower() for part in ('credential', 'transcript', '.env', 'canonical', 'test-result'))
            if name.endswith('.py'):
                ast.parse(data.decode('utf-8'), filename=name)
        for name in ('kaggle-runtime.py', 'smoke-worker.py', 'vllm-t4-compat.py', 'verify-t4-prefix-kernel.py'):
            assert zipped.read(name) == (HERE / name).read_bytes(), 'Stale packaged wrapper'
        trace = list(csv.DictReader(io.StringIO(zipped.read('input/trace/all/trace_jaeger-span.csv').decode())))
        metrics = list(csv.DictReader(io.StringIO(zipped.read('input/metric/all/metrics.csv').decode())))
        logs = list(csv.DictReader(io.StringIO(zipped.read('input/log/all/logs.csv').decode())))
        assert len(trace) == 33 and {r['trace_id'] for r in trace} == {'68791e1f360d910bd01428c3cd9748ef'}
        for name in zipped.namelist():
            if name.startswith('input/'):
                assert 'groundtruth' not in name and 'label' not in name
                if name.endswith('.csv'):
                    header = zipped.read(name).splitlines()[0].decode()
                    assert not any(term in header for term in ('_case_id', 'failure_type', 'groundtruth', 'label'))
        assert len(zipped.read('input/error_traces.txt').decode().splitlines()) == 2
        assert len(list(csv.DictReader(io.StringIO(zipped.read('scoring/groundtruth.csv').decode())))) == 1
        parity = json.loads(zipped.read('cpu-equivalence.json'))
        assert parity['status'] == 'pass' and all(c['equal'] for c in parity['comparisons'])
    notebook = json.loads(notebook_path.read_text(encoding='utf-8'))
    assert notebook['nbformat'] == 4
    code_cells = [c for c in notebook['cells'] if c['cell_type'] == 'code']
    assert len(code_cells) == 4
    for cell in code_cells:
        assert cell['execution_count'] is None and not cell['outputs']
        compile(''.join(cell['source']), '<notebook>', 'exec')
    tree = ast.parse(''.join(code_cells[0]['source']))
    assigned = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
                if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id in ('EXPECTED_BUNDLE_SHA256', 'EXPECTED_MANIFEST_SHA256', 'RUNTIME_SOURCE')}
    assert assigned['EXPECTED_BUNDLE_SHA256'] == sha(bundle.read_bytes())
    assert assigned['EXPECTED_MANIFEST_SHA256'] == sha((HERE / 'manifest.json').read_bytes())
    assert assigned['RUNTIME_SOURCE'] == (HERE / 'kaggle-runtime.py').read_text(encoding='utf-8')
    def body(cell):
        return cell['source'] if isinstance(cell['source'], str) else ''.join(cell['source'])
    native_sources = list((HERE / 'runtime/kaggle-source-v3').glob('*.ipynb'))
    native_code_match = None
    if native_sources:
        assert len(native_sources) == 1
        native_notebook = json.loads(native_sources[0].read_text(encoding='utf-8'))
        native_cells = [c for c in native_notebook['cells'] if c['cell_type'] == 'code']
        native_code_match = [body(c) for c in native_cells] == [body(c) for c in code_cells]
    repair_versions = [int(p.name.removeprefix('kaggle-source-v')) for p in (HERE / 'runtime').glob('kaggle-source-v[4-9]') if p.is_dir()]
    repair_version = max(repair_versions) if repair_versions else None
    repair_sources = list((HERE / f'runtime/kaggle-source-v{repair_version}').glob('*.ipynb')) if repair_version else []
    repair_code_match = None
    if repair_sources:
        assert len(repair_sources) == 1
        repair_notebook = json.loads(repair_sources[0].read_text(encoding='utf-8'))
        repair_cells = [c for c in repair_notebook['cells'] if c['cell_type'] == 'code']
        repair_code_match = [body(c) for c in repair_cells] == [body(c) for c in code_cells]
    for path in HERE.glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    result = {'status': 'pass', 'files_in_bundle': len(expected), 'trace_rows': len(trace),
              'metric_rows': len(metrics), 'log_rows': len(logs), 'notebook_code_cells': len(code_cells),
              'bundle_sha256': sha(bundle.read_bytes()), 'bundle_bytes': bundle.stat().st_size,
              'notebook_sha256': sha(notebook_path.read_bytes()),
              'code_cells_identical_to_native_version_3': native_code_match,
              'latest_downloaded_native_version': repair_version,
              'code_cells_identical_to_latest_downloaded_native': repair_code_match,
              'cpu_endpoint_comparisons': parity['endpoint_comparisons'],
              'scope': 'Static package and completed CPU checks only; actual GPU/server compatibility requires Kaggle execution.'}
    (HERE / 'package-validation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
