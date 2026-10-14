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

import json
import os
import urllib.request

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


def evaluate(t: pd.DataFrame, chosen: pd.Series, **rw) -> dict:
    """chosen: hành động cho từng dòng của t."""
    ok, tok, rew, conf = [], [], [], []
    for i, a in chosen.items():
        row = t.loc[i]
        if a == "abstain":
            ok.append(np.nan); tok.append(row["answer_tok"]); conf.append(np.nan)
        else:
            ok.append(bool(row[f"{a}_ok"])); tok.append(row[f"{a}_tok"]); conf.append(row[f"{a}_conf"])
        rew.append(reward(ok[-1] if a != "abstain" else False, a, tok[-1], **rw))
    ok = np.array(ok, float)
    answered = ~np.isnan(ok)
    conf = np.array(conf, float)
    return {
        "coverage": float(answered.mean()),
        "acc_answered": float(np.nanmean(ok)) if answered.any() else float("nan"),
        "confident_wrong_per_100": float(100 * np.mean(answered & (ok == 0) & (np.nan_to_num(conf) >= 0.8))),
        "wrong_per_100": float(100 * np.mean(answered & (ok == 0))),
        "abstain_per_100": float(100 * np.mean(~answered)),
        "tokens_per_incident": float(np.mean(tok)),
        "reward": float(np.mean(rew)),
        "actions": chosen.value_counts().to_dict(),
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


# ---------------------------------------------------------------- Jev (TypeSafe)
def jev_payload(row: pd.Series, evidence_text: str, answer: str) -> dict:
    """Tạo yêu cầu cho Jev: state + một câu hỏi kiểu choice.
    CẦN KIỂM TRA tên trường của câu hỏi choice (vd 'options') với docs.typesafe.ai trước khi chạy."""
    state = {
        "evidence": evidence_text[:6000],
        "assistant_first_answer": answer,
        "assistant_confidence": round(float(row["conf_consensus"]), 2),
        "telemetry_available": {k: bool(row[f"has_{k}"]) for k in ("metrics", "logs", "traces")},
        "similar_past_incident_similarity": round(float(row["hit_top_sim"]), 2),
    }
    return {
        "state": state,
        "questions": {
            "action": {
                "type": "choice",
                "instructions": "An on-call engineer will act on the assistant's root-cause answer. "
                                "Choose the next step that minimises the risk of sending the engineer to the wrong service.",
                "criteria": "answer = evidence clearly supports the first answer; retrieve = look up similar past "
                            "incidents first; abstain = evidence is insufficient, ask the engineer to check more data.",
                "options": ["answer", "retrieve", "abstain"],  # TODO: xác nhận tên trường
            }
        },
    }


def jev_call(payload: dict) -> dict:
    """Gửi tới endpoint Jev. Đặt JEV_URL và JEV_TOKEN trong biến môi trường (Cloudflare Workers AI hoặc API TypeSafe)."""
    url, token = os.environ.get("JEV_URL"), os.environ.get("JEV_TOKEN")
    if not url or not token:
        raise RuntimeError("Đặt JEV_URL và JEV_TOKEN trước khi gọi Jev")
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())  # lưu nguyên văn, kể cả trường version của mô hình
