"""CPU tests for check-hash-seed-order.py on small ZIPs from the analyzer fixture writer; this Python predicts the order."""
import contextlib
import csv
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check = load('check_under_test', 'check-hash-seed-order.py')
fixtures = load('analyzer_fixtures', 'test-analyze-missing-source-results.py')
check.SEEDS = range(16)  # Each seed is one Python process; 16 still give order-sensitive sets.
SEED = fixtures.SEEDS[0]
SERVICES = ['cartservice', 'adservice', 'emailservice', 'paymentservice', 'currencyservice']
NAMES = ('match', 'other_seed', 'no_final', 'unparsed', 'order_only', 'early', 'one_service')
RUNS = {name: fixtures.make_run(name, 'no_metric', SEED) for name in NAMES}


def hints(lists, seed):
    return check.predict(sys.executable, lists)[seed]


def nodes(errors, metrics):
    return ([{'span_id': f'e{i}', 'service_name': s, 'evidence': '{"has_error_logs": true}'} for i, s in enumerate(errors)] +
            [{'span_id': f'm{i}', 'service_name': s, 'evidence': '{"is_abnormal": true}'} for i, s in enumerate(metrics)] +
            [{'span_id': 'n', 'service_name': 'frontendservice', 'evidence': '{"is_abnormal": false}'}])


def prompt(graph, hint):
    return (f'You are the ROOT AGENT.\n\nGlobal Evidence Graph ({len(graph)} span evidences collected):\n'
            f'{json.dumps(graph, ensure_ascii=False, indent=2)}\n{hint}\n\nGoal: identify the root-cause service.')


def run_events(answers, final=None, verdict='cartservice', number=1):
    """Self-state requests answered by `answers`, then a final synthesis request with user content `final`."""
    events = []
    for number, answer in enumerate(answers, number):
        events.append({'kind': 'request', 'number': number, 'phase': 'trace', 'operation': 'self_state_verification',
                       'payload': {'seed': SEED, 'messages': [{'role': 'user', 'content': 'check the span'}]}})
        body = {'choices': [{'message': {'content': answer, 'tool_calls': []}}]}
        events.append({'kind': 'response', 'number': number, 'status': 200, 'body': json.dumps(body)})
    if final is not None:
        events.append({'kind': 'request', 'number': len(answers) + 1, 'phase': 'trace', 'operation': None,
                       'payload': {'seed': SEED, 'messages': [{'role': 'system', 'content': 'rank'},
                                                              {'role': 'user', 'content': final}]}})
        body = {'choices': [{'message': {'content': None, 'tool_calls': [
            {'id': 'x', 'function': {'name': 'print_results', 'arguments': json.dumps({'root_causes': [verdict]})}}]}}]}
        events.append({'kind': 'response', 'number': len(answers) + 1, 'status': 200, 'body': json.dumps(body)})
    return events


class CheckHashSeedOrder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lists = [[[], SERVICES], [SERVICES[:2], SERVICES[2:]]]
        texts = check.predict(sys.executable, lists)
        cls.seed0 = texts[0]
        # A seed whose order differs from seed 0 for both lists stands in for a session under a random seed.
        cls.other = next(texts[s] for s in check.SEEDS if all(texts[s][i] != texts[0][i] for i in range(2)))
        cls.lists = lists

    def write(self, root, finals, version=None):
        archive, manifest = fixtures.write_session(root, [RUNS[n] for n in finals],
                                                   events={RUNS[n]['run_id']: finals[n] for n in finals})
        (archive.parent / 'environment-before.json').write_text(
            json.dumps({'python': version or sys.version}), encoding='utf-8')
        return archive, manifest

    def sessions(self, new_hint=None, version=None):
        graph, mixed = nodes([], SERVICES), nodes(*self.lists[1])
        new_hint = new_hint or self.seed0[0]
        new = {'match': run_events(['a'], prompt(graph, new_hint)),
               'other_seed': run_events(['a'], prompt(mixed, self.other[1])),
               'no_final': run_events(['a']),
               'unparsed': run_events(['a'], 'no graph here'),
               'order_only': run_events(['a', 'b'], prompt(mixed, self.seed0[1])),
               'early': run_events(['a', 'b'], prompt(mixed, self.seed0[1])),
               'one_service': run_events(['a'], prompt(nodes([], ['adservice']),
                                                       '\n⚡ Services with metric anomalies only: adservice'))}
        old = dict(new, order_only=run_events(['a', 'b'], prompt(mixed, self.other[1]), 'adservice'),
                   early=run_events(['a', 'c'], prompt(mixed, self.other[1]), 'adservice'))
        return self.write(self.tmp / 'new', new, version), self.write(self.tmp / 'old', old)

    def run_check(self, sessions):
        (new_zip, new_manifest), (old_zip, old_manifest) = sessions
        out = self.tmp / 'out'
        argv, sys.argv = sys.argv, ['check-hash-seed-order.py', str(out), sys.executable, 'A', str(new_zip),
                                    str(new_manifest), str(old_zip), str(old_manifest)]
        code = 0
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                check.main()
        except SystemExit as exc:
            code = exc.code
        finally:
            sys.argv = argv
        with (out / 'runs.csv').open(encoding='utf-8', newline='') as handle:
            runs = {(r['side'], r['run_id']): r for r in csv.DictReader(handle)}
        with (out / 'pairs.csv').open(encoding='utf-8', newline='') as handle:
            pairs = {r['trace_id']: r for r in csv.DictReader(handle)}
        return code, runs, pairs, json.loads((out / 'summary.json').read_text(encoding='utf-8'))

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def test_hint_classes(self):
        _, runs, _, summary = self.run_check(self.sessions())
        hint = {name: runs[('new', RUNS[name]['run_id'])]['hint'] for name in NAMES}
        self.assertEqual(hint, {'match': 'match', 'other_seed': 'other_seed', 'no_final': 'no_final_prompt',
                                'unparsed': 'unparsed', 'order_only': 'match', 'early': 'match', 'one_service': 'match'})
        self.assertEqual(runs[('new', RUNS['match']['run_id'])]['order_sensitive'], 'True')
        self.assertEqual(runs[('new', RUNS['one_service']['run_id'])]['order_sensitive'], 'False')
        self.assertEqual(runs[('new', RUNS['match']['run_id'])]['services'], '5')
        self.assertEqual(summary['new']['hint'], {'match': 4, 'other_seed': 1, 'no_final_prompt': 1, 'unparsed': 1})

    def test_seed_zero_is_pinned_to_a_known_order(self):
        # PYTHONHASHSEED=0 gives this order on Python 3.12 and 3.13; a predictor that ignored or shifted the seed would not.
        self.assertEqual(check.predict(sys.executable, [[[], SERVICES]])[0][0],
                         '\n⚡ Services with metric anomalies only: '
                         'currencyservice, adservice, cartservice, paymentservice, emailservice')

    def test_other_seed_alone_fails_the_verdict(self):
        runs = {'other_seed': run_events(['a'], prompt(nodes(*self.lists[1]), self.other[1])),
                'match': run_events(['a'], prompt(nodes([], SERVICES), self.seed0[0]))}
        code, _, _, summary = self.run_check((self.write(self.tmp / 'n5', runs), self.write(self.tmp / 'o5', runs)))
        self.assertEqual((code, summary['verified'], summary['new']['hint']), (1, False, {'match': 1, 'other_seed': 1}))

    def test_unanswered_final_request_is_not_order_only(self):
        mixed = nodes(*self.lists[1])
        answered = run_events(['a', 'b'], prompt(mixed, self.seed0[1]))
        unanswered = run_events(['a', 'b'], prompt(mixed, self.other[1]))[:-1]
        _, _, pairs, _ = self.run_check((self.write(self.tmp / 'n6', {'order_only': answered}),
                                         self.write(self.tmp / 'o6', {'order_only': unanswered})))
        self.assertEqual(pairs[RUNS['order_only']['trace_id']]['explained'], 'unexplained')

    def test_final_request_with_another_system_message_is_not_order_only(self):
        mixed = nodes(*self.lists[1])
        other = run_events(['a', 'b'], prompt(mixed, self.other[1]), 'adservice')
        other[-2]['payload']['messages'][0]['content'] = 'rank differently'
        _, _, pairs, _ = self.run_check((self.write(self.tmp / 'n7', {'order_only': run_events(['a', 'b'], prompt(mixed, self.seed0[1]))}),
                                         self.write(self.tmp / 'o7', {'order_only': other})))
        self.assertEqual(pairs[RUNS['order_only']['trace_id']]['explained'], 'unexplained')

    def test_same_order_with_different_output_is_listed(self):
        mixed = nodes(*self.lists[1])
        new = {'early': run_events(['a', 'b'], prompt(mixed, self.seed0[1]))}
        old = {'early': run_events(['a', 'c'], prompt(mixed, self.seed0[1]))}
        _, _, _, summary = self.run_check((self.write(self.tmp / 'n8', new), self.write(self.tmp / 'o8', old)))
        self.assertEqual(summary['same_order_different_output'], [f"A {RUNS['early']['trace_id']} no_metric {SEED}"])

    def test_run_on_one_side_only_is_unexplained(self):
        match = run_events(['a'], prompt(nodes([], SERVICES), self.seed0[0]))
        _, _, pairs, _ = self.run_check((self.write(self.tmp / 'n9', {'match': match, 'early': match}),
                                         self.write(self.tmp / 'o9', {'match': match})))
        self.assertEqual((pairs[RUNS['early']['trace_id']]['present'], pairs[RUNS['early']['trace_id']]['explained']),
                         ('only_new', 'unexplained'))

    def test_a_reordered_hint_no_seed_gives_is_unreachable(self):
        wrong = '\n⚡ Services with metric anomalies only: ' + ', '.join(SERVICES) + ', extraservice'
        _, runs, _, summary = self.run_check(self.sessions(new_hint=wrong))
        self.assertEqual(runs[('new', RUNS['match']['run_id'])]['hint'], 'unreachable')
        self.assertFalse(summary['verified'])

    def test_pairs(self):
        _, _, pairs, summary = self.run_check(self.sessions())
        explained = {name: pairs[RUNS[name]['trace_id']]['explained'] for name in NAMES}
        # other_seed has the same outputs on both sides, so it is identical; early differs before the final request.
        self.assertEqual(explained, {'match': 'identical', 'other_seed': 'identical', 'no_final': 'identical',
                                     'unparsed': 'identical', 'order_only': 'order_only', 'early': 'unexplained',
                                     'one_service': 'identical'})
        self.assertEqual(pairs[RUNS['order_only']['trace_id']]['hint_order_equal'], 'False')
        self.assertEqual(summary['unexplained'], [f"A {RUNS['early']['trace_id']} no_metric {SEED}"])

    def test_final_prompt_that_differs_outside_the_hint_is_unexplained(self):
        archive, manifest = self.write(self.tmp / 'old2', {'order_only': run_events(
            ['a', 'b'], prompt(nodes(*self.lists[1]), self.other[1]).replace('ROOT AGENT', 'root agent'), 'adservice')})
        mixed = run_events(['a', 'b'], prompt(nodes(*self.lists[1]), self.seed0[1]))
        _, _, pairs, _ = self.run_check((self.write(self.tmp / 'new2', {'order_only': mixed}), (archive, manifest)))
        self.assertEqual(pairs[RUNS['order_only']['trace_id']]['explained'], 'unexplained')

    def test_verdict(self):
        code, _, _, summary = self.run_check(self.sessions())
        self.assertEqual((code, summary['verified']), (1, False))  # other_seed and unparsed on the new side
        clean = {n: e for n, e in {'match': run_events(['a'], prompt(nodes([], SERVICES), self.seed0[0])),
                                   'no_final': run_events(['a'])}.items()}
        sessions = (self.write(self.tmp / 'n3', clean), self.write(self.tmp / 'o3', clean))
        code, _, _, summary = self.run_check(sessions)
        self.assertEqual((code, summary['verified'], summary['new']['order_sensitive_match']), (0, True, 1))

    def test_verdict_needs_an_order_sensitive_match(self):
        single = {'one_service': run_events(['a'], prompt(nodes([], ['adservice']),
                                                           '\n⚡ Services with metric anomalies only: adservice'))}
        code, _, _, summary = self.run_check((self.write(self.tmp / 'n4', single), self.write(self.tmp / 'o4', single)))
        self.assertEqual((code, summary['verified']), (1, False))

    def test_python_version_must_match_kaggle(self):
        (new_zip, new_manifest), (old_zip, old_manifest) = self.sessions(version='2.7.18 (default)')
        argv, sys.argv = sys.argv, ['check-hash-seed-order.py', str(self.tmp / 'out'), sys.executable, 'A',
                                    str(new_zip), str(new_manifest), str(old_zip), str(old_manifest)]
        try:
            with self.assertRaises(SystemExit) as raised:
                check.main()
        finally:
            sys.argv = argv
        self.assertIn('ran Python 2.7.18', str(raised.exception))

    def test_other_minor_python_version_is_refused(self):
        # Same major version, other minor: string hashing and set layout may differ.
        other_minor = f'{sys.version_info[0]}.{sys.version_info[1] + 1}.0'
        (new_zip, new_manifest), (old_zip, old_manifest) = self.sessions(version=other_minor)
        argv, sys.argv = sys.argv, ['check-hash-seed-order.py', str(self.tmp / 'out'), sys.executable, 'A',
                                    str(new_zip), str(new_manifest), str(old_zip), str(old_manifest)]
        try:
            with self.assertRaises(SystemExit) as raised:
                check.main()
        finally:
            sys.argv = argv
        self.assertIn(f'ran Python {other_minor}', str(raised.exception))

    def test_predictions_follow_the_seed(self):
        lists = [[[], SERVICES]]
        texts = check.predict(sys.executable, lists)
        self.assertEqual(texts[0], check.predict(sys.executable, lists)[0])
        self.assertGreater(len({t[0] for t in texts.values()}), 1)

    def test_final_request_index_and_responses_before_it(self):
        events = run_events(['a', 'b'], prompt(nodes([], SERVICES), self.seed0[0]))
        index, answered, event = check.final_request(events)
        self.assertEqual((index, answered, event['operation']), (3, 2, None))
        self.assertEqual(check.final_request(run_events(['a'])), (None, None, None))

    def test_prompt_rebuild_follows_the_author_loop(self):
        graph = nodes(['cartservice', 'cartservice'], ['adservice']) + [
            {'span_id': 'x', 'service_name': 'emailservice', 'evidence': '{"has_error_logs": true, "is_abnormal": true}'},
            {'span_id': 'u', 'service_name': 'upperservice', 'evidence': '{"has_error_logs": True}'},
            {'span_id': 'f', 'service_name': 'falseservice', 'evidence': '{"has_error_logs": false, "is_abnormal": true}'},
            {'span_id': 'w', 'service_name': 'wordservice', 'evidence': 'has_error_logs, "is_abnormal": True'},
            {'span_id': 'y', 'service_name': 'skipped', 'evidence': {'not': 'a string'}}]
        errors, metrics, hint, rest = check.parse_prompt(prompt(graph, 'HINT'))
        self.assertEqual((errors, metrics, hint), (['cartservice', 'cartservice', 'emailservice', 'upperservice'],
                                                   ['adservice', 'falseservice', 'wordservice'], 'HINT'))
        self.assertEqual(rest, prompt(graph, ''))

    def test_last_message_with_the_graph_is_parsed(self):
        events = run_events(['a'], prompt(nodes([], SERVICES), self.seed0[0]))
        events[-2]['payload']['messages'].insert(0, {'role': 'user', 'content': prompt(nodes([], ['adservice']), 'OLD')})
        final = check.final_prompt(events)
        self.assertEqual(final['parsed'][2], self.seed0[0])
        # Only the parsed message loses its hint; the earlier one is compared as sent.
        self.assertEqual([m['content'] for m in final['final_messages']],
                         [prompt(nodes([], ['adservice']), 'OLD'), 'rank', prompt(nodes([], SERVICES), '')])

    def test_usage_is_checked(self):
        argv, sys.argv = sys.argv, ['check-hash-seed-order.py', 'out', sys.executable, 'A', 'x']
        try:
            with self.assertRaises(SystemExit):
                check.main()
        finally:
            sys.argv = argv


if __name__ == '__main__':
    unittest.main()
