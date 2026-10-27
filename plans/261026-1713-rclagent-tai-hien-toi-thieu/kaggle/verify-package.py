"""Validate deliverable hashes, allowlisted members, notebook syntax and data scope."""
import ast
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


# Measured independently by work/scripts/re2ob-full-data-time-range.py.
FULL_DATA_SECONDS = {'metric': [1705339822, 1708489861], 'log': [1705339822, 1708489860]}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check_trace(read, names, entry):
    """One trace sub-package: its own trace only, rows inside its windows from its own case, no label in input/."""
    base = '' if entry['dir'] == '.' else entry['dir'] + '/'

    def table(name):
        return list(csv.DictReader(io.StringIO(read(base + name).decode())))
    trace, metrics, logs = (table('input/' + part) for part in
                            ('trace/all/trace_jaeger-span.csv', 'metric/all/metrics.csv', 'log/all/logs.csv'))
    selection = json.loads(read(base + 'selection.json'))
    assert selection['trace_id'] == entry['trace_id'] and selection['span_count'] == entry['span_count']
    assert len(trace) == selection['span_count'] and {r['trace_id'] for r in trace} == {entry['trace_id']}
    assert selection['root_span_id'] in {r['span_id'] for r in trace}
    for name in names:
        if name.startswith(base + 'input/'):
            assert 'groundtruth' not in name and 'label' not in name
            if name.endswith('.csv'):
                header = read(name).splitlines()[0].decode()
                assert not any(term in header for term in ('_case_id', 'failure_type', 'groundtruth', 'label')), name
    assert len(read(base + 'input/error_traces.txt').decode().splitlines()) == 2
    assert len(table('scoring/groundtruth.csv')) == 1
    parity = json.loads(read(base + 'cpu-equivalence.json'))
    assert parity['status'] == 'pass' and all(c['equal'] for c in parity['comparisons'])
    assert parity['trace_rows'] == len(trace) and parity['metric_rows'] == len(metrics) and parity['log_rows'] == len(logs)
    # The worker guard trusts this window; the packaged rows must cover it from the selected case only.
    window = selection['query_window']
    seconds = {int(r['timestamp'][:10]) for r in trace}
    assert (window['start_second'], window['end_second']) == (min(seconds), max(seconds))
    assert window['service_name'] == 'any'
    assert window['metric_rows_seconds'] == [window['start_second'] - 1200, window['end_second'] + 1200]
    assert window['log_rows_seconds'] == [window['start_second'] - 60, window['end_second'] + 60]
    assert parity['query_window'] == {k: window[k] for k in ('start_second', 'end_second', 'metric_rows_seconds', 'log_rows_seconds')}
    # The guard also answers windows wholly outside all full data; the packaged rows must lie inside that range.
    full = window['full_data_seconds']
    assert full == FULL_DATA_SECONDS
    for source in ('metric', 'log'):
        assert full[source][0] <= window['start_second'] <= window['end_second'] <= full[source][1]
        assert full[source][0] <= window[source + '_rows_seconds'][0] <= window[source + '_rows_seconds'][1] <= full[source][1]
    low, high = window['metric_rows_seconds']
    assert all(low <= int(r['timestamp']) <= high for r in metrics)
    low, high = window['log_rows_seconds']
    assert all(low <= int(r['timestamp']) <= high and r['log_id'].startswith('re2ob_' + entry['case'] + '_') for r in logs)
    return {'trace_id': entry['trace_id'], 'case': entry['case'], 'trace_rows': len(trace), 'metric_rows': len(metrics),
            'log_rows': len(logs), 'cpu_endpoint_comparisons': parity['endpoint_comparisons'], 'query_window': window}


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
        for name in ('kaggle-runtime.py', 'smoke-worker.py', 'tool-result-budget.py', 'vllm-t4-compat.py', 'verify-t4-prefix-kernel.py'):
            assert zipped.read(name) == (HERE / name).read_bytes(), 'Stale packaged wrapper'
        entries = manifest['traces']
        assert entries and len({e['trace_id'] for e in entries}) == len(entries)
        traces = [check_trace(zipped.read, zipped.namelist(), entry) for entry in entries]
        # Every nested member belongs to upstream or to a checked trace directory.
        roots = ('upstream/',) + tuple(p for e in entries for p in (('input/', 'scoring/') if e['dir'] == '.' else (e['dir'] + '/',)))
        assert all('/' not in n or n.startswith(roots) for n in zipped.namelist())
        # The search_logs budget is a declared deviation; its CPU check must cover the shipped code.
        budget_check = json.loads((HERE / 'tool-result-budget-check.json').read_text())
        assert budget_check['status'] == 'pass' and budget_check['budget_tokens'] == manifest['tool_result_budget']['budget_tokens']
        assert budget_check['module_sha256'] == manifest['files']['tool-result-budget.py']['sha256']
        assert budget_check['worker_sha256'] == manifest['files']['smoke-worker.py']['sha256']
        assert manifest['tool_result_budget']['deviation_from_upstream'] is True
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
    result = {'status': 'pass', 'files_in_bundle': len(expected), 'traces': traces,
              'notebook_code_cells': len(code_cells),
              'bundle_sha256': sha(bundle.read_bytes()), 'bundle_bytes': bundle.stat().st_size,
              'notebook_sha256': sha(notebook_path.read_bytes()),
              'code_cells_identical_to_native_version_3': native_code_match,
              'latest_downloaded_native_version': repair_version,
              'code_cells_identical_to_latest_downloaded_native': repair_code_match,
              'tool_result_budget': {**manifest['tool_result_budget'], 'cpu_check': budget_check['grid'],
                                     'version6_request3': budget_check['version6_request3']},
              'scope': 'Static package and completed CPU checks only; actual GPU/server compatibility requires Kaggle execution.'}
    (HERE / 'package-validation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
