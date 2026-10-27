"""Append native repair evidence; never reset or hide failed attempts."""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('version', type=int)
options = parser.parse_args()
state_path = HERE / 'fix-state.json'
state = json.loads(state_path.read_text())
summary_path = HERE / f'kaggle-repair-v{options.version}-summary.json'
summary = json.loads(summary_path.read_text())
attempts = state['shared_memory_repair_attempts']
entry = {'notebook_version': options.version, 'native_status': summary['status'],
         'summary': summary_path.name, 'artifact_sha256': summary['artifact_sha256'],
         'kernel_status': (summary['compatibility']['status'] or {}).get('status'),
         'requests': {phase: data['request_count'] for phase, data in summary['phases'].items()}}
if any(row['notebook_version'] == options.version for row in attempts):
    assert next(row for row in attempts if row['notebook_version'] == options.version) == entry
else:
    attempts.append(entry)
failed = sum(row['native_status']['status'] != 'passed' for row in attempts)
state['failed_native_repair_attempts'] = failed
state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'recorded': entry, 'failed_native_repair_attempts': failed}, indent=2))
if failed >= state['max_failed_repairs_before_human_architecture_checkpoint']:
    raise SystemExit('Three failed repairs: stop for architecture checkpoint with user')
