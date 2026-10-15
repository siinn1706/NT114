"""GPU memory estimator and GPU probe (CPU only)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from rca import capacity

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT / "configs" / "hardware" / "rtx4080-laptop-12gb.yaml"

_spec = importlib.util.spec_from_file_location("gpu_probe", ROOT / "scripts" / "gpu_probe.py")
gpu_probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gpu_probe)


@pytest.fixture(scope="module")
def plan():
    return capacity.load_plan(HW)


def _model(plan, name):
    return next(m for m in plan.models if m.name == name)


def test_kv_per_token_matches_architecture(plan):
    # Qwen3-4B: 36 layers x 8 KV heads x 128 x (K + V) x 2 bytes = 144 KiB per token
    assert capacity.kv_per_token(_model(plan, "qwen3-4b-instruct-2507")) == 144 * 1024
    # Qwen3.5-4B: only its 8 full-attention layers hold a per-token cache (4 x 256)
    assert capacity.kv_per_token(_model(plan, "qwen3.5-4b")) == 32 * 1024
    assert capacity.kv_per_token(_model(plan, "qwen3.5-4b"), kv_bytes=1) == 16 * 1024


def test_weights_keep_embeddings_16bit(plan):
    m = _model(plan, "qwen3-8b")
    assert capacity.weights_gb(m, "bf16") == pytest.approx(16.38)
    awq = capacity.weights_gb(m, "awq4")
    assert awq > m.embed_params_b * 2 and awq < capacity.weights_gb(m, "fp8") < 16.38


def test_prefix_shared_across_samples():
    assert capacity.request_tokens(2000, 400, 10) == 6000


def test_twelve_gb_fits(plan):
    hw = plan.hardware
    s = {(r["model"], r["precision"]): r for r in capacity.report(plan, 2048)["serve"]}
    assert s[("qwen3.5-4b", "fp8")]["fits"] and not s[("qwen3.5-4b", "bf16")]["fits"]
    assert s[("qwen3-8b", "awq4")]["fits"] and not s[("qwen3-8b", "fp8")]["fits"]
    assert all(r["weights_gb"] <= hw.vram_gb for r in s.values() if r["fits"])
    t = capacity.qlora(_model(plan, "qwen3.5-4b"), hw, 4096)
    assert t["fits"] and t["total_gb"] < hw.train_budget_gb
    longer = capacity.qlora(_model(plan, "qwen3.5-4b"), hw, 8192)
    assert longer["activations_gb"] == pytest.approx(2 * t["activations_gb"], rel=0.01)
    # without answer-only logits a 248k vocabulary needs vocab-sized logits at every position
    full_logits = capacity.qlora(_model(plan, "qwen3.5-4b"), hw, 4096, label_tokens=4096)
    assert full_logits["logits_gb"] > 8 * t["logits_gb"]


def test_prompt_stats(tmp_path):
    for i, n in enumerate([300, 3000]):
        rec = {"system": "s", "candidates": ["a", "b"],
               "conditions": {"full": {"text": "x" * n}, "no_log": {"text": "x" * (n // 2)}}}
        (tmp_path / f"{i}.json").write_text(json.dumps(rec), encoding="utf-8")
    st = capacity.prompt_stats(tmp_path, chars_per_token=3.0)
    assert st["full"]["n"] == 2 and st["full"]["max"] > 1000 > st["full"]["p50"] > st["no_log"]["p50"]
    assert st["retrieval"]["p95"] == 4 * st["full"]["p95"]
    with pytest.raises(ValueError, match="no evidence"):
        capacity.prompt_stats(tmp_path / "empty")


def test_cli(capsys):
    rep = capacity.main([str(HW)])
    assert rep["serve"] and rep["qlora"] and json.loads(capsys.readouterr().out)["hardware"] == "rtx4080-laptop-12gb"


def test_parse_smi():
    rows = gpu_probe.parse_smi("NVIDIA GeForce RTX 4080 Laptop GPU, 12282, 412, 11590, 560.94, 8.9\n")
    assert rows == [{"name": "NVIDIA GeForce RTX 4080 Laptop GPU", "memory_total_mib": 12282, "memory_used_mib": 412,
                     "memory_free_mib": 11590, "driver_version": "560.94", "compute_capability": "8.9"}]
    assert gpu_probe.cuda_driver_version("| NVIDIA-SMI 560.94   Driver Version: 560.94   CUDA Version: 12.6 |") == "12.6"


def test_probe_without_gpu(monkeypatch, tmp_path):
    monkeypatch.setattr(gpu_probe.shutil, "which", lambda name: None)
    monkeypatch.setattr(gpu_probe, "_run", lambda cmd: None)
    rep = gpu_probe.main(["--data-home", str(tmp_path), "--out", str(tmp_path / "probe.json")])
    assert rep["gpus"] == [] and "hardware" not in rep and rep["cuda_driver"] is None
    assert json.loads((tmp_path / "probe.json").read_text(encoding="utf-8"))["disk_free_gib"] > 0
