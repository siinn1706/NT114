"""CPU tests with deterministic HTTP fixtures. No model or weights are loaded."""
import csv
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CODE = Path('F:/Nam/UIT/nt114-paper-artifacts/W7165616276/code')


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker = load('worker_under_test', 'smoke-worker.py')
runtime = load('runtime_under_test', 'kaggle-runtime.py')


class TokenizerFixture:
    def apply_chat_template(self, *args, **kwargs):
        return [0] * 100


class Handler(BaseHTTPRequestHandler):
    hits = []
    mode = 'valid'

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        type(self).hits.append(body)
        if type(self).mode in ('503', 'oom'):
            self.send_response(503 if type(self).mode == '503' else 500)
            self.end_headers()
            self.wfile.write(b'{"error":"synthetic server error / CUDA OOM fixture"}')
            return
        tools = body.get('tools') or []
        if tools and tools[0]['function']['name'] == 'print_results':
            message = {'role': 'assistant', 'content': None, 'tool_calls': [
                {'id': 'fixture-call', 'type': 'function', 'function': {'name': 'print_results',
                    'arguments': json.dumps({'root_causes': ['synthetic'+str(i) for i in range(10)]})}}]}
        else:
            prompt = body['messages'][-1]['content']
            if 'Span data:\n' in prompt:
                raw = json.loads(prompt.split('Span data:\n', 1)[1].split('\n\nSteps:', 1)[0])
                text = {'span_id': raw['span_id'], 'is_abnormal': False}
            elif prompt.startswith('You are analysing span: '):
                raw = json.loads(prompt.split('\n', 1)[0].removeprefix('You are analysing span: '))
                text = {'span_id': raw['span_id'], 'local_root_cause': 'synthetic'}
            else:
                text = {'fixture': True}
            message = {'role': 'assistant', 'content': json.dumps(text), 'tool_calls': []}
        if type(self).mode == 'bad-schema':
            message = {'content': '', 'tool_calls': [{'type': 'function', 'id': 'bad',
                'function': {'name': 'print_results', 'arguments': '{"root_causes":["too-short"]}'}}]}
        reply = {'choices': [{'message': message, 'finish_reason': 'length' if type(self).mode == 'length' else 'tool_calls' if message.get('tool_calls') else 'stop'}],
                 'usage': {'prompt_tokens': 100, 'completion_tokens': 10}}
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(reply).encode())


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 8000), Handler)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        Handler.hits, Handler.mode = [], 'valid'
        self.area = tempfile.TemporaryDirectory(dir=HERE / 'runtime')
        self.selection = {'query_pairs': [{'service_name': 'synthetic', 'timestamp': '1700000000'}]}
        self.guard = worker.Guard(self.area.name, self.selection, TokenizerFixture(), 16384,
                                 'trace', time.monotonic()+60)
        for name in ('config', 'llm', 'coordinator', 'tools_gpt'):
            sys.modules.pop(name, None)
        os.environ.update(LLM_API_KEY='local-placeholder', LLM_MODEL=runtime.MODEL,
                          LLM_API_URL='http://127.0.0.1:8000/v1/chat/completions',
                          TOOL_SERVER_HOST='127.0.0.1', TOOL_SERVER_PORT='5000',
                          MAX_AGENT_PARALLEL='1', DATASET_TYPE='re2ob')
        self.coordinator, self.llm, self.chat = worker.install_guards(self.guard, CODE)
        from tenacity import wait_none
        self.llm.LLMClient.generate.retry.wait = wait_none()

    def tearDown(self):
        for pool in self.guard.pools:
            pool._executor.shutdown(wait=True, cancel_futures=True)
        self.guard.session.close()
        self.area.cleanup()

    def test_enable_thinking_translation_and_unknown_fields(self):
        result = worker.adapt_payload({'model': runtime.MODEL, 'messages': [], 'enable_thinking': False}, 512)
        self.assertNotIn('enable_thinking', result)
        self.assertEqual(result['chat_template_kwargs'], {'enable_thinking': False})
        with self.assertRaises(ValueError):
            worker.adapt_payload({'model': runtime.MODEL, 'messages': [], 'unknown': 1}, 512)
        with self.assertRaises(ValueError):
            worker.adapt_payload({'model': runtime.MODEL, 'messages': [], 'enable_thinking': True}, 512)

    def test_actual_author_client_tuple_protocol(self):
        content, calls = self.chat([{'role': 'user', 'content': 'fixture'}], None)
        self.assertEqual(json.loads(content), {'fixture': True})
        self.assertEqual(calls, [])
        self.assertEqual(len(Handler.hits), 1)
        self.assertEqual(Handler.hits[0]['chat_template_kwargs'], {'enable_thinking': False})
        self.assertEqual(self.guard.tokens['prompt_tokens'], 100)

    def test_structured_print_results_schema(self):
        from tools_gpt import print_result_function
        _, calls = self.chat([{'role': 'user', 'content': 'fixture'}], [print_result_function])
        self.assertEqual(len(json.loads(calls[0]['function']['arguments'])['root_causes']), 10)
        Handler.mode = 'bad-schema'
        with self.assertRaises(worker.HarnessStop):
            self.chat([{'role': 'user', 'content': 'fixture'}], [print_result_function])

    def test_text_tool_fallback_is_rejected(self):
        from tools_gpt import print_result_function
        for text in ('Action: print_results\nAction Input: {}', '<tool_call>{}</tool_call>'):
            with self.assertRaises(ValueError):
                worker.validate_calls({'content': text}, [print_result_function])

    def test_budget_counts_retry_attempts(self):
        Handler.mode = '503'
        with self.assertRaises(worker.HarnessStop):
            self.chat([{'role': 'user', 'content': 'fixture'}], None)
        self.assertEqual(self.guard.count, 3)
        self.assertEqual(len(Handler.hits), 3)

    def test_no_request_161(self):
        self.guard.count = 159
        self.chat([{'role': 'user', 'content': 'fixture'}], None)
        with self.assertRaises(worker.HarnessStop):
            self.chat([{'role': 'user', 'content': 'fixture'}], None)
        self.assertEqual(self.guard.count, 160)
        self.assertEqual(len(Handler.hits), 1)

    def test_no_context_truncation(self):
        self.guard.context = 600
        with self.assertRaises(worker.HarnessStop):
            self.chat([{'role': 'user', 'content': 'fixture'}], None)
        self.assertEqual(len(Handler.hits), 0)

    def test_oom_and_output_length_are_fatal(self):
        for mode in ('oom', 'length'):
            with self.subTest(mode=mode):
                self.guard.fatal = None
                Handler.mode = mode
                before = len(Handler.hits)
                with self.assertRaises(worker.HarnessStop):
                    self.chat([{'role': 'user', 'content': 'fixture'}], None)
                self.assertEqual(len(Handler.hits), before+1)

    def test_deadline_blocks_request(self):
        self.guard.deadline = time.monotonic()-1
        with self.assertRaises(worker.HarnessStop):
            self.chat([{'role': 'user', 'content': 'fixture'}], None)
        self.assertEqual(len(Handler.hits), 0)

    def test_query_domain_is_bounded(self):
        self.guard.validate_query('search_logs', {'service_name': 'synthetic', 'timestamp': '1700000000123'})
        with self.assertRaises(worker.HarnessStop):
            self.guard.validate_query('search_logs', {'service_name': 'another-case', 'timestamp': '1700000000'})

    def test_local_model_guard_rejects_other_endpoints(self):
        with self.assertRaises(worker.HarnessStop):
            self.guard.post('https://example.invalid/v1/chat/completions', json={})
        self.assertEqual(len(Handler.hits), 0)

    def test_windows_cannot_execute_model(self):
        if sys.platform == 'win32':
            with self.assertRaises(RuntimeError):
                runtime.kaggle_only()

    def test_expanded_kaggle_dataset_hash_verification(self):
        previous = runtime.ROOT
        try:
            runtime.ROOT = Path(self.area.name) / 'expanded-test'
            source = HERE / 'runtime/package'
            manifest_hash = runtime.digest(source / 'manifest.json')
            target = runtime.unpack(source, runtime.digest(HERE / 'rclagent-kaggle-bundle.zip'), manifest_hash)
            self.assertEqual(runtime.digest(target / 'manifest.json'), manifest_hash)
            state = json.loads((runtime.ROOT / 'input-verification.json').read_text())
            self.assertTrue(state['all_member_hashes_verified'])
            self.assertFalse(state['container_zip_hash_checked'])
            with self.assertRaises(RuntimeError):
                runtime.unpack(source, 'unused-for-expanded-content', '0'*64)
        finally:
            runtime.ROOT = previous

    def test_original_recursion_with_33_spans_and_no_model(self):
        path = HERE / 'runtime/package/input/trace/all/trace_jaeger-span.csv'
        rows = list(csv.DictReader(path.open(encoding='utf-8')))
        self.assertEqual(len(rows), 33)
        def build(row):
            return {'span_id': row['span_id'], 'raw': row,
                    'children': [build(child) for child in rows if child['parent_span'] == row['span_id']]}
        graph = build(next(row for row in rows if row['span_id'] == '6752e26884a7fee8'))
        result = self.coordinator.inspect_trace(graph, max_parallel=1)
        self.assertEqual(len(result['root_causes']), 10)
        self.assertEqual(self.guard.count, 67)
        events = [json.loads(line) for line in (Path(self.area.name) / 'events.jsonl').read_text().splitlines()]
        complete = [e for e in events if e['kind'] == 'agent_complete']
        self.assertEqual(len(complete), 66)
        self.assertTrue(all(e['operation'] == 'self_state_verification' for e in complete[:33]))
        consolidated = [e['span_id'] for e in complete[33:]]
        self.assertEqual(len(set(consolidated)), 33)
        for row in rows:
            if row['parent_span']:
                self.assertLess(consolidated.index(row['span_id']), consolidated.index(row['parent_span']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
