"""Compares the model outputs of the same runs in two results packages, e.g. the same bundle under two harness caps.

Usage: compare-run-outputs.py OUT_DIR PACKAGE LABEL1 ZIP1 MANIFEST1 LABEL2 ZIP2 MANIFEST2 [PACKAGE LABEL1 ... ]

Each group of seven arguments is one package pair (PACKAGE names it, e.g. A or B), so A and B go in one call. Both
sides are read through analyze-missing-source-results.py load(), so the same SHA256, bundle and duplicate checks apply.
Runs are paired by (trace_id, condition, seed). Model output means the 'response' events of a run in log order
(retries included): the assistant content and each tool call's name and arguments. Random ids (chatcmpl-..., tool call
ids), 'created', usage and timing are dropped, so only what the model said is compared. Match classes:

- identical: same responses in the same order.
- final_response_only: same number of responses, all but the last equal.
- strict_prefix / side2_prefix: side 1 (side 2) is a proper prefix of the other, e.g. a run stopped by a cap.
- diverged: otherwise; first_divergence is the 1-based index of the first differing response, with its span and
  operation (the request that produced it). no_output: a side has no response.

The request messages are compared too (ids dropped): first_request_divergence is the first 1-based request whose
messages differ, and request_before_response is true when that is at or before the first differing response, that is,
when the model was given different input rather than answering the same input differently. Writes:

- pairs.csv: one row per pair, or per run present on one side only.
- summary.json: per package and 'all', the match classes of capped (side-1 stop cause is a harness cap) and
  non-capped pairs, and how many pairs have equal R@1, MRR and top-1.
"""
import csv
import importlib.util
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def import_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analyzer = import_script('missing_source_analyzer', 'analyze-missing-source-results.py')
stops = import_script('completion_and_budget_stops', 'analyze-completion-and-budget-stops.py')
DROPPED = ('id', 'tool_call_id')
DIVERGED = ('diverged', 'final_response_only')


def strip_ids(value):
    if isinstance(value, dict):
        return {k: strip_ids(v) for k, v in value.items() if k not in DROPPED}
    if isinstance(value, list):
        return [strip_ids(v) for v in value]
    return value


def model_output(event):
    """What the model said in one response event: content and (name, arguments) of the tool calls."""
    body = event.get('body')
    try:
        while isinstance(body, str):
            body = json.loads(body)
        message = body['choices'][0]['message']
        return [message.get('content'), [(c['function']['name'], c['function']['arguments'])
                                         for c in message.get('tool_calls') or []]]
    except (ValueError, KeyError, IndexError, TypeError):
        return ['unparsed', event.get('status'), body]


def sequences(events):
    """(responses, requests): each response as (output, span, operation), each request as its id-free messages."""
    responses, requests, sent = [], [], {}
    for event in events:
        kind = event.get('kind')
        if kind == 'request' and event.get('phase') == 'trace':
            sent[event['number']] = event
            requests.append(strip_ids(stops.payload_of(event).get('messages')))
        elif kind == 'response' and event.get('number') in sent:
            origin = sent[event['number']]
            responses.append((model_output(event), origin.get('span_id'), origin.get('operation')))
    return responses, requests


def first_difference(a, b):
    """1-based index of the first position where the lists differ; a list that ends first counts as a difference."""
    for i, (x, y) in enumerate(zip(a, b), 1):
        if x != y:
            return i
    return min(len(a), len(b)) + 1 if len(a) != len(b) else None


def compare(events1, events2):
    """Match class and divergence details of two runs' event lists."""
    (res1, req1), (res2, req2) = sequences(events1), sequences(events2)
    out1, out2 = [r[0] for r in res1], [r[0] for r in res2]
    first = first_difference(out1, out2)
    first_request = first_difference(req1, req2)
    if not out1 or not out2:
        kind = 'no_output'
    elif first is None:
        kind = 'identical'
    elif len(out1) < len(out2) and out2[:len(out1)] == out1:
        kind = 'strict_prefix'
    elif len(out2) < len(out1) and out1[:len(out2)] == out2:
        kind = 'side2_prefix'
    elif len(out1) == len(out2) and first == len(out1):
        kind = 'final_response_only'
    else:
        kind = 'diverged'
    span, operation = (res1 if first <= len(res1) else res2)[first - 1][1:] if kind in DIVERGED else (None, None)
    return {'match': kind, 'responses_1': len(out1), 'responses_2': len(out2),
            'first_divergence': first if kind in DIVERGED else None, 'divergence_span': span,
            'divergence_operation': operation, 'side1_strict_prefix': kind == 'strict_prefix',
            'requests_1': len(req1), 'requests_2': len(req2), 'first_request_divergence': first_request,
            'request_before_response': first_request is not None and (first is None or first_request <= first)}


def read_events(archive, rid):
    try:
        text = archive.read(f'run/traces/{rid}/events.jsonl').decode()
    except KeyError:
        return []
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def compare_package(package, label1, rows1, zip1, label2, rows2, zip2):
    by1 = {(r['trace_id'], r['condition'], r['seed']): r for r in rows1}
    by2 = {(r['trace_id'], r['condition'], r['seed']): r for r in rows2}
    out = []
    with zipfile.ZipFile(zip1) as z1, zipfile.ZipFile(zip2) as z2:
        for key in sorted(set(by1) | set(by2)):
            a, b = by1.get(key), by2.get(key)
            row = {'package': package, 'trace_id': key[0], 'condition': key[1], 'seed': key[2],
                   'present': 'both' if a and b else f'only_{label1 if a else label2}'}
            if a and b:
                row.update(status_1=a['status'], status_2=b['status'], cause_1=stops.cause(a),
                           cause_2=stops.cause(b), capped=stops.cause(a) in stops.CAPS)
                for metric in ('R@1', 'MRR', 'top1'):
                    row[f'{metric}_1'], row[f'{metric}_2'] = a[metric], b[metric]
                row['scores_equal'] = all(a[m] == b[m] for m in ('R@1', 'MRR', 'top1'))
                row.update(compare(read_events(z1, a['run_id']), read_events(z2, b['run_id'])))
            out.append(row)
    return out


def summarize(rows, packages):
    summary = {}
    for scope in packages + ['all']:
        group = [r for r in rows if scope in ('all', r['package'])]
        both = [r for r in group if r['present'] == 'both']
        entry = {'runs': len(group), 'paired': len(both),
                 'only_one_side': dict(Counter(r['present'] for r in group if r['present'] != 'both'))}
        for name, part in (('all', both), ('capped', [r for r in both if r['capped']]),
                           ('non_capped', [r for r in both if not r['capped']])):
            entry[name] = {'pairs': len(part), 'match': dict(Counter(r['match'] for r in part)),
                           'scores_equal': sum(r['scores_equal'] for r in part),
                           'R@1_equal': sum(r['R@1_1'] == r['R@1_2'] for r in part),
                           'MRR_equal': sum(r['MRR_1'] == r['MRR_2'] for r in part),
                           'top1_equal': sum(r['top1_1'] == r['top1_2'] for r in part),
                           'status_pairs': dict(Counter(f"{r['status_1']}->{r['status_2']}" for r in part)),
                           'request_before_response': sum(r['request_before_response'] for r in part),
                           'divergence_operations': dict(Counter(str(r['divergence_operation']) for r in part
                                                                 if r['first_divergence']))}
        summary[scope] = entry
    return summary


def main():
    if len(sys.argv) < 9 or (len(sys.argv) - 2) % 7:
        raise SystemExit(__doc__)
    out_dir, groups = Path(sys.argv[1]), sys.argv[2:]
    rows, packages = [], []
    for i in range(0, len(groups), 7):
        package, label1, zip1, manifest1, label2, zip2, manifest2 = groups[i:i + 7]
        packages.append(package)
        rows += compare_package(package, label1, analyzer.load(zip1, manifest1), zip1,
                                label2, analyzer.load(zip2, manifest2), zip2)
    out_dir.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (out_dir / 'pairs.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    summary = summarize(rows, packages)
    (out_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    for scope, entry in summary.items():
        print(scope, 'paired', entry['paired'], 'non_capped', entry['non_capped']['match'],
              'capped', entry['capped']['match'])


if __name__ == '__main__':
    main()
