---
title: NT114-RCA dataset standardization plan
date: 2026-10-14
summary: "Planned canonical incident store, leakage-safe splits and portable bundle; red team found label leaks via Case and no_precedent"
---

# NT114-RCA dataset standardization plan

## What happened
Created `plans/261014-0749-nt114-rca-dataset-standardization-and-validation/`: 12 phases, delivered as milestones M1 (RCAEval only), M2 (Nezha, AIOps2025, RCA100) and M3 (B datasets).

Scouting the raw data found:
- `data.py` mislabels the RE3-TT `ts-route-service_f3_1` cases. A naive fix would make their `case_id` collide with `ts-route-service_f3`, so 3 cases would be skipped silently.
- The Zenodo RE3-SS zip ships 8 `root_cause.txt` label artefacts. The audit doc wrongly said they were HF-only.
- `RE2-OB/checkoutservice_cpu/multi-source-data` duplicates case 1.
- The Nezha metric `TimeStamp` column is offset by +2e8 s from its `Time` string.
- 31 AIOps2025 incidents fall on UTC dates with no archive (time zone still to be determined).
- On Windows, the default cp1252 encoding breaks UTF-8 JSON.

## Decision
- Ground truth goes in separate `visible/` and `eval_only/` zones. Model-facing code receives `VisibleCase` only (the red team showed that `Case` attributes leak labels).
- `precedent` retrieval is label-free and is the only source of Jev's `hit_top_sim`. `no_precedent` is an oracle ablation.
- Two split rules: physical grouping for retrieval experiments, fault-cell grouping for gate and fine-tuning.
- The bundle carries canonical data only. The RCA100 answer key stays in eval_only, private.
- AIOps2025 node faults are B. Multi-entity faults without a single named service are set-scoring only.
- Red team: 14 findings; 13 accepted, 1 partially accepted (scope kept, split into milestones).

## Next steps
Start phase 01 (venv, lock file, golden set) via `/ak:cook`. Phase 02 resolves the remaining UNKNOWNs: Nezha offset prevalence, AIOps2025 time zone, RCA100 entities, RCABench/AnoMod/MSDS label formats, and split group counts.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
