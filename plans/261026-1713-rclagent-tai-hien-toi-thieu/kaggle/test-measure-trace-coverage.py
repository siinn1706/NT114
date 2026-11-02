"""CPU tests for measure-trace-coverage.py: the coverage label, server and client spans of the faulty service, the
fault-window counts, the start offset, the sealed test role and the refusal to overwrite. No model and no Kaggle is run."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, filename):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tc = load('trace_coverage_under_test', 'measure-trace-coverage.py')
INJECT = 1_000_000  # s
T0 = INJECT * 1000  # ms


def write(path, rows):
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def span(ts, service, trace, operation):
    return {'timestamp': ts, 'cmdb_id': service, 'span_id': f'{trace}-{service}-{ts}', 'trace_id': trace,
            'duration': 10, 'type': 'rpc', 'status_code': 0, 'operation_name': operation, 'parent_span': ''}


SPANS = [
    # q_server: the query trace holds a server span of emailservice
    span(T0 + 5_000, 'checkoutservice', 'q_server', 'hipstershop.EmailService/SendOrderConfirmation'),
    span(T0 + 5_001, 'emailservice', 'q_server', '/hipstershop.EmailService/SendOrderConfirmation'),
    # q_client: only a client span names emailservice
    span(T0 + 7_000, 'checkoutservice', 'q_client', 'hipstershop.EmailService/SendOrderConfirmation'),
    # q_none: no span of emailservice; starts 2 s before the injection
    span(T0 - 2_000, 'frontendservice', 'q_none', 'hipstershop.CartService/GetCart'),
    span(T0 - 1_000, 'cartservice', 'q_none', '/hipstershop.CartService/GetCart'),
    # other traces: one in the window touching emailservice, one in the window without it, one after the window
    span(T0 + 100_000, 'emailservice', 'other_in', '/hipstershop.EmailService/SendOrderConfirmation'),
    span(T0 + 200_000, 'frontendservice', 'other_plain', 'frontend'),
    span(T0 + 600_000, 'emailservice', 'other_late', '/hipstershop.EmailService/SendOrderConfirmation'),
]


class CoverageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.raw, self.queries, self.roles = d / 'raw.csv', d / 'queries.csv', d / 'roles.csv'
        write(self.raw, SPANS)
        write(self.queries, [{'case_id': 'emailservice_delay_9', 'role': 'train', 'trace_id': t}
                             for t in ('q_server', 'q_client', 'q_none')]
              + [{'case_id': 'emailservice_delay_8', 'role': 'test', 'trace_id': 'sealed'}])
        write(self.roles, [{'case_id': 'emailservice_delay_9', 'inject_ts': INJECT, 'role': 'train'},
                           {'case_id': 'emailservice_delay_9', 'inject_ts': INJECT, 'role': 'train'}])

    def tearDown(self):
        self.tmp.cleanup()

    def rows(self):
        queries = tc.read_queries(self.queries, ['train'])
        inject = tc.read_inject(self.roles, {q['case_id'] for q in queries})
        return {r['trace_id']: r for r in tc.collect(self.raw, queries, inject, chunksize=3)}

    def test_coverage_labels(self):
        rows = self.rows()
        self.assertEqual({t: r['coverage'] for t, r in rows.items()},
                         {'q_server': 'server', 'q_client': 'client_only', 'q_none': 'none'})
        self.assertEqual((rows['q_server']['gt_server_spans'], rows['q_server']['gt_client_spans']), (1, 1))
        self.assertEqual((rows['q_client']['gt_server_spans'], rows['q_client']['gt_client_spans']), (0, 1))

    def test_window_counts_and_offset(self):
        row = self.rows()['q_none']
        # in [T0, T0 + 600 s): q_server, q_client, other_in, other_plain; q_none starts before, other_late after
        self.assertEqual(row['window_traces'], 4)
        self.assertEqual(row['window_traces_touching_gt'], 3)
        self.assertEqual(row['query_start_offset_s'], -2.0)

    def test_test_role_is_refused_and_not_read(self):
        with self.assertRaises(SystemExit):
            tc.read_queries(self.queries, ['train', 'test'])
        self.assertNotIn('sealed', {q['trace_id'] for q in tc.read_queries(self.queries, ['train', 'val'])})

    def test_summary_and_no_overwrite(self):
        out = Path(self.tmp.name) / 'out'
        argv = [str(out), '--roles-allowed', 'train', '--queries', str(self.queries), '--case-roles', str(self.roles),
                '--raw-traces', str(self.raw)]
        tc.main(argv)
        summary = json.loads((out / 'summary.json').read_text(encoding='utf-8'))
        self.assertEqual(summary['by_role_and_gt']['train/emailservice'],
                         {'server': 1, 'client_only': 1, 'none': 1, 'total': 3})
        self.assertEqual(json.dumps(summary['cases_by_role']['train'], sort_keys=True),
                         '{"cases": 1, "every_query_none": 0, "some_query_none": 1}')
        with self.assertRaises(SystemExit):
            tc.main(argv)


if __name__ == '__main__':
    unittest.main()
