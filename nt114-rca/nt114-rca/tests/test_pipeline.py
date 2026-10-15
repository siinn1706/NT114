"""Chạy: PYTHONPATH=src python -m pytest -q tests   (hoặc python tests/test_pipeline.py)"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rca import ablate, llm as llm_mod, metrics
from rca.data import canon
from rca.llm import LLM, Cache, aggregate, build_messages, parse
from rca.retrieve import BM25, tokenize


def test_canon():
    assert canon("frontendservice") == canon("frontend") == "frontend"
    assert canon("ts-auth-service") == "auth"
    assert canon("front-end") == "frontend"


def test_metrics():
    assert metrics.rank_of_truth(["a", "b"], "b") == 2
    assert metrics.rank_of_truth(["a", "b"], "z") == 3
    assert metrics.ac_at_k([1, 2, 3, 1], 1) == 0.5
    assert metrics.ece([1, 1, 0, 0], [1, 1, 0, 0]) == 0.0
    assert abs(metrics.ece([0, 0], [0.9, 0.9]) - 0.9) < 1e-9
    assert metrics.confident_wrong_rate([0, 1, 0], [0.9, 0.9, 0.5]) == 1 / 3
    assert metrics.mcnemar([1, 1, 0], [1, 1, 0])["p"] == 1.0


def test_ablation():
    tr = pd.DataFrame({"svc": ["a", "b", "a"], "duration": [1, 2, 3]})
    tel = {"metrics": pd.DataFrame({"time": [1]}), "logs": pd.DataFrame({"x": [1]}), "traces": tr}
    assert ablate.apply(tel, "no_trace", "a")["traces"] is None
    assert set(ablate.apply(tel, "blind_root", "a")["traces"]["svc"]) == {"b"}
    assert not ablate.applicable("no_trace", {**tel, "traces": None})


def test_bm25():
    bm = BM25([tokenize("cart latency up"), tokenize("payment cpu up")])
    s = bm.scores(tokenize("cart latency"))
    assert s[0] > s[1]


def test_parse_and_aggregate():
    c = ["a", "b", "c"]
    s = [parse(json.dumps({"ranking": ["a", "b"], "confidence": 80, "insufficient_evidence": False,
                           "next_check": "x", "reason": "r"}), c) for _ in range(3)]
    s.append(parse("garbage", c))
    g = aggregate(s)
    assert g["ranking"][0] == "a" and g["conf_consensus"] == 0.75 and abs(g["conf_verbal"] - 0.8) < 1e-9


class _Fake(BaseHTTPRequestHandler):
    """Giả lập endpoint /v1/models và /v1/chat/completions của vLLM."""
    models = [{"id": "m", "root": "m"}]

    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(json.dumps({"data": type(self).models}).encode())

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert body["chat_template_kwargs"] == {"enable_thinking": False}
        if "response_format" not in body:                      # T=0 canary of the server fingerprint
            res = {"choices": [{"message": {"content": "ready"}}]}
            self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(res).encode())
            return
        assert body["response_format"]["type"] == "json_schema"
        enum = body["response_format"]["json_schema"]["schema"]["properties"]["ranking"]["items"]["enum"]
        msg = json.dumps({"reason": "r", "ranking": enum[:2], "confidence": 70,
                          "insufficient_evidence": False, "next_check": "logs"})
        res = {"choices": [{"message": {"content": msg}}] * body["n"],
               "usage": {"prompt_tokens": 1000, "completion_tokens": 50}}
        self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(res).encode())

    def log_message(self, *a):
        pass


@pytest.fixture
def fake_vllm():
    srv = HTTPServer(("127.0.0.1", 0), _Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}/v1"
    srv.shutdown()


def _args(tmp_path, text="m --revision abc --quantization fp8 --enable-prefix-caching"):
    p = tmp_path / "server.args"
    p.write_text(text, encoding="utf-8")
    return p


class _C:
    system = "online-boutique"


def test_vllm_http(fake_vllm, tmp_path):
    llm = LLM("m", fake_vllm, n=3, cache=Cache(str(tmp_path / "t_cache.sqlite")), revision="abc")
    msgs = build_messages(_C, ["x", "y", "z"], "evidence")
    with pytest.raises(RuntimeError, match="fingerprint"):
        llm.ask(msgs, ["x", "y", "z"])                     # a live server is never asked without its fingerprint
    llm.server_fingerprint(_args(tmp_path), "fp8")
    r1 = llm.ask(msgs, ["x", "y", "z"])
    r2 = llm.ask(msgs, ["x", "y", "z"])
    assert len(r1["samples"]) == 3 and r1["prompt_tokens"] == 1000 and r2["cached"]


def test_server_fingerprint(fake_vllm, tmp_path):
    llm = LLM("m", fake_vllm, revision="abc")
    fp = llm.server_fingerprint(_args(tmp_path), "fp8")
    with pytest.raises(RuntimeError, match="revision"):
        LLM("m", fake_vllm, revision="other").server_fingerprint(_args(tmp_path), "fp8")
    with pytest.raises(RuntimeError, match="quantization"):
        LLM("m", fake_vllm, revision="abc").server_fingerprint(_args(tmp_path), "awq")
    with pytest.raises(RuntimeError, match="launch arguments"):
        LLM("m", fake_vllm, revision="abc").server_fingerprint(tmp_path / "missing.args")
    other = LLM("m", fake_vllm, revision="abc").server_fingerprint(_args(tmp_path, "m --revision abc --quantization fp8 --max-model-len 8192"), "fp8")
    _Fake.models = [{"id": "m", "root": "other-weights"}]
    try:
        served = LLM("m", fake_vllm, revision="abc").server_fingerprint(_args(tmp_path), "fp8")
    finally:
        _Fake.models = [{"id": "m", "root": "m"}]
    assert len({fp, other, served}) == 3                    # launch args and served model both enter the fingerprint


def test_cache_key_versions(monkeypatch, tmp_path):
    msgs = build_messages(_C, ["x", "y"], "evidence")
    base = LLM("m", backend="mock", cache=Cache(str(tmp_path / "c.sqlite")))
    k = base.key(msgs, ["x", "y"])
    assert LLM("m", backend="mock", revision="r2", cache=base.cache).key(msgs, ["x", "y"]) != k
    assert LLM("m", backend="mock", max_tokens=200, cache=base.cache).key(msgs, ["x", "y"]) != k
    assert LLM("m", backend="mock", chat_template_kwargs={"enable_thinking": True}, cache=base.cache).key(msgs, ["x", "y"]) != k
    out = base.ask(msgs, ["x", "y"])
    monkeypatch.setattr(llm_mod, "PROMPT_VERSION", "v2")
    assert base.key(msgs, ["x", "y"]) != k
    again = base.ask(msgs, ["x", "y"])
    assert not again["cached"] and again["samples"] == out["samples"]   # mock output does not depend on the key


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and not fn.__code__.co_argcount:   # fixture tests run under pytest only
            fn(); print("ok", name)
