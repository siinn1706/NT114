"""BARO-style metric baseline in NumPy (evaluation-only, CPU). A reimplementation, not RCAEval code.

Reference: RCAEval at commit 259ea4167160256a74ad30004aa3d96a998c846e (github.com/phamquiluan/RCAEval).
Each step below names the reference file and function it reproduces; NT114 never imports RCAEval.

Until every reference-fixture test in `tests/test_baro.py` passes, outputs carry the name
`BARO-style (unvalidated)` (`NAME`) and the baseline is never called B2.

Steps (input: the wide metric frame of `legacy_view.legacy_telemetry`, a `time` column in seconds
plus one `<entity>_<metric>` column per series, and the visible inject time):

0. `main.py` reads `data.csv` with `pandas.read_csv` (default C parser). The frame passes through
   `to_csv` / `read_csv` the same way: repeated headers become `x`, `x.1`, ..., and values take the
   parser's default float conversion, which can differ from the stored value in the last bits. That
   difference is enough to change `drop_constant` or a near-tie, so it is reproduced, not avoided.
1. `main.py` (script body of `process`): drop a repeated `time.1` header; drop columns ending in
   `_latency-50`; optionally keep only `ts-*` columns (`ts_only`, the `mm-tt` / `torai-TT` branch,
   off for RCAEval RE1-RE3 directory names); replace +-inf with NaN; forward-fill, then fill 0.
2. `main.py`: inject time = visible inject time + `tdelta` (default 0); keep the last
   `length * 60 // 2` rows before it and the first `length * 60 // 2` rows from it (`length` 20).
3. `main.py`: rename `<x>_latency-90` to `<x>_latency`.
4. `RCAEval/e2e/baro.py::baro`: split at the inject time (`time < t` normal, `time >= t` anomalous).
5. `RCAEval/io/time_series.py::preprocess` with a dataset name and `dk_select_useful=False`, applied
   to each window separately: `drop_time` (`time.1`, then `time` or `Time`), `drop_constant` (keep a
   column when any value differs from its first row), `convert_mem_mb` (columns ending `_mem` / 1e6).
6. `baro`: keep the columns present in both windows, in normal-window order.
7. `baro`: per column, `sklearn.preprocessing.RobustScaler` fitted on the normal window (center =
   median, scale = 75th - 25th percentile with linear interpolation; a scale below 10 * float64 eps
   becomes 1.0), applied to the anomalous window; the score is the maximum scaled value.
8. `baro`: stable sort by score, descending (ties keep column order).
9. `main.py` (evaluation): service = column name up to the first `_`, with `-db` removed; keep each
   service's first occurrence.
"""
from __future__ import annotations

import io

import numpy as np
import pandas as pd

NAME = "BARO-style (unvalidated)"
REFERENCE_COMMIT = "259ea4167160256a74ad30004aa3d96a998c846e"
_EPS10 = 10 * np.finfo(np.float64).eps


def as_read_csv(data: pd.DataFrame) -> pd.DataFrame:
    """Step 0: the frame as `pandas.read_csv` returns it from a CSV file of `data`."""
    return pd.read_csv(io.StringIO(data.to_csv(index=False, lineterminator="\n")))


def prepare_frame(data: pd.DataFrame, inject_time: float, length: int = 20, tdelta: int = 0,
                  ts_only: bool = False) -> tuple[pd.DataFrame, float]:
    """Steps 1-3: the windowed, filled frame the reference passes to `baro`, and the inject time."""
    d = as_read_csv(data)
    d = d.drop(columns=["time.1"]) if "time.1" in d else d
    d = d.loc[:, ~d.columns.str.endswith("_latency-50")]
    if ts_only:
        t = d["time"]
        d = d.loc[:, d.columns.str.startswith("ts-")].copy()
        d["time"] = t
    d = d.replace([np.inf, -np.inf], np.nan).ffill().fillna(0)
    t = inject_time + tdelta
    n = length * 60 // 2
    d = pd.concat([d[d["time"] < t].tail(n), d[d["time"] >= t].head(n)], ignore_index=True)
    return d.rename(columns={c: c.replace("_latency-90", "_latency") for c in d.columns if c.endswith("_latency-90")}), t


def _preprocess(w: pd.DataFrame) -> pd.DataFrame:
    """Step 5 on one window."""
    if "time.1" in w:
        w = w.drop(columns=["time.1"])
    if "time" in w:
        w = w.drop(columns=["time"])
    elif "Time" in w:
        w = w.drop(columns=["Time"])
    w = w.loc[:, (w != w.iloc[0]).any()]
    mem = [c for c in w.columns if c.endswith("_mem")]
    if mem:
        w = w.astype({c: float for c in mem})
        w[mem] = w[mem] / 1e6
    return w


def metric_scores(frame: pd.DataFrame, inject_time: float) -> list[tuple[str, float]]:
    """Steps 4-8 on a prepared frame: [(column, score)] sorted by score, descending, ties in column order."""
    normal = _preprocess(frame[frame["time"] < inject_time])
    anomal = _preprocess(frame[frame["time"] >= inject_time])
    cols = [c for c in normal.columns if c in anomal.columns]
    if not cols:
        return []
    a = normal[cols].to_numpy(dtype=float)
    b = anomal[cols].to_numpy(dtype=float)
    center = np.nanmedian(a, axis=0)
    q25, q75 = np.nanpercentile(a, [25, 75], axis=0)
    scale = q75 - q25
    scale[scale < _EPS10] = 1.0
    score = ((b - center) / scale).max(axis=0)
    order = sorted(range(len(cols)), key=lambda i: -score[i])          # stable: ties keep column order
    return [(cols[i], float(score[i])) for i in order]


def service_of(column: str) -> str:
    return column.split("_")[0].replace("-db", "")


def service_ranking(ranked_columns) -> list[str]:
    """Step 9."""
    return list(dict.fromkeys(service_of(c) for c in ranked_columns))


def rank(data: pd.DataFrame, inject_time: float, **kw) -> dict:
    """{"metrics": [(column, score)], "services": [service]} for one incident."""
    frame, t = prepare_frame(data, inject_time, **kw)
    ms = metric_scores(frame, t)
    return {"metrics": ms, "services": service_ranking(c for c, _ in ms)}
