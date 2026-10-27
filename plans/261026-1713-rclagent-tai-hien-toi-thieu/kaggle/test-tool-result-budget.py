"""CPU tests for the search_logs tool-result budget, as module and through the worker's tool wrapper.

A character-based tokenizer fixture stands in for Qwen; the pinned tokenizer is exercised by
check-tool-result-budget.py on the packaged telemetry and the version 6 request.
"""
import csv
import importlib.util
import io
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CODE = Path('F:/Nam/UIT/nt114-paper-artifacts/W7165616276/code')
spec = importlib.util.spec_from_file_location('worker_budget_test', HERE / 'smoke-worker.py')
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
budget = worker.budget
BUDGET = worker.LOG_RESULT_BUDGET
SECOND = 1700000000
HEADER = 'log_id,timestamp,cmdb_id,log_name,value\n'


class ThirdTokenizer:
    """About three characters per token, like CSV log text under the Qwen tokenizer."""
    def __call__(self, text, add_special_tokens=False):
        return {'input_ids': [0] * ((len(text) + 2) // 3)}

    def apply_chat_template(self, messages, **kwargs):
        return [0] * 100


def csv_body(rows):
    out = io.StringIO()
    writer = csv.writer(out, lineterminator='\n')
    writer.writerow(['log_id', 'timestamp', 'cmdb_id', 'log_name', 'value'])
    writer.writerows([f'fixture_{i}', ts, service, 'log_' + service, value] for i, (ts, service, value) in enumerate(rows))
    return out.getvalue()


def cart_rows(n):
    return [(SECOND - 60 + i % 121, 'cartservice', 'severity: unknown, message: GetCartAsync called with userId=' +
             str(uuid.uuid5(uuid.NAMESPACE_URL, str(i % 50)))) for i in range(n)]


def shown_table(text):
    return list(csv.reader(io.StringIO(text.split('\n', 1)[1], newline='')))


def run(params, body):
    return worker.budget_log_result(ThirdTokenizer(), params, body)


PARAMS = {'service_name': 'cartservice', 'timestamp': str(SECOND) + '662'}


class BudgetRules(unittest.TestCase):
    def test_results_within_budget_pass_byte_for_byte(self):
        for body in (HEADER, '{"message":"No matching records found."}\n', csv_body(cart_rows(3)),
                     'x' * (3 * BUDGET)):  # Exactly at budget under the fixture tokenizer.
            delivered, audit = run(PARAMS, body)
            self.assertIs(delivered, body)
            self.assertFalse(audit['applied'])

    def test_repetitive_service_log_is_merged_by_template_without_dropping_rows(self):
        body = csv_body(cart_rows(1500))
        delivered, audit = run(PARAMS, body)
        self.assertTrue(audit['applied'])
        self.assertLessEqual(audit['condensed_tokens'], BUDGET)
        self.assertIn('1500 rows merged into 1 message templates', audit['notice'])
        self.assertIn('no row omitted', audit['notice'])
        table = shown_table(delivered)
        self.assertEqual(table[0], budget.TEMPLATE_HEADER)
        self.assertEqual(table[1][3], 'GetCartAsync called with userId=<*>')
        self.assertEqual((int(table[1][4]), int(table[1][7])), (1500, 50))
        self.assertEqual((int(table[1][5]), int(table[1][6])), (SECOND - 60, SECOND + 60))

    def test_duplicate_errors_are_kept_verbatim_with_counts(self):
        rows = [(SECOND, 'frontend', 'severity: error, message: request error')] * 400 + \
               [(SECOND + 1, 'frontend', 'severity: unknown, message: env platform is either empty or invalid')] * 300
        delivered, audit = run(PARAMS, csv_body(rows))
        self.assertIn('identical (cmdb_id, log_name, value) entries', audit['notice'])
        table = shown_table(delivered)
        self.assertEqual(table[1], ['frontend', 'log_frontend', 'severity: error, message: request error', '400',
                                    str(SECOND), str(SECOND)])
        self.assertEqual(sum(int(r[3]) for r in table[1:]), 700)

    def test_truncation_keeps_errors_first_and_says_so(self):
        letters = 'abcdefghijklmnopqrstuvwxyz'
        words = [a + b + c for a in letters for b in letters for c in letters[:4]]
        rows = [(SECOND + 30, 'svc', f'severity: unknown, message: background job {w} finished') for w in words[:1500]]
        rows += [(SECOND + 50, 'svc', f'severity: error, message: request failed in {w}') for w in words[1500:1510]]
        delivered, audit = run(PARAMS, csv_body(rows))
        self.assertIn('truncated:', audit['notice'])
        self.assertIn('omitted rows by severity: unknown=', audit['notice'])
        self.assertNotIn('error=', audit['notice'])
        shown = shown_table(delivered)[1:]
        self.assertEqual(sum(r[2] == 'error' for r in shown), 10)
        self.assertLessEqual(audit['condensed_tokens'], BUDGET)

    def test_deterministic_output(self):
        body = csv_body(cart_rows(900) + [(SECOND, 'cartservice', 'severity: error, message: Redis timeout 42')])
        self.assertEqual(run(PARAMS, body), run(PARAMS, body))

    def test_unrecognised_or_unanchored_large_results_stop_instead_of_guessing(self):
        with self.assertRaises(ValueError):
            run(PARAMS, 'not,the,author,csv\n' + 'x' * (4 * BUDGET))
        with self.assertRaises(ValueError):
            run({'service_name': 'cartservice', 'timestamp': 'noon'}, csv_body(cart_rows(1500)))


class LargeTelemetry(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        body = csv_body(cart_rows(1500)) if self.path.startswith('/search_logs') else 'key,regular_mean\n' + 'x' * 20000
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body.encode())


class WorkerWrapper(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(('127.0.0.1', 5000), LargeTelemetry)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.area = tempfile.TemporaryDirectory(dir=HERE / 'runtime')
        selection = {'query_window': {'start_second': SECOND, 'end_second': SECOND + 1}}
        self.guard = worker.Guard(self.area.name, selection, ThirdTokenizer(), 16384, 'trace', time.monotonic() + 60)
        for name in ('config', 'llm', 'coordinator', 'tools_gpt'):
            sys.modules.pop(name, None)
        os.environ.update(LLM_API_KEY='local-placeholder', LLM_MODEL='fixture', TOOL_SERVER_HOST='127.0.0.1',
                          LLM_API_URL='http://127.0.0.1:8000/v1/chat/completions',
                          TOOL_SERVER_PORT='5000', MAX_AGENT_PARALLEL='1', DATASET_TYPE='re2ob')
        self.coordinator, _, _ = worker.install_guards(self.guard, CODE)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.guard.session.close()
        self.area.cleanup()

    def events(self):
        return [json.loads(line) for line in (Path(self.area.name) / 'events.jsonl').read_text().splitlines()]

    def test_upstream_tool_call_receives_condensed_logs_and_audit_keeps_original(self):
        delivered = self.coordinator._get('search_logs', PARAMS)
        self.assertTrue(delivered.startswith('[harness tool-result budget 2048 tokens: 1500 rows merged'))
        raw = next(e for e in self.events() if e['kind'] == 'tool_result')
        audit = next(e for e in self.events() if e['kind'] == 'tool_result_budget')
        self.assertEqual(raw['response'], csv_body(cart_rows(1500)))
        self.assertTrue(audit['applied'])
        self.assertEqual(audit['delivered'], delivered)
        self.assertEqual(audit['original_bytes'], len(raw['response'].encode()))

    def test_metric_results_are_never_budgeted(self):
        delivered = self.coordinator._get('search_fluctuating_metrics', PARAMS)
        self.assertEqual(delivered, 'key,regular_mean\n' + 'x' * 20000)
        self.assertFalse(any(e['kind'] == 'tool_result_budget' for e in self.events()))

    def test_unfittable_result_is_a_harness_stop(self):
        original = worker.budget.apply
        worker.budget.apply = lambda *args: None
        try:
            with self.assertRaises(worker.HarnessStop):
                self.coordinator._get('search_logs', PARAMS)
        finally:
            worker.budget.apply = original
        self.assertIn('Tool-result budget', self.guard.fatal)


if __name__ == '__main__':
    unittest.main(verbosity=2)
