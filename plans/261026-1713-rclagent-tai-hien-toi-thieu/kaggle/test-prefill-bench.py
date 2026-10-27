"""CPU checks for prefill-bench.py against a stand-in server; no model, GPU or Kaggle path."""
import importlib.util
import json
import socket
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bench = load('prefill_bench_under_test', 'prefill-bench.py')
runtime = load('runtime_for_bench_test', 'kaggle-runtime.py')

# Prompt time grows with tokens; chunked is ten times slower so its longest prompt passes the client timeout.
STAND_IN = r'''
import json, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
chunked = '--enable-chunked-prefill' in sys.argv
if chunked and '--hide-chunked-line' not in sys.argv:
    print('INFO Chunked prefill is enabled with max_num_batched_tokens=2048.', flush=True)
print('INFO # GPU blocks: 100, # CPU blocks: 0', flush=True)
running = [0]
lock = threading.Lock()
def tokens(body):
    return len(json.dumps(body['messages'])) // 4 + len(json.dumps(body.get('tools') or [])) // 4
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def reply(self, value, kind='application/json'):
        data = value.encode() if isinstance(value, str) else json.dumps(value).encode()
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        if self.path == '/health':
            self.reply('')
        elif self.path == '/metrics':
            self.reply('vllm:num_requests_running{model_name="m"} %d.0\n' % running[0], 'text/plain')
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        count = tokens(body)
        if self.path == '/tokenize':
            assert body['add_generation_prompt'] and body['chat_template_kwargs'] == {'enable_thinking': False}
            return self.reply({'count': count, 'max_model_len': 16384, 'tokens': []})
        with lock:
            running[0] += 1
        try:
            time.sleep(count / (1000 if chunked else 10000))
            completion = 1 if body['max_tokens'] == 1 else 5
            self.reply({'choices': [{'finish_reason': 'length' if completion == 1 else 'stop',
                                     'message': {'content': 'x', 'tool_calls': []}}],
                        'usage': {'prompt_tokens': count, 'completion_tokens': completion}})
        except OSError:
            pass
        finally:
            with lock:
                running[0] -= 1
ThreadingHTTPServer(('127.0.0.1', 8000), Handler).serve_forever()
'''


class StandInProcesses:
    """Same surface as kaggle-runtime Processes, without POSIX process groups."""
    def __init__(self, result):
        self.result, self.children = result, []

    def start(self, name, argv, env):
        log = (self.result / (name + '.log')).open('wb')
        child = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT)
        self.children.append((child, log))
        return child

    def stop(self, child):
        if child.poll() is None:
            child.terminate()
        child.wait(timeout=10)

    def cleanup(self):
        for child, log in self.children:
            self.stop(child)
            log.close()


def payload(chars, max_tokens=1024):
    return {'model': runtime.MODEL, 'messages': [{'role': 'system', 'content': 's'},
                                                 {'role': 'user', 'content': 'y' * chars}],
            'tools': [{'type': 'function', 'function': {'name': 'print_results'}}], 'max_tokens': max_tokens,
            'temperature': 0.7, 'top_p': 0.8, 'top_k': 20, 'min_p': 0.0, 'seed': 20261026,
            'chat_template_kwargs': {'enable_thinking': False}}


class Bench(unittest.TestCase):
    def setUp(self):
        self.area = tempfile.TemporaryDirectory(dir=HERE / 'runtime')
        self.out = Path(self.area.name)
        self.server = self.out / 'stand-in-server.py'
        self.server.write_text(STAND_IN, encoding='utf-8')
        self.saved = bench.OUT, bench.REQUEST_TIMEOUT, bench.CONFIG_BUDGET, bench.PROBE_TOKENS, bench.server_argv
        bench.OUT, bench.REQUEST_TIMEOUT, bench.CONFIG_BUDGET, bench.PROBE_TOKENS = self.out, 1, 120, 3000
        # The base interpreter, not the venv launcher: terminating a launcher on Windows leaves its child serving.
        bench.server_argv = lambda rcl, snapshot, context, scheduling: [sys._base_executable, str(self.server), *scheduling]
        self.rcl = types.SimpleNamespace(PYTHON=sys.executable, MODEL=runtime.MODEL, REVISION=runtime.REVISION,
                                         assert_free_port=runtime.assert_free_port, wait_ready=runtime.wait_ready)
        self.proc = StandInProcesses(self.out)
        self.prompts = [('short', payload(400)), ('middle', payload(2000)), ('long', payload(8000))]

    def tearDown(self):
        self.proc.cleanup()
        bench.OUT, bench.REQUEST_TIMEOUT, bench.CONFIG_BUDGET, bench.PROBE_TOKENS, bench.server_argv = self.saved
        self.area.cleanup()

    def run_config(self, label, scheduling):
        results = []
        bench.run_config(self.rcl, self.proc, {}, 'snapshot', 16384, label, scheduling, self.prompts, results)
        return results[0]

    def test_both_servers_are_timed_on_every_prompt_and_a_timeout_is_recorded_not_fatal(self):
        chunked = self.run_config('chunked-2048', bench.CONFIGS['chunked-2048'])
        self.assertNotIn('error', chunked)
        self.assertTrue(chunked['chunked_prefill_logged'])
        self.assertEqual([(r['prompt'], r['mode']) for r in chunked['rows']],
                         [(n, m) for n, _ in self.prompts for m in ('prefill', 'real')] + [('long-padded', 'prefill')])
        rows = {(r['prompt'], r['mode']): r for r in chunked['rows']}
        self.assertEqual(rows[('short', 'real')]['http_status'], 200)
        self.assertEqual(rows[('short', 'prefill')]['completion_tokens'], 1)
        self.assertEqual(rows[('short', 'real')]['completion_tokens'], 5)
        for mode in ('prefill', 'real'):
            self.assertIsNone(rows[('long', mode)]['http_status'])
            self.assertIn('timed out', rows[('long', mode)]['error'])
            self.assertIn('idle_wait_seconds', rows[('long', mode)])
        self.assertTrue(2800 < chunked['prompt_tokens']['long-padded'] <= 3000)
        self.assertIsNotNone(chunked['server_exit'])

        unchunked = self.run_config('unchunked-16384', bench.CONFIGS['unchunked-16384'])
        self.assertNotIn('error', unchunked)
        self.assertFalse(unchunked['chunked_prefill_logged'])
        self.assertTrue(all(r['http_status'] == 200 for r in unchunked['rows']))

    def test_a_server_whose_log_disagrees_with_the_intended_setting_is_not_measured(self):
        record = self.run_config('chunked-2048', ['--enable-chunked-prefill', '--hide-chunked-line'])
        self.assertIn('does not match', record['error'])
        self.assertEqual(record['rows'], [])

    def hold_port(self, seconds):
        holder = socket.socket()
        holder.bind(('127.0.0.1', 8000))
        holder.listen()
        timer = threading.Timer(seconds, holder.close)
        timer.start()
        self.addCleanup(timer.cancel)
        self.addCleanup(holder.close)

    def test_the_next_server_waits_for_the_port_the_previous_one_left_busy(self):
        self.hold_port(3)
        record = self.run_config('unchunked-16384', bench.CONFIGS['unchunked-16384'])
        self.assertNotIn('error', record)
        self.assertGreaterEqual(record['port_wait_seconds'], 2)
        self.assertTrue(all(r['http_status'] == 200 for r in record['rows']))

    def test_a_port_that_never_frees_is_recorded_and_no_server_starts(self):
        self.hold_port(60)
        self.addCleanup(setattr, bench, 'PORT_WAIT', bench.PORT_WAIT)
        bench.PORT_WAIT = 3
        results = []
        bench.run_config(self.rcl, self.proc, {}, 'snapshot', 16384, 'unchunked-16384',
                         bench.CONFIGS['unchunked-16384'], self.prompts, results)
        self.assertIn('port 8000 still in use', results[0]['error'])
        self.assertEqual(results[0]['rows'], [])
        self.assertEqual(self.proc.children, [])

    def test_time_budget_skips_the_remaining_prompts(self):
        bench.CONFIG_BUDGET = 29
        record = self.run_config('unchunked-16384', bench.CONFIGS['unchunked-16384'])
        self.assertTrue(record['rows'] and all('skipped' in r for r in record['rows']))


if __name__ == '__main__':
    unittest.main()
