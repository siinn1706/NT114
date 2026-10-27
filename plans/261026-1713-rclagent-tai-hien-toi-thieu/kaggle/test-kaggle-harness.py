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
import zipfile
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
                if type(self).mode == 'null-root-cause':
                    # the shape of the v9 leaf answers that stopped two traces
                    text = {'span_id': raw['span_id'], 'service_name': raw['cmdb_id'], 'local_root_cause': None,
                            'has_error_logs': False, 'reason': 'No downstream child spans are available.',
                            'confidence': 0.0}
                elif type(self).mode == 'missing-root-cause':
                    del text['local_root_cause']
                elif type(self).mode == 'numeric-root-cause':
                    text['local_root_cause'] = 0
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
        self.selection = {'query_window': {'start_second': 1700000000, 'end_second': 1700000001}}
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

    def test_oversized_tool_result_stops_before_sending(self):
        class CharacterTokenizer:
            def apply_chat_template(self, messages, **kwargs):
                return [0] * sum(len(m.get('content') or '') for m in messages)
        self.guard.tokenizer = CharacterTokenizer()
        messages = [{'role': 'user', 'content': 'fixture'},
                    {'role': 'assistant', 'content': '', 'tool_calls': [{'id': 'a', 'type': 'function',
                     'function': {'name': 'search_logs', 'arguments': '{}'}}]},
                    {'role': 'tool', 'tool_call_id': 'a', 'content': 'x' * 20000}]
        with self.assertRaises(worker.HarnessStop):
            self.chat(messages, None)
        self.assertIn('Context overflow', self.guard.fatal)
        self.assertIn('no truncation', self.guard.fatal)
        self.assertEqual(len(Handler.hits), 0)
        self.assertEqual(self.guard.count, 0)

    def test_oom_and_output_length_are_fatal(self):
        for mode in ('oom', 'length'):
            with self.subTest(mode=mode):
                self.guard.fatal = None
                Handler.mode = mode
                before = len(Handler.hits)
                with self.assertRaises(worker.HarnessStop):
                    self.chat([{'role': 'user', 'content': 'fixture'}], None)
                self.assertEqual(len(Handler.hits), before+1)

    def leaf_trace(self):
        """The paymentservice leaf of trace 2095688a and its parent, as the v9 run saw them."""
        common = {'operation_name': 'grpc.hipstershop.PaymentService/Charge', 'status_code': '0',
                  'trace_id': '2095688a1eb7e72f9efbd9fad2b36a50', 'type': 'rpc'}
        leaf = dict(common, cmdb_id='paymentservice', duration='253', parent_span='149400ec465d7e63',
                    span_id='b81ba52867406a5c', timestamp='1705517089465')
        parent = dict(common, cmdb_id='checkoutservice', duration='1012', parent_span='',
                      span_id='149400ec465d7e63', timestamp='1705517089400')
        return {'span_id': parent['span_id'], 'raw': parent,
                'children': [{'span_id': leaf['span_id'], 'raw': leaf, 'children': []}]}

    def test_version9_null_local_root_cause_regression(self):
        """Cause: v9 stopped two traces on a leaf answering local_root_cause null, which upstream passes upward."""
        Handler.mode = 'null-root-cause'
        result = self.coordinator.inspect_trace(self.leaf_trace(), max_parallel=1)
        self.assertIsNone(self.guard.fatal)
        self.assertEqual(len(result['root_causes']), 10)
        events = [json.loads(line) for line in (Path(self.area.name) / 'events.jsonl').read_text().splitlines()]
        consolidated = [json.loads(e['output']) for e in events
                        if e['kind'] == 'agent_complete' and e['operation'] == 'consolidate']
        self.assertEqual([c['span_id'] for c in consolidated], ['b81ba52867406a5c', '149400ec465d7e63'])
        self.assertTrue(all(c['local_root_cause'] is None for c in consolidated))

    def test_consolidation_without_a_local_root_cause_field_still_stops(self):
        for mode in ('missing-root-cause', 'numeric-root-cause'):
            with self.subTest(mode=mode):
                self.guard.fatal = None
                Handler.mode = mode
                with self.assertRaises(worker.HarnessStop):
                    self.coordinator.inspect_trace(self.leaf_trace(), max_parallel=1)
                self.assertIn('local_root_cause', self.guard.fatal)

    def test_deadline_blocks_request(self):
        self.guard.deadline = time.monotonic()-1
        with self.assertRaises(worker.HarnessStop):
            self.chat([{'role': 'user', 'content': 'fixture'}], None)
        self.assertEqual(len(Handler.hits), 0)

    def test_query_window_allows_any_service(self):
        for service in ('synthetic', 'cartservice', 'another-service'):
            for stamp in ('1700000000123', '1700000001', ' 1700000000 '):
                self.guard.validate_query('search_logs', {'service_name': service, 'timestamp': stamp})
                self.guard.validate_query('search_fluctuating_metrics', {'service_name': service, 'timestamp': stamp})
        self.assertIsNone(self.guard.fatal)

    def test_query_outside_window_is_refused(self):
        for stamp in ('1699999999999', '1700000002', 'not-a-time'):
            with self.subTest(stamp=stamp):
                self.guard.fatal = None
                with self.assertRaises(worker.HarnessStop):
                    self.guard.validate_query('search_logs', {'service_name': 'cartservice', 'timestamp': stamp})
        self.guard.fatal = None
        with self.assertRaises(worker.HarnessStop):
            self.guard.validate_query('search_logs', {'service_name': 'cartservice', 'timestamp': '1700000000', 'extra': 1})

    def test_windows_outside_all_full_data_are_answerable_and_bounded(self):
        selection = {'query_window': {'start_second': 1700000000, 'end_second': 1700000001,
                                      'full_data_seconds': {'log': [1000, 2000], 'metric': [1000, 2000]}}}
        guard = worker.Guard(self.area.name, selection, TokenizerFixture(), 16384, 'trace', time.monotonic()+60)
        cases = [('search_logs', 939, True), ('search_logs', 940, False), ('search_logs', 2061, True),
                 ('search_logs', 2060, False), ('search_fluctuating_metrics', 3201, True),
                 ('search_fluctuating_metrics', 3200, False), ('search_fluctuating_metrics', 1500, False),
                 ('search_fluctuating_metrics', -201, True)]
        for name, second, allowed in cases:
            with self.subTest(name=name, second=second):
                guard.fatal = None
                params = {'service_name': 'cartservice', 'timestamp': str(second)}
                if allowed:
                    guard.validate_query(name, params)
                    self.assertIsNone(guard.fatal)
                else:
                    with self.assertRaises(worker.HarnessStop):
                        guard.validate_query(name, params)
        guard.session.close()

    def test_version7_mistyped_metric_timestamp_regression(self):
        """Cause: v7 stopped on a timestamp 3 years after all data, which upstream answers as empty."""
        package = HERE / 'runtime/package'
        selection = json.loads((package / 'selection.json').read_text())
        call = {'service_name': 'productcatalogservice', 'timestamp': '1808475368747'}
        old = {'query_window': {k: v for k, v in selection['query_window'].items() if k != 'full_data_seconds'}}
        old_guard = worker.Guard(self.area.name, old, TokenizerFixture(), 16384, 'trace', time.monotonic()+60)
        with self.assertRaises(worker.HarnessStop):
            old_guard.validate_query('search_fluctuating_metrics', call)
        guard = worker.Guard(self.area.name, selection, TokenizerFixture(), 16384, 'trace', time.monotonic()+60)
        guard.validate_query('search_fluctuating_metrics', call)
        guard.validate_query('search_logs', call)
        self.assertIsNone(guard.fatal)
        # The packaged endpoints give the empty answers the full data gives for that second.
        spec = importlib.util.spec_from_file_location('prepare_bundle_test', HERE / 'prepare-bundle.py')
        prepare = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(prepare)
        ns, client = prepare.endpoint_module()
        import pandas as pd
        ns['metric_df'] = pd.read_csv(package / 'input/metric/all/metrics.csv', low_memory=False)
        ns['log_df'] = pd.read_csv(package / 'input/log/all/logs.csv', low_memory=False)
        self.assertEqual(client.get('/search_fluctuating_metrics', query_string=call).get_json(),
                         {'message': 'No matching records found.'})
        self.assertEqual(client.get('/search_logs', query_string=call).data.decode().splitlines(),
                         ['log_id,timestamp,cmdb_id,log_name,value'])
        old_guard.session.close()
        guard.session.close()

    def test_url_parameter_injection_is_checked_where_the_server_reads_it(self):
        # Upstream builds the URL without encoding; a second timestamp would reach the server first.
        with self.assertRaises(worker.HarnessStop):
            self.coordinator._get('search_logs', {'service_name': 'x&timestamp=1', 'timestamp': '1700000000'})
        self.assertIn('outside the packaged time window', self.guard.fatal)

    def test_version5_cartservice_request_regression(self):
        """Cause: v5 allowed only trace-span pairs. Fix: the exact v5 call is covered and answered as full data."""
        old = json.loads((HERE / 'runtime/package-v5/selection.json').read_text())
        new = json.loads((HERE / 'runtime/package/selection.json').read_text())
        call = {'service_name': 'cartservice', 'timestamp': '1708475368662'}
        old_pairs = {(p['service_name'], p['timestamp']) for p in old['query_pairs']}
        self.assertNotIn((call['service_name'], call['timestamp'][:10]), old_pairs)
        self.assertNotIn('cartservice', {service for service, _ in old_pairs})
        guard = worker.Guard(self.area.name, new, TokenizerFixture(), 16384, 'trace', time.monotonic()+60)
        guard.validate_query('search_logs', call)
        guard.validate_query('search_fluctuating_metrics', call)
        self.assertIsNone(guard.fatal)
        parity = json.loads((HERE / 'runtime/package/cpu-equivalence.json').read_text())
        matched = [c for c in parity['comparisons'] if c['params'] == call]
        self.assertEqual({c['endpoint'] for c in matched}, {'search_logs', 'search_fluctuating_metrics'})
        self.assertTrue(all(c['equal'] for c in matched))
        logs = next(c for c in matched if c['endpoint'] == 'search_logs')
        self.assertEqual(logs['response_bytes'], 274292)  # 1,570 full-data cartservice rows; v5 had none.
        self.assertIn('cartservice', parity['nonempty_log_responses'])
        guard.session.close()

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
            # The staged package that was promoted to the bundle, as Kaggle expands it.
            manifest_hash = runtime.digest(HERE / 'manifest.json')
            source = next(p.parent for p in sorted((HERE / 'runtime').glob('package*/manifest.json'))
                          if runtime.digest(p) == manifest_hash)
            target = runtime.unpack(source, runtime.digest(HERE / 'rclagent-kaggle-bundle.zip'), manifest_hash)
            self.assertEqual(runtime.digest(target / 'manifest.json'), manifest_hash)
            state = json.loads((runtime.ROOT / 'input-verification.json').read_text())
            self.assertTrue(state['all_member_hashes_verified'])
            self.assertFalse(state['container_zip_hash_checked'])
            with self.assertRaises(RuntimeError):
                runtime.unpack(source, 'unused-for-expanded-content', '0'*64)
        finally:
            runtime.ROOT = previous

    def test_known_services_follow_upstream_config(self):
        prepare = load('prepare_under_test', 'prepare-bundle.py')
        self.assertEqual(prepare.KNOWN_SERVICES, tuple(self.coordinator._KNOWN_SERVICES))
        with tempfile.TemporaryDirectory() as area:
            text = (CODE / 'config.py').read_text(encoding='utf-8')
            edited = text.replace('"shippingservice", "redis",', '"shippingservice", "redis", "fixtureservice",')
            self.assertNotEqual(edited, text)
            (Path(area) / 'config.py').write_text(edited, encoding='utf-8')
            self.assertEqual(prepare.upstream_known_services(Path(area)), prepare.KNOWN_SERVICES + ('fixtureservice',))

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


class BatchRuntime(unittest.TestCase):
    """The trace loop with an injected per-trace runner; no model, server or Kaggle path."""
    def setUp(self):
        self.area = tempfile.TemporaryDirectory(dir=HERE / 'runtime')
        self.package, self.result = Path(self.area.name) / 'package', Path(self.area.name) / 'run'
        self.package.mkdir()
        self.result.mkdir()
        self.ids = ['trace-a', 'trace-b', 'trace-c']
        (self.package / 'manifest.json').write_text(json.dumps({'traces': [
            {'dir': 'traces/' + t, 'trace_id': t, 'case': 'case-' + t[-1], 'span_count': 3} for t in self.ids]}))
        self.calls, self.failing, self.alive = [], set(), True

    def tearDown(self):
        self.area.cleanup()

    def run_trace(self, trace_dir, out):
        self.calls.append(trace_dir.name)
        out.mkdir(parents=True)
        if trace_dir.name in self.failing:
            raise RuntimeError('synthetic HarnessStop for ' + trace_dir.name)

    def run_batch(self, bundle='bundle-1'):
        return runtime.run_traces(self.package, self.result, bundle, self.run_trace, lambda: self.alive)

    def test_failed_trace_is_recorded_and_the_next_trace_runs(self):
        self.failing = {'trace-b'}
        progress = self.run_batch()
        self.assertEqual(self.calls, self.ids)
        states = progress['traces']
        self.assertEqual([states[t]['status'] for t in self.ids], ['passed', 'failed', 'passed'])
        self.assertIn('synthetic HarnessStop', states['trace-b']['reason'])
        self.assertEqual(json.loads((self.result / 'progress.json').read_text()), progress)

    def test_resume_skips_finished_traces_and_reruns_an_interrupted_one(self):
        self.failing = {'trace-b'}
        self.run_batch()
        progress = json.loads((self.result / 'progress.json').read_text())
        progress['traces']['trace-c'].update(status='running')
        (self.result / 'progress.json').write_text(json.dumps(progress))
        self.calls, self.failing = [], set()
        progress = self.run_batch()
        self.assertEqual(self.calls, ['trace-c'])  # The failed trace is never retried.
        self.assertEqual(progress['traces']['trace-b']['status'], 'failed')
        attempts = progress['traces']['trace-c']['attempts']
        self.assertEqual([a['outcome'] for a in attempts], ['interrupted', 'passed'])
        self.assertTrue((self.result / 'traces/trace-c.previous-0').is_dir())

    def test_dead_model_server_stops_the_batch_and_leaves_traces_pending(self):
        self.alive = False
        with self.assertRaises(RuntimeError):
            self.run_batch()
        self.assertEqual(self.calls, [])
        self.assertNotIn('status', json.loads((self.result / 'progress.json').read_text())['traces'].get('trace-a', {}))

    def test_progress_of_another_bundle_is_refused(self):
        self.run_batch()
        with self.assertRaises(RuntimeError):
            self.run_batch('bundle-2')

    def test_prior_results_are_imported_from_an_attached_archive(self):
        self.failing = {'trace-b'}
        self.run_batch()
        prior = Path(self.area.name) / 'input/previous-version'
        prior.mkdir(parents=True)
        with zipfile.ZipFile(prior / 'rclagent-smoke-results.zip', 'w') as zipped:
            for path in sorted(self.result.rglob('*')):
                if path.is_file():
                    zipped.write(path, 'run/' + path.relative_to(self.result).as_posix())
        fresh = Path(self.area.name) / 'fresh-run'
        fresh.mkdir()
        previous = runtime.INPUT
        try:
            runtime.INPUT = Path(self.area.name) / 'input'
            self.assertTrue(runtime.import_prior(fresh, 'bundle-1'))
            with self.assertRaises(RuntimeError):
                runtime.import_prior(fresh, 'bundle-2')
        finally:
            runtime.INPUT = previous
        self.calls = []
        progress = runtime.run_traces(self.package, fresh, 'bundle-1', self.run_trace, lambda: True)
        self.assertEqual(self.calls, [])
        self.assertEqual(progress['traces']['trace-b']['status'], 'failed')

    def test_span_count_comes_from_selection(self):
        graph = {'span_id': 'r', 'children': [{'span_id': 'a', 'children': []}, {'span_id': 'b', 'children': []}]}
        self.assertEqual(len(worker.graph_nodes(graph, {'span_count': 3})), 3)
        with self.assertRaises(AssertionError):
            worker.graph_nodes(graph, {'span_count': 33})


class PackageValidator(unittest.TestCase):
    """verify-package's per-trace check over the single-trace package, mounted as one of two batch traces."""
    ENTRY = {'trace_id': '68791e1f360d910bd01428c3cd9748ef', 'case': 'checkoutservice_cpu_2', 'span_count': 33}

    @classmethod
    def setUpClass(cls):
        cls.verify = load('verify_under_test', 'verify-package.py')
        package = HERE / 'runtime/package'
        cls.files = {}
        for path in package.rglob('*'):
            relative = path.relative_to(package).as_posix()
            if path.is_file() and relative.startswith(('input/', 'scoring/', 'selection.json', 'cpu-equivalence.json')):
                for base in ('traces/a/', 'traces/b/'):
                    cls.files[base + relative] = path.read_bytes()

    def check(self, files, base='traces/b', **entry):
        return self.verify.check_trace(files.__getitem__, list(files), dict(self.ENTRY, dir=base, **entry))

    def test_each_trace_directory_is_checked_on_its_own(self):
        self.assertEqual(self.check(self.files, 'traces/a')['trace_rows'], 33)
        self.assertEqual(self.check(self.files)['log_rows'], self.check(self.files, 'traces/a')['log_rows'])

    def test_rows_of_another_case_label_columns_and_wrong_span_counts_fail(self):
        logs = 'traces/b/input/log/all/logs.csv'
        foreign = dict(self.files, **{logs: self.files[logs].replace(b're2ob_checkoutservice_cpu_2_', b're2ob_checkoutservice_cpu_3_', 1)})
        metrics = 'traces/b/input/metric/all/metrics.csv'
        labelled = dict(self.files, **{metrics: self.files[metrics].replace(b'kpi_name', b'label', 1)})
        for files, entry in ((foreign, {}), (labelled, {}), (self.files, {'span_count': 34}), (self.files, {'case': 'checkoutservice_cpu_3'})):
            with self.assertRaises(AssertionError):
                self.check(files, **entry)
        self.check(self.files, 'traces/a')  # The other trace stays valid.


if __name__ == '__main__':
    unittest.main(verbosity=2)
