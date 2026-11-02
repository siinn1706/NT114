"""CPU tests for run-non-llm-baselines.py on synthetic data: the latency ranker's attribution variants, rank / R@1 / MRR,
train-only reading and window slicing, expansion of case results to queries, the summary groups, and the adapters to the
RCAEval layouts. Tests that need pandas (and RCAEval) are skipped with a message when the interpreter lacks them; run
with the rcaeval-env interpreter to run them all. No model and no raw RE2-OB file is read."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, filename):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run = load('run_non_llm_baselines_under_test', 'run-non-llm-baselines.py')

try:
    import pandas as pd
except ImportError:
    pd = None
try:
    from RCAEval.e2e import tracerca  # noqa: F401
    HAS_RCAEVAL = True
except ImportError:
    HAS_RCAEVAL = False


def span(service, operation, duration, timestamp=0, trace='t1', span_id='s', parent=''):
    return {'cmdb_id': service, 'operation_name': operation, 'duration': duration, 'timestamp': timestamp,
            'trace_id': trace, 'span_id': span_id, 'parent_span': parent, 'status_code': 0}


CART = 'hipstershop.CartService/GetCart'
BASELINE = {('cartservice', CART): {'p50': 100}, ('frontendservice', CART): {'p50': 100},
            ('currencyservice', 'hipstershop.CurrencyService/Convert'): {'p50': 100}}


class LatencyRanker(unittest.TestCase):
    def setUp(self):
        # the client span of the frontend (callee cart) is the slowest; the server span of the currency service next
        self.spans = [span('frontendservice', CART, 900), span('cartservice', CART, 120),
                      span('currencyservice', 'hipstershop.CurrencyService/Convert', 300)]

    def test_server_span_goes_to_its_cmdb_id(self):
        self.assertEqual(run.attributed_services(self.spans[1], 'callee'), ['cartservice'])
        self.assertEqual(run.attributed_services(self.spans[1], 'caller'), ['cartservice'])

    def test_client_span_variants(self):
        client = self.spans[0]
        self.assertEqual(run.attributed_services(client, 'callee'), ['cartservice'])
        self.assertEqual(run.attributed_services(client, 'caller'), ['frontendservice'])
        self.assertEqual(run.attributed_services(client, 'either'), ['cartservice', 'frontendservice'])

    def test_ranking_by_rule(self):
        self.assertEqual(run.latency_ranking(self.spans, BASELINE, 'callee'),
                         ['cartservice', 'currencyservice'])
        self.assertEqual(run.latency_ranking(self.spans, BASELINE, 'caller'),
                         ['frontendservice', 'currencyservice', 'cartservice'])
        self.assertEqual(run.latency_ranking(self.spans, BASELINE, 'either'),
                         ['cartservice', 'frontendservice', 'currencyservice'])

    def test_score_is_max_ratio_and_ties_break_by_name(self):
        spans = [span('cartservice', CART, 500), span('cartservice', CART, 200),
                 span('currencyservice', 'hipstershop.CurrencyService/Convert', 500)]
        self.assertEqual(run.latency_ranking(spans, BASELINE, 'either'), ['cartservice', 'currencyservice'])

    def test_spans_without_baseline_are_skipped(self):
        self.assertEqual(run.latency_ranking([span('adservice', 'hipstershop.AdService/GetAds', 9)], BASELINE,
                                             'either'), [])

    def test_fault_period_is_half_open(self):
        inject = 1000
        spans = [span('a', 'x', 1, timestamp=t * 1000) for t in (999, 1000, 1599, 1600)]
        self.assertEqual([s['timestamp'] // 1000 for s in run.fault_period_spans(spans, inject)], [1000, 1599])


class RankAndMrr(unittest.TestCase):
    def test_rank_and_scores(self):
        self.assertEqual(run.score_row('cartservice', ['cartservice', 'x']), (0, 'cartservice', 1, 1.0))
        self.assertEqual(run.score_row('cartservice', ['x', 'y', 'cartservice']), (2, 'x', 0, 1 / 3))
        self.assertEqual(run.score_row('cartservice', ['x']), (None, 'x', 0, 0.0))
        self.assertEqual(run.score_row('cartservice', []), (None, '', 0, 0.0))

    def test_instance_suffix_still_matches(self):
        self.assertEqual(run.rank_of_gt('cartservice', ['x', 'cartservice-7d9f8c6b5-abcde']), 1)

    def test_rcaeval_candidates_to_services(self):
        self.assertEqual(run.dedupe(run.rcaeval_service(c) for c in
                                    ['cartservice_GetCart', 'redis-db_cpu', 'cartservice_latency', 'redis_mem']),
                         ['cartservice', 'redis'])

    def test_aggregate_ignores_not_applicable_and_counts_errors(self):
        rows = [{'status': 'ok', 'R@1': 1, 'MRR': 1.0}, {'status': 'ok', 'R@1': 0, 'MRR': 0.5},
                {'status': 'not_applicable'}, {'status': 'error: boom'}]
        self.assertEqual(run.aggregate(rows), {'n': 2, 'R@1': 0.5, 'MRR': 0.75, 'not_applicable': 1, 'errors': 1})


class QueriesAndExpansion(unittest.TestCase):
    def test_only_train_queries_are_read(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'q.csv'
            path.write_text('case_id,role,trace_id\ncartservice_cpu_1,train,a\ncartservice_cpu_2,test,b\n'
                            'cartservice_cpu_3,val,c\ncartservice_cpu_1,train,d\n', encoding='utf-8')
            self.assertEqual(run.read_train_queries(path), [{'case': 'cartservice_cpu_1', 'trace_id': 'a'},
                                                            {'case': 'cartservice_cpu_1', 'trace_id': 'd'}])

    def test_gt_is_prefix_of_case_id(self):
        self.assertEqual(run.gt_of('productcatalogservice_cpu_1'), 'productcatalogservice')

    def test_roles_split_into_train_and_other_windows(self):
        cases = {'a_cpu_1': {'inject_ts': 5000, 'role': 'train'}, 'b_cpu_1': {'inject_ts': 9000, 'role': 'test'},
                 'c_cpu_1': {'inject_ts': 20000, 'role': 'val'}}
        train, other = run.windows_by_role(cases)
        self.assertEqual(train, [('a_cpu_1', 3800000, 5600000)])
        self.assertEqual(other, [(7800000, 9600000), (18800000, 20600000)])

    def test_expansion_copies_case_result_to_every_query(self):
        queries = [{'case': 'cartservice_cpu_1', 'trace_id': 'a'}, {'case': 'cartservice_cpu_1', 'trace_id': 'b'},
                   {'case': 'emailservice_cpu_1', 'trace_id': 'c'}]
        case_ranks = {'cartservice_cpu_1': {'tracerca': {'services': ['x', 'cartservice'], 'status': 'ok'},
                                            'baro': {'services': ['cartservice'], 'status': 'ok'}},
                      'emailservice_cpu_1': {'tracerca': {'services': [], 'status': 'error: boom'}}}
        rows = run.expand_to_queries(case_ranks, queries)
        by_key = {(r['method'], r['condition'], r['trace_id']): r for r in rows}
        self.assertEqual(len(rows), 10)  # two queries x two methods x two conditions + one query x one method x two
        self.assertEqual(by_key[('tracerca', 'full', 'a')]['rank'], 1)
        self.assertEqual(by_key[('tracerca', 'no_metric', 'b')]['MRR'], 0.5)
        self.assertEqual(by_key[('baro', 'full', 'a')]['R@1'], 1)
        self.assertEqual(by_key[('baro', 'no_metric', 'a')]['status'], 'not_applicable')
        self.assertNotIn('R@1', by_key[('baro', 'no_metric', 'a')])
        self.assertEqual(by_key[('tracerca', 'full', 'c')]['status'], 'error: boom')

    def test_summary_groups_by_gt_and_coverage(self):
        rows = [dict(method='m', condition='full', case='cartservice_cpu_1', trace_id='a', gt='cartservice',
                     status='ok', **{'R@1': 1, 'MRR': 1.0}),
                dict(method='m', condition='full', case='emailservice_cpu_1', trace_id='b', gt='emailservice',
                     status='ok', **{'R@1': 0, 'MRR': 0.0})]
        out = run.summarize(rows, {'a': True, 'b': False})['m']['full']
        self.assertEqual(out['overall']['R@1'], 0.5)
        self.assertEqual(out['by_gt_service']['cartservice']['R@1'], 1.0)
        self.assertEqual(out['by_coverage']['has_gt_span']['n'], 1)
        self.assertEqual(out['by_coverage']['no_gt_span']['R@1'], 0.0)

    def test_coverage_counts_server_and_client_spans(self):
        self.assertTrue(run.coverage_of([span('cartservice', CART, 1)], 'cartservice'))
        self.assertTrue(run.coverage_of([span('frontendservice', CART, 1)], 'cartservice'))
        self.assertFalse(run.coverage_of([span('currencyservice', 'hipstershop.CurrencyService/Convert', 1)],
                                         'cartservice'))


@unittest.skipIf(pd is None, 'pandas is not installed in this interpreter')
class SlicingAndAdapters(unittest.TestCase):
    def test_slice_drops_rows_of_val_and_test_windows(self):
        train = [('a_cpu_1', 0, 1000)]
        other = [(500, 2000)]
        chunk = pd.DataFrame({'timestamp': [100, 499, 500, 999, 1000, 1500], 'v': range(6)})
        part, dropped = run.slice_rows(chunk, 'timestamp', train, other)
        self.assertEqual(list(part['timestamp']), [100, 499])
        self.assertEqual(set(part['case_id']), {'a_cpu_1'})
        self.assertEqual(dropped['dropped_in_val_or_test_window'], 2)

    def test_slice_keeps_a_row_of_two_train_windows_for_both_cases(self):
        train = [('a_cpu_1', 0, 1000), ('b_cpu_1', 500, 1500)]
        part, _ = run.slice_rows(pd.DataFrame({'timestamp': [100, 700, 1200]}), 'timestamp', train, [])
        self.assertEqual(sorted(zip(part['case_id'], part['timestamp'])),
                         [('a_cpu_1', 100), ('a_cpu_1', 700), ('b_cpu_1', 700), ('b_cpu_1', 1200)])

    def test_slice_of_a_chunk_without_rows_is_empty(self):
        part, _ = run.slice_rows(pd.DataFrame({'timestamp': [5000]}), 'timestamp', [('a', 0, 10)], [])
        self.assertEqual(len(part), 0)

    def test_read_slices_end_to_end(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            rows = ['timestamp,cmdb_id,span_id,trace_id,duration,type,status_code,operation_name,parent_span']
            # case a injects at 2000 s: window [800 s, 2600 s); case t (test) injects at 5000 s: [3800 s, 5600 s)
            for ts, trace in ((900, 'q1'), (2500, 'x'), (2700, 'q2'), (4000, 'y'), (5000, 'q3')):
                rows.append(f'{ts * 1000},cartservice,{trace}s,{trace},50,rpc,0,hipstershop.CartService/GetCart,')
            (folder / 'spans.csv').write_text('\n'.join(rows) + '\n')
            (folder / 'metrics.csv').write_text('timestamp,node_id,service_name,kpi_name,value\n'
                                                '1000,,cartservice,cpu,1.0\n4000,,cartservice,cpu,2.0\n')
            cases = {'cartservice_cpu_1': {'inject_ts': 2000, 'role': 'train'},
                     'cartservice_cpu_9': {'inject_ts': 5000, 'role': 'test'}}
            spans, query_spans, metrics, counts = run.read_slices(folder / 'spans.csv', folder / 'metrics.csv', cases,
                                                                  {'q1', 'q2'})
            self.assertEqual(sorted(spans['trace_id']), ['q1', 'x'])
            self.assertEqual(set(spans['case_id']), {'cartservice_cpu_1'})
            self.assertEqual(sorted(query_spans['trace_id']), ['q1', 'q2'])
            self.assertEqual(list(metrics['timestamp']), [1000])
            self.assertEqual(counts['trace_rows_scanned'], 5)

    def test_traces_adapter_layout(self):
        frame = pd.DataFrame([span('cartservice', CART, 120, timestamp=1705353846065, span_id='s1', parent='p1')])
        out = run.to_rcaeval_traces(frame)
        self.assertEqual(out.loc[0, 'startTime'], 1705353846065000)
        self.assertEqual(out.loc[0, 'serviceName'], 'cartservice')
        self.assertTrue(pd.isna(out.loc[0, 'methodName']))
        self.assertEqual(out.loc[0, 'parentSpanID'], 'p1')

    def test_metrics_adapter_layout(self):
        long = pd.DataFrame({'timestamp': [1, 1, 1, 2, 2, 2], 'service_name': ['cartservice'] * 6,
                             'kpi_name': ['cpu', 'latency-50', 'latency-90'] * 2, 'value': [1.0, 9, 3, 2.0, 9, 4]})
        out = run.to_rcaeval_metrics(long)
        self.assertEqual(list(out.columns), ['time', 'cartservice_cpu', 'cartservice_latency'])
        self.assertEqual(list(out['cartservice_latency']), [3, 4])


@unittest.skipIf(pd is None or not HAS_RCAEVAL, 'pandas or RCAEval is not installed in this interpreter')
class RcaevalOnSyntheticCase(unittest.TestCase):
    def synthetic_case(self):
        """Normal spans before inject (ts < 1000 s); after it the cart operation is 50 times slower."""
        rows = []
        for i in range(60):
            ts = (900 + i) * 1000 if i < 40 else (1000 + i) * 1000
            slow = i >= 40
            rows.append(span('cartservice', CART, 5000 if slow else 100 + i % 3, ts, f't{i}', f'a{i}', f'f{i}'))
            rows.append(span('frontendservice', 'hipstershop.Frontend/Home', 200 + i % 4, ts, f't{i}', f'f{i}'))
        return pd.DataFrame(rows)

    def test_tracerca_and_microrank_rank_the_slow_service_first(self):
        frame = self.synthetic_case()
        for method in ('tracerca', 'microrank'):
            services = run.run_rcaeval(method, frame.copy(), None, 1000)
            self.assertEqual(services[0], 'cartservice', method)

    def test_baro_ranks_the_shifted_metric_first(self):
        rows = []
        for t in range(0, 40):
            after = t >= 20
            rows += [{'timestamp': t, 'service_name': 'cartservice', 'kpi_name': 'cpu',
                      'value': 90.0 + t % 3 if after else 1.0 + t % 3},
                     {'timestamp': t, 'service_name': 'adservice', 'kpi_name': 'cpu', 'value': 1.0 + t % 3}]
        services = run.run_rcaeval('baro', None, pd.DataFrame(rows), 20)
        self.assertEqual(services[0], 'cartservice')


if __name__ == '__main__':
    unittest.main()
