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
L0 = "l0"


def arm_column(df: pd.DataFrame) -> pd.Series:
    """Evidence arm of each row (amendment a02). Rows written before the `arm` field are arm `l0`, the
    existing builder: with `retrieval = none` the existing H1 arm, with `hybrid` the existing retrieval arm
    (the retrieval column keeps them apart). Rows of different arms are never pooled or fitted together."""
    return df["arm"].fillna(L0) if "arm" in df else pd.Series(L0, index=df.index)


# ---------------------------------------------------------------- action table
def _arm_rows(rows: pd.DataFrame, meth: str) -> pd.DataFrame:
    g = rows[(rows.model_role == "primary") & (rows.retrieval == meth)]
    if meth != "none":
        g = g[g.store_mode == "precedent"]
    return g


def select_rows(rows: pd.DataFrame, prompt_version: str, revision: str | None = None, arms: dict = ARMS,
                model: str | None = None, evidence_arm: str = L0) -> dict:
    """{arm: rows indexed by (incident_uid, condition)} of one primary model (`model`, needed when a sweep
    has several) for one prompt version (and model revision) and one evidence arm (`evidence_arm`, default
    `l0`; never mixed). Fails on oracle-store rows and on duplicate keys within an arm."""
    if "oracle_store" in rows and rows["oracle_store"].fillna(False).astype(bool).any():
        raise ValueError("grid contains oracle_store (no_precedent) rows: they mask by the query's true label "
                         "and never enter a selective evaluation; evaluate a grid without them")
    rows = rows[(rows.prompt_version == prompt_version) & (arm_column(rows) == evidence_arm)]
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
                 arms: dict = ARMS, model: str | None = None, evidence_arm: str = L0) -> pd.DataFrame:
    """Evaluation table keyed (incident_uid, condition): per arm `<a>_ok`, `<a>_tok`, `<a>_conf`
    (consensus of the arm that produced the answer), `<a>_verbal`, `<a>_rank`, `<a>_lat`; visible
    features of the primary answer."""
    sel = select_rows(rows, prompt_version, revision, arms, model, evidence_arm)
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


def _ci(name: str, draws: np.ndarray, alpha: float = 0.05) -> dict:
    """{name: est, name_lo, name_hi} from (point, draws...) values; draws where the statistic is undefined
    (NaN) are ignored, and their share is reported as `name_nan_draws` when > 0."""
    ok = np.isfinite(draws[1:])
    lo, hi = np.nanquantile(draws[1:], [alpha / 2, 1 - alpha / 2]) if ok.any() else (np.nan, np.nan)
    out = {name: float(draws[0]), f"{name}_lo": float(lo), f"{name}_hi": float(hi)}
    if len(ok) and not ok.all():
        out[f"{name}_nan_draws"] = float(1 - ok.mean())
    return out


def _endpoint(name: str, draws: np.ndarray) -> dict:
    r = _ci(name, draws)
    return {"est": r[name], "lo": r[f"{name}_lo"], "hi": r[f"{name}_hi"],
            **({"nan_draws": r[f"{name}_nan_draws"]} if f"{name}_nan_draws" in r else {})}


def references(correct, abstain_vote, weights=None, clusters=None, n_boot: int = 2000, seed: int = 0) -> list[dict]:
    """L1 (the LLM's own flag), C2 (random deferral: risk = base error at any coverage, analytic) and O.
    With `clusters`, every value carries a cluster-bootstrap CI over injections."""
    c = np.asarray(correct, bool)
    w = np.ones(len(c)) if weights is None else np.asarray(weights, float)
    w = w / w.sum()
    ans = np.asarray(abstain_vote, float) < 0.5
    l1_cov = float((w * ans).sum())
    out = [
        {"policy": "L1 self-abstain", "coverage": l1_cov,
         "risk": float((w * ans * ~c).sum() / l1_cov) if l1_cov > 0 else np.nan},
        {"policy": "C2 random deferral", "coverage": np.nan, "risk": float((w * ~c).sum())},
        {"policy": "O oracle", "coverage": float((w * c).sum()), "risk": 0.0},
    ]
    if clusters is None:
        return out
    boot = lambda v, ww: metrics.cluster_bootstrap_means(v, clusters, ww, n=n_boot, seed=seed)
    cis = {("L1 self-abstain", "coverage"): boot(ans.astype(float), w),
           ("C2 random deferral", "risk"): boot((~c).astype(float), w),
           ("O oracle", "coverage"): boot(c.astype(float), w)}
    if l1_cov > 0:
        cis[("L1 self-abstain", "risk")] = boot((~c).astype(float), w * ans)
    for r in out:
        for (policy, k), b in cis.items():
            if r["policy"] == policy:
                r[f"{k}_lo"], r[f"{k}_hi"] = float(b["lo"]), float(b["hi"])
    return out


# ---------------------------------------------------------------- vectorised endpoints over tie levels
# Every endpoint of a score depends on the records only through the weight and correct weight per
# (injection, distinct score level). A cluster-bootstrap draw is then a count vector over injections, so
# all draws are one matrix product. Row 0 of every (draws x levels) matrix is the point estimate.

def level_mats(correct, score, clusters, weights=None):
    """Levels (descending) and per-cluster weight / correct-weight per level: (levels, Mw, Mc, inv)."""
    c, s = np.asarray(correct, float), np.asarray(score, float)
    w = np.ones(len(c)) if weights is None else np.asarray(weights, float)
    levels = np.unique(s)[::-1]
    li = np.searchsorted(-levels, -s)
    _, inv = np.unique(np.asarray(clusters), return_inverse=True)
    k = inv.max() + 1
    Mw, Mc = np.zeros((k, len(levels))), np.zeros((k, len(levels)))
    np.add.at(Mw, (inv, li), w)
    np.add.at(Mc, (inv, li), w * c)
    return levels, Mw, Mc, inv


def boot_counts(inv, n_boot: int, seed: int) -> np.ndarray:
    """(1 + n_boot) x clusters: a row of ones (the point estimate), then `metrics.cluster_draws`."""
    counts, _ = metrics.cluster_draws(inv, n_boot, seed)
    return np.vstack([np.ones((1, counts.shape[1])), counts])


def boot_mats(Mw, Mc, inv, n_boot, seed):
    """Point (row 0) and cluster-bootstrap level matrices; draws as `metrics.cluster_draws`."""
    C = boot_counts(inv, n_boot, seed)
    return C @ Mw, C @ Mc


def _base(Wl, Cl):
    return 1 - Cl.sum(1) / Wl.sum(1)


def gain_exact(Wl, Cl, coverage):
    """Base error - risk at exactly `coverage` of the weight: the boundary tie group is answered
    fractionally, which is the expectation of the seeded random tie-break of C1."""
    T = Wl.sum(1)
    cw, cc = Wl.cumsum(1), Cl.cumsum(1)
    target = coverage * T
    idx = np.argmax(cw >= target[:, None] - 1e-12, axis=1)
    r = np.arange(len(T))
    prev_w, prev_c = cw[r, idx] - Wl[r, idx], cc[r, idx] - Cl[r, idx]
    with np.errstate(invalid="ignore", divide="ignore"):
        frac = np.where(Wl[r, idx] > 0, (target - prev_w) / Wl[r, idx], 0.0)
        risk = 1 - (prev_c + frac * Cl[r, idx]) / target
    return _base(Wl, Cl) - risk


def gain_tiegroup(Wl, Cl, coverage):
    """Whole tie groups (`metrics.selective_risk_at`): returns (gain, achieved coverage >= coverage)."""
    T = Wl.sum(1)
    cw, cc = Wl.cumsum(1), Cl.cumsum(1)
    cov = cw / T[:, None]
    idx = np.argmax(cov >= coverage - 1e-12, axis=1)
    r = np.arange(len(T))
    return _base(Wl, Cl) - (1 - cc[r, idx] / cw[r, idx]), cov[r, idx]


def gain_threshold(Wl, Cl, levels, tau):
    """Base error - risk of answering levels >= tau: returns (gain, achieved coverage)."""
    ans = levels >= tau
    aw, ac = Wl[:, ans].sum(1), Cl[:, ans].sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return _base(Wl, Cl) - (1 - ac / aw), aw / Wl.sum(1)


def gain_aurc(Wl, Cl):
    """Base error - AURC (ties answered together), as `metrics.aurc_w`."""
    cw, cc = Wl.cumsum(1), Cl.cumsum(1)
    cov = cw / Wl.sum(1)[:, None]
    with np.errstate(invalid="ignore", divide="ignore"):
        risk = np.where(cw > 0, 1 - cc / cw, 0.0)
    d = np.diff(np.concatenate([np.zeros((len(cov), 1)), cov], 1), axis=1)
    return _base(Wl, Cl) - (d * risk).sum(1)


def exact_coverage_risk(correct, score, coverage: float, weights=None) -> float:
    """Selective risk when answering exactly `coverage` of the weight, highest score first; the boundary
    tie group is answered fractionally (expected risk of C1's random tie-break)."""
    c = np.asarray(correct, bool)
    _, Mw, Mc, _ = level_mats(c, score, np.arange(len(c)), weights)
    Wl, Cl = Mw.sum(0, keepdims=True), Mc.sum(0, keepdims=True)
    return float((_base(Wl, Cl) - gain_exact(Wl, Cl, coverage))[0])


def selective_endpoints(correct, score, clusters, weights=None, coverages=COVERAGES, risk_goals=(),
                        n_boot: int = 2000, seed: int = 0) -> dict:
    """Fixed-coverage endpoints of one score with cluster-bootstrap CIs, rows with a NaN score left out:

    - `risk@c` / `coverage_ties@c`: tie groups answered together (achieved coverage >= c, reported);
    - `risk_exact@c` / `gain_exact@c`: exactly c of the weight, boundary tie group fractional;
      gain = base error - risk, the contrast with C2 random deferral (risk = base error at any coverage);
    - `AURC`, `gain_AURC`, `base_error`, and `coverage_at_risk<g>` per risk goal.
    Returns {name: {"est", "lo", "hi"[, "nan_draws"]}}."""
    c, s = np.asarray(correct, bool), np.asarray(score, float)
    m = ~np.isnan(s)
    names = (["base_error", "AURC", "gain_AURC"]
             + [f"{p}@{x}" for x in coverages for p in ("risk", "coverage_ties", "risk_exact", "gain_exact")]
             + [f"coverage_at_risk{g}" for g in risk_goals])
    if not m.any():
        return {n: {"est": np.nan, "lo": np.nan, "hi": np.nan} for n in names}
    w = np.ones(len(c)) if weights is None else np.asarray(weights, float)
    _, Mw, Mc, inv = level_mats(c[m], s[m], np.asarray(clusters)[m], w[m])
    Wl, Cl = boot_mats(Mw, Mc, inv, n_boot, seed)
    base = _base(Wl, Cl)
    vals = {"base_error": base, "gain_AURC": gain_aurc(Wl, Cl)}
    vals["AURC"] = base - vals["gain_AURC"]
    for x in coverages:
        g, cov = gain_tiegroup(Wl, Cl, x)
        vals[f"risk@{x}"], vals[f"coverage_ties@{x}"] = base - g, cov
        vals[f"gain_exact@{x}"] = gain_exact(Wl, Cl, x)
        vals[f"risk_exact@{x}"] = base - vals[f"gain_exact@{x}"]
    cw, cc = Wl.cumsum(1), Cl.cumsum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        risk = np.where(cw > 0, 1 - cc / cw, np.nan)
    cov = cw / Wl.sum(1)[:, None]
    for gl in risk_goals:
        vals[f"coverage_at_risk{gl}"] = np.where(risk <= gl + 1e-12, cov, 0.0).max(1)
    return {n: _endpoint(n, vals[n]) for n in names}


def confidence_endpoints(correct, score, clusters, weights=None, probability: bool = False,
                         support: str = "continuous", n_boot: int = 2000, seed: int = 0) -> dict:
    """Error-detection AUPRC (positive = wrong) and AURC of one score, plus Brier, ECE (`support`:
    one bin per level for discrete scores, 10 equal-width bins otherwise) and overconfidence gap for
    probability scores; each with a cluster-bootstrap CI over injections (`metrics` definitions)."""
    c, p = np.asarray(correct, bool), np.asarray(score, float)
    w = np.ones(len(c)) if weights is None else np.asarray(weights, float)
    _, Mw, Mc, inv = level_mats(c, p, clusters, w)
    C = boot_counts(inv, n_boot, seed)
    Wl, Cl = C @ Mw, C @ Mc
    vals = {"AURC": _base(Wl, Cl) - gain_aurc(Wl, Cl)}
    # AUPRC: thresholds at distinct scores of -p, i.e. levels by ascending confidence
    P, N = (Wl - Cl)[:, ::-1], Cl[:, ::-1]
    tp, fp = P.cumsum(1), N.cumsum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        recall = tp / tp[:, -1:]
        prec = np.where(tp + fp > 0, tp / (tp + fp), 0.0)
        vals["AUPRC"] = np.where(tp[:, -1] > 0, (np.diff(recall, prepend=0.0, axis=1) * prec).sum(1), np.nan)
    if probability:
        k = inv.max() + 1
        pc = np.clip(p, 0, 1)
        S = np.zeros((k, 3))
        np.add.at(S, inv, np.column_stack([w, w * (pc - c) ** 2, w * (p - c)]))
        T = C @ S
        vals["Brier"], vals["gap"] = T[:, 1] / T[:, 0], T[:, 2] / T[:, 0]
        bins = (np.unique(np.round(pc, 9), return_inverse=True)[1] if support == "discrete"
                else np.minimum((pc * 10).astype(int), 9))
        B = np.zeros((k, bins.max() + 1, 2))
        np.add.at(B, (inv, bins), np.column_stack([w * c, w * pc]))
        Bd = np.einsum("dk,kbj->dbj", C, B)
        vals["ECE"] = np.abs(Bd[..., 0] - Bd[..., 1]).sum(1) / T[:, 0]
    return {n: _endpoint(n, v) for n, v in vals.items()}


def shift_table(df: pd.DataFrame, score_col: str = "conf_consensus", strata=()) -> pd.DataFrame:
    """DEV (split_role val) vs test per stratum (`strata`, e.g. dataset x model x condition x arm) x
    system x fault: records, injections, injection-weighted base error and share of each confidence
    level. Reported next to every DEV-fit result."""
    rows = []
    d = df[df["split_role"].isin(["val", "test"])]
    d = d.assign(_w=d["weight"].astype(float) if "weight" in d else 1.0)
    keys = [*strata, "system", "fault", "split_role"]
    for k, g in d.groupby(keys, dropna=False):
        rec = dict(zip(keys, k))
        rec.update(n_records=len(g), n_injections=int(g["injection_id"].nunique()) if "injection_id" in g else len(g),
                   base_error=float(1 - np.average(g["correct"].astype(float), weights=g["_w"])))
        lv = g[score_col].astype(float).round(2)
        for lvl, share in (g["_w"].groupby(lv).sum() / g["_w"].sum()).sort_index().items():
            rec[f"share_{score_col}={lvl:.2f}"] = float(share)
        rows.append(rec)
    out = pd.DataFrame(rows)
    if len(out):
        grp = [*strata, "system", "fault"]
        out.insert(len(keys), "present_in",
                   out.groupby(grp, dropna=False)["split_role"].transform(lambda s: "+".join(sorted(set(s)))))
    return out
