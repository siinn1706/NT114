"""Read metadata with stored auth; never print credential values."""
import inspect
import json
from pathlib import Path
import huggingface_hub
from huggingface_hub import HfApi, hf_hub_download

HERE = Path(__file__).resolve().parent
api = HfApi()
identity = api.whoami()
assert identity['name'] == 'siinn1706'
repo = 'siinn1706/nt114-rca-data'
info = api.repo_info(repo, repo_type='dataset')
assert info.private is True
paths = api.list_repo_files(repo, repo_type='dataset', revision=info.sha)
result = {'account': identity['name'], 'repo': repo, 'private': info.private,
          'revision': info.sha, 'file_count': len(paths),
          'top_level': sorted({p.split('/')[0] for p in paths}),
          'huggingface_hub': huggingface_hub.__version__,
          'create_commit_parameters': list(inspect.signature(api.create_commit).parameters),
          'credential_role': identity.get('auth', {}).get('accessToken', {}).get('role')}
if 'README.md' in paths:
    readme = Path(hf_hub_download(repo, 'README.md', repo_type='dataset', revision=info.sha))
    (HERE / 'hf-readme-before.txt').write_text(readme.read_text(encoding='utf-8'), encoding='utf-8')
(HERE / 'hf-before.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
