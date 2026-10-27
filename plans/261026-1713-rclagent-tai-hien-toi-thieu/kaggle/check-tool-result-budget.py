"""Check the shipped search_logs budget on the packaged telemetry and on the request that stopped version 6.

usage: python -I -X utf8 check-tool-result-budget.py TOKENIZER_DIR

Runs smoke-worker.budget_log_result (the code path used on Kaggle) with the pinned tokenizer over every service the
re2ob system prompt lists, at every second of the packaged query window, in both timestamp forms the model sees.
Then rebuilds version 6 request 3 from its native events, first with the raw tool results (must reproduce the
recorded overflow) and then with the budgeted ones. No model, network or label is used.
"""
import csv
import hashlib
import importlib.util
import io
import json
import os
import sys
from pathlib import Path

import pandas as pd

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PACKAGE = HERE / 'runtime/package'
V6_EVENTS = HERE / 'runtime/kaggle-output-v6/rclagent-smoke/run/trace/events.jsonl'


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker = load('worker_under_check', 'smoke-worker.py')
prepare = load('prepare_bundle', 'prepare-bundle.py')
from transformers import AutoTokenizer  # noqa: E402

tokenizer = AutoTokenizer.from_pretrained(sys.argv[1], local_files_only=True)
ns, client = prepare.endpoint_module()
ns.update(os=os, DATA_ROOT=str(PACKAGE / 'input'))
ns['log_df'] = ns['_load_log_df']()  # Upstream loader, including its INFO/DEBUG filter.
window = json.loads((PACKAGE / 'selection.json').read_text())['query_window']
rows = []
for service in prepare.KNOWN_SERVICES:
    for second in range(window['start_second'], window['end_second'] + 1):
        for stamp in (str(second), str(second) + '662'):
            params = {'service_name': service, 'timestamp': stamp}
            response = client.get('/search_logs', query_string=params)
            assert response.status_code == 200
            body = response.data.decode('utf-8').replace('\r\n', '\n')  # Linux line endings as on Kaggle.
            delivered, audit = worker.budget_log_result(tokenizer, params, body)
            row = {'params': params, **{k: v for k, v in audit.items() if k != 'notice'}}
            if audit['applied']:
                original = worker.budget.parse(body)
                table = list(csv.reader(io.StringIO(delivered.split('\n', 1)[1], newline='')))
                count_column = table[0].index('count')
                row.update(notice=audit['notice'], original_rows=len(original),
                           rows_represented=sum(int(r[count_column]) for r in table[1:]))
                assert audit['condensed_tokens'] <= worker.LOG_RESULT_BUDGET
                assert row['rows_represented'] == row['original_rows'] and 'no row omitted' in audit['notice']
            else:
                assert delivered == body
            rows.append(row)

events = [json.loads(line) for line in V6_EVENTS.read_text(encoding='utf-8').splitlines()]
request = next(e for e in events if e['kind'] == 'request' and e['number'] == 2)
reply = json.loads(next(e for e in events if e['kind'] == 'response' and e['number'] == 2)['body'])['choices'][0]['message']
results = [e for e in events if e['kind'] == 'tool_result'][-len(reply['tool_calls']):]
assert [r['name'] for r in results] == [c['function']['name'] for c in reply['tool_calls']]


def request_three(transform):
    messages = request['payload']['messages'] + [{'role': 'assistant', 'content': reply['content'] or '',
                                                   'tool_calls': reply['tool_calls']}]
    for call, result in zip(reply['tool_calls'], results):
        messages.append({'role': 'tool', 'tool_call_id': call['id'], 'content': transform(result)})
    return len(tokenizer.apply_chat_template(messages, tools=request['payload']['tools'], tokenize=True,
                                             add_generation_prompt=True, enable_thinking=False))


def budgeted(result):
    if result['name'] != 'search_logs':
        return result['response']
    return worker.budget_log_result(tokenizer, result['params'], result['response'])[0]


raw_tokens = request_three(lambda r: r['response'])
assert raw_tokens == 126088, raw_tokens  # Version 6 guard: input=126088.
budget_tokens = request_three(budgeted)
assert budget_tokens + 512 <= 16384
applied = [r for r in rows if r['applied']]
report = {'status': 'pass', 'budget_tokens': worker.LOG_RESULT_BUDGET,
          'module_sha256': hashlib.sha256((HERE / 'tool-result-budget.py').read_bytes()).hexdigest(),
          'worker_sha256': hashlib.sha256((HERE / 'smoke-worker.py').read_bytes()).hexdigest(),
          'tokenizer': sys.argv[1].replace('\\', '/').split('snapshots/')[-1], 'pandas_version': pd.__version__,
          'grid': {'services': list(prepare.KNOWN_SERVICES), 'seconds': [window['start_second'], window['end_second']],
                   'queries': len(rows), 'unchanged': len(rows) - len(applied), 'condensed': len(applied),
                   'condensed_services': sorted({r['params']['service_name'] for r in applied}),
                   'max_condensed_tokens': max((r['condensed_tokens'] for r in applied), default=None),
                   'rows_omitted': sum(r['original_rows'] - r['rows_represented'] for r in applied)},
          'version6_request3': {'raw_prompt_tokens': raw_tokens, 'budgeted_prompt_tokens': budget_tokens,
                                'reserved_output': 512, 'context': 16384},
          'rows': rows}
(HERE / 'tool-result-budget-check.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, indent=2))
