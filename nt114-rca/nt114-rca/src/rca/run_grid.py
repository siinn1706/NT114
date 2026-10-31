"""Chạy lưới thí nghiệm. Hai bước, đều chạy tiếp được nếu bị dừng giữa chừng.

  python -m rca.run_grid prepare configs/canonical_pilot.yaml   # đọc telemetry, lưu bằng chứng mọi điều kiện ra đĩa
  python -m rca.run_grid run     configs/canonical_pilot.yaml   # gọi LLM cho từng ô, ghi mỗi ca một dòng JSONL

Bước prepare tách riêng vì đọc log/trace tốn RAM; bước run chỉ đọc văn bản bằng chứng đã lưu.

Nguồn dữ liệu duy nhất là kho chuẩn hóa (`source: canonical`, `rca.prep`), lọc theo manifest chia tập
`split` + `split_role`. Điều kiện lấy từ `condition-matrix-<dataset>.json`; tệp bằng chứng KHÔNG chứa nhãn
(schema 2); nhãn chỉ được nối lại khi chấm điểm. Mô hình chỉ thấy `VisibleCase`.
"""
from __future__ import annotations

import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

from . import ablate, evidence, im1_frame, rcl_evidence, score
from .data import Truth, VisibleCase
from .llm import LLM, PROMPT_VERSION, Cache, aggregate, build_messages, check_no_secrets
from .retrieve import CaseStore, Embedder, format_hits

EVIDENCE_SCHEMA = 2
# Evidence-matched control for blind_root: masks the traces of a non-root service chosen from the
# full evidence text (not from span counts), so the masked service is as visible as the root.
NONROOT_EV = "blind_nonroot_ev"
# Every model of a config is an independent single-LLM run; no row depends on another model's output.
MODEL_ROLES = ("primary", "replication")
# Packages whose versions the manifest records (distribution names).
MANIFEST_PACKAGES = ("numpy", "pandas", "scipy", "scikit-learn", "pyarrow", "PyYAML")
# Evidence arms (amendment a02): `l0` is the existing pipeline (`evidence.py`); the others are the RCLAgent
# adaptation without recursion-of-thought (`rcl_evidence.py`), one LLM call per answer, `retrieval = none`.
L0 = "l0"
ARMS = (L0, *rcl_evidence.ARMS)


def load_cfg(path):
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not is_canonical(cfg):
        raise ValueError(f"{path}: only `source: canonical` configs are supported; the direct RCAEval "
                         "directory loader was retired (build the canonical store with `python -m rca.prep`)")
    cfg["_hash"] = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:10]
    return cfg


def is_canonical(cfg) -> bool:
    return cfg.get("source") == "canonical"


def _sample(items, key_system, key_sort, lim):
    """Lấy rải đều theo loại lỗi để ca thử đại diện (giữ nguyên quy tắc cũ)."""
    if not lim:
        return items
    by_sys: dict[str, list] = {}
    for c in items:
        by_sys.setdefault(key_system(c), []).append(c)
    out = []
    for lst in by_sys.values():
        lst = sorted(lst, key=key_sort)
        step = max(len(lst) // lim, 1)
        out += lst[::step][:lim]
    return out


def evidence_dir(cfg) -> Path:
    p = Path(cfg.get("evidence_dir", "results/evidence"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def cfg_arms(cfg) -> list[str]:
    """`arms` of the config (default `[l0]`: the pipeline as before)."""
    arms = list(cfg.get("arms") or [L0])
    bad = [a for a in arms if a not in ARMS]
    if bad or len(set(arms)) != len(arms):
        raise ValueError(f"arms {arms}: each must be one of {list(ARMS)}, once")
    if any(rcl_evidence.ARMS[a] for a in arms if a != L0) and not cfg.get("split"):
        raise ValueError("framed arms need a `split`: IM1 frames come only from its train role")
    return arms


def framed(cfg) -> bool:
    return any(rcl_evidence.ARMS[a] for a in cfg_arms(cfg) if a != L0)


def frames_dir(cfg) -> Path:
    return Path(cfg.get("im1_frames_dir") or evidence_dir(cfg) / "im1_frames")


def im1_frames(cfg, cn: Canon, build: bool = False) -> dict:
    """IM1 frames of the split's train role. `build`: build and freeze them (a rebuild must give the frozen
    hashes); otherwise read the frozen files, checking each file's content against its sha256."""
    if build:
        return im1_frame.build_all(cn.store, cn.datasets, cn.split_dir, cn.roles, frames_dir(cfg))
    return im1_frame.load_frozen(frames_dir(cfg))


def arm_dir(cfg, arm: str) -> Path:
    """Evidence files of an R-a arm; `l0` keeps `evidence_dir` itself."""
    return evidence_dir(cfg) if arm == L0 else evidence_dir(cfg) / "arms" / arm


# ---------------------------------------------------------------- canonical source
class Canon:
    """Kho chuẩn hóa + manifest chia tập + ma trận điều kiện cho một cấu hình."""

    def __init__(self, cfg):
        from .prep import load_config, resolve_data_home
        from .splits import load_condition_matrix
        from .store import CanonicalStore, read_json, read_jsonl
        self.cfg = cfg
        self.data_home = resolve_data_home(cfg.get("data_home"), load_config())
        self.prep_cfg = load_config()
        self.store = CanonicalStore(self.data_home)
        self.datasets = list(cfg.get("canonical_datasets", ["rcaeval"]))
        builds = {ds: self.store.build(ds) for ds in self.datasets}
        self.split_dir = self._split_dir(cfg.get("split"))
        self.roles, self.group = {}, {}
        if self.split_dir:
            # A split made on another build assigns roles to incidents that may have changed or gone.
            for b in read_json(self.split_dir / "split.json")["builds"]:
                if b["dataset_id"] in builds and b["dataset_digest"] != builds[b["dataset_id"]]["dataset_digest"]:
                    raise RuntimeError(f"split {self.split_dir.name} was made on another {b['dataset_id']} build: "
                                       "run `verify-splits`, then make the split again")
            for a in read_jsonl(self.split_dir / "assignments.jsonl"):
                self.roles[a["incident_uid"]] = a["split"]
                self.group[a["incident_uid"]] = a["group_id_hash"]
        self.matrix = {}
        for ds in self.datasets:
            m = load_condition_matrix(self.data_home, ds)
            if (m["build_id"], m["dataset_digest"]) != (builds[ds]["build_id"], builds[ds]["dataset_digest"]):
                raise RuntimeError(f"condition matrix of {ds} is from build {m['build_id']}, not the current "
                                   f"{builds[ds]['build_id']}: run `conditions` again")
            self.matrix.update(m["incidents"])
        self._labels = {}
        self.excluded_queries = {}

    def _split_dir(self, name):
        if not name:
            return None
        root = self.data_home / "splits"
        exact = root / name
        if (exact / "split.json").is_file():
            return exact
        hits = sorted(p for p in root.glob(f"{name}-*") if (p / "split.json").is_file())
        if len(hits) != 1:
            raise FileNotFoundError(f"split {name!r}: {len(hits)} matching manifests under {root}")
        return hits[0]

    @property
    def split_id(self):
        return self.split_dir.name if self.split_dir else None

    def labels(self) -> dict:
        """Vùng eval-only: chỉ dùng cho chọn mục tiêu ablation, chấm điểm và kho oracle."""
        if not self._labels:
            for ds in self.datasets:
                self._labels.update(self.store.labels(ds))
        return self._labels

    def truth(self, uid) -> Truth:
        from .legacy_view import truth
        return truth(self.labels()[uid])

    def split_roles(self) -> list[str]:
        """`split_roles: [train, test]` (e.g. the zero-shot union) or the single `split_role` (default test)."""
        roles = self.cfg.get("split_roles") or [self.cfg.get("split_role", "test")]
        return [roles] if isinstance(roles, str) else list(roles)

    def incidents(self, role):
        roles = {role} if isinstance(role, str) else set(role)
        out = []
        for ds in self.datasets:
            for inc in self.store.incidents(ds):
                u = inc["incident_uid"]
                if self.split_dir and self.roles.get(u) not in roles:
                    continue
                if not self.matrix.get(u, {}).get("conditions", {}).get("full", {}).get("applicable"):
                    continue
                out.append(inc)
        return out

    def selected(self):
        """[(VisibleCase, incident)] cho các vai trò `split_roles` / `split_role` (mặc định test)."""
        from .legacy_view import visible_case
        incs = self.incidents(self.split_roles())
        subsets = self.cfg.get("subsets")
        incs = [i for i in incs if (not subsets or i.get("dataset_subset") in subsets)
                and i["system"] in self.cfg.get("systems", [i["system"]])]
        lab = self.labels()
        if "train" in self.split_roles():
            # A train query labelled only by a node has no service to score; it is left out and counted.
            scorable = [i for i in incs if score.truth_ids(self.truth(i["incident_uid"]))]
            missing = len(incs) - len(scorable)
            self.excluded_queries = {"no_service_label": missing} if missing else {}
            if missing:
                print(f"queries: {missing} train incidents without a service label left out")
            incs = scorable
        incs = _sample(incs, lambda i: i["system"],
                       lambda i: (lab[i["incident_uid"]]["fault"]["type_raw"], i["incident_uid"]), self.cfg.get("limit_per_system"))
        return [(visible_case(i), i) for i in sorted(incs, key=lambda i: i["incident_uid"])]

    def store_incidents(self):
        """Kho truy hồi: mọi ca vai trò train có điều kiện `full` (không giới hạn bởi limit_per_system)."""
        incs = sorted(self.incidents("train"), key=lambda i: i["incident_uid"]) if self.split_dir else []
        lim = self.cfg.get("store_limit")
        return incs[:lim] if lim else incs

    def conditions(self, uid):
        """Requested conditions applicable to `uid`; `blind_nonroot_ev` wherever `blind_root` applies."""
        row_c = self.matrix[uid]["conditions"]
        return [c for c in self.cfg["conditions"]
                if row_c.get("blind_root" if c == NONROOT_EV else c, {}).get("applicable")]

    def evidence_fp(self, uid) -> str:
        """Everything a canonical evidence record depends on besides the requested conditions: the
        evidence builder and its per-dataset options, the dataset build and this incident's matrix row."""
        from .legacy_view import METRIC_ALIGN_S, VIEW_VERSION, evidence_kwargs
        ds = self.store.incident(uid)["dataset_id"]
        blob = json.dumps({"evidence": evidence.fingerprint(**evidence_kwargs(self.prep_cfg, ds)),
                           "view": [VIEW_VERSION, METRIC_ALIGN_S.get(ds)],
                           "dataset_digest": self.store.build(ds)["dataset_digest"], "matrix": self.matrix[uid]},
                          sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    def arm_fp(self, uid, arm: str, frame_sha: str | None = None) -> str:
        """Fingerprint of an R-a arm's evidence: the l0 fingerprint (data, view, matrix row), the R-a builder
        and the arm with its frame."""
        blob = json.dumps({"base": self.evidence_fp(uid), "builder": rcl_evidence.fingerprint(), "arm": arm,
                           "frame": frame_sha}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]


def _is_current(path: Path, fp: str, conditions=None) -> bool:
    """An evidence file is reused only when it was built with the same fingerprint (and conditions)."""
    if not path.exists():
        return False
    with open(path, encoding="utf-8") as f:
        rec = json.load(f)
    if rec.get("schema") == EVIDENCE_SCHEMA and "same_as_full" not in rec:
        return False
    if conditions is not None:
        conditions = [c for c in conditions if c not in rec.get("skipped", [])]
    return rec.get("evidence_fp") == fp and (conditions is None or list(rec["conditions"]) == list(conditions))


def _check_current(rec: dict, fp: str, path: Path) -> None:
    if rec.get("evidence_fp") != fp:
        raise RuntimeError(f"stale evidence {path} (fingerprint {rec.get('evidence_fp')} != {fp}): run `prepare` again")


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False)
    tmp.replace(path)


_EV_LINE = re.compile(r"^- ([a-z0-9][a-z0-9\-]*):", re.M)


def nonroot_ev_target(full_text: str, root: str, uid: str) -> str | None:
    """Non-root service listed in the Traces block of the full evidence whose number of evidence lines
    (all blocks) is closest to the root's; ties by sha256(uid + service). None when there is none."""
    traces = full_text.split("## Traces", 1)
    if len(traces) < 2:
        return None
    trace_block = traces[1].split("\n## ", 1)[0]
    counts: dict[str, int] = {}
    for m in _EV_LINE.finditer(full_text):
        counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    others = sorted({m.group(1) for m in _EV_LINE.finditer(trace_block)} - {root})
    if not others:
        return None
    n_root = counts.get(root, 0)
    return min(others, key=lambda s: (abs(counts[s] - n_root), hashlib.sha256(f"{uid}{s}".encode()).hexdigest()))


def _prep_row(uid: str, cond: str, kind: str, load_s: float, build_s: float, tel: dict, ev: dict, fp: str) -> dict:
    """One preparation-log row: what building the evidence of (incident, condition) read and cost."""
    return {"incident_uid": uid, "condition": cond, "kind": kind, "load_s": round(load_s, 4),
            "build_s": round(build_s, 4), "wall_s": round(load_s + build_s, 4),
            "telemetry_rows": {m: (None if t is None else int(len(t))) for m, t in tel.items()},
            "evidence_chars": len(ev["text"]), "truncated": ev["text"].endswith("[truncated]"),
            "evidence_fp": fp, "ts": int(time.time())}


def _canonical_evidence(cn: Canon, vc: VisibleCase, conditions, log: list | None = None, kind: str = "query") -> dict:
    """Evidence record of every condition. With `log`, appends one `_prep_row` per built condition; the
    log never enters the record, so fingerprints and cache keys are unchanged."""
    from .legacy_view import evidence_kwargs, legacy_telemetry
    t0 = time.perf_counter()
    tel = legacy_telemetry(cn.store, vc.case_id)
    load_s = time.perf_counter() - t0
    tr = cn.truth(vc.case_id)
    target = cn.matrix[vc.case_id]["nonroot_target"]
    kw = evidence_kwargs(cn.prep_cfg, vc.dataset)
    rec = {"schema": EVIDENCE_SCHEMA, "incident_uid": vc.case_id, "system": vc.system,
           "evidence_fp": cn.evidence_fp(vc.case_id), "candidates": evidence.shuffled_candidates(vc), "conditions": {},
           "same_as_full": {}}
    t0 = time.perf_counter()
    full = evidence.build(vc, tel, **kw)
    full_s = time.perf_counter() - t0
    for cond in conditions:
        t0 = time.perf_counter()
        if cond == NONROOT_EV:
            ev_target = nonroot_ev_target(full["text"], tr.root_service, vc.case_id)
            if ev_target is None:
                rec.setdefault("skipped", []).append(cond)
                continue
            ev = evidence.build(vc, ablate.mask_service_traces(tel, ev_target), **kw)
        else:
            ev = full if cond == "full" else evidence.build(vc, ablate.apply(tel, cond, tr.root_service, target), **kw)
        rec["conditions"][cond] = ev
        rec["same_as_full"][cond] = ev["text"] == full["text"]
        if log is not None:
            # a condition's cost includes the telemetry read; `full` is built once and reused
            build_s = full_s if cond == "full" else time.perf_counter() - t0
            log.append(_prep_row(vc.case_id, cond, kind, load_s, build_s, tel, ev, rec["evidence_fp"]))
    return rec


def _arm_evidence(cn: Canon, vc: VisibleCase, l0_rec: dict, arm: str, frame: dict | None = None,
                  log: list | None = None) -> dict:
    """R-a evidence record of the conditions present in the l0 record. `blind_nonroot_ev` masks the
    service chosen from the l0 full evidence (same target as l0); other conditions as in l0."""
    from .legacy_view import evidence_kwargs, legacy_telemetry
    t0 = time.perf_counter()
    tel = legacy_telemetry(cn.store, vc.case_id)
    load_s = time.perf_counter() - t0
    tr = cn.truth(vc.case_id)
    target = cn.matrix[vc.case_id]["nonroot_target"]
    kw = evidence_kwargs(cn.prep_cfg, vc.dataset)
    fsha = frame.get("sha256") if frame else None
    rec = {"schema": EVIDENCE_SCHEMA, "arm": arm, "incident_uid": vc.case_id, "system": vc.system,
           "evidence_fp": cn.arm_fp(vc.case_id, arm, fsha), "candidates": l0_rec["candidates"], "conditions": {},
           "same_as_full": {}}
    for cond in l0_rec["conditions"]:
        t0 = time.perf_counter()
        if cond == NONROOT_EV:
            masked = ablate.mask_service_traces(
                tel, nonroot_ev_target(l0_rec["conditions"]["full"]["text"], tr.root_service, vc.case_id))
        else:
            masked = tel if cond == "full" else ablate.apply(tel, cond, tr.root_service, target)
        rec["conditions"][cond] = rcl_evidence.build(vc, masked, arm, frame, **kw)
        if log is not None:
            log.append({**_prep_row(vc.case_id, cond, "query", load_s, time.perf_counter() - t0, masked,
                                    rec["conditions"][cond], rec["evidence_fp"]), "arm": arm})
    full = rec["conditions"].get("full")
    rec["same_as_full"] = {c: full is not None and ev["text"] == full["text"] for c, ev in rec["conditions"].items()}
    return rec


def ablation_log(cn: Canon, uids, ev_dir: Path | None = None) -> list[dict]:
    """Vùng eval-only: dịch vụ bị che của từng biến thể (ghi cạnh kết quả, không ở thư mục bằng chứng)."""
    out = []
    for u in sorted(uids):
        rec = None
        if ev_dir is not None and (ev_dir / f"{u}.json").exists():
            with open(ev_dir / f"{u}.json", encoding="utf-8") as f:
                rec = json.load(f)
        for cond in cn.conditions(u):
            if cond == NONROOT_EV:
                if rec is None or cond not in rec["conditions"]:
                    continue
                masked = nonroot_ev_target(rec["conditions"]["full"]["text"], cn.truth(u).root_service, u)
            else:
                masked = {"blind_root": cn.truth(u).root_service, "blind_nonroot": cn.matrix[u]["nonroot_target"]}.get(cond)
            out.append({"variant_id": f"{u}|{cond}", "pair_id": u, "condition": cond, "masked_service": masked})
    return out


def prepare(cfg):
    cn = Canon(cfg)
    _require_split_for_retrieval(cfg, cn)
    if NONROOT_EV in cfg["conditions"] and "full" not in cfg["conditions"]:
        raise ValueError(f"{NONROOT_EV} is chosen from the full evidence: add 'full' to conditions")
    out = evidence_dir(cfg)
    r_arms = [a for a in cfg_arms(cfg) if a != L0]
    # frames are built and frozen before any evidence of a framed arm
    frames = im1_frames(cfg, cn, build=True) if framed(cfg) else {}
    sel = cn.selected()
    print(f"{len(sel)} incidents ({cn.split_id or 'no split'}, roles {cn.split_roles()})")
    plog = prepare_log_path(cfg)
    plog.parent.mkdir(parents=True, exist_ok=True)
    with open(plog, "a", encoding="utf-8", newline="\n") as fp_log:
        def flush(rows):
            for r in rows:
                fp_log.write(json.dumps(r, ensure_ascii=False) + "\n")
            fp_log.flush()

        for i, (vc, inc) in enumerate(sel, 1):
            f = out / f"{vc.case_id}.json"
            if _is_current(f, cn.evidence_fp(vc.case_id), cn.conditions(vc.case_id)):
                with open(f, encoding="utf-8") as fh:
                    rec = json.load(fh)
            else:
                rows = []
                rec = _canonical_evidence(cn, vc, cn.conditions(vc.case_id), rows)
                _write_json(f, rec)
                flush(rows)
                print(f"[{i}/{len(sel)}] {vc.case_id}: {list(rec['conditions'])}")
            for arm in r_arms:
                fr = im1_frame.for_arm(frames, inc, cn.split_id, arm) if rcl_evidence.ARMS[arm] else None
                fa = arm_dir(cfg, arm) / f"{vc.case_id}.json"
                if not _is_current(fa, cn.arm_fp(vc.case_id, arm, fr and fr["sha256"]), list(rec["conditions"])):
                    rows = []
                    _write_json(fa, _arm_evidence(cn, vc, rec, arm, fr, rows))
                    flush(rows)
        if any(m != "none" for m in cfg.get("retrieval", ["none"])):
            from .legacy_view import visible_case
            st = cn.store_incidents()
            for k, inc in enumerate(st, 1):
                f = out / "store" / f"{inc['incident_uid']}.json"
                if not _is_current(f, cn.evidence_fp(inc["incident_uid"]), ["full"]):
                    rows = []
                    _write_json(f, _canonical_evidence(cn, visible_case(inc), ["full"], rows, kind="store"))
                    flush(rows)
            print(f"store: {len(st)} train-role incidents")
    log = Path(cfg["out"]).parent / "ablation_log.jsonl"
    with open(log, "w", encoding="utf-8", newline="\n") as fh:
        for r in ablation_log(cn, [vc.case_id for vc, _ in sel], out):
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- bước 1
def load_evidence(cfg) -> list[dict]:
    """Mỗi bản ghi có `vc` (VisibleCase, cho mô hình) và `truth` (Truth, chỉ để chấm điểm)."""
    from .legacy_view import visible_case
    recs = []
    cn = Canon(cfg)
    wanted = {vc.case_id for vc, _ in cn.selected()}
    stray = 0
    for f in sorted(evidence_dir(cfg).glob("*.json")):
        with open(f, encoding="utf-8") as fh:
            r = json.load(fh)
        if r.get("incident_uid") not in wanted:   # left by another split, role or limit
            stray += 1
            continue
        if r.get("schema") != EVIDENCE_SCHEMA:
            raise RuntimeError(f"{f}: evidence schema {r.get('schema')!r} is not {EVIDENCE_SCHEMA}; rerun `prepare`")
        _check_current(r, cn.evidence_fp(r["incident_uid"]), f)
        r["vc"] = visible_case(cn.store.incident(r["incident_uid"]))
        r["truth"] = cn.truth(r["incident_uid"])
        recs.append(r)
    if stray:
        print(f"evidence: {stray} files outside the selected incidents ignored")
    return recs


def load_arm_evidence(cfg, arm: str) -> list[dict]:
    """R-a evidence records of `arm` (as `load_evidence`), checked against their fingerprint."""
    from .legacy_view import visible_case
    recs = []
    cn = Canon(cfg)
    frames = im1_frames(cfg, cn) if rcl_evidence.ARMS[arm] else {}
    for f in sorted(arm_dir(cfg, arm).glob("*.json")):
        with open(f, encoding="utf-8") as fh:
            r = json.load(fh)
        if r.get("schema") != EVIDENCE_SCHEMA or r.get("arm") != arm:
            raise RuntimeError(f"{f}: not a schema {EVIDENCE_SCHEMA} record of arm {arm!r}; rerun `prepare`")
        fsha = next((ev.get("frame_sha256") for ev in r["conditions"].values()), None)
        if rcl_evidence.ARMS[arm]:      # the evidence must use the frozen frame of its key
            fr = im1_frame.for_arm(frames, cn.store.incident(r["incident_uid"]), cn.split_id, arm)
            if (fr and fr["sha256"]) != fsha:
                raise RuntimeError(f"{f}: frame {fsha} is not the frozen frame {fr and fr['sha256']}; rerun `prepare`")
        _check_current(r, cn.arm_fp(r["incident_uid"], arm, fsha), f)
        r["vc"] = visible_case(cn.store.incident(r["incident_uid"]))
        r["truth"] = cn.truth(r["incident_uid"])
        recs.append(r)
    return recs


def _require_split_for_retrieval(cfg, cn: Canon) -> None:
    if any(m != "none" for m in cfg.get("retrieval", ["none"])) and not cn.split_dir:
        raise ValueError("retrieval needs a `split`: precedents come only from its train role")


def _store_entries(cfg, cn: Canon) -> tuple[list[dict], dict]:
    """Precedents = exactly the train-role incidents of the configured split (after `store_limit`).

    Files under `<evidence_dir>/store` left by another split or limit are ignored and counted; a missing
    eligible file raises. Prompt v1 names one root service per precedent, so train incidents labelled
    only by a root set or a node are excluded and counted by granularity. Returns (entries, info)."""
    _require_split_for_retrieval(cfg, cn)
    eligible = [i["incident_uid"] for i in cn.store_incidents()]
    queries = {vc.case_id for vc, _ in cn.selected()}
    sdir = evidence_dir(cfg) / "store"
    entries, excluded = [], {}
    # Train queries search the train store itself; their own incident and group are excluded at search time.
    train_queries = "train" in cn.split_roles()
    for u in eligible:
        if cn.roles.get(u) != "train" or (u in queries and not train_queries):
            raise RuntimeError(f"store incident {u} is not a train-role incident outside the scored set")
        f = sdir / f"{u}.json"
        if not f.is_file():
            raise RuntimeError(f"store evidence {f} is missing for split {cn.split_id}: run `prepare` again")
        with open(f, encoding="utf-8") as fh:
            r = json.load(fh)
        _check_current(r, cn.evidence_fp(u), f)
        t = cn.truth(u)   # nhãn của ca TRAIN (bản post-mortem), không phải của ca hỏi
        if t.root_service is None:
            excluded[t.granularity] = excluded.get(t.granularity, 0) + 1
            continue
        entries.append({"case_id": u, "system": r["system"], "root": t.root_service, "root_ids": tuple(t.root_ids),
                        "granularity": t.granularity, "fault": t.fault, "text": r["conditions"]["full"]["text"],
                        "evidence_fp": r["evidence_fp"]})
    on_disk = {p.stem for p in sdir.glob("*.json")}
    binding = {"split_id": cn.split_id, "split_sha256": _sha256(cn.split_dir / "split.json"),
               "store_limit": cfg.get("store_limit"), "eligible": eligible}
    info = {"split_id": cn.split_id, "store_limit": cfg.get("store_limit"), "eligible": len(eligible),
            "entries": len(entries), "excluded": excluded, "ignored_files": len(on_disk - set(eligible)),
            "binding": hashlib.sha256(json.dumps(binding, sort_keys=True).encode()).hexdigest()[:16]}
    return entries, info


def exclusions(store: CaseStore, vc: VisibleCase, truth: Truth, mode: str, group_members: frozenset) -> frozenset:
    """`precedent`: cùng nhóm trong manifest (không nhãn). `no_precedent` (oracle): thêm cùng (gốc, lỗi) từ Truth."""
    ex = frozenset(group_members) - {vc.case_id}
    if mode == "no_precedent":
        ex |= store.oracle_exclusions(score.truth_ids(truth), truth.fault)
    return ex


def _git(*args) -> str | None:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True,
                              cwd=Path(__file__).resolve().parent).stdout.strip()
    except Exception:
        return None


def _gpu_name() -> str | None:
    if not shutil.which("nvidia-smi"):
        return None
    try:
        return subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True,
                              text=True, check=True).stdout.strip() or None
    except Exception:
        return None


def prepare_log_path(cfg) -> Path:
    """Preparation cost log (appended by `prepare`), next to the results; outside the evidence files."""
    return Path(cfg["out"]).parent / "prepare_log.jsonl"


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _package_versions() -> dict:
    from importlib import metadata
    out = {}
    for name in MANIFEST_PACKAGES:
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            out[name] = None
    return out


def write_config_copy(cfg) -> tuple[str, Path]:
    """The resolved config as `config.yaml` next to the grid; returns (sha256 of its text, path)."""
    resolved = {k: v for k, v in cfg.items() if not k.startswith("_")}
    check_no_secrets(resolved)
    text = yaml.safe_dump(resolved, sort_keys=True, allow_unicode=True)
    path = Path(cfg["out"]).parent / "config.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest(), path


def write_manifest(cfg, cn: Canon, server_fps: dict, started: float, executions: list | None = None,
                   store_info: dict | None = None) -> dict:
    """`manifest.json` next to the results: code, environment, data, split, config and model identity of
    this run, each model's execution signature and the retrieval store's binding to the split. Wall times
    in the logs are measurements of the machine named by `platform`."""
    executions = executions or [{} for _ in cfg["models"]]
    from .legacy_view import VIEW_VERSION
    bundle = {}
    root = cn.data_home.parent
    if (root / "bundle.json").is_file():
        with open(root / "bundle.json", encoding="utf-8") as f:
            bundle["bundle_id"] = json.load(f).get("bundle_id")
    if (root / "MANIFEST.sha256").is_file():
        bundle["manifest_sha256"] = hashlib.sha256((root / "MANIFEST.sha256").read_bytes()).hexdigest()
    man = {"git_commit": _git("rev-parse", "HEAD"), "git_dirty": bool(_git("status", "--porcelain", "--", ".")),
           **bundle, "split_id": cn.split_id,
           "split_roles": cn.split_roles(), **({"excluded_queries": cn.excluded_queries} if cn.excluded_queries else {}),
           "config_hash": cfg["_hash"],
           "models": [{"name": m["name"], "role": m.get("role", "primary"), "revision": m.get("revision"),
                       "quantization": m.get("quantization"), "backend": m.get("backend", "vllm"),
                       "presence_penalty": m.get("presence_penalty"),
                       "vllm_version": m.get("vllm_version"), "server_fp": server_fps.get(m["name"]),
                       **ex}
                      for m, ex in zip(cfg["models"], executions)],
           "gpu": _gpu_name(), "prompt_version": PROMPT_VERSION, "seed": cfg.get("seed", 0),
           "sampling": {"n": cfg["n_samples"], "temperature": cfg["temperature"]},
           "raw_outputs": raw_outputs_path(cfg).name if raw_outputs_enabled(cfg) else None,
           "started": int(started), "finished": int(time.time())}
    cfg_sha, cfg_path = write_config_copy(cfg)
    man.update({"manifest_version": 3, "store": store_info, "python": platform.python_version(),
                "platform": platform.platform(),
                "packages": _package_versions(), "evidence_builder_version": evidence.BUILDER_VERSION,
                "legacy_view_version": VIEW_VERSION, "config_sha256": cfg_sha, "config_copy": cfg_path.name,
                **({"arms": cfg_arms(cfg), "rcl_builder_version": rcl_evidence.BUILDER_VERSION}
                   if cfg_arms(cfg) != [L0] else {}),
                **({"im1_frames": im1_frame.manifest(im1_frames(cfg, cn))} if framed(cfg) else {}),
                "split_sha256": _sha256(cn.split_dir / "split.json") if cn.split_dir else None,
                "prepare_log_sha256": _sha256(prepare_log_path(cfg))})
    check_no_secrets(man)
    path = Path(cfg["out"]).parent / "manifest.json"
    _write_json(path, man)
    return man


class _NullFile:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def raw_outputs_enabled(cfg) -> bool:
    """`raw_outputs: false` turns raw-output persistence off (default on)."""
    return bool(cfg.get("raw_outputs", True))


def raw_outputs_path(cfg) -> Path:
    """`llm_raw.jsonl` next to the results (results*/ is git-ignored), or `raw_outputs_path`. The
    completions can quote telemetry, so the file is a private local artefact like the evidence."""
    return Path(cfg.get("raw_outputs_path") or Path(cfg["out"]).parent / "llm_raw.jsonl")


def raw_output_keys(path: Path) -> set:
    """Keys already in a raw-output file; a torn last line (crash mid-write) is skipped."""
    keys = set()
    if path.exists():
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    keys.add(json.loads(line)["key"])
                except (ValueError, KeyError, TypeError):
                    continue
    return keys


def _open_append(path: Path):
    """Append mode that first ends a torn last line, so the next record starts on a line of its own."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size:
        with open(path, "rb") as f:
            f.seek(-1, 2)
            torn = f.read(1) != b"\n"
        if torn:
            with open(path, "ab") as f:
                f.write(b"\n")
    return open(path, "a", encoding="utf-8", newline="\n")


def raw_output_row(key, model, role, uid, cond, meth, mode, res) -> dict:
    """One raw-output record per grid cell (`key` joins it to the grid row). No label field: truth is
    joined only in the grid row. A crash between the two writes leaves a raw record without a grid
    row; the resumed run reuses it instead of writing a second one."""
    raw = res.get("raw")
    return {"key": key, "model": model, "model_role": role, "incident_uid": uid, "condition": cond,
            "retrieval": meth, "store_mode": mode, "cached": res["cached"], "raw_available": raw is not None,
            "samples": res["samples"], **(raw or {})}


def _check_roles(models):
    for m in models:
        if m.get("role", "primary") not in MODEL_ROLES:
            raise ValueError(f"model {m['name']}: role must be one of {MODEL_ROLES}")


def _check_resumable(rows: list[dict], llms: list[LLM], out_path: Path) -> None:
    """A grid only holds rows of the execution signatures this config declares (several entries of one model,
    e.g. sampling arms, each have their own); rows made with other settings are never resumed."""
    declared = {}
    for llm in llms:
        declared.setdefault(llm.model, {})[llm.execution_signature()] = llm.execution()
    for r in rows:
        mine = declared.get(r.get("model"))
        if mine is None or r.get("exec_sig") in mine:
            continue
        old = r.get("execution") or {}
        diff = sorted({k for now in mine.values() for k in now if old.get(k, "<missing>") != now[k]}) or ["exec_sig"]
        raise RuntimeError(f"{out_path} holds rows of model {r['model']!r} made with other settings ({', '.join(diff)}); "
                           "write this configuration to a new `out` path")


# ---------------------------------------------------------------- bước 2
def run(cfg):
    cn = Canon(cfg)
    _require_split_for_retrieval(cfg, cn)
    arms = cfg_arms(cfg)
    wanted = {vc.case_id for vc, _ in cn.selected()}
    sources = [(a, [r for r in (load_evidence(cfg) if a == L0 else load_arm_evidence(cfg, a)) if r["vc"].case_id in wanted])
               for a in arms]
    for a, recs in sources:
        print(f"arm {a}: {len(recs)} cases with evidence")

    _check_roles(cfg["models"])
    started = time.time()
    store, store_fp, store_info = None, "-", None
    if any(m != "none" for m in cfg["retrieval"]):
        entries, store_info = _store_entries(cfg, cn)
        emb_name = cfg.get("embedder", "BAAI/bge-small-en-v1.5")
        store = CaseStore(entries, Embedder(emb_name))
        if emb_name != "tfidf" and store.emb.kind != "st":
            raise RuntimeError(f"embedder {emb_name!r} is unavailable (fell back to {store.emb.kind}); "
                               "install sentence-transformers or set `embedder: tfidf` explicitly")
        blob = "\n".join([f"embedder:{store.emb.kind}:{emb_name}", f"binding:{store_info['binding']}"]
                         + sorted(f"{e['case_id']}:{e['evidence_fp']}" for e in entries))
        store_fp = hashlib.sha256(blob.encode()).hexdigest()[:16]
        store_info["store_fp"] = store_fp
        print(f"case store: {len(entries)} entries ({store_info['ignored_files']} other store files ignored, "
              f"excluded {store_info['excluded'] or 'none'}), embedder={store.emb.kind}")
    members: dict[str, set] = {}
    for u, g in cn.group.items():
        members.setdefault(g, set()).add(u)

    out_path = Path(cfg["out"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if out_path.exists():
        with open(out_path, encoding="utf-8") as fh:
            existing = [json.loads(l) for l in fh if l.strip()]
    done = {r["key"] for r in existing}
    cache = Cache(cfg.get("cache", "results/llm_cache.sqlite"))
    keep_raw = raw_outputs_enabled(cfg)
    raw_path = raw_outputs_path(cfg)
    raw_done = raw_output_keys(raw_path) if keep_raw else set()
    llms = []
    for m in cfg["models"]:
        llm = LLM(m["name"], m.get("base_url", "http://localhost:8000/v1"), m.get("backend", "vllm"),
                  n=cfg["n_samples"], temperature=cfg["temperature"], seed=cfg.get("seed", 0), cache=cache,
                  max_tokens=m.get("max_tokens", 400), revision=m.get("revision"),
                  chat_template_kwargs=m.get("chat_template_kwargs"), logprobs=m.get("logprobs", False),
                  presence_penalty=m.get("presence_penalty"), keep_raw=keep_raw)
        llm.server_fingerprint(m.get("launch_args"), m.get("quantization"))
        llms.append(llm)
    _check_resumable(existing, llms, out_path)
    server_fps = {llm.model: llm.server_fp for llm in llms}
    executions = [{"exec_sig": llm.execution_signature(), "execution": llm.execution()} for llm in llms]

    with open(out_path, "a", encoding="utf-8", newline="\n") as fout, \
            (_open_append(raw_path) if keep_raw else _NullFile()) as fraw:
        for m, llm, ex in zip(cfg["models"], llms, executions):
            sig = ex["exec_sig"]
            role, rev = m.get("role", "primary"), m.get("revision")
            for arm, r in ((a, r) for a, recs in sources for r in recs):
                vc, tr, cands = r["vc"], r["truth"], r["candidates"]
                grp = frozenset(members.get(cn.group.get(vc.case_id), ()))
                for cond, ev in r["conditions"].items():
                    # R-a arms run only the `retrieval = none` cell
                    cells = [("none", "-")] + ([] if arm != L0 else [(meth, mode) for meth in cfg["retrieval"]
                                                                     if meth != "none" for mode in cfg["store_modes"]])
                    for meth, mode in cells:
                        if meth == "none" and "none" not in cfg["retrieval"] and arm == L0:
                            continue
                        # the evidence and store fingerprints and the execution signature are part of the
                        # key: rows produced from stale evidence or other settings are never counted as done
                        key = (f"{m['name']}|{rev}|{PROMPT_VERSION}|{vc.case_id}|{cond}|{meth}|{mode}|{r['evidence_fp']}|"
                               f"{store_fp if meth != 'none' else '-'}|sig={sig}")
                        if arm != L0:
                            key += f"|arm={arm}|frame={ev.get('frame_sha256') or '-'}"
                        if key in done:
                            continue
                        ft = ev.get("features", {})
                        applicable = arm == L0 or ev["path"] == "trace" or bool(ft.get("has_metrics") or ft.get("has_logs"))
                        t0 = time.perf_counter()
                        hits = (store.search(ev["text"], vc, meth, mode, cfg["top_k"], exclude_ids=exclusions(store, vc, tr, mode, grp))
                                if meth != "none" else [])
                        retrieval_s = round(time.perf_counter() - t0, 4) if meth != "none" else 0.0
                        msgs = build_messages(vc, cands, ev["text"], format_hits(hits))
                        if applicable:
                            res = llm.ask(msgs, cands, scope=None if arm == L0 else arm)
                        else:   # no telemetry for any tool: not_applicable, no call, kept in the denominator
                            res = {"samples": [], "prompt_tokens": 0, "completion_tokens": 0, "latency_s": 0.0,
                                   "cached": False}
                        if keep_raw and key not in raw_done:   # before the grid row: a done key has its raw record
                            fraw.write(json.dumps({**raw_output_row(key, m["name"], role, vc.case_id, cond, meth, mode, res),
                                                   "exec_sig": sig}, ensure_ascii=False) + "\n")
                            fraw.flush()
                            raw_done.add(key)
                        agg = aggregate(res["samples"])
                        sc = score.correctness(agg["ranking"], tr, len(cands))
                        row = {
                            "key": key, "cfg": cfg["_hash"], "model": m["name"], "model_role": role, "model_revision": rev,
                            "prompt_version": PROMPT_VERSION, "server_fp": llm.server_fp, "backend": llm.backend,
                            "sampling": {"n": llm.n, "temperature": llm.temperature, "seed": llm.seed,
                                         "presence_penalty": llm.presence_penalty, "max_tokens": llm.max_tokens},
                            "exec_sig": sig, "execution": ex["execution"],
                            "case_id": vc.case_id,
                            "system": vc.system, "dataset": vc.dataset, "fault": tr.fault, "truth": tr.root_service,
                            "truth_ids": list(score.truth_ids(tr)), "label_granularity": tr.granularity,
                            "n_candidates": len(cands), "condition": cond, "retrieval": meth, "store_mode": mode,
                            "rank": sc["rank"], "correct": sc["correct_at_1"], "correct_at_3": sc["correct_at_3"],
                            "parse_failed": sc["parse_failed"], "set_scored": sc["set_scored"], **agg,
                            "features": ev["features"],
                            "hits": [{"case_id": h["case_id"], "root": h["root"], "dense_sim": h["dense_sim"]} for h in hits],
                            "hit_has_truth": any(set(score.truth_ids(tr)) & {h["root"], *h["root_ids"]} for h in hits),
                            "prompt_tokens": res["prompt_tokens"], "completion_tokens": res["completion_tokens"],
                            "latency_s": res["latency_s"], "cached": res["cached"], "retrieval_s": retrieval_s,
                            "ts": int(time.time()),
                            "incident_uid": vc.case_id, "pair_id": vc.case_id,
                            "split_id": cn.split_id,
                            "split_role": cn.roles.get(vc.case_id),
                            "oracle_store": mode == "no_precedent",
                            "evidence_fp": r["evidence_fp"], "store_fp": store_fp if meth != "none" else None,
                        }
                        if arm != L0:   # l0 rows keep their schema: a row without `arm` is arm l0
                            row.update(arm=arm, path=ev["path"], frame_sha256=ev.get("frame_sha256"),
                                       llm_calls=int(applicable),
                                       outcome=score.outcome(sc["correct_at_1"], sc["parse_failed"], applicable))
                        fout.write(json.dumps(row) + "\n")
                        fout.flush()
                        done.add(key)
            print(f"model {m['name']} done")
    write_manifest(cfg, cn, server_fps, started, executions, store_info)


if __name__ == "__main__":
    step, path = sys.argv[1], sys.argv[2]
    {"prepare": prepare, "run": run}[step](load_cfg(path))
