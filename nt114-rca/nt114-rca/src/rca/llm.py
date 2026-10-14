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
                 n=5, temperature=0.7, max_tokens=400, seed=0, cache: Cache | None = None, timeout=300):
        self.model, self.base_url, self.backend = model, base_url.rstrip("/"), backend
        self.n, self.temperature, self.max_tokens, self.seed = n, temperature, max_tokens, seed
        self.cache, self.timeout = cache or Cache(), timeout

    def key(self, messages, candidates) -> str:
        blob = json.dumps([self.model, self.backend, self.n, self.temperature, self.seed, messages, candidates])
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
            "max_tokens": self.max_tokens, "seed": self.seed,
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "rca", "schema": schema(candidates)}},
        }
        req = urllib.request.Request(f"{self.base_url}/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    res = json.loads(r.read())
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(5 * (attempt + 1))
        u = res.get("usage", {})
        return {"texts": [c["message"]["content"] for c in res["choices"]],
                "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens")}

    def _mock(self, messages, candidates) -> dict:
        """LLM giả: tin dịch vụ có z-score cao nhất ở phần Metrics, nhiễu ngẫu nhiên. Chỉ để test."""
        text = messages[-1]["content"]
        rng = random.Random(self.key(messages, candidates))
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
