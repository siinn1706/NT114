"""Check and score the missing-source Kaggle sessions without issuing any model request.

Usage: analyze-missing-source-results.py OUT_DIR RESULTS_ZIP MANIFEST [RESULTS_ZIP MANIFEST ...]

Each ZIP must match its recorded SHA256 and must have run the bundle whose .sha256 sits next to the manifest; its
progress may name no run outside that manifest, and no run or (case, seed, condition) may appear twice. Otherwise
the analysis stops before writing anything.

Per run: the final status, the seed of every trace-phase request, the malformed-tool-call retry chain walked in log
order, the source recorded on every tool_result against the run's condition, the author scorer's R@1/R@3/MRR (a
failed or unscored run counts 0) and whether the top-1 name carries a '-N' suffix. An unparseable events line is an
integrity problem of that run. Then paired deltas (same case and seed) and the screening rule fixed before the
runs; a comparison with a (case, seed) missing either condition is not evaluable. The summary is provisional while
a session has not passed, a run is pending or running, a passed run has no score, or a run has an integrity problem
(a failed run that stopped before writing events is not one).
"""
import csv
import hashlib
import json
import re
import statistics
import sys
import zipfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASELINES = HERE.parent / 'work/pilot-trace-analysis/metric-dev-rank.csv'
SOURCE_OF = {'search_logs': 'logs', 'search_fluctuating_metrics': 'metric'}
# Comparison -> (reference condition, condition with one source removed).
PAIRS = {'metric_removed': ('metric', 'no_metric'), 'logs_removed': ('metric', 'metric_no_log')}
R1_DROP, MRR_DROP = 0.125, 0.10
CASE_R1, CASE_MRR = 1 / 3, 0.10
RETRY_LIMIT = 3
# The worker checks both before sending, so a retry event may be the last thing logged before one of these stops.
# The deadline message names its length ("30-minute ..."), so stops are matched by substring.
STOPS_BEFORE_SEND = ('Model request budget exhausted', 'RCLAgent deadline exceeded')
BUNDLE_SHA256 = 'rclagent-kaggle-bundle.zip.sha256'


def score(text):
    found = {k: float(v) for k, v in re.findall(r'^\s*(R@1|R@3|MRR)\s*:\s*([0-9.]+)', text, re.M)}
    return found if {'R@1', 'R@3', 'MRR'} <= found.keys() else None


def retry_seed(seed, first, attempt):
    """The seed of a malformed-tool-call retry as smoke-worker.py derives it, written out again here."""
    digest = hashlib.sha256(f'{seed}:{first}:{attempt}'.encode()).digest()
    return int.from_bytes(digest[:4], 'big') & 0x7fffffff


def check_retries(seed, events):
    """Walk trace requests, retry events and fatal stops in log order; return (requests with a wrong seed, problems).

    Attempt 0 carries the run seed and starts a chain. A retry event names the request just before it, that request's
    attempt + 1 (at most RETRY_LIMIT) and the derived seed. The retried request follows it directly with that attempt
    and seed, and retry_of set to the chain's first request.
    """
    bad_seed, problems, previous, pending, first = 0, [], None, None, None
    for event in events:
        kind = event.get('kind')
        if kind == 'request' and event.get('phase') == 'trace':
            number, attempt, sent = event.get('number'), event.get('attempt') or 0, event['payload'].get('seed')
            if not attempt:
                if pending:
                    problems.append(f'request {number} starts a new chain after retry of request {pending.get("number")}')
                bad_seed += sent != seed
                first = number
            elif not pending or attempt != pending.get('next_attempt'):
                problems.append(f'request {number} attempt {attempt} does not follow a matching retry event')
            elif event.get('retry_of') != first:
                problems.append(f'request {number} retry_of {event.get("retry_of")}, but its chain starts at {first}')
            else:
                bad_seed += sent != pending.get('next_seed')
            previous, pending = event, None
        elif kind == 'malformed_tool_call_retry':
            number = event.get('number')
            if pending:
                problems.append(f'retry event for request {number} follows another retry event')
            if previous is None or number != previous.get('number'):
                problems.append(f'retry event names request {number}, but the last request is '
                                f'{previous and previous.get("number")}')
            else:
                attempt = (previous.get('attempt') or 0) + 1
                if event.get('next_attempt') != attempt or attempt > RETRY_LIMIT:
                    problems.append(f'retry event for request {number} gives attempt {event.get("next_attempt")}, '
                                    f'expected {attempt} of at most {RETRY_LIMIT}')
                elif event.get('next_seed') != retry_seed(seed, first, attempt):
                    problems.append(f'retry event for request {number} gives seed {event.get("next_seed")}, '
                                    f'expected {retry_seed(seed, first, attempt)}')
            pending = event
        elif kind == 'fatal':
            if pending and not any(stop in str(event.get('reason', '')) for stop in STOPS_BEFORE_SEND):
                problems.append(f'retry of request {pending.get("number")} is followed by stop: {event.get("reason")}')
            pending = None
    if pending:
        problems.append(f'retry of request {pending.get("number")} has neither a retried request nor a stop after it')
    return bad_seed, problems


def check_run(zipped, run):
    rid, problems, events = run['run_id'], [], []
    for number, line in enumerate(zipped.read(f'run/traces/{rid}/events.jsonl').decode().splitlines(), 1):
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            problems.append(f'unparseable events line {number}')
    requests = [e for e in events if e.get('kind') == 'request' and e.get('phase') == 'trace']
    bad_seed, chain = check_retries(run['seed'], events)
    if bad_seed:
        problems.append(f'{bad_seed}/{len(requests)} requests with another seed')
    problems += chain
    retries = sum(e.get('kind') == 'malformed_tool_call_retry' for e in events)
    tools = [e for e in events if e.get('kind') == 'tool_result']
    bad_source = sum(e.get('source') != run[SOURCE_OF[e['name']]] for e in tools)
    if bad_source:
        problems.append(f'{bad_source}/{len(tools)} tool results with another source')
    return len(requests), len(tools), retries, problems


def top1(zipped, rid):
    try:
        names = json.loads(zipped.read(f'run/traces/{rid}/result.json'))['root_causes']
    except (KeyError, ValueError):
        return ''
    return names[0] if names else ''


def load(archive, manifest):
    archive, manifest = Path(archive), Path(manifest)
    recorded = Path(str(archive) + '.sha256').read_text().split()[0]
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual != recorded:
        raise SystemExit(f'{archive}: SHA256 {actual} differs from recorded {recorded}')
    sidecar = manifest.parent / BUNDLE_SHA256
    if not sidecar.exists():
        raise SystemExit(f'{manifest}: no {BUNDLE_SHA256} next to it; the results cannot be bound to a bundle')
    bundle = sidecar.read_text().split()[0]
    runs = json.loads(manifest.read_text())['runs']
    rows = []
    with zipfile.ZipFile(archive) as zipped:
        names = set(zipped.namelist())
        if 'run/progress.json' not in names:
            raise SystemExit(f'{archive}: no run/progress.json')
        recorded_progress = json.loads(zipped.read('run/progress.json'))
        if recorded_progress.get('bundle_sha256') != bundle:
            raise SystemExit(f'{archive} ran bundle {recorded_progress.get("bundle_sha256")}, '
                             f'but {manifest} belongs to bundle {bundle}')
        progress = recorded_progress['traces']
        extra = sorted(set(progress) - {run['run_id'] for run in runs})
        if extra:
            raise SystemExit(f'{archive}: runs absent from {manifest}: {", ".join(extra)}')
        for run in runs:
            rid = run['run_id']
            state = progress.get(rid, {})
            status = state.get('status', 'pending')
            row = {k: run[k] for k in ('run_id', 'case', 'trace_id', 'condition', 'seed')}
            row.update(status=status, reason=state.get('reason', ''), attempts=len(state.get('attempts', [])),
                       results_zip=archive.name, results_sha256=actual, bundle_sha256=bundle)
            if f'run/traces/{rid}/events.jsonl' in names:
                row['requests'], row['tool_results'], row['retries'], problems = check_run(zipped, run)
                row['integrity'] = '; '.join(problems) or 'ok'
            else:
                row.update(requests=0, tool_results=0, retries=0, integrity='no events')
            path = f'run/scoring/{rid}/author-score.txt'
            scored = score(zipped.read(path).decode('utf-8', 'replace')) if path in names else None
            row['scored'] = scored is not None
            row.update(scored or {'R@1': 0.0, 'R@3': 0.0, 'MRR': 0.0})
            row['top1'] = top1(zipped, rid)
            row['suffixed_top1'] = bool(re.search(r'-\d+$', row['top1']))
            rows.append(row)
    return rows


def session(archive):
    """The session's final status.json; a missing one means the session never finished."""
    archive = Path(archive)
    with zipfile.ZipFile(archive) as zipped:
        state = json.loads(zipped.read('run/status.json')) if 'run/status.json' in zipped.namelist() else {}
    return {'results_zip': str(archive), 'results_sha256': Path(str(archive) + '.sha256').read_text().split()[0],
            'status': state.get('status', 'missing'), 'stage': state.get('stage'), 'error': state.get('error')}


def screen(rows):
    by = {(r['case'], r['seed'], r['condition']): r for r in rows}
    cases = sorted({r['case'] for r in rows})
    seeds = sorted({r['seed'] for r in rows})
    out = {}
    for name, (ref, cut) in PAIRS.items():
        per_case, seed_drops = {}, {}
        missing = [[case, s] for case in cases for s in seeds if (case, s, ref) not in by or (case, s, cut) not in by]
        for case in cases:
            deltas = [(by[case, s, cut]['R@1'] - by[case, s, ref]['R@1'], by[case, s, cut]['MRR'] - by[case, s, ref]['MRR'])
                      for s in seeds if (case, s, ref) in by and (case, s, cut) in by]
            if not deltas:
                continue
            d_r1 = statistics.mean(d[0] for d in deltas)
            d_mrr = statistics.mean(d[1] for d in deltas)
            per_case[case] = {'pairs': len(deltas), 'delta_R@1': d_r1, 'delta_MRR': d_mrr,
                              'affected': abs(d_r1) >= CASE_R1 - 1e-9 or abs(d_mrr) >= CASE_MRR - 1e-9,
                              'direction': 'down' if (d_r1 < 0 or (d_r1 == 0 and d_mrr < 0)) else
                                           'up' if (d_r1 > 0 or d_mrr > 0) else 'none'}
        for s in seeds:
            pairs = [(by[c, s, ref], by[c, s, cut]) for c in cases if (c, s, ref) in by and (c, s, cut) in by]
            if pairs:
                seed_drops[s] = {'delta_R@1': statistics.mean(b['R@1'] - a['R@1'] for a, b in pairs),
                                 'delta_MRR': statistics.mean(b['MRR'] - a['MRR'] for a, b in pairs),
                                 'cases': len(pairs)}
        overall_r1 = statistics.mean(v['delta_R@1'] for v in seed_drops.values()) if seed_drops else 0.0
        overall_mrr = statistics.mean(v['delta_MRR'] for v in seed_drops.values()) if seed_drops else 0.0
        big = overall_r1 <= -R1_DROP + 1e-9 or overall_mrr <= -MRR_DROP + 1e-9
        same_dir = sum(v['delta_R@1'] < 0 or v['delta_MRR'] < 0 for v in seed_drops.values())
        affected_down = sum(v['affected'] and v['direction'] == 'down' for v in per_case.values())
        evaluable = not missing and bool(seed_drops)
        out[name] = {'reference': ref, 'removed': cut, 'delta_R@1': overall_r1, 'delta_MRR': overall_mrr,
                     'seeds_with_drop': same_dir, 'seeds': len(seed_drops), 'affected_cases_down': affected_down,
                     'opens_direction': bool(big and same_dir >= 2 and affected_down >= 2) if evaluable else None,
                     'evaluable': evaluable, 'missing_pairs': missing, 'per_seed': seed_drops, 'per_case': per_case}
    return out


def baselines(rows):
    traces = {r['trace_id'][:8] for r in rows}
    found = {}
    with BASELINES.open(encoding='utf-8') as handle:
        for line in csv.DictReader(handle):
            if line['trace'] in traces:
                found[line['trace']] = {'case': line['case'], 'span_count_rank': line['heur_rank'] or None,
                                        'metric_deviation_rank_in_trace': line['rank_trace'] or None,
                                        'metric_deviation_rank_all': line['rank_all'] or None}
    return found


def main():
    out_dir = Path(sys.argv[1])
    pairs = sys.argv[2:]
    rows = [row for i in range(0, len(pairs), 2) for row in load(pairs[i], pairs[i + 1])]
    duplicates = [key for key, n in Counter(r['run_id'] for r in rows).items() if n > 1]
    duplicates += [key for key, n in Counter((r['case'], r['seed'], r['condition']) for r in rows).items() if n > 1]
    if duplicates:
        raise SystemExit('Duplicate runs: ' + '; '.join(map(str, duplicates)))
    sessions = [session(pairs[i]) for i in range(0, len(pairs), 2)]
    unscored = [r['run_id'] for r in rows if r['status'] == 'passed' and not r['scored']]
    doubtful = [r for r in rows if r['integrity'] != 'ok' and (r['integrity'], r['status']) != ('no events', 'failed')]
    provisional = (any(s['status'] != 'passed' for s in sessions) or bool(unscored) or bool(doubtful)
                   or any(r['status'] in ('pending', 'running') for r in rows))
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / 'runs.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    conditions = sorted({r['condition'] for r in rows})
    summary = {
        'runs': len(rows),
        'status': {s: sum(r['status'] == s for r in rows) for s in sorted({r['status'] for r in rows})},
        'integrity_problems': [(r['run_id'], r['integrity']) for r in rows if r['integrity'] != 'ok'],
        'suffixed_top1': sum(r['suffixed_top1'] for r in rows),
        'by_condition': {c: {m: statistics.mean(r[m] for r in rows if r['condition'] == c) for m in ('R@1', 'R@3', 'MRR')}
                         | {'runs': sum(r['condition'] == c for r in rows)} for c in conditions},
        'screening': screen(rows),
        'cpu_baselines_by_trace': baselines(rows),
        'sessions': sessions,
        'unscored_passed': unscored,
        'provisional': provisional,
        'note': 'Descriptive; no statistical test. Failed or unscored runs count 0; unscored passed runs, pending '
                'runs, integrity problems or an unfinished session make the summary provisional.',
    }
    (out_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: summary[k] for k in ('runs', 'status', 'integrity_problems', 'suffixed_top1', 'by_condition',
                                              'unscored_passed', 'provisional')}, indent=1))
    for name, s in summary['screening'].items():
        print(name, {k: s[k] for k in s if k not in ('per_seed', 'per_case')})


if __name__ == '__main__':
    main()
