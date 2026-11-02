"""Run the Modal shards of the packaged bundle on T4 containers with the unchanged Kaggle runtime.

usage (from this folder, after refresh-package.py and build-notebook.py):
  modal run --detach modal-run.py --shards 10 --only 0      # first shard alone, to prove setup
  modal run --detach modal-run.py --shards 10 --skip 0      # the other nine
  modal volume get rclagent-telemetry-gap-results / runtime/modal-results

Each container lays the bundle out as a Kaggle input dataset, then runs cells A (environment), B (isolated install and
T4 kernel check) and C-F (model server, protocol gate, the shard's runs, scoring) of kaggle-runtime.py exactly as the
notebook does, for shard modal:K/N: within the bundle's modal runs, every N-th run starting at K. Same GPU model,
FP16, context, limits and sampling as Kaggle; each container runs one request at a time. The result ZIP of every
shard, finished or not, lands in the results volume.
"""
import hashlib
import json
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
BUNDLE = 'rclagent-kaggle-bundle.zip'
REMOTE_RUNTIME = '/root/kaggle-runtime.py'
app = modal.App('rclagent-telemetry-gap')
volume = modal.Volume.from_name('rclagent-telemetry-gap-results', create_if_missing=True)
# Kaggle's base Python of the S1 v3 sessions was 3.13; the runtime builds its own pinned venv from it. Triton
# compiles its launcher with the system C compiler, which Kaggle images carry.
image = (modal.Image.debian_slim(python_version='3.13')
         .apt_install('build-essential')
         .add_local_file(HERE / BUNDLE, '/kaggle/input/rclagent-bundle/' + BUNDLE)
         .add_local_file(HERE / 'kaggle-runtime.py', REMOTE_RUNTIME))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@app.function(image=image, gpu='T4', cpu=2, memory=12288, timeout=8 * 3600, volumes={'/results': volume},
              retries=0)
def run_shard(shard, bundle_sha256, manifest_sha256):
    import importlib.util
    import os
    import shutil
    import traceback
    os.environ['RCL_PLATFORM'] = 'modal'
    Path('/kaggle/working').mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('rclagent_kaggle_runtime', REMOTE_RUNTIME)
    rcl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rcl)
    out = Path('/results') / shard.replace(':', '-').replace('/', '-of-')
    out.mkdir(parents=True, exist_ok=True)
    stage, error = 'A', None
    try:
        rcl.environment()
        stage = 'B'
        rcl.install(bundle_sha256, manifest_sha256)
        stage = 'C'
        rcl.run_once(bundle_sha256, manifest_sha256, shard)
        stage = 'done'
    except BaseException:
        error = traceback.format_exc()
        if not list(rcl.ROOT.glob('rclagent-smoke-results*.zip')):
            rcl.preparation_failure(stage)
    finally:
        for path in rcl.ROOT.glob('rclagent-smoke-results*.zip*'):
            shutil.copyfile(path, out / path.name)
        (out / 'modal-status.json').write_text(json.dumps({'shard': shard, 'stage': stage, 'error': error},
                                                          indent=2) + '\n', encoding='utf-8')
        volume.commit()
    return {'shard': shard, 'stage': stage, 'error': error.splitlines()[-1] if error else None}


@app.local_entrypoint()
def main(shards: int = 10, only: str = '', skip: str = ''):
    manifest = json.loads((HERE / 'manifest.json').read_text(encoding='utf-8'))
    if manifest['files']['kaggle-runtime.py']['sha256'] != digest(HERE / 'kaggle-runtime.py'):
        raise SystemExit('kaggle-runtime.py differs from the packaged runtime; refresh the package first')
    modal_runs = sum(run.get('site') == 'modal' for run in manifest.get('runs', []))
    if not modal_runs:
        raise SystemExit('The bundle lists no modal runs')
    picked = [int(k) for k in only.split(',') if k] or [k for k in range(shards) if str(k) not in skip.split(',')]
    names = [f'modal:{k}/{shards}' for k in picked]
    print(json.dumps({'bundle_sha256': digest(HERE / BUNDLE), 'modal_runs': modal_runs, 'shards': names}))
    for result in run_shard.starmap([(name, digest(HERE / BUNDLE), digest(HERE / 'manifest.json')) for name in names]):
        print(json.dumps(result))
