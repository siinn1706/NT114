"""Runs the non-LLM baselines (RCAEval TraceRCA, MicroRank and BARO, plus a latency-only ranker) on the train queries
(error traces) of RCLAgent on RE2-OB, and scores them against the faulty service. No model request, no Kaggle, no
test-split row: only role == train cases and queries are read.

Usage: run-non-llm-baselines.py OUT_DIR [--raw-traces FILE] [--raw-metrics FILE] [--roles FILE] [--queries FILE]
                                       [--rcaeval-src DIR] [--limit-cases N] [--methods a,b,c]

Case window. Per train case the raw data is cut to [inject_ts - 1200 s, inject_ts + 600 s) and RCAEval receives the
inject time separately (tracerca and microrank split spans into normal/abnormal by startTime + duration against it, baro
splits the metric rows by time against it). A row that also falls inside the window of a val or test case is dropped
from the case (counted in summary.json), so no non-train row reaches a baseline. These baselines see the whole case
window, not only the query trace; the result of a case is copied to every query (error trace) of that case, which is
the unit RCLAgent is scored on. Only the latency_query_* variants look at the query trace alone.

Conditions. full: all sources. no_metric: BARO needs metrics and is marked not_applicable; TraceRCA, MicroRank and the
latency rankers read traces only, so their no_metric result is the same as the full one.

Latency-only ranker. A service scores the max over spans of duration / train p50 of the key (cmdb_id, operation_name);
the p50 is analyze-metric-substitutes.build_baseline() (train cases, [inject-1200 s, inject-60 s)). Case level: spans
of the fault period [inject_ts, inject_ts + 600 s) of the case window; query level: spans of the query trace only.
Attribution of a span (as analyze-metric-substitutes.py): a server span goes to its cmdb_id; a client span (the service
named in operation_name differs from cmdb_id) goes to the callee (variant callee), to its own cmdb_id (caller) or to
both (either). Ties are broken by service name. A service no span points at is not ranked.

Output (OUT_DIR): results.csv (one row per method, condition and query: method, condition, case, trace_id, gt, rank
(0-based rank of the faulty service, empty when it is not ranked), top1, R@1, MRR, status), summary.json (R@1 and MRR
per method and condition, overall, by faulty service and by coverage group: the query trace has a span of the faulty
service (server or client) or not; hashes of the inputs and the RCAEval commit), case-ranks.json (ranked services per
case and method) and slices/ (the cut data, reused by a later run). MicroRank returns only its top 5 operations, so a
faulty service outside them has no rank (MRR counts 0).
"""
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parent / 'work'
RAW = Path('F:/Nam/UIT/nt114-paper-artifacts/W7165616276/data/re2ob')
RAW_TRACES = RAW / 'trace' / 'all' / 'trace_jaeger-span.csv'
RAW_METRICS = RAW / 'metric' / 'all' / 'metrics.csv'
ROLES = WORK / 're2ob-case-roles-by-source-key.csv'
QUERIES = WORK / 'tool-response-scan' / 'tool-response-scan.csv'
RCAEVAL_SRC = HERE / 'runtime' / 'rcaeval-src'

BEFORE_S, AFTER_S = 1200, 600
RULES = ('either', 'callee', 'caller')
RCAEVAL_METHODS = ('tracerca', 'microrank', 'baro')
LATENCY_METHODS = tuple(f'latency_{r}' for r in RULES) + tuple(f'latency_query_{r}' for r in RULES)
ALL_METHODS = RCAEVAL_METHODS + LATENCY_METHODS
RESULT_FIELDS = ['method', 'condition', 'case', 'trace_id', 'gt', 'rank', 'top1', 'R@1', 'MRR', 'status']


def import_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


substitutes = import_script('metric_substitutes_for_non_llm_baselines', 'analyze-metric-substitutes.py')
evidence = substitutes.evidence
sha256_lf = evidence.sha256_lf
label_hit = evidence.label_hit
IMPORTED = ('analyze-metric-substitutes.py',) + substitutes.IMPORTED


# -- Inputs ----------------------------------------------------------------------------------------------------------

def gt_of(case_id):
    """Faulty service of a case: the part of its id before the first underscore."""
    return case_id.split('_', 1)[0]


def read_cases(roles_path):
    """{case_id: {'inject_ts': seconds, 'role': role}} of the roles file (every role; the caller filters)."""
    rows = csv.DictReader(Path(roles_path).read_text(encoding='utf-8-sig').splitlines())
    return {r['case_id']: {'inject_ts': int(r['inject_ts']), 'role': r['role']} for r in rows}


def read_train_queries(queries_path):
    """Queries (case_id, trace_id) with role == train, in file order. Other roles are never kept."""
    with Path(queries_path).open(encoding='utf-8-sig', newline='') as handle:
        return [{'case': r['case_id'], 'trace_id': r['trace_id']} for r in csv.DictReader(handle)
                if r['role'] == 'train']


def case_window_ms(inject_ts):
    """[inject_ts - 1200 s, inject_ts + 600 s) in milliseconds."""
    return (inject_ts - BEFORE_S) * 1000, (inject_ts + AFTER_S) * 1000


def windows_by_role(cases):
    """(train, other): train = [(case_id, start_ms, end_ms)], other = [(start_ms, end_ms)] of val and test cases."""
    train, other = [], []
    for case, info in sorted(cases.items()):
        start, end = case_window_ms(info['inject_ts'])
        if info['role'] == 'train':
            train.append((case, start, end))
        else:
            other.append((start, end))
    return train, other


# -- Slicing ---------------------------------------------------------------------------------------------------------

def slice_rows(chunk, ts_col, train_windows, other_windows):
    """(frame of the rows of train windows with a case_id column, dropped counter) for one chunk. A row in a train
    window and in a val/test window is dropped; a row in two train windows is kept once for each case."""
    import numpy as np
    import pandas as pd
    ts = chunk[ts_col].to_numpy()
    in_other = np.zeros(len(chunk), dtype=bool)
    for start, end in other_windows:
        in_other |= (ts >= start) & (ts < end)
    parts, dropped = [], Counter()
    for case, start, end in train_windows:
        inside = (ts >= start) & (ts < end)
        dropped['dropped_in_val_or_test_window'] += int((inside & in_other).sum())
        part = chunk[inside & ~in_other]
        if len(part):
            parts.append(part.assign(case_id=case))
    return (pd.concat(parts, ignore_index=True) if parts else chunk.iloc[0:0].assign(case_id='')), dropped


def read_slices(raw_traces, raw_metrics, cases, query_ids, chunksize=2_000_000):
    """(case spans, query-trace spans, case metrics, counts) cut from the raw files in one chunked pass each."""
    import pandas as pd
    train, other = windows_by_role(cases)
    lo, hi = min(w[1] for w in train), max(w[2] for w in train)
    counts = Counter()
    spans, query_spans = [], []
    for chunk in pd.read_csv(raw_traces, chunksize=chunksize, dtype={'span_id': str, 'trace_id': str,
                                                                      'parent_span': str, 'operation_name': str}):
        counts['trace_rows_scanned'] += len(chunk)
        query_spans.append(chunk[chunk['trace_id'].isin(query_ids)])
        near = chunk[(chunk['timestamp'] >= lo) & (chunk['timestamp'] < hi)]
        part, dropped = slice_rows(near, 'timestamp', train, other)
        counts.update(dropped)
        spans.append(part)
    metrics = []
    for chunk in pd.read_csv(raw_metrics, chunksize=chunksize):
        counts['metric_rows_scanned'] += len(chunk)
        chunk = chunk.assign(timestamp=chunk['timestamp'] * 1000)
        part, dropped = slice_rows(chunk[(chunk['timestamp'] >= lo) & (chunk['timestamp'] < hi)], 'timestamp', train,
                                   other)
        metrics.append(part.assign(timestamp=part['timestamp'] // 1000))
    spans, query_spans, metrics = (pd.concat(x, ignore_index=True) for x in (spans, query_spans, metrics))
    counts['case_span_rows'], counts['query_span_rows'], counts['case_metric_rows'] = (len(spans), len(query_spans),
                                                                                         len(metrics))
    return spans, query_spans, metrics, dict(counts)


# -- Ranks and metrics -----------------------------------------------------------------------------------------------

def rank_of_gt(gt, services):
    """0-based rank of the faulty service in a ranked service list, by the scorer's name matching; None if absent."""
    found = label_hit(gt, services)
    return None if found < 0 else found


def score_row(gt, services):
    """(rank or None, top1 or '', R@1, MRR) of one ranked service list."""
    rank = rank_of_gt(gt, services)
    return rank, (services[0] if services else ''), int(rank == 0), (0.0 if rank is None else 1.0 / (rank + 1))


def dedupe(names):
    """Ranked names with the first occurrence of each kept."""
    seen, out = set(), []
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def rcaeval_service(candidate):
    """Service of an RCAEval candidate (service_operation or service_kpi), as RCAEval benchmark/scoring.to_service."""
    return candidate.split('_')[0].replace('-db', '')


# -- Latency-only ranker ---------------------------------------------------------------------------------------------

def attributed_services(span, rule):
    """Services a span's ratio counts for under a rule: server span -> its cmdb_id; client span -> callee, caller
    (cmdb_id) or both."""
    caller = span['cmdb_id'].lower()
    if not substitutes.is_client(span):
        return [caller]
    target = substitutes.callee(span['operation_name'])
    return {'callee': [target], 'caller': [caller], 'either': [target, caller]}[rule]


def latency_ranking(spans, baseline, rule):
    """Services by the max of duration / train p50 over spans, descending, ties by name. Spans without a baseline or
    with a zero p50 are skipped."""
    best = {}
    for span in spans:
        found = baseline.get((span['cmdb_id'], span['operation_name']))
        if not found or not found['p50']:
            continue
        ratio = int(span['duration']) / found['p50']
        for service in attributed_services(span, rule):
            best[service] = max(ratio, best.get(service, ratio))
    return [service for service, _ in sorted(best.items(), key=lambda kv: (-kv[1], kv[0]))]


def fault_period_spans(spans, inject_ts):
    """Spans (dicts with a millisecond timestamp) in [inject_ts, inject_ts + 600 s)."""
    start, end = inject_ts * 1000, (inject_ts + AFTER_S) * 1000
    return [s for s in spans if start <= int(s['timestamp']) < end]


# -- RCAEval adapters ------------------------------------------------------------------------------------------------

def to_rcaeval_traces(frame):
    """RCAEval traces.csv layout from the raw Jaeger rows: startTime in microseconds, serviceName = cmdb_id, no
    methodName (RCAEval falls back to operationName)."""
    import pandas as pd
    return pd.DataFrame({'traceID': frame['trace_id'], 'spanID': frame['span_id'], 'serviceName': frame['cmdb_id'],
                         'methodName': pd.Series([None] * len(frame), index=frame.index, dtype=object),
                         'operationName': frame['operation_name'], 'startTime': frame['timestamp'] * 1000,
                         'duration': frame['duration'], 'statusCode': frame['status_code'],
                         'parentSpanID': frame['parent_span']}).reset_index(drop=True)


def to_rcaeval_metrics(frame):
    """RCAEval data.csv layout from long metric rows: a time column in seconds and one column per
    service_kpi (mean of duplicates). As RCAEval main.py: latency-50 dropped, latency-90 named latency, inf as NaN,
    forward fill, then 0."""
    import numpy as np
    wide = frame.pivot_table(index='timestamp', columns=['service_name', 'kpi_name'], values='value', aggfunc='mean')
    wide = wide.loc[:, [c for c in wide.columns if c[1] != 'latency-50']]
    wide.columns = [f'{s}_{"latency" if k == "latency-90" else k}' for s, k in wide.columns]
    wide = wide.sort_index().replace([np.inf, -np.inf], np.nan).ffill().fillna(0)
    wide.insert(0, 'time', wide.index.to_numpy())
    return wide.reset_index(drop=True)


def run_rcaeval(method, case_frame, metric_frame, inject_ts):
    """Ranked services of one RCAEval method on one case; raises whatever RCAEval raises."""
    from RCAEval.e2e import baro, microrank, tracerca
    if method == 'baro':
        ranks = baro(to_rcaeval_metrics(metric_frame), inject_time=inject_ts, dataset='re2-ob')['ranks']
    else:
        func = {'tracerca': tracerca, 'microrank': microrank}[method]
        ranks = func(to_rcaeval_traces(case_frame), inject_time=inject_ts * 1_000_000, dataset='re2-ob')['ranks']
    return dedupe(rcaeval_service(r) for r in ranks)


def short_error(error):
    return f'{type(error).__name__}: {" ".join(str(error).split())[:200]}'


# -- Results ---------------------------------------------------------------------------------------------------------

def coverage_of(query_spans, gt):
    """Whether a query trace has a span of the faulty service, server (cmdb_id) or client (named in operation_name)."""
    return any(substitutes.related(s, gt) for s in query_spans)


def expand_to_queries(case_ranks, queries, conditions=('full', 'no_metric')):
    """Result rows of the case-level methods copied to every query of the case. case_ranks[case][method] is
    {'services': [...], 'status': 'ok' | 'error: ...'}; BARO under no_metric is not_applicable."""
    rows = []
    for query in queries:
        case, gt = query['case'], gt_of(query['case'])
        for method, found in sorted(case_ranks.get(case, {}).items()):
            for condition in conditions:
                if method == 'baro' and condition == 'no_metric':
                    rows.append(dict(method=method, condition=condition, case=case, trace_id=query['trace_id'],
                                     gt=gt, status='not_applicable'))
                    continue
                rows.append(result_row(method, condition, query, found['services'], found['status']))
    return rows


def result_row(method, condition, query, services, status):
    gt = gt_of(query['case'])
    row = {'method': method, 'condition': condition, 'case': query['case'], 'trace_id': query['trace_id'], 'gt': gt,
           'status': status}
    if status == 'ok':
        rank, top1, hit, rr = score_row(gt, services)
        row.update({'rank': '' if rank is None else rank, 'top1': top1, 'R@1': hit, 'MRR': round(rr, 6)})
    return row


def mean(values):
    return round(sum(values) / len(values), 4) if values else None


def aggregate(rows):
    """n, R@1 and MRR over the scored rows (status ok), plus counts of the others."""
    scored = [r for r in rows if r['status'] == 'ok']
    return {'n': len(scored), 'R@1': mean([r['R@1'] for r in scored]), 'MRR': mean([r['MRR'] for r in scored]),
            'not_applicable': sum(r['status'] == 'not_applicable' for r in rows),
            'errors': sum(r['status'].startswith('error') for r in rows)}


def summarize(rows, coverage):
    """{method: {condition: {overall, by_gt_service, by_coverage}}}; coverage[trace_id] is True or False."""
    groups = defaultdict(list)
    for row in rows:
        groups[(row['method'], row['condition'])].append(row)
    out = {}
    for (method, condition), part in sorted(groups.items()):
        by_gt, by_cov = defaultdict(list), defaultdict(list)
        for row in part:
            by_gt[row['gt']].append(row)
            by_cov['has_gt_span' if coverage.get(row['trace_id']) else 'no_gt_span'].append(row)
        out.setdefault(method, {})[condition] = {
            'overall': aggregate(part), 'by_gt_service': {k: aggregate(v) for k, v in sorted(by_gt.items())},
            'by_coverage': {k: aggregate(v) for k, v in sorted(by_cov.items())}}
    return out


# -- Run -------------------------------------------------------------------------------------------------------------

def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 22), b''):
            digest.update(block)
    return digest.hexdigest()


def rcaeval_commit(src):
    try:
        return subprocess.run(['git', '-C', str(src), 'rev-parse', 'HEAD'], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def load_or_cut(out_dir, raw_traces, raw_metrics, cases, query_ids):
    import pandas as pd
    folder = out_dir / 'slices'
    names = ('spans', 'query-spans', 'metrics')
    if all((folder / f'{n}.csv.gz').exists() for n in names) and (folder / 'counts.json').exists():
        frames = [pd.read_csv(folder / f'{n}.csv.gz', dtype=str if n != 'metrics' else None) for n in names]
        spans, query_spans, metrics = frames
        for col in ('timestamp', 'duration'):
            spans[col] = spans[col].astype('int64')
            query_spans[col] = query_spans[col].astype('int64')
        return spans, query_spans, metrics, json.loads((folder / 'counts.json').read_text(encoding='utf-8'))
    spans, query_spans, metrics, counts = read_slices(raw_traces, raw_metrics, cases, query_ids)
    folder.mkdir(parents=True, exist_ok=True)
    for name, frame in zip(names, (spans, query_spans, metrics)):
        frame.to_csv(folder / f'{name}.csv.gz', index=False)
    (folder / 'counts.json').write_text(json.dumps(counts, indent=2) + '\n', encoding='utf-8')
    return spans, query_spans, metrics, counts


def case_level(cases, spans, metrics, baseline, methods, log):
    """{case: {method: {'services', 'status'}}} of the case-level methods; a failing method is recorded, not hidden."""
    out = {}
    span_groups = {k: v for k, v in spans.groupby('case_id')}
    metric_groups = {k: v for k, v in metrics.groupby('case_id')}
    for case in sorted(span_groups):
        inject = cases[case]['inject_ts']
        out[case] = {}
        for method in methods:
            started = time.time()
            try:
                if method in RCAEVAL_METHODS:
                    services, status = run_rcaeval(method, span_groups[case].copy(), metric_groups.get(case), inject), 'ok'
                else:
                    rule = method.split('_')[1]
                    records = fault_period_spans(span_groups[case].to_dict('records'), inject)
                    services, status = latency_ranking(records, baseline, rule), 'ok'
            except Exception as error:
                services, status = [], 'error: ' + short_error(error)
            out[case][method] = {'services': services, 'status': status}
            log(f'{case} {method} {status} top3={services[:3]} {time.time() - started:.1f}s')
    return out


def query_level(queries, query_spans, baseline, methods):
    """Result rows of the latency_query_* methods (condition-independent) and the coverage of every query."""
    by_trace = {k: v.to_dict('records') for k, v in query_spans.groupby('trace_id')}
    rows, coverage = [], {}
    for query in queries:
        records = by_trace.get(query['trace_id'], [])
        coverage[query['trace_id']] = coverage_of(records, gt_of(query['case']))
        for method in methods:
            for condition in ('full', 'no_metric'):
                if not records:
                    rows.append(dict(method=method, condition=condition, case=query['case'],
                                     trace_id=query['trace_id'], gt=gt_of(query['case']), status='error: no spans'))
                else:
                    rows.append(result_row(method, condition, query,
                                           latency_ranking(records, baseline, method.split('_')[2]), 'ok'))
    return rows, coverage


def parse_args(argv):
    values = {'--raw-traces': str(RAW_TRACES), '--raw-metrics': str(RAW_METRICS), '--roles': str(ROLES),
              '--queries': str(QUERIES), '--rcaeval-src': str(RCAEVAL_SRC), '--limit-cases': None,
              '--methods': ','.join(ALL_METHODS)}
    positional, i = [], 0
    while i < len(argv):
        if argv[i] in values and i + 1 < len(argv):
            values[argv[i]] = argv[i + 1]
            i += 1
        elif argv[i].startswith('--'):
            raise SystemExit(f'bad option {argv[i]}\n\n{__doc__}')
        else:
            positional.append(argv[i])
        i += 1
    if len(positional) != 1:
        raise SystemExit(__doc__)
    methods = values['--methods'].split(',')
    unknown = [m for m in methods if m not in ALL_METHODS]
    if unknown:
        raise SystemExit(f'unknown method {unknown}')
    return {'out_dir': Path(positional[0]), 'raw_traces': Path(values['--raw-traces']),
            'raw_metrics': Path(values['--raw-metrics']), 'roles': Path(values['--roles']),
            'queries': Path(values['--queries']), 'rcaeval_src': Path(values['--rcaeval-src']),
            'limit': int(values['--limit-cases']) if values['--limit-cases'] else None, 'methods': methods}


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    out_dir = args['out_dir']
    out_dir.mkdir(parents=True, exist_ok=True)
    if (out_dir / 'summary.json').exists():
        raise SystemExit(f'{out_dir} already holds a summary.json; choose a new folder')
    log_file = (out_dir / 'run.log').open('a', encoding='utf-8')

    def log(message):
        line = f'{time.strftime("%H:%M:%S")} {message}'
        print(line, flush=True)
        log_file.write(line + '\n')
        log_file.flush()

    cases = read_cases(args['roles'])
    queries = read_train_queries(args['queries'])
    train_cases = sorted({q['case'] for q in queries})
    if args['limit']:
        train_cases = train_cases[:args['limit']]
        queries = [q for q in queries if q['case'] in train_cases]
    bad = [c for c in train_cases if cases.get(c, {}).get('role') != 'train']
    if bad:
        raise SystemExit(f'queries of cases that are not train in the roles file: {bad}')
    log(f'{len(queries)} train queries, {len(train_cases)} train cases')
    spans, query_spans, metrics, counts = load_or_cut(out_dir, args['raw_traces'], args['raw_metrics'],
                                                      {c: cases[c] for c in cases if c in train_cases or
                                                       cases[c]['role'] != 'train'},
                                                      {q['trace_id'] for q in queries})
    log(f'slices: {counts}')
    keys = {(s['cmdb_id'], s['operation_name']) for s in spans[['cmdb_id', 'operation_name']].drop_duplicates()
            .to_dict('records')} | {(s['cmdb_id'], s['operation_name']) for s in
                                    query_spans[['cmdb_id', 'operation_name']].drop_duplicates().to_dict('records')}
    baseline_rows, baseline_counts = substitutes.build_baseline(args['raw_traces'], args['roles'], keys)
    baseline = {(b['cmdb_id'], b['operation_name']): b for b in baseline_rows}
    log(f'baseline: {baseline_counts}')
    case_methods = [m for m in args['methods'] if m in RCAEVAL_METHODS or m in LATENCY_METHODS[:3]]
    query_methods = [m for m in args['methods'] if m in LATENCY_METHODS[3:]]
    case_ranks = case_level(cases, spans, metrics, baseline, case_methods, log)
    rows = expand_to_queries(case_ranks, queries)
    query_rows, coverage = query_level(queries, query_spans, baseline, query_methods)
    rows += query_rows
    rows.sort(key=lambda r: (r['method'], r['condition'], r['case'], r['trace_id']))
    evidence.write_csv(out_dir / 'results.csv', rows, RESULT_FIELDS)
    (out_dir / 'case-ranks.json').write_text(json.dumps(case_ranks, indent=1) + '\n', encoding='utf-8')
    queries_with = Counter(coverage.values())
    summary = {
        'window': f'[inject_ts - {BEFORE_S} s, inject_ts + {AFTER_S} s) per train case; fault period for the latency '
                  f'ranker [inject_ts, inject_ts + {AFTER_S} s)',
        'note': 'RCAEval baselines see the whole case window, not only the query trace; a case result is copied to '
                'every query of the case. latency_query_* use the query trace only. TraceRCA, MicroRank and latency '
                'rankers read traces only, so full and no_metric are identical for them; BARO is not_applicable '
                'under no_metric. MicroRank returns its top 5 operations only.',
        'queries': len(queries), 'cases': len(train_cases),
        'queries_by_coverage': {'has_gt_span': queries_with[True], 'no_gt_span': queries_with[False]},
        'slice_counts': counts, 'baseline': baseline_counts, 'methods': args['methods'],
        'results': summarize(rows, coverage),
        'rcaeval': {'commit': rcaeval_commit(args['rcaeval_src']), 'src': str(args['rcaeval_src'])},
        'script_sha256': sha256_lf(Path(__file__)), 'imports_sha256': {n: sha256_lf(HERE / n) for n in IMPORTED},
        'inputs': {'raw_traces': {'path': str(args['raw_traces']), 'sha256': sha256_file(args['raw_traces'])},
                   'raw_metrics': {'path': str(args['raw_metrics']), 'sha256': sha256_file(args['raw_metrics'])},
                   'roles': {'path': str(args['roles']), 'sha256': sha256_lf(args['roles'])},
                   'queries': {'path': str(args['queries']), 'sha256': sha256_lf(args['queries'])}},
        'errors': sorted({(c, m, v['status']) for c, ms in case_ranks.items() for m, v in ms.items()
                          if v['status'] != 'ok'})}
    (out_dir / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    log('done')


if __name__ == '__main__':
    main()
