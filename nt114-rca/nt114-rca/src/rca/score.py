"""Scoring (evaluation-only zone): rank of the true root, set-scored labels, eval-unit weights.

A ranking hits when its entry is the primary root service, or, for records labelled only with a set
of root services (AIOps2025 multi-service labels), any member of `Truth.root_ids`. A miss has rank
max(n_candidates, RANK_CAP) + 1: it lies beyond the top-RANK_CAP window, so a short wrong ranking never
counts for AC@1..AC@5 or MRR@5, however few candidates the incident has. An empty ranking (every sample
failed to parse) is a miss with `parse_failed` set.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .data import Truth
from .metrics import RANK_CAP


def truth_ids(truth: Truth) -> tuple[str, ...]:
    """Services that count as a hit: the primary root, else the label's root set."""
    return (truth.root_service,) if truth.root_service is not None else tuple(truth.root_ids)


def correctness(ranking: list[str], truth: Truth, n_candidates: int) -> dict:
    ids = set(truth_ids(truth))
    rank = next((i + 1 for i, s in enumerate(ranking) if s in ids), max(n_candidates, RANK_CAP) + 1)
    return {"rank": rank, "correct_at_1": rank == 1, "correct_at_3": rank <= 3,
            "set_scored": truth.root_service is None, "parse_failed": not ranking}


OUTCOMES = ("not_applicable", "execution_error", "wrong", "correct")


def outcome(correct_at_1: bool, parse_failed: bool, applicable: bool = True) -> str:
    """Result class of one answer: no evidence path applied, no parseable answer, wrong or correct top-1.
    Every class stays in the denominator."""
    if not applicable:
        return "not_applicable"
    if parse_failed:
        return "execution_error"
    return "correct" if correct_at_1 else "wrong"


UNIT_COLUMNS =["incident_uid", "weight", "injection_id", "representative", "cov_logs", "cov_traces", "excluded"]


def units(data_home: Path, dataset: str) -> pd.DataFrame:
    """One row per accepted record of `dataset` from `reports/eval-units-<dataset>.json`."""
    path = Path(data_home) / "reports" / f"eval-units-{dataset}.json"
    with open(path, encoding="utf-8") as f:
        rep = json.load(f)
    rows = [{"incident_uid": u, "weight": r["weight"], "injection_id": r["injection_id"],
             "representative": r["representative"], "cov_logs": r["coverage"]["logs"]["cause"],
             "cov_traces": r["coverage"]["traces"]["cause"], "excluded": r["excluded_from_primary"]}
            for u, r in sorted(rep["units"].items())]
    return pd.DataFrame(rows, columns=UNIT_COLUMNS)


def default_units(uids) -> pd.DataFrame:
    """Every record its own injection (used when a dataset has no eval-units report, e.g. synthetic)."""
    uids = sorted(set(uids))
    return pd.DataFrame({"incident_uid": uids, "weight": 1.0, "injection_id": uids, "representative": True,
                         "cov_logs": "covered", "cov_traces": "covered", "excluded": None}, columns=UNIT_COLUMNS)
