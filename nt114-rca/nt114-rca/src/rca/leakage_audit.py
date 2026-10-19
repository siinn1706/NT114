"""Text-level near-duplicate audit between query evidence and the retrieval store (evaluation-only).

  python -m rca.leakage_audit <canonical cfg>

For every selected incident and condition, against the same-system entries of the `precedent` store
(the store bound to the configured split's train role, as `run` builds it, minus the query's own split
group, as the model would see it):

- `max_cosine`: the largest TF-IDF cosine (the retrieval tokenizer; fitted on store and query texts);
- `max_jaccard`: the largest Jaccard similarity of the sets of evidence lines;
- `nearest_same_cell`: whether the entry with the largest cosine has the query's (root, fault),
  read from labels in this eval-only module;
- `same_root_reachable`, `nearest_same_root`, `same_root_in_top_k`: the same for the root service alone
  (any fault), over all reachable entries, the nearest one and the `top_k` nearest. Excluding the query's
  split group removes its fault cell, not its root service;
- `same_root_share` and `same_root_in_top_k_chance`: the chance that a similarity-blind pick of one entry,
  or of `top_k` entries without replacement, has the query's root.

Writes `leakage_near_duplicates.jsonl` (flags and similarities only: no service names, no store ids)
and `leakage_near_duplicates_summary.csv` (per split role and condition: records, counts at or above
0.90 / 0.95 / 0.99 for both similarities, the nearest-same-cell share, and the same-root counts next to
their similarity-blind expectations) next to the config's `out`,
which may not be inside the evidence directory.
"""
from __future__ import annotations

import argparse
import json
import math

import numpy as np
import pandas as pd

from .visibility import out_dir

THRESHOLDS = (0.90, 0.95, 0.99)


def _lines(text: str) -> frozenset:
    return frozenset(l.strip() for l in text.splitlines() if l.strip())


def jaccard(a: frozenset, b: frozenset) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def _tfidf(texts: list[str]) -> np.ndarray:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from .retrieve import _TOK
    return TfidfVectorizer(token_pattern=_TOK.pattern, lowercase=True).fit_transform(texts)


def audit(queries: list[dict], store: list[dict], top_k: int = 3) -> list[dict]:
    """queries: {incident_uid, condition, system, split_role, group, cell, text};
    store: {incident_uid, system, group, cell, text}. `cell` = (root, fault), eval-only."""
    if not queries:
        return []
    m = _tfidf([e["text"] for e in store] + [q["text"] for q in queries]) if store else None
    ns = len(store)
    s_lines = [_lines(e["text"]) for e in store]
    out = []
    for i, q in enumerate(queries):
        ok = [j for j, e in enumerate(store) if e["system"] == q["system"] and e["group"] != q["group"]
              and e["incident_uid"] != q["incident_uid"]]
        row = {"incident_uid": q["incident_uid"], "condition": q["condition"], "split_role": q["split_role"],
               "n_store": len(ok), "max_cosine": np.nan, "max_jaccard": np.nan, "nearest_same_cell": None,
               "same_root_reachable": None, "same_root_share": np.nan, "nearest_same_root": None,
               "same_root_in_top_k": None, "same_root_in_top_k_chance": np.nan}
        if ok:
            cos = (m[ns + i] @ m[ok].T).toarray().ravel()
            ql = _lines(q["text"])
            row.update(max_cosine=float(cos.max()), max_jaccard=max(jaccard(ql, s_lines[j]) for j in ok),
                       nearest_same_cell=bool(store[ok[int(cos.argmax())]]["cell"] == q["cell"]))
            same = np.array([store[j]["cell"][0] == q["cell"][0] for j in ok])
            top = np.argsort(-cos, kind="stable")[:top_k]
            n, n_same, k = len(ok), int(same.sum()), min(top_k, len(ok))
            row.update(same_root_reachable=bool(n_same), same_root_share=n_same / n,
                       nearest_same_root=bool(same[int(cos.argmax())]), same_root_in_top_k=bool(same[top].any()),
                       same_root_in_top_k_chance=1 - math.comb(n - n_same, k) / math.comb(n, k))
        out.append(row)
    return out


def summary(df: pd.DataFrame) -> pd.DataFrame:
    recs = []
    for (role, cond), g in df.groupby(["split_role", "condition"], dropna=False):
        r = {"split_role": role, "condition": cond, "n_records": len(g), "n_compared": int(g["max_cosine"].notna().sum())}
        for t in THRESHOLDS:
            r[f"cosine_ge_{t:.2f}"] = int((g["max_cosine"] >= t).sum())
            r[f"jaccard_ge_{t:.2f}"] = int((g["max_jaccard"] >= t).sum())
        r["nearest_same_cell_share"] = float(g["nearest_same_cell"].dropna().astype(float).mean()) \
            if g["nearest_same_cell"].notna().any() else np.nan
        for c in ("same_root_reachable", "nearest_same_root", "same_root_in_top_k"):
            r[c] = int(g[c].dropna().astype(bool).sum())
        r["nearest_same_root_chance"] = round(float(g["same_root_share"].sum()), 2)
        r["same_root_in_top_k_chance"] = round(float(g["same_root_in_top_k_chance"].sum()), 2)
        recs.append(r)
    return pd.DataFrame(recs)


def inputs(cfg: dict) -> tuple[list[dict], list[dict]]:
    from .run_grid import Canon, _store_entries, evidence_dir
    cn = Canon(cfg)
    ev = evidence_dir(cfg)

    def cell(u):
        t = cn.truth(u)
        return (t.root_service, t.fault)

    # the store bound to the split, exactly as `run` builds it (files left by another split are not seen)
    store = [{"incident_uid": e["case_id"], "system": e["system"], "group": cn.group.get(e["case_id"], e["case_id"]),
              "cell": cell(e["case_id"]), "text": e["text"]} for e in _store_entries(cfg, cn)[0]]
    queries = []
    for vc, _ in cn.selected():
        f = ev / f"{vc.case_id}.json"
        if not f.is_file():
            continue
        r = json.loads(f.read_text(encoding="utf-8"))
        u = vc.case_id
        for cond, e in r["conditions"].items():
            queries.append({"incident_uid": u, "condition": cond, "system": r["system"], "split_role": cn.roles.get(u),
                            "group": cn.group.get(u, u), "cell": cell(u), "text": e["text"]})
    return queries, store


def main(argv=None) -> pd.DataFrame:
    from .run_grid import load_cfg
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cfg")
    a = ap.parse_args(argv)
    cfg = load_cfg(a.cfg)
    d = out_dir(cfg)
    queries, store = inputs(cfg)
    df = pd.DataFrame(audit(queries, store, top_k=int(cfg.get("top_k", 3))))
    df.to_json(d / "leakage_near_duplicates.jsonl", orient="records", lines=True)
    tab = summary(df) if len(df) else pd.DataFrame()
    tab.to_csv(d / "leakage_near_duplicates_summary.csv", index=False)
    print(f"{len(queries)} query records, {len(store)} store entries")
    if len(tab):
        print(tab.to_string(index=False))
    return tab


if __name__ == "__main__":
    main()
