"""Jev client: API shape, state allowlist, option order, version guard, retries, cache. Fake HTTP only."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from rca import jev, schema

INP = jev.DecisionInputs("## Metrics\n- cart: cpu up z=9", ["cart", "frontend", "payment"], 0.85, 0.8, 10, 0.1,
                         {"metrics": 1, "logs": 0, "traces": 1}, 6, top_sim=0.41)


def _ok_response(body, model="jev-1.13.0", choice=None):
    opts = list(body["questions"]["action"]["criteria"])
    pick = choice or opts[-1]
    probs = {o: (0.7 if o == pick else 0.3 / (len(opts) - 1)) for o in opts}
    return {"model": model, "answers": {"action": {"choice": pick, "probabilities": probs, "confidence": 0.5},
                                        "supported": {"noul": 0.6}}, "usage": {"input_tokens": 100, "output_tokens": 0}}


class _Server:
    """Scripted responses: each item is (status, body-or-callable)."""

    def __init__(self, script):
        self.script, self.requests = list(script), []
        outer = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append({"body": body, "auth": self.headers.get("Authorization")})
                status, resp = outer.script.pop(0) if len(outer.script) > 1 else outer.script[0]
                resp = resp(body) if callable(resp) else resp
                self.send_response(status); self.end_headers(); self.wfile.write(json.dumps(resp).encode())

            def log_message(self, *a):
                pass

        self.srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_port}/v1/systemone"

    def close(self):
        self.srv.shutdown()


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv(jev.API_KEY_ENV, "test-key-not-real")


def _client(url, tmp_path, **kw):
    return jev.JevClient(url=url, cache=tmp_path / "jev.sqlite", sleep=lambda s: None, **kw)


def test_payload_shape(key, tmp_path):
    srv = _Server([(200, _ok_response)])
    try:
        res, raw = _client(srv.url, tmp_path).decide(jev.build_state(INP), jev.build_questions(jev.ACTIONS), "u|full|first_look")
    finally:
        srv.close()
    body = srv.requests[0]["body"]
    assert srv.requests[0]["auth"] == "Bearer test-key-not-real"
    assert body["model"] == "jev-1.13.0" and set(body) == {"model", "state", "questions"}
    a = body["questions"]["action"]
    assert a["type"] == "choice" and isinstance(a["criteria"], dict) and set(a["criteria"]) == set(jev.ACTIONS)
    assert "options" not in a and isinstance(a["instructions"], str)
    assert body["questions"]["supported"]["type"] == "noul"
    assert res.status == "ok" and res.action in jev.ACTIONS and abs(sum(res.probabilities.values()) - 1) < 1e-9
    assert res.supported == 0.6 and raw["request"] == body and "test-key" not in json.dumps(raw)


def test_state_allowlist():
    deny_tokens = frozenset({"root", "fault", "label", "gt", "answer", "culprit"})
    assert schema._DENY_TOKENS == deny_tokens                      # this plan never edits the denylist
    assert schema.denylisted("assistant_first_answer")             # ...which is why the allowlist takes precedence
    st = jev.build_state(INP)
    assert set(st) <= schema.DECISION_STATE_ALLOWED_KEYS and st["assistant_first_answer"] == "cart"
    assert st["assistant_confidence"] == "self-reported 85/100 (high); 8 of 10 samples agree (high)"
    assert st["similar_past_incident_similarity"] == "0.41 (low)" and st["candidate_count"] == "6"
    with pytest.raises(ValueError, match="denylisted"):
        jev.check_state({**st, "telemetry_available": {"root": "cart"}})
    with pytest.raises(ValueError, match="not allowed"):
        jev.check_state({**st, "truth": "cart"})
    assert "evidence" not in jev.build_state(INP, drop=("evidence",))


def test_numbers_are_banded_text():
    st = jev.build_state(jev.DecisionInputs("e", [], 0.3, 0.5, 10, 0.9, {}, 3, stage="after_escalation"))
    assert st["assistant_confidence"] == "self-reported 30/100 (low); 5 of 10 samples agree (medium)"
    assert st["assistant_first_answer"].startswith("none") and st["assistant_flagged_insufficient"] == "yes"
    assert "similar_past_incident_similarity" not in st and st["decision_stage"] == "after_escalation"


def test_available_actions():
    q = jev.build_questions(("accept", "escalate", "abstain"))
    assert list(q["action"]["criteria"]) == ["accept", "escalate", "abstain"]
    assert set(jev.build_questions(jev.ACTIONS, "after_retrieval")["action"]["criteria"]) == {"accept", "abstain"}
    with pytest.raises(ValueError):
        jev.build_questions(("accept", "retrieve"))


def test_option_order(tmp_path):
    q = jev.build_questions(jev.ACTIONS)
    a, oa = jev.order_options(q, "u|full|first_look")
    b, ob = jev.order_options(q, "u|full|first_look")
    assert oa == ob == list(a["action"]["criteria"]) and sorted(oa) == sorted(jev.ACTIONS)
    orders = {tuple(jev.order_options(q, f"u{i}|full|first_look")[1]) for i in range(30)}
    assert len(orders) > 3
    res, _ = jev.JevClient(backend="mock").decide(jev.build_state(INP), q, "u|full|first_look")
    assert res.option_order == oa                                   # logged with the result


def test_version_guard(key, tmp_path):
    srv = _Server([(200, lambda b: _ok_response(b, model="jev-1.14.0"))])
    try:
        with pytest.raises(jev.JevVersionError):
            _client(srv.url, tmp_path).decide(jev.build_state(INP), jev.build_questions(jev.ACTIONS), "s")
    finally:
        srv.close()
    # the observed string recorded in M0 is what the guard compares against
    srv = _Server([(200, lambda b: _ok_response(b, model="jev-1.13.0+build7"))])
    try:
        res, _ = _client(srv.url, tmp_path, expected_model="jev-1.13.0+build7").decide(
            jev.build_state(INP), jev.build_questions(jev.ACTIONS), "s")
        assert res.status == "ok" and res.model == "jev-1.13.0+build7"
    finally:
        srv.close()


def test_retry_policy(key, tmp_path):
    srv = _Server([(429, {"error": "rate"}), (529, {"error": "busy"}), (200, _ok_response)])
    try:
        c = _client(srv.url, tmp_path)
        res, _ = c.decide(jev.build_state(INP), jev.build_questions(jev.ACTIONS), "s")
        assert res.status == "ok" and c.http_calls == 3
    finally:
        srv.close()
    srv = _Server([(422, {"error": "bad"})])
    try:
        c = _client(srv.url, tmp_path / "fresh")
        with pytest.raises(jev.JevRequestError, match="422"):
            c.decide(jev.build_state(INP), jev.build_questions(jev.ACTIONS), "s2")
        assert c.http_calls == 1
    finally:
        srv.close()


def test_errors_not_cached(key, tmp_path):
    srv = _Server([(529, {"error": "busy"})])
    try:
        c = _client(srv.url, tmp_path, max_retries=2)
        res, _ = c.decide(jev.build_state(INP), jev.build_questions(jev.ACTIONS), "s")
        assert res.status == "error" and c.http_calls == 2
    finally:
        srv.close()
    srv = _Server([(200, lambda b: _ok_response(b, choice="nonsense"))])     # invalid response, not cached either
    try:
        c = _client(srv.url, tmp_path)
        res, _ = c.decide(jev.build_state(INP), jev.build_questions(jev.ACTIONS), "s")
        assert res.status == "invalid_response"
    finally:
        srv.close()
    srv = _Server([(200, _ok_response)])
    try:
        c = _client(srv.url, tmp_path)
        res, _ = c.decide(jev.build_state(INP), jev.build_questions(jev.ACTIONS), "s")
        assert res.status == "ok" and not res.cached and c.http_calls == 1
    finally:
        srv.close()


def test_cache_key(key, tmp_path, monkeypatch):
    srv = _Server([(200, _ok_response)])
    try:
        c = _client(srv.url, tmp_path)
        st, q = jev.build_state(INP), jev.build_questions(jev.ACTIONS)
        first, _ = c.decide(st, q, "s")
        again, _ = c.decide(st, q, "s")
        assert not first.cached and again.cached and c.http_calls == 1 and again.action == first.action
        monkeypatch.setattr(jev, "JEV_QUESTION_VERSION", "q2")
        changed, _ = c.decide(st, q, "s")
        assert not changed.cached and c.http_calls == 2
    finally:
        srv.close()


def test_missing_key_and_provider(monkeypatch, tmp_path):
    monkeypatch.delenv(jev.API_KEY_ENV, raising=False)
    with pytest.raises(RuntimeError, match=jev.API_KEY_ENV):
        _client("http://127.0.0.1:9/never", tmp_path).decide(jev.build_state(INP), jev.build_questions(jev.ACTIONS), "s")
    with pytest.raises(ValueError, match="TypeSafe"):
        jev.JevClient(provider="cloudflare")


def test_mock_is_deterministic_and_valid():
    c = jev.JevClient(backend="mock")
    q = jev.build_questions(("accept", "escalate", "abstain"))
    a, _ = c.decide(jev.build_state(INP), q, "s")
    b, _ = c.decide(jev.build_state(INP), q, "s")
    assert a.summary() == b.summary() and a.status == "ok" and a.action in q["action"]["criteria"]
