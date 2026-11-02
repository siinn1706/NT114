"""Outcomes and the go/no-go verdict of the telemetry-gap dev grid, written before any output was downloaded.

Usage: decide-telemetry-gap-outcomes.py OUT_DIR MANIFEST DEV_SET WINDOW_KPI RESULTS_ZIP [RESULTS_ZIP ...]

Rules (prereg-261102-rclagent-telemetry-gap-method.md, sections 5 and 6):
- a run's R@1 and MRR come from the author scorer; a failed, unscored or missing run counts 0 in every condition;
- a run final (passed or failed) in two ZIPs keeps the record of its assigned site; a run final in none is missing;
- a condition with more than 3 stopped runs is unreadable;
- win of X over Y: X has R@1 and Y not on the same query; net = wins - losses; d_noise counts queries whose R@1
  differs between base_nometric and base_nometric_s2;
- verdict "not enough evidence" while a run of conditions 1-5 is missing or one of them is unreadable; "go, method
  paper" when a_nometric over base_nometric has wins >= 6, losses <= 2, net >= d_noise + 3, O5 holds and a_nometric's
  R@1 is at least the pre-query p95 ranker's; "go, measurement paper" when only the ranker clause fails; else no-go.
No model request is issued; nothing here chooses a run, a seed or a threshold after the fact.
"""
import csv
import hashlib
import importlib.util
import json
import statistics
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORE = ('base_metric', 'base_nometric', 'base_nometric_s2', 'a_metric', 'a_nometric')
CONDITIONS = CORE + ('m1m3_nometric', 'm2_nometric')
MAX_STOPPED = 3
WINS, LOSSES, NOISE_GAP, O5_NET, O5_CART = 6, 2, 3, -1, 2


def import_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


missing = import_script('missing_source_for_gap', 'analyze-missing-source-results.py')
kpis = import_script('window_kpi_for_gap', 'build-window-kpi.py')
gap = import_script('telemetry_gap_for_outcomes', 'telemetry-gap.py')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_record(zipped, names, run, status, platform):
    rid = run['run_id']
    row = {'status': status, 'platform': platform, 'scored': False, 'R@1': 0.0, 'MRR': 0.0, 'top1': '',
           'requests': 0, 'prompt_max': None, 'prompt_median': None, 'metric_services': []}
    path = f'run/scoring/{rid}/author-score.txt'
    scored = missing.score(zipped.read(path).decode('utf-8', 'replace')) if path in names else None
    if scored and status == 'passed':
        row.update(scored=True, **{k: scored[k] for k in ('R@1', 'MRR')})
    row['top1'] = missing.top1(zipped, rid) if f'run/traces/{rid}/result.json' in names else ''
    events = f'run/traces/{rid}/events.jsonl'
    if events in names:
        parsed = [json.loads(line) for line in zipped.read(events).decode('utf-8').splitlines() if line.strip()]
        sizes = [e['prompt_tokens_local'] for e in parsed if e.get('kind') == 'request' and e.get('phase') == 'trace']
        row.update(requests=len(sizes), prompt_max=max(sizes, default=None),
                   prompt_median=statistics.median(sizes) if sizes else None,
                   metric_services=[e['params']['service_name'] for e in parsed
                                    if e.get('kind') == 'tool_result' and e.get('name') == 'search_fluctuating_metrics'])
    return row


def collect(manifest, archives):
    """One record per manifest run, merged across the shard ZIPs."""
    runs = {r['run_id']: r for r in manifest['runs']}
    records = {}
    for archive in archives:
        recorded = Path(str(archive) + '.sha256').read_text().split()[0]
        if sha256(archive) != recorded:
            raise SystemExit(f'{archive}: SHA256 differs from its .sha256')
        with zipfile.ZipFile(archive) as zipped:
            names = set(zipped.namelist())
            progress = json.loads(zipped.read('run/progress.json'))
            status = json.loads(zipped.read('run/status.json')) if 'run/status.json' in names else {}
            if progress['bundle_sha256'] != manifest['bundle_sha256']:
                raise SystemExit(f'{archive} ran another bundle')
            platform = status.get('platform', 'kaggle')
            for rid, state in progress['traces'].items():
                if rid not in runs:
                    raise SystemExit(f'{archive}: run {rid} is not in the manifest')
                if state.get('status') not in ('passed', 'failed'):
                    continue
                row = run_record(zipped, names, runs[rid], state['status'], platform)
                previous = records.get(rid)
                if previous and previous['platform'] == runs[rid]['site']:
                    continue
                if previous and platform != runs[rid]['site']:
                    raise SystemExit(f'Run {rid} is final in two ZIPs, neither from its site')
                records[rid] = dict(row, results_zip=Path(archive).name)
    return records


def table(manifest, records, dev, kpi):
    gt = {q['trace_id']: q for q in dev['queries']}
    rows = []
    for run in manifest['runs']:
        record = records.get(run['run_id'], {'status': 'missing', 'platform': '', 'scored': False, 'R@1': 0.0,
                                             'MRR': 0.0, 'top1': '', 'requests': 0, 'prompt_max': None,
                                             'prompt_median': None, 'metric_services': []})
        q = gt[run['trace_id']]
        services = kpi[run['trace_id']]['services']
        in_trace = {s for s, v in services.items() if v['in_trace']}
        rows.append({'run_id': run['run_id'], 'trace_id': run['trace_id'], 'condition': run['condition'],
                     'site': run['site'], 'stratum': q['stratum'], 'gt': q['gt'], **{
                         k: v for k, v in record.items() if k != 'metric_services'},
                     'cart_top1': gap.match('cartservice', record['top1']) if record['top1'] else False,
                     'queried_gt_metric': any(gap.match(q['gt'], s) for s in record['metric_services']),
                     'top1_outside_trace': bool(record['top1']) and not any(gap.match(record['top1'], s)
                                                                            for s in in_trace)})
    return rows


def pair(by, x, y, queries):
    wins = sum(by[(q, x)]['R@1'] == 1 and by[(q, y)]['R@1'] != 1 for q in queries)
    losses = sum(by[(q, y)]['R@1'] == 1 and by[(q, x)]['R@1'] != 1 for q in queries)
    return {'x': x, 'y': y, 'n': len(queries), 'wins': wins, 'losses': losses, 'net': wins - losses,
            'r1_x': sum(by[(q, x)]['R@1'] == 1 for q in queries), 'r1_y': sum(by[(q, y)]['R@1'] == 1 for q in queries)}


def decide(rows, dev, kpi):
    by = {(r['trace_id'], r['condition']): r for r in rows}
    queries = [q['trace_id'] for q in dev['queries']]
    none = [q['trace_id'] for q in dev['queries'] if q['stratum'] == 'none']
    covered = [q['trace_id'] for q in dev['queries'] if q['stratum'] == 'covered']
    per = {}
    for c in CONDITIONS:
        rs = [by[(q, c)] for q in queries]
        per[c] = {'runs': len(rs), 'missing': sum(r['status'] == 'missing' for r in rs),
                  'stopped': sum(r['status'] == 'failed' or (r['status'] == 'passed' and not r['scored']) for r in rs),
                  'R@1': sum(r['R@1'] for r in rs) / len(rs), 'MRR': sum(r['MRR'] for r in rs) / len(rs),
                  'cart_top1': sum(r['cart_top1'] for r in rs),
                  'r1_none': sum(by[(q, c)]['R@1'] == 1 for q in none),
                  'r1_covered': sum(by[(q, c)]['R@1'] == 1 for q in covered),
                  'queried_gt_metric': sum(r['queried_gt_metric'] for r in rs),
                  'top1_outside_trace': sum(r['top1_outside_trace'] for r in rs),
                  'prompt_max': max((r['prompt_max'] for r in rs if r['prompt_max']), default=None)}
        per[c]['readable'] = per[c]['stopped'] <= MAX_STOPPED
    gts = {q['trace_id']: q['gt'] for q in dev['queries']}
    ranker_hits = {q: bool(kpis.ranker_order(kpi[q])) and gap.match(gts[q], kpis.ranker_order(kpi[q])[0])
                   for q in queries}
    ranker = {'r1': sum(ranker_hits.values()), 'r1_none': sum(ranker_hits[q] for q in none),
              'r1_covered': sum(ranker_hits[q] for q in covered)}
    d_noise = sum(by[(q, 'base_nometric')]['R@1'] != by[(q, 'base_nometric_s2')]['R@1'] for q in queries)
    o1 = pair(by, 'a_nometric', 'base_nometric', queries)
    o5_net = pair(by, 'a_metric', 'base_metric', covered)
    o5_cart = per['a_nometric']['cart_top1'] - per['base_nometric']['cart_top1']
    outcomes = {
        'd_noise': d_noise, 'O1': o1,
        'O2': {c: per[c]['r1_none'] for c in CONDITIONS},
        'O3': {'m2_vs_base_none': pair(by, 'm2_nometric', 'base_nometric', none),
               'm2_vs_base_covered': pair(by, 'm2_nometric', 'base_nometric', covered),
               'a_vs_m2_none': pair(by, 'a_nometric', 'm2_nometric', none),
               'a_vs_m2_covered': pair(by, 'a_nometric', 'm2_nometric', covered),
               'a_vs_m1m3': pair(by, 'a_nometric', 'm1m3_nometric', queries)},
        'O4': {'a_nometric_r1': o1['r1_x'], 'ranker': ranker},
        'O5': {'covered_a_metric_vs_base_metric': o5_net, 'cart_top1_increase': o5_cart,
               'holds': o5_net['net'] >= O5_NET and o5_cart <= O5_CART}}
    effect = o1['wins'] >= WINS and o1['losses'] <= LOSSES and o1['net'] >= d_noise + NOISE_GAP
    if any(per[c]['missing'] or not per[c]['readable'] for c in CORE):
        verdict = 'not enough evidence'
    elif effect and outcomes['O5']['holds'] and o1['r1_x'] >= ranker['r1']:
        verdict = 'go, method paper'
    elif effect and outcomes['O5']['holds']:
        verdict = 'go, measurement paper'
    else:
        verdict = 'no-go'
    return {'verdict': verdict, 'conditions': per, 'outcomes': outcomes,
            'rule': {'wins': WINS, 'losses': LOSSES, 'noise_gap': NOISE_GAP, 'o5_net': O5_NET, 'o5_cart': O5_CART,
                     'max_stopped': MAX_STOPPED}}


def main(argv):
    out, manifest_path, dev_path, kpi_path, archives = Path(argv[0]), Path(argv[1]), Path(argv[2]), Path(argv[3]), argv[4:]
    if out.exists():
        raise SystemExit(f'{out} exists; refusing to overwrite')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['bundle_sha256'] = (manifest_path.parent / 'rclagent-kaggle-bundle.zip.sha256').read_text().split()[0]
    dev = json.loads(dev_path.read_text(encoding='utf-8'))
    kpi = json.loads(kpi_path.read_text(encoding='utf-8'))['queries']
    rows = table(manifest, collect(manifest, archives), dev, kpi)
    report = decide(rows, dev, kpi)
    report['inputs'] = {'manifest_sha256': sha256(manifest_path), 'bundle_sha256': manifest['bundle_sha256'],
                        'dev_set_sha256': sha256(dev_path), 'window_kpi_sha256': sha256(kpi_path),
                        'results': {Path(a).name: sha256(a) for a in archives}, 'script_sha256': sha256(__file__)}
    out.mkdir(parents=True)
    with (out / 'runs.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (out / 'outcomes.json').write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'verdict': report['verdict'], 'O1': report['outcomes']['O1'],
                      'd_noise': report['outcomes']['d_noise']}))


if __name__ == '__main__':
    main(sys.argv[1:])
