# 04 — Evidence visibility audit: full results (CPU only)

Run on 2026-10-18/19 with `python -m rca.visibility configs/exp/visibility-<ds>.yaml` after
`run_grid prepare` on the same config. No model was called. All four `run.log` files end with
`exit 0`. (The wrapper job reported exit 1 only because its final `tail -3` over several files is
invalid syntax for this `tail`; the audits themselves succeeded.)

Outputs, all git-ignored and outside every evidence directory:
`nt114-rca/nt114-rca/results_visibility/<ds>/{evidence_visibility.jsonl, table_evidence_visibility.csv, visibility_counts.json, run.log}`.

## Definitions

- **in_candidates**: a true root is in the prompt's candidate list.
- **named**: a true root appears as a service line (`- <svc>: ...`) in any evidence block, or as an
  endpoint of a slow call edge. `named_metrics/logs/traces/trace_edge` say where.
- **token_anywhere**: the root id appears as a word anywhere in the text (looser; not counted as
  named).
- **same_as_full**: the condition's evidence text is identical to `full`.
- For AIOps2025 set-scored incidents (multi-service labels), "a true root" means any member of the
  root set.

**Being named is a property of the summary, not a precondition of a correct answer.** The model
ranks the whole candidate list and can rank an unnamed root first. Nothing below implies that an
unnamed root makes a correct answer impossible.

Unit: one record = one (incident, condition). Rates are given as numerator/denominator of
records. Injection-weighted rates differ only for RCA100 (86 records from 70 injections) and are
given there.

## 1. Denominators and exclusions

| Dataset | Split (roles) | Incidents in roles | Excluded (reason) | Selected | Missing evidence | Skipped conditions | Records |
|---|---|---|---|---|---|---|---|
| RCAEval | `within-rcaeval-grouped-0-e9b2c81c` (val, test) | 361 (143 val, 218 test) | 0 | 361 | 0 | 31 × `blind_nonroot_ev` | 1,380 |
| Nezha | `eval-only-nezha-0-38cde4e0` (test) | 101 | 4 (`PRE_WINDOW_SHORT`) | 97 | 0 | 24 × `blind_nonroot_ev` | 752 |
| RCA100 | `eval-only-rca100-0-b8a32300` (test) | 86 (70 injections) | 0 | 86 | 0 | 79 × `blind_nonroot_ev` | 609 |
| AIOps2025 | `eval-only-aiops2025-0-f92dd409` (test) | 318 (245 top-1, 73 set-scored) | 0 | 318 | 0 | 42 × `blind_nonroot_ev` | 1,720 |

A skipped `blind_nonroot_ev` means the condition driver found no non-root service eligible as an
evidence-matched target. Conditions that do not apply to an incident (for example `no_trace`
without traces) are not records and not exclusions; `rca.visibility` raises on any condition set
other than the applicable one, so no record was dropped silently. Label granularity: RCAEval 361
service; Nezha 97 pod; RCA100 83 service + 3 pod; AIOps2025 122 service + 123 pod + 73
multi-service. No train-role incident was read.

## 2. Observations

### 2.1 Candidate membership

`in_candidates` is true in **every** record of every dataset (RCAEval 1,380/1,380 val+test records (579 val, 801 test),
Nezha 752/752, RCA100 609/609, AIOps2025 1,720/1,720). Candidate-generation failure is zero for
tier A, as expected from the construction (candidate set = all services).

### 2.2 Root named in `full`

| Dataset (role) | named | not named | token_anywhere |
|---|---|---|---|
| RCAEval test | 216/218 (99.1 %) | 2 | 216/218 |
| RCAEval val (DEV) | 140/143 (97.9 %) | 3 | 140/143 |
| Nezha test | 80/97 (82.5 %) | 17 | 80/97 |
| RCA100 test | 77/86 (89.5 %; injection-weighted 0.898) | 9 | 77/86 |
| AIOps2025 test, all | 298/318 (93.7 %) | 20 | 298/318 |
| AIOps2025 top-1 only | 225/245 (91.8 %) | 20 | – |
| AIOps2025 set-scored | 73/73 (100 %) | 0 | – |

By granularity (full): AIOps2025 pod 104/123, service 121/122, multi-service 73/73; RCA100 pod
3/3, service 74/83. `token_anywhere` never exceeded `named` in `full`.

### 2.3 Conditions against `full` (paired on the same incidents)

"Lost" = named under `full` but not under the condition; "gained" = the reverse. Gained was 0 in
every cell of every dataset.

| Dataset (role) | Condition | n | named | lost vs full | same_as_full |
|---|---|---|---|---|---|
| RCAEval test | no_metric | 108 | 66 | 42/108 | 0 |
| | metrics_only | 108 | 107 | 1 | 0 |
| | no_log | 108 | 108 | 0 | 0 |
| | no_trace | 69 | 68 | 1 | 0 |
| | blind_root | 69 | 68 | 1 | 20/69 |
| | blind_nonroot | 69 | 69 | 0 | 62/69 |
| | blind_nonroot_ev | 52 | 52 | 0 | 0/52 |
| RCAEval val | no_metric | 78 | 51 | 25/78 | 0 |
| | metrics_only / no_log | 78 | 76 | 0 | 0 |
| | no_trace / blind_root / blind_nonroot | 54 | 52 | 0 | 0 / 28 / 48 |
| | blind_nonroot_ev | 40 | 40 | 0 | 0 |
| Nezha test | no_metric | 97 | 60 | 20/97 | 0 |
| | metrics_only | 97 | 59 | 21/97 | 0 |
| | no_log | 97 | 70 | 10/97 | 0 |
| | no_trace | 97 | 69 | 11/97 | 0 |
| | blind_root | 97 | 69 | 11/97 | 55/97 |
| | blind_nonroot | 97 | 80 | 0 | 81/97 |
| | blind_nonroot_ev | 73 | 59 | 0 | 0 |
| RCA100 test | no_metric | 86 | 8 | 69/86 | 0 |
| | metrics_only / no_trace / blind_root | 86 | 76 | 1 | 0 / 0 / 83 |
| | no_log / blind_nonroot | 86 | 77 | 0 | 0 / 84 |
| | blind_nonroot_ev | 7 | 7 | 0 | 0 |
| AIOps2025 test | no_metric | 304 | 192 | 93/304 | 0 |
| | metrics_only | 304 | 274 | 11/304 | 0 |
| | no_log | 304 | 280 | 5/304 | 0 |
| | no_trace | 283 | 265 | 0 | 0 |
| | blind_root | 83 | 81 | 0 | 46/83 |
| | blind_nonroot | 83 | 81 | 0 | 66/83 |
| | blind_nonroot_ev | 41 | 41 | 0 | 0 |

Truncation: 0 records truncated in any dataset or condition.

### 2.4 Where the root is named (`full`)

| Dataset (role) | metrics | logs | traces (service line) | trace edge |
|---|---|---|---|---|
| RCAEval test | 215/218 | 39/218 | 49/218 | 17/218 |
| Nezha test | 59/97 | 26/97 | 38/97 | 26/97 |
| RCA100 test | 76/86 | 7/86 | 2/86 | 0/86 |
| AIOps2025 test | 287/318 | 146/318 | 101/318 | 55/318 |

Block presence in `full`: RCAEval test has a logs block in 108/218 and a traces block in 69/218
records (the rest are natural metrics-only incidents); Nezha has a metrics block in 94/97;
AIOps2025 has logs in 304/318 and traces in 283/318.

### 2.5 Named services outside the candidate list

In RCAEval `full`, 148 of the 175 metrics-only records (no logs block; val + test) name at least
one service line that is not in the candidate list. In the 186 multimodal RCAEval records, and in
every record of Nezha, RCA100 and AIOps2025, the count is 0. The most frequent out-of-list names
are digit strings that look like host addresses with port 9100 (for example `1921681589100`),
`main`, `queue` and `front`. This is an observation about the metric-to-entity naming of these
incidents; whether it affects the LLM is untested.

## 3. Comparison with the earlier samples (01 §5)

| Dataset | Sample `full` (01 §5) | Full set `full` |
|---|---|---|
| RCAEval | 1.00 (n = 30) | 216/218 test, 140/143 val |
| AIOps2025 | 0.76 (n = 35–41) | 298/318 |
| RCA100 | 0.75 (n = 12) | 77/86 |
| Nezha | 1.00 (n = 4) | 80/97 |

The samples had unknown selection. The full-set rates replace them; the statement in 01 that the
root is unnamed in "about a quarter" of AIOps2025 and RCA100 `full` prompts does not hold on the
full sets (20/318 and 9/86).

## 4. Interpretation (not causal claims)

These are properties of the evidence instrument. No accuracy was measured, so nothing here says
how the LLM responds to any of it.

1. **`no_metric` is the condition that most often removes the root's name** (RCA100 69/86,
   AIOps2025 93/304, RCAEval test 42/108, Nezha 20/97). Any accuracy drop under `no_metric` is
   therefore confounded with the summary dropping the root's name, and must be reported stratified
   by `named`.
2. **`blind_root` is a weak manipulation of root visibility.** It removed the root's name in
   1/69 RCAEval test, 0/54 RCAEval val, 11/97 Nezha, 1/86 RCA100 and 0/83 AIOps2025 records.
   Its evidence was identical to `full` in 20/69, 28/54, 55/97, 83/86 and 46/83 records. A
   `blind_root` contrast that includes unchanged incidents measures a partly null manipulation;
   the `require_changed` filter of protocol v2 is needed, and the remaining effect concerns trace
   visibility only.
3. **`blind_nonroot` is often a null manipulation** (same as full in 62/69, 48/54, 81/97, 84/86,
   66/83), which is why `blind_nonroot_ev` exists. `blind_nonroot_ev` changed the text in every
   record where it applies, but it applies to few RCA100 incidents (7/86).
4. **Nezha is the dataset where single-modality conditions most often remove the root's name**
   (metrics_only 21/97, no_log 10/97, no_trace 11/97).
5. **Unnamed roots are a small stratum in `full`** (2/218 RCAEval test, 17/97 Nezha, 9/86
   RCA100, 20/318 AIOps2025). Accuracy on that stratum will have wide intervals.

## 5. Implications for H1, H2, H3

- **H1 (confidence and abstention under missingness).** `named` must be a stratum in every
  missingness contrast, especially `no_metric`. Contrasts on `blind_root` and `blind_nonroot`
  must be reported with and without `same_as_full` incidents.
- **H2 (evidence acquisition / cost).** Metrics carry the root's name in most incidents
  (`named_metrics` in `full`: 215/218, 59/97, 76/86, 287/318). An acquisition study that starts
  from metrics starts from a summary that already names the root in most cases; this bounds how
  much additional naming other modalities can add, not how much accuracy they can add.
- **H3 (retrieval vs ranking decomposition).** `in_candidates` is 1 everywhere, so on tier A the
  candidate-generation stage cannot fail and a decomposition reduces to ranking, unless a
  shortlist arm is added. `named` is a separate evidence-omission stratum, not a retrieval
  failure. The decomposition paper in `02` (H3) uses a retriever stage; NT114 has no such stage
  yet.

## Unresolved questions

1. Should the RCAEval metrics-only out-of-list entity names (§2.5) be mapped to services, filtered,
   or left as they are? Any change would alter evidence text and fingerprints, which this plan
   forbids; it is a question for after the literature review.
2. The 4 Nezha `PRE_WINDOW_SHORT` exclusions are inherited from the canonical bundle; whether they
   should be reported as a sensitivity set is open.
