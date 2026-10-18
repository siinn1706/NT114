"""Raw-output persistence: completions, parsed samples, logprobs and request metadata, never credentials."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import canonical_run_cfg
from rca import run_grid
from rca.llm import LLM, Cache, build_messages, check_no_secrets, compact_logprobs, redact_url

MSG = json.dumps({"reason": "slow db", "ranking": ["a", "b"], "confidence": 70, "insufficient_evidence": False,
                  "next_check": "logs"})
LP = {"content": [{"token": "{", "logprob": -0.01, "bytes": [123],
                   "top_logprobs": [{"token": "{", "logprob": -0.01, "bytes": [123]},
                                    {"token": " ", "logprob": -5.2, "bytes": [32]}]}]}
CANDS = ["a", "b", "c"]
GRID_LABEL_FIELDS = {"truth", "truth_ids", "fault", "correct", "correct_at_3", "rank", "hits", "hit_has_truth",
                     "label_granularity", "set_scored"}


class _C:
    system = "online-boutique"


def _live(monkeypatch, tmp_path, sent, **kw) -> LLM:
    llm = LLM("m", "http://user:secret@127.0.0.1:8000/v1?key=abc", revision="abc", server_fp="fp", n=2,
              cache=Cache(str(tmp_path / "c.sqlite")), **kw)
    res = {"id": "chatcmpl-1", "model": "m", "created": 1,
           "choices": [{"message": {"content": MSG}, "finish_reason": "stop", "logprobs": LP}] * 2,
           "usage": {"prompt_tokens": 10, "completion_tokens": 4}}
    monkeypatch.setattr(llm, "_post", lambda path, body=None: sent.append(body) or res)
    return llm


def _keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


def test_raw_record_has_completions_logprobs_and_request(monkeypatch, tmp_path):
    sent = []
    llm = _live(monkeypatch, tmp_path, sent, logprobs=True)
    msgs = build_messages(_C, CANDS, "evidence text")
    out = llm.ask(msgs, CANDS)
    raw = out["raw"]
    assert raw["texts"] == [MSG, MSG] and raw["finish_reasons"] == ["stop", "stop"]
    assert raw["logprobs"][0] == [{"token": "{", "logprob": -0.01, "top": [["{", -0.01], [" ", -5.2]]}]
    assert raw["response"]["id"] == "chatcmpl-1" and raw["response"]["usage"]["prompt_tokens"] == 10
    req = raw["request"]
    assert "messages" not in req and len(req["messages_sha256"]) == 64
    assert req["endpoint"] == "http://127.0.0.1:8000/v1/chat/completions"
    assert req["top_logprobs"] == 5 and req["n"] == 2 and req["candidates"] == CANDS and req["cache_key"] == llm.key(msgs, CANDS)
    blob = json.dumps(raw)
    assert "secret" not in blob and "key=abc" not in blob and "evidence text" not in blob
    assert out["samples"][0]["reason"] == "slow db"                     # parsed outputs keep the reason
    again = llm.ask(msgs, CANDS)
    assert again["cached"] and again["raw"] == raw and len(sent) == 1


def test_keep_raw_off_stores_nothing_raw(monkeypatch, tmp_path):
    llm = _live(monkeypatch, tmp_path, [], keep_raw=False)
    msgs = build_messages(_C, CANDS, "e")
    out = llm.ask(msgs, CANDS)
    assert "raw" not in out and "raw" not in llm.cache.get(llm.key(msgs, CANDS))


def test_cache_key_and_old_entries_unchanged(monkeypatch, tmp_path):
    msgs = build_messages(_C, CANDS, "e")
    on = _live(monkeypatch, tmp_path, [])
    off = LLM("m", "http://127.0.0.1:8000/v1", revision="abc", server_fp="fp", n=2, cache=on.cache, keep_raw=False)
    k = on.key(msgs, CANDS)
    assert off.key(msgs, CANDS) == k                                     # persistence never enters the key
    old = {"samples": [{"ok": True, "ranking": ["a"], "confidence": 0.7, "insufficient": False, "next_check": ""}],
           "prompt_tokens": 1, "completion_tokens": 1, "latency_s": 0.1}
    on.cache.put(k, old)                                                 # a value written before this change
    hit = on.ask(msgs, CANDS)
    assert hit["cached"] and hit["samples"] == old["samples"] and "raw" not in hit


def test_secret_guard_and_helpers():
    with pytest.raises(ValueError, match="credential"):
        check_no_secrets({"a": [{"Authorization": "Bearer x"}]})
    check_no_secrets({"logprobs": [[{"token": "a", "logprob": -1.0}]], "usage": {"prompt_tokens": 3}})
    assert compact_logprobs(None) is None and compact_logprobs({"content": []}) == []
    assert redact_url("https://u:p@h.example:8443/v1?api_key=z#f") == "https://h.example:8443/v1"
    assert redact_url("http://u:p@[::1]:8000/v1") == "http://[::1]:8000/v1"


def test_sampled_token_logprob_kept_when_outside_top():
    lp = {"content": [{"token": "x", "logprob": -7.5, "bytes": [120],
                       "top_logprobs": [{"token": "a", "logprob": -0.1}, {"token": "b", "logprob": -2.3}]}]}
    assert compact_logprobs(lp) == [{"token": "x", "logprob": -7.5, "top": [["a", -0.1], ["b", -2.3]]}]


def test_mock_backend_records_raw(tmp_path):
    llm = LLM("mock-x", backend="mock", n=3, cache=Cache(str(tmp_path / "m.sqlite")))
    out = llm.ask(build_messages(_C, CANDS, "- a: cpu up z=9"), CANDS)
    assert len(out["raw"]["texts"]) == 3 and out["raw"]["request"]["endpoint"] == "mock"
    assert out["raw"]["logprobs"] is None


def test_run_grid_writes_one_raw_record_per_cell(canonical_synth, tmp_path):
    dh = canonical_synth["dh"]
    over = dict(conditions=["full", "no_log"], retrieval=["none"], store_modes=["precedent"],
                models=[{"name": "mock-a", "backend": "mock"}])
    cfg = canonical_run_cfg(dh, tmp_path / "on", **over)
    run_grid.prepare(cfg)
    run_grid.run(cfg)
    out = Path(cfg["out"]).parent
    grid = [json.loads(l) for l in open(cfg["out"], encoding="utf-8")]
    raw = [json.loads(l) for l in open(out / "llm_raw.jsonl", encoding="utf-8")]
    assert grid and {r["key"] for r in raw} == {r["key"] for r in grid} and len(raw) == len(grid)
    for r in raw:
        assert r["raw_available"] and len(r["texts"]) == cfg["n_samples"] == len(r["samples"])
        assert not (set(r) & GRID_LABEL_FIELDS)
        check_no_secrets(r)
    assert json.loads((out / "manifest.json").read_text(encoding="utf-8"))["raw_outputs"] == "llm_raw.jsonl"
    run_grid.run(cfg)                                                    # resume: nothing new, no duplicates
    assert sum(1 for _ in open(out / "llm_raw.jsonl", encoding="utf-8")) == len(raw)

    # crash after the raw write, before the grid row: drop the last grid row and tear the raw file's tail
    lines = open(cfg["out"], encoding="utf-8").read().splitlines(keepends=True)
    open(cfg["out"], "w", encoding="utf-8", newline="\n").writelines(lines[:-1])
    with open(out / "llm_raw.jsonl", "a", encoding="utf-8", newline="") as f:
        f.write('{"key": "torn')
    run_grid.run(cfg)
    grid2 = [json.loads(l) for l in open(cfg["out"], encoding="utf-8")]
    raw2 = [json.loads(l) for l in open(out / "llm_raw.jsonl", encoding="utf-8").read().splitlines()
            if l.strip() and not l.startswith('{"key": "torn')]
    assert len(grid2) == len(grid) and len(raw2) == len(raw)          # the resumed cell reuses its raw record
    assert sorted(r["key"] for r in raw2) == sorted(r["key"] for r in grid2)

    off = canonical_run_cfg(dh, tmp_path / "off", raw_outputs=False, **over)
    run_grid.prepare(off)
    run_grid.run(off)
    assert not (Path(off["out"]).parent / "llm_raw.jsonl").exists()
    assert json.loads((Path(off["out"]).parent / "manifest.json").read_text(encoding="utf-8"))["raw_outputs"] is None
