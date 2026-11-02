"""Telemetry-gap components that smoke-worker.py applies outside the unchanged upstream code.

M1 (gap_aware): a source that is absent and not replaced answers with a SOURCE UNAVAILABLE notice, and the
self-state prompt gains one line once such a notice is in its conversation.
M2 (trace_kpi): with metrics absent, search_fluctuating_metrics answers with trace-derived latency KPIs of the
window before the query, and the self-state prompt gains one line.
M3 (trace_expand): the final prompt gains a table of every known service's window latency, sorted by name.

The numbers come precomputed per query in window-kpi.json (build-window-kpi.py): spans in [t_q - 300 s, t_q),
ratio = duration / train p50 of (cmdb_id, operation_name). Pure functions; no model, no label.
"""
import json
import re

SELF_STATE_MARK = 'IMPORTANT evidence ranking'
SELF_STATE_ANCHOR = '- High latency alone → WEAK signal (may just be a victim of downstream issues)\n'
FINAL_ANCHOR = '\nGoal: identify the root-cause service.'
UNAVAILABLE = 'SOURCE UNAVAILABLE'
M1_LINE = '- A tool answer starting with SOURCE UNAVAILABLE means the source is missing, not that the span is normal.\n'
M2_LINE = ('- A trace-derived latency KPI compares this service with its training baseline; window_ratio well above 1 '
           'is a measured deviation, not "latency alone".\n')
M2_SOURCE = 'trace-derived latency KPI vs training baseline (metrics unavailable)'
NO_ROWS = '{"message":"No matching records found."}\n'  # metric-repair.NO_ROWS, the author's no-row answer.
# Upstream KNOWN_SERVICES['re2ob'] without the two frontend names, in name order.
TABLE_SERVICES = ('adservice', 'cartservice', 'checkoutservice', 'currencyservice', 'emailservice', 'paymentservice',
                  'productcatalogservice', 'recommendationservice', 'redis', 'shippingservice')
SIDES = (('server', 'server'), ('client', 'incoming_calls'))


def unavailable(source):
    noun = {'metric': 'metrics', 'logs': 'logs'}[source]
    return (f'{UNAVAILABLE}: {noun} are not collected for this system in this incident. Missing data is not evidence '
            'that the service is healthy; judge from the other evidence.')


# -- Names: the author scorer's matching (upstream evaluate.py), as in analyze-evidence-loss.py ----------------------

def base_of(name):
    low = name.lower()
    found = re.match(r'^(.+?)-[a-z0-9]{5,}-[a-z0-9]{4,}$', low)
    if found:
        return found.group(1)
    if low[-1:].isdigit():
        return low.rsplit('-', 1)[0]
    return low


def match(label, candidate):
    label_low, cand_low = str(label).lower().strip(), str(candidate).lower()
    if not label_low:
        return False
    label_base, cand_base = base_of(label_low), base_of(cand_low)
    return (label_low == cand_low or (label_base == cand_base and bool(label_base))
            or (cand_low.startswith(label_low) and (len(cand_low) == len(label_low) or cand_low[len(label_low)] == '-'))
            or (label_low.startswith(cand_low) and (len(label_low) == len(cand_low) or label_low[len(cand_low)] == '-')))


def lookup(kpi, name):
    """(service, entry) of the first window service, in name order, the scorer would count as `name`."""
    for service in sorted(kpi['services']):
        if match(name, service):
            return service, kpi['services'][service]
    return None, None


# -- M2 ----------------------------------------------------------------------------------------------------------

def kpi_response(kpi, service_name):
    """Body of search_fluctuating_metrics under M2: up to four KPIs (p95 and median of each side) or no rows."""
    service, entry = lookup(kpi, service_name)
    body = {}
    for side, label in SIDES:
        stats = (entry or {}).get(side)
        if stats:
            for stat in ('p95', 'median'):
                body[f'{service}.trace_latency_ratio_{stat}.{label}'] = {
                    'baseline_ratio': 1.0, 'window_ratio': round(stats[stat], 2), 'spans': stats['spans']}
    if not body:
        return NO_ROWS
    return json.dumps(dict(source=M2_SOURCE, **body), ensure_ascii=False) + '\n'


# -- M3 ----------------------------------------------------------------------------------------------------------

def ratio_text(stats):
    return 'n/a' if not stats else f"{stats['p95']:.2f}"


def window_table(kpi, drop_empty=False):
    rows = []
    for name in TABLE_SERVICES:
        _, entry = lookup(kpi, name)
        entry = entry or {}
        if drop_empty and not entry.get('server') and not entry.get('client'):
            continue
        rows.append(f"{name} | {'yes' if entry.get('in_trace') else 'no'} | {entry.get('traces', 0)} | "
                    f"{ratio_text(entry.get('server'))} | {ratio_text(entry.get('client'))}")
    return '\n'.join([f"Window evidence beyond this trace (all traces in the {kpi['window_s']} s before this query, "
                      'against a training baseline):',
                      'service | in this trace | traces | server p95 ratio | incoming-call p95 ratio', *rows,
                      'Services absent from this trace can still be the root cause.'])


# -- Prompt edits --------------------------------------------------------------------------------------------------

def edit_messages(messages, gap_aware=False, trace_kpi=False, trace_expand=False, kpi=None, drop_empty=False):
    """The messages sent to the model. With every flag off, or no matching prompt, the same list object returns."""
    notice = gap_aware and any(m.get('role') == 'tool' and str(m.get('content') or '').startswith(UNAVAILABLE)
                               for m in messages)
    edited = None
    for index, message in enumerate(messages):
        text = message.get('content')
        if message.get('role') != 'user' or not isinstance(text, str):
            continue
        new = text
        if SELF_STATE_MARK in text:
            lines = (M2_LINE if trace_kpi else '') + (M1_LINE if notice else '')
            if lines:
                if SELF_STATE_ANCHOR not in text:
                    raise ValueError('Self-state prompt without the evidence-ranking anchor line')
                new = text.replace(SELF_STATE_ANCHOR, SELF_STATE_ANCHOR + lines, 1)
        elif trace_expand and FINAL_ANCHOR in text:
            new = text.replace(FINAL_ANCHOR, '\n' + window_table(kpi, drop_empty) + '\n' + FINAL_ANCHOR, 1)
        if new != text:
            edited = edited or list(messages)
            edited[index] = dict(message, content=new)
    return edited or messages
