"""Kho sự cố cũ + ba kiểu truy hồi: BM25, dense, hybrid (RRF).

Kho chứa bằng chứng ĐẦY ĐỦ modality của các ca khác cùng hệ thống, kèm nhãn
(dịch vụ gốc, loại lỗi) — giống bản post-mortem của sự cố đã xử lý.

Hai chế độ kho (chống rò rỉ nhãn):
  precedent     : chỉ loại chính ca đang hỏi và các ca bên gọi đưa vào `exclude_ids` (cùng nhóm
                  trong manifest chia tập). Không so với nhãn của ca hỏi.
  no_precedent  : ORACLE — bên gọi thêm vào `exclude_ids` mọi ca cùng (dịch vụ gốc, loại lỗi), tính
                  từ `Truth`. Kho không bao giờ đọc nhãn của ca hỏi.
"""
from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np

_TOK = re.compile(r"[a-z][a-z0-9\-]+")


def tokenize(s: str) -> list[str]:
    return _TOK.findall(s.lower())


class BM25:
    def __init__(self, docs: list[list[str]], k1=1.5, b=0.75):
        self.docs, self.k1, self.b = docs, k1, b
        self.avgdl = sum(map(len, docs)) / max(len(docs), 1)
        df = Counter(w for d in docs for w in set(d))
        n = len(docs)
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}
        self.tf = [Counter(d) for d in docs]

    def scores(self, q: list[str]) -> np.ndarray:
        out = np.zeros(len(self.docs))
        for i, (tf, d) in enumerate(zip(self.tf, self.docs)):
            norm = self.k1 * (1 - self.b + self.b * len(d) / self.avgdl)
            out[i] = sum(self.idf.get(w, 0) * tf[w] * (self.k1 + 1) / (tf[w] + norm) for w in q if w in tf)
        return out


class Embedder:
    """sentence-transformers nếu có (khuyến nghị: BAAI/bge-small-en-v1.5), nếu không thì TF-IDF + SVD."""

    def __init__(self, model_name="BAAI/bge-small-en-v1.5"):
        self.model_name = model_name
        try:
            from sentence_transformers import SentenceTransformer
            self.st = SentenceTransformer(model_name, device="cpu")
            self.kind = "st"
        except Exception:
            self.st, self.kind = None, "tfidf-svd"
        self._fit = None

    def fit(self, texts: list[str]):
        if self.kind == "tfidf-svd":
            from sklearn.decomposition import TruncatedSVD
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.vec = TfidfVectorizer(token_pattern=_TOK.pattern, lowercase=True)
            X = self.vec.fit_transform(texts)
            self.svd = TruncatedSVD(n_components=max(2, min(128, X.shape[1] - 1, X.shape[0] - 1)), random_state=0)
            self.svd.fit(X)
            self._fit = True
        return self

    def encode(self, texts: list[str]) -> np.ndarray:
        if self.kind == "st":
            return np.asarray(self.st.encode(texts, normalize_embeddings=True))
        E = self.svd.transform(self.vec.transform(texts))
        return E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-9)


class CaseStore:
    def __init__(self, entries: list[dict], embedder: Embedder | None = None):
        """entries: [{case_id, system, root, fault, text}] — text là bằng chứng đầy đủ modality."""
        self.entries = entries
        self.bm25 = BM25([tokenize(e["text"]) for e in entries])
        self.emb = (embedder or Embedder()).fit([e["text"] for e in entries])
        self.E = self.emb.encode([e["text"] for e in entries])

    def _mask(self, case, mode: str, exclude_ids=frozenset()) -> np.ndarray:
        if mode not in ("precedent", "no_precedent"):
            raise ValueError(mode)
        return np.array([e["system"] == case.system and e["case_id"] != case.case_id and e["case_id"] not in exclude_ids
                         for e in self.entries], dtype=bool)

    def oracle_exclusions(self, root: str, fault: str) -> frozenset:
        """`no_precedent`: ca trong kho cùng (dịch vụ gốc, loại lỗi) với nhãn đúng của ca hỏi (bên gọi truyền Truth)."""
        return frozenset(e["case_id"] for e in self.entries if e["root"] == root and e["fault"] == fault)

    def search(self, query: str, case, method: str, mode: str, k: int = 3, exclude_ids=frozenset()) -> list[dict]:
        ok = self._mask(case, mode, exclude_ids)
        if not ok.any():
            return []
        bm = self.bm25.scores(tokenize(query))
        dn = self.E @ self.emb.encode([query])[0]
        if method == "bm25":
            s = bm
        elif method == "dense":
            s = dn
        elif method == "hybrid":  # Reciprocal Rank Fusion, k=60
            s = np.zeros(len(self.entries))
            for sc in (bm, dn):
                sc = np.where(ok, sc, -np.inf)
                for r, i in enumerate(np.argsort(-sc)):
                    s[i] += 1 / (60 + r + 1)
        else:
            raise ValueError(method)
        s = np.where(ok, s, -np.inf)
        idx = [i for i in np.argsort(-s)[:k] if np.isfinite(s[i])]
        return [{**self.entries[i], "score": float(s[i]), "dense_sim": float(dn[i])} for i in idx]


def format_hits(hits: list[dict], max_chars_each: int = 1200) -> str:
    if not hits:
        return ""
    parts = ["# Similar past incidents (resolved, root cause known)"]
    for j, h in enumerate(hits, 1):
        parts.append(f"### Past incident {j} — root cause: {h['root']} ({h['fault']})\n{h['text'][:max_chars_each]}")
    return "\n\n".join(parts)
