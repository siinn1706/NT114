"""Lớp quyết định chạy OFFLINE trên kết quả của lưới (không gọi lại LLM, trừ Jev).

Với mỗi sự cố (case × điều kiện modality), lớp quyết định chọn một hành động:
  answer        : trả lời bằng mô hình cơ sở, không tra cứu
  retrieve      : tra ca cũ (hybrid, kho precedent) rồi trả lời
  escalate      : chuyển lên mô hình lớn (nếu lưới có 2 mô hình)
  abstain       : báo "chưa đủ dữ liệu, hãy kiểm tra X"

Vì lưới đã chạy MỌI hành động cho MỌI ca nên đánh giá phản thực tế là chính xác (full feedback).
Đánh giá công bằng: huấn luyện trên 2 hệ thống, kiểm tra trên hệ thống còn lại (leave-one-system-out).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ACTIONS = ("answer", "retrieve", "escalate", "abstain")
FEATS = ["conf_verbal", "conf_consensus", "abstain_vote", "has_metrics", "has_logs", "has_traces",
         "max_metric_z", "n_flagged_services", "z_gap_top2", "n_candidates", "hit_top_sim"]


# ---------------------------------------------------------------- bảng hành động
def action_table(rows: pd.DataFrame, base_model: str, big_model: str | None = None,
                 retrieval: str = "hybrid", store_mode: str = "precedent", oracle: bool = False) -> pd.DataFrame:
    """Mỗi dòng = một sự cố; cột = kết quả của từng hành động + đặc trưng nhìn thấy TRƯỚC khi quyết định.

    `hit_top_sim` vào trạng thái của Jev, nên mặc định lấy từ kho `precedent` (không dùng nhãn).
    Kho `no_precedent` loại ca theo nhãn đúng của ca hỏi; chỉ dùng cho ablation oracle với `oracle=True`."""
    if store_mode == "no_precedent" and not oracle:
        raise ValueError("store_mode='no_precedent' masks by the query's true label; pass oracle=True for the oracle ablation")
    b = rows[(rows.model == base_model) & (rows.retrieval == "none")].set_index(["case_id", "condition"])
    r = rows[(rows.model == base_model) & (rows.retrieval == retrieval) & (rows.store_mode == store_mode)]
    if r.empty:
        raise ValueError(f"no {retrieval!r} rows with store_mode={store_mode!r} for {base_model!r}; "
                         f"available: {sorted(rows.store_mode.dropna().unique())}")
    r = r.set_index(["case_id", "condition"])
    t = pd.DataFrame(index=b.index)
    t["system"] = b["system"]
    feats = pd.json_normalize(b["features"].tolist()).set_index(b.index)
    for f in FEATS:
        if f in b:
            t[f] = b[f].astype(float)
        elif f in feats:
            t[f] = feats[f].astype(float)
    t["hit_top_sim"] = r["hits"].map(lambda h: h[0]["dense_sim"] if h else 0.0).reindex(t.index).fillna(0.0)
    tok = lambda df: (df["prompt_tokens"].fillna(0) + df["completion_tokens"].fillna(0)).astype(float)
    t["answer_ok"], t["answer_tok"], t["answer_conf"] = b["correct"].astype(bool), tok(b), b["conf_consensus"]
    t["retrieve_ok"] = r["correct"].reindex(t.index).astype("boolean").fillna(False).astype(bool)
    t["retrieve_tok"] = t["answer_tok"] + tok(r).reindex(t.index).fillna(0)
    t["retrieve_conf"] = r["conf_consensus"].reindex(t.index).fillna(0)
    if big_model:
        g = rows[(rows.model == big_model) & (rows.retrieval == "none")].set_index(["case_id", "condition"])
        t["escalate_ok"] = g["correct"].reindex(t.index).astype("boolean").fillna(False).astype(bool)
        t["escalate_tok"] = t["answer_tok"] + tok(g).reindex(t.index).fillna(0)
        t["escalate_conf"] = g["conf_consensus"].reindex(t.index).fillna(0)
    return t.reset_index()


def reward(ok: bool, action: str, tokens: float, wrong_penalty: float = 2.0, tok_cost: float = 0.01) -> float:
    """Đúng +1 · trả lời sai -wrong_penalty (đưa kỹ sư đi sai hướng) · từ chối 0 · trừ chi phí mỗi 1k token."""
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
    for act in ("answer", "retrieve", "escalate"):
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
    """chosen: hành động cho từng dòng của t. `weights`: trọng số eval-unit (1 / số bản ghi của lần tiêm).
    CWA dùng độ tự tin của nhánh tạo ra câu trả lời cuối cùng."""
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


# ---------------------------------------------------------------- chính sách
def fixed(t, action):
    return pd.Series(action, index=t.index)


def threshold_policy(t, t_retrieve, t_abstain, conf="conf_consensus"):
    """Tự tin >= t_retrieve: trả lời. Thấp hơn: tra cứu; sau tra cứu vẫn < t_abstain: từ chối."""
    out = []
    for _, r in t.iterrows():
        if r[conf] >= t_retrieve:
            out.append("answer")
        elif r["retrieve_conf"] >= t_abstain:
            out.append("retrieve")
        else:
            out.append("abstain")
    return pd.Series(out, index=t.index)


def tune_threshold(train, **rw):
    grid = np.round(np.arange(0.2, 1.01, 0.1), 2)
    best = max(((a, b) for a in grid for b in grid),
               key=lambda ab: evaluate(train, threshold_policy(train, *ab), **rw)["reward"])
    return best


def learned_policy(train, test, actions=("answer", "retrieve", "abstain"), **rw):
    """Bandit offline với phản hồi đầy đủ = hồi quy phần thưởng cho từng hành động, chọn argmax.
    (Trên dữ liệu log có đủ mọi hành động, đây là dạng cost-sensitive classification.)"""
    from sklearn.ensemble import GradientBoostingRegressor
    X_tr, X_te = train[FEATS].fillna(0).values, test[FEATS].fillna(0).values
    preds = {}
    for a in actions:
        if a == "abstain":
            preds[a] = np.array([reward(False, "abstain", x, **rw) for x in test["answer_tok"]])
            continue
        y = [reward(bool(r[f"{a}_ok"]), a, r[f"{a}_tok"], **rw) for _, r in train.iterrows()]
        m = GradientBoostingRegressor(n_estimators=150, max_depth=2, learning_rate=0.05, random_state=0)
        preds[a] = m.fit(X_tr, y).predict(X_te)
    P = np.vstack([preds[a] for a in actions]).T
    return pd.Series([actions[i] for i in P.argmax(1)], index=test.index)


def leave_one_system_out(t: pd.DataFrame, **rw) -> pd.DataFrame:
    res = []
    has_big = "escalate_ok" in t
    for sys_ in sorted(t["system"].unique()):
        tr, te = t[t.system != sys_], t[t.system == sys_]
        pols = {"always_answer": fixed(te, "answer"), "always_retrieve": fixed(te, "retrieve")}
        if has_big:
            pols["always_escalate"] = fixed(te, "escalate")
        a, b = tune_threshold(tr, **rw)
        pols[f"threshold({a},{b})"] = threshold_policy(te, a, b)
        acts = ("answer", "retrieve", "escalate", "abstain") if has_big else ("answer", "retrieve", "abstain")
        pols["learned"] = learned_policy(tr, te, acts, **rw)
        if "jev_action" in te:
            pols["jev"] = te["jev_action"]
        for name, ch in pols.items():
            res.append({"test_system": sys_, "policy": name, **evaluate(te, ch, **rw)})
    return pd.DataFrame(res)


# ---------------------------------------------------------------- Jev policies (decisions from `rca.decide`)
def _decision_rows(t: pd.DataFrame, decisions: pd.DataFrame, variant: str) -> pd.DataFrame:
    d = decisions[decisions.variant == variant].drop_duplicates(["incident_uid", "condition"], keep="last")
    d = d.set_index(["incident_uid", "condition"])
    idx = pd.MultiIndex.from_frame(t[["incident_uid", "condition"]])
    missing = ~idx.isin(d.index)
    if missing.any():
        raise ValueError(f"{int(missing.sum())} rows have no {variant} decision")
    return d.loc[idx]


def jev_policy(t: pd.DataFrame, decisions: pd.DataFrame, variant: str = "J-full", floor: float | None = None):
    """Final action per row: stage-1 choice; after retrieve/escalate the stage-2 accept/abstain. Any
    failed stage on the path gives `abstain` (fail-closed) and `flagged`. `floor`: J-floor, a stage-1
    accept with Jev confidence below it becomes abstain."""
    from .decide import POLICY_ACTION
    d = _decision_rows(t, decisions, variant)
    acts, flagged = [], []
    for _, r in d.iterrows():
        s1 = r["stage1"]
        if s1["status"] != "ok":
            acts.append("abstain"); flagged.append(True)
            continue
        a = POLICY_ACTION[s1["action"]]
        if a == "answer" and floor is not None and (s1["confidence"] or 0) < floor:
            a = "abstain"
        if a in ("retrieve", "escalate"):
            s2 = r.get(f"stage2_{a}")
            if not isinstance(s2, dict) or s2["status"] != "ok":
                acts.append("abstain"); flagged.append(True)
                continue
            a = a if s2["action"] == "accept" else "abstain"
        acts.append(a); flagged.append(False)
    return pd.Series(acts, index=t.index), pd.Series(flagged, index=t.index)


def jev_scores(t: pd.DataFrame, decisions: pd.DataFrame, variant: str = "J-full") -> dict[str, pd.Series]:
    """Stage-1 Jev P(accept) and the `supported` noul, for risk-coverage and error detection (NaN on failure)."""
    d = _decision_rows(t, decisions, variant)
    pa = [r["stage1"]["probabilities"].get("accept", np.nan) if r["stage1"]["status"] == "ok" else np.nan for _, r in d.iterrows()]
    sp = [r["stage1"]["supported"] if r["stage1"]["status"] == "ok" else np.nan for _, r in d.iterrows()]
    return {"p_accept": pd.Series(pa, index=t.index, dtype=float), "supported": pd.Series(sp, index=t.index, dtype=float)}


def tune_jev_floor(t_dev: pd.DataFrame, decisions_dev: pd.DataFrame, variant: str = "J-full", **rw) -> float:
    """J-floor: the stage-1 confidence floor maximising the utility on DEV (labels of DEV only)."""
    grid = np.round(np.arange(0.0, 1.0, 0.05), 2)
    return float(max(grid, key=lambda f: evaluate(t_dev, jev_policy(t_dev, decisions_dev, variant, f)[0], **rw)["reward"]))


# ---------------------------------------------------------------- controls (research design §5)
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


def route_matched_random(t: pd.DataFrame, reference: pd.Series, draws: int = 1000, seed: int = 0) -> list[pd.Series]:
    """R1: J's final actions reassigned to random rows (same count of every action)."""
    rng = np.random.default_rng(seed)
    a = reference.reindex(t.index).to_numpy()
    return [pd.Series(rng.permutation(a), index=t.index) for _ in range(draws)]


def route_matched_consensus(t: pd.DataFrame, reference: pd.Series, conf: str = "answer_conf",
                            draws: int = 1000, seed: int = 0) -> list[pd.Series]:
    """R2: the lowest-consensus rows get abstain, then escalate, then retrieve, at J's counts; ties at random."""
    rng = np.random.default_rng(seed)
    counts = reference.value_counts()
    sc = t[conf].to_numpy(float)
    out = []
    for _ in range(draws):
        order = np.lexsort((rng.random(len(sc)), sc))      # ascending confidence
        acts = np.full(len(sc), "answer", dtype=object)
        pos = 0
        for a in ("abstain", "escalate", "retrieve"):
            n = int(counts.get(a, 0))
            acts[order[pos:pos + n]] = a
            pos += n
        out.append(pd.Series(acts, index=t.index))
    return out


def evaluate_draws(t: pd.DataFrame, draws: list[pd.Series], weights=None, **rw) -> dict:
    """Mean of every numeric metric over the draws of a randomised control."""
    res = [evaluate(t, c, weights, **rw) for c in draws]
    keys = [k for k, v in res[0].items() if isinstance(v, float)]
    return {**{k: float(np.nanmean([r[k] for r in res])) for k in keys}, "draws": len(draws)}


def oracle_policy(t: pd.DataFrame) -> pd.Series:
    """O (analysis only, reads labels): the first correct arm in cost order, else abstain."""
    out = pd.Series("abstain", index=t.index, dtype=object)
    for a in ("escalate", "retrieve", "answer"):
        if f"{a}_ok" in t:
            out[t[f"{a}_ok"].astype(bool)] = a
    return out
