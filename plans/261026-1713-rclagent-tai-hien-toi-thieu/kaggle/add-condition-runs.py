"""Add the controlled runs to a staged package built by prepare-bundle.py.

usage: add-condition-runs.py STAGE SELECTION                                 missing-source runs (pilot-selection.json)
       add-condition-runs.py STAGE DEV_SET --telemetry-gap WINDOW_KPI        telemetry-gap dev grid (select-dev-set.py)
(then refresh-package.py STAGE builds the Kaggle bundle)

Missing-source runs: every trace of the stage must belong to SELECTION (fixed before any run). Each trace runs once
per condition and seed, with the same seeds in every condition. Runs go seed by seed, trace by trace, so a session
cut short leaves whole (trace, seed) blocks of all conditions.

Telemetry-gap grid (prereg-261102-rclagent-telemetry-gap-method.md, section 4): every dev query runs the seven
conditions on its site, query by query in the dev set's site order, conditions in GAP_CONDITIONS order; each trace
directory gains the query's window-kpi.json.
"""
import hashlib
import json
import sys
from pathlib import Path

SEEDS = (20261026, 20261027, 20261028)
# 'absent' answers with the author's own no-row response; 'repaired' is metric-repair.py; the model is not told.
CONDITIONS = {'no_metric': {'metric': 'absent', 'logs': 'author'},
              'metric': {'metric': 'repaired', 'logs': 'author'},
              'metric_no_log': {'metric': 'repaired', 'logs': 'absent'}}
GAP_SEED = 20261026
# The trace limits of the S1 v3 sessions (s1-v3/*/manifest.json); the prereg keeps them unchanged.
S1_LIMITS = {'max_tool_rounds_per_span': 8, 'max_model_requests_including_retry': 320, 'rcl_deadline_seconds': 2400}
OFF = {'gap_aware': False, 'trace_kpi': False, 'trace_expand': False}
# Run order 2, 3, 5, 1, 4, 7, 6 of the prereg table: a site cut short keeps the comparisons that decide go/no-go.
GAP_CONDITIONS = {
    'base_nometric': dict(OFF, metric='absent', logs='author', seed=GAP_SEED),
    'base_nometric_s2': dict(OFF, metric='absent', logs='author', seed=20261027),
    'a_nometric': dict(OFF, metric='absent', logs='author', seed=GAP_SEED, trace_kpi=True, trace_expand=True),
    'base_metric': dict(OFF, metric='repaired', logs='author', seed=GAP_SEED),
    'a_metric': dict(OFF, metric='repaired', logs='author', seed=GAP_SEED, trace_expand=True),
    'm2_nometric': dict(OFF, metric='absent', logs='author', seed=GAP_SEED, trace_kpi=True),
    'm1m3_nometric': dict(OFF, metric='absent', logs='author', seed=GAP_SEED, gap_aware=True, trace_expand=True)}


def condition_runs(traces, seeds=SEEDS, conditions=CONDITIONS):
    return [dict(trace, run_id=f"{trace['trace_id']}--{name}--s{seed}", condition=name, seed=seed, **sources)
            for seed in seeds for trace in traces for name, sources in conditions.items()]


def gap_runs(traces, queries, conditions=GAP_CONDITIONS):
    """Runs of the telemetry-gap grid; queries come in the dev set's order and carry their site."""
    by_id = {t['trace_id']: t for t in traces}
    return [dict(by_id[q['trace_id']], run_id=f"{q['trace_id']}--{name}--s{setting['seed']}", condition=name,
                 site=q['site'], **setting)
            for q in queries for name, setting in conditions.items()]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def add_gap_design(stage, manifest, dev_path, kpi_path):
    dev = json.loads(dev_path.read_text(encoding='utf-8'))
    kpi = json.loads(kpi_path.read_text(encoding='utf-8'))['queries']
    traces = {t['trace_id']: t for t in manifest['traces']}
    wanted = [q['trace_id'] for q in dev['queries']]
    assert set(traces) == set(wanted), 'The stage must hold exactly the dev queries'
    for trace_id in wanted:
        target = stage / traces[trace_id]['dir'] / 'window-kpi.json'
        target.write_text(json.dumps(kpi[trace_id], indent=1) + '\n', encoding='utf-8', newline='\n')
        relative = target.relative_to(stage).as_posix()
        manifest['files'][relative] = {'sha256': sha(target), 'bytes': target.stat().st_size}
    manifest['runs'] = gap_runs(manifest['traces'], dev['queries'])
    manifest['harness_limits'] = dict(S1_LIMITS)
    manifest['condition_design'] = {
        'design': 'telemetry-gap dev grid', 'prereg': 'prereg-261102-rclagent-telemetry-gap-method.md',
        'dev_set_file': dev_path.name, 'dev_set_sha256': sha(dev_path),
        'window_kpi_file': kpi_path.name, 'window_kpi_sha256': sha(kpi_path), 'conditions': GAP_CONDITIONS,
        'sites': {site: sum(r['site'] == site for r in manifest['runs']) for site in ('kaggle', 'modal')},
        'components': 'telemetry-gap.py: gap_aware = missing-source notice, trace_kpi = trace-derived latency KPI '
                      'for absent metrics, trace_expand = window evidence table in the final prompt.'}


if __name__ == '__main__':
    stage, selection_path = Path(sys.argv[1]), Path(sys.argv[2])
    manifest = json.loads((stage / 'manifest.json').read_text(encoding='utf-8'))
    if 'runs' in manifest:
        raise RuntimeError('This stage already lists runs; build a fresh stage instead of rewriting them')
    if sys.argv[3:4] == ['--telemetry-gap']:
        add_gap_design(stage, manifest, selection_path, Path(sys.argv[4]))
    else:
        selection = json.loads(selection_path.read_text(encoding='utf-8'))
        order = [item['trace_id'] for item in selection]
        by_id = {t['trace_id']: t for t in manifest['traces']}
        assert set(by_id) <= set(order), 'Stage holds a trace outside the fixed selection'
        traces = [by_id[t] for t in order if t in by_id]
        manifest['runs'] = condition_runs(traces)
        manifest['condition_design'] = {
            'selection_file': selection_path.name,
            'selection_sha256': hashlib.sha256(selection_path.read_bytes()).hexdigest(),
            'seeds': list(SEEDS), 'conditions': CONDITIONS,
            'absent_source': 'Answered by the harness with the author endpoint bytes for "no row"; the tool server is '
                             'not asked and the model is not told the source is missing.',
            'repaired_metric': 'metric-repair.py: NaN node_id groups kept; baseline [t-1200, t-600), window '
                               '[t-600, t+600], KPI reported when |window mean - baseline mean| >= 100 baseline '
                               'standard deviations.'}
    (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'traces': len(manifest['traces']), 'runs': len(manifest['runs'])}))
