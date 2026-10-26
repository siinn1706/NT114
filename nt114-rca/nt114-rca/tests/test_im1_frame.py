"""IM1 frame builder: pre-anchor window, train-only input, validity threshold, freezing, shuffled control."""
from __future__ import annotations

import pyarrow as pa
import pytest

from rca import im1_frame

ANCHOR = 10_000 * 10**9
KEY = ("rcaeval", "RE2", "online-boutique", "split-x")


class FakeStore:
    """Minimal `CanonicalStore.telemetry` stand-in: trace tables keyed by incident uid."""

    def __init__(self, tables):
        self.tables, self.columns_read = tables, []

    def telemetry(self, uid, modality, columns=None, filters=None):
        assert modality == "traces"
        self.columns_read.append(list(columns))
        t = self.tables.get(uid)
        return None if t is None else t.select(columns)


def _table(rows):
    cols = list(zip(*rows)) if rows else [[]] * 6
    return pa.table({"ts_ns": pa.array(cols[0], pa.int64()), "trace_id": pa.array(cols[1], pa.string()),
                     "span_id": pa.array(cols[2], pa.string()), "parent_span_id": pa.array(cols[3], pa.string()),
                     "service_id": pa.array(cols[4], pa.string()), "duration_ns": pa.array(cols[5], pa.int64())})


def _inc(uid):
    return {"incident_uid": uid, "dataset_id": "rcaeval", "dataset_subset": "RE2", "system": "online-boutique",
            "time": {"anchor_ns": ANCHOR}}


def _call(t0, tid, parent_svc, child_svc):
    return [(t0, tid, f"{tid}p", None, parent_svc, 5), (t0, tid, f"{tid}c", f"{tid}p", child_svc, 3)]


def store3(extra_after=True):
    tabs = {}
    for k in range(3):
        rows = _call(ANCHOR - 100 * 10**9, f"t{k}", "frontend", "cart")
        if extra_after:   # at or after the anchor: must never become an edge
            rows += _call(ANCHOR, f"a{k}", "frontend", "payment") + _call(ANCHOR + 10**9, f"b{k}", "cart", "redis")
        rows += _call(ANCHOR - 700 * 10**9, f"o{k}", "ad", "email")      # before the 600 s window
        tabs[f"u{k}"] = _table(rows)
    return FakeStore(tabs)


ROLES = {f"u{k}": "train" for k in range(3)}


def test_window_fields_and_edges():
    st = store3()
    f = im1_frame.build_frame(st, [_inc(f"u{k}") for k in range(3)], ROLES, KEY)
    assert f["edges"] == [["frontend", "cart", 3]] and f["nodes"] == ["cart", "frontend"]
    assert f["valid"] and f["n_contributing"] == 3
    assert all(c == im1_frame.COLUMNS for c in st.columns_read)          # duration, status, operation never read
    assert set(f) == {"frame_version", "kind", "key", "window_s", "n_train_incidents", "n_contributing",
                      "min_contributing", "valid", "nodes", "edges", "sha256"}


def test_parent_resolves_within_the_same_trace_only():
    rows = [(ANCHOR - 10**9, "t1", "p", None, "frontend", 1), (ANCHOR - 10**9, "t2", "c", "p", "cart", 1)]
    st = FakeStore({f"u{k}": _table(rows) for k in range(3)})
    assert im1_frame.build_frame(st, [_inc(f"u{k}") for k in range(3)], ROLES, KEY)["edges"] == []


def test_validity_threshold_is_three_contributing_incidents():
    st = store3()
    st.tables["u2"] = _table(_call(ANCHOR + 10**9, "z", "frontend", "cart"))   # contributes nothing before anchor
    f = im1_frame.build_frame(st, [_inc(f"u{k}") for k in range(3)], ROLES, KEY)
    assert f["n_contributing"] == 2 and not f["valid"] and im1_frame.MIN_CONTRIBUTING == 3


@pytest.mark.parametrize("role", ["val", "test", None])
def test_non_train_incident_raises(role):
    roles = dict(ROLES)
    roles.pop("u1") if role is None else roles.update(u1=role)
    with pytest.raises(ValueError, match="train-role"):
        im1_frame.build_frame(store3(), [_inc(f"u{k}") for k in range(3)], roles, KEY)


def test_other_key_raises():
    inc = dict(_inc("u0"), dataset_subset="RE3")
    with pytest.raises(ValueError, match="frame key"):
        im1_frame.build_frame(store3(), [inc], ROLES, KEY)


def test_deterministic_hash_and_freezing(tmp_path):
    a = im1_frame.build_frame(store3(), [_inc(f"u{k}") for k in range(3)], ROLES, KEY)
    b = im1_frame.build_frame(store3(), [_inc(f"u{k}") for k in (2, 0, 1)], ROLES, KEY)
    assert a["sha256"] == b["sha256"]
    p = tmp_path / "f.json"
    im1_frame.write_frozen(p, a)
    im1_frame.write_frozen(p, a)                                   # same hash: accepted
    with pytest.raises(RuntimeError, match="frozen IM1 frame"):
        im1_frame.write_frozen(p, {**a, "sha256": "0" * 64})


def test_shuffled_keeps_nodes_and_edge_count_with_one_seed():
    nodes = [f"s{i}" for i in range(6)]
    content = {"frame_version": "1", "kind": "real", "key": list(KEY), "window_s": 600, "n_train_incidents": 3,
               "n_contributing": 3, "min_contributing": 3, "valid": True, "nodes": nodes,
               "edges": [[nodes[i], nodes[i + 1], 3] for i in range(5)]}
    real = {**content, "sha256": im1_frame._sha(content)}
    s1, s2 = im1_frame.shuffled(real), im1_frame.shuffled(real)
    assert s1 == s2 and s1["source_sha256"] == real["sha256"]
    assert s1["nodes"] == real["nodes"] and len(s1["edges"]) == len(real["edges"])
    assert all(p != c for p, c, _ in s1["edges"])
    assert s1["retained_real_share"] == 0.0 and s1["informative"]       # enough non-real pairs exist
    dense = {**content, "nodes": nodes[:2], "edges": [[nodes[0], nodes[1], 3]]}
    dense["sha256"] = im1_frame._sha(dense)
    sd = im1_frame.shuffled(dense)
    assert sd["edges"] == [[nodes[1], nodes[0], None]] and sd["retained_real_share"] == 0.0
    full = {**content, "nodes": nodes[:2], "edges": [[nodes[0], nodes[1], 3], [nodes[1], nodes[0], 3]]}
    full["sha256"] = im1_frame._sha(full)
    sf = im1_frame.shuffled(full)                                    # no non-real pair left
    assert sf["retained_real_share"] == 1.0 and not sf["informative"]


def test_for_arm_picks_real_or_shuffled_and_none_without_a_key():
    real = im1_frame.build_frame(store3(), [_inc(f"u{k}") for k in range(3)], ROLES, KEY)
    frames = {im1_frame.key_id(KEY): {"key": list(KEY), "real": real, "shuffled": im1_frame.shuffled(real)}}
    assert im1_frame.for_arm(frames, _inc("q"), KEY[3], "ra_im1")["sha256"] == real["sha256"]
    assert im1_frame.for_arm(frames, _inc("q"), KEY[3], "ra_im1_shuf")["sha256"] != real["sha256"]
    assert im1_frame.for_arm(frames, dict(_inc("q"), dataset_subset="RE3"), KEY[3], "ra_im1") is None
