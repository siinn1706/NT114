"""Window latency KPIs of each dev query, read by telemetry-gap.py (M2 answers, M3 table) and by the go/no-go ranker.

Usage: build-window-kpi.py DEV_SET OUT_JSON [--window-s 300] [--coverage FILE]

Rule (prereg-261102-rclagent-telemetry-gap-method.md, section 2):
- t_q = first timestamp of the query trace; window [t_q - W, t_q): nothing after t_q, no label;
- ratio of a span = duration / p50 of its (cmdb_id, operation_name) over the train pre-fault windows
  [inject_ts - 1200 s, inject_ts - 60 s) (rows in exactly one window, that window a train case), leaving the query's
  own case out; a span whose key has no baseline is dropped from the ratios;
- server side of S: spans whose cmdb_id is S and that are not client calls; client side: client spans of another
  service whose callee is S; each side gives p95 and median (sorted[min(n - 1, floor(p n))]) and its span count, or
  null under 5 spans;
- traces: window traces with a span on either side of S; in_trace: the query trace has such a span.
The output carries no case name, fault or label; inject_ts only locates the query time recorded by the coverage table.
"""
import argparse
import collections
import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
COVERAGE = HERE / 'runtime' / 'trace-coverage' / 'coverage.csv'
MIN_SPANS = 5


def import_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ms = import_script('metric_substitutes_for_window_kpi', 'analyze-metric-substitutes.py')


def quantile(values, p):
    values = np.sort(np.asarray(values, dtype=float))
    return float(values[min(len(values) - 1, int(p * len(values)))])


def side_stats(ratios):
    if len(ratios) < MIN_SPANS:
        return None
    return {'p95': quantile(ratios, 0.95), 'median': quantile(ratios, 0.5), 'spans': int(len(ratios))}


def annotate(frame):
    """Callee and client flag of each span, as in analyze-metric-substitutes.is_client."""
    operations = frame['operation_name'].astype(str)
    callee_of = {op: ms.callee(op) for op in set(operations)}
    callee = operations.map(callee_of)
    client = [bool(c) and not ms.match(s, c) for s, c in zip(frame['cmdb_id'], callee)]
    return frame.assign(operation_name=operations, callee=callee, client=client)


def touched(frame):
    """(trace_id, service) pairs: a server span's cmdb_id, a client span's callee."""
    pairs = set(zip(frame.loc[~frame['client'], 'trace_id'], frame.loc[~frame['client'], 'cmdb_id']))
    return pairs | set(zip(frame.loc[frame['client'], 'trace_id'], frame.loc[frame['client'], 'callee']))


def query_kpi(window, query_spans, baseline, window_s):
    """KPI of one query from its window spans and its own trace spans; baseline maps (cmdb_id, operation) to p50."""
    window, query_spans = annotate(window), annotate(query_spans)
    p50 = np.array([baseline.get(k, np.nan) for k in zip(window['cmdb_id'], window['operation_name'])], dtype=float)
    ratios = window.assign(ratio=window['duration'].to_numpy(dtype=float) / p50)
    known = ratios.dropna(subset=['ratio'])
    pairs = touched(window)
    in_trace = {service for _, service in touched(query_spans)}
    services = {s for _, s in pairs} | in_trace
    out = {}
    for service in sorted(str(s) for s in services):
        out[service] = {
            'in_trace': service in in_trace,
            'traces': len({t for t, s in pairs if s == service}),
            'server': side_stats(known.loc[~known['client'] & (known['cmdb_id'] == service), 'ratio'].to_numpy()),
            'client': side_stats(known.loc[known['client'] & (known['callee'] == service), 'ratio'].to_numpy())}
    return {'window_s': window_s, 'services': out}


def ranker_order(kpi):
    """Pre-query p95 ranker: max of the non-null p95 sides, frontend services excluded, ties by name."""
    score = {s: max(v[side]['p95'] for side in ('server', 'client') if v[side])
             for s, v in kpi['services'].items() if 'frontend' not in s and (v['server'] or v['client'])}
    return sorted(score, key=lambda s: (-score[s], s))


def leave_one_out_baseline(by_key, excluded_windows):
    return {key: quantile(d[~np.isin(w, excluded_windows)], 0.5)
            for key, (d, w) in by_key.items() if (~np.isin(w, excluded_windows)).any()}


def scan(raw_path, roles, queries, window_ms):
    """One pass over the raw trace file: train pre-fault rows by key, window rows and query-trace spans."""
    windows = ms.windows_of(roles)
    starts = np.array([q['t_q'] - window_ms for q in queries])
    ends = np.array([q['t_q'] for q in queries])
    wanted = {q['trace_id'] for q in queries}
    train_parts, window_parts, query_parts = collections.defaultdict(list), [], []
    columns = ['timestamp', 'trace_id', 'cmdb_id', 'operation_name', 'duration']
    for chunk in pd.read_csv(raw_path, usecols=columns, chunksize=1_000_000):
        chunk['operation_name'] = chunk['operation_name'].astype(str)
        ts = chunk['timestamp'].to_numpy()
        owners = np.zeros(len(chunk), dtype=np.int8)
        owner = np.full(len(chunk), -1, dtype=np.int16)
        is_train = np.zeros(len(chunk), dtype=bool)
        for index, (start, end, role) in enumerate(windows):
            inside = (ts >= start) & (ts < end)
            owners += inside
            owner[inside] = index
            if role == 'train':
                is_train |= inside
        keep = (owners == 1) & is_train
        if keep.any():
            part = chunk[keep].assign(window=owner[keep])
            for k, g in part.groupby(['cmdb_id', 'operation_name']):
                train_parts[k].append((g['duration'].to_numpy(np.float64), g['window'].to_numpy()))
        in_any = np.zeros(len(chunk), dtype=bool)
        for start, end in zip(starts, ends):
            in_any |= (ts >= start) & (ts < end)
        if in_any.any():
            window_parts.append(chunk[in_any])
        mine = chunk['trace_id'].isin(wanted)
        if mine.any():
            query_parts.append(chunk[mine])
    by_key = {k: (np.concatenate([d for d, _ in parts]), np.concatenate([w for _, w in parts]))
              for k, parts in train_parts.items()}
    return by_key, pd.concat(window_parts), pd.concat(query_parts)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('dev_set', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--window-s', type=int, default=300)
    parser.add_argument('--coverage', type=Path, default=COVERAGE)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.out.exists():
        raise SystemExit(f'{args.out} exists; refusing to overwrite')
    dev = json.loads(args.dev_set.read_text(encoding='utf-8'))['queries']
    coverage = {r['trace_id']: r for r in csv.DictReader(args.coverage.read_text(encoding='utf-8').splitlines())}
    roles = list(csv.DictReader(Path(ms.ROLES).read_text(encoding='utf-8-sig').splitlines()))
    inject = {r['case_id']: int(r['inject_ts']) for r in roles}
    queries = [dict(q, t_q=inject[q['case_id']] * 1000 + int(round(float(coverage[q['trace_id']]['query_start_offset_s'])
                                                                    * 1000))) for q in dev]
    by_key, window, spans = scan(ms.RAW_TRACES, ms.ROLES, queries, args.window_s * 1000)
    windows_of_case = collections.defaultdict(list)
    for index, row in enumerate(roles):
        windows_of_case[row['case_id']].append(index)
    report = {}
    for q in queries:
        own = spans[spans['trace_id'] == q['trace_id']]
        if int(own['timestamp'].min()) != q['t_q']:
            raise RuntimeError(f"{q['trace_id']}: coverage query time differs from the first span timestamp")
        rows = window[(window['timestamp'] >= q['t_q'] - args.window_s * 1000) & (window['timestamp'] < q['t_q'])]
        baseline = leave_one_out_baseline(by_key, windows_of_case[q['case_id']])
        report[q['trace_id']] = dict(trace_id=q['trace_id'], t_q_ms=q['t_q'],
                                     baseline='train p50 by (cmdb_id, operation_name), own case left out',
                                     **query_kpi(rows, own, baseline, args.window_s))
    meta = {'script_sha256': ms.sha256_lf(Path(__file__)), 'dev_set_sha256': ms.sha256_lf(args.dev_set),
            'coverage_sha256': ms.sha256_lf(args.coverage)}
    args.out.write_text(json.dumps({'meta': meta, 'queries': report}, indent=1) + '\n', encoding='utf-8', newline='\n')
    gt = {q['trace_id']: q['gt'] for q in dev}
    hits = {t: next((i for i, s in enumerate(ranker_order(k)) if ms.match(gt[t], s)), None) for t, k in report.items()}
    print(json.dumps({'queries': len(report), 'ranker_r1': sum(r == 0 for r in hits.values())}))


if __name__ == '__main__':
    main()
