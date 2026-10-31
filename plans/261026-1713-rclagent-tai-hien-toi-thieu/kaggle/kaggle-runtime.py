"""Kaggle bootstrap, localhost model lifecycle, one protocol gate and one trace.

This file uses only the standard library until dependencies have been installed.
"""
import atexit
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import venv
import zipfile
from pathlib import Path

MODEL = 'Qwen/Qwen3-4B-Instruct-2507'
REVISION = 'cdbee75f17c01a7cc42f958dc650907174af0554'
VLLM_VERSION = '0.10.2'
COMMIT = '3052e7a6a9598d984ba1482f3dc41123c8823a99'
PINS = ['vllm==0.10.2', 'pandas==2.2.3', 'numpy==2.2.6', 'flask==3.1.2',
        'requests==2.32.5', 'tenacity==9.1.2', 'jsonschema==4.25.1', 'psutil==7.0.0',
        'transformers==4.55.4', 'huggingface-hub==0.34.4']
PINS += ['openai==1.101.0', 'fastapi==0.116.1', 'pydantic==2.11.7', 'tokenizers==0.21.4']
ROOT = Path('/kaggle/working/rclagent-smoke')
INPUT = Path('/kaggle/input')
TEMP = Path('/tmp/rclagent-smoke')
PYTHON = TEMP / 'env/bin/python'
# Per-run trace limits; a manifest's harness_limits overrides them for a sensitivity bundle.
HARNESS_LIMITS = {'max_model_requests_including_retry': 160, 'rcl_deadline_seconds': 1800,
                  'max_tool_rounds_per_span': 4}
LIMIT_FLAGS = {'max_model_requests_including_retry': '--max-requests', 'rcl_deadline_seconds': '--deadline-seconds',
               'max_tool_rounds_per_span': '--tool-rounds'}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def kaggle_only():
    if sys.platform != 'linux' or not INPUT.is_dir():
        raise RuntimeError('GPU/model execution is permitted only inside Kaggle, never Windows')


def environment():
    kaggle_only()
    ROOT.mkdir(parents=True, exist_ok=True)
    result = {'python': sys.version, 'platform': platform.platform(),
              'disk': {str(p): shutil.disk_usage(p)._asdict() for p in (Path('/tmp'), Path('/kaggle/working'))}}
    with open('/proc/meminfo', encoding='utf-8') as f:
        result['ram_kib'] = {line.split(':')[0]: int(line.split()[1]) for line in f if line.startswith(('MemTotal:', 'MemAvailable:'))}
    query = subprocess.run(['nvidia-smi', '--query-gpu=index,name,uuid,memory.total,memory.free,driver_version,compute_cap',
                            '--format=csv,noheader,nounits'], capture_output=True, text=True)
    result['nvidia_smi_exit'] = query.returncode
    result['gpus'] = []
    for line in query.stdout.splitlines():
        fields = [x.strip() for x in line.split(',')]
        if len(fields) != 7:
            continue
        index, name, uuid, total, free, driver, capability = fields
        result['gpus'].append({'index': int(index), 'name': name, 'uuid': uuid,
                              'total_mib': float(total), 'free_mib': float(free),
                              'driver': driver, 'compute_capability': float(capability)})
    probe = subprocess.run([sys.executable, '-c', 'import json,torch; print(json.dumps({"torch":torch.__version__,"cuda":torch.version.cuda,"cuda_available":torch.cuda.is_available()}))'], capture_output=True, text=True)
    result['base_torch_probe'] = {'exit': probe.returncode, 'stdout': probe.stdout, 'stderr': probe.stderr}
    dump(ROOT / 'environment-before.json', result)
    print(json.dumps(result, indent=2))
    if query.returncode or not result['gpus']:
        raise RuntimeError('No GPU allocated; enable a Kaggle GPU before continuing')
    # One device only. No summed VRAM and no tensor parallelism across devices.
    eligible = [g for g in result['gpus'] if g['compute_capability'] >= 7.5 and g['free_mib'] >= 13000]
    if not eligible:
        raise RuntimeError('This fixed vLLM/FP16 configuration needs one GPU with compute capability >=7.5 and >=13000 MiB free; unsupported allocation stops here')
    if result['ram_kib']['MemAvailable'] < 10 * 1024**2:
        raise RuntimeError('Less than 10 GiB host RAM available')
    if shutil.disk_usage('/tmp').free < 22 * 1024**3:
        raise RuntimeError('Less than 22 GiB temporary disk available for isolated dependencies and model')
    chosen = eligible[0]
    context = 16384 if chosen['total_mib'] < 22000 else 32768
    # One prefill step for the whole prompt: on T4, chunked prefill (2.048) made an 8.4k-token
    # synthesis prompt take ~230 s against the upstream 180 s client timeout.
    settings = {'gpu': chosen, 'context': context,
                'dtype': 'half', 'tensor_parallel_size': 1, 'max_num_seqs': 1,
                'vllm_engine': 'V0',
                'enable_chunked_prefill': False, 'max_num_batched_tokens': context,
                'max_output_tokens': {'self_state': 512, 'consolidate': 512, 'synthesizer': 1024},
                **HARNESS_LIMITS, 'client_retry_attempts': 3,
                'model': MODEL, 'model_revision': REVISION, 'vllm': VLLM_VERSION,
                'sampling': {'temperature': 0.7, 'top_p': 0.8, 'top_k': 20, 'min_p': 0.0, 'seed': 20261026},
                'context_overflow': 'fatal, never truncate', 'concurrency': 1}
    dump(ROOT / 'settings.json', settings)
    return settings


def find_archive():
    candidates = list(INPUT.rglob('rclagent-kaggle-bundle.zip'))
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        raise RuntimeError('Multiple bundle archives attached')
    # Kaggle Dataset ingestion expands ZIPs. Bind the expanded content to the
    # manifest digest embedded in the notebook, then verify every member.
    manifests = [p for p in INPUT.rglob('manifest.json') if (p.parent / 'upstream/coordinator.py').is_file()]
    if len(manifests) != 1:
        raise RuntimeError(f'Attach exactly one private bundle dataset; found {len(manifests)} expanded packages')
    return manifests[0].parent


def unpack(archive, expected_sha256, expected_manifest_sha256):
    archive = Path(archive)
    if archive.is_file() and digest(archive) != expected_sha256:
        raise RuntimeError('Bundle SHA256 mismatch')
    package = ROOT / 'package'
    if package.exists():
        # Safe reuse for bootstrap; execution is separately protected by run-once.json.
        manifest = json.loads((package / 'manifest.json').read_text())
    else:
        package.mkdir(parents=True)
        if archive.is_dir():
            if digest(archive / 'manifest.json') != expected_manifest_sha256:
                raise RuntimeError('Expanded Kaggle manifest SHA256 mismatch')
            manifest = json.loads((archive / 'manifest.json').read_text())
            for relative in [*manifest['files'], 'manifest.json']:
                destination = (package / relative).resolve()
                if not destination.is_relative_to(package.resolve()):
                    raise RuntimeError('Unsafe manifest path')
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(archive / relative, destination)
        else:
            with zipfile.ZipFile(archive) as zipped:
                for entry in zipped.infolist():
                    target = (package / entry.filename).resolve()
                    if not target.is_relative_to(package.resolve()):
                        raise RuntimeError('Unsafe zip path')
                zipped.extractall(package)
        manifest = json.loads((package / 'manifest.json').read_text())
    if digest(package / 'manifest.json') != expected_manifest_sha256:
        raise RuntimeError('Manifest SHA256 mismatch')
    if manifest['upstream_commit'] != COMMIT or manifest['model_revision'] != REVISION:
        raise RuntimeError('Code/model revision mismatch')
    actual = {p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()}
    if actual != set(manifest['files']) | {'manifest.json'}:
        raise RuntimeError('Unexpected or missing package members')
    for relative, entry in manifest['files'].items():
        if digest(package / relative) != entry['sha256']:
            raise RuntimeError('Package member hash mismatch: ' + relative)
    if manifest['files']['kaggle-runtime.py']['sha256'] != digest(__file__):
        raise RuntimeError('Notebook runtime differs from hashed package runtime')
    dump(ROOT / 'input-verification.json', {'source': str(archive),
        'container': 'expanded Kaggle dataset' if archive.is_dir() else 'zip',
        'manifest_sha256': expected_manifest_sha256, 'all_member_hashes_verified': True,
        'original_bundle_sha256': expected_sha256,
        'container_zip_hash_checked': archive.is_file()})
    return package


def clean_env():
    env = os.environ.copy()
    for key in list(env):
        if key.startswith('LLM_') or key in ('HF_TOKEN', 'HUGGING_FACE_HUB_TOKEN', 'HUGGINGFACEHUB_API_TOKEN', 'VLLM_API_KEY',
                                           'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'DASHSCOPE_API_KEY'):
            env.pop(key)
    env.update(HF_HUB_DISABLE_IMPLICIT_TOKEN='1', HF_HUB_DISABLE_TELEMETRY='1',
               HF_HOME=str(TEMP / 'huggingface'), PIP_DISABLE_PIP_VERSION_CHECK='1',
               DO_NOT_TRACK='1', TOKENIZERS_PARALLELISM='false',
               PYTHONDONTWRITEBYTECODE='1',
               # The author's code joins sets of service names into prompts; a fixed hash seed fixes their order.
               PYTHONHASHSEED='0')
    return env


def install(expected_sha256, expected_manifest_sha256):
    kaggle_only()
    if not (ROOT / 'settings.json').exists():
        raise RuntimeError('Run environment cell A first')
    TEMP.mkdir(parents=True, exist_ok=True)
    package = unpack(find_archive(), expected_sha256, expected_manifest_sha256)
    if not PYTHON.exists():
        # Kaggle's Debian Python may omit ensurepip. Create a bare venv, then
        # use base pip's supported --python option to seed only that venv.
        venv.EnvBuilder(with_pip=False).create(TEMP / 'env')
    marker = TEMP / 'pins.json'
    if marker.exists() and json.loads(marker.read_text()) != PINS:
        raise RuntimeError('Existing isolated environment has different pins; stop without altering it')
    if not marker.exists():
        with (ROOT / 'install.log').open('w', encoding='utf-8') as log:
            subprocess.run([sys.executable, '-m', 'pip', '--python', str(PYTHON),
                            'install', '--index-url', 'https://pypi.org/simple',
                            '--no-cache-dir', 'pip==25.2'], env=clean_env(),
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
            subprocess.run([str(PYTHON), '-m', 'pip', 'install', '--index-url', 'https://pypi.org/simple', '--no-cache-dir', *PINS],
                           env=clean_env(), stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1500)
        dump(marker, PINS)
    check = subprocess.run([str(PYTHON), '-m', 'pip', 'check'], capture_output=True, text=True, env=clean_env())
    (ROOT / 'pip-check.txt').write_text(check.stdout + check.stderr, encoding='utf-8')
    check.check_returncode()
    freeze = subprocess.run([str(PYTHON), '-m', 'pip', 'freeze', '--all'], capture_output=True, text=True, check=True, env=clean_env())
    (ROOT / 'pip-freeze.txt').write_text(freeze.stdout, encoding='utf-8')
    probe = subprocess.run([str(PYTHON), '-c', 'import json,torch,transformers,vllm,pandas; print(json.dumps({"torch":torch.__version__,"cuda":torch.version.cuda,"vllm":vllm.__version__,"transformers":transformers.__version__,"pandas":pandas.__version__,"gpu_count":torch.cuda.device_count(),"cuda_available":torch.cuda.is_available()}))'],
                           capture_output=True, text=True, env=clean_env(), check=True, timeout=180)
    (ROOT / 'environment-isolated.json').write_text(probe.stdout, encoding='utf-8')
    if not json.loads(probe.stdout)['cuda_available']:
        raise RuntimeError('Isolated PyTorch cannot access CUDA; no model will be downloaded or run')
    settings = json.loads((ROOT / 'settings.json').read_text())
    kernel_env = clean_env()
    kernel_env.update(CUDA_VISIBLE_DEVICES=str(settings['gpu']['index']), VLLM_USE_V1='0',
                      VLLM_NO_USAGE_STATS='1', VLLM_DO_NOT_TRACK='1')
    evidence = ROOT / 'compatibility'
    checked = evidence / 'status.json'
    if not checked.exists():
        subprocess.run([str(PYTHON), str(package / 'verify-t4-prefix-kernel.py'),
                        '--evidence', str(evidence)], env=kernel_env, check=True, timeout=600)
    if json.loads(checked.read_text())['status'] != 'passed':
        raise RuntimeError('GPU prefix compatibility verification failed')
    print(probe.stdout)
    print('Installed in /tmp; Kaggle base packages were not modified.')
    return package


def assert_free_port(port):
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', port))


class Processes:
    def __init__(self, result):
        self.result = result
        self.children = []
        self.files = []

    def start(self, name, argv, env):
        log = (self.result / (name + '.log')).open('wb')
        self.files.append(log)
        child = subprocess.Popen(argv, env=env, cwd=self.result,
                                 stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        self.children.append({'name': name, 'process': child, 'argv': argv})
        self.record()
        return child

    def record(self):
        dump(self.result / 'processes.json', [{'name': item['name'], 'pid': item['process'].pid,
            'port': 8000 if item['name'] == 'vllm' else 5000 if item['name'].startswith('tools-') else None,
            'cwd': str(self.result), 'argv': item['argv'], 'exit': item['process'].poll()} for item in self.children])

    def stop(self, child):
        # Only process groups created by start_new_session=True in this run.
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            child.wait(timeout=12)
        except subprocess.TimeoutExpired:
            pass
        # The leader can exit before its descendants. Check the owned group too.
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            pass
        else:
            os.killpg(child.pid, signal.SIGKILL)
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        self.record()

    def cleanup(self):
        for item in reversed(self.children):
            self.stop(item['process'])
        for handle in self.files:
            handle.close()


def wait_ready(child, path, timeout):
    import urllib.request
    end = time.monotonic() + timeout
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while time.monotonic() < end:
        if child.poll() is not None:
            raise RuntimeError('Owned server exited before ready; inspect its log')
        try:
            with opener.open(path, timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, ValueError):
            time.sleep(1)
    raise TimeoutError('Server startup timed out')


def assert_unserved(port):
    # A connect probe, not a bind: the last server's connections may still sit in TIME_WAIT on this port, which
    # blocks a plain bind on Linux although nothing answers there any more.
    with socket.socket() as probe:
        probe.settimeout(2)
        if probe.connect_ex(('127.0.0.1', port)) == 0:
            raise RuntimeError(f'Port {port} still held by another process; refusing to start a tool server')


def start_tool_server(proc, name, argv, env, probe_url, timeout):
    """Start a tool server on port 5000; one that never becomes ready is stopped before the error propagates."""
    assert_unserved(5000)
    child = proc.start(name, argv, env)
    try:
        wait_ready(child, probe_url, timeout)
    except BaseException:
        proc.stop(child)
        raise
    return child


def score_runs(package, result, progress, python, env):
    """Score each passed run with the author's evaluate.py on its own; return the run_ids whose scoring failed."""
    shutil.rmtree(result / 'scoring', ignore_errors=True)
    failed = []
    for entry in run_entries(package):
        if progress['traces'][entry['run_id']]['status'] != 'passed':
            continue
        trace_dir, scoring = package / entry['dir'], result / 'scoring' / entry['run_id']
        exit_code, error = None, None
        try:
            (scoring / 'result').mkdir(parents=True)
            shutil.copyfile(trace_dir / 'scoring/groundtruth.csv', scoring / 'groundtruth.csv')
            shutil.copyfile(trace_dir / 'input/error_traces.txt', scoring / 'error_traces.txt')
            shutil.copyfile(result / 'traces' / entry['run_id'] / 'result.json', scoring / 'result/conversation_trace_1.txt')
            with (scoring / 'author-score.txt').open('w', encoding='utf-8') as log:
                exit_code = subprocess.run([str(python), str(package / 'upstream/evaluate.py'), str(scoring), 'result'],
                                           env=env, stdout=log, stderr=subprocess.STDOUT, timeout=60).returncode
        except Exception as exc:
            error = repr(exc)
        dump(scoring / 'scorer-status.json', {'exit': exit_code, 'error': error})
        if exit_code or error:
            failed.append(entry['run_id'])
    return failed


class Resources:
    def __init__(self, processes, result):
        self.processes, self.result = processes, result
        self.done = threading.Event()
        self.phase = 'setup'
        self.peaks = {}
        self.thread = threading.Thread(target=self.sample, daemon=True)

    def sample(self):
        # This stdlib thread uses /proc, so no package changes to the notebook kernel.
        while not self.done.is_set():
            try:
                self.sample_once()
            except Exception as exc:
                with (self.result / 'monitor-errors.log').open('a', encoding='utf-8') as f:
                    f.write(repr(exc) + '\n')
            self.done.wait(1)

    def sample_once(self):
        roots = {item['process'].pid for item in self.processes.children}
        rows = {}
        for procdir in Path('/proc').glob('[0-9]*'):
            try:
                stat = (procdir / 'stat').read_text()
                tail = stat[stat.rfind(')')+2:].split()
                rows[int(procdir.name)] = (int(tail[1]), int(tail[21]) * os.sysconf('SC_PAGE_SIZE'))
            except (OSError, ValueError, IndexError):
                continue
        owned = set(roots)
        for _ in range(20):
            more = {pid for pid, (ppid, _) in rows.items() if ppid in owned}
            if more <= owned:
                break
            owned |= more
        ram = sum(rss for pid, (_, rss) in rows.items() if pid in owned)
        gpu = {}
        probe = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,used_gpu_memory,gpu_uuid',
                                '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5)
        if probe.returncode == 0:
            for line in probe.stdout.splitlines():
                parts = [x.strip() for x in line.split(',')]
                if len(parts) == 3 and parts[0].isdigit() and int(parts[0]) in owned:
                    try:
                        gpu[parts[2]] = gpu.get(parts[2], 0) + float(parts[1])
                    except ValueError:
                        continue
        peak = self.peaks.setdefault(self.phase, {'sampled_peak_owned_rss_bytes': 0, 'sampled_peak_owned_gpu_mib': {}, 'samples': 0})
        peak['samples'] += 1
        peak['sampled_peak_owned_rss_bytes'] = max(peak['sampled_peak_owned_rss_bytes'], ram)
        for uuid, mib in gpu.items():
            peak['sampled_peak_owned_gpu_mib'][uuid] = max(peak['sampled_peak_owned_gpu_mib'].get(uuid, 0), mib)
        with (self.result / 'resources.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps({'time': time.time(), 'phase': self.phase, 'owned_rss_bytes': ram,
                                'owned_gpu_mib': gpu or None, 'gpu_probe_exit': probe.returncode}) + '\n')

    def finish(self):
        self.done.set()
        self.thread.join(timeout=7)
        dump(self.result / 'resource-peaks.json', {'by_phase': self.peaks,
             'method': 'Owned process-tree RSS and nvidia-smi compute-app memory, sampled every ~1s. Device peaks remain separate; RSS may double-count shared pages. Missing GPU metrics are unknown, not zero. Brief allocation peaks between samples can be missed.'})


def synthetic_data(path):
    path.mkdir(parents=True, exist_ok=True)
    for part in ('trace/all', 'metric/all', 'log/all'):
        (path / part).mkdir(parents=True, exist_ok=True)
    (path / 'trace/all/trace_jaeger-span.csv').write_text('timestamp,cmdb_id,span_id,trace_id,duration,type,status_code,operation_name,parent_span\n1700000000000,syntheticservice,synthetic-span,synthetic-trace,1,rpc,0,synthetic-operation,\n')
    (path / 'metric/all/metrics.csv').write_text('timestamp,node_id,service_name,kpi_name,value\n1700000000,,syntheticservice,cpu,1.0\n')
    (path / 'log/all/logs.csv').write_text('log_id,timestamp,cmdb_id,log_name,value\nsynthetic-log,1700000000,syntheticservice,synthetic,"severity: ERROR, message: SYNTHETIC_OK"\n')
    for name in ('node_service_map.pkl', 'service_node_map.pkl'):
        (path / 'metric' / name).write_bytes(b'\x80\x04}\x94.')


def export_results(result):
    archive = ROOT / 'rclagent-smoke-results.zip'
    allowed_extra = ('environment-before.json', 'settings.json', 'environment-isolated.json',
                     'pip-freeze.txt', 'pip-check.txt', 'install.log', 'input-verification.json')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(result.rglob('*')):
            if path.is_file():
                zipped.write(path, 'run/' + path.relative_to(result).as_posix())
        for name in allowed_extra:
            if (ROOT / name).exists():
                zipped.write(ROOT / name, name)
        for path in sorted((ROOT / 'compatibility').rglob('*')):
            if path.is_file():
                zipped.write(path, 'compatibility/' + path.relative_to(ROOT / 'compatibility').as_posix())
    (ROOT / 'rclagent-smoke-results.zip.sha256').write_text(digest(archive) + '  ' + archive.name + '\n')
    print('Results:', archive, 'SHA256:', digest(archive))
    return archive


def run_entries(package):
    """The manifest's runs (a trace under one seed and source condition), or one author-condition run per trace."""
    manifest = json.loads((package / 'manifest.json').read_text())
    return manifest.get('runs') or [dict(t, run_id=t['trace_id']) for t in manifest['traces']]


def harness_limits(manifest):
    """The bundle's trace limits: the defaults, overridden by known positive integers in harness_limits."""
    given = manifest.get('harness_limits', {})
    unknown = sorted(set(given) - set(HARNESS_LIMITS))
    if unknown:
        raise ValueError('Unknown harness limits: ' + ', '.join(unknown))
    for key, value in given.items():
        if type(value) is not int or value < 1:
            raise ValueError(f'Harness limit {key} must be a positive integer, not {value!r}')
    return dict(HARNESS_LIMITS, **given)


def limit_options(limits):
    return [part for key, flag in LIMIT_FLAGS.items() for part in (flag, str(limits[key]))]


def worker_options(entry):
    """Worker flags of one run; a run without them keeps the author's tools and the frozen seed."""
    options = []
    for flag in ('seed', 'logs', 'metric'):
        if flag in entry:
            options += ['--' + flag, str(entry[flag])]
    return options


def set_aside(path):
    """Keep a partial directory from an interrupted attempt as evidence instead of overwriting it."""
    if path.exists():
        index = 0
        while path.with_name(f'{path.name}.previous-{index}').exists():
            index += 1
        path.rename(path.with_name(f'{path.name}.previous-{index}'))


def load_progress(path, bundle_sha256):
    if not path.exists():
        return {'bundle_sha256': bundle_sha256, 'traces': {}}
    progress = json.loads(path.read_text())
    if progress['bundle_sha256'] != bundle_sha256:
        raise RuntimeError('Recorded progress belongs to another bundle; refusing to mix runs')
    return progress


def run_traces(package, result, bundle_sha256, run_trace, model_alive):
    """Run every packaged run once, in package order, recording progress after each state change.

    A run is a trace under one seed and source condition; progress, outputs and scores are keyed by its run_id
    (the trace_id when the manifest lists no runs).

    A trace with a final status (passed or failed) is skipped when the batch is resumed; one cut off mid-run
    (still running) runs again, its partial output set aside. A failed trace is recorded with its reason and the
    batch moves on, without retry or configuration change. A dead model server stops the batch with the
    remaining traces pending; a trace that fails while the server process has died is left running, so a resume
    reruns it instead of booking an infrastructure failure as the model's. A second server death in the same trace
    books it failed, so a prompt that crashes the server cannot block the batch on every resume.
    """
    path = result / 'progress.json'
    progress = load_progress(path, bundle_sha256)
    for entry in run_entries(package):
        state = progress['traces'].setdefault(entry['run_id'], {'case': entry['case'], 'attempts': []})
        if state.get('status') in ('passed', 'failed'):
            continue
        if not model_alive():
            dump(path, progress)
            raise RuntimeError('Model server is not running; remaining traces stay pending for a resumed run')
        out = result / 'traces' / entry['run_id']
        if state.get('status') == 'running':
            state['attempts'][-1]['outcome'] = 'interrupted'
            set_aside(out)
        state['status'] = 'running'
        state['attempts'].append({'started': time.time()})
        dump(path, progress)
        try:
            run_trace(package / entry['dir'], out, entry)
            state['status'] = 'passed'
        except Exception as exc:  # An interrupt (BaseException) leaves the trace running, so a resume reruns it.
            if not model_alive() and not any(a.get('server_died') for a in state['attempts'][:-1]):
                state['attempts'][-1].update(outcome='interrupted', server_died=True, reason=repr(exc),
                                             finished=time.time())
                dump(path, progress)
                raise RuntimeError('Model server died during a trace; it and the remaining traces run again on resume')
            state.update(status='failed', reason=repr(exc))
        state['attempts'][-1].update(outcome=state['status'], finished=time.time())
        dump(path, progress)
    return progress


def import_prior(result, bundle_sha256):
    """Continue a batch from the results of an earlier session attached as input, zip or expanded."""
    sources = [p for p in INPUT.rglob('rclagent-smoke-results.zip')] + \
              [p.parent.parent for p in INPUT.rglob('progress.json') if p.parent.name == 'run']
    if not sources:
        return False
    if len(sources) != 1:
        raise RuntimeError(f'Attach at most one earlier result set; found {len(sources)}')
    if (result / 'progress.json').exists():
        raise RuntimeError('This session already has progress; refusing to merge an attached result set')
    source = sources[0]
    zipped = zipfile.ZipFile(source) if source.is_file() else None
    try:
        progress = json.loads(zipped.read('run/progress.json') if zipped else (source / 'run/progress.json').read_text())
        if progress['bundle_sha256'] != bundle_sha256:
            raise RuntimeError('Attached results belong to another bundle')
        if zipped:
            for entry in zipped.infolist():
                if entry.filename.startswith('run/traces/') and not entry.is_dir():
                    target = (result / entry.filename.removeprefix('run/')).resolve()
                    if not target.is_relative_to(result.resolve()):
                        raise RuntimeError('Unsafe path in attached results')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zipped.read(entry))
        elif (source / 'run/traces').is_dir():
            shutil.copytree(source / 'run/traces', result / 'traces', dirs_exist_ok=True)
    finally:
        if zipped:
            zipped.close()
    dump(result / 'progress.json', progress)
    return True


def preparation_failure(stage):
    """Make A/B/early-C errors downloadable even before a model process exists."""
    output = ROOT / ('preparation-' + stage)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'error.txt').write_text(traceback.format_exc(), encoding='utf-8')
    dump(output / 'status.json', {'status': 'failed', 'stage': stage, 'model_run': 'not-started'})
    return export_results(output)


def run_once(expected_sha256, expected_manifest_sha256):
    kaggle_only()
    package = unpack(find_archive(), expected_sha256, expected_manifest_sha256)
    settings = json.loads((ROOT / 'settings.json').read_text())
    limits = harness_limits(json.loads((package / 'manifest.json').read_text()))
    settings.update(limits)  # Record the limits this bundle's traces run under.
    dump(ROOT / 'settings.json', settings)
    if json.loads((ROOT / 'compatibility/status.json').read_text())['status'] != 'passed':
        raise RuntimeError('Run the synthetic GPU kernel compatibility check before starting the model')
    marker = ROOT / 'run-once.json'
    if marker.exists():
        state = json.loads(marker.read_text())
        if state['bundle_sha256'] != expected_sha256:
            raise RuntimeError('A run of another bundle exists here; stop without altering it')
        state['resumed'] = state.get('resumed', []) + [time.time()]
    else:
        state = {'started': time.time(), 'bundle_sha256': expected_sha256,
                 'policy': 'One pass over the packaged traces. A resumed run continues pending traces only; a '
                           'finished trace, passed or failed, never runs again. A new pass needs a new user decision.'}
    dump(marker, state)
    result = ROOT / 'run'
    result.mkdir(exist_ok=True)
    imported = import_prior(result, expected_sha256)
    proc = Processes(result)
    monitor = Resources(proc, result)
    atexit.register(proc.cleanup)
    status = {'status': 'failed', 'stage': 'C', 'started': time.time(), 'score': 'not-run',
              'resumed_from_attached_results': imported}
    env = clean_env()
    env.update(CUDA_VISIBLE_DEVICES=str(settings['gpu']['index']), LLM_MODEL=MODEL,
               LLM_API_URL='http://127.0.0.1:8000/v1/chat/completions',
               LLM_API_KEY='local-placeholder', MAX_AGENT_PARALLEL='1', DATASET_TYPE='re2ob',
               TOOL_SERVER_HOST='127.0.0.1', TOOL_SERVER_PORT='5000', LLM_FORCE_STREAM='false',
               VLLM_USE_V1='0', VLLM_NO_USAGE_STATS='1', VLLM_DO_NOT_TRACK='1')
    monitor.thread.start()
    progress = None
    try:
        for port in (8000, 5000):
            assert_free_port(port)  # Never kill another session or increment ports.
        # Downloads weights/config only from the public, non-gated official repo.
        download = 'from huggingface_hub import snapshot_download; print(snapshot_download(repo_id=' + repr(MODEL) + ',revision=' + repr(REVISION) + ',token=False))'
        with (result / 'model-download.log').open('w', encoding='utf-8') as log:
            subprocess.run([str(PYTHON), '-c', download], env=env, stdout=log,
                           stderr=subprocess.STDOUT, check=True, timeout=1200)
        snapshot = TEMP / 'huggingface/hub' / ('models--' + MODEL.replace('/', '--')) / 'snapshots' / REVISION
        if not snapshot.is_dir():
            raise RuntimeError('Pinned model snapshot not found')
        dump(result / 'model-files.json', {p.name: {'bytes': p.stat().st_size, 'sha256': digest(p)} for p in snapshot.iterdir() if p.is_file()})
        env.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
        server = proc.start('vllm', [str(PYTHON), '-m', 'vllm.entrypoints.openai.api_server',
            '--model', str(snapshot), '--tokenizer', str(snapshot), '--served-model-name', MODEL,
            '--revision', REVISION, '--tokenizer-revision', REVISION,
            '--host', '127.0.0.1', '--port', '8000', '--dtype', 'half',
            '--tensor-parallel-size', '1', '--max-num-seqs', '1',
            '--max-model-len', str(settings['context']), '--gpu-memory-utilization', '0.85',
            '--max-num-batched-tokens', str(settings['max_num_batched_tokens']), '--enforce-eager',
            '--enable-auto-tool-choice', '--tool-call-parser', 'hermes',
            '--generation-config', 'vllm', '--disable-log-requests'], env)
        wait_ready(server, 'http://127.0.0.1:8000/health', 600)
        if 'Chunked prefill is enabled' in (result / 'vllm.log').read_text(encoding='utf-8', errors='replace'):
            raise RuntimeError('vLLM turned chunked prefill on; each prompt must be prefilled in one step')
        print('C: pinned local model server ready; single GPU, FP16, context', settings['context'])
        status['stage'] = 'D'
        monitor.phase = 'protocol'
        synth = TEMP / 'synthetic'
        synthetic_data(synth)
        def start_tools(name, data):
            return start_tool_server(proc, name, [str(PYTHON), str(package / 'upstream/tool_server.py')],
                                     dict(env, DATA_ROOT=str(data)), 'http://127.0.0.1:5000/search_span?span_id=probe', 90)
        tools = start_tools('tools-synthetic', synth)
        def worker(phase, data, out, timeout, trace_dir=None, options=()):
            out.mkdir(parents=True)
            worker_env = dict(env, DATA_ROOT=str(data))
            child = proc.start('worker-' + out.name, [str(PYTHON), str(package / 'smoke-worker.py'), phase,
                '--package', str(package), '--output', str(out), '--model-path', str(snapshot),
                '--context', str(settings['context'])] + (['--trace-dir', str(trace_dir)] if trace_dir else []) +
                list(options), worker_env)
            try:
                exit_code = child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.stop(child)
                raise TimeoutError(phase + ' wall-clock limit reached; partial logs retained')
            proc.record()
            state = json.loads((out / 'worker-status.json').read_text()) if (out / 'worker-status.json').exists() else {}
            if exit_code or state.get('status') != 'passed':
                raise RuntimeError(f"{phase} failed: {state.get('fatal') or state.get('error') or 'exit ' + str(exit_code)}")
        protocol = result / 'protocol'
        set_aside(protocol)  # A resumed session checks its own server again.
        worker('protocol', synth, protocol, 480)
        proc.stop(tools)
        print('D: synthetic structured tool calls, tool-role round trip, print_results and request field checks passed')
        status['stage'] = 'E'
        monitor.phase = 'trace'
        def run_trace(trace_dir, out, entry):
            started = time.monotonic()  # Per-trace deadline, tool server start included.
            tools = start_tools('tools-' + out.name, trace_dir / 'input')
            try:
                worker('trace', trace_dir / 'input', out,
                       max(0.1, limits['rcl_deadline_seconds']-(time.monotonic()-started)), trace_dir,
                       worker_options(entry) + limit_options(limits))
            finally:
                proc.stop(tools)
            print('E:', out.name, 'completed in', round(time.monotonic()-started), 's')
        progress = run_traces(package, result, expected_sha256, run_trace, lambda: server.poll() is None)
        print('E: every packaged trace has a final status; failed traces are recorded, not retried')
        status['stage'] = 'F'
        monitor.phase = 'scoring'
        # Stop model inference before opening any groundtruth file.
        proc.stop(server)
        failed = score_runs(package, result, progress, PYTHON, env)
        if failed:
            raise RuntimeError('Author scorer failed for: ' + ', '.join(failed))
        status.update(status='passed', score='author scorer per passed trace; descriptive pilot result, not an accuracy estimate')
    except BaseException as exc:
        status['error'] = repr(exc)
        (result / 'error.txt').write_text(traceback.format_exc(), encoding='utf-8')
        print('STOP:', status['stage'], repr(exc))
    finally:
        try:
            proc.cleanup()
        finally:
            monitor.finish()
            status['finished'] = time.time()
            status['elapsed_seconds'] = status['finished']-status['started']
            if (result / 'progress.json').exists():
                progress = json.loads((result / 'progress.json').read_text())
                outcomes = [t.get('status', 'pending') for t in progress['traces'].values()]
                status['traces'] = {s: outcomes.count(s) for s in sorted(set(outcomes))}
            status['observed_requests'] = {}
            for events in sorted(result.glob('*/events.jsonl')) + sorted(result.glob('traces/*/events.jsonl')):
                count = 0
                for line in events.read_text(encoding='utf-8').splitlines():
                    try:
                        count += json.loads(line).get('kind') == 'request'
                    except json.JSONDecodeError:
                        continue
                status['observed_requests'][events.parent.relative_to(result).as_posix()] = count
            dump(result / 'status.json', status)
            archive = export_results(result)
            atexit.unregister(proc.cleanup)
    if status['status'] != 'passed':
        raise RuntimeError('Run stopped; download partial results, then resume with them attached: ' + str(archive))
    return archive
