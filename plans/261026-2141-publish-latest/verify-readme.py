"""Validate authored navigation and manifest-derived README/chart claims."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
documents = [ROOT/'README.md', ROOT/'docs/publication.md', ROOT/'docs/hugging-face-data-card.md']
missing = []
for path in documents:
    text = path.read_text(encoding='utf-8')
    assert len(text.splitlines()) <= 800
    for target in re.findall(r'\]\(([^)]+)\)', text):
        if target.startswith(('http:', 'https:', '#', 'mailto:')):
            continue
        resolved = (path.parent / target.split('#')[0]).resolve()
        if not resolved.exists():
            missing.append({'document': path.relative_to(ROOT).as_posix(), 'target': target})
charts = json.loads((HERE/'chart-provenance.json').read_text())
for path, expected in charts['source_sha256'].items():
    assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == expected
assert sum(sum(row.values()) for row in charts['canonical_counts'].values()) == 1340
assert charts['native_request_counts'] == [[1, 0], [0, 0], [3, 2]]
for name, expected in charts['charts'].items():
    assert hashlib.sha256((ROOT/'docs/figures'/name).read_bytes()).hexdigest() == expected
print(json.dumps({'documents_checked': len(documents), 'missing_relative_links': missing,
                  'chart_source_hashes': 'matched', 'canonical_records': 1340,
                  'native_chart_counts': 'matched'}, indent=2))
if missing:
    raise SystemExit(1)
