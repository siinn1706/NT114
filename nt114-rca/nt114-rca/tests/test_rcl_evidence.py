"""R-a evidence builder: paths, frame use only on `no_trace`, determinism, refusals."""
from __future__ import annotations

import re

import pandas as pd
import pytest

from rca import ablate, rcl_evidence
from rca.data import VisibleCase
from test_rcl_tools import T, _metrics, _traces

CANDS = ["cart", "frontend", "payment"]
FRAME = {"valid": True, "sha256": "f" * 64, "edges": [("frontend", "cart"), ("frontend", "redis"), ("cart", "payment")]}


def case():
    return VisibleCase(case_id="x.0000000000000001", dataset="rcaeval", system="online-boutique", inject_time=T,
                       services=CANDS)


def tel():
    return {"metrics": _metrics(), "logs": None, "traces": _traces()}


def listed(text):
    return re.findall(r"^- ([a-z0-9]+):", text, re.M)


def test_trace_path_lists_the_deepest_anomalous_service_first():
    ev = rcl_evidence.build(case(), tel(), "ra")
    assert ev["path"] == "trace" and ev["frame_sha256"] is None
    assert listed(ev["text"])[0] == "cart" and set(listed(ev["text"])) <= set(CANDS)
    assert "Call edges: frontend -> cart" in ev["text"] and "trace: in selected trace" in ev["text"]
    assert "## Not available\n- logs were not collected" in ev["text"]


def test_frame_never_changes_the_trace_path():
    a, b = rcl_evidence.build(case(), tel(), "ra"), rcl_evidence.build(case(), tel(), "ra_im1", FRAME)
    assert a["text"] == b["text"] and b["frame_sha256"] == FRAME["sha256"]


@pytest.mark.parametrize("arm,frame,path", [("ra", None, "frame_free"), ("ra_im1", FRAME, "no_trace"),
                                            ("ra_im1_shuf", FRAME, "no_trace"), ("ra_im1", {**FRAME, "valid": False}, "frame_free"),
                                            ("ra_im1", None, "frame_free")])
def test_no_trace_condition_paths(arm, frame, path):
    t = ablate.apply(tel(), "no_trace", "cart")
    ev = rcl_evidence.build(case(), t, arm, frame)
    assert ev["path"] == path
    assert "trace:" not in ev["text"] and "Selected trace" not in ev["text"]
    if path == "no_trace":
        assert "Frame edges among candidates: cart -> payment; frontend -> cart" in ev["text"]
        assert "redis" not in ev["text"]                     # frame edges restricted to candidates
    else:
        assert "frame" not in ev["text"].lower()


def test_deterministic_and_row_order_free():
    t1, t2 = tel(), tel()
    t2["traces"] = t2["traces"].sample(frac=1, random_state=1)
    for arm, fr in (("ra", None), ("ra_im1", FRAME)):
        assert rcl_evidence.build(case(), t1, arm, fr) == rcl_evidence.build(case(), t1, arm, fr)
        assert rcl_evidence.build(case(), t1, arm, fr)["text"] == rcl_evidence.build(case(), t2, arm, fr)["text"]


def test_refusals():
    with pytest.raises(ValueError, match="unknown R-a arm"):
        rcl_evidence.build(case(), tel(), "l0")
    with pytest.raises(ValueError, match="reads no frame"):
        rcl_evidence.build(case(), tel(), "ra", FRAME)
    with pytest.raises(NotImplementedError):
        rcl_evidence.build(case(), tel(), "ra", log_trace_segment_gap_s=30.0)


def test_nothing_flagged_still_gives_evidence():
    quiet = {"metrics": None, "logs": None, "traces": None}
    ev = rcl_evidence.build(case(), quiet, "ra")
    assert ev["path"] == "frame_free" and "- no tool flagged any candidate" in ev["text"]
    assert listed(ev["text"]) == []
    assert rcl_evidence.fingerprint() == rcl_evidence.fingerprint() and len(rcl_evidence.fingerprint()) == 16
