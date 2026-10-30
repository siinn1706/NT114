"""CPU tests for analyze-missing-source-results.py: the retry chain checked in log order, the binding of a results
ZIP to its bundle and manifest, duplicate and missing runs, unscored or unfinished work, and the recorded SHA256.
Every fixture is a small ZIP written into a temporary folder; no model and no Kaggle output is read."""
import contextlib
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SCRIPT = HERE / 'analyze-missing-source-results.py'


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analyzer = load('analyzer_under_test', 'analyze-missing-source-results.py')
worker = load('worker_analyzer_test', 'smoke-worker.py')
SEEDS = (20261026, 20261027, 20261028)
SOURCES = {'metric': {'logs': 'author', 'metric': 'repaired'}, 'no_metric': {'logs': 'author', 'metric': 'absent'},
           'metric_no_log': {'logs': 'absent', 'metric': 'repaired'}}
BUNDLE = 'b' * 64
SCORE = 'R@1 : 1.0\nR@3 : 1.0\nMRR : 1.0\n'
BUDGET = 'Model request budget exhausted (including retries)'


def make_run(case, condition, seed):
    trace = hashlib.md5(case.encode()).hexdigest()
    return {'run_id': f'{trace}--{condition}--s{seed}', 'case': case, 'trace_id': trace, 'condition': condition,
            'seed': seed, **SOURCES[condition]}


def matrix(cases=('case_a', 'case_b'), conditions=tuple(SOURCES), seeds=SEEDS):
    return [make_run(c, k, s) for c in cases for k in conditions for s in seeds]


def request(number, seed, attempt=0, retry_of=None):
    return {'kind': 'request', 'number': number, 'phase': 'trace', 'payload': {'seed': seed},
            'attempt': attempt, 'retry_of': retry_of}


def retry(number, next_attempt, next_seed):
    return {'kind': 'malformed_tool_call_retry', 'number': number, 'next_attempt': next_attempt,
            'next_seed': next_seed, 'reason': 'Tool call text outside structured tool_calls'}


def clean_events(run):
    return [request(1, run['seed']), {'kind': 'response', 'number': 1, 'status': 200},
            {'kind': 'tool_result', 'name': 'search_logs', 'source': run['logs']}, request(2, run['seed'])]


def write_session(root, runs, events=None, scores=None, states=None, status='passed', progress_bundle=BUNDLE,
                  sidecar=BUNDLE, extra_progress=()):
    """A results ZIP with its .sha256, next to a bundle folder holding the manifest and the bundle's .sha256."""
    root = Path(root)
    events, scores, states = events or {}, scores or {}, states or {}
    bundle = root / 'bundle'
    bundle.mkdir(parents=True, exist_ok=True)
    manifest = bundle / 'manifest.json'
    manifest.write_text(json.dumps({'runs': runs}), encoding='utf-8')
    if sidecar is not None:
        (bundle / 'rclagent-kaggle-bundle.zip.sha256').write_text(f'{sidecar}  rclagent-kaggle-bundle.zip\n')
    progress = {}
    for run in runs:
        state = states.get(run['run_id'], {'status': 'passed', 'reason': '', 'attempts': [{}]})
        if state is not None:
            progress[run['run_id']] = state
    for rid in extra_progress:
        progress[rid] = {'status': 'passed', 'attempts': [{}]}
    archive = root / 'out' / 'rclagent-smoke-results.zip'
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr('run/progress.json', json.dumps({'bundle_sha256': progress_bundle, 'traces': progress}))
        if status is not None:
            zipped.writestr('run/status.json', json.dumps({'status': status, 'stage': 'F', 'error': None}))
        for run in runs:
            rid = run['run_id']
            if rid not in progress:
                continue
            lines = [e if isinstance(e, str) else json.dumps(e) for e in events.get(rid, clean_events(run))]
            zipped.writestr(f'run/traces/{rid}/events.jsonl', '\n'.join(lines) + '\n')
            zipped.writestr(f'run/traces/{rid}/result.json', json.dumps({'root_causes': ['checkoutservice']}))
            if progress[rid]['status'] == 'passed':
                zipped.writestr(f'run/scoring/{rid}/author-score.txt', scores.get(rid, SCORE))
    archive.with_name(archive.name + '.sha256').write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name + '\n')
    return archive, manifest


def analyze(out_dir, *paths):
    argv = sys.argv
    sys.argv = ['analyze-missing-source-results.py', str(out_dir), *map(str, paths)]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            analyzer.main()
    finally:
        sys.argv = argv
    return json.loads((Path(out_dir) / 'summary.json').read_text(encoding='utf-8'))


class RetryChain(unittest.TestCase):
    def integrity(self, events):
        run = make_run('case_a', 'metric', SEEDS[0])
        with tempfile.TemporaryDirectory() as tmp:
            [row] = analyzer.load(*write_session(tmp, [run], events={run['run_id']: events}))
        return row

    def seed(self, first, attempt):
        return worker.retry_seed(SEEDS[0], first, attempt)

    def test_final_retry_before_budget_stop_is_valid(self):
        row = self.integrity([request(159, SEEDS[0]), retry(159, 1, self.seed(159, 1)),
                              request(160, self.seed(159, 1), 1, 159), retry(160, 2, self.seed(159, 2)),
                              {'kind': 'fatal', 'reason': BUDGET}])
        self.assertEqual(row['integrity'], 'ok')
        self.assertEqual(row['retries'], 2)

    def test_final_retry_before_deadline_stop_is_valid(self):
        row = self.integrity([request(40, SEEDS[0]), retry(40, 1, self.seed(40, 1)),
                              {'kind': 'fatal', 'reason': '30-minute RCLAgent deadline exceeded'}])
        self.assertEqual(row['integrity'], 'ok')

    def test_final_retry_before_another_stop_is_a_problem(self):
        row = self.integrity([request(159, SEEDS[0]), retry(159, 1, self.seed(159, 1)),
                              request(160, self.seed(159, 1), 1, 159), retry(160, 2, self.seed(159, 2)),
                              {'kind': 'fatal', 'reason': 'Invalid structured response: bad call'}])
        self.assertNotEqual(row['integrity'], 'ok')

    def test_retry_of_must_name_the_first_request(self):
        wrong = worker.retry_seed(SEEDS[0], 99, 1)
        row = self.integrity([request(10, SEEDS[0]), retry(10, 1, wrong), request(11, wrong, 1, 99)])
        self.assertNotEqual(row['integrity'], 'ok')

    def test_attempts_cannot_skip(self):
        row = self.integrity([request(10, SEEDS[0]), retry(10, 2, self.seed(10, 2)),
                              request(11, self.seed(10, 2), 2, 10)])
        self.assertNotEqual(row['integrity'], 'ok')

    def test_retry_event_seed_must_match_the_derivation(self):
        row = self.integrity([request(10, SEEDS[0]), retry(10, 1, 12345), request(11, self.seed(10, 1), 1, 10)])
        self.assertNotEqual(row['integrity'], 'ok')

    def test_transport_retry_restarts_the_chain(self):
        row = self.integrity([request(10, SEEDS[0]), retry(10, 1, self.seed(10, 1)),
                              request(11, self.seed(10, 1), 1, 10),
                              {'kind': 'response', 'number': 11, 'status': 503}, request(12, SEEDS[0])])
        self.assertEqual(row['integrity'], 'ok')

    def test_unparseable_line_is_an_integrity_problem(self):
        run = make_run('case_a', 'metric', SEEDS[0])
        lines = [json.dumps(e) for e in clean_events(run)] + ['{"kind": "requ']
        with tempfile.TemporaryDirectory() as tmp:
            [row] = analyzer.load(*write_session(tmp, [run], events={run['run_id']: lines}))
        self.assertIn('unparseable events line 5', row['integrity'])
        self.assertEqual(row['requests'], 2)


class Binding(unittest.TestCase):
    def test_duplicate_runs_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            pair = write_session(tmp, matrix())
            with self.assertRaises(SystemExit):
                analyze(Path(tmp) / 'analysis', *pair, *pair)

    def test_results_from_another_bundle_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                analyzer.load(*write_session(tmp, matrix(), progress_bundle='c' * 64))

    def test_missing_bundle_checksum_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                analyzer.load(*write_session(tmp, matrix(), sidecar=None))

    def test_runs_outside_the_manifest_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as raised:
                analyzer.load(*write_session(tmp, matrix(), extra_progress=['ffff--metric--s1']))
        self.assertIn('ffff--metric--s1', str(raised.exception))

    def test_tampered_zip_is_refused_even_without_asserts(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive, manifest = write_session(tmp, matrix())
            with archive.open('ab') as handle:
                handle.write(b'tampered')
            with self.assertRaises(SystemExit):
                analyzer.load(archive, manifest)
            out = Path(tmp) / 'optimized'
            done = subprocess.run([sys.executable, '-B', '-O', str(SCRIPT), str(out), str(archive), str(manifest)],
                                  capture_output=True, text=True)
            self.assertNotEqual(done.returncode, 0)
            self.assertFalse((out / 'summary.json').exists())


class Completeness(unittest.TestCase):
    def test_clean_design_is_final_and_evaluable(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = analyze(Path(tmp) / 'analysis', *write_session(tmp, matrix()))
        self.assertEqual(summary['integrity_problems'], [])
        self.assertFalse(summary['provisional'])
        self.assertEqual(summary['unscored_passed'], [])
        for comparison in summary['screening'].values():
            self.assertTrue(comparison['evaluable'])
            self.assertEqual(comparison['missing_pairs'], [])
            self.assertIs(comparison['opens_direction'], False)

    def test_missing_condition_is_not_evaluable(self):
        runs = matrix(conditions=('metric', 'metric_no_log'))
        with tempfile.TemporaryDirectory() as tmp:
            summary = analyze(Path(tmp) / 'analysis', *write_session(tmp, runs))
        removed = summary['screening']['metric_removed']
        self.assertFalse(removed['evaluable'])
        self.assertIsNone(removed['opens_direction'])
        self.assertEqual(len(removed['missing_pairs']), 6)
        self.assertTrue(summary['screening']['logs_removed']['evaluable'])

    def test_unscored_pending_and_failed_session_are_reported(self):
        runs = matrix()
        unscored, pending = runs[0]['run_id'], runs[1]['run_id']
        with tempfile.TemporaryDirectory() as tmp:
            pair = write_session(tmp, runs, status='failed', states={pending: None},
                                 scores={unscored: 'Traceback (most recent call last):\nKeyError: 0\n'})
            summary = analyze(Path(tmp) / 'analysis', *pair)
        self.assertEqual(summary['unscored_passed'], [unscored])
        self.assertTrue(summary['provisional'])
        self.assertEqual(summary['status']['pending'], 1)
        self.assertEqual([s['status'] for s in summary['sessions']], ['failed'])


if __name__ == '__main__':
    unittest.main()
