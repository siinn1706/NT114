"""Dataset-level and cross-dataset audit over every canonical build (`python -m rca.prep audit`).

Sections: duplicates (fingerprints and telemetry content hashes, inside and across datasets),
lineage reconciliation with the acquisition registry `manifests/incidents.jsonl`, imbalance and
coverage tables, leakage scans of the model-visible zone, and split isolation. Writes
`reports/audit-<id>.json`; exits 3 when anything is unexplained.
"""
from __future__ import annotations

import hashlib
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

from .schema import MODALITIES, denylisted
from .store import CanonicalStore, read_json, read_jsonl, write_json_atomic

EXIT_OK, EXIT_ATTENTION, EXIT_PRECONDITION = 0, 3, 5
# raw-layout fragments that would reveal a label if they reached the visible zone
PATH_PATTERNS = [re.compile(p) for p in (r"RE\d-[A-Z]{2}/", r"_(cpu|mem|disk|delay|loss|socket|f[1-5])(_\d+)?/\d+/",
                                         r"fault_list", r"root_cause\.txt", r"inject_time\.txt")]


# ---------------------------------------------------------------- duplicates
def fingerprint(inc: dict, lab: dict) -> str:
    rc = lab["root_cause"]
    root = rc["primary_root_service"] or ",".join(rc["root_service_ids"])
    return f"{inc['system']}|{inc['time']['anchor_ns'] // 10**9}|{root}|{lab['fault']['family']}"


def _linked(lab_a: dict, lab_b: dict, ua: str, ub: str) -> bool:
    ga, gb = lab_a["group"], lab_b["group"]
    return (ga["duplicate_of"] == ub or gb["duplicate_of"] == ua or ga["copy_of"] == ub or gb["copy_of"] == ua
            or (ga["group_id"] is not None and ga["group_id"] == gb["group_id"]))


def duplicates(rows: list[tuple[dict, dict]]) -> dict:
    """rows: [(incident, label)] across all datasets."""
    by_fp, by_hash = defaultdict(list), defaultdict(list)
    for inc, lab in rows:
        by_fp[fingerprint(inc, lab)].append((inc, lab))
        for m in MODALITIES:
            h = inc["telemetry"][m]["content_sha256"]
            if h:
                by_hash[f"{m}:{h}"].append((inc, lab))
    out = {"fingerprint": [], "content": [], "unexplained": 0, "cross_dataset": 0}
    for kind, idx in (("fingerprint", by_fp), ("content", by_hash)):
        seen = set()
        for key, members in sorted(idx.items()):
            uids = sorted({i["incident_uid"] for i, _ in members})
            if len(uids) < 2 or tuple(uids) in seen:
                continue
            seen.add(tuple(uids))
            labs = {i["incident_uid"]: l for i, l in members}
            explained = all(any(_linked(labs[a], labs[b], a, b) for b in uids if b != a) for a in uids)
            datasets = sorted({i["dataset_id"] for i, _ in members})
            out[kind].append({"key": key, "incident_uids": uids, "datasets": datasets, "explained": explained})
            out["unexplained"] += not explained
            out["cross_dataset"] += len(datasets) > 1
    return out


# ---------------------------------------------------------------- lineage
def _registry_label_diff(lab: dict, reg: dict) -> str | None:
    """None if equal; otherwise a classified difference."""
    from .identity import DEPLOYMENT_POD, STATEFULSET_POD
    orig, fault = lab["root_cause"]["original"], lab["fault"]["type_raw"]
    if reg.get("root_cause_entity") == orig and str(reg.get("fault")) == fault:
        return None
    # pod-level labels (Nezha): the registry records the deployment of the raw pod
    raws = {e["raw"] for e in lab["root_cause"]["entities"] if e.get("raw")}
    deps = {m["d"] for r in raws if (m := DEPLOYMENT_POD.match(r) or STATEFULSET_POD.match(r))}
    # AIOps2025 registry rows keep a list-valued `instance` as a list
    ents = reg.get("root_cause_entity")
    ents = set(ents) if isinstance(ents, list) else {ents}
    if ents and ents <= raws | deps and str(reg.get("fault")) == fault:
        return None
    batch = next((n.split()[1] for n in lab["validity_notes"] if n.startswith("batch ")), None)
    if batch and reg.get("root_cause_entity") == f"{orig}_{fault}" and str(reg.get("fault")) == batch:
        return "registry splits the batch cell at its last underscore (root and fault shifted)"
    # RCA100: the registry keeps the fault name without its taxonomy id ("F001-nodeDown" -> "nodeDown")
    m = re.match(r"^F\d{3}-(.+)$", fault)
    if m and str(reg.get("fault")) == m[1] and reg.get("fault_cell") == fault and ents <= raws:
        return "registry fault without the taxonomy id prefix"
    return "unexplained"


def _iso_ns(s: str) -> int | None:
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        return None
    return int(d.timestamp()) * 10**9 + d.microsecond * 1000


# Registry ids that keep only the first N characters of the source id (measured: AIOps2025 rows are
# `aiops2025:<first 12 characters of the uuid>`); the audit checks the truncation stays unique.
REGISTRY_ID_CHARS = {"aiops2025": 12}


def _registry_key(ds: str, sid: str) -> str:
    n = REGISTRY_ID_CHARS.get(ds)
    if n is None:
        return sid
    prefix, _, key = sid.partition(":")
    return f"{prefix}:{key[:n]}"


def lineage(store: CanonicalStore, datasets: list[str], manifests: Path) -> dict:
    reg_path = manifests / "incidents.jsonl"
    if not reg_path.is_file():
        return {"status": "registry missing"}
    reg = defaultdict(list)
    for r in read_jsonl(reg_path):
        reg[(r["source_id"], r["incident_id"])].append(r)
    out = {"datasets": {}, "unexplained": 0}
    for ds in datasets:
        incs = store.incidents(ds, states=None)
        labels = store.labels(ds)
        sources = {i["source_id"] for i in incs}
        # sources shared by several datasets (agenticopseval: AIOps2025 and RCA100): only this dataset's id prefix
        prefixes = {labels[i["incident_uid"]]["source_incident_id"].partition(":")[0] + ":" for i in incs}
        mine = (lambda i: i.startswith(next(iter(prefixes)))) if len(prefixes) == 1 else (lambda i: True)
        matched, missing_canon, multi, label_diffs, time_diffs = 0, [], [], Counter(), []
        time_explained = Counter()
        seen = set()
        keys = Counter(_registry_key(ds, labels[i["incident_uid"]]["source_incident_id"]) for i in incs)
        for inc in incs:
            lab = labels[inc["incident_uid"]]
            k = (inc["source_id"], _registry_key(ds, lab["source_incident_id"]))
            rows = reg.get(k, [])
            if len(rows) == 1 and ds in REGISTRY_ID_CHARS and keys[k[1]] > 1:
                multi.append(inc["incident_uid"])            # a truncated registry id names several incidents
            elif len(rows) == 1:
                matched += 1
                seen.add(k)
                d = _registry_label_diff(lab, rows[0])
                if d:
                    label_diffs[d] += 1
                t = str(rows[0].get("inject_or_start_time") or "")
                anchor = inc["time"]["anchor_ns"]
                if t.isdigit() and int(t) * 10**9 != anchor:
                    orig = lab["root_cause"]["original"]
                    if isinstance(orig, dict) and str(orig.get("inject_timestamp")) == t:
                        # the registry took `inject_timestamp`; the anchor is `inject_time` (measured in profiling)
                        time_explained["registry used inject_timestamp"] += 1
                    else:
                        time_diffs.append(inc["incident_uid"])
                elif not t.isdigit() and t:
                    ns = _iso_ns(t)
                    if ns == anchor:
                        pass
                    elif ns is not None and inc["time"]["anchor_kind"] == "alert" and 0 < anchor - ns <= 900 * 10**9:
                        # RCA100: the registry records the answer-key window start; the anchor is the first alert
                        time_explained["registry window start precedes the alert anchor"] += 1
                    else:
                        time_diffs.append(inc["incident_uid"])
            elif not rows:
                why = "duplicate of a registered incident" if lab["group"]["duplicate_of"] else "unexplained"
                missing_canon.append({"incident_uid": inc["incident_uid"], "source_incident_id": lab["source_incident_id"],
                                      "explanation": why})
            else:
                multi.append(inc["incident_uid"])
        reg_only = sorted(i for (s, i) in reg if s in sources and mine(i) and (s, i) not in seen)
        unexplained = (sum(1 for m in missing_canon if m["explanation"] == "unexplained") + len(multi) + len(reg_only)
                       + label_diffs.get("unexplained", 0) + len(time_diffs))
        out["datasets"][ds] = {
            "canonical": len(incs), "registry_rows": sum(len(v) for (s, i), v in reg.items() if s in sources and mine(i)),
            "matched_one_to_one": matched, "not_in_registry": missing_canon, "multiple_registry_rows": multi,
            "registry_only": reg_only[:50], "registry_only_count": len(reg_only),
            "label_differences": dict(label_diffs), "anchor_differences": time_diffs[:50],
            "anchor_differences_explained": {"registry used inject_timestamp": 0, **time_explained},
            "unexplained": unexplained}
        out["unexplained"] += unexplained
    rep = manifests / "lineage-report.json"
    if rep.is_file():
        groups = read_json(rep).get("lineage", {}).get("groups", {})
        out["lineage_report_groups"] = {g: v.get("independent_incidents") for g, v in groups.items()}
    return out


# ---------------------------------------------------------------- imbalance and coverage
def _dist(xs):
    xs = sorted(xs)
    return {"n": len(xs), "min": xs[0], "median": statistics.median(xs), "max": xs[-1]} if xs else {"n": 0}


def root_position(store: CanonicalStore, uid: str, root: str, segment_gap_s: float | None = None) -> dict:
    """Where the root sits among services flagged by the `full` evidence (sanity signal for easy subsets)."""
    from . import evidence, legacy_view
    from .data import canon
    inc = store.incident(uid)
    tel = legacy_view.legacy_telemetry(store, uid)
    t = inc["time"]["anchor_ns"] // 10**9
    flagged_metric = []
    if tel["metrics"] is not None:
        ms = evidence.metric_scores(tel["metrics"], t)
        if len(ms):
            ms["svc"] = ms["svc"].map(canon)
            agg = ms.groupby("svc")["z"].max().sort_values(ascending=False)
            flagged_metric = [s for s in agg.index if agg[s] >= 3]
    flagged = set(flagged_metric)
    if tel["logs"] is not None:
        flagged |= set(evidence.log_summary(tel["logs"], t, segment_gap_s))
    if tel["traces"] is not None:
        flagged |= set(evidence.trace_summary(tel["traces"], t, segment_gap_s)[0])
    pos = flagged_metric.index(root) + 1 if root in flagged_metric else None
    return {"metric_rank": pos, "flagged": len(flagged), "root_flagged": root in flagged,
            "root_only_flagged": flagged == {root}}


def imbalance(store: CanonicalStore, ds: str, evidence_stats: bool = False, cfg: dict | None = None) -> list[dict]:
    labels, quality = store.labels(ds), store.quality(ds)
    cells = defaultdict(list)
    for inc in store.incidents(ds, states=None):
        lab = labels[inc["incident_uid"]]
        cells[(inc.get("dataset_subset") or "-", inc["system"], lab["fault"]["family"])].append((inc, lab))
    out = []
    for (subset, system, fam), members in sorted(cells.items()):
        row = {"subset": subset, "system": system, "fault_family": fam, "incidents": len(members),
               "states": dict(Counter(quality[i["incident_uid"]]["state"] for i, _ in members)),
               "modality_status": {m: dict(Counter(i["telemetry"][m]["status"] for i, _ in members)) for m in MODALITIES},
               "candidates": _dist([len(i["candidates"]["services"]) for i, _ in members]),
               "coverage": {m: _dist([i["telemetry"][m]["coverage"] for i, _ in members
                                      if i["telemetry"][m]["coverage"] is not None]) for m in MODALITIES}}
        if evidence_stats:
            from .legacy_view import evidence_kwargs
            seg = evidence_kwargs(cfg or {}, ds).get("log_trace_segment_gap_s")
            pos = [root_position(store, i["incident_uid"], l["root_cause"]["primary_root_service"], seg)
                   for i, l in members if quality[i["incident_uid"]]["state"] in ("ACCEPT", "ACCEPT_WITH_WARNINGS")
                   and l["root_cause"]["primary_root_service"]]
            row["root_position"] = {
                "n": len(pos), "metric_rank_1": sum(p["metric_rank"] == 1 for p in pos),
                "root_not_flagged": sum(not p["root_flagged"] for p in pos),
                "root_only_flagged": sum(p["root_only_flagged"] for p in pos),
                "flagged_services": _dist([p["flagged"] for p in pos])}
        out.append(row)
    return out


# ---------------------------------------------------------------- leakage scans
def _label_texts(store: CanonicalStore, ds: str) -> set[str]:
    """Free-text label artefacts: lines of `root_cause.txt`-like files referenced in `label_artifacts`."""
    from .adapters.base import MemberSource
    texts = set()
    raw = store.data_home / "raw"
    records: dict[Path, dict] = {}
    for lab in store.labels(ds).values():
        for a in lab["label_artifacts"]:
            ref = a["ref"]
            if "#" in ref:
                # `<jsonl>#<uuid>`: one field of one label record (AIOps2025 groundtruth.jsonl). `key_*` fields
                # are metric names that legitimately occur in telemetry and are not free text.
                rel, key = ref.split("#", 1)
                field = a["kind"].split(":", 1)[1]
                if field.startswith("key_") or not (raw / rel).is_file():
                    continue
                if raw / rel not in records:
                    records[raw / rel] = {r.get("uuid"): r for r in read_jsonl(raw / rel)}
                val = records[raw / rel].get(key, {}).get(field)
                texts |= {s.strip() for s in (val if isinstance(val, list) else [val])
                          if isinstance(s, str) and len(s.strip()) >= 12}
                continue
            for base in (raw, store.data_home):
                if "!" in ref:
                    arc, member = ref.split("!", 1)
                    if not (base / arc).is_file():
                        continue
                    src = MemberSource("", base, arc)
                    try:
                        body = src.read_bytes(member)
                    finally:
                        src.close()
                elif (base / ref).is_file():
                    body = (base / ref).read_bytes()
                else:
                    continue
                texts |= {ln.strip() for ln in body.decode("utf-8", "replace").splitlines() if len(ln.strip()) >= 12}
                break
    return texts


def _walk_strings(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield f"{path}.{k}" if path else k, k, None
            yield from _walk_strings(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_strings(v, path)
    elif isinstance(obj, str):
        yield path, None, obj


def leakage_scan(store: CanonicalStore, ds: str, extra_texts=()) -> dict:
    vis = store.root / ds / "visible"
    deny, paths, artefacts = [], [], []
    label_texts = _label_texts(store, ds) | set(extra_texts)
    for f in sorted(vis.glob("*.jsonl")) + sorted(vis.glob("*.json")):
        data = read_jsonl(f) if f.suffix == ".jsonl" else [read_json(f)]
        for rec in data:
            for path, key, val in _walk_strings(rec):
                if key is not None and denylisted(key):
                    deny.append(f"{f.name}:{path}")
                if val is not None:
                    if f.name == "service_map.json":
                        continue                          # raw service names are telemetry identities
                    for p in PATH_PATTERNS:
                        if p.search(val):
                            paths.append(f"{f.name}:{path}:{p.pattern}")
                    if path.startswith("context.") and any(t in val for t in label_texts):
                        artefacts.append(f"{f.name}:{path}")
    cols = set()
    for f in vis.rglob("*.parquet"):
        cols |= set(pq.read_schema(f).names)
    deny += [f"parquet column {c}" for c in sorted(cols) if denylisted(c)]
    return {"denylist_hits": sorted(set(deny))[:50], "path_hits": sorted(set(paths))[:50],
            "artefact_hits": sorted(set(artefacts))[:50], "label_texts_checked": len(label_texts),
            "total_hits": len(set(deny)) + len(set(paths)) + len(set(artefacts))}


def evidence_scan(evidence_dir: Path, label_texts: set[str]) -> dict:
    """Evidence files (from `run_grid prepare`) must hold no label keys, raw paths or artefact text."""
    hits = []
    for f in sorted(Path(evidence_dir).glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        for path, key, val in _walk_strings(rec):
            if key is not None and key in ("root_service", "fault", "root", "truth", "path"):
                hits.append(f"{f.name}:{path}")
            if val is not None and (any(p.search(val) for p in PATH_PATTERNS) or any(t in val for t in label_texts)):
                hits.append(f"{f.name}:{path}")
    return {"files": len(list(Path(evidence_dir).glob("*.json"))), "hits": hits[:50], "total_hits": len(hits)}


# ---------------------------------------------------------------- driver
def run(data_home: Path, cfg: dict, evidence_stats: bool = False) -> dict:
    from .prep import paths
    from .splits import verify_split
    store = CanonicalStore(data_home)
    datasets = store.datasets()
    builds = {ds: store.build(ds) for ds in datasets}
    rows = []
    for ds in datasets:
        labels = store.labels(ds)
        rows += [(i, labels[i["incident_uid"]]) for i in store.incidents(ds, states=None)]
    P = paths(cfg, data_home)
    split_dirs = sorted(p for p in P["splits"].iterdir() if (p / "split.json").is_file()) if P["splits"].is_dir() else []
    splits = {d.name: verify_split(d, store) for d in split_dirs}
    leak = {ds: leakage_scan(store, ds) for ds in datasets}
    rep = {
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "builds": {ds: {"build_id": b["build_id"], "dataset_digest": b["dataset_digest"], "states": b["counts"]["states"]}
                   for ds, b in builds.items()},
        "duplicates": duplicates(rows), "lineage": lineage(store, datasets, data_home / "manifests"),
        "imbalance": {ds: imbalance(store, ds, evidence_stats, cfg) for ds in datasets},
        "leakage": leak, "splits": splits,
    }
    rep["summary"] = {
        "incidents": len(rows), "unexplained_duplicates": rep["duplicates"]["unexplained"],
        "cross_dataset_overlaps": rep["duplicates"]["cross_dataset"],
        "lineage_unexplained": rep["lineage"].get("unexplained", 0),
        "leakage_hits": sum(v["total_hits"] for v in leak.values()),
        "split_errors": sum(len(v) for v in splits.values()),
    }
    return rep


def main_cmd(cfg: dict, data_home: Path, evidence_stats: bool = False) -> int:
    from .prep import paths
    store = CanonicalStore(data_home)
    if not store.datasets():
        print("no canonical builds")
        return EXIT_PRECONDITION
    rep = run(data_home, cfg, evidence_stats)
    ids = sorted(b["build_id"] for b in rep["builds"].values())
    name = ids[0] if len(ids) == 1 else hashlib.sha256("\n".join(ids).encode()).hexdigest()[:12]
    out = paths(cfg, data_home)["reports"] / f"audit-{name}.json"
    write_json_atomic(out, rep, indent=1)
    print(json.dumps(rep["summary"]), "->", out.name)
    s = rep["summary"]
    bad = s["unexplained_duplicates"] or s["lineage_unexplained"] or s["leakage_hits"] or s["split_errors"]
    return EXIT_ATTENTION if bad else EXIT_OK
