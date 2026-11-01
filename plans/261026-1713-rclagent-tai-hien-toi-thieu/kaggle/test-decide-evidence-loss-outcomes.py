"""CPU tests for decide-evidence-loss-outcomes.py: every outcome-sentence predicate on synthetic runs.csv rows, the n >= 3
feasibility gate, the ranking by (k/n, k) with ties kept, the variants (calibration case, one fault service left out, the
run that stopped early), the checks of the predictions, the command line, and a gate that regenerates the three CSVs from
the real S1 v2 analysis and compares them byte for byte with the ones kept in runtime/. No model and no Kaggle is run."""
import contextlib
import csv
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dec = load('decide_evidence_loss_under_test', 'decide-evidence-loss-outcomes.py')
ABSENT, NOT_QUERIED, QUERIED = 'S0_gt_span_absent', 'S0_gt_span_present_not_queried', 'S0_queried'
SENTENCE_ORDER = ['S0_gt_span_absent', 'S0_gt_span_present_not_queried', 'S2_root_label_lost_hit_kept',
                  'S4_inputs_present_not_rank1', 'label_mismatch_flags']


def run(unit, case=None, seq=1, condition='metric', completed='true', s0=QUERIED, span=1, i0='true', i1='true',
        i2='true', i3='true', i4='true', d1='false', **extra):
    """One runs.csv row (strings, as the analyzer writes them) of the fault service `unit`."""
    case = case or unit + '-case'
    row = {'run_id': f'{case}--{condition}--s{seq}', 'case': case, 'condition': condition, 'completed': completed,
           'gt_service': unit, 'gt_span_in_trace': str(span), 's0_label': s0, 'I0': i0, 'I1': i1, 'I2': i2,
           'I2_lenient': i2, 'I3': i3, 'I4': i4, 'D1': d1, 'queried_gt': 'true', 'empty_reason_set': '',
           'table_received': 'true', 'hit_without_evidence': 'false'}
    row.update(extra)
    return row


def detail(rows, sentence, extra=()):
    return dec.sentences(rows, extra)[sentence]


def table(rows, extra=()):
    out = []
    ranked = dec.outcome_table('v', rows, out, extra)
    return {r['sentence']: r for r in out}, ranked


class SentencePredicateTest(unittest.TestCase):
    def test_absent_needs_one_case_where_every_run_is_absent(self):
        rows = [run('u', 'c1', 1, s0=ABSENT, span=0), run('u', 'c1', 2, s0=QUERIED),
                run('u', 'c2', 1, s0=ABSENT, span=0), run('u', 'c2', 2, s0=ABSENT, span=0)]
        self.assertEqual(detail(rows, 'S0_gt_span_absent'), {'u': (True, '3/4')})
        self.assertEqual(detail(rows[:2], 'S0_gt_span_absent'), {'u': (False, '1/2')})

    def test_incomplete_runs_do_not_count(self):
        rows = [run('u', 'c1', 1, s0=ABSENT, span=0), run('u', 'c1', 2, completed='false', s0=QUERIED)]
        self.assertEqual(detail(rows, 'S0_gt_span_absent'), {'u': (True, '1/1')})
        self.assertEqual(dec.sentences([run('u', completed='false')], ())['S0_gt_span_absent'], {})

    def test_present_not_queried_ignores_runs_without_gt_span(self):
        rows = [run('u', 'c1', 1, s0=NOT_QUERIED, span=2), run('u', 'c1', 2, s0=NOT_QUERIED, span=1),
                run('u', 'c2', 1, s0=ABSENT, span=0), run('v', 'c3', 1, s0=ABSENT, span=0)]
        result = detail(rows, 'S0_gt_span_present_not_queried')
        self.assertEqual(result, {'u': (True, '2/2')})
        self.assertNotIn('v', result)

    def test_present_not_queried_not_met_when_a_run_queried(self):
        rows = [run('u', 'c1', 1, s0=NOT_QUERIED), run('u', 'c1', 2, s0=QUERIED)]
        self.assertEqual(detail(rows, 'S0_gt_span_present_not_queried'), {'u': (False, '1/2')})

    def test_root_label_lost_hit_kept(self):
        rows = [run('a', 'c', 1, i2='false', i4='true'), run('a', 'c', 2, i2='false', i4='false'),
                run('b', 'c', 1, i2='false', i4='false'),
                run('c', 'c', 1, i2='true', i4='true'),
                run('d', 'c', 1, i0='false', i2='false', i4='true'),
                run('e', 'c', 1, i1='false', i2='false', i4='true')]
        self.assertEqual(detail(rows, 'S2_root_label_lost_hit_kept'), {'a': (True, '1/2'), 'b': (False, '0/1')})

    def test_inputs_present_not_rank_one(self):
        rows = [run('a', 'c', 1, i4='false'), run('a', 'c', 2, i4='true'),
                run('b', 'c', 1, i4='true'),
                run('c', 'c', 1, i3='false', i4='false'),
                run('d', 'c', 1, i1='false', i4='false'),
                run('e', 'c', 1, i0='false', i4='false')]
        self.assertEqual(detail(rows, 'S4_inputs_present_not_rank1'),
                         {'a': (True, '1/2'), 'b': (False, '0/1'), 'c': (False, '0/1'), 'd': (False, '0/1')})

    def test_label_mismatch_compares_failure_rates_inside_a_case(self):
        worse = [run('a', 'c', 1, d1='true', i4='false'), run('a', 'c', 2, i4='true')]
        self.assertEqual(detail(worse, 'label_mismatch_flags'), {'a': (True, 'case c: D1 trượt 1/1; không D1 trượt 0/1')})
        equal = [run('a', 'c', 1, d1='true', i4='false'), run('a', 'c', 2, i4='false')]
        self.assertFalse(detail(equal, 'label_mismatch_flags')['a'][0])
        better = [run('a', 'c', 1, d1='true', i4='true'), run('a', 'c', 2, i4='false')]
        self.assertFalse(detail(better, 'label_mismatch_flags')['a'][0])

    def test_label_mismatch_needs_both_groups_in_one_case(self):
        rows = [run('a', 'c1', 1, d1='true', i4='false'), run('a', 'c2', 1, i4='true')]
        self.assertEqual(detail(rows, 'label_mismatch_flags'), {})

    def test_label_mismatch_ignores_runs_without_evidence(self):
        rows = [run('a', 'c', 1, d1='true', i4='false', i0='false'), run('a', 'c', 2, i4='true')]
        self.assertEqual(detail(rows, 'label_mismatch_flags'), {})

    def test_label_mismatch_keeps_the_last_case_in_case_order(self):
        rows = [run('a', 'c1', 1, d1='true', i4='false'), run('a', 'c1', 2, i4='true'),
                run('a', 'c2', 1, d1='true', i4='true'), run('a', 'c2', 2, i4='false')]
        self.assertEqual(detail(rows, 'label_mismatch_flags'), {'a': (False, 'case c2: D1 trượt 0/1; không D1 trượt 1/1')})

    def test_cases_are_taken_in_case_order_whatever_the_input_order(self):
        rows = [run('a', 'c2', 1, d1='true', i4='true'), run('a', 'c2', 2, i4='false'),
                run('a', 'c1', 1, d1='true', i4='false'), run('a', 'c1', 2, i4='true')]
        self.assertEqual(detail(rows, 'label_mismatch_flags'), {'a': (False, 'case c2: D1 trượt 0/1; không D1 trượt 1/1')})

    def test_label_mismatch_compares_rates_not_counts(self):
        rows = [run('a', 'c', 1, d1='true', i4='false'), run('a', 'c', 2, d1='true', i4='false'),
                run('a', 'c', 3, d1='true', i4='true'), run('a', 'c', 4, i4='false')]
        self.assertEqual(detail(rows, 'label_mismatch_flags'), {'a': (False, 'case c: D1 trượt 2/3; không D1 trượt 1/1')})

    def test_present_not_queried_holds_when_one_case_is_all_not_queried(self):
        rows = [run('u', 'c1', 1, s0=NOT_QUERIED), run('u', 'c2', 1, s0=NOT_QUERIED), run('u', 'c2', 2, s0=QUERIED)]
        self.assertEqual(detail(rows, 'S0_gt_span_present_not_queried'), {'u': (True, '2/3')})

    def test_present_not_queried_drops_runs_without_gt_span_before_grouping(self):
        rows = [run('u', 'c1', 1, s0=NOT_QUERIED, span=1), run('u', 'c1', 2, s0=QUERIED, span=0)]
        self.assertEqual(detail(rows, 'S0_gt_span_present_not_queried'), {'u': (True, '1/1')})

    def test_inputs_present_not_rank_one_leaves_runs_without_evidence_out_of_the_unit(self):
        rows = [run('a', 'c', 1, i0='false', i4='false'), run('a', 'c', 2, i4='true')]
        self.assertEqual(detail(rows, 'S4_inputs_present_not_rank1'), {'a': (False, '0/1')})


class FeasibilityGateTest(unittest.TestCase):
    @staticmethod
    def hits(units):
        return [run(u, i4='false') for u in units]

    def test_two_units_is_not_testable(self):
        rows, ranked = table(self.hits('ab'))
        row = rows['S4_inputs_present_not_rank1']
        self.assertEqual((row['n_units'], row['k_units'], row['status']), (2, 2, 'not_testable'))
        self.assertEqual(ranked, [])

    def test_three_units_is_testable(self):
        rows, ranked = table(self.hits('abc'))
        row = rows['S4_inputs_present_not_rank1']
        self.assertEqual((row['n_units'], row['k_units'], row['status']), (3, 3, '3/3'))
        self.assertEqual([(k, n, name) for _, k, name, n in ranked], [(3, 3, 'S4_inputs_present_not_rank1')])

    def test_a_testable_sentence_without_support_is_not_ranked(self):
        rows, ranked = table([run(u, i4='true') for u in 'abc'])
        self.assertEqual(rows['S4_inputs_present_not_rank1']['status'], '0/3')
        self.assertEqual(ranked, [])

    def test_unit_lists_and_run_counts(self):
        rows, _ = table([run('a', i4='false'), run('b', i4='true'), run('c', i4='false')])
        row = rows['S4_inputs_present_not_rank1']
        self.assertEqual((row['supporting_units'], row['non_supporting_units']), ('a;c', 'b'))
        self.assertEqual(row['per_unit_runs_supporting_over_with_data'], 'a=1/1;b=0/1;c=1/1')

    def test_empty_input_yields_every_sentence_not_testable(self):
        rows, ranked = table([])
        self.assertEqual(list(rows), SENTENCE_ORDER)
        self.assertEqual({r['status'] for r in rows.values()}, {'not_testable'})
        self.assertEqual(ranked, [])


class RankingTest(unittest.TestCase):
    @staticmethod
    def world():
        """Four units. S0 absent 3/4, S4 3/4 (a tie), S2 1/3, present_not_queried 0/4, label_mismatch n = 0."""
        return [run('a', s0=ABSENT, i2='false', i4='false'), run('a', seq=2, s0=ABSENT, i2='false', i4='true'),
                run('b', s0=ABSENT, i2='false', i4='false'), run('c', s0=ABSENT, i2='false', i4='false'),
                run('d', s0=QUERIED, i2='true', i4='true')]

    def test_equal_pairs_share_a_rank_and_keep_the_definition_order(self):
        out = []
        ranked = dec.outcome_table(dec.LABEL_MAIN, self.world(), out)
        dec.outcome_table(dec.LABEL_ALL8, self.world(), out)
        rows = dec.direction_rows(out, ranked)
        self.assertEqual([(r[0], r[1], r[2], r[3]) for r in rows],
                         [(1, 'S0_gt_span_absent', 3, 4), (1, 'S4_inputs_present_not_rank1', 3, 4),
                          (3, 'S2_root_label_lost_hit_kept', 1, 3), ('', 'label_mismatch_flags', '', 0),
                          ('', 'S0_gt_span_present_not_queried', 0, 4)])

    def test_k_breaks_a_tie_of_k_over_n(self):
        # S4 holds for 3 of 6 units, S2 for 2 of 4 units, both 1/2; S2 is defined first and still ranks second.
        rows = [run('u0', i2='false', i4='false'), run('u0', seq=2, i2='false', i4='true'),
                run('u1', i2='false', i4='false'), run('u1', seq=2, i2='false', i4='true'),
                run('u2', i2='false', i4='false'), run('u3', i2='false', i3='false', i4='false'),
                run('u4'), run('u5')]
        out = []
        ranked = dec.outcome_table('v', rows, out)
        by_name = {name: (k, n) for _, k, name, n in ranked}
        self.assertEqual(by_name['S4_inputs_present_not_rank1'], (3, 6))
        self.assertEqual(by_name['S2_root_label_lost_hit_kept'], (2, 4))
        self.assertEqual([name for _, _, name, _ in ranked], ['S4_inputs_present_not_rank1', 'S2_root_label_lost_hit_kept'])

    def test_a_higher_ratio_beats_a_higher_k(self):
        # S4: 3 of 3 units (1); S0: 3 of 4 units (3/4).
        rows = [run(u, s0=ABSENT, i4='false') for u in 'abc'] + [run('d', s0=QUERIED, i4='true')]
        rows[3]['I0'] = 'false'
        out = []
        ranked = dec.outcome_table('v', rows, out)
        self.assertEqual([(name, k, n) for _, k, name, n in ranked],
                         [('S4_inputs_present_not_rank1', 3, 3), ('S0_gt_span_absent', 3, 4)])

    def test_not_testable_rows_come_before_zero_support_rows(self):
        out = []
        ranked = dec.outcome_table(dec.LABEL_MAIN, self.world(), out)
        dec.outcome_table(dec.LABEL_ALL8, self.world(), out)
        names = [r[1] for r in dec.direction_rows(out, ranked)]
        self.assertEqual(names[-2:], ['label_mismatch_flags', 'S0_gt_span_present_not_queried'])

    def test_direction_text_carries_the_counts(self):
        out = []
        ranked = dec.outcome_table(dec.LABEL_MAIN, self.world(), out)
        dec.outcome_table(dec.LABEL_ALL8, self.world(), out)
        rows = {r[1]: r for r in dec.direction_rows(out, ranked)}
        self.assertEqual(rows['label_mismatch_flags'][7],
                         'not_testable (n = 0 bang chinh; n = 0 o 8 case); khong co du lieu nhat quan de xep hang')
        self.assertEqual(rows['S0_gt_span_present_not_queried'][7], 'khong co du lieu nhat quan (k = 0)')

    def ranks_of(self, ranked):
        out = []
        dec.outcome_table(dec.LABEL_MAIN, self.world(), out)
        dec.outcome_table(dec.LABEL_ALL8, self.world(), out)
        return [r[0] for r in dec.direction_rows(out, ranked)][:len(ranked)]

    def test_a_pair_shares_a_rank_only_when_both_k_over_n_and_k_are_equal(self):
        same_k = [(Fraction(3, 4), 3, 'S0_gt_span_absent', 4), (Fraction(3, 6), 3, 'S4_inputs_present_not_rank1', 6)]
        self.assertEqual(self.ranks_of(same_k), [1, 2])
        same_ratio = [(Fraction(2, 4), 2, 'S0_gt_span_absent', 4), (Fraction(1, 2), 1, 'S4_inputs_present_not_rank1', 2)]
        self.assertEqual(self.ranks_of(same_ratio), [1, 2])
        same_both = [(Fraction(3, 4), 3, 'S0_gt_span_absent', 4), (Fraction(3, 4), 3, 'S4_inputs_present_not_rank1', 4)]
        self.assertEqual(self.ranks_of(same_both), [1, 1])


class VariantTest(unittest.TestCase):
    @staticmethod
    def corpus():
        rows = []
        for u in dec.FAULT_SERVICES:
            rows.append(run(u, case=u + '-c', s0=ABSENT, span=0, i4='false'))
        rows.append(run('checkoutservice', case=dec.CALIBRATION_CASE, s0=ABSENT, span=0, i4='false'))
        rows.append(run('checkoutservice', case=dec.CALIBRATION_CASE, condition='metric_no_log', s0=QUERIED))
        rows.append(run('checkoutservice', case=dec.CALIBRATION_CASE, condition='no_metric', s0=QUERIED))
        return rows

    def variants(self):
        rows, ranks = dec.outcome_variants(self.corpus(), self.corpus())
        by = {}
        for r in rows:
            by.setdefault(r['variant'], {})[r['sentence']] = r
        return rows, ranks, by

    def test_variant_order_and_row_count(self):
        rows, ranks, _ = self.variants()
        seen = []
        for r in rows:
            if r['variant'] not in seen:
                seen.append(r['variant'])
        self.assertEqual(seen[:4], [dec.LABEL_MAIN, dec.LABEL_ALL8, 'r2 main (bo 99f095)', 'r2 all8'])
        self.assertEqual(seen[4:12], [f'{prefix} {u}' for u in dec.FAULT_SERVICES
                                      for prefix in ('main bo dich vu GT', 'all8 bo dich vu GT')])
        self.assertEqual(len(seen), 14)
        self.assertEqual(len(rows), 14 * len(SENTENCE_ORDER))
        self.assertEqual(list(ranks), ['main', 'all8', 'r2_main', 'r2_all8'] + [p + u for u in dec.FAULT_SERVICES
                                                                                  for p in ('loo_', 'loo8_')] + ['cens_worst', 'cens_best'])

    def test_calibration_case_is_dropped_from_the_main_table_only(self):
        _, _, by = self.variants()
        per_unit = lambda v: dict(p.split('=') for p in by[v]['S0_gt_span_absent']['per_unit_runs_supporting_over_with_data'].split(';'))
        self.assertEqual(per_unit(dec.LABEL_MAIN)['checkoutservice'], '1/1')
        self.assertEqual(per_unit(dec.LABEL_ALL8)['checkoutservice'], '2/2')

    def test_only_the_metric_condition_is_read(self):
        _, _, by = self.variants()
        self.assertEqual(by[dec.LABEL_ALL8]['S0_gt_span_absent']['per_unit_runs_supporting_over_with_data'].count('='), 4)
        self.assertEqual(by[dec.LABEL_ALL8]['S0_gt_span_absent']['k_units'], 4)

    def test_leaving_a_service_out_removes_its_unit(self):
        _, _, by = self.variants()
        row = by['main bo dich vu GT emailservice']['S0_gt_span_absent']
        self.assertEqual((row['n_units'], row['non_supporting_units'], row['supporting_units']),
                         (3, '', 'checkoutservice;currencyservice;recommendationservice'))

    def test_the_run_that_stopped_early_is_filled_with_both_readings(self):
        corpus = [run(u, i2='false', i4='false') for u in 'abc']
        corpus.append(run('d', completed='false', i1='NA', i2='NA', i3='NA', i4='NA'))
        _, ranks = dec.outcome_variants(corpus, corpus)
        as_dict = lambda key: {r[2]: (r[1], r[3]) for r in ranks[key]}
        self.assertEqual(as_dict('main'), {'S4_inputs_present_not_rank1': (3, 3)})
        # I4 false for the early-stopped run: S4 holds for its unit too; S2 gets a fourth unit that does not hold.
        self.assertEqual(as_dict('cens_worst'), {'S4_inputs_present_not_rank1': (4, 4)})
        # I4 true: S4 does not hold for it, S2 holds for it.
        self.assertEqual(as_dict('cens_best'), {'S4_inputs_present_not_rank1': (3, 4), 'S2_root_label_lost_hit_kept': (1, 4)})

    def test_the_early_stopped_run_is_not_counted_without_a_scenario(self):
        corpus = [run(u) for u in 'abc'] + [run('d', completed='false')]
        rows, _ = dec.outcome_variants(corpus, corpus)
        main = {r['sentence']: r for r in rows if r['variant'] == dec.LABEL_MAIN}
        self.assertEqual(main['S4_inputs_present_not_rank1']['n_units'], 3)

    def test_the_second_round_is_read_from_its_own_rows(self):
        s1 = [run(u, s0=ABSENT, span=0) for u in 'abc']
        r2 = [run(u, s0=QUERIED) for u in 'abc']
        rows, _ = dec.outcome_variants(s1, r2)
        by = {(r['variant'], r['sentence']): r for r in rows}
        self.assertEqual(by[(dec.LABEL_MAIN, 'S0_gt_span_absent')]['k_units'], 3)
        self.assertEqual(by[('r2 main (bo 99f095)', 'S0_gt_span_absent')]['k_units'], 0)
        self.assertEqual(by[(dec.LABEL_ALL8, 'S0_gt_span_absent')]['k_units'], 3)
        self.assertEqual(by[('r2 all8', 'S0_gt_span_absent')]['k_units'], 0)

    def test_the_early_stop_scenarios_ignore_an_incomplete_run_of_the_calibration_case(self):
        corpus = [run(u, i2='false', i4='false') for u in 'abc']
        corpus.append(run('d', case=dec.CALIBRATION_CASE, completed='false', i1='NA', i2='NA', i3='NA', i4='NA'))
        _, ranks = dec.outcome_variants(corpus, corpus)
        for key in ('cens_worst', 'cens_best'):
            self.assertEqual(ranks[key], ranks['main'])


class PredictionTest(unittest.TestCase):
    @staticmethod
    def spans(run_id, abnormal, total, gt=0):
        rows = [{'run_id': run_id, 'table_has_gt_kpi': 'true', 'is_gt_span': 'true', 'self_is_abnormal': 'true'}
                for _ in range(abnormal)]
        rows += [{'run_id': run_id, 'table_has_gt_kpi': 'true', 'is_gt_span': 'false', 'self_is_abnormal': 'false'}
                 for _ in range(total - abnormal)]
        return rows

    def corpus(self):
        runs = [run('a', case='c1', i2='false', i4='false', d1='true'), run('a', case='c1', seq=2, i2='false', i4='true'),
                run('b', case='c2', i4='true'),
                run('x', case='c3', condition='no_metric', i0='false', i4='true', table_received='false',
                    empty_reason_set='absent_source', hit_without_evidence='true'),
                run('x', case='c3', seq=2, condition='no_metric', i0='false', i4='false', table_received='false',
                    empty_reason_set='absent_source')]
        spans = self.spans(runs[0]['run_id'], 3, 4) + self.spans(runs[2]['run_id'], 2, 2)
        return runs, spans

    def predictions(self, runs, spans):
        return {r[0]: r for r in dec.prediction_rows(runs, spans)}

    def test_numbers_are_recomputed_from_the_rows(self):
        runs, spans = self.corpus()
        p = self.predictions(runs, spans)
        self.assertEqual([r for r in p], ['P1', 'P2', 'P3', 'P4', 'P5'])
        self.assertEqual(p['P1'][3], '2/2 run hoan tat bang chinh (2/2 o 8 case) I0 sai; table_received sai 2/2 (2/2 o 8 case); '
                                     '2/2 run bang chinh (2/2 o 8 case) co hoi GT chi co absent_source')
        self.assertEqual(p['P2'][3], 'span mang bang chua khoa GT, run hoan tat bang chinh 5/6 (8 case 5/6); '
                                     'span cua dich vu GT trong trace 5/5 (8 case 5/5)')
        self.assertEqual(p['P3'][3], 'I2 dung 1/3 Ev bang chinh (8 case 1/3); do nhay I2_lenient 1/3 (8 case 1/3)')
        self.assertEqual(p['P5'][3], '1/2 run hoan tat bang chinh dung R@1, ca 1 la hit_without_evidence (8 case 1/2, ca 1)')
        self.assertTrue(all(p[k][4].startswith('supported') for k in p))

    def test_p4_names_the_single_case_that_carries_the_flag(self):
        runs, spans = self.corpus()
        p = self.predictions(runs, spans)
        self.assertEqual(p['P4'][4], 'supported (hep: ca 1 run D1 thuoc c1, trong case khong testable)')

    def test_p4_is_refuted_when_the_right_runs_carry_the_flag_as_often(self):
        runs, spans = self.corpus()
        runs[1]['D1'] = runs[2]['D1'] = 'true'
        self.assertEqual(self.predictions(runs, spans)['P4'][4], 'refuted')

    def test_p4_without_runs_that_got_it_right_does_not_divide_by_zero(self):
        runs, spans = self.corpus()
        for r in runs[:3]:
            r['I4'] = 'false'
        numbers = self.predictions(runs, spans)['P4'][3]
        self.assertTrue(numbers.startswith('metric bang chinh hoan tat: D1 1/3 run truot so voi 0/0 run dung'), numbers)

    def test_p1_is_refuted_by_a_table_that_arrived(self):
        runs, spans = self.corpus()
        runs[3]['table_received'] = 'true'
        self.assertEqual(self.predictions(runs, spans)['P1'][4], 'refuted')

    def test_p1_is_refuted_by_another_empty_reason(self):
        runs, spans = self.corpus()
        runs[4]['empty_reason_set'] = 'no_rows'
        self.assertEqual(self.predictions(runs, spans)['P1'][4], 'refuted')

    def test_p2_needs_more_than_half(self):
        runs, _ = self.corpus()
        spans = self.spans(runs[0]['run_id'], 2, 4)
        self.assertEqual(self.predictions(runs, spans)['P2'][4], 'refuted')
        self.assertEqual(self.predictions(runs, self.spans(runs[0]['run_id'], 3, 4))['P2'][4], 'supported')

    def test_p3_is_refuted_at_half_and_notes_a_lenient_flip(self):
        runs, spans = self.corpus()
        self.assertEqual(self.predictions(runs, spans)['P3'][4], 'supported theo I2 dong bang')
        for r in runs[:3]:
            r['I2_lenient'] = 'true'
        self.assertEqual(self.predictions(runs, spans)['P3'][4], 'supported theo I2 dong bang; se bi bac theo I2_lenient')
        runs[0]['I2'] = runs[1]['I2'] = 'true'
        self.assertEqual(self.predictions(runs, spans)['P3'][4], 'refuted')

    def test_p5_is_refuted_without_a_hit_without_evidence(self):
        runs, spans = self.corpus()
        runs[3]['hit_without_evidence'] = 'false'
        self.assertEqual(self.predictions(runs, spans)['P5'][4], 'refuted')

    def test_the_calibration_case_is_in_the_all_case_numbers_only(self):
        runs, spans = self.corpus()
        runs.append(run('x', case=dec.CALIBRATION_CASE, condition='no_metric', i0='false', table_received='false',
                        empty_reason_set='absent_source', i4='false'))
        p = self.predictions(runs, spans)
        self.assertIn('2/2 run hoan tat bang chinh (3/3 o 8 case) I0 sai', p['P1'][3])

    def test_p1_is_refuted_by_a_run_with_evidence(self):
        runs, spans = self.corpus()
        runs[3]['I0'] = 'true'
        self.assertEqual(self.predictions(runs, spans)['P1'][4], 'refuted')

    def test_p1_ignores_the_empty_reason_of_an_unfinished_run(self):
        runs, spans = self.corpus()
        runs.append(run('x', case='c3', seq=3, condition='no_metric', completed='false',
                        table_received='false', empty_reason_set='no_rows'))
        self.assertEqual(self.predictions(runs, spans)['P1'][4], 'supported')

    def test_p1_gives_the_main_table_figure_of_table_received_first(self):
        runs, spans = self.corpus()
        runs.append(run('x', case=dec.CALIBRATION_CASE, condition='no_metric', i0='false', table_received='false',
                        empty_reason_set='absent_source', i4='false'))
        self.assertIn('table_received sai 2/2 (3/3 o 8 case);', self.predictions(runs, spans)['P1'][3])

    def test_p4_follows_the_flag_over_all_runs_not_over_the_evidence_runs(self):
        runs = [run('a', case='c1', i0='false', i4='false', d1='true'), run('a', case='c1', seq=2, i4='false'),
                run('a', case='c1', seq=3, i4='true')]
        self.assertTrue(self.predictions(runs, [])['P4'][4].startswith('supported'))

    def test_p4_without_runs_that_got_it_right_is_supported(self):
        runs, spans = self.corpus()
        for r in runs[:3]:
            r['I4'] = 'false'
        self.assertTrue(self.predictions(runs, spans)['P4'][4].startswith('supported'))

    def test_p4_has_no_note_when_two_cases_carry_the_flag(self):
        runs, spans = self.corpus()
        runs.append(run('b', case='c9', seq=1, i4='false', d1='true'))
        self.assertEqual(self.predictions(runs, spans)['P4'][4], 'supported')

    def test_p4_refuted_stays_plain_when_one_case_carries_the_flag(self):
        runs, spans = self.corpus()
        runs[1]['D1'] = 'true'
        runs.append(run('a', case='c1', seq=3, i4='false'))
        self.assertEqual(self.predictions(runs, spans)['P4'][4], 'refuted')

    def test_p4_note_counts_the_missed_runs_with_the_flag_over_all_runs(self):
        runs, spans = self.corpus()
        runs[0]['I0'] = 'false'
        self.assertEqual(self.predictions(runs, spans)['P4'][4], 'supported (hep: ca 1 run D1 thuoc c1, trong case khong testable)')

    def test_p3_is_refuted_at_exactly_half_and_notes_a_lenient_half(self):
        runs, spans = self.corpus()
        runs[2]['I0'] = 'false'
        runs[1]['I2'] = 'true'
        self.assertEqual(self.predictions(runs, spans)['P3'][4], 'refuted')
        runs[1]['I2'] = 'false'
        runs[1]['I2_lenient'] = 'true'
        self.assertEqual(self.predictions(runs, spans)['P3'][4], 'supported theo I2 dong bang; se bi bac theo I2_lenient')

    def test_the_verdicts_follow_the_main_table_not_the_calibration_case(self):
        runs, spans = self.corpus()
        runs[3]['hit_without_evidence'] = 'false'
        calibration = [run('x', case=dec.CALIBRATION_CASE, condition='no_metric', i0='true', table_received='true',
                           empty_reason_set='no_rows', i4='true', hit_without_evidence='true')]
        calibration += [run('b', case=dec.CALIBRATION_CASE, seq=n, i2='true') for n in (1, 2, 3)]
        spans = spans + self.spans(calibration[1]['run_id'], 0, 10)
        p = self.predictions(runs + calibration, spans)
        self.assertEqual(p['P1'][4], 'supported')
        self.assertEqual(p['P2'][4], 'supported')
        self.assertTrue(p['P3'][4].startswith('supported'), p['P3'][4])
        self.assertEqual(p['P5'][4], 'refuted')
        self.assertIn('I2 dung 1/3 Ev bang chinh (8 case 4/6)', p['P3'][3])
        self.assertIn('run hoan tat bang chinh 5/6 (8 case 5/16)', p['P2'][3])
        self.assertIn('(8 case 2/3, ca 1)', p['P5'][3])


class CommandLineTest(unittest.TestCase):
    @staticmethod
    def write_analysis(directory, runs, spans=None):
        directory.mkdir(parents=True, exist_ok=True)
        for name, rows in (('runs.csv', runs), ('spans.csv', spans or [])):
            if not rows and name == 'spans.csv':
                rows = [{'run_id': 'none', 'table_has_gt_kpi': 'false', 'is_gt_span': 'false', 'self_is_abnormal': 'false'}]
            with open(directory / name, 'w', encoding='utf-8', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator='\n')
                writer.writeheader()
                writer.writerows(rows)

    def test_writes_the_three_files_with_lf_line_ends(self):
        runs = [run(u) for u in 'abc'] + [run('x', condition='no_metric')]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.write_analysis(tmp / 's1', runs)
            self.write_analysis(tmp / 'r2', runs)
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(dec.main(['--analysis', str(tmp / 's1'), '--analysis-r2', str(tmp / 'r2'),
                                           '--out', str(tmp / 'out' / 'nested')]), 0)
            names = sorted(p.name for p in (tmp / 'out' / 'nested').iterdir())
            self.assertEqual(names, ['outcome-sentences.csv', 'predictions.csv', 'x-direction-ranking.csv'])
            self.assertEqual(out.getvalue().count('wrote '), 3)
            for name in names:
                data = (tmp / 'out' / 'nested' / name).read_bytes()
                self.assertNotIn(b'\r', data)
                data.decode('utf-8')
            first = (tmp / 'out' / 'nested' / 'outcome-sentences.csv').read_bytes()
            with contextlib.redirect_stdout(io.StringIO()):
                dec.main(['--analysis', str(tmp / 's1'), '--analysis-r2', str(tmp / 'r2'), '--out', str(tmp / 'out' / 'nested')])
            self.assertEqual((tmp / 'out' / 'nested' / 'outcome-sentences.csv').read_bytes(), first)

    def test_a_missing_analysis_folder_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stderr(io.StringIO()) as err, self.assertRaises(SystemExit) as caught:
                dec.main(['--analysis', str(Path(tmp) / 'absent'), '--out', str(Path(tmp) / 'out')])
            self.assertEqual(caught.exception.code, 2)
            self.assertIn('runs.csv', err.getvalue())

    def test_a_missing_second_round_file_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.write_analysis(tmp / 's1', [run(u) for u in 'abc'])
            with contextlib.redirect_stderr(io.StringIO()) as err, self.assertRaises(SystemExit) as caught:
                dec.main(['--analysis', str(tmp / 's1'), '--analysis-r2', str(tmp / 'r2'), '--out', str(tmp / 'out')])
            self.assertEqual(caught.exception.code, 2)
            self.assertIn(str(tmp / 'r2' / 'runs.csv'), err.getvalue())

    def test_a_missing_spans_file_of_the_first_analysis_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.write_analysis(tmp / 's1', [run(u) for u in 'abc'])
            self.write_analysis(tmp / 'r2', [run(u) for u in 'abc'])
            (tmp / 's1' / 'spans.csv').unlink()
            with contextlib.redirect_stderr(io.StringIO()) as err, self.assertRaises(SystemExit) as caught:
                dec.main(['--analysis', str(tmp / 's1'), '--analysis-r2', str(tmp / 'r2'), '--out', str(tmp / 'out')])
            self.assertEqual(caught.exception.code, 2)
            self.assertIn('spans.csv', err.getvalue())

    def distinct_rounds(self, tmp):
        """Writes the first analysis with a fault that is absent from the trace and the second round with a queried one."""
        s1 = [run(u, s0=ABSENT, span=0) for u in 'abc']
        r2 = [run(u, s0=QUERIED) for u in 'abc']
        spans = PredictionTest.spans(s1[0]['run_id'], 2, 2)
        self.write_analysis(tmp / 's1', s1, spans)
        self.write_analysis(tmp / 'r2', r2, PredictionTest.spans(r2[0]['run_id'], 0, 7))

    def check_distinct_rounds(self, out):
        with open(out / 'outcome-sentences.csv', encoding='utf-8', newline='') as handle:
            by = {(r['variant'], r['sentence']): r for r in csv.DictReader(handle)}
        self.assertEqual(by[(dec.LABEL_MAIN, 'S0_gt_span_absent')]['k_units'], '3')
        self.assertEqual(by[('r2 main (bo 99f095)', 'S0_gt_span_absent')]['k_units'], '0')
        with open(out / 'predictions.csv', encoding='utf-8', newline='') as handle:
            p2 = {r['id']: r for r in csv.DictReader(handle)}['P2']['numbers']
        self.assertIn('run hoan tat bang chinh 2/2', p2)

    def test_each_analysis_folder_feeds_its_own_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.distinct_rounds(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                dec.main(['--analysis', str(tmp / 's1'), '--analysis-r2', str(tmp / 'r2'), '--out', str(tmp / 'out')])
            self.check_distinct_rounds(tmp / 'out')

    def test_the_defaults_are_the_three_module_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.distinct_rounds(tmp)
            with mock.patch.object(dec, 'DEFAULT_ANALYSIS', tmp / 's1'), \
                    mock.patch.object(dec, 'DEFAULT_ANALYSIS_R2', tmp / 'r2'), \
                    mock.patch.object(dec, 'DEFAULT_OUT', tmp / 'out'), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(dec.main([]), 0)
            self.check_distinct_rounds(tmp / 'out')

    def test_the_second_round_needs_no_spans_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.distinct_rounds(tmp)
            (tmp / 'r2' / 'spans.csv').unlink()
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(dec.main(['--analysis', str(tmp / 's1'), '--analysis-r2', str(tmp / 'r2'),
                                           '--out', str(tmp / 'out')]), 0)


class RealDecisionGateTest(unittest.TestCase):
    """Regenerates the three CSVs from the real S1 v2 and second-round analyses and compares them byte for byte with the
    ones kept in runtime/. A missing input fails the test unless EVIDENCE_LOSS_ALLOW_NO_ZIP=1."""
    NAMES = ('outcome-sentences.csv', 'predictions.csv', 'x-direction-ranking.csv')

    def test_regenerated_files_equal_the_kept_ones(self):
        needed = [dec.DEFAULT_ANALYSIS / 'runs.csv', dec.DEFAULT_ANALYSIS / 'spans.csv', dec.DEFAULT_ANALYSIS_R2 / 'runs.csv']
        needed += [dec.DEFAULT_OUT / name for name in self.NAMES]
        missing = [str(p) for p in needed if not p.exists()]
        if missing:
            if os.environ.get('EVIDENCE_LOSS_ALLOW_NO_ZIP') == '1':
                print('WARNING: real decision gate skipped, files missing: ' + ', '.join(missing), file=sys.stderr)
                self.skipTest('real analysis outputs missing and EVIDENCE_LOSS_ALLOW_NO_ZIP=1')
            self.fail('real analysis outputs missing (set EVIDENCE_LOSS_ALLOW_NO_ZIP=1 to skip): ' + ', '.join(missing))
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stdout(io.StringIO()):
                dec.main(['--out', tmp])
            for name in self.NAMES:
                self.assertEqual((Path(tmp) / name).read_bytes(), (dec.DEFAULT_OUT / name).read_bytes(), name)


if __name__ == '__main__':
    unittest.main()
