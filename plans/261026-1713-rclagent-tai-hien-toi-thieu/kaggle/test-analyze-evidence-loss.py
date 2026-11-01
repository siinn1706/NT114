"""CPU tests for analyze-evidence-loss.py: the scorer's name matching, every indicator and label on synthetic runs that
have the event shapes of the real logs, right-censoring, the join of tool results with tool calls, the command line,
determinism, the freeze receipt, and a gate on the real S1 v2 results ZIPs. No model and no Kaggle is run."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
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


ev = load('evidence_loss_under_test', 'analyze-evidence-loss.py')
fixtures = load('analyzer_fixtures_for_evidence_loss', 'test-analyze-missing-source-results.py')
METRIC, LOGS = 'search_fluctuating_metrics', 'search_logs'
GT = 'checkoutservice'
SEED = 20261026
TS = '1705738345756'
SYSTEM = {'role': 'system', 'content': 'You are a root cause localization agent.'}
EMPTY_LOG = 'log_id,timestamp,cmdb_id,log_name,value\n'
NO_KPI = '{"message":"No fluctuating metrics found."}\n'
NO_ROWS = '{"message":"No matching records found."}\n'
FALLBACK = 'Based on all retrieved evidence above, produce a final\nJSON conclusion for this span (no markdown):'
# root -> productcatalogservice -> checkoutservice, and a sibling cartservice
TREE = ('r', 'frontendservice', [('a', 'productcatalogservice', [('c', 'checkoutservice', [])]),
                                 ('b', 'cartservice', [])])
TREE_WITHOUT_GT = ('r', 'frontendservice', [('a', 'productcatalogservice', []), ('b', 'cartservice', [])])


def table(*services):
    return 'key,regular_mean,current_mean\n' + ''.join(f'{s}.cpu,0.4,9.0\n' for s in services)


def output(span, service, abnormal=False, errors=False, metric=False, compact=False):
    values = {'span_id': span, 'service_name': service, 'is_abnormal': abnormal, 'has_error_logs': errors,
              'has_metric_anomaly': metric, 'key_symptoms': None, 'hypothesis': 'because'}
    return json.dumps(values, separators=(',', ':')) if compact else json.dumps(values, indent=2)


def metric_call(service, response, source='repaired'):
    return (METRIC, service, response, source)


def log_call(service, response=EMPTY_LOG, source='author', delivered=None):
    return (LOGS, service, response, source, delivered)


def walk(tree, parent=None):
    span, service, children = tree
    yield span, service, parent
    for child in children:
        yield from walk(child, span)


def graph_of(tree, parent=None):
    span, service, children = tree
    return {'span_id': span, 'raw': {'cmdb_id': service, 'parent_span': parent, 'span_id': span,
                                     'timestamp': int(TS) - 1000},
            'children': [graph_of(child, span) for child in children]}


def request_event(number, span, operation, attempt=0, retry_of=None, messages=None):
    return {'kind': 'request', 'number': number, 'phase': 'trace', 'span_id': span, 'operation': operation,
            'attempt': attempt, 'retry_of': retry_of,
            'payload': {'seed': SEED, 'messages': messages or [SYSTEM, {'role': 'user', 'content': 'go'}]}}


def response_event(number, calls=(), content=None):
    message = {'content': content, 'tool_calls': [
        {'id': f'call-{i}', 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(params)}}
        for i, (name, params) in enumerate(calls)]}
    return {'kind': 'response', 'number': number, 'status': 200, 'body': json.dumps({'choices': [{'message': message}]})}


def author_hint(nodes):
    """The author's hint text, written out again here with sorted names so that the text is stable."""
    errors, metrics = [], []
    for service, evidence in nodes:
        if 'has_error_logs' in evidence and '"has_error_logs": true' in evidence.lower():
            errors.append(service)
        elif '"is_abnormal": true' in evidence.lower():
            metrics.append(service)
    hint = ''
    if errors:
        hint = f"\n⚠️ Services with ERROR LOGS (strongest evidence): {', '.join(sorted(set(errors)))}"
    if metrics:
        hint += f"\n⚡ Services with metric anomalies only: {', '.join(sorted(set(metrics)))}"
    return hint


def span_events(number, span, service, spec, sources):
    calls = spec.get('calls') or [metric_call(service, NO_KPI, sources[0]), log_call(service, source=sources[1])]
    events, n = [request_event(number, span, 'self_state_verification')], number
    for k in range(spec.get('retries', 0)):
        events.append({'kind': 'malformed_tool_call_retry', 'number': n, 'next_attempt': k + 1, 'next_seed': k,
                       'reason': 'text outside tool_calls'})
        n += 1
        events.append(request_event(n, span, 'self_state_verification', attempt=k + 1, retry_of=number))
    events.append(response_event(n, [(c[0], {'service_name': c[1], 'timestamp': TS}) for c in calls]))
    tool_messages = []
    for call in calls:
        name, svc, response, source = call[:4]
        params = {'service_name': svc, 'timestamp': TS}
        events.append({'kind': 'tool_result', 'name': name, 'params': params, 'response': response, 'source': source,
                       'span_id': span})
        tool_messages.append({'role': 'tool', 'tool_call_id': 'x', 'content': response})
        if name == LOGS:
            delivered = call[4] if len(call) > 4 else None
            events.append({'kind': 'tool_result_budget', 'name': name, 'params': params, 'delivered': delivered,
                           'span_id': span, 'budget_tokens': 2048, 'original_bytes': len(response),
                           'original_sha256': '0', 'applied': delivered is not None})
    n += 1
    text = spec.get('output') or output(span, service, spec.get('abn', False), spec.get('err', False),
                                        spec.get('met', False), spec.get('compact', False))
    last = tool_messages + ([{'role': 'user', 'content': FALLBACK}] if spec.get('fallback') else [])
    events.append(request_event(n, span, 'self_state_verification',
                                messages=[SYSTEM, {'role': 'user', 'content': 'go'}] + last))
    events.append(response_event(n, (), content=text))
    events.append({'kind': 'agent_complete', 'operation': 'self_state_verification', 'span_id': span, 'output': text})
    return events, n + 1, text


def consolidation_text(span, service, value):
    if isinstance(value, tuple) and value[0] == 'raw':
        return value[1]
    reason = value[2] if isinstance(value, tuple) else 'because'
    label = value[1] if isinstance(value, tuple) else value
    return json.dumps({'span_id': span, 'service_name': service, 'local_root_cause': label,
                       'has_error_logs': False, 'reason': reason, 'confidence': 0.5}, indent=2)


def build_run(tree=TREE, selfs=None, cons=None, final=(GT, 'adservice'), gt=GT, condition='metric', case='case_a',
              seed=SEED, stop='', hint=None, score=None, extra=()):
    """A run record shaped as read_run() builds it. selfs maps a span to its self-state spec (abn, err, met, calls,
    output, fallback, retries, compact); cons maps a span to its consolidation (default: its own service; False: none);
    final is the ranking (None: the run stopped before the final answer)."""
    selfs, cons = selfs or {}, {} if cons is None else cons
    sources = (('absent' if condition == 'no_metric' else 'repaired'), ('absent' if condition == 'metric_no_log'
                                                                       else 'author'))
    spans = list(walk(tree))
    events, number, nodes = [], 1, []
    for span, service, _ in spans:
        new, number, text = span_events(number, span, service, selfs.get(span, {}), sources)
        events += new
        nodes.append((service, text))
    if cons is not False:
        for span, service, _ in reversed(spans):
            text = consolidation_text(span, service, cons.get(span, service.lower()))
            events += [request_event(number, span, 'consolidate'), response_event(number, (), content=text),
                       {'kind': 'agent_complete', 'operation': 'consolidate', 'span_id': span, 'output': text}]
            number += 1
    events += list(extra)
    if final is not None:
        graph = [{'span_id': s, 'service_name': svc, 'evidence': t} for (s, svc, _), (_, t) in zip(spans, nodes)]
        prompt = (f'You are the ROOT AGENT.\n\nGlobal Evidence Graph ({len(graph)} span evidences collected):\n'
                  f'{json.dumps(graph, ensure_ascii=False, indent=2)}\n'
                  f'{author_hint(nodes) if hint is None else hint}\n\nGoal: identify the root-cause service.')
        events += [request_event(number, None, None, messages=[SYSTEM, {'role': 'user', 'content': prompt}]),
                   response_event(number, [('print_results', {'root_causes': list(final)})])]
    status = 'passed' if final is not None and not stop else 'failed'
    made = fixtures.make_run(case, condition, seed)
    return {'run_id': made['run_id'], 'case': 'checkoutservice_cpu_1', 'trace_id': made['trace_id'], 'condition': condition,
            'seed': seed, 'package': 'A', 'events': events, 'problems': [], 'gt': gt, '_case': case,
            'progress': {'status': status, 'reason': f"RuntimeError('trace failed: {stop}')" if stop else ''},
            'graph': graph_of(tree), 'result': {'root_causes': list(final)} if final is not None else None,
            'worker': {'status': status, 'fatal': stop or None, 'error': None}, 'author_score': score}


SCORED = 'R@1  : 1.0000  (1/1)\n  MRR  : 1.0000\n'
CARRIER = {'c': {'abn': True, 'met': True, 'calls': [metric_call(GT, table(GT)), log_call(GT)]}}


def analyze(run):
    spans, row, _, unseen = ev.analyze_run(run)
    return row, {s['span_id']: s for s in spans}, unseen


def final_request_count(events):
    """Final-synthesis requests of a log, retries left out."""
    return sum(e.get('kind') == 'request' and e.get('phase') == 'trace' and e.get('operation') is None
               and not (e.get('attempt') or 0) for e in events)


def write_package(root, runs, reverse=False):
    """A results ZIP with its checksum, bundle sidecar and manifest, as the analyzer's loader expects them."""
    root = Path(root)
    bundle = root / 'bundle'
    bundle.mkdir(parents=True, exist_ok=True)
    manifest = bundle / 'manifest.json'
    manifest.write_text(json.dumps({'runs': [fixtures.make_run(r['_case'], r['condition'], r['seed']) for r in runs]}))
    (bundle / 'rclagent-kaggle-bundle.zip.sha256').write_text(f'{fixtures.BUNDLE}  rclagent-kaggle-bundle.zip\n')
    entries, progress = [], {}
    for run in runs:
        rid = run['run_id']
        progress[rid] = dict(run['progress'], case=run['case'], attempts=[{}])
        entries.append((f'run/traces/{rid}/events.jsonl', '\n'.join(json.dumps(e) for e in run['events']) + '\n'))
        entries.append((f'run/traces/{rid}/trace-graph.json', json.dumps(run['graph'])))
        entries.append((f'run/traces/{rid}/worker-status.json', json.dumps(run['worker'])))
        if run['result'] is not None:
            entries.append((f'run/traces/{rid}/result.json', json.dumps(run['result'])))
        if run['progress']['status'] == 'passed':
            entries.append((f'run/scoring/{rid}/groundtruth.csv',
                            'timestamp,level,cmdb_id,failure_type\r\n1705738059,service,' + run['gt'] + ',cpu\r\n'))
            entries.append((f'run/scoring/{rid}/author-score.txt', run['author_score'] or SCORED))
    archive = root / 'out' / 'rclagent-smoke-results.zip'
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr('run/progress.json', json.dumps({'bundle_sha256': fixtures.BUNDLE, 'traces': progress}))
        for path, text in (reversed(entries) if reverse else entries):
            zipped.writestr(path, text)
    archive.with_name(archive.name + '.sha256').write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name + '\n')
    return archive, manifest


def run_main(*argv):
    with contextlib.redirect_stdout(io.StringIO()) as out:
        ev.main([str(a) for a in argv])
    return out.getvalue()


class NameMatchTest(unittest.TestCase):
    def test_scorer_table(self):
        cases = [('cartservice', ['cartservice-0'], 0), ('cartservice-0', ['cartservice'], 0),
                 ('frontendservice', ['frontend'], -1), ('frontend', ['frontendservice'], -1),
                 ('currencyservice', ['currencyservice-2'], 0), ('emailservice', ['email'], -1),
                 ('emailservice', ['emailservice2'], -1), ('checkoutservice', ['checkout-service'], -1),
                 ('checkoutservice', ['adservice', 'checkoutservice'], 1),
                 ('checkoutservice', ['checkoutservice-0', 'checkoutservice'], 0),
                 ('currencyservice', ['adservice', 'paymentservice', 'currencyservice-1'], 2),
                 ('recommendationservice', ['unknown', 'none', ''], -1)]
        for label, candidates, rank in cases:
            self.assertEqual(ev.label_hit(label, candidates), rank, (label, candidates))
            self.assertEqual(ev.rank_of(label, candidates), rank)

    def test_match_and_pods(self):
        self.assertTrue(ev.match('cartservice', 'cartservice-0'))
        self.assertTrue(ev.match('cartservice-0', 'cartservice'))
        self.assertFalse(ev.match('frontend', 'frontendservice'))
        self.assertTrue(ev.in_list('checkoutservice', ['adservice', 'checkoutservice-0']))
        self.assertEqual(ev.base_of('ts-contacts-service-866bd68c97-xcqfx'), 'ts-contacts-service')
        self.assertEqual(ev.base_of('checkoutservice-0'), 'checkoutservice')
        self.assertTrue(ev.match('checkout', 'checkout-svc'))  # prefix followed by a dash
        self.assertFalse(ev.match('checkout', 'checkoutservice'))
        self.assertEqual(ev.label_hit('checkout-svc', ['checkout']), 0)  # label longer than candidate, joined by a dash
        self.assertEqual(ev.label_hit('checkoutservice', ['checkout']), -1)
        self.assertEqual(ev.base_of('x-service-abcde-abcd'), 'x-service')
        self.assertEqual(ev.base_of('x-service-abcde-abc'), 'x-service-abcde-abc')

    def test_author_normalisation(self):
        self.assertEqual(ev.normalise_name(' Checkout-Service '), 'checkoutservice')
        self.assertEqual(ev.normalise_name('payment-service-0'), 'paymentservice-0')
        self.assertEqual(ev.normalise_name('cartservice'), 'cartservice')
        self.assertEqual(ev.normalise_name('mystery'), 'mystery')
        self.assertEqual(ev.normalise_name('product-catalog-service'), 'productcatalogservice')
        self.assertEqual(ev.normalise_name('product-catalog-service-3'), 'productcatalogservice-3')
        self.assertEqual(ev.normalise_name('cart-service-0'), 'cartservice-0')

    def test_params_dict_and_string_fallback(self):
        self.assertEqual(ev.parse_params({'service_name': 'a'}), ({'service_name': 'a'}, True))
        self.assertEqual(ev.parse_params("{'service_name': 'a'}"), ({'service_name': 'a'}, True))
        self.assertEqual(ev.parse_params(7), ({}, False))
        self.assertEqual(ev.parse_params('not a dict'), ({}, False))


class StageLabelTest(unittest.TestCase):
    def test_not_queried_splits_by_trace_shape(self):
        other = {'c': {'calls': [metric_call('frontendservice', NO_KPI), log_call(GT)]}}
        row, _, _ = analyze(build_run(TREE, other))
        self.assertEqual((row['I0'], row['s0_label'], row['gt_span_in_trace']), (False, 'S0_gt_span_present_not_queried', 1))
        row, _, _ = analyze(build_run(TREE_WITHOUT_GT))
        self.assertEqual((row['I0'], row['s0_label'], row['gt_span_in_trace']), (False, 'S0_gt_span_absent', 0))
        self.assertEqual((row['I1'], row['first_loss_linear']), ('NA', 'S0'))

    def test_a_run_that_never_asks_for_metrics_is_not_na(self):
        logs_only = {span: {'calls': [log_call(service)]} for span, service, _ in walk(TREE)}
        row, _, _ = analyze(build_run(TREE, logs_only))
        self.assertEqual((row['I0'], row['queried_gt'], row['s0_label']), (False, False, 'S0_gt_span_present_not_queried'))

    def test_empty_result_reasons(self):
        for response, source, reason in ((NO_KPI, 'repaired', 'no_kpi'), (NO_ROWS, 'repaired', 'no_rows'),
                                         (NO_ROWS, 'absent', 'absent_source'),
                                         (table('currencyservice'), 'repaired', 'table_no_gt_kpi')):
            selfs = {'c': {'calls': [metric_call(GT, response, source), log_call(GT)]}}
            row, _, _ = analyze(build_run(TREE, selfs))
            self.assertEqual((row['I0'], row['s0_label'], row['empty_reason']), (False, 'S0_empty_result', reason))
        selfs = {'c': {'calls': [metric_call(GT, NO_KPI), log_call(GT)]}, 'b': {'calls': [metric_call(GT, NO_ROWS)]}}
        row, _, _ = analyze(build_run(TREE, selfs))
        self.assertEqual((row['empty_reason'], row['empty_reason_set']), ('mixed', ['no_kpi', 'no_rows']))

    def test_table_wins_even_without_a_gt_span(self):
        selfs = {'a': {'abn': True, 'calls': [metric_call(GT, table(GT)), log_call(GT)]}}
        row, spans, _ = analyze(build_run(TREE_WITHOUT_GT, selfs))
        self.assertEqual((row['I0'], row['gt_span_in_trace'], row['s0_label']), (True, 0, ''))
        self.assertTrue(spans['a']['is_carrier'])
        self.assertFalse(spans['a']['is_gt_span'])

    def test_table_from_a_query_the_scorer_does_not_match(self):
        selfs = {'c': {'abn': True, 'calls': [metric_call('frontendservice', table(GT)), log_call(GT)]}}
        row, spans, _ = analyze(build_run(TREE, selfs))
        self.assertTrue(row['I0'])
        self.assertFalse(row['queried_gt'])
        self.assertTrue(spans['c']['table_gt_kpi_from_nonmatching_query'])
        self.assertTrue(spans['c']['tool_match_rule_differs'])
        self.assertEqual(spans['c']['table_key_prefixes'], [GT])

    def test_table_and_query_agree_or_differ(self):
        _, spans, _ = analyze(build_run(TREE, CARRIER))
        self.assertEqual((spans['c']['table_gt_kpi_from_nonmatching_query'], spans['c']['tool_match_rule_differs']),
                         (False, False))
        selfs = {'c': {'abn': True, 'calls': [metric_call(GT, table('cartservice')), log_call(GT)]}}
        _, spans, _ = analyze(build_run(TREE, selfs))
        self.assertEqual((spans['c']['table_has_gt_kpi'], spans['c']['table_gt_kpi_from_nonmatching_query'],
                          spans['c']['tool_match_rule_differs']), (False, False, True))

    def test_the_service_of_a_kpi_is_the_second_last_part_of_its_key(self):
        deep = 'key,regular_mean,current_mean\npod.checkoutservice.cpu,0.4,9.0\n'
        selfs = {'c': {'abn': True, 'calls': [metric_call(GT, deep), log_call(GT)]}}
        row, spans, _ = analyze(build_run(TREE, selfs))
        self.assertEqual((row['I0'], spans['c']['table_has_gt_kpi'], spans['c']['table_key_prefixes']), (True, True, ['pod']))
        first = 'key,regular_mean,current_mean\ncheckoutservice.cpu.pod,0.4,9.0\n'
        selfs = {'c': {'abn': True, 'calls': [metric_call(GT, first), log_call(GT)]}}
        self.assertEqual(analyze(build_run(TREE, selfs))[0]['I0'], False)

    def test_first_metric_query_gives_the_timestamp_offset(self):
        def result(delta):
            return {'params': {'service_name': GT, 'timestamp': str(int(TS) + delta)}, 'response': NO_KPI,
                    'source': 'repaired'}
        self.assertEqual(ev.span_metric_view([result(5000), result(9000)], GT, TS)['offset'], 5.0)
        self.assertEqual(ev.span_metric_view([result(-300000000000), result(0)], GT, TS)['offset'], -300000000.0)
        self.assertEqual(ev.span_metric_view([], GT, TS)['offset'], 'NA')

    def test_not_flagged_and_fallback_branch(self):
        quiet = {'c': {'abn': False, 'calls': CARRIER['c']['calls']}}
        row, _, _ = analyze(build_run(TREE, quiet))
        self.assertEqual((row['I0'], row['I1'], row['s1_label'], row['first_loss_linear']), (True, False, 'S1_not_flagged', 'S1'))
        bare = output('c', GT).replace('"has_error_logs": false,', '').replace('"has_metric_anomaly": false,', '')
        fallback = {'c': {'output': bare, 'fallback': True, 'calls': CARRIER['c']['calls']}}
        row, spans, unseen = analyze(build_run(TREE, fallback))
        self.assertEqual((row['I1'], row['s1_label']), (False, 'S1_not_flagged:fallback_flags_missing'))
        self.assertTrue(spans['c']['fallback_used'] and spans['c']['fallback_flags_missing'])
        self.assertEqual(unseen['fallback_used'], 1)
        one = output('c', GT).replace('"has_metric_anomaly": false,', '')
        row, spans, _ = analyze(build_run(TREE, {'c': {'output': one, 'fallback': True, 'calls': CARRIER['c']['calls']}}))
        self.assertTrue(spans['c']['fallback_flags_missing'])
        self.assertEqual((row['I1'], row['s1_label']), (False, 'S1_not_flagged:fallback_flags_missing'))
        both = dict(fallback, a={'abn': True, 'calls': [metric_call(GT, table(GT)), log_call('productcatalogservice')]})
        row, _, unseen = analyze(build_run(TREE, both))
        self.assertEqual((row['I1'], row['s1_label']), (True, ''))
        self.assertEqual(unseen['fallback_used'], 1)

    def test_fallback_needs_a_user_message(self):
        def last(role, text):
            return request_event(1, 'c', 'self_state_verification',
                                 messages=[SYSTEM, {'role': 'user', 'content': 'go'}, {'role': role, 'content': text}])
        self.assertTrue(ev.is_fallback(last('user', FALLBACK)))
        self.assertFalse(ev.is_fallback(last('assistant', FALLBACK)))
        self.assertFalse(ev.is_fallback(last('user', 'something else')))
        self.assertFalse(ev.is_fallback({'kind': 'request'}))

    def test_a_carrier_without_a_self_state_leaves_i1_open(self):
        run = build_run(TREE, CARRIER)
        run['events'] = [e for e in run['events']
                         if not (e.get('kind') == 'agent_complete' and e.get('operation') == 'self_state_verification'
                                 and e.get('span_id') == 'c')]
        row, spans, _ = analyze(run)
        self.assertEqual((row['I0'], row['I1'], row['carrier_count'], spans['c']['self_present']), (True, 'NA', 1, False))

    def test_censored_consolidation_is_na_in_all_three_forms(self):
        row, _, _ = analyze(build_run(TREE, CARRIER, {'r': 'adservice'}, final=None, stop='Model request budget exhausted'))
        self.assertEqual((row['I2'], row['I2_raw'], row['I2_lenient']), ('NA', 'NA', 'NA'))
        row, _, _ = analyze(build_run(TREE, CARRIER, {'r': 'adservice'}))
        self.assertEqual((row['I2'], row['I2_raw'], row['I2_lenient']), (False, False, False))

    def test_misattributed_carrier(self):
        selfs = {'a': {'abn': True, 'met': True, 'calls': [metric_call(GT, table(GT)), log_call(GT)]}}
        row, _, _ = analyze(build_run(TREE, selfs))
        self.assertEqual((row['I1'], row['misattributed']), (True, True))
        row, _, _ = analyze(build_run(TREE, CARRIER))
        self.assertEqual((row['I1'], row['misattributed']), (True, False))
        both = dict(selfs, c=CARRIER['c'])  # one abnormal carrier is the faulty service itself
        row, _, _ = analyze(build_run(TREE, both))
        self.assertEqual((row['carrier_abnormal_count'], row['I1'], row['misattributed']), (2, True, False))

    def test_chain_depth_and_break_class(self):
        cons = {'c': GT, 'a': GT, 'r': GT}
        row, spans, _ = analyze(build_run(TREE, CARRIER, cons))
        self.assertEqual((row['I2'], spans['c']['chain_depth_kept'], spans['c']['break_class']), (True, 3, 'none'))
        self.assertEqual((row['chain_depth_kept_max'], row['chains_intact_count']), (3, 1))
        row, spans, _ = analyze(build_run(TREE, CARRIER, {'c': GT, 'a': 'currencyservice', 'r': GT}))
        self.assertEqual((row['I2'], spans['c']['chain_depth_kept'], spans['c']['break_class']), (True, 1, 'other_service'))
        self.assertEqual(row['chains_intact_count'], 0)
        row, spans, _ = analyze(build_run(TREE, CARRIER, {'c': GT, 'a': None, 'r': GT}))
        self.assertEqual(spans['c']['break_class'], 'refusal')
        row, spans, _ = analyze(build_run(TREE, CARRIER, {'c': 'adservice', 'a': GT, 'r': GT}))
        self.assertEqual((spans['c']['chain_depth_kept'], spans['c']['break_class']), (0, 'other_service'))

    def test_two_carriers_have_their_own_chain(self):
        selfs = {'c': CARRIER['c'], 'a': {'abn': True, 'calls': [metric_call(GT, table(GT)), log_call('productcatalogservice')]}}
        row, spans, _ = analyze(build_run(TREE, selfs, {'c': GT, 'a': 'adservice', 'r': GT}))
        self.assertEqual((spans['c']['chain_depth_kept'], spans['a']['chain_depth_kept']), (1, 0))
        self.assertEqual((row['carrier_count'], row['carrier_abnormal_count'], row['chains_intact_count']), (2, 2, 0))

    def test_refusal_values(self):
        for value in (None, 'none', 5, '', '  Unknown ', ('raw', '{"local_root_cause": null}')):
            row, _, _ = analyze(build_run(TREE, CARRIER, {'r': value}))
            self.assertEqual((row['root_class'], row['I2'], row['I5']), ('refusal', False, 'refusal'), value)

    def test_refusal_words_are_all_recognised(self):
        for value in ('N/A', 'NA', 'null', 'None', 'unknown', ' n/a '):
            self.assertEqual(ev.classify_label(value, GT)[0], 'refusal', value)
        self.assertEqual(ev.classify_label('nasty', GT)[0], 'other_service')

    def test_root_label_is_normalised_before_matching(self):
        row, _, unseen = analyze(build_run(TREE, CARRIER, {'r': 'Checkout-Service'}))
        self.assertEqual((row['I2'], row['I2_raw']), (True, False))
        self.assertEqual(unseen['label_normalisation_changes_name'], 1)

    def test_lenient_variant_reads_the_reason(self):
        row, _, _ = analyze(build_run(TREE, CARRIER, {'r': ('reason', 'currencyservice', 'the checkoutservice. is slow')}))
        self.assertEqual((row['I2'], row['I2_lenient']), (False, True))
        row, _, _ = analyze(build_run(TREE, CARRIER, {'r': ('reason', 'currencyservice', 'checkoutservice2 and mycheckoutservice')}))
        self.assertEqual(row['I2_lenient'], False)

    def test_hint_indicator_and_strict_variant(self):
        row, _, _ = analyze(build_run(TREE, CARRIER))
        self.assertEqual((row['I3'], row['I3_strict'], row['hint_list_size'], row['gt_sole_entry']), (True, True, 1, True))
        crowd = {s: {'abn': True} for s in ('r', 'a', 'b')}
        crowd['c'] = CARRIER['c']
        row, _, _ = analyze(build_run(TREE, crowd))
        self.assertEqual((row['I3'], row['I3_strict'], row['hint_list_size'], row['gt_sole_entry']), (True, False, 4, False))
        by_pod = {'c': dict(CARRIER['c'])}
        row, _, _ = analyze(build_run(('r', 'frontendservice', [('c', 'checkoutservice-0', [])]), by_pod))
        self.assertEqual((row['I3'], row['hint_list_size_by_base']), (True, 1))

    def test_strict_variant_and_sole_entry_bounds(self):
        two = {'c': CARRIER['c'], 'r': {'abn': True}}
        row, _, _ = analyze(build_run(TREE, two))
        self.assertEqual((row['hint_list_size'], row['I3_strict'], row['gt_sole_entry']), (2, True, False))
        three = dict(two, a={'abn': True})
        row, _, _ = analyze(build_run(TREE, three))
        self.assertEqual((row['hint_list_size'], row['I3'], row['I3_strict'], row['gt_sole_entry']), (3, True, False, False))

    def test_a_none_service_name_does_not_stop_the_run(self):
        run = build_run(TREE, {'b': {'abn': True}, 'c': CARRIER['c']})
        run['graph']['children'][1]['raw']['cmdb_id'] = None
        row, spans, _ = analyze(run)
        self.assertEqual((row['I0'], row['I3'], row['hint_list_size']), (True, True, 2))
        self.assertEqual(spans['b']['cmdb_id'], None)

    def test_hint_missing_when_the_carrier_belongs_to_another_service(self):
        selfs = {'a': {'abn': True, 'calls': [metric_call(GT, table(GT)), log_call('productcatalogservice')]}}
        row, _, _ = analyze(build_run(TREE, selfs, final=('adservice', 'paymentservice')))
        self.assertEqual((row['I1'], row['I3'], row['I4']), (True, False, False))
        self.assertEqual((row['final_residual'], row['hint_weakened']), ('hint_missing_not_rank1', True))
        self.assertEqual(row['first_loss_linear'], 'S2')

    def test_rank_recall_and_mrr(self):
        row, _, _ = analyze(build_run(TREE, CARRIER, final=('currencyservice', 'checkoutservice-0')))
        self.assertEqual((row['I4'], row['rank'], row['R@3'], row['MRR']), (False, 1, True, '0.5000'))
        row, _, _ = analyze(build_run(TREE, CARRIER, final=['a', 'b', 'c', 'd', 'e', 'f', 'checkoutservice']))
        self.assertEqual((row['rank'], row['MRR']), (6, '0.1429'))
        row, _, _ = analyze(build_run(TREE, CARRIER, final=('adservice',)))
        self.assertEqual((row['rank'], row['MRR'], row['R@3']), (-1, '0.0000', False))

    def test_recall_at_three_stops_after_the_third_place(self):
        row, _, _ = analyze(build_run(TREE, CARRIER, final=['a', 'b', GT]))
        self.assertEqual((row['rank'], row['R@3']), (2, True))
        row, _, _ = analyze(build_run(TREE, CARRIER, final=['a', 'b', 'c', GT]))
        self.assertEqual((row['rank'], row['R@3'], row['MRR']), (3, False, '0.2500'))

    def test_leading_true_and_its_end(self):
        self.assertEqual(ev.leading_true([True, False]), (1, 'false'))
        self.assertEqual(ev.leading_true([True, 'NA']), (1, 'NA'))
        self.assertEqual(ev.leading_true([True, True]), (2, 'all'))
        self.assertEqual(ev.leading_true([False, True]), (0, 'false'))
        row, _, _ = analyze(build_run(TREE, CARRIER, {'r': GT}))
        self.assertEqual((row['leading_true'], row['leading_true_end']), (5, 'all'))
        quiet = {'c': {'abn': False, 'calls': CARRIER['c']['calls']}}
        row, _, _ = analyze(build_run(TREE, quiet))
        self.assertEqual((row['leading_true'], row['leading_true_end']), (1, 'false'))
        row, _, _ = analyze(build_run(TREE, CARRIER, cons=False, final=None, stop='Model request budget exhausted'))
        self.assertEqual((row['leading_true'], row['leading_true_end']), (2, 'NA'))

    def test_final_agreement_classes(self):
        row, _, _ = analyze(build_run(TREE, CARRIER, {'r': 'currencyservice'}, final=('currencyservice', GT)))
        self.assertEqual(row['I5'], 'same')
        row, _, _ = analyze(build_run(TREE, CARRIER, {'r': 'currencyservice'}, final=(GT, 'currencyservice')))
        self.assertEqual(row['I5'], 'diff')

    def test_final_residual_branches(self):
        selfs = CARRIER
        row, _, _ = analyze(build_run(TREE, selfs, {'r': 'adservice'}, final=('adservice', 'x')))
        self.assertEqual((row['final_residual'], row['final_residual_split']),
                         ('reaches_final_input_not_rank1', 'top1_equals_wrong_root_label'))
        row, _, _ = analyze(build_run(TREE, selfs, {'r': 'adservice'}, final=('paymentservice', 'x')))
        self.assertEqual(row['final_residual_split'], 'top1_differs_from_root_label')
        row, _, _ = analyze(build_run(TREE, selfs, {'r': None}, final=('paymentservice', 'x')))
        self.assertEqual(row['final_residual_split'], 'root_refusal')
        row, _, _ = analyze(build_run(TREE_WITHOUT_GT, final=('paymentservice',)))
        self.assertEqual(row['final_residual'], 'S0')
        quiet = {'c': {'abn': False, 'calls': CARRIER['c']['calls']}}
        row, _, _ = analyze(build_run(TREE, quiet, final=('paymentservice',)))
        self.assertEqual(row['final_residual'], 'S1')
        row, _, _ = analyze(build_run(TREE_WITHOUT_GT, final=(GT,)))
        self.assertEqual((row['final_residual'], row['hit_without_evidence'], row['outcome_hit']), ('none', True, True))

    def test_preserved(self):
        row, _, _ = analyze(build_run(TREE, CARRIER, {'r': GT}))
        self.assertEqual((row['first_loss_linear'], row['final_residual'], row['leading_true']), ('preserved', 'none', 5))
        self.assertEqual((row['I5'], row['chain_weakened'], row['hint_weakened']), ('same', False, False))

    def test_first_loss_linear_is_not_the_final_residual(self):
        row, _, _ = analyze(build_run(TREE, CARRIER, {'r': 'frontendservice'}))
        self.assertEqual((row['I2'], row['I3'], row['I4']), (False, True, True))
        self.assertEqual((row['first_loss_linear'], row['final_residual'], row['chain_weakened']), ('S2', 'none', True))
        self.assertIn('S2 even when the service is in the evidence graph', ev.FIRST_LOSS_NOTE)
        summary = ev.summarise([row], ev.case_rows([row]), [], ev.funnel([row]), [], {}, 'x')
        self.assertEqual(summary['first_loss_linear_note'], ev.FIRST_LOSS_NOTE)


class SpanFlagTest(unittest.TestCase):
    def test_d1_reads_the_delivered_text(self):
        error_log = 'log_id,timestamp,cmdb_id,log_name,value\n1,2,checkoutservice,x,Exception thrown\n2,3,c,x,ok\n'
        spec = {'abn': True, 'err': True, 'calls': [metric_call(GT, table(GT)), log_call(GT, EMPTY_LOG)]}
        _, spans, _ = analyze(build_run(TREE, {'c': spec}))
        self.assertEqual((spans['c']['D1'], spans['c']['D1_empty_logs'], spans['c']['d1_log_source']), (True, True, 'author'))
        spec['calls'][1] = log_call(GT, error_log)
        _, spans, _ = analyze(build_run(TREE, {'c': spec}))
        self.assertEqual((spans['c']['D1'], spans['c']['D1_empty_logs']), (False, False))
        spec['calls'][1] = log_call(GT, error_log, delivered='cmdb_id,message_template\nc,all fine\nc,also fine\n')
        _, spans, _ = analyze(build_run(TREE, {'c': spec}))
        self.assertEqual((spans['c']['D1'], spans['c']['D1_empty_logs']), (True, False))
        spec['calls'][1] = log_call(GT, 'header\nrow one\nrow two\n')
        _, spans, _ = analyze(build_run(TREE, {'c': spec}))
        self.assertEqual((spans['c']['D1'], spans['c']['log_result_classes']), (True, 'no_error_text'))

    def test_d1_needs_every_log_result_and_a_usable_source(self):
        spec = {'abn': True, 'err': True, 'calls': [metric_call(GT, table(GT)), log_call(GT, source='absent')]}
        _, spans, _ = analyze(build_run(TREE, {'c': spec}))
        self.assertEqual((spans['c']['D1'], spans['c']['D1_na'], spans['c']['d1_log_source']), ('NA', True, 'absent'))
        spec['calls'] = [metric_call(GT, table(GT))]
        _, spans, _ = analyze(build_run(TREE, {'c': spec}))
        self.assertEqual((spans['c']['D1'], spans['c']['d1_log_source']), (False, 'none'))
        spec['calls'] = [metric_call(GT, table(GT)), log_call(GT), log_call(GT, 'header\nError one\nrow\n')]
        _, spans, _ = analyze(build_run(TREE, {'c': spec}))
        self.assertEqual(spans['c']['D1'], False)
        row, _, _ = analyze(build_run(TREE, {'c': {'abn': True, 'err': True, 'calls': CARRIER['c']['calls']}}))
        self.assertEqual((row['D1'], row['D1_empty_logs']), (True, True))

    def test_a_log_class_mix_is_not_empty_logs(self):
        mixed = [metric_call(GT, table(GT)), log_call(GT), log_call(GT, 'header\nrow one\nrow two\n')]
        _, spans, _ = analyze(build_run(TREE, {'c': {'abn': True, 'err': True, 'calls': mixed}}))
        self.assertEqual((spans['c']['D1'], spans['c']['D1_empty_logs'], spans['c']['log_result_classes']),
                         (True, False, 'empty;no_error_text'))

    def test_an_unapplied_budget_leaves_the_raw_response(self):
        error_log = 'log_id,timestamp,cmdb_id,log_name,value\n1,2,checkoutservice,x,Exception thrown\n'
        unapplied = {'response': error_log, 'budget': {'applied': False, 'delivered': 'a\nb\nc\n'}}
        applied = {'response': error_log, 'budget': {'applied': True, 'delivered': 'a\nb\nc\n'}}
        self.assertEqual(ev.delivered_text(unapplied), error_log)
        self.assertEqual(ev.log_class(ev.delivered_text(unapplied)), 'error_text')
        self.assertEqual(ev.log_class(ev.delivered_text(applied)), 'no_error_text')
        self.assertEqual(ev.delivered_text({'response': None, 'budget': None}), '')

    def test_d2_ignores_a_span_that_received_a_table(self):
        spec = {'abn': True, 'calls': [metric_call(GT, table(GT)), log_call(GT)]}
        _, spans, _ = analyze(build_run(TREE, {'c': spec}))
        self.assertEqual(spans['c']['D2'], False)

    def test_d2_for_latency_only_spans(self):
        _, spans, _ = analyze(build_run(TREE, {'c': {'abn': True, 'calls': [metric_call(GT, NO_KPI), log_call(GT)]}}))
        self.assertTrue(spans['c']['D2'])
        _, spans, _ = analyze(build_run(TREE, CARRIER))
        self.assertEqual(spans['c']['D2'], False)
        missing = output('c', GT, True).replace('"has_error_logs": false,', '')
        _, spans, _ = analyze(build_run(TREE, {'c': {'output': missing, 'calls': [metric_call(GT, NO_KPI), log_call(GT)]}}))
        self.assertEqual(spans['c']['D2'], 'NA')
        row, _, _ = analyze(build_run(TREE, {'c': {'abn': True, 'calls': [metric_call(GT, NO_KPI), log_call(GT)]}}))
        self.assertTrue(row['D2'])
        row, _, _ = analyze(build_run(TREE, {'c': CARRIER['c'], 'a': {'abn': True}}))
        self.assertEqual(row['D2'], True)  # productcatalogservice has only latency-style spans

    def test_empty_metric_detection_prefers_the_absent_source(self):
        selfs = {'c': {'calls': [metric_call(GT, NO_ROWS, 'absent'), metric_call(GT, NO_KPI), metric_call(GT, NO_ROWS),
                                 metric_call(GT, '{"x":1}'), log_call(GT)]}}
        _, spans, _ = analyze(build_run(TREE, selfs))
        self.assertEqual(spans['c']['metric_empty_reasons'], ['absent_source', 'no_kpi', 'no_rows', 'other'])

    def test_query_timestamp_offset_is_in_seconds(self):
        _, spans, _ = analyze(build_run(TREE, CARRIER))
        self.assertEqual(spans['c']['metric_query_ts_offset_s'], 1.0)

    def test_hint_columns_of_the_author_code(self):
        crowd = {'r': {'abn': True, 'err': True}, 'c': dict(CARRIER['c'], err=True)}
        row, spans, _ = analyze(build_run(TREE, crowd))
        self.assertEqual((row['hint_list_size'], row['d1_dropped_list_size'], row['d2_dropped_list_size']), (2, 0, 2))
        self.assertEqual(spans['c']['hint_list_size'], 2)

    def test_compact_json_passes_the_parser_but_not_the_author_rule(self):
        selfs = {'c': dict(CARRIER['c'], compact=True)}
        row, _, unseen = analyze(build_run(TREE, selfs))
        self.assertEqual((row['I1'], row['I3']), (True, False))
        self.assertEqual(unseen['parsed_true_but_hint_string_false'], 1)


class HintReplayTest(unittest.TestCase):
    def test_rebuild_matches_the_prompt_in_any_order(self):
        names = ['cartservice', 'adservice', 'emailservice']
        nodes = [(s, output(s, s, True)) for s in names] + [('b', output('b', 'b', True, errors=True))]
        errors, metrics = ev.reconstruct_hint(nodes)
        self.assertEqual((errors, metrics), (['b'], names))
        hint = f"\n{ev.HINT_ERROR_PREFIX}b\n{ev.HINT_METRIC_PREFIX}{', '.join(reversed(names))}\n\nGoal:"
        self.assertEqual(ev.prompt_hint(hint), ({'b'}, set(names)))
        row, _, _ = analyze(build_run(TREE, CARRIER))
        self.assertEqual(row['hint_equivalent'], True)
        order = f"\n{ev.HINT_METRIC_PREFIX}checkoutservice"
        row, _, _ = analyze(build_run(TREE, CARRIER, hint=order))
        self.assertEqual(row['hint_equivalent'], True)

    def test_disagreement_and_missing_final(self):
        row, _, _ = analyze(build_run(TREE, CARRIER, hint=f'\n{ev.HINT_METRIC_PREFIX}frontendservice'))
        self.assertEqual(row['hint_equivalent'], False)
        row, _, _ = analyze(build_run(TREE, CARRIER, final=None, stop='Model request budget exhausted'))
        self.assertEqual(row['hint_equivalent'], 'NA')

    def test_hint_rule_is_string_based_with_error_priority(self):
        both = output('c', GT, True, errors=True)
        self.assertEqual(ev.hint_list(both.replace('false', 'true')), 'error')
        self.assertEqual(ev.hint_list(output('c', GT, True)), 'metric')
        self.assertEqual(ev.hint_list(output('c', GT, False)), '')
        self.assertEqual(ev.hint_list(None), '')


class CensoringTest(unittest.TestCase):
    STOP = 'Per-span tool round budget exceeded for span c'

    def test_positive_indicators_survive_and_negative_ones_become_na(self):
        row, _, _ = analyze(build_run(TREE, CARRIER, cons=False, final=None, stop=self.STOP))
        self.assertEqual((row['harness_class'], row['completed'], row['censored']), ('H_cap', False, True))
        self.assertEqual((row['I0'], row['I1'], row['I3']), (True, True, True))
        self.assertEqual((row['I2'], row['I4'], row['I5'], row['first_loss_linear']), ('NA', 'NA', 'NA', 'NA'))
        row, _, _ = analyze(build_run(TREE_WITHOUT_GT, cons=False, final=None, stop=self.STOP))
        self.assertEqual((row['I0'], row['I1'], row['I3'], row['s0_label']), ('NA_censored', 'NA', 'NA', ''))
        quiet = {'c': {'abn': False, 'calls': CARRIER['c']['calls']}}
        row, _, _ = analyze(build_run(TREE, quiet, cons=False, final=None, stop=self.STOP))
        self.assertEqual((row['I0'], row['I1'], row['I3'], row['s1_label']), (True, 'NA', 'NA', ''))

    def test_no_tool_result_is_na_not_censored(self):
        run = build_run(TREE, cons=False, final=None, stop=self.STOP)
        run['events'] = []
        row, _, _ = analyze(run)
        self.assertEqual((row['I0'], row['I3']), ('NA', 'NA'))

    def test_harness_classes(self):
        for reason, label in (('Output stopped without completion', 'H_cap'), ('Per-span tool round budget exceeded', 'H_cap'),
                              ('Model request budget exhausted', 'H_cap'), ('RCLAgent deadline exceeded (30-minute)', 'H_cap'),
                              ("Invalid structured response: Output stopped without completion", 'H_cap'),
                              ('Context overflow', 'H_context'), ('Unsupported telemetry tool parameters', 'H_query'),
                              ('Model server HTTP 500', 'H_infra'), ('Invalid structured response: x', 'H_parse'),
                              ('Invalid agent JSON output: x', 'H_parse'), ('weird', 'H_other'), ('', 'H_other')):
            self.assertEqual(ev.harness_class('failed', reason), label, reason)
        self.assertEqual(ev.harness_class('passed', 'anything'), 'none')

    def test_stop_reason_order(self):
        run = {'worker': {'fatal': None, 'error': 'worker error'}, 'progress': {'reason': 'progress'}, 'events': [
            {'kind': 'fatal', 'reason': 'event'}]}
        self.assertEqual(ev.stop_reason(run), 'worker error')
        run['worker'] = {'fatal': 'worker fatal', 'error': 'worker error'}
        self.assertEqual(ev.stop_reason(run), 'worker fatal')
        run['worker'] = {}
        self.assertEqual(ev.stop_reason(run), 'progress')
        run['progress'] = {}
        self.assertEqual(ev.stop_reason(run), 'event')

    def test_funnel_has_na_columns_and_the_loss_sensitivity(self):
        rows = [analyze(build_run(TREE, CARRIER, cons=False, final=None, stop=self.STOP, seed=SEED))[0],
                analyze(build_run(TREE, CARRIER, {'r': GT}, seed=SEED + 1))[0]]
        table_ = {(r['indicator']): r for r in ev.funnel(rows)}
        self.assertEqual((table_['I2']['true'], table_['I2']['NA'], table_['I2']['runs']), (1, 1, 2))
        self.assertEqual((table_['I0']['true'], table_['I0']['censored'], table_['I0']['true_over_all_runs']), (2, 1, '2/2'))
        self.assertEqual(table_['I0']['saturated'], True)


class RetryAndJoinTest(unittest.TestCase):
    def test_retries_are_not_counted_as_requests(self):
        plain, _, _ = analyze(build_run(TREE, CARRIER, score=SCORED))
        retried, spans, _ = analyze(build_run(TREE, {'c': dict(CARRIER['c'], retries=3)}))
        self.assertEqual((retried['requests'], retried['retries']), (plain['requests'], 3))
        self.assertEqual((spans['c']['self_requests'], spans['c']['self_retries']), (2, 3))
        once, spans, _ = analyze(build_run(TREE, {'c': dict(CARRIER['c'], retries=1)}))
        self.assertEqual((once['retries'], spans['c']['self_retries']), (1, 1))
        self.assertEqual(plain['integrity'], 'ok')

    def test_budget_event_attaches_by_tool_name(self):
        params = {'service_name': GT, 'timestamp': TS}
        events = [request_event(1, 'a', 'self_state_verification'),
                  response_event(1, [(LOGS, params), (METRIC, params)]),
                  {'kind': 'tool_result', 'name': LOGS, 'params': params, 'response': EMPTY_LOG, 'source': 'author',
                   'span_id': 'a'},
                  {'kind': 'tool_result', 'name': METRIC, 'params': params, 'response': NO_KPI, 'source': 'repaired',
                   'span_id': 'a'},
                  {'kind': 'tool_result_budget', 'name': LOGS, 'params': params, 'delivered': None, 'span_id': 'a',
                   'applied': False}]
        problems = []
        results = ev.join_tool_results(events, problems)
        self.assertEqual(problems, [])
        self.assertEqual([r['budget'] is not None for r in results], [True, False])

    def test_final_requests_are_counted_without_retries(self):
        final = request_event(9, None, None)
        retry = request_event(10, None, None, attempt=1, retry_of=9)
        self.assertEqual(final_request_count([request_event(1, 'a', 'consolidate'), final, retry]), 1)
        self.assertEqual(final_request_count([retry]), 0)

    def test_events_are_split_on_newlines_only(self):
        line = json.dumps({'kind': 'surprise', 'text': 'a\u2028b\u0085c\u2029d'}, ensure_ascii=False)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zipped:
            zipped.writestr('run/traces/r1/events.jsonl', line + '\n\n' + line + '\n')
        with zipfile.ZipFile(buffer) as zipped:
            run = ev.read_run(zipped, set(zipped.namelist()), {'run_id': 'r1'}, {}, None)
        self.assertEqual((len(run['events']), run['problems']), (2, []))

    def test_join_is_a_multiset_not_a_position(self):
        run = build_run(TREE, CARRIER, score=SCORED)
        events = run['events']
        first = next(i for i, e in enumerate(events) if e['kind'] == 'tool_result' and e['span_id'] == 'c')
        events[first], events[first + 1] = events[first + 1], events[first]  # tool results in the other order
        row, _, _ = analyze(run)
        self.assertEqual((row['integrity'], row['tool_results_joined'], row['tool_results_raw']), ('ok', 8, 8))

    def test_unmatched_tool_result_is_an_integrity_problem(self):
        run = build_run(TREE, CARRIER)
        run['events'].insert(3, {'kind': 'tool_result', 'name': METRIC, 'params': {'service_name': 'ghost', 'timestamp': TS},
                                 'response': NO_KPI, 'source': 'repaired', 'span_id': 'a'})
        row, _, _ = analyze(run)
        self.assertIn('matches no tool call', row['integrity'])

    def test_response_number_and_tree_parent_are_checked(self):
        run = build_run(TREE, CARRIER)
        next(e for e in run['events'] if e['kind'] == 'response')['number'] = 99
        self.assertIn('does not follow request', analyze(run)[0]['integrity'])
        run = build_run(TREE, CARRIER)
        run['graph']['children'][0]['raw']['parent_span'] = 'zzz'
        self.assertIn('names parent zzz', analyze(run)[0]['integrity'])

    def test_metric_results_never_carry_a_budget_event(self):
        run = build_run(TREE, CARRIER)
        index = next(i for i, e in enumerate(run['events']) if e['kind'] == 'tool_result' and e['name'] == METRIC)
        base = run['events'][index]
        run['events'].insert(index + 1, dict(base, kind='tool_result_budget', delivered=None, applied=False))
        row, _, _ = analyze(run)
        self.assertEqual(row['metric_budget_events'], 1)
        self.assertIn('budget events for metric', row['integrity'])
        self.assertEqual(analyze(build_run(TREE, CARRIER))[0]['metric_budget_events'], 0)

    def test_params_as_a_string_is_the_fallback_and_is_counted(self):
        run = build_run(TREE, CARRIER, score=SCORED)
        for event in run['events']:
            if event['kind'] in ('tool_result', 'tool_result_budget'):
                event['params'] = str(event['params'])
        row, _, unseen = analyze(run)
        self.assertEqual(row['integrity'], 'ok')
        self.assertEqual(unseen['params_string'], 8)

    def test_unseen_kinds_and_unknown_operations_are_counted_not_fatal(self):
        extra = [{'kind': 'surprise'}, {'kind': 'agent_complete', 'operation': None, 'span_id': 'c', 'output': '{}'}]
        row, _, unseen = analyze(build_run(TREE, CARRIER, extra=extra, score=SCORED))
        self.assertEqual((unseen['kind:surprise'], unseen['agent_complete_operation:None']), (1, 1))
        self.assertEqual(row['integrity'], 'ok')

    def test_unparseable_self_state_is_reported(self):
        run = build_run(TREE, {'c': dict(CARRIER['c'], output='not json')})
        row, _, _ = analyze(run)
        self.assertIn('self-state of span c is not a JSON object', row['integrity'])


class ScorerEquivalenceTest(unittest.TestCase):
    def check(self, rank_text, final, expected):
        row, _, _ = analyze(build_run(TREE, CARRIER, final=final, score=rank_text))
        self.assertEqual(row['score_check'], expected)

    def test_exact_r1_and_four_decimal_mrr(self):
        self.check('R@1  : 1.0000  (1/1)\n  MRR  : 1.0000\n', (GT, 'x'), 'match')
        self.check('R@1  : 0.0000  (0/1)\n  MRR  : 0.5000\n', ('x', GT), 'match')
        self.check('R@1  : 0.0000  (0/1)\n  MRR  : 0.1429\n', ['a', 'b', 'c', 'd', 'e', 'f', GT], 'match')
        self.check('R@1  : 0.0000  (0/1)\n  MRR  : 0.5001\n', ('x', GT), 'mismatch')
        self.check('R@1  : 1.0000  (1/1)\n  MRR  : 1.0000\n', ('x', GT), 'mismatch')
        self.check(None, (GT, 'x'), 'no_author_score')

    def test_a_score_that_cannot_be_compared_is_listed_not_dropped(self):
        score = 'R@1  : 1.0000  (1/1)\n  MRR  : 1.0000\n'
        blind = analyze(build_run(TREE, CARRIER, gt=None, score=score))[0]
        fine = analyze(build_run(TREE, CARRIER, score=score, seed=SEED + 1))[0]
        none = analyze(build_run(TREE, CARRIER, seed=SEED + 2))[0]
        self.assertEqual((blind['score_check'], fine['score_check'], none['score_check']),
                         ('not_comparable', 'match', 'no_author_score'))
        rows = [blind, fine, none]
        summary = ev.summarise(rows, ev.case_rows(rows), [], ev.funnel(rows), [], {}, 'x')
        self.assertEqual(summary['scorer_equivalence']['author_scored_runs'], 2)
        self.assertEqual(summary['scorer_equivalence']['compared_runs'], 1)
        self.assertEqual(summary['scorer_equivalence']['not_comparable'], [blind['run_id']])
        self.assertEqual(summary['scorer_equivalence']['mismatches'], [])

    def test_author_score_parser_skips_noise(self):
        noise = ("Error in sitecustomize\nModuleNotFoundError: No module named 'wrapt'\n\nResults  (1 faults)\n"
                 '  R@1  : 0.0000  (0/1)\n  R@3  : 0.0000  (0/1)\n  MRR  : 0.1429\n')
        self.assertEqual(ev.author_score(noise), (0.0, '0.1429'))
        self.assertIsNone(ev.author_score('nothing'))


class TableTest(unittest.TestCase):
    def rows(self, spec):
        keys = ('condition', 'completed', 'I0', 'I1', 'I2', 'I3', 'case', 'gt_service')
        return [dict(zip(keys, ('metric', True) + values)) for values in spec]

    def test_feasibility_needs_three_cases_with_both_groups(self):
        spec = [(True, True, False, True, 'c1', 'x'), (True, True, True, True, 'c1', 'x'),
                (True, True, False, True, 'c2', 'y'), (True, True, True, True, 'c2', 'y'),
                (True, True, False, True, 'c3', 'z'), (True, True, True, True, 'c4', 'z')]
        table_ = {r['stage']: r for r in ev.feasibility(self.rows(spec))}
        self.assertEqual(table_['I2']['status'], 'not_testable')
        self.assertEqual(table_['I2']['cases_with_both_groups'], ['c1', 'c2'])
        self.assertEqual(table_['I1']['status'], 'not_testable')
        spec += [(True, True, True, True, 'c3', 'z')]
        table_ = {r['stage']: r for r in ev.feasibility(self.rows(spec))}
        self.assertEqual((table_['I2']['status'], table_['I2']['cases_with_both_groups']), ('testable', ['c1', 'c2', 'c3']))
        self.assertEqual(table_['I2']['gt_services_with_both_groups'], ['x', 'y', 'z'])

    def test_feasibility_for_i0_uses_all_completed_runs(self):
        rows = self.rows([(True, 'NA', 'NA', 'NA', 'c1', 'x'), (False, 'NA', 'NA', 'NA', 'c2', 'y')])
        table_ = {r['stage']: r for r in ev.feasibility(rows)}
        self.assertEqual((table_['I0']['lost_runs'], table_['I0']['kept_runs']), (1, 1))
        self.assertEqual(table_['I0']['cases_with_both_groups'], [])

    def test_case_comparison_separates_wording_from_content(self):
        a = build_run(TREE, CARRIER)
        b = build_run(TREE, {'c': {'abn': True, 'calls': [metric_call(GT, NO_ROWS, 'absent'), log_call(GT)]}}, condition='no_metric')
        c = build_run(TREE, {'c': {'abn': True, 'calls': [metric_call(GT, NO_ROWS), log_call(GT)]}}, condition='metric_no_log')
        rows = {}
        prints = {}
        for run in (a, b, c):
            _, rows[run['condition']], _, _ = ev.analyze_run(run)
            prints[run['run_id']] = ev.fingerprint(run['events'])
        run_rows = [analyze(r)[0] for r in (a, b, c)]
        comparison = {r['other']: r for r in ev.case_comparison(run_rows, prints)}
        self.assertEqual(set(comparison), {'no_metric', 'metric_no_log'})
        self.assertEqual(comparison['no_metric']['request_numbering'], 'one-based, retries included')
        self.assertEqual(comparison['no_metric']['pairing'], 'independent trajectories, not paired')
        self.assertTrue(comparison['no_metric']['first_request_divergence'])
        # no_metric answers with the empty-log wording only in the metric table; the sentence merge removes that alone
        self.assertNotEqual(comparison['no_metric']['agent_complete_same_share'], '')
        self.assertEqual(comparison['metric_no_log']['divergence_stage'], 'self_state_verification')

    def test_wording_only_difference_disappears_after_merging(self):
        quiet = {'c': {'calls': [metric_call(GT, NO_KPI), log_call(GT)]}}
        other = {'c': {'calls': [metric_call(GT, NO_ROWS), log_call(GT)]}}
        a, b = build_run(TREE, quiet), build_run(TREE, other, condition='no_metric')
        prints = {r['run_id']: ev.fingerprint(r['events']) for r in (a, b)}
        row = ev.case_comparison([analyze(a)[0], analyze(b)[0]], prints)[0]
        self.assertNotEqual(row['first_request_divergence'], '')
        self.assertEqual(row['first_request_divergence_merged'], '')

    def test_case_rows_count_k_of_n(self):
        runs = [analyze(build_run(TREE, CARRIER, {'r': GT}, seed=SEED + i))[0] for i in range(2)]
        runs.append(analyze(build_run(TREE_WITHOUT_GT, seed=SEED + 2, case='case_a'))[0])
        rows = ev.case_rows(runs)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['I0_true'], rows[0]['I0_n'], rows[0]['runs'], rows[0]['gt_service']), (2, 3, 3, GT))


class CommandLineTest(unittest.TestCase):
    def test_options_may_stand_anywhere(self):
        groups = ['A', 'z.zip', 'm.json', 'B', 'y.zip', 'n.json']
        calls = [['out', *groups, '--runs', 'r.txt', '--structure-only', '--label', 'x'],
                 ['--structure-only', 'out', *groups, '--label', 'x', '--runs', 'r.txt'],
                 ['--label', 'x', 'out', '--runs', 'r.txt', *groups, '--structure-only'],
                 ['out', 'A', 'z.zip', 'm.json', '--label', 'x', '--structure-only', 'B', 'y.zip', 'n.json', '--runs', 'r.txt']]
        parsed = [ev.parse_args(call) for call in calls]
        for args in parsed:
            self.assertEqual(args, parsed[0])
        self.assertEqual((parsed[0]['label'], parsed[0]['runs'], parsed[0]['structure_only']), ('x', 'r.txt', True))
        self.assertEqual(parsed[0]['groups'], [('A', 'z.zip', 'm.json'), ('B', 'y.zip', 'n.json')])
        self.assertEqual(parsed[0]['out_dir'], Path('out'))

    def test_the_two_forms_used_by_the_workflow(self):
        self.assertTrue(ev.parse_args(['--structure-only', 'out', 'A', 'a.zip', 'a.json', 'B', 'b.zip', 'b.json'])['structure_only'])
        args = ev.parse_args(['out', '--label', 'main', 'A', 'a.zip', 'a.json', 'B', 'b.zip', 'b.json'])
        self.assertEqual((args['label'], len(args['groups'])), ('main', 2))

    def test_bad_command_lines(self):
        for argv in (['out', 'A', 'z'], ['out'], ['out', 'A', 'z', 'm', '--label'], ['out', 'A', 'z', 'm', '--nope'], []):
            with self.assertRaises(SystemExit):
                ev.parse_args(argv)


class EndToEndTest(unittest.TestCase):
    def package(self, root, reverse=False):
        runs = [build_run(TREE, CARRIER, {'r': GT}, case='case_a', seed=SEED),
                build_run(TREE, CARRIER, {'r': GT}, condition='no_metric', case='case_a', seed=SEED),
                build_run(TREE_WITHOUT_GT, case='case_b', seed=SEED, final=(GT, 'x')),
                build_run(TREE, CARRIER, cons=False, final=None, stop='Model request budget exhausted', case='case_a',
                          seed=SEED + 1)]
        return write_package(root, runs, reverse), runs

    def read(self, directory):
        return {p.name: p.read_bytes() for p in sorted(Path(directory).iterdir())}

    def test_outputs_are_deterministic_whatever_the_zip_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            (zip1, man1), _ = self.package(Path(tmp) / 'one')
            (zip2, man2), _ = self.package(Path(tmp) / 'two', reverse=True)
            run_main(Path(tmp) / 'o1', 'A', zip1, man1)
            run_main('--label', 'x', Path(tmp) / 'o2', 'A', zip2, man2)
            run_main('--label', 'x', Path(tmp) / 'o3', 'A', zip2, man2)
            first, second, third = (self.read(Path(tmp) / n) for n in ('o1', 'o2', 'o3'))
            self.assertEqual(second, third)
            self.assertEqual(sorted(first), ['case-comparison.csv', 'cases.csv', 'funnel.csv', 'runs.csv', 'spans.csv', 'summary.json'])
            for name in first:
                if name != 'summary.json':
                    self.assertEqual(first[name], second[name], name)
            self.assertNotIn(b'\r', first['runs.csv'])
            self.assertTrue(first['summary.json'].endswith(b'\n'))

    def test_outputs_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            (archive, manifest), runs = self.package(tmp)
            run_main('--label', 'synthetic', Path(tmp) / 'analysis', 'A', archive, manifest)
            summary = json.loads((Path(tmp) / 'analysis' / 'summary.json').read_text(encoding='utf-8'))
            self.assertEqual((summary['runs'], summary['completed'], summary['censored']), (4, 3, 1))
            self.assertEqual(summary['label'], 'synthetic')
            self.assertEqual(summary['integrity_problems'], [])
            self.assertFalse(summary['provisional'])
            self.assertEqual(summary['scorer_equivalence']['mismatches'], [])
            self.assertEqual(summary['join_checks']['tool_results_joined'], summary['join_checks']['tool_results_raw'])
            self.assertEqual(summary['hint_equivalence'], {'NA': 1, 'true': 3})
            self.assertEqual(summary['harness_class'], {'H_cap': 1, 'none': 3})
            self.assertEqual(summary['first_loss_linear_note'], ev.FIRST_LOSS_NOTE)
            self.assertEqual({c['gt_service'] for c in summary['cases']}, {GT})
            self.assertEqual(summary['prereg'], ev.prereg_report())
            self.assertIn('funnel', summary)
            self.assertEqual({r['status'] for r in summary['feasibility']}, {'not_testable'})
            text = (Path(tmp) / 'analysis' / 'runs.csv').read_text(encoding='utf-8')
            self.assertIn('first_loss_linear', text.splitlines()[0])
            self.assertEqual(len(text.splitlines()), 5)

    def test_refuses_to_write_over_an_existing_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            (archive, manifest), _ = self.package(tmp)
            run_main(Path(tmp) / 'analysis', 'A', archive, manifest)
            before = self.read(Path(tmp) / 'analysis')
            with self.assertRaises(SystemExit):
                run_main(Path(tmp) / 'analysis', 'A', archive, manifest)
            self.assertEqual(self.read(Path(tmp) / 'analysis'), before)

    def test_the_same_package_twice_is_a_duplicate_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            (archive, manifest), _ = self.package(tmp)
            with self.assertRaisesRegex(SystemExit, 'Duplicate run'):
                run_main(Path(tmp) / 'analysis', 'A', archive, manifest, 'B', archive, manifest)

    def test_a_runs_id_that_no_package_holds_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            (archive, manifest), runs = self.package(tmp)
            listed = Path(tmp) / 'runs.txt'
            listed.write_text(f'{runs[0]["run_id"]}\n\n# a note\ntypo--metric--s1\n', encoding='utf-8')
            for extra in ((), ('--structure-only',)):
                with self.assertRaisesRegex(SystemExit, 'typo--metric--s1'):
                    run_main(Path(tmp) / f'analysis{len(extra)}', 'A', archive, manifest, '--runs', listed, *extra)

    def test_rows_are_sorted_whatever_the_manifest_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = [build_run(TREE, CARRIER, {'r': GT}, case=c, seed=SEED) for c in ('case_a', 'case_b', 'case_c')]
            ordered = sorted(runs, key=lambda r: r['run_id'])
            archive, manifest = write_package(tmp, ordered[::-1])
            run_main(Path(tmp) / 'analysis', 'A', archive, manifest)
            out = Path(tmp) / 'analysis'
            ids = [line.split(',')[0] for line in (out / 'runs.csv').read_text(encoding='utf-8').splitlines()[1:]]
            self.assertEqual(ids, [r['run_id'] for r in ordered])
            spans = [line.split(',')[:5] for line in (out / 'spans.csv').read_text(encoding='utf-8').splitlines()[1:]]
            first = [s[4] for s in spans if s[0] == ordered[0]['run_id']]
            self.assertEqual(first, ['r', 'a', 'b', 'c'])  # depth then span id, not the pre-order of the tree

    def test_runs_option_keeps_the_listed_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            (archive, manifest), runs = self.package(tmp)
            listed = Path(tmp) / 'runs.txt'
            listed.write_text(f'# calibration\n{runs[0]["run_id"]}\n', encoding='utf-8')
            run_main(Path(tmp) / 'analysis', 'A', archive, manifest, '--runs', listed)
            lines = (Path(tmp) / 'analysis' / 'runs.csv').read_text(encoding='utf-8').splitlines()
            self.assertEqual(len(lines), 2)
            self.assertIn(runs[0]['run_id'], lines[1])

    def test_structure_only_prints_and_writes_no_label_or_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            (archive, manifest), _ = self.package(tmp)
            printed = run_main('--structure-only', Path(tmp) / 'analysis', 'A', archive, manifest)
            self.assertIn('spans=4 gt_spans=1 max_depth=2', printed)
            self.assertIn('gt_spans=0', printed)
            names = sorted(p.name for p in (Path(tmp) / 'analysis').iterdir())
            self.assertEqual(names, ['structure.csv', 'summary.json'])
            body = printed + (Path(tmp) / 'analysis' / 'structure.csv').read_text(encoding='utf-8') + \
                (Path(tmp) / 'analysis' / 'summary.json').read_text(encoding='utf-8')
            for forbidden in ('I0', 'I4', 'R@1', 'MRR', 'first_loss', 'residual', 'rank'):
                self.assertNotIn(forbidden, body)
            summary = json.loads((Path(tmp) / 'analysis' / 'summary.json').read_text(encoding='utf-8'))
            self.assertTrue(summary['structure_only'])

    def test_ground_truth_of_a_stopped_run_comes_from_its_sibling(self):
        with tempfile.TemporaryDirectory() as tmp:
            (archive, manifest), runs = self.package(tmp)
            run_main(Path(tmp) / 'analysis', 'A', archive, manifest)
            rows = (Path(tmp) / 'analysis' / 'runs.csv').read_text(encoding='utf-8').splitlines()
            stopped = next(r for r in rows if f'--metric--s{SEED + 1}' in r)
            self.assertIn(',' + GT + ',', stopped)

    def test_unscored_or_unparseable_input_is_provisional(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = [build_run(TREE, CARRIER, {'r': GT})]
            runs[0]['events'].insert(2, {'kind': 'tool_result', 'name': METRIC, 'params': {'service_name': 'ghost', 'timestamp': TS},
                                         'response': NO_KPI, 'source': 'repaired', 'span_id': 'a'})
            archive, manifest = write_package(tmp, runs)
            run_main(Path(tmp) / 'analysis', 'A', archive, manifest)
            summary = json.loads((Path(tmp) / 'analysis' / 'summary.json').read_text(encoding='utf-8'))
            self.assertTrue(summary['provisional'])
            self.assertEqual(len(summary['integrity_problems']), 1)


class EdgeInputTest(unittest.TestCase):
    STOP = 'Per-span tool round budget exceeded for span c'
    PARAMS = {'service_name': GT, 'timestamp': TS}

    def test_a_budget_event_attaches_to_the_latest_identical_result(self):
        result = {'kind': 'tool_result', 'name': LOGS, 'params': self.PARAMS, 'response': EMPTY_LOG, 'source': 'author',
                  'span_id': 'a'}
        budget = {'kind': 'tool_result_budget', 'name': LOGS, 'params': self.PARAMS, 'delivered': None, 'span_id': 'a',
                  'applied': False}
        events = [request_event(1, 'a', 'self_state_verification'),
                  response_event(1, [(LOGS, self.PARAMS), (LOGS, self.PARAMS)]), result, dict(result), budget]
        results = ev.join_tool_results(events, [])
        self.assertEqual([r['budget'] is not None for r in results], [False, True])

    def test_lenient_reason_needs_a_boundary_on_both_sides(self):
        for text in ('x_checkoutservice', '_checkoutservice is slow', '1checkoutservice'):
            row, _, _ = analyze(build_run(TREE, CARRIER, {'r': ('reason', 'currencyservice', text)}))
            self.assertEqual(row['I2_lenient'], False, text)

    def test_a_faulty_service_beside_one_other_is_not_the_sole_entry(self):
        row, _, _ = analyze(build_run(TREE, {'c': CARRIER['c'], 'a': {'abn': True}}))
        self.assertEqual((row['hint_list_size'], row['gt_sole_entry']), (2, False))

    def test_a_final_candidate_that_is_not_a_string_gives_no_relation(self):
        for final in ([123, 'x'], [None], [[GT]]):
            row, _, _ = analyze(build_run(TREE, CARRIER, final=final))
            self.assertEqual(row['I5'], 'NA', final)

    def test_ground_truth_is_the_first_row_with_a_service(self):
        for body, expected in (('1,service,checkoutservice,cpu\r\n2,service,adservice,cpu\r\n', GT),
                               ('1,service,,cpu\r\n2,service,adservice,cpu\r\n', None)):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w') as zipped:
                zipped.writestr('run/scoring/r1/groundtruth.csv', 'timestamp,level,cmdb_id,failure_type\r\n' + body)
            with zipfile.ZipFile(buffer) as zipped:
                self.assertEqual(ev.read_gt(zipped, set(zipped.namelist()), 'r1'), expected)

    def test_the_empty_reason_is_kept_for_a_censored_run(self):
        selfs = {'c': {'calls': [metric_call(GT, NO_ROWS, 'absent'), log_call(GT)]}}
        row, _, _ = analyze(build_run(TREE, selfs, condition='no_metric', cons=False, final=None, stop=self.STOP))
        self.assertEqual((row['I0'], row['s0_label'], row['empty_reason']), ('NA_censored', '', 'absent_source'))

    def test_a_completed_run_without_a_score_is_an_integrity_problem(self):
        row, _, _ = analyze(build_run(TREE, CARRIER))
        self.assertIn('without a parseable author-score', row['integrity'])
        rows = [row]
        summary = ev.summarise(rows, ev.case_rows(rows), [], ev.funnel(rows), [], {}, 'x')
        self.assertEqual((summary['completed_without_score'], summary['provisional']), (1, True))
        stopped, _, _ = analyze(build_run(TREE, CARRIER, cons=False, final=None, stop=self.STOP))
        self.assertEqual(stopped['integrity'], 'ok')

    def test_an_unreadable_request_payload_is_a_problem_not_a_crash(self):
        run = build_run(TREE, CARRIER, score=SCORED)
        run['events'].insert(0, {'kind': 'request', 'phase': 'trace', 'number': 0, 'payload': '{not json'})
        run['events'].insert(1, {'kind': 'request', 'phase': 'trace', 'number': 0})
        row, _, _ = analyze(run)
        self.assertIn('unreadable payload', row['integrity'])

    def test_params_of_an_unknown_type_are_a_problem_and_have_their_own_count(self):
        run = build_run(TREE, CARRIER, score=SCORED)
        next(e for e in run['events'] if e['kind'] == 'tool_result')['params'] = 5
        row, _, unseen = analyze(run)
        self.assertIn('unrecognised params', row['integrity'])
        self.assertEqual((unseen['params_unrecognised'], unseen['params_string']), (1, 0))

    def test_status_comes_from_the_worker_file_only(self):
        run = build_run(TREE, CARRIER, score=SCORED)
        run['worker'] = None
        row, _, _ = analyze(run)
        self.assertEqual((row['status'], row['harness_class'], row['censored']), ('missing', 'H_other', True))

    def test_hint_facts_of_a_censored_run_are_not_available(self):
        row, spans, _ = analyze(build_run(TREE, CARRIER, cons=False, final=None, stop=self.STOP))
        self.assertEqual((row['I3'], row['hint_list_size'], row['hint_list_size_by_base'], row['gt_sole_entry']),
                         (True, 'NA', 'NA', 'NA'))
        self.assertEqual((row['d1_dropped_list_size'], row['d2_dropped_list_size']), ('NA', 'NA'))
        self.assertEqual(spans['c']['hint_list_size'], 'NA')

    def test_a_failed_runs_option_leaves_no_output_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive, manifest = write_package(tmp, [build_run(TREE, CARRIER, seed=SEED)])
            listed = Path(tmp) / 'runs.txt'
            listed.write_text('no-such-run\n', encoding='utf-8')
            for extra in ((), ('--structure-only',)):
                with self.assertRaises(SystemExit):
                    run_main(Path(tmp) / 'analysis', 'A', archive, manifest, '--runs', listed, *extra)
                self.assertFalse((Path(tmp) / 'analysis').exists())


class FreezeReceiptTest(unittest.TestCase):
    def receipt(self, tmp, **changes):
        codebook = Path(tmp) / 'codebook.md'
        codebook.write_bytes(b'rule one\r\nrule two\r\n')
        recorded = {'codebook_path': str(codebook), 'codebook_sha256': hashlib.sha256(b'rule one\nrule two\n').hexdigest(),
                    'analyzer_sha256': ev.sha256_lf(ev.__file__), 'imports_sha256': ev.module_hashes()}
        recorded.update(changes)
        path = Path(tmp) / 'prereg.json'
        path.write_text(json.dumps(recorded), encoding='utf-8')
        return path

    def test_all_components_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = ev.prereg_report(self.receipt(tmp), tmp)
        self.assertEqual(report, {'frozen': True, 'codebook_sha_matches': True, 'analyzer_sha_matches': True,
                                  'imports_sha_match': True})

    def test_each_component_can_fail_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ev.prereg_report(self.receipt(tmp, codebook_sha256='0' * 64), tmp)['codebook_sha_matches'], False)
            self.assertEqual(ev.prereg_report(self.receipt(tmp, analyzer_sha256='0' * 64), tmp)['analyzer_sha_matches'], False)
            wrong = dict(ev.module_hashes(), **{'compare-run-outputs.py': '0' * 64})
            report = ev.prereg_report(self.receipt(tmp, imports_sha256=wrong), tmp)
            self.assertEqual((report['imports_sha_match'], report['codebook_sha_matches'], report['analyzer_sha_matches']),
                             (False, True, True))
            report = ev.prereg_report(self.receipt(tmp, codebook_path='gone.md'), tmp)
            self.assertEqual(report['codebook_sha_matches'], False)

    def test_no_receipt_means_not_frozen(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = ev.prereg_report(Path(tmp) / 'none.json', tmp)
        self.assertEqual(report, {'frozen': False, 'codebook_sha_matches': False, 'analyzer_sha_matches': False,
                                  'imports_sha_match': False})

    def test_crlf_does_not_change_the_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            one, two = Path(tmp) / 'one', Path(tmp) / 'two'
            one.write_bytes(b'a\nb\n')
            two.write_bytes(b'a\r\nb\r\n')
            self.assertEqual(ev.sha256_lf(one), ev.sha256_lf(two))
        self.assertEqual(set(ev.module_hashes()), set(ev.IMPORTED))


class InputHandlingTest(unittest.TestCase):
    def test_agent_complete_without_operation_is_an_unseen_branch(self):
        extra = [{'kind': 'agent_complete', 'operation': None, 'span_id': None, 'output': 'x'}]
        row, _, unseen = analyze(build_run(TREE, CARRIER, extra=extra, score=SCORED))
        self.assertEqual(unseen['agent_complete_operation:None'], 1)
        self.assertEqual(row['integrity'], 'ok')

    def test_known_operation_on_a_missing_span_is_a_problem(self):
        extra = [{'kind': 'agent_complete', 'operation': 'consolidate', 'span_id': 'nowhere', 'output': 'x'}]
        row, _, _ = analyze(build_run(TREE, CARRIER, extra=extra))
        self.assertNotEqual(row['integrity'], 'ok')

    def test_an_empty_cmdb_id_is_kept_as_the_hint_name(self):
        run = build_run(TREE, {'c': {'abn': True, 'calls': CARRIER['c']['calls']}})
        node = run['graph']['children'][0]['children'][0]
        node['raw']['cmdb_id'], node['raw']['service_name'] = '', GT
        row, _, _ = analyze(run)
        self.assertEqual(row['I3'], False)

    def test_strict_hint_size_counts_names_in_lower_case(self):
        tree = ('r', 'frontendservice', [('a', 'Checkoutservice', []), ('b', 'checkoutservice', []), ('c', 'adservice', [])])
        selfs = {s: {'abn': True} for s in 'abc'}
        row, _, _ = analyze(build_run(tree, selfs))
        self.assertEqual((row['hint_list_size'], row['I3'], row['I3_strict']), (2, True, True))

    def test_runs_file_with_a_byte_order_mark_and_indented_comment(self):
        with tempfile.TemporaryDirectory() as tmp:
            listed = Path(tmp) / 'runs.txt'
            listed.write_bytes('﻿one--metric--s1\n  # note\ntwo--metric--s1\n'.encode('utf-8'))
            self.assertEqual(ev.selected_runs(listed), {'one--metric--s1', 'two--metric--s1'})
            self.assertIsNone(ev.selected_runs(None))


class NameEdgeTest(unittest.TestCase):
    def test_only_a_dash_continues_a_name(self):
        self.assertFalse(ev.match('checkout', 'checkout_svc'))
        self.assertFalse(ev.match('checkout_svc', 'checkout'))
        self.assertTrue(ev.match('checkout', 'checkout-svc'))

    def test_pod_hash_needs_five_characters_in_the_first_group(self):
        self.assertEqual(ev.base_of('x-service-abcd-abcd'), 'x-service-abcd-abcd')
        self.assertEqual(ev.base_of('cartservice-abcde-abcd'), 'cartservice')

    def test_top_label_equality_is_the_scorer_match(self):
        row, _, _ = analyze(build_run(TREE, CARRIER, {'r': 'checkoutservice-0'}, final=('checkoutservice', 'adservice')))
        self.assertEqual(row['I5'], 'same')


class SpanFlagEdgeTest(unittest.TestCase):
    def d1(self, calls, err=True):
        _, spans, _ = analyze(build_run(TREE, {'c': {'abn': True, 'err': err, 'calls': calls}}))
        return spans['c']

    def test_logs_of_mixed_sources_are_not_d1(self):
        for other in ('absent', 'repaired'):
            span = self.d1([metric_call(GT, table(GT)), log_call(GT), log_call(GT, source=other)])
            self.assertEqual((span['D1'], span['d1_log_source'], span['D1_empty_logs']), (False, 'mixed', False), other)

    def test_a_span_that_claims_no_error_logs_is_not_d1(self):
        span = self.d1([metric_call(GT, table(GT)), log_call(GT)], err=False)
        self.assertEqual((span['D1'], span['D1_empty_logs']), (False, False))

    def test_failed_alone_is_error_text(self):
        span = self.d1([metric_call(GT, table(GT)), log_call(GT, 'log_id,timestamp,cmdb_id,log_name,value\n1,2,c,x,request failed\n')])
        self.assertEqual((span['log_result_classes'], span['D1']), ('error_text', False))

    def test_fallback_prefix_must_match_in_full(self):
        def request(text):
            return request_event(1, 'a', 'self_state_verification', messages=[SYSTEM, {'role': 'user', 'content': text}])
        self.assertTrue(ev.is_fallback(request(FALLBACK)))
        self.assertFalse(ev.is_fallback(request('Based on all the logs, go on')))

    def test_lenient_reason_stops_at_an_underscore(self):
        row, _, _ = analyze(build_run(TREE, CARRIER, {'r': ('reason', 'currencyservice', 'checkoutservice_x')}))
        self.assertEqual(row['I2_lenient'], False)


class JoinEdgeTest(unittest.TestCase):
    PARAMS = {'service_name': GT, 'timestamp': TS}

    def result(self, name=LOGS):
        return {'kind': 'tool_result', 'name': name, 'params': self.PARAMS, 'response': EMPTY_LOG, 'source': 'author',
                'span_id': 'a'}

    def test_a_call_answers_one_result_only(self):
        events = [request_event(1, 'a', 'self_state_verification'), response_event(1, [(LOGS, self.PARAMS)]),
                  self.result(), self.result()]
        problems = []
        ev.join_tool_results(events, problems)
        self.assertEqual(len(problems), 1)
        self.assertIn('matches no tool call', problems[0])

    def test_each_identical_result_gets_its_own_budget(self):
        budget = {'kind': 'tool_result_budget', 'name': LOGS, 'params': self.PARAMS, 'delivered': None, 'span_id': 'a',
                  'applied': False}
        events = [request_event(1, 'a', 'self_state_verification'),
                  response_event(1, [(LOGS, self.PARAMS), (LOGS, self.PARAMS)]),
                  self.result(), dict(budget, tag=1), self.result(), dict(budget, tag=2)]
        problems = []
        results = ev.join_tool_results(events, problems)
        self.assertEqual(problems, [])
        self.assertEqual([r['budget']['tag'] for r in results], [1, 2])


class TableEdgeTest(unittest.TestCase):
    def test_funnel_without_determinable_runs_is_not_saturated(self):
        rows = [analyze(build_run(TREE_WITHOUT_GT, seed=SEED))[0]]
        table_ = {r['indicator']: r for r in ev.funnel(rows)}
        self.assertEqual(table_['I1']['saturated'], False)

    def test_feasibility_pool_for_later_stages_needs_i0(self):
        keys = ('condition', 'completed', 'I0', 'I1', 'I2', 'I3', 'case', 'gt_service')
        rows = [dict(zip(keys, ('metric', True) + values)) for values in
                [(False, 'NA', 'NA', False, 'c1', 'x'), (True, True, True, True, 'c1', 'x')]]
        table_ = {r['stage']: r for r in ev.feasibility(rows)}
        self.assertEqual((table_['I3']['lost_runs'], table_['I3']['kept_runs']), (0, 1))

    def test_case_comparison_reports_the_final_request_as_a_stage(self):
        a = build_run(TREE, CARRIER)
        b = build_run(TREE, CARRIER, hint=' another hint', condition='no_metric')
        prints = {r['run_id']: ev.fingerprint(r['events']) for r in (a, b)}
        row = ev.case_comparison([analyze(a)[0], analyze(b)[0]], prints)[0]
        self.assertEqual(row['first_request_divergence'], len(prints[a['run_id']]['operations']))
        self.assertEqual(row['divergence_stage'], 'final')

    def test_cell_joins_a_list_with_semicolons(self):
        self.assertEqual(ev.cell(['no_kpi', 'no_rows']), 'no_kpi;no_rows')

    def test_one_structure_row_per_trace(self):
        runs = [build_run(TREE, seed=SEED + i) for i in range(3)]
        self.assertEqual(len({r['trace_id'] for r in runs}), 1)
        self.assertEqual(len(ev.structure_rows(runs)), 1)

    def test_spans_of_one_depth_are_sorted_by_id(self):
        tree = ('r', 'frontendservice', [('z', 'cartservice', []), ('b', 'adservice', [])])
        with tempfile.TemporaryDirectory() as tmp:
            archive, manifest = write_package(tmp, [build_run(tree, {'b': {'abn': True}})])
            run_main(Path(tmp) / 'analysis', 'A', archive, manifest)
            lines = (Path(tmp) / 'analysis' / 'spans.csv').read_text(encoding='utf-8').splitlines()[1:]
            self.assertEqual([line.split(',')[4] for line in lines], ['r', 'b', 'z'])

    def test_hint_names_differing_in_case_count_once(self):
        tree = ('r', 'frontendservice', [('a', 'Checkoutservice', []), ('b', 'checkoutservice', [])])
        row, _, _ = analyze(build_run(tree, {'a': {'abn': True}, 'b': {'abn': True}}))
        self.assertEqual(row['hint_list_size'], 1)


class RealRunGateTest(unittest.TestCase):
    """Reads the two real S1 v2 results ZIPs; a missing ZIP fails the test unless EVIDENCE_LOSS_ALLOW_NO_ZIP=1."""
    GROUPS = [('A', HERE / 'runtime/kaggle-output-a-s1-v2/rclagent-smoke/rclagent-smoke-results.zip', HERE / 's1-v2/a/manifest.json'),
              ('B', HERE / 'runtime/kaggle-output-b-s1-v2/rclagent-smoke/rclagent-smoke-results.zip', HERE / 's1-v2/b/manifest.json')]

    def test_real_zips_have_a_consistent_event_shape(self):
        missing = [str(p) for _, z, m in self.GROUPS for p in (z, m) if not p.exists()]
        if missing:
            if os.environ.get('EVIDENCE_LOSS_ALLOW_NO_ZIP') == '1':
                print('WARNING: real-data gate skipped, files missing: ' + ', '.join(missing), file=sys.stderr)
                self.skipTest('real S1 v2 files missing and EVIDENCE_LOSS_ALLOW_NO_ZIP=1')
            self.fail('real S1 v2 files missing (set EVIDENCE_LOSS_ALLOW_NO_ZIP=1 to skip): ' + ', '.join(missing))
        raw = results = 0
        for _, archive, _ in self.GROUPS:
            with zipfile.ZipFile(archive) as zipped:
                names = zipped.namelist()
                results += sum(n.startswith('run/traces/') and n.endswith('/result.json') for n in names)
                for name in names:
                    if name.startswith('run/traces/') and name.endswith('/events.jsonl'):
                        raw += sum('"kind": "tool_result"' in line for line in zipped.read(name).decode('utf-8').splitlines())
        joined = finals = runs = compared = equivalent = 0
        for run in ev.iter_runs(self.GROUPS):
            runs += 1
            problems, spans, tool_results = ev.structural_problems(run)
            self.assertEqual(problems, [], run['run_id'])
            joined += len(tool_results)
            finals += final_request_count(run['events'])
            _, row, _, unseen = ev.analyze_run(run)
            self.assertNotEqual(row['hint_equivalent'], False, run['run_id'])
            equivalent += row['hint_equivalent'] is True
            self.assertEqual([k for k in unseen if k.startswith(('kind:', 'agent_complete_operation:', 'source:'))], [],
                             run['run_id'])
            if run['author_score']:
                self.assertEqual(row['score_check'], 'match', run['run_id'])
            if run['author_score'] and run['result'] and run['gt']:
                rank = ev.rank_of(run['gt'], run['result']['root_causes'])
                score = ev.author_score(run['author_score'])
                mrr = f'{(0.0 if rank < 0 else 1 / (rank + 1)):.4f}'
                self.assertEqual(((rank == 0), mrr), (score[0] == 1.0, score[1]), run['run_id'])
                compared += 1
        self.assertGreater(runs, 0)
        self.assertEqual(joined, raw)
        self.assertEqual(finals, results)
        self.assertEqual(compared, results)
        self.assertGreater(equivalent, 0)


class RealRunFixtureTest(unittest.TestCase):
    """One real run whose indicators a blind reader filled in by hand from the telemetry before any rule was run on it.
    The expected values are the reader's; the run is read from the real ZIP, which stays outside the repository.
    A missing ZIP fails the test unless EVIDENCE_LOSS_ALLOW_NO_ZIP=1."""
    ARCHIVE = HERE / 'runtime/kaggle-output-a-s1-v2/rclagent-smoke/rclagent-smoke-results.zip'
    MANIFEST = HERE / 's1-v2/a/manifest.json'
    RUN = '99f095aeb2571c7f2ee99885e8332c8a--metric_no_log--s20261026'

    def test_hand_checked_run_gets_the_hand_checked_indicators(self):
        missing = [str(p) for p in (self.ARCHIVE, self.MANIFEST) if not p.exists()]
        if missing:
            if os.environ.get('EVIDENCE_LOSS_ALLOW_NO_ZIP') == '1':
                print('WARNING: real-run fixture skipped, files missing: ' + ', '.join(missing), file=sys.stderr)
                self.skipTest('real S1 v2 files missing and EVIDENCE_LOSS_ALLOW_NO_ZIP=1')
            self.fail('real S1 v2 files missing (set EVIDENCE_LOSS_ALLOW_NO_ZIP=1 to skip): ' + ', '.join(missing))
        runs = list(ev.iter_runs([('A', self.ARCHIVE, self.MANIFEST)], {self.RUN}))
        self.assertEqual([r['run_id'] for r in runs], [self.RUN])
        spans, row, _, _ = ev.analyze_run(runs[0])
        expected = {'gt_service': 'currencyservice', 'completed': True, 'censored': False,
                    'I0': True, 'I1': True, 'I2': False, 'I3': True, 'I4': False, 'I5': 'same',
                    'root_class': 'other_service', 'rank': 1, 'R@3': True, 'MRR': '0.5000',
                    'hint_list_size': 2, 'first_loss_linear': 'S2', 'final_residual': 'reaches_final_input_not_rank1',
                    'final_residual_split': 'top1_equals_wrong_root_label', 'chain_weakened': True,
                    'hint_weakened': False, 'hit_without_evidence': False, 'integrity': 'ok', 'score_check': 'match'}
        for key, value in expected.items():
            self.assertEqual(row[key], value, key)
        self.assertEqual(sorted(row['table_key_prefixes']), ['checkoutservice', 'currencyservice'])
        root = [s for s in spans if s['is_root']]
        self.assertEqual([(s['cons_label'], s['cons_class']) for s in root], [('adservice', 'other_service')])
        self.assertEqual(sum(bool(s['carrier_abnormal']) for s in spans), 20)


if __name__ == '__main__':
    unittest.main()
