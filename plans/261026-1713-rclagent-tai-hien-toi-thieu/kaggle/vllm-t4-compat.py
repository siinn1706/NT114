"""One hash-bound launch-tile compatibility patch; no RCLAgent changes."""
import difflib
import hashlib
import json
from pathlib import Path

ORIGINAL_SHA256 = '8055f9dc80be1727ac9255ac8a2e565ef08e3572325e0b69e170b2249b4b789a'
OLD = b'        BLOCK_M=128,\n'
NEW = b'        BLOCK_M=64 if IS_TURING else 128,\n'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def patched_bytes(original):
    if sha(original) != ORIGINAL_SHA256:
        raise RuntimeError('Unrecognized vLLM prefix source; refusing a fuzzy patch')
    if original.count(OLD) != 1:
        raise RuntimeError('Expected exactly one non-ALiBi query tile')
    return original.replace(OLD, NEW, 1)


def apply(source, evidence):
    source, evidence = Path(source), Path(evidence)
    evidence.mkdir(parents=True, exist_ok=True)
    backup = evidence / 'prefix-prefill.original.py'
    current = source.read_bytes()
    if sha(current) == ORIGINAL_SHA256:
        original = current
    elif backup.exists() and current == patched_bytes(backup.read_bytes()):
        original = backup.read_bytes()
    else:
        raise RuntimeError('Unexpected installed source or missing original backup')
    patched = patched_bytes(original)
    backup.write_bytes(original)
    (evidence / 'vllm-t4-prefix.patch').write_text(''.join(difflib.unified_diff(
        original.decode().splitlines(True), patched.decode().splitlines(True),
        fromfile='vllm/attention/ops/prefix_prefill.py.original',
        tofile='vllm/attention/ops/prefix_prefill.py')), encoding='utf-8')
    source.write_bytes(patched)
    report = {'vllm': '0.10.2', 'source': str(source),
        'before_sha256': sha(original), 'after_sha256': sha(patched),
        'official_wheel_sha256': 'e0cba6110483d9bf25c4402d8655cf78d366dd13e4155210980cc3480ed98b7b',
        'reason': 'SM75 non-ALiBi prefix kernel requests 98304 bytes shared memory with BLOCK_M=128; T4 limit is 65536. Use 64 query rows per tile on Turing only. Grid already uses ceil(query_length/BLOCK_M); no tokens or attention terms removed.',
        'changes': {'Turing_BLOCK_M': 64, 'other_architectures_BLOCK_M': 128},
        'unchanged': ['BLOCK_N=64', 'num_stages=1', 'kernel math', 'RCLAgent source/prompt/tools', 'context and request limits']}
    (evidence / 'patch.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report
