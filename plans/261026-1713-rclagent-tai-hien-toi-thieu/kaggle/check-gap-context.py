"""Context margin of the telemetry-gap prompt additions on the dev queries (prereg section 2, M3 context rule).

Usage: check-gap-context.py WINDOW_KPI S1_FINAL_PROMPT_MAX OUT_JSON S1_OTHER_PROMPT_MAX

Counts the M3 table and the M1/M2 lines with the pinned tokenizer, adds them to the largest final (respectively
self-state) prompt S1 v3 sent, plus the reserved output, and requires at least 1,000 tokens left of the 16,384 context.
"""
import importlib.util
import json
import sys
from pathlib import Path

from transformers import AutoTokenizer

HERE = Path(__file__).resolve().parent
TOKENIZER = HERE / 'runtime/hf-cache/models--Qwen--Qwen3-4B-Instruct-2507/snapshots/cdbee75f17c01a7cc42f958dc650907174af0554'
CONTEXT, MARGIN, FINAL_OUTPUT, SELF_OUTPUT = 16384, 1000, 1024, 512


def main(kpi_path, final_max, out, self_max):
    spec = importlib.util.spec_from_file_location('telemetry_gap', HERE / 'telemetry-gap.py')
    gap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gap)
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER, local_files_only=True)
    count = lambda text: len(tokenizer(text, add_special_tokens=False)['input_ids'])
    queries = json.loads(Path(kpi_path).read_text(encoding='utf-8'))['queries']
    table = max(count('\n' + gap.window_table(k) + '\n') for k in queries.values())
    lines = count(gap.M1_LINE + gap.M2_LINE)
    report = {'context': CONTEXT, 'required_margin': MARGIN, 'max_table_tokens': table, 'm1_m2_line_tokens': lines,
              'final': {'s1_v3_max_prompt': final_max, 'reserved_output': FINAL_OUTPUT,
                        'margin': CONTEXT - final_max - table - FINAL_OUTPUT},
              'self_state': {'s1_v3_max_prompt': self_max, 'reserved_output': SELF_OUTPUT,
                             'margin': CONTEXT - self_max - lines - SELF_OUTPUT}}
    report['passed'] = min(report['final']['margin'], report['self_state']['margin']) >= MARGIN
    Path(out).write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(report))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]))
