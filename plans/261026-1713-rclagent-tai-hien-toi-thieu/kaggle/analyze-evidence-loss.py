"""Measures, per run, where the evidence of the injected fault is lost between the telemetry tools and the final ranking,
from the events.jsonl of the results ZIPs alone; no model request, no Kaggle, no test split.

Usage: analyze-evidence-loss.py OUT_DIR PACKAGE ZIP MANIFEST [PACKAGE ZIP MANIFEST ...]
                                [--runs FILE] [--structure-only] [--label NAME]

The options may stand anywhere on the command line. Each group of three arguments is one package (A or B); its ZIP is read
through analyze-missing-source-results.py load(), so the SHA256, bundle and duplicate checks apply. --runs FILE keeps only
the run ids listed in FILE (one per line). --structure-only counts spans, spans of the faulty service and tree depth per
case and writes no indicator, label or score. --label NAME is recorded in summary.json.

Indicators per run, each true, false, NA (not determinable) or, for I0 only, NA_censored:
- I0 a metric table that holds a KPI of the faulty service reached the model (the harness tool answers any query whose
  text matches the service, so this is close to "the model asked for it");
- I1 a span that received such a table marked itself abnormal;
- I2 the root's consolidation names the faulty service;
- I3 the hint of the final prompt, rebuilt with the author's string rules, lists the faulty service;
- I4 the final ranking puts it first;
- I5 how the first final candidate relates to the root's consolidation label (same, diff, refusal).
A run that stopped before its final answer is right-censored: indicators that are true stay, false ones become NA.
The evidence reaches the final prompt along three independent paths (root report, whole evidence graph, hint), so the
vector of indicators is the result; first_loss_linear (first false indicator in the order I0..I4) is a secondary view
and is biased by that order: I2 always precedes I3, so a run whose root report drops the service is labelled at I2 even
when the service is in the evidence graph and the hint. final_residual labels what is left of a missed first place.

Column names of runs.csv that differ from the pre-registered indicator names: I5 is final_top1_matches_root_label.
The diagnostic gt_kpi_in_table is not a separate column; table_received (the basis of I0) carries it. A span with
has_error_logs true and no search_logs call is not D1, because D1 needs the logs the model was given.
For a censored run the evidence graph is partial, so the hint sizes, gt_sole_entry and the dropped-list sizes are NA.

Writes spans.csv, runs.csv, cases.csv, case-comparison.csv, funnel.csv and summary.json (UTF-8, sorted by key). It
refuses to write into a folder that already holds a summary.json. The summary is provisional while any run has an
integrity problem.
"""
import ast
import csv
import hashlib
import importlib.util
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREREG = HERE / 'evidence-loss-prereg.json'


def import_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hash_order = import_script('hash_seed_order_for_evidence_loss', 'check-hash-seed-order.py')
compare = hash_order.compare
analyzer = compare.analyzer
stops = compare.stops
IMPORTED = ('check-hash-seed-order.py', 'compare-run-outputs.py', 'analyze-missing-source-results.py',
            'analyze-completion-and-budget-stops.py')

METRIC, LOGS = 'search_fluctuating_metrics', 'search_logs'
NO_ROWS = '{"message":"No matching records found."}'
NO_KPI = '{"message":"No fluctuating metrics found."}'
NO_ROWS_SENTENCE, NO_KPI_SENTENCE = 'No matching records found.', 'No fluctuating metrics found.'
REFUSALS = {'none', 'unknown', 'null', 'n/a', 'na'}
# config.get_known_services() of the upstream coordinator for the re2ob dataset, which the harness selects.
KNOWN_SERVICES = ('adservice', 'cartservice', 'checkoutservice', 'currencyservice', 'emailservice', 'frontend',
                  'frontendservice', 'paymentservice', 'productcatalogservice', 'recommendationservice',
                  'shippingservice', 'redis')
HINT_ERROR_PREFIX = '⚠️ Services with ERROR LOGS (strongest evidence): '
HINT_METRIC_PREFIX = '⚡ Services with metric anomalies only: '
FALLBACK_PREFIX = 'Based on all retrieved evidence above'
ERROR_WORDS = re.compile(r'error|exception|fail', re.I)
KNOWN_KINDS = {'request', 'response', 'tool_result', 'tool_result_budget', 'agent_complete',
               'malformed_tool_call_retry', 'fatal', 'worker_error'}
SOURCES = {'author', 'repaired', 'absent'}
# Stop reason substrings; the first row with a matching substring names the class.
HARNESS = (('H_cap', ('Output stopped without completion', 'Per-span tool round budget exceeded',
                      'Model request budget exhausted', 'RCLAgent deadline exceeded')),
           ('H_context', ('Context overflow',)),
           ('H_query', ('Unexpected telemetry tool', 'Unsupported telemetry tool parameters',
                        'Telemetry timestamp is not parseable', 'outside the packaged time window')),
           ('H_infra', ('Model server HTTP', 'Request/template incompatibility', 'Telemetry transport failure',
                        'Telemetry tool transport failure', 'Tool-result budget')),
           ('H_parse', ('Invalid structured response', 'Invalid agent JSON output',
                        'Exactly one structured print_results call', 'Empty model output',
                        'Author client failed after bounded retries', 'No valid final result')))
INDICATORS = ('I0', 'I1', 'I2', 'I3', 'I4')
FEASIBLE_UNITS = 3
FIRST_LOSS_NOTE = ('first_loss_linear is order-biased: I2 precedes I3 by convention, not by dependence, so a run whose '
                   'root report drops the service is labelled S2 even when the service is in the evidence graph and '
                   'the hint and the run ranks it first. S4 appears only when I0..I3 are all true. The vector of '
                   'indicators is the primary result.')
SPAN_FIELDS = (
    'run_id', 'case', 'condition', 'seed', 'span_id', 'parent_span', 'depth', 'cmdb_id', 'is_root', 'is_gt_span',
    'gt_span_in_trace', 'self_requests', 'self_retries', 'log_calls', 'metric_calls', 'queried_gt', 'metric_tables',
    'table_key_prefixes', 'table_has_gt_kpi', 'table_gt_kpi_from_nonmatching_query', 'tool_match_rule_differs',
    'metric_empty_reasons', 'metric_query_ts_offset_s', 'is_carrier', 'self_present', 'self_is_abnormal',
    'self_has_error_logs', 'self_has_metric_anomaly', 'fallback_used', 'fallback_flags_missing', 'hint_list', 'D1',
    'D1_na', 'd1_log_source', 'D1_empty_logs', 'D2', 'log_result_classes', 'cons_present', 'cons_class', 'cons_label',
    'carrier_abnormal', 'chain_depth_kept', 'break_class', 'hint_list_size', 'gt_sole_entry', 'd1_dropped_list_size',
    'd2_dropped_list_size')


# -- Names: the scorer's matching, copied from upstream evaluate.py and coordinator.py ------------------------------

def base_of(name):
    low = name.lower()
    found = re.match(r'^(.+?)-[a-z0-9]{5,}-[a-z0-9]{4,}$', low)
    if found:
        return found.group(1)
    if low[-1:].isdigit():
        return low.rsplit('-', 1)[0]
    return low


def label_hit(label, candidates):
    """0-based rank of the first candidate the scorer counts as the label, or -1."""
    label_low = label.lower()
    label_base = base_of(label_low)
    for rank, candidate in enumerate(candidates):
        cand_low = str(candidate).lower()
        cand_base = base_of(cand_low)
        if label_low == cand_low:
            return rank
        if label_base == cand_base and label_base:
            return rank
        if cand_low.startswith(label_low) and (len(cand_low) == len(label_low) or cand_low[len(label_low)] == '-'):
            return rank
        if label_low.startswith(cand_low) and (len(label_low) == len(cand_low) or label_low[len(cand_low)] == '-'):
            return rank
    return -1


rank_of = label_hit


def match(a, b):
    return label_hit(a, [b]) == 0


def in_list(a, names):
    return label_hit(a, names) >= 0


def normalise_name(name):
    """The author's normalisation of a service name (coordinator.py _normalise_name)."""
    low = name.lower().strip()
    base = low.rsplit('-', 1)[0] if low[-1:].isdigit() else low
    if base in KNOWN_SERVICES:
        return low
    dehyphen = low.replace('-service', 'service').replace('-cart', '-cart')
    base2 = dehyphen.rsplit('-', 1)[0] if dehyphen[-1:].isdigit() else dehyphen
    if base2 in KNOWN_SERVICES:
        return dehyphen
    parts = low.split('-')
    if len(parts) >= 2 and parts[-1].isdigit():
        service = ''.join(parts[:-1])
        if service in KNOWN_SERVICES:
            return f'{service}-{parts[-1]}'
    elif len(parts) >= 2:
        service = ''.join(parts)
        if service in KNOWN_SERVICES:
            return service
    return low


def classify_label(value, gt):
    """(class, normalised label, class without normalisation) of a local_root_cause; class is gt, other_service or refusal."""
    if not isinstance(value, str):
        return 'refusal', None, 'refusal'
    stripped = value.strip()
    if not stripped or stripped.lower() in REFUSALS:
        return 'refusal', None, 'refusal'
    normalised = normalise_name(stripped)
    return ('gt' if match(gt, normalised) else 'other_service', normalised,
            'gt' if match(gt, stripped.lower()) else 'other_service')


# -- Reading a run ------------------------------------------------------------------------------------------------

def parse_params(value):
    """(params dict, recognised); the dict is the real shape, the string form is the fallback."""
    if isinstance(value, dict):
        return value, True
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return {}, False
        return (parsed, True) if isinstance(parsed, dict) else ({}, False)
    return {}, False


def canonical(params):
    return json.dumps(params, sort_keys=True, default=str)


def parse_object(text):
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def read_json(zipped, names, path, problems):
    if path not in names:
        return None
    try:
        return json.loads(zipped.read(path).decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        problems.append(f'unparseable {path.rsplit("/", 1)[-1]}')
        return None


def read_gt(zipped, names, rid):
    path = f'run/scoring/{rid}/groundtruth.csv'
    if path not in names:
        return None
    rows = list(csv.DictReader(zipped.read(path).decode('utf-8').splitlines()))
    return (rows[0].get('cmdb_id') or '').strip() or None if rows else None


def read_run(zipped, names, row, progress, gt):
    """The raw material of one run; an unparseable events line is an integrity problem of the run."""
    rid, problems, events = row['run_id'], [], []
    path = f'run/traces/{rid}/events.jsonl'
    if path in names:
        for number, line in enumerate(zipped.read(path).decode('utf-8').split('\n'), 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except ValueError:
                problems.append(f'unparseable events line {number}')
                continue
            if isinstance(event, dict):
                events.append(event)
            else:
                problems.append(f'events line {number} is not an object')
    score_path = f'run/scoring/{rid}/author-score.txt'
    return dict(row, events=events, problems=problems, gt=gt, progress=progress.get(rid) or {},
                graph=read_json(zipped, names, f'run/traces/{rid}/trace-graph.json', problems),
                result=read_json(zipped, names, f'run/traces/{rid}/result.json', problems),
                worker=read_json(zipped, names, f'run/traces/{rid}/worker-status.json', problems),
                author_score=zipped.read(score_path).decode('utf-8', 'replace') if score_path in names else None)


def flatten_tree(graph, problems):
    """Spans of the trace graph in pre-order as dicts with span_id, raw, parent and depth."""
    spans = []

    def walk(node, parent, depth):
        raw = node.get('raw') or {}
        span_id = node.get('span_id')
        if raw.get('parent_span') != parent:
            problems.append(f'span {span_id} names parent {raw.get("parent_span")}, but sits under {parent}')
        spans.append({'span_id': span_id, 'raw': raw, 'parent': parent, 'depth': depth})
        for child in node.get('children') or []:
            walk(child, span_id, depth + 1)

    walk(graph, None, 0)
    return spans


def join_tool_results(events, problems):
    """Tool results in log order. Each is matched, as a multiset, with a tool call of the response before it by
    (name, params, span); a budget event is attached to the result it follows."""
    results, pending, request, open_logs = [], Counter(), None, []
    for event in events:
        kind = event.get('kind')
        if kind == 'request' and event.get('phase') == 'trace':
            request, pending = event, Counter()
        elif kind == 'response':
            if request is None or event.get('number') != request.get('number'):
                problems.append(f'response {event.get("number")} does not follow request '
                                f'{request and request.get("number")}')
                request = request or {}
            pending = Counter()
            for name, arguments in stops.tool_calls(event) or ():
                params = parse_object(arguments) or {}
                pending[(name, canonical(params), request.get('span_id'))] += 1
        elif kind == 'tool_result':
            params, recognised = parse_params(event.get('params'))
            key = (event.get('name'), canonical(params), event.get('span_id'))
            if pending[key] > 0:
                pending[key] -= 1
            else:
                problems.append(f'tool_result {event.get("name")} of span {event.get("span_id")} matches no tool call')
            if not recognised:
                problems.append(f'tool_result {event.get("name")} of span {event.get("span_id")} has unrecognised params')
            results.append({'name': event.get('name'), 'params': params, 'params_string': isinstance(event.get('params'), str),
                            'params_unrecognised': not recognised, 'response': event.get('response'),
                            'source': event.get('source'), 'span_id': event.get('span_id'), 'budget': None})
            open_logs.append(results[-1])
        elif kind == 'tool_result_budget':
            params, _ = parse_params(event.get('params'))
            for result in reversed(open_logs):
                if (result['budget'] is None and result['name'] == event.get('name')
                        and canonical(result['params']) == canonical(params)
                        and result['span_id'] == event.get('span_id')):
                    result['budget'] = event
                    break
            else:
                problems.append(f'budget event of span {event.get("span_id")} follows no tool_result')
    return results


def structural_problems(run):
    """(problems, spans, joined tool results) of a run: parse problems, tree parents and the tool-call join."""
    problems = list(run['problems'])
    spans = flatten_tree(run['graph'], problems) if run['graph'] else []
    if not spans:
        problems.append('no trace graph')
    return problems, spans, join_tool_results(run['events'], problems)


# -- Span facts ---------------------------------------------------------------------------------------------------

def flag(values, key):
    value = (values or {}).get(key)
    return value if isinstance(value, bool) else None


def hint_list(evidence):
    """Which hint list the author's string rule puts a span's self-evidence in: error, metric or ''."""
    if not isinstance(evidence, str):
        return ''
    low = evidence.lower()
    if 'has_error_logs' in evidence and '"has_error_logs": true' in low:
        return 'error'
    if '"is_abnormal": true' in low:
        return 'metric'
    return ''


def reconstruct_hint(nodes):
    """(error_log_services, metric_anomaly_services) from (service_name, evidence) in the author's order."""
    errors, metrics = [], []
    for service, evidence in nodes:
        which = hint_list(evidence)
        (errors if which == 'error' else metrics if which == 'metric' else []).append(service)
    return errors, metrics


def prompt_hint(text):
    """The two service sets named by the hint lines of a final prompt."""
    sets = {HINT_ERROR_PREFIX: set(), HINT_METRIC_PREFIX: set()}
    for line in text.splitlines():
        for prefix in sets:
            if line.startswith(prefix):
                sets[prefix] = set(line[len(prefix):].split(', '))
    return sets[HINT_ERROR_PREFIX], sets[HINT_METRIC_PREFIX]


def delivered_text(result):
    """What the model saw of a tool result: the condensed text of an applied budget, else the response."""
    budget = result.get('budget')
    if budget and budget.get('applied') and isinstance(budget.get('delivered'), str):
        return budget['delivered']
    return result['response'] if isinstance(result['response'], str) else ''


def log_class(text):
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) <= 1:
        return 'empty'
    return 'error_text' if any(ERROR_WORDS.search(line) for line in lines) else 'no_error_text'


def metric_kind(result):
    """absent_source, table, no_kpi, no_rows or other; an absent source is checked first (its bytes equal no_rows)."""
    text = result['response'].strip() if isinstance(result['response'], str) else ''
    if result['source'] == 'absent':
        return 'absent_source'
    if text.startswith('key,'):
        return 'table'
    return 'no_kpi' if text == NO_KPI else 'no_rows' if text == NO_ROWS else 'other'


def table_keys(text):
    return [line.split(',', 1)[0] for line in text.strip().splitlines()[1:] if line.strip()]


def span_metric_view(results, gt, raw_timestamp):
    """What a span's metric queries gave, judged against the faulty service gt."""
    view = {'queried_gt': False, 'tables': 0, 'prefixes': set(), 'has_gt_kpi': False, 'from_nonmatching': False,
            'rule_differs': False, 'empty_reasons': [], 'offset': 'NA', 'gt_reasons': []}
    for number, result in enumerate(results):
        service = result['params'].get('service_name')
        queried = isinstance(service, str) and match(gt, service)
        kind = metric_kind(result)
        view['queried_gt'] |= queried
        if number == 0:
            try:
                view['offset'] = (int(result['params'].get('timestamp')) - int(raw_timestamp)) / 1000
            except (TypeError, ValueError):
                pass
        if kind == 'table':
            keys = table_keys(result['response'])
            gt_kpi = any(len(parts) >= 2 and match(gt, parts[-2]) for parts in (k.split('.') for k in keys))
            view['tables'] += 1
            view['prefixes'] |= {k.split('.')[0] for k in keys}
            view['has_gt_kpi'] |= gt_kpi
            view['from_nonmatching'] |= gt_kpi and not queried
            view['rule_differs'] |= gt_kpi != queried
            kind = 'table_gt_kpi' if gt_kpi else 'table_no_gt_kpi'
        view['empty_reasons'].append(kind)
        if queried and kind != 'table_gt_kpi':
            view['gt_reasons'].append('table_no_gt_kpi' if kind == 'table_no_gt_kpi' else kind)
    return view


def d1_flags(selfd, logs):
    """(D1, D1_na, log source, D1_empty_logs, log classes) of a span: a claimed error log with no error line in the
    logs the model was given. A span with no log query, or one whose logs differ in source, is not D1."""
    hel = flag(selfd, 'has_error_logs')
    sources = sorted({str(r['source']) for r in logs})
    source = 'none' if not sources else sources[0] if len(sources) == 1 else 'mixed'
    classes = [log_class(delivered_text(r)) for r in logs]
    flags = {'classes': ';'.join(sorted(set(classes)))}
    if hel is None:
        return dict(flags, d1='NA', na=False, source=source, empty='NA')
    if not hel:
        return dict(flags, d1=False, na=False, source=source, empty=False)
    if source == 'absent':
        return dict(flags, d1='NA', na=True, source=source, empty=False)
    usable = bool(logs) and source != 'mixed' and 'absent' not in sources
    return dict(flags, d1=usable and 'error_text' not in classes, na=False, source=source,
                empty=usable and set(classes) == {'empty'})


def d2_flag(selfd, tables):
    """D2: abnormal without error logs or metric anomaly flags and without any metric table. Missing flags give NA."""
    abnormal = flag(selfd, 'is_abnormal')
    if abnormal is None:
        return 'NA'
    if not abnormal:
        return False
    error, metric = flag(selfd, 'has_error_logs'), flag(selfd, 'has_metric_anomaly')
    if error is None or metric is None:
        return 'NA'
    return not error and not metric and not tables


def is_fallback(request):
    """True when the last message of the span conversation asks for the fallback conclusion."""
    try:
        last = (stops.payload_of(request).get('messages') or [None])[-1]
        return last['role'] == 'user' and last['content'].startswith(FALLBACK_PREFIX)
    except (KeyError, TypeError, AttributeError, ValueError):
        return False


# -- Harness class and the indicators -----------------------------------------------------------------------------

def stop_reason(run):
    worker, progress = run['worker'] or {}, run['progress']
    fatal = next((e.get('reason') for e in run['events'] if e.get('kind') == 'fatal'), None)
    for value in (worker.get('fatal'), worker.get('error'), progress.get('reason'), fatal):
        if value:
            return str(value)
    return ''


def harness_class(status, reason):
    if status == 'passed':
        return 'none'
    return next((name for name, marks in HARNESS if any(m in reason for m in marks)), 'H_other')


def censor(value, censored):
    return 'NA' if value is False and censored else value


def leading_true(values):
    """(number of leading true indicators, how the run ended: false, NA or all)."""
    count = 0
    for value in values:
        if value is True:
            count += 1
        else:
            return count, 'false' if value is False else 'NA'
    return count, 'all'


def first_loss_linear(values):
    for number, value in enumerate(values):
        if value is False:
            return f'S{number}'
        if value is not True:
            return 'NA'
    return 'preserved'


def final_residual(i0, i1, i3, i4, i5):
    """(label, split) of what is left of a missed first place; split names the I5 class of the remaining case."""
    if i4 is True:
        return 'none', ''
    if i4 is not False:
        return 'NA', ''
    if i0 is False:
        return 'S0', ''
    if i0 is not True:
        return 'NA', ''
    if i1 is False:
        return 'S1', ''
    if i1 is not True:
        return 'NA', ''
    if i3 is False:
        return 'hint_missing_not_rank1', ''
    if i3 is not True:
        return 'NA', ''
    split = {'same': 'top1_equals_wrong_root_label', 'diff': 'top1_differs_from_root_label',
             'refusal': 'root_refusal'}.get(i5, 'NA')
    return 'reaches_final_input_not_rank1', split


def author_score(text):
    if text is None:
        return None
    first = re.search(r'^\s*R@1\s*:\s*([0-9.]+)\s*\((\d+)/(\d+)\)', text, re.M)
    mrr = re.search(r'^\s*MRR\s*:\s*([0-9.]+)', text, re.M)
    return (float(first.group(1)), mrr.group(1)) if first and mrr else None


def fingerprint(events, problems=None):
    """Compact view of a run for the comparison across conditions: hashes of the request messages (as given and with
    the two empty-metric sentences merged), their operations and the agent outputs keyed by (span, operation, n)."""
    requests, merged, operations, counts, complete = [], [], [], Counter(), {}
    for event in events:
        if event.get('kind') == 'request' and event.get('phase') == 'trace':
            try:
                messages = stops.payload_of(event).get('messages')
            except (KeyError, TypeError, ValueError, AttributeError):
                messages = []
                if problems is not None:
                    problems.append(f'request {event.get("number")} has an unreadable payload')
            text = json.dumps(compare.strip_ids(messages), sort_keys=True)
            requests.append(hashlib.sha1(text.encode()).hexdigest())
            merged.append(hashlib.sha1(text.replace(NO_KPI_SENTENCE, NO_ROWS_SENTENCE).encode()).hexdigest())
            operations.append(event.get('operation'))
        elif event.get('kind') == 'agent_complete':
            key = (event.get('span_id'), event.get('operation'))
            counts[key] += 1
            complete[key + (counts[key],)] = hashlib.sha1(str(event.get('output')).encode()).hexdigest()
    return {'requests': requests, 'merged': merged, 'operations': operations, 'complete': complete}


# -- One run ------------------------------------------------------------------------------------------------------

def analyze_run(run):
    """(span rows, run row, fingerprint, unseen branch counts) of one run read by read_run()."""
    problems, spans, results = structural_problems(run)
    events, gt, unseen = run['events'], run['gt'], Counter()
    worker = run['worker'] or {}
    status = worker.get('status') or 'missing'
    result = run['result']
    candidates = result.get('root_causes') if isinstance(result, dict) else None
    candidates = candidates if isinstance(candidates, list) else None
    completed = status == 'passed' and candidates is not None
    censored = not completed
    if status == 'passed' and not completed:
        problems.append('passed run without a usable result.json')
    if gt is None:
        problems.append('no ground truth for the case')
    index = {s['span_id']: s for s in spans}
    data = {s['span_id']: {'self_requests': 0, 'retries': 0, 'fallback': False, 'self': None, 'cons': None,
                           'metric': [], 'logs': []} for s in spans}
    geg, requests, retries = [], 0, 0
    for event in events:
        kind = event.get('kind')
        if kind not in KNOWN_KINDS:
            unseen[f'kind:{kind}'] += 1
        if kind == 'request' and event.get('phase') == 'trace':
            retry = (event.get('attempt') or 0) > 0
            requests += not retry
            span = data.get(event.get('span_id'))
            if span is not None and event.get('operation') == 'self_state_verification':
                if retry:
                    span['retries'] += 1
                else:
                    span['self_requests'] += 1
                    span['fallback'] = is_fallback(event)
        elif kind == 'malformed_tool_call_retry':
            retries += 1
        elif kind == 'agent_complete':
            span, operation = data.get(event.get('span_id')), event.get('operation')
            if operation not in ('self_state_verification', 'consolidate'):
                unseen[f'agent_complete_operation:{operation}'] += 1
            elif span is None:
                problems.append(f'agent_complete for span {event.get("span_id")} outside the trace graph')
            elif operation == 'self_state_verification':
                if span['self'] is not None:
                    problems.append(f'span {event.get("span_id")} has more than one self-state')
                span['self'] = event.get('output')
                raw = index[event['span_id']]['raw']
                name = raw['cmdb_id'] if raw.get('cmdb_id') is not None else raw.get('service_name')
                name = event['span_id'] if name is None else name
                geg.append((event['span_id'], name, event.get('output')))
            else:
                span['cons'] = event.get('output')
    metric_budget = sum(e.get('kind') == 'tool_result_budget' and e.get('name') == METRIC for e in events)
    if metric_budget:
        problems.append(f'{metric_budget} budget events for metric results')
    for result_row in results:
        span = data.get(result_row['span_id'])
        if result_row['params_string']:
            unseen['params_string'] += 1
        if result_row['params_unrecognised']:
            unseen['params_unrecognised'] += 1
        if result_row['source'] not in SOURCES:
            unseen[f'source:{result_row["source"]}'] += 1
        if span is None:
            problems.append(f'tool_result of span {result_row["span_id"]} outside the trace graph')
        elif result_row['name'] == METRIC:
            span['metric'].append(result_row)
        elif result_row['name'] == LOGS:
            span['logs'].append(result_row)
    roots = [s for s in spans if s['parent'] is None]
    if len(roots) > 1:
        problems.append(f'{len(roots)} root spans')
    gt_name = gt or ''
    gt_spans = sum(match(gt_name, s['raw'].get('cmdb_id', '') or '') for s in spans) if gt else 0
    hint_nodes = [(service, evidence) for _, service, evidence in geg]
    errors, metrics = reconstruct_hint(hint_nodes)
    cons_class = {}
    cons_info = {}
    for span_id, d in data.items():
        consd = parse_object(d['cons'])
        if d['cons'] is not None and consd is None:
            problems.append(f'consolidation of span {span_id} is not a JSON object')
        if consd is None:
            cons_class[span_id] = 'NA'
            continue
        label, normalised, raw_class = classify_label(consd.get('local_root_cause'), gt_name)
        cons_class[span_id], cons_info[span_id] = label, (consd, normalised, raw_class)
        if isinstance(consd.get('local_root_cause'), str) and normalised != consd['local_root_cause'].strip().lower() \
                and label != 'refusal':
            unseen['label_normalisation_changes_name'] += 1
    span_rows, per_run_views = [], {}
    for s in spans:
        d, span_id = data[s['span_id']], s['span_id']
        selfd = parse_object(d['self'])
        if d['self'] is not None and selfd is None:
            problems.append(f'self-state of span {span_id} is not a JSON object')
        view = span_metric_view(d['metric'], gt_name, s['raw'].get('timestamp'))
        carrier = gt is not None and view['has_gt_kpi']
        abnormal = flag(selfd, 'is_abnormal')
        flags_missing = (d['fallback'] and (flag(selfd, 'has_error_logs') is None
                                            or flag(selfd, 'has_metric_anomaly') is None))
        if d['fallback']:
            unseen['fallback_used'] += 1
        which = hint_list(d['self'])
        if abnormal is True and not which:
            unseen['parsed_true_but_hint_string_false'] += 1
        d1 = d1_flags(selfd, d['logs'])
        row = {'run_id': run['run_id'], 'case': run['trace_id'][:6], 'condition': run['condition'],
               'seed': run['seed'], 'span_id': span_id, 'parent_span': s['parent'], 'depth': s['depth'],
               'cmdb_id': s['raw'].get('cmdb_id'), 'is_root': s['parent'] is None,
               'is_gt_span': gt is not None and bool(s['raw'].get('cmdb_id')) and match(gt, s['raw']['cmdb_id']),
               'gt_span_in_trace': gt_spans, 'self_requests': d['self_requests'], 'self_retries': d['retries'],
               'log_calls': len(d['logs']), 'metric_calls': len(d['metric']), 'queried_gt': view['queried_gt'],
               'metric_tables': view['tables'], 'table_key_prefixes': sorted(view['prefixes']),
               'table_has_gt_kpi': view['has_gt_kpi'], 'table_gt_kpi_from_nonmatching_query': view['from_nonmatching'],
               'tool_match_rule_differs': view['rule_differs'], 'metric_empty_reasons': view['empty_reasons'],
               'metric_query_ts_offset_s': view['offset'], 'is_carrier': carrier, 'self_present': selfd is not None,
               'self_is_abnormal': 'NA' if abnormal is None else abnormal,
               'self_has_error_logs': 'NA' if flag(selfd, 'has_error_logs') is None else flag(selfd, 'has_error_logs'),
               'self_has_metric_anomaly': 'NA' if flag(selfd, 'has_metric_anomaly') is None
               else flag(selfd, 'has_metric_anomaly'),
               'fallback_used': d['fallback'], 'fallback_flags_missing': flags_missing, 'hint_list': which,
               'D1': d1['d1'], 'D1_na': d1['na'], 'd1_log_source': d1['source'], 'D1_empty_logs': d1['empty'],
               'D2': d2_flag(selfd, view['tables']), 'log_result_classes': d1['classes'],
               'cons_present': d['cons'] is not None, 'cons_class': cons_class[span_id],
               'cons_label': (cons_info.get(span_id) or (None, None))[1], 'carrier_abnormal': carrier and abnormal is True,
               'chain_depth_kept': '', 'break_class': ''}
        if row['carrier_abnormal']:
            kept, node, steps = 0, span_id, 0
            row['break_class'] = 'none'
            while node is not None and steps <= len(spans):
                if cons_class.get(node, 'NA') != 'gt':
                    row['break_class'] = cons_class.get(node, 'NA')
                    break
                kept, node, steps = kept + 1, index[node]['parent'], steps + 1
            row['chain_depth_kept'] = kept
        span_rows.append(row)
        per_run_views[span_id] = view
    # Indicators
    carriers = [r for r in span_rows if r['is_carrier']]
    table_received = any(r['table_has_gt_kpi'] for r in span_rows)
    queried_gt = any(r['queried_gt'] for r in span_rows)
    gt_reasons = [reason for v in per_run_views.values() for reason in v['gt_reasons']]
    if gt is None or not results:
        i0 = 'NA'
    else:
        i0 = True if table_received else 'NA_censored' if censored else False
    s0_label, empty_reason = '', ''
    if i0 is False:
        if not queried_gt:
            s0_label = 'S0_gt_span_absent' if not gt_spans else 'S0_gt_span_present_not_queried'
        else:
            s0_label = 'S0_empty_result'
    if gt_reasons:
        empty_reason = gt_reasons[0] if len(set(gt_reasons)) == 1 else 'mixed'
    abnormal_carriers = [r for r in carriers if r['self_is_abnormal'] is True]
    if i0 is not True:
        i1 = 'NA'
    elif abnormal_carriers:
        i1 = True
    elif not any(r['self_present'] for r in carriers):
        i1 = 'NA'
    else:
        i1 = censor(False, censored)
    s1_label = ''
    if i1 is False:
        s1_label = 'S1_not_flagged' + (':fallback_flags_missing' if any(r['fallback_flags_missing'] for r in carriers)
                                       else '')
    misattributed = i1 is True and not any(r['is_gt_span'] for r in abnormal_carriers)
    root = roots[0] if roots else None
    root_info = cons_info.get(root['span_id']) if root else None
    if root_info is None or gt is None:
        i2, i2_raw, i2_lenient, root_class, root_label = 'NA', 'NA', 'NA', 'NA', None
    else:
        consd, root_label, raw_class = root_info
        root_class = cons_class[root['span_id']]
        reason = consd.get('reason')
        mentioned = isinstance(reason, str) and re.search(
            r'(?<![a-z0-9_])' + re.escape(gt.lower()) + r'(?![a-z0-9_])', reason.lower()) is not None
        i2 = censor(root_class == 'gt', censored)
        i2_raw = censor(raw_class == 'gt', censored)
        i2_lenient = censor(root_class == 'gt' or mentioned, censored)
    hint_all = {s.lower() for s in errors + metrics}
    d1_spans = {r['span_id'] for r in span_rows if r['D1'] is True}
    d2_spans = {r['span_id'] for r in span_rows if r['D2'] is True}

    def listed(excluded):
        kept = [(service, evidence) for span_id, service, evidence in geg if span_id not in excluded]
        return {s.lower() for names in reconstruct_hint(kept) for s in names}

    if gt is None or not geg:
        i3, i3_strict = 'NA', 'NA'
    else:
        i3 = censor(in_list(gt, errors) or in_list(gt, metrics), censored)
        i3_strict = censor(any(in_list(gt, names) and len({n.lower() for n in names}) <= 2 for names in (errors, metrics)), censored)
    final_event = hash_order.final_request(events)[2]
    hint_equivalent = 'NA'
    if final_event is not None:
        try:
            messages = stops.payload_of(final_event)['messages']
            hint_equivalent = prompt_hint(messages[-1]['content']) == (set(errors), set(metrics))
        except (KeyError, IndexError, TypeError, ValueError):
            hint_equivalent = 'NA'
    rank = label_hit(gt, candidates) if completed and gt else None
    i4 = 'NA' if rank is None else rank == 0
    mrr = '' if rank is None else f'{(0.0 if rank < 0 else 1 / (rank + 1)):.4f}'
    top1 = candidates[0] if candidates else None
    if not completed or root_label is None and root_class != 'refusal' or top1 is None or not isinstance(top1, str):
        i5 = 'NA'
    elif root_class == 'refusal':
        i5 = 'refusal'
    else:
        i5 = 'same' if label_hit(root_label, [top1]) == 0 else 'diff'
    values = [i0, i1, i2, i3, i4]
    count, ended = leading_true(values)
    residual, split = final_residual(i0, i1, i3, i4, i5)
    score = author_score(run['author_score'])
    if completed and score is None:
        problems.append('completed run without a parseable author-score.txt')
    print_ = fingerprint(events, problems)
    score_check = 'no_author_score' if score is None else 'not_comparable' if rank is None else (
        'match' if (score[0] == 1.0) == (rank == 0) and score[1] == mrr else 'mismatch')
    if censored:
        hint_facts = dict(hint_list_size='NA', hint_list_size_by_base='NA', gt_sole_entry='NA',
                          d1_dropped_list_size='NA', d2_dropped_list_size='NA')
    else:
        hint_facts = dict(hint_list_size=len(hint_all), hint_list_size_by_base=len({base_of(s) for s in hint_all}),
                          gt_sole_entry=bool(gt) and len(hint_all) == 1 and in_list(gt, hint_all),
                          d1_dropped_list_size=len(listed(d1_spans)), d2_dropped_list_size=len(listed(d2_spans)))
    for row in span_rows:
        row.update({k: v for k, v in hint_facts.items() if k != 'hint_list_size_by_base'})
    d2_services = defaultdict(list)
    for row in span_rows:
        if row['self_is_abnormal'] is True:
            d2_services[(row['cmdb_id'] or '').lower()].append(row['D2'])
    tool_counts = Counter(r['source'] for r in results)
    reason = stop_reason(run)
    run_row = {
        'run_id': run['run_id'], 'package': run.get('package', ''), 'case': run['trace_id'][:6],
        'trace_id': run['trace_id'], 'condition': run['condition'], 'seed': run['seed'], 'gt_service': gt or '',
        'gt_span_in_trace': gt_spans, 'total_spans': len(spans), 'status': status,
        'harness_class': harness_class(status, reason), 'completed': completed, 'censored': censored,
        'requests': requests, 'retries': retries, 'tool_results_joined': len(results),
        'tool_results_raw': sum(e.get('kind') == 'tool_result' for e in events),
        'tool_results_by_source': ';'.join(f'{k}:{v}' for k, v in sorted(tool_counts.items(), key=str)),
        'metric_budget_events': metric_budget, 'I0': i0, 'queried_gt': queried_gt, 'table_received': table_received,
        's0_label': s0_label, 'empty_reason': empty_reason, 'empty_reason_set': sorted(set(gt_reasons)),
        'table_key_prefixes': sorted({p for r in span_rows for p in r['table_key_prefixes']}),
        'carrier_count': len(carriers), 'carrier_abnormal_count': len(abnormal_carriers), 'I1': i1,
        's1_label': s1_label, 'misattributed': misattributed, 'root_class': root_class, 'I2': i2, 'I2_raw': i2_raw,
        'I2_lenient': i2_lenient,
        'chain_depth_kept_max': max((r['chain_depth_kept'] for r in span_rows if r['carrier_abnormal']), default=''),
        'chains_intact_count': sum(r['carrier_abnormal'] and r['break_class'] == 'none' for r in span_rows),
        'I3': i3, 'I3_strict': i3_strict, **hint_facts,
        'hint_equivalent': hint_equivalent, 'I4': i4, 'rank': '' if rank is None else rank,
        'R@3': 'NA' if rank is None else 0 <= rank < 3, 'MRR': mrr, 'I5': i5,
        'leading_true': count, 'leading_true_end': ended, 'first_loss_linear': first_loss_linear(values),
        'final_residual': residual, 'final_residual_split': split,
        'chain_weakened': i1 is True and i2 is False, 'hint_weakened': i1 is True and i3 is False,
        'outcome_hit': i4, 'hit_without_evidence': i0 is False and i4 is True,
        'D1': any(r['D1'] is True for r in span_rows), 'D1_empty_logs': any(r['D1_empty_logs'] is True for r in span_rows),
        'D2': any(v and all(x is True for x in v) for v in d2_services.values()),
        'score_check': score_check, 'integrity': '; '.join(problems) or 'ok'}
    return span_rows, run_row, print_, unseen


# -- Tables across runs -------------------------------------------------------------------------------------------

def case_rows(run_rows):
    """One row per (case, condition): run counts, k-of-n of each indicator and the per-seed furthest indicator."""
    groups = defaultdict(list)
    for row in run_rows:
        groups[(row['case'], row['condition'])].append(row)
    out = []
    for (case, condition), rows in sorted(groups.items()):
        rows = sorted(rows, key=lambda r: r['seed'])
        entry = {'case': case, 'condition': condition, 'package': rows[0]['package'], 'trace_id': rows[0]['trace_id'],
                 'gt_service': rows[0]['gt_service'], 'gt_span_in_trace': rows[0]['gt_span_in_trace'],
                 'total_spans': rows[0]['total_spans'], 'runs': len(rows),
                 'completed': sum(r['completed'] for r in rows), 'censored': sum(r['censored'] for r in rows)}
        for name in INDICATORS + ('I2_lenient', 'I3_strict'):
            entry[f'{name}_true'] = sum(r[name] is True for r in rows)
            entry[f'{name}_n'] = sum(r[name] is True or r[name] is False for r in rows)
        entry['I5_same'] = sum(r['I5'] == 'same' for r in rows)
        entry['I5_diff'] = sum(r['I5'] == 'diff' for r in rows)
        entry['I5_refusal'] = sum(r['I5'] == 'refusal' for r in rows)
        entry['leading_true_by_seed'] = [f'{r["seed"]}:{r["leading_true"]}' for r in rows]
        entry['rank_by_seed'] = [f'{r["seed"]}:{r["rank"]}' for r in rows]
        entry['first_loss_linear_by_seed'] = [f'{r["seed"]}:{r["first_loss_linear"]}' for r in rows]
        entry['final_residual_by_seed'] = [f'{r["seed"]}:{r["final_residual"]}' for r in rows]
        out.append(entry)
    return out


def first_request_divergence(a, b):
    return compare.first_difference(a, b)


def case_comparison(run_rows, prints):
    """Per (case, seed, condition pair): where the request sequences first differ and how many agent outputs are the
    same bytes. The two sides are independent sampled trajectories, so this is a description, not a paired effect."""
    by = {(r['case'], r['seed'], r['condition']): r for r in run_rows}
    out = []
    for case, seed, reference in sorted(k for k in by if k[2] == 'metric'):
        for other in ('no_metric', 'metric_no_log'):
            if (case, seed, other) not in by:
                continue
            a, b = by[case, seed, reference], by[case, seed, other]
            fa, fb = prints[a['run_id']], prints[b['run_id']]
            raw = first_request_divergence(fa['requests'], fb['requests'])
            merged = first_request_divergence(fa['merged'], fb['merged'])
            same = sum(fb['complete'].get(key) == value for key, value in fa['complete'].items())
            stage = ''
            if raw is not None and raw <= len(fa['operations']):
                stage = fa['operations'][raw - 1] or 'final'
            out.append({
                'case': case, 'gt_service': a['gt_service'], 'seed': seed, 'reference': reference, 'other': other,
                'reference_run': a['run_id'], 'other_run': b['run_id'], 'request_numbering': 'one-based, retries included',
                'first_request_divergence': '' if raw is None else raw,
                'first_request_divergence_merged': '' if merged is None else merged, 'divergence_stage': stage,
                'agent_complete_reference': len(fa['complete']), 'agent_complete_same_bytes': same,
                'agent_complete_same_share': f'{same / len(fa["complete"]):.4f}' if fa['complete'] else '',
                'leading_true_reference': a['leading_true'], 'leading_true_other': b['leading_true'],
                'rank_reference': a['rank'], 'rank_other': b['rank'], 'pairing': 'independent trajectories, not paired'})
    return out


def funnel(run_rows):
    """Runs and GT services per condition and indicator; censored runs sit in the NA columns. true_over_all_runs is
    the sensitivity that counts every NA run as lost."""
    out = []
    for condition in sorted({r['condition'] for r in run_rows}):
        rows = [r for r in run_rows if r['condition'] == condition]
        ev = [r for r in rows if r['completed'] and r['I0'] is True]
        for name in INDICATORS + ('I2_lenient', 'I3_strict'):
            true = [r for r in rows if r[name] is True]
            counts = Counter('true' if r[name] is True else 'false' if r[name] is False else str(r[name]) for r in rows)
            determinable = [r for r in ev if r[name] is True or r[name] is False]
            out.append({
                'condition': condition, 'indicator': name, 'runs': len(rows), 'completed': sum(r['completed'] for r in rows),
                'censored': sum(r['censored'] for r in rows), 'true': counts['true'], 'false': counts['false'],
                'NA': counts['NA'], 'NA_censored': counts['NA_censored'],
                'gt_services_true': len({r['gt_service'] for r in true}),
                'gt_services': len({r['gt_service'] for r in rows}),
                'saturated': bool(determinable) and all(r[name] is True for r in determinable) if name in INDICATORS else '',
                'true_over_all_runs': f'{counts["true"]}/{len(rows)}'})
    return out


def feasibility(run_rows):
    """For each condition and stage, the cases (and GT services) that have both a run that lost it and a run that kept
    it among completed runs; fewer than three cases make the within-case contrast not_testable."""
    out = []
    for condition in sorted({r['condition'] for r in run_rows}):
        rows = [r for r in run_rows if r['condition'] == condition and r['completed']]
        for name in INDICATORS[:4]:
            pool = rows if name == 'I0' else [r for r in rows if r['I0'] is True]
            cases = defaultdict(set)
            for r in pool:
                if r[name] is True or r[name] is False:
                    cases[r['case']].add(r[name])
            both = sorted(c for c, seen in cases.items() if seen == {True, False})
            units = sorted({r['gt_service'] for r in pool if r['case'] in both})
            out.append({'condition': condition, 'stage': name, 'cases_with_both_groups': both,
                        'gt_services_with_both_groups': units, 'lost_runs': sum(r[name] is False for r in pool),
                        'kept_runs': sum(r[name] is True for r in pool),
                        'status': 'testable' if len(both) >= FEASIBLE_UNITS else 'not_testable'})
    return out


def sha256_lf(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def module_hashes():
    return {name: sha256_lf(HERE / name) for name in IMPORTED}


def prereg_report(path=PREREG, root=ROOT):
    """Whether the codebook, this analyzer and the modules it loads still have the SHA256 recorded when the rules were
    frozen. Text is hashed with CRLF turned into LF, so a checkout with another line ending does not change it."""
    report = {'frozen': False, 'codebook_sha_matches': False, 'analyzer_sha_matches': False, 'imports_sha_match': False}
    path = Path(path)
    if not path.exists():
        return report
    recorded = json.loads(path.read_text(encoding='utf-8'))
    codebook = Path(recorded.get('codebook_path', ''))
    codebook = codebook if codebook.is_absolute() else Path(root) / codebook
    return {'frozen': True,
            'codebook_sha_matches': codebook.is_file() and sha256_lf(codebook) == recorded.get('codebook_sha256'),
            'analyzer_sha_matches': sha256_lf(Path(__file__)) == recorded.get('analyzer_sha256'),
            'imports_sha_match': module_hashes() == recorded.get('imports_sha256')}


# -- Corpus, CLI and output ---------------------------------------------------------------------------------------

def parse_args(argv):
    """OUT_DIR, the package groups and the options, with the options at any position."""
    values, structure_only, positional, i = {'--runs': None, '--label': None}, False, [], 0
    while i < len(argv):
        arg = argv[i]
        if arg == '--structure-only':
            structure_only = True
        elif arg in values:
            if i + 1 >= len(argv):
                raise SystemExit(f'{arg} needs a value\n\n{__doc__}')
            values[arg] = argv[i + 1]
            i += 1
        elif arg.startswith('--'):
            raise SystemExit(f'unknown option {arg}\n\n{__doc__}')
        else:
            positional.append(arg)
        i += 1
    if len(positional) < 4 or (len(positional) - 1) % 3:
        raise SystemExit(__doc__)
    return {'out_dir': Path(positional[0]), 'label': values['--label'] or 'default', 'runs': values['--runs'],
            'structure_only': structure_only,
            'groups': [tuple(positional[i:i + 3]) for i in range(1, len(positional), 3)]}


def selected_runs(path):
    if path is None:
        return None
    return {line.strip() for line in Path(path).read_text(encoding='utf-8-sig').splitlines()
            if line.strip() and not line.strip().startswith('#')}


def iter_runs(groups, selected=None):
    """Yield every run of the groups as read_run() builds it, one at a time. The ground truth of a run that stopped
    before scoring comes from a sibling run of the same case in the same ZIP. A selected id that no group holds is an
    error, raised once all groups are read."""
    found_ids = set()
    for package, archive, manifest in groups:
        rows = analyzer.load(archive, manifest)
        with zipfile.ZipFile(archive) as zipped:
            names = set(zipped.namelist())
            progress = json.loads(zipped.read('run/progress.json'))['traces']
            by_case = {}
            for row in rows:
                found = read_gt(zipped, names, row['run_id'])
                if found:
                    by_case.setdefault(row['trace_id'], found)
            for row in rows:
                found_ids.add(row['run_id'])
                if selected is None or row['run_id'] in selected:
                    yield dict(read_run(zipped, names, row, progress, by_case.get(row['trace_id'])), package=package)
    unknown = sorted(selected - found_ids) if selected else []
    if unknown:
        raise SystemExit(f'--runs names runs that no package holds: {", ".join(unknown)}')


def structure_rows(runs):
    """One row per case: the faulty service, span count, spans of that service and tree depth."""
    seen, out = set(), []
    for run in runs:
        if run['trace_id'] in seen:
            continue
        seen.add(run['trace_id'])
        spans, gt = flatten_tree(run['graph'], []) if run['graph'] else [], run['gt']
        out.append({'package': run['package'], 'case': run['trace_id'][:6], 'trace_id': run['trace_id'],
                    'fault_case': run['case'], 'gt_service': gt or '', 'spans': len(spans),
                    'gt_spans': sum(bool(gt) and match(gt, s['raw'].get('cmdb_id') or '') for s in spans),
                    'max_depth': max((s['depth'] for s in spans), default=0)})
    return sorted(out, key=lambda r: (r['package'], r['case']))


def cell(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if value is None:
        return ''
    if isinstance(value, (list, tuple, set)):
        return ';'.join(map(str, value))
    return value


def write_csv(path, rows, fields=None):
    fields = fields or list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: cell(row.get(k)) for k in fields})


def write_summary(out_dir, summary):
    (Path(out_dir) / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n',
                                                encoding='utf-8')


def summarise(run_rows, cases, comparison, funnel_rows, feasible, unseen, label):
    problems = [(r['run_id'], r['integrity']) for r in run_rows if r['integrity'] != 'ok']
    scored = [r for r in run_rows if r['score_check'] != 'no_author_score']
    compared = [r for r in scored if r['score_check'] != 'not_comparable']
    pair_share = {}
    for pair in ('no_metric', 'metric_no_log'):
        rows = [r for r in comparison if r['other'] == pair]
        total = sum(r['agent_complete_reference'] for r in rows)
        same = sum(r['agent_complete_same_bytes'] for r in rows)
        pair_share[f'metric_vs_{pair}'] = {'pairs': len(rows), 'agent_complete_same_bytes': same,
                                           'agent_complete_reference': total,
                                           'share': f'{same / total:.4f}' if total else ''}
    return {
        'label': label, 'structure_only': False, 'provisional': bool(problems),
        'runs': len(run_rows), 'completed': sum(r['completed'] for r in run_rows),
        'censored': sum(r['censored'] for r in run_rows),
        'by_condition': {c: {'runs': sum(r['condition'] == c for r in run_rows),
                             'completed': sum(r['condition'] == c and r['completed'] for r in run_rows)}
                         for c in sorted({r['condition'] for r in run_rows})},
        'harness_class': dict(sorted(Counter(r['harness_class'] for r in run_rows).items())),
        'integrity_problems': problems,
        'completed_without_score': sum(r['completed'] and r['score_check'] == 'no_author_score' for r in run_rows),
        'scorer_equivalence': {'author_scored_runs': len(scored), 'compared_runs': len(compared),
                               'not_comparable': [r['run_id'] for r in scored if r['score_check'] == 'not_comparable'],
                               'mismatches': [r['run_id'] for r in compared if r['score_check'] == 'mismatch'],
                               'rule': 'R@1 compared exactly, MRR as the four decimals of author-score.txt'},
        'join_checks': {'tool_results_joined': sum(r['tool_results_joined'] for r in run_rows),
                        'tool_results_raw': sum(r['tool_results_raw'] for r in run_rows),
                        'metric_budget_events': sum(r['metric_budget_events'] for r in run_rows)},
        'hint_equivalence': dict(sorted(Counter(cell(r['hint_equivalent']) for r in run_rows).items())),
        'unseen_branches': dict(sorted(unseen.items())), 'funnel': funnel_rows, 'feasibility': feasible,
        'cases': cases, 'condition_comparison': pair_share, 'first_loss_linear_note': FIRST_LOSS_NOTE,
        'unit': 'GT service; cases and seeds are nested inside it and are not independent samples',
        'prereg': prereg_report(),
        'note': 'Descriptive; no statistical test. The tool answers any query whose text matches the faulty service, '
                'so I0 is close to "the model asked for it". The hint columns describe the author code only.'}


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    out_dir = args['out_dir']
    if (out_dir / 'summary.json').exists():
        raise SystemExit(f'{out_dir} already holds a summary.json; choose a new folder')
    selected = selected_runs(args['runs'])
    duplicates = Counter()
    if args['structure_only']:
        rows = structure_rows(iter_runs(args['groups'], selected))
        out_dir.mkdir(parents=True, exist_ok=True)
        write_csv(out_dir / 'structure.csv', rows)
        write_summary(out_dir, {'label': args['label'], 'structure_only': True, 'cases': rows})
        for row in rows:
            print(f'{row["package"]} {row["case"]} {row["fault_case"]} gt={row["gt_service"]} spans={row["spans"]} '
                  f'gt_spans={row["gt_spans"]} max_depth={row["max_depth"]}')
        return
    spans, run_rows, prints, unseen = [], [], {}, Counter()
    for run in iter_runs(args['groups'], selected):
        duplicates[run['run_id']] += 1
        if duplicates[run['run_id']] > 1:
            raise SystemExit(f'Duplicate run: {run["run_id"]}')
        span_rows, run_row, print_, counts = analyze_run(run)
        spans += span_rows
        run_rows.append(run_row)
        prints[run['run_id']] = print_
        unseen += counts
    run_rows.sort(key=lambda r: r['run_id'])
    spans.sort(key=lambda r: (r['run_id'], r['depth'], str(r['span_id'])))
    cases, comparison = case_rows(run_rows), case_comparison(run_rows, prints)
    funnel_rows, feasible = funnel(run_rows), feasibility(run_rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / 'spans.csv', spans, list(SPAN_FIELDS))
    write_csv(out_dir / 'runs.csv', run_rows)
    write_csv(out_dir / 'cases.csv', cases)
    write_csv(out_dir / 'case-comparison.csv', comparison)
    write_csv(out_dir / 'funnel.csv', funnel_rows)
    summary = summarise(run_rows, cases, comparison, funnel_rows, feasible, unseen, args['label'])
    write_summary(out_dir, summary)
    print(json.dumps({k: summary[k] for k in ('runs', 'completed', 'censored', 'provisional', 'harness_class',
                                              'scorer_equivalence', 'join_checks')}, indent=1))
    print('integrity problems:', len(summary['integrity_problems']), 'prereg:', summary['prereg'])


if __name__ == '__main__':
    main()
