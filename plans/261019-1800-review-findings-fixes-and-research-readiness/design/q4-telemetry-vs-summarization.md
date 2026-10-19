# Q4: missing telemetry vs summarisation loss (proposed design, not approved)

## Why the current instruments cannot answer it

- Availability is manipulated (`no_metric`, `no_log`, `no_trace`, `metrics_only`), but the
  summariser is fixed (`evidence.build`, builder v3: `max_services` 10, `top_metrics_per_svc` 3,
  `MAX_CHARS` 14,000 with truncation). Every condition therefore confounds "less telemetry" with "a
  different summary of what is left".
- `visibility.named*` says whether the root's **name** appears in the summary. A name can appear with
  no anomaly attached, and a real anomaly can be summarised under another line. Name visibility is
  neither raw support nor summary retention.

## Factors (paired within incident)

| Factor | Levels | Notes |
|---|---|---|
| A: telemetry availability | `full`, `no_metric`, `no_log`, `no_trace` (existing conditions) | Same frozen ablation code |
| S: summariser | S0 = builder v3 (frozen, primary arm); S1 = same selection, larger budget (more services and metrics per service); S2 = raw-excerpt summariser (fixed-length raw lines around the anchor, no ranking by z-score) | S1 and S2 are new builders with their own fingerprints; v1 evidence is never replaced |
| Budget | Each (A, S) cell is truncated to the same token budget B, measured with the served model's tokenizer; two budgets (B_low ≈ S0's p50, B_high ≈ S0's p95) | Holds prompt length fixed so a summariser cannot win by being longer |

Every incident gets every applicable (A, S, B) cell from the same model, prompt v1 body, n = 10.

## Independent assessments (eval-only, label-reading, never in a prompt)

1. **Raw support R(i, a)** per incident i and availability a: does the raw telemetry still available
   under a contain a root-attributed anomaly? Defined per modality on the raw frames, not the summary:
   metric robust z of the root above a fixed threshold, error-log template rate change of the root,
   trace error/latency change on root spans. Threshold fixed on DEV, frozen before test.
2. **Summary retention K(i, a, s, b)**: given R = 1, does the summary text carry that anomaly for the
   root (the specific line type, not only the name)? Computed by matching the raw-support signal to the
   evidence line of the root in the summary.
3. Validation: on a DEV sample, a human (or the owner) checks R and K on ~50 incidents; report
   agreement. B1m and B1 max-z on raw frames give a second, model-free view of R.

## Decomposition and estimands

- **Availability loss** = P(error | A = a, S fixed) − P(error | A = full, S fixed), on incidents
  with R(i, a) = 0, i.e. the evidence is gone from the raw data.
- **Summarisation loss** = P(error | S0) − P(error | S1 or S2) at fixed A and B, on incidents with
  R(i, a) = 1 and K(i, a, S0, b) = 0, i.e. the signal existed but the summary dropped it.
- Interaction A × S as a paired difference-in-differences on the injection-level intersection
  (`contrasts.py` `did`), with sign-flip test and cluster bootstrap.

All contrasts are paired within incident, injection-weighted and reported on the applicable
intersection, as protocol v2 §3 requires.

## Feasibility and cost

- Cells: 4 A × 3 S × 2 B = 24 per incident, against 8 conditions × 2 retrieval arms in the DEV pilot.
  Restrict to `retrieval = none` and the 108 RCAEval test injections with at least two modalities
  (69 with all three; counts from plan 261019-1501) to keep it near the pilot size. Single-modality
  conditions apply only where the modality exists, so each contrast is on its applicable intersection.
- Power: rerun `h1_power.py`-style simulation for the DiD with the DEV-measured discordance before
  committing; the single-modality DiD in plan 261019-1501 was underpowered (0.03-0.46).

## Gates before implementation

1. Owner approves S1/S2 as new arms and the budget rule.
2. R and K definitions frozen on DEV; agreement reported.
3. Phases 01, 02 and 05 of this plan done (store binding, signature, stratified CIs).
