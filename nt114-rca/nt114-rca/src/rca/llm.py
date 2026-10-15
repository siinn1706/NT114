"""Gọi LLM (vLLM, API kiểu OpenAI) với đầu ra JSON bắt buộc, lấy nhiều mẫu, cache trên đĩa.

Không cần thư viện `openai`: gọi HTTP thuần bằng urllib.
Backend "mock" giả lập LLM từ bằng chứng để test pipeline khi chưa có GPU.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import sqlite3
import time
import urllib.request
from collections import Counter
from pathlib import Path

# Bump on any change to SYSTEM_PROMPT, USER_TEMPLATE or schema(): it is part of every cache and result key.
PROMPT_VERSION = "v1"
MOCK_SEED = "mock-v1"
CANARY_MESSAGES = [{"role": "user", "content": "Reply with the single word: ready"}]

SYSTEM_PROMPT = (
    "You are an on-call SRE assistant for a microservice system. Given monitoring evidence collected "
    "around an incident, identify which service is the ROOT CAUSE (not merely a service showing symptoms). "
    "Upstream callers often look slow because a downstream dependency is faulty. "
    "Some telemetry may be missing; if the evidence is not enough to decide, say so via "
    "insufficient_evidence=true and tell the engineer what to check next. "
    "confidence is your probability (0-100) that ranking[0] is the true root cause."
)

USER_TEMPLATE = """# Incident
System: {system}
Candidate services: {candidates}

# Evidence
{evidence}

{retrieved}

Answer in JSON only."""


def schema(candidates: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "reason": {"type": "string", "maxLength": 400},
            "ranking": {"type": "array", "items": {"type": "string", "enum": candidates},
                        "minItems": 1, "maxItems": 5},
            "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
            "insufficient_evidence": {"type": "boolean"},
            "next_check": {"type": "string", "maxLength": 200},
        },
        "required": ["reason", "ranking", "confidence", "insufficient_evidence", "next_check"],
    }


def build_messages(case, candidates, evidence_text, retrieved_text="") -> list[dict]:
    user = USER_TEMPLATE.format(system=case.system, candidates=", ".join(candidates),
                                evidence=evidence_text, retrieved=retrieved_text)
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


# ---------------------------------------------------------------- cache
class Cache:
    def __init__(self, path="results/llm_cache.sqlite"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS c (k TEXT PRIMARY KEY, v TEXT)")

    def get(self, k):
        r = self.db.execute("SELECT v FROM c WHERE k=?", (k,)).fetchone()
        return json.loads(r[0]) if r else None

    def put(self, k, v):
        self.db.execute("INSERT OR REPLACE INTO c VALUES (?,?)", (k, json.dumps(v)))
        self.db.commit()


# ---------------------------------------------------------------- client
class LLM:
    def __init__(self, model: str, base_url="http://localhost:8000/v1", backend="vllm",
                 n=5, temperature=0.7, max_tokens=400, seed=0, cache: Cache | None = None, timeout=300,
                 revision: str | None = None, chat_template_kwargs: dict | None = None, logprobs: bool = False,
                 server_fp: str | None = None):
        if backend != "mock" and not revision:
            raise ValueError(f"model {model!r}: a live backend needs a pinned `revision` (commit sha of the weights)")
        self.model, self.base_url, self.backend = model, base_url.rstrip("/"), backend
        self.n, self.temperature, self.max_tokens, self.seed = n, temperature, max_tokens, seed
        self.cache, self.timeout = cache or Cache(), timeout
        self.revision, self.logprobs = revision, logprobs
        self.chat_template_kwargs = {"enable_thinking": False} if chat_template_kwargs is None else dict(chat_template_kwargs)
        self.server_fp = server_fp if server_fp is not None else ("mock" if backend == "mock" else None)

    def key(self, messages, candidates) -> str:
        if self.server_fp is None:
            raise RuntimeError("server fingerprint not set: call server_fingerprint() before asking a live server")
        blob = json.dumps([self.model, self.revision, self.backend, self.n, self.temperature, self.seed, self.max_tokens,
                           PROMPT_VERSION, self.chat_template_kwargs, self.logprobs, self.server_fp, messages, candidates],
                          sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()

    def ask(self, messages, candidates) -> dict:
        k = self.key(messages, candidates)
        hit = self.cache.get(k)
        if hit is not None:
            return {**hit, "cached": True}
        t0 = time.time()
        raw = self._mock(messages, candidates) if self.backend == "mock" else self._vllm(messages, candidates)
        samples = [parse(x, candidates) for x in raw["texts"]]
        out = {"samples": samples, "prompt_tokens": raw.get("prompt_tokens"),
               "completion_tokens": raw.get("completion_tokens"), "latency_s": round(time.time() - t0, 3)}
        self.cache.put(k, out)
        return {**out, "cached": False}

    def _vllm(self, messages, candidates) -> dict:
        body = {
            "model": self.model, "messages": messages, "n": self.n, "temperature": self.temperature,
            "max_tokens": self.max_tokens, "seed": self.seed, "chat_template_kwargs": self.chat_template_kwargs,
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "rca", "schema": schema(candidates)}},
        }
        if self.logprobs:
            body.update(logprobs=True, top_logprobs=5)
        res = self._post("/chat/completions", body)
        u = res.get("usage", {})
        out = {"texts": [c["message"]["content"] for c in res["choices"]],
               "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens")}
        if self.logprobs:
            out["logprobs"] = [c.get("logprobs") for c in res["choices"]]
        return out

    def _post(self, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"{self.base_url}{path}", data=data, headers={"Content-Type": "application/json"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read())
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(5 * (attempt + 1))

    def server_fingerprint(self, launch_args_path=None, quantization: str | None = None) -> str:
        """sha of the served model list, the launch arguments written by scripts/serve_model.sh and the
        T=0 answer to a fixed canary prompt. Raises when the launch arguments contradict the configured
        revision or quantisation. Sets and returns `self.server_fp`."""
        if self.backend == "mock":
            self.server_fp = "mock"
            return self.server_fp
        if not launch_args_path or not Path(launch_args_path).is_file():
            raise RuntimeError(f"launch arguments file {launch_args_path!r} not found (written by scripts/serve_model.sh)")
        args = Path(launch_args_path).read_text(encoding="utf-8").split()
        for flag, want in (("--revision", self.revision), ("--quantization", quantization)):
            got = args[args.index(flag) + 1] if flag in args[:-1] else None
            if want is not None and got != want:
                raise RuntimeError(f"server {flag} is {got!r}, config expects {want!r}")
        models = self._post("/models")
        canary = self._post("/chat/completions", {"model": self.model, "messages": CANARY_MESSAGES, "temperature": 0,
                                                  "max_tokens": 8, "seed": 0, "chat_template_kwargs": self.chat_template_kwargs})
        blob = json.dumps([models.get("data"), args, canary["choices"][0]["message"]["content"]], sort_keys=True)
        self.server_fp = hashlib.sha256(blob.encode()).hexdigest()[:16]
        return self.server_fp

    def _mock(self, messages, candidates) -> dict:
        """LLM giả: tin dịch vụ có z-score cao nhất ở phần Metrics, nhiễu ngẫu nhiên. Chỉ để test."""
        text = messages[-1]["content"]
        # seeded independently of the cache key, so adding key fields does not change mock fixtures
        rng = random.Random(hashlib.sha256(json.dumps([MOCK_SEED, self.model, self.seed, messages, candidates]).encode()).hexdigest())
        seen = [s for s in re.findall(r"^- ([a-z0-9]+):", text, re.M) if s in candidates]
        order = list(dict.fromkeys(seen + candidates))
        outs = []
        for _ in range(self.n):
            r = order[:]
            if rng.random() < 0.3:
                rng.shuffle(r)
            thin = "Not available" in text
            conf = rng.randint(55, 95) if not thin else rng.randint(40, 90)
            outs.append(json.dumps({"reason": "mock", "ranking": r[:5], "confidence": conf,
                                    "insufficient_evidence": thin and rng.random() < 0.3,
                                    "next_check": f"check logs of {r[0]}"}))
        return {"texts": outs, "prompt_tokens": len(text) // 4, "completion_tokens": 60 * self.n}


def parse(text: str, candidates: list[str]) -> dict:
    try:
        d = json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        try:
            d = json.loads(m.group(0)) if m else {}
        except Exception:
            d = {}
    rank = [s for s in d.get("ranking", []) if s in candidates]
    return {"ok": bool(rank), "ranking": rank, "confidence": float(d.get("confidence", 0)) / 100,
            "insufficient": bool(d.get("insufficient_evidence", False)), "next_check": d.get("next_check", "")}


def aggregate(samples: list[dict]) -> dict:
    """Gộp n mẫu: xếp hạng Borda, độ tự tin tự khai (trung bình) và độ đồng thuận (tỷ lệ phiếu top-1)."""
    good = [s for s in samples if s["ok"]]
    if not good:
        return {"ranking": [], "conf_verbal": 0.0, "conf_consensus": 0.0, "abstain_vote": 1.0, "parse_rate": 0.0}
    borda = Counter()
    for s in good:
        for i, svc in enumerate(s["ranking"]):
            borda[svc] += 5 - i
    ranking = [s for s, _ in borda.most_common()]
    top1 = Counter(s["ranking"][0] for s in good)
    return {
        "ranking": ranking,
        "conf_verbal": sum(s["confidence"] for s in good) / len(good),
        "conf_consensus": top1[ranking[0]] / len(samples),
        "abstain_vote": sum(s["insufficient"] for s in good) / len(good),
        "next_check": good[0]["next_check"],
        "parse_rate": len(good) / len(samples),
    }
