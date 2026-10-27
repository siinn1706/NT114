"""Metadata-only scope inventory and authenticated private artifact preflight."""
import importlib.util
import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
result = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard', '-z'],
                        cwd=ROOT, capture_output=True, check=True)
files = [ROOT / p.decode('utf-8') for p in result.stdout.split(b'\0') if p]
rows = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size} for p in files if p.is_file()]
(HERE / 'untracked-inventory.json').write_text(json.dumps(rows, indent=2) + '\n')
print(json.dumps({'untracked_files': len(rows), 'bytes': sum(r['bytes'] for r in rows),
    'extensions': dict(Counter(Path(r['path']).suffix for r in rows)),
    'largest': sorted(rows, key=lambda r: r['bytes'], reverse=True)[:20],
    'python_modules': {name: bool(importlib.util.find_spec(name)) for name in ('huggingface_hub', 'matplotlib', 'pytest')}}, indent=2))
