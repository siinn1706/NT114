"""Session fixtures: one RCAEval-shaped raw tree (zips) and one canonical build of it, both in tmp."""
from __future__ import annotations

from pathlib import Path

import pytest

from fixtures.build_fixtures import rcaeval_zips

RCA_ROOT = Path(__file__).resolve().parents[1]
REAL_DATA = RCA_ROOT / "data"


def fixture_config(root_rel: str = "raw/zenodo-test") -> dict:
    from rca import prep
    cfg = prep.load_config()
    cfg["datasets"]["rcaeval"]["root"] = root_rel        # relative to the data home: portable
    cfg["_hash"] = prep.config_hash(cfg)
    return cfg


def build_fixture_home(dh: Path, max_workers: int = 1) -> dict:
    from rca import prep
    rcaeval_zips(dh / "raw")
    return prep.build_dataset("rcaeval", fixture_config(), dh, max_workers=max_workers, log=lambda *a: None)


@pytest.fixture(scope="session")
def rcaeval_home(tmp_path_factory) -> Path:
    """Data home with fixture zips under raw/zenodo-test and a full canonical build."""
    dh = tmp_path_factory.mktemp("dh")
    build_fixture_home(dh)
    return dh


def real_data_available() -> bool:
    return (REAL_DATA / "raw" / "rcaeval-zenodo").is_dir()


@pytest.fixture(scope="session")
def canonical_synth(tmp_path_factory) -> dict:
    """Synthetic RCAEval-layout data (non-overlapping windows) built, condition-matrixed and split."""
    import subprocess
    import sys
    from rca import prep, splits
    root = tmp_path_factory.mktemp("canon")
    dh = root / "data_synth_home"
    subprocess.run([sys.executable, str(RCA_ROOT / "scripts/make_synthetic.py"), str(dh / "raw/synthetic"),
                    "--anchor-gap", "12000"], check=True, capture_output=True)
    pcfg = prep.load_config(RCA_ROOT / "configs/prep_synthetic.yaml")
    prep.build_dataset("rcaeval", pcfg, dh, max_workers=1, log=lambda *a: None)
    assert splits.conditions_cmd("rcaeval", pcfg, dh) == 0
    assert splits.split_cmd("within-rcaeval-retrieval", 0, pcfg, dh) in (0, 3)
    return {"dh": dh, "pcfg": pcfg, "root": root}


def canonical_run_cfg(dh, out_root, **over) -> dict:
    from rca import run_grid
    cfg = run_grid.load_cfg(RCA_ROOT / "configs/canonical_synthetic.yaml")
    cfg.update(data_home=str(dh), evidence_dir=str(out_root / "evidence"), cache=str(out_root / "cache.sqlite"),
               out=str(out_root / "grid.jsonl"), retrieval=["none", "bm25", "hybrid"], embedder="tfidf")
    cfg.update(over)
    return cfg
