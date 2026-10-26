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
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

# Bump on any change to SYSTEM_PROMPT, USER_TEMPLATE or schema(): it is part of every cache and result key.
PROMPT_VERSION = "v1"
MOCK_SEED = "mock-v1"
CANARY_MESSAGES = [{"role": "user", "content": "Reply with the single word: ready"}]
# Never written into a raw-output record (request metadata holds no headers; this is the backstop).
SECRET_KEYS = frozenset({"authorization", "api_key", "apikey", "x-api-key", "bearer", "password", "access_token"})

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
                 server_fp: str | None = None, presence_penalty: float | None = None, keep_raw: bool = True):
        if backend != "mock" and not revision:
            raise ValueError(f"model {model!r}: a live backend needs a pinned `revision` (commit sha of the weights)")
        self.model, self.base_url, self.backend = model, base_url.rstrip("/"), backend
        self.n, self.temperature, self.max_tokens, self.seed = n, temperature, max_tokens, seed
        self.cache, self.timeout = cache or Cache(), timeout
        self.revision, self.logprobs = revision, logprobs
        self.presence_penalty = presence_penalty   # None = not sent (server default)
        self.chat_template_kwargs = {"enable_thinking": False} if chat_template_kwargs is None else dict(chat_template_kwargs)
        self.server_fp = server_fp if server_fp is not None else ("mock" if backend == "mock" else None)
        # raw completions, logprobs and request metadata are kept in the cache value (not the key), so
        # turning this on or off never invalidates cached answers
        self.keep_raw = keep_raw

    def execution(self) -> dict:
        """Every setting that changes this model's outputs for a given prompt (the cache key's fields
        besides the prompt). `server_fp` covers the served model list, launch arguments and canary."""
        if self.server_fp is None:
            raise RuntimeError("server fingerprint not set: call server_fingerprint() first")
        return {"model": self.model, "revision": self.revision, "backend": self.backend, "prompt_version": PROMPT_VERSION,
                "n": self.n, "temperature": self.temperature, "seed": self.seed, "max_tokens": self.max_tokens,
                "chat_template_kwargs": self.chat_template_kwargs, "logprobs": self.logprobs,
                "presence_penalty": self.presence_penalty, "server_fp": self.server_fp}

    def execution_signature(self) -> str:
        return hashlib.sha256(json.dumps(self.execution(), sort_keys=True).encode()).hexdigest()[:16]

    def key(self, messages, candidates, scope: str | None = None) -> str:
        """`scope`: evidence arm other than l0, so arms never share a cache entry even for identical prompts."""
        if self.server_fp is None:
            raise RuntimeError("server fingerprint not set: call server_fingerprint() before asking a live server")
        blob = json.dumps([self.model, self.revision, self.backend, self.n, self.temperature, self.seed, self.max_tokens,
                           PROMPT_VERSION, self.chat_template_kwargs, self.logprobs, self.server_fp, messages, candidates]
                          # appended only when set, so keys of runs without them stay valid
                          + ([{"presence_penalty": self.presence_penalty}] if self.presence_penalty is not None else [])
                          + ([{"arm": scope}] if scope is not None else []),
                          sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()

    def ask(self, messages, candidates, scope: str | None = None) -> dict:
        k = self.key(messages, candidates, scope)
        hit = self.cache.get(k)
        if hit is not None:
            out = {**hit, "cached": True}       # entries written before raw persistence have no "raw"
            if not self.keep_raw:
                out.pop("raw", None)
            return out
        t0 = time.time()
        raw = self._mock(messages, candidates) if self.backend == "mock" else self._vllm(messages, candidates)
        samples = [parse(x, candidates) for x in raw["texts"]]
        out = {"samples": samples, "prompt_tokens": raw.get("prompt_tokens"),
               "completion_tokens": raw.get("completion_tokens"), "latency_s": round(time.time() - t0, 3)}
        if self.keep_raw:
            out["raw"] = self.raw_record(raw, messages, candidates, k)
        self.cache.put(k, out)
        return {**out, "cached": False}

    def request_body(self, messages, candidates) -> dict:
        body = {
            "model": self.model, "messages": messages, "n": self.n, "temperature": self.temperature,
            "max_tokens": self.max_tokens, "seed": self.seed, "chat_template_kwargs": self.chat_template_kwargs,
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "rca", "schema": schema(candidates)}},
        }
        if self.presence_penalty is not None:
            body["presence_penalty"] = self.presence_penalty
        if self.logprobs:
            body.update(logprobs=True, top_logprobs=5)
        return body

    def request_meta(self, messages, candidates, key: str) -> dict:
        """The request as sent, without headers and with the prompt replaced by its sha256 (the prompt
        is rebuilt from the evidence files, which stay in the private results directory)."""
        body = self.request_body(messages, candidates)
        meta = {k: v for k, v in body.items() if k not in ("messages", "response_format")}
        meta.update(endpoint="mock" if self.backend == "mock" else f"{redact_url(self.base_url)}/chat/completions",
                    response_format="json_schema", candidates=list(candidates), backend=self.backend,
                    revision=self.revision, prompt_version=PROMPT_VERSION, server_fp=self.server_fp, cache_key=key,
                    messages_sha256=hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest())
        return meta

    def raw_record(self, raw: dict, messages, candidates, key: str) -> dict:
        rec = {"request": self.request_meta(messages, candidates, key), "response": raw.get("response", {}),
               "texts": list(raw["texts"]), "finish_reasons": raw.get("finish_reasons"),
               "logprobs": raw.get("logprobs")}
        check_no_secrets(rec)
        return rec

    def _vllm(self, messages, candidates) -> dict:
        res = self._post("/chat/completions", self.request_body(messages, candidates))
        u = res.get("usage", {})
        out = {"texts": [c["message"]["content"] for c in res["choices"]],
               "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
               "finish_reasons": [c.get("finish_reason") for c in res["choices"]],
               "response": {"id": res.get("id"), "model": res.get("model"), "created": res.get("created"),
                            "system_fingerprint": res.get("system_fingerprint"), "usage": u}}
        if self.logprobs:
            out["logprobs"] = [compact_logprobs(c.get("logprobs")) for c in res["choices"]]
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
        return {"texts": outs, "prompt_tokens": len(text) // 4, "completion_tokens": 60 * self.n,
                "finish_reasons": ["stop"] * self.n, "response": {"model": self.model}}


def redact_url(url: str) -> str:
    """scheme://host[:port]/path: drops user info, query and fragment, where credentials could sit."""
    p = urllib.parse.urlsplit(url)
    host = p.hostname or ""
    host = f"[{host}]" if ":" in host else host            # IPv6 literal keeps its brackets
    return urllib.parse.urlunsplit((p.scheme, f"{host}:{p.port}" if p.port else host, p.path, "", ""))


def check_no_secrets(obj) -> None:
    if isinstance(obj, dict):
        bad = [k for k in obj if str(k).lower() in SECRET_KEYS]
        if bad:
            raise ValueError(f"raw-output record would contain credential fields {bad}")
        for v in obj.values():
            check_no_secrets(v)
    elif isinstance(obj, list):
        for v in obj:
            check_no_secrets(v)


def compact_logprobs(lp: dict | None) -> list[dict] | None:
    """Per generated token: the token, its logprob and the top alternatives as [token, logprob] pairs
    (vLLM's `bytes` arrays dropped)."""
    if not lp:
        return None
    return [{"token": t.get("token"), "logprob": t.get("logprob"),
             "top": [[x.get("token"), x.get("logprob")] for x in t.get("top_logprobs") or []]}
            for t in lp.get("content") or []]


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
            "insufficient": bool(d.get("insufficient_evidence", False)), "next_check": d.get("next_check", ""),
            "reason": d.get("reason", "")}


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
    conf = [s["confidence"] for s in good]
    mean = sum(conf) / len(conf)
    return {
        "ranking": ranking,
        "conf_verbal": mean,
        "conf_verbal_sd": (sum((c - mean) ** 2 for c in conf) / len(conf)) ** 0.5,  # spread across samples
        "conf_consensus": top1[ranking[0]] / len(samples),
        "abstain_vote": sum(s["insufficient"] for s in good) / len(good),
        "next_check": good[0]["next_check"],
        "parse_rate": len(good) / len(samples),
    }
