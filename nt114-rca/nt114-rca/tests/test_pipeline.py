"""Chạy: PYTHONPATH=src python -m pytest -q tests   (hoặc python tests/test_pipeline.py)"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rca import ablate, metrics
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
    """Giả lập endpoint /v1/chat/completions của vLLM."""
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert body["response_format"]["type"] == "json_schema"
        enum = body["response_format"]["json_schema"]["schema"]["properties"]["ranking"]["items"]["enum"]
        msg = json.dumps({"reason": "r", "ranking": enum[:2], "confidence": 70,
                          "insufficient_evidence": False, "next_check": "logs"})
        res = {"choices": [{"message": {"content": msg}}] * body["n"],
               "usage": {"prompt_tokens": 1000, "completion_tokens": 50}}
        self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(res).encode())

    def log_message(self, *a):
        pass


def test_vllm_http(tmp_path=Path("/tmp")):
    srv = HTTPServer(("127.0.0.1", 0), _Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    llm = LLM("m", f"http://127.0.0.1:{srv.server_port}/v1", n=3, cache=Cache(str(tmp_path / "t_cache.sqlite")))

    class C: system = "online-boutique"
    msgs = build_messages(C, ["x", "y", "z"], "evidence")
    r1 = llm.ask(msgs, ["x", "y", "z"])
    r2 = llm.ask(msgs, ["x", "y", "z"])
    assert len(r1["samples"]) == 3 and r1["prompt_tokens"] == 1000 and r2["cached"]
    srv.shutdown()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
