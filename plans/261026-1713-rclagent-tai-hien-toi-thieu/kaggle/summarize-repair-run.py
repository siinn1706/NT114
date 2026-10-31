"""Validate a downloaded run, single trace (versions 4-8) or batch, without issuing any inference requests."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('version', type=int)
args = parser.parse_args()
version = args.version
folder = HERE / f'runtime/kaggle-output-v{version}/rclagent-smoke'
source = folder / 'rclagent-smoke-results.zip'
digest = hashlib.sha256(source.read_bytes()).hexdigest()
assert digest == (folder / 'rclagent-smoke-results.zip.sha256').read_text().split()[0]
archive = HERE / f'rclagent-kaggle-repair-v{version}-results.zip'
shutil.copyfile(source, archive)
archive.with_suffix('.zip.sha256').write_text(digest + '  ' + archive.name + '\n')
with zipfile.ZipFile(archive) as zipped:
    names = set(zipped.namelist())
    def read(name):
        return json.loads(zipped.read(name)) if name in names else None
    status = read('run/status.json')
    preparation = next((read(n) for n in names if n == 'run/status.json'), None)
    assert status is not None
    summary = {'notebook_version': version, 'status': status,
               'compatibility': {mode: read('compatibility/' + mode + '.json') for mode in ('before', 'after', 'patch', 'status')},
               'settings': read('settings.json'), 'phases': {},
               'artifact': archive.name, 'artifact_bytes': source.stat().st_size,
               'artifact_sha256': digest}
    progress = read('run/progress.json')
    summary['progress'] = progress
    # A batch runs each trace in run/traces/<trace_id>/ with its own 160-request cap; scores per trace.
    phases = [('protocol', 8)] + ([('traces/' + t, 160) for t in progress['traces']] if progress else [('trace', 160)])
    for phase, limit in phases:
        event_name = f'run/{phase}/events.jsonl'
        events = [json.loads(line) for line in zipped.read(event_name).decode().splitlines()] if event_name in names else []
        worker = read(f'run/{phase}/worker-status.json')
        requests = [e for e in events if e['kind'] == 'request']
        responses = [e for e in events if e['kind'] == 'response']
        assert len(requests) <= limit
        if worker:
            assert len(requests) == worker['model_requests_including_retries']
        if 'observed_requests' in status and phase in status['observed_requests']:
            assert status['observed_requests'][phase] == len(requests)
        summary['phases'][phase] = {'worker': worker, 'request_count': len(requests),
            'response_http_statuses': [r['status'] for r in responses],
            'events': {kind: sum(e['kind'] == kind for e in events) for kind in ('protocol_pass', 'fatal', 'worker_error')},
            'last_error_events': [e for e in events if e['kind'] in ('fatal', 'worker_error')][-2:]}
        budgeted = [e for e in events if e['kind'] == 'tool_result_budget']
        summary['phases'][phase]['tool_result_budget'] = {
            'search_logs_results': len(budgeted), 'condensed': sum(e['applied'] for e in budgeted),
            'spans_with_condensed_result': len({e['span_id'] for e in budgeted if e['applied']}),
            'condensed_detail': [{k: e.get(k) for k in ('span_id', 'params', 'original_bytes', 'original_tokens',
                                                        'condensed_tokens', 'notice')} for e in budgeted if e['applied']]}
    processes = read('run/processes.json') or []
    assert all(p['exit'] is not None for p in processes), 'Owned process not stopped'
    summary['processes'] = [{'name': p['name'], 'exit': p['exit']} for p in processes]
    summary['resource_peaks'] = read('run/resource-peaks.json')
    verified = read('input-verification.json')
    assert verified and verified['all_member_hashes_verified']
    summary['input_verification'] = verified
    if progress:
        summary['results'], summary['author_score_text'] = {}, {}
        for trace_id, state in progress['traces'].items():
            summary['results'][trace_id] = read(f'run/traces/{trace_id}/result.json')
            score = f'run/scoring/{trace_id}/author-score.txt'
            if score in names:
                assert state['status'] == 'passed' and summary['phases']['traces/' + trace_id]['worker']['status'] == 'passed'
                summary['author_score_text'][trace_id] = zipped.read(score).decode()
        summary['scoring_ran'] = bool(summary['author_score_text'])
        trace_requests = sum(summary['phases'][p]['request_count'] for p, _ in phases[1:])
    else:
        summary['result'] = read('run/trace/result.json')
        summary['scoring_ran'] = 'run/scoring/author-score.txt' in names
        if summary['scoring_ran']:
            assert summary['phases']['trace']['worker']['status'] == 'passed'
            summary['author_score_text'] = zipped.read('run/scoring/author-score.txt').decode()
        trace_requests = summary['phases']['trace']['request_count']
    if trace_requests:
        assert summary['phases']['protocol']['events']['protocol_pass'] == 1
    for mode in ('before', 'after'):
        row = summary['compatibility'][mode]
        if row:
            row.pop('traceback', None)

native = HERE / f'runtime/kaggle-source-v{version}'
notebooks = list(native.glob('*.ipynb'))
assert len(notebooks) == 1
metadata = json.loads((native / 'kernel-metadata.json').read_text())
assert metadata['is_private'] is True and metadata['enable_gpu'] is True
def code(path):
    cells = json.loads(path.read_text(encoding='utf-8'))['cells']
    return [c['source'] if isinstance(c['source'], str) else ''.join(c['source']) for c in cells if c['cell_type'] == 'code']
assert code(notebooks[0]) == code(HERE / 'rclagent-kaggle-smoke.ipynb')
summary['code_matches_downloaded_native_source'] = True
summary['private_notebook_metadata_verified'] = True
destination = HERE / f'kaggle-repair-v{version}-summary.json'
destination.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in summary.items() if k in ('notebook_version', 'status', 'phases', 'processes', 'artifact', 'artifact_sha256', 'code_matches_downloaded_native_source')}, indent=2))
