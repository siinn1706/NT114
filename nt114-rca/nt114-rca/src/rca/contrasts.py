"""Paired contrasts declared in config (evaluation-only), with the injection as the independent unit.

A contrast compares arms on the **intersection** of incidents where every arm exists:

  {name: drop_blind_root, a: {condition: full}, b: {condition: blind_root}, metric: ac1}
  {name: did, kind: did, a: {condition: full}, b: {condition: blind_root},
   c: {condition: full}, d: {condition: blind_nonroot_ev}, metric: ac1}
  {name: auroc_cons_vs_verbal, a: {score: consensus}, b: {score: verbal}, metric: auroc,
   within: {condition: full}}

An arm selector filters records by column values (`condition`, `retrieval`, `model`, ...); `score`
picks the registry score the metric reads (default `consensus`). `within` applies to every arm.
Options: `require_changed: true` (drop incidents whose manipulated variant equals `full`; both the
unfiltered and the filtered result are written) and `filter: {column: value}` (any stratum, e.g.
`named`).

Decomposable metrics (ac1..ac5, mrr5, brier, gap) are differenced per incident, averaged per
injection, and tested with the paired sign-flip test; the CI is a cluster bootstrap over
injections. Non-decomposable metrics (auroc, aurc, risk@<coverage>) use the paired cluster
bootstrap, resampling the same injections for all arms. Holm is applied within declared families
only; without a family every p-value is unadjusted and labelled exploratory.

Sensitivity (D10): with a `group_col` (the split's `group_id`), a second CI (`lo_group`, `hi_group`)
resamples whole groups, keeping repeats of one fault cell together; both arms of a paired contrast use
the same drawn groups. The primary analysis (injection clusters) is unchanged.

Reading a CI (`ci_reading`, never "rejected"): inside +-SESOI -> `excludes_practical_effect`; wholly on
the harmful side of 0 -> `evidence_of_harm`; wholly on the beneficial side -> `evidence_of_benefit`;
otherwise `insufficient_evidence`. The direction of a metric decides which side is harmful (`gap`
has none: `nonzero`). Contrasts that select an exploratory arm (IM1 frames, D13) never enter a family.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import metrics

DECOMPOSABLE = {"ac1", "ac2", "ac3", "ac4", "ac5", "mrr5", "brier", "gap"}
# IM1 arms are exploratory in the first MVP (D13): their contrasts are never part of a family
EXPLORATORY_ARMS = frozenset({"ra_im1", "ra_im1_shuf"})


def direction(metric: str) -> int:
    """+1 when a larger value is better, -1 when smaller is better, 0 when neither (gap)."""
    if metric.startswith("ac") or metric in ("mrr5", "auroc"):
        return 1
    if metric in ("brier", "aurc") or metric.startswith("risk@"):
        return -1
    return 0


def ci_reading(lo: float, hi: float, metric: str, sesoi: float | None = None) -> str | None:
    """Reading of the CI of `a - b` (a DiD reads the same way)."""
    if lo is None or hi is None or np.isnan(lo) or np.isnan(hi):
        return None
    if sesoi is not None and -sesoi < lo and hi < sesoi:
        return "excludes_practical_effect"
    if lo <= 0 <= hi:
        return "insufficient_evidence"
    d = direction(metric)
    if d == 0:
        return "nonzero"
    return "evidence_of_benefit" if (lo > 0) == (d > 0) else "evidence_of_harm"


def _selects_exploratory(spec: dict) -> bool:
    sels = [spec.get(k) or {} for k in ("a", "b", "c", "d", "within")]
    return any(v in EXPLORATORY_ARMS for s in sels for v in ([s.get("arm")] if not isinstance(s.get("arm"), list)
                                                              else s.get("arm")))
ASSUMPTIONS = {
    "sign_flip": ("paired sign-flip on per-injection differences: injections independent; under H0 each "
                  "difference symmetric about 0 (tests a zero mean only under that symmetry)"),
    "cluster_bootstrap": ("percentile paired cluster bootstrap: injections i.i.d.; enough clusters "
                          "(n_injections reported); smooth statistic; p = two-sided share of draws across 0"),
    "intersection": ("estimand on the applicable intersection only: arm availability depends on labels, "
                     "so it is not missing at random; no extrapolation to all incidents"),
    "censored_ranks": "ranks beyond 5 are censored: only AC@1-5 and MRR@5 are computed",
    "sampling": "n samples at fixed temperature from one fixed model; sampling variance folded into each incident",
}


def record_values(df: pd.DataFrame, metric: str, score: str) -> np.ndarray:
    """Per-record value of a decomposable metric (rank metrics ignore `score`)."""
    r = df["rank"].astype(float).to_numpy()
    if metric.startswith("ac"):
        return (r <= int(metric[2:])).astype(float)
    if metric == "mrr5":
        return np.where(r <= metrics.RANK_CAP, 1.0 / r, 0.0)
    c = df["correct"].astype(float).to_numpy()
    p = df[f"score_{score}"].astype(float).to_numpy()
    if metric == "brier":
        return (np.clip(p, 0, 1) - c) ** 2
    if metric == "gap":
        return p - c
    raise ValueError(f"metric {metric!r} is not decomposable")


def set_metric(correct, score, weights, metric: str) -> float:
    """Non-decomposable metric of one arm. Error detection: positives = wrong, lower score flags them."""
    c, s, w = np.asarray(correct, bool), np.asarray(score, float), np.asarray(weights, float)
    if metric == "auroc":
        return metrics.auroc(~c, -s, w)
    if metric == "aurc":
        return metrics.aurc_w(c, s, w)
    if metric.startswith("risk@"):
        return metrics.selective_risk_at(c, s, float(metric[5:]), w)
    raise ValueError(f"unknown metric {metric!r}")


def _select(df: pd.DataFrame, sel: dict, within: dict) -> pd.DataFrame:
    g = df
    for k, v in {**within, **sel}.items():
        if k == "score":
            continue
        if k not in g:
            raise ValueError(f"selector column {k!r} not in the data")
        g = g[g[k].isin(v if isinstance(v, list) else [v])]
    dup = g["incident_uid"].duplicated()
    if dup.any():
        raise ValueError(f"arm {sel} matches several records per incident ({int(dup.sum())} duplicates): "
                         "add selector columns (model, retrieval, store_mode)")
    return g.set_index("incident_uid")


def _arms(spec: dict) -> list[str]:
    return ["a", "b", "c", "d"] if spec.get("kind") == "did" else ["a", "b"]


def intersect(df: pd.DataFrame, spec: dict) -> tuple[dict, list, dict]:
    """({arm: records indexed by incident}, common incidents, {arm: dropped incident count})."""
    within = spec.get("within") or {}
    arms = {k: _select(df, spec[k], within) for k in _arms(spec)}
    common = sorted(set.intersection(*(set(g.index) for g in arms.values())))
    for col, val in (spec.get("filter") or {}).items():
        keep = set(arms["a"].index[arms["a"][col].isin(val if isinstance(val, list) else [val])])
        common = [u for u in common if u in keep]
    dropped = {k: int(len(set(g.index) - set(common))) for k, g in arms.items()}
    return arms, common, dropped


def _changed(arms: dict, common: list) -> list:
    """Incidents where no manipulated (non-`full`) arm has evidence identical to `full`."""
    out = []
    for u in common:
        if not any(bool(g.at[u, "same_as_full"]) for g in arms.values()
                   if "same_as_full" in g and g.at[u, "condition"] != "full" and pd.notna(g.at[u, "same_as_full"])):
            out.append(u)
    return out


def _per_injection(diff: np.ndarray, inj: np.ndarray, w: np.ndarray) -> pd.Series:
    d = pd.DataFrame({"d": diff * w, "w": w, "i": inj}).groupby("i")
    return d["d"].sum() / d["w"].sum()


def _groups_of_injections(a0: pd.DataFrame, group_col: str) -> pd.Series:
    g = a0.groupby("injection_id")[group_col].nunique(dropna=False)
    if (g > 1).any():
        raise ValueError(f"injection(s) in several {group_col} values: {list(g[g > 1].index[:3])}")
    return a0.groupby("injection_id")[group_col].first()


def evaluate(df: pd.DataFrame, spec: dict, n_boot: int = 10000, n_perm: int = 10000, seed: int = 0,
             restrict: list | None = None, group_col: str | None = None, sesoi: float | None = None) -> dict:
    arms, common, dropped = intersect(df, spec)
    if restrict is not None:
        common = [u for u in common if u in set(restrict)]
    metric = spec["metric"]
    kind = spec.get("kind", "diff")
    a0 = arms["a"].loc[common]
    inj = a0["injection_id"].to_numpy()
    # equal weight per injection on the intersection
    w = 1.0 / a0.groupby("injection_id")["injection_id"].transform("size").to_numpy() if len(common) else np.array([])
    row = {"contrast": spec["name"], "metric": metric, "kind": kind, "n_incidents": len(common),
           "n_injections": int(len(set(inj))), **{f"dropped_{k}": v for k, v in dropped.items()}}
    if not common:
        return {**row, "est": np.nan, "lo": np.nan, "hi": np.nan, "p": np.nan, "test": None}
    grouped = group_col is not None and group_col in a0 and a0[group_col].notna().all()
    sc = {k: spec[k].get("score", "consensus") for k in arms}
    if metric in DECOMPOSABLE:
        v = {k: record_values(g.loc[common], metric, sc[k]) for k, g in arms.items()}
        diff = v["a"] - v["b"] if kind == "diff" else (v["a"] - v["b"]) - (v["c"] - v["d"])
        per = _per_injection(diff, inj, w)
        boot = metrics.cluster_bootstrap_means(per.to_numpy(), per.index.to_numpy(), None, n=n_boot, seed=seed)
        sf = metrics.sign_flip_test(per.to_numpy(), n=n_perm, seed=seed)
        d = per.to_numpy()
        skew = float(((d - d.mean()) ** 3).mean() / d.std() ** 3) if d.std() > 0 else 0.0
        row.update(est=float(per.mean()), lo=float(boot["lo"]), hi=float(boot["hi"]), p=sf["p"], test="sign_flip",
                   skew_per_injection=skew)
        if grouped:
            grp = _groups_of_injections(a0, group_col).reindex(per.index).to_numpy()
            gb = metrics.cluster_bootstrap_means(per.to_numpy(), grp, None, n=n_boot, seed=seed)
            row.update(lo_group=float(gb["lo"]), hi_group=float(gb["hi"]), n_groups=int(gb["n_clusters"]))
        if metric == "ac1" and kind == "diff" and "representative" in a0:
            rep = a0["representative"].astype(bool).to_numpy()
            mc = metrics.mcnemar(v["a"][rep].astype(bool), v["b"][rep].astype(bool))
            row["mcnemar_representative_p"] = mc["p"]
    else:
        cols = []
        for k in _arms(spec):
            g = arms[k].loc[common]
            cols += [g["correct"].astype(float).to_numpy(), g[f"score_{sc[k]}"].astype(float).to_numpy()]
        X = np.column_stack(cols)
        sign = [1, -1, -1, 1][:len(_arms(spec))]

        def fn(x, ww):
            vals = [set_metric(x[:, 2 * i], x[:, 2 * i + 1], ww, metric) for i in range(len(sign))]
            return float(np.dot(sign, vals))
        boot = metrics.cluster_bootstrap(X, inj, w, fn=fn, n=n_boot, seed=seed)
        row.update(est=boot["est"], lo=boot["lo"], hi=boot["hi"], p=boot["p"], test="cluster_bootstrap")
        if grouped:
            gb = metrics.cluster_bootstrap(X, a0[group_col].to_numpy(), w, fn=fn, n=n_boot, seed=seed)
            row.update(lo_group=gb["lo"], hi_group=gb["hi"], n_groups=gb["n_clusters"])
    s = spec.get("sesoi", sesoi)
    row["ci_reading"] = ci_reading(row["lo"], row["hi"], metric, s)
    if grouped:
        row["ci_reading_group"] = ci_reading(row["lo_group"], row["hi_group"], metric, s)
    return row


def run(df: pd.DataFrame, specs: list[dict], families: dict | None = None, n_boot: int = 10000,
        n_perm: int = 10000, seed: int = 0, group_col: str | None = None, sesoi: float | None = None) -> pd.DataFrame:
    """One row per contrast (and a second, `require_changed`, row when requested); Holm per family."""
    in_family = {n for names in (families or {}).values() for n in names}
    bad = [s["name"] for s in specs if s["name"] in in_family and _selects_exploratory(s)]
    if bad:
        raise ValueError(f"contrasts {bad} select an exploratory IM1 arm and cannot belong to a family")
    rows = []
    for spec in specs:
        rows.append({**evaluate(df, spec, n_boot, n_perm, seed, group_col=group_col, sesoi=sesoi), "filter": "none"})
        if spec.get("require_changed"):
            arms, common, _ = intersect(df, spec)
            note = None if "same_as_full" in df else "same_as_full unavailable (no visibility join): filter not applied"
            rows.append({**evaluate(df, spec, n_boot, n_perm, seed, restrict=_changed(arms, common),
                                    group_col=group_col, sesoi=sesoi),
                         "filter": "require_changed", "note": note})
    out = pd.DataFrame(rows)
    if not len(out):
        return pd.DataFrame(columns=["contrast", "metric", "kind", "filter", "est", "lo", "hi", "p", "family",
                                     "p_holm", "assumptions"])
    out["family"], out["p_holm"] = None, np.nan
    for fam, names in (families or {}).items():
        m = out["contrast"].isin(names) & (out["filter"] == "none") & out["p"].notna()
        adj = metrics.holm(out.loc[m, "p"].to_dict())
        out.loc[m, "family"] = fam
        out.loc[m, "p_holm"] = pd.Series(adj)
    out["assumptions"] = [
        "; ".join([ASSUMPTIONS[t] for t in (r["test"],) if t] + [ASSUMPTIONS["intersection"], ASSUMPTIONS["censored_ranks"],
                                                                 ASSUMPTIONS["sampling"]])
        for _, r in out.iterrows()]
    out["exploratory"] = out["family"].isna()
    return out
