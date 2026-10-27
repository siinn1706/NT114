"""Atomic allowlisted commit to the existing private dataset, then hash every download."""
import hashlib
import json
from pathlib import Path
from huggingface_hub import CommitOperationAdd, HfApi, hf_hub_download

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
STAGE = HERE / 'publish-stage'
manifest = json.loads((HERE / 'artifact-manifest.json').read_text(encoding='utf-8'))
before = json.loads((HERE / 'hf-before.json').read_text())
repo = manifest['repo']
assert repo == before['repo'] == 'siinn1706/nt114-rca-data'
assert manifest['visibility'] == 'private'
expected = dict(manifest['files'])
data = (STAGE / 'artifact-manifest.json').read_bytes()
expected['artifact-manifest.json'] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
assert {p.relative_to(STAGE).as_posix() for p in STAGE.rglob('*') if p.is_file()} == set(expected)
for name, entry in expected.items():
    assert not name.startswith(manifest['canonical_release_unchanged'] + '/')
    assert hashlib.sha256((STAGE/name).read_bytes()).hexdigest() == entry['sha256'], name
api = HfApi()
assert api.whoami()['name'] == 'siinn1706'
current = api.repo_info(repo, repo_type='dataset', files_metadata=True)
assert current.private is True and current.sha == before['revision'], 'HF HEAD/privacy changed; re-inspect before writing'
canonical_prefix = manifest['canonical_release_unchanged'] + '/'
def canonical_tree(info):
    return {s.rfilename: {'blob_id': s.blob_id, 'size': s.size,
                         'lfs_sha256': getattr(s.lfs, 'sha256', None) if s.lfs else None}
            for s in info.siblings if s.rfilename.startswith(canonical_prefix)}
prior_canonical = canonical_tree(current)
assert prior_canonical
commit = api.create_commit(repo_id=repo, repo_type='dataset', parent_commit=current.sha,
    operations=[CommitOperationAdd(path_in_repo=name, path_or_fileobj=str(STAGE/name)) for name in sorted(expected)],
    commit_message='Add RCLAgent one-trace GPU smoke artifacts and manifest-derived research overview',
    commit_description='Private artifact publication. Keep canonical release unchanged. Preserve failed native runs; D passed, trace E stopped on out-of-domain service query. No new inference run.')
revision = commit.oid
downloaded = {}
for name, entry in expected.items():
    path = Path(hf_hub_download(repo, name, repo_type='dataset', revision=revision,
                               local_dir=HERE/'download-cache'))
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == entry['sha256'] and path.stat().st_size == entry['bytes'], name
    downloaded[name] = actual
after = api.repo_info(repo, repo_type='dataset', revision=revision, files_metadata=True)
assert after.private is True and canonical_tree(after) == prior_canonical
receipt = {'repo': repo, 'repo_type': 'dataset', 'visibility': 'private',
    'previous_revision': current.sha, 'revision': revision, 'commit_url': commit.commit_url,
    'files_uploaded_and_download_verified': len(downloaded), 'download_sha256': downloaded,
    'canonical_file_count_unchanged': len(prior_canonical),
    'canonical_tree_unchanged': True, 'private_after_publish': after.private,
    'scope': 'Private data/artifact publication only; no app/server or model job deployed'}
(HERE/'hf-publish-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k:v for k,v in receipt.items() if k != 'download_sha256'}, indent=2))
