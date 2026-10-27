"""Inspect official wheel source as ZIP bytes only; never imports or runs vLLM."""
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
area = HERE / 'runtime/vllm-wheel-source'
area.mkdir(parents=True, exist_ok=True)
metadata = json.load(urllib.request.urlopen('https://pypi.org/pypi/vllm/0.10.2/json'))
wheel = next(x for x in metadata['urls'] if x['filename'].endswith('manylinux1_x86_64.whl'))
path = area / wheel['filename']
if not path.exists():
    urllib.request.urlretrieve(wheel['url'], path)
h = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
assert h == wheel['digests']['sha256']
names = ['vllm/attention/ops/prefix_prefill.py', 'vllm/attention/backends/xformers.py',
         'vllm/attention/ops/paged_attn.py']
files = {}
with zipfile.ZipFile(path) as zipped:
    for name in names:
        data = zipped.read(name)
        destination = area / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        files[name] = {'sha256': hashlib.sha256(data).hexdigest(), 'lines': len(data.splitlines())}
result = {'wheel_sha256': h, 'wheel_bytes': path.stat().st_size, 'files': files}
(area / 'provenance.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
