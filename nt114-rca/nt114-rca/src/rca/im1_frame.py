"""IM1 historical service-dependency frame (data contract §7 rule 8, amendment a02 of 2026-10-26).

One frame per key (dataset, dataset_subset, system, split), built only from the incidents the split
assigns to `train`: their trace rows in [anchor - 600 s, anchor), columns trace_id, span_id,
parent_span_id, service_id (ts_ns only for the window). An edge `parent service -> child service` comes
from a span whose parent resolves to a span of the same trace, both services non-null and different.
The frame holds the node set, the edge set and per edge the number of contributing train incidents:
no incident id, time or other field. Valid when at least MIN_CONTRIBUTING train incidents contributed
an edge (fixed). Each frame and its edge-shuffled control are written once with their sha256; a rebuild
with a different hash stops the run.

Never reads labels, root services, fault types, val or test telemetry, or model output: incidents
come from the split's assignments, and a non-train incident passed to the builder raises.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random
from pathlib import Path

import pandas as pd
import pyarrow.compute as pc

from . import rcl_trace_graph as tg
from .evidence import NORMAL_S

FRAME_VERSION = "1"
MIN_CONTRIBUTING = 3
NOT_INFORMATIVE_SHARE = 0.5
COLUMNS = ["ts_ns", "trace_id", "span_id", "parent_span_id", "service_id"]


def key_of(incident: dict, split_id: str) -> tuple[str, str, str, str]:
    return (incident["dataset_id"], incident.get("dataset_subset") or "", incident["system"], split_id)


def key_id(key) -> str:
    return hashlib.sha256(json.dumps(list(key)).encode()).hexdigest()[:16]


def _sha(content: dict) -> str:
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def incident_edges(store, incident: dict) -> set[tuple[str, str]]:
    """Service edges of one train incident's pre-anchor trace rows."""
    t = store.telemetry(incident["incident_uid"], "traces", columns=COLUMNS)
    if t is None or not t.num_rows:
        return set()
    anchor = incident["time"]["anchor_ns"]
    ts = t["ts_ns"]
    t = t.filter(pc.and_(pc.greater_equal(ts, anchor - NORMAL_S * 10**9), pc.less(ts, anchor)))
    df = t.to_pandas()
    df = pd.DataFrame({"traceID": df["trace_id"], "spanID": df["span_id"], "parentSpanID": df["parent_span_id"],
                       "svc": df["service_id"]})
    return set(tg.service_edges(df))


def build_frame(store, incidents: list[dict], roles: dict[str, str], key) -> dict:
    """Frame of `key` from `incidents` (all of which must be train-role and of that key)."""
    split_id = key[3]
    counts: dict[tuple[str, str], int] = {}
    contributing = 0
    for inc in incidents:
        if roles.get(inc["incident_uid"]) != "train":
            raise ValueError(f"{inc['incident_uid']}: only train-role incidents may build an IM1 frame")
        if key_of(inc, split_id) != tuple(key):
            raise ValueError(f"{inc['incident_uid']}: not of frame key {key}")
        edges = incident_edges(store, inc)
        contributing += bool(edges)
        for e in edges:
            counts[e] = counts.get(e, 0) + 1
    content = {"frame_version": FRAME_VERSION, "kind": "real", "key": list(key), "window_s": NORMAL_S,
               "n_train_incidents": len(incidents), "n_contributing": contributing,
               "min_contributing": MIN_CONTRIBUTING, "valid": contributing >= MIN_CONTRIBUTING,
               "nodes": sorted({s for e in counts for s in e}),
               "edges": [[p, c, n] for (p, c), n in sorted(counts.items())]}
    return {**content, "sha256": _sha(content)}


def shuffled(frame: dict) -> dict:
    """Edge-shuffled control: same node set and edge count, no self-loops, drawn without replacement
    first from ordered pairs that are not real edges (real edges only when too few remain); the single
    seed is the real frame's sha256. Records the share of real edges retained."""
    real = {(p, c) for p, c, _ in frame["edges"]}
    m = len(real)
    pairs = [p for p in itertools.permutations(frame["nodes"], 2)]
    rng = random.Random(int(frame["sha256"][:16], 16))
    non_real = [p for p in pairs if p not in real]
    chosen = rng.sample(non_real, m) if len(non_real) >= m else non_real + rng.sample(sorted(real), m - len(non_real))
    share = (len(set(chosen) & real) / m) if m else 0.0
    content = {"frame_version": FRAME_VERSION, "kind": "shuffled", "key": frame["key"], "source_sha256": frame["sha256"],
               "seed_from": "source_sha256", "valid": frame["valid"], "nodes": frame["nodes"],
               "edges": [[p, c, None] for p, c in sorted(chosen)], "retained_real_share": share,
               "informative": share <= NOT_INFORMATIVE_SHARE}
    return {**content, "sha256": _sha(content)}


def train_incidents(store, datasets, split_dir: Path) -> dict[tuple, list[dict]]:
    """Train-role incidents of the split (from `assignments.jsonl`), grouped by frame key."""
    split_id = Path(split_dir).name
    out: dict[tuple, list[dict]] = {}
    for ds in datasets:
        for inc in store.incidents(ds, states=None, split_dir=split_dir, role="train"):
            out.setdefault(key_of(inc, split_id), []).append(inc)
    return out


def write_frozen(path: Path, frame: dict) -> None:
    """Write a frame once; an existing file must hold the same sha256, otherwise the run stops."""
    path = Path(path)
    if path.is_file():
        with open(path, encoding="utf-8") as f:
            old = json.load(f)
        if old.get("sha256") != frame["sha256"]:
            raise RuntimeError(f"frozen IM1 frame {path} has sha256 {old.get('sha256')}, rebuild gives {frame['sha256']}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    tmp.write_text(json.dumps(frame, sort_keys=True, indent=1), encoding="utf-8", newline="\n")
    tmp.replace(path)


def build_all(store, datasets, split_dir: Path, roles: dict[str, str], out_dir: Path) -> dict[str, dict]:
    """Build, freeze and return {key_id: {"key", "real", "shuffled"}} for every train key of the split."""
    frames = {}
    for key, incs in sorted(train_incidents(store, datasets, split_dir).items()):
        real = build_frame(store, incs, roles, key)
        shuf = shuffled(real)
        kid = key_id(key)
        write_frozen(Path(out_dir) / f"{kid}.real.json", real)
        write_frozen(Path(out_dir) / f"{kid}.shuffled.json", shuf)
        frames[kid] = {"key": list(key), "real": real, "shuffled": shuf}
    return frames


def load_frozen(out_dir: Path) -> dict[str, dict]:
    """Frozen frames as `build_all` returns them; a file whose content does not match its sha256 raises."""
    frames: dict[str, dict] = {}
    for path in sorted(Path(out_dir).glob("*.json")):
        kid, kind, _ = path.name.split(".")
        with open(path, encoding="utf-8") as f:
            fr = json.load(f)
        if _sha({k: v for k, v in fr.items() if k != "sha256"}) != fr.get("sha256"):
            raise RuntimeError(f"IM1 frame {path} does not match its sha256")
        frames.setdefault(kid, {"key": fr["key"]})[kind] = fr
    return frames


def manifest(frames: dict[str, dict]) -> dict:
    """Per key: frame hashes, validity, contributing incidents and the shuffled control's retained share."""
    return {kid: {"key": e["key"], "real_sha256": e["real"]["sha256"], "shuffled_sha256": e["shuffled"]["sha256"],
                  "valid": e["real"]["valid"], "n_contributing": e["real"]["n_contributing"],
                  "n_edges": len(e["real"]["edges"]), "retained_real_share": e["shuffled"]["retained_real_share"],
                  "shuffle_informative": e["shuffled"]["informative"]}
            for kid, e in sorted(frames.items())}


def for_arm(frames: dict[str, dict], incident: dict, split_id: str, arm: str) -> dict | None:
    """The frame an arm reads for an incident: real for `ra_im1`, shuffled for `ra_im1_shuf`; None when the
    incident's key has no train frame (the arm then takes the frame_free path)."""
    entry = frames.get(key_id(key_of(incident, split_id)))
    if entry is None:
        return None
    f = entry["real" if arm == "ra_im1" else "shuffled"]
    return {"valid": f["valid"], "sha256": f["sha256"], "edges": [(p, c) for p, c, _ in f["edges"]]}
