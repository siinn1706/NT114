"""Completion within the harness budget, scores on valid completions, both-passed pairs and the logs of budget stops.

Usage: analyze-completion-and-budget-stops.py OUT_DIR LABEL RESULTS_ZIP MANIFEST [LABEL RESULTS_ZIP MANIFEST ...]

Reads the same ZIPs and manifests as analyze-missing-source-results.py, through its load(), so the same SHA256,
bundle and duplicate checks apply; it changes nothing in the screening rule, where a failed run counts 0. Writes:

- completion.csv: per package label (and 'all') and condition, the runs, valid completions (passed, scored, integrity
  ok), the completion rate, failures by cause, unscored passed runs and integrity problems kept apart, and R@1/MRR
  over valid completions with their count.
- pairs.json: per comparison and scope, the (case, trace, seed) pairs whose two runs are both valid completions; the
  mean over pairs and the mean of per-case means. A sensitivity check: filtering on completion can bias the sample.
- cases.json: per comparison and case, the all-run delta, the seeds lost to a harness cap and the both-passed delta.
- budget-stops.json: for every run stopped by a harness cap, where it stopped and what it queried, with the run of
  the reference condition on the same trace and seed.
"""
import csv
import hashlib
import importlib.util
import json
import statistics
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('missing_source_analyzer', HERE / 'analyze-missing-source-results.py')
analyzer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyzer)

CAUSES = (('tool_round_cap', 'Per-span tool round budget exceeded'),
          ('request_budget', 'Model request budget exhausted'),
          ('deadline', 'RCLAgent deadline exceeded'),
          ('context_overflow', 'Context overflow'),
          ('malformed_tool_call', 'Invalid structured response'),
          ('agent_output', 'Invalid agent JSON output'))
CAPS = ('tool_round_cap', 'request_budget', 'deadline')
CONDITIONS = ('metric', 'no_metric', 'metric_no_log')
# Bytes an endpoint returns when it holds no row (absent sources answer with the same bytes).
NO_ROWS = {'log_id,timestamp,cmdb_id,log_name,value\n', '{"message":"No matching records found."}\n'}


def cause(row):
    if row['status'] == 'passed':
        return None
    for name, marker in CAUSES:
        if marker in row['reason']:
            return name
    return 'other' if row['status'] == 'failed' else row['status']


def valid(row):
    return row['status'] == 'passed' and row['scored'] and row['integrity'] == 'ok'


def mean(values):
    return statistics.mean(values) if values else None


def completion(rows, labels):
    out = []
    for label in labels + ['all']:
        for condition in CONDITIONS:
            group = [r for r in rows if r['condition'] == condition and label in ('all', r['label'])]
            done = [r for r in group if valid(r)]
            causes = Counter(cause(r) for r in group if r['status'] != 'passed')
            out.append({'package': label, 'condition': condition, 'runs': len(group), 'valid_completions': len(done),
                        'completion_rate': len(done) / len(group) if group else None,
                        **{f'failed_{name}': causes.get(name, 0) for name, _ in CAUSES},
                        'failed_other': causes.get('other', 0),
                        'pending_or_running': causes.get('pending', 0) + causes.get('running', 0),
                        'unscored_passed': sum(r['status'] == 'passed' and not r['scored'] for r in group),
                        'integrity_problems': sum(r['integrity'] != 'ok' for r in group),
                        'R@1_all_runs': mean([r['R@1'] for r in group]), 'MRR_all_runs': mean([r['MRR'] for r in group]),
                        'R@1_valid': mean([r['R@1'] for r in done]), 'MRR_valid': mean([r['MRR'] for r in done]),
                        'n_valid': len(done)})
    return out


def pairs(rows, labels):
    by = {(r['case'], r['trace_id'], r['seed'], r['condition']): r for r in rows}
    out = {}
    for name, (ref, cut) in analyzer.PAIRS.items():
        out[name] = {}
        for label in labels + ['all']:
            matched = [(by[c, t, s, ref], by[c, t, s, cut]) for (c, t, s, k) in by
                       if k == ref and (c, t, s, cut) in by and label in ('all', by[c, t, s, k]['label'])]
            both = [(a, b) for a, b in matched if valid(a) and valid(b)]
            per_case = defaultdict(list)
            for a, b in both:
                per_case[a['case']].append((b['R@1'] - a['R@1'], b['MRR'] - a['MRR']))
            case_means = {c: {'pairs': len(d), 'delta_R@1': mean([x[0] for x in d]), 'delta_MRR': mean([x[1] for x in d])}
                          for c, d in sorted(per_case.items())}
            out[name][label] = {
                'reference': ref, 'removed': cut, 'matched_pairs': len(matched), 'both_valid_pairs': len(both),
                'cases': len(case_means),
                'pair_mean_delta_R@1': mean([b['R@1'] - a['R@1'] for a, b in both]),
                'pair_mean_delta_MRR': mean([b['MRR'] - a['MRR'] for a, b in both]),
                'case_mean_delta_R@1': mean([v['delta_R@1'] for v in case_means.values()]),
                'case_mean_delta_MRR': mean([v['delta_MRR'] for v in case_means.values()]),
                'per_case': case_means}
    return out


def cases(rows):
    by = {(r['case'], r['seed'], r['condition']): r for r in rows}
    out = {}
    for name, (ref, cut) in analyzer.PAIRS.items():
        out[name] = {}
        for case in sorted({r['case'] for r in rows}):
            seeds = sorted(s for (c, s, k) in by if c == case and k == ref and (c, s, cut) in by)
            if not seeds:
                continue
            duo = [(by[case, s, ref], by[case, s, cut]) for s in seeds]
            both = [(a, b) for a, b in duo if valid(a) and valid(b)]
            out[name][case] = {
                'package': duo[0][0]['label'], 'seeds': len(seeds),
                'all_runs_delta_R@1': mean([b['R@1'] - a['R@1'] for a, b in duo]),
                'all_runs_delta_MRR': mean([b['MRR'] - a['MRR'] for a, b in duo]),
                'removed_failed': {str(s): cause(b) for s, (a, b) in zip(seeds, duo) if b['status'] != 'passed'},
                'reference_failed': {str(s): cause(a) for s, (a, b) in zip(seeds, duo) if a['status'] != 'passed'},
                'both_valid_pairs': len(both),
                'both_valid_delta_R@1': mean([b['R@1'] - a['R@1'] for a, b in both]),
                'both_valid_delta_MRR': mean([b['MRR'] - a['MRR'] for a, b in both])}
    return out


def payload_of(event):
    payload = event['payload']
    return json.loads(payload) if isinstance(payload, str) else payload


def tool_calls(event):
    body = event.get('body')
    try:
        while isinstance(body, str):
            body = json.loads(body)
        return [(c['function']['name'], c['function']['arguments'])
                for c in body['choices'][0]['message'].get('tool_calls') or []]
    except (ValueError, KeyError, IndexError, TypeError):
        return None


def timeline(events):
    """Logical model calls (attempt 0) in log order, each with its malformed-call retries, its tool calls and results."""
    calls, current = [], None
    for event in events:
        kind = event.get('kind')
        if kind == 'request' and event.get('phase') == 'trace':
            if event.get('attempt'):
                current['retries'] += 1
                continue
            current = {'number': event['number'], 'span_id': event.get('span_id'), 'operation': event.get('operation'),
                       'retries': 0, 'calls': None, 'results': []}
            calls.append(current)
        elif kind == 'response' and current is not None:
            parsed = tool_calls(event)
            current['calls'] = parsed if parsed is not None else current['calls']
        elif kind == 'tool_result' and current is not None:
            params, response = event.get('params') or {}, event.get('response') or ''
            current['results'].append({'name': event['name'], 'service_name': params.get('service_name'),
                                       'timestamp': params.get('timestamp'), 'rows': bool(response) and response not in NO_ROWS,
                                       'sha256': hashlib.sha256(response.encode()).hexdigest()})
    return calls


def run_profile(zipped, rid):
    events = [json.loads(line) for line in zipped.read(f'run/traces/{rid}/events.jsonl').decode().splitlines()]
    graph = json.loads(zipped.read(f'run/traces/{rid}/trace-graph.json'))
    spans = len(analyzer_walk(graph))
    calls = timeline(events)
    done = Counter(e.get('operation') for e in events if e.get('kind') == 'agent_complete')
    per_span = Counter(c['span_id'] for c in calls if c['operation'] == 'self_state_verification')
    return {'events': events, 'calls': calls, 'spans': spans, 'done': done, 'per_span': per_span,
            'requests': sum(1 + c['retries'] for c in calls),
            'seconds': round(events[-1].get('time', 0) - events[0].get('time', 0)) if events else 0}


def analyzer_walk(node):
    return [node] + [d for child in node['children'] for d in analyzer_walk(child)]


def classify_rounds(conversation):
    """Each tool round of one span conversation: new rows, a query already made in this conversation, or empty."""
    seen_queries, seen_rows, out = set(), set(), []
    for call in conversation:
        if not call['results']:
            continue
        queries = [(r['name'], r['service_name'], r['timestamp']) for r in call['results']]
        new_rows = [r for r in call['results'] if r['rows'] and r['sha256'] not in seen_rows]
        repeated = all(q in seen_queries for q in queries)
        out.append({'request': call['number'], 'queries': [list(q) for q in queries],
                    'rows': [r['rows'] for r in call['results']],
                    'kind': 'new_rows' if new_rows else 'repeated_query' if repeated else 'new_query_no_rows'})
        seen_queries.update(queries)
        seen_rows.update(r['sha256'] for r in call['results'] if r['rows'])
    return out


def budget_stop(zipped, row, reference):
    profile = run_profile(zipped, row['run_id'])
    calls = profile['calls']
    last = calls[-1]
    conversation = [c for c in calls if (c['span_id'], c['operation']) == (last['span_id'], last['operation'])]
    queries = [(r['name'], r['service_name'], r['timestamp']) for c in calls for r in c['results']]
    rows_seen = [r['sha256'] for c in calls for r in c['results'] if r['rows']]
    stop = {
        'run_id': row['run_id'], 'package': row['label'], 'case': row['case'], 'condition': row['condition'],
        'seed': row['seed'], 'cause': cause(row), 'reason': row['reason'], 'spans': profile['spans'],
        'requests_including_retries': profile['requests'], 'logical_calls': len(calls),
        'malformed_call_retries': sum(c['retries'] for c in calls), 'seconds': profile['seconds'],
        'calls_by_operation': dict(Counter(str(c['operation']) for c in calls)),
        'completed': {str(k): v for k, v in profile['done'].items()},
        'self_state_calls_per_span': {'mean': mean(list(profile['per_span'].values())),
                                      'max': max(profile['per_span'].values(), default=0)},
        'tool_rounds': sum(bool(c['results']) for c in calls), 'tool_results': len(queries),
        'distinct_queries': len(set(queries)), 'repeated_queries_in_run': len(queries) - len(set(queries)),
        'results_with_rows': len(rows_seen), 'distinct_results_with_rows': len(set(rows_seen)),
        'stop_span': last['span_id'], 'stop_operation': last['operation'], 'stop_request': last['number'],
        'stop_step_in_conversation': len(conversation), 'stop_model_calls': last['calls'],
        'stop_conversation_rounds': classify_rounds(conversation)}
    if stop['cause'] == 'request_budget':
        # The upstream order: every span's self-state check, one consolidation per span, then one final synthesis.
        remaining = profile['spans'] - profile['done'].get('consolidate', 0)
        stop['projected_requests_to_finish'] = len(calls) + remaining + 1 + stop['malformed_call_retries']
    if reference is not None:
        ref = run_profile(zipped, reference['run_id'])
        stop['reference'] = {'run_id': reference['run_id'], 'status': reference['status'], 'reason': reference['reason'],
                             'requests_including_retries': ref['requests'], 'seconds': ref['seconds'],
                             'self_state_calls_per_span': {'mean': mean(list(ref['per_span'].values())),
                                                           'max': max(ref['per_span'].values(), default=0)},
                             'stop_span_self_state_calls': ref['per_span'].get(last['span_id'], 0)}
    return stop


def main():
    out_dir = Path(sys.argv[1])
    triples = sys.argv[2:]
    if not triples or len(triples) % 3:
        raise SystemExit(__doc__)
    rows, labels, archives = [], [], {}
    for i in range(0, len(triples), 3):
        label, archive, manifest = triples[i:i + 3]
        labels.append(label)
        for row in analyzer.load(archive, manifest):
            row['label'] = label
            archives[row['run_id']] = archive
            rows.append(row)
    duplicates = [k for k, n in Counter(r['run_id'] for r in rows).items() if n > 1]
    if duplicates:
        raise SystemExit('Duplicate runs: ' + '; '.join(duplicates))
    out_dir.mkdir(parents=True, exist_ok=True)
    table = completion(rows, labels)
    with (out_dir / 'completion.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    for name, value in (('pairs.json', pairs(rows, labels)), ('cases.json', cases(rows))):
        (out_dir / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    by = {(r['trace_id'], r['seed'], r['condition']): r for r in rows}
    stops = []
    for row in rows:
        if cause(row) in CAPS:
            with zipfile.ZipFile(archives[row['run_id']]) as zipped:
                stops.append(budget_stop(zipped, row, by.get((row['trace_id'], row['seed'], 'metric'))))
    (out_dir / 'budget-stops.json').write_text(json.dumps(stops, indent=2) + '\n', encoding='utf-8')
    for line in table:
        print(line['package'], line['condition'], f"{line['valid_completions']}/{line['runs']}",
              {k: v for k, v in line.items() if k.startswith('failed_') and v})
    print('budget stops:', Counter(s['cause'] for s in stops))


if __name__ == '__main__':
    main()
