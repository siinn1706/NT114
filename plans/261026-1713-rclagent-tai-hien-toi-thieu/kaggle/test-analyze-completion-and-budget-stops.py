"""CPU tests for analyze-completion-and-budget-stops.py on small ZIPs built by the analyzer tests' fixture writer."""
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stops = load('budget_stops_under_test', 'analyze-completion-and-budget-stops.py')
fixtures = load('analyzer_fixtures', 'test-analyze-missing-source-results.py')
make_run, request, SEEDS = fixtures.make_run, fixtures.request, fixtures.SEEDS
CAP = "RuntimeError('trace failed: Per-span tool round budget exceeded (4); no further tool executed')"
BUDGET = "RuntimeError('trace failed: Model request budget exhausted (including retries)')"
EMPTY_LOGS = 'log_id,timestamp,cmdb_id,log_name,value\n'


def failed(reason):
    return {'status': 'failed', 'reason': reason, 'attempts': [{}]}


def call(number, span, operation, results, seed=SEEDS[0]):
    """A logical call: its request, a response with one tool call per result, then the results."""
    tool_calls = [{'function': {'name': name, 'arguments': json.dumps({'service_name': service, 'timestamp': '1'})}}
                  for name, service, _ in results]
    body = json.dumps({'choices': [{'message': {'tool_calls': tool_calls}}]})
    events = [dict(request(number, seed), span_id=span, operation=operation),
              {'kind': 'response', 'number': number, 'status': 200, 'body': body}]
    events += [{'kind': 'tool_result', 'name': name, 'params': {'service_name': service, 'timestamp': '1'},
                'response': response, 'source': 'author', 'span_id': span} for name, service, response in results]
    return events


def add_graphs(archive, run_ids, spans):
    graph = {'span_id': 's0', 'children': [{'span_id': f's{i}', 'children': []} for i in range(1, spans)]}
    with zipfile.ZipFile(archive, 'a') as zipped:
        for rid in run_ids:
            zipped.writestr(f'run/traces/{rid}/trace-graph.json', json.dumps(graph))
    archive.with_name(archive.name + '.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + '\n')


def analyze(out_dir, *triples):
    argv = sys.argv
    sys.argv = ['analyze-completion-and-budget-stops.py', str(out_dir), *map(str, triples)]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            stops.main()
    finally:
        sys.argv = argv


class CompletionAndPairs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        runs = fixtures.matrix(cases=('case_a',))
        self.rid = {(r['condition'], r['seed']): r['run_id'] for r in runs}
        states = {self.rid['no_metric', SEEDS[0]]: failed(CAP), self.rid['no_metric', SEEDS[1]]: failed(BUDGET)}
        scores = {self.rid['metric', SEEDS[2]]: 'R@1 : 0.0\nR@3 : 0.0\nMRR : 0.5\n',
                  self.rid['metric_no_log', SEEDS[0]]: 'Traceback (most recent call last):\n'}
        archive, manifest = fixtures.write_session(self.tmp.name, runs, states=states, scores=scores)
        add_graphs(archive, [r['run_id'] for r in runs], 3)
        self.out = Path(self.tmp.name) / 'out'
        analyze(self.out, 'A', archive, manifest)

    def test_completion_counts_causes_and_keeps_unscored_apart(self):
        with (self.out / 'completion.csv').open(encoding='utf-8') as handle:
            table = {(r['package'], r['condition']): r for r in csv.DictReader(handle)}
        no_metric = table['A', 'no_metric']
        self.assertEqual((no_metric['runs'], no_metric['valid_completions']), ('3', '1'))
        self.assertEqual((no_metric['failed_tool_round_cap'], no_metric['failed_request_budget']), ('1', '1'))
        self.assertAlmostEqual(float(no_metric['R@1_all_runs']), 1 / 3)
        self.assertEqual(float(no_metric['R@1_valid']), 1.0)
        no_log = table['A', 'metric_no_log']
        self.assertEqual((no_log['valid_completions'], no_log['unscored_passed']), ('2', '1'))
        self.assertEqual(no_log['failed_other'], '0')
        self.assertEqual(table['all', 'metric']['runs'], '3')

    def test_pairs_keep_only_both_valid_runs_and_average_cases_first(self):
        removed = json.loads((self.out / 'pairs.json').read_text())['metric_removed']['all']
        self.assertEqual((removed['matched_pairs'], removed['both_valid_pairs'], removed['cases']), (3, 1, 1))
        self.assertEqual(removed['pair_mean_delta_R@1'], 1.0)  # Seed 28: metric scored 0, no_metric 1.
        self.assertEqual(removed['case_mean_delta_MRR'], 0.5)

    def test_case_table_names_the_seeds_lost_to_caps(self):
        case = json.loads((self.out / 'cases.json').read_text())['metric_removed']['case_a']
        self.assertEqual(case['removed_failed'], {str(SEEDS[0]): 'tool_round_cap', str(SEEDS[1]): 'request_budget'})
        self.assertAlmostEqual(case['all_runs_delta_R@1'], (-1 - 1 + 1) / 3)
        self.assertEqual(case['both_valid_pairs'], 1)


class BudgetStops(unittest.TestCase):
    def test_round_kinds_and_request_budget_projection(self):
        run = make_run('case_a', 'no_metric', SEEDS[0])
        reference = make_run('case_a', 'metric', SEEDS[0])
        logs = 'log_id,timestamp,cmdb_id,log_name,value\n1,1,cart,log,error\n'
        events = (call(1, 's1', 'self_state_verification', [('search_logs', 'a', EMPTY_LOGS)])
                  + call(2, 's1', 'self_state_verification', [('search_logs', 'b', logs)])
                  + call(3, 's1', 'self_state_verification', [('search_logs', 'a', EMPTY_LOGS)])
                  + call(4, 's1', 'self_state_verification', [])
                  + [{'kind': 'agent_complete', 'operation': 'self_state_verification', 'span_id': 's1'}]
                  + call(5, 's0', 'consolidate', [])
                  + [{'kind': 'agent_complete', 'operation': 'consolidate', 'span_id': 's0'},
                     {'kind': 'fatal', 'reason': 'Model request budget exhausted (including retries)'}])
        with tempfile.TemporaryDirectory() as tmp:
            archive, manifest = fixtures.write_session(tmp, [run, reference], states={run['run_id']: failed(BUDGET)},
                                                       events={run['run_id']: events})
            add_graphs(archive, [run['run_id'], reference['run_id']], 4)
            analyze(Path(tmp) / 'out', 'A', archive, manifest)
            [stop] = json.loads((Path(tmp) / 'out/budget-stops.json').read_text())
        self.assertEqual(stop['cause'], 'request_budget')
        self.assertEqual([r['kind'] for r in stop['stop_conversation_rounds']], [])  # Stopped in a consolidation.
        self.assertEqual(stop['projected_requests_to_finish'], 5 + (4 - 1) + 1)
        self.assertEqual((stop['repeated_queries_in_run'], stop['distinct_results_with_rows']), (1, 1))
        self.assertEqual(stop['reference']['status'], 'passed')
        rounds = stops.classify_rounds(stops.timeline(events)[:4])
        self.assertEqual([r['kind'] for r in rounds], ['new_query_no_rows', 'new_rows', 'repeated_query'])


if __name__ == '__main__':
    unittest.main()
