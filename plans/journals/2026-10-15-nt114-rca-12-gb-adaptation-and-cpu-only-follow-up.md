---
title: NT114-RCA 12 GB adaptation and CPU-only follow-up
date: 2026-10-15
summary: "Owner decisions D1-D8 recorded; plan adapted to RTX 4080 Laptop 12 GB; capacity estimator, GPU probe, CPU baselines and Jev evidence/mock guards added"
---

# NT114-RCA 12 GB adaptation and CPU-only follow-up

## What happened
- Recorded owner decisions D1-D8 and marked M0 blocked on the Linux gate, the GPU probe and TypeSafe access.
- Adapted the plan to a 12 GB RTX 4080 Laptop: Qwen3.5-4B FP8 primary; Qwen3.5-9B NF4 or Qwen3-8B-AWQ escalation chosen by measurement; Phi-4-mini replication; QLoRA only.
- Added `rca.capacity`, `configs/hardware/rtx4080-laptop-12gb.yaml`, `scripts/gpu_probe.py`, `rca.baselines`, `configs/exp/dev-pilot.yaml` and `configs/exp/baselines-rca100.yaml`.
- `rca.decide` now withholds AIOps2025/RCA100 evidence from Jev and refuses mock Jev on real-LLM grids. Live LLM backends require a revision.
- Tests: 251 fast and 40 real-data passed. In the real-data smoke run, no AIOps2025/RCA100 Jev request carried evidence.

## Findings
- Prompts are short: full-condition p95 is about 1.1k tokens, and about 4.5k with 3 retrieved precedents, so an 8k context is enough.
- B3 reproduces the protocol on RCA100 tier A: 0.586 / 0.374. The alert entity can lack `::`, which first cost one task.
- No official FP8 or 4-bit Qwen3.5 small checkpoint exists.

## Next steps
- Owner: GPU probe, Linux gate, TypeSafe key and model string, D3 licence check, D6 alias evidence.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
