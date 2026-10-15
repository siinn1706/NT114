"""Jev decisions on a finished grid (offline full feedback).

  python -m rca.decide configs/exp/smoke-offline.yaml

For every incident x condition x Jev variant: stage 1 on the primary answer, and both stage-2 states
(after retrieval, after escalation) whenever those arms exist, so every policy path is observed.
Writes `decisions.jsonl` (one row per incident x condition x variant), `jev_raw.jsonl` (verbatim
requests and responses) and `jev_retry.jsonl` (rows with a failed stage, retried on the next run).

Decision inputs are built from the evidence files and named LLM aggregate fields only: a Jev state
never sees `truth`, `truth_ids`, `fault`, `correct`, `rank`, `hits[].root` or `hit_has_truth`.
Jev's `accept` is the policy action `answer` (see `POLICY_ACTION`).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

from . import jev
from .llm import PROMPT_VERSION

# Arms of the action table: (policy action, model role, retrieval method). Optional except `answer`.
ARMS = {"answer": ("primary", "none"), "retrieve": ("primary", "hybrid"), "escalate": ("escalation", "none")}
STAGE2 = {"retrieve": "after_retrieval", "escalate": "after_escalation"}
POLICY_ACTION = {"accept": "answer", "retrieve": "retrieve", "escalate": "escalate", "abstain": "abstain"}
# Datasets without a comparable retrieval store (research design §6): no retrieve action.
NO_RETRIEVE = {"aiops2025", "rca100"}
# Datasets whose evidence text is never sent to the external Jev API until their licence and
# data-processing terms are verified: their states use the J-noevidence form whatever the variant.
# `jev.evidence_cleared: [<dataset>, ...]` lifts this once the terms are recorded.
EVIDENCE_WITHHELD = {"aiops2025", "rca100"}
VARIANTS = {
    "J-full": {"actions": jev.ACTIONS, "drop": ()},
    "J-AA": {"actions": jev.TERMINAL_ACTIONS, "drop": ()},
    "J-noconf": {"actions": jev.ACTIONS, "drop": ("assistant_confidence", "assistant_flagged_insufficient")},
    "J-noevidence": {"actions": jev.ACTIONS, "drop": ("evidence",)},
}
AGG_FIELDS = ("ranking", "conf_verbal", "conf_consensus", "abstain_vote", "next_check", "n_candidates")
FEATS = ["conf_verbal", "conf_consensus", "abstain_vote", "parse_rate"]


def load_grid(path) -> pd.DataFrame:
    with open(path, encoding="utf-8") as f:
        return pd.DataFrame([json.loads(l) for l in f if l.strip()])


def _arm_rows(rows: pd.DataFrame, arm: str, arms: dict) -> pd.DataFrame:
    role, meth = arms[arm]
    g = rows[(rows.model_role == role) & (rows.retrieval == meth)]
    if meth != "none":
        g = g[g.store_mode == "precedent"]
    return g


def select_rows(rows: pd.DataFrame, prompt_version: str, revisions: dict, arms: dict = ARMS) -> dict:
    """{arm: rows indexed by (incident_uid, condition)} for one prompt version and model revision per
    role. Fails on oracle-store rows and on duplicate keys within an arm."""
    if "oracle_store" in rows and rows["oracle_store"].fillna(False).astype(bool).any():
        raise ValueError("grid contains oracle_store (no_precedent) rows: they can never reach a Jev decision; "
                         "run decisions on a grid without them")
    rows = rows[rows.prompt_version == prompt_version]
    out = {}
    for arm in arms:
        g = _arm_rows(rows, arm, arms)
        rev = revisions.get(arms[arm][0])
        if rev is not None:
            g = g[g.model_revision == rev]
        if g.empty:
            if arm == "answer":
                raise ValueError(f"no primary rows for prompt_version={prompt_version!r}")
            continue
        uid = g["incident_uid"].fillna(g["case_id"])
        g = g.assign(incident_uid=uid)
        dup = g.duplicated(["incident_uid", "condition"], keep=False)
        if dup.any():
            ex = g[dup][["model", "incident_uid", "condition"]].head(3).to_dict("records")
            raise ValueError(f"duplicate (incident_uid, condition) rows in arm {arm!r}: {ex}")
        out[arm] = g.set_index(["incident_uid", "condition"])
    return out


def action_table(rows: pd.DataFrame, prompt_version: str = PROMPT_VERSION, revisions: dict | None = None,
                 arms: dict = ARMS) -> pd.DataFrame:
    """Evaluation table keyed (incident_uid, condition): per arm `<a>_ok`, `<a>_tok`, `<a>_conf`
    (consensus of the arm that produced the answer) and `<a>_rank`; visible features of the primary
    answer. Evaluation-only (it holds correctness); Jev states never read it."""
    sel = select_rows(rows, prompt_version, revisions or {}, arms)
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
    for arm in ("retrieve", "escalate"):
        if arm not in sel:
            continue
        g = sel[arm].reindex(t.index)
        missing = g["correct"].isna()
        if missing.any():
            raise ValueError(f"arm {arm!r} lacks {int(missing.sum())} (incident, condition) cells of the primary arm")
        t[f"{arm}_ok"] = g["correct"].astype(bool)
        t[f"{arm}_tok"] = t["answer_tok"] + tok(g)
        t[f"{arm}_conf"] = g["conf_consensus"].astype(float)
        t[f"{arm}_verbal"] = g["conf_verbal"].astype(float)
        t[f"{arm}_rank"] = g["rank"]
        t[f"{arm}_lat"] = t["answer_lat"] + lat(g)
    if "retrieve" in sel:
        t["hit_top_sim"] = sel["retrieve"]["hits"].reindex(t.index).map(lambda h: h[0]["dense_sim"] if h else 0.0)
    return t.reset_index()


def aggregates(sel: dict) -> dict:
    """{(arm, incident_uid, condition): named LLM aggregate fields}: the only grid content a Jev state uses."""
    out = {}
    for arm, g in sel.items():
        for (uid, cond), r in g.iterrows():
            a = {f: r[f] for f in AGG_FIELDS if f in r.index}
            a["n_samples"] = int(r["sampling"]["n"]) if isinstance(r.get("sampling"), dict) else 1
            # similarity of the nearest precedent: a number only, never the precedent's label
            a["top_sim"] = (r["hits"][0]["dense_sim"] if r["hits"] else 0.0) if arm == "retrieve" else None
            out[(arm, uid, cond)] = a
    return out


def decision_inputs(evidence_rec: dict, agg: dict, condition: str, top_sim: float | None,
                    stage: str = "first_look") -> jev.DecisionInputs:
    """Never reads a grid row: evidence text and availability from the evidence file, the rest from
    the named aggregate fields."""
    ev = evidence_rec["conditions"][condition]
    f = ev["features"]
    return jev.DecisionInputs(
        evidence=ev["text"], ranking=list(agg["ranking"]), conf_verbal=float(agg["conf_verbal"]),
        conf_consensus=float(agg["conf_consensus"]), n_samples=int(agg["n_samples"]),
        abstain_vote=float(agg["abstain_vote"]),
        telemetry={k: bool(f.get(f"has_{k}")) for k in ("metrics", "logs", "traces")},
        n_candidates=len(evidence_rec["candidates"]), stage=stage, top_sim=top_sim)


def available_actions(dataset: str, arms_present: set, variant: str) -> tuple[str, ...]:
    acts = [a for a in VARIANTS[variant]["actions"]
            if a in jev.TERMINAL_ACTIONS
            or (a == "retrieve" and "retrieve" in arms_present and dataset not in NO_RETRIEVE)
            or (a == "escalate" and "escalate" in arms_present)]
    return tuple(acts)


def withheld_datasets(jcfg: dict) -> frozenset:
    cleared = set(jcfg.get("evidence_cleared") or ())
    unknown = cleared - EVIDENCE_WITHHELD
    if unknown:
        raise ValueError(f"evidence_cleared names datasets that are not withheld: {sorted(unknown)}")
    return frozenset(EVIDENCE_WITHHELD - cleared)


def check_backends(grid: pd.DataFrame, client: jev.JevClient, jcfg: dict) -> None:
    """Mock Jev is for offline smoke runs: on a grid with any real-LLM row it needs `jev.smoke: true`."""
    real = "backend" in grid and (grid["backend"] != "mock").any()
    if client.backend == "mock" and real and not jcfg.get("smoke"):
        raise ValueError("mock Jev on a grid with real-LLM rows: use the live Jev backend, "
                         "or set jev.smoke: true for a smoke run (never reported)")


def jev_fp(client: jev.JevClient, variant: str, prompt_version: str, revisions: dict,
           withheld: frozenset = frozenset()) -> str:
    blob = json.dumps([jev.JEV_QUESTION_VERSION, client.backend, client.expected_model, variant, prompt_version,
                       sorted(revisions.items()), sorted(withheld)], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def _stage(client, inp, actions, drop, seed) -> tuple[dict, dict]:
    state = jev.build_state(inp, drop)
    res, raw = client.decide(state, jev.build_questions(actions, inp.stage), seed)
    s = res.summary()
    s["state_sha"] = hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()[:16]
    return s, raw


def _client(jcfg: dict, out_dir: Path) -> jev.JevClient:
    return jev.JevClient(model=jcfg.get("model", jev.PINNED_MODEL), backend=jcfg.get("backend", "live"),
                         cache=jcfg.get("cache", str(out_dir / "jev_cache.sqlite")),
                         expected_model=jcfg.get("expected_model"), max_retries=jcfg.get("max_retries", 6))


def run(cfg: dict, client: jev.JevClient | None = None) -> dict:
    jcfg = cfg.get("jev") or {}
    out_dir = Path(cfg["out"]).parent
    client = client or _client(jcfg, out_dir)
    prompt_version = jcfg.get("prompt_version", PROMPT_VERSION)
    revisions = {m.get("role", "primary"): m.get("revision") for m in cfg["models"] if m.get("revision")}
    variants = jcfg.get("variants", ["J-full", "J-AA"])
    unknown = set(variants) - set(VARIANTS)
    if unknown:
        raise ValueError(f"unknown Jev variants {sorted(unknown)}")
    grid = load_grid(cfg["out"])
    check_backends(grid, client, jcfg)
    withheld = withheld_datasets(jcfg)
    sel = select_rows(grid, prompt_version, revisions)
    agg = aggregates(sel)
    ev_dir = Path(cfg.get("evidence_dir", "results/evidence"))
    dec_path, raw_path, retry_path = out_dir / "decisions.jsonl", out_dir / "jev_raw.jsonl", out_dir / "jev_retry.jsonl"
    done = set()
    if dec_path.exists():
        with open(dec_path, encoding="utf-8") as f:
            done = {r["key"] for r in map(json.loads, filter(str.strip, f)) if r["done"]}
    fps = {v: jev_fp(client, v, prompt_version, revisions, withheld) for v in variants}
    arms_present = set(sel)
    counts = {"rows": 0, "skipped_done": 0, "failed": 0}
    retry = []
    evidence_cache: dict[str, dict] = {}
    with open(dec_path, "a", encoding="utf-8", newline="\n") as fd, open(raw_path, "a", encoding="utf-8", newline="\n") as fr:
        for (uid, cond), prim in sorted(sel["answer"].iterrows(), key=lambda x: x[0]):
            if uid not in evidence_cache:
                with open(ev_dir / f"{uid}.json", encoding="utf-8") as f:
                    evidence_cache[uid] = json.load(f)
            rec = evidence_cache[uid]
            sim = agg[("retrieve", uid, cond)]["top_sim"] if ("retrieve", uid, cond) in agg else None
            for v in variants:
                key = f"{uid}|{cond}|{v}|{fps[v]}"
                if key in done:
                    counts["skipped_done"] += 1
                    continue
                no_ev = prim["dataset"] in withheld
                drop = tuple(dict.fromkeys(VARIANTS[v]["drop"] + (("evidence",) if no_ev else ())))
                acts = available_actions(prim["dataset"], arms_present, v)
                row = {"key": key, "incident_uid": uid, "condition": cond, "dataset": prim["dataset"],
                       "split_id": prim.get("split_id"), "split_role": prim.get("split_role"), "variant": v,
                       "available_actions": list(acts), "jev_question_version": jev.JEV_QUESTION_VERSION,
                       "jev_fp": fps[v], "jev_backend": client.backend, "prompt_version": prompt_version,
                       "evidence_withheld": no_ev or "evidence" in VARIANTS[v]["drop"]}
                s_sim = sim if "retrieve" in acts else None
                stages = {"stage1": (decision_inputs(rec, agg[("answer", uid, cond)], cond, s_sim), acts)}
                for arm in ("retrieve", "escalate"):
                    if arm in acts:
                        a2 = agg[(arm, uid, cond)]
                        stages[f"stage2_{arm}"] = (decision_inputs(rec, a2, cond, s_sim, jev.STAGES[1 if arm == "retrieve" else 2]),
                                                   jev.TERMINAL_ACTIONS)
                for name, (inp, a) in stages.items():
                    s, raw = _stage(client, inp, a, drop, f"{uid}|{cond}|{inp.stage}")
                    row[name] = s
                    fr.write(json.dumps({**raw, "incident_uid": uid, "condition": cond, "variant": v, "stage": name}) + "\n")
                row["done"] = all(row[n]["status"] == "ok" for n in stages)
                fd.write(json.dumps(row) + "\n")
                counts["rows"] += 1
                if not row["done"]:
                    counts["failed"] += 1
                    retry.append({"key": key, "incident_uid": uid, "condition": cond, "variant": v,
                                  "status": {n: row[n]["status"] for n in stages}})
    with open(retry_path, "w", encoding="utf-8", newline="\n") as f:
        for r in retry:
            f.write(json.dumps(r) + "\n")
    print(f"decisions: {counts}")
    return counts


def load_decisions(path) -> pd.DataFrame:
    """Latest row per key; `done=False` rows remain (fail-closed at analysis time)."""
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(l) for l in f if l.strip()]
    df = pd.DataFrame(rows)
    return df.drop_duplicates("key", keep="last").reset_index(drop=True) if len(df) else df


if __name__ == "__main__":
    from .run_grid import load_cfg
    run(load_cfg(sys.argv[1]))
