"""Build a scoped benchmark package of train traces and compare original tool endpoints on CPU.

One package holds the unchanged upstream code and one sub-package per trace (traces/<trace_id>/: input, selection,
CPU equivalence report, scoring label). No LLM imports, network requests, or NT114 canonical bundle reads.
"""
import ast
import csv
import gc
import hashlib
import importlib.util
import json
import os
import pickle
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ARTIFACT = Path('F:/Nam/UIT/nt114-paper-artifacts/W7165616276')
CODE = ARTIFACT / 'code'
FULL = ARTIFACT / 'data/re2ob'
ROLES = HERE.parent / 'work/re2ob-case-roles-by-source-key.csv'
SCAN = HERE.parent / 'work/tool-response-scan/tool-response-scan.csv'  # Span counts per error trace.
COMMIT = '3052e7a6a9598d984ba1482f3dc41123c8823a99'
SMOKE_TRACE = '68791e1f360d910bd01428c3cd9748ef'  # checkoutservice_cpu_2, the trace of versions 1-8.
MODEL_REV = 'cdbee75f17c01a7cc42f958dc650907174af0554'
UPSTREAM_FILES = ('config.py', 'llm.py', 'coordinator.py', 'tool_server.py',
                  'tools_gpt.py', 'evaluate.py', 'LICENSE', 'README.md',
                  'requirements.txt', 'preprocess/preprocess_re2ob.py')
WRAPPERS = ('kaggle-runtime.py', 'smoke-worker.py', 'tool-result-budget.py', 'vllm-t4-compat.py', 'verify-t4-prefix-kernel.py')


def upstream_known_services(code=CODE):
    """config.get_known_services() for re2ob, read from the literal without importing config (env side effects)."""
    for node in ast.parse((code / 'config.py').read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == 'KNOWN_SERVICES' for t in node.targets):
            return tuple(ast.literal_eval(node.value)['re2ob'])
    raise AssertionError('KNOWN_SERVICES literal not found in upstream config.py')


# Service names the upstream re2ob system prompt lists; the model may query any of them.
KNOWN_SERVICES = upstream_known_services()
TOOL_RESULT_BUDGET = {
    'deviation_from_upstream': True, 'endpoint': 'search_logs', 'budget_tokens': 2048,
    'tokenizer': 'Qwen/Qwen3-4B-Instruct-2507@' + MODEL_REV, 'scheme': 'ladder', 'module': 'tool-result-budget.py',
    'share': 'The search_logs calls of one model response share the budget equally: floor(2048 / n) tokens each. '
             'Metric results are not budgeted.',
    'rule': 'Results within their share pass byte-for-byte. Larger results are merged by exact duplicates, then by '
            'masked message template, then truncated by severity priority, whichever first fits; a notice line '
            'tells the model. Applied by smoke-worker.py outside the unchanged upstream code.'}
# Substring, case and unknown-name probes of the endpoints' str.contains predicates.
SERVICE_PROBES = ('service', 'cart', 'Frontend', 'CARTSERVICE', 'node-1', 'unknownservice')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 << 20), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def endpoint_module():
    """Compile the author's unchanged endpoint bodies; bind real data separately."""
    tree = ast.parse((CODE / 'tool_server.py').read_text(encoding='utf-8'))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    app = Flask('cpu-equivalence')
    namespace = dict(pd=pd, app=app, jsonify=jsonify, request=request)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(CODE / 'tool_server.py'), 'exec'), namespace)
    namespace['service_node_map'] = {}
    return namespace, app.test_client()


def collect_csv(path, selector):
    frames = []
    for chunk in pd.read_csv(path, chunksize=250000, low_memory=False,
                             dtype={'status_code': str} if 'trace' in path.name else None):
        frames.append(chunk.loc[selector(chunk)])
    return pd.concat(frames, ignore_index=True)


def full_data_seconds():
    """First and last second of all full-data metric and log rows (logs before the INFO/DEBUG filter, a superset).

    An endpoint window lying wholly outside this range is empty on the full data and on the package alike.
    """
    result = {}
    for name, path in (('metric', FULL / 'metric/all/metrics.csv'), ('log', FULL / 'log/all/logs.csv')):
        low = high = None
        for chunk in pd.read_csv(path, usecols=['timestamp'], chunksize=2_000_000):
            low = int(chunk.timestamp.min()) if low is None else min(low, int(chunk.timestamp.min()))
            high = int(chunk.timestamp.max()) if high is None else max(high, int(chunk.timestamp.max()))
        result[name] = [low, high]
    return result




def raw_dir(case):
    fault, number = case.rsplit('_', 1)
    return ARTIFACT / 'data/raw/RE2-OB' / fault / number


def select_traces(trace_ids):
    """Error-trace row and owning case of each trace; it must lie in exactly one case's author window, a train case."""
    lines = (FULL / 'error_traces.txt').read_text(encoding='utf-8').splitlines()
    rows = {tokens[4]: tokens for tokens in (line.split() for line in lines[1:])}
    assert len(rows) == len(lines) - 1
    cases = list(csv.DictReader(ROLES.open(encoding='utf-8')))
    chosen = []
    for trace_id in trace_ids:
        tokens = rows[trace_id]
        root_ts = int(tokens[1])
        owners = [c for c in cases if int(c['inject_ts']) * 1000 - 60_000 <= root_ts <= int(c['inject_ts']) * 1000 + 300_000]
        assert len(owners) == 1 and owners[0]['role'] == 'train', (trace_id, [(c['case_id'], c['role']) for c in owners])
        chosen.append({'trace_id': trace_id, 'root_span': tokens[3], 'case': owners[0]['case_id'], 'tokens': tokens})
    assert len({c['trace_id'] for c in chosen}) == len(chosen)
    return lines[0], chosen


PILOT_RULE = ('Train traces stratified by span count, one per case, excluding the trace of versions 1-8: the largest, '
              'then the smallest, lower quartile, median and upper quartile of the span-ordered list (ties by '
              'error-trace row); a case already used moves the pick to the nearest unused position.')


def pilot_traces():
    rows = [r for r in csv.DictReader(SCAN.open(encoding='utf-8')) if r['role'] == 'train' and r['trace_id'] != SMOKE_TRACE]
    order = sorted(rows, key=lambda r: (int(r['spans']), int(r['error_trace_row'])))
    picked, used = [], set()
    for quantile in (1, 0, 0.25, 0.5, 0.75):
        target = round(quantile * (len(order) - 1))
        for index in sorted(range(len(order)), key=lambda i: (abs(i - target), i)):
            if order[index]['case_id'] not in used:
                picked.append(order[index]['trace_id'])
                used.add(order[index]['case_id'])
                break
    return picked


def copy_metric_windows(metric_path, windows):
    """One pass over the author CSV; each line goes VERBATIM to every package whose metric window holds it."""
    targets = [(lo, hi, path.open('w', encoding='utf-8', newline='')) for lo, hi, path in windows]
    try:
        with metric_path.open('r', encoding='utf-8', newline='') as source:
            header = next(source)
            for _, _, target in targets:
                target.write(header)
            for line in source:
                second = int(next(csv.reader([line]))[0])
                for lo, hi, target in targets:
                    if lo <= second <= hi:
                        target.write(line)
    finally:
        for _, _, target in targets:
            target.close()


def build(name, trace_ids, rule):
    assert subprocess.check_output(['git', '-C', str(CODE), 'rev-parse', 'HEAD'], text=True).strip() == COMMIT
    assert not subprocess.check_output(['git', '-C', str(CODE), 'status', '--porcelain', '--untracked-files=no'], text=True).strip()
    stage = HERE / 'runtime' / ('package-' + name)
    if stage.exists():
        raise RuntimeError('Package staging already exists; preserve it and choose a fresh attempt.')
    header, chosen = select_traces(trace_ids)
    spec = importlib.util.spec_from_file_location('author_preprocess', CODE / 'preprocess/preprocess_re2ob.py')
    pp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pp)
    by_case = {}
    for item in chosen:
        by_case.setdefault(item['case'], []).append(item)
    for case, items in by_case.items():
        case_trace = pp._convert_one_trace(str(raw_dir(case)), case).drop(columns='_case_id')
        for item in items:
            trace = case_trace[case_trace.trace_id == item['trace_id']].copy()
            assert len(trace) and trace.span_id.nunique() == len(trace)
            assert item['root_span'] in set(trace.span_id)
            # The model sees span timestamps; upstream endpoints parse the first ten digits as seconds.
            seconds = sorted({int(str(ts)[:10]) for ts in trace.timestamp})
            lo, hi = seconds[0], seconds[-1]
            item.update(trace=trace, seconds=seconds, lo=lo, hi=hi, dir=stage / 'traces' / item['trace_id'],
                        metric_window=(lo - 1200, hi + 1200),  # search_fluctuating_metrics baseline window.
                        log_window=(lo - 60, hi + 60))  # search_logs window.
            seen, pending = set(), [item['root_span']]
            while pending:
                sid = pending.pop()
                assert sid not in seen, 'Cycle or duplicate child'
                seen.add(sid)
                pending.extend(trace.loc[trace.parent_span == sid, 'span_id'].tolist())
            assert seen == set(trace.span_id)
            for part in ('trace/all', 'metric/all', 'log/all'):
                (item['dir'] / 'input' / part).mkdir(parents=True)
        del case_trace
    trace_path = FULL / 'trace/all/trace_jaeger-span.csv'
    metric_path = FULL / 'metric/all/metrics.csv'
    log_path = FULL / 'log/all/logs.csv'
    full_hashes = {str(p.relative_to(FULL)): sha(p) for p in (trace_path, metric_path, log_path)}
    full_range = full_data_seconds()
    # Each full file is scanned once for all selected traces; per-trace frames are exact subsets in file order.
    all_spans = set().union(*(set(item['trace'].span_id) for item in chosen))
    trace_scan = collect_csv(trace_path, lambda c: c.span_id.isin(all_spans) | c.parent_span.isin(all_spans))
    copy_metric_windows(metric_path, [(*item['metric_window'], item['dir'] / 'input/metric/all/metrics.csv')
                                      for item in chosen])
    full_metric = pd.read_csv(metric_path, low_memory=False)

    def noise(frame):
        # The upstream loader drops INFO/DEBUG lines before serving; then only the time window filters.
        return frame.value.astype(str).str.lower().str.contains(r'severity:\s*(?:info|debug)', regex=True, na=False)

    def in_windows(frame, windows):
        mask = pd.Series(False, index=frame.index)
        for lo, hi in windows:
            mask |= frame.timestamp.between(lo, hi)
        return mask

    log_scan = collect_csv(log_path, lambda c: in_windows(c, [item['log_window'] for item in chosen]) & ~noise(c))
    ns, client = endpoint_module()
    lines = (FULL / 'error_traces.txt').read_text(encoding='utf-8').splitlines()
    gt_all = pd.read_csv(FULL / 'groundtruth.csv')
    raw_case_hashes, entries = {}, []
    for case, items in by_case.items():
        raw = raw_dir(case)
        raw_hashes = {name: sha(raw / name) for name in ('traces.csv', 'simple_metrics.csv', 'logs.csv', 'inject_time.txt')}
        raw_case_hashes[case] = raw_hashes
        # Every row of every service inside the window: no service or anomaly selection. A row outside it
        # fails the endpoint's timestamp predicate for every allowed query second, so it can never be returned.
        case_metric = pp._convert_one_metric_simple(str(raw), case).drop(columns='_case_id')
        case_log = pp._convert_one_log(str(raw), case).drop(columns='_case_id')
        gt = gt_all[gt_all.timestamp == int((raw / 'inject_time.txt').read_text())]
        assert len(gt) == 1
        for item in items:
            entries.append(build_trace(item, case, header, lines, raw, raw_hashes, case_metric, case_log, gt,
                                       trace_scan, full_metric, log_scan, full_range, ns, client, noise))
            entries[-1]['dir'] = item['dir'].relative_to(stage).as_posix()
            print(json.dumps(entries[-1]), flush=True)
        del case_metric, case_log
        gc.collect()
    for name in UPSTREAM_FILES:
        destination = stage / 'upstream' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        original = subprocess.check_output(['git', '-C', str(CODE), 'show', COMMIT + ':' + name])
        assert original.replace(b'\r\n', b'\n') == (CODE / name).read_bytes().replace(b'\r\n', b'\n'), name
        destination.write_bytes(original)
    for name in WRAPPERS:
        shutil.copyfile(HERE / name, stage / name)
    manifest = {'schema_version': 2, 'upstream_commit': COMMIT,
                'upstream_url': 'https://github.com/LLM4AIOps/RCLAgent-V2',
                'benchmark_url': 'https://zenodo.org/records/14590730',
                'benchmark_file': 'RE2-OB.zip',
                'benchmark_zip_sha256': '0605a36cdcad8a6ae0107f2357c9c91ecee2c4ab5d72579bffea0372d9747513',
                'cases': sorted(by_case), 'partition': 'train', 'selection_rule': rule, 'traces': entries,
                'model': 'Qwen/Qwen3-4B-Instruct-2507', 'model_revision': MODEL_REV,
                'raw_case_file_hashes': raw_case_hashes, 'full_preprocessed_hashes': full_hashes,
                'metrics_source': 'simple_metrics.csv, the upstream preprocessing default; all KPIs of all services in the window retained.',
                'tool_query_domain': 'Any service_name; query second within the selected trace span seconds. Each trace package holds every full-data metric row within 1200 s and every served log row within 60 s of its window; all belong to its case.',
                'data_policy': 'Only selected train cases. Labels in traces/*/scoring/; never forwarded to model. Private Kaggle use only.',
                'upstream_patch': None, 'tool_result_budget': TOOL_RESULT_BUDGET, 'files': {}}
    manifest['files'] = {str(p.relative_to(stage)).replace('\\', '/'): {'sha256': sha(p), 'bytes': p.stat().st_size}
                         for p in sorted(stage.rglob('*')) if p.is_file()}
    write_json(stage / 'manifest.json', manifest)
    print(json.dumps({'stage': str(stage), 'traces': len(entries), 'cases': len(by_case),
                      'endpoint_comparisons': sum(e['endpoint_comparisons'] for e in entries)}, indent=2))


def build_trace(item, case, header, lines, raw, raw_hashes, case_metric, case_log, gt, trace_scan, full_metric, log_scan,
                full_range, ns, client, noise):
    """One trace package with byte-for-byte endpoint parity against the full merged data."""
    trace_id, trace, target = item['trace_id'], item['trace'], item['dir']
    data = target / 'input'
    span_count, seconds, lo, hi = len(trace), item['seconds'], item['lo'], item['hi']
    (metric_lo, metric_hi), (log_lo, log_hi) = item['metric_window'], item['log_window']
    span_ids = set(trace.span_id)
    # The full scan holds every row sharing a span id with any selected trace; collisions or extra children
    # outside this trace would show up here.
    full_trace_queries = trace_scan.loc[trace_scan.span_id.isin(span_ids) | trace_scan.parent_span.isin(span_ids)]
    full_trace_queries = full_trace_queries.reset_index(drop=True)
    assert set(full_trace_queries.trace_id) == {trace_id}
    assert len(full_trace_queries) == span_count
    trace.to_csv(data / 'trace/all/trace_jaeger-span.csv', index=False)
    comparisons = []

    def compare(endpoint, params, full_frame, small_frame, key):
        ns[key] = full_frame
        before = client.get('/' + endpoint, query_string=params)
        ns[key] = small_frame
        after = client.get('/' + endpoint, query_string=params)
        assert before.status_code == after.status_code == 200
        assert before.data == after.data, (endpoint, params, before.data[:160], after.data[:160])
        comparisons.append({'endpoint': endpoint, 'params': params, 'status': 200,
                            'response_sha256': hashlib.sha256(before.data).hexdigest(),
                            'response_bytes': len(before.data), 'equal': True})

    reloaded_trace = pd.read_csv(data / 'trace/all/trace_jaeger-span.csv', dtype={'status_code': str})
    for row in trace.itertuples():
        compare('search_span', {'span_id': row.span_id}, full_trace_queries, reloaded_trace, 'trace_df')
        compare('search_traces', {'parent_span_id': row.span_id}, full_trace_queries, reloaded_trace, 'trace_df')
    ns.pop('trace_df', None)

    def metric_mask(frame):
        return frame.timestamp.between(metric_lo, metric_hi)

    expected_case_rows = case_metric[metric_mask(case_metric)].reset_index(drop=True)
    expected_case_rows['node_id'] = expected_case_rows['node_id'].replace('', float('nan'))
    # Provenance: the full merged rows in the window are exactly this case's rows, so no other case
    # (and no val/test case) overlaps it. Independent raw conversion can differ in the final bit across
    # pandas versions; actual package rows are copied VERBATIM from the author CSV.
    pd.testing.assert_frame_equal(full_metric.loc[metric_mask(full_metric)].reset_index(drop=True),
                                  expected_case_rows, check_dtype=False, check_exact=False, rtol=1e-14, atol=0)
    small_metric = pd.read_csv(data / 'metric/all/metrics.csv', low_memory=False)
    # Stronger than response equality: the complete window rows must be identical.
    pd.testing.assert_frame_equal(full_metric.loc[metric_mask(full_metric)].reset_index(drop=True),
                                  small_metric.reset_index(drop=True), check_exact=True)
    services = sorted(set(trace.cmdb_id.astype(str)) | set(small_metric.service_name.dropna().astype(str))
                      | set(KNOWN_SERVICES) | set(SERVICE_PROBES))
    # Seconds plus the millisecond strings the model actually sees in span data. Each full-dataframe
    # metric query scans 9.4 million rows, so it uses one millisecond form per second.
    stamps = sorted({str(s) for s in seconds} | {str(ts) for ts in trace.timestamp})
    metric_stamps = sorted({str(s) for s in seconds} | {min(t for t in stamps if t[:10] == str(s) and len(t) > 10) for s in seconds})
    for service in services:
        for ts in metric_stamps:
            compare('search_fluctuating_metrics', {'service_name': service, 'timestamp': ts},
                    full_metric, small_metric, 'metric_df')
    metric_count = len(small_metric)
    del expected_case_rows, small_metric
    ns.pop('metric_df', None)
    # Empty maps are actual upstream outputs, verified before copying.
    for name in ('service_node_map.pkl', 'node_service_map.pkl'):
        assert (FULL / 'metric' / name).read_bytes() == pickle.dumps({})
        shutil.copyfile(FULL / 'metric' / name, data / 'metric' / name)

    def log_mask(frame):
        return frame.timestamp.between(log_lo, log_hi) & ~noise(frame)

    logs = case_log[log_mask(case_log)]
    logs.to_csv(data / 'log/all/logs.csv', index=False)
    # The scan covers the entire merged log dataset. Equal frames also prove that only this case lies in the window.
    full_log_queries = log_scan.loc[log_mask(log_scan)].reset_index(drop=True)
    assert full_log_queries.log_id.str.startswith('re2ob_' + case + '_').all()
    small_logs = pd.read_csv(data / 'log/all/logs.csv', low_memory=False)
    pd.testing.assert_frame_equal(full_log_queries, small_logs, check_dtype=False, check_exact=True)
    for service in services:
        for ts in stamps:
            compare('search_logs', {'service_name': service, 'timestamp': ts}, full_log_queries, small_logs, 'log_df')
    log_count = len(small_logs)
    ns.pop('log_df', None)

    # The original header and exact selected row, renumbered to one trace only.
    tokens = list(item['tokens'])
    assert tokens[3] == item['root_span'] and tokens[4] == trace_id
    tokens[0] = '0'
    (data / 'error_traces.txt').write_text(header + '\n' + ' '.join(tokens) + '\n', encoding='utf-8')
    write_json(target / 'selection.json', {'trace_id': trace_id, 'root_span_id': item['root_span'], 'span_count': span_count,
               'query_window': {'start_second': lo, 'end_second': hi, 'service_name': 'any',
                                'metric_rows_seconds': [metric_lo, metric_hi], 'log_rows_seconds': [log_lo, log_hi],
                                'full_data_seconds': full_range}})
    (target / 'scoring').mkdir()
    gt.to_csv(target / 'scoring/groundtruth.csv', index=False)
    report = {'status': 'pass', 'method': 'Unchanged upstream Flask endpoint bodies; byte-for-byte HTTP responses. Full merged CSV scans, complete metric dataframe, exact window row equality.',
              'trace_rows': span_count, 'metric_rows': metric_count, 'log_rows': log_count,
              'query_window': {'start_second': lo, 'end_second': hi, 'metric_rows_seconds': [metric_lo, metric_hi],
                               'log_rows_seconds': [log_lo, log_hi]},
              'coverage_argument': 'Upstream metric and log endpoints return only rows with timestamp in [t-1200, t+1200] and [t-60, t+60] for the parsed query second t. For t in the query window these lie inside the packaged row windows, which equal the full merged data exactly, so any service_name gives the full-data response.',
              'queried_services': services, 'queried_timestamps': {'search_logs': stamps, 'search_fluctuating_metrics': metric_stamps},
              'nonempty_log_responses': sorted({c['params']['service_name'] for c in comparisons if c['endpoint'] == 'search_logs' and c['response_bytes'] > 41}),
              'endpoint_comparisons': len(comparisons),
              'comparisons': comparisons, 'pandas_version': pd.__version__,
              'source_inputs_unchanged': raw_hashes == {name: sha(raw / name) for name in raw_hashes}}
    assert report['source_inputs_unchanged']
    write_json(target / 'cpu-equivalence.json', report)
    return {'trace_id': trace_id, 'case': case, 'span_count': span_count, 'metric_rows': metric_count,
            'log_rows': log_count, 'endpoint_comparisons': len(comparisons)}


if __name__ == '__main__':
    # usage: prepare-bundle.py NAME (--pilot | TRACE_ID ...). Builds runtime/package-NAME only;
    # refresh-package.py promotes a stage to the Kaggle bundle.
    if sys.argv[2:] == ['--pilot']:
        build(sys.argv[1], pilot_traces(), PILOT_RULE)
    else:
        build(sys.argv[1], sys.argv[2:], 'Explicit trace list: ' + ' '.join(sys.argv[2:]))
