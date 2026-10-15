# Model selection and hardware (2026-10-15)

**[F]** = stated by an official release or model card found in this session; **[S]** = only
secondary sources found, must be confirmed on the model card in M0; **[A]** = estimate.

## 1. What the task needs from the RCA LLM

1. A ranked list of ≤5 services, drawn from a given candidate list (enum-constrained JSON).
   `llm.schema()` already enforces this with vLLM guided decoding.
2. Prompts measured at p95 ≈ 1.1k tokens without retrieval and ≈ 4.5k with 3 precedents (§4.1),
   so an 8k context is enough.
3. Ten samples at T = 0.7 per prompt (consensus confidence). vLLM shares the prefill across
   `n`, so the cost is mostly prefill.
4. A verbal confidence (0–100) and an `insufficient_evidence` flag in the same JSON.
5. Thinking/reasoning traces are **not** needed for the main grid. They multiply tokens 5–20×,
   and they interact badly with guided JSON on some parsers. Thinking mode is an optional ablation.

The model does not need tool use, vision or long context. On the 12 GB GPU (D2) that favours a
3–4B instruct model as primary and a 4-bit 8–9B sibling for escalation (§3).

## 2. Candidates

| Model | Licence | Params (active) | Released | Notes |
|---|---|---|---|---|
| Qwen3.5-9B | Apache-2.0 [S] | 9B dense | 2026-03 [S] | Small Qwen3.5 series (0.8B–9B); native vision; hybrid thinking expected [S]; structured output reported [S] |
| Qwen3.5-4B | Apache-2.0 [S] | 4B dense | 2026-03 [S] | Fits 12 GB at bf16 [A] |
| Qwen3.5-27B | Apache-2.0 [S] | 27B dense | 2026-02-24 [S] | Natural escalation sibling |
| Qwen3.5-35B-A3B | Apache-2.0 [S] | 35B MoE (3B) | 2026-02 [S] | Fast, but all experts must sit in memory |
| Gemma 4 E4B | Apache-2.0 [S] | ~4.5B effective | 2026-04-02 [S] | 128k context; text+image+audio |
| Gemma 4 26B-A4B | Apache-2.0 [S] | 26B MoE (~4B) | 2026-04-02 [S] | Cross-family mid model |
| Gemma 4 31B | Apache-2.0 [S] | 31B dense | 2026-04-02 [S] | Cross-family large |
| NVIDIA Nemotron 3 Nano 30B-A3B | NVIDIA Nemotron Open Model License [S] | 30B MoE (3B) | 2025-12 [S] | Needs `--trust-remote-code` and a custom reasoning parser in vLLM [S]; reasoning on by default, toggled via `enable_thinking` [S] |
| Qwen2.5-7B-Instruct-AWQ | Apache-2.0 [F] | 7B | 2024 | Current pilot config; legacy smoke only |

Sources: [Artificial Analysis on Qwen3.5 small models](https://artificialanalysis.ai/articles/qwen3-5-small-models),
[Gigazine 2026-03-03](https://gigazine.net/gsc_news/en/20260303-qwen-3-5-small),
[DataNorth: Gemma 4](https://datanorth.ai/news/google-releases-gemma-4-open-models),
[Gemma (Wikipedia)](https://en.wikipedia.org/wiki/Gemma_(language_model)),
[Nemotron 3 Nano card mirror](https://dell.huggingface.co/models/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16),
[Jetson AI Lab: Nemotron 3 Nano](https://www.jetson-ai-lab.com/models/nemotron-3-nano-30b-a3b).
Search results disagreed on context lengths (32k vs 262k for small Qwen3.5) and on whether a
Gemma 4 12B exists. Neither affects this design (≥16k is enough), but the M0 model probe records
the official card values.

No public RCA benchmark ranks these exact checkpoints on RCAEval-style evidence. Reasoning ability
for RCA is therefore measured in our own pilot (M2), not assumed from leaderboards.

## 3. Recommendation for the 12 GB GPU (decision D2, 2026-10-15)

The owner's planned GPU is an **NVIDIA RTX 4080 Laptop, 12 GB** (owner-reported; GPU, driver,
CUDA, PyTorch and free VRAM still to be probed with `scripts/gpu_probe.py`). 14B–27B models are
**not** assumed to run. Every figure below is an **[A]** estimate from
`python -m rca.capacity configs/hardware/rtx4080-laptop-12gb.yaml`, which uses each model's
`config.json` at a pinned revision **[C]**. The M2 gate replaces the estimates with measurements.

Assumptions in the estimate: a serving budget of 10.8 GB (0.90 × 12 GB, at most 12 − 0.6 GB
reserved for display and driver), 1 GB runtime overhead, 10 samples × 400 output tokens per
request sharing one prompt prefix, and fp16 KV. Weight-only formats keep embeddings in 16 bit.

| Role | Model (repo @ revision) | Precision | Weights | KV per request (2k prompt, n=10) | Concurrent requests | QLoRA, seq 4096, micro-batch 1 |
|---|---|---|---|---|---|---|
| **Primary** | **Qwen3.5-4B** (`Qwen/Qwen3.5-4B` @ `851bf6e`), non-thinking | FP8 (on the fly) | 5.3 GB | 0.72 GB | ~6 | ~6.6 GB (fits) |
| Primary fallback | Qwen3-4B-Instruct-2507 (`cdbee75`), text-only, non-thinking | FP8 / bf16 | 4.4 / 8.0 GB | 0.89 GB | ~6 / 1 | ~5.8 GB (fits) |
| Cross-family replication | Phi-4-mini-instruct (`microsoft/Phi-4-mini-instruct` @ `cfbefac`, MIT, 3.8B) | FP8 / bf16 | 4.5 / 7.7 GB | 0.79 GB | ~6 / 2 | ~6.1 GB (fits) |
| Escalation and 7–9B 4-bit evaluation, candidate A | Qwen3.5-9B (`c202236`), same tokenizer and prompt as the primary | NF4 (bitsandbytes) | 8.0 GB | 0.72 GB | ~2 | ~12.0 GB (does **not** fit; 2048 is marginal at 11.1 GB) |
| Escalation and 7–9B 4-bit evaluation, candidate B | Qwen3-8B-AWQ (`Qwen/Qwen3-8B-AWQ` @ `4da05a8`, official) | AWQ 4-bit | 6.2 GB | 0.89 GB | ~4 | ~10.0 GB (fits, tight) |
| Measured only if it fits | Gemma 4 E4B-it (`ee0ef60`; 8.0B stored, ~4B effective) | FP8 | 11.5 GB | — | 0 | does not fit |

Why this set:

- **Qwen3.5-4B** is the newest permissive small model in the family the plan already chose. Its
  hybrid attention means only 8 of 32 layers keep a per-token KV cache (32 KiB per token against
  144 KiB for Qwen3-4B), so long telemetry prompts and 10 samples cost little KV. bf16 (9.3 GB)
  leaves under 0.5 GB of KV, so **every primary run uses FP8**, and the precision is fixed for the
  whole paper. Ada (sm_89) supports FP8 in vLLM; the M2 gate confirms it, together with the Gated
  DeltaNet kernels, on this laptop.
- The **fallback** Qwen3-4B-Instruct-2507 is text-only with standard attention and mature vLLM
  support. It is used if Qwen3.5-4B fails the M2 gates: parse rate < 99 %, full-condition AC@1 on
  DEV not above the max-z heuristic, or a kernel or precision problem on the laptop.
- **Escalation stays inside one family**, so a gain comes from scale rather than formatting.
  Candidate A (Qwen3.5-9B NF4) is the cleaner scale contrast for the Qwen3.5-4B primary. No
  official 4-bit checkpoint exists, bitsandbytes serving is slower, and the precision differs from
  the primary's. Candidate B (Qwen3-8B-AWQ) is official and faster, and is the natural pair for
  the fallback primary. The M2 gate picks the escalation model from measured parse rate, DEV
  AC@1 gain over the primary, and throughput. The choice is recorded in decisions.md before the
  main grid. External inference for escalation is used only if the owner approves it separately.
- **Cross-family replication** uses Phi-4-mini (a different lab, MIT licence, text-only). Gemma 4
  E4B stores 8B parameters (2.8B of them per-layer embeddings kept in 16 bit), so it does not fit
  12 GB with KV by this estimate. It is used only if a measurement shows otherwise (for example,
  with per-layer embeddings offloaded).
- **Optional** models (Nemotron 3 Nano 30B-A3B, Qwen3.5-27B, Gemma 4 26B-A4B) are out of scope on
  this GPU. They return only with separately approved external inference or a larger GPU.

Minimal baseline configuration: the Qwen3.5-4B FP8 primary with mock Jev and
`limit_per_system: 2` (`configs/exp/smoke-canonical.yaml` with the model block swapped). This is a
smoke run only and is never reported.

## 4. Memory accounting and what the M2 gate measures

The estimator (`src/rca/capacity.py`, tests in `tests/test_capacity.py`) computes the following:

- **Weights:** `params × bytes`. Embeddings and an untied lm_head stay in 16 bit under FP8, AWQ
  and NF4. This dominates for the 248k-token Qwen3.5 vocabulary: the 9B model's untied
  embeddings alone are 4.1 GB.
- **KV:** `2 × kv_layers × kv_heads × head_dim × bytes` per token, times `prompt + n × max_tokens`
  per request (vLLM shares the prompt prefix across the n samples). Linear-attention layers add a
  fixed state per sequence of about 52 MB.
- **QLoRA:** NF4 base with double quantisation, plus LoRA r=16 on all linear layers with fp32
  Adam (about 30–45M parameters, under 1 GB), plus gradient-checkpointed activations (linear in
  sequence length), plus logits. Logits must be computed only on the supervised answer tokens
  (`logits_to_keep`, answer-only loss). Over a full 4096-token sequence, vocabulary-sized logits
  alone would add about 10 GB for Qwen3.5.

Prompt length decides the KV and training sequence length. Estimates from the evidence files
(characters ÷ 3 + template) are recorded in §4.1. The M2 pilot replaces them with
`usage.prompt_tokens` from the served tokenizer.

The M2 gate measures, on the laptop: peak VRAM (`nvidia-smi`) at the chosen `--max-model-len`;
sustained requests in flight and tokens/s for the primary and both escalation candidates;
extrapolated wall-clock for the M3 volume, which must fit in 3 GPU-days; and QLoRA peak memory at
the training sequence length. A configuration counts as feasible only when it is measured, not
estimated.

### 4.1 Prompt lengths (estimate)

Measured on 2026-10-15 from 89 evidence files: a stratified sample of up to 12 incidents per
system over all four datasets, built on CPU with `run_grid prepare`. Tokens ≈ characters ÷ 3 +
30 for the chat template, which is conservative for English-heavy telemetry text.

| Condition | n | p50 | p95 | max |
|---|---|---|---|---|
| full | 89 | 796 | 1,126 | 1,579 |
| no_trace | 59 | 748 | 1,121 | 1,572 |
| no_log | 68 | 691 | 885 | 1,080 |
| no_metric | 68 | 435 | 826 | 1,348 |
| metrics_only | 68 | 636 | 822 | 962 |
| blind_root / blind_nonroot | 28 | ~785 | ~1,400 | ~1,580 |
| retrieval (full + 3 precedents of p95 size; upper estimate) | 89 | 4,174 | 4,504 | 4,957 |

Consequences:

- Prompts are short. `--max-model-len 8192` covers the retrieval arm (p95 ≈ 4.5k tokens + 400
  output) with margin, and the no-retrieval arms need only about 2k.
- At the p95 retrieval prompt with n = 10, the KV budget holds about 5 concurrent requests for
  Qwen3.5-4B FP8, 2 for Qwen3.5-9B NF4 and 2 for Qwen3-8B-AWQ. This compares with 6 / 2 / 4 at a
  2k-token prompt.
- A QLoRA sequence length of 2048 covers every no-retrieval training example. 4096 is needed only
  if retrieved precedents are part of the training prompt.

## 5. Serving decisions to verify in M0/M2

- vLLM version that supports Qwen3.5 and Gemma 4, and guided JSON (`response_format:
  json_schema`) with thinking disabled (`chat_template_kwargs: {enable_thinking: false}` or the
  model's equivalent).
- Text-only loading of the multimodal checkpoints (vision tower memory; `--limit-mm-per-prompt`).
- An official FP8 or 4-bit checkpoint; else pin a community quantisation by HF commit sha.
- Prefix caching on; `--max-model-len` set from the measured p99 prompt (plus retrieval) and no larger, since
  12 GB leaves little KV headroom; `seed` honoured.
- Each model pinned by HF repo **and** revision sha in the config and the run manifest.
