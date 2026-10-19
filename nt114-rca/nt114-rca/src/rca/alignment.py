"""RE1 alignment check with an external benchmark release (evaluation-only, CPU).

  python -m rca.alignment inventory <out dir> [--data-home data]          # step 1, inside NT114
  python -m rca.alignment compare <out dir> <release table.csv>            # step 2, after inspecting the release

Step 1 writes `re1_inventory.jsonl`, one row per RCAEval RE1 incident: the canonical uid, the source
case id (`source_incident_id` of the eval-only labels, e.g. `rcaeval:re1ob_cartservice_cpu_1`), the
source member (`RE1-OB/cartservice_cpu/1/data.csv`), the system, the injection timestamp (the
member's `inject_time.txt`, and the canonical anchor), `raw_sha256` (sha256 of the raw `data.csv`
bytes) and `canonical_sha256` (the canonical metrics content hash). Source case ids carry the
injected service, so the inventory is label-bearing and stays out of every model-facing directory.

Step 2 matches a release table with columns `system`, `inject_time` and `raw_sha256` (and an optional
`case_id`): a match needs an equal system, an equal injection timestamp and an equal raw fingerprint;
partial matches are listed with the key that failed. Even a full match aligns incidents and telemetry
only: preprocessing, split, granularity and the candidate set need their own checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import pandas as pd

SUBSET = "RE1"
SYSTEM_CODE = {"OB": "online-boutique", "SS": "sock-shop", "TT": "train-ticket"}


def check_out_dir(out: Path, data_home: Path) -> Path:
    """Outputs hold label-bearing ids: never under the data home or an evidence directory."""
    o = Path(out).resolve()
    if Path(data_home).resolve() in [o, *o.parents] or any(p.name == "evidence" for p in [o, *o.parents]):
        raise ValueError(f"alignment outputs are eval-only: {o} must not be under the data home or an evidence dir")
    o.mkdir(parents=True, exist_ok=True)
    return o


def _member(store_root: Path, ref: str) -> tuple[Path, str]:
    """`<source>/<version>/<zip>!<member>` -> (zip path under raw/, member)."""
    z, m = ref.split("!", 1)
    return store_root / "raw" / z, m


def inventory(data_home: Path) -> list[dict]:
    from .store import CanonicalStore, read_jsonl
    st = CanonicalStore(data_home)
    ev = data_home / "canonical" / "v1" / "rcaeval" / "eval_only"
    labels = {r["incident_uid"]: r for r in read_jsonl(ev / "labels.jsonl")}
    index = {r["incident_uid"]: r for r in read_jsonl(ev / "source_index.jsonl")}
    zips: dict[Path, zipfile.ZipFile] = {}
    out = []
    try:
        for inc in sorted(st.incidents("rcaeval"), key=lambda i: i["incident_uid"]):
            if inc.get("dataset_subset") != SUBSET:
                continue
            u = inc["incident_uid"]
            members = [m["member"] for m in index[u]["members"]]
            data = next(m for m in members if m.endswith("/data.csv"))
            zpath, mem = _member(data_home, data)
            zf = zips.setdefault(zpath, zipfile.ZipFile(zpath))
            raw = zf.read(mem)
            inject = zf.read(mem.rsplit("/", 1)[0] + "/inject_time.txt").decode().strip().splitlines()[0].strip()
            out.append({"incident_uid": u, "source_case_id": labels[u]["source_incident_id"],
                        "source_member": mem, "system": inc["system"], "inject_time": int(inject),
                        "anchor_s": inc["time"]["anchor_ns"] // 10**9, "raw_sha256": hashlib.sha256(raw).hexdigest(),
                        "canonical_sha256": inc["telemetry"]["metrics"]["content_sha256"]})
    finally:
        for zf in zips.values():
            zf.close()
    return out


def compare(inv: pd.DataFrame, release: pd.DataFrame) -> pd.DataFrame:
    """One row per NT114 incident: `match`, or the first key that failed against the closest release row."""
    rel = release.assign(inject_time=release["inject_time"].astype("int64"))
    rows = []
    for r in inv.itertuples():
        same_sys = rel[rel["system"] == r.system]
        same_t = same_sys[same_sys["inject_time"] == r.inject_time]
        full = same_t[same_t["raw_sha256"] == r.raw_sha256]
        status = ("match" if len(full) == 1 else "ambiguous" if len(full) > 1 else
                  "fingerprint_differs" if len(same_t) else "inject_time_not_found" if len(same_sys) else "system_not_found")
        rows.append({"incident_uid": r.incident_uid, "system": r.system, "status": status,
                     "release_case_id": full["case_id"].iloc[0] if len(full) == 1 and "case_id" in full else None})
    out = pd.DataFrame(rows)
    matched = set(out.loc[out.status == "match", "release_case_id"].dropna())
    extra = rel[~rel["case_id"].isin(matched)] if "case_id" in rel else rel.iloc[:0]
    return pd.concat([out, pd.DataFrame({"incident_uid": None, "system": extra.get("system"), "status": "release_only",
                                         "release_case_id": extra.get("case_id")})], ignore_index=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("inventory")
    a1.add_argument("out", type=Path)
    a1.add_argument("--data-home", type=Path, default=Path("data"))
    a2 = sub.add_parser("compare")
    a2.add_argument("out", type=Path)
    a2.add_argument("release", type=Path)
    a2.add_argument("--data-home", type=Path, default=Path("data"))
    a = ap.parse_args(argv)
    out = check_out_dir(a.out, a.data_home)
    if a.cmd == "inventory":
        rows = inventory(a.data_home)
        pd.DataFrame(rows).to_json(out / "re1_inventory.jsonl", orient="records", lines=True)
        df = pd.DataFrame(rows)
        summary = {"incidents": len(df), "per_system": df["system"].value_counts().sort_index().to_dict(),
                   "inject_time_equals_anchor": int((df["inject_time"] == df["anchor_s"]).sum()),
                   "distinct_raw_sha256": int(df["raw_sha256"].nunique())}
        (out / "re1_inventory_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
        print(json.dumps(summary))
    else:
        inv = pd.read_json(out / "re1_inventory.jsonl", lines=True)
        res = compare(inv, pd.read_csv(a.release))
        res.to_csv(out / "re1_alignment.csv", index=False)
        print(res["status"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
