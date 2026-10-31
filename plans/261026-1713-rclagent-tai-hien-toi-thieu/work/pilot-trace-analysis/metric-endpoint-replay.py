"""Replay the author's search_fluctuating_metrics on the pilot packages and decompose why it is empty."""
import json, pickle, sys, collections
from pathlib import Path
import pandas as pd

PKG = Path(sys.argv[1])          # package-pilot-01/traces
RUN = Path(sys.argv[2])          # art/v11/run
OUT = Path(sys.argv[3])

rows, gt_rows = [], []
for tdir in sorted(PKG.iterdir()):
    tid = tdir.name
    m = pd.read_csv(tdir / 'input/metric/all/metrics.csv', low_memory=False)
    sn = pickle.load(open(tdir / 'input/metric/service_node_map.pkl', 'rb'))
    gt = pd.read_csv(tdir / 'scoring/groundtruth.csv').iloc[0]
    inject = int(gt.timestamp)
    sel = json.load(open(tdir / 'selection.json'))
    tsec = sel['query_window']['start_second']
    # Queries the model actually sent in v11, with the response it received.
    q = []
    for l in open(RUN / 'traces' / tid / 'events.jsonl', encoding='utf-8'):
        e = json.loads(l)
        if e['kind'] == 'tool_result' and e['name'] == 'search_fluctuating_metrics':
            q.append((e['params'].get('service_name'), e['params'].get('timestamp'), e['response'][:60]))
    for svc, ts_s, resp in q:
        ts = int(str(ts_s)[:10])
        node = sn.get(svc)
        name_hit = m.service_name.str.contains(svc, case=False, na=False)
        cond = name_hit | ((m.node_id == node) & (m.service_name.fillna('') == '')) if node else name_hit
        base = m[cond & m.timestamp.between(ts - 1200, ts + 1200)]
        r = dict(trace=tid[:8], gt=gt.cmdb_id, fault=gt.failure_type, svc=svc, ts_minus_inject=ts - inject,
                 ts_minus_trace=ts - tsec, node=node, rows=len(base), groups=0, std0=0, spike_author=0,
                 spike_pre_baseline=0, resp=resp.strip())
        for (kpi, nid, s), g in base.groupby(['kpi_name', 'node_id', 'service_name'], dropna=False):
            r['groups'] += 1
            mu, sd = g.value.mean(), g.value.std()
            w = g[g.timestamp.between(ts - 600, ts + 600)]
            if pd.isna(sd) or sd == 0:
                r['std0'] += 1
            elif ((w.value - mu).abs() > 3 * sd).any():
                r['spike_author'] += 1
            pre = g[g.timestamp < inject]
            if len(pre) > 30 and pre.value.std() > 0:
                post = g[g.timestamp >= inject]
                if ((post.value - pre.value.mean()).abs() > 3 * pre.value.std()).any():
                    r['spike_pre_baseline'] += 1
        rows.append(r)
    # Ground-truth service KPIs: pre vs post injection shift in pre-sigma units.
    g_all = m[m.service_name.str.contains(gt.cmdb_id, case=False, na=False)]
    for (kpi, s), g in g_all.groupby(['kpi_name', 'service_name']):
        pre, post = g[g.timestamp < inject], g[g.timestamp >= inject]
        b = g[g.timestamp.between(tsec - 1200, tsec + 1200)]
        w = g[g.timestamp.between(tsec - 600, tsec + 600)]
        gt_rows.append(dict(trace=tid[:8], svc=s, kpi=kpi, n_pre=len(pre), n_post=len(post),
                            pre_mean=pre.value.mean(), pre_std=pre.value.std(), post_mean=post.value.mean(),
                            shift_sigma=(post.value.mean() - pre.value.mean()) / pre.value.std() if pre.value.std() else float('nan'),
                            max_dev_author_sigma=((w.value - b.value.mean()).abs().max() / b.value.std()) if b.value.std() else float('nan'),
                            sampling_s=g.timestamp.diff().median(), span_s=(g.timestamp.min() - inject, g.timestamp.max() - inject)))

d = pd.DataFrame(rows); gtd = pd.DataFrame(gt_rows)
d.to_csv(OUT / 'metric-queries.csv', index=False); gtd.to_csv(OUT / 'metric-gt-kpis.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30); pd.set_option('display.max_rows', 300)
print(d.groupby('resp').size())
print(d.groupby('trace')[['rows', 'groups', 'std0', 'spike_author', 'spike_pre_baseline']].sum())
print(d[d.rows == 0].svc.value_counts())
print(d.ts_minus_trace.describe())
print(gtd.round(2).to_string())
