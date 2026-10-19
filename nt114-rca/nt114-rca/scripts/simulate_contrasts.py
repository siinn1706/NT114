"""Calibration and detectable effects of the paired-contrast engine on the real injection structure.

  python scripts/simulate_contrasts.py <out dir> [--data-home data] [--reps 1000]

Structures: the incidents of `results_visibility/<ds>/evidence_visibility.jsonl` with the `test` role,
grouped by the injection of `reports/eval-units-<ds>.json` (records of one injection share the
cluster), plus named intersections (the incidents carrying every listed condition).

Generators of paired binary outcomes (arm a vs arm b, per record):
- `difficulty`: per injection a difficulty u ~ U(0.2, 0.8); a record is correct with probability
  u + shift in arm a and u in arm b, independently (the phase-03 test's generator). True
  difference = shift.
- `discordance`: per injection a discordance rate d_j ~ Beta with mean d (concentration 4) and a
  concordant level u ~ U(0.2, 0.8); a record is discordant with probability d_j, and a discordant
  record favours arm a with probability (1 + delta / d) / 2. True difference = delta.

V4: CI coverage of the true difference (shift 0.1) and sign-flip type-I error (shift 0) for both
generators. V5: power at alpha = 0.05 over a grid of delta for discordance 10 %, 20 %, 30 %; the MDE is
the smallest grid delta with power >= 0.8. Writes `calibration.csv`, `power.csv`, `mde.csv` and
`structures.json`. CPU only; seeds fixed.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rca import contrasts, score  # noqa: E402

SPEC = {"name": "sim", "a": {"condition": "a"}, "b": {"condition": "b"}, "metric": "ac1"}
DATASETS = ("rcaeval", "nezha", "rca100", "aiops2025")
INTERSECTIONS = {"rcaeval_test_blind_root_and_blind_nonroot_ev": ("rcaeval", ["blind_root", "blind_nonroot_ev"])}


def structures(data_home: Path, vis_root: Path) -> dict[str, pd.DataFrame]:
    out = {}
    for ds in DATASETS:
        vis = pd.read_json(vis_root / ds / "evidence_visibility.jsonl", lines=True)
        vis = vis[vis["split_role"] == "test"]
        units = score.units(data_home, ds).drop_duplicates("incident_uid")
        units = units[units["excluded"].isna()] if "excluded" in units else units
        full = set(vis.loc[vis.condition == "full", "incident_uid"])
        out[f"{ds}_test_full"] = units[units.incident_uid.isin(full)][["incident_uid", "injection_id"]]
        for name, (d, conds) in INTERSECTIONS.items():
            if d == ds:
                keep = set.intersection(*(set(vis.loc[vis.condition == c, "incident_uid"]) for c in conds))
                out[name] = units[units.incident_uid.isin(keep)][["incident_uid", "injection_id"]]
    return {k: v.reset_index(drop=True) for k, v in out.items()}


def _frame(st: pd.DataFrame, a: np.ndarray, b: np.ndarray) -> pd.DataFrame:
    n = len(st)
    return pd.DataFrame({"incident_uid": np.tile(st["incident_uid"].to_numpy(), 2),
                         "injection_id": np.tile(st["injection_id"].to_numpy(), 2),
                         "condition": ["a"] * n + ["b"] * n,
                         "rank": np.where(np.concatenate([a, b]), 1, 6)})


def sample_difficulty(st, rng, shift):
    inj, idx = np.unique(st["injection_id"].to_numpy(), return_inverse=True)
    u = rng.uniform(0.2, 0.8, len(inj))[idx]
    return _frame(st, rng.random(len(st)) < u + shift, rng.random(len(st)) < u)


def sample_discordance(st, rng, d, delta):
    inj, idx = np.unique(st["injection_id"].to_numpy(), return_inverse=True)
    k = 4.0
    dj = rng.beta(d * k, (1 - d) * k, len(inj))[idx]
    u = rng.uniform(0.2, 0.8, len(inj))[idx]
    n = len(st)
    conc = rng.random(n) < u
    disc = rng.random(n) < dj
    a_wins = rng.random(n) < (1 + delta / d) / 2
    a = np.where(disc, a_wins, conc)
    b = np.where(disc, ~a_wins, conc)
    return _frame(st, a, b)


def calibration(st, reps, seed, n_boot, n_perm) -> list[dict]:
    rows = []
    for gen in ("difficulty", "discordance"):
        rng = np.random.default_rng(seed)
        cover = reject = 0
        for r in range(reps):
            if gen == "difficulty":
                pos, null = sample_difficulty(st, rng, 0.1), sample_difficulty(st, rng, 0.0)
            else:
                pos, null = sample_discordance(st, rng, 0.2, 0.1), sample_discordance(st, rng, 0.2, 0.0)
            row = contrasts.evaluate(pos, SPEC, n_boot=n_boot, n_perm=10, seed=r)
            cover += row["lo"] <= 0.1 <= row["hi"]
            reject += contrasts.evaluate(null, SPEC, n_boot=10, n_perm=n_perm, seed=r)["p"] < 0.05
        rows.append({"generator": gen, "reps": reps, "covered": int(cover), "coverage": cover / reps,
                     "rejected_null": int(reject), "type1": reject / reps})
    return rows


def power(st, reps, seed, n_perm, discordances=(0.1, 0.2, 0.3)) -> list[dict]:
    rows = []
    for d in discordances:
        for delta in np.round(np.arange(0.02, d + 1e-9, 0.02), 3):
            rng = np.random.default_rng(seed)
            hits = sum(contrasts.evaluate(sample_discordance(st, rng, d, delta), SPEC, n_boot=10, n_perm=n_perm,
                                          seed=r)["p"] < 0.05 for r in range(reps))
            rows.append({"discordance": d, "delta": float(delta), "reps": reps, "rejected": int(hits), "power": hits / reps})
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--data-home", type=Path, default=ROOT / "data")
    ap.add_argument("--visibility", type=Path, default=ROOT / "results_visibility")
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--power-reps", type=int, default=400)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--n-perm", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    sts = structures(a.data_home, a.visibility)
    info = {k: {"records": len(v), "injections": int(v["injection_id"].nunique()),
                "records_per_injection_max": int(v.groupby("injection_id").size().max())} for k, v in sts.items()}
    (a.out / "structures.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    cal, pw = [], []
    for name, st in sts.items():
        t0 = time.time()
        cal += [{"structure": name, **r} for r in calibration(st, a.reps, a.seed, a.n_boot, a.n_perm)]
        pw += [{"structure": name, **r} for r in power(st, a.power_reps, a.seed, a.n_perm)]
        print(f"{name}: {info[name]} in {time.time() - t0:.0f} s", flush=True)
    pd.DataFrame(cal).to_csv(a.out / "calibration.csv", index=False)
    pw = pd.DataFrame(pw)
    pw.to_csv(a.out / "power.csv", index=False)
    mde = [{"structure": s, "discordance": d,
            "mde_power80": (g.loc[g.power >= 0.8, "delta"].min() if (g.power >= 0.8).any() else None)}
           for (s, d), g in pw.groupby(["structure", "discordance"])]
    pd.DataFrame(mde).to_csv(a.out / "mde.csv", index=False)
    print(pd.DataFrame(cal).to_string(index=False))
    print(pd.DataFrame(mde).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
