"""Export the raw metric frames BARO-style is checked on, with a sha256 per file (NT114 side of the
reference-fixture task; the reference side reads exactly these files).

  python scripts/export_baro_inputs.py <out dir> [--data-home data] [--split within-rcaeval-grouped] [--per-cell 2]

- Real inputs: `legacy_view.legacy_telemetry(...)["metrics"]` of the first `--per-cell` DEV (`val`)
  incidents, by uid, of every RCAEval (subset, system) present in the split. Needs the canonical build.
- Edge cases (`edge_*`): deterministic synthetic frames with constant series, missing values, +-inf,
  ties, a `-db` service, `_latency-50` / `_latency-90` columns, `_mem` columns and a zero-IQR normal window.

Writes `<name>.csv` (`DataFrame.to_csv(index=False)`, floats round-trip) and `inputs.json`:
[{name, incident_uid, subset, system, inject_time, file, sha256, n_rows, n_cols}]. Holds no labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def edge_frames() -> dict[str, tuple[pd.DataFrame, int]]:
    rng = np.random.default_rng(20261019)
    t = np.arange(0, 1200, 2)
    t0 = 600
    after = t >= t0
    n = len(t)
    base = {"time": t,
            "cart_cpu": rng.normal(1, 0.1, n) + 3 * after,
            "cart_mem": rng.normal(2e8, 1e6, n) + 5e7 * after,
            "orders-db_cpu": rng.normal(1, 0.1, n) + 1.5 * after,
            "pay_cpu": np.full(n, 0.5),                                       # constant: dropped
            "front_latency-50": rng.normal(10, 1, n) + 50 * after,            # dropped by main.py
            "front_latency-90": rng.normal(20, 1, n) + 4 * after,             # renamed to front_latency
            "ship_cpu": np.where(after, rng.normal(3, 0.5, n), 1.0),          # zero IQR in the normal window
            "user_cpu": rng.normal(1, 0.1, n) + 2 * after}
    gaps = pd.DataFrame(base)
    gaps.loc[[3, 4, 5, 400], "user_cpu"] = np.nan
    gaps.loc[[0, 1], "cart_cpu"] = np.nan                                     # leading NaN: filled with 0
    gaps.loc[700, "orders-db_cpu"] = np.inf
    ties = pd.DataFrame(base)
    ties["zeta_cpu"] = ties["cart_cpu"]                                       # identical series: a tie
    ties["alpha_cpu"] = ties["cart_cpu"]
    flat_after = pd.DataFrame(base)
    flat_after.loc[after, "user_cpu"] = flat_after.loc[~after, "user_cpu"].iloc[0]   # constant after, not before
    return {"edge_gaps_inf": (gaps, t0), "edge_ties": (ties, t0), "edge_flat_after": (flat_after, t0)}


def real_frames(data_home: Path, split: str, per_cell: int) -> dict[str, tuple[pd.DataFrame, int, dict]]:
    from rca.legacy_view import legacy_telemetry, visible_case
    from rca.store import CanonicalStore, read_jsonl
    hits = sorted(p for p in (data_home / "splits").glob(f"{split}-*") if (p / "split.json").is_file())
    if not hits:
        raise SystemExit(f"no split {split!r} under {data_home / 'splits'}")
    roles = {a["incident_uid"]: a["split"] for a in read_jsonl(hits[-1] / "assignments.jsonl")}
    st = CanonicalStore(data_home)
    cells: dict[tuple, list] = {}
    for inc in sorted(st.incidents("rcaeval"), key=lambda i: i["incident_uid"]):
        if roles.get(inc["incident_uid"]) == "val":
            cells.setdefault((inc.get("dataset_subset"), inc["system"]), []).append(inc)
    out = {}
    for (subset, system), incs in sorted(cells.items(), key=str):
        for inc in incs[:per_cell]:
            m = legacy_telemetry(st, inc["incident_uid"])["metrics"]
            if m is None:
                continue
            vc = visible_case(inc)
            out[vc.case_id] = (m, vc.inject_time, {"incident_uid": vc.case_id, "subset": subset, "system": system})
    return out


def write(out: Path, name: str, frame: pd.DataFrame, inject_time: int, extra: dict) -> dict:
    f = out / f"{name}.csv"
    frame.to_csv(f, index=False, lineterminator="\n")
    return {"name": name, **extra, "inject_time": int(inject_time), "file": f.name,
            "sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "n_rows": len(frame), "n_cols": frame.shape[1]}


def export(out: Path, data_home: Path | None, split: str, per_cell: int) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    rows = [write(out, n, f, t, {"incident_uid": None, "subset": None, "system": None})
            for n, (f, t) in edge_frames().items()]
    if data_home is not None:
        rows += [write(out, n, f, t, extra) for n, (f, t, extra) in real_frames(data_home, split, per_cell).items()]
    (out / "inputs.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--data-home", type=Path, default=None, help="canonical data directory (omit: edge cases only)")
    ap.add_argument("--split", default="within-rcaeval-grouped")
    ap.add_argument("--per-cell", type=int, default=2)
    a = ap.parse_args(argv)
    rows = export(a.out, a.data_home, a.split, a.per_cell)
    print(f"{len(rows)} inputs -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
