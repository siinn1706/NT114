"""Synthetic checks of the telemetry-gap go/no-go rule; no model output is read."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('decide_gap', HERE / 'decide-telemetry-gap-outcomes.py')
decide = importlib.util.module_from_spec(spec)
spec.loader.exec_module(decide)

QUERIES = [f'q{i:02d}' for i in range(25)]
STRATUM = {q: 'none' if i < 12 else 'covered' for i, q in enumerate(QUERIES)}
GT = {q: 'paymentservice' for q in QUERIES}


def kpi(ranker_hit):
    """Window KPI whose ranker puts paymentservice (hit) or adservice (miss) first."""
    top, other = ('paymentservice', 'adservice') if ranker_hit else ('adservice', 'paymentservice')
    side = lambda p95: {'spans': 10, 'p95': p95, 'median': 1.0}
    return {'services': {top: {'in_trace': True, 'traces': 3, 'server': side(5.0), 'client': None},
                         other: {'in_trace': True, 'traces': 3, 'server': side(2.0), 'client': None}}}


def rows_for(hits, cart=()):
    """hits: condition -> set of queries with R@1 = 1; every run passed and scored."""
    rows = []
    for c in decide.CONDITIONS:
        for q in QUERIES:
            hit = q in hits.get(c, set())
            top1 = 'cartservice' if (c, q) in cart else ('paymentservice' if hit else 'adservice')
            rows.append({'run_id': f'{c}-{q}', 'trace_id': q, 'condition': c, 'site': 'kaggle',
                         'stratum': STRATUM[q], 'gt': GT[q], 'status': 'passed', 'scored': True,
                         'R@1': 1.0 if hit else 0.0, 'MRR': 1.0 if hit else 0.25, 'top1': top1,
                         'requests': 5, 'prompt_max': 3000, 'prompt_median': 2000,
                         'cart_top1': top1 == 'cartservice', 'queried_gt_metric': False,
                         'top1_outside_trace': False})
    return rows


DEV = {'queries': [{'trace_id': q, 'stratum': STRATUM[q], 'gt': GT[q]} for q in QUERIES]}
BASE = set(QUERIES[:8])


def grid(a_extra, a_lost=(), ranker_hits=5, **more):
    a = (BASE | set(a_extra)) - set(a_lost)
    hits = {c: set(BASE) for c in decide.CONDITIONS}
    hits['a_nometric'] = a
    hits.update(more)
    kpis = {q: kpi(i < ranker_hits) for i, q in enumerate(QUERIES)}
    return hits, kpis


class Verdict(unittest.TestCase):
    def verdict(self, hits, kpis, cart=()):
        return decide.decide(rows_for(hits, cart), DEV, kpis)

    def test_method_paper_when_every_clause_holds(self):
        hits, kpis = grid(QUERIES[8:14])
        report = self.verdict(hits, kpis)
        self.assertEqual(report['outcomes']['O1']['wins'], 6)
        self.assertEqual(report['outcomes']['d_noise'], 0)
        self.assertEqual(report['verdict'], 'go, method paper')

    def test_five_wins_is_no_go(self):
        hits, kpis = grid(QUERIES[8:13])
        self.assertEqual(self.verdict(hits, kpis)['verdict'], 'no-go')

    def test_three_losses_is_no_go(self):
        hits, kpis = grid(QUERIES[8:17], a_lost=QUERIES[:3])
        report = self.verdict(hits, kpis)
        self.assertEqual((report['outcomes']['O1']['wins'], report['outcomes']['O1']['losses']), (9, 3))
        self.assertEqual(report['verdict'], 'no-go')

    def test_seed_noise_raises_the_net_bar(self):
        hits, kpis = grid(QUERIES[8:14], base_nometric_s2=set(BASE) - set(QUERIES[:4]))
        report = self.verdict(hits, kpis)
        self.assertEqual(report['outcomes']['d_noise'], 4)
        self.assertEqual(report['verdict'], 'no-go')

    def test_ranker_above_agent_gives_measurement_paper(self):
        hits, kpis = grid(QUERIES[8:14], ranker_hits=15)
        report = self.verdict(hits, kpis)
        self.assertEqual(report['outcomes']['O4']['ranker']['r1'], 15)
        self.assertEqual(report['verdict'], 'go, measurement paper')

    def test_covered_regression_breaks_o5(self):
        covered_base = {q for q in QUERIES[12:16]}
        hits, kpis = grid(QUERIES[8:14], base_metric=BASE | covered_base, a_metric=set(BASE))
        report = self.verdict(hits, kpis)
        self.assertEqual(report['outcomes']['O5']['covered_a_metric_vs_base_metric']['net'], -4)
        self.assertEqual(report['verdict'], 'no-go')

    def test_cartservice_drift_breaks_o5(self):
        hits, kpis = grid(QUERIES[8:14])
        cart = {('a_nometric', q) for q in QUERIES[20:23]}
        report = self.verdict(hits, kpis, cart)
        self.assertEqual(report['outcomes']['O5']['cart_top1_increase'], 3)
        self.assertEqual(report['verdict'], 'no-go')

    def test_missing_core_run_is_not_enough_evidence(self):
        hits, kpis = grid(QUERIES[8:14])
        rows = rows_for(hits)
        rows[0].update(status='missing', scored=False, **{'R@1': 0.0, 'MRR': 0.0})
        self.assertEqual(decide.decide(rows, DEV, kpis)['verdict'], 'not enough evidence')

    def test_four_stopped_runs_make_a_condition_unreadable(self):
        hits, kpis = grid(QUERIES[8:14])
        rows = rows_for(hits)
        for row in [r for r in rows if r['condition'] == 'a_metric'][:4]:
            row.update(status='failed', scored=False, **{'R@1': 0.0, 'MRR': 0.0})
        report = decide.decide(rows, DEV, kpis)
        self.assertFalse(report['conditions']['a_metric']['readable'])
        self.assertEqual(report['verdict'], 'not enough evidence')

    def test_ablation_conditions_do_not_gate_the_verdict(self):
        hits, kpis = grid(QUERIES[8:14])
        rows = rows_for(hits)
        for row in [r for r in rows if r['condition'] == 'm2_nometric'][:5]:
            row.update(status='missing', scored=False, **{'R@1': 0.0, 'MRR': 0.0})
        self.assertEqual(decide.decide(rows, DEV, kpis)['verdict'], 'go, method paper')


def write_zip(folder, name, bundle, traces, platform, scores):
    path = Path(folder) / name
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('run/progress.json', json.dumps({'bundle_sha256': bundle, 'traces': traces}))
        z.writestr('run/status.json', json.dumps({'status': 'passed', 'platform': platform}))
        for rid, r1 in scores.items():
            z.writestr(f'run/scoring/{rid}/author-score.txt', f'R@1: {r1}\nR@3: 1.0\nMRR: {r1}\n')
            z.writestr(f'run/traces/{rid}/result.json', json.dumps({'root_causes': ['paymentservice']}))
            z.writestr(f'run/traces/{rid}/events.jsonl', json.dumps(
                {'kind': 'request', 'phase': 'trace', 'prompt_tokens_local': 1200}) + '\n')
    Path(str(path) + '.sha256').write_text(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + name + '\n')
    return path


class Collect(unittest.TestCase):
    MANIFEST = {'bundle_sha256': 'b' * 64,
                'runs': [{'run_id': 'r1', 'site': 'kaggle'}, {'run_id': 'r2', 'site': 'modal'}]}

    def test_merges_shards_and_prefers_the_assigned_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            kaggle = write_zip(tmp, 'k.zip', 'b' * 64, {'r1': {'status': 'passed'}, 'r2': {'status': 'failed'}},
                               'kaggle', {'r1': 1.0})
            modal = write_zip(tmp, 'm.zip', 'b' * 64, {'r2': {'status': 'passed'}}, 'modal', {'r2': 0.0})
            records = decide.collect(self.MANIFEST, [kaggle, modal])
        self.assertEqual(records['r1']['R@1'], 1.0)
        self.assertEqual((records['r2']['status'], records['r2']['platform']), ('passed', 'modal'))
        self.assertEqual(records['r1']['prompt_max'], 1200)

    def test_pending_runs_stay_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            kaggle = write_zip(tmp, 'k.zip', 'b' * 64, {'r1': {'status': 'running'}}, 'kaggle', {})
            self.assertEqual(decide.collect(self.MANIFEST, [kaggle]), {})

    def test_refuses_another_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            other = write_zip(tmp, 'k.zip', 'c' * 64, {'r1': {'status': 'passed'}}, 'kaggle', {'r1': 1.0})
            with self.assertRaises(SystemExit):
                decide.collect(self.MANIFEST, [other])

    def test_refuses_a_tampered_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_zip(tmp, 'k.zip', 'b' * 64, {'r1': {'status': 'passed'}}, 'kaggle', {'r1': 1.0})
            Path(str(path) + '.sha256').write_text('0' * 64 + '\n')
            with self.assertRaises(SystemExit):
                decide.collect(self.MANIFEST, [path])


if __name__ == '__main__':
    unittest.main()
