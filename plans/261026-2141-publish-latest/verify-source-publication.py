"""Review candidate paths and scan for credential literals without printing matches."""
import ast
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
def paths(args):
    output = subprocess.run(['git', *args, '-z'], cwd=ROOT, capture_output=True, check=True).stdout
    return {p.decode('utf-8') for p in output.split(b'\0') if p}
candidate = sorted(paths(['ls-files', '--others', '--exclude-standard']) |
                   paths(['diff', '--name-only']) | paths(['diff', '--cached', '--name-only']))
patterns = {
    'hf-token': rb'\bhf_[a-zA-Z0-9]{24,}\b',
    'github-token': rb'\b(?:gh[pousr]_[a-zA-Z0-9]{30,}|github_pat_[a-zA-Z0-9_]{40,})\b',
    'private-key': rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'aws-access-key': rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'provider-key': rb'\b(?:sk-ant-[a-zA-Z0-9_-]{30,}|sk-proj-[a-zA-Z0-9_-]{30,}|AIza[a-zA-Z0-9_-]{30,})\b',
    'signed-url': rb'(?:X-Amz-Signature|X-Goog-Signature|[?&](?:api_key|access_token))=[a-zA-Z0-9%_-]{20,}',
}
findings, binary, parsed = [], [], 0
for relative in candidate:
    path = ROOT / relative
    if not path.is_file():
        continue
    if path.suffix.lower() in {'.pdf', '.zip', '.sqlite', '.parquet', '.pyc', '.pem', '.key', '.stackdump'} or path.name.startswith('.env'):
        binary.append(relative)
    data = path.read_bytes()
    for name, pattern in patterns.items():
        for match in re.finditer(pattern, data):
            findings.append({'path': relative, 'line': data[:match.start()].count(b'\n')+1, 'rule': name})
    if path.suffix == '.py':
        ast.parse(data.decode('utf-8-sig'), filename=relative)
        parsed += 1
result = {'candidate_files': len(candidate), 'candidate_bytes': sum((ROOT/p).stat().st_size for p in candidate if (ROOT/p).is_file()),
          'python_files_syntax_checked': parsed, 'credential_findings': findings,
          'unexpected_binary_or_data_paths': binary,
          'status': 'passed' if not findings and not binary else 'needs-review'}
(HERE / 'source-publication-check.json').write_text(json.dumps(result, indent=2) + '\n')
(HERE / 'source-candidates.json').write_text(json.dumps(candidate, indent=2) + '\n')
print(json.dumps(result, indent=2))
if findings or binary:
    raise SystemExit(1)
