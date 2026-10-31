"""Long-prompt timing on one T4: the pilot's vLLM server against the same server without chunked prefill.

Standard library only. The model server runs in the isolated environment that the pilot runtime installs
(`rcl.install`). No RCLAgent code, tool server, groundtruth or scorer is touched. Each prompt is a request
the pilot actually sent, replayed twice per server: once unchanged (end-to-end time under the upstream
180-second client timeout) and once with max_tokens=1 (prefill time). One extra prefill-only probe pads
the longest prompt to PROBE_TOKENS to see how the unchunked server copes near the 16k context.
"""
import json
import subprocess
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

# The pilot's server flags are kept as they are, except the two that decide chunked prefill.
# chunked-2048 is the pilot server up to Kaggle version 10; unchunked-16384 is the pilot server since.
# Without --enable-chunked-prefill and with max_model_len <= 32K, vLLM 0.10.2 V0 leaves it off.
CONFIGS = {
    'chunked-2048': ['--max-num-batched-tokens', '2048', '--enable-chunked-prefill'],
    'unchunked-16384': ['--max-num-batched-tokens', '16384'],
}
CHUNKED_LOG_LINE = 'Chunked prefill is enabled with max_num_batched_tokens'
REQUEST_TIMEOUT = 900
CONFIG_BUDGET = 2700
PROBE_TOKENS = 14000
PORT_WAIT = 300
OUT = Path('/kaggle/working/prefill-bench')


def server_argv(rcl, snapshot, context, scheduling):
    return [str(rcl.PYTHON), '-m', 'vllm.entrypoints.openai.api_server',
            '--model', str(snapshot), '--tokenizer', str(snapshot), '--served-model-name', rcl.MODEL,
            '--revision', rcl.REVISION, '--tokenizer-revision', rcl.REVISION,
            '--host', '127.0.0.1', '--port', '8000', '--dtype', 'half',
            '--tensor-parallel-size', '1', '--max-num-seqs', '1',
            '--max-model-len', str(context), '--gpu-memory-utilization', '0.85',
            *scheduling, '--enforce-eager',
            '--enable-auto-tool-choice', '--tool-call-parser', 'hermes',
            '--generation-config', 'vllm', '--disable-log-requests']


def post(url, body, timeout):
    """One request; returns (seconds, status, parsed body or error text). No proxy, no retry."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    started = time.monotonic()
    try:
        with opener.open(request, timeout=timeout) as response:
            return time.monotonic() - started, response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return time.monotonic() - started, exc.code, exc.read().decode(errors='replace')[:2000]
    except (OSError, ValueError) as exc:
        return time.monotonic() - started, None, repr(exc)


def count_tokens(base, payload):
    _, status, body = post(base + '/tokenize', {'model': payload['model'], 'messages': payload['messages'],
                                                'tools': payload.get('tools'), 'add_generation_prompt': True,
                                                'chat_template_kwargs': payload.get('chat_template_kwargs')}, 120)
    if status != 200:
        raise RuntimeError('tokenize failed: ' + str(body)[:300])
    return body['count']


def padded_probe(base, payload, target):
    """The longest prompt with its last user message repeated, cut to about `target` tokens."""
    text = payload['messages'][-1]['content']
    def build(chars):
        messages = [dict(m) for m in payload['messages']]
        messages[-1]['content'] = (text * (target // 1000 + 2))[:chars]
        return dict(payload, messages=messages)
    low, high = len(text), len(text) * (target // 1000 + 2)
    while high - low > 200:
        middle = (low + high) // 2
        low, high = (middle, high) if count_tokens(base, build(middle)) <= target else (low, middle)
    return build(low)


def running_requests(base):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(base + '/metrics', timeout=10) as response:
        for line in response.read().decode().splitlines():
            if line.startswith('vllm:num_requests_running'):
                return float(line.rsplit(' ', 1)[1])
    raise RuntimeError('vllm:num_requests_running not in /metrics')


def wait_idle(base, limit=600):
    """A timed-out request may still be running server-side; the next timing must not queue behind it."""
    started = time.monotonic()
    while running_requests(base) > 0:
        if time.monotonic() - started > limit:
            raise RuntimeError('server still busy after a timed-out request')
        time.sleep(2)
    return round(time.monotonic() - started, 1)


def measure(base, name, payload, mode, timeout):
    body = dict(payload, max_tokens=1) if mode == 'prefill' else payload
    seconds, status, reply = post(base + '/v1/chat/completions', body, timeout)
    row = {'prompt': name, 'mode': mode, 'seconds': round(seconds, 2), 'http_status': status}
    if status == 200:
        choice = reply['choices'][0]
        row.update(prompt_tokens=reply['usage']['prompt_tokens'], completion_tokens=reply['usage']['completion_tokens'],
                   finish_reason=choice['finish_reason'], content=choice['message'].get('content'),
                   tool_calls=choice['message'].get('tool_calls'))
    else:
        row['error'] = str(reply)[:2000]
    return row


def wait_port_free(rcl, port):
    """A stopped server's port can stay unbindable for a while (TIME_WAIT); never move to another port."""
    limit, started = PORT_WAIT, time.monotonic()
    while True:
        try:
            rcl.assert_free_port(port)
            return round(time.monotonic() - started, 1)
        except OSError:
            if time.monotonic() - started > limit:
                try:
                    listing = subprocess.run(['ss', '-tanp'], capture_output=True, text=True).stdout
                except OSError:
                    listing = ''
                raise RuntimeError(f'port {port} still in use after {limit} s:\n' +
                                   '\n'.join(line for line in listing.splitlines() if f':{port} ' in line)[:2000])
            time.sleep(2)


def run_config(rcl, proc, env, snapshot, context, label, scheduling, prompts, results):
    log_path = OUT / ('vllm-' + label + '.log')
    record = {'config': label, 'argv_scheduling': scheduling, 'rows': []}
    results.append(record)
    server = None
    try:
        record['port_wait_seconds'] = wait_port_free(rcl, 8000)
        server = proc.start('vllm-' + label, server_argv(rcl, snapshot, context, scheduling), env)
        started = time.monotonic()
        rcl.wait_ready(server, 'http://127.0.0.1:8000/health', 900)
        record['startup_seconds'] = round(time.monotonic() - started, 1)
        log = log_path.read_text(encoding='utf-8', errors='replace')
        record['chunked_prefill_logged'] = CHUNKED_LOG_LINE in log
        record['kv_cache_lines'] = [line for line in log.splitlines()
                                    if '# cuda blocks' in line or 'Maximum concurrency' in line or 'activation peak' in line][:4]
        if record['chunked_prefill_logged'] != ('--enable-chunked-prefill' in scheduling):
            raise RuntimeError(label + ': server log does not match the intended chunked-prefill setting')
        base = 'http://127.0.0.1:8000'
        deadline = time.monotonic() + CONFIG_BUDGET
        cases = [(name, payload, mode) for name, payload in prompts for mode in ('prefill', 'real')]
        longest_name, longest = prompts[-1]
        probe = padded_probe(base, longest, PROBE_TOKENS)
        cases.append((longest_name + '-padded', probe, 'prefill'))
        record['prompt_tokens'] = {name: count_tokens(base, payload) for name, payload, mode in cases if mode == 'prefill'}
        for name, payload, mode in cases:
            left = deadline - time.monotonic()
            if left < 30:
                record['rows'].append({'prompt': name, 'mode': mode, 'skipped': 'config time budget used'})
                continue
            if server.poll() is not None:
                raise RuntimeError(label + ': server exited during measurement')
            row = measure(base, name, payload, mode, min(REQUEST_TIMEOUT, left))
            if row['http_status'] != 200:
                row['idle_wait_seconds'] = wait_idle(base)
            record['rows'].append(row)
            print(label, name, mode, row.get('seconds'), row.get('http_status'), row.get('prompt_tokens'), flush=True)
    except BaseException as exc:
        record['error'] = repr(exc)
        print(label, 'stopped:', repr(exc), flush=True)
    finally:
        if server is not None:
            proc.stop(server)
            record['server_exit'] = server.poll()


def run(rcl, payloads_path, only=None):
    """Measure every server in CONFIGS, or only the labels in `only`."""
    configs = {label: flags for label, flags in CONFIGS.items() if only is None or label in only}
    if not configs or (only and set(only) - set(CONFIGS)):
        raise RuntimeError('unknown configuration in ' + repr(only))
    rcl.kaggle_only()
    settings = json.loads((rcl.ROOT / 'settings.json').read_text())
    if json.loads((rcl.ROOT / 'compatibility/status.json').read_text())['status'] != 'passed':
        raise RuntimeError('Run cell B (install and T4 kernel check) first')
    prompts = sorted(json.loads(Path(payloads_path).read_text(encoding='utf-8')).items(),
                     key=lambda item: len(json.dumps(item[1])))
    if OUT.exists():
        raise RuntimeError(str(OUT) + ' exists; this notebook measures once per session')
    OUT.mkdir(parents=True)
    env = rcl.clean_env()
    env.update(CUDA_VISIBLE_DEVICES=str(settings['gpu']['index']), VLLM_USE_V1='0',
               VLLM_NO_USAGE_STATS='1', VLLM_DO_NOT_TRACK='1')
    download = ('from huggingface_hub import snapshot_download; print(snapshot_download(repo_id=' + repr(rcl.MODEL)
                + ',revision=' + repr(rcl.REVISION) + ',token=False))')
    with (OUT / 'model-download.log').open('w', encoding='utf-8') as log:
        subprocess.run([str(rcl.PYTHON), '-c', download], env=env, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=1200)
    snapshot = rcl.TEMP / 'huggingface/hub' / ('models--' + rcl.MODEL.replace('/', '--')) / 'snapshots' / rcl.REVISION
    if not snapshot.is_dir():
        raise RuntimeError('Pinned model snapshot not found')
    env.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    proc = rcl.Processes(OUT)
    results = []
    summary = {'started': time.time(), 'gpu': settings['gpu'], 'context': settings['context'],
               'prompts': [name for name, _ in prompts], 'request_timeout': REQUEST_TIMEOUT,
               'config_budget_seconds': CONFIG_BUDGET, 'probe_tokens': PROBE_TOKENS, 'configs': results}
    try:
        for label, scheduling in configs.items():
            run_config(rcl, proc, env, snapshot, settings['context'], label, scheduling, prompts, results)
            rcl.dump(OUT / 'prefill-bench.json', summary)
    finally:
        proc.cleanup()
        summary['finished'] = time.time()
        rcl.dump(OUT / 'prefill-bench.json', summary)
        archive = OUT.parent / 'prefill-bench-results.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipped:
            for path in sorted(OUT.rglob('*')):
                if path.is_file():
                    zipped.write(path, path.relative_to(OUT.parent).as_posix())
        (OUT.parent / 'prefill-bench-results.zip.sha256').write_text(rcl.digest(archive) + '  ' + archive.name + '\n')
    return archive
