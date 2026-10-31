"""Split the train traces into Kaggle sessions from span counts and the measured pilot cost; CPU only, no model.

Request count follows the trace structure: one self-state request, one tool round and one consolidation per span,
plus the synthesis (the scan's min_requests_one_tool_round), and a few extra tool rounds the pilot measured.
Time is requests times the pilot's mean seconds per request. Whole cases stay in one batch; cases alternate
between faulty services.

usage: plan-train-batches.py [PILOT_SUMMARY] [--exclude-pilot]
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCAN = HERE.parent / 'work/tool-response-scan/tool-response-scan.csv'
ROLES = HERE.parent / 'work/re2ob-case-roles-by-source-key.csv'
OUT = HERE / 'train-batches.json'
SETUP_SECONDS = 480        # install, model download, server start and protocol check; ~461 s in the pilot
REQUEST_CAP = 160          # frozen per-trace cap, retries included
DEADLINE_SECONDS = 1800    # frozen per-trace wall clock
HIGH_FACTOR = 1.25         # allowance for slower requests or more tool rounds than the pilot saw
TARGET_HIGH_SECONDS = 10 * 3600  # the high estimate of a batch stays well under a 12-hour Kaggle session


def fit(points):
    """Least-squares line through (x, y) points."""
    n = len(points)
    mx, my = sum(x for x, _ in points) / n, sum(y for _, y in points) / n
    slope = sum((x - mx) * (y - my) for x, y in points) / sum((x - mx) ** 2 for x, _ in points)
    return my - slope * mx, slope


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    summary_path = Path(args[0]) if args else HERE / 'kaggle-repair-v11-summary.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    scan = {r['trace_id']: r for r in csv.DictReader(SCAN.open(encoding='utf-8')) if r['role'] == 'train'}
    assert len(scan) == 240, len(scan)

    pilot = []
    for trace_id, record in summary['progress']['traces'].items():
        assert record['status'] == 'passed', (trace_id, record['status'])
        attempt = record['attempts'][-1]
        requests = summary['phases'][f'traces/{trace_id}']['request_count']
        pilot.append({'trace_id': trace_id, 'min_requests': int(scan[trace_id]['min_requests_one_tool_round']),
                      'requests': requests, 'seconds': attempt['finished'] - attempt['started']})
    intercept, slope = fit([(p['min_requests'], p['requests']) for p in pilot])
    seconds_per_request = sum(p['seconds'] for p in pilot) / sum(p['requests'] for p in pilot)

    excluded = {p['trace_id'] for p in pilot} if '--exclude-pilot' in sys.argv else set()
    roles_order = [r['case_id'] for r in csv.DictReader(ROLES.open(encoding='utf-8')) if r['role'] == 'train']
    # Round-robin over the faulty services, so any finished prefix of batches covers every service.
    by_service = {}
    for case in roles_order:
        by_service.setdefault(case.rsplit('_', 2)[0], []).append(case)
    case_order = [case for i in range(max(map(len, by_service.values())))
                  for cases in by_service.values() if i < len(cases) for case in [cases[i]]]
    assert sorted(case_order) == sorted(roles_order)
    traces = []
    for row in sorted(scan.values(), key=lambda r: (case_order.index(r['case_id']), int(r['error_trace_row']))):
        if row['trace_id'] in excluded:
            continue
        minimum = int(row['min_requests_one_tool_round'])
        requests = intercept + slope * minimum
        traces.append({'trace_id': row['trace_id'], 'case': row['case_id'], 'spans': int(row['spans']),
                       'min_requests': minimum, 'estimated_requests': round(requests, 1),
                       'estimated_seconds': round(requests * seconds_per_request),
                       'request_cap_headroom': REQUEST_CAP - minimum})

    by_case = {}
    for trace in traces:
        by_case.setdefault(trace['case'], []).append(trace)
    batches, current = [], []
    for case in case_order:
        group = by_case.get(case, [])
        cost = SETUP_SECONDS + sum(t['estimated_seconds'] for t in current + group)
        if current and cost * HIGH_FACTOR > TARGET_HIGH_SECONDS:
            batches.append(current)
            current = []
        current += group
    if current:
        batches.append(current)

    plan = {
        'model': {'pilot_summary': summary_path.name, 'pilot_bundle_sha256': summary['progress']['bundle_sha256'],
                  'requests': f'{intercept:.2f} + {slope:.3f} x min_requests_one_tool_round',
                  'seconds_per_request': round(seconds_per_request, 2), 'setup_seconds': SETUP_SECONDS,
                  'high_factor': HIGH_FACTOR, 'target_high_seconds': TARGET_HIGH_SECONDS,
                  'request_cap': REQUEST_CAP, 'deadline_seconds': DEADLINE_SECONDS,
                  'pilot': pilot},
        'excluded_pilot_traces': sorted(excluded),
        'totals': {'traces': len(traces), 'cases': len({t['case'] for t in traces}),
                   'spans': sum(t['spans'] for t in traces),
                   'estimated_trace_seconds': sum(t['estimated_seconds'] for t in traces),
                   'estimated_session_seconds': sum(t['estimated_seconds'] for t in traces) + SETUP_SECONDS * len(batches),
                   'max_estimated_trace_seconds': max(t['estimated_seconds'] for t in traces),
                   'min_request_cap_headroom': min(t['request_cap_headroom'] for t in traces)},
        'batches': [{'index': i + 1, 'cases': sorted({t['case'] for t in b}, key=case_order.index),
                     'traces': len(b), 'spans': sum(t['spans'] for t in b),
                     'estimated_seconds': SETUP_SECONDS + sum(t['estimated_seconds'] for t in b),
                     'high_seconds': round((SETUP_SECONDS + sum(t['estimated_seconds'] for t in b)) * HIGH_FACTOR),
                     'trace_ids': [t['trace_id'] for t in b]} for i, b in enumerate(batches)],
        'traces': traces,
    }
    assert sorted(t for b in plan['batches'] for t in b['trace_ids']) == sorted(t['trace_id'] for t in traces)
    OUT.write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: plan[k] for k in ('totals',)} | {'model': {k: v for k, v in plan['model'].items() if k != 'pilot'}},
                     indent=2))
    for b in plan['batches']:
        print(f"batch {b['index']}: {b['traces']} traces, {len(b['cases'])} cases, {b['spans']} spans, "
              f"{b['estimated_seconds'] / 3600:.2f} h (high {b['high_seconds'] / 3600:.2f} h)")


if __name__ == '__main__':
    main()
