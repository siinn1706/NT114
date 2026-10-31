"""Per-trace reasoning chain: span services, self-state flags, log evidence for the labelled service, consolidation and final ranking."""
import json, sys, re, collections
from pathlib import Path
import pandas as pd

PKG, RUN = Path(sys.argv[1]), Path(sys.argv[2])


def jload(s):
    s = s.strip()
    s = re.sub(r'^```(?:json)?|```$', '', s).strip()
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r'\{.*\}', s, re.S)
        try:
            return json.loads(m.group(0)) if m else None
        except Exception:
            return None


for tdir in sorted(PKG.iterdir()):
    tid = tdir.name
    gt = pd.read_csv(tdir / 'scoring/groundtruth.csv').iloc[0]
    tr = pd.read_csv(tdir / 'input/trace/all/trace_jaeger-span.csv', low_memory=False)
    tr = tr[tr.trace_id == tid] if 'trace_id' in tr else tr
    ev = [json.loads(l) for l in open(RUN / 'traces' / tid / 'events.jsonl', encoding='utf-8')]
    res = json.load(open(RUN / 'traces' / tid / 'result.json'))['root_causes']
    print('=' * 100)
    print(tid[:8], 'GT', gt.cmdb_id, gt.failure_type, '| rank', (res.index(gt.cmdb_id) + 1) if gt.cmdb_id in res else None, '| top3', res[:3])
    print('trace span services:', dict(collections.Counter(tr.cmdb_id.astype(str))), '| GT in trace:', gt.cmdb_id in set(tr.cmdb_id.astype(str)))
    # Log results per service actually received.
    logs = collections.defaultdict(list)
    for e in ev:
        if e['kind'] == 'tool_result' and e['name'] == 'search_logs':
            body = e['response']
            n = max(body.count('\n') - 1, 0)
            logs[e['params'].get('service_name')].append(n)
    trunc = [e for e in ev if e['kind'] == 'tool_result_budget' and e['applied']]
    print('search_logs data rows per service:', {k: (len(v), max(v)) for k, v in logs.items()}, '| truncated:', [(t['params']['service_name'], t['original_bytes']) for t in trunc])
    # Self-state flags.
    ss = []
    for e in ev:
        if e['kind'] == 'agent_complete' and e['operation'] == 'self_state_verification':
            o = jload(e['output']) or {}
            ss.append((o.get('service_name'), o.get('is_abnormal'), o.get('has_error_logs'), o.get('has_metric_anomaly')))
    c = collections.Counter(ss)
    print('self-state (service, abnormal, errlog, metric) x n:')
    for k, v in sorted(c.items(), key=lambda x: str(x)):
        print('   ', k, v)
    # Consolidation outputs that name the GT service, and the root-level ones.
    cons = [jload(e['output']) or e['output'] for e in ev if e['kind'] == 'agent_complete' and e['operation'] == 'consolidate']
    last = cons[-1] if cons else None
    print('last consolidate:', json.dumps(last, ensure_ascii=False)[:1500])
    gt_named = sum(1 for c_ in cons if gt.cmdb_id in json.dumps(c_))
    print('consolidations naming GT:', gt_named, '/', len(cons))
    # Final synthesis response.
    reqs = [e for e in ev if e['kind'] == 'request' and e.get('operation') is None]
    if reqs:
        n = reqs[-1]['number']
        resp = [e for e in ev if e['kind'] == 'response' and e['number'] == n]
        body = json.loads(resp[-1]['body'])['choices'][0]['message']['content'] if resp else ''
        print('final synthesis prompt tokens', reqs[-1]['prompt_tokens_local'])
        print('final synthesis out:', (body or '')[:1800])
