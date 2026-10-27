"""Prepare an explicit private-artifact allowlist; never upload the project tree."""
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
STAGE = HERE / 'publish-stage'
STAGE.mkdir(exist_ok=True)
SMOKE = ROOT / 'plans/261026-1713-rclagent-tai-hien-toi-thieu/kaggle'
PREFIX = 'reproductions/rclagent-smoke-261026/'
payload = {}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def copy(source, target):
    source = Path(source)
    assert source.is_file(), source
    destination = STAGE / target
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    assert sha(source) == sha(destination)
    payload[target] = {'bytes': destination.stat().st_size, 'sha256': sha(destination),
                       'source': source.relative_to(ROOT).as_posix()}

copy(ROOT / 'docs/hugging-face-data-card.md', 'README.md')
for source in sorted((ROOT / 'docs/figures').glob('*')):
    if source.suffix in ('.png', '.svg'):
        copy(source, 'figures/' + source.name)
names = ['rclagent-kaggle-smoke.ipynb', 'rclagent-kaggle-bundle.zip',
         'rclagent-kaggle-bundle.zip.sha256', 'manifest.json', 'cpu-equivalence.json',
         'package-validation.json', 'README.md', 'preparation-report.md',
         'kaggle-run-report.md', 'repair-report.md', 'kaggle-native-summary.json',
         'kaggle-repair-v4-summary.json', 'kaggle-repair-v5-summary.json']
archives = ['kaggle-setup-v1-error-results.zip', 'kaggle-setup-v2-error-results.zip',
            'rclagent-kaggle-gpu-results.zip', 'rclagent-kaggle-repair-v4-results.zip',
            'rclagent-kaggle-repair-v5-results.zip']
for name in [*names, *archives]:
    copy(SMOKE / name, PREFIX + name)
    if name in archives:
        checksum = SMOKE / (name + '.sha256')
        if checksum.exists():
            copy(checksum, PREFIX + checksum.name)

literature = ROOT / 'plans/261024-0858-tong-quan-1000-q1-chon-bai-nen-rca-thieu-telemetry/work/records'
members = {}
archive = STAGE / 'research/literature-261024-records.zip'
archive.parent.mkdir(exist_ok=True)
credential_pattern = re.compile(rb'\b(?:hf_[A-Za-z0-9]{24,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
    for source in sorted(literature.glob('*.csv')):
        data = source.read_bytes()
        if credential_pattern.search(data):
            raise RuntimeError('Credential-like literal in literature metadata: ' + source.name)
        members[source.name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        zipped.writestr(source.name, data)
assert members
with zipfile.ZipFile(archive) as zipped:
    assert set(zipped.namelist()) == set(members)
    for name, entry in members.items():
        assert hashlib.sha256(zipped.read(name)).hexdigest() == entry['sha256']
corpus_manifest = {'scope': 'Public scholarly response metadata CSVs only; no PDFs/fulltext, benchmark labels, credentials or transcripts',
                   'source_directory': literature.relative_to(ROOT).as_posix(), 'members': members}
corpus_path = STAGE / 'research/literature-261024-records-manifest.json'
corpus_path.write_text(json.dumps(corpus_manifest, indent=2) + '\n')
for path in (archive, corpus_path):
    payload[path.relative_to(STAGE).as_posix()] = {'bytes': path.stat().st_size,
        'sha256': sha(path), 'source': 'generated from ' + literature.relative_to(ROOT).as_posix()}

manifest = {'repo': 'siinn1706/nt114-rca-data', 'repo_type': 'dataset', 'visibility': 'private',
            'canonical_release_unchanged': 'nt114-data-v1-20261014-6fdd9835',
            'scope': 'Explicit new documentation, manifest-derived charts, one-trace input/results and scholarly metadata archive',
            'files': payload}
(HERE / 'artifact-manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
shutil.copyfile(HERE / 'artifact-manifest.json', STAGE / 'artifact-manifest.json')
assert {p.relative_to(STAGE).as_posix() for p in STAGE.rglob('*') if p.is_file()} == set(payload) | {'artifact-manifest.json'}
print(json.dumps({'files': len(payload)+1, 'bytes': sum(p.stat().st_size for p in STAGE.rglob('*') if p.is_file()),
                  'literature_csv_members': len(members), 'literature_archive_bytes': archive.stat().st_size,
                  'canonical_release_not_in_upload': True}, indent=2))
