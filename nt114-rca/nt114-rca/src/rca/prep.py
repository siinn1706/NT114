"""Data-preparation CLI and build driver.

  python -m rca.prep status
  python -m rca.prep profile   --source rcaeval-zenodo
  python -m rca.prep extract   --source agenticopseval --member-glob 'AIOps2025/*.tar.gz'
  python -m rca.prep normalize --dataset rcaeval [--limit N] [--incident UID] [--force]
  python -m rca.prep validate  --dataset rcaeval
  python -m rca.prep audit [--evidence-stats]
  python -m rca.prep conditions --dataset rcaeval
  python -m rca.prep eval-units --dataset rca100
  python -m rca.prep split --protocol within-rcaeval-grouped --seed 0
  python -m rca.prep verify-splits
  python -m rca.prep export --bundle nt114-data-v1
  python -m rca.prep verify-bundle <dir> [--deep]

Exit codes: 0 ok, 2 usage, 3 finished with QUARANTINE/REJECT items that need attention,
4 integrity failure, 5 precondition missing.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import copy
import ctypes
import hashlib
import json
import os
import sys
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import yaml

from . import adapters as adapter_registry
from .adapters.base import BuildContext, DiscoveredIncident, Finding, LabelDraft, ModalityAbsent, TimeInfo
from .identity import ServiceMap
from .quality import (finding, invariant_findings, load_overrides, quality_record, roll_up, validate_incident)
from .schema import MODALITIES, SCHEMA_VERSION, TS_MAX_NS, TS_MIN_NS, make_incident_uid
from .store import (SCHEMAS, TableBuffer, dump_json, read_json, read_jsonl, sort_table, table_content_sha256,
                    write_json_atomic, write_jsonl_atomic, write_parquet_atomic, write_text_atomic)

RCA_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = RCA_ROOT / "configs" / "prep.yaml"
OVERRIDES = RCA_ROOT / "configs" / "quality_overrides.yaml"
ALIASES = RCA_ROOT / "configs" / "service_aliases.yaml"
EXIT_OK, EXIT_USAGE, EXIT_ATTENTION, EXIT_INTEGRITY, EXIT_PRECONDITION = 0, 2, 3, 4, 5


class ParseFailure(Exception):
    """A whole member could not be parsed; the modality becomes `corrupted`."""


# ---------------------------------------------------------------- config and paths
def load_config(path: Path | None = None) -> dict:
    with open(path or DEFAULT_CONFIG, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    cfg = copy.deepcopy(cfg)
    cfg.setdefault("processing", {}).setdefault("max_workers", 2)
    cfg["processing"].setdefault("chunk_rows", 500_000)
    cfg.setdefault("windows", {}).setdefault("evidence", {"pre_s": 600, "post_s": 300})
    cfg["_hash"] = config_hash(cfg)
    return cfg


def config_hash(cfg: dict) -> str:
    """Hash of everything that shapes per-incident output: the config (without the machine-specific
    data home and the `evidence` section, which only shapes evidence text built later from the
    canonical store) and the reviewed service aliases."""
    body = copy.deepcopy({k: v for k, v in cfg.items() if not k.startswith("_") and k != "evidence"})
    if isinstance(body.get("paths"), dict):
        body["paths"].pop("data_home", None)   # machine-specific; must not change the hash
    from .identity import load_aliases
    body["_service_aliases"] = load_aliases(ALIASES)
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode()).hexdigest()


def resolve_data_home(cli_value: str | None, cfg: dict) -> Path:
    v = cli_value or os.environ.get("RCA_DATA_HOME") or (cfg.get("paths") or {}).get("data_home")
    return Path(v).resolve() if v else (RCA_ROOT / "data").resolve()


def paths(cfg: dict, data_home: Path) -> dict[str, Path]:
    p = {"raw": "raw", "work": "work", "canonical": "canonical/v1", "splits": "splits", "reports": "reports",
         "export": "export", **{k: v for k, v in (cfg.get("paths") or {}).items() if k != "data_home" and v}}
    return {k: data_home / v for k, v in p.items()}


def rel(p: Path, data_home: Path) -> str:
    return Path(p).resolve().relative_to(data_home.resolve()).as_posix()


def peak_rss_bytes() -> int | None:
    try:
        if sys.platform == "win32":
            class PMC(ctypes.Structure):
                _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
            pmc = PMC()
            pmc.cb = ctypes.sizeof(PMC)
            h = ctypes.windll.kernel32.GetCurrentProcess()
            if ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
                return int(pmc.PeakWorkingSetSize)
            return None
        import resource
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    except Exception:
        return None


# ---------------------------------------------------------------- per-incident processing
def _window_filter(t: pa.Table, tinfo: TimeInfo) -> tuple[pa.Table, int]:
    if t.num_rows == 0 or (tinfo.window_start_ns is None and tinfo.window_end_ns is None):
        return t, 0
    ts = t["ts_ns"]
    mask = pc.and_(pc.greater_equal(ts, tinfo.window_start_ns), pc.less_equal(ts, tinfo.window_end_ns))
    kept = t.filter(mask)
    return kept, t.num_rows - kept.num_rows


def _coverage(ts_ns: np.ndarray, lo: int, hi: int, bucket_s: int = 60) -> float | None:
    if hi is None or lo is None or hi <= lo or len(ts_ns) == 0:
        return None
    n_buckets = (hi - lo) // (bucket_s * 10**9) + 1
    b = (ts_ns - lo) // (bucket_s * 10**9)
    b = b[(b >= 0) & (b < n_buckets)]
    return round(len(np.unique(b)) / n_buckets, 4)


def _empty_modality(status: str, notes=()) -> dict:
    return {"status": status, "path": None, "rows": 0, "services": [], "t_min_ns": None, "t_max_ns": None,
            "coverage": None, "metric_sets": [], "content_sha256": None, "notes": sorted(set(notes))}


def _label_record(uid: str, inc: DiscoveredIncident, lab: LabelDraft) -> dict:
    return {
        "incident_uid": uid, "source_incident_id": inc.source_incident_id,
        "root_cause": {"original": lab.original, "entities": lab.entities, "root_service_ids": sorted(set(lab.root_service_ids)),
                       "primary_root_service": lab.primary_root_service, "label_granularity": lab.label_granularity},
        "fault": {"type_raw": lab.fault_type_raw, "family": lab.fault_family}, "label_source": lab.label_source,
        "injection_kind": lab.injection_kind, "label_validity": lab.label_validity, "validity_notes": lab.validity_notes,
        "eval_tier": lab.eval_tier, "eval_tier_reason": lab.eval_tier_reason,
        "group": {"fault_cell": lab.fault_cell, "copy_of": lab.copy_of, "duplicate_of": None, "group_id": lab.group_key},
        "label_artifacts": lab.label_artifacts, "truth_time": {"end_ns": lab.truth_end_ns},
    }


def input_digest(inc: DiscoveredIncident) -> str:
    items = sorted(f"{role}|{r.source_id}|{r.member}|{r.size}|{r.sha256}|{r.crc32}" for role, refs in inc.refs.items() for r in refs)
    return hashlib.sha256("\n".join(items).encode()).hexdigest()


def process_incident(adapter, inc: DiscoveredIncident, uid: str, ctx: BuildContext, digest: str) -> dict:
    """Run the adapter for one incident, write its telemetry, return the per-incident record."""
    t0 = time.time()
    findings: list[Finding] = []
    ledger = {"incident_uid": uid, "rows_in": {}, "rows_out": {}, "dropped": {}}
    smap = adapter.service_map(ctx)
    lab, f = adapter.read_label(inc, ctx)
    findings += f
    tinfo, f = adapter.anchor_and_window(inc, lab, ctx)
    findings += f
    tel_dir = paths(ctx.config, ctx.data_home)["canonical"] / adapter.dataset_id / "visible" / "telemetry" / uid
    tel, stats, services = {}, {}, {}
    parquet_cfg = (ctx.config.get("processing") or {}).get("parquet")
    tables = {}
    for m in MODALITIES:
        st: dict = {"rows": 0}
        notes: list[str] = []
        try:
            buf = TableBuffer(m)
            for b in adapter.normalize(inc, m, tinfo, smap, ctx, findings):
                buf.add(b)
            t = buf.table()
        except ModalityAbsent:
            tel[m] = _empty_modality("natural_absent")
            stats[m] = st
            continue
        except ParseFailure as e:
            findings.append(finding("PARSE_ERROR", f"whole member unparseable: {e}", m, "quarantine"))
            tel[m] = _empty_modality("corrupted", ["PARSE_ERROR"])
            stats[m] = st
            continue
        ledger["rows_in"][m] = t.num_rows
        nulls = t["ts_ns"].null_count
        if nulls:
            findings.append(finding("PARSE_ERROR", f"{nulls} rows without a parseable timestamp dropped", m))
            t = t.filter(pc.is_valid(t["ts_ns"]))
        oor = pc.or_(pc.less(t["ts_ns"], TS_MIN_NS), pc.greater_equal(t["ts_ns"], TS_MAX_NS))
        n_oor = pc.sum(oor).as_py() or 0
        if n_oor:
            st["ts_out_of_range"] = n_oor
            t = t.filter(pc.invert(oor))
        t, n_out = _window_filter(t, tinfo)
        ledger["dropped"][m] = {"null_ts": nulls, "ts_out_of_range": n_oor, "outside_window": n_out}
        tables[m] = t
        st["rows"] = t.num_rows
        stats[m] = st
    # window for pre-cut sources is the union of observed ranges
    observed = [(pc.min(t["ts_ns"]).as_py(), pc.max(t["ts_ns"]).as_py()) for t in tables.values() if t.num_rows]
    w_lo = tinfo.window_start_ns if tinfo.window_start_ns is not None else (min(o[0] for o in observed) if observed else None)
    w_hi = tinfo.window_end_ns if tinfo.window_end_ns is not None else (max(o[1] for o in observed) if observed else None)
    for m, t in tables.items():
        if t.num_rows == 0:
            tel[m] = _empty_modality("empty", ["EMPTY_MODALITY_FILE"])
            continue
        t = sort_table(t, m)
        path = tel_dir / f"{m}.parquet"
        write_parquet_atomic(path, t, parquet_cfg)
        ts = t["ts_ns"].to_numpy()
        svcs = sorted(x for x in pc.unique(t["service_id"]).to_pylist() if x)
        services[m] = svcs
        if m == "metrics":
            for ms in pc.unique(t["metric_set"]).to_pylist():
                sub = t.filter(pc.equal(t["metric_set"], ms))
                services[f"metrics:{ms}"] = sorted(x for x in pc.unique(sub["service_id"]).to_pylist() if x)
            vals = t["value"].to_numpy(zero_copy_only=False)
            stats[m]["nonfinite"] = int(np.count_nonzero(~np.isfinite(np.asarray(vals, dtype=float))))
        if m == "logs":
            stats[m]["has_level"] = t["level"].null_count < t.num_rows
        if m == "traces":
            span_ids = set(pc.unique(t["span_id"]).to_pylist())
            parents = t["parent_span_id"].to_pylist()
            stats[m]["orphan_spans"] = sum(1 for p in parents if p is not None and p not in span_ids)
        tel[m] = {"status": "present", "path": rel(path, ctx.data_home), "rows": t.num_rows, "services": svcs,
                  "t_min_ns": int(ts.min()), "t_max_ns": int(ts.max()), "coverage": _coverage(ts, w_lo, w_hi),
                  "metric_sets": sorted(x for x in pc.unique(t["metric_set"]).to_pylist() if x) if m == "metrics" else [],
                  "content_sha256": table_content_sha256(t, m), "notes": []}
        ledger["rows_out"][m] = t.num_rows
    for f_ in findings:
        if f_.modality in tel and f_.code not in tel[f_.modality]["notes"]:
            tel[f_.modality]["notes"] = sorted(set(tel[f_.modality]["notes"]) | {f_.code})
    cands, csource = adapter.candidates(inc, services, smap, lab.system)
    rec = {
        "schema_version": SCHEMA_VERSION, "incident_uid": uid, "dataset_id": adapter.dataset_id,
        "dataset_subset": lab.dataset_subset, "dataset_version": inc.hints.get("dataset_version", ""),
        "source_id": inc.hints.get("source_id", adapter.source_ids[0] if adapter.source_ids else ""),
        "lineage_group": lab.lineage_group, "system": lab.system,
        "time": {"anchor_ns": tinfo.anchor_ns, "anchor_kind": tinfo.anchor_kind, "anchor_original": tinfo.anchor_original,
                 "end_ns": tinfo.end_ns, "window": {"start_ns": w_lo, "end_ns": w_hi,
                                                     "clipped_start": tinfo.clipped_start, "clipped_end": tinfo.clipped_end}},
        "candidates": {"services": cands, "source": csource}, "telemetry": tel,
        "context": {"visible_text": inc.hints.get("visible_text")},
        "repro": {"adapter": {"name": adapter.name, "version": adapter.version}, "build_id": "pending",
                  "config_hash": ctx.config["_hash"], "input_digest": digest},
        "quality_state": "ACCEPT",
    }
    label = _label_record(uid, inc, lab)
    members = []
    for role, refs in sorted(inc.refs.items()):
        for r in refs:
            members.append({"role": role, "source_id": r.source_id, "member": r.member,
                            "sha256": inc.hints.get("member_sha256", {}).get(r.member, r.sha256), "size": r.size})
    src = {"incident_uid": uid, "source_incident_id": inc.source_incident_id, "source_incident_key": inc.source_incident_key,
           "members": members, "label_files": [r.member for r in inc.refs.get("label", [])]}
    findings += validate_incident(rec, label, stats, ctx.config)
    ledger.update(seconds=round(time.time() - t0, 2), peak_rss=peak_rss_bytes())
    return {"incident": rec, "label": label, "source_index": src, "findings": [f.to_json() for f in findings],
            "stats": stats, "service_map": smap.to_json(), "dup_key": lab.duplicate_of_key, "ledger": ledger,
            "marker": {"input_digest": digest, "config_hash": ctx.config["_hash"], "adapter_version": adapter.version}}


def _worker(dataset_id: str, adapter_cls, inc, uid, ctx, digest, rec_path: str):
    adapter = adapter_cls()
    try:
        try:
            out = process_incident(adapter, inc, uid, ctx, digest)
        except Exception as e:  # recorded, never silent: QUARANTINE + exit 3
            tb = traceback.format_exc()
            out = {"exception": f"{type(e).__name__}: {e}", "traceback_sha256": hashlib.sha256(tb.encode()).hexdigest(),
                   "traceback": tb[-4000:], "marker": {"input_digest": digest, "config_hash": ctx.config["_hash"],
                                                        "adapter_version": adapter.version}}
        write_json_atomic(Path(rec_path), out)
        write_json_atomic(Path(rec_path).with_suffix(".done"), out["marker"])
        return uid, "exception" in out
    finally:
        adapter.close()


def _marker_valid(rec_path: Path, digest: str, cfg_hash: str, version: str) -> bool:
    done = rec_path.with_suffix(".done")
    if not (done.is_file() and rec_path.is_file()):
        return False
    m = read_json(done)
    return m == {"input_digest": digest, "config_hash": cfg_hash, "adapter_version": version}


def build_dataset(dataset_id: str, cfg: dict, data_home: Path, limit: int | None = None, only_uid: str | None = None,
                  force: bool = False, adapter_cls=None, max_workers: int | None = None, log=print) -> dict:
    adapter_cls = adapter_cls or adapter_registry.get(dataset_id)
    P = paths(cfg, data_home)
    built = P["canonical"] / dataset_id / "_build.json"
    if (limit or only_uid) and built.is_file() and not read_json(built)["counts"].get("partial"):
        # A partial build rewrites the dataset with a subset; it must not replace a full release.
        raise RuntimeError(f"{built} is a full build: run a partial build (--limit/--uid) with a separate --data-home")
    ds_cfg = (cfg.get("datasets") or {}).get(dataset_id, {})
    ctx = BuildContext(data_home=data_home, raw_root=P["raw"], config=cfg, dataset_cfg=ds_cfg, work=P["work"])
    adapter = adapter_cls()
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    incs = sorted(adapter.discover(ctx), key=lambda i: i.source_incident_key)
    keys = [i.source_incident_key for i in incs]
    if len(set(keys)) != len(keys):
        dup = [k for k, n in Counter(keys).items() if n > 1]
        raise RuntimeError(f"source incident keys are not unique: {dup[:5]}")
    uid_of = {i.source_incident_key: make_incident_uid(dataset_id, i.source_incident_key) for i in incs}
    if len(set(uid_of.values())) != len(uid_of):
        raise RuntimeError("incident_uid collision")
    todo = sorted(incs, key=lambda i: uid_of[i.source_incident_key])
    if only_uid:
        todo = [i for i in todo if uid_of[i.source_incident_key] == only_uid]
    if limit:
        todo = todo[:limit]
    run_dir = P["work"] / "runs" / dataset_id
    rec_dir = run_dir / "records"
    rec_dir.mkdir(parents=True, exist_ok=True)
    digests = {i.source_incident_key: input_digest(i) for i in todo}
    jobs = []
    skipped = 0
    for inc in todo:
        uid = uid_of[inc.source_incident_key]
        rp = rec_dir / f"{uid}.json"
        if not force and _marker_valid(rp, digests[inc.source_incident_key], cfg["_hash"], adapter.version):
            skipped += 1
            continue
        jobs.append((dataset_id, adapter_cls, inc, uid, ctx, digests[inc.source_incident_key], str(rp)))
    log(f"{dataset_id}: {len(todo)} incidents, {skipped} up to date, {len(jobs)} to build")
    workers = max_workers if max_workers is not None else int(cfg["processing"]["max_workers"])
    n_exc = 0
    if workers <= 1 or len(jobs) <= 1:
        for k, j in enumerate(jobs, 1):
            _, exc = _worker(*j)
            n_exc += exc
            log(f"  [{k}/{len(jobs)}] {j[3]}{' EXCEPTION' if exc else ''}")
    else:
        with cf.ProcessPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_worker, *j): j[3] for j in jobs}
            for k, fu in enumerate(cf.as_completed(futs), 1):
                uid, exc = fu.result()
                n_exc += exc
                log(f"  [{k}/{len(jobs)}] {uid}{' EXCEPTION' if exc else ''}")
    adapter.close()
    uids = [uid_of[i.source_incident_key] for i in todo]
    receipt = finalize(dataset_id, adapter, cfg, data_home, uids, uid_of, started, partial=bool(limit or only_uid))
    receipt["exceptions"] = n_exc
    return receipt


# ---------------------------------------------------------------- finalize
def _exception_record(uid: str, rec: dict) -> dict:
    """Records for incidents whose adapter raised: kept, QUARANTINE, so nothing disappears silently."""
    return {"exception": rec["exception"], "traceback_sha256": rec["traceback_sha256"]}


def finalize(dataset_id: str, adapter, cfg: dict, data_home: Path, uids: list[str], uid_of: dict, started: str,
             partial: bool = False) -> dict:
    P = paths(cfg, data_home)
    rec_dir = P["work"] / "runs" / dataset_id / "records"
    if not partial:   # a full build covers every discovered incident
        uids = sorted(set(uid_of.values()))
    records = {u: read_json(rec_dir / f"{u}.json") for u in sorted(uids)}
    exc = {u: r for u, r in records.items() if "exception" in r}
    good = {u: r for u, r in records.items() if "exception" not in r}
    # merged service map and dataset-level identity checks
    smap = ServiceMap()
    for r in good.values():
        for system, entries in r["service_map"].items():
            for raw, e in entries.items():
                smap.entries[system].setdefault(raw, e)
    collisions = {s: smap.collisions(s) for s in list(smap.entries)}
    key_to_uid = dict(uid_of)
    overrides = load_overrides(OVERRIDES)
    inc_out, lab_out, q_out, src_out = [], [], [], []
    for u, r in good.items():
        inc, lab, src = r["incident"], r["label"], r["source_index"]
        fnd = [dict(f) for f in r["findings"]]
        if r.get("dup_key"):
            dup_uid = key_to_uid.get(r["dup_key"])
            lab["group"]["duplicate_of"] = dup_uid
            fnd.append(finding("DUPLICATE", f"duplicate_of={dup_uid}").to_json())
        for sid, raws in collisions.get(inc["system"], {}).items():
            if sid in inc["candidates"]["services"]:
                fnd.append(finding("SERVICE_ID_COLLISION", f"{sid} <- {raws}").to_json())
        inc["repro"]["build_id"] = "pending"
        fnd += [f.to_json() for f in invariant_findings({**inc, "quality_state": roll_up(fnd)}, lab, data_home)]
        q = quality_record(u, fnd, overrides)
        inc["quality_state"] = q["state"]
        inc_out.append(inc), lab_out.append(lab), q_out.append(q), src_out.append(src)
    exc_q = [quality_record(u, [finding("ADAPTER_EXCEPTION", f"{r['exception']} [{r['traceback_sha256'][:12]}]")])
             for u, r in exc.items()]
    # deterministic build id from inputs and config
    ver = adapter.version
    digests = sorted(r["marker"]["input_digest"] for r in records.values())
    build_id = f"{dataset_id}-{hashlib.sha256(json.dumps([cfg['_hash'], ver, SCHEMA_VERSION, digests]).encode()).hexdigest()[:12]}"
    for inc in inc_out:
        inc["repro"]["build_id"] = build_id
    ds_root = P["canonical"] / dataset_id
    write_jsonl_atomic(ds_root / "visible" / "incidents.jsonl", inc_out)
    write_jsonl_atomic(ds_root / "eval_only" / "labels.jsonl", lab_out)
    write_jsonl_atomic(ds_root / "eval_only" / "quality.jsonl", q_out)
    write_jsonl_atomic(ds_root / "eval_only" / "source_index.jsonl", src_out)
    # incidents whose adapter raised have no visible record; they are listed here and the CLI exits 3
    write_jsonl_atomic(ds_root / "eval_only" / "exceptions.jsonl",
                       [{**q, **_exception_record(u, exc[u])} for u, q in ((q["incident_uid"], q) for q in exc_q)])
    write_json_atomic(ds_root / "visible" / "service_map.json", smap.to_json(), indent=1)
    write_jsonl_atomic(P["work"] / "runs" / dataset_id / "ledger.jsonl", [r["ledger"] for r in good.values()])
    states = Counter(q["state"] for q in q_out + exc_q)
    dataset_digest = hashlib.sha256(b"".join(
        (ds_root / p).read_bytes() for p in ("visible/incidents.jsonl", "eval_only/labels.jsonl",
                                             "eval_only/quality.jsonl", "eval_only/source_index.jsonl"))).hexdigest()
    receipt = {
        "schema_version": SCHEMA_VERSION, "dataset_id": dataset_id, "build_id": build_id,
        "adapter": {"name": adapter.name, "version": ver}, "config_hash": cfg["_hash"],
        "package_versions": package_versions(), "input_digests": {"incidents": len(digests),
                                                                    "sha256_of_sorted": hashlib.sha256("\n".join(digests).encode()).hexdigest()},
        "counts": {"incidents": len(records), "records": len(inc_out), "exceptions": len(exc), "states": dict(sorted(states.items())),
                   "partial": partial, "collisions": {s: c for s, c in collisions.items() if c}},
        "started": started, "finished": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset_digest": dataset_digest,
    }
    write_json_atomic(ds_root / "_build.json", receipt, indent=1)
    return receipt


def package_versions() -> dict:
    import importlib.metadata as md
    out = {"python": sys.version.split()[0]}
    for p in ("pyarrow", "pandas", "numpy", "jsonschema"):
        try:
            out[p] = md.version(p)
        except md.PackageNotFoundError:
            out[p] = None
    return out


# ---------------------------------------------------------------- validate / status
def validate_dataset_cmd(dataset_id: str, cfg: dict, data_home: Path) -> int:
    from .schema import validate_dataset
    P = paths(cfg, data_home)
    ds = P["canonical"] / dataset_id
    if not (ds / "_build.json").is_file():
        print(f"{dataset_id}: no canonical build")
        return EXIT_PRECONDITION
    overrides = load_overrides(OVERRIDES)
    inc = read_jsonl(ds / "visible" / "incidents.jsonl")
    labels = {r["incident_uid"]: r for r in read_jsonl(ds / "eval_only" / "labels.jsonl")}
    qual = {r["incident_uid"]: r for r in read_jsonl(ds / "eval_only" / "quality.jsonl")}
    for r in inc:
        q = qual[r["incident_uid"]]
        rule_findings = [f for f in q["findings"] if f["code"] != "INVARIANT_VIOLATION"]
        cur = {**r, "quality_state": roll_up(rule_findings)}
        fnd = rule_findings + [f.to_json() for f in invariant_findings(cur, labels.get(r["incident_uid"]), data_home)]
        newq = quality_record(r["incident_uid"], fnd, overrides)
        qual[r["incident_uid"]] = newq
        r["quality_state"] = newq["state"]
    write_jsonl_atomic(ds / "visible" / "incidents.jsonl", inc)
    write_jsonl_atomic(ds / "eval_only" / "quality.jsonl", list(qual.values()))
    errs = validate_dataset(ds, data_home)
    rep = quality_report(dataset_id, inc, labels, qual)
    rep["invariant_errors"] = errs[:200]
    rep["invariant_error_count"] = len(errs)
    write_json_atomic(P["reports"] / f"quality-{dataset_id}.json", rep, indent=1)
    b = read_json(ds / "_build.json")
    b["dataset_digest"] = hashlib.sha256(b"".join(
        (ds / p).read_bytes() for p in ("visible/incidents.jsonl", "eval_only/labels.jsonl",
                                        "eval_only/quality.jsonl", "eval_only/source_index.jsonl"))).hexdigest()
    b["counts"]["states"] = dict(sorted(Counter(q["state"] for q in qual.values()).items()))
    write_json_atomic(ds / "_build.json", b, indent=1)
    print(json.dumps(rep["states"]), f"invariant errors: {len(errs)}")
    if errs:
        return EXIT_INTEGRITY
    needs = rep["states"].get("QUARANTINE", 0)
    return EXIT_ATTENTION if needs else EXIT_OK


def quality_report(dataset_id: str, inc: list[dict], labels: dict, qual: dict) -> dict:
    by = Counter()
    for r in inc:
        lab = labels.get(r["incident_uid"], {})
        by[(r.get("dataset_subset") or "-", r["system"], qual[r["incident_uid"]]["state"])] += 1
    codes = Counter((f["code"], f["severity"]) for q in qual.values() for f in q["findings"])
    return {"dataset_id": dataset_id, "incidents": len(inc), "states": dict(sorted(Counter(q["state"] for q in qual.values()).items())),
            "by_subset_system_state": [{"subset": k[0], "system": k[1], "state": k[2], "n": v} for k, v in sorted(by.items())],
            "findings": [{"code": k[0], "severity": k[1], "n": v} for k, v in sorted(codes.items())],
            "quarantined": sorted(u for u, q in qual.items() if q["state"] == "QUARANTINE"),
            "rejected": sorted(u for u, q in qual.items() if q["state"] == "REJECT")}


def status_cmd(cfg: dict, data_home: Path) -> int:
    P = paths(cfg, data_home)
    root = P["canonical"]
    builds = sorted(p for p in root.glob("*/_build.json")) if root.is_dir() else []
    if not builds:
        print(f"data home: {data_home}\nno canonical builds")
    else:
        print(f"data home: {data_home}")
        print(f"{'dataset':<16}{'build_id':<30}{'incidents':>10}  states")
        for b in builds:
            r = read_json(b)
            print(f"{r['dataset_id']:<16}{r['build_id']:<30}{r['counts']['incidents']:>10}  {json.dumps(r['counts']['states'])}")
    sd = P["splits"]
    splits = sorted(p.name for p in sd.iterdir() if (p / "split.json").is_file()) if sd.is_dir() else []
    print(f"splits: {len(splits)}" + (f" (last: {splits[-1]})" if splits else ""))
    return EXIT_OK


# ---------------------------------------------------------------- CLI
def _not_implemented(name):
    def f(*a, **k):
        print(f"{name}: not available")
        return EXIT_USAGE
    return f


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="rca.prep")
    ap.add_argument("--config", default=None)
    ap.add_argument("--data-home", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    p = sub.add_parser("profile"); p.add_argument("--source", required=True)
    p = sub.add_parser("extract"); p.add_argument("--source", required=True); p.add_argument("--member-glob", default="*.tar.gz")
    p = sub.add_parser("normalize"); p.add_argument("--dataset", required=True); p.add_argument("--limit", type=int)
    p.add_argument("--incident"); p.add_argument("--force", action="store_true"); p.add_argument("--workers", type=int)
    p = sub.add_parser("validate"); p.add_argument("--dataset", required=True)
    p = sub.add_parser("audit"); p.add_argument("--evidence-stats", action="store_true")
    p = sub.add_parser("conditions"); p.add_argument("--dataset", required=True)
    p = sub.add_parser("eval-units"); p.add_argument("--dataset", required=True)
    p = sub.add_parser("split"); p.add_argument("--protocol", required=True); p.add_argument("--seed", type=int, default=0)
    sub.add_parser("verify-splits")
    p = sub.add_parser("export"); p.add_argument("--bundle", required=True); p.add_argument("--include-raw", action="store_true")
    p.add_argument("--parts", default="visible,eval_only,splits,reports,manifests,provenance")
    p = sub.add_parser("verify-bundle"); p.add_argument("dir"); p.add_argument("--deep", action="store_true")
    a = ap.parse_args(argv)
    cfg = load_config(Path(a.config) if a.config else None)
    dh = resolve_data_home(a.data_home, cfg)
    if a.cmd == "status":
        return status_cmd(cfg, dh)
    if a.cmd == "profile":
        from . import profile
        print(profile.run(a.source, dh))
        return EXIT_OK
    if a.cmd == "extract":
        from .safe_extract import UnsafeArchive, extract
        src_root = paths(cfg, dh)["raw"] / a.source
        archives = sorted(src_root.rglob(a.member_glob))
        if not archives:
            print(f"no archive matches {a.member_glob} under {src_root}")
            return EXIT_PRECONDITION
        for arc in archives:
            dest = paths(cfg, dh)["work"] / "extract" / a.source / arc.relative_to(src_root).parent / arc.name.split(".")[0]
            try:
                r = extract(arc, dest, cfg.get("extraction"))
            except UnsafeArchive as e:
                print(f"UNSAFE {arc.name}: {e}")
                return EXIT_INTEGRITY
            print(f"{arc.name}: {len(r['members'])} members, {len(r['skipped'])} skipped")
        return EXIT_OK
    if a.cmd == "normalize":
        r = build_dataset(a.dataset, cfg, dh, limit=a.limit, only_uid=a.incident, force=a.force, max_workers=a.workers)
        print(json.dumps(r["counts"]))
        return EXIT_ATTENTION if r["exceptions"] or r["counts"]["states"].get("QUARANTINE") else EXIT_OK
    if a.cmd == "validate":
        return validate_dataset_cmd(a.dataset, cfg, dh)
    if a.cmd == "audit":
        from . import audit
        return audit.main_cmd(cfg, dh, a.evidence_stats)
    if a.cmd == "conditions":
        from . import splits
        return splits.conditions_cmd(a.dataset, cfg, dh)
    if a.cmd == "eval-units":
        from . import eval_units
        return eval_units.eval_units_cmd(a.dataset, cfg, dh)
    if a.cmd == "split":
        from . import splits
        return splits.split_cmd(a.protocol, a.seed, cfg, dh)
    if a.cmd == "verify-splits":
        from . import splits
        return splits.verify_cmd(cfg, dh)
    if a.cmd == "export":
        from . import bundle
        return bundle.export_cmd(a.bundle, a.parts.split(","), a.include_raw, cfg, dh)
    if a.cmd == "verify-bundle":
        from . import bundle
        return bundle.verify_cmd(Path(a.dir), a.deep)
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
