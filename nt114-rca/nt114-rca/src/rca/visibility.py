"""Evidence visibility audit (evaluation-only): is the true root named in the evidence summary?

  python -m rca.visibility <cfg> [--roles train val test]

For every incident a canonical config selects (its split roles, or `--roles`) that has an evidence
file from `run_grid prepare`, and every condition in that file:

- `in_candidates`: a true root is in the prompt's candidate list (candidate-set membership);
- `named`: a true root is named explicitly in the evidence text, as a service line (`- <svc>: ...`)
  in any block or as an endpoint of a slow call edge (`- a -> b: ...`);
- `named_metrics` / `named_logs` / `named_traces` / `named_trace_edge`: where it is named, and
  `has_<modality>_block` whether that block exists at all;
- `token_anywhere`: a looser check, the root id as a word anywhere in the text (e.g. inside a
  quoted log template). Not counted as `named`.

Being named is a property of the summary, not a precondition of a correct answer: the model ranks
the whole candidate list and can pick an unnamed root.

Reads labels, so it runs offline after `prepare` and nothing it writes reaches a prompt. Writes `evidence_visibility.jsonl` (flags only, no service names),
`table_evidence_visibility.csv` (by dataset x split x condition; per record and injection-weighted) and
`visibility_counts.json` (incidents of the roles, exclusions with reasons, skipped conditions) next to
the config's `out`, never into the evidence directory.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from . import analyze, score
from .data import canon

BLOCKS = {"Metrics": "metrics", "Logs": "logs", "Traces": "traces"}
_SVC = re.compile(r"^- ([a-z0-9][a-z0-9\-]*):", re.M)          # as run_grid._EV_LINE
_EDGE = re.compile(r"^- ([a-z0-9][a-z0-9\-]*) -> ([a-z0-9][a-z0-9\-]*):", re.M)
FLAGS = ["in_candidates", "named", "named_metrics", "named_logs", "named_traces", "named_trace_edge",
         "has_metrics_block", "has_logs_block", "has_traces_block", "token_anywhere"]


def split_blocks(text: str) -> dict[str, str]:
    """{metrics|logs|traces: block text} for the `## <Name> ...` blocks of an evidence text."""
    out = {}
    for part in re.split(r"(?m)^(?=## )", text):
        head = part[3:].split(None, 1)[0] if part.startswith("## ") and len(part) > 3 else ""
        if head in BLOCKS:
            out[BLOCKS[head]] = part
    return out


def visibility(text: str, roots, candidates) -> dict:
    """Flags for one evidence text. `roots`: the services that count as the truth (primary root, or
    the label's root set); both the id and its `canon()` form are matched."""
    names = {n for r in roots for n in (r, canon(r)) if n}
    blocks = split_blocks(text)
    rec = {"in_candidates": bool(set(roots) & set(candidates))}
    for mod in BLOCKS.values():
        b = blocks.get(mod, "")
        rec[f"has_{mod}_block"] = mod in blocks
        rec[f"named_{mod}"] = bool(names & set(_SVC.findall(b)))
    edges = {s for pair in _EDGE.findall(blocks.get("traces", "")) for s in pair}
    rec["named_trace_edge"] = bool(names & edges)
    rec["named"] = bool(names & set(_SVC.findall(text))) or rec["named_trace_edge"]
    rec["token_anywhere"] = any(re.search(rf"(?<![a-z0-9\-]){re.escape(n)}(?![a-z0-9\-])", text) for n in names)
    named = set(_SVC.findall(text)) | edges
    rec["n_named_services"] = len(named)
    rec["n_named_outside_candidates"] = len(named - set(candidates))
    rec["n_candidates"] = len(candidates)
    return rec


def rows(cfg: dict) -> tuple[list[dict], dict]:
    """Records per (incident, condition) plus an account of every incident of the selected roles that
    yields no record. Anything unexpected (stale evidence, a condition set other than the applicable one,
    an empty truth) raises instead of being dropped."""
    from .run_grid import NONROOT_EV, Canon, _check_current, evidence_dir
    cn = Canon(cfg)
    ev_dir = evidence_dir(cfg)
    roles = set(cn.split_roles())
    in_roles = [u for u, r in cn.roles.items() if r in roles] if cn.split_dir else None
    not_full = {u: cn.matrix.get(u, {}).get("conditions", {}).get("full", {}).get("reason", "not in condition matrix")
                for u in in_roles or [] if not cn.matrix.get(u, {}).get("conditions", {}).get("full", {}).get("applicable")}
    sel = cn.selected()
    out, missing, skipped = [], [], []
    for vc, inc in sel:
        f = ev_dir / f"{vc.case_id}.json"
        if not f.is_file():
            missing.append(vc.case_id)
            continue
        rec = json.loads(f.read_text(encoding="utf-8"))
        _check_current(rec, cn.evidence_fp(vc.case_id), f)
        want = cn.conditions(vc.case_id)
        skip = rec.get("skipped", [])
        if list(rec["conditions"]) != [c for c in want if c not in skip] or set(skip) - {NONROOT_EV}:
            raise RuntimeError(f"{f}: conditions {list(rec['conditions'])} (skipped {skip}) != applicable {want}: "
                               "run `prepare` with this config")
        skipped += [(vc.case_id, c) for c in skip]
        tr = cn.truth(vc.case_id)
        roots = score.truth_ids(tr)
        if not roots:
            raise RuntimeError(f"{vc.case_id}: label has no root service")
        base = {"incident_uid": vc.case_id, "dataset": vc.dataset, "system": vc.system, "split_id": cn.split_id,
                "split_role": cn.roles.get(vc.case_id), "set_scored": tr.root_service is None,
                "label_granularity": tr.granularity, "n_roots": len(roots)}
        for cond, ev in rec["conditions"].items():
            out.append({**base, "condition": cond, "same_as_full": rec.get("same_as_full", {}).get(cond),
                        "truncated": ev["text"].endswith("[truncated]"),
                        **visibility(ev["text"], roots, rec["candidates"])})
    counts = {"split_id": cn.split_id, "roles": sorted(roles),
              "in_roles": len(in_roles) if in_roles is not None else None,
              "excluded_full_not_applicable": dict(sorted(not_full.items())),
              "selected": len(sel), "missing_evidence": sorted(missing),
              "skipped_conditions": [f"{u}|{c}" for u, c in skipped],
              "requested_conditions": list(cfg["conditions"])}
    return out, counts


def table(df: pd.DataFrame, data_home: Path | None = None) -> pd.DataFrame:
    """Rates per dataset x split x condition: per record and injection-weighted (eval-units)."""
    w = analyze.attach_units(df, data_home)
    keys = ["dataset", "split_id", "split_role", "condition"]
    recs = []
    for k, g in w.groupby(keys, dropna=False):
        r = dict(zip(keys, k))
        r.update(n_records=len(g), n_injections=g["injection_id"].nunique(),
                 mean_named_services=float(g["n_named_services"].mean()), mean_candidates=float(g["n_candidates"].mean()),
                 records_named_outside_candidates=int((g["n_named_outside_candidates"] > 0).sum()),
                 truncated_per_record=float(g["truncated"].mean()))
        for f in FLAGS:
            v = g[f].astype(float)
            r[f] = float((v * g["weight"]).sum() / g["weight"].sum())
            r[f"{f}_per_record"] = float(v.mean())
        r["named_given_candidate"] = float(g.loc[g["in_candidates"], "named"].mean()) if g["in_candidates"].any() else float("nan")
        recs.append(r)
    return pd.DataFrame(recs)


def out_dir(cfg: dict) -> Path:
    from .run_grid import evidence_dir
    d = Path(cfg["out"]).parent.resolve()
    ev = evidence_dir(cfg).resolve()
    if d == ev or ev in d.parents:
        raise ValueError(f"visibility outputs hold label-derived flags: {d} must not be inside the evidence dir {ev}")
    d.mkdir(parents=True, exist_ok=True)
    return d


def main(argv=None) -> pd.DataFrame:
    from .run_grid import Canon, is_canonical, load_cfg
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cfg")
    ap.add_argument("--roles", nargs="+", help="split roles to audit (default: the config's split_role(s))")
    a = ap.parse_args(argv)
    cfg = load_cfg(a.cfg)
    if not is_canonical(cfg):
        raise SystemExit("rca.visibility needs a canonical config (source: canonical)")
    if a.roles:
        cfg["split_roles"] = a.roles
    d = out_dir(cfg)
    recs, counts = rows(cfg)
    df = pd.DataFrame(recs)
    df.to_json(d / "evidence_visibility.jsonl", orient="records", lines=True)
    tab = table(df, Canon(cfg).data_home) if len(df) else pd.DataFrame()
    tab.to_csv(d / "table_evidence_visibility.csv", index=False)
    (d / "visibility_counts.json").write_text(json.dumps(counts, indent=1), encoding="utf-8")
    print(f"incidents in roles {counts['in_roles']}, excluded (full not applicable) "
          f"{len(counts['excluded_full_not_applicable'])}, selected {counts['selected']}, "
          f"without evidence file {len(counts['missing_evidence'])}, skipped conditions "
          f"{len(counts['skipped_conditions'])}, records {len(df)}")
    if len(tab):
        cols = ["dataset", "split_role", "condition", "n_records", "n_injections", "in_candidates", "named",
                "named_metrics", "named_logs", "named_traces", "named_trace_edge", "token_anywhere"]
        print(tab[cols].round(3).to_string(index=False))
    return tab


if __name__ == "__main__":
    main()
