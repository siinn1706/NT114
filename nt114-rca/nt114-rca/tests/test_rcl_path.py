"""Path selection (spec a02): truth table, signature, label-free inputs, `no_trace` never yields `trace`."""
from __future__ import annotations

import inspect
import itertools

import pandas as pd
import pytest

from rca import ablate, rcl_path
from rca.rcl_path import has_spans, select_path


@pytest.mark.parametrize("spans,frame,valid", list(itertools.product([True, False], repeat=3)))
def test_truth_table(spans, frame, valid):
    want = "trace" if spans else ("no_trace" if frame and valid else "frame_free")
    assert select_path(spans, frame, valid) == want
    assert want in rcl_path.PATHS


def test_signature_has_only_the_three_inputs():
    assert list(inspect.signature(select_path).parameters) == ["has_spans", "uses_frame", "frame_valid"]


def _traces(**over):
    df = pd.DataFrame({"traceID": ["t1", "t1"], "spanID": ["a", "b"], "parentSpanID": [None, "a"],
                       "svc": ["frontend", "cart"], "startTime": [0, 1], "duration": [10, 5], "statusCode": [0, 0]})
    return df.assign(**over)


def test_has_spans_needs_a_span_id_and_a_candidate_service():
    assert has_spans(_traces(), ["cart"])
    assert not has_spans(_traces(), ["payment"])
    assert not has_spans(_traces(spanID=[None, ""]), ["cart", "frontend"])
    assert not has_spans(_traces(svc=[None, None]), ["cart", "frontend"])
    assert not has_spans(None, ["cart"])                       # status natural_absent
    assert not has_spans(_traces().iloc[:0], ["cart"])         # status empty


@pytest.mark.parametrize("frame,valid", list(itertools.product([True, False], repeat=2)))
def test_no_trace_condition_never_yields_trace(frame, valid):
    tel = ablate.apply({"metrics": None, "logs": None, "traces": _traces()}, "no_trace", "cart")
    path = select_path(has_spans(tel["traces"], ["cart", "frontend"]), frame, valid)
    assert path == ("no_trace" if frame and valid else "frame_free")
