# Phases 09–11: audit, conditions, splits, evaluation units and integration (2026-10-14)

## Outcome

The four primary datasets pass the complete real-data audit, every one of the 16 split manifests
verifies, and the canonical `run_grid prepare` path works on real RCAEval without an LLM call.
Owner decisions of 2026-10-14 are implemented: RCAEval system-scoped identity is fixed, 4 RCAEval
incidents are excluded from primary evaluation, a `metrics_only` baseline condition exists,
independent injections and coverage strata are recorded per record, and AIOps2025 splits group by
campaign day. Two defects found on the way were fixed (B-tier leakage in within splits, a
missed short-hash Kubernetes pod in RCA100).

## Datasets

| Dataset | Build | Raw cases | Parsed | Accepted (ACCEPT / AWW) | Quarantined | Rejected | Independent injections | Primary-excluded | Label validity | Leakage scan |
|---|---|---|---|---|---|---|---|---|---|---|
| RCAEval | `rcaeval-2f4bf056cb8a` (adapter 1.0.1) | 736 | 736 | 735 (703 / 32) | 0 | 1 (duplicate `multi-source-data`) | 735 | 4 (temporary) | 736/736 valid, tier A | 0 hits (visible zone) |
| Nezha | `nezha-ea30424eba55` (1.0.3) | 101 | 101 | 101 (0 / 101) | 0 | 0 | 101 | 0 | 101/101 valid, A | 0 hits |
| AIOps2025 | `aiops2025-40efa9b2d22f` (1.0.1) | 400 | 400 | 400 (381 / 19) | 0 | 0 | 400 | 0 | 400/400 valid; A 318 (73 set-scoring-only), B 82 | 0 hits |
| RCA100 | `rca100-430dfff49e51` (1.0.2) | 103 | 103 | 103 (9 / 94) | 0 | 0 | 86 (11 multi-task injections, 28 tasks) | 0 | 103/103 valid; A 86, B 17 | 0 hits |

Audit `data/reports/audit-9338d463a84f.json` (`audit --evidence-stats`, exit 0, 53 min): 1,340
incidents; 0 unexplained duplicates; 0 cross-dataset overlaps; lineage 1:1 with the registry for
all four datasets with 0 unexplained differences (RCAEval: 735 registry rows plus the rejected
duplicate; 3 batch-cell label differences and RCA100's 103 fault-id prefix and window-start
differences are explained); 0 leakage hits; 0 split errors.

## Owner decisions implemented

1. **RCAEval identity.** Adapter 1.0.1 classifies a metric-header entity as the other system's
   container when it occurs in ≤ 5 % of its own system's incidents and ≥ 90 % of the other's
   (measured: ≤ 1.3 % and 100 %, nothing between 10 % and 30 %). Rebuild: same counts, 0
   collisions, validate exit 0. The 4 affected incidents now list only their own services and keep
   their root as a candidate. All other incidents take the unchanged code path; their condition
   applicability and non-root targets are identical to the previous build, and every RCAEval split
   kept its assignment hash (re-pinned; old manifests in `splits/_superseded/`).
2. **Primary exclusions.** `configs/eval_exclusions.yaml` lists the 4 uids with reasons
   (`status: temporary`, `decided: owner 2026-10-14`). They stay in the store and splits.
3. **Aliases.** Evidence table in `docs/dataset_quality_audit.md` ("Service identity: alias and
   rule evidence"). Only two ids are reached from two raw non-pod spellings in all four datasets
   (`frontend` ← `frontendservice` in RCAEval OB, `rediscart` ← `redis` in AIOps2025), both
   intended. The six alias entries stay "owner to confirm"; the Redis and TiDB rules are confirmed by
   source telemetry; `(deleted)` pods keep their raw `entity_raw`.
4. **RCA100 evaluation.** `eval-units-rca100.json`: 86 injections, weights 1/size,
   representatives; coverage causes logs 19 covered / 62 export truncated / 22 export gap, traces
   29 / 57 / 17. Injection-level permutation tests (5,000): short coverage vs fault p 0.45–0.76,
   vs root p 0.27–0.58 (no association). Injection-weighted baselines on 70 tier-A injections:
   majority 0.586, alert entity 0.374.
5. **metrics_only.** Applicable: RCAEval 360, Nezha 97, AIOps2025 384, RCA100 103.
6. **AIOps2025 short-log incidents** (report with and without): `aiops2025.04ad6e5c9dba28d6`,
   `0d1dbec5fb1c426e`, `1538f32c07e6b341`, `d953c265cb0c8016`, `e94fcb2acf4ae4b5`; still associated
   with fault (p 0.0048) and root (p 0.0016) at the injection level (one record per injection).

## Defects found and fixed

- **B-tier records beside held-out groups.** `within-*` put every B-tier record in train, even
  when its group was in test. `verify-splits` caught it on the first AIOps2025 manifests
  (`GROUP_SPANS_SPLITS`); those two manifests, minutes old and never used, were deleted. B-tier
  records now train only when their group is not held out (`tier_b_dropped_held_out_group`;
  AIOps2025 retrieval drops 53). RCAEval and RCA100 manifests were unaffected (same hashes).
- **Degenerate within split.** Day plus fault-cell grouping makes all 400 AIOps2025 incidents one
  group; `headline_ok` now also requires ≥ 3 groups for within splits, so
  `within-aiops2025-grouped` is flagged (exit 3) instead of passing as 100 % test.
- **Short pod-template hash.** `identity.DEPLOYMENT_POD` required 8–10 characters; four RCA100
  `checkout-5489989-*` pods were unmapped or infra (102 metric and 11,740 log rows in
  `rca100.9fbfe46db86017ff`, `rca100.e3d9b46aef9f46e8`; neither root is checkout). Short hashes
  are now accepted in Kubernetes' vowel-free alphabet only, so `ts-config-mongo` stays plain;
  across all four maps only these four names change match. RCA100 adapter 1.0.2; a forced rebuild
  reproduces digest `64b40b1d…`.

## Splits (seed 0; `verify-splits` exit 0, 16 OK)

| Manifest | Train / val / test | Groups (largest) | Test share | headline_ok |
|---|---|---|---|---|
| within-rcaeval-grouped-0-e9b2c81c | 374 / 143 / 218 | 91 (40) | 0.30 | yes |
| within-rcaeval-retrieval-0-45ef97c3 | 451 / 140 / 144 | 620 (15) | 0.20 | yes |
| loso-rcaeval-{online-boutique,sock-shop,train-ticket} | 490 / – / 245 each | 91 (40) | 0.33 | yes |
| eval-only-rcaeval-0-87d5bcc3 | – / – / 735 | 91 | 1.0 | yes |
| eval-only-nezha-0-38cde4e0 | – / – / 101 | 7 (34) | 1.0 | yes |
| within-aiops2025-grouped-0-f92dd409 | – / – / 318 | 1 (400) | 1.0 | **no** (degenerate) |
| within-aiops2025-retrieval-0-bb231eaa | 141 / 36 / 170 | 17 (24) | 0.49 | yes |
| eval-only-aiops2025-0-f92dd409 | – / – / 318 | 1 | 1.0 | yes |
| within-rca100-grouped-0-753fb47c | 48 / 4 / 51 | 28 (14) | 0.50 | yes (val has 4 tasks) |
| within-rca100-retrieval-0-3bfc8743 | 69 / 15 / 19 | 72 (7) | 0.18 | yes |
| eval-only-rca100-0-b8a32300 | – / – / 86 | 28 | 1.0 | yes |
| xdata-rcaeval-to-nezha-0-28246781 | 735 / – / 101 | 98 | 0.12 | yes (shared system names OB, TT) |
| xdata-rcaeval-to-aiops2025-0-730c1c48 | 735 / – / 318 | 92 | 0.30 | yes |
| xdata-rcaeval-to-rca100-0-a2a83b78 | 735 / – / 86 | 119 | 0.10 | yes |

No xdata manifest dropped a train incident for sharing a group with test.

## Integration (phase 11)

`run_grid prepare configs/canonical_pilot.yaml` on real RCAEval (exit 0, 23 min, no LLM call):
30 test-role incidents (10 per system), 180 condition variants in 30 pairs (`full`, `no_log`,
`no_metric`, `metrics_only` 30 each; `no_trace`, `blind_root`, `blind_nonroot` 20 each, as the
matrix allows), 374 train-role store incidents. Evidence length: median 782 chars (`full`), maximum
4,436 against `MAX_CHARS` 14,000; 0 label-key or source-path hits in 404 evidence files. None of the
4 excluded incidents was selected. Tests: full suite 212 passed (Windows); bundle and canonical
run_grid tests re-run after the last edits, 8 passed.

## Not done here

- Commit of `data/reports/` and `data/splits/` (plan DoD 3): no commit was requested.
- Phase 08 (B datasets) deferred to M3.

## Addendum (2026-10-14, release preparation)

`tests/test_realdata_identity.py` (16 real-data tests) passes on `rcaeval-2f4bf056cb8a`: the six
aliases resolve only in their own system, the only multi-spelling ids in all four datasets are the
two intended merges, no infra id is a candidate, and each of the 4 shared-cluster incidents has
system-scoped candidates, foreign-container rows that keep their raw name and carry the infra id,
a label root that matches its case path and has telemetry, deterministic evidence without foreign
services or label text, and no visible-zone leakage. The owner's condition was met, so the 4
exclusions are lifted (`status: lifted`); `eval-units-rcaeval.json` now has 735 primary records.
Splits and condition matrices do not depend on exclusions and are unchanged.
