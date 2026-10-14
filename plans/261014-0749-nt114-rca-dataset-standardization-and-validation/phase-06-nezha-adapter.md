---
phase: 6
title: "Nezha adapter"
status: completed
priority: P2
effort: "2d"
dependencies: [5]
---

# Phase 06: Nezha adapter

## Goal
Add Nezha (Online Boutique and Train Ticket, metrics/logs/traces) as the second A benchmark, with
stream windowing, pod-to-service mapping and the documented timestamp rule.

## Inputs
- `RCA_ROOT/data/raw/nezha/git-d8140101fdb4/rca_data/<date>/`
- Phase-02 profile and Nezha gate outcome (`data/reports/compatibility-matrix.json`)
- Spec: [design/adapter-contracts.md](design/adapter-contracts.md) §3.2

## Outputs
- `RCA_ROOT/data/canonical/v1/nezha/`, `data/reports/quality-nezha.json`

## Files
- Create: `RCA_ROOT/src/rca/adapters/nezha.py` — `FAULT_FAMILY` (`cpu_contention, cpu_consumed→cpu;
  network_delay→network-delay; return, exception→code-defect`; any other value → `unknown` with a
  finding), metric-name table (`CpuUsageRate(%)` → `cpu-usage-rate-pct`, ...), stream reader over
  minute files
- Create: `RCA_ROOT/tests/test_adapter_nezha.py`; extend `tests/test_realdata_samples.py` (`nezha`)
- Modify: `RCA_ROOT/configs/service_aliases.yaml` only if the profile shows a collision

## Tasks
1. Tests first (T11) with fixtures reproducing: the +2e8 `TimeStamp` offset, `ParentID=root`,
   minute files around a window boundary, two incidents 8 minutes apart, a pod name per pattern.
2. Discovery and labels from `fault_list.json`; system by date with the pod-name check.
3. Window: config `windows.default` (or a `nezha` override if the profile shows streams are
   shorter); list minute files overlapping the window; clip at stream edges with flags.
4. Metrics: `Time` string is the time base; `TimeStamp` used only when within 60 s.
   Each numeric column → one metric; entity = pod; service via `pod-to-deployment`.
5. Logs: parse nested `Log` JSON defensively; count failures.
6. Traces: verify the Duration unit per file; convert to ns.
7. `BASELINE_CONTAMINATED` findings computed in the adapter from the incident list (cheap, within
   one dataset).
8. Build and validate; phase report with counts and findings.

## Tests
- T11; realdata: 101 incidents discovered (56 OB, 45 TT) or a documented difference.

## Completion criteria
- 100% of incidents have records; A-tier incidents satisfy the root ∈ candidates invariant or are
  quarantined with reason.
- If the gate failed for metrics, metrics are `corrupted` (not dropped) and the report says so.
- ≥95% of accepted incidents have all three modalities present in [t−600 s, t+300 s] (gate
  threshold); otherwise the shortfall is listed per incident.

## Risks and rollback
- Overlapping windows inflate storage (each incident stores its own slice): measured in the
  report; acceptable at Nezha's size (2.8 GB raw).
- Rollback: delete `data/canonical/v1/nezha/`.
