# Handoff contract for the LLM + Jev core-code plan

Architecture: Dataset → Adapter → Canonical Schema → Ablation → Evidence → RCA LLM → Confidence →
**Jev Decision Layer** (mandatory default) → Evaluation. This plan delivers everything up to and
including Ablation and the evidence inputs; the next plan owns the LLM, confidence, Jev and
training.

## 1. What the next plan can rely on

| Interface | Provider (this plan) | Guarantee |
|---|---|---|
| `rca.store.CanonicalStore(data_home).incidents(dataset, states=SPLIT_STATES, split_dir=None, role=None)` | phase 03, 10 | Returns visible incident records (no labels) filtered by quality state (`states=None`: all) and, with `split_dir`, by the split assignment and role |
| `CanonicalStore.telemetry(uid, modality, columns=None)` | phase 03 | Lazy pyarrow Table; canonical schema §4 |
| `CanonicalStore.labels(dataset)` | phase 03 | Eval-only `LabelRecord`s; only scoring, ablation and split code may call it (enforced by an import-boundary test) |
| `rca.legacy_view.visible_case(incident)` → `VisibleCase` (no label attributes, `case_id = incident_uid`), `truth(label)` → `Truth`, `legacy_telemetry(store, uid, metric_set="simple")` | phase 05, used in 11 | Same DataFrame shapes as today's `data.load_case`; model-facing code receives only `VisibleCase` |
| `rca.ablate.apply(tel, condition, root_service, nonroot_target=None)` + condition matrix | phase 10 | Conditions `full`, `no_metric`, `no_log`, `no_trace`, `blind_root`, `blind_nonroot`, `metrics_only`; `variant_id`, `pair_id` |
| Split manifests | phase 10 | `within-*-grouped`, `within-*-retrieval`, `loso-*` (one directory per fold), `eval-only-*`, `xdata-rcaeval-to-{nezha,aiops2025,rca100}`; immutable and hash-verified (16 manifests, `verify-splits` OK) |
| `reports/eval-units-<dataset>.json` | phase 10 | Per record: `injection_id`, `weight`, `representative`, `excluded_from_primary`, log/trace coverage cause (see [data_contract.md](../../../nt114-rca/nt114-rca/docs/data_contract.md) §6) |
| Retrieval store from train split | phase 10, 11 | Built from all train-role `full` evidence of a `within-*-retrieval` split. `precedent` = label-free (headline, Jev source); `no_precedent` = oracle ablation (`oracle_store: true`), never a Jev input. `gate.action_table` defaults to `store_mode="precedent"` and raises on `no_precedent` unless `oracle=True` (fixed 2026-10-14: the default was `no_precedent`, which `analyze --gate` used) |
| Export bundle + `verify-bundle` | phase 12 | Byte-identical transfer; offline use on the GPU machine |

## 2. Decision-state inputs for Jev (data side)

The Jev state may contain only fields derivable from the visible zone and model outputs:

| Field | Source | Allowed |
|---|---|---|
| Evidence text, truncated | `evidence.build` on the condition view, with the per-dataset options from `configs/prep.yaml` `evidence:` (`legacy_view.evidence_kwargs`). Nezha (owner decision 2026-10-14, option b): logs/traces are compared only inside the contiguous data stretch around the anchor (rows ≤ 30 s apart), rates use the seconds covered, and under 30 s of pre-anchor data is stated as "no pre-incident baseline". The same segment mode applies to AIOps2025 and RCA100 with a 60 s gap; under 30 s of post-anchor data is stated as "less than 30 s after incident start; no comparison possible" (evidence builder v3). Metrics and RCAEval keep the fixed 10 min / 5 min windows. Evidence caches key on the canonical build plus the evidence fingerprint (builder version, per-dataset options, legacy-view version and metric alignment), so changing evidence logic never reuses stale outputs | yes |
| Modality availability after the condition (`has_metrics`, `has_logs`, `has_traces`) | condition view (`ablated` and natural absence both → false) | yes |
| Evidence features (`max_metric_z`, `n_flagged_services`, `z_gap_top2`) | `evidence.build` | yes |
| `n_candidates`, `system` | visible record | yes |
| Retrieval similarity of the top hit | train-split store, `precedent` mode only | yes |
| Retrieval similarity from `no_precedent` (oracle) rows | label-conditioned mask | **never** |
| LLM answer, verbal confidence, consensus confidence | LLM layer (next plan) | yes |
| Root service, fault type, label artefacts, masked-service id, missingness cause, `source_incident_id`, dataset paths | eval-only | **never** |
| `quality_state`, `truth_time`, a source-given window end (AIOps2025/RCA100 `end_time`) | label-dependent (state rolls up label findings; window ends are fault ends) | **never**; `quality_state` selects incidents only |

The allowlist is codified in `src/rca/schema.py` as `DECISION_STATE_ALLOWED_KEYS`; phase 09 adds a
test that `gate.jev_payload` output stays inside it.

## 2a. Evaluation requirements per dataset

- RCA100: `inventory` is the primary root in 56 of 86 tier-A tasks (class imbalance, labels kept
  as given). Every RCA100 result must be reported next to the majority-class baseline (always
  answer `inventory`) and the alert-entity baseline (answer the service of the first alert's
  entity). With equal injection weight over the 70 tier-A injections they score 41/70 = 0.586 and
  0.374; per task they score 0.651 and 0.372. The 103 tasks come from 86 independent injections
  (`group.group_id` links 28 tasks in 11 groups). Log/trace coverage after the alert, by cause
  (`eval-units-rca100.json`): logs 19 covered, 62 export truncated, 22 export gap; traces 29, 57,
  17. Tested at the injection level (one row per injection; 5,000 permutations), short coverage is
  not associated with the fault id (p 0.45–0.76) or the root (p 0.27–0.58), whether an injection
  counts as short when any of its tasks is or when its representative is. Keep the "less than 30 s
  after incident start" note and stratify results by the coverage cause.
- AIOps2025: the campaign day carries fault-type information (MI 0.91 bits, p 0.0005), so
  within-dataset splits group by day (`splits.GROUP_BY_DAY`). With day and fault-cell grouping all
  400 incidents form one group, so `within-aiops2025-grouped` is degenerate (`headline_ok: false`);
  use `within-aiops2025-retrieval`, `eval-only-aiops2025` or `xdata-rcaeval-to-aiops2025`. The 73
  `set-scoring-only` incidents (no single primary root) are excluded from top-1 service accuracy
  and from `blind_root`/`blind_nonroot`, and scored as sets. Five incidents have a log export that
  stops before the anchor (an hourly file missing in the source, `export_truncated` in
  `eval-units-aiops2025.json`); the note is associated with the fault (p 0.0048) and the root
  (p 0.0016), so report every AIOps2025 result with and without these five.
- RCAEval: the 4 incidents whose cluster also ran the other demo were temporarily excluded; after
  the adapter 1.0.1 identity fix passed `tests/test_realdata_identity.py`, the owner lifted the
  exclusion (`status: lifted` in `configs/eval_exclusions.yaml`). No record is excluded from
  primary evaluation in any dataset.
- Protocol deviations from the original benchmarks (agents in AgenticOpsEval see the fault
  window start and end and, in RCA100, the `prompt_text`): our visible record has the start or
  first alert only, a fixed window, no description text (AIOps2025) or only the alert title and
  entity (RCA100). Results are therefore not directly comparable with published AgenticOpsEval
  numbers.

## 2b. Evaluation protocol (owner decisions 2026-10-14)

The original benchmark data and labels are preserved unchanged; the protocol below is our
leakage-safe modification and must be described as such in any report.

1. **Units.** The independent unit is the injection (`injection_id` in `eval-units-<dataset>.json`),
   not the task, record, condition variant or retrieval variant. RCA100 keeps all 103 tasks, but
   statistics use 86 injections: equal injection weight (`weight`) and cluster bootstrap
   confidence intervals that resample injections. A secondary sensitivity analysis scores only
   `representative` records (one per injection, smallest uid, label-free choice).
2. **Splits.** Records of one injection never fall in different splits (union on `group_id`;
   `verify-splits` checks it). Training data come only from train-role records.
3. **Paired conditions.** Missingness conditions, including the `metrics_only` baseline, are
   compared on identical incidents (paired by `pair_id`); a condition variant is never a new
   sample.
4. **Strata.** Report results separately by dataset, by label granularity (service top-1, pod
   roots mapped to services, set-scoring-only), and by missingness condition, and stratify by
   telemetry coverage cause (`covered`, `export_truncated`, `export_gap`, natural absence).
   Export truncation is not the same as an absent event and must not be scored as one.
5. **Primary exclusions.** Apply `excluded_from_primary` to headline tables only; report the
   excluded records in a secondary table. Currently none is active.
6. **Associations.** Any check of a feature against the label (e.g. coverage vs fault) is done
   at the injection level, never across repeated tasks or evidence variants.
7. **Jev.** Jev stays the mandatory decision layer after the LLM in the core-code architecture;
   its state follows §2.

## 3. Backbone independence

Nothing in the data layer depends on a model family. Token budgets are a config value of the
evidence builder (`MAX_CHARS`), not of the data. Prompt templates stay in `llm.py`. Gemma, Qwen,
Nemotron or others can be swapped by config in the next plan.

## 4. Open items deliberately left to the next plan

- Training-data export format (chat/JSONL for SFT) built from `within-*` train splits.
- Jev field names (`gate.py` TODO at `jev_payload`) and live calls.
- A fourth modality (`events`/`alerts`/`k8s_state`) for RCA100 and Cloud-OpsBench: schema MINOR
  bump, only if the LLM plan needs it.
- OpenRCA adapter after its acquisition completes.

## 5. Acceptance hand-over checklist

Bundle `nt114-data-v1-20261014-6fdd9835`, built from code commit `cd96e9e` (clean); release
record in [release-handoff-nt114-data-v1.md](../reports/release-handoff-nt114-data-v1.md).
It supersedes `0a45570e`. Status 2026-10-14 (prep machine, Windows): items 1–2 pass on a full
copy of the bundle, the Windows suite passes (230), and `run_grid prepare` of
`canonical_pilot.yaml` runs on real RCAEval without an LLM call. All four items remain to be
confirmed on the GPU machine (Linux).

1. `verify-bundle` exit 0 on the GPU machine. — Windows copy: pass. Linux: pending.
2. `python -m rca.prep status` counts equal `bundle.json`. — Windows copy: pass. Linux: pending.
3. `PYTHONPATH=src python -m pytest -q tests` passes on the GPU machine (Linux). — Windows: 230
   passed. Linux: pending.
4. `run_grid prepare` on a canonical config with `limit_per_system: 2` and the `mock` backend runs
   end to end on the GPU machine without network access. — Linux: pending
   (`scripts/verify_portability.sh` step 5).
5. The evaluation follows §2b (injection units, paired conditions, strata, primary exclusions)
   and keeps Jev as the mandatory decision layer.
