---
title: "Phase 3: M2 — Real-model inference, live Jev on DEV, freezes"
status: todo
priority: P1
effort: 5 person-days + ~1 GPU-day (week 3, 2026-11-02 → 11-06)
dependencies: [phase-01, phase-02]
---

# Phase 3: M2 — Real-model inference, live Jev on DEV, freezes

## Context links

[Model selection](research/model-selection.md) §3–5 · [Jev verification](research/jev-api-verification.md) §5–6 ·
[Research design](design/research-design.md) §6 (DEV) · [Architecture](design/architecture.md) §4

## Goal and research justification

Turn the harness into a measurement instrument using **DEV only** (`within-rcaeval-grouped` val, 143 incidents): verify that
the models serve reliably, freeze the prompt and the Jev wording, and measure Jev's position bias
and repeat stability. Because all of this happens on DEV, the test sets stay untouched. The
phase ends by freezing the preregistration.

**This is the exact point where the GPU machine becomes necessary:** task 1 (vLLM serving). All
earlier work runs on CPU.

## Dependencies

Phase 02 done; phase 01 tasks 1 (Linux gate), 2 (hardware), 3 (model probe), 4 (Jev access).

## Tasks

1. **Serve the primary model** on the GPU machine with the probe's pinned revision:
   `vllm serve <repo> --revision <sha> --max-model-len 16384 --enable-prefix-caching
   --gpu-memory-utilization 0.85 [--quantization ...] [--limit-mm-per-prompt ...]`. Record the vLLM
   version in the manifest.
2. **Pilot on DEV** (`configs/exp/dev-pilot.yaml`: DEV, all conditions, retrieval none + hybrid
   precedent, n = 10). Gates:
   - parse rate ≥ 99 % per condition (`aggregate.parse_rate`);
   - prompt length ≤ 12k tokens at p99;
   - full-condition AC@1 above the B1 max-z heuristic and above random (CIs reported, DEV only);
   - wall-clock per incident × condition, extrapolated to the M3 volume, fits ≤ 3 GPU-days;
   - <!-- Red team B10 --> for the escalation model at n = 10: measured KV-cache headroom,
     concurrent sequences and tokens/s are recorded; if 27B at 4-bit cannot sustain the E3 volume
     in ≤ 1.5 GPU-days, E3 drops to RCA-T + NEZ and the change is logged before the freeze.
   If the parse rate fails: fix the prompt or the guided-decoding settings. If accuracy fails:
   switch the primary per model-selection §3 and log the switch.
3. **Prompt freeze.** At most 3 prompt iterations on DEV, each logged with its DEV metrics in
   `decisions.md`. Freeze `PROMPT_VERSION = "v1"`. Thinking stays off.
4. **Serve the escalation model** (and later the replication model) one at a time; run DEV with
   the frozen prompt; confirm the parse rate gate.
5. **Live Jev on DEV** (`configs/exp/jev-dev.yaml`):
   - stage 1 and both stage-2 calls for every DEV incident × condition;
   - option-order test: each state with all cyclic rotations of the criteria order; position bias =
     max over options of P(chosen | option in first position) − P(chosen); gate ≤ 0.10, else add a
     per-call shuffle (already default) and report the bias;
   - repeat stability: 3 identical calls with the cache bypassed for 100 states; report the
     agreement rate and the max |Δp|;
   - at most 3 wording iterations of `instructions` and `criteria`, logged; then freeze
     `JEV_QUESTION_VERSION = "q1"`.
6. **J-floor and comparator tuning on DEV** (C3 thresholds, C4 learned policy, Jev-confidence
   floor, LLM confidence recalibration map with isotonic/Platt). Save the fitted parameters as
   `results/dev/tuned.json` (hashed).
7. **Preregistration freeze, in two parts.** <!-- Red team B6 --> Part 1 (LLM: sets, conditions,
   prompt v1, endpoints, power simulation from DEV discordance) is frozen and hashed at the end of
   this phase, before E1. Part 2 (Jev: question wording q1, state encoding, J-floor, the CWA
   final-arm rule) is frozen as a hashed addendum before E4. If Jev access arrived late, only part 2
   moves. Write both hashes to `decisions.md`. From now on the analysis follows it; deviations are
   logged.

## Existing modules to reuse

Phase 02 outputs; `llm.LLM`, `run_grid`, `decide`, `gate.tune_threshold`, `gate.learned_policy`.

## Files

| File | Action |
|---|---|
| `configs/exp/dev-pilot.yaml`, `configs/exp/jev-dev.yaml` | create |
| `src/rca/llm.py` | modify (prompt text v1 only, if a DEV iteration requires it) |
| `src/rca/jev.py` | modify (question wording v1 only) |
| `src/rca/decide.py` | modify (`--rotations`, `--repeat` diagnostic flags) |
| `design/preregistration.md`, `decisions.md` | update (plan dir) |

## Interfaces and contracts

Frozen at exit: `PROMPT_VERSION`, `JEV_QUESTION_VERSION`, pinned model revisions, the Jev pin
`jev-1.13.0`, and `tuned.json`. Any later change = a new version + a rerun of the affected cells.

## Testing strategy

| Check | Pass condition |
|---|---|
| Fast suite on Linux | green |
| DEV pilot gates (task 2) | all four met, or a logged model switch |
| Jev DEV run | error rate ≤ 1 %, `model == jev-1.13.0` on 100 % of rows |
| Position bias, repeat stability | measured and logged (bias gate ≤ 0.10 or disclosed) |
| No test-set access | `grep` over `results/dev/*.jsonl` split roles: only `val` |

## Acceptance criteria / Definition of Done

- [ ] Primary and escalation models serve, with pinned revisions in the manifest
- [ ] DEV pilot gates met; prompt v1 frozen
- [ ] Jev live on DEV with pinned version; wording q1 frozen; bias and stability measured
- [ ] `tuned.json` written from DEV labels only
- [ ] Preregistration frozen and hashed in `decisions.md`
- [ ] Measured throughput confirms M3 fits the GPU budget (or the M3 scope cut list is applied)

## Risks

| Risk | Mitigation |
|---|---|
| Qwen3.5 thinking cannot be disabled together with guided JSON in the installed vLLM | Use the model's documented non-thinking template; else switch primary (model-selection §3) |
| Jev shows strong option-order bias | Shuffle is default; report bias; average probabilities over 2 rotations as a disclosed J variant |
| Jev rate limit too low for M3 volume | Measured here; request a higher limit, or spread calls over days (cache makes runs resumable) |
| Over-fitting the prompt to DEV | ≤ 3 iterations, logged; DEV never reported |

## Security

The GPU machine holds the private bundle: non-commercial use only, no copy to public storage
(release handoff "Restricted data"). The Jev key lives in that machine's environment only. D3
decides whether NC evidence (AIO, R100) may go to Jev; DEV is RCAEval (CC BY 4.0) only.

## Next

Phase 04.
