"""Shared pipeline of the RE2-OB endpoint scans (re2ob-tool-response-scan.py, re2ob-tool-result-budget-impact.py).

Loaded by path with importlib (the scans run with -I). Error traces and their cases, the trace rows the author's
search_span/search_traces could return, exact time slices of the full metric and log data, the author's unchanged
tool_server.py endpoint bodies behind a cached serve(), the author's coordinator with a scripted chat_api, and the
pinned Qwen chat template. No label, groundtruth or result file is read.
"""
import ast
import csv
import json
import os
import sys
from types import SimpleNamespace
from urllib.parse import parse_qsl, urlparse

import pandas as pd
import requests as real_requests
from flask import Flask, jsonify, request


# ── Error traces and their cases (author's selection window: inject-60 s .. inject+300 s) ──
def load_traces(data, roles_csv, only):
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
    return traces


# ── Trace rows the author's search_span/search_traces could return, in full-file order ──
def scan_traces(trace_path, selector):
    frames, offset = [], 0
    for chunk in pd.read_csv(trace_path, chunksize=1_000_000, dtype={'status_code': str}, low_memory=False):
        chunk.index = range(offset, offset + len(chunk))
        offset += len(chunk)
        frames.append(chunk.loc[selector(chunk)])
    return pd.concat(frames)


def load_trace_rows(data, traces):
    """(own, extra, trace_df): rows of the traces, cross-trace parent/child rows, and both in full-file order."""
    trace_ids = {t['trace_id'] for t in traces}
    trace_path = data / 'trace/all/trace_jaeger-span.csv'
    own = scan_traces(trace_path, lambda c: c.trace_id.isin(trace_ids))
    span_ids = set(own.span_id)
    extra = scan_traces(trace_path, lambda c: ~c.trace_id.isin(trace_ids) & (c.span_id.isin(span_ids) | c.parent_span.isin(span_ids)))
    return own, extra, pd.concat([own, extra]).sort_index()


# ── Time slices of the full metric and log data needed by any span second ──
def load_slices(data, own):
    seconds = {int(str(ts)[:10]) for ts in own.timestamp}
    log_seconds = {s + d for s in seconds for d in range(-60, 61)}
    metric_full = pd.read_csv(data / 'metric/all/metrics.csv', low_memory=False)
    log_frames = []
    for chunk in pd.read_csv(data / 'log/all/logs.csv', chunksize=1_000_000, low_memory=False):
        chunk = chunk.loc[chunk.timestamp.isin(log_seconds)]
        noise = chunk['value'].astype(str).str.lower().str.contains(r'severity:\s*(?:info|debug)', regex=True, na=False)
        log_frames.append(chunk.loc[~noise])  # Same filter as tool_server._load_log_df.
    return metric_full, pd.concat(log_frames, ignore_index=True)


# ── Author endpoint bodies, unchanged ──
def author_endpoints(code, app_name, trace_df, metric_full, log_full):
    """(serve, cache): a requests.get stand-in over the author's endpoints, and its metric/log response cache."""
    tree = ast.parse((code / 'tool_server.py').read_text(encoding='utf-8'))
    app = Flask(app_name)
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

    return serve, cache


def author_agents(code, tokenizer_dir, serve):
    """(coordinator, tokenizer, template_tokens): the author's coordinator served by serve(), and the pinned template."""
    os.environ.update(LLM_API_KEY='local-placeholder', DATASET_TYPE='re2ob', MAX_AGENT_PARALLEL='1')
    sys.path.insert(0, str(code))
    import coordinator
    from tools_gpt import search_fluctuating_metrics_function, search_logs_function

    coordinator.requests = SimpleNamespace(get=serve)
    tools = [search_logs_function, search_fluctuating_metrics_function]
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_dir), local_files_only=True)

    def template_tokens(messages):
        return len(tokenizer.apply_chat_template(messages, tools=tools, tokenize=True,
                                                 add_generation_prompt=True, enable_thinking=False))

    return coordinator, tokenizer, template_tokens


class Captured(BaseException):
    pass


def own_round(coordinator, agent):
    """Exact round-1 prompt messages if the model makes the instructed calls for its own span."""
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
