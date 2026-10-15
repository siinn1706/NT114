# Risks and mitigations

Likelihood (L) and impact (I): H/M/L. Owner: R1 = researcher 1 (pipeline/experiments), R2 =
researcher 2 (analysis/writing); with one researcher, both roles fall to R1.

| # | Risk | L | I | Trigger / signal | Mitigation | Owner |
|---|---|---|---|---|---|---|
| R1 | Linux GPU gate not run or failing | M | H | Not done by 2026-10-23 | M1 continues on CPU; M2 start moves; week-6 checkpoint absorbs ≤ 1 week | R1 |
| R2 | Jev access or rate limit blocks E4 | M | H | No key by 10-30; 429s in M2 | Jev is mandatory and cannot be dropped: escalate to the owner by 11-06; cached, resumable calls spread over days; Cloudflare/OpenRouter adapters only **if** D1 requires and they can pin `jev-1.13.0` | R1 |
| R3 | `jev-latest` changes during the project (1.14 shipped 2026-10-14) | H | H | response `model` ≠ pin | Pin `jev-1.13.0`; version guard stops the run; O4 measures drift | R1 |
| R4 | Jev adds no signal (H4b fails) | M | M | DEV: Jev P(accept) AUROC ≈ 0.5 | A valid negative result; C1/C2 make it interpretable; the paper still stands on RQ1–3 | R2 |
| R5 | Jev mis-reads numeric confidence | M | M | J-noconf ≈ J-full on DEV | Banded text encoding; disclose; E8 quantifies | R1 |
| R6 | Primary model too weak (AC@1 ≈ random) | L | H | DEV pilot gate | Switch primary per model-selection §3 before the freeze | R1 |
| R7 | Retrieval has no effect (±2 pp) | M | L | E2 on DEV/RCA-T | RQ5 reported as negative; focus RQ1–4 | R2 |
| R8 | Underpowered RQ4 on RCA-T (MDE ≈ 8.5 pp, n = 218) | H | M | CIs straddle 0 | Simulation-based power in M2; replication on 3 external sets; pooled secondary estimate | R2 |
| R19 | Retrieval looks strong only because of repeated injections | H | H | Same-cell twins in the store (138/144 on the retrieval split) | Primary split is cell-held-out (0/218); recurring regime is a separate, labelled E2b | R2 |
| R9 | Label leakage through grid rows into Jev | L | H | Permutation-invariance test fails | Decision inputs built from evidence + LLM aggregates only; end-to-end label-store permutation and canary tests (architecture §7) | R1 |
| R10 | Stale caches mix prompt or model versions | M | H | Mixed `prompt_version` in a table | Versioned cache keys; `analyze` refuses mixed versions | R1 |
| R11 | DEV contamination of reported results | L | H | `val` uid in a headline table | Guard + test; DEV never reported | R2 |
| R12 | NC-licensed evidence sent to a third-party API without permission | M | H | D3 unanswered when E4 starts | E4 on AIO/R100 waits for D3; RCAEval/Nezha (CC BY / MIT) proceed | Owner |
| R13 | Timeline overrun with 1 researcher | H | H | M3 not done by 11-27 | Cut order: phase 05 → O-extensions → E7 retrieval arm → E3 on AIO; the minimum set stays | Owner |
| R14 | GPU tier S only (12 GB) | M | M | D2 | Escalation pair 4B → 9B; disclose | R1 |
| R15 | Thinking/guided-JSON incompatibility in vLLM | M | M | Parse rate < 99 % | Non-thinking template; vLLM pin; switch model | R1 |
| R16 | BARO package conflicts with the main env | M | L | Install failure | Separate venv; B2 optional if it cannot run (B0, B1, B3 remain) | R1 |
| R17 | Secrets committed | L | H | `.env` not ignored (verified 2026-10-15) | Phase 01 (M0) adds `.env`, `results*/` and `paper/artifact/` to `.gitignore`; keys only in env vars | R1 |
| R18 | Holidays cut weeks 10–11 | H | M | Calendar | Experiments end 2026-12-18 | Owner |
