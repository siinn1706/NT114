"""Exploration (no test file): R@1 and MRR of the pre-query window latency ranker that M3's table summarises, on train
queries with a leave-one-case-out baseline and on val queries with the full train baseline. Reads the coverage table of
measure-trace-coverage.py, the case roles and the raw RE2-OB trace file; no model, no run result, no test-split row.

Usage: explore-window-ranker.py OUT_JSON [--window-s 300] [--coverage FILE]

Rule (prereg-261102-rclagent-telemetry-gap-method.md, section 2):
- query time t_q = first timestamp of the query trace; window [t_q - W, t_q);
- ratio of a span = duration / p50 of its (cmdb_id, operation_name) over the train pre-fault windows
  [inject_ts - 1200 s, inject_ts - 60 s) (rows in exactly one window, that window a train case); a train query leaves
  its own case out; a key without baseline drops the span;
- server side of S: spans whose cmdb_id is S and that are not client calls; client side: client spans of another
  service whose callee is S; a side with fewer than 5 spans is null;
- p95 = sorted[min(n - 1, floor(0.95 n))]; score of S = max of its non-null sides; frontend services are not ranked;
  ties break by service name.
"""
import collections
import csv
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


ms = import_script('metric_substitutes_for_window_ranker', 'analyze-metric-substitutes.py')


def quantile(values, p):
    values = np.sort(values)
    return float(values[min(len(values) - 1, int(p * len(values)))])


def main(argv):
    out = Path(argv[0])
    window = int(argv[argv.index('--window-s') + 1]) * 1000 if '--window-s' in argv else 300_000
    coverage = Path(argv[argv.index('--coverage') + 1]) if '--coverage' in argv else COVERAGE
    queries = [r for r in csv.DictReader(coverage.read_text(encoding='utf-8').splitlines())
               if r['role'] in ('train', 'val')]
    roles = list(csv.DictReader(Path(ms.ROLES).read_text(encoding='utf-8-sig').splitlines()))
    inject = {r['case_id']: int(r['inject_ts']) for r in roles}
    windows = ms.windows_of(ms.ROLES)
    case_of_window = [r['case_id'] for r in roles]
    windows_of_case = collections.defaultdict(list)
    for index, case in enumerate(case_of_window):
        windows_of_case[case].append(index)
    tq = {q['trace_id']: inject[q['case_id']] * 1000 + int(round(float(q['query_start_offset_s']) * 1000))
          for q in queries}
    merged = []
    for a, b in sorted((t - window, t) for t in tq.values()):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    starts, ends = np.array([m[0] for m in merged]), np.array([m[1] for m in merged])
    train_parts, window_parts = collections.defaultdict(list), []
    key_code, service_code = {}, {}

    def codes(values, table):
        return np.array([table.setdefault(v, len(table)) for v in values], dtype=np.int32)

    for ch in pd.read_csv(ms.RAW_TRACES, usecols=['timestamp', 'cmdb_id', 'operation_name', 'duration'],
                          chunksize=1_000_000):
        ch['operation_name'] = ch['operation_name'].astype(str)
        ts = ch['timestamp'].to_numpy()
        owners = np.zeros(len(ch), dtype=np.int8)
        owner = np.full(len(ch), -1, dtype=np.int16)
        is_train = np.zeros(len(ch), dtype=bool)
        for index, (start, end, role) in enumerate(windows):
            inside = (ts >= start) & (ts < end)
            owners += inside
            owner[inside] = index
            if role == 'train':
                is_train |= inside
        keep = (owners == 1) & is_train
        if keep.any():
            part = ch[keep].assign(window=owner[keep])
            for key, g in part.groupby(['cmdb_id', 'operation_name']):
                train_parts[key].append((g['duration'].to_numpy(np.float64), g['window'].to_numpy()))
        i = np.searchsorted(starts, ts, side='right') - 1
        inside = (i >= 0) & (ts < ends[np.clip(i, 0, None)])
        if inside.any():
            part = ch[inside]
            pairs = list(zip(part['cmdb_id'], part['operation_name']))
            callee_of = {op: ms.callee(op) for op in set(part['operation_name'])}
            callee = [callee_of[op] for _, op in pairs]
            window_parts.append({
                'ts': part['timestamp'].to_numpy(), 'duration': part['duration'].to_numpy(np.float64),
                'key': codes(pairs, key_code), 'server': codes(part['cmdb_id'], service_code),
                'callee': codes(callee, service_code),
                'client': np.array([bool(c) and not ms.match(s, c) for (s, _), c in zip(pairs, callee)])})
        del ch
    win = {name: np.concatenate([w[name] for w in window_parts]) for name in window_parts[0]}
    del window_parts
    order = np.argsort(win['ts'], kind='stable')
    win = {name: values[order] for name, values in win.items()}
    by_key = {key: (np.concatenate([d for d, _ in parts]), np.concatenate([w for _, w in parts]))
              for key, parts in train_parts.items()}
    del train_parts
    service_name = {code: name for name, code in service_code.items()}
    baselines = {}

    def baseline(left_out):
        if left_out not in baselines:
            excluded = windows_of_case[left_out] if left_out else []
            column = np.full(len(key_code), np.nan)
            for key, code in key_code.items():
                values = by_key.get(key)
                if values is not None:
                    kept = values[0][~np.isin(values[1], excluded)]
                    if len(kept):
                        column[code] = quantile(kept, 0.5)
            baselines[left_out] = column
        return baselines[left_out]

    results = []
    for q in queries:
        t = tq[q['trace_id']]
        lo, hi = np.searchsorted(win['ts'], [t - window, t], side='left')
        left_out = q['case_id'] if q['role'] == 'train' else None
        ratio = win['duration'][lo:hi] / baseline(left_out)[win['key'][lo:hi]]
        known = ~np.isnan(ratio)
        client = win['client'][lo:hi]
        sides = collections.defaultdict(dict)
        for side, mask, column in (('server', known & ~client, win['server'][lo:hi]),
                                   ('client', known & client, win['callee'][lo:hi])):
            for code in np.unique(column[mask]):
                values = ratio[mask & (column == code)]
                if len(values) >= MIN_SPANS:
                    sides[service_name[int(code)]][side] = quantile(values, 0.95)
        score = {s: max(v.values()) for s, v in sides.items() if 'frontend' not in s}
        order = sorted(score, key=lambda s: (-score[s], s))
        rank = next((i for i, s in enumerate(order) if ms.match(q['gt'], s)), None)
        results.append({'role': q['role'], 'case_id': q['case_id'], 'trace_id': q['trace_id'], 'gt': q['gt'],
                        'coverage': q['coverage'], 'rank': rank, 'top1': order[0] if order else None})
    summary = collections.defaultdict(dict)
    for role in ('train', 'val'):
        for group in ('all', 'covered', 'none'):
            rs = [r for r in results if r['role'] == role and
                  (group == 'all' or (r['coverage'] == 'none') == (group == 'none'))]
            if rs:
                summary[role][group] = {'n': len(rs), 'R@1': round(sum(r['rank'] == 0 for r in rs) / len(rs), 3),
                                        'MRR': round(sum(1 / (r['rank'] + 1) for r in rs if r['rank'] is not None)
                                                     / len(rs), 3),
                                        'top1_cartservice': sum(r['top1'] == 'cartservice' for r in rs)}
    report = {'window_s': window // 1000, 'summary': summary, 'queries': results,
              'script_sha256': ms.sha256_lf(Path(__file__)), 'coverage_sha256': ms.sha256_lf(coverage)}
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main(sys.argv[1:])
