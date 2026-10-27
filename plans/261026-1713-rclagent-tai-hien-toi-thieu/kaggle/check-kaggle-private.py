"""Read-only privacy/status check through the installed authenticated Kaggle API."""
import json
import re
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()
ref = 'siinn1706/rclagent-one-trace-smoke-261026'
matches = [d for d in api.dataset_list(search='rclagent-one-trace-smoke-261026', mine=True) if d.ref == ref]
assert len(matches) == 1, 'Expected one owned dataset'
dataset = matches[0]
assert dataset.is_private is True, 'Dataset must be private'
result = {'dataset': {'ref': dataset.ref, 'is_private': dataset.is_private,
                      'version': dataset.current_version_number, 'bytes': dataset.total_bytes}}
runtime = Path(__file__).resolve().parent / 'runtime'
result['native_notebooks'] = {}
sources = [p for p in runtime.glob('kaggle-source-v*/kernel-metadata.json')
           if re.fullmatch(r'kaggle-source-v\d+', p.parent.name)]
for native_metadata in sorted(sources, key=lambda p: int(p.parent.name.removeprefix('kaggle-source-v'))):
    kernel = json.loads(native_metadata.read_text(encoding='utf-8'))
    assert kernel['is_private'] is True and kernel['enable_gpu'] is True and kernel['enable_internet'] is True
    result['native_notebooks'][native_metadata.parent.name] = {key: kernel.get(key) for key in
        ('id', 'is_private', 'enable_gpu', 'enable_internet', 'machine_shape', 'dataset_sources')}
destination = Path(__file__).resolve().parent / 'kaggle-private-status.json'
destination.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, indent=2))
