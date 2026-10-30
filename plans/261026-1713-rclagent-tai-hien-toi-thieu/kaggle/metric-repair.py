"""Repaired search_fluctuating_metrics for the controlled missing-source pilot (a deviation from upstream).

Same row selection, KPI grouping key, rounding and response format as the author's endpoint, with two changes:
- groups whose node_id is empty are kept: the RE2-OB preprocess writes node_id empty, it reads back as NaN, and
  upstream's groupby drops every NaN group, so the original endpoint never reports a KPI on RE2-OB;
- a KPI is reported only when its window mean [t-600, t+600] departs from the mean of a baseline taken before the
  window, [t-1200, t-600), by at least K baseline standard deviations. Upstream's +-1200 s baseline contains the
  faulty window itself, which inflates the deviation it measures against.
K = 100 was fixed on 35 train cases outside the pilot (plans/reports/analysis-261028-1104-...). No labels are read.
"""
import pandas as pd

K = 100
MIN_BASELINE_ROWS = 31
NO_ROWS = '{"message":"No matching records found."}\n'
NO_KPI = '{"message":"No fluctuating metrics found."}\n'


def search_fluctuating_metrics(metric_df, service_node_map, service_name, timestamp):
    ts = int(str(timestamp)[:10])  # Same parse as the upstream endpoint.
    node_id = service_node_map.get(service_name)
    named = metric_df['service_name'].str.contains(service_name, case=False, na=False)
    if node_id:
        named = named | ((metric_df['node_id'] == node_id) & (metric_df['service_name'].fillna('') == ''))
    baseline_df = metric_df[named & metric_df['timestamp'].between(ts - 1200, ts + 1200)]
    if baseline_df.empty:
        return NO_ROWS

    kpi_dict = {}
    for (kpi, nid, svc), group in baseline_df.groupby(['kpi_name', 'node_id', 'service_name'], dropna=False):
        before = group[group['timestamp'].between(ts - 1200, ts - 601)]
        window = group[group['timestamp'].between(ts - 600, ts + 600)]
        mean_val, std_val = before['value'].mean(), before['value'].std()
        if len(before) < MIN_BASELINE_ROWS or window.empty or pd.isna(std_val) or std_val == 0:
            continue
        if abs(window['value'].mean() - mean_val) < K * std_val:
            continue
        key = kpi
        if not pd.isna(svc) and svc:
            key = f'{svc}.{key}'
        if not pd.isna(nid) and nid:
            key = f'{nid}.{key}'
        kpi_dict[key] = {
            'regular_mean': round(mean_val, 2),
            'regular_std_dev': round(std_val, 2),
            'current_mean': round(window['value'].mean(), 2),
            'current_std_dev': round(window['value'].std(), 2),
        }

    if not kpi_dict:
        return NO_KPI
    rows = [[k] + list(v.values()) for k, v in kpi_dict.items()]
    return pd.DataFrame(rows, columns=['key', 'regular_mean', 'regular_std_dev', 'current_mean',
                                       'current_std_dev']).to_csv(index=False)
