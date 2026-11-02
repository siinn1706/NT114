"""Measures, for every RCLAgent query (error trace) of the allowed roles, whether the query trace holds a span of the
faulty service, and how many other traces of the fault window pass through it. Reads the query list, the case roles and
the raw RE2-OB trace file; no model request, no Kaggle, no result of any run. The test role is refused.

Usage: measure-trace-coverage.py OUT_DIR [--roles-allowed train,val] [--queries FILE] [--case-roles FILE]
                                 [--raw-traces FILE]

The faulty service is the case_id prefix before the first '_'. A span is a server span of it when its cmdb_id matches
the service (analyze-evidence-loss.py match()), and a client span of it when another service's operation_name names it
(analyze-metric-substitutes.py related()). Coverage of a query: 'server' with a server span, 'client_only' with client
spans only, 'none' without either. The fault window of a case is [inject_ts, inject_ts + 600 s).

Writes coverage.csv (one row per query) and summary.json (UTF-8). It refuses to write into a folder that already holds
a summary.json.
"""
import csv
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUERIES = HERE.parent / 'work' / 'tool-response-scan' / 'tool-response-scan.csv'
CASE_ROLES = HERE.parent / 'work' / 're2ob-case-roles-by-source-key.csv'
RAW_TRACES = Path('F:/Nam/UIT/nt114-paper-artifacts/W7165616276/data/re2ob/trace/all/trace_jaeger-span.csv')
SEALED = 'test'
FAULT_WINDOW_S = 600
COVERAGE = ('server', 'client_only', 'none')


def import_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


substitutes = import_script('metric_substitutes_for_trace_coverage', 'analyze-metric-substitutes.py')
match, related, sha256_lf = substitutes.match, substitutes.related, substitutes.sha256_lf


def gt_of(case_id):
    return case_id.split('_', 1)[0]


def coverage_of(server, client):
    return 'server' if server else ('client_only' if client else 'none')


def read_queries(path, roles):
    if SEALED in roles:
        raise SystemExit(f'role {SEALED!r} is sealed')
    rows = [r for r in csv.DictReader(Path(path).read_text(encoding='utf-8-sig').splitlines()) if r['role'] in roles]
    if len({r['trace_id'] for r in rows}) != len(rows):
        raise SystemExit(f'{path}: duplicate trace_id')
    return [{'case_id': r['case_id'], 'role': r['role'], 'trace_id': r['trace_id'], 'gt': gt_of(r['case_id'])}
            for r in rows]


def read_inject(path, case_ids):
    """inject_ts (s) per case; a case listed twice must carry one value."""
    inject = {}
    for r in csv.DictReader(Path(path).read_text(encoding='utf-8-sig').splitlines()):
        if r['case_id'] in case_ids:
            if inject.setdefault(r['case_id'], int(r['inject_ts'])) != int(r['inject_ts']):
                raise SystemExit(f'{path}: {r["case_id"]} has two inject_ts')
    missing = sorted(set(case_ids) - set(inject))
    if missing:
        raise SystemExit(f'{path}: no inject_ts for {missing}')
    return inject


def gt_masks(chunk, gt, server_of):
    """Boolean server and client masks of the faulty service over a chunk."""
    server = chunk['cmdb_id'].map(lambda c: server_of(c, gt))
    client = ~server & chunk['operation_name'].map(lambda op: related({'cmdb_id': '', 'operation_name': str(op)}, gt)
                                                  == 'client')
    return server, client


def collect(raw_path, queries, inject, chunksize=2_000_000):
    """Per query: server and client span counts of the faulty service in its own trace and its first timestamp; per
    case: traces in the fault window and those of them that pass through the faulty service."""
    import pandas as pd
    server_cache = {}

    def server_of(cmdb_id, gt):
        key = (cmdb_id, gt)
        if key not in server_cache:
            server_cache[key] = match(gt, str(cmdb_id))
        return server_cache[key]

    by_trace = {q['trace_id']: q for q in queries}
    spans = {t: Counter() for t in by_trace}
    first = {}
    cases = {q['case_id']: q['gt'] for q in queries}
    window_traces = defaultdict(set)
    window_gt_traces = defaultdict(set)
    for chunk in pd.read_csv(raw_path, usecols=['timestamp', 'cmdb_id', 'trace_id', 'operation_name'],
                             chunksize=chunksize):
        own = chunk[chunk['trace_id'].isin(by_trace.keys())]
        for trace_id, rows in own.groupby('trace_id'):
            gt = by_trace[trace_id]['gt']
            server, client = gt_masks(rows, gt, server_of)
            spans[trace_id]['server'] += int(server.sum())
            spans[trace_id]['client'] += int(client.sum())
            ts = int(rows['timestamp'].min())
            first[trace_id] = min(first.get(trace_id, ts), ts)
        for case_id, gt in cases.items():
            start = inject[case_id] * 1000
            rows = chunk[(chunk['timestamp'] >= start) & (chunk['timestamp'] < start + FAULT_WINDOW_S * 1000)]
            if not len(rows):
                continue
            window_traces[case_id].update(rows['trace_id'].unique())
            server, client = gt_masks(rows, gt, server_of)
            window_gt_traces[case_id].update(rows.loc[server | client, 'trace_id'].unique())
    out = []
    for q in queries:
        t = q['trace_id']
        if t not in first:
            raise SystemExit(f'query trace {t} not in {raw_path}')
        server, client = spans[t]['server'], spans[t]['client']
        out.append(dict(q, gt_server_spans=server, gt_client_spans=client, coverage=coverage_of(server, client),
                        window_traces=len(window_traces[q['case_id']]),
                        window_traces_touching_gt=len(window_gt_traces[q['case_id']]),
                        query_start_offset_s=round((first[t] - inject[q['case_id']] * 1000) / 1000, 3)))
    return out


def summarise(rows):
    by = defaultdict(Counter)
    for r in rows:
        by[(r['role'], r['gt'])][r['coverage']] += 1
        by[(r['role'], 'ALL')][r['coverage']] += 1
    per_case = defaultdict(list)
    for r in rows:
        per_case[(r['role'], r['case_id'])].append(r['coverage'] == 'none')
    cases = defaultdict(Counter)
    for (role, _), flags in per_case.items():
        cases[role].update({'cases': 1, 'every_query_none': int(all(flags)), 'some_query_none': int(any(flags))})
    return {'by_role_and_gt': {f'{role}/{gt}': {c: n[c] for c in COVERAGE} | {'total': sum(n.values())}
                               for (role, gt), n in sorted(by.items())},
            'cases_by_role': {role: dict(n) for role, n in sorted(cases.items())}}


def parse_args(argv):
    values = {'--roles-allowed': 'train,val', '--queries': str(QUERIES), '--case-roles': str(CASE_ROLES),
              '--raw-traces': str(RAW_TRACES)}
    positional, i = [], 0
    while i < len(argv):
        if argv[i] in values:
            if i + 1 >= len(argv):
                raise SystemExit(f'{argv[i]} needs a value')
            values[argv[i]] = argv[i + 1]
            i += 2
        else:
            positional.append(argv[i])
            i += 1
    if len(positional) != 1:
        raise SystemExit(__doc__)
    return {'out': Path(positional[0]), 'roles': [r for r in values['--roles-allowed'].split(',') if r],
            'queries': Path(values['--queries']), 'case_roles': Path(values['--case-roles']),
            'raw_traces': Path(values['--raw-traces'])}


def main(argv):
    args = parse_args(argv)
    if (args['out'] / 'summary.json').exists():
        raise SystemExit(f'{args["out"]} already holds a summary.json')
    queries = read_queries(args['queries'], args['roles'])
    inject = read_inject(args['case_roles'], {q['case_id'] for q in queries})
    rows = collect(args['raw_traces'], queries, inject)
    args['out'].mkdir(parents=True, exist_ok=True)
    with (args['out'] / 'coverage.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {'roles': args['roles'], 'queries': len(rows), 'fault_window_s': FAULT_WINDOW_S,
               'inputs': {'queries': {'path': str(args['queries']), 'sha256': sha256_lf(args['queries'])},
                          'case_roles': {'path': str(args['case_roles']), 'sha256': sha256_lf(args['case_roles'])},
                          'raw_traces': {'path': str(args['raw_traces']),
                                         'bytes': args['raw_traces'].stat().st_size},
                          'script_sha256': sha256_lf(Path(__file__))}} | summarise(rows)
    (args['out'] / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n',
                                              encoding='utf-8')
    print(json.dumps(summary['by_role_and_gt'], indent=1))
    print(json.dumps(summary['cases_by_role']))


if __name__ == '__main__':
    main(sys.argv[1:])
