"""Jev (TypeSafe "System One") decision layer client: state builder, questions, HTTP client, cache, mock.

The RCA LLM diagnoses; Jev decides afterwards what to do with the answer. Jev's probabilities are an
uncalibrated score: TypeSafe makes no calibration claim, so nothing here treats them as a probability
of RCA correctness.

API (docs.typesafe.ai): POST https://api.typesafe.ai/v1/systemone, `Authorization: Bearer`, body
{model, state, questions}. A `choice` question has a `criteria` map {option: description}; the answer
carries `choice`, `probabilities` (sum to 1) and `confidence`. A `noul` answer carries `noul` in [0, 1].
The key is read from `TYPESAFE_API_KEY` and never logged or stored.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import sqlite3
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .schema import DECISION_STATE_ALLOWED_KEYS, denylisted

# Bump on any change to the question wording, criteria or state encoding: it is part of every cache key.
JEV_QUESTION_VERSION = "q1-draft"
PINNED_MODEL = "jev-1.13.0"
TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
API_KEY_ENV = "TYPESAFE_API_KEY"

ACTIONS = ("accept", "retrieve", "escalate", "abstain")
TERMINAL_ACTIONS = ("accept", "abstain")
STAGES = ("first_look", "after_retrieval", "after_escalation")
MAX_EVIDENCE_CHARS = 6000
RETRY_STATUS = {429, 529, 500, 502, 503, 504}

INSTRUCTIONS = ("An on-call engineer will act on the assistant's root-cause answer for this incident. "
                "Choose the next step that best avoids sending the engineer to the wrong service.")
CRITERIA = {
    "accept": "The evidence clearly points to the assistant's first answer as the root cause.",
    "retrieve": "Look up similar past incidents before deciding.",
    "escalate": "Ask a stronger diagnostic model before deciding.",
    "abstain": "The evidence is not enough; tell the engineer what to check next.",
}
SUPPORTED_INSTRUCTIONS = ("Does the evidence show that the assistant's first answer is the root cause, "
                          "not a service that only shows symptoms of another service's fault?")
SUPPORTED_CRITERIA = {"true": "The evidence supports the first answer as the root cause.",
                      "false": "The evidence does not support it, or points elsewhere."}


class JevRequestError(RuntimeError):
    """400/401/413/415/422: a bug in the request or the credentials, never retried; the run stops."""


class JevVersionError(RuntimeError):
    """The response `model` differs from the pinned version; the run stops."""


# ---------------------------------------------------------------- state
@dataclass
class DecisionInputs:
    """Everything a Jev state may be built from. Filled from the evidence file and named LLM aggregate
    fields only (see `decide.decision_inputs`), never from a scored grid row."""
    evidence: str
    ranking: list[str]
    conf_verbal: float
    conf_consensus: float
    n_samples: int
    abstain_vote: float
    telemetry: dict
    n_candidates: int
    stage: str = "first_look"
    top_sim: float | None = None


def band(x: float) -> str:
    return "high" if x >= 0.8 else "medium" if x >= 0.5 else "low"


def build_state(inp: DecisionInputs, drop: tuple[str, ...] = ()) -> dict:
    """Jev state; numbers are passed as text with a verbal band (Jev 1.13 is weak on numbers).
    `drop` removes keys for ablations (J-noconf, J-noevidence)."""
    if inp.stage not in STAGES:
        raise ValueError(f"unknown stage {inp.stage!r}")
    agree = round(inp.conf_consensus * inp.n_samples)
    state = {
        "evidence": inp.evidence[:MAX_EVIDENCE_CHARS],
        "assistant_first_answer": inp.ranking[0] if inp.ranking else "none (no valid answer)",
        "assistant_ranking": ", ".join(inp.ranking[:3]) if inp.ranking else "none",
        "assistant_confidence": (f"self-reported {round(inp.conf_verbal * 100)}/100 ({band(inp.conf_verbal)}); "
                                 f"{agree} of {inp.n_samples} samples agree ({band(inp.conf_consensus)})"),
        "assistant_flagged_insufficient": "yes" if inp.abstain_vote > 0.5 else "no",
        "telemetry_available": {k: bool(inp.telemetry.get(k)) for k in ("metrics", "logs", "traces")},
        "candidate_count": str(inp.n_candidates),
        "decision_stage": inp.stage,
    }
    if inp.top_sim is not None:
        state["similar_past_incident_similarity"] = f"{inp.top_sim:.2f} ({band(inp.top_sim)})"
    for k in drop:
        state.pop(k, None)
    check_state(state)
    return state


def _nested_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _nested_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _nested_keys(v)


def check_state(state: dict) -> None:
    """Top-level keys must be in the allowlist (exact match; it takes precedence over the denylist,
    which would reject `assistant_first_answer`). Nested keys must not be denylisted."""
    extra = set(state) - DECISION_STATE_ALLOWED_KEYS
    if extra:
        raise ValueError(f"state keys not allowed: {sorted(extra)}")
    bad = [k for v in state.values() for k in _nested_keys(v) if denylisted(k)]
    if bad:
        raise ValueError(f"denylisted nested keys in state: {bad}")


# ---------------------------------------------------------------- questions
def build_questions(actions: tuple[str, ...], stage: str = "first_look") -> dict:
    """`action` (choice over the available actions only) and `supported` (noul). After a retrieve or
    escalate, only accept/abstain remain."""
    acts = TERMINAL_ACTIONS if stage != "first_look" else tuple(a for a in ACTIONS if a in actions)
    if "accept" not in acts or "abstain" not in acts:
        raise ValueError(f"actions must include accept and abstain: {actions}")
    return {"action": {"type": "choice", "instructions": INSTRUCTIONS, "criteria": {a: CRITERIA[a] for a in acts}},
            "supported": {"type": "noul", "instructions": SUPPORTED_INSTRUCTIONS, "criteria": dict(SUPPORTED_CRITERIA)}}


def order_options(questions: dict, seed: str) -> tuple[dict, list[str]]:
    """Shuffle the choice options (Jev favours the first option) with a seed from sha256(seed)."""
    q = json.loads(json.dumps(questions))
    opts = list(q["action"]["criteria"])
    random.Random(int(hashlib.sha256(seed.encode()).hexdigest()[:16], 16)).shuffle(opts)
    q["action"]["criteria"] = {o: questions["action"]["criteria"][o] for o in opts}
    return q, opts


# ---------------------------------------------------------------- result and cache
@dataclass
class JevResult:
    action: str | None
    probabilities: dict = field(default_factory=dict)
    confidence: float | None = None
    supported: float | None = None
    option_order: list = field(default_factory=list)
    model: str | None = None
    status: str = "ok"                   # ok | error | invalid_response
    usage: dict = field(default_factory=dict)
    latency_s: float = 0.0
    cached: bool = False
    request_sha: str = ""
    error: str | None = None

    def summary(self) -> dict:
        return asdict(self)


class JevCache:
    """Validated 200 responses only, keyed by the request sha (which includes the expected model)."""

    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.execute("CREATE TABLE IF NOT EXISTS j (k TEXT PRIMARY KEY, v TEXT)")

    def get(self, k):
        r = self.db.execute("SELECT v FROM j WHERE k=?", (k,)).fetchone()
        return json.loads(r[0]) if r else None

    def put(self, k, v):
        self.db.execute("INSERT OR REPLACE INTO j VALUES (?,?)", (k, json.dumps(v)))
        self.db.commit()


def validate(resp: dict, questions: dict) -> str | None:
    """None when the response answers both questions in the documented shape, else the reason."""
    try:
        a = resp["answers"]["action"]
        opts = set(questions["action"]["criteria"])
        if a["choice"] not in opts:
            return f"choice {a['choice']!r} not an option"
        p = a["probabilities"]
        if set(p) != opts or abs(sum(p.values()) - 1) > 1e-3:
            return "probabilities do not cover the options or do not sum to 1"
        if "supported" in questions:
            nl = resp["answers"]["supported"]["noul"]
            if not 0 <= nl <= 1:
                return "noul outside [0, 1]"
        if not isinstance(resp.get("model"), str):
            return "missing model"
    except (KeyError, TypeError, AttributeError) as e:
        return f"malformed response: {e!r}"
    return None


# ---------------------------------------------------------------- client
class JevClient:
    """One provider: TypeSafe direct (the only documented route that pins a version).

    `expected_model` is the exact response `model` string observed for the pinned version (recorded in
    the decision log); it defaults to `model`. Retries 429/529/5xx and network errors with exponential
    backoff and jitter; 400/401/413/415/422 raise `JevRequestError`; a different response model raises
    `JevVersionError`. Error responses are never cached."""

    def __init__(self, provider="typesafe", model=PINNED_MODEL, backend="live", cache=None, max_retries=6,
                 expected_model: str | None = None, url: str = TYPESAFE_URL, timeout: float = 60,
                 backoff_s: float = 2.0, sleep=time.sleep):
        if provider != "typesafe":
            raise ValueError(f"provider {provider!r} not supported: only TypeSafe can pin {PINNED_MODEL}")
        if backend not in ("live", "mock"):
            raise ValueError(backend)
        self.provider, self.model, self.backend = provider, model, backend
        self.expected_model = expected_model or model
        self.cache = JevCache(cache) if isinstance(cache, (str, Path)) else cache
        self.max_retries, self.url, self.timeout, self.backoff_s, self.sleep = max_retries, url, timeout, backoff_s, sleep
        self.http_calls = 0

    def request_body(self, state: dict, questions: dict) -> dict:
        return {"model": self.model, "state": state, "questions": questions}

    def request_sha(self, body: dict) -> str:
        blob = json.dumps([self.backend, self.expected_model, JEV_QUESTION_VERSION, body], sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()

    def decide(self, state: dict, questions: dict, seed: str) -> tuple[JevResult, dict]:
        """Returns the result and the raw record {request_sha, request, response} for `jev_raw.jsonl`."""
        check_state(state)
        q, order = order_options(questions, seed)
        body = self.request_body(state, q)
        sha = self.request_sha(body)
        hit = self.cache.get(sha) if self.cache else None
        t0 = time.time()
        if hit is not None:
            resp, cached = hit, True
        else:
            resp, cached = (self._mock(state, q) if self.backend == "mock" else self._post(body)), False
        latency = round(time.time() - t0, 3)
        raw = {"request_sha": sha, "request": body, "response": resp}
        if resp is None or "_error" in resp:
            return JevResult(None, option_order=order, status="error", latency_s=latency, request_sha=sha,
                             error=(resp or {}).get("_error")), raw
        if resp.get("model") != self.expected_model:
            raise JevVersionError(f"Jev answered with model {resp.get('model')!r}, pinned {self.expected_model!r}")
        why = validate(resp, q)
        if why:
            return JevResult(None, option_order=order, status="invalid_response", model=resp.get("model"),
                             latency_s=latency, request_sha=sha, error=why), raw
        if self.cache and not cached:
            self.cache.put(sha, resp)
        a = resp["answers"]["action"]
        sup = resp["answers"].get("supported", {}).get("noul")
        return JevResult(a["choice"], dict(a["probabilities"]), a.get("confidence"), sup, order, resp["model"], "ok",
                         resp.get("usage", {}), latency, cached, sha), raw

    def _post(self, body: dict) -> dict:
        key = os.environ.get(API_KEY_ENV)
        if not key:
            raise RuntimeError(f"set {API_KEY_ENV} before calling Jev (or use backend: mock offline)")
        data = json.dumps(body).encode()
        last = "no attempt"
        for attempt in range(self.max_retries):
            req = urllib.request.Request(self.url, data=data, method="POST",
                                         headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
            self.http_calls += 1
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                if e.code not in RETRY_STATUS:
                    raise JevRequestError(f"Jev HTTP {e.code}: {e.read()[:300]!r}") from None
                last = f"HTTP {e.code}"
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last = f"network: {e!r}"
            if attempt < self.max_retries - 1:
                self.sleep(self.backoff_s * 2 ** attempt * (1 + random.random()))
        return {"_error": f"gave up after {self.max_retries} tries ({last})"}

    def _mock(self, state: dict, questions: dict) -> dict:
        """Deterministic offline stand-in from the state hash and visible rules. Offline tests only."""
        h = int(hashlib.sha256(json.dumps([state, questions], sort_keys=True).encode()).hexdigest()[:8], 16)
        opts = list(questions["action"]["criteria"])
        conf = str(state.get("assistant_confidence", ""))
        if state.get("assistant_flagged_insufficient") == "yes" and "abstain" in opts:
            pick = "abstain"
        elif "agree (high)" in conf:
            pick = "accept"
        else:
            pick = next((a for a in ("retrieve", "escalate", "abstain") if a in opts), "abstain")
        rest = (1 - 0.55) / max(len(opts) - 1, 1)
        probs = {o: (0.55 if o == pick else rest) for o in opts}
        n = len(opts)
        out = {"model": self.model, "answers": {"action": {"choice": pick, "probabilities": probs,
                                                           "confidence": (0.55 - 1 / n) / (1 - 1 / n)}},
               "usage": {"input_tokens": len(json.dumps(state)) // 4, "output_tokens": 0}}
        if "supported" in questions:
            out["answers"]["supported"] = {"noul": round(0.3 + 0.4 * (h % 1000) / 1000 + (0.2 if pick == "accept" else 0), 3)}
        return out
