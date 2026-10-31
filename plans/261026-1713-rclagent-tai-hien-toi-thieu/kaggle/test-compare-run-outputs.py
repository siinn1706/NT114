"""CPU tests for compare-run-outputs.py on small ZIPs written by the analyzer tests' fixture writer, through load()."""
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


compare = load('compare_under_test', 'compare-run-outputs.py')
fixtures = load('analyzer_fixtures', 'test-analyze-missing-source-results.py')
make_run, SEEDS = fixtures.make_run, fixtures.SEEDS
CAP = "RuntimeError('trace failed: Per-span tool round budget exceeded (4); no further tool executed')"
TOOL = ('search_logs', '{"service_name": "checkoutservice", "timestamp": "1"}')


def conversation(seed, steps, tag, prompt='find the root cause'):
    """Events of one run. A step is (content, tool call or None, span, operation); `tag` makes the random ids differ."""
    events, history = [], []
    for number, (content, tool, span, operation) in enumerate(steps, 1):
        messages = [{'role': 'user', 'content': prompt}] + history
        events.append({'kind': 'request', 'number': number, 'phase': 'trace', 'span_id': span, 'operation': operation,
                       'attempt': 0, 'retry_of': None, 'payload': {'seed': seed, 'messages': messages}})
        calls = [{'id': f'chatcmpl-tool-{tag}{number}', 'type': 'function',
                  'function': {'name': tool[0], 'arguments': tool[1]}}] if tool else []
        message = {'role': 'assistant', 'content': content, 'tool_calls': calls}
        body = {'id': f'chatcmpl-{tag}{number}', 'created': 1000 + len(tag) * number, 'usage': {'total_tokens': number * len(tag)},
                'choices': [{'index': 0, 'message': message}]}
        events.append({'kind': 'response', 'number': number, 'status': 200, 'body': json.dumps(body)})
        history.append(message)
        if tool:
            history.append({'role': 'tool', 'tool_call_id': f'chatcmpl-tool-{tag}{number}', 'content': 'no rows'})
    return events


def step(content, tool=None, span='s0', operation='self_state_verification'):
    return content, tool, span, operation


BASE = [step('look', TOOL), step('look again', TOOL), step('{"root_causes": ["checkoutservice"]}', None, 's0', 'final')]
RUNS = {name: make_run(name, 'no_metric', SEEDS[0]) for name in
        ('identical', 'ids_only', 'final_only', 'early', 'capped_prefix', 'one_side', 'no_output', 'side2', 'short_diverged',
          'long_diverged', 'input_differs', 'prompt_only')}


def session(root, runs, events, states=None):
    return fixtures.write_session(root, [RUNS[n] for n in runs],
                                  events={RUNS[n]['run_id']: events[n] for n in runs}, states=states)


class CompareRunOutputs(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp, seed = Path(tmp.name), SEEDS[0]
        early = [BASE[0], step('look elsewhere', ('search_logs', '{"service_name": "other", "timestamp": "1"}'), 's1',
                               'consolidate'), BASE[2]]
        left = {'identical': conversation(seed, BASE, 'a'), 'ids_only': conversation(seed, BASE, 'a'),
                'final_only': conversation(seed, BASE, 'a'), 'early': conversation(seed, BASE, 'a'),
                'capped_prefix': conversation(seed, BASE[:2], 'a'), 'one_side': conversation(seed, BASE, 'a'),
                'no_output': conversation(seed, [], 'a'), 'side2': conversation(seed, BASE, 'a'),
                'short_diverged': conversation(seed, [BASE[0], early[1]], 'a'),
                'long_diverged': conversation(seed, BASE, 'a'),
                'input_differs': conversation(seed, BASE, 'a'), 'prompt_only': conversation(seed, BASE, 'a')}
        right = {'identical': conversation(seed, BASE, 'a'), 'ids_only': conversation(seed, BASE, 'bbbb'),
                 'final_only': conversation(seed, BASE[:2] + [step('a different verdict', None, 's0', 'final')], 'a'),
                 'early': conversation(seed, early, 'a'), 'capped_prefix': conversation(seed, BASE, 'a'),
                 'no_output': conversation(seed, BASE, 'a'), 'side2': conversation(seed, BASE[:2], 'a'),
                 'short_diverged': conversation(seed, BASE, 'a'),
                 'long_diverged': conversation(seed, [BASE[0], early[1]], 'a'),
                 'input_differs': conversation(seed, [step('look differently', TOOL)] + BASE[1:], 'a', 'other task'),
                 'prompt_only': conversation(seed, BASE, 'a', 'the root cause, find it')}
        capped = {RUNS['capped_prefix']['run_id']: {'status': 'failed', 'reason': CAP, 'attempts': [{}]}}
        zip1, manifest1 = session(self.tmp / 'one', list(left), left, capped)
        zip2, manifest2 = session(self.tmp / 'two', list(right), right)
        self.out = self.tmp / 'out'
        argv, sys.argv = sys.argv, ['compare-run-outputs.py', str(self.out), 'A', 'r2', str(zip1), str(manifest1),
                                    's1', str(zip2), str(manifest2)]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                compare.main()
        finally:
            sys.argv = argv
        with (self.out / 'pairs.csv').open(encoding='utf-8', newline='') as handle:
            self.rows = {r['trace_id']: r for r in csv.DictReader(handle)}
        self.summary = json.loads((self.out / 'summary.json').read_text(encoding='utf-8'))

    def row(self, name):
        return self.rows[RUNS[name]['trace_id']]

    def test_identical_and_random_ids_only_are_identical(self):
        for name in ('identical', 'ids_only'):
            self.assertEqual(self.row(name)['match'], 'identical', name)
            self.assertEqual(self.row(name)['first_request_divergence'], '', name)
            self.assertEqual(self.row(name)['scores_equal'], 'True', name)

    def test_final_response_only(self):
        row = self.row('final_only')
        self.assertEqual((row['match'], row['first_divergence'], row['divergence_operation']), ('final_response_only', '3', 'final'))

    def test_early_divergence_names_index_span_and_input(self):
        row = self.row('early')
        self.assertEqual((row['match'], row['first_divergence'], row['divergence_span'], row['divergence_operation']),
                         ('diverged', '2', 's0', 'self_state_verification'))
        # Request 1 is the same; request 3 differs because request 2's answer is in its history; the response differs first.
        self.assertEqual((row['first_request_divergence'], row['request_before_response']), ('3', 'False'))

    def test_capped_run_that_is_a_strict_prefix(self):
        row = self.row('capped_prefix')
        self.assertEqual((row['match'], row['capped'], row['side1_strict_prefix'], row['first_divergence']),
                         ('strict_prefix', 'True', 'True', ''))
        self.assertEqual((row['responses_1'], row['responses_2'], row['status_1'], row['status_2']), ('2', '3', 'failed', 'passed'))

    def test_side2_ends_first(self):
        row = self.row('side2')
        self.assertEqual((row['match'], row['side1_strict_prefix'], row['first_divergence'], row['capped']),
                         ('side2_prefix', 'False', '', 'False'))
        self.assertEqual((row['responses_1'], row['responses_2']), ('3', '2'))

    def test_shorter_run_that_diverged_is_not_a_prefix(self):
        row = self.row('short_diverged')
        self.assertEqual((row['match'], row['side1_strict_prefix'], row['first_divergence']), ('diverged', 'False', '2'))
        self.assertEqual((row['responses_1'], row['responses_2']), ('2', '3'))

    def test_longer_run_that_diverged_is_not_a_side2_prefix(self):
        row = self.row('long_diverged')
        self.assertEqual((row['match'], row['first_divergence'], row['responses_1'], row['responses_2']), ('diverged', '2', '3', '2'))

    def test_run_without_responses(self):
        row = self.row('no_output')
        self.assertEqual((row['match'], row['responses_1'], row['responses_2'], row['first_divergence']), ('no_output', '0', '3', ''))

    def test_different_input_at_the_first_difference_counts_as_input(self):
        # Request 1 and response 1 differ at the same position: the model was given different input.
        row = self.row('input_differs')
        self.assertEqual((row['match'], row['first_divergence'], row['first_request_divergence'], row['request_before_response']),
                         ('diverged', '1', '1', 'True'))

    def test_different_input_with_the_same_answers_is_identical(self):
        row = self.row('prompt_only')
        self.assertEqual((row['match'], row['first_divergence'], row['first_request_divergence'], row['request_before_response']),
                         ('identical', '', '1', 'True'))

    def test_run_missing_on_one_side(self):
        row = self.row('one_side')
        self.assertEqual((row['present'], row['match']), ('only_r2', ''))

    def test_summary_counts(self):
        everything = self.summary['all']
        self.assertEqual((everything['runs'], everything['paired'], everything['only_one_side']), (12, 11, {'only_r2': 1}))
        self.assertEqual(everything['non_capped']['match'],
                         {'identical': 3, 'final_response_only': 1, 'diverged': 4, 'no_output': 1, 'side2_prefix': 1})
        self.assertEqual(everything['capped']['match'], {'strict_prefix': 1})
        # The capped run failed (scores 0) while its side-2 run passed (1.0); the other ten pairs score alike.
        self.assertEqual(everything['all']['scores_equal'], 10)
        self.assertEqual(self.summary['A'], everything)

    def test_usage_and_group_size_are_checked(self):
        argv, sys.argv = sys.argv, ['compare-run-outputs.py', str(self.out), 'A', 'r2', 'x']
        try:
            with self.assertRaises(SystemExit):
                compare.main()
        finally:
            sys.argv = argv


if __name__ == '__main__':
    unittest.main()
