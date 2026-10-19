# 06 — Calibration and detectable effects of the paired-contrast engine (CPU only)

This is phase 06 (V4, V5) of `plans/261018-2300-single-llm-simplification-and-evaluation-hardening/`,
run on 2026-10-19. No model was called. The outcomes are simulated; the structure is real.

- **Engine.** The contrasts go through `rca.contrasts.evaluate`, the code path that `analyze`
  uses for real contrasts. It runs the paired cluster bootstrap over injections (percentile
  95 % CI) and the paired sign-flip test, with injection weights 1/records.
- **Script.** `scripts/simulate_contrasts.py results_stats --reps 1000 --power-reps 400`:
  bootstrap B = 1,000, sign-flip draws = 1,000, seed 0. Outputs (git-ignored) are in
  `nt114-rca/nt114-rca/results_stats/`: `calibration.csv`, `power.csv`, `mde.csv` and
  `structures.json`.
- **Draw counts.** The simulation uses fewer draws than the headline setting (B = 10,000 and
  10,000 sign-flips, protocol v2 §3) so that it runs on a CPU. The number of draws affects the
  Monte Carlo precision of each interval, not its target.

## Structures

The structures are test-role incidents from `results_visibility/<ds>/evidence_visibility.jsonl`,
clustered by the injection in `reports/eval-units-<ds>.json`.

| Structure | Records | Injections | Max records per injection |
|---|---:|---:|---:|
| RCAEval test `full` | 218 | 218 | 1 |
| RCAEval test `blind_root` ∩ `blind_nonroot_ev` | 52 | 52 | 1 |
| Nezha test `full` | 97 | 97 | 1 |
| RCA100 test `full` | 86 | 70 | 4 |
| AIOps2025 test `full` | 318 | 318 | 1 |

RCA100 is the only structure with real clustering. It is the one that tests whether the cluster
bootstrap handles several records per injection.

## Generators

- **`difficulty`.** Each injection gets a difficulty u ~ U(0.2, 0.8). A record is correct with
  probability u + shift in arm a and u in arm b, independently. This generator has little
  discordance-structure realism, but its correlation within a cluster is strong.
- **`discordance`.** Each injection gets a discordance rate d_j ~ Beta with mean d
  (concentration 4) and a concordant level u. A discordant record favours arm a with
  probability (1 + δ/d)/2. The true difference is δ. Paired LLM arms behave like this: most
  records agree, and the effect is in the discordant ones.

## V4 — Calibration

- **Coverage:** whether the 95 % CI contains the true difference 0.10, over 1,000 replications.
- **Type-I error:** the sign-flip p < 0.05 at shift 0, over 1,000 replications.
- **Monte Carlo SE:** about 0.007 for coverage and about 0.007 for type-I at these replication counts.

| Structure | Generator | Coverage | Type-I |
|---|---|---:|---:|
| RCAEval test `full` | difficulty | 0.945 | 0.036 |
| RCAEval test `full` | discordance | 0.950 | 0.032 |
| RCAEval `blind_root` ∩ `blind_nonroot_ev` | difficulty | 0.941 | 0.025 |
| RCAEval `blind_root` ∩ `blind_nonroot_ev` | discordance | 0.930 | 0.027 |
| Nezha test `full` | difficulty | 0.955 | 0.033 |
| Nezha test `full` | discordance | 0.940 | 0.035 |
| RCA100 test `full` | difficulty | 0.948 | 0.041 |
| RCA100 test `full` | discordance | 0.945 | 0.036 |
| AIOps2025 test `full` | difficulty | 0.940 | 0.040 |
| AIOps2025 test `full` | discordance | 0.948 | 0.036 |

**Verdict: PASS.** Every structure meets the phase criterion: coverage is in [0.93, 0.97] and
type-I is ≤ 0.07.

- **Weakest coverage.** The weakest case is the 52-injection intersection under
  `discordance`, at 0.930. It sits on the lower bound, within one Monte Carlo SE of 0.937.
  Percentile intervals are known to under-cover slightly at small n with discrete outcomes, so
  intervals on intersections this small should be read as slightly liberal.
- **Sign-flip test.** The test is conservative, with type-I from 0.025 to 0.041.
- **Bootstrap method.** No revision of the phase-03 bootstrap method is required.

## V5 — Minimum detectable effects

- **Definition.** The MDE is the smallest grid δ (step 0.02) with sign-flip power ≥ 0.80 at
  α = 0.05, over 400 replications.
- **Scope.** It is a two-sided paired AC@1 contrast, with no multiplicity correction.
- **Constraint.** δ cannot exceed the discordance rate d.

| Structure | d = 10 % | d = 20 % | d = 30 % |
|---|---:|---:|---:|
| RCAEval test `full` (218) | 0.08 | 0.10 | 0.12 |
| RCAEval `blind_root` ∩ `blind_nonroot_ev` (52) | not reachable (power 0.445 at δ = d = 0.10) | 0.18 | 0.22 |
| Nezha test `full` (97) | 0.10 | 0.14 | 0.18 |
| RCA100 test `full` (86 records, 70 injections) | 0.10 | 0.16 | 0.18 |
| AIOps2025 test `full` (318) | 0.06 | 0.08 | 0.10 |

**Reading.**

- **Discordance values are placeholders.** The discordance rates are assumptions until a DEV
  pilot measures them. A pilot gives the discordance between two arms on the same incidents.
  That figure, not the marginal accuracies, picks the row.
- **The H3-type intersection is underpowered.** On the RCAEval `blind_root` ∩
  `blind_nonroot_ev` intersection, only large effects are detectable: 0.18 or more at 20 %
  discordance, and none at 10 %. If H3 rests on this contrast, either the effect must be large,
  or the set must grow (for example by pooling val after preregistration, which protocol v2
  §3 forbids for results), or the contrast becomes exploratory.
- **Holm raises the MDEs.** Holm correction within a declared family raises these MDEs. For a
  family of k contrasts, the first step tests at α/k.
- **RCA100 clustering.** RCA100 has 86 records over 70 injections. Its MDE is close to that of
  a 70-unit set, as the clustering implies.

**Protocol v2 §9.6.** This table replaces the old §9.6 MDE table. The protocol's accounting row
now points here.

## Unresolved questions

1. What is the actual discordance between the candidate arms? A DEV pilot on real model outputs
   is needed before the MDE row and the confirmatory family size can be fixed.
2. Should the confirmatory family include the 52-injection intersection at all, given its MDE?
   Or should H3 be preregistered as exploratory on RCAEval?
3. Should the headline intervals switch from percentile to BCa or studentized bootstrap for
   sets of 100 or fewer injections? Coverage at 0.930–0.941 passes, but it is at the low end.
4. Should a Holm-adjusted power run be added once the family size k is known?
