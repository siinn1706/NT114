"""Confidence registry (evaluation-only): every score comes from the same model's call on the same cell.

Each score declares its orientation (higher = more confident), its support (`discrete` or
`continuous`), whether it needs `llm_raw.jsonl`, whether it is a probability (so Brier, ECE and the
overconfidence gap apply) and whether it has been validated on real-model output. Unvalidated scores
(`token_prob`) are exploratory: `analyze` never writes them to a headline table.

`scores(grid, raw)` returns one column `score_<name>` per registry entry, aligned with the grid rows.
Raw-only scores are NaN for a grid row without a raw record; `missing_raw` counts those rows, so
nothing is dropped silently.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .metrics import RANK_CAP


@dataclass(frozen=True)
class Score:
    name: str
    source: str                 # grid column or `raw`
    support: str                # "discrete" or "continuous"
    needs_raw: bool
    probability: bool           # a calibrated-probability reading is meaningful (Brier, ECE, gap)
    validated: bool
    note: str = ""


REGISTRY = {s.name: s for s in (
    Score("consensus", "conf_consensus", "discrete", False, True, True, "share of samples whose top-1 is the Borda top-1"),
    Score("verbal", "conf_verbal", "continuous", False, True, True, "mean self-reported confidence"),
    Score("verbal_agreement", "conf_verbal_sd", "continuous", False, False, True, "minus the SD of verbal confidence across samples"),
    Score("not_insufficient", "abstain_vote", "discrete", False, False, True, "1 - share of samples flagging insufficient evidence"),
    Score("borda_margin", "raw", "discrete", True, False, True, "normalised gap between the top-two Borda totals"),
    Score("vote_entropy", "raw", "continuous", True, False, True, "1 - normalised entropy of the top-1 votes"),
    Score("token_prob", "raw", "continuous", True, False, False,
          "mean token log-probability of ranking[0], averaged over samples; requires real-model validation"),
)}


def load_raw(path) -> dict[str, dict]:
    """{key: raw-output record}; the last record of a key wins, a torn line is skipped."""
    out = {}
    p = Path(path)
    if not p.is_file():
        return out
    with open(p, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
                out[r["key"]] = r
            except (ValueError, KeyError, TypeError):
                continue
    return out


# ---------------------------------------------------------------- raw-sample scores
def borda_margin(samples: list[dict]) -> float:
    """(top Borda total - second total) / (cap x n samples), with the aggregate's points (cap - position)."""
    if not samples:
        return float("nan")
    b = Counter()
    for s in samples:
        if s.get("ok"):
            for i, svc in enumerate(s["ranking"][:RANK_CAP]):
                b[svc] += RANK_CAP - i
    if not b:
        return 0.0
    top = [v for _, v in b.most_common(2)] + [0]
    return (top[0] - top[1]) / (RANK_CAP * len(samples))


def vote_entropy(samples: list[dict]) -> float:
    """1 - H(top-1 votes) / log(n parsed samples); 1 when every parsed sample agrees, 0 when none parse."""
    good = [s["ranking"][0] for s in samples if s.get("ok") and s.get("ranking")]
    if not good:
        return 0.0
    if len(good) == 1:
        return 1.0
    p = np.array(list(Counter(good).values()), float) / len(good)
    return float(1 - (-(p * np.log(p)).sum()) / math.log(len(good)))


_FIRST = re.compile(r'"ranking"\s*:\s*\[\s*"((?:[^"\\]|\\.)*)"')


def first_entry_logprob(text: str, logprobs: list[dict] | None) -> float:
    """Mean log-probability of the tokens that spell the first `ranking` entry of one completion.
    The tokens are aligned to the text by their concatenation; NaN when the concatenation differs from
    the text (alignment unknown), when the entry is absent or when there are no logprobs."""
    if not logprobs or not text:
        return float("nan")
    toks = [t.get("token") or "" for t in logprobs]
    if "".join(toks) != text:
        return float("nan")
    m = _FIRST.search(text)
    if not m or not m.group(1):
        return float("nan")
    a, b = m.span(1)
    vals, pos = [], 0
    for t, lp in zip(toks, logprobs):
        end = pos + len(t)
        if end > a and pos < b and lp.get("logprob") is not None:
            vals.append(float(lp["logprob"]))
        pos = end
    return float(np.mean(vals)) if vals else float("nan")


def token_prob(raw: dict) -> float:
    lps = raw.get("logprobs")
    if not lps:
        return float("nan")
    vals = [first_entry_logprob(t, lp) for t, lp in zip(raw.get("texts") or [], lps)]
    vals = [v for v in vals if not math.isnan(v)]
    return float(np.mean(vals)) if vals else float("nan")


# ---------------------------------------------------------------- registry
def scores(grid: pd.DataFrame, raw: dict[str, dict] | None = None) -> tuple[pd.DataFrame, dict]:
    """(`score_<name>` columns aligned with `grid`, counts). Higher always means more confident."""
    raw = raw or {}
    out = pd.DataFrame(index=grid.index)
    out["score_consensus"] = grid["conf_consensus"].astype(float)
    out["score_verbal"] = grid["conf_verbal"].astype(float)
    out["score_verbal_agreement"] = -grid["conf_verbal_sd"].astype(float) if "conf_verbal_sd" in grid else np.nan
    out["score_not_insufficient"] = 1 - grid["abstain_vote"].astype(float)
    recs = grid["key"].map(raw.get) if "key" in grid else pd.Series([None] * len(grid), index=grid.index)
    has = recs.notna()
    out["score_borda_margin"] = [borda_margin(r["samples"]) if r is not None else np.nan for r in recs]
    out["score_vote_entropy"] = [vote_entropy(r["samples"]) if r is not None else np.nan for r in recs]
    out["score_token_prob"] = [token_prob(r) if r is not None else np.nan for r in recs]
    counts = {"rows": int(len(grid)), "missing_raw": int((~has).sum()),
              "token_prob_available": int(out["score_token_prob"].notna().sum())}
    return out, counts
