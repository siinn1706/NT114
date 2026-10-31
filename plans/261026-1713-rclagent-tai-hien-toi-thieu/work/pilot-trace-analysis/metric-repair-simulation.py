"""Simulate repaired search_fluctuating_metrics variants on every train trace (CPU only, labels used only for scoring).

as_written : author code (groupby drops NaN node_id) -> always empty on RE2-OB.
keep_nan   : same 3-sigma rule, groupby(dropna=False).
pre_base   : keep_nan, but mean/std from [ts-1200, ts-600) only, window [ts-600, ts+600]; label-free.
"""
import json, sys, importlib.util
from pathlib import Path
import pandas as pd

ROOT = Path(sys.argv[1])      # W7165616276
S = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location('pp', ROOT / 'code/preprocess/preprocess_re2ob.py')
pp = importlib.util.module_from_spec(spec); spec.loader.exec_module(pp)

t = pd.DataFrame(json.load(open(S / 'train-traces.json')))
ids = set(t.trace_id)
start = {}
for c in pd.read_csv(ROOT / 'data/re2ob/trace/all/trace_jaeger-span.csv', usecols=['trace_id', 'timestamp'], chunksize=3_000_000):
    c = c[c.trace_id.isin(ids)]
    for tid, v in c.groupby('trace_id').timestamp.min().items():
        start[tid] = min(start.get(tid, v), v)
t['ts'] = t.trace_id.map(lambda x: int(str(start[x])[:10]))


def dev(m, svc, ts):
    """Largest |window mean - pre mean| / pre std over the service's KPIs (what the returned table would show)."""
    g0 = m[m.service_name.str.contains(svc, case=False, na=False)]
    best = 0.0
    for _, g in g0.groupby('kpi_name'):
        ref, w = g[g.timestamp.between(ts - 1200, ts - 601)], g[g.timestamp.between(ts - 600, ts + 600)]
        sd = ref.value.std()
        if len(ref) > 30 and sd > 0:
            best = max(best, abs(w.value.mean() - ref.value.mean()) / sd)
    return best


def flags(m, svc, ts, mode):
    base = m[m.service_name.str.contains(svc, case=False, na=False) & m.timestamp.between(ts - 1200, ts + 1200)]
    if mode == 'as_written':
        groups = base.groupby(['kpi_name', 'node_id', 'service_name'])
    else:
        groups = base.groupby(['kpi_name', 'node_id', 'service_name'], dropna=False)
    out = []
    for (kpi, _, s), g in groups:
        w = g[g.timestamp.between(ts - 600, ts + 600)]
        ref = g[g.timestamp < ts - 600] if mode == 'pre_base' else g
        mu, sd = ref.value.mean(), ref.value.std()
        if pd.isna(mu) or pd.isna(sd) or sd == 0:
            continue
        if ((w.value - mu).abs() > 3 * sd).any():
            out.append(f'{s}.{kpi}')
    return out


rows = []
for case, tc in t.groupby('case'):
    fdir, n = case.rsplit('_', 1)
    cdir = ROOT / 'data/raw/RE2-OB' / fdir / n
    m = pp._convert_one_metric_simple(str(cdir), case).drop(columns='_case_id')
    m['timestamp'] = m.timestamp.astype(int)
    m['node_id'] = float('nan')   # the served CSV reads the empty string back as NaN
    inj = int((cdir / 'inject_time.txt').read_text().strip())
    for _, x in tc.iterrows():
        cands = [s for s in x.services if s not in ('frontendservice', 'frontend')]
        for mode in ('as_written', 'keep_nan', 'pre_base', 'pre_dev'):
            fn = (lambda s: dev(m, s, x.ts)) if mode == 'pre_dev' else (lambda s: len(flags(m, s, x.ts, mode)))
            f = {s: fn(s) for s in cands}
            if x['gt'] not in f:
                f[x['gt'] + '*'] = fn(x['gt'])   # GT outside the trace: what a query would return
            rows.append(dict(case=case, trace=x.trace_id[:8], fault=x.fault, gt=x['gt'], gt_in_trace=x.gt_in_trace,
                             ts_minus_inject=x.ts - inj, mode=mode,
                             gt_flags=f.get(x['gt'], f.get(x['gt'] + '*')),
                             other_flagged=sum(1 for k, v in f.items() if not k.startswith(x['gt']) and v > 0),
                             n_other=sum(1 for k in f if not k.startswith(x['gt'])),
                             gt_top=max(f, key=f.get).rstrip('*') == x['gt'] and f[max(f, key=f.get)] > 0 and
                                    sum(1 for v in f.values() if v == f[max(f, key=f.get)]) == 1))
    print(case, flush=True)
d = pd.DataFrame(rows); d.to_csv(S / 'metric-fix-sim.csv', index=False)
print(d.ts_minus_inject.describe())
print(d.groupby('mode').agg(gt_flagged=('gt_flags', lambda s: (s > 0).mean()), gt_unique_top=('gt_top', 'mean'),
                            other_flag_rate=('other_flagged', 'sum')).join(d.groupby('mode').n_other.sum()))
print(d[d['mode'] != 'as_written'].groupby(['mode', 'fault']).agg(gt_flagged=('gt_flags', lambda s: (s > 0).mean()),
                                                                 gt_unique_top=('gt_top', 'mean')).round(2))
