"""Evaluation units: the independent statistical unit of every incident, its weight, a deterministic
representative, the primary-evaluation exclusion, and log/trace coverage strata.

  python -m rca.prep eval-units --dataset rca100

Output `data/reports/eval-units-<dataset>.json` (eval-only metadata, never a model input):
- `injection_id`: records cut from one source incident share it (`group.group_id`, else `duplicate_of` /
  `copy_of`, else the uid). Statistics resample injections, not records; `weight` = 1 / accepted records
  of the injection, so every injection counts once. `representative`: the smallest uid of the injection
  (label-free), for the one-record-per-injection sensitivity analysis.
- `excluded_from_primary`: the reason from `configs/eval_exclusions.yaml`, or null.
- `coverage`: per log/trace modality, the seconds of recorded data after the anchor inside the contiguous
  stretch the evidence builder uses, and its cause: `covered` (>= MIN_AFTER_S, so an absent error is a
  real absence), `export_truncated` (the stored export ends before that), `export_gap` (data resumes after
  a gap), or the natural modality status. Same segment rule and gap as `evidence.build` for the dataset.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from .evidence import ANOMAL_S, MIN_AFTER_S, NORMAL_S, _segment
from .legacy_view import evidence_kwargs
from .store import SPLIT_STATES, CanonicalStore, dump_json, write_json_atomic

EXCLUSIONS = Path(__file__).resolve().parents[2] / "configs" / "eval_exclusions.yaml"
EXIT_OK, EXIT_PRECONDITION = 0, 5


def load_exclusions(path: Path = EXCLUSIONS) -> dict[str, dict[str, str]]:
    """{dataset: {incident_uid: reason}} for active entries; `status: lifted` entries stay in the file
    as the record of the decision but exclude nothing."""
    if not Path(path).is_file():
        return {}
    with open(path, encoding="utf-8") as f:
        rows = (yaml.safe_load(f) or {}).get("exclusions") or []
    out: dict[str, dict[str, str]] = {}
    for r in rows:
        if r["status"] == "lifted":
            continue
        out.setdefault(r["dataset"], {})[r["incident_uid"]] = f"{r['reason']} [{r['status']}, {r['decided']}]"
    return out


def coverage(store: CanonicalStore, inc: dict, modality: str, gap_s: float | None) -> dict:
    tel = inc["telemetry"][modality]
    if tel["status"] != "present":
        return {"after_s": 0.0, "cause": tel["status"]}
    t = inc["time"]["anchor_ns"] / 1e9
    ts = store.telemetry(inc["incident_uid"], modality, columns=["ts_ns"])["ts_ns"]
    sec = pd.Series(ts.to_numpy(zero_copy_only=False), dtype="float64") / 1e9
    if gap_s is None:                                    # fixed windows: last row inside [t, t + ANOMAL_S]
        after = sec[(sec >= t) & (sec <= t + ANOMAL_S)]
        hi = float(after.max()) if len(after) else t
    else:
        hi = _segment(sec, t, gap_s)[1]
    after_s = round(hi - t, 3)
    if after_s >= MIN_AFTER_S:
        cause = "covered"
    else:
        later = sec[(sec > hi) & (sec <= t + ANOMAL_S)]
        cause = "export_gap" if len(later) else "export_truncated"
    return {"after_s": after_s, "cause": cause}


def eval_units(store: CanonicalStore, dataset: str, cfg: dict, exclusions: dict | None = None) -> dict:
    labels, quality = store.labels(dataset), store.quality(dataset)
    excl = (exclusions if exclusions is not None else load_exclusions()).get(dataset, {})
    gap = evidence_kwargs(cfg, dataset).get("log_trace_segment_gap_s")
    incs = sorted(store.incidents(dataset, states=None), key=lambda r: r["incident_uid"])
    accepted = [i for i in incs if quality[i["incident_uid"]]["state"] in SPLIT_STATES]
    unknown = sorted(set(excl) - {i["incident_uid"] for i in incs})
    if unknown:
        raise ValueError(f"eval_exclusions names uids not in {dataset}: {unknown}")

    def injection(u: str) -> str:
        g = labels[u]["group"]
        return g["group_id"] or g["duplicate_of"] or g["copy_of"] or u
    members: dict[str, list[str]] = {}
    for i in accepted:
        members.setdefault(injection(i["incident_uid"]), []).append(i["incident_uid"])
    units = {}
    for i in accepted:
        u = i["incident_uid"]
        inj = injection(u)
        units[u] = {"injection_id": inj, "injection_size": len(members[inj]), "weight": round(1 / len(members[inj]), 6),
                    "representative": u == min(members[inj]), "excluded_from_primary": excl.get(u),
                    "coverage": {m: coverage(store, i, m, gap) for m in ("logs", "traces")}}
    primary = [u for u, r in units.items() if not r["excluded_from_primary"]]
    b = store.build(dataset)
    causes = {m: {} for m in ("logs", "traces")}
    for r in units.values():
        for m in causes:
            causes[m][r["coverage"][m]["cause"]] = causes[m].get(r["coverage"][m]["cause"], 0) + 1
    return {"dataset_id": dataset, "build_id": b["build_id"], "dataset_digest": b["dataset_digest"],
            "rules": {"min_after_s": MIN_AFTER_S, "window_s": [NORMAL_S, ANOMAL_S], "segment_gap_s": gap},
            "counts": {"accepted_records": len(units), "independent_injections": len(members),
                       "multi_record_injections": sum(1 for v in members.values() if len(v) > 1),
                       "excluded_from_primary": len(units) - len(primary),
                       "primary_records": len(primary),
                       "primary_injections": len({units[u]["injection_id"] for u in primary}),
                       "coverage_causes": {m: dict(sorted(v.items())) for m, v in causes.items()}},
            "units": units}


def eval_units_cmd(dataset: str, cfg: dict, data_home: Path) -> int:
    from .prep import paths
    store = CanonicalStore(data_home)
    if dataset not in store.datasets():
        print(f"{dataset}: no canonical build")
        return EXIT_PRECONDITION
    rep = eval_units(store, dataset, cfg)
    write_json_atomic(paths(cfg, data_home)["reports"] / f"eval-units-{dataset}.json", rep, indent=1)
    print(dump_json(rep["counts"]))
    return EXIT_OK
