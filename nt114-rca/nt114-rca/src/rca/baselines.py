"""Non-LLM baselines on the incidents a canonical config selects (CPU only).

  python -m rca.baselines <cfg>

- B0 random: expected AC@1 / AC@3 of a uniform random ranking over the candidates (analytic).
- B1 max-z: the services of the evidence's Metrics block in its order (largest robust z first), then
  the other candidates in the evidence file's shuffled order; needs the evidence files of `prepare`.
- B1 logs / B1 traces: the same rule on the Logs or the Traces block alone (a trace block's call-edge
  lines contribute both endpoints), so every condition with any block has a non-LLM row.
- B1m evidence order: services by first appearance across the whole evidence text, block by block
  (service lines and call-edge endpoints), then the shuffled rest: the fair non-LLM reference for
  "the summary already ranks the root".
  A B1 variant whose block is absent from a condition writes a row with `no_row_reason` and no score.
- B3 majority: the most frequent primary root of the **train** role of the config's split for that
  dataset (`label_prior: train`). Without train incidents it falls back to the scored set's own prior
  (`label_prior: scored_set`, `reference_only: true`: a label-prior reference, never a comparator).
- B3 alert-entity (RCA100 only): the service of the first alert's entity in the visible incident text.
- `--baro`: the BARO-style metric baseline (`rca.baro`, named `BARO-style (unvalidated)`) on the raw
  metric frame. Every condition except `no_metric` keeps the metrics unchanged, so one ranking serves
  them all; services are matched to candidates by `data.canon` (unmatched names are counted, then
  dropped). `table_baro_overlap.csv` compares it with B1 max-z per incident and condition (top-1
  agreement, top-5 Jaccard, Kendall tau on the shared top 5) and gives the paired AC@1 difference
  from `rca.contrasts`.

Rows are keyed like grid rows (`incident_uid`, `condition`, `retrieval: none`, `rank`, `correct`) so
`rca.analyze` can contrast a baseline with the LLM on the same incidents. Writes `baselines.jsonl`
next to the config's `out` and returns the injection-weighted table.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd

from . import analyze, score
from . import baro as baro_mod
from .data import canon

ALERT_DATASETS = {"rca100"}


def random_expected(n_candidates: int, n_hits: int = 1) -> tuple[float, float]:
    """P(a hit at rank 1) and P(a hit in the top 3) for a uniform random ranking."""
    n, h = n_candidates, min(n_hits, n_candidates)
    return h / n, 1 - comb(n - h, min(3, n)) / comb(n, min(3, n))


# a service line `- svc: ...` or a call edge `- parent -> child: ...`; status lines have no colon
_MENTION = re.compile(r"^- ([^:\n]+?)(?: -> ([^:\n]+?))?:", re.M)
BLOCKS = {"B1 max-z": "Metrics", "B1 logs": "Logs", "B1 traces": "Traces"}
B1M = "B1m evidence order"


def block_text(text: str, name: str) -> str | None:
    """Body of the `## <name>` block, or None when the evidence has no such block."""
    m = re.search(rf"^## {name}.*?$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else None


def mentions(body: str) -> list[str]:
    """Services in order of first appearance: service lines and both endpoints of call-edge lines."""
    out = []
    for a, b in _MENTION.findall(body):
        out += [a.strip()] + ([b.strip()] if b else [])
    return list(dict.fromkeys(out))


def _rank(named: list[str], cands: list[str]) -> list[str]:
    named = [s for s in named if s in cands]
    return named + [s for s in cands if s not in named]


def block_ranking(rec: dict, condition: str = "full", block: str = "Metrics") -> list[str] | None:
    """Services of one evidence block in its order, then the rest of the candidates; None without the block."""
    body = block_text(rec["conditions"][condition]["text"], block)
    return None if body is None else _rank(mentions(body), rec["candidates"])


def max_z_ranking(rec: dict, condition: str = "full") -> list[str]:
    return block_ranking(rec, condition, "Metrics") or list(rec["candidates"])


def evidence_order_ranking(rec: dict, condition: str = "full") -> list[str]:
    """B1m: first appearance across every block, in block order (the `Not available` note names none)."""
    text = rec["conditions"][condition]["text"]
    return _rank(mentions(text), rec["candidates"])


def alert_entity(inc: dict) -> str | None:
    """`"<title> | <entity>"` with entity `<service>[::<operation>]` -> canonical service name. Without
    the separator the text is the entity alone only when it has `::` (else it is a bare title)."""
    text = (inc.get("context") or {}).get("visible_text") or ""
    ent = text.rsplit(" | ", 1)[-1] if " | " in text else (text if "::" in text else "")
    svc = ent.split("::", 1)[0].strip()
    return canon(svc) if svc else None


def baro_ranking(cn, uid: str, cands: list[str]) -> tuple[list[str] | None, int]:
    """BARO-style service ranking mapped to candidates, and the number of ranked services left unmatched."""
    from .legacy_view import legacy_telemetry
    m = legacy_telemetry(cn.store, uid)["metrics"]
    if m is None:
        return None, 0
    t = cn.store.incident(uid)["time"]["anchor_ns"] // 10**9
    by_key = {canon(c): c for c in cands}
    named = baro_mod.rank(m, t)["services"]
    mapped = [by_key[canon(x)] for x in named if canon(x) in by_key]
    return _rank(mapped, cands), len([x for x in named if canon(x) not in by_key])


def rows(cfg: dict, with_baro: bool = False) -> list[dict]:
    from .run_grid import Canon, evidence_dir
    cn = Canon(cfg)
    sel = cn.selected()
    lab = cn.labels()
    ev_dir = evidence_dir(cfg)
    by_ds: dict[str, list] = {}
    for _, inc in sel:
        by_ds.setdefault(inc["dataset_id"], []).append(inc)
    # the prior comes from train incidents only when none of them is scored (not the zero-shot union)
    train = cn.incidents("train") if cn.split_dir and "train" not in cn.split_roles() else []
    out = []
    for ds, incs in by_ds.items():
        prior_incs = [i for i in train if i["dataset_id"] == ds]
        label_prior = "train" if prior_incs else "scored_set"
        prim = Counter(r for i in (prior_incs or incs)
                       if (r := lab[i["incident_uid"]]["root_cause"].get("primary_root_service")) is not None)
        majority = prim.most_common(1)[0][0] if prim else None
        for inc in incs:
            uid = inc["incident_uid"]
            tr = cn.truth(uid)
            cands = inc["candidates"]["services"]
            base = {"incident_uid": uid, "dataset": ds, "system": inc["system"], "split_id": cn.split_id,
                    "split_role": cn.roles.get(uid), "label_granularity": tr.granularity,
                    "n_candidates": len(cands), "set_scored": tr.root_service is None,
                    "retrieval": "none", "store_mode": "-", "oracle_store": False, "no_row_reason": None}

            def scored(name, cond, ranking, **extra):
                c = score.correctness(ranking, tr, len(cands))
                return {**base, "baseline": name, "condition": cond, "rank": c["rank"],
                        "correct": bool(c["correct_at_1"]), "ac1": float(c["correct_at_1"]),
                        "ac3": float(c["correct_at_3"]), "top5": list(ranking[:5]), **extra}

            a1, a3 = random_expected(len(cands), len(score.truth_ids(tr)))
            out.append({**base, "baseline": "B0 random", "condition": "full", "ac1": a1, "ac3": a3, "analytic": True})
            f = ev_dir / f"{uid}.json"
            if f.is_file():
                rec = json.loads(f.read_text(encoding="utf-8"))
                for cond in rec["conditions"]:
                    for name, block in BLOCKS.items():
                        r = block_ranking(rec, cond, block)
                        out.append(scored(name, cond, r) if r is not None else
                                   {**base, "baseline": name, "condition": cond, "no_row_reason": f"no {block} block"})
                    out.append(scored(B1M, cond, evidence_order_ranking(rec, cond)))
                if with_baro:
                    br, unmatched = baro_ranking(cn, uid, rec["candidates"])
                    for cond in rec["conditions"]:
                        out.append(scored(baro_mod.NAME, cond, br, baro_unmatched=unmatched)
                                   if br is not None and cond != "no_metric" else
                                   {**base, "baseline": baro_mod.NAME, "condition": cond, "no_row_reason": "no metrics"})
            if majority is not None:
                out.append(scored("B3 majority", "full", [majority], guess=majority, label_prior=label_prior,
                                  reference_only=label_prior == "scored_set"))
            if ds in ALERT_DATASETS:
                guess = alert_entity(inc)
                out.append(scored("B3 alert-entity", "full", [guess] if guess else [], guess=guess))
    return out


def _kendall_shared(a: list, b: list) -> float:
    shared = [x for x in a if x in b]
    if len(shared) < 2:
        return float("nan")
    from scipy.stats import kendalltau
    return float(kendalltau([a.index(x) for x in shared], [b.index(x) for x in shared]).statistic)


def baro_overlap(df: pd.DataFrame, data_home: Path | None = None, n_boot: int = 2000, n_perm: int = 10000,
                 seed: int = 0) -> pd.DataFrame:
    """B1 max-z vs BARO-style per dataset x split role x condition, on the incidents where both are
    scored; agreement and the paired AC@1 difference use the same incidents."""
    from . import contrasts
    s = df[df["no_row_reason"].isna() & df["baseline"].isin(["B1 max-z", baro_mod.NAME])]
    s = s.assign(split_role=s["split_role"].fillna("-")) if "split_role" in s else s.assign(split_role="-")
    units = analyze.attach_units(s.rename(columns={"baseline": "model"}), data_home)
    recs = []
    for (ds, role, cond), g in units.groupby(["dataset", "split_role", "condition"]):
        tops = {m: dict(zip(h["incident_uid"], h["top5"])) for m, h in g.groupby("model")}
        if len(tops) < 2:
            continue
        uids = sorted(set(tops["B1 max-z"]) & set(tops[baro_mod.NAME]))
        a, b = [list(tops["B1 max-z"][u]) for u in uids], [list(tops[baro_mod.NAME][u]) for u in uids]
        tau = [_kendall_shared(x, y) for x, y in zip(a, b)]
        con = contrasts.evaluate(g, {"name": f"b1_vs_baro_{cond}", "a": {"model": "B1 max-z"},
                                     "b": {"model": baro_mod.NAME}, "metric": "ac1"}, n_boot, n_perm, seed)
        recs.append({"dataset": ds, "split_role": role, "condition": cond, "n_incidents": len(uids),
                     "n_injections": con.get("n_injections"),
                     "top1_agreement": float(np.mean([x[0] == y[0] for x, y in zip(a, b)])),
                     "top5_jaccard": float(np.mean([len(set(x) & set(y)) / len(set(x) | set(y)) for x, y in zip(a, b)])),
                     "kendall_tau_shared_top5": float(np.nanmean(tau)) if np.isfinite(tau).any() else float("nan"),
                     **{f"dAC1_{k}": v for k, v in con.items() if k in ("est", "lo", "hi", "p")}})
    return pd.DataFrame(recs)


def table(df: pd.DataFrame, data_home: Path | None = None) -> pd.DataFrame:
    """Injection-weighted AC@1 / AC@3 per dataset x split role x baseline x condition (and unweighted per
    record). Rows with a `no_row_reason` are counted, not scored."""
    df = df.assign(split_role=df["split_role"].fillna("-")) if "split_role" in df else df.assign(split_role="-")
    gaps = df.groupby(["dataset", "split_role", "baseline", "condition"])["no_row_reason"].apply(
        lambda x: int(x.notna().sum())) if "no_row_reason" in df else None
    if "no_row_reason" in df:
        df = df[df["no_row_reason"].isna()]
    w = analyze.attach_units(df.rename(columns={"baseline": "model"}), data_home)
    recs = []
    for (ds, role, b, cond), g in w.groupby(["dataset", "split_role", "model", "condition"]):
        prior = g["label_prior"].dropna().unique() if "label_prior" in g else []
        recs.append({"dataset": ds, "split_role": role, "baseline": b, "condition": cond, "n_records": len(g),
                     "n_no_row": int(gaps.get((ds, role, b, cond), 0)) if gaps is not None else 0,
                     "n_injections": g["injection_id"].nunique(),
                     "AC@1": float(np.average(g["ac1"], weights=g["weight"])),
                     "AC@3": float(np.average(g["ac3"], weights=g["weight"])),
                     "AC@1_per_record": float(g["ac1"].mean()),
                     "label_prior": prior[0] if len(prior) else None})
    return pd.DataFrame(recs)


def main(argv=None) -> pd.DataFrame:
    from .run_grid import load_cfg
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cfg")
    ap.add_argument("--baro", action="store_true", help="add the BARO-style baseline and its overlap with B1")
    a = ap.parse_args(argv)
    cfg = load_cfg(a.cfg)
    df = pd.DataFrame(rows(cfg, with_baro=a.baro))
    out = Path(cfg["out"]).parent
    out.mkdir(parents=True, exist_ok=True)
    df.to_json(out / "baselines.jsonl", orient="records", lines=True)
    from .run_grid import Canon
    tab = table(df, Canon(cfg).data_home)
    tab.to_csv(out / "table_baselines.csv", index=False)
    if a.baro:
        ov = baro_overlap(df, Canon(cfg).data_home)
        ov.to_csv(out / "table_baro_overlap.csv", index=False)
        print(ov.to_string(index=False))
    print(tab.to_string(index=False))
    return tab


if __name__ == "__main__":
    main()
