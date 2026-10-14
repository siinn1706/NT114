---
title: "M2 data pipeline: identity fix, eval units, splits, verified bundle"
date: 2026-10-14
summary: "RCAEval identity fix, eval units and exclusions, metrics_only, day/xdata splits, full audit clean, 10.67 GB bundle verified on a copy"
---

# M2 data pipeline: identity fix, eval units, splits, verified bundle

## What happened
Applied the owner's decisions after Phase 07 and finished the M1/M2 data pipeline.
- RCAEval adapter 1.0.1: containers of the other demo (same cluster) become infra by a measured share rule (own <= 5 %, other >= 90 %). 4 incidents fixed; the other 731 are unchanged (identical condition matrix rows, same split hashes).
- New: `metrics_only` condition, `prep eval-units` (injection id, weight, representative, primary exclusion, coverage cause), `configs/eval_exclusions.yaml`, AIOps2025 day grouping, `xdata-*` protocols over two builds.
- Bugs found: B-tier records trained beside held-out groups (verify-splits caught it on AIOps2025); within-aiops2025-grouped collapses to one group (now headline_ok false); `DEPLOYMENT_POD` missed 7-char pod-template hashes (RCA100 checkout pods; adapter 1.0.2, rule limited to the vowel-free alphabet so `ts-config-mongo` stays plain); bundle export crashed on a per-subset licence mapping.
- Audit audit-9338d463a84f: 1,340 incidents, 0 unexplained duplicates/lineage/leakage/split errors. 16 splits OK. Pilot prepare on real RCAEval OK.
- Bundle nt114-data-v1-20261014-0a45570e (10.67 GB) passes verify-bundle --deep on a full copy.

## Decision
Phase 08 deferred to M3 (owner). Linux verification moves to the GPU machine (no WSL distro here). Six aliases stay "owner to confirm"; Redis/TiDB rules confirmed by telemetry.

## Next steps
Copy code + bundle to the GPU machine and run scripts/verify_portability.sh. Owner: confirm aliases, decide whether to lift the 4 RCAEval exclusions, commit nt114-rca (code untracked; bundle records rca_root_tracked false).

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
