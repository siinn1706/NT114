"""GPU feasibility runner: profiles, log parsing, verdict, and one end-to-end run against a fake server."""
from __future__ import annotations

import json
import os
import shutil
import socket
import sys
from pathlib import Path

import pytest
import yaml

from conftest import canonical_run_cfg
from rca import feasibility, run_grid

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT / "configs" / "hardware" / "rtx4080-laptop-12gb.yaml"

LOG = """INFO Loading weights took 3.10 seconds
INFO Model loading took 5.42 GiB and 12.0 seconds
INFO Available KV cache memory: 3.21 GiB
INFO GPU KV cache size: 46,752 tokens
INFO Maximum concurrency for 8,192 tokens per request: 5.71x
"""


def _row(cond="full", ret="none", ok=True, cached=False, lat=4.0, pt=1200, correct=True):
    return {"case_id": f"c-{cond}-{ret}-{lat}", "condition": cond, "retrieval": ret, "parse_failed": not ok,
            "cached": cached, "latency_s": lat, "prompt_tokens": pt, "completion_tokens": 800, "correct": correct}


def test_profiles_pinned_and_fallbacks_resolve():
    plan, prof = feasibility.load(HW)
    assert {"qwen35-4b-fp8", "qwen3-4b-2507-fp8", "phi4-mini-fp8", "qwen35-9b-nf4", "qwen3-8b-awq"} <= set(prof)
    assert prof["qwen35-4b-fp8"]["role"] == "primary" and prof["qwen35-4b-fp8"]["fallback"] == "qwen3-4b-2507-fp8"
    assert prof["qwen35-9b-nf4"]["fallback"] == "qwen3-8b-awq"
    awq = prof["qwen3-8b-awq"]                         # official AWQ repo replaces the base checkpoint
    assert awq["repo"] == "Qwen/Qwen3-8B-AWQ" and awq["revision"].startswith("4da05a8e")
    specs = {m.name: m for m in plan.models}
    assert prof["qwen35-4b-fp8"]["revision"] == specs["qwen3.5-4b"].revision
    assert all(p["max_model_len"] == 8192 for p in prof.values())


def test_profile_validation(tmp_path):
    d = yaml.safe_load(HW.read_text(encoding="utf-8"))
    d["profiles"][0]["revision"] = "main"
    (tmp_path / "hw.yaml").write_text(yaml.safe_dump(d), encoding="utf-8")
    with pytest.raises(ValueError, match="full commit sha"):
        feasibility.load(tmp_path / "hw.yaml")
    d = yaml.safe_load(HW.read_text(encoding="utf-8"))
    d["profiles"][0]["fallback"] = "nope"
    (tmp_path / "hw.yaml").write_text(yaml.safe_dump(d), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown fallback"):
        feasibility.load(tmp_path / "hw.yaml")


def test_serve_args_and_grid_cfg(tmp_path):
    plan, prof = feasibility.load(HW)
    args = feasibility.serve_args(prof["qwen35-4b-fp8"], plan.hardware, 8000)
    assert args == ["--max-model-len", "8192", "--gpu-memory-utilization", "0.9", "--quantization", "fp8",
                    "--language-model-only", "--port", "8000"]
    exp = run_grid.load_cfg(ROOT / "configs" / "exp" / "gpu-feasibility.yaml")
    assert exp["split_role"] == "val" and "jev" not in exp            # DEV only, never calls Jev
    a = feasibility.grid_cfg(exp, prof["qwen35-4b-fp8"], tmp_path / "a")
    b = feasibility.grid_cfg(exp, prof["qwen3-8b-awq"], tmp_path / "b")
    (m,) = a["models"]
    assert m["revision"] == prof["qwen35-4b-fp8"]["revision"] and m["quantization"] == "fp8"
    assert m["chat_template_kwargs"] == {"enable_thinking": False} and m["launch_args"].endswith("server.args")
    assert a["out"].startswith(str(tmp_path / "a")) and a["_hash"] != b["_hash"]
    assert exp["models"] == []                                          # the experiment config is not mutated


def test_parse_server_log():
    got = feasibility.parse_server_log(LOG)
    assert got == {"model_load_gib": 5.42, "kv_cache_gib": 3.21, "kv_cache_tokens": 46752,
                   "max_concurrency": 5.71, "oom": False}
    assert feasibility.parse_server_log("torch.OutOfMemoryError: CUDA out of memory")["oom"]


def test_smi_stats(tmp_path):
    f = tmp_path / "smi.csv"
    f.write_text("2026/10/15 10:00:00.000, 650, 12282, 45, 2100, 20.1, 0x0000000000000000\n"
                 "2026/10/15 10:00:01.000, 10900, 12282, 83, 1650, 120.4, 0x0000000000000004\n"
                 "garbage\n", encoding="utf-8")
    s = feasibility.smi_stats(f)
    assert s["baseline_mib"] == 650 and s["peak_mib"] == 10900 and s["temp_max_c"] == 83
    assert s["sm_clock_min_mhz"] == 1650 and s["throttle_reasons"] == ["0x0000000000000004"]
    assert feasibility.smi_stats(tmp_path / "missing.csv") == {}


def test_grid_stats_ignore_cached_rows(tmp_path):
    rows = [_row(lat=2), _row(lat=4), _row("no_trace", "hybrid", ok=False, lat=6, pt=4000), _row(cached=True, lat=0)]
    f = tmp_path / "grid.jsonl"
    f.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    g = feasibility.grid_stats(f)
    assert g["rows"] == 4 and g["live_rows"] == 3
    assert g["parse_rate"] == pytest.approx(2 / 3, abs=1e-4) and g["parse_rate_by_cell"]["no_trace/hybrid"] == 0
    assert g["prompt_tokens"]["max"] == 4000 and g["completion_tokens_per_s"] == pytest.approx(2400 / 12, abs=0.1)


def test_verdict():
    good = {"live_rows": 10, "parse_rate": 1.0}
    assert feasibility.verdict({"ready": True, "kv_cache_tokens": 46752}, good, 5500)["feasible"]
    v = feasibility.verdict({"ready": True, "kv_cache_tokens": 8000}, {"live_rows": 10, "parse_rate": 0.9}, 5500)
    assert not v["feasible"] and len(v["reasons"]) == 2 and v["concurrent_requests_measured"] == pytest.approx(1.45, abs=0.01)
    v = feasibility.verdict({"ready": False, "oom": True}, {"live_rows": 0}, None)
    assert not v["feasible"] and "out of memory" in v["reasons"][0]


def test_pinned_requirements():
    want = feasibility.pinned(ROOT / "requirements-gpu.txt")
    assert want["vllm"] == "0.30.0" and set(want) == {"vllm", "transformers", "bitsandbytes"}


FAKE_SERVER = r'''
import json, sys, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer
port = int(sys.argv[sys.argv.index("--port") + 1])
last = [time.time()]
class H(BaseHTTPRequestHandler):
    def _send(self, obj):
        last[0] = time.time()
        self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(obj).encode())
    def do_GET(self):
        self._send({"data": [{"id": sys.argv[2]}]})
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if "response_format" not in body:
            return self._send({"choices": [{"message": {"content": "ready"}}]})
        enum = body["response_format"]["json_schema"]["schema"]["properties"]["ranking"]["items"]["enum"]
        msg = json.dumps({"reason": "r", "ranking": enum[:2], "confidence": 70, "insufficient_evidence": False,
                          "next_check": "logs"})
        self._send({"choices": [{"message": {"content": msg}}] * body["n"],
                    "usage": {"prompt_tokens": 1500, "completion_tokens": 900}})
    def log_message(self, *a):
        pass
print("INFO Model loading took 5.42 GiB and 12.0 seconds", flush=True)
print("INFO GPU KV cache size: 46,752 tokens", flush=True)
srv = HTTPServer(("127.0.0.1", port), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
while time.time() - last[0] < 30:         # exits on its own if the runner's stop signal is lost
    time.sleep(0.5)
'''


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash for scripts/serve_model.sh")
def test_run_end_to_end_with_fake_server(canonical_synth, tmp_path, monkeypatch):
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    (tmp_path / "fake_vllm.py").write_text(FAKE_SERVER, encoding="utf-8")
    py = Path(sys.executable).as_posix()
    vllm = venv / "bin" / "vllm"
    vllm.write_text(f'#!/usr/bin/env bash\nexec "{py}" "{(tmp_path / "fake_vllm.py").as_posix()}" "$@"\n', encoding="utf-8")
    vllm.chmod(0o755)
    monkeypatch.setenv("VLLM_VENV", str(venv))
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    exp = canonical_run_cfg(canonical_synth["dh"], tmp_path / "res", retrieval=["none", "hybrid"], n_samples=3,
                            conditions=["full"], port=port, server_timeout_s=60)
    exp.pop("_hash")
    (tmp_path / "exp.yaml").write_text(yaml.safe_dump(exp), encoding="utf-8")
    real_which = shutil.which
    monkeypatch.setattr(shutil, "which", lambda n, *a, **k: None if n == "nvidia-smi" else real_which(n, *a, **k))
    rep = feasibility.run(HW, "qwen35-4b-fp8", tmp_path / "exp.yaml", tmp_path / "feas")
    assert rep["server"]["ready"] and rep["server"]["kv_cache_tokens"] == 46752
    assert rep["grid"]["live_rows"] > 0 and rep["grid"]["parse_rate"] == 1.0
    assert rep["verdict"]["request_tokens"] == 1500 + 3 * 400 and rep["verdict"]["feasible"]
    args = (tmp_path / "feas" / "qwen35-4b-fp8" / "server.args").read_text(encoding="utf-8")
    assert "--revision 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a" in args and "--quantization fp8" in args
    if os.name != "nt":                 # MSYS bash `exec` detaches the child from the Windows process tree
        assert not feasibility._port_busy(port)                        # the runner stopped what it started
    with pytest.raises(RuntimeError, match="exists"):
        feasibility.run(HW, "qwen35-4b-fp8", tmp_path / "exp.yaml", tmp_path / "feas")
    rows = feasibility.report(tmp_path / "feas")
    assert rows[0]["profile"] == "qwen35-4b-fp8" and rows[0]["feasible"]
    assert (tmp_path / "feas" / "feasibility.csv").is_file()


def _arm_rows(pp, correct, tokens=800, parse=1.0, role="val"):
    return [{"case_id": f"inc{i // 2}", "condition": "full" if i % 2 else "no_metric", "retrieval": "none",
             "store_mode": "-", "split_role": role, "sampling": {"n": 10, "presence_penalty": pp},
             "correct": c, "correct_at_3": True, "parse_rate": parse, "conf_consensus": 0.7, "conf_verbal_sd": 5.0,
             "completion_tokens": tokens, "latency_s": 3.0} for i, c in enumerate(correct)]


def _write(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_compare_sampling_keeps_base_without_clear_gain(tmp_path):
    f = tmp_path / "grid.jsonl"
    _write(f, _arm_rows(None, [True, False] * 20) + _arm_rows(1.5, [False, True] * 20))   # None = server default 0
    rep = feasibility.compare_sampling(f, n_boot=500)
    assert rep["pairs"] == 40 and rep["incidents"] == 20 and rep["choice"] == 0.0
    assert rep["base"]["ac1"] == rep["alt"]["ac1"] == 0.5


def test_compare_sampling_switches_only_on_gain_parse_and_cost(tmp_path):
    f = tmp_path / "grid.jsonl"
    base = _arm_rows(None, [False] * 40)
    _write(f, base + _arm_rows(1.5, [True] * 40))
    assert feasibility.compare_sampling(f, n_boot=500)["choice"] == 1.5
    _write(f, base + _arm_rows(1.5, [True] * 40, tokens=1100))      # +37.5 % completion tokens
    assert feasibility.compare_sampling(f, n_boot=500)["choice"] == 0.0
    _write(f, base + _arm_rows(1.5, [True] * 40, parse=0.95))
    assert feasibility.compare_sampling(f, n_boot=500)["choice"] == 0.0


def test_compare_sampling_refuses_test_rows(tmp_path):
    f = tmp_path / "grid.jsonl"
    _write(f, _arm_rows(None, [True] * 4, role="test") + _arm_rows(1.5, [True] * 4, role="test"))
    with pytest.raises(ValueError, match="DEV"):
        feasibility.compare_sampling(f)


def test_dev_sampling_config_pairs_two_arms():
    cfg = run_grid.load_cfg(ROOT / "configs" / "exp" / "dev-sampling.yaml")
    a, b = cfg["models"]
    assert cfg["split_role"] == "val" and "jev" not in cfg
    assert a.get("presence_penalty") is None and b["presence_penalty"] == 1.5
    assert {k: v for k, v in b.items() if k != "presence_penalty"} == a


def test_presence_penalty_arms_do_not_collide(canonical_synth, tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    cfg = canonical_run_cfg(canonical_synth["dh"], tmp_path, retrieval=["none"], conditions=["full"],
                            models=[{"name": "mock-small", "backend": "mock"},
                                    {"name": "mock-small", "backend": "mock", "presence_penalty": 1.5}])
    run_grid.prepare(cfg)
    run_grid.run(cfg)
    rows = [json.loads(l) for l in Path(cfg["out"]).read_text(encoding="utf-8").splitlines()]
    by = {}
    for r in rows:
        by.setdefault(r["sampling"]["presence_penalty"], []).append(r)
    assert set(by) == {None, 1.5} and len(by[None]) == len(by[1.5]) > 0
    assert all("|pp=" not in r["key"] for r in by[None]) and all(r["key"].endswith("|pp=1.5") for r in by[1.5])
