"""Derives the decision tables of the evidence-loss analysis (RQ b) from the output of analyze-evidence-loss.py: the outcome
sentences per unit with their sensitivity variants, the ranking of the candidate X directions, and the check of the
pre-registered predictions. No ZIP, no model, no Kaggle; it reads runs.csv and spans.csv only.

Usage: decide-evidence-loss-outcomes.py [--analysis DIR] [--analysis-r2 DIR] [--out DIR]

--analysis is the analyzer output of the S1 v2 results (default runtime/analysis-evidence-loss-s1-v2), --analysis-r2 the
one of the second round (default runtime/analysis-evidence-loss-r2), --out the folder of the three CSVs (default
runtime/analysis-evidence-loss-decision); files already there are replaced. Writes, UTF-8 with LF line ends:

- outcome-sentences.csv: for each variant and each outcome sentence, the number of units with data (n_units), the units
  that support it (k_units), status (k/n, or not_testable when n < 3) and, per unit, supporting runs over runs with data.
  The unit is the service of the injected fault. Variants: the main table (metric condition, calibration case 99f095
  dropped), all 8 cases, the same two for the second round, each of them with one fault service left out, and two
  scenarios for the single metric run that stopped early.
- x-direction-ranking.csv: the sentences of the main table that are testable with k >= 1 ordered by k/n, then k (both
  descending; equal pairs share a rank, no tie breaker), then the sentences that are not_testable, then those with
  k = 0, each with the X direction it points to.
- predictions.csv: the pre-registered predictions with the numbers they are checked against, recomputed from the runs.

The sentence predicates are those of section 9.3 of the pre-registration codebook, the n >= 3 gate that of 9.1, the
ranking that of 9.3 and the directions those of 9.4. Hand-entered, not derivable from the data: the variant labels, the
X direction texts, the prediction wording and exposure notes, and the suffixes of the P3 and P4 outcomes (DIRECTIONS,
PREDICTIONS, OUTCOME_NOTES below); their source is the codebook sections 9.4 and 10.

Not derived here: the sentence no_stage_implicated of 9.3 (it holds only when no other sentence has k >= 1, which is false
whenever any ranked sentence exists), the sensitivity of the sentences to I2_lenient (the sentences use I2 and I3 as
defined; I2_lenient is read in P3 only) and an I3-false reading of the run that stopped early (both scenarios keep I3 true,
so they vary I4 only). Prediction P4 reads the metric condition only, as the main table does.
"""
import argparse
import csv
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / 'runtime'
DEFAULT_ANALYSIS = RUNTIME / 'analysis-evidence-loss-s1-v2'
DEFAULT_ANALYSIS_R2 = RUNTIME / 'analysis-evidence-loss-r2'
DEFAULT_OUT = RUNTIME / 'analysis-evidence-loss-decision'

CALIBRATION_CASE = '99f095'
# Quick feasibility gate of the codebook section 9.1: fewer units than this and a sentence is not testable.
MIN_UNITS = 3
FAULT_SERVICES = ('checkoutservice', 'currencyservice', 'emailservice', 'recommendationservice')
# The metric run that was cut short: the only incomplete run of the main table (case ad1c27, seed 20261027). Its
# unknown indicators are filled in with the two extreme readings of the stages after consolidation.
CUT_SCENARIOS = (('cens_worst', 'main, run cat cut ad1c27 s27 gia dinh I2 sai, I3 dung, I4 sai', ('false', 'true', 'false')),
                 ('cens_best', 'main, run cat cut ad1c27 s27 gia dinh I2 sai, I3 dung, I4 dung', ('false', 'true', 'true')))
LABEL_MAIN = 'main (bo 99f095)'
LABEL_ALL8 = 'all8 (= chi bo 2 run hieu chinh, vi 2 run do thuoc metric_no_log)'
OUTCOME_COLUMNS = ['variant', 'sentence', 'n_units', 'k_units', 'status', 'supporting_units', 'non_supporting_units',
                   'per_unit_runs_supporting_over_with_data']
RANKING_COLUMNS = ['rank', 'sentence', 'k', 'n', 'x_direction', 'stage', 'achievable_without_editing_upstream',
                   'test_condition_requires_model']
PREDICTION_COLUMNS = ['id', 'prediction', 'refuted_when', 'numbers', 'outcome', 'exposure', 'source']

# Codebook 9.4 and 9.3: sentence -> (X direction, stage, achievable without editing upstream, condition that needs a model).
# The condition texts of label_mismatch_flags and S0_gt_span_present_not_queried state what the current data shows; they
# are not recomputed when those sentences become testable or gain support.
# {n}, {n_all8} and {k} in a text are filled with the count of the sentence in the main table, in the all-8 table and its k.
DIRECTIONS = {
    'S0_gt_span_absent': (
        'Dua danh sach dich vu da biet vao truy van metric hoac wrapper tu truy van bang cho moi dich vu da biet', 'S0',
        'dat: wrapper get_tool hoac them buoc o harness',
        'chay lai ba case khong co span GT (272a47, 30e3c7, de6a50) voi truy van bo sung va do R@1; lan voi hinh dang trace va tool oracle GT'),
    'S2_root_label_lost_hit_kept': (
        'Dua tin hieu metric vao luat consolidation hoac giam vai tro chuoi consolidation', 'S2',
        'can override ben ngoai (viet lai payload consolidate)',
        'chay voi override prompt consolidate; muc loi ky vong thap vi GT van hang 1 o cac run do'),
    'S4_inputs_present_not_rank1': (
        'Hau xu ly hoac xep lai hang o tong hop cuoi', 'S4',
        'dat: xu ly result.json o harness, tranh dung nhan GT',
        'chay lai 29583d voi buoc xep lai hang; mot case, ba seed gan nhu nhan ban'),
    'label_mismatch_flags': (
        'Kiem chung hoac sua khai bao has_error_logs; sua nhan hint cho span chi tre', 'S1, S3',
        'dat neu viet lai payload.messages o adapt_payload; sua luat chuoi trong coordinator.py thi khong dat',
        'not_testable (n = {n} bang chinh; n = {n_all8} o 8 case); khong co du lieu nhat quan de xep hang'),
    'S0_gt_span_present_not_queried': (
        'Huong nham S0 cho case co span GT ma khong duoc hoi', 'S0', 'khong can',
        'khong co du lieu nhat quan (k = {k})'),
}

# Codebook section 10: id -> (prediction, refuted when, exposure, source columns).
PREDICTIONS = {
    'P1': ('no_metric: moi run I0 sai; moi luot hoi GT co empty_reason = absent_source',
           'co run table_received dung, hoac empty_reason khac absent_source o luot hoi GT',
           'tautology theo thiet ke harness', 'runs.csv: I0, table_received, queried_gt, empty_reason_set'),
    'P2': ('metric: hon mot nua span mang bang GT tu danh dau is_abnormal = true', 'chung mot nua hoac it hon',
           'mo ta co phoi nhiem (scout thay 92/98)',
           'spans.csv: table_has_gt_kpi, metric_tables, is_gt_span, self_is_abnormal'),
    'P3': ('nhan root neu GT o duoi nua so run Ev', 'tu nua tro len', 'mo ta co phoi nhiem (thay 3/14)',
           'runs.csv: I0, I2, I2_lenient'),
    'P4': ('run truot R@1 o nhanh co metric co D1 nhieu hon run dung', 'ti le D1 cua run truot khong lon hon run dung',
           'kham pha goc tu scout; D1 gan hang dang voi khai bao has_error_logs', 'runs.csv: D1, I4'),
    'P5': ('mot phan run dung R@1 o no_metric la hit_without_evidence', 'khong run nao',
           'da thay ad1c27 3/3 (scout); gan hang dang voi P1', 'runs.csv: I4, hit_without_evidence'),
}
# Words the outcome column carries beyond the supported or refuted verdict: a reading of the data, not a count.
OUTCOME_NOTES = {
    'P3': '; se bi bac theo I2_lenient',
    'P4': ' (hep: ca {d1_runs} run D1 thuoc {d1_case}, trong case khong testable)',
}


def read_rows(directory, name):
    with open(Path(directory) / name, encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def is_true(value):
    return value == 'true'


def is_false(value):
    return value == 'false'


def sentences(runs, extra=()):
    """Maps each outcome sentence to {unit: (supports, 'runs supporting/runs with data')} for the completed runs of
    `runs`, plus the `extra` rows taken as completed. A unit without data for a sentence is left out of it."""
    done = [r for r in runs if is_true(r['completed'])] + list(extra)
    units = sorted({r['gt_service'] for r in done})
    by_unit = {u: [r for r in done if r['gt_service'] == u] for u in units}
    evidence = [r for r in done if is_true(r['I0'])]
    ev_by_unit = {u: [r for r in evidence if r['gt_service'] == u] for u in units}

    def cases_of(rows):
        grouped = {}
        for r in rows:
            grouped.setdefault(r['case'], []).append(r)
        return [grouped[c] for c in sorted(grouped)]

    result = {}
    detail = {}
    for u in units:
        rows = by_unit[u]
        every = any(all(r['s0_label'] == 'S0_gt_span_absent' for r in g) for g in cases_of(rows))
        detail[u] = (every, f"{sum(r['s0_label'] == 'S0_gt_span_absent' for r in rows)}/{len(rows)}")
    result['S0_gt_span_absent'] = detail
    detail = {}
    for u in units:
        rows = [r for r in by_unit[u] if int(r['gt_span_in_trace']) >= 1]
        if rows:
            every = any(all(r['s0_label'] == 'S0_gt_span_present_not_queried' for r in g) for g in cases_of(rows))
            count = sum(r['s0_label'] == 'S0_gt_span_present_not_queried' for r in rows)
            detail[u] = (every, f'{count}/{len(rows)}')
    result['S0_gt_span_present_not_queried'] = detail
    detail = {}
    for u in units:
        rows = [r for r in ev_by_unit[u] if is_true(r['I1']) and is_false(r['I2'])]
        if rows:
            kept = sum(is_true(r['I4']) for r in rows)
            detail[u] = (kept >= 1, f'{kept}/{len(rows)}')
    result['S2_root_label_lost_hit_kept'] = detail
    detail = {}
    for u in units:
        if ev_by_unit[u]:
            rows = [r for r in ev_by_unit[u] if is_true(r['I1']) and is_true(r['I3']) and is_false(r['I4'])]
            detail[u] = (len(rows) >= 1, f'{len(rows)}/{len(ev_by_unit[u])}')
    result['S4_inputs_present_not_rank1'] = detail
    detail = {}
    for u in units:
        for group in cases_of(ev_by_unit[u]):
            with_d1 = [r for r in group if is_true(r['D1'])]
            without = [r for r in group if not is_true(r['D1'])]
            if with_d1 and without:
                missed_with = sum(is_false(r['I4']) for r in with_d1)
                missed_without = sum(is_false(r['I4']) for r in without)
                # A unit with several such cases keeps the last one in case order.
                detail[u] = (Fraction(missed_with, len(with_d1)) > Fraction(missed_without, len(without)),
                             f"case {group[0]['case']}: D1 trượt {missed_with}/{len(with_d1)}; "
                             f"không D1 trượt {missed_without}/{len(without)}")
    result['label_mismatch_flags'] = detail
    return result


def outcome_table(label, runs, rows_out, extra=()):
    """Appends the rows of one variant to rows_out and returns its ranking: (k/n, k, sentence, n) of the testable
    sentences with k >= 1, best first. Sentences of equal k/n and k keep their order of definition."""
    ranked = []
    for name, detail in sentences(runs, extra).items():
        n = len(detail)
        k = sum(1 for supports, _ in detail.values() if supports)
        rows_out.append({
            'variant': label, 'sentence': name, 'n_units': n, 'k_units': k,
            'status': 'not_testable' if n < MIN_UNITS else f'{k}/{n}',
            'supporting_units': ';'.join(u for u, v in detail.items() if v[0]),
            'non_supporting_units': ';'.join(u for u, v in detail.items() if not v[0]),
            'per_unit_runs_supporting_over_with_data': ';'.join(f'{u}={v[1]}' for u, v in detail.items())})
        if n >= MIN_UNITS and k >= 1:
            ranked.append((Fraction(k, n), k, name, n))
    ranked.sort(key=lambda x: (-x[0], -x[1]))
    return ranked


def outcome_variants(s1_runs, r2_runs):
    """Returns the outcome rows of every variant and the ranking of each, keyed by variant id."""
    rows, ranks = [], {}
    metric = [r for r in s1_runs if r['condition'] == 'metric']
    metric_r2 = [r for r in r2_runs if r['condition'] == 'metric']
    main = [r for r in metric if r['case'] != CALIBRATION_CASE]
    ranks['main'] = outcome_table(LABEL_MAIN, main, rows)
    ranks['all8'] = outcome_table(LABEL_ALL8, metric, rows)
    ranks['r2_main'] = outcome_table('r2 main (bo 99f095)', [r for r in metric_r2 if r['case'] != CALIBRATION_CASE], rows)
    ranks['r2_all8'] = outcome_table('r2 all8', metric_r2, rows)
    for u in FAULT_SERVICES:
        ranks['loo_' + u] = outcome_table(f'main bo dich vu GT {u}', [r for r in main if r['gt_service'] != u], rows)
        ranks['loo8_' + u] = outcome_table(f'all8 bo dich vu GT {u}', [r for r in metric if r['gt_service'] != u], rows)
    cut = [r for r in main if not is_true(r['completed'])]
    for key, label, (i2, i3, i4) in CUT_SCENARIOS:
        extra = [dict(r, completed='true', I1='true', I2=i2, I3=i3, I4=i4) for r in cut]
        ranks[key] = outcome_table(label, main, rows, extra)
    return rows, ranks


def direction_rows(rows, ranked):
    """Rows of x-direction-ranking.csv: the ranked sentences of the main table, then not_testable, then k = 0."""
    main = {r['sentence']: r for r in rows if r['variant'] == LABEL_MAIN}
    all8 = {r['sentence']: r for r in rows if r['variant'] == LABEL_ALL8}
    out, rank, previous = [], 0, None
    for position, (ratio, k, name, n) in enumerate(ranked, 1):
        if (ratio, k) != previous:
            rank, previous = position, (ratio, k)
        out.append((rank, name, k, n))
    ranked_names = {name for _, name, _, _ in out}
    rest = [r for r in main.values() if r['sentence'] not in ranked_names]
    out += [('', r['sentence'], '', r['n_units']) for r in rest if r['status'] == 'not_testable']
    out += [('', r['sentence'], r['k_units'], r['n_units']) for r in rest if r['status'] != 'not_testable']
    result = []
    for rank, name, k, n in out:
        direction, stage, achievable, condition = DIRECTIONS[name]
        condition = condition.format(n=n, n_all8=all8[name]['n_units'], k=k)
        result.append([rank, name, k, n, direction, stage, achievable, condition])
    return result


def count(rows, predicate):
    return sum(1 for r in rows if predicate(r))


def prediction_rows(s1_runs, s1_spans):
    """Rows of predictions.csv; each number is recomputed for the main table and for all 8 cases."""
    def scope(condition, only_main, completed=True):
        return [r for r in s1_runs if r['condition'] == condition and (not only_main or r['case'] != CALIBRATION_CASE)
                and (not completed or is_true(r['completed']))]

    def stats(only_main):
        """Every statement as (numerator, denominator)."""
        no_metric = scope('no_metric', only_main, completed=False)
        done = [r for r in no_metric if is_true(r['completed'])]
        asked = [r for r in done if is_true(r['queried_gt'])]
        metric_done = scope('metric', only_main)
        ids = {r['run_id'] for r in metric_done}
        spans = [s for s in s1_spans if s['run_id'] in ids]
        tables = [s for s in spans if is_true(s['table_has_gt_kpi'])]
        gt = [s for s in spans if is_true(s['is_gt_span'])]
        ev = [r for r in metric_done if is_true(r['I0'])]
        hit = [r for r in done if is_true(r['I4'])]
        out = {
            'p1_no_i0': (count(done, lambda r: is_false(r['I0'])), len(done)),
            'p1_i0_true': (count(done, lambda r: is_true(r['I0'])), len(done)),
            'p1_table_true': (count(no_metric, lambda r: is_true(r['table_received'])), len(no_metric)),
            'p1_other_reason': (count(asked, lambda r: r['empty_reason_set'] != 'absent_source'), len(asked)),
            'p1_no_table': (count(no_metric, lambda r: is_false(r['table_received'])), len(no_metric)),
            'p1_absent': (count(asked, lambda r: r['empty_reason_set'] == 'absent_source'), len(asked)),
            'p2_tables': (count(tables, lambda s: is_true(s['self_is_abnormal'])), len(tables)),
            'p2_gt': (count(gt, lambda s: is_true(s['self_is_abnormal'])), len(gt)),
            'p3_strict': (count(ev, lambda r: is_true(r['I2'])), len(ev)),
            'p3_lenient': (count(ev, lambda r: is_true(r['I2_lenient'])), len(ev)),
            'p5_hit': (len(hit), len(done)),
            'p5_blind': (count(hit, lambda r: is_true(r['hit_without_evidence'])), len(hit)),
        }
        for key, rows in (('all', metric_done), ('ev', ev)):
            missed = [r for r in rows if is_false(r['I4'])]
            right = [r for r in rows if is_true(r['I4'])]
            out[f'p4_{key}_missed'] = (count(missed, lambda r: is_true(r['D1'])), len(missed))
            out[f'p4_{key}_right'] = (count(right, lambda r: is_true(r['D1'])), len(right))
        return out

    main_stats, all_stats = stats(True), stats(False)
    d1_cases = sorted({r['case'] for r in scope('metric', True) if is_true(r['D1'])})

    def m(key):
        return '%d/%d' % main_stats[key]

    def a(key):
        return '%d/%d' % all_stats[key]

    def half_or_more(key):
        return 2 * main_stats[key][0] >= main_stats[key][1]

    def verdict(supported):
        return 'supported' if supported else 'refuted'

    def d1_rate(key):
        # No run in the group: the rate is taken as 0, so an empty group of runs that got it right does not refute.
        flagged, size = main_stats[key]
        return Fraction(flagged, size) if size else Fraction(0)

    higher = d1_rate('p4_all_missed') > d1_rate('p4_all_right')
    p4 = verdict(higher)
    if higher and len(d1_cases) == 1:
        p4 += OUTCOME_NOTES['P4'].format(d1_runs=main_stats['p4_all_missed'][0], d1_case=d1_cases[0])
    p3 = verdict(not half_or_more('p3_strict'))
    if not half_or_more('p3_strict'):
        p3 += ' theo I2 dong bang' + (OUTCOME_NOTES['P3'] if half_or_more('p3_lenient') else '')
    results = {
        'P1': (f"{m('p1_no_i0')} run hoan tat bang chinh ({a('p1_no_i0')} o 8 case) I0 sai; "
               f"table_received sai {m('p1_no_table')} ({a('p1_no_table')} o 8 case); "
               f"{m('p1_absent')} run bang chinh ({a('p1_absent')} o 8 case) co hoi GT chi co absent_source",
               # Refuted by any run that is true, so a value that is neither true nor false cannot flip the verdict.
               verdict(not any(main_stats[key][0] for key in ('p1_i0_true', 'p1_table_true', 'p1_other_reason')))),
        'P2': (f"span mang bang chua khoa GT, run hoan tat bang chinh {m('p2_tables')} (8 case {a('p2_tables')}); "
               f"span cua dich vu GT trong trace {m('p2_gt')} (8 case {a('p2_gt')})",
               verdict(2 * main_stats['p2_tables'][0] > main_stats['p2_tables'][1])),
        'P3': (f"I2 dung {m('p3_strict')} Ev bang chinh (8 case {a('p3_strict')}); "
               f"do nhay I2_lenient {m('p3_lenient')} (8 case {a('p3_lenient')})", p3),
        'P4': (f"metric bang chinh hoan tat: D1 {m('p4_all_missed')} run truot so voi {m('p4_all_right')} run dung "
               f"(Ev: {m('p4_ev_missed')} so voi {m('p4_ev_right')}; 8 case {a('p4_all_missed')} so voi {a('p4_all_right')})", p4),
        'P5': (f"{m('p5_hit')} run hoan tat bang chinh dung R@1, ca {main_stats['p5_blind'][0]} la hit_without_evidence "
               f"(8 case {a('p5_hit')}, ca {all_stats['p5_blind'][0]})",
               verdict(main_stats['p5_blind'][0] >= 1)),
    }
    return [[pid, prediction, refuted_when, results[pid][0], results[pid][1], exposure, source]
            for pid, (prediction, refuted_when, exposure, source) in PREDICTIONS.items()]


def write_csv(path, header, rows, dict_rows=False):
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator='\n') if dict_rows else csv.writer(handle, lineterminator='\n')
        if dict_rows:
            writer.writeheader()
        else:
            writer.writerow(header)
        writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Derives the decision tables of the evidence-loss analysis.')
    parser.add_argument('--analysis', type=Path, default=DEFAULT_ANALYSIS, help='analyzer output of the S1 v2 results')
    parser.add_argument('--analysis-r2', type=Path, default=DEFAULT_ANALYSIS_R2, help='analyzer output of the second round')
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT, help='folder of the three CSVs')
    args = parser.parse_args(argv)
    for directory in (args.analysis, args.analysis_r2):
        for name in ('runs.csv', 'spans.csv') if directory == args.analysis else ('runs.csv',):
            if not (directory / name).is_file():
                parser.error(f'missing {directory / name}')
    s1_runs = read_rows(args.analysis, 'runs.csv')
    rows, ranks = outcome_variants(s1_runs, read_rows(args.analysis_r2, 'runs.csv'))
    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / 'outcome-sentences.csv', OUTCOME_COLUMNS, rows, dict_rows=True)
    write_csv(args.out / 'x-direction-ranking.csv', RANKING_COLUMNS, direction_rows(rows, ranks['main']))
    write_csv(args.out / 'predictions.csv', PREDICTION_COLUMNS, prediction_rows(s1_runs, read_rows(args.analysis, 'spans.csv')))
    for name in ('outcome-sentences.csv', 'x-direction-ranking.csv', 'predictions.csv'):
        print(f'wrote {args.out / name}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
