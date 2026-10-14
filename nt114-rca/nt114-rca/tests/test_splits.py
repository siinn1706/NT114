"""Grouping, protocols and immutable split manifests."""
from __future__ import annotations

import shutil
from collections import defaultdict
from datetime import datetime, timezone

from conftest import fixture_config
from rca import splits
from rca.store import CanonicalStore, read_json, read_jsonl, write_json_atomic
from test_adapter_rca100 import _build as _build_rca100

S = 10**9


def _it(uid, stream="s1", t=0, cell="c1", dup=None, hashes=(), system="sys", family="cpu", tier="A"):
    return {"uid": uid, "stream": stream, "anchor_ns": t * S, "cell": cell, "dup_of": dup, "hashes": list(hashes),
            "system": system, "family": family, "tier": tier}


def _parts(groups):
    by = defaultdict(set)
    for u, g in groups.items():
        by[g].add(u)
    return sorted(sorted(v) for v in by.values())


def test_physical_grouping_rules():
    items = [_it("a", t=0, cell="x"), _it("b", t=899, cell="y"),          # windows overlap (gap < 900 s)
             _it("c", t=5000, cell="x"), _it("d", t=5000, stream="s2", cell="z"),   # other stream: no overlap
             _it("e", t=20000, cell="w", dup="c"),                          # duplicate_of
             _it("f", t=40000, cell="v", hashes=["h1"]), _it("g", t=60000, cell="u", hashes=["h1"])]  # equal content
    assert _parts(splits.group_items(items, "physical")) == [["a", "b"], ["c", "e"], ["d"], ["f", "g"]]
    assert _parts(splits.group_items(items, "cell")) == [["a", "b", "c", "e"], ["d"], ["f", "g"]]
    assert splits.group_items(list(reversed(items)), "physical") == splits.group_items(items, "physical")


def test_window_boundary_is_pre_plus_post():
    assert len(set(splits.group_items([_it("a", t=0), _it("b", t=900)], "physical", 600, 300).values())) == 1
    assert len(set(splits.group_items([_it("a", t=0), _it("b", t=901)], "physical", 600, 300).values())) == 2


def test_grouped_fill_keeps_groups_whole_and_small_strata_in_test():
    items = [_it(f"u{i:03d}", stream=f"s{i}", t=i * 10**4, cell=f"c{i % 30}", family="cpu") for i in range(90)]
    items += [_it("rare1", stream="r", cell="r1", family="disk"), _it("rare2", stream="r2", cell="r2", family="disk")]
    groups = splits.group_items(items, "cell")
    split, extra = splits.grouped_fill(items, groups, seed=0)
    by_group = defaultdict(set)
    for u, s in split.items():
        by_group[groups[u]].add(s)
    assert all(len(s) == 1 for s in by_group.values())
    assert split["rare1"] == split["rare2"] == "test" and extra["incidents_in_whole_test_strata"] == 2
    n = {r: sum(1 for u, s in split.items() if s == r and not u.startswith("rare")) for r in ("train", "val", "test")}
    assert n == {"train": 54, "val": 18, "test": 18}
    assert splits.grouped_fill(items, groups, seed=0)[0] == split
    assert splits.grouped_fill(items, groups, seed=1)[0] != split


def _home_copy(rcaeval_home, tmp_path):
    dh = tmp_path / "dh"
    shutil.copytree(rcaeval_home / "canonical", dh / "canonical")
    return dh


def test_split_cmd_is_reproducible_and_immutable(rcaeval_home, tmp_path, capsys):
    dh = _home_copy(rcaeval_home, tmp_path)
    cfg = fixture_config()
    for proto in ("within-rcaeval-grouped", "within-rcaeval-retrieval", "loso-rcaeval", "eval-only-rcaeval"):
        assert splits.split_cmd(proto, 0, cfg, dh) in (0, 3)
    dirs = sorted(p.name for p in (dh / "splits").iterdir())
    assert len([d for d in dirs if d.startswith("loso-rcaeval-")]) == 3        # one fold per system
    before = {d: (dh / "splits" / d / "assignments.jsonl").read_bytes() for d in dirs}
    capsys.readouterr()
    splits.split_cmd("within-rcaeval-grouped", 0, cfg, dh)
    assert "exists" in capsys.readouterr().out
    assert sorted(p.name for p in (dh / "splits").iterdir()) == dirs
    assert {d: (dh / "splits" / d / "assignments.jsonl").read_bytes() for d in dirs} == before
    assert splits.verify_cmd(cfg, dh) == 0
    store = CanonicalStore(dh)
    for d in dirs:
        rows = read_jsonl(dh / "splits" / d / "assignments.jsonl")
        assert all(set(r) == {"incident_uid", "split", "group_id_hash"} for r in rows)
        uids = {r["incident_uid"] for r in rows}
        q = store.quality("rcaeval")
        assert all(q[u]["state"] in ("ACCEPT", "ACCEPT_WITH_WARNINGS") for u in uids)   # REJECT duplicate never enters
        m = read_json(dh / "splits" / d / "split.json")
        assert m["builds"][0]["build_id"] == store.build("rcaeval")["build_id"]
    ev = next(d for d in dirs if d.startswith("eval-only"))
    assert {r["split"] for r in read_jsonl(dh / "splits" / ev / "assignments.jsonl")} == {"test"}
    for d in (d for d in dirs if d.startswith("loso-")):
        m = read_json(dh / "splits" / d / "split.json")
        test_sys = m["params"]["fold"]
        inc = {r["incident_uid"]: r for r in store.incidents("rcaeval")}
        for r in read_jsonl(dh / "splits" / d / "assignments.jsonl"):
            assert (inc[r["incident_uid"]]["system"] == test_sys) == (r["split"] == "test")


def test_verify_detects_tampering_and_staleness(rcaeval_home, tmp_path):
    dh = _home_copy(rcaeval_home, tmp_path)
    cfg = fixture_config()
    splits.split_cmd("eval-only-rcaeval", 0, cfg, dh)
    d = next((dh / "splits").iterdir())
    store = CanonicalStore(dh)
    assert splits.verify_split(d, store) == []
    rows = (d / "assignments.jsonl").read_text(encoding="utf-8").splitlines()
    (d / "assignments.jsonl").write_text("\n".join(rows[1:]) + "\n", encoding="utf-8")
    assert "HASH_MISMATCH" in splits.verify_split(d, store)
    (d / "assignments.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")
    b = read_json(dh / "canonical/v1/rcaeval/_build.json")
    b["dataset_digest"] = "0" * 64
    write_json_atomic(dh / "canonical/v1/rcaeval/_build.json", b, indent=1)
    assert "STALE rcaeval" in splits.verify_split(d, CanonicalStore(dh))
    assert splits.verify_cmd(cfg, dh) == 4
    # re-running split after the rebuild re-pins the same assignments and keeps the stale manifest
    splits.split_cmd("eval-only-rcaeval", 0, cfg, dh)
    assert splits.verify_split(d, CanonicalStore(dh)) == [] and splits.verify_cmd(cfg, dh) == 0
    old = dh / "splits" / "_superseded" / f"{d.name}-{b['build_id']}"
    assert read_json(old / "split.json")["builds"][0]["dataset_digest"] != "0" * 64
    # (the restore above rewrote the old file with platform newlines, so compare lines, not bytes)
    assert (old / "assignments.jsonl").read_text(encoding="utf-8").splitlines() == \
        (d / "assignments.jsonl").read_text(encoding="utf-8").splitlines()


def test_store_reads_split_roles(rcaeval_home, tmp_path):
    dh = _home_copy(rcaeval_home, tmp_path)
    splits.split_cmd("eval-only-rcaeval", 0, fixture_config(), dh)
    d = next((dh / "splits").iterdir())
    store = CanonicalStore(dh)
    assert len(store.incidents("rcaeval", split_dir=d, role="test")) == len(read_jsonl(d / "assignments.jsonl"))
    assert store.incidents("rcaeval", split_dir=d, role="train") == []


def test_unknown_protocol_is_usage_error(rcaeval_home, tmp_path):
    dh = _home_copy(rcaeval_home, tmp_path)
    assert splits.split_cmd("random-rcaeval", 0, fixture_config(), dh) == 2
    assert splits.split_cmd("xdata-rcaeval-to-rcaeval", 0, fixture_config(), dh) == 2


def test_tier_b_never_trains_beside_a_held_out_group(monkeypatch):
    items = [{**_it(f"u{i:02d}", stream=f"s{i}", t=i * 10**4, cell=f"c{i}"), "dataset": "x", "group": None, "day": None}
             for i in range(30)]
    items += [{**it, "uid": it["uid"] + "b", "tier": "B", "hashes": ["h" + it["uid"]]} for it in items[:30]]
    for it in items[:30]:
        it["hashes"] = ["h" + it["uid"]]                  # each B record shares content with one A record
    monkeypatch.setattr(splits, "eligible", lambda store, d: items)
    (f,) = splits.build_assignments(None, "within-x-grouped", 0, fixture_config())
    rows = {r["incident_uid"]: r for r in f["assignments"]}
    a_role = {r["incident_uid"]: r["split"] for r in rows.values() if not r["incident_uid"].endswith("b")}
    for u, s in a_role.items():
        assert rows.get(u + "b", {}).get("split") == ("train" if s == "train" else None)
    assert f["extra"]["tier_b_dropped_held_out_group"] == sum(1 for s in a_role.values() if s != "train") > 0


def test_campaign_day_joins_incidents_across_streams():
    t = int(datetime(2025, 6, 5, 16, 30, tzinfo=timezone.utc).timestamp())      # 00:30 on 2025-06-06 at UTC+8
    assert splits._day("aiops2025", t * S) == "aiops2025/2025-06-06"
    assert splits._day("aiops2025", (t - 3600) * S) == "aiops2025/2025-06-05"
    assert splits._day("rcaeval", t * S) is None
    items = [_it("a", stream="s1", t=0, cell="x"), _it("b", stream="s2", t=50000, cell="y"), _it("c", stream="s3", cell="z")]
    items[0]["day"] = items[1]["day"] = "aiops2025/2025-06-06"
    assert _parts(splits.group_items(items, "physical")) == [["a", "b"], ["c"]]


def test_xdata_trains_on_one_dataset_and_tests_on_the_other(rcaeval_home, tmp_path, capsys):
    h = _build_rca100(tmp_path / "dh")
    dh = h["dh"]
    shutil.copytree(rcaeval_home / "canonical/v1/rcaeval", dh / "canonical/v1/rcaeval")
    cfg = fixture_config()
    assert splits.split_cmd("xdata-rcaeval-to-rca100", 0, cfg, dh) in (0, 3)
    (d,) = [p for p in (dh / "splits").iterdir() if p.name.startswith("xdata-")]
    m = read_json(d / "split.json")
    store = CanonicalStore(dh)
    assert [b["dataset_id"] for b in m["builds"]] == ["rcaeval", "rca100"]
    assert m["counts"]["train_dataset"] == "rcaeval" and m["counts"]["test_dataset"] == "rca100"
    rows = read_jsonl(d / "assignments.jsonl")
    tier_a = {u for u, lab in store.labels("rca100").items() if lab["eval_tier"] == "A"}
    assert {r["incident_uid"] for r in rows if r["split"] == "test"} == tier_a & {i["incident_uid"] for i in store.incidents("rca100")}
    train = {r["incident_uid"] for r in rows if r["split"] == "train"}
    assert train and all(u.startswith("rcaeval.") for u in train)
    assert splits.verify_cmd(cfg, dh) == 0
    capsys.readouterr()
    splits.split_cmd("xdata-rcaeval-to-rca100", 0, cfg, dh)
    assert "exists" in capsys.readouterr().out
