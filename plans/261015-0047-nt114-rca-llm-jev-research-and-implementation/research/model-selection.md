# Model selection and hardware (2026-10-15)

**[F]** = stated by an official release or model card found in this session; **[S]** = only
secondary sources found, must be confirmed on the model card in M0; **[A]** = estimate.

## 1. What the task needs from the RCA LLM

1. A ranked list of ≤5 services, drawn from a given candidate list (enum-constrained JSON).
   `llm.schema()` already enforces this with vLLM guided decoding.
2. Prompts of about 3.5k evidence tokens + ≤1k retrieved precedents + instructions, so ≥16k
   context is plenty.
3. Ten samples at T = 0.7 per prompt (consensus confidence). vLLM shares the prefill across
   `n`, so the cost is mostly prefill.
4. A verbal confidence (0–100) and an `insufficient_evidence` flag in the same JSON.
5. Thinking/reasoning traces are **not** needed for the main grid. They multiply tokens 5–20×,
   and they interact badly with guided JSON on some parsers. Thinking mode is an optional ablation.

The model does not need tool use, vision or long context. That favours a dense 4–10B instruct
model as primary and a larger sibling for escalation.

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

## 3. Recommendation

| Role | Model | Why |
|---|---|---|
| **Primary RCA LLM** | **Qwen3.5-9B instruct, non-thinking mode** | Newest permissive small dense model; fits every hardware tier at 4–8 bit; same family as a strong larger sibling, so escalation isolates scale |
| **Escalation LLM** | **Qwen3.5-27B, non-thinking** | Same family, same tokenizer and prompt; any gain comes from scale, not formatting. Not co-resident: the grid runs models one after another |
| **Cross-family replication** (required for generality) | Gemma 4 26B-A4B on ≥24 GB, else Gemma 4 E4B | Different family and lab; repeats the core LLM-only and Jev runs on the RCAEval test split |
| Optional | Nemotron 3 Nano 30B-A3B | Third family; custom vLLM parser and licence review make it optional |
| Minimal baseline config | Qwen3.5-4B (or 9B at 4-bit) + Jev mock, `limit_per_system: 2` | Smoke on any ≥12 GB GPU |

Fallback if Qwen3.5-9B fails the M2 gates (parse rate <99%, or full-condition AC@1 on dev not
above the max-z heuristic): switch the primary to Gemma 4 E4B/26B-A4B and keep Qwen3.5-27B as
the escalation model. Record the switch in the decision log before the main grid.

## 4. Hardware tiers (target GPU not chosen)

Weight memory ≈ params × bytes (bf16 2, FP8 1, 4-bit ≈0.55) plus KV cache and activations. All
figures are **[A]** estimates for the M0 probe to confirm.

| Tier | Example GPUs | Primary | Escalation | Replication | Fine-tuning (M4) |
|---|---|---|---|---|---|
| S: 12–16 GB | RTX 4080 Laptop 12 GB, 4060 Ti 16 GB, T4 16 GB | 9B at 4-bit (~6 GB) or 4B bf16 (~9 GB) | 27B 4-bit (~16 GB) does **not** fit 12 GB; use 9B as "escalation" from a 4B primary | Gemma 4 E4B 4-bit | QLoRA on 4B only |
| M: 24 GB | RTX 3090/4090, L4, A10 | 9B FP8 (~10 GB) | 27B AWQ/GPTQ 4-bit (~16 GB; leaves only ~3–4 GB KV at 0.85 utilisation, so M2 measures concurrency) | Gemma 4 26B-A4B 4-bit (~15 GB) | QLoRA 9B (~12–16 GB) |
| L: 40–80 GB | A100, L40S 48 GB, H100 | 9B bf16 | 27B FP8 (48 GB) or bf16 (80 GB) | Gemma 4 26B-A4B bf16 (80 GB) | LoRA bf16 9B; QLoRA 27B |

Recommended minimum for the full plan: **tier M (24 GB)**. Tier S works if the escalation pair
is 4B → 9B; the paper must then say so.

Throughput estimate for tier M **[A]**: the main grid has about 6.5k prompts for the primary
model (research-design §7). The earlier estimate assumed ~5k prefill tokens and 10 × ~150 output
tokens per prompt, giving ~33M prefill and ~10M decode tokens. Pilot evidence (median ~800
characters) suggests prefill is several times smaller. With vLLM batching this is a few GPU-hours for 9B and under one day for 27B
4-bit. Compute is not the schedule bottleneck; the pilot (M2) measures it.

## 5. Serving decisions to verify in M0/M2

- vLLM version that supports Qwen3.5 and Gemma 4, and guided JSON (`response_format:
  json_schema`) with thinking disabled (`chat_template_kwargs: {enable_thinking: false}` or the
  model's equivalent).
- Text-only loading of the multimodal checkpoints (vision tower memory; `--limit-mm-per-prompt`).
- An official FP8 or 4-bit checkpoint; else pin a community quantisation by HF commit sha.
- Prefix caching on; `--max-model-len 16384`; `seed` honoured.
- Each model pinned by HF repo **and** revision sha in the config and the run manifest.
