import io
import tarfile

from rca import profile
from rca.identity import pod_pattern


def test_time_unit_classification():
    assert profile.classify_time_unit([1705354566, 1705354567]) == "s"
    assert profile.classify_time_unit(["1705354566000"]) == "ms"
    assert profile.classify_time_unit([1705354566000000]) == "us"
    assert profile.classify_time_unit([1705354566000000000]) == "ns"
    assert profile.classify_time_unit(["2025-06-05T16:10:02Z"]) == "iso8601"
    assert profile.classify_time_unit([12, 13]) == "unknown"
    assert profile.classify_time_unit([]) == "unknown"


def test_iso_parsing_and_go_style():
    assert profile.parse_iso_ns("2025-06-05T16:10:02Z") == 1749139802 * 10**9
    assert profile.parse_iso_ns("2022-08-22 03:51:19.607158889 +0000 UTC m=+0.113") == 1661140279_607158889
    assert profile.parse_iso_ns("2026-04-25T05:18:12.716735+00:00") == 1777094292_716735000
    assert profile.parse_iso_ns("2025-06-06T08:00:00+08:00") == profile.parse_iso_ns("2025-06-06T00:00:00Z")
    assert profile.parse_iso_ns("not a time") is None


def test_constant_offset_detects_nezha_shift():
    times = [profile.parse_iso_ns(f"2022-08-22 03:5{i}:19 +0000 UTC") for i in range(5)]
    stamps = [t + 2 * 10**8 * 10**9 for t in times]
    r = profile.constant_offset_s(times, stamps)
    assert r["constant"] and r["median_offset_s"] == 2e8
    assert not profile.constant_offset_s(times, [times[0]] * 5)["constant"]


def test_pod_pattern_classifier():
    assert pod_pattern("frontend-579b9bff58-t2dbm") == "deployment"
    assert pod_pattern("paymentservice-1") == "statefulset"
    assert pod_pattern("checkoutservice") == "plain"


def test_tar_stream_never_writes(tmp_path):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for name, data in (("a/x.json", b'{"k":1}'), ("a/big.bin", b"0" * 5000)):
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            t.addfile(ti, io.BytesIO(data))
    p = tmp_path / "arc.tar.gz"
    p.write_bytes(buf.getvalue())
    before = sorted(x.name for x in tmp_path.iterdir())
    got = {m.name: d for m, d in profile.iter_tar_stream(p, want=lambda n: True, max_bytes=1000)}
    assert got == {"a/x.json": b'{"k":1}', "a/big.bin": None}
    assert sorted(x.name for x in tmp_path.iterdir()) == before


def test_group_counts_chain_overlapping_windows():
    items = [{"key": str(i), "stream": "d1", "anchor_s": 1000 + 480 * i, "cell": f"c{i % 2}"} for i in range(10)]
    phys = profile.count_groups(items, rule="physical")
    assert phys["groups"] == 1 and phys["largest_group"] == 10
    spaced = [{**it, "anchor_s": 1000 + 5000 * i} for i, it in enumerate(items)]
    assert profile.count_groups(spaced, rule="physical")["groups"] == 10
    assert profile.count_groups(spaced, rule="cell")["groups"] == 2


def test_parquet_time_stats_skip_nested_leaves():
    import io
    import pyarrow as pa
    import pyarrow.parquet as pq
    from rca.profile import _parquet_time_stats
    t = pa.table({"spanID": ["a", "b"],
                  "references": [[{"refType": "x", "spanID": "zz"}], []],
                  "startTime": pa.array([1749150000000000, 1749150060000000], pa.int64())})
    buf = io.BytesIO()
    pq.write_table(t, buf)
    st = _parquet_time_stats(buf.getvalue())["time"]
    assert st == {"startTime": {"min": "1749150000000000", "max": "1749150060000000"}}


def test_matrix_tiers_follow_gates(tmp_path):
    import json
    pdir = tmp_path / "reports" / "profile"
    pdir.mkdir(parents=True)
    (pdir / "nezha.json").write_text(json.dumps({"incidents": 10, "gate": {"result": "fail", "window_mlt": 7}}))
    (pdir / "agenticopseval.json").write_text(json.dumps({
        "AIOps2025": {"instance_type": {"service": 3, "pod": 2, "node": 1},
                      "gate": {"result": "pass", "archive_name_tz_offset_h": [8], "covered": 5, "natural_absent": 1}},
        "RCA100": {"gate": "fail", "service_resolvable": 1, "incidents": 4, "gate_threshold": 0.8}}))
    (pdir / "msds.json").write_text(json.dumps({"gate": "fail", "gate_reason": "no label"}))
    rows = {(r["source_id"], r["subset"]): r for r in profile.matrix(tmp_path)["rows"]}
    assert rows[("nezha", None)]["tier"] == "A" and rows[("nezha", None)]["gate"] == "fail"
    assert rows[("agenticopseval", "AIOps2025 service+pod")]["tier"] == "A"
    assert rows[("agenticopseval", "AIOps2025 service+pod")]["incidents"] == 5
    assert rows[("agenticopseval", "AIOps2025 node")]["tier"] == "B"
    assert rows[("agenticopseval", "RCA100")]["tier"] == "B"
    assert rows[("msds", None)]["tier"] == "C"
    assert all(r["tier"] in "ABC" and "incidents" in r for r in rows.values())
