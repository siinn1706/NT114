import pyarrow as pa
import pyarrow.parquet as pq

from fixtures import records as R
from rca import store


def _logs(n=1000):
    return pa.table({
        "ts_ns": pa.array([R.T0 + i * 10**6 for i in range(n)], pa.int64()),
        "entity_raw": ["cartservice"] * n, "service_id": ["cart"] * n,
        "level": [None if i % 7 == 0 else "info" for i in range(n)],
        "message": [f"msg {i} – ünïcode 日本" for i in range(n)],
        "src_file": pa.array([0] * n, pa.int32()), "src_row": pa.array(range(n), pa.int64()),
    })


def test_jsonl_is_deterministic_and_utf8(tmp_path):
    recs = [R.incident(uid="synth.00000000000000bb"), R.incident(uid="synth.00000000000000aa")]
    recs[0]["context"]["visible_text"] = "Cảnh báo 告警"
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    store.write_jsonl_atomic(a, recs)
    store.write_jsonl_atomic(b, list(reversed(recs)))
    assert a.read_bytes() == b.read_bytes()
    assert b"\r\n" not in a.read_bytes()
    got = store.read_jsonl(a)
    assert [r["incident_uid"] for r in got] == ["synth.00000000000000aa", "synth.00000000000000bb"]
    assert got[1]["context"]["visible_text"] == "Cảnh báo 告警"
    assert not list(tmp_path.glob("*.part"))


def test_parquet_roundtrip_keeps_int64_ns_and_nulls(tmp_path):
    t = store.sort_table(store.conform(_logs(), "logs"), "logs")
    p = tmp_path / "logs.parquet"
    store.write_parquet_atomic(p, t)
    back = pq.read_table(p)
    assert back.schema.field("ts_ns").type == pa.int64()
    assert back["ts_ns"][5].as_py() == R.T0 + 5 * 10**6
    assert back["level"].null_count == t["level"].null_count > 0
    assert back["message"][1].as_py() == "msg 1 – ünïcode 日本"
    assert pq.read_table(p, columns=["ts_ns"]).column_names == ["ts_ns"]  # lazy column read


def test_content_sha256_independent_of_batches_and_order():
    t = store.conform(_logs(), "logs")
    h1 = store.table_content_sha256(t, "logs")
    for size in (1, 7, 333):
        batches = t.to_batches(max_chunksize=size)
        assert store.table_content_sha256(pa.Table.from_batches(batches), "logs") == h1
    shuffled = t.take(pa.array(list(range(999, -1, -1))))
    assert store.table_content_sha256(shuffled, "logs") == h1
    changed = t.set_column(4, "message", pa.array(["x"] * t.num_rows))
    assert store.table_content_sha256(changed, "logs") != h1
    assert store.table_content_sha256(store.empty_table("traces"), "traces") == \
        store.table_content_sha256(store.empty_table("traces"), "traces")


def test_null_vs_empty_string_differ():
    a = store.conform(pa.table({"ts_ns": pa.array([1], pa.int64()), "message": [""]}), "logs")
    b = store.conform(pa.table({"ts_ns": pa.array([1], pa.int64()), "message": pa.array([None], pa.string())}), "logs")
    assert store.table_content_sha256(a, "logs") != store.table_content_sha256(b, "logs")


def test_canonical_store_reader(tmp_path):
    ds = tmp_path / "canonical" / "v1" / "synth"
    rec = R.incident()
    path = rec["telemetry"]["logs"]["path"]
    store.write_parquet_atomic(tmp_path / path, store.conform(_logs(10), "logs"))
    store.write_jsonl_atomic(ds / "visible" / "incidents.jsonl", [rec, R.incident(uid="synth.00000000000000ff", quality_state="REJECT")])
    store.write_jsonl_atomic(ds / "eval_only" / "labels.jsonl", [R.label()])
    store.write_json_atomic(ds / "_build.json", {"build_id": "b1"})
    cs = store.CanonicalStore(tmp_path)
    assert cs.datasets() == ["synth"]
    assert [r["incident_uid"] for r in cs.incidents("synth")] == [R.UID]
    assert len(cs.incidents("synth", states=None)) == 2
    assert cs.telemetry(R.UID, "logs").num_rows == 10
    assert cs.telemetry(R.UID, "traces") is None
    assert "root_cause" not in cs.incidents("synth")[0]
    assert cs.labels("synth")[R.UID]["root_cause"]["primary_root_service"] == "checkout"
