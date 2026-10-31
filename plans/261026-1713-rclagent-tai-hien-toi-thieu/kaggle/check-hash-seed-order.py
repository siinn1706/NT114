"""Checks that a run with PYTHONHASHSEED=0 wrote the services of the final synthesis prompt in seed-0 order, and pairs
its model outputs with an earlier run of the same runs under random hash seeds.

Usage: check-hash-seed-order.py OUT_DIR PYTHON PACKAGE NEW_ZIP NEW_MANIFEST OLD_ZIP OLD_MANIFEST [PACKAGE ...]

Each group of five arguments is one package (A or B): NEW is the run under the fixed seed, OLD the earlier one. Both
sides are read through analyze-missing-source-results.py load(), so its SHA256 and bundle checks apply.

The author's coordinator joins set(error_log_services) and set(metric_anomaly_services) into the final prompt, so their
order follows the process's string hash seed. The same prompt carries the whole evidence graph as JSON, so the two lists
can be rebuilt in the author's order and joined again by PYTHON under a chosen seed. String hashing and set layout
differ between Python versions, so PYTHON must have the major.minor version that ran on Kaggle, read from
environment-before.json beside each results ZIP.

Per run, on both sides, hint is:
- match: seed 0 gives the prompt's exact text;
- other_seed: one of seeds 1..63 does, but seed 0 does not;
- unreachable: no seed does, so the rebuild disagrees with the author's code;
- unparsed: the final prompt lacks the evidence graph;
- no_final_prompt: the run stopped before the final synthesis.
order_sensitive means seeds 0..63 give more than one text, so a match is evidence of seed 0 and not of chance.

Per pair (columns *_1 are NEW, *_2 OLD, as in compare-run-outputs.py), explained is:
- identical: the same model outputs;
- order_only: every request and response before the final request is equal, both final requests were answered, and
  their messages differ only in the service order;
- unexplained: anything else, left for manual review.
summary.json also lists same_order_different_output: pairs whose final prompts have the same service order but whose
outputs differ, which a fixed seed alone cannot explain.

Writes runs.csv, pairs.csv and summary.json. Exits 1 unless every NEW final prompt matches seed 0, none is unparsed and
at least one is order-sensitive.
"""
import csv
import importlib.util
import json
import os
import subprocess
import sys
import zipfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARK = 'Global Evidence Graph ('
END = '\n\nGoal:'
SEEDS = range(64)
# The author's hint, verbatim from upstream coordinator.py; run by PYTHON under each seed.
PREDICT = r'''
import json, sys
hints = []
for error_log_services, metric_anomaly_services in json.load(sys.stdin):
    evidence_hint = ""
    if error_log_services:
        evidence_hint = f"\n⚠️ Services with ERROR LOGS (strongest evidence): {', '.join(set(error_log_services))}"
    if metric_anomaly_services:
        evidence_hint += f"\n⚡ Services with metric anomalies only: {', '.join(set(metric_anomaly_services))}"
    hints.append(evidence_hint)
sys.stdout.buffer.write(json.dumps(hints).encode())
'''


def import_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compare = import_script('compare_run_outputs', 'compare-run-outputs.py')
analyzer = compare.analyzer


def final_request(events):
    """(1-based index among trace requests, responses before it, event) of the first final synthesis request."""
    index, sent, answered = 0, set(), 0
    for event in events:
        if event.get('kind') == 'request' and event.get('phase') == 'trace':
            index += 1
            if event.get('operation') is None:
                return index, answered, event
            sent.add(event['number'])
        elif event.get('kind') == 'response' and event.get('number') in sent:
            answered += 1
    return None, None, None


def parse_prompt(text):
    """(error_log_services, metric_anomaly_services, hint, prompt without hint), rebuilt as the author's loop does."""
    start = text.index('\n', text.index(MARK)) + 1
    nodes, end = json.JSONDecoder().raw_decode(text, start)
    if text[end] != '\n':  # f"{geg.summary()}\n{evidence_hint}"
        raise ValueError('no newline after the evidence graph')
    stop = text.index(END, end)
    errors, metrics = [], []
    for node in nodes:
        evidence = node.get('evidence', '')
        if isinstance(evidence, str):
            if 'has_error_logs' in evidence and '"has_error_logs": true' in evidence.lower():
                errors.append(node['service_name'])
            elif '"is_abnormal": true' in evidence.lower():
                metrics.append(node['service_name'])
    return errors, metrics, text[end + 1:stop], text[:end + 1] + text[stop:]


def final_prompt(events):
    """The final synthesis request of a run: its index, the responses before it, whether it was answered, its messages
    with the hint removed, the parsed prompt (None when unparsable) and an error class."""
    index, answered, event = final_request(events)
    record = {'final_request': index, 'responses_before_final': answered, 'final_answered': False,
              'final_messages': None, 'parsed': None, 'hint': None}
    if event is None:
        return dict(record, hint='no_final_prompt')
    record['final_answered'] = any(e.get('kind') == 'response' and e.get('number') == event['number'] for e in events)
    messages = event['payload'].get('messages', [])
    marked = [i for i, m in enumerate(messages) if isinstance(m.get('content'), str) and MARK in m['content']]
    try:
        parsed = parse_prompt(messages[marked[-1]]['content'])
    except (IndexError, ValueError, KeyError) as exc:
        return dict(record, hint='unparsed: ' + repr(exc))
    without_hint = [dict(m, content=parsed[3]) if i == marked[-1] else m for i, m in enumerate(messages)]
    return dict(record, parsed=parsed, final_messages=compare.strip_ids(without_hint))


def python_version(python):
    out = subprocess.run([python, '-I', '-c', 'import sys; print("%d.%d.%d" % sys.version_info[:3])'],
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


def kaggle_version(archive):
    """The Python version the session ran, from environment-before.json beside the results ZIP."""
    path = Path(archive).parent / 'environment-before.json'
    if not path.exists():
        raise SystemExit(f'{path} missing: the Python version that ran on Kaggle is unknown')
    return json.loads(path.read_text(encoding='utf-8'))['python'].split()[0]


def predict(python, lists):
    """{seed: [hint per (errors, metrics)]} from PYTHON under PYTHONHASHSEED=seed."""
    data = json.dumps(lists).encode()
    out = {}
    for seed in SEEDS:
        # No -I or -E here: both make Python ignore PYTHONHASHSEED. -s still keeps user site-packages out.
        env = dict(os.environ, PYTHONHASHSEED=str(seed))
        done = subprocess.run([python, '-s', '-X', 'utf8', '-c', PREDICT], input=data, capture_output=True,
                              env=env, check=True)
        out[seed] = json.loads(done.stdout)
    return out


def classify(hint, texts):
    """texts[s] is the hint seed s gives."""
    if texts[0] == hint:
        return 'match'
    return 'other_seed' if hint in texts else 'unreachable'


def read_runs(package, side, rows, archive):
    """Per-run records with the parsed final prompt; the hint is classified once all predictions exist."""
    records = {}
    with zipfile.ZipFile(archive) as zipped:
        for row in rows:
            key = (row['trace_id'], row['condition'], row['seed'])
            records[key] = {'package': package, 'side': side, 'run_id': row['run_id'], 'status': row['status'],
                            **final_prompt(compare.read_events(zipped, row['run_id']))}
    return records


def explain(pair, new, old):
    if pair['match'] == 'identical':
        return 'identical'
    if (new and old and new['parsed'] and old['parsed'] and new['final_answered'] and old['final_answered']
            and new['final_request'] == old['final_request']):
        requests_equal = pair['first_request_divergence'] == new['final_request']
        responses_equal = (pair['first_divergence'] or sys.maxsize) > new['responses_before_final']
        if requests_equal and responses_equal and new['final_messages'] == old['final_messages']:
            return 'order_only'
    return 'unexplained'


def main():
    if len(sys.argv) < 8 or (len(sys.argv) - 3) % 5:
        raise SystemExit(__doc__)
    out_dir, python, groups = Path(sys.argv[1]), sys.argv[2], sys.argv[3:]
    predictor = python_version(python)
    records, pairs, packages, kaggle = {}, [], [], {}
    for i in range(0, len(groups), 5):
        package, new_zip, new_manifest, old_zip, old_manifest = groups[i:i + 5]
        packages.append(package)
        for side, archive in (('new', new_zip), ('old', old_zip)):
            kaggle[f'{package}/{side}'] = version = kaggle_version(archive)
            if version.split('.')[:2] != predictor.split('.')[:2]:
                raise SystemExit(f'{python} is Python {predictor}, but {archive} ran Python {version}')
        new_rows, old_rows = analyzer.load(new_zip, new_manifest), analyzer.load(old_zip, old_manifest)
        for side, rows, archive in (('new', new_rows, new_zip), ('old', old_rows, old_zip)):
            for key, record in read_runs(package, side, rows, archive).items():
                records[(package, side) + key] = record
        pairs += compare.compare_package(package, 'new', new_rows, new_zip, 'old', old_rows, old_zip)
    parsed = [r for r in records.values() if r['parsed']]
    predictions = predict(python, [list(r['parsed'][:2]) for r in parsed])
    for n, record in enumerate(parsed):
        texts = [predictions[s][n] for s in SEEDS]
        record['hint'] = classify(record['parsed'][2], texts)
        record['order_sensitive'] = len(set(texts)) > 1
        record['services'] = len(set(record['parsed'][0])) + len(set(record['parsed'][1]))
    for pair in pairs:
        key = (pair['trace_id'], pair['condition'], pair['seed'])
        new, old = records.get((pair['package'], 'new') + key), records.get((pair['package'], 'old') + key)
        pair['hint_new'], pair['hint_old'] = (new or {}).get('hint'), (old or {}).get('hint')
        pair['hint_order_equal'] = bool(new and old and new['parsed'] and old['parsed']
                                        and new['parsed'][2] == old['parsed'][2])
        pair['explained'] = explain(pair, new, old) if pair['present'] == 'both' else 'unexplained'
    run_rows = [{'package': r['package'], 'side': r['side'], 'run_id': r['run_id'], 'status': r['status'],
                 'final_request': r['final_request'], 'hint': r['hint'].split(':')[0],
                 'detail': r['hint'] if r['hint'].startswith('unparsed') else '',
                 'order_sensitive': r.get('order_sensitive'), 'services': r.get('services')}
                for r in records.values()]
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in (('runs.csv', run_rows), ('pairs.csv', pairs)):
        with (out_dir / name).open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
            writer.writeheader()
            writer.writerows(rows)
    summary = {'python': {'predictor': predictor, 'kaggle': kaggle}}
    for side in ('new', 'old'):
        group = [r for r in run_rows if r['side'] == side]
        summary[side] = {'runs': len(group), 'hint': dict(Counter(r['hint'] for r in group)),
                         'order_sensitive': sum(bool(r['order_sensitive']) for r in group),
                         'order_sensitive_match': sum(bool(r['order_sensitive']) and r['hint'] == 'match'
                                                      for r in group)}
    summary['pairs'] = {scope: dict(Counter(p['explained'] for p in pairs if scope in ('all', p['package'])))
                        for scope in packages + ['all']}
    def label(p):
        return f"{p['package']} {p['trace_id']} {p['condition']} {p['seed']}"
    summary['unexplained'] = [label(p) for p in pairs if p['explained'] == 'unexplained']
    summary['same_order_different_output'] = [label(p) for p in pairs
                                              if p['hint_order_equal'] and p['match'] != 'identical']
    new_hints = summary['new']['hint']
    summary['verified'] = (set(new_hints) <= {'match', 'no_final_prompt'} and summary['new']['order_sensitive_match'] > 0)
    (out_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: summary[k] for k in ('new', 'old', 'pairs', 'same_order_different_output', 'verified')}))
    if not summary['verified']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
