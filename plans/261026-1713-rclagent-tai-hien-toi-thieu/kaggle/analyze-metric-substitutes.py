"""Measures, for every no_metric run, which non-metric signal about the faulty service the data holds and where the run
loses it, by the frozen rules of plans/reports/prereg-261102-rclagent-metric-substitute-codebook.md. Reads the results
ZIPs, the bundles beside the manifests, the runs.csv of analyze-evidence-loss.py and the raw RE2-OB trace file (train
windows only, for the latency baseline); no model request, no Kaggle, no test-split label or result.

Usage: analyze-metric-substitutes.py OUT_DIR PACKAGE ZIP MANIFEST [PACKAGE ZIP MANIFEST ...] --evidence-runs FILE
                                     [--raw-traces FILE] [--roles FILE] [--label NAME]

The options may stand anywhere on the command line. Each group of three arguments is one package; its ZIP is read through
analyze-missing-source-results.py load(), so the SHA256, bundle and manifest checks apply, and its bundle is the
rclagent-kaggle-bundle.zip beside the manifest. --evidence-runs is the runs.csv of analyze-evidence-loss.py for the same
ZIPs; I2, I3 and rank are joined from it and not recomputed, and a run missing from it is an error.

Indicators (codebook section 4), per no_metric run; true, false or NA:
- U0_trace / U0_baseline / U0 for the attributions either (main), callee and caller; U0_status and U0_logs (reported,
  outside the chain);
- U1 every span whose cmdb_id is the faulty service got a self_state_verification request;
- U2 / U2_latency a span related to the faulty service judged itself abnormal (with a latency word);
- U3 = I2 or I3, U4 = rank 0, U_struct and top1_is_struct_max.
Sets per (case, seed): D metric hit and no_metric miss, R both miss and the metric MRR at least 0.2 above, K no_metric
hit; a case without a span of the faulty service is excluded.

Writes pairs.csv (one row per no_metric run), cases.csv, baseline.csv and summary.json (UTF-8). It refuses to write
into a folder that already holds a summary.json.
"""
import csv
import hashlib
import importlib.util
import io
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREREG = HERE / 'metric-substitute-prereg.json'
RAW_TRACES = Path('F:/Nam/UIT/nt114-paper-artifacts/W7165616276/data/re2ob/trace/all/trace_jaeger-span.csv')
ROLES = HERE.parent / 'work' / 're2ob-case-roles-by-source-key.csv'
BUNDLE = 'rclagent-kaggle-bundle.zip'


def import_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


evidence = import_script('evidence_loss_for_metric_substitutes', 'analyze-evidence-loss.py')
analyzer, match, read_gt, write_csv = evidence.analyzer, evidence.match, evidence.read_gt, evidence.write_csv
sha256_lf = evidence.sha256_lf
IMPORTED = ('analyze-evidence-loss.py',) + evidence.IMPORTED

RULES = ('either', 'callee', 'caller')
CHAIN = ('U0', 'U1', 'U2', 'U3', 'U4')
LATENCY_WORDS = re.compile(r'latenc|duration|slow|delay|took|response time', re.I)
SELF_STATE = 'self_state_verification'
FRONTEND = 'frontendservice'
WINDOW_START_S, WINDOW_END_S = 1200, 60
MRR_DROP = 0.2
CALIBRATION_CASE = '99f095'


# -- Spans of one case ---------------------------------------------------------------------------------------------

def callee(operation):
    """Service named by an rpc operation such as hipstershop.CartService/GetCart, lower case; None without a '/'."""
    head = operation.strip().lstrip('/').split('/', 1)
    if len(head) < 2 or not head[0]:
        return None
    return head[0].rsplit('.', 1)[-1].lower() or None


def is_client(span):
    target = callee(span['operation_name'])
    return bool(target) and not match(span['cmdb_id'], target)


def attributed(span, gt, rule):
    """Whether a span points at the faulty service: a server span by its cmdb_id, a client span by its callee, its
    caller (its own cmdb_id) or either (codebook section 3)."""
    caller_hit = match(gt, span['cmdb_id'])
    if not is_client(span):
        return caller_hit
    callee_hit = match(gt, callee(span['operation_name']))
    return {'callee': callee_hit, 'caller': caller_hit, 'either': callee_hit or caller_hit}[rule]


def related(span, gt):
    """Server span of the faulty service (cmdb_id) or a client span of another service whose operation names it."""
    if match(gt, span['cmdb_id']):
        return 'server'
    return 'client' if evidence.base_of(gt) in span['operation_name'].lower() else ''


def with_self_time(spans):
    """Copies of the spans with an integer duration and self_time = duration minus the direct children, at least 0."""
    out = [dict(s, duration=int(s['duration'])) for s in spans]
    children = Counter()
    for span in out:
        children[span['parent_span']] += span['duration']
    for span in out:
        span['self_time'] = max(0, span['duration'] - children[span['span_id']])
    return out


def top_span(spans, key):
    """(span with the largest key, number of spans sharing that value); the first in file order wins a tie."""
    scored = [s for s in spans if key(s) is not None]
    if not scored:
        return None, 0
    best = max(key(s) for s in scored)
    tied = [s for s in scored if key(s) == best]
    return tied[0], len(tied)


def struct_max(spans):
    """The service with most spans without the frontend, or 'tie'."""
    counts = Counter(s['cmdb_id'] for s in spans if not match(FRONTEND, s['cmdb_id'])).most_common()
    if not counts:
        return 'tie', counts
    return (counts[0][0] if len(counts) == 1 or counts[0][1] > counts[1][1] else 'tie'), counts


def ratio_of(span, baseline):
    found = baseline.get((span['cmdb_id'], span['operation_name']))
    return span['duration'] / found['p50'] if found and found['p50'] else None


def case_signals(spans, log_services, gt, baseline):
    """Indicators of a case that depend on the bundle alone (codebook section 4)."""
    spans = with_self_time(spans)
    top_self, self_ties = top_span(spans, lambda s: s['self_time'])
    top_ratio, ratio_ties = top_span(spans, lambda s: ratio_of(s, baseline))
    above_p99 = bool(top_ratio) and top_ratio['duration'] > baseline[(top_ratio['cmdb_id'],
                                                                       top_ratio['operation_name'])]['p99']
    shape_max, counts = struct_max(spans)
    gt_related = [s for s in spans if related(s, gt)]
    out = {'gt_service': gt, 'spans': len(spans), 'traces': len({s['trace_id'] for s in spans}),
           'gt_server_spans': sum(related(s, gt) == 'server' for s in spans),
           'gt_client_spans': sum(related(s, gt) == 'client' for s in spans),
           'status_nonzero': sum(str(s['status_code']).strip() != '0' for s in spans),
           'gt_log_lines': sum(n for service, n in log_services.items() if match(gt, service)),
           'log_services': ';'.join(f'{k}={v}' for k, v in sorted(log_services.items())),
           'shape': ';'.join(f'{k}={v}' for k, v in counts), 'struct_max': shape_max,
           'U_struct': shape_max != 'tie' and match(gt, shape_max),
           'U0_status': any(str(s['status_code']).strip() != '0' for s in gt_related),
           'U0_logs': any(match(gt, service) and n for service, n in log_services.items()),
           'top_self_span': top_self and f'{top_self["cmdb_id"]} {top_self["operation_name"]}',
           'top_self_time': top_self and top_self['self_time'], 'top_self_ties': self_ties,
           'top_ratio_span': top_ratio and f'{top_ratio["cmdb_id"]} {top_ratio["operation_name"]}',
           'top_ratio': top_ratio and round(ratio_of(top_ratio, baseline), 2), 'top_ratio_ties': ratio_ties,
           'top_ratio_above_p99': above_p99,
           'spans_without_baseline': sum(ratio_of(s, baseline) is None for s in spans)}
    for rule in RULES:
        trace_hit = bool(top_self) and attributed(top_self, gt, rule)
        baseline_hit = bool(top_ratio) and attributed(top_ratio, gt, rule) and above_p99
        out[f'U0_trace_{rule}'], out[f'U0_baseline_{rule}'] = trace_hit, baseline_hit
        out[f'U0_{rule}'] = trace_hit or baseline_hit
    return out, spans


def read_bundle_case(bundle, trace_id):
    """(spans, log line count per cmdb_id) of one case in an open bundle ZIP."""
    prefix = f'traces/{trace_id}/input/'
    with bundle.open(prefix + 'trace/all/trace_jaeger-span.csv') as handle:
        spans = list(csv.DictReader(io.TextIOWrapper(handle, encoding='utf-8')))
    with bundle.open(prefix + 'log/all/logs.csv') as handle:
        logs = Counter(r['cmdb_id'] for r in csv.DictReader(io.TextIOWrapper(handle, encoding='utf-8')))
    return spans, logs


# -- Latency baseline from train windows -----------------------------------------------------------------------------

def windows_of(roles_path):
    """(start ms, end ms, role) of every case window [inject_ts - 1200 s, inject_ts - 60 s)."""
    rows = list(csv.DictReader(Path(roles_path).read_text(encoding='utf-8-sig').splitlines()))
    return [(int(r['inject_ts']) * 1000 - WINDOW_START_S * 1000, int(r['inject_ts']) * 1000 - WINDOW_END_S * 1000,
             r['role']) for r in rows]


def quantile(sorted_values, p):
    return sorted_values[min(len(sorted_values) - 1, int(p * len(sorted_values)))]


def build_baseline(raw_path, roles_path, keys, chunksize=2_000_000):
    """p50 and p99 of duration per (cmdb_id, operation_name) in keys over rows that fall in exactly one window, and
    that window belongs to a train case. Rows of val or test windows and rows of several windows are dropped before
    any aggregation; the counts are returned, nothing else about them."""
    import numpy as np
    import pandas as pd
    windows = windows_of(roles_path)
    train = [w for w in windows if w[2] == 'train']
    if not train:
        raise SystemExit(f'{roles_path}: no train case')
    lo, hi = min(w[0] for w in train), max(w[1] for w in train)
    services = sorted({k[0] for k in keys})
    kept, counts = {}, Counter()
    for chunk in pd.read_csv(raw_path, usecols=['timestamp', 'cmdb_id', 'operation_name', 'duration'],
                             chunksize=chunksize):
        chunk = chunk[chunk['cmdb_id'].isin(services) & (chunk['timestamp'] >= lo) & (chunk['timestamp'] < hi)]
        ts = chunk['timestamp'].to_numpy()
        owners = np.zeros(len(chunk), dtype=np.int64)
        is_train = np.zeros(len(chunk), dtype=bool)
        for start, end, role in windows:
            inside = (ts >= start) & (ts < end)
            owners += inside
            if role == 'train':
                is_train |= inside
        counts['dropped_several_windows'] += int((owners > 1).sum())
        counts['dropped_nontrain'] += int(((owners == 1) & ~is_train).sum())
        chunk = chunk[(owners == 1) & is_train]
        for (service, operation), durations in chunk.groupby(['cmdb_id', 'operation_name'])['duration']:
            if (service, operation) in keys:
                kept.setdefault((service, operation), []).extend(int(d) for d in durations)
        counts['train_rows_scanned'] += len(chunk)
    rows = []
    for (service, operation), values in sorted(kept.items()):
        values.sort()
        rows.append({'cmdb_id': service, 'operation_name': operation, 'n': len(values),
                     'p50': quantile(values, 0.5), 'p99': quantile(values, 0.99)})
    return rows, dict(counts, train_windows=len(train), keys=len(keys), keys_with_baseline=len(rows),
                      rule='[inject_ts-1200s, inject_ts-60s) of train cases; quantile = sorted[min(n-1, floor(p*n))]')


# -- Runs ----------------------------------------------------------------------------------------------------------

def read_events(zipped, names, rid, problems):
    path = f'run/traces/{rid}/events.jsonl'
    if path not in names:
        problems.append('no events')
        return []
    events = []
    for number, line in enumerate(zipped.read(path).decode('utf-8').split('\n'), 1):
        if line.strip():
            try:
                events.append(json.loads(line))
            except ValueError:
                problems.append(f'unparseable events line {number}')
    return events


def run_signals(events, spans, gt, problems):
    """U1, U2 and U2_latency of one run from its events (codebook section 4)."""
    asked = {str(e.get('span_id')) for e in events if e.get('kind') == 'request' and e.get('operation') == SELF_STATE}
    verdicts = {}
    for event in events:
        if event.get('kind') == 'agent_complete' and event.get('operation') == SELF_STATE:
            try:
                value = json.loads(event.get('output') or '')
            except (TypeError, ValueError):
                problems.append(f'unparseable self-state output of span {event.get("span_id")}')
                continue
            if isinstance(value, dict):
                verdicts.setdefault(str(event.get('span_id')), []).append(value)
    server = [s['span_id'] for s in spans if related(s, gt) == 'server']
    gt_related = [s['span_id'] for s in spans if related(s, gt)]
    flagged = [v for sid in gt_related for v in verdicts.get(sid, []) if v.get('is_abnormal') is True]
    return {'gt_server_spans_asked': sum(sid in asked for sid in server),
            'gt_related_spans_judged': sum(sid in verdicts for sid in gt_related),
            'gt_related_spans_abnormal': sum(any(v.get('is_abnormal') is True for v in verdicts.get(sid, []))
                                             for sid in gt_related),
            'U1': all(sid in asked for sid in server) if server else None,
            'U2': bool(flagged),
            'U2_latency': any(LATENCY_WORDS.search(f'{v.get("hypothesis") or ""} {v.get("key_symptoms") or ""}')
                              for v in flagged)}


def top1_of(zipped, names, rid):
    path = f'run/traces/{rid}/result.json'
    if path not in names:
        return None
    try:
        causes = json.loads(zipped.read(path).decode('utf-8')).get('root_causes') or []
    except (ValueError, AttributeError):
        return None
    return str(causes[0]) if causes else None


def flag(value):
    """'true'/'false' of runs.csv as a bool; anything else (NA, empty) as None."""
    return {'true': True, 'false': False}.get(str(value).strip().lower())


def first_loss(row, u0='U0'):
    for name in CHAIN:
        value = row[u0] if name == 'U0' else row[name]
        if value is None:
            return f'{name}_NA'
        if value is False:
            return name
    return 'preserved'


def assign_set(metric, no_metric, gt_spans):
    """D, R, K or '' for one (case, seed) from the scorer's R@1 and MRR (codebook section 2)."""
    if not gt_spans:
        return 'excluded'
    if no_metric['R@1'] == 1:
        return 'K'
    if metric['R@1'] == 1:
        return 'D'
    if metric['MRR'] >= no_metric['MRR'] + MRR_DROP - 1e-9:
        return 'R'
    return ''


def read_evidence_runs(path):
    return {r['run_id']: r for r in csv.DictReader(Path(path).read_text(encoding='utf-8').splitlines())}


def join_evidence(row, evidence_rows, problems):
    found = evidence_rows.get(row['run_id'])
    if found is None:
        raise SystemExit(f'{row["run_id"]} is not in the --evidence-runs file')
    rank = str(found.get('rank', '')).strip()
    i2, i3 = flag(found.get('I2')), flag(found.get('I3'))
    if found.get('integrity', 'ok') != 'ok':
        problems.append(f'evidence-loss integrity: {found["integrity"]}')
    return {'I2': i2, 'I3': i3, 'U3': None if i2 is None or i3 is None else i2 or i3,
            'rank': rank, 'U4': rank == '0' if rank.lstrip('-').isdigit() else None,
            'evidence_gt_service': found.get('gt_service', '')}


# -- Outcomes ------------------------------------------------------------------------------------------------------

def outcome_d(pairs, u0, drop=()):
    """O1 and O2 for the D set: per case the first-loss positions of its runs and whether U0 holds."""
    by_case = {}
    for row in pairs:
        if row['set'] == 'D' and row['case'] not in drop:
            by_case.setdefault(row['case'], []).append(row)
    cases = {}
    for case, rows in sorted(by_case.items()):
        losses = sorted({first_loss(r, u0) for r in rows})
        cases[case] = {'runs': len(rows), 'first_loss': losses, 'same': len(losses) == 1, u0: rows[0][u0]}
    same = Counter(c['first_loss'][0] for c in cases.values() if c['same'])
    return {'cases': cases, 'O1_cases_same_first_loss': sum(c['same'] for c in cases.values()),
            'O1_by_indicator': dict(sorted(same.items())), 'O2_cases_with_U0': sum(c[u0] is True for c in cases.values()),
            'O2_no_substitute': bool(cases) and all(c[u0] is False for c in cases.values())}


def outcomes(pairs):
    k_rows = [r for r in pairs if r['set'] == 'K']
    hits = [r for r in k_rows if r['hit_without_substitute']]
    main = outcome_d(pairs, 'U0_either')
    ranking = Counter(c['first_loss'][0] for c in main['cases'].values() if c['same'])
    top = ranking.most_common()
    return {
        'main': main,
        'sensitivity': {'callee': outcome_d(pairs, 'U0_callee'), 'caller': outcome_d(pairs, 'U0_caller'),
                        f'without_{CALIBRATION_CASE}': outcome_d(pairs, 'U0_either', drop=(CALIBRATION_CASE,))},
        'O3': {'K_runs': len(k_rows), 'hit_without_substitute': len(hits),
               'with_U_struct_and_top1_struct_max': sum(r['U_struct'] is True and r['top1_is_struct_max'] is True
                                                        for r in hits)},
        'O4': {f'{r["case"]} s{r["seed"]}': first_loss(r, 'U0_either') for r in pairs if r['set'] == 'R'},
        'x_rank_1': ('ngang nhau' if len(top) > 1 and top[0][1] == top[1][1] else top[0][0]) if top else None}


# -- Freeze receipt, CLI, output -----------------------------------------------------------------------------------

def module_hashes():
    return {name: sha256_lf(HERE / name) for name in IMPORTED}


def prereg_report(path=PREREG, root=ROOT):
    report = {'frozen': False, 'codebook_sha_matches': False, 'analyzer_sha_matches': False, 'imports_sha_match': False}
    path = Path(path)
    if not path.exists():
        return report
    recorded = json.loads(path.read_text(encoding='utf-8'))
    codebook = Path(recorded.get('codebook_path', ''))
    codebook = codebook if codebook.is_absolute() else Path(root) / codebook
    return {'frozen': True,
            'codebook_sha_matches': codebook.is_file() and sha256_lf(codebook) == recorded.get('codebook_sha256'),
            'analyzer_sha_matches': sha256_lf(Path(__file__)) == recorded.get('analyzer_sha256'),
            'imports_sha_match': module_hashes() == recorded.get('imports_sha256')}


def parse_args(argv):
    values = {'--evidence-runs': None, '--raw-traces': str(RAW_TRACES), '--roles': str(ROLES), '--label': 'default'}
    positional, i = [], 0
    while i < len(argv):
        arg = argv[i]
        if arg in values:
            if i + 1 >= len(argv):
                raise SystemExit(f'{arg} needs a value\n\n{__doc__}')
            values[arg] = argv[i + 1]
            i += 1
        elif arg.startswith('--'):
            raise SystemExit(f'unknown option {arg}\n\n{__doc__}')
        else:
            positional.append(arg)
        i += 1
    if len(positional) < 4 or (len(positional) - 1) % 3 or not values['--evidence-runs']:
        raise SystemExit(__doc__)
    return {'out_dir': Path(positional[0]), 'evidence_runs': Path(values['--evidence-runs']),
            'raw_traces': Path(values['--raw-traces']), 'roles': Path(values['--roles']), 'label': values['--label'],
            'groups': [tuple(positional[i:i + 3]) for i in range(1, len(positional), 3)]}


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def collect(groups, evidence_rows):
    """Cases (bundle spans and logs) and no_metric runs of every package, with the scorer rows of all conditions."""
    cases, runs, inputs = {}, [], []
    for package, archive, manifest in groups:
        rows = analyzer.load(archive, manifest)
        bundle_path = Path(manifest).parent / BUNDLE
        recorded = (Path(manifest).parent / analyzer.BUNDLE_SHA256).read_text().split()[0]
        actual = sha256_file(bundle_path)
        if actual != recorded:
            raise SystemExit(f'{bundle_path}: SHA256 {actual} differs from recorded {recorded}')
        inputs.append({'package': package, 'results_zip': str(archive), 'results_sha256': rows[0]['results_sha256'],
                       'bundle': str(bundle_path), 'bundle_sha256': actual})
        scores = {(r['trace_id'], r['condition'], str(r['seed'])): r for r in rows}
        with zipfile.ZipFile(archive) as zipped, zipfile.ZipFile(bundle_path) as bundle:
            names = set(zipped.namelist())
            for row in rows:
                if row['trace_id'] not in cases:
                    spans, logs = read_bundle_case(bundle, row['trace_id'])
                    cases[row['trace_id']] = {'package': package, 'fault_case': row['case'], 'spans': spans,
                                              'logs': logs}
                if row['condition'] != 'no_metric':
                    continue
                problems = [] if row['integrity'] == 'ok' else [f'results integrity: {row["integrity"]}']
                joined = join_evidence(row, evidence_rows, problems)
                gt = joined['evidence_gt_service'] or read_gt(zipped, names, row['run_id'])
                scored_gt = read_gt(zipped, names, row['run_id'])
                if scored_gt and gt and not match(gt, scored_gt):
                    problems.append(f'faulty service {gt} differs from groundtruth.csv {scored_gt}')
                metric = scores.get((row['trace_id'], 'metric', str(row['seed'])))
                if metric is None:
                    raise SystemExit(f'{row["run_id"]}: no metric run of the same case and seed')
                if (row['R@1'] == 1) != (joined['rank'] == '0'):
                    problems.append(f'R@1 {row["R@1"]} disagrees with evidence-loss rank {joined["rank"]}')
                runs.append({'row': row, 'metric': metric, 'joined': joined, 'gt': gt, 'problems': problems,
                             'events': read_events(zipped, names, row['run_id'], problems),
                             'top1': top1_of(zipped, names, row['run_id'])})
    return cases, runs, inputs


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    out_dir = args['out_dir']
    if (out_dir / 'summary.json').exists():
        raise SystemExit(f'{out_dir} already holds a summary.json; choose a new folder')
    prereg = prereg_report()
    evidence_rows = read_evidence_runs(args['evidence_runs'])
    cases, runs, inputs = collect(args['groups'], evidence_rows)
    keys = {(s['cmdb_id'], s['operation_name']) for case in cases.values() for s in case['spans']}
    baseline_rows, baseline_counts = build_baseline(args['raw_traces'], args['roles'], keys)
    baseline = {(b['cmdb_id'], b['operation_name']): b for b in baseline_rows}
    gts = {}
    for run in runs:
        gts.setdefault(run['row']['trace_id'], run['gt'])
    case_rows, spans_of = [], {}
    for trace_id, case in sorted(cases.items()):
        gt = gts.get(trace_id)
        if not gt:
            continue
        signals, spans_of[trace_id] = case_signals(case['spans'], case['logs'], gt, baseline)
        case_rows.append({'package': case['package'], 'case': trace_id[:6], 'trace_id': trace_id,
                          'fault_case': case['fault_case'], **signals})
    by_trace = {r['trace_id']: r for r in case_rows}
    pairs = []
    for run in runs:
        row, case = run['row'], by_trace[run['row']['trace_id']]
        signals = run_signals(run['events'], spans_of[row['trace_id']], run['gt'], run['problems'])
        top1 = run['top1']
        pair = {'run_id': row['run_id'], 'package': case['package'], 'case': case['case'],
                'fault_case': case['fault_case'], 'seed': row['seed'], 'gt_service': run['gt'],
                'set': assign_set(run['metric'], row, case['gt_server_spans']),
                'metric_R@1': run['metric']['R@1'], 'metric_MRR': run['metric']['MRR'],
                'no_metric_R@1': row['R@1'], 'no_metric_MRR': row['MRR'], 'top1': top1,
                'struct_max': case['struct_max'], 'U_struct': case['U_struct'],
                'top1_is_struct_max': None if top1 is None else case['struct_max'] != 'tie' and match(case['struct_max'],
                                                                                                    top1),
                **{k: case[k] for k in case if k.startswith('U0')},
                **signals, **{k: run['joined'][k] for k in ('I2', 'I3', 'U3', 'rank', 'U4')}}
        pair['U0'] = pair['U0_either']
        for rule in RULES:
            pair[f'first_loss_{rule}'] = first_loss(pair, f'U0_{rule}')
        pair['first_loss'] = pair['first_loss_either']
        pair['hit_without_substitute'] = pair['U4'] is True and pair['U2'] is False and pair['U3'] is False
        pair['integrity'] = '; '.join(run['problems']) or 'ok'
        pairs.append(pair)
    pairs.sort(key=lambda r: r['run_id'])
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / 'pairs.csv', pairs)
    write_csv(out_dir / 'cases.csv', case_rows)
    write_csv(out_dir / 'baseline.csv', baseline_rows, ['cmdb_id', 'operation_name', 'n', 'p50', 'p99'])
    summary = {
        'label': args['label'], 'codebook': 'plans/reports/prereg-261102-rclagent-metric-substitute-codebook.md',
        'prereg': prereg, 'prereg_after_run': prereg_report(),
        'analyzer_sha256': sha256_lf(Path(__file__)), 'imports_sha256': module_hashes(), 'inputs': inputs,
        'evidence_runs': {'path': str(args['evidence_runs']), 'sha256': sha256_lf(args['evidence_runs'])},
        'raw_traces': str(args['raw_traces']), 'roles': {'path': str(args['roles']), 'sha256': sha256_lf(args['roles'])},
        'baseline': baseline_counts,
        'sets': dict(sorted(Counter(r['set'] for r in pairs).items())),
        'integrity_problems': [(r['run_id'], r['integrity']) for r in pairs if r['integrity'] != 'ok'],
        'outcomes': outcomes(pairs),
        'note': 'Descriptive; unit is the case (n = 3 for D); seeds within a case are near-duplicates.'}
    (out_dir / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str) + '\n',
                                          encoding='utf-8')
    print(json.dumps({k: summary[k] for k in ('sets', 'integrity_problems', 'prereg', 'baseline')}, indent=1))
    print(json.dumps(summary['outcomes']['main'], indent=1))


if __name__ == '__main__':
    main()
