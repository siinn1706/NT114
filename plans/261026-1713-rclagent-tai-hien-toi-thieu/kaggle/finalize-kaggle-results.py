"""Summarize the stopped native run without issuing any further model request."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
output = HERE / 'runtime/kaggle-output-v3/rclagent-smoke'
source = output / 'rclagent-smoke-results.zip'
archive = HERE / 'rclagent-kaggle-gpu-results.zip'
digest = hashlib.sha256(source.read_bytes()).hexdigest()
assert digest == (output / 'rclagent-smoke-results.zip.sha256').read_text().split()[0]
shutil.copyfile(source, archive)
(HERE / 'rclagent-kaggle-gpu-results.zip.sha256').write_text(digest + '  ' + archive.name + '\n', encoding='utf-8')
with zipfile.ZipFile(archive) as zipped:
    status = json.loads(zipped.read('run/status.json'))
    worker = json.loads(zipped.read('run/protocol/worker-status.json'))
    events = [json.loads(line) for line in zipped.read('run/protocol/events.jsonl').decode('utf-8').splitlines()]
    peaks = json.loads(zipped.read('run/resource-peaks.json'))
    processes = json.loads(zipped.read('run/processes.json'))
    settings = json.loads(zipped.read('settings.json'))
    verified = json.loads(zipped.read('input-verification.json'))
requests = [e for e in events if e['kind'] == 'request']
responses = [e for e in events if e['kind'] == 'response']
assert status['stage'] == 'D' and status['status'] == 'failed'
assert status['observed_requests'] == {'protocol': 1, 'trace': 0}
assert len(requests) == worker['model_requests_including_retries'] == 1
assert len(responses) == 1 and responses[0]['status'] == 500
assert not any(e.get('kind') == 'protocol_pass' for e in events)
assert all(p['exit'] is not None for p in processes)
assert not any(p['name'] in ('tools-telemetry', 'worker-trace') for p in processes)
assert verified['all_member_hashes_verified']
peak_rss = max(p['sampled_peak_owned_rss_bytes'] for p in peaks['by_phase'].values())
gpu_peaks = {}
for phase in peaks['by_phase'].values():
    for uuid, mib in phase['sampled_peak_owned_gpu_mib'].items():
        gpu_peaks[uuid] = max(gpu_peaks.get(uuid, 0), mib)
summary = {
    'native_status': 'stopped-at-D', 'notebook_version': 3, 'dataset_version': 4,
    'model': settings['model'], 'model_revision': settings['model_revision'],
    'used_gpu': {'name': settings['gpu']['name'], 'index': settings['gpu']['index'],
                 'total_mib': settings['gpu']['total_mib']},
    'context': settings['context'], 'model_requests_including_retries': status['observed_requests'],
    'response_http_status': 500, 'token_usage': worker['token_usage'],
    'runtime_error': 'triton.runtime.errors.OutOfResources: shared memory required 98304 bytes, hardware limit 65536 bytes',
    'elapsed_C_to_cleanup_seconds': status['elapsed_seconds'],
    'model_request_elapsed_seconds': responses[0]['elapsed_seconds'],
    'sampled_peak_owned_rss_bytes': peak_rss, 'sampled_peak_owned_rss_gib': round(peak_rss/2**30, 3),
    'sampled_peak_owned_gpu_mib': gpu_peaks,
    'sampled_peak_owned_gpu_gib': {u: round(mib/1024, 3) for u, mib in gpu_peaks.items()},
    'recorded_processes_stopped': [{'name': p['name'], 'exit': p['exit']} for p in processes],
    'telemetry_tool_server_started': False, 'benchmark_trace_ran': False, 'scoring_ran': False,
    'all_native_input_member_hashes_verified': True,
    'artifact': archive.name, 'artifact_sha256': digest, 'artifact_bytes': archive.stat().st_size,
    'stop_policy': 'Gate D failed; no inference rerun, backbone change, limit increase or textual tool parser added.',
    'resource_measurement': peaks['method'],
}
(HERE / 'kaggle-native-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, indent=2))
