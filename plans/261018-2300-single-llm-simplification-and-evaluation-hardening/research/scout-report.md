# Scout report: Jev footprint, evaluation gaps and obsolete components

Scouted on 2026-10-18 at `fee95cf`, with the uncommitted turn-2 to turn-4 work on top (raw LLM
outputs, `rca.visibility`, the four visibility configs). Paths are relative to
`nt114-rca/nt114-rca/` unless they start with `/plans` or `/research`. No code was changed while
scouting.

## 1. Where Jev and the multi-model routing live

Jev is isolated well. It reaches the rest of the code through four seams only: the decision
modules, one schema constant, two manifest fields, and the analysis tables.

| Component | Lines | Role | Fate under a single-LLM architecture |
|---|---|---|---|
| `src/rca/jev.py` | 307 | TypeSafe client, state builder, questions, cache, mock | Delete |
| `src/rca/decide.py` | 280 | Builds Jev states from the grid, runs stages 1 and 2, writes `decisions.jsonl` / `jev_raw.jsonl` | Delete |
| `src/rca/gate.py:180-228` | ~50 | `jev_policy`, `jev_scores`, `tune_jev_floor` | Delete |
| `src/rca/gate.py:260-284` | ~25 | R1/R2 route-matched controls (exist only to judge Jev's routing) | Delete |
| `src/rca/gate.py:23-57,123-176` | ~90 | Legacy model-name action table, 3-action threshold policy, GBR learned policy, leave-one-system-out | Delete (the learned policy is itself a second decision model) |
| `src/rca/gate.py:59-117,230-257,293-299` | ~90 | `reward`, `outcomes`, `evaluate`, C1/C2 coverage-matched controls, oracle | Keep and generalise into a single-model selective evaluator |
| `src/rca/analyze.py:34-51` | 18 | Headline guard (mock / DEV / mixed versions, plus Jev checks) | Keep; drop the Jev checks, add new guards |
| `src/rca/analyze.py:110-153,192-221` | ~75 | `policy_table`, `jev_score_table`, `decision_report` | Replace |
| `src/rca/schema.py:38-44` | 7 | `DECISION_STATE_ALLOWED_KEYS` (Jev state allowlist) | Delete |
| `src/rca/run_grid.py:37,472-476` | ~8 | `MODEL_ROLES = (primary, escalation, replication)` and the role check | Drop `escalation` |
| `src/rca/run_grid.py:390,407-408` | 3 | Manifest `jev_question_version`, `jev_pinned_model` | Delete |
| Configs | – | `jev:` blocks and `mock-escalation` models in `configs/exp/smoke-offline.yaml:30-34`, `smoke-canonical.yaml:26-30`, `dev-pilot.yaml:39-43`; escalation profiles in `configs/hardware/rtx4080-laptop-12gb.yaml:152,161` | Edit |
| Docs | – | `README.md:14,72,74`; `docs/data_contract.md:4,13,198-242` (§8 Jev decision state); `docs/gpu_deployment.md:5,35,42,73,95-101,167-201` | Edit |
| Tests | – | `tests/test_jev.py` (11 tests), `tests/test_decide.py` (10), Jev parts of `tests/test_leakage.py` (`MODEL_FACING` lists `gate.py`, `jev.py`; lines 72-73, 136-153, 199-251) and `tests/test_stats.py:94-127` | Delete or rewrite |

Side effects of removal:

- **Licence decision D3 becomes moot.** AIOps2025 and RCA100 evidence never leaves the machine,
  because no external API remains (`decide.EVIDENCE_WITHHELD`).
- **No credential remains in the pipeline.** `TYPESAFE_API_KEY` was the only
  credential the pipeline read (`jev.py:30`).
- **No paid or non-deterministic external call remains.** Results become reproducible from
  the LLM cache alone, whereas Jev had no seed (`/plans/261015-0047-.../design/research-design.md:253`).

## 2. Evaluation gaps found while scouting

1. **No paired-contrast pipeline exists.** The preregistered confirmatory contrasts are
   per-injection paired differences: ΔAC@1, the difference-in-differences, Δgap and ΔAUROC
   (`/plans/261015-0047-.../design/research-design.md:196-222`). No code computes any of them.
   `metrics.sign_flip_test` and `metrics.per_injection` (`metrics.py:198-242`) are never called
   from `src/` (verified by grep). The only paired test in `analyze` is
   `retrieval_tests` (`analyze.py:174-189`). It is an unweighted exact McNemar on `case_id`. It
   ignores injection clustering, and its Holm family is "every retrieval row", which no protocol
   defines.
2. **Two analysis paths disagree.** The legacy `cell_table` (`analyze.py:156-171`) is unweighted
   and uses 10-bin ECE. `weighted_cell_table` (`analyze.py:85-107`) is injection-weighted with
   support ECE. The CLI default (`analyze.py:226-256`) still prints the legacy tables.
3. **Only AC@1 has a CI.** AUROC, AURC, Brier and the gap are point estimates
   (`analyze.py:92-106`).
4. **`excluded_from_primary` is loaded but never applied** (`score.py:40`, the `excluded`
   column). It is latent today because all exclusions are lifted.
5. **Within-cell weights do not make contrasts paired.** `analyze.reweight` (`analyze.py:71-78`)
   equalises injections inside a cell. Conditions with different applicability (`blind_root` 228
   of 360 on RCAEval) still need an explicit intersection before a paired difference.
6. **The output schema caps the ranking at 5** (`llm.py:50`). A miss beyond rank 5 is stored as
   `n_candidates + 1` (`score.py:25`), so mean rank and MRR are biased and H3's rank analysis is
   truncated.
7. **Thresholds tuned on DEV meet a shifted test mix.** 94 test incidents sit in strata that
   exist only in test (`/research/01_experimental_readiness.md` §3). No shift diagnostic exists.

## 3. Baseline fairness

- B1 max-z reads the Metrics block only (`baselines.py:38-44`), while the LLM reads all three
  modalities. No non-LLM baseline uses logs or traces. The evidence order itself (services sorted
  by z, `evidence.py:235-240`) gives the LLM a ranking hint that B1 reproduces. The LLM must be
  shown to beat an "evidence order" baseline across all blocks, not only B1.
- B3 majority uses the prior of the **scored test set** (`baselines.py:65-67`). Where a train
  role exists, the prior must come from train. On eval-only sets it can only be a labelled
  reference, and the code already says it is "not a fair comparator".
- B2 BARO is documented only, and the plan installs the `RCAEval` package in a separate
  environment (`/plans/261015-0047-.../phase-04-...md`, task 1). That was forbidden when the
  scout ran. The Internet and install policy of 2026-10-18 now allows it, in an isolated
  environment (phase 05, task 5a).
- B0 and B1 run on `full` and metric-bearing conditions only. LLM rows exist for every applicable
  condition, so a joint table must show the cells where a baseline has no row.

## 4. Cost and reproducibility

- Cost per cell is prompt and completion tokens plus wall latency (the grid row, `run_grid.py:557-581`). Cached
  rows replay the original latency. Evidence preparation, measured at about 18 s per RCAEval
  incident in the smoke run of 2026-10-18, is not recorded anywhere. Retrieval time and the n = 10
  sampling multiplier are not reported as cost.
- `manifest.json` records commit, dirty flag, bundle, split, models and sampling
  (`run_grid.py:388-413`). It does not record the Python and package versions, `BUILDER_VERSION`,
  the config text, or the split manifest digest. There is no script that regenerates every table
  (the old plan's Definition of Done lists `reproduce_tables.sh`, which does not exist).

## 5. Leakage controls already in place (keep)

- Evidence files hold no labels (schema 2); the label is joined only at scoring.
- Candidates are shuffled per incident (`evidence.py:302-305`).
- The `precedent` store excludes the query's own manifest group. The `no_precedent` oracle
  reads labels and is refused by the decision layer (`decide.py:62-64`); that guard must move to
  the new evaluator.
- `rca.visibility` writes label-derived flags only outside the evidence directory
  (`visibility.py:141-148`). A test proves that model-facing modules never import it
  (`tests/test_visibility.py:97-99`).

Not covered: a text-level near-duplicate check between test evidence and store evidence. Cell
twins are 0 of 218 on the grouped split, but nobody has measured textual near-duplicates.

## 6. Other obsolete or redundant components

- **Legacy RCAEval `data_root` path:** `run_grid.select_cases` and the non-canonical branch of
  `prepare`/`load_evidence` (`run_grid.py:302-345`), `data.discover_cases`/`load_case`,
  `configs/pilot.yaml`, `configs/synthetic.yaml`, `tests/test_legacy_compat.py` and
  `tests/test_legacy_golden.py`. Every experiment config is canonical. `legacy_view.py` is
  **not** obsolete: the canonical path uses it to build telemetry frames
  (`run_grid.py:230`).
- **Vietnamese and English docstrings are mixed** in `gate.py`, `analyze.py` and `run_grid.py`.
  This is cosmetic; it should be addressed only in files that are rewritten anyway.

## 7. Live state at planning time

- The visibility audit jobs (`bghjdbdqv` for RCAEval; `bkj5zzdec` for Nezha → RCA100 → AIOps2025)
  are running.
  - Nezha finished with exit 0 (97 incidents).
  - RCAEval had 277 of 361 evidence files at 23:06.
  - RCA100 had 47 evidence files.
  - AIOps2025 had not started.
- **Each job starts `rca.visibility` in a new Python process after `prepare`, so it imports
  whatever `src/` holds at that moment.** No source file may change until both jobs have exited.
