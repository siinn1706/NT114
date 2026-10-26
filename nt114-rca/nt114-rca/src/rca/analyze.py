"""Analysis entry point (evaluation-only): grids -> weighted, injection-clustered tables.

  python -m rca.analyze configs/analysis/<name>.yaml
  python -m rca.analyze results/grid.jsonl [--data-home D]        # defaults: no contrasts, exploratory

The analysis config names the grid file(s), the optional raw outputs (default `llm_raw.jsonl` next to
each grid), visibility JSONL, baselines JSONL, `data_home`, contrasts and families, the selective
goals and `preregistration_sha`. Tables:

- `table_cells`: per dataset x granularity x split role x set-scored x model x condition x retrieval:
  AC@1-5 and MRR@5 (ranks beyond 5 are censored; no mean rank is computed), Brier, gap, ECE on the
  support, AUROC and AURC, each with a cluster-bootstrap CI over injections;
- `table_confidence`: every registry score per cell (error detection; calibration for probabilities);
- `table_selective`: risk-coverage per score, L1, C2, O, and DEV-fit thresholds transferred to test;
- `table_contrasts`: the declared paired contrasts (`rca.contrasts`); scored baseline rows join the
  frame with `model` = the baseline name, so `{model: B1m evidence order}` is an arm like any other;
- `table_shift`: DEV vs test by system x fault;
- `table_cost`: tokens, latency, retrieval and preparation seconds per cell and arm path (`rca.cost`);
- `table_cells_by_precedent_root` (retrieval rows only): `table_cells` split by whether a retrieved precedent
  carries the query's root, i.e. records, injections and outcomes per stratum of the retrieval regime.

`analysis_config.yaml` (the resolved config, absolute input paths) and `analysis_meta.json` (sha256 of
every input and table) let `python -m rca.reproduce <out dir>` regenerate and compare the tables.

Without `preregistration_sha` every file is prefixed `exploratory_`. With it, the headline guard
refuses mock rows, DEV rows, mixed prompt versions, mixed model revisions or server fingerprints
within a model, oracle-store rows and mixed evidence fingerprints of an incident, and unvalidated
confidence scores go to a separate exploratory file. `excluded_from_primary` records are removed
from every table and counted in `analysis_meta.json`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import confidence, contrasts, cost, score, selective
from .metrics import RANK_CAP, auroc, aurc_w, cluster_bootstrap, cluster_bootstrap_means, ece_w, selective_risk_at


def load(path) -> pd.DataFrame:
    with open(path, encoding="utf-8") as f:
        return pd.DataFrame([json.loads(l) for l in f if l.strip()])


class HeadlineGuardError(ValueError):
    pass


def _mixed_within(grid: pd.DataFrame, col: str, by) -> list:
    if col not in grid or any(b not in grid for b in ([by] if isinstance(by, str) else by)):
        return []
    n = grid.groupby(by)[col].nunique(dropna=False)
    return sorted(n[n > 1].index)


def guard_headline(grid: pd.DataFrame) -> None:
    """Headline tables never contain mock rows, DEV rows, mixed prompt versions, mixed model revisions or
    server fingerprints within one model, oracle-store rows or mixed evidence fingerprints of an incident."""
    problems = []
    if not len(grid):
        problems.append("no rows")
    if "backend" in grid and (grid["backend"] == "mock").any():
        problems.append("mock LLM rows")
    if "split_role" in grid and (grid["split_role"] == "val").any():
        problems.append("DEV (split_role=val) rows")
    if "prompt_version" in grid and grid["prompt_version"].nunique() > 1:
        problems.append(f"mixed prompt_version {sorted(grid['prompt_version'].unique())}")
    for col in ("model_revision", "server_fp", "exec_sig"):
        bad = _mixed_within(grid, col, "model")
        if bad:
            problems.append(f"mixed {col} within model(s) {bad}")
    if "oracle_store" in grid and grid["oracle_store"].fillna(False).astype(bool).any():
        problems.append("oracle_store (no_precedent) rows")
    # evidence arms have their own builders and fingerprints: mixing is checked within an arm
    bad = _mixed_within(grid.assign(arm=selective.arm_column(grid)), "evidence_fp", ["incident_uid", "arm"])
    if bad:
        problems.append(f"mixed evidence fingerprints for {len(bad)} incident(s)")
    if problems:
        raise HeadlineGuardError("refusing headline tables: " + "; ".join(problems))


def attach_units(df: pd.DataFrame, data_home: Path | None = None, uid_col: str = "incident_uid") -> pd.DataFrame:
    """Join weight / injection_id / coverage causes; one unit per record when no eval-units report exists."""
    uid = df[uid_col].fillna(df["case_id"]) if "case_id" in df else df[uid_col]
    df = df.assign(incident_uid=uid)
    frames = []
    for ds in sorted(df["dataset"].dropna().unique()) if "dataset" in df else []:
        path = Path(data_home) / "reports" / f"eval-units-{ds}.json" if data_home else None
        if path is not None and path.is_file():
            frames.append(score.units(data_home, ds))
    known = pd.concat(frames) if frames else pd.DataFrame(columns=score.UNIT_COLUMNS)
    rest = score.default_units(set(df["incident_uid"]) - set(known["incident_uid"]))
    units = pd.concat([known, rest], ignore_index=True)
    out = df.drop(columns=[c for c in score.UNIT_COLUMNS if c != "incident_uid" and c in df]).merge(
        units, on="incident_uid", how="left")
    return reweight(out)


def attach_groups(df: pd.DataFrame, data_home=None) -> pd.DataFrame:
    """`group_id` of each record from its split's `assignments.jsonl` (sensitivity clusters, D10); left out
    when no assignment file is found."""
    if not data_home or "split_id" not in df:
        return df
    groups = {}
    for sid in df["split_id"].dropna().unique():
        path = Path(data_home) / "splits" / str(sid) / "assignments.jsonl"
        if path.is_file():
            groups.update({a["incident_uid"]: a["group_id_hash"] for a in _read_assignments(path)})
    return df.assign(group_id=df["incident_uid"].map(groups)) if groups else df


def _read_assignments(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def reweight(df: pd.DataFrame) -> pd.DataFrame:
    """Equal weight per injection within each evaluated cell: weight = 1 / (records of that injection in
    the cell). The eval-units weights count every record of the dataset, so in a cell holding only part
    of an injection (a condition not applicable to every task, a `limit_per_system` sample) that
    injection would otherwise count less than one. On the full sets the weights are unchanged."""
    keys = [c for c in strata_cols(df) if c != "label_granularity"] + ["injection_id"]
    n = df.groupby(keys, dropna=False)["incident_uid"].transform("nunique")
    return df.assign(weight=1.0 / n)


def strata_cols(df: pd.DataFrame, extra=()) -> list[str]:
    """Cell keys; `arm` (evidence arm, present when a grid has R-a rows) keeps arms apart in every cell,
    weight, pool and DEV-fit stratum."""
    return [c for c in ("dataset", "label_granularity", "split_role", "set_scored", *extra, "model", "arm", "condition",
                        "retrieval", "store_mode") if c in df]


# ---------------------------------------------------------------- tables
def _boot(fn, cols: list[np.ndarray], g: pd.DataFrame, n_boot: int, seed: int) -> tuple[float, float, float]:
    X = np.column_stack(cols)
    r = cluster_bootstrap(X, g["injection_id"].to_numpy(), g["weight"].to_numpy(),
                          fn=lambda x, w: fn(*[x[:, i] for i in range(x.shape[1])], w), n=n_boot, seed=seed)
    return r["est"], r["lo"], r["hi"]


def cell_table(df: pd.DataFrame, n_boot: int = 2000, seed: int = 0, extra=()) -> pd.DataFrame:
    """Weighted cell metrics, each with a percentile cluster-bootstrap CI over injections."""
    rows = []
    cols = strata_cols(df, extra)
    for k, g in df.groupby(cols, dropna=False):
        rec = dict(zip(cols, k if isinstance(k, tuple) else (k,)))
        w, inj = g["weight"].to_numpy(), g["injection_id"].to_numpy()
        r = g["rank"].astype(float).to_numpy()
        c = g["correct"].astype(float).to_numpy()
        pc, pv = g["conf_consensus"].astype(float).to_numpy(), g["conf_verbal"].astype(float).to_numpy()
        means = {f"AC@{j}": (r <= j).astype(float) for j in range(1, RANK_CAP + 1)}
        means["MRR@5"] = np.where(r <= RANK_CAP, 1.0 / r, 0.0)
        means["Brier_consensus"], means["gap_consensus"] = (np.clip(pc, 0, 1) - c) ** 2, pc - c
        means["Brier_verbal"], means["gap_verbal"] = (np.clip(pv, 0, 1) - c) ** 2, pv - c
        means["parse_failed"] = g["parse_failed"].astype(float).to_numpy() if "parse_failed" in g else np.zeros(len(g))
        b = cluster_bootstrap_means(np.column_stack(list(means.values())), inj, w, n=n_boot, seed=seed)
        rec.update(n_records=len(g), n_injections=int(len(set(inj))))
        for i, name in enumerate(means):
            rec[name] = float(b["est"][i])
            if name != "parse_failed":
                rec[f"{name}_lo"], rec[f"{name}_hi"] = float(b["lo"][i]), float(b["hi"][i])
        cb = c.astype(bool)
        for name, fn, arrays in (
                ("ECE_support_consensus", lambda cc, p, ww: ece_w(cc, p, ww, "support"), [c, pc]),
                ("AUROC_consensus", lambda cc, p, ww: auroc(cc < 0.5, -p, ww), [c, pc]),
                ("AUROC_verbal", lambda cc, p, ww: auroc(cc < 0.5, -p, ww), [c, pv]),
                ("AURC_consensus", lambda cc, p, ww: aurc_w(cc >= 0.5, p, ww), [c, pc])):
            if name.startswith("AUROC") and (cb.all() or not cb.any()):
                rec[name] = rec[f"{name}_lo"] = rec[f"{name}_hi"] = np.nan
                continue
            rec[name], rec[f"{name}_lo"], rec[f"{name}_hi"] = _boot(fn, arrays, g, n_boot, seed)
        rows.append(rec)
    return pd.DataFrame(rows)


def precedent_root_table(df: pd.DataFrame, n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Retrieval cells split by `precedent_has_root`: one of the `top_k` precedents shown to the model is labelled
    with the query's root (the grid's `hit_has_truth`, computed after retrieval and the model call).

    It describes the retrieval regime: the grouped split holds out the query's (root, fault) cell, not its root
    service. It is not evidence of leakage, and no confidence score, threshold or prediction uses it."""
    if "hit_has_truth" not in df or "retrieval" not in df:
        return pd.DataFrame()
    r = df[df["retrieval"].ne("none") & df["hit_has_truth"].notna()]
    if not len(r):
        return pd.DataFrame()
    return cell_table(r.assign(precedent_has_root=r["hit_has_truth"].astype(bool)), n_boot, seed,
                      extra=("precedent_has_root",))


def _flat(ep: str, v: dict) -> dict:
    """An endpoint {est, lo, hi[, nan_draws]} as columns `ep`, `ep_lo`, `ep_hi`[, `ep_nan_draws`]."""
    return {ep: v["est"], f"{ep}_lo": v["lo"], f"{ep}_hi": v["hi"],
            **({f"{ep}_nan_draws": v["nan_draws"]} if "nan_draws" in v else {})}


def confidence_table(df: pd.DataFrame, names: list[str], n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Every requested registry score per cell: error detection (positive = wrong) with a CI on AUROC,
    AURC, and Brier / ECE / gap for probability scores."""
    rows = []
    cols = strata_cols(df)
    for k, g in df.groupby(cols, dropna=False):
        base = dict(zip(cols, k if isinstance(k, tuple) else (k,)))
        for name in names:
            spec = confidence.REGISTRY[name]
            s = g[f"score_{name}"].astype(float)
            m = s.notna().to_numpy()
            h = g[m]
            rec = {**base, "score": name, "validated": spec.validated, "support": spec.support,
                   "n_records": len(g), "n_scored": int(m.sum())}
            if m.sum() >= 2:
                c, p, w = h["correct"].astype(bool).to_numpy(), s[m].to_numpy(), h["weight"].to_numpy()
                if c.all() or not c.any():
                    rec["AUROC"] = rec["AUROC_lo"] = rec["AUROC_hi"] = np.nan
                else:
                    rec["AUROC"], rec["AUROC_lo"], rec["AUROC_hi"] = _boot(
                        lambda cc, pp, ww: auroc(cc < 0.5, -pp, ww), [c.astype(float), p], h, n_boot, seed)
                for ep, v in selective.confidence_endpoints(c, p, h["injection_id"].to_numpy(), w, spec.probability,
                                                            spec.support, n_boot, seed).items():
                    rec.update(_flat(ep, v))
            rows.append(rec)
    return pd.DataFrame(rows)


SELECTIVE_TIES = {
    "risk@c": "tie groups answered together; achieved coverage (>= c) reported as coverage_ties@c",
    "risk_exact@c": "exactly c of the weight answered; the boundary tie group answered fractionally "
                    "(expected risk of C1's seeded random tie-break); gain_exact@c = base error - risk_exact@c "
                    "is the contrast with C2 random deferral",
    "dev_fit": "tau fitted on the DEV rows of the same stratum (source_stratum) for the goal, applied unchanged; "
               "achieved test coverage and risk reported with CIs",
}


def _pooled(df: pd.DataFrame, pools: dict) -> pd.DataFrame:
    """Declared pools as extra cells: `{name: {column: [values]}}` -> rows with column = `pool:<name>`.
    Within the pooled cell weight = 1 / (records of the injection), so every injection weighs 1 however
    many pooled conditions apply to it (an incident has one record per condition, so `reweight`'s
    distinct-incident count would not do). Nothing is pooled unless declared."""
    frames = []
    for name, spec in (pools or {}).items():
        (col, values), = spec.items()
        if col in df:
            sub = df[df[col].isin(values)].assign(**{col: f"pool:{name}"})
            if len(sub):
                keys = [c for c in strata_cols(sub) if c != "label_granularity"] + ["injection_id"]
                frames.append(sub.assign(weight=1.0 / sub.groupby(keys, dropna=False)["incident_uid"].transform("size")))
    return pd.concat(frames, ignore_index=True) if frames else df.iloc[:0]


def _same_stratum(df: pd.DataFrame, base: dict, keys: list[str]) -> pd.DataFrame:
    m = pd.Series(True, index=df.index)
    for k in keys:
        v = base[k]
        m &= df[k].isna() if pd.isna(v) else df[k] == v
    return df[m]


def _plain(v):
    return v.item() if hasattr(v, "item") else v


def selective_table(df: pd.DataFrame, names: list[str], dev: pd.DataFrame | None = None, goals: dict | None = None,
                    n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Risk-coverage endpoints per score and the L1 / C2 / O references per cell, each with a CI over
    injections (`SELECTIVE_TIES` states the tie handling). DEV-fit thresholds (`goals`: {coverage: [...],
    risk: [...]}) are fitted on the `dev` rows of the **same stratum** (dataset, granularity, set-scored,
    model, condition, retrieval, store mode) and applied unchanged to the test cell, next to the
    test-oracle point; a stratum without DEV rows gets a `no_source` row. `goals["pools"]` declares
    pooled cells (`{name: {column: [values]}}`), pooled the same way on DEV and test."""
    goals = goals or {}
    pools = goals.get("pools")
    df = pd.concat([df, _pooled(df, pools)], ignore_index=True)
    dev = dev if dev is not None else df.iloc[:0]
    dev = pd.concat([dev, _pooled(dev, pools)], ignore_index=True) if len(dev) else dev
    rows = []
    cols = strata_cols(df)
    fit_keys = [c for c in cols if c != "split_role"]
    coverages = sorted(set(selective.COVERAGES) | set(goals.get("coverage", [])))
    for k, g in df.groupby(cols, dropna=False):
        base = dict(zip(cols, k if isinstance(k, tuple) else (k,)))
        c, w, inj = g["correct"].astype(bool).to_numpy(), g["weight"].to_numpy(), g["injection_id"].to_numpy()
        for r in selective.references(c, g["abstain_vote"].to_numpy(), w, inj, n_boot, seed):
            rows.append({**base, "kind": "reference", **r})
        d = _same_stratum(dev, base, fit_keys) if len(dev) else dev
        source = {"source_split_role": "val", "source_stratum": json.dumps({kc: _plain(base[kc]) for kc in fit_keys}),
                  "n_dev_records": len(d), "n_dev_injections": int(d["injection_id"].nunique()) if len(d) else 0}
        for name in names:
            s = g[f"score_{name}"].astype(float).to_numpy()
            rec = {**base, "kind": "curve", "score": name, "n_scored": int((~np.isnan(s)).sum())}
            for ep, v in selective.selective_endpoints(c, s, inj, w, coverages, goals.get("risk", []),
                                                       n_boot, seed).items():
                rec.update(_flat(ep, v))
            rows.append(rec)
            if not len(dev):
                continue
            ds = d[f"score_{name}"].astype(float).to_numpy() if len(d) else np.array([])
            dm = ~np.isnan(ds)
            for kind, vals in (("coverage", goals.get("coverage", [])), ("risk", goals.get("risk", []))):
                for x in vals:
                    fit = {**base, "kind": "dev_fit", "score": name, "goal": kind, "goal_value": x, **source}
                    if not dm.any():
                        rows.append({**fit, "no_source": True, "tau": np.nan})
                        continue
                    dc, dw = d["correct"].astype(bool).to_numpy()[dm], d["weight"].to_numpy()[dm]
                    tau = selective.fit_threshold(dc, ds[dm], dw, **{kind: x})
                    real = selective.apply_threshold(c, s, tau, inj, w, n_boot, seed)
                    m = ~np.isnan(s)
                    if not m.any():
                        oracle = np.nan
                    elif kind == "risk":
                        oracle = selective.coverage_at_risk(c[m], s[m], x, w[m])
                    else:
                        oracle = selective_risk_at(c[m], s[m], x, w[m])
                    rows.append({**fit, "no_source": False, "tau": tau, **real,
                                 ("oracle_coverage" if kind == "risk" else "oracle_risk"): oracle})
    return pd.DataFrame(rows)


def baselines_table(df: pd.DataFrame, n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    rows = []
    for (ds, b, cond), g in df.groupby(["dataset", "model", "condition"]):
        r = cluster_bootstrap_means(g[["ac1", "ac3"]].astype(float).to_numpy(), g["injection_id"].to_numpy(),
                                    g["weight"].to_numpy(), n=n_boot, seed=seed)
        rows.append({"dataset": ds, "baseline": b, "condition": cond, "n_records": len(g),
                     "n_injections": g["injection_id"].nunique(), "AC@1": r["est"][0], "AC@1_lo": r["lo"][0],
                     "AC@1_hi": r["hi"][0], "AC@3": r["est"][1], "AC@3_lo": r["lo"][1], "AC@3_hi": r["hi"][1]})
    return pd.DataFrame(rows)


def joint_baselines(bl: pd.DataFrame, data_home=None) -> pd.DataFrame:
    """Scored, non-DEV baseline rows keyed like grid rows; analytic (B0), absent-block and label-prior
    reference rows (`reference_only`) never enter a contrast."""
    if not len(bl) or "rank" not in bl:
        return pd.DataFrame()
    keep = bl["rank"].notna()
    for col in ("no_row_reason", "reference_only"):
        if col in bl:
            keep &= ~bl[col].fillna(False).astype(bool) if col == "reference_only" else bl[col].isna()
    if "split_role" in bl:
        keep &= bl["split_role"] != "val"
    return attach_units(bl[keep].rename(columns={"baseline": "model"}), data_home)


# ---------------------------------------------------------------- entry point
def load_config(path: str, data_home: str | None = None) -> dict:
    p = Path(path)
    if p.suffix in (".yaml", ".yml"):
        with open(p, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    else:
        cfg = {"grids": [str(p)]}
    if data_home:
        cfg["data_home"] = data_home
    cfg.setdefault("out_dir", str(Path(cfg["grids"][0]).parent))
    return cfg


def _read_jsonl(paths) -> pd.DataFrame:
    frames = [load(p) for p in paths or [] if Path(p).is_file()]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_frame(cfg: dict) -> tuple[pd.DataFrame, dict]:
    """Grid rows with units, registry scores and visibility strata; and the counts of what was joined."""
    grid = _read_jsonl(cfg["grids"])
    if not len(grid):
        raise ValueError(f"no grid rows in {cfg['grids']}")
    if "arm" in grid:                   # rows written before the arm field are arm l0
        grid["arm"] = selective.arm_column(grid)
    raw = {}
    for p in cfg.get("raw") or [Path(g).parent / "llm_raw.jsonl" for g in cfg["grids"]]:
        raw.update(confidence.load_raw(p))
    sc, counts = confidence.scores(grid, raw)
    df = attach_groups(attach_units(pd.concat([grid, sc], axis=1), cfg.get("data_home")), cfg.get("data_home"))
    vis = _read_jsonl(cfg.get("visibility"))
    if len(vis):
        keep = [c for c in ("named", "in_candidates", "same_as_full", "token_anywhere") if c in vis]
        vis = vis.drop_duplicates(["incident_uid", "condition"], keep="last")[["incident_uid", "condition", *keep]]
        df = df.merge(vis, on=["incident_uid", "condition"], how="left")
        counts["visibility_joined"] = int(df["named"].notna().sum()) if "named" in df else 0
    excl = df["excluded"].notna() if "excluded" in df else pd.Series(False, index=df.index)
    counts["excluded_from_primary"] = int(excl.sum())
    return reweight(df[~excl].reset_index(drop=True)), counts


PATH_KEYS = ("grids", "raw", "visibility", "baselines", "prepare_log")


def _sha(path) -> str | None:
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def resolve_inputs(cfg: dict) -> dict:
    """Input paths made absolute and the defaults made explicit, so the config copy reruns anywhere."""
    out = dict(cfg)
    grids = [str(Path(g).resolve()) for g in cfg["grids"]]
    defaults = {"raw": [str(Path(g).parent / "llm_raw.jsonl") for g in grids],
                "prepare_log": [str(Path(g).parent / "prepare_log.jsonl") for g in grids]}
    out["grids"] = grids
    for k in PATH_KEYS[1:]:
        v = cfg.get(k) or defaults.get(k) or []
        out[k] = [str(Path(x).resolve()) for x in ([v] if isinstance(v, str) else v)]
    if cfg.get("data_home"):
        out["data_home"] = str(Path(cfg["data_home"]).resolve())
    out["out_dir"] = str(Path(cfg["out_dir"]).resolve())
    return out


def run(cfg: dict) -> dict:
    cfg = resolve_inputs(cfg)
    df, counts = build_frame(cfg)
    headline = bool(cfg.get("preregistration_sha"))
    is_dev = (df["split_role"] == "val") if "split_role" in df else pd.Series(False, index=df.index)
    # DEV rows only fit thresholds and feed the shift table; a DEV-only grid is analysed as exploratory
    if headline or (~is_dev).any():
        main, dev = df[~is_dev], df[is_dev]
    else:
        main, dev = df, df.iloc[:0]
    if headline:
        guard_headline(main)
    # IM1 arms are exploratory (D13): never in a headline table, reported in `exploratory_im1_*` files
    im1 = main.iloc[:0]
    if headline and "arm" in main:
        is_im1 = main["arm"].isin(contrasts.EXPLORATORY_ARMS)
        im1, main = main[is_im1], main[~is_im1]
    names = cfg.get("scores") or list(confidence.REGISTRY)
    bl = _read_jsonl(cfg.get("baselines"))
    validated = [n for n in names if confidence.REGISTRY[n].validated]
    n_boot, seed = int(cfg.get("n_boot", 2000)), int(cfg.get("seed", 0))
    out = Path(cfg["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    prefix = "" if headline else "exploratory_"
    tabs = {
        "table_cells": cell_table(main, n_boot, seed),
        "table_confidence": confidence_table(main, validated if headline else names, n_boot, seed),
        "table_selective": selective_table(main, validated if headline else names, dev, cfg.get("selective"),
                                           n_boot, seed),
        "table_contrasts": contrasts.run(pd.concat([main, im1, joint_baselines(bl, cfg.get("data_home"))], ignore_index=True),
                                         cfg.get("contrasts") or [], cfg.get("families"),
                                         int(cfg.get("n_boot_contrasts", n_boot)), int(cfg.get("n_perm", 10000)), seed,
                                         group_col="group_id" if "group_id" in df else None, sesoi=cfg.get("sesoi")),
        "table_shift": (selective.shift_table(pd.concat([df, _pooled(df, (cfg.get("selective") or {}).get("pools"))],
                                                        ignore_index=True),
                                              strata=[c for c in strata_cols(df) if c != "split_role"])
                        if "fault" in df else pd.DataFrame()),
        "table_cost": cost.table_cost(main, cfg["prepare_log"]),
    }
    if "named" in main:
        tabs["table_cells_by_named"] = cell_table(main[main["named"].notna()], n_boot, seed, extra=("named",))
    by_root = precedent_root_table(main, n_boot, seed)
    if len(by_root):
        tabs["table_cells_by_precedent_root"] = by_root
    if len(bl):
        scored = bl[bl["no_row_reason"].isna()] if "no_row_reason" in bl else bl
        tabs["table_baselines"] = baselines_table(attach_units(scored.rename(columns={"baseline": "model"}),
                                                               cfg.get("data_home")), n_boot, seed)
    written = {}
    for name, tab in tabs.items():
        path = out / f"{prefix}{name}.csv"
        tab.to_csv(path, index=False)
        written[name] = path.name
    if len(im1):
        for name, tab in (("table_cells", cell_table(im1, n_boot, seed)), ("table_cost", cost.table_cost(im1, cfg["prepare_log"]))):
            tab.to_csv(out / f"exploratory_im1_{name}.csv", index=False)
            written[f"im1_{name}"] = f"exploratory_im1_{name}.csv"
    if headline and set(names) - set(validated):
        extra = confidence_table(main, [n for n in names if n not in validated], n_boot, seed)
        extra.to_csv(out / "exploratory_table_confidence_unvalidated.csv", index=False)
        written["table_confidence_unvalidated"] = "exploratory_table_confidence_unvalidated.csv"
    (out / f"{prefix}analysis_config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=True, allow_unicode=True),
                                                       encoding="utf-8", newline="\n")
    meta = {"headline": headline, "preregistration_sha": cfg.get("preregistration_sha"), "counts": counts,
            "n_rows": int(len(main)), "n_dev_rows": int(len(dev)), "n_boot": n_boot, "seed": seed,
            "scores": {n: {"validated": confidence.REGISTRY[n].validated, "note": confidence.REGISTRY[n].note} for n in names},
            "assumptions": contrasts.ASSUMPTIONS, "selective_ties": SELECTIVE_TIES, "tables": written,
            "config": f"{prefix}analysis_config.yaml",
            "inputs_sha256": {x: _sha(x) for k in PATH_KEYS for x in cfg[k]},
            "tables_sha256": {n: _sha(out / f) for n, f in written.items()}}
    (out / f"{prefix}analysis_meta.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    return {"tables": tabs, "meta": meta}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config", help="analysis YAML, or a grid.jsonl for the default exploratory analysis")
    ap.add_argument("--data-home", help="data directory holding reports/eval-units-<dataset>.json")
    a = ap.parse_args(argv)
    try:
        res = run(load_config(a.config, a.data_home))
    except HeadlineGuardError as e:
        print(f"HeadlineGuardError: {e}")
        return 2
    pd.set_option("display.width", 200, "display.max_columns", 30)
    m = res["meta"]
    print(("headline" if m["headline"] else "EXPLORATORY (no preregistration_sha)") + f": {m['n_rows']} rows, "
          f"{m['counts']['excluded_from_primary']} excluded from primary, {m['counts']['missing_raw']} without raw outputs")
    cols = [c for c in ("dataset", "split_role", "model", "condition", "retrieval", "n_records", "n_injections",
                        "AC@1", "AC@1_lo", "AC@1_hi", "MRR@5", "Brier_consensus", "AUROC_consensus")
            if c in res["tables"]["table_cells"]]
    print(res["tables"]["table_cells"][cols].round(3).to_string(index=False))
    print("tables:", ", ".join(m["tables"].values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
