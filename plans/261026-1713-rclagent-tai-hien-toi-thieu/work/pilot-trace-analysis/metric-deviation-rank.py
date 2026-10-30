"""Label-free ranking by the pre-baseline deviation, without adding the labelled service to the candidates."""
import json, sys, importlib.util
from pathlib import Path
import pandas as pd
ROOT, S = Path(sys.argv[1]), Path(sys.argv[2])
# Reuse dev() from the simulation script without running that script's main body.
src = open(Path(__file__).with_name('metric-repair-simulation.py'), encoding='utf-8').read()
ns = {'pd': pd}; exec(src[src.index('def dev('):src.index('def flags(')], ns); dev = ns['dev']
spec = importlib.util.spec_from_file_location('pp', ROOT / 'code/preprocess/preprocess_re2ob.py')
pp = importlib.util.module_from_spec(spec); spec.loader.exec_module(pp)
t = pd.DataFrame(json.load(open(S / 'train-traces.json')))
ALL = ['adservice', 'cartservice', 'checkoutservice', 'currencyservice', 'emailservice', 'frontend', 'paymentservice',
       'productcatalogservice', 'recommendationservice', 'redis', 'shippingservice']
start = {}
for c in pd.read_csv(ROOT / 'data/re2ob/trace/all/trace_jaeger-span.csv', usecols=['trace_id', 'timestamp'], chunksize=3_000_000):
    c = c[c.trace_id.isin(set(t.trace_id))]
    for tid, v in c.groupby('trace_id').timestamp.min().items():
        start[tid] = min(start.get(tid, v), v)
rows = []
for case, tc in t.groupby('case'):
    fdir, n = case.rsplit('_', 1)
    m = pp._convert_one_metric_simple(str(ROOT / 'data/raw/RE2-OB' / fdir / n), case).drop(columns='_case_id')
    m['timestamp'] = m.timestamp.astype(int)
    for _, x in tc.iterrows():
        ts = int(str(start[x.trace_id])[:10])
        sc = {s: dev(m, s, ts) for s in ALL}
        # 'frontend' metric name also matches 'frontend-external'; contains() is the author's matching rule.
        def rank(cands):
            r = sorted(cands, key=lambda s: -sc[s.replace('frontendservice', 'frontend')])
            r = [s.replace('frontendservice', 'frontend') for s in r]
            return r.index(x['gt']) + 1 if x['gt'] in r else None
        tr = [s for s in x.services]
        rows.append(dict(case=case, fault=x.fault, trace=x.trace_id[:8], spans=x.spans, gt_in_trace=x.gt_in_trace,
                         heur_rank=x.heur_rank, rank_trace=rank(tr), rank_all=rank(ALL), gt=x['gt'], scores=json.dumps(sc)))
d = pd.DataFrame(rows); d.to_csv(S / 'metric-dev-rank.csv', index=False)
def summ(col):
    r = d[col]; return f'R@1 {int((r == 1).sum())}/{len(r)}  MRR {(1 / r).fillna(0).mean():.3f}'
for col in ('heur_rank', 'rank_trace', 'rank_all'):
    print(col, summ(col))
print(d.groupby('fault').agg(heur=('heur_rank', lambda r: (r == 1).mean()), trace=('rank_trace', lambda r: (r == 1).mean()),
                             all=('rank_all', lambda r: (r == 1).mean())).round(2))
