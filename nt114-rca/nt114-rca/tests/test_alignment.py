"""RE1 alignment check (evaluation-only): matching keys, partial matches, output location."""
from __future__ import annotations

import pandas as pd
import pytest

from conftest import REAL_DATA
from rca import alignment

INV = pd.DataFrame([
    {"incident_uid": "u1", "system": "sock-shop", "inject_time": 100, "raw_sha256": "a"},
    {"incident_uid": "u2", "system": "sock-shop", "inject_time": 200, "raw_sha256": "b"},
    {"incident_uid": "u3", "system": "sock-shop", "inject_time": 300, "raw_sha256": "c"},
    {"incident_uid": "u4", "system": "train-ticket", "inject_time": 100, "raw_sha256": "d"},
])


def test_compare_needs_system_time_and_fingerprint():
    rel = pd.DataFrame([{"case_id": "r1", "system": "sock-shop", "inject_time": "100", "raw_sha256": "a"},
                        {"case_id": "r2", "system": "sock-shop", "inject_time": "200", "raw_sha256": "x"},
                        {"case_id": "r3", "system": "online-boutique", "inject_time": "100", "raw_sha256": "d"}])
    res = alignment.compare(INV, rel).set_index("incident_uid", drop=False)
    assert res.loc["u1", "status"] == "match" and res.loc["u1", "release_case_id"] == "r1"
    assert res.loc["u2", "status"] == "fingerprint_differs"
    assert res.loc["u3", "status"] == "inject_time_not_found"
    assert res.loc["u4", "status"] == "system_not_found"
    assert sorted(res.loc[res.status == "release_only", "release_case_id"]) == ["r2", "r3"]


def test_outputs_stay_out_of_data_and_evidence(tmp_path):
    with pytest.raises(ValueError, match="eval-only"):
        alignment.check_out_dir(tmp_path / "data" / "x", tmp_path / "data")
    with pytest.raises(ValueError, match="eval-only"):
        alignment.check_out_dir(tmp_path / "res" / "evidence" / "a", tmp_path / "data")
    assert alignment.check_out_dir(tmp_path / "results_alignment", tmp_path / "data").is_dir()


@pytest.mark.realdata
@pytest.mark.skipif(not (REAL_DATA / "canonical/v1/rcaeval/_build.json").is_file(), reason="needs the real RCAEval build")
def test_re1_inventory():
    df = pd.DataFrame(alignment.inventory(REAL_DATA))
    assert len(df) == 375 and df["system"].value_counts().eq(125).all()
    assert (df["inject_time"] == df["anchor_s"]).all() and df["raw_sha256"].is_unique
    assert df["source_member"].str.startswith("RE1-").all()
