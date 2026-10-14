"""Deterministic readers and writers for the canonical store.

Record files are JSON Lines (UTF-8, LF, sorted keys, sorted by `incident_uid`); telemetry is one
Parquet file per incident and modality with a fixed Arrow schema. Every write goes to a temporary
file first and is moved into place with `os.replace`.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Iterable, Iterator

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from .schema import MODALITIES, SPLIT_STATES

# ---------------------------------------------------------------- Arrow schemas (canonical v1)
_STR = pa.string()
METRICS_SCHEMA = pa.schema([
    ("ts_ns", pa.int64()), ("entity_raw", _STR), ("entity_kind", _STR), ("service_id", _STR),
    ("metric", _STR), ("metric_set", _STR), ("value", pa.float64()), ("unit", _STR),
    ("src_file", pa.int32()), ("src_row", pa.int64()), ("src_col", pa.int32()),
])
LOGS_SCHEMA = pa.schema([
    ("ts_ns", pa.int64()), ("entity_raw", _STR), ("service_id", _STR), ("level", _STR),
    ("message", _STR), ("template", _STR), ("trace_id", _STR), ("span_id", _STR),
    ("src_file", pa.int32()), ("src_row", pa.int64()),
])
TRACES_SCHEMA = pa.schema([
    ("ts_ns", pa.int64()), ("duration_ns", pa.int64()), ("trace_id", _STR), ("span_id", _STR),
    ("parent_span_id", _STR), ("entity_raw", _STR), ("service_id", _STR), ("operation", _STR),
    ("status_code", _STR), ("src_file", pa.int32()), ("src_row", pa.int64()),
])
SCHEMAS = {"metrics": METRICS_SCHEMA, "logs": LOGS_SCHEMA, "traces": TRACES_SCHEMA}
# Sort keys; src_file/src_row make the order total, so the stored row order never depends on batching.
SORT_KEYS = {
    "metrics": ["metric_set", "service_id", "metric", "ts_ns", "src_file", "src_row", "src_col"],
    "logs": ["ts_ns", "src_file", "src_row"],
    "traces": ["ts_ns", "src_file", "src_row"],
}
PARQUET_DEFAULTS = {"compression": "zstd", "compression_level": 3, "row_group_rows": 1_000_000}


# ---------------------------------------------------------------- JSON
def dump_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def write_text_atomic(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)


def write_json_atomic(path: Path, obj, indent: int | None = None) -> None:
    text = dump_json(obj) if indent is None else json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=indent)
    write_text_atomic(path, text + "\n")


def write_jsonl_atomic(path: Path, records: Iterable[dict], key: str | None = "incident_uid") -> None:
    recs = list(records)
    if key:
        recs.sort(key=lambda r: r[key])
    write_text_atomic(path, "".join(dump_json(r) + "\n" for r in recs))


def read_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------- tables
def empty_table(modality: str) -> pa.Table:
    return SCHEMAS[modality].empty_table()


def conform(batch: pa.RecordBatch | pa.Table, modality: str) -> pa.Table:
    """Cast to the canonical schema; columns missing from `batch` become null."""
    schema = SCHEMAS[modality]
    t = batch if isinstance(batch, pa.Table) else pa.Table.from_batches([batch])
    cols = []
    for f in schema:
        if f.name in t.column_names:
            c = t[f.name]
            if pa.types.is_dictionary(c.type):
                c = c.cast(c.type.value_type)
            cols.append(c.cast(f.type))
        else:
            cols.append(pa.nulls(t.num_rows, f.type))
    return pa.Table.from_arrays(cols, schema=schema)


def sort_table(t: pa.Table, modality: str) -> pa.Table:
    if t.num_rows == 0:
        return t
    idx = pc.sort_indices(t, sort_keys=[(k, "ascending", "at_start") for k in SORT_KEYS[modality]])
    return t.take(idx).combine_chunks()


def _validity_bytes(arr: pa.Array) -> bytes:
    valid = np.asarray(pc.is_valid(arr).to_numpy(zero_copy_only=False), dtype=bool)
    return np.packbits(valid, bitorder="little").tobytes()


def table_content_sha256(t: pa.Table, modality: str) -> str:
    """sha256 of a canonical row serialization: independent of Arrow chunking, IPC framing and
    Parquet writer bytes. Rows are sorted by the modality sort key; then for every column in
    schema order: name, Arrow type string, validity bitmap (LSB first), and values. Fixed-width
    values are little-endian with nulls zeroed; strings are int64 little-endian lengths followed
    by the concatenated UTF-8 bytes (nulls have length 0)."""
    t = sort_table(conform(t, modality), modality)
    h = hashlib.sha256()
    h.update(f"rows={t.num_rows}".encode())
    for f in t.schema:
        col = t[f.name]
        arr = col.combine_chunks() if col.num_chunks != 1 else col.chunk(0)
        h.update(f.name.encode() + b"\x00" + str(f.type).encode() + b"\x00")
        h.update(_validity_bytes(arr))
        if pa.types.is_string(f.type) or pa.types.is_large_string(f.type):
            filled = pc.fill_null(arr, "")
            lengths = pc.binary_length(filled).to_numpy(zero_copy_only=False).astype("<i8")
            h.update(lengths.tobytes())
            h.update(_string_data(filled))
        else:
            zero = pa.scalar(0, f.type)
            vals = pc.fill_null(arr, zero).to_numpy(zero_copy_only=False)
            h.update(np.ascontiguousarray(vals.astype(vals.dtype.newbyteorder("<"))).tobytes())
    return h.hexdigest()


def _string_data(arr: pa.Array) -> bytes:
    arr = pa.concat_arrays([arr]).cast(pa.large_string())
    bufs = arr.buffers()
    offs = np.frombuffer(bufs[1], dtype="<i8")[arr.offset: arr.offset + len(arr) + 1]
    return bufs[2].to_pybytes()[offs[0]:offs[-1]] if bufs[2] is not None else b""


def write_parquet_atomic(path: Path, t: pa.Table, parquet_cfg: dict | None = None) -> None:
    cfg = {**PARQUET_DEFAULTS, **(parquet_cfg or {})}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    pq.write_table(t, tmp, compression=cfg["compression"], compression_level=cfg["compression_level"],
                   row_group_size=cfg["row_group_rows"], write_statistics=True, store_schema=False)
    os.replace(tmp, path)


class TableBuffer:
    """Collects batches of one modality for one incident, then filters, sorts and writes once.

    One incident is the unit of memory (design: peak memory = largest incident member)."""

    def __init__(self, modality: str):
        self.modality = modality
        self.parts: list[pa.Table] = []
        self.rows_in = 0

    def add(self, batch) -> None:
        t = conform(batch, self.modality)
        self.rows_in += t.num_rows
        if t.num_rows:
            self.parts.append(t)

    def table(self) -> pa.Table:
        if not self.parts:
            return empty_table(self.modality)
        return pa.concat_tables(self.parts)


# ---------------------------------------------------------------- reader
class CanonicalStore:
    """Read access to `canonical/v1`. `incidents()` returns visible records only (no labels)."""

    def __init__(self, data_home: Path, canonical: str = "canonical/v1"):
        self.data_home = Path(data_home)
        self.root = self.data_home / canonical
        self._inc: dict[str, list[dict]] = {}

    def datasets(self) -> list[str]:
        if not self.root.is_dir():
            return []
        return sorted(p.name for p in self.root.iterdir() if (p / "_build.json").is_file())

    def build(self, dataset: str) -> dict:
        return read_json(self.root / dataset / "_build.json")

    def _incidents(self, dataset: str) -> list[dict]:
        if dataset not in self._inc:
            self._inc[dataset] = read_jsonl(self.root / dataset / "visible" / "incidents.jsonl")
        return self._inc[dataset]

    def incidents(self, dataset: str, states=SPLIT_STATES, split_dir: Path | None = None,
                  role: str | None = None) -> list[dict]:
        recs = [r for r in self._incidents(dataset) if states is None or r["quality_state"] in states]
        if split_dir is not None:
            roles = {a["incident_uid"]: a["split"] for a in read_jsonl(Path(split_dir) / "assignments.jsonl")}
            recs = [r for r in recs if r["incident_uid"] in roles and (role is None or roles[r["incident_uid"]] == role)]
        return recs

    def incident(self, uid: str) -> dict:
        ds = uid.split(".", 1)[0]
        for r in self._incidents(ds):
            if r["incident_uid"] == uid:
                return r
        raise KeyError(uid)

    def telemetry(self, uid: str, modality: str, columns: list[str] | None = None,
                  filters=None) -> pa.Table | None:
        mi = self.incident(uid)["telemetry"][modality]
        if mi["status"] != "present":
            return None
        return pq.read_table(self.data_home / mi["path"], columns=columns, filters=filters)

    def service_map(self, dataset: str) -> dict:
        return read_json(self.root / dataset / "visible" / "service_map.json")

    # eval-only zone: only scoring, ablation-target choice and split code may call these
    def labels(self, dataset: str) -> dict[str, dict]:
        return {r["incident_uid"]: r for r in read_jsonl(self.root / dataset / "eval_only" / "labels.jsonl")}

    def quality(self, dataset: str) -> dict[str, dict]:
        return {r["incident_uid"]: r for r in read_jsonl(self.root / dataset / "eval_only" / "quality.jsonl")}

    def source_index(self, dataset: str) -> dict[str, dict]:
        return {r["incident_uid"]: r for r in read_jsonl(self.root / dataset / "eval_only" / "source_index.jsonl")}


def iter_present(store: CanonicalStore, dataset: str) -> Iterator[tuple[dict, str]]:
    for r in store.incidents(dataset, states=None):
        for m in MODALITIES:
            if r["telemetry"][m]["status"] == "present":
                yield r, m
