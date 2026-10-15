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
| LoRA (bf16) | train role of a `within-*` split | Domain adaptation | tier L GPU | Over-fitting, calibration loss | Gated (phase 05) |
| QLoRA (4-bit base) | same | Same, on 24 GB | tier M GPU | Same, plus a quantisation mismatch between training and serving | Gated (phase 05), preferred on tier M |

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
4. A tier M or L GPU is available for ≥ 2 days.

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
