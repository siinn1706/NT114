"""Selective evaluation of one LLM on a finished grid (offline, full feedback, evaluation-only).

Every answer comes from one model's call on one cell. A policy only chooses, per (incident,
condition), between the cached cells of that same model:

  answer   : the primary answer without retrieval
  retrieve : the same model's cached answer with retrieval (`hybrid`, `precedent` store)
  abstain  : no answer ("not enough evidence, check X")

Because the grid holds every arm for every cell, counterfactual evaluation is exact. Policies here
are fixed rules and controls (always answer, coverage-matched threshold and random deferral, oracle);
hypothesis-specific policies are out of scope. The action table holds correctness, so nothing in this
module ever reaches a prompt.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import metrics
from .llm import PROMPT_VERSION

ACTIONS = ("answer", "retrieve", "abstain")
# Arms of the action table: (policy action, retrieval method). Optional except `answer`.
ARMS = {"answer": "none", "retrieve": "hybrid"}
FEATS = ["conf_verbal", "conf_consensus", "abstain_vote", "parse_rate"]


# ---------------------------------------------------------------- action table
def _arm_rows(rows: pd.DataFrame, meth: str) -> pd.DataFrame:
    g = rows[(rows.model_role == "primary") & (rows.retrieval == meth)]
    if meth != "none":
        g = g[g.store_mode == "precedent"]
    return g


def select_rows(rows: pd.DataFrame, prompt_version: str, revision: str | None = None, arms: dict = ARMS,
                model: str | None = None) -> dict:
    """{arm: rows indexed by (incident_uid, condition)} of one primary model (`model`, needed when a sweep
    has several) for one prompt version (and model revision). Fails on oracle-store rows and on duplicate
    keys within an arm."""
    if "oracle_store" in rows and rows["oracle_store"].fillna(False).astype(bool).any():
        raise ValueError("grid contains oracle_store (no_precedent) rows: they mask by the query's true label "
                         "and never enter a selective evaluation; evaluate a grid without them")
    rows = rows[rows.prompt_version == prompt_version]
    if model is not None:
        rows = rows[rows.model == model]
    out = {}
    for arm, meth in arms.items():
        g = _arm_rows(rows, meth)
        if revision is not None:
            g = g[g.model_revision == revision]
        if g.empty:
            if arm == "answer":
                raise ValueError(f"no primary rows for prompt_version={prompt_version!r}")
            continue
        g = g.assign(incident_uid=g["incident_uid"].fillna(g["case_id"]))
        dup = g.duplicated(["incident_uid", "condition"], keep=False)
        if dup.any():
            ex = g[dup][["model", "incident_uid", "condition"]].head(3).to_dict("records")
            raise ValueError(f"duplicate (incident_uid, condition) rows in arm {arm!r}: {ex}")
        out[arm] = g.set_index(["incident_uid", "condition"])
    return out


def action_table(rows: pd.DataFrame, prompt_version: str = PROMPT_VERSION, revision: str | None = None,
                 arms: dict = ARMS, model: str | None = None) -> pd.DataFrame:
    """Evaluation table keyed (incident_uid, condition): per arm `<a>_ok`, `<a>_tok`, `<a>_conf`
    (consensus of the arm that produced the answer), `<a>_verbal`, `<a>_rank`, `<a>_lat`; visible
    features of the primary answer."""
    sel = select_rows(rows, prompt_version, revision, arms, model)
    b = sel["answer"]
    t = pd.DataFrame(index=b.index)
    for c in ("system", "dataset", "split_id", "split_role", "n_candidates", "backend", "set_scored", "label_granularity"):
        if c in b:
            t[c] = b[c]
    for f in FEATS:
        t[f] = b[f].astype(float)
    feats = pd.json_normalize(b["features"].tolist()).set_index(b.index)
    for f in ("has_metrics", "has_logs", "has_traces", "max_metric_z", "n_flagged_services", "z_gap_top2"):
        if f in feats:
            t[f] = feats[f].astype(float)
    tok = lambda df: (df["prompt_tokens"].fillna(0) + df["completion_tokens"].fillna(0)).astype(float)
    lat = lambda df: df["latency_s"].fillna(0).astype(float)
    t["answer_ok"], t["answer_tok"], t["answer_conf"], t["answer_rank"] = (
        b["correct"].astype(bool), tok(b), b["conf_consensus"].astype(float), b["rank"])
    t["answer_verbal"], t["answer_lat"] = b["conf_verbal"].astype(float), lat(b)
    t["parse_failed"] = b["parse_failed"].astype(bool) if "parse_failed" in b else False
    if "retrieve" in sel:
        g = sel["retrieve"].reindex(t.index)
        missing = g["correct"].isna()
        if missing.any():
            raise ValueError(f"arm 'retrieve' lacks {int(missing.sum())} (incident, condition) cells of the primary arm")
        t["retrieve_ok"] = g["correct"].astype(bool)
        t["retrieve_tok"] = t["answer_tok"] + tok(g)
        t["retrieve_conf"] = g["conf_consensus"].astype(float)
        t["retrieve_verbal"] = g["conf_verbal"].astype(float)
        t["retrieve_rank"] = g["rank"]
        t["retrieve_lat"] = t["answer_lat"] + lat(g)
        t["hit_top_sim"] = g["hits"].map(lambda h: h[0]["dense_sim"] if h else 0.0)
    return t.reset_index()


# ---------------------------------------------------------------- evaluation
def reward(ok: bool, action: str, tokens: float, wrong_penalty: float = 2.0, tok_cost: float = 0.01) -> float:
    """Secondary utility: correct +1, wrong answer -wrong_penalty, abstain 0, minus a cost per 1k tokens."""
    if action == "abstain":
        return -tok_cost * tokens / 1000
    return (1.0 if ok else -wrong_penalty) - tok_cost * tokens / 1000


def outcomes(t: pd.DataFrame, chosen: pd.Series) -> dict[str, np.ndarray]:
    """Per row: answered, correct (NaN when abstaining), confidence of the arm that produced the final
    answer, tokens and latency along the chosen path."""
    a = chosen.reindex(t.index).to_numpy()
    bad = set(a) - set(ACTIONS)
    if bad:
        raise ValueError(f"unknown actions {bad}")
    n = len(t)
    ok, conf = np.full(n, np.nan), np.full(n, np.nan)
    tok = t["answer_tok"].to_numpy(float).copy()
    lat = t["answer_lat"].to_numpy(float).copy() if "answer_lat" in t else np.zeros(n)
    for act in ("answer", "retrieve"):
        m = a == act
        if not m.any():
            continue
        if f"{act}_ok" not in t:
            raise ValueError(f"policy chose {act!r} but the table has no {act} arm")
        ok[m] = t[f"{act}_ok"].to_numpy(float)[m]
        conf[m] = t[f"{act}_conf"].to_numpy(float)[m]
        tok[m] = t[f"{act}_tok"].to_numpy(float)[m]
        if f"{act}_lat" in t:
            lat[m] = t[f"{act}_lat"].to_numpy(float)[m]
    return {"action": a, "answered": a != "abstain", "ok": ok, "conf": conf, "tok": tok, "lat": lat}


def evaluate(t: pd.DataFrame, chosen: pd.Series, weights=None, conf_thr: float = 0.8, **rw) -> dict:
    """`chosen`: an action per row of `t`. `weights`: eval-unit weights (1 / records of the injection).
    Confidently-wrong uses the confidence of the arm that produced the final answer."""
    o = outcomes(t, chosen)
    w = np.ones(len(t)) if weights is None else np.asarray(weights, float)
    w = w / w.sum()
    ans, ok = o["answered"], o["ok"]
    wrong = ans & (np.nan_to_num(ok, nan=1.0) == 0)
    cw = wrong & (np.nan_to_num(o["conf"]) >= conf_thr)
    cov = float((w * ans).sum())
    acc = float((w * np.nan_to_num(ok) * ans).sum() / cov) if cov > 0 else float("nan")
    rew = np.array([reward(bool(k) if s else False, act, tk, **rw)
                    for k, s, act, tk in zip(np.nan_to_num(ok), ans, o["action"], o["tok"])])
    return {
        "coverage": cov,
        "acc_answered": acc,
        "selective_risk": 1 - acc if cov > 0 else float("nan"),
        "confident_wrong_per_100": float(100 * (w * cw).sum()),
        "wrong_per_100": float(100 * (w * wrong).sum()),
        "abstain_per_100": float(100 * (w * ~ans).sum()),
        "tokens_per_incident": float((w * o["tok"]).sum()),
        "latency_per_incident": float((w * o["lat"]).sum()),
        "reward": float((w * rew).sum()),
        "actions": pd.Series(o["action"]).value_counts().to_dict(),
    }


# ---------------------------------------------------------------- fixed policies and controls
def fixed(t, action):
    return pd.Series(action, index=t.index)


def _accept_top(score: np.ndarray, k: int, rng) -> np.ndarray:
    """Accept the k highest scores; ties at the boundary broken at random (exact coverage per draw)."""
    order = np.lexsort((rng.random(len(score)), -score))
    acc = np.zeros(len(score), bool)
    acc[order[:k]] = True
    return acc


def coverage_matched_threshold(t: pd.DataFrame, coverage: float, conf: str = "answer_conf",
                               draws: int = 1000, seed: int = 0) -> list[pd.Series]:
    """C1: answer the round(coverage·n) most confident rows (primary answer), abstain on the rest;
    one action vector per seeded tie-breaking draw."""
    rng = np.random.default_rng(seed)
    k = int(round(coverage * len(t)))
    sc = t[conf].to_numpy(float)
    return [pd.Series(np.where(_accept_top(sc, k, rng), "answer", "abstain"), index=t.index) for _ in range(draws)]


def coverage_matched_random(t: pd.DataFrame, coverage: float, draws: int = 1000, seed: int = 0) -> list[pd.Series]:
    """C2: answer a uniformly random round(coverage·n) rows, abstain on the rest."""
    rng = np.random.default_rng(seed)
    k = int(round(coverage * len(t)))
    out = []
    for _ in range(draws):
        acc = np.zeros(len(t), bool)
        acc[rng.choice(len(t), k, replace=False)] = True
        out.append(pd.Series(np.where(acc, "answer", "abstain"), index=t.index))
    return out


def evaluate_draws(t: pd.DataFrame, draws: list[pd.Series], weights=None, **rw) -> dict:
    """Mean of every numeric metric over the draws of a randomised control."""
    res = [evaluate(t, c, weights, **rw) for c in draws]
    keys = [k for k, v in res[0].items() if isinstance(v, float)]
    return {**{k: float(np.nanmean([r[k] for r in res])) for k in keys}, "draws": len(draws)}


def oracle_policy(t: pd.DataFrame) -> pd.Series:
    """O (analysis only, reads labels): the first correct arm in cost order, else abstain."""
    out = pd.Series("abstain", index=t.index, dtype=object)
    for a in ("retrieve", "answer"):
        if f"{a}_ok" in t:
            out[t[f"{a}_ok"].astype(bool)] = a
    return out


def random_arm(t: pd.DataFrame, share: float, arm: str = "retrieve", draws: int = 1000, seed: int = 0) -> list[pd.Series]:
    """Random control for arm selection: a uniformly random round(share·n) rows take `arm`, the rest `answer`."""
    rng = np.random.default_rng(seed)
    k = int(round(share * len(t)))
    out = []
    for _ in range(draws):
        pick = np.zeros(len(t), bool)
        pick[rng.choice(len(t), k, replace=False)] = True
        out.append(pd.Series(np.where(pick, arm, "answer"), index=t.index))
    return out


# ---------------------------------------------------------------- risk-coverage and DEV-fit thresholds
COVERAGES = (0.5, 0.7, 0.9)


def coverage_at_risk(correct, score, goal: float, weights=None) -> float:
    """Largest coverage (ties answered together) whose selective risk is <= goal; 0 if none."""
    cov, risk = metrics.risk_coverage_w(correct, score, weights)
    ok = risk <= goal + 1e-12
    return float(cov[ok].max()) if ok.any() else 0.0


def risk_coverage_summary(correct, score, weights=None) -> dict:
    """AURC and selective risk at the standard coverages for one score (higher = more confident);
    rows with a NaN score are left out and counted by `n_scored`."""
    c, s = np.asarray(correct, bool), np.asarray(score, float)
    m = ~np.isnan(s)
    c, s = c[m], s[m]
    w = None if weights is None else np.asarray(weights, float)[m]
    if not len(c):
        return {"n_scored": 0, "AURC": np.nan, **{f"risk@{x}": np.nan for x in COVERAGES}}
    return {"n_scored": int(len(c)), "AURC": metrics.aurc_w(c, s, w),
            **{f"risk@{x}": metrics.selective_risk_at(c, s, x, w) for x in COVERAGES}}


def fit_threshold(correct, score, weights=None, coverage: float | None = None, risk: float | None = None) -> float:
    """Threshold tau (answer when score >= tau) fitted on DEV rows, for a coverage goal (the smallest
    tie group reaching it) or a risk goal (the largest coverage meeting it; +inf = abstain on all)."""
    if (coverage is None) == (risk is None):
        raise ValueError("give exactly one of coverage, risk")
    s = np.asarray(score, float)
    levels = np.unique(s[~np.isnan(s)])[::-1]
    cov, rk = metrics.risk_coverage_w(correct, s, weights)
    if coverage is not None:
        i = int(np.searchsorted(cov, coverage - 1e-12))
        return float(levels[min(i, len(levels) - 1)])
    ok = np.flatnonzero(rk <= risk + 1e-12)
    return float(levels[ok.max()]) if len(ok) else float("inf")


def apply_threshold(correct, score, tau: float, clusters, weights=None, n_boot: int = 2000, seed: int = 0) -> dict:
    """Realised coverage and risk of `score >= tau`, with cluster-bootstrap CIs over injections."""
    c = np.asarray(correct, float)
    ans = (np.nan_to_num(np.asarray(score, float), nan=-np.inf) >= tau).astype(float)
    w = np.ones(len(c)) if weights is None else np.asarray(weights, float)
    cov = metrics.cluster_bootstrap_means(ans, clusters, w, n=n_boot, seed=seed)
    out = {"coverage": float(cov["est"]), "coverage_lo": float(cov["lo"]), "coverage_hi": float(cov["hi"])}
    wa = w * ans
    if wa.sum() > 0:
        # risk = error among answered rows; a draw without answered rows gives NaN and is ignored
        r = metrics.cluster_bootstrap_means(1 - c, clusters, wa, n=n_boot, seed=seed)
        out.update(risk=float(r["est"]), risk_lo=float(r["lo"]), risk_hi=float(r["hi"]))
    else:
        out.update(risk=np.nan, risk_lo=np.nan, risk_hi=np.nan)
    return out


def references(correct, abstain_vote, weights=None) -> list[dict]:
    """L1 (the LLM's own flag), C2 (random deferral: risk = base error at any coverage, analytic) and O."""
    c = np.asarray(correct, bool)
    w = np.ones(len(c)) if weights is None else np.asarray(weights, float)
    w = w / w.sum()
    ans = np.asarray(abstain_vote, float) < 0.5
    l1_cov = float((w * ans).sum())
    return [
        {"policy": "L1 self-abstain", "coverage": l1_cov,
         "risk": float((w * ans * ~c).sum() / l1_cov) if l1_cov > 0 else np.nan},
        {"policy": "C2 random deferral", "coverage": np.nan, "risk": float((w * ~c).sum())},
        {"policy": "O oracle", "coverage": float((w * c).sum()), "risk": 0.0},
    ]


def shift_table(df: pd.DataFrame, score_col: str = "conf_consensus") -> pd.DataFrame:
    """DEV (split_role val) vs test by system x fault: records, base error and the share of each
    confidence level. Reported next to every DEV-fit result."""
    rows = []
    d = df[df["split_role"].isin(["val", "test"])]
    for (sys_, fault, role), g in d.groupby(["system", "fault", "split_role"], dropna=False):
        rec = {"system": sys_, "fault": fault, "split_role": role, "n_records": len(g),
               "base_error": float(1 - g["correct"].astype(float).mean())}
        for lvl, share in g[score_col].round(2).value_counts(normalize=True).sort_index().items():
            rec[f"share_{score_col}={lvl:.2f}"] = float(share)
        rows.append(rec)
    out = pd.DataFrame(rows)
    if len(out):
        out.insert(3, "present_in", out.groupby(["system", "fault"])["split_role"].transform(lambda s: "+".join(sorted(set(s)))))
    return out
