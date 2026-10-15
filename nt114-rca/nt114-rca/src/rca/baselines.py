"""Non-LLM baselines on the incidents a canonical config selects (CPU only).

  python -m rca.baselines <cfg>

- B0 random: expected AC@1 / AC@3 of a uniform random ranking over the candidates (analytic).
- B1 max-z: the services of the evidence's Metrics block in its order (largest robust z first), then
  the other candidates in the evidence file's shuffled order; needs the evidence files of `prepare`.
- B3 (RCA100 only): majority class (the most frequent primary root of the scored set, a label-prior
  reference, not a fair comparator) and alert-entity (the service of the first alert's entity in the
  visible incident text).

Writes `baselines.jsonl` next to the config's `out` and returns the injection-weighted table.
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
from .data import canon

ALERT_DATASETS = {"rca100"}


def random_expected(n_candidates: int, n_hits: int = 1) -> tuple[float, float]:
    """P(a hit at rank 1) and P(a hit in the top 3) for a uniform random ranking."""
    n, h = n_candidates, min(n_hits, n_candidates)
    return h / n, 1 - comb(n - h, min(3, n)) / comb(n, min(3, n))


def max_z_ranking(rec: dict, condition: str = "full") -> list[str]:
    text = rec["conditions"][condition]["text"]
    m = re.search(r"^## Metrics.*?$(.*?)(?=^## |\Z)", text, re.M | re.S)
    flagged = re.findall(r"^- ([^:\n]+):", m.group(1), re.M) if m else []
    cands = rec["candidates"]
    flagged = [s for s in dict.fromkeys(flagged) if s in cands]
    return flagged + [s for s in cands if s not in flagged]


def alert_entity(inc: dict) -> str | None:
    """`"<title> | <entity>"` with entity `<service>[::<operation>]` -> canonical service name. Without
    the separator the text is the entity alone only when it has `::` (else it is a bare title)."""
    text = (inc.get("context") or {}).get("visible_text") or ""
    ent = text.rsplit(" | ", 1)[-1] if " | " in text else (text if "::" in text else "")
    svc = ent.split("::", 1)[0].strip()
    return canon(svc) if svc else None


def rows(cfg: dict) -> list[dict]:
    from .run_grid import Canon, evidence_dir
    cn = Canon(cfg)
    sel = cn.selected()
    lab = cn.labels()
    ev_dir = evidence_dir(cfg)
    by_ds: dict[str, list] = {}
    for _, inc in sel:
        by_ds.setdefault(inc["dataset_id"], []).append(inc)
    out = []
    for ds, incs in by_ds.items():
        majority = None
        if ds in ALERT_DATASETS:
            prim = Counter(lab[i["incident_uid"]]["root_cause"]["primary_root_service"] for i in incs)
            majority = prim.most_common(1)[0][0]
        for inc in incs:
            uid = inc["incident_uid"]
            tr = cn.truth(uid)
            cands = inc["candidates"]["services"]
            base = {"incident_uid": uid, "dataset": ds, "system": inc["system"], "split_id": cn.split_id,
                    "n_candidates": len(cands), "set_scored": tr.root_service is None}
            a1, a3 = random_expected(len(cands), len(score.truth_ids(tr)))
            out.append({**base, "baseline": "B0 random", "condition": "full", "ac1": a1, "ac3": a3})
            f = ev_dir / f"{uid}.json"
            if f.is_file():
                rec = json.loads(f.read_text(encoding="utf-8"))
                for cond, ev in rec["conditions"].items():
                    if not ev["features"].get("has_metrics"):
                        continue
                    c = score.correctness(max_z_ranking(rec, cond), tr, len(rec["candidates"]))
                    out.append({**base, "baseline": "B1 max-z", "condition": cond,
                                "ac1": float(c["correct_at_1"]), "ac3": float(c["correct_at_3"])})
            if majority is not None:
                for name, guess in (("B3 majority", majority), ("B3 alert-entity", alert_entity(inc))):
                    c = score.correctness([guess] if guess else [], tr, len(cands))
                    out.append({**base, "baseline": name, "condition": "full", "guess": guess,
                                "ac1": float(c["correct_at_1"]), "ac3": float(c["correct_at_3"])})
    return out


def table(df: pd.DataFrame, data_home: Path | None = None) -> pd.DataFrame:
    """Injection-weighted AC@1 / AC@3 per dataset x baseline x condition (and unweighted per record)."""
    w = analyze.attach_units(df.rename(columns={"baseline": "model"}), data_home)
    recs = []
    for (ds, b, cond), g in w.groupby(["dataset", "model", "condition"]):
        recs.append({"dataset": ds, "baseline": b, "condition": cond, "n_records": len(g),
                     "n_injections": g["injection_id"].nunique(),
                     "AC@1": float(np.average(g["ac1"], weights=g["weight"])),
                     "AC@3": float(np.average(g["ac3"], weights=g["weight"])),
                     "AC@1_per_record": float(g["ac1"].mean())})
    return pd.DataFrame(recs)


def main(argv=None) -> pd.DataFrame:
    from .run_grid import load_cfg
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cfg")
    a = ap.parse_args(argv)
    cfg = load_cfg(a.cfg)
    df = pd.DataFrame(rows(cfg))
    out = Path(cfg["out"]).parent
    out.mkdir(parents=True, exist_ok=True)
    df.to_json(out / "baselines.jsonl", orient="records", lines=True)
    from .run_grid import Canon
    tab = table(df, Canon(cfg).data_home)
    tab.to_csv(out / "table_baselines.csv", index=False)
    print(tab.to_string(index=False))
    return tab


if __name__ == "__main__":
    main()
