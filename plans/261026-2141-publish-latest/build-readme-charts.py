"""Render documentation charts directly from release/native manifests."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'docs/figures'
OUT.mkdir(parents=True, exist_ok=True)
SMOKE = ROOT / 'plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle'
sources = [ROOT / 'nt114-rca/nt114-rca/releases/nt114-data-v1.json',
           SMOKE / 'kaggle-native-summary.json', SMOKE / 'kaggle-repair-v4-summary.json',
           SMOKE / 'kaggle-repair-v5-summary.json']
release, v3, v4, v5 = [json.loads(p.read_text(encoding='utf-8')) for p in sources]
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.spines.left': False,
    'axes.edgecolor': '#CBD5E1', 'text.color': '#172B4D', 'axes.labelcolor': '#334155',
    'xtick.color': '#64748B', 'ytick.color': '#172B4D', 'savefig.facecolor': '#F8FAFC',
    'figure.facecolor': '#F8FAFC', 'axes.facecolor': '#F8FAFC', 'svg.hashsalt': 'nt114-readme'})

def save(fig, name):
    for suffix in ('png', 'svg'):
        fig.savefig(OUT / (name + '.' + suffix), dpi=180, bbox_inches='tight',
                    metadata={'Creator': 'NT114 manifest-derived documentation chart'})
    plt.close(fig)

names = ['rcaeval', 'aiops2025', 'rca100', 'nezha']
labels = ['RCAEval', 'AIOps2025', 'RCA100', 'Nezha']
states = ['ACCEPT', 'ACCEPT_WITH_WARNINGS', 'REJECT']
counts = np.array([[release['builds'][name]['states'].get(state, 0) for state in states] for name in names])
fig, ax = plt.subplots(figsize=(10.8, 4.8))
fig.subplots_adjust(top=.70, bottom=.17, left=.17, right=.93)
fig.text(.07, .94, 'Quy mô bản phát hành dữ liệu canonical', size=19, weight='bold')
fig.text(.07, .865, f'{counts.sum():,} bản ghi  ·  {counts[:, :2].sum():,} ACCEPT / có cảnh báo  ·  {counts[:, 2].sum()} REJECT'.replace(',', '.'), size=12, color='#475569')
left = np.zeros(len(names))
for column, color, label in zip(range(3), ['#2563EB', '#F59E0B', '#DC2626'], ['ACCEPT', 'ACCEPT_WITH_WARNINGS', 'REJECT']):
    bars = ax.barh(labels, counts[:, column], left=left, height=.57, color=color, label=label)
    for bar, count in zip(bars, counts[:, column]):
        if count >= 18:
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_y()+bar.get_height()/2,
                    str(count), ha='center', va='center', color='white' if column == 0 else '#422006', size=10, weight='bold')
    left += counts[:, column]
for y, total in enumerate(counts.sum(axis=1)):
    ax.text(total+10, y, str(total), va='center', weight='bold')
ax.invert_yaxis()
ax.set_xlim(0, 800)
ax.set_xlabel('Số bản ghi trong release manifest; không phải số sự cố độc lập hoặc kết quả chẩn đoán', labelpad=12, size=10)
ax.grid(axis='x', alpha=.18)
ax.set_axisbelow(True)
ax.tick_params(axis='y', length=0, pad=10)
ax.legend(loc='lower left', bbox_to_anchor=(-.12, -0.57), ncol=3, frameon=False, fontsize=9)
save(fig, 'canonical-data-quality')

requests = np.array([[v3['model_requests_including_retries']['protocol'], v3['model_requests_including_retries']['trace']],
                    [v4['phases'][phase]['request_count'] for phase in ('protocol', 'trace')],
                    [v5['phases'][phase]['request_count'] for phase in ('protocol', 'trace')]])
fig, ax = plt.subplots(figsize=(10.8, 4.5))
fig.subplots_adjust(top=.72, bottom=.20, left=.25, right=.93)
fig.text(.07, .94, 'Kaggle GPU: lời gọi đã thực hiện, kể cả retry', size=18, weight='bold')
fig.text(.07, .855, 'Một backbone Qwen3-4B · một T4 · một trace được chọn trước', size=12, color='#475569')
ylabels = ['v3 · dừng tại D', 'v4 · trước model', 'v5 · D đạt, E dừng']
for column, color, label in zip(range(2), ['#0D9488', '#7C3AED'], ['D · dữ liệu tổng hợp', 'E · trace benchmark']):
    left = np.zeros(3) if column == 0 else requests[:, 0]
    bars = ax.barh(ylabels, requests[:, column], left=left, height=.54, color=color, label=label)
    for bar, count in zip(bars, requests[:, column]):
        if count:
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_y()+bar.get_height()/2, str(count), ha='center', va='center', color='white', weight='bold')
for y, total in enumerate(requests.sum(axis=1)):
    ax.text(total+.12, y, f'{total} request' + ('s' if total != 1 else ''), va='center', color='#475569', size=10)
ax.invert_yaxis()
ax.set_xlim(0, 6)
ax.set_xticks(range(7))
ax.tick_params(axis='y', length=0, pad=10)
ax.grid(axis='x', alpha=.18)
ax.set_axisbelow(True)
ax.set_xlabel('Số request model thực tế — biểu đồ vận hành, không biểu diễn accuracy', labelpad=12, size=10)
ax.legend(loc='lower left', bbox_to_anchor=(-.26, -.55), ncol=2, frameon=False, fontsize=10)
save(fig, 'kaggle-smoke-requests')
manifest = {'matplotlib': matplotlib.__version__,
    'source_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
    'canonical_counts': {label: dict(zip(states, map(int, row))) for label, row in zip(labels, counts)},
    'native_request_counts': requests.tolist(),
    'charts': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob('*.png'))}}
(HERE / 'chart-provenance.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'charts': manifest['charts'], 'canonical_records': int(counts.sum()), 'usable_records': int(counts[:, :2].sum())}, indent=2))
