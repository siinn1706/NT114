"""Impact of candidate search_logs budgets on every RE2-OB error trace (CPU, no model).

usage: python -I -X utf8 re2ob-tool-result-budget-impact.py CODE DATA ROLES_CSV TOKENIZER_DIR OUT_DIR PRIOR_SCAN_CSV [TRACE_ID ...]

Same pipeline as re2ob-tool-response-scan.py (author endpoint bodies over the full merged data, real
build_trace_graph and self_state_verification with a scripted chat_api, pinned Qwen chat template), plus the
schemes of tool-result-budget.py at several budgets. Per trace it records the instructed (own-span) queries, which
must stay byte-identical, and every service the model can name at every span second. Per distinct changed log
response it records what each scheme keeps and drops. Unbudgeted numbers are checked against the prior scan CSV.
No label, groundtruth or result file is read.
"""
import ast
import csv
import importlib.util
import io
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qsl, urlparse

import pandas as pd
import requests as real_requests
from flask import Flask, jsonify, request

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


def log(*parts):
    print(f'[{time.time() - started:7.1f}s]', *parts, flush=True)


# ── Traces, cases, data slices and author endpoints: identical to re2ob-tool-response-scan.py ──
lines = (data / 'error_traces.txt').read_text(encoding='utf-8').splitlines()
traces = [{'row': int(p[0]), 'root_ts': int(p[1]), 'root_service': p[2], 'root_span': p[3], 'trace_id': p[4]}
          for p in (line.split() for line in lines[1:])]
cases = list(csv.DictReader(roles_csv.open(encoding='utf-8')))
for t in traces:
    owners = [c for c in cases if int(c['inject_ts']) * 1000 - 60_000 <= t['root_ts'] <= int(c['inject_ts']) * 1000 + 300_000]
    assert len(owners) == 1, (t, [c['case_id'] for c in owners])
    t['case_id'], t['role'] = owners[0]['case_id'], owners[0]['role']
if only:
    traces = [t for t in traces if t['trace_id'] in only]
assert traces
log('traces', len(traces), 'cases', len({t['case_id'] for t in traces}))

trace_ids = {t['trace_id'] for t in traces}
trace_path = data / 'trace/all/trace_jaeger-span.csv'


def scan_traces(selector):
    frames, offset = [], 0
    for chunk in pd.read_csv(trace_path, chunksize=1_000_000, dtype={'status_code': str}, low_memory=False):
        chunk.index = range(offset, offset + len(chunk))
        offset += len(chunk)
        frames.append(chunk.loc[selector(chunk)])
    return pd.concat(frames)


own = scan_traces(lambda c: c.trace_id.isin(trace_ids))
span_ids = set(own.span_id)
extra = scan_traces(lambda c: ~c.trace_id.isin(trace_ids) & (c.span_id.isin(span_ids) | c.parent_span.isin(span_ids)))
trace_df = pd.concat([own, extra]).sort_index()
log('trace rows', len(own), 'cross-trace rows', len(extra))

seconds = {int(str(ts)[:10]) for ts in own.timestamp}
log_seconds = {s + d for s in seconds for d in range(-60, 61)}
metric_full = pd.read_csv(data / 'metric/all/metrics.csv', low_memory=False)
log_frames = []
for chunk in pd.read_csv(data / 'log/all/logs.csv', chunksize=1_000_000, low_memory=False):
    chunk = chunk.loc[chunk.timestamp.isin(log_seconds)]
    noise = chunk['value'].astype(str).str.lower().str.contains(r'severity:\s*(?:info|debug)', regex=True, na=False)
    log_frames.append(chunk.loc[~noise])
log_full = pd.concat(log_frames, ignore_index=True)
log('metric rows', len(metric_full), 'served log rows near traces', len(log_full))

tree = ast.parse((code / 'tool_server.py').read_text(encoding='utf-8'))
app = Flask('tool-result-budget-impact')
ns = dict(pd=pd, app=app, jsonify=jsonify, request=request)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)], type_ignores=[]),
             str(code / 'tool_server.py'), 'exec'), ns)
ns.update(service_node_map={}, trace_df=trace_df)
client = app.test_client()
cache = {}


def serve(url, params=None, **_):
    sent = real_requests.Request('GET', url, params=params).prepare().url
    parsed = urlparse(sent)
    query = {}
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        query.setdefault(key, value)
    if parsed.path in ('/search_logs', '/search_fluctuating_metrics'):
        second = int(str(query['timestamp'])[:10])
        key = (parsed.path, query['service_name'], second)
        if key not in cache:
            ns['metric_df'] = metric_full.loc[metric_full.timestamp.between(second - 1200, second + 1200)]
            ns['log_df'] = log_full.loc[log_full.timestamp.between(second - 60, second + 60)]
            response = client.get(parsed.path, query_string=query)
            assert response.status_code == 200, (key, response.status_code)
            cache[key] = response.data.replace(b'\r\n', b'\n')
        body = cache[key]
    else:
        response = client.get(parsed.path, query_string=query)
        body = response.data
    return SimpleNamespace(content=body, text=body.decode('utf-8'), status_code=200)


os.environ.update(LLM_API_KEY='local-placeholder', DATASET_TYPE='re2ob', MAX_AGENT_PARALLEL='1')
sys.path.insert(0, str(code))
import coordinator  # noqa: E402
from tools_gpt import search_fluctuating_metrics_function, search_logs_function  # noqa: E402

coordinator.requests = SimpleNamespace(get=serve)
TOOLS = [search_logs_function, search_fluctuating_metrics_function]
from transformers import AutoTokenizer  # noqa: E402

tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_dir), local_files_only=True)
token_cache = {}


def template_tokens(messages):
    return len(tokenizer.apply_chat_template(messages, tools=TOOLS, tokenize=True,
                                             add_generation_prompt=True, enable_thinking=False))


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


class Captured(BaseException):
    pass


def own_round(agent):
    service = str(agent.raw.get('cmdb_id', ''))
    stamp = str(agent.raw.get('timestamp', ''))
    arguments = json.dumps({'service_name': service, 'timestamp': stamp})
    seen = []

    def scripted(messages, tools=None):
        if seen:
            raise Captured(list(messages))
        seen.append(True)
        return '', [{'id': 'scan-' + name, 'type': 'function', 'function': {'name': name, 'arguments': arguments}}
                    for name in ('search_logs', 'search_fluctuating_metrics')]

    coordinator.chat_api = scripted
    try:
        agent.self_state_verification()
    except Captured as captured:
        return service, int(stamp[:10]), captured.args[0]
    raise AssertionError('round-1 prompt not captured')


def walk(node):
    return [node] + [d for child in node['children'] for d in walk(child)]


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
    nodes = walk(graph)
    agent = coordinator.build_agent_tree(graph, None, coordinator.GlobalEvidenceGraph())
    by_depth = coordinator._collect_agents_by_depth(agent)
    agents = [a for level in sorted(by_depth) for a in by_depth[level]]
    bases, bases0, overheads, own_max = [], [], [], 0
    for a in agents:
        service, second, messages = own_round(a)
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
