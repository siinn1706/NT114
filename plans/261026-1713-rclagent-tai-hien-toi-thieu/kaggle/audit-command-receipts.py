"""Rehash completed command observations without changing their actual verdicts."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
STORE = PROJECT / 'private/kaggle-command-observations-261026'
RECORDER = Path('C:/Users/Siinn/.agents/skills/nckh-cook/references/_shared/scripts/record-command.py')
rows = []
incomplete = []
for area in sorted(STORE.iterdir()):
    if not (area / 'receipt-v2.json').exists():
        if (area / 'attempt.json').exists():
            item = json.loads((area / 'attempt.json').read_text())
            incomplete.append({'attempt': area.name, 'status': item['status'],
                               'command_exit': item['exit_status'],
                               'process_cleanup': item.get('process_cleanup'), 'receipt_v2': None})
        continue
    process = subprocess.run([sys.executable, '-X', 'utf8', str(RECORDER), 'verify',
                              '--private-store', str(STORE), '--attempt', area.name],
                             capture_output=True, text=True, encoding='utf-8')
    result = json.loads(process.stdout)
    rows.append({'attempt': area.name, 'verification_exit': process.returncode,
                 'verdict': result['verdict'], 'command_status': result['status'],
                 'command_exit': result['exit_status']})
    # Recorder verify returns 1 for a consistently recorded failed command.
    expected_exit = 0 if result['status'] == 'completed-unreviewed' else 1
    assert process.returncode == expected_exit and result['verdict'] == 'CONSISTENT', area.name
summary = {'completed_observations_rehashed': len(rows), 'all_completed_consistent': True,
           'attempts': rows, 'incomplete_observations': incomplete,
           'limitation': 'Raw-command/receipt consistency only; failed commands remain failed, native/scientific acceptance separate.'}
(HERE / 'command-receipts.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, indent=2))
