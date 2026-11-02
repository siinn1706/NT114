"""CPU tests for the telemetry-gap components (telemetry-gap.py), their wiring in smoke-worker.py, the run grid and
shards of add-condition-runs.py and kaggle-runtime.py, and the dev-set and window-KPI rules. No model is loaded."""
import ast
import copy
import importlib.util
import json
import os
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
SECOND = 1705690314
PARAMS = {'service_name': 'currencyservice', 'timestamp': str(SECOND) + '687'}


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gap = load('telemetry_gap_test', 'telemetry-gap.py')
worker = load('worker_gap_test', 'smoke-worker.py')
runtime = load('runtime_gap_test', 'kaggle-runtime.py')
conditions = load('conditions_gap_test', 'add-condition-runs.py')
devset = load('devset_gap_test', 'select-dev-set.py')
kpis = load('window_kpi_gap_test', 'build-window-kpi.py')
evidence = load('evidence_gap_test', 'analyze-evidence-loss.py')

SELF_STATE = (Path(CODE / 'coordinator.py').read_text(encoding='utf-8').split('IMPORTANT evidence ranking:')[0][-40:]
              + 'IMPORTANT evidence ranking:\n- ERROR/EXCEPTION logs → strong anomaly signal\n'
              + gap.SELF_STATE_ANCHOR + '\nUse the tools iteratively.')
FINAL = 'You are the ROOT AGENT producing the FINAL diagnosis.\n\nhint\n\nGoal: identify the root-cause service.\n\nRanking'
KPI = {'trace_id': 't', 'window_s': 300, 'services': {
    'cartservice': {'in_trace': True, 'traces': 40, 'server': {'p95': 1.234, 'median': 0.9, 'spans': 80},
                    'client': None},
    'currencyservice': {'in_trace': False, 'traces': 12, 'server': {'p95': 3.456, 'median': 1.2, 'spans': 30},
                        'client': {'p95': 5.0, 'median': 2.0, 'spans': 9}},
    'frontend': {'in_trace': True, 'traces': 50, 'server': {'p95': 9.0, 'median': 1.0, 'spans': 60}, 'client': None},
    'redis-cart': {'in_trace': False, 'traces': 3, 'server': None, 'client': None}}}


class Components(unittest.TestCase):
    def messages(self, tool_text=None):
        out = [{'role': 'system', 'content': 'sys'}, {'role': 'user', 'content': SELF_STATE}]
        if tool_text is not None:
            out += [{'role': 'assistant', 'content': '', 'tool_calls': []}, {'role': 'tool', 'content': tool_text}]
        return out

    def test_every_flag_off_returns_the_same_object(self):
        messages = self.messages()
        self.assertIs(gap.edit_messages(messages), messages)
        final = [{'role': 'user', 'content': FINAL}]
        self.assertIs(gap.edit_messages(final, gap_aware=True, trace_kpi=False), final)

    def test_m2_line_follows_the_latency_line_without_touching_the_input(self):
        messages = self.messages()
        before = copy.deepcopy(messages)
        edited = gap.edit_messages(messages, trace_kpi=True, kpi=KPI)
        self.assertEqual(messages, before)
        self.assertIn(gap.SELF_STATE_ANCHOR + gap.M2_LINE + '\nUse the tools', edited[1]['content'])
        self.assertNotIn(gap.M1_LINE, edited[1]['content'])

    def test_m1_line_only_once_a_tool_answered_unavailable(self):
        plain = self.messages('log_id,timestamp\n')
        self.assertIs(gap.edit_messages(plain, gap_aware=True), plain)
        edited = gap.edit_messages(self.messages(gap.unavailable('metric')), gap_aware=True)
        self.assertIn(gap.SELF_STATE_ANCHOR + gap.M1_LINE, edited[1]['content'])

    def test_missing_anchor_is_an_error_not_a_silent_skip(self):
        with self.assertRaises(ValueError):
            gap.edit_messages([{'role': 'user', 'content': 'IMPORTANT evidence ranking: changed'}], trace_kpi=True)

    def test_m3_table_sits_before_the_goal_line_in_name_order(self):
        edited = gap.edit_messages([{'role': 'user', 'content': FINAL}], trace_expand=True, kpi=KPI)[0]['content']
        head, tail = edited.split('\nGoal: identify the root-cause service.')
        self.assertTrue(head.startswith('You are the ROOT AGENT'))
        rows = head.split('incoming-call p95 ratio\n')[1].split('\nServices absent')[0].splitlines()
        self.assertEqual([r.split(' | ')[0] for r in rows], list(gap.TABLE_SERVICES))
        self.assertIn('cartservice | yes | 40 | 1.23 | n/a', rows)
        self.assertIn('currencyservice | no | 12 | 3.46 | 5.00', rows)
        self.assertIn('redis | no | 3 | n/a | n/a', rows)
        self.assertIn('adservice | no | 0 | n/a | n/a', rows)
        self.assertNotIn('frontend', head.split('\n\nWindow evidence')[1])
        self.assertTrue(head.endswith('Services absent from this trace can still be the root cause.\n'))
        self.assertTrue(tail.startswith('\n\nRanking'))

    def test_table_services_are_the_upstream_known_services_without_frontends(self):
        for node in ast.parse((CODE / 'config.py').read_text(encoding='utf-8')).body:
            if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == 'KNOWN_SERVICES' for t in node.targets):
                known = ast.literal_eval(node.value)['re2ob']
        self.assertEqual(gap.TABLE_SERVICES, tuple(sorted(set(known) - {'frontend', 'frontendservice'})))

    def test_kpi_answer_fields_and_no_rows(self):
        body = json.loads(gap.kpi_response(KPI, 'currencyservice'))
        self.assertEqual(body['source'], gap.M2_SOURCE)
        self.assertEqual(body['currencyservice.trace_latency_ratio_p95.server'],
                         {'baseline_ratio': 1.0, 'window_ratio': 3.46, 'spans': 30})
        self.assertEqual(body['currencyservice.trace_latency_ratio_median.incoming_calls']['window_ratio'], 2.0)
        self.assertEqual(len(body), 5)
        self.assertEqual(gap.kpi_response(KPI, 'redis'), gap.NO_ROWS)
        self.assertEqual(gap.kpi_response(KPI, 'paymentservice'), gap.NO_ROWS)
        self.assertEqual(gap.NO_ROWS, worker.metric_repair.NO_ROWS)

    def test_name_matching_is_the_scorers(self):
        names = ['cartservice', 'cartservice-0', 'cartservice-7d9f8b6c5-abcd1', 'redis', 'redis-cart', 'frontend',
                 'frontendservice', 'cart', 'checkoutservice', 'emailservice-1']
        for a in names:
            for b in names:
                self.assertEqual(gap.match(a, b), evidence.match(a, b), (a, b))


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


class Response:
    status_code = 200
    text = '{}'

    def json(self):
        return {'choices': [{'finish_reason': 'stop', 'message': {'content': 'done'}}]}


class WorkerWiring(unittest.TestCase):
    def setUp(self):
        Telemetry.hits = []
        self.server = ThreadingHTTPServer(('127.0.0.1', 5003), Telemetry)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.area = tempfile.TemporaryDirectory(dir=HERE / 'runtime')
        for name in ('config', 'llm', 'coordinator', 'tools_gpt'):
            sys.modules.pop(name, None)
        os.environ.update(LLM_API_KEY='local-placeholder', LLM_MODEL='fixture', TOOL_SERVER_HOST='127.0.0.1',
                          LLM_API_URL='http://127.0.0.1:8003/v1/chat/completions',
                          TOOL_SERVER_PORT='5003', MAX_AGENT_PARALLEL='1', DATASET_TYPE='re2ob')

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.guard.session.close()
        self.area.cleanup()
        os.environ.update(LLM_API_URL='http://127.0.0.1:8000/v1/chat/completions', TOOL_SERVER_PORT='5000')

    def install(self, metric, **components):
        selection = {'query_window': {'start_second': SECOND, 'end_second': SECOND + 3}}
        self.guard = worker.Guard(self.area.name, selection, Tokenizer(), 16384, 'trace', time.monotonic() + 60,
                                  sources={'logs': 'author', 'metric': metric}, data_root=PILOT / 'input',
                                  components=components, window_kpi=KPI)
        self.coordinator, _, _ = worker.install_guards(self.guard, CODE)

    def sent(self, messages):
        captured = []
        self.guard.session.post = lambda url, json, timeout: (captured.append(json), Response())[1]
        self.guard.post(os.environ['LLM_API_URL'], json={'model': 'fixture', 'messages': messages})
        return captured[0]['messages']

    def test_trace_kpi_answers_absent_metrics_and_logs_stay_with_the_author(self):
        self.install('absent', trace_kpi=True)
        self.assertEqual(self.coordinator._get('search_fluctuating_metrics', PARAMS),
                         gap.kpi_response(KPI, 'currencyservice'))
        self.assertEqual(self.coordinator._get('search_logs', PARAMS), 'author-server-body\n')
        self.assertEqual(len(Telemetry.hits), 1)

    def test_gap_aware_answers_unavailable_instead_of_the_empty_table(self):
        self.install('absent', gap_aware=True)
        self.assertEqual(self.coordinator._get('search_fluctuating_metrics', PARAMS), gap.unavailable('metric'))

    def test_off_keeps_the_author_no_row_bytes_and_the_request_unchanged(self):
        self.install('absent')
        self.assertEqual(self.coordinator._get('search_fluctuating_metrics', PARAMS),
                         worker.ABSENT_RESPONSE['search_fluctuating_metrics'])
        messages = [{'role': 'user', 'content': SELF_STATE}]
        self.assertEqual(self.sent(messages), messages)

    def test_requests_carry_the_edited_prompts(self):
        self.install('absent', trace_kpi=True, trace_expand=True)
        self.assertIn(gap.M2_LINE, self.sent([{'role': 'user', 'content': SELF_STATE}])[0]['content'])
        self.assertIn('Window evidence beyond this trace', self.sent([{'role': 'user', 'content': FINAL}])[0]['content'])

    def test_model_endpoint_follows_the_slot_port_and_stays_local(self):
        self.install('absent')
        with self.assertRaises(worker.HarnessStop):
            self.guard.post('http://127.0.0.1:8000/v1/chat/completions', json={'model': 'x', 'messages': []})


class GridAndShards(unittest.TestCase):
    traces = [{'dir': 'traces/' + t, 'trace_id': t, 'case': 'case-' + t, 'span_count': 3} for t in 'abc']
    queries = [{'trace_id': 'a', 'site': 'kaggle'}, {'trace_id': 'c', 'site': 'kaggle'},
               {'trace_id': 'b', 'site': 'modal'}]

    def test_grid_has_seven_conditions_per_query_in_prereg_order(self):
        runs = conditions.gap_runs(self.traces, self.queries)
        self.assertEqual(len(runs), 21)
        self.assertEqual([r['condition'] for r in runs[:7]],
                         ['base_nometric', 'base_nometric_s2', 'a_nometric', 'base_metric', 'a_metric',
                          'm2_nometric', 'm1m3_nometric'])
        self.assertEqual([r['trace_id'] for r in runs[::7]], ['a', 'c', 'b'])
        by = {r['condition']: r for r in runs[:7]}
        self.assertEqual(by['base_nometric_s2']['seed'], 20261027)
        self.assertEqual({r['seed'] for c, r in by.items() if c != 'base_nometric_s2'}, {20261026})
        self.assertEqual(runtime.worker_options(by['a_nometric']),
                         ['--seed', '20261026', '--logs', 'author', '--metric', 'absent', '--trace-kpi',
                          '--trace-expand'])
        self.assertEqual(runtime.worker_options(by['base_metric']),
                         ['--seed', '20261026', '--logs', 'author', '--metric', 'repaired'])
        self.assertEqual(runtime.worker_options(by['m1m3_nometric'])[-2:], ['--gap-aware', '--trace-expand'])
        self.assertTrue(all(r['metric'] == 'absent' for r in runs if r['trace_kpi']))

    def test_grid_keeps_the_s1_v3_limits(self):
        for path in sorted((HERE / 's1-v3').glob('*/manifest.json')):
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['harness_limits'], conditions.S1_LIMITS)

    def test_shards_split_a_site_and_cover_it_once(self):
        runs = conditions.gap_runs(self.traces, self.queries)
        kaggle = [r['run_id'] for r in runs if r['site'] == 'kaggle']
        halves = [runtime.shard_runs(runs, f'kaggle:{k}/2') for k in range(2)]
        self.assertEqual(sorted(r['run_id'] for h in halves for r in h), sorted(kaggle))
        self.assertEqual(halves[0][0]['run_id'], kaggle[0])
        with self.assertRaises(ValueError):
            runtime.shard_runs(runs, None)
        with self.assertRaises(ValueError):
            runtime.parse_shard('kaggle:2/2')
        self.assertEqual(runtime.shard_runs(self.traces, None), self.traces)

    def test_a_non_boolean_component_is_refused(self):
        with self.assertRaises(ValueError):
            runtime.worker_options({'run_id': 'x', 'trace_kpi': 'yes'})

    def test_shard_archives_have_their_own_names(self):
        self.assertEqual(runtime.shard_label(None), '')
        self.assertEqual(runtime.shard_label('modal:3/10'), '-modal-3-of-10')


class DevSetRule(unittest.TestCase):
    def rows(self):
        rows = []
        for service in ('checkoutservice', 'currencyservice', 'emailservice'):
            for n in range(12):
                case = f'{service}_cpu_{n}'
                rows += [{'case_id': case, 'role': 'train', 'trace_id': f'{case}-q{i}', 'gt': service,
                          'coverage': 'none' if (n % 2 and i == 0) else 'server'} for i in range(3)]
        return rows + [{'case_id': 'x_cpu_1', 'role': 'test', 'trace_id': 't', 'gt': 'x', 'coverage': 'none'}]

    def test_strata_sizes_exclusions_and_sites(self):
        picked = devset.select(self.rows(), {'checkoutservice_cpu_1'})
        self.assertEqual([q['stratum'] for q in picked], ['none'] * 12 + ['covered'] * 13)
        self.assertNotIn('checkoutservice_cpu_1', {q['case_id'] for q in picked})
        self.assertEqual(len({q['case_id'] for q in picked}), 25)
        self.assertTrue(all(q['coverage'] == 'none' for q in picked[:12]))
        self.assertTrue(all(q['coverage'] != 'none' for q in picked[12:]))
        covered = [q['gt'] for q in picked[12:]]
        self.assertLessEqual(max(covered.count(s) for s in set(covered)) - min(covered.count(s) for s in set(covered)), 1)
        sited = devset.assign_sites(picked, 5)
        self.assertEqual(sum(q['site'] == 'kaggle' for q in sited), 10)
        self.assertEqual(sum(q['site'] == 'kaggle' and q['stratum'] == 'none' for q in sited), 5)

    def test_frozen_dev_set_matches_the_prereg_list(self):
        frozen = json.loads((HERE / 'runtime/dev-set.json').read_text(encoding='utf-8'))
        preview = json.loads((HERE / 'runtime/dev-set-preview.json').read_text(encoding='utf-8'))
        self.assertEqual({q['trace_id'] for q in frozen['queries']}, {q['trace_id'] for q in preview['queries']})
        self.assertEqual(sorted(frozen['excluded_s1_cases']), sorted(devset.s1_cases()))
        self.assertEqual(len(frozen['excluded_s1_cases']), 8)


class WindowKpiRule(unittest.TestCase):
    def frame(self, rows):
        return pd.DataFrame(rows, columns=['timestamp', 'trace_id', 'cmdb_id', 'operation_name', 'duration'])

    def test_sides_ratios_traces_and_minimum_spans(self):
        call = 'hipstershop.CurrencyService/Convert'
        window = self.frame([(i, f'w{i}', 'currencyservice', call, 20) for i in range(5)]
                            + [(i, f'w{i}', 'checkoutservice', call, 40) for i in range(6)]
                            + [(9, 'w9', 'cartservice', 'hipstershop.CartService/GetCart', 5)])
        query = self.frame([(10, 'q', 'frontend', 'hipstershop.CartService/GetCart', 1)])
        baseline = {('currencyservice', call): 10.0, ('checkoutservice', call): 10.0}
        kpi = kpis.query_kpi(window, query, baseline, 300)['services']
        self.assertEqual(kpi['currencyservice']['server'], {'p95': 2.0, 'median': 2.0, 'spans': 5})
        self.assertEqual(kpi['currencyservice']['client'], {'p95': 4.0, 'median': 4.0, 'spans': 6})
        self.assertEqual(kpi['currencyservice']['traces'], 6)
        self.assertIsNone(kpi['cartservice']['server'])  # No baseline: dropped from ratios.
        self.assertTrue(kpi['cartservice']['in_trace'])
        self.assertFalse(kpi['currencyservice']['in_trace'])
        self.assertEqual(kpis.ranker_order({'services': kpi}), ['currencyservice'])

    def test_ranker_breaks_ties_by_name_and_skips_frontends(self):
        stats = {'p95': 2.0, 'median': 1.0, 'spans': 9}
        kpi = {'services': {'b': {'server': stats, 'client': None}, 'a': {'server': None, 'client': stats},
                            'frontendservice': {'server': dict(stats, p95=9.0), 'client': None},
                            'c': {'server': None, 'client': None}}}
        self.assertEqual(kpis.ranker_order(kpi), ['a', 'b'])

    def test_quantile_rule(self):
        self.assertEqual(kpis.quantile([1, 2, 3, 4], 0.5), 3.0)
        self.assertEqual(kpis.quantile(list(range(1, 21)), 0.95), 20.0)


if __name__ == '__main__':
    unittest.main()
