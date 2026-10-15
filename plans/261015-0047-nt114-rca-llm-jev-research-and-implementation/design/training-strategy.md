# Training strategy

Recommendation: **zero-shot is the primary configuration. Retrieval is the few-shot arm.
Fine-tuning is an optional, gated extension (phase 05) and is not needed for the minimum paper.**
Training from scratch is not considered: no dataset here is large enough, and no result would
depend on it.

## 1. Alternatives

| Option | Data needed | What it would show | Cost | Risk | Decision |
|---|---|---|---|---|---|
| Zero-shot | none | The deployment-relevant setting; Jev untuned too | lowest | none | **Primary** |
| Static few-shot (k = 2 fixed train exemplars) | 2 train incidents | Formatting help only | low | Exemplar choice biases answers | DEV check only, not reported unless it changes AC@1 by > 5 pp |
| Dynamic few-shot = retrieval of labelled precedents | STORE (grouped train, 374) | Value of past incidents (RQ5) | already in E2 | Label leakage, handled by precedent mode | **In minimum set (E2)** |
| LoRA (bf16 base) | train role of a `within-*` split | Domain adaptation | 4B bf16 base (~9 GB) leaves too little room on 12 GB | Over-fitting, calibration loss | Not used on the 12 GB GPU |
| QLoRA (4-bit base) | same | Same | 3–4B: ~6–7 GB estimated at seq 4096 on the 12 GB GPU | Same, plus a quantisation mismatch between training and serving | Gated (phase 05); the only fine-tuning option on 12 GB |
| Full fine-tuning | same | Same | does not fit 12 GB for ≥ 3B | Same | Not considered |

## 2. Is there enough training data?

Train-role incidents that are legal for training (handoff §2b.2): `within-rcaeval-grouped` train
374 (cell-held-out test 218). They yield **1,223** applicable (incident × condition) examples
(verified by the red team from the condition matrix). 200 of the 374 are RE1 metrics-only with one
example each, and condition variants share one target, so the **effective n is about 374** from 3
systems and 7 fault families. <!-- Red team A9 --> AIOps2025 `within-*-retrieval` train is 141; RCA100 train is 48–69. These are
small. SFT can teach the output format and system-specific service names. The risks are
memorising the (system, fault) → root prior, which the cell-held-out test punishes, and degrading
calibration, which is a known effect of SFT on chat models. That second risk is the
scientifically interesting part, not a speed-up.

## 3. What fine-tuning would be allowed to claim

Only: "on held-out fault cells (`within-rcaeval-grouped` test) and on another dataset
(`xdata-rcaeval-to-*`), SFT changes AC@1 by X and the overconfidence gap by Y, relative to the
same base model zero-shot." Train and evaluation must use the same prompt, the same evidence and
the same serving precision.

## 4. Gate (decided at the week-6 checkpoint, logged)

Run phase 05 only if all hold:

1. M3 minimum set (E1–E8) is complete and analysed.
2. Zero-shot primary AC@1 on DEV is between 1.5× random and 0.85. Below that, evidence or prompt
   is the bottleneck. Above it, there is no headroom.
3. ≥ 3 weeks remain before the submission freeze.
4. The 12 GB GPU is available for ≥ 2 days, and a measured QLoRA step fits (§7).

## 5. Must exist before any training vs can wait

| Before training (blocking) | Can wait until the gate |
|---|---|
| Linux GPU portability gate passed (data handoff gate 1) | `sft_export.py` (chat JSONL from train-role evidence + ranking target) |
| Frozen prompt v1 and evidence builder version | `scripts/train_lora.py` (PEFT/TRL or Unsloth, pinned versions) |
| Zero-shot baseline numbers on DEV and test (M3) | Hyper-parameter grid (rank 16, α 32, lr 1e-4–2e-4, 2–3 epochs; early stop on DEV loss) |
| Split-role leakage test for the export | Serving the adapter in vLLM (`--enable-lora`) |
| Decision on the target split (grouped vs retrieval) | Calibration analysis of the SFT model |

## 6. Training target (if the gate passes)

Target JSON = the same schema as inference, with `ranking[0]` = true root, the rest in the base
model's own order, and **no confidence target** (the confidence field is masked from the loss).
Teaching a confidence would confound RQ2. Jev stays untuned and is rerun on the SFT model's
outputs. The comparison is SFT + Jev vs zero-shot + Jev.

## 7. Memory-efficient settings on the 12 GB GPU (D2)

Estimates come from `python -m rca.capacity configs/hardware/rtx4080-laptop-12gb.yaml`. The first
training step on the machine replaces them with the measured peak (`torch.cuda.max_memory_allocated`).

| Setting | Value | Reason |
|---|---|---|
| Base | the 3–4B primary in NF4 with double quantisation | ~3.4 GB for Qwen3.5-4B, whose embeddings stay 16 bit |
| Adapters | LoRA r = 16, α = 32, all linear layers | ~30M parameters; under 1 GB with fp32 Adam |
| Micro-batch / accumulation | 1 / 16 | Activations scale with micro-batch × sequence |
| Gradient checkpointing | on | Activations ~1.1 GB at seq 4096 instead of ~10× that |
| Sequence length | configurable; p99 prompt + target, default ≤ 4096 | Telemetry prompts are the longest input |
| Loss | answer tokens only, `logits_to_keep` = target length | Full-sequence logits over a 248k vocabulary would add ~10 GB |
| 7–9B QLoRA | only if measured under budget (Qwen3-8B estimated ~10 GB at 4096; Qwen3.5-9B does not fit at 4096) | No assumption of feasibility |
| Serving after training | adapter merged, served at the primary's FP8 | Keeps precision fixed between the zero-shot and SFT arms |

