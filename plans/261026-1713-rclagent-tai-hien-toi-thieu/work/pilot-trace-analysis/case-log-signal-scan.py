"""Per RE2-OB case: does the labelled service have served (non-INFO/DEBUG) logs or error-like logs after injection,
and does the author's metric endpoint (as written, and with NaN node_id kept) flag any of its KPIs?"""
import sys
from pathlib import Path
import pandas as pd

RAW = Path(sys.argv[1])        # data/raw/RE2-OB
OUT = Path(sys.argv[2])
ERR = r'error|exception|fail|refused|timeout|unavailable|deadline'
rows = []
for fdir in sorted(p for p in RAW.iterdir() if p.is_dir()):
    for cdir in sorted(p for p in fdir.iterdir() if p.is_dir() and p.name.isdigit()):
        case = f'{fdir.name}_{cdir.name}'
        gt, fault = fdir.name.rsplit('_', 1)
        inj = int((cdir / 'inject_time.txt').read_text().strip())
        lg = pd.read_csv(cdir / 'logs.csv', low_memory=False, usecols=['timestamp', 'container_name', 'message', 'level'])
        lg['t'] = lg.timestamp // 10**9
        lg = lg[lg.t.between(inj, inj + 600)]
        # The author's preprocessing writes "severity: <level>, message: ..." and the server drops info/debug.
        lvl = lg.level.astype(str).str.lower()
        served = lg[~lvl.isin(['info', 'debug'])]
        g_srv = served[served.container_name.astype(str).str.contains(gt, na=False)]
        g_err = lg[lg.container_name.astype(str).str.contains(gt, na=False) &
                   (lvl.isin(['error', 'warn', 'warning', 'fatal']) | lg.message.astype(str).str.contains(ERR, case=False))]
        m = pd.read_csv(cdir / 'simple_metrics.csv', low_memory=False)
        rows.append(dict(case=case, gt=gt, fault=fault,
                         gt_served_log_rows=len(g_srv), gt_errorlike_log_rows=len(g_err),
                         served_services=','.join(sorted(served.container_name.astype(str).unique())),
                         gt_metric_cols=sum(1 for c in m.columns if c.startswith(gt + '_'))))
        print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(OUT / 'case-signal-scan.csv', index=False)
