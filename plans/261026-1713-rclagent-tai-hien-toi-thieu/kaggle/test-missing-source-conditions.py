"""CPU tests for the controlled missing-source runs: per-run seed, absent sources, the repaired metric endpoint and
the run matrix. No model is loaded; the repaired endpoint is checked on the packaged data of pilot trace 1e527c6a."""
import importlib.util
import json
import os
import pickle
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pandas as pd

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CODE = Path('F:/Nam/UIT/nt114-paper-artifacts/W7165616276/code')
PILOT = HERE / 'runtime/package-pilot-01/traces/1e527c6a967e105118fdc1acdf739e02'
SECOND = 1705690314  # First span second of that trace.
PARAMS = {'service_name': 'currencyservice', 'timestamp': str(SECOND) + '687'}


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker = load('worker_conditions_test', 'smoke-worker.py')
runtime = load('runtime_conditions_test', 'kaggle-runtime.py')
conditions = load('conditions_test', 'add-condition-runs.py')
repair = worker.metric_repair


def author_endpoints(log_df, metric_df, service_node_map):
    """The author's unchanged endpoint bodies, served by a Flask test client over the given frames."""
    prepare = load('prepare_bundle_conditions_test', 'prepare-bundle.py')
    namespace, client = prepare.endpoint_module()
    namespace.update(log_df=log_df, metric_df=metric_df, service_node_map=service_node_map)
    return client


class Telemetry(BaseHTTPRequestHandler):
    hits = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        type(self).hits.append(self.path)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'author-server-body\n')


class Tokenizer:
    def __call__(self, text, add_special_tokens=False):
        return {'input_ids': list(text)}

    def apply_chat_template(self, *args, **kwargs):
        return [0] * 100


class AuthorBytes(unittest.TestCase):
    def test_absent_responses_are_the_author_endpoints_no_row_bytes(self):
        client = author_endpoints(pd.DataFrame(columns=['log_id', 'timestamp', 'cmdb_id', 'log_name', 'value']),
                                  pd.DataFrame(columns=['timestamp', 'node_id', 'service_name', 'kpi_name', 'value']), {})
        query = '?service_name=currencyservice&timestamp=' + PARAMS['timestamp']
        # pandas writes os.linesep; on Kaggle (Linux) that is the 40-byte '\n' body recorded in the v11 events.
        self.assertEqual(client.get('/search_logs' + query).get_data(as_text=True).replace(os.linesep, '\n'),
                         worker.ABSENT_RESPONSE['search_logs'])
        self.assertEqual(client.get('/search_fluctuating_metrics' + query).get_data(as_text=True),
                         worker.ABSENT_RESPONSE['search_fluctuating_metrics'])


class RepairedMetric(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metric_df = pd.read_csv(PILOT / 'input/metric/all/metrics.csv', low_memory=False)
        with (PILOT / 'input/metric/service_node_map.pkl').open('rb') as f:
            cls.node_map = pickle.load(f)

    def answer(self, service):
        return repair.search_fluctuating_metrics(self.metric_df, self.node_map, service, PARAMS['timestamp'])

    def test_author_endpoint_never_reports_a_kpi_on_re2ob(self):
        client = author_endpoints(pd.DataFrame(), self.metric_df, self.node_map)
        for service in ('currencyservice', 'cartservice', 'productcatalogservice'):
            body = client.get(f"/search_fluctuating_metrics?service_name={service}&timestamp={PARAMS['timestamp']}")
            self.assertEqual(body.get_data(as_text=True), repair.NO_KPI)  # Every node_id is NaN: no group survives.
        self.assertTrue(self.metric_df['node_id'].isna().all())

    def test_repaired_endpoint_reports_the_faulty_service_in_the_author_format(self):
        body = self.answer('currencyservice')
        lines = body.splitlines()
        self.assertEqual(lines[0], 'key,regular_mean,regular_std_dev,current_mean,current_std_dev')
        self.assertIn('currencyservice.mem', [line.split(',')[0] for line in lines[1:]])

    def test_unmatched_service_keeps_the_author_no_row_reply(self):
        self.assertEqual(self.answer('frontendservice'), repair.NO_ROWS)

    def test_threshold_and_baseline_window(self):
        rows = [(t, None, 'svc', 'kpi', 1.0 + (t % 2) * 0.01) for t in range(SECOND - 1200, SECOND - 600)]
        quiet = pd.DataFrame(rows + [(t, None, 'svc', 'kpi', 1.0) for t in range(SECOND - 600, SECOND + 601)],
                             columns=['timestamp', 'node_id', 'service_name', 'kpi_name', 'value'])
        self.assertEqual(repair.search_fluctuating_metrics(quiet, {}, 'svc', SECOND), repair.NO_KPI)
        # Baseline std is 0.005, so a shift of 0.4 (80 std) stays quiet and a shift of 0.6 (120 std) is reported.
        for shift, reported in ((0.4, False), (0.6, True)):
            moved = quiet.copy()
            moved.loc[moved.timestamp >= SECOND - 600, 'value'] += shift
            body = repair.search_fluctuating_metrics(moved, {}, 'svc', SECOND)
            self.assertEqual(body.startswith('key,'), reported, shift)


class WorkerConditions(unittest.TestCase):
    def setUp(self):
        Telemetry.hits = []
        self.server = ThreadingHTTPServer(('127.0.0.1', 5000), Telemetry)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.area = tempfile.TemporaryDirectory(dir=HERE / 'runtime')
        for name in ('config', 'llm', 'coordinator', 'tools_gpt'):
            sys.modules.pop(name, None)
        os.environ.update(LLM_API_KEY='local-placeholder', LLM_MODEL='fixture', TOOL_SERVER_HOST='127.0.0.1',
                          LLM_API_URL='http://127.0.0.1:8000/v1/chat/completions',
                          TOOL_SERVER_PORT='5000', MAX_AGENT_PARALLEL='1', DATASET_TYPE='re2ob')

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.guard.session.close()
        self.area.cleanup()

    def install(self, logs, metric, phase='trace'):
        selection = {'query_window': {'start_second': SECOND, 'end_second': SECOND + 3}}
        self.guard = worker.Guard(self.area.name, selection, Tokenizer(), 16384, phase, time.monotonic() + 60,
                                  seed=20261027, sources={'logs': logs, 'metric': metric}, data_root=PILOT / 'input')
        self.coordinator, _, _ = worker.install_guards(self.guard, CODE)

    def events(self):
        return [json.loads(line) for line in (Path(self.area.name) / 'events.jsonl').read_text().splitlines()]

    def test_author_condition_asks_the_tool_server(self):
        self.install('author', 'author')
        self.assertEqual(self.coordinator._get('search_fluctuating_metrics', PARAMS), 'author-server-body\n')
        self.assertEqual(len(Telemetry.hits), 1)
        self.assertEqual(self.events()[0]['source'], 'author')

    def test_absent_sources_answer_without_the_tool_server(self):
        self.install('absent', 'absent')
        self.assertEqual(self.coordinator._get('search_logs', PARAMS), worker.ABSENT_RESPONSE['search_logs'])
        self.assertEqual(self.coordinator._get('search_fluctuating_metrics', PARAMS), repair.NO_ROWS)
        self.assertEqual(Telemetry.hits, [])
        self.assertEqual([e['source'] for e in self.events() if e['kind'] == 'tool_result'], ['absent', 'absent'])

    def test_repaired_metric_reads_the_trace_package_and_logs_stay_with_the_author(self):
        self.install('author', 'repaired')
        delivered = self.coordinator._get('search_fluctuating_metrics', PARAMS)
        expected = repair.search_fluctuating_metrics(pd.read_csv(PILOT / 'input/metric/all/metrics.csv', low_memory=False),
                                                     {}, PARAMS['service_name'], PARAMS['timestamp'])
        self.assertEqual(delivered, expected)
        self.assertEqual(Telemetry.hits, [])
        self.assertEqual(self.coordinator._get('search_logs', PARAMS), 'author-server-body\n')
        self.assertEqual(len(Telemetry.hits), 1)

    def test_out_of_window_queries_still_stop_under_every_condition(self):
        self.install('absent', 'absent')
        with self.assertRaises(worker.HarnessStop):
            self.coordinator._get('search_logs', {'service_name': 'cartservice', 'timestamp': str(SECOND + 600)})

    def test_protocol_phase_keeps_the_author_tools(self):
        self.install('absent', 'absent', phase='protocol')
        self.assertEqual(self.coordinator._get('search_logs', PARAMS), 'author-server-body\n')

    def test_the_run_seed_reaches_the_request(self):
        self.install('author', 'author')
        payload = {'model': 'fixture', 'messages': [{'role': 'user', 'content': 'x'}]}
        self.assertEqual(worker.adapt_payload(payload, 512, self.guard.seed)['seed'], 20261027)
        self.assertEqual(worker.adapt_payload(payload, 512)['seed'], worker.DEFAULT_SEED)


class RunMatrix(unittest.TestCase):
    traces = [{'dir': 'traces/' + t, 'trace_id': t, 'case': 'case-' + t, 'span_count': 3} for t in ('a', 'b')]

    def test_every_trace_runs_once_per_condition_and_seed_with_shared_seeds(self):
        runs = conditions.condition_runs(self.traces)
        self.assertEqual(len(runs), 2 * 3 * 3)
        self.assertEqual(len({r['run_id'] for r in runs}), len(runs))
        for name in conditions.CONDITIONS:
            self.assertEqual(sorted(r['seed'] for r in runs if r['condition'] == name), sorted(list(conditions.SEEDS) * 2))
        first_block = runs[:3]  # One (trace, seed) block holds all conditions before the next trace starts.
        self.assertEqual({r['trace_id'] for r in first_block}, {'a'})
        self.assertEqual([r['condition'] for r in first_block], list(conditions.CONDITIONS))

    def test_runtime_passes_each_runs_flags_and_keys_progress_by_run(self):
        area = tempfile.TemporaryDirectory(dir=HERE / 'runtime')
        self.addCleanup(area.cleanup)
        package, result = Path(area.name) / 'package', Path(area.name) / 'run'
        package.mkdir()
        result.mkdir()
        runs = conditions.condition_runs(self.traces[:1], seeds=(7,))
        (package / 'manifest.json').write_text(json.dumps({'traces': self.traces[:1], 'runs': runs}))
        seen = []
        progress = runtime.run_traces(package, result, 'bundle', lambda d, out, e: (seen.append(
            (d.name, out.name, runtime.worker_options(e))), out.mkdir(parents=True)), lambda: True)
        self.assertEqual(seen[1], ('a', 'a--metric--s7', ['--seed', '7', '--logs', 'author', '--metric', 'repaired']))
        self.assertEqual(sorted(progress['traces']), sorted(r['run_id'] for r in runs))

    def test_a_manifest_without_runs_keeps_one_author_run_per_trace(self):
        area = tempfile.TemporaryDirectory(dir=HERE / 'runtime')
        self.addCleanup(area.cleanup)
        (Path(area.name) / 'manifest.json').write_text(json.dumps({'traces': self.traces}))
        entries = runtime.run_entries(Path(area.name))
        self.assertEqual([e['run_id'] for e in entries], ['a', 'b'])
        self.assertEqual(runtime.worker_options(entries[0]), [])


if __name__ == '__main__':
    unittest.main()
