"""GPU memory estimates for serving and QLoRA training, from model architecture and prompt lengths.

  python -m rca.capacity configs/hardware/rtx4080-laptop-12gb.yaml [--evidence-dir results/evidence]

Estimates only: they decide which configurations are worth measuring on the GPU machine, never
replace the measurement. Prompt tokens are approximated from characters (`chars_per_token`) until
the served tokenizer's `usage.prompt_tokens` is available in a real grid.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

from .llm import build_messages

GB = 1e9


@dataclass(frozen=True)
class ModelSpec:
    """Architecture numbers from the model's config.json. `kv_layers` counts layers holding a
    per-token KV cache (full-attention layers only in hybrid models); `state_mb_per_seq` is the
    fixed recurrent state per sequence of linear-attention layers. `kv_bytes_per_token`, when set,
    overrides the formula (architectures it does not describe, e.g. sliding-window + shared KV)."""
    name: str
    params_b: float
    layers: int
    hidden: int
    vocab: int
    attn_heads: int
    kv_layers: int
    kv_heads: int
    head_dim: int
    intermediate: int
    tied_embeddings: bool = True
    state_mb_per_seq: float = 0.0
    kv_bytes_per_token: float | None = None
    extra_embed_params_b: float = 0.0  # other 16-bit lookup tables (e.g. per-layer embeddings)
    repo: str = ""
    revision: str = ""
    licence: str = ""
    notes: str = ""

    @property
    def embed_params_b(self) -> float:
        """Embedding (+ untied lm_head) parameters, kept in 16 bit by weight-only quantisation."""
        return self.vocab * self.hidden * (1 if self.tied_embeddings else 2) / 1e9 + self.extra_embed_params_b


@dataclass
class Hardware:
    name: str
    vram_gb: float
    reserved_gb: float = 0.5          # display, driver and other processes on a laptop GPU
    gpu_memory_utilization: float = 0.90
    runtime_overhead_gb: float = 1.0  # CUDA context, activations, CUDA graphs (vLLM)
    train_overhead_gb: float = 1.0    # CUDA context, allocator fragmentation (training)

    @property
    def serve_budget_gb(self) -> float:
        return min(self.vram_gb * self.gpu_memory_utilization, self.vram_gb - self.reserved_gb)

    @property
    def train_budget_gb(self) -> float:
        return self.vram_gb - self.reserved_gb


# bytes per non-embedding parameter: AWQ/GPTQ add group-128 scales and zeros (~0.25 bit), NF4 with
# double quantisation ~0.13 bit
BYTES = {"bf16": 2.0, "fp8": 1.0, "int8": 1.0, "awq4": 0.53, "gptq4": 0.53, "nf4": 0.516}


def weights_gb(m: ModelSpec, precision: str) -> float:
    """Weight-only formats keep the embeddings (and an untied lm_head) in 16 bit."""
    if precision == "bf16":
        return m.params_b * 2
    return max(m.params_b - m.embed_params_b, 0.0) * BYTES[precision] + m.embed_params_b * 2


def kv_per_token(m: ModelSpec, kv_bytes: int = 2) -> float:
    if m.kv_bytes_per_token is not None:
        return m.kv_bytes_per_token * kv_bytes / 2
    return 2 * m.kv_layers * m.kv_heads * m.head_dim * kv_bytes


def request_tokens(prompt_tokens: int, max_tokens: int, n_samples: int) -> int:
    """KV tokens of one request with n samples: the prompt prefix is shared, each sample decodes its own."""
    return prompt_tokens + n_samples * max_tokens


def serve(m: ModelSpec, hw: Hardware, precision: str, prompt_tokens: int, max_tokens: int, n_samples: int,
          kv_bytes: int = 2) -> dict:
    w = weights_gb(m, precision)
    free = hw.serve_budget_gb - w - hw.runtime_overhead_gb
    per_req = request_tokens(prompt_tokens, max_tokens, n_samples) * kv_per_token(m, kv_bytes) / GB \
        + n_samples * m.state_mb_per_seq / 1e3
    return {"model": m.name, "precision": precision, "weights_gb": round(w, 2), "kv_gb_per_request": round(per_req, 3),
            "kv_budget_gb": round(free, 2), "concurrent_requests": max(int(free // per_req), 0) if per_req else 0,
            "fits": free >= per_req}


def lora_params_b(m: ModelSpec, rank: int) -> float:
    """LoRA on q, k, v, o, gate, up and down of every layer (hybrid layers approximated as attention)."""
    q, kv = m.attn_heads * m.head_dim, m.kv_heads * m.head_dim
    per_layer = (m.hidden + q) + 2 * (m.hidden + kv) + (q + m.hidden) + 2 * (m.hidden + m.intermediate) \
        + (m.intermediate + m.hidden)
    return rank * per_layer * m.layers / 1e9


def qlora(m: ModelSpec, hw: Hardware, seq_len: int, micro_batch: int = 1, rank: int = 16, label_tokens: int = 256,
          grad_checkpointing: bool = True) -> dict:
    """4-bit NF4 base (double quantisation), bf16 LoRA weights, fp32 Adam states, gradient checkpointing.
    Logits are counted for `label_tokens` positions only (answer-only loss with `logits_to_keep`); without
    that, every position materialises vocab-sized logits, which dominates memory for 150k+ vocabularies."""
    base = weights_gb(m, "nf4")
    lp = lora_params_b(m, rank)
    lora = lp * (2 + 2 + 12)                                   # weights, grads, fp32 master + 2 Adam moments
    tok = micro_batch * seq_len
    if grad_checkpointing:                                     # saved layer inputs + one layer recomputed
        act = tok * m.hidden * 2 * m.layers + tok * (10 * m.hidden + 3 * m.intermediate) * 2
    else:
        act = tok * (10 * m.hidden + 3 * m.intermediate) * 2 * m.layers
    logits = micro_batch * min(label_tokens, seq_len) * m.vocab * (2 + 4 + 4)  # bf16 logits, fp32 upcast, grad
    total = base + lora + act / GB + logits / GB + hw.train_overhead_gb
    return {"model": m.name, "seq_len": seq_len, "micro_batch": micro_batch, "rank": rank,
            "base_gb": round(base, 2), "lora_params_m": round(lp * 1e3, 1), "activations_gb": round(act / GB, 2),
            "logits_gb": round(logits / GB, 2), "total_gb": round(total, 2), "fits": total <= hw.train_budget_gb}


# ---------------------------------------------------------------- prompt lengths
@dataclass
class _Case:
    system: str


def prompt_chars(rec: dict, condition: str) -> int:
    msgs = build_messages(_Case(rec.get("system", "")), rec["candidates"], rec["conditions"][condition]["text"])
    return sum(len(m["content"]) for m in msgs)


def prompt_stats(evidence_dir, chars_per_token: float = 3.0, template_tokens: int = 30, top_k: int = 3) -> dict:
    """Per condition: p50 / p95 / max estimated prompt tokens over the evidence files; `retrieval`
    adds `top_k` precedents of p95 full-evidence size."""
    lens: dict[str, list[int]] = {}
    for f in sorted(Path(evidence_dir).glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        for cond in rec["conditions"]:
            lens.setdefault(cond, []).append(prompt_chars(rec, cond))
    if not lens:
        raise ValueError(f"no evidence files in {evidence_dir}")
    out = {}
    for cond, xs in sorted(lens.items()):
        t = np.asarray(xs) / chars_per_token + template_tokens
        out[cond] = {"n": len(xs), "p50": int(np.percentile(t, 50)), "p95": int(np.percentile(t, 95)), "max": int(t.max())}
    full = out.get("full")
    if full:
        out["retrieval"] = {"n": full["n"], "p50": full["p50"] + top_k * full["p95"],
                            "p95": full["p95"] * (1 + top_k), "max": full["max"] + top_k * full["p95"]}
    return out


# ---------------------------------------------------------------- report
@dataclass
class Plan:
    hardware: Hardware
    models: list[ModelSpec]
    serve_precisions: dict = field(default_factory=dict)
    n_samples: int = 10
    max_tokens: int = 400
    prompt_tokens: int = 2048
    train_seq_lens: tuple = (2048, 4096)
    lora_rank: int = 16
    label_tokens: int = 256


def load_plan(path) -> Plan:
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    hw = Hardware(**d["hardware"])
    models = [ModelSpec(**m) for m in d["models"]]
    s, t = d.get("serve", {}), d.get("train", {})
    return Plan(hw, models, s.get("precisions", {}), s.get("n_samples", 10), s.get("max_tokens", 400),
                s.get("prompt_tokens", 2048), tuple(t.get("seq_lens", (2048, 4096))), t.get("lora_rank", 16),
                t.get("label_tokens", 256))


def report(plan: Plan, prompt_tokens: int | None = None) -> dict:
    p = prompt_tokens or plan.prompt_tokens
    rows = [serve(m, plan.hardware, prec, p, plan.max_tokens, plan.n_samples)
            for m in plan.models for prec in plan.serve_precisions.get(m.name, ["bf16"])]
    train = [qlora(m, plan.hardware, s, 1, plan.lora_rank, plan.label_tokens) for m in plan.models for s in plan.train_seq_lens]
    return {"hardware": plan.hardware.name, "serve_budget_gb": round(plan.hardware.serve_budget_gb, 2),
            "train_budget_gb": round(plan.hardware.train_budget_gb, 2), "prompt_tokens": p,
            "serve": rows, "qlora": train}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("plan")
    ap.add_argument("--evidence-dir", help="estimate prompt length from these evidence files (p95 of the retrieval prompt)")
    ap.add_argument("--chars-per-token", type=float, default=3.0)
    a = ap.parse_args(argv)
    plan = load_plan(a.plan)
    stats = prompt_stats(a.evidence_dir, a.chars_per_token) if a.evidence_dir else None
    rep = report(plan, max(v["p95"] for v in stats.values()) if stats else None)
    if stats:
        rep["prompt_stats"] = stats
    print(json.dumps(rep, indent=1))
    return rep


if __name__ == "__main__":
    main()
