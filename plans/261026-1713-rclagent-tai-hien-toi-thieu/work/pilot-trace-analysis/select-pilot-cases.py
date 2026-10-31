"""Fixed, outcome-blind pick of 8 train cases and one trace each for the controlled pilot.

Rule (declared before any run): exclude the five pilot-trace cases; order cases by sha256(SALT + case_id);
walk that order taking the first case of each fault type not yet covered (6), then the next two cases overall,
skipping any case whose labelled service already appears twice. Traces: give the 8 cases, in pick order, the
length buckets short (<=25 spans), medium (26-33), long (>=34) in turn; in each case take the trace of that bucket
with the smallest sha256(SALT + trace_id), else the nearest bucket. Labels are used only for fault/service strata.
"""
import hashlib, json, sys, collections
SALT = 'nt114-rclagent-missing-source-pilot-261028'
H = lambda s: hashlib.sha256((SALT + s).encode()).hexdigest()
t = json.load(open(sys.argv[1]))
batch = {x['trace_id']: x for x in json.load(open(sys.argv[2], encoding='utf-8'))['traces']}
PILOT = {'currencyservice_mem_3', 'productcatalogservice_delay_3', 'recommendationservice_socket_3',
         'emailservice_socket_2', 'productcatalogservice_mem_1'}
cases = sorted({x['case'] for x in t} - PILOT, key=H)
fault = lambda c: c.rsplit('_', 2)[1]; svc = lambda c: c.rsplit('_', 2)[0]
pick, used = [], collections.Counter()
for c in cases:
    if fault(c) not in {fault(p) for p in pick} and used[svc(c)] < 2:
        pick.append(c); used[svc(c)] += 1
for c in cases:
    if len(pick) == 8: break
    if c not in pick and used[svc(c)] < 2:
        pick.append(c); used[svc(c)] += 1
bucket = lambda n: 0 if n <= 25 else 1 if n <= 33 else 2
out = []
for i, c in enumerate(pick):
    want = i % 3
    tr = [x for x in t if x['case'] == c]
    best = min(tr, key=lambda x: (abs(bucket(x['spans']) - want), H(x['trace_id'])))
    out.append(dict(case=c, fault=fault(c), service=svc(c), trace_id=best['trace_id'], spans=best['spans'],
                    bucket=['short', 'medium', 'long'][bucket(best['spans'])],
                    est_s=batch[best['trace_id']]['estimated_seconds'], est_req=batch[best['trace_id']]['estimated_requests'],
                    gt_in_trace=best['gt_in_trace'], heur_rank=best.get('heur_rank')))
json.dump(out, open('pilot-selection.json', 'w'), indent=1)
for o in out: print(o)
per = sum(o['est_s'] for o in out)
print('sum est seconds per condition-seed pass', per)
for nc in (3, 4):
    runs = 8 * nc * 3; tr_s = per * nc * 3
    print(nc, 'conditions:', runs, 'runs; trace hours', round(tr_s / 3600, 1), '| x1.25', round(tr_s * 1.25 / 3600, 1),
          '| + setup 2 sessions', round((tr_s * 1.25 + 2 * 480) / 3600, 1))
