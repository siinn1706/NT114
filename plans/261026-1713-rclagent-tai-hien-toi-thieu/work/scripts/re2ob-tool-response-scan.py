"""Measure upstream RCLAgent tool-response sizes and prompt tokens for every RE2-OB error trace (CPU, no model).

usage: python -I -X utf8 re2ob-tool-response-scan.py CODE DATA ROLES_CSV TOKENIZER_DIR OUT_DIR [TRACE_ID ...]

Uses the author's unchanged code: endpoint bodies of tool_server.py over the full merged preprocessed data,
coordinator.build_trace_graph, and DedicatedAgent.self_state_verification with only chat_api scripted. The
scripted model makes exactly the call the author's prompt instructs (search_logs and search_fluctuating_metrics
for the span's own cmdb_id and timestamp); the captured round-1 prompt is counted with the pinned Qwen chat
template, as the Kaggle guard does. A second, model-independent view takes, per trace, the cheapest span prompt
plus the largest single-round response pair for any service the model can name (system-prompt list plus span
services) at any span second. Both are lower bounds: later tool rounds, consolidation and synthesis add tokens.

Each metric/log response depends only on (service, query second) over the full data, and only on rows within
1200 s / 60 s of that second, so responses are computed on exact time slices of the full data and cached.
Windows to_csv writes CRLF; responses are normalized to LF as served on Kaggle (Linux).
No label, groundtruth or result file is read. Roles come from the source-key mapping CSV (split roles only).
"""
import csv
import importlib.util
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
code, data, roles_csv, tokenizer_dir, out = (Path(a) for a in sys.argv[1:6])
only = set(sys.argv[6:])
OUTPUT_RESERVE = 512  # Self-state output budget in the harness; synthesis would reserve 1024.
CONTEXTS = (16384, 32768)
REQUEST_BUDGET = 160
out.mkdir(parents=True, exist_ok=True)
started = time.time()
spec = importlib.util.spec_from_file_location('common', Path(__file__).resolve().parent / 're2ob-endpoint-common.py')
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)


def log(*parts):
    print(f'[{time.time() - started:7.1f}s]', *parts, flush=True)


# ── Traces, cases, data slices, author endpoints and coordinator: re2ob-endpoint-common.py ──
traces = common.load_traces(data, roles_csv, only)
log('traces', len(traces), 'cases', len({t['case_id'] for t in traces}))
own, extra, trace_df = common.load_trace_rows(data, traces)
log('trace rows', len(own), 'cross-trace rows', len(extra))
metric_full, log_full = common.load_slices(data, own)
log('metric rows', len(metric_full), 'served log rows near traces', len(log_full))
serve, cache = common.author_endpoints(code, 'tool-response-scan', trace_df, metric_full, log_full)
coordinator, tokenizer, template_tokens = common.author_agents(code, tokenizer_dir, serve)
token_cache = {}


def text_tokens(body):
    if body not in token_cache:
        token_cache[body] = len(tokenizer(body.decode('utf-8'), add_special_tokens=False)['input_ids'])
    return token_cache[body]


known = list(coordinator._KNOWN_SERVICES)
rows, additivity = [], []
for number, t in enumerate(traces, 1):
    graph = coordinator.build_trace_graph(t['root_span'])
    nodes = common.walk(graph)
    agent = coordinator.build_agent_tree(graph, None, coordinator.GlobalEvidenceGraph())
    by_depth = coordinator._collect_agents_by_depth(agent)
    agents = [a for level in sorted(by_depth) for a in by_depth[level]]
    depth = max(by_depth)
    per_span, bases = [], []
    for a in agents:
        service, second, messages = common.own_round(coordinator, a)
        empty = [dict(msg, content='') if msg.get('role') == 'tool' else msg for msg in messages]
        base = template_tokens(empty)
        bodies = [msg['content'].encode('utf-8') for msg in messages if msg.get('role') == 'tool']
        estimate = base + sum(text_tokens(b) for b in bodies)
        if len(additivity) < 200 and (number % 9 == 1 or max(len(b) for b in bodies) > 20000):
            additivity.append(template_tokens(messages) - estimate)
        bases.append(base)
        per_span.append({'span_id': a.span_id, 'service': service, 'tokens': estimate,
                         'log_bytes': len(bodies[0]), 'metric_bytes': len(bodies[1])})
    span_seconds = sorted({int(str(n['raw'].get('timestamp', ''))[:10]) for n in nodes})
    services = sorted(set(known) | {str(n['raw'].get('cmdb_id', '')) for n in nodes})
    best, by_service = None, {}
    for service in services:
        for second in span_seconds:
            pair = [serve(f'{coordinator.BASE_URL}/{ep}?service_name={service}&timestamp={second}').content
                    for ep in ('search_logs', 'search_fluctuating_metrics')]
            tokens = min(bases) + sum(text_tokens(b) for b in pair)
            by_service[service] = max(by_service.get(service, 0), tokens)
            if best is None or tokens > best[0]:
                best = (tokens, service, second, len(pair[0]))
    worst_own = max(per_span, key=lambda s: s['tokens'])
    row = {'case_id': t['case_id'], 'role': t['role'], 'error_trace_row': t['row'], 'trace_id': t['trace_id'],
           'root_span': t['root_span'], 'spans': len(nodes), 'depth': depth,
           'min_requests_one_tool_round': 3 * len(nodes) + 1,
           'own_max_tokens': worst_own['tokens'], 'own_max_service': worst_own['service'],
           'own_max_log_bytes': worst_own['log_bytes'],
           'any_max_tokens': best[0], 'any_max_service': best[1], 'any_max_second': best[2], 'any_max_log_bytes': best[3]}
    for context in CONTEXTS:
        limit = context - OUTPUT_RESERVE
        row[f'own_spans_over_{context}'] = sum(s['tokens'] > limit for s in per_span)
        row[f'any_over_{context}'] = best[0] > limit
    row['any_tokens_by_service'] = json.dumps(by_service, sort_keys=True)
    rows.append(row)
    (out / 'spans').mkdir(exist_ok=True)
    (out / 'spans' / f"{t['trace_id']}.json").write_text(json.dumps(per_span, indent=1), encoding='utf-8')
    if number % 25 == 0 or number == len(traces):
        log('trace', number, '/', len(traces), 'cache', len(cache))

with (out / 'tool-response-scan.csv').open('w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)


def share(items, test):
    hit = sum(1 for i in items if test(i))
    return {'count': hit, 'of': len(items)}


summary = {'traces': len(rows), 'cases': len({r['case_id'] for r in rows}), 'output_reserve': OUTPUT_RESERVE,
           'additivity_check': {'samples': len(additivity), 'max_abs_error_tokens': max(map(abs, additivity)),
                                'errors': dict(Counter(additivity))},
           'request_budget': REQUEST_BUDGET, 'by_role': {}}
groups = defaultdict(list)
for r in rows:
    groups[r['role']].append(r)
groups['all'] = rows
for role, items in sorted(groups.items()):
    by_case = defaultdict(list)
    for r in items:
        by_case[r['case_id']].append(r)
    longest = [max(v, key=lambda r: (r['spans'], -r['error_trace_row'])) for v in by_case.values()]
    entry = {'traces': len(items), 'cases': len(by_case),
             'traces_over_request_budget_min': share(items, lambda r: r['min_requests_one_tool_round'] > REQUEST_BUDGET),
             'spans': {'min': min(r['spans'] for r in items), 'max': max(r['spans'] for r in items)}}
    for context in CONTEXTS:
        own_key, any_key = f'own_spans_over_{context}', f'any_over_{context}'
        entry[str(context)] = {
            'traces_with_own_span_overflow': share(items, lambda r: r[own_key] > 0),
            'traces_with_possible_overflow_any_service': share(items, lambda r: r[any_key]),
            'cases_all_traces_own_overflow': share(list(by_case.values()), lambda v: all(r[own_key] > 0 for r in v)),
            'cases_any_trace_own_overflow': share(list(by_case.values()), lambda v: any(r[own_key] > 0 for r in v)),
            'cases_possible_overflow_all_traces': share(list(by_case.values()), lambda v: all(r[any_key] for r in v)),
            'longest_trace_per_case_own_overflow': share(longest, lambda r: r[own_key] > 0),
            'longest_trace_per_case_possible_overflow': share(longest, lambda r: r[any_key]),
            'longest_trace_per_case_clear_and_within_budget': share(
                longest, lambda r: not r[any_key] and r['min_requests_one_tool_round'] <= REQUEST_BUDGET)}
    summary['by_role'][role] = entry
summary['own_overflow_services_16384'] = dict(Counter(r['own_max_service'] for r in rows if r['own_spans_over_16384']))
summary['possible_overflow_services_16384'] = dict(Counter(r['any_max_service'] for r in rows if r['any_over_16384']))
service_view = {}
for context in CONTEXTS:
    limit = context - OUTPUT_RESERVE
    counts = Counter(svc for r in rows for svc, tok in json.loads(r['any_tokens_by_service']).items() if tok > limit)
    service_view[str(context)] = {'traces_where_query_overflows': dict(sorted(counts.items())),
                                  'traces_overflow_excluding_cartservice': sum(any(tok > limit for svc, tok in json.loads(r['any_tokens_by_service']).items() if svc != 'cartservice') for r in rows)}
max_by_service = defaultdict(int)
for r in rows:
    for svc, tok in json.loads(r['any_tokens_by_service']).items():
        max_by_service[svc] = max(max_by_service[svc], tok)
summary['by_queried_service'] = {'max_round1_tokens': dict(sorted(max_by_service.items())), **service_view}
summary['own_max_tokens_overall'] = max(r['own_max_tokens'] for r in rows)
summary['elapsed_seconds'] = round(time.time() - started, 1)
(out / 'tool-response-scan.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, indent=2))
