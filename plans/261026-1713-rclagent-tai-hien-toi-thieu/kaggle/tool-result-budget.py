"""Tool-result budget for RCLAgent search_logs responses; the harness uses the ladder scheme only.

Every scheme is a pure function of (response body, queried second, budget, token counter). A response whose token
count is within the budget is returned byte-for-byte. Rules read only the response itself: no service name, case,
label or result enters any decision. A body that is not the author's log CSV is never rewritten, and a non-empty
response is never reduced to an empty one; both cases return None so the caller stops instead of guessing.

Schemes
  cap       keep verbatim CSV rows by priority until the budget is met, with an explicit truncation line.
  template  merge rows sharing (cmdb_id, log_name, severity, masked message); keep count, first/last second,
            distinct values and the first verbatim value. No cap: returns None when still over budget.
  ladder    least lossy step that fits: exact-duplicate merge, then template merge, then cap over templates.
"""
import csv
import io
import re

HEADER = ['log_id', 'timestamp', 'cmdb_id', 'log_name', 'value']
SEVERITY = re.compile(r'^severity:\s*([^,]*),\s*message:\s?(.*)$', re.S)
ERROR_SEVERITIES = {'emergency', 'alert', 'critical', 'fatal', 'error'}
WARNING_SEVERITIES = {'warning', 'warn'}
ERROR_TEXT = re.compile(r'error|exception', re.I)
MASKS = [re.compile(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b'),
         re.compile(r'\b\w*\d\w*\b')]  # UUIDs, then any word containing a digit (ids, numbers, clock fields).
MASK_TEXT = 'variable parts (UUIDs and words containing digits) masked as <*>'
PRIORITY_TEXT = 'error/fatal/critical severity > warning > other rows whose text contains error/exception > rest; ' \
                'ties by distance to the queried second, then original order'


def parse(body):
    """Rows of the author's search_logs CSV, or None when the body is anything else."""
    try:
        rows = list(csv.reader(io.StringIO(body, newline='')))
    except csv.Error:
        return None
    if not rows or rows[0] != HEADER or any(len(r) != len(HEADER) for r in rows[1:]):
        return None
    try:
        for r in rows[1:]:
            int(r[1])
    except ValueError:
        return None
    return rows[1:]


def render(header, rows):
    out = io.StringIO()
    writer = csv.writer(out, lineterminator='\n')  # Same quoting and line ending as pandas to_csv on Linux.
    writer.writerow(header)
    writer.writerows(rows)
    return out.getvalue()


def severity_and_message(value):
    match = SEVERITY.match(value)
    return (match.group(1).strip().lower(), match.group(2)) if match else ('', value)


def is_error_like(value):
    severity, _ = severity_and_message(value)
    return severity in ERROR_SEVERITIES or bool(ERROR_TEXT.search(value))


def rank(value):
    severity, _ = severity_and_message(value)
    if severity in ERROR_SEVERITIES:
        return 0
    if severity in WARNING_SEVERITIES:
        return 1
    return 2 if ERROR_TEXT.search(value) else 3


def template(message):
    for pattern in MASKS:
        message = pattern.sub('<*>', message)
    return message


def note(budget, text):
    return f'[harness tool-result budget {budget} tokens: {text}]\n'


def severity_counts(values):
    counts = {}
    for value in values:
        severity = severity_and_message(value)[0] or 'none'
        counts[severity] = counts.get(severity, 0) + 1
    return ', '.join(f'{k}={v}' for k, v in sorted(counts.items()))


def fit(items, key, build, budget, count):
    """Largest priority prefix whose rendered text fits; items keep their original order in the output."""
    order = sorted(range(len(items)), key=key)
    low, high, best = 0, len(order), None
    while low <= high:  # Token count is monotone in the number of kept items up to BPE boundary effects.
        middle = (low + high) // 2
        text = build(sorted(order[:middle]))
        if count(text) <= budget:
            best, low = (middle, text), middle + 1
        else:
            high = middle - 1
    return best


def merge_exact(rows):
    groups = {}
    for log_id, ts, cmdb, name, value in rows:
        g = groups.setdefault((cmdb, name, value), [cmdb, name, value, 0, int(ts), int(ts)])
        g[3] += 1
        g[4], g[5] = min(g[4], int(ts)), max(g[5], int(ts))
    return list(groups.values())


def merge_template(rows):
    groups = {}
    for log_id, ts, cmdb, name, value in rows:
        severity, message = severity_and_message(value)
        g = groups.setdefault((cmdb, name, severity, template(message)),
                              {'cmdb': cmdb, 'name': name, 'severity': severity, 'template': template(message),
                               'count': 0, 'first': int(ts), 'last': int(ts), 'values': set(), 'example': value,
                               'rank': rank(value), 'error_like': 0})
        g['count'] += 1
        g['first'], g['last'] = min(g['first'], int(ts)), max(g['last'], int(ts))
        g['values'].add(value)
        g['error_like'] += is_error_like(value)
        g['rank'] = min(g['rank'], rank(value))
    return list(groups.values())


TEMPLATE_HEADER = ['cmdb_id', 'log_name', 'severity', 'message_template', 'count', 'first_timestamp',
                   'last_timestamp', 'distinct_values', 'first_value']


def template_rows(groups):
    return [[g['cmdb'], g['name'], g['severity'], g['template'], g['count'], g['first'], g['last'],
             len(g['values']), g['example']] for g in groups]


def cap(body, second, budget, count):
    rows = parse(body)
    if rows is None or not rows:
        return None
    total = len(rows)

    def build(kept):
        shown, kept = [rows[i] for i in kept], set(kept)
        omitted = [rows[i][4] for i in range(total) if i not in kept]
        return note(budget, f'truncated: {len(shown)} of {total} rows shown, verbatim; '
                            f'omitted rows by severity: {severity_counts(omitted)}; priority: {PRIORITY_TEXT}') \
            + render(HEADER, shown)

    best = fit(rows, lambda i: (rank(rows[i][4]), abs(int(rows[i][1]) - second), i), build, budget, count)
    return None if best is None or best[0] == 0 else best[1]


def merged_templates(rows, groups, budget, count):
    text = note(budget, f'{len(rows)} rows merged into {len(groups)} message templates ({MASK_TEXT}); '
                        'count, first/last second, distinct values and the first verbatim '
                        'value kept; log_id omitted; no row omitted') + render(TEMPLATE_HEADER, template_rows(groups))
    return text if count(text) <= budget else None


def template_only(body, second, budget, count):
    rows = parse(body)
    if rows is None or not rows:
        return None
    return merged_templates(rows, merge_template(rows), budget, count)


def ladder(body, second, budget, count):
    rows = parse(body)
    if rows is None or not rows:
        return None
    exact = merge_exact(rows)
    text = note(budget, f'{len(rows)} rows merged into {len(exact)} identical (cmdb_id, log_name, value) entries; '
                        'count and first/last second kept; log_id omitted; no row omitted') \
        + render(['cmdb_id', 'log_name', 'value', 'count', 'first_timestamp', 'last_timestamp'], exact)
    if count(text) <= budget:
        return text
    groups = merge_template(rows)
    text = merged_templates(rows, groups, budget, count)
    if text is not None:
        return text

    def build(kept):
        shown, kept = [groups[i] for i in kept], set(kept)
        omitted = [g for i, g in enumerate(groups) if i not in kept]
        covered = sum(g['count'] for g in shown)
        lost = ', '.join(f"{k}={v}" for k, v in sorted(
            {s: sum(g['count'] for g in omitted if (g['severity'] or 'none') == s)
             for s in {g['severity'] or 'none' for g in omitted}}.items()))
        return note(budget, f'truncated: {len(shown)} of {len(groups)} message templates shown, covering {covered} '
                            f'of {len(rows)} rows ({MASK_TEXT}); omitted rows by '
                            f'severity: {lost}; priority: {PRIORITY_TEXT}') + render(TEMPLATE_HEADER, template_rows(shown))

    nearest = [min(abs(t - second) for t in (g['first'], g['last'])) if not g['first'] <= second <= g['last'] else 0
               for g in groups]
    best = fit(groups, lambda i: (groups[i]['rank'], nearest[i], i), build, budget, count)
    return None if best is None or best[0] == 0 else best[1]


SCHEMES = {'cap': cap, 'template': template_only, 'ladder': ladder}


def apply(scheme, body, second, budget, count):
    """Budgeted response, the unchanged body when within budget, or None when the scheme cannot fit it."""
    if len(body.encode('utf-8')) <= budget or count(body) <= budget:  # A token spans at least one byte.
        return body
    return SCHEMES[scheme](body, second, budget, count)
