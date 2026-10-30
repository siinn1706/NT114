"""Add the controlled missing-source runs to a staged package built by prepare-bundle.py.

usage: add-condition-runs.py STAGE SELECTION     (then refresh-package.py STAGE builds the Kaggle bundle)

Every trace of the stage must belong to SELECTION (pilot-selection.json, fixed before any run). Each trace runs once
per condition and seed, with the same seeds in every condition. Runs go seed by seed, trace by trace, so a session
cut short leaves whole (trace, seed) blocks of all conditions.
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


def condition_runs(traces, seeds=SEEDS, conditions=CONDITIONS):
    return [dict(trace, run_id=f"{trace['trace_id']}--{name}--s{seed}", condition=name, seed=seed, **sources)
            for seed in seeds for trace in traces for name, sources in conditions.items()]


if __name__ == '__main__':
    stage, selection_path = Path(sys.argv[1]), Path(sys.argv[2])
    manifest = json.loads((stage / 'manifest.json').read_text(encoding='utf-8'))
    if 'runs' in manifest:
        raise RuntimeError('This stage already lists runs; build a fresh stage instead of rewriting them')
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
        'absent_source': 'Answered by the harness with the author endpoint bytes for "no row"; the tool server is not '
                         'asked and the model is not told the source is missing.',
        'repaired_metric': 'metric-repair.py: NaN node_id groups kept; baseline [t-1200, t-600), window [t-600, t+600], '
                           'KPI reported when |window mean - baseline mean| >= 100 baseline standard deviations.'}
    (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'traces': len(traces), 'runs': len(manifest['runs'])}))
