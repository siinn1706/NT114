"""Select the 25 dev queries of the telemetry-gap prereg and assign each to a run site.

Usage: select-dev-set.py OUT_JSON [--coverage FILE] [--kaggle-per-stratum 5]

Rule (prereg-261102-rclagent-telemetry-gap-method.md, sections 3 and 4), on train queries of measure-trace-coverage.py
outside the eight S1 cases; key(id) = sha256((salt + id).encode()) hex, ascending:
- none stratum: the first 12 cases by key among those with a query without any span of the faulty service; each gives
  its none query with the smallest key;
- covered stratum: the other cases with a covered query, grouped by faulty service, each group ordered by key; take
  one case per service in alphabetical round robin, skipping exhausted services, until 13; each gives its covered
  query with the smallest key;
- site: within each stratum, the first N queries by site key run on Kaggle, the rest on Modal.
Reads query structure only; no run result and no test-split row.
"""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
COVERAGE = HERE / 'runtime' / 'trace-coverage' / 'coverage.csv'
S1_MANIFESTS = sorted((HERE / 's1-v3').glob('*/manifest.json'))
DEV_SALT, SITE_SALT = 'telemetry-gap-dev-v1', 'telemetry-gap-site-v1'
NONE_CASES, COVERED_CASES = 12, 13


def key(salt, identifier):
    return hashlib.sha256((salt + identifier).encode()).hexdigest()


def s1_cases(manifests=S1_MANIFESTS):
    return {case for path in manifests for case in json.loads(Path(path).read_text(encoding='utf-8'))['cases']}


def select(rows, excluded):
    """The dev queries in prereg order: none stratum, then covered stratum."""
    by_case = collections.defaultdict(list)
    for row in rows:
        if row['role'] == 'train' and row['case_id'] not in excluded:
            by_case[row['case_id']].append(row)
    case_key = lambda case: key(DEV_SALT, case)
    trace_key = lambda row: key(DEV_SALT, row['trace_id'])
    none_cases = sorted((c for c, qs in by_case.items() if any(q['coverage'] == 'none' for q in qs)), key=case_key)
    picked = [dict(min((q for q in by_case[c] if q['coverage'] == 'none'), key=trace_key), stratum='none')
              for c in none_cases[:NONE_CASES]]
    used = {q['case_id'] for q in picked}
    groups = collections.defaultdict(list)
    for case in sorted((c for c, qs in by_case.items() if c not in used and any(q['coverage'] != 'none' for q in qs)),
                       key=case_key):
        groups[by_case[case][0]['gt']].append(case)
    covered = []
    while len(covered) < COVERED_CASES and any(groups.values()):
        for service in sorted(groups):
            if groups[service] and len(covered) < COVERED_CASES:
                covered.append(groups[service].pop(0))
    picked += [dict(min((q for q in by_case[c] if q['coverage'] != 'none'), key=trace_key), stratum='covered')
               for c in covered]
    if len(picked) != NONE_CASES + COVERED_CASES:
        raise ValueError(f'Only {len(picked)} dev queries satisfy the rule')
    return picked


def assign_sites(queries, kaggle_per_stratum):
    """Each query with its site; within a site, queries run in site-key order."""
    out = []
    for stratum in ('none', 'covered'):
        ordered = sorted((q for q in queries if q['stratum'] == stratum), key=lambda q: key(SITE_SALT, q['trace_id']))
        out += [dict(q, site='kaggle' if i < kaggle_per_stratum else 'modal') for i, q in enumerate(ordered)]
    return sorted(out, key=lambda q: (q['site'], key(SITE_SALT, q['trace_id'])))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('out', type=Path)
    parser.add_argument('--coverage', type=Path, default=COVERAGE)
    parser.add_argument('--kaggle-per-stratum', type=int, default=5)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.out.exists():
        raise SystemExit(f'{args.out} exists; refusing to overwrite a frozen dev set')
    rows = list(csv.DictReader(args.coverage.read_text(encoding='utf-8').splitlines()))
    excluded = s1_cases()
    queries = assign_sites(select(rows, excluded), args.kaggle_per_stratum)
    fields = ('case_id', 'trace_id', 'gt', 'coverage', 'stratum', 'site')
    report = {'rule': 'prereg-261102-rclagent-telemetry-gap-method.md sections 3 and 4', 'dev_salt': DEV_SALT,
              'site_salt': SITE_SALT, 'excluded_s1_cases': sorted(excluded),
              'coverage_sha256': hashlib.sha256(args.coverage.read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
              'queries': [{f: q[f] for f in fields} for q in queries]}
    args.out.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(collections.Counter((q['site'], q['stratum']) for q in queries).most_common()))


if __name__ == '__main__':
    main()
