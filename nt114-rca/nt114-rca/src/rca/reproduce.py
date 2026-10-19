"""Regenerate every analysis table of a run and compare it with the published one.

  python -m rca.reproduce <analysis out dir>

Reads `analysis_meta.json` and the config copy `analysis_config.yaml` written by `rca.analyze` (with
or without the `exploratory_` prefix), reruns the analysis into a temporary directory with the same
inputs and seeds, and compares the sha256 of every table. Exit 0 when all tables match, 1 when any
table differs or is missing (the tables are named, and so are inputs whose sha256 changed since the
analysis), 2 when the directory holds no analysis.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import yaml

from . import analyze


def find_meta(run_dir: Path) -> Path | None:
    for name in ("analysis_meta.json", "exploratory_analysis_meta.json"):
        if (run_dir / name).is_file():
            return run_dir / name
    return None


def reproduce(run_dir: Path) -> dict:
    """{"tables": {name: "match" | "differs" | "missing"}, "inputs_changed": [paths]}."""
    meta_path = find_meta(run_dir)
    if meta_path is None:
        raise FileNotFoundError(f"no analysis_meta.json in {run_dir}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    cfg = yaml.safe_load((run_dir / meta["config"]).read_text(encoding="utf-8"))
    changed = [p for p, sha in meta.get("inputs_sha256", {}).items() if analyze._sha(p) != sha]
    with tempfile.TemporaryDirectory() as tmp:
        res = analyze.run({**cfg, "out_dir": tmp})
        new = res["meta"]["tables_sha256"]
    tables = {n: ("missing" if n not in new else "match" if new[n] == sha else "differs")
              for n, sha in meta["tables_sha256"].items()}
    tables.update({n: "differs" for n in set(new) - set(tables)})
    return {"tables": tables, "inputs_changed": changed}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", help="analysis output directory (holds analysis_meta.json)")
    a = ap.parse_args(argv)
    try:
        out = reproduce(Path(a.run_dir))
    except FileNotFoundError as e:
        print(e)
        return 2
    bad = sorted(n for n, s in out["tables"].items() if s != "match")
    for p in out["inputs_changed"]:
        print(f"input changed since the analysis: {p}")
    if bad:
        print("tables that differ: " + ", ".join(f"{n} ({out['tables'][n]})" for n in bad))
        return 1
    print(f"all {len(out['tables'])} tables reproduced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
