"""Build a scoped benchmark package and compare original tool endpoints on CPU.

No LLM imports, network requests, or NT114 canonical bundle reads.
"""
import ast
import csv
import gc
import hashlib
import importlib.util
import json
import os
import pickle
import re
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
RAW = ARTIFACT / 'data/raw/RE2-OB/checkoutservice_cpu/2'
COMMIT = '3052e7a6a9598d984ba1482f3dc41123c8823a99'
TRACE_ID = '68791e1f360d910bd01428c3cd9748ef'
ROOT_SPAN = '6752e26884a7fee8'
MODEL_REV = 'cdbee75f17c01a7cc42f958dc650907174af0554'
UPSTREAM_FILES = ('config.py', 'llm.py', 'coordinator.py', 'tool_server.py',
                  'tools_gpt.py', 'evaluate.py', 'LICENSE', 'README.md',
                  'requirements.txt', 'preprocess/preprocess_re2ob.py')


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


def run():
    assert subprocess.check_output(['git', '-C', str(CODE), 'rev-parse', 'HEAD'], text=True).strip() == COMMIT
    assert not subprocess.check_output(['git', '-C', str(CODE), 'status', '--porcelain', '--untracked-files=no'], text=True).strip()
    stage = HERE / 'runtime/package'
    if stage.exists():
        raise RuntimeError('Package staging already exists; preserve it and choose a fresh attempt.')
    stage.mkdir(parents=True)
    data = stage / 'input'
    for part in ('trace/all', 'metric/all', 'log/all'):
        (data / part).mkdir(parents=True)
    spec = importlib.util.spec_from_file_location('author_preprocess', CODE / 'preprocess/preprocess_re2ob.py')
    pp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pp)
    raw_hashes = {name: sha(RAW / name) for name in ('traces.csv', 'simple_metrics.csv', 'logs.csv', 'inject_time.txt')}
    case_trace = pp._convert_one_trace(str(RAW), 'checkoutservice_cpu_2').drop(columns='_case_id')
    trace = case_trace[case_trace.trace_id == TRACE_ID].copy()
    assert len(trace) == 33 and trace.span_id.nunique() == 33
    assert ROOT_SPAN in set(trace.span_id)
    pairs = sorted({(str(row.cmdb_id), str(row.timestamp)[:10]) for row in trace.itertuples()})
    span_ids = set(trace.span_id)
    seen, pending = set(), [ROOT_SPAN]
    while pending:
        sid = pending.pop()
        assert sid not in seen, 'Cycle or duplicate child'
        seen.add(sid)
        pending.extend(trace.loc[trace.parent_span == sid, 'span_id'].tolist())
    assert seen == span_ids
    trace_path = FULL / 'trace/all/trace_jaeger-span.csv'
    metric_path = FULL / 'metric/all/metrics.csv'
    log_path = FULL / 'log/all/logs.csv'
    full_hashes = {str(p.relative_to(FULL)): sha(p) for p in (trace_path, metric_path, log_path)}
    # Scan all traces to detect collisions/extra children outside the chosen trace.
    full_trace_queries = collect_csv(trace_path, lambda c: c.span_id.isin(span_ids) | c.parent_span.isin(span_ids))
    assert set(full_trace_queries.trace_id) == {TRACE_ID}
    assert len(full_trace_queries) == 33
    trace.to_csv(data / 'trace/all/trace_jaeger-span.csv', index=False)
    ns, client = endpoint_module()
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
    del case_trace, full_trace_queries
    ns.pop('trace_df', None)
    gc.collect()

    # Every KPI matched by the author's service predicate; no anomaly selection.
    case_metric = pp._convert_one_metric_simple(str(RAW), 'checkoutservice_cpu_2').drop(columns='_case_id')

    def metric_mask(frame):
        mask = pd.Series(False, index=frame.index)
        for service, ts in pairs:
            mask |= frame.service_name.str.contains(service, case=False, na=False) & frame.timestamp.between(int(ts)-1200, int(ts)+1200)
        return mask

    full_metric = pd.read_csv(metric_path, low_memory=False)
    expected_case_rows = case_metric[metric_mask(case_metric)].reset_index(drop=True)
    expected_case_rows['node_id'] = expected_case_rows['node_id'].replace('', float('nan'))
    # Provenance only: independent raw conversion can differ in the final bit across
    # pandas versions. Actual package rows are copied VERBATIM from the author CSV.
    pd.testing.assert_frame_equal(full_metric.loc[metric_mask(full_metric)].reset_index(drop=True),
                                  expected_case_rows, check_dtype=False, check_exact=False, rtol=1e-14, atol=0)
    with metric_path.open('r', encoding='utf-8', newline='') as source, (data / 'metric/all/metrics.csv').open('w', encoding='utf-8', newline='') as target:
        target.write(next(source))
        for line in source:
            fields = next(csv.reader([line]))
            ts, service = int(fields[0]), fields[2]
            if any(re.search(svc, service, re.IGNORECASE) and int(at)-1200 <= ts <= int(at)+1200 for svc, at in pairs):
                target.write(line)
    small_metric = pd.read_csv(data / 'metric/all/metrics.csv', low_memory=False)
    # Stronger than response equality: the complete baseline rows must be identical.
    pd.testing.assert_frame_equal(full_metric.loc[metric_mask(full_metric)].reset_index(drop=True),
                                  small_metric.reset_index(drop=True), check_exact=True)
    for service, ts in pairs:
        compare('search_fluctuating_metrics', {'service_name': service, 'timestamp': ts},
                full_metric, small_metric, 'metric_df')
    metric_count = len(small_metric)
    del case_metric, expected_case_rows, full_metric, small_metric
    ns.pop('metric_df', None)
    gc.collect()
    # Empty maps are actual upstream outputs, verified before copying.
    for name in ('service_node_map.pkl', 'node_service_map.pkl'):
        assert (FULL / 'metric' / name).read_bytes() == pickle.dumps({})
        shutil.copyfile(FULL / 'metric' / name, data / 'metric' / name)

    def log_mask(frame):
        mask = pd.Series(False, index=frame.index)
        for service, ts in pairs:
            mask |= frame.cmdb_id.astype(str).str.contains(service, na=False) & frame.timestamp.between(int(ts)-60, int(ts)+60)
        noise = frame.value.astype(str).str.lower().str.contains(r'severity:\s*(?:info|debug)', regex=True, na=False)
        return mask & ~noise

    case_log = pp._convert_one_log(str(RAW), 'checkoutservice_cpu_2').drop(columns='_case_id')
    logs = case_log[log_mask(case_log)]
    logs.to_csv(data / 'log/all/logs.csv', index=False)
    # Scan the entire merged log dataset, applying precisely the endpoint predicate.
    full_log_queries = collect_csv(log_path, log_mask)
    small_logs = pd.read_csv(data / 'log/all/logs.csv', low_memory=False)
    pd.testing.assert_frame_equal(full_log_queries.reset_index(drop=True), small_logs,
                                  check_dtype=False, check_exact=True)
    for service, ts in pairs:
        compare('search_logs', {'service_name': service, 'timestamp': ts}, full_log_queries, small_logs, 'log_df')
    log_count = len(small_logs)
    del case_log, logs, full_log_queries, small_logs
    ns.pop('log_df', None)
    gc.collect()

    # The original header and exact selected row, renumbered to one trace only.
    lines = (FULL / 'error_traces.txt').read_text(encoding='utf-8').splitlines()
    selected = [line for line in lines[1:] if ROOT_SPAN in line.split()]
    assert len(selected) == 1 and TRACE_ID in selected[0]
    tokens = selected[0].split()
    tokens[0] = '0'
    (data / 'error_traces.txt').write_text(lines[0] + '\n' + ' '.join(tokens) + '\n', encoding='utf-8')
    write_json(stage / 'selection.json', {'trace_id': TRACE_ID, 'root_span_id': ROOT_SPAN,
               'span_count': 33, 'query_pairs': [{'service_name': a, 'timestamp': b} for a, b in pairs]})
    gt = pd.read_csv(FULL / 'groundtruth.csv')
    gt = gt[gt.timestamp == int((RAW / 'inject_time.txt').read_text())]
    assert len(gt) == 1
    (stage / 'scoring').mkdir()
    gt.to_csv(stage / 'scoring/groundtruth.csv', index=False)
    for name in UPSTREAM_FILES:
        destination = stage / 'upstream' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        original = subprocess.check_output(['git', '-C', str(CODE), 'show', COMMIT + ':' + name])
        assert original.replace(b'\r\n', b'\n') == (CODE / name).read_bytes().replace(b'\r\n', b'\n'), name
        destination.write_bytes(original)
    for name in ('kaggle-runtime.py', 'smoke-worker.py', 'vllm-t4-compat.py', 'verify-t4-prefix-kernel.py'):
        shutil.copyfile(HERE / name, stage / name)
    report = {'status': 'pass', 'method': 'Unchanged upstream Flask endpoint bodies; byte-for-byte HTTP responses. Full merged CSV scans, complete metric dataframe, exact full baseline row equality.',
              'trace_rows': 33, 'metric_rows': metric_count, 'log_rows': log_count,
              'query_pairs': len(pairs), 'endpoint_comparisons': len(comparisons),
              'comparisons': comparisons, 'pandas_version': pd.__version__,
              'source_inputs_unchanged': raw_hashes == {name: sha(RAW / name) for name in raw_hashes}}
    assert report['source_inputs_unchanged']
    write_json(HERE / 'cpu-equivalence.json', report)
    shutil.copyfile(HERE / 'cpu-equivalence.json', stage / 'cpu-equivalence.json')
    manifest = {'schema_version': 1, 'upstream_commit': COMMIT,
                'upstream_url': 'https://github.com/LLM4AIOps/RCLAgent-V2',
                'benchmark_url': 'https://zenodo.org/records/14590730',
                'benchmark_file': 'RE2-OB.zip',
                'benchmark_zip_sha256': '0605a36cdcad8a6ae0107f2357c9c91ecee2c4ab5d72579bffea0372d9747513',
                'case': 'checkoutservice_cpu_2', 'partition': 'train',
                'selection_rule': 'Previously selected longest author-chosen trace of the first unambiguous train case in author processing order; original error_traces data row 442.',
                'model': 'Qwen/Qwen3-4B-Instruct-2507', 'model_revision': MODEL_REV,
                'raw_case_file_hashes': raw_hashes, 'full_preprocessed_hashes': full_hashes,
                'metrics_source': 'simple_metrics.csv, the upstream preprocessing default; all matched KPIs retained.',
                'data_policy': 'Only selected case. Labels in scoring/; never forwarded to model. Private Kaggle use only.',
                'upstream_patch': None, 'files': {}}
    manifest['files'] = {str(p.relative_to(stage)).replace('\\', '/'): {'sha256': sha(p), 'bytes': p.stat().st_size}
                         for p in sorted(stage.rglob('*')) if p.is_file()}
    write_json(stage / 'manifest.json', manifest)
    shutil.copyfile(stage / 'manifest.json', HERE / 'manifest.json')
    archive = HERE / 'rclagent-kaggle-bundle.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(stage.rglob('*')):
            if path.is_file():
                zipped.write(path, path.relative_to(stage).as_posix())
    (HERE / 'rclagent-kaggle-bundle.zip.sha256').write_text(sha(archive) + '  ' + archive.name + '\n', encoding='utf-8')
    print(json.dumps({'archive': str(archive), 'sha256': sha(archive), 'bytes': archive.stat().st_size,
                      'trace_rows': 33, 'metric_rows': metric_count, 'log_rows': log_count,
                      'endpoint_comparisons': len(comparisons)}, indent=2))


if __name__ == '__main__':
    run()
