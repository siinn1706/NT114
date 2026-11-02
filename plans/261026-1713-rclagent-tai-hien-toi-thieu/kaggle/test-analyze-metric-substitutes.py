"""CPU tests for analyze-metric-substitutes.py: span attribution, self time, every indicator on synthetic spans and
events, the set rule, the first-loss order, the join with the evidence-loss runs.csv, the train-only baseline, the
outcome sentences, the freeze receipt, and a hand count on one real S1 v2 run. No model and no Kaggle is run."""
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, filename):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ms = load('metric_substitutes_under_test', 'analyze-metric-substitutes.py')
GT = 'recommendationservice'


def span(sid, service, operation, duration, parent='', status='0', trace='t1'):
    return {'span_id': sid, 'cmdb_id': service, 'operation_name': operation, 'duration': str(duration),
            'parent_span': parent, 'status_code': status, 'trace_id': trace, 'type': 'rpc', 'timestamp': '0'}


# frontend root -> client call to RecommendationService -> its server span -> client call to ProductCatalogService
TRACE = [span('r', 'frontendservice', 'frontend', 1000),
         span('c1', 'frontendservice', 'hipstershop.RecommendationService/ListRecommendations', 900, 'r'),
         span('s1', GT, '/hipstershop.RecommendationService/ListRecommendations', 100, 'c1'),
         span('c2', GT, '/hipstershop.ProductCatalogService/ListProducts', 60, 's1'),
         span('s2', 'productcatalogservice', 'hipstershop.ProductCatalogService/ListProducts', 5, 'c2'),
         span('c3', 'frontendservice', 'hipstershop.CartService/GetCart', 50, 'r')]


def baseline_for(spans, p50=10, p99=1000, override=None):
    out = {(s['cmdb_id'], s['operation_name']): {'p50': p50, 'p99': p99, 'n': 100} for s in spans}
    out.update(override or {})
    return out


ROOT_SLOW = {('frontendservice', 'frontend'): {'p50': 1000, 'p99': 100000, 'n': 100}}


def verdict(sid, abnormal, hypothesis='because', symptoms=None):
    return {'kind': 'agent_complete', 'operation': ms.SELF_STATE, 'span_id': sid,
            'output': json.dumps({'span_id': sid, 'is_abnormal': abnormal, 'hypothesis': hypothesis,
                                  'key_symptoms': symptoms})}


def asked(sid):
    return {'kind': 'request', 'operation': ms.SELF_STATE, 'span_id': sid, 'number': '1'}


class AttributionTest(unittest.TestCase):
    def test_callee_parses_rpc_names(self):
        self.assertEqual(ms.callee('hipstershop.CartService/GetCart'), 'cartservice')
        self.assertEqual(ms.callee('/hipstershop.RecommendationService/ListRecommendations'), 'recommendationservice')
        self.assertEqual(ms.callee('grpc.hipstershop.CurrencyService/Convert'), 'currencyservice')
        self.assertIsNone(ms.callee('frontend'))

    def test_client_and_server(self):
        self.assertTrue(ms.is_client(TRACE[1]))
        self.assertFalse(ms.is_client(TRACE[2]))
        self.assertFalse(ms.is_client(TRACE[0]))

    def test_rules_split_on_a_client_span_of_the_faulty_service(self):
        call = span('x', 'checkoutservice', 'hipstershop.CartService/GetCart', 5)
        self.assertTrue(ms.attributed(call, 'checkoutservice', 'either'))
        self.assertTrue(ms.attributed(call, 'checkoutservice', 'caller'))
        self.assertFalse(ms.attributed(call, 'checkoutservice', 'callee'))
        self.assertTrue(ms.attributed(call, 'cartservice', 'callee'))
        self.assertFalse(ms.attributed(call, 'cartservice', 'caller'))

    def test_server_span_counts_under_every_rule(self):
        for rule in ms.RULES:
            self.assertTrue(ms.attributed(TRACE[2], GT, rule))
            self.assertFalse(ms.attributed(TRACE[0], GT, rule))

    def test_related(self):
        self.assertEqual([ms.related(s, GT) for s in TRACE], ['', 'client', 'server', 'server', '', ''])


class CaseSignalTest(unittest.TestCase):
    def test_self_time_subtracts_direct_children_and_floors_at_zero(self):
        spans = ms.with_self_time(TRACE + [span('k', 'x', 'y', 2000, 'c3')])
        self_time = {s['span_id']: s['self_time'] for s in spans}
        self.assertEqual(self_time['r'], 1000 - 900 - 50)
        self.assertEqual(self_time['c1'], 800)
        self.assertEqual(self_time['c3'], 0)

    def test_u0_trace_by_self_time(self):
        signals, _ = ms.case_signals(TRACE, {}, GT, {})
        self.assertEqual(signals['top_self_span'], 'frontendservice hipstershop.RecommendationService/ListRecommendations')
        self.assertTrue(signals['U0_trace_either'])
        self.assertTrue(signals['U0_trace_callee'])
        self.assertFalse(signals['U0_trace_caller'])
        self.assertFalse(signals['U0_baseline_either'])

    def test_u0_baseline_needs_top_ratio_and_p99(self):
        base = baseline_for(TRACE, p50=10, p99=500, override=ROOT_SLOW)
        signals, _ = ms.case_signals(TRACE, {}, GT, base)
        self.assertEqual(signals['top_ratio'], 90.0)
        self.assertTrue(signals['U0_baseline_either'])
        self.assertTrue(signals['U0_baseline_callee'])
        self.assertFalse(signals['U0_baseline_caller'])
        base = baseline_for(TRACE, p50=10, p99=5000, override=ROOT_SLOW)
        signals, _ = ms.case_signals(TRACE, {}, GT, base)
        self.assertFalse(signals['top_ratio_above_p99'])
        self.assertFalse(signals['U0_baseline_either'])

    def test_u0_false_when_the_slowest_span_is_elsewhere(self):
        spans = [dict(s) for s in TRACE]
        spans[5]['duration'] = '99999'
        signals, _ = ms.case_signals(spans, {}, GT, baseline_for(spans, p99=10))
        self.assertFalse(signals['U0_either'])
        self.assertEqual(signals['top_ratio_span'], 'frontendservice hipstershop.CartService/GetCart')

    def test_spans_without_baseline_are_counted_not_ranked(self):
        base = baseline_for(TRACE[:2])
        signals, _ = ms.case_signals(TRACE, {}, GT, base)
        self.assertEqual(signals['spans_without_baseline'], 4)

    def test_status_and_logs(self):
        spans = [dict(s) for s in TRACE]
        signals, _ = ms.case_signals(spans, {'cartservice': 3}, GT, {})
        self.assertFalse(signals['U0_status'])
        self.assertFalse(signals['U0_logs'])
        spans[1]['status_code'] = '2'
        signals, _ = ms.case_signals(spans, {GT: 1}, GT, {})
        self.assertTrue(signals['U0_status'])
        self.assertTrue(signals['U0_logs'])
        self.assertEqual(signals['gt_log_lines'], 1)

    def test_struct_max_and_tie(self):
        signals, _ = ms.case_signals(TRACE, {}, GT, {})
        self.assertEqual(signals['struct_max'], GT)
        self.assertTrue(signals['U_struct'])
        tied = TRACE + [span('p', 'productcatalogservice', 'hipstershop.ProductCatalogService/GetProduct', 1)]
        signals, _ = ms.case_signals(tied, {}, GT, {})
        self.assertEqual(signals['struct_max'], 'tie')
        self.assertFalse(signals['U_struct'])


class RunSignalTest(unittest.TestCase):
    def spans(self):
        return ms.with_self_time(TRACE)

    def test_u1_needs_every_server_span(self):
        problems = []
        out = ms.run_signals([asked('s1'), asked('c2')], self.spans(), GT, problems)
        self.assertTrue(out['U1'])
        out = ms.run_signals([asked('s1')], self.spans(), GT, problems)
        self.assertFalse(out['U1'])
        self.assertEqual(out['gt_server_spans_asked'], 1)

    def test_u1_na_without_a_server_span(self):
        out = ms.run_signals([], self.spans(), 'emailservice', [])
        self.assertIsNone(out['U1'])

    def test_u2_on_client_span_and_latency_words(self):
        out = ms.run_signals([verdict('c1', True, 'High latency on the call')], self.spans(), GT, [])
        self.assertTrue(out['U2'])
        self.assertTrue(out['U2_latency'])
        out = ms.run_signals([verdict('c1', True, 'errors seen')], self.spans(), GT, [])
        self.assertTrue(out['U2'])
        self.assertFalse(out['U2_latency'])

    def test_u2_false_when_only_unrelated_spans_or_normal(self):
        events = [verdict('s1', False, 'duration high but normal'), verdict('c3', True, 'slow')]
        out = ms.run_signals(events, self.spans(), GT, [])
        self.assertFalse(out['U2'])
        self.assertFalse(out['U2_latency'])

    def test_unparseable_output_is_a_problem(self):
        problems = []
        ms.run_signals([{'kind': 'agent_complete', 'operation': ms.SELF_STATE, 'span_id': 's1', 'output': '{'}],
                       self.spans(), GT, problems)
        self.assertEqual(len(problems), 1)


class RuleTest(unittest.TestCase):
    def row(self, **values):
        base = {'U0': True, 'U0_either': True, 'U1': True, 'U2': True, 'U3': True, 'U4': True}
        base.update(values)
        return base

    def test_first_loss_order(self):
        self.assertEqual(ms.first_loss(self.row()), 'preserved')
        self.assertEqual(ms.first_loss(self.row(U2=False, U4=False)), 'U2')
        self.assertEqual(ms.first_loss(self.row(U0=False, U1=False)), 'U0')
        self.assertEqual(ms.first_loss(self.row(U3=None)), 'U3_NA')
        self.assertEqual(ms.first_loss(self.row(U0_either=False), 'U0_either'), 'U0')

    def test_sets(self):
        hit, miss = {'R@1': 1.0, 'MRR': 1.0}, {'R@1': 0.0, 'MRR': 0.5}
        self.assertEqual(ms.assign_set(hit, miss, 2), 'D')
        self.assertEqual(ms.assign_set(miss, hit, 2), 'K')
        self.assertEqual(ms.assign_set(hit, hit, 0), 'excluded')
        self.assertEqual(ms.assign_set({'R@1': 0.0, 'MRR': 0.5}, {'R@1': 0.0, 'MRR': 0.3}, 1), 'R')
        self.assertEqual(ms.assign_set({'R@1': 0.0, 'MRR': 0.5}, {'R@1': 0.0, 'MRR': 0.31}, 1), '')

    def test_join_reads_flags_and_rank(self):
        rows = {'a': {'run_id': 'a', 'I2': 'false', 'I3': 'true', 'rank': '0', 'gt_service': GT, 'integrity': 'ok'},
                'b': {'run_id': 'b', 'I2': 'NA', 'I3': 'false', 'rank': '', 'gt_service': GT, 'integrity': 'ok'}}
        joined = ms.join_evidence({'run_id': 'a'}, rows, [])
        self.assertEqual((joined['U3'], joined['U4']), (True, True))
        joined = ms.join_evidence({'run_id': 'b'}, rows, [])
        self.assertEqual((joined['U3'], joined['U4']), (None, None))

    def test_join_missing_run_is_an_error(self):
        with self.assertRaises(SystemExit):
            ms.join_evidence({'run_id': 'zzz'}, {}, [])

    def test_outcomes(self):
        def pair(case, seed, set_, **values):
            row = {'case': case, 'seed': seed, 'set': set_, 'U0_either': False, 'U0_callee': False,
                   'U0_caller': False, 'U1': True, 'U2': False, 'U3': False, 'U4': False, 'U_struct': False,
                   'top1_is_struct_max': False, 'hit_without_substitute': False}
            row.update(values)
            return row
        pairs = [pair('aaa', 1, 'D', U0_either=True, U0_callee=True), pair('aaa', 2, 'D', U0_either=True,
                                                                             U0_callee=True),
                 pair('bbb', 1, 'D', U0_either=True), pair('99f095', 1, 'D'),
                 pair('ccc', 1, 'K', U4=True, U_struct=True, top1_is_struct_max=True, hit_without_substitute=True),
                 pair('ddd', 1, 'R')]
        out = ms.outcomes(pairs)
        self.assertEqual(out['main']['O1_cases_same_first_loss'], 3)
        self.assertEqual(out['main']['O1_by_indicator'], {'U0': 1, 'U2': 2})
        self.assertEqual(out['main']['O2_cases_with_U0'], 2)
        self.assertFalse(out['main']['O2_no_substitute'])
        self.assertEqual(out['sensitivity']['callee']['O2_cases_with_U0'], 1)
        self.assertEqual(out['sensitivity']['without_99f095']['O1_by_indicator'], {'U2': 2})
        self.assertEqual(out['O3'], {'K_runs': 1, 'hit_without_substitute': 1, 'with_U_struct_and_top1_struct_max': 1})
        self.assertEqual(out['O4'], {'ddd s1': 'U0'})
        self.assertEqual(out['x_rank_1'], 'U2')


class BaselineTest(unittest.TestCase):
    def test_train_only_single_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'roles.csv').write_text('case_id,inject_ts,role\na,2000,train\nb,4000,test\nc,5000,train\n',
                                           encoding='utf-8')
            # windows in ms: a [800000, 1940000), b [2800000, 3940000), c [3800000, 4940000)
            rows = ['timestamp,cmdb_id,span_id,trace_id,duration,type,status_code,operation_name,parent_span']
            data = [(850000, 10), (860000, 20), (870000, 30),  # a only, train
                    (3000000, 777),                            # b only, test -> dropped
                    (3900000, 999),                            # b and c overlap -> dropped
                    (2000000, 555),                            # no window -> ignored
                    (4000000, 40)]                             # c only, train
            rows += [f'{ts},svc,x,t,{d},rpc,0,op,' for ts, d in data]
            rows += ['850000,other,x,t,5,rpc,0,op,']
            (tmp / 'raw.csv').write_text('\n'.join(rows) + '\n', encoding='utf-8')
            out, counts = ms.build_baseline(tmp / 'raw.csv', tmp / 'roles.csv', {('svc', 'op')}, chunksize=3)
        self.assertEqual(out, [{'cmdb_id': 'svc', 'operation_name': 'op', 'n': 4, 'p50': 30, 'p99': 40}])
        self.assertEqual(counts['dropped_nontrain'], 1)
        self.assertEqual(counts['dropped_several_windows'], 1)

    def test_quantile(self):
        self.assertEqual(ms.quantile(list(range(100)), 0.5), 50)
        self.assertEqual(ms.quantile(list(range(100)), 0.99), 99)
        self.assertEqual(ms.quantile([7], 0.99), 7)


class CommandLineTest(unittest.TestCase):
    def test_needs_evidence_runs(self):
        with self.assertRaises(SystemExit):
            ms.parse_args(['out', 'a', 'z', 'm'])
        args = ms.parse_args(['out', '--evidence-runs', 'e.csv', 'a', 'z', 'm', '--label', 'x'])
        self.assertEqual(args['groups'], [('a', 'z', 'm')])
        self.assertEqual(args['label'], 'x')

    def test_refuses_existing_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'summary.json').write_text('{}', encoding='utf-8')
            with self.assertRaises(SystemExit) as raised:
                ms.main([tmp, '--evidence-runs', 'e.csv', 'a', 'z', 'm'])
            self.assertIn('already holds', str(raised.exception))


class FreezeReceiptTest(unittest.TestCase):
    def test_receipt_matches_codebook(self):
        report = ms.prereg_report()
        self.assertTrue(report['frozen'])
        self.assertTrue(report['codebook_sha_matches'])

    def test_receipt_detects_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'cb.md').write_text('a\r\nb\n', encoding='utf-8', newline='')
            (tmp / 'r.json').write_text(json.dumps({'codebook_path': 'cb.md',
                                                    'codebook_sha256': ms.sha256_lf(tmp / 'cb.md')}), encoding='utf-8')
            self.assertTrue(ms.prereg_report(tmp / 'r.json', tmp)['codebook_sha_matches'])
            (tmp / 'cb.md').write_text('a\nb\n', encoding='utf-8', newline='')
            self.assertTrue(ms.prereg_report(tmp / 'r.json', tmp)['codebook_sha_matches'])
            (tmp / 'cb.md').write_text('a\nc\n', encoding='utf-8')
            self.assertFalse(ms.prereg_report(tmp / 'r.json', tmp)['codebook_sha_matches'])

    def test_rq_b_receipt_still_matches(self):
        self.assertEqual(ms.evidence.prereg_report(), {'frozen': True, 'codebook_sha_matches': True,
                                                       'analyzer_sha_matches': True, 'imports_sha_match': True})


REAL_ZIP = HERE / 'runtime/kaggle-output-b-s1-v2/rclagent-smoke/rclagent-smoke-results.zip'
REAL_BUNDLE = HERE / 's1-v2/b/rclagent-kaggle-bundle.zip'
REAL_TRACE = '7bbfa6060d6e01eed1ac0ec2ceead992'


@unittest.skipUnless(REAL_ZIP.exists() and REAL_BUNDLE.exists(), 'S1 v2 package b not present')
class RealRunHandCountTest(unittest.TestCase):
    """Hand count on 7bbfa6 no_metric s26 (phase 1 scout): 2 server spans of recommendationservice, both asked; one client
    span from the frontend; none judged abnormal; the slowest span by self time is the frontend call to it."""

    def test_hand_count(self):
        with zipfile.ZipFile(REAL_BUNDLE) as bundle:
            spans, logs = ms.read_bundle_case(bundle, REAL_TRACE)
        signals, spans = ms.case_signals(spans, logs, GT, {})
        self.assertEqual((signals['spans'], signals['gt_server_spans'], signals['gt_client_spans']), (23, 2, 1))
        self.assertEqual((signals['status_nonzero'], signals['gt_log_lines']), (0, 0))
        self.assertEqual(signals['struct_max'], 'productcatalogservice')
        self.assertTrue(signals['U0_trace_either'])
        rid = f'{REAL_TRACE}--no_metric--s20261026'
        with zipfile.ZipFile(REAL_ZIP) as zipped:
            names = set(zipped.namelist())
            problems = []
            events = ms.read_events(zipped, names, rid, problems)
            top1 = ms.top1_of(zipped, names, rid)
        out = ms.run_signals(events, spans, GT, problems)
        self.assertEqual(problems, [])
        self.assertEqual((out['gt_server_spans_asked'], out['U1']), (2, True))
        self.assertEqual((out['gt_related_spans_judged'], out['gt_related_spans_abnormal'], out['U2']), (3, 0, False))
        self.assertEqual(top1, 'cartservice')


if __name__ == '__main__':
    unittest.main()
