"""Missing-observability condition matrix and leakage-safe split manifests.

  python -m rca.prep conditions --dataset rcaeval
  python -m rca.prep split --protocol within-rcaeval-grouped --seed 0
  python -m rca.prep verify-splits

Grouping is union-find. `physical`: overlapping evidence windows within one stream, `duplicate_of`
/ `copy_of`, equal `group_id` (records of one source incident), equal telemetry `content_sha256`, and
for datasets in GROUP_BY_DAY the same campaign day. `cell`: `physical` plus equal `fault_cell`.
Every protocol is a deterministic function of (seed, sorted groups). A manifest directory is
`<protocol>[-<fold>]-<seed>-<hash8>`, where hash8 starts the sha256 of `assignments.jsonl`;
existing directories are never overwritten.
"""
from __future__ import annotations

import hashlib
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from .ablate import CONDITIONS, choose_nonroot_target
from .schema import MODALITIES, SCHEMA_VERSION, validate_record
from .store import (CanonicalStore, SPLIT_STATES, dump_json, read_json, read_jsonl, write_json_atomic,
                    write_jsonl_atomic)

EXIT_OK, EXIT_USAGE, EXIT_ATTENTION, EXIT_INTEGRITY, EXIT_PRECONDITION = 0, 2, 3, 4, 5
FRACTIONS = {"train": 0.6, "val": 0.2, "test": 0.2}
ANCHOR_KINDS = ("injection", "alert")
# Datasets whose campaign day carries fault information join all incidents of one day into one group
# (value: UTC offset of the source's day, hours). AIOps2025: MI(day; fault type) = 0.91 bits, permutation
# p = 0.0005 (measured 2026-10-14); its archives are named by UTC+8 day.
GROUP_BY_DAY = {"aiops2025": 8}


def _paths(cfg, data_home):
    from .prep import paths
    return paths(cfg, data_home)


def _evidence_window(cfg) -> tuple[int, int]:
    ev = (cfg.get("windows") or {}).get("evidence") or {}
    return int(ev.get("pre_s", 600)), int(ev.get("post_s", 300))


# ---------------------------------------------------------------- condition matrix
def _span_counts(store: CanonicalStore, inc: dict) -> pd.DataFrame | None:
    if inc["telemetry"]["traces"]["status"] != "present":
        return None
    t = pq.read_table(store.data_home / inc["telemetry"]["traces"]["path"], columns=["service_id"])
    return pd.DataFrame({"svc": t["service_id"].to_pandas()})


def condition_row(inc: dict, label: dict | None, quality: dict, traces: pd.DataFrame | None) -> dict:
    """{condition: {applicable, reason}} plus `nonroot_target` for one incident (eval-only)."""
    st = {m: inc["telemetry"][m]["status"] for m in MODALITIES}
    present = {m for m, s in st.items() if s == "present"}
    codes = {f["code"] for f in quality["findings"]}
    root = (label or {}).get("root_cause", {}).get("primary_root_service")
    out: dict = {}
    blocked = None
    if quality["state"] not in SPLIT_STATES:
        blocked = f"quality_state {quality['state']}"
    elif inc["time"]["anchor_kind"] not in ANCHOR_KINDS:
        blocked = f"anchor_kind {inc['time']['anchor_kind']}"
    elif "PRE_WINDOW_SHORT" in codes:
        blocked = "PRE_WINDOW_SHORT"
    elif not present:
        blocked = "no modality present"
    target = None
    if traces is not None and root:
        target = choose_nonroot_target({"traces": traces}, root, inc["incident_uid"])
    for c in CONDITIONS:
        if blocked:
            out[c] = {"applicable": False, "reason": blocked}
            continue
        if c == "full":
            out[c] = {"applicable": True, "reason": "ok"}
        elif c.startswith("no_"):
            m = {"no_metric": "metrics", "no_log": "logs", "no_trace": "traces"}[c]
            if m not in present:
                out[c] = {"applicable": False, "reason": f"{m} {st[m]}"}
            elif not present - {m}:
                out[c] = {"applicable": False, "reason": f"nothing left without {m}"}
            else:
                out[c] = {"applicable": True, "reason": "ok"}
        elif c == "metrics_only":
            if "metrics" not in present:
                out[c] = {"applicable": False, "reason": f"metrics {st['metrics']}"}
            elif not present - {"metrics"}:
                out[c] = {"applicable": False, "reason": "no logs or traces to drop (equals full)"}
            else:
                out[c] = {"applicable": True, "reason": "ok"}
        else:
            if "traces" not in present:
                out[c] = {"applicable": False, "reason": f"traces {st['traces']}"}
            elif not root:
                out[c] = {"applicable": False, "reason": "no primary root service"}
            elif root not in set(traces["svc"].dropna()):
                out[c] = {"applicable": False, "reason": "root has no spans"}
            elif c == "blind_nonroot" and target is None:
                out[c] = {"applicable": False, "reason": "no other service has spans"}
            else:
                out[c] = {"applicable": True, "reason": "ok"}
    return {"conditions": out, "nonroot_target": target if out["blind_nonroot"]["applicable"] else None,
            "natural": {m: st[m] for m in MODALITIES}}


def condition_matrix(store: CanonicalStore, dataset: str) -> dict:
    labels, quality = store.labels(dataset), store.quality(dataset)
    b = store.build(dataset)
    rows = {}
    for inc in sorted(store.incidents(dataset, states=None), key=lambda r: r["incident_uid"]):
        u = inc["incident_uid"]
        need_traces = quality[u]["state"] in SPLIT_STATES
        rows[u] = condition_row(inc, labels.get(u), quality[u], _span_counts(store, inc) if need_traces else None)
    counts = {c: sum(r["conditions"][c]["applicable"] for r in rows.values()) for c in CONDITIONS}
    return {"dataset_id": dataset, "build_id": b["build_id"], "dataset_digest": b["dataset_digest"],
            "schema_version": SCHEMA_VERSION, "conditions": list(CONDITIONS), "counts": counts, "incidents": rows}


def conditions_cmd(dataset: str, cfg: dict, data_home: Path) -> int:
    store = CanonicalStore(data_home)
    if dataset not in store.datasets():
        print(f"{dataset}: no canonical build")
        return EXIT_PRECONDITION
    m = condition_matrix(store, dataset)
    out = _paths(cfg, data_home)["reports"] / f"condition-matrix-{dataset}.json"
    write_json_atomic(out, m, indent=1)
    print(dump_json(m["counts"]))
    return EXIT_OK


def load_condition_matrix(data_home: Path, dataset: str, cfg: dict | None = None) -> dict:
    from .prep import load_config
    return read_json(_paths(cfg or load_config(), data_home)["reports"] / f"condition-matrix-{dataset}.json")


# ---------------------------------------------------------------- grouping
class _UF:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, i):
        while self.p[i] != i:
            self.p[i] = self.p[self.p[i]]
            i = self.p[i]
        return i

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def stream_of(inc: dict) -> str:
    return f"{inc['dataset_id']}/{inc['lineage_group']}/{inc.get('dataset_subset') or '-'}/{inc['system']}"


def group_items(items: list[dict], rule: str, pre_s: int = 600, post_s: int = 300) -> dict[str, str]:
    """items: {uid, stream, anchor_ns, cell, dup_of, hashes}. Returns uid -> group_id (16 hex)."""
    if rule not in ("physical", "cell"):
        raise ValueError(rule)
    items = sorted(items, key=lambda x: x["uid"])
    idx = {it["uid"]: i for i, it in enumerate(items)}
    uf = _UF(len(items))
    by_stream = defaultdict(list)
    for i, it in enumerate(items):
        by_stream[it["stream"]].append(i)
    span = (pre_s + post_s) * 10**9
    for ix in by_stream.values():   # windows [t-pre, t+post] overlap iff anchors are closer than pre+post
        ix.sort(key=lambda i: (items[i]["anchor_ns"], items[i]["uid"]))
        for a, b in zip(ix, ix[1:]):
            if items[b]["anchor_ns"] - items[a]["anchor_ns"] <= span:
                uf.union(a, b)
    for it in items:
        if it.get("dup_of") in idx:
            uf.union(idx[it["uid"]], idx[it["dup_of"]])
    first: dict = {}
    for i, it in enumerate(items):
        keys = [f"h:{h}" for h in it.get("hashes", ()) if h]
        if it.get("group"):
            keys.append(f"g:{it['group']}")
        if it.get("day"):
            keys.append(f"d:{it['day']}")
        if rule == "cell":
            keys.append(f"c:{it['cell']}")
        for k in keys:
            if k in first:
                uf.union(first[k], i)
            else:
                first[k] = i
    members = defaultdict(list)
    for i, it in enumerate(items):
        members[uf.find(i)].append(it["uid"])
    out = {}
    for ms in members.values():
        gid = hashlib.sha256("\n".join(sorted(ms)).encode()).hexdigest()[:16]
        for u in ms:
            out[u] = gid
    return out


def _day(dataset: str, anchor_ns: int) -> str | None:
    off = GROUP_BY_DAY.get(dataset)
    if off is None:
        return None
    return f"{dataset}/{datetime.fromtimestamp(anchor_ns / 1e9 + off * 3600, timezone.utc):%Y-%m-%d}"


def eligible(store: CanonicalStore, dataset: str) -> list[dict]:
    """Split candidates: ACCEPT / ACCEPT_WITH_WARNINGS incidents with their labels (split code may read labels)."""
    labels = store.labels(dataset)
    out = []
    for inc in store.incidents(dataset):
        lab = labels[inc["incident_uid"]]
        if lab["eval_tier"] not in ("A", "B"):
            continue
        out.append({"uid": inc["incident_uid"], "dataset": dataset, "system": inc["system"], "stream": stream_of(inc),
                    "anchor_ns": inc["time"]["anchor_ns"], "cell": lab["group"]["fault_cell"],
                    "dup_of": lab["group"]["duplicate_of"] or lab["group"]["copy_of"],
                    "group": lab["group"]["group_id"], "day": _day(dataset, inc["time"]["anchor_ns"]),
                    "hashes": [inc["telemetry"][m]["content_sha256"] for m in MODALITIES],
                    "family": lab["fault"]["family"], "tier": lab["eval_tier"]})
    return out


# ---------------------------------------------------------------- protocols
def _stratum(members: list[dict]) -> str:
    c = Counter(f"{m['system']}|{m['family']}" for m in members)
    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def grouped_fill(items: list[dict], groups: dict[str, str], seed: int) -> tuple[dict[str, str], dict]:
    """Greedy stratified fill of whole groups to 60/20/20 of incidents; strata with <3 groups go to test."""
    by_group = defaultdict(list)
    for it in items:
        by_group[groups[it["uid"]]].append(it)
    strata = defaultdict(list)
    for gid in sorted(by_group):
        strata[_stratum(by_group[gid])].append(gid)
    assign, whole_test = {}, 0
    rng = random.Random(seed)
    for st in sorted(strata):
        gids = sorted(strata[st])
        rng.shuffle(gids)
        if len(gids) < 3:
            for g in gids:
                assign[g] = "test"
                whole_test += len(by_group[g])
            continue
        total = sum(len(by_group[g]) for g in gids)
        have = dict.fromkeys(FRACTIONS, 0)
        for g in gids:
            role = max(FRACTIONS, key=lambda r: (FRACTIONS[r] * total - have[r], -list(FRACTIONS).index(r)))
            assign[g] = role
            have[role] += len(by_group[g])
    return {it["uid"]: assign[groups[it["uid"]]] for it in items}, {"incidents_in_whole_test_strata": whole_test}


def _protocol(protocol: str):
    """(kind, dataset, rule) from a protocol id; for `xdata-<train>-to-<test>` the dataset is (train, test)."""
    if protocol.startswith("xdata-"):
        train, sep, test = protocol[len("xdata-"):].partition("-to-")
        if not (sep and train and test) or train == test:
            raise ValueError(protocol)
        return "xdata", (train, test), None
    for kind in ("within", "loso", "eval-only"):
        if protocol.startswith(kind + "-"):
            rest = protocol[len(kind) + 1:]
            if kind == "within":
                ds, _, rule = rest.rpartition("-")
                if rule not in ("grouped", "retrieval") or not ds:
                    raise ValueError(protocol)
                return kind, ds, rule
            return kind, rest, None
    raise ValueError(f"unknown protocol {protocol!r}")


def _datasets(ds) -> tuple[str, ...]:
    return tuple(ds) if isinstance(ds, tuple) else (ds,)


def build_assignments(store: CanonicalStore, protocol: str, seed: int, cfg: dict) -> list[dict]:
    """[{fold, assignments: [{incident_uid, split, group_id_hash}], groups, extra}] (one entry, or one per LOSO fold)."""
    kind, ds, rule = _protocol(protocol)
    items = [i for d in _datasets(ds) for i in eligible(store, d)]
    pre_s, post_s = _evidence_window(cfg)
    grule = "cell" if (kind != "within" or rule == "grouped") else "physical"
    groups = group_items(items, grule, pre_s, post_s)
    sizes = Counter(groups.values())
    gstats = {"rule": grule, "n_groups": len(sizes), "largest_group": max(sizes.values(), default=0),
              "singletons": sum(1 for v in sizes.values() if v == 1)}
    folds = []
    if kind == "within":
        split, extra = grouped_fill([i for i in items if i["tier"] == "A"], groups, seed)
        role = {groups[u]: s for u, s in split.items()}
        dropped = 0
        for i in items:   # B-tier incidents may only train, and only when their group is not held out
            if i["tier"] == "B":
                if role.get(groups[i["uid"]], "train") == "train":
                    split[i["uid"]] = "train"
                else:
                    dropped += 1
        folds.append((None, split, {**extra, "tier_b_dropped_held_out_group": dropped}))
    elif kind == "eval-only":
        folds.append((None, {i["uid"]: "test" for i in items if i["tier"] == "A"}, {}))
    elif kind == "xdata":
        train_ds, test_ds = ds
        test = {i["uid"]: "test" for i in items if i["dataset"] == test_ds and i["tier"] == "A"}
        test_groups = {groups[u] for u in test}
        split = {**{i["uid"]: "train" for i in items if i["dataset"] == train_ds and groups[i["uid"]] not in test_groups}, **test}
        systems = lambda d: sorted({i["system"] for i in items if i["dataset"] == d})
        folds.append((None, split, {"train_dataset": train_ds, "test_dataset": test_ds,
                                    "shared_systems": sorted(set(systems(train_ds)) & set(systems(test_ds))),
                                    "train_dropped_shared_group": sum(1 for i in items if i["dataset"] == train_ds and i["uid"] not in split)}))
    else:
        systems = sorted({i["system"] for i in items})
        for s in systems:
            sys_groups = {groups[i["uid"]] for i in items if i["system"] == s}
            split = {}
            for i in items:
                g = groups[i["uid"]]
                if i["system"] == s:
                    if i["tier"] == "A":
                        split[i["uid"]] = "test"
                elif g not in sys_groups:
                    split[i["uid"]] = "train"
            folds.append((s, split, {"test_system": s}))
    out = []
    for fold, split, extra in folds:
        rows = [{"incident_uid": u, "split": split[u], "group_id_hash": groups[u]} for u in sorted(split)]
        out.append({"fold": fold, "assignments": rows, "groups": gstats, "extra": extra, "dataset": _datasets(ds),
                    "params": {"rule": grule, "fractions": FRACTIONS if kind == "within" else None,
                               "evidence_window_s": [pre_s, post_s], "stratify": "system|fault_family",
                               "min_groups_per_stratum": 3, **({"fold": fold} if fold else {})}})
    return out


def _counts(rows, items_by_uid) -> dict:
    c = defaultdict(Counter)
    for r in rows:
        it = items_by_uid[r["incident_uid"]]
        c[r["split"]][f"{it['system']}|{it['family']}"] += 1
    return {s: {"total": sum(v.values()), "by_stratum": dict(sorted(v.items()))} for s, v in sorted(c.items())}


def assignments_bytes(rows: list[dict]) -> bytes:
    return "".join(dump_json(r) + "\n" for r in rows).encode("utf-8")


def split_cmd(protocol: str, seed: int, cfg: dict, data_home: Path) -> int:
    store = CanonicalStore(data_home)
    try:
        kind, ds, _ = _protocol(protocol)
    except ValueError as e:
        print(e)
        return EXIT_USAGE
    dss = _datasets(ds)
    missing = [d for d in dss if d not in store.datasets()]
    if missing:
        print(f"{', '.join(missing)}: no canonical build")
        return EXIT_PRECONDITION
    builds = [{"dataset_id": d, "build_id": store.build(d)["build_id"], "dataset_digest": store.build(d)["dataset_digest"]}
              for d in dss]
    items_by_uid = {i["uid"]: i for d in dss for i in eligible(store, d)}
    root = _paths(cfg, data_home)["splits"]
    rc = EXIT_OK
    for f in build_assignments(store, protocol, seed, cfg):
        data = assignments_bytes(f["assignments"])
        h = hashlib.sha256(data).hexdigest()
        name = f"{protocol}{'-' + f['fold'] if f['fold'] else ''}-{seed}-{h[:8]}"
        d = root / name
        if d.exists():
            old = read_json(d / "split.json")["builds"]
            if [o["dataset_digest"] for o in old] == [b["dataset_digest"] for b in builds]:
                print(f"{name}: exists (same inputs give the same directory); not rewritten")
                continue
            # same assignments, rebuilt dataset: keep the stale manifest for audit, re-pin a new one
            dest = root / "_superseded" / f"{name}-{'+'.join(o['build_id'] for o in old)}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            d.rename(dest)
            print(f"{name}: pinned to superseded build(s); moved to {dest.relative_to(root).as_posix()}")
        test_share = sum(1 for r in f["assignments"] if r["split"] == "test") / max(len(f["assignments"]), 1)
        manifest = {"protocol": protocol, "seed": seed, "params": f["params"], "schema_version": SCHEMA_VERSION,
                    "builds": builds,
                    "counts": {**_counts(f["assignments"], items_by_uid), **f["extra"]},
                    "groups": {**f["groups"], "test_share": round(test_share, 4),
                               # a within split needs >= 3 groups to hold anything out (one group: all in test)
                               "headline_ok": kind == "eval-only" or (test_share >= 0.10 and (
                                   kind != "within" or f["groups"]["n_groups"] >= 3))},
                    "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "assignments_sha256": h}
        errs = validate_record("SplitManifest", manifest)
        if errs:
            print(f"{name}: invalid manifest {errs[:3]}")
            return EXIT_INTEGRITY
        tmp = root / f".{name}.part"
        tmp.mkdir(parents=True, exist_ok=True)
        (tmp / "assignments.jsonl").write_bytes(data)
        write_json_atomic(tmp / "split.json", manifest, indent=1)
        tmp.rename(d)
        print(f"{name}: {dump_json({k: v['total'] for k, v in manifest['counts'].items() if isinstance(v, dict)})}"
              f" groups={f['groups']['n_groups']} largest={f['groups']['largest_group']}")
        if not manifest["groups"]["headline_ok"]:
            rc = EXIT_ATTENTION
    return rc


# ---------------------------------------------------------------- verification
def verify_split(d: Path, store: CanonicalStore) -> list[str]:
    errs = []
    m = read_json(d / "split.json")
    data = (d / "assignments.jsonl").read_bytes()
    h = hashlib.sha256(data).hexdigest()
    if h != m["assignments_sha256"] or not d.name.endswith(h[:8]):
        errs.append("HASH_MISMATCH")
    rows = read_jsonl(d / "assignments.jsonl")
    by_group = defaultdict(set)
    for r in rows:
        by_group[r["group_id_hash"]].add(r["split"])
        if set(r) != {"incident_uid", "split", "group_id_hash"}:
            errs.append(f"EXTRA_FIELDS {r['incident_uid']}")
    for g, s in by_group.items():
        if len(s) > 1:
            errs.append(f"GROUP_SPANS_SPLITS {g} {sorted(s)}")
    if [r["incident_uid"] for r in rows] != sorted(r["incident_uid"] for r in rows):
        errs.append("NOT_SORTED")
    for b in m["builds"]:
        try:
            cur = store.build(b["dataset_id"])
        except FileNotFoundError:
            errs.append(f"MISSING_BUILD {b['dataset_id']}")
            continue
        if cur["dataset_digest"] != b["dataset_digest"]:
            errs.append(f"STALE {b['dataset_id']}")
    return errs


def verify_cmd(cfg: dict, data_home: Path) -> int:
    root = _paths(cfg, data_home)["splits"]
    dirs = sorted(p for p in root.iterdir() if (p / "split.json").is_file()) if root.is_dir() else []
    store = CanonicalStore(data_home)
    rc = EXIT_OK
    for d in dirs:
        errs = verify_split(d, store)
        print(f"{d.name}: {'OK' if not errs else '; '.join(errs[:5])}")
        if errs:
            rc = EXIT_INTEGRITY
    if not dirs:
        print("no split manifests")
    return rc
