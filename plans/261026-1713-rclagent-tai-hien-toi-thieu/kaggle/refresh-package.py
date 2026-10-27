"""Refresh external wrapper files without repeating or weakening telemetry parity.

First verifies every old member; data, upstream and CPU report stay byte-identical.
"""
import hashlib
import importlib.util
import json
import shutil
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
stage = HERE / 'runtime/package'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


manifest = json.loads((stage / 'manifest.json').read_text())
for relative, item in manifest['files'].items():
    assert sha(stage / relative) == item['sha256'], relative
for name in ('kaggle-runtime.py', 'smoke-worker.py', 'tool-result-budget.py', 'vllm-t4-compat.py', 'verify-t4-prefix-kernel.py'):
    shutil.copyfile(HERE / name, stage / name)
    manifest['files'][name] = {'sha256': sha(stage / name), 'bytes': (stage / name).stat().st_size}
spec = importlib.util.spec_from_file_location('prepare_bundle', HERE / 'prepare-bundle.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)  # Constants only; run() is not called.
manifest['tool_result_budget'] = prepare.TOOL_RESULT_BUDGET
# Additive: lets the worker answer queries whose endpoint window is outside all full data (empty either way).
selection = json.loads((stage / 'selection.json').read_text())
if 'full_data_seconds' not in selection['query_window']:
    selection['query_window']['full_data_seconds'] = prepare.full_data_seconds()
    (stage / 'selection.json').write_text(json.dumps(selection, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    manifest['files']['selection.json'] = {'sha256': sha(stage / 'selection.json'),
                                           'bytes': (stage / 'selection.json').stat().st_size}
(stage / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
shutil.copyfile(stage / 'manifest.json', HERE / 'manifest.json')
archive = HERE / 'rclagent-kaggle-bundle.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipped:
    for path in sorted(stage.rglob('*')):
        if path.is_file():
            zipped.write(path, path.relative_to(stage).as_posix())
(HERE / 'rclagent-kaggle-bundle.zip.sha256').write_text(sha(archive) + '  ' + archive.name + '\n', encoding='utf-8')
print(json.dumps({'bundle_sha256': sha(archive), 'manifest_sha256': sha(stage / 'manifest.json'),
                  'unchanged_telemetry_upstream_parity_report': True}, indent=2))
