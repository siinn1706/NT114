"""Impact of candidate search_logs budgets on every RE2-OB error trace (CPU, no model).

usage: python -I -X utf8 re2ob-tool-result-budget-impact.py CODE DATA ROLES_CSV TOKENIZER_DIR OUT_DIR PRIOR_SCAN_CSV [TRACE_ID ...]

Same pipeline as re2ob-tool-response-scan.py (author endpoint bodies over the full merged data, real
build_trace_graph and self_state_verification with a scripted chat_api, pinned Qwen chat template), plus the
schemes of tool-result-budget.py at several budgets. Per trace it records the instructed (own-span) queries, which
must stay byte-identical, and every service the model can name at every span second. Per distinct changed log
response it records what each scheme keeps and drops. Unbudgeted numbers are checked against the prior scan CSV.
No label, groundtruth or result file is read.
"""
import csv
import importlib.util
import io
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
code, data, roles_csv, tokenizer_dir, out, prior_csv = (Path(a) for a in sys.argv[1:7])
only = set(sys.argv[7:])
OUTPUT_RESERVE = 512
CONTEXT = 16384
ROUNDS = 4
BUDGETS = (1024, 2048, 4096, 8192)
out.mkdir(parents=True, exist_ok=True)
started = time.time()
spec = importlib.util.spec_from_file_location('budget', Path(__file__).resolve().parents[2] / 'kaggle/tool-result-budget.py')
budget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(budget)
SCHEMES = list(budget.SCHEMES)
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
serve, cache = common.author_endpoints(code, 'tool-result-budget-impact', trace_df, metric_full, log_full)
coordinator, tokenizer, template_tokens = common.author_agents(code, tokenizer_dir, serve)
token_cache = {}


def count(text):
    if text not in token_cache:
        token_cache[text] = len(tokenizer(text, add_special_tokens=False)['input_ids'])
    return token_cache[text]


# Parsing and merging depend only on the body; reuse them across schemes and budgets.
_parse, _exact, _template = budget.parse, budget.merge_exact, budget.merge_template
parsed_cache, merge_cache = {}, {}
budget.parse = lambda body: parsed_cache[body] if body in parsed_cache else parsed_cache.setdefault(body, _parse(body))
budget.merge_exact = lambda rows: merge_cache.setdefault(('exact', id(rows)), _exact(rows))
budget.merge_template = lambda rows: merge_cache.setdefault(('template', id(rows)), _template(rows))


def describe(rows, output):
    """What a budgeted response keeps relative to the original rows."""
    errors = [r[4] for r in rows if budget.is_error_like(r[4])]
    info = {'rows': len(rows), 'error_rows': len(errors), 'error_values': len(set(errors))}
    if output is None:
        return {**info, 'form': 'stop', 'rows_covered': 0, 'rows_verbatim': 0, 'error_rows_dropped': len(errors),
                'error_values_not_verbatim': len(set(errors)), 'units_shown': 0, 'units_total': None}
    note, body = output.split('\n', 1)
    table = list(csv.reader(io.StringIO(body, newline='')))
    header, shown = table[0], table[1:]
    if header == budget.HEADER:
        kept = Counter(r[4] for r in shown)
        covered, verbatim_values, form, total = len(shown), set(kept), 'cap_rows', len(rows)
        error_dropped = len(errors) - sum(n for v, n in kept.items() if budget.is_error_like(v))
    elif header[:3] == ['cmdb_id', 'log_name', 'value']:
        covered, verbatim_values, form = sum(int(r[3]) for r in shown), {r[2] for r in shown}, 'exact_merge'
        total, error_dropped = len(_exact(rows)), len(errors) - sum(int(r[3]) for r in shown if budget.is_error_like(r[2]))
    else:
        keys = {(r[0], r[1], r[2], r[3]) for r in shown}
        covered, verbatim_values = sum(int(r[4]) for r in shown), {r[8] for r in shown}
        form, total = ('template_cap' if 'truncated' in note else 'template_merge'), len(_template(rows))
        error_dropped = sum(1 for r in rows if budget.is_error_like(r[4]) and (
            r[2], r[3], *(lambda s, m: (s, budget.template(m)))(*budget.severity_and_message(r[4]))) not in keys)
    return {**info, 'form': form, 'rows_covered': covered,
            'rows_verbatim': sum(1 for r in rows if r[4] in verbatim_values),
            'error_rows_dropped': error_dropped, 'error_values_not_verbatim': len(set(errors) - verbatim_values),
            'units_shown': len(shown), 'units_total': total}


responses = {}  # (service, second) -> per-response record for log bodies over the smallest budget
budgeted_cache = {}


def budgeted(service, second, body):
    """{(scheme, budget): (text or None)} for one log response; records loss statistics once per response."""
    if (service, second) not in budgeted_cache:
        budgeted_cache[(service, second)] = compute_budgeted(service, second, body)
    return budgeted_cache[(service, second)]


def compute_budgeted(service, second, body):
    text = body.decode('utf-8')
    results = {(s, b): budget.apply(s, text, second, b, count) for s in SCHEMES for b in BUDGETS}
    if any(v != text for v in results.values()) and (service, second) not in responses:
        rows = budget.parse(text)
        record = {'service': service, 'second': second, 'bytes': len(body), 'tokens': count(text),
                  'rows': None if rows is None else len(rows),
                  'csv_roundtrip_exact': rows is not None and budget.render(budget.HEADER, rows) == text}
        if rows is not None:
            record['exact_entries'] = len(_exact(rows))
            record['templates'] = len(_template(rows))
        for (s, b), v in results.items():
            if v != text:
                record[f'{s}@{b}'] = {'tokens': None if v is None else count(v),
                                      **(describe(rows, v) if rows is not None else {'form': 'stop'})}
        responses[(service, second)] = record
    return results


known = list(coordinator._KNOWN_SERVICES)
prior = {r['trace_id']: r for r in csv.DictReader(prior_csv.open(encoding='utf-8'))}
rows_out, own_changed, prior_mismatch = [], Counter(), []
budget_rows = []
for number, t in enumerate(traces, 1):
    graph = coordinator.build_trace_graph(t['root_span'])
    nodes = common.walk(graph)
    agent = coordinator.build_agent_tree(graph, None, coordinator.GlobalEvidenceGraph())
    by_depth = coordinator._collect_agents_by_depth(agent)
    agents = [a for level in sorted(by_depth) for a in by_depth[level]]
    bases, bases0, overheads, own_max = [], [], [], 0
    for a in agents:
        service, second, messages = common.own_round(coordinator, a)
        empty = [dict(m, content='') if m.get('role') == 'tool' else m for m in messages]
        base, base0 = template_tokens(empty), template_tokens(messages[:2])
        bodies = [m['content'].encode('utf-8') for m in messages if m.get('role') == 'tool']
        own_max = max(own_max, base + sum(count(b.decode('utf-8')) for b in bodies))
        for key, value in budgeted(service, second, bodies[0]).items():
            if value != bodies[0].decode('utf-8'):
                own_changed[key] += 1
        bases.append(base)
        bases0.append(base0)
        overheads.append(base - base0)
    span_seconds = sorted({int(str(n['raw'].get('timestamp', ''))[:10]) for n in nodes})
    services = sorted(set(known) | {str(n['raw'].get('cmdb_id', '')) for n in nodes})
    original_by_service = {}
    after = {k: {} for k in [(s, b) for s in SCHEMES for b in BUDGETS]}
    changed_services = {k: set() for k in after}
    stops = {k: set() for k in after}
    metric_max = 0
    for service in services:
        for second in span_seconds:
            log_body, metric_body = [serve(f'{coordinator.BASE_URL}/{ep}?service_name={service}&timestamp={second}').content
                                     for ep in ('search_logs', 'search_fluctuating_metrics')]
            metric_tokens = count(metric_body.decode('utf-8'))
            metric_max = max(metric_max, metric_tokens)
            log_tokens = count(log_body.decode('utf-8'))
            original_by_service[service] = max(original_by_service.get(service, 0), min(bases) + log_tokens + metric_tokens)
            for key, value in budgeted(service, second, log_body).items():
                if value is None:
                    stops[key].add(service)
                    continue
                if value != log_body.decode('utf-8'):
                    changed_services[key].add(service)
                tokens = min(bases) + count(value) + metric_tokens
                after[key][service] = max(after[key].get(service, 0), tokens)
    any_max = max(original_by_service.values())
    p = prior[t['trace_id']]
    if (int(p['own_max_tokens']), int(p['any_max_tokens'])) != (own_max, any_max) or \
            json.loads(p['any_tokens_by_service']) != original_by_service:
        prior_mismatch.append(t['trace_id'])
    row = {'case_id': t['case_id'], 'role': t['role'], 'trace_id': t['trace_id'], 'spans': len(nodes),
           'own_max_tokens': own_max, 'any_max_tokens': any_max,
           'base0_max': max(bases0), 'round_overhead_max': max(overheads), 'metric_max_tokens': metric_max}
    for (s, b) in after:
        row[f'{s}@{b}_max_tokens'] = max(after[(s, b)].values()) if after[(s, b)] else None
        row[f'{s}@{b}_changed_services'] = ' '.join(sorted(changed_services[(s, b)]))
        row[f'{s}@{b}_stop_services'] = ' '.join(sorted(stops[(s, b)]))
        row[f'{s}@{b}_by_service'] = json.dumps(after[(s, b)], sort_keys=True)
    rows_out.append(row)
    if number % 25 == 0 or number == len(traces):
        log('trace', number, '/', len(traces), 'cache', len(cache), 'changed responses', len(responses))

with (out / 'trace-impact.csv').open('w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(rows_out[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows_out)
(out / 'changed-responses.json').write_text(json.dumps(
    sorted(responses.values(), key=lambda r: (r['service'], r['second'])), indent=1) + '\n', encoding='utf-8')

# ── Samples of what the model would see for the smoke trace's v6 request and the frontend overflow case ──
samples = out / 'samples'
samples.mkdir(exist_ok=True)
for service, second in [('cartservice', 1708475368), ('frontend', 1705347533)]:
    body = serve(f'{coordinator.BASE_URL}/search_logs?service_name={service}&timestamp={second}').content.decode('utf-8')
    for s in SCHEMES:
        for b in BUDGETS:
            text = budget.apply(s, body, second, b, count)
            (samples / f'{service}-{second}-{s}-{b}.txt').write_text('<stop: scheme cannot fit>\n' if text is None else text,
                                                                     encoding='utf-8', newline='\n')

summary = {'traces': len(rows_out), 'cases': len({r['case_id'] for r in rows_out}), 'context': CONTEXT,
           'output_reserve': OUTPUT_RESERVE, 'budgets': BUDGETS, 'schemes': SCHEMES,
           'prior_scan_mismatch_traces': prior_mismatch,
           'instructed_queries_changed': {f'{s}@{b}': own_changed[(s, b)] for s in SCHEMES for b in BUDGETS},
           'base0_max': max(r['base0_max'] for r in rows_out),
           'round_overhead_max': max(r['round_overhead_max'] for r in rows_out),
           'metric_max_tokens': max(r['metric_max_tokens'] for r in rows_out),
           'own_max_tokens': max(r['own_max_tokens'] for r in rows_out),
           'changed_log_responses': len(responses),
           'csv_roundtrip_exact': Counter(r['csv_roundtrip_exact'] for r in responses.values()),
           'by_budget': {}}
summary['four_round_worst_case'] = {
    str(b): summary['base0_max'] + ROUNDS * (summary['round_overhead_max'] + b + summary['metric_max_tokens']) + OUTPUT_RESERVE
    for b in BUDGETS}
for s in SCHEMES:
    for b in BUDGETS:
        key = f'{s}@{b}'
        by_service = defaultdict(int)
        for r in rows_out:
            for svc, tok in json.loads(r[f'{key}_by_service']).items():
                by_service[svc] = max(by_service[svc], tok)
        recs = [r[key] for r in responses.values() if key in r]
        changed = [r for r in rows_out if r[f'{key}_changed_services']]
        summary['by_budget'][key] = {
            'max_round1_tokens_by_service': dict(sorted(by_service.items())),
            'traces_over_context_any_service': sum(1 for r in rows_out if (r[f'{key}_max_tokens'] or 0) + OUTPUT_RESERVE > CONTEXT),
            'traces_with_changed_response': len(changed),
            'cases_with_changed_response': len({r['case_id'] for r in changed}),
            'traces_changed_by_service': dict(Counter(svc for r in rows_out for svc in r[f'{key}_changed_services'].split())),
            'traces_with_stop': sum(1 for r in rows_out if r[f'{key}_stop_services']),
            'changed_responses': len(recs),
            'forms': dict(Counter(x['form'] for x in recs)),
            'rows_original': sum(x.get('rows', 0) or 0 for x in recs),
            'rows_covered': sum(x.get('rows_covered', 0) for x in recs),
            'rows_verbatim': sum(x.get('rows_verbatim', 0) for x in recs),
            'error_rows_original': sum(x.get('error_rows', 0) for x in recs),
            'error_rows_dropped': sum(x.get('error_rows_dropped', 0) for x in recs),
            'responses_dropping_error_rows': sum(1 for x in recs if x.get('error_rows_dropped', 0)),
            'error_values_original': sum(x.get('error_values', 0) for x in recs),
            'error_values_not_verbatim': sum(x.get('error_values_not_verbatim', 0) for x in recs),
            'max_tokens_after': max((x['tokens'] or 0) for x in recs) if recs else None}
summary['elapsed_seconds'] = round(time.time() - started, 1)
(out / 'tool-result-budget-impact.json').write_text(json.dumps(summary, indent=2, default=list) + '\n', encoding='utf-8')
print(json.dumps(summary, indent=2, default=list))
