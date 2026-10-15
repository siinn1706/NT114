"""Chạy lưới thí nghiệm. Hai bước, đều chạy tiếp được nếu bị dừng giữa chừng.

  python -m rca.run_grid prepare configs/pilot.yaml   # đọc telemetry, lưu bằng chứng mọi điều kiện ra đĩa
  python -m rca.run_grid run     configs/pilot.yaml   # gọi LLM cho từng ô, ghi mỗi ca một dòng JSONL

Bước prepare tách riêng vì đọc log/trace tốn RAM; bước run chỉ đọc văn bản bằng chứng đã lưu.

Hai nguồn dữ liệu:
  - mặc định (legacy): thư mục RCAEval `data_root`, như trước.
  - `source: canonical`: kho chuẩn hóa (`rca.prep`), lọc theo manifest chia tập `split` + `split_role`.
    Điều kiện lấy từ `condition-matrix-<dataset>.json`; tệp bằng chứng KHÔNG chứa nhãn (schema 2);
    nhãn chỉ được nối lại khi chấm điểm. Mô hình chỉ thấy `VisibleCase`.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

import yaml

from . import ablate, evidence, score
from .data import Case, Truth, VisibleCase, discover_cases, load_case
from .llm import LLM, PROMPT_VERSION, Cache, aggregate, build_messages
from .retrieve import CaseStore, Embedder, format_hits

EVIDENCE_SCHEMA = 2
# Evidence-matched control for blind_root: masks the traces of a non-root service chosen from the
# full evidence text (not from span counts), so the masked service is as visible as the root.
NONROOT_EV = "blind_nonroot_ev"
MODEL_ROLES = ("primary", "escalation", "replication")


def load_cfg(path):
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
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


def select_cases(cfg) -> list[Case]:
    cases = discover_cases(cfg["data_root"], tuple(cfg.get("datasets", ["re2", "re3"])))
    cases = [c for c in cases if c.system in cfg.get("systems", [c.system])]
    return _sample(cases, lambda c: c.system, lambda c: (c.fault, c.case_id), cfg.get("limit_per_system"))


def evidence_dir(cfg) -> Path:
    p = Path(cfg.get("evidence_dir", "results/evidence"))
    p.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------- canonical source
class Canon:
    """Kho chuẩn hóa + manifest chia tập + ma trận điều kiện cho một cấu hình."""

    def __init__(self, cfg):
        from .prep import load_config, resolve_data_home
        from .splits import load_condition_matrix
        from .store import CanonicalStore, read_jsonl
        self.cfg = cfg
        self.data_home = resolve_data_home(cfg.get("data_home"), load_config())
        self.prep_cfg = load_config()
        self.store = CanonicalStore(self.data_home)
        self.datasets = list(cfg.get("canonical_datasets", ["rcaeval"]))
        self.matrix = {}
        for ds in self.datasets:
            self.matrix.update(load_condition_matrix(self.data_home, ds)["incidents"])
        self.split_dir = self._split_dir(cfg.get("split"))
        self.roles, self.group = {}, {}
        if self.split_dir:
            for a in read_jsonl(self.split_dir / "assignments.jsonl"):
                self.roles[a["incident_uid"]] = a["split"]
                self.group[a["incident_uid"]] = a["group_id_hash"]
        self._labels = {}

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


def _canonical_evidence(cn: Canon, vc: VisibleCase, conditions) -> dict:
    from .legacy_view import evidence_kwargs, legacy_telemetry
    tel = legacy_telemetry(cn.store, vc.case_id)
    tr = cn.truth(vc.case_id)
    target = cn.matrix[vc.case_id]["nonroot_target"]
    kw = evidence_kwargs(cn.prep_cfg, vc.dataset)
    rec = {"schema": EVIDENCE_SCHEMA, "incident_uid": vc.case_id, "system": vc.system,
           "evidence_fp": cn.evidence_fp(vc.case_id), "candidates": evidence.shuffled_candidates(vc), "conditions": {},
           "same_as_full": {}}
    full = evidence.build(vc, tel, **kw)
    for cond in conditions:
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


def prepare_canonical(cfg):
    cn = Canon(cfg)
    if NONROOT_EV in cfg["conditions"] and "full" not in cfg["conditions"]:
        raise ValueError(f"{NONROOT_EV} is chosen from the full evidence: add 'full' to conditions")
    out = evidence_dir(cfg)
    sel = cn.selected()
    print(f"{len(sel)} incidents ({cn.split_id or 'no split'}, roles {cn.split_roles()})")
    for i, (vc, _) in enumerate(sel, 1):
        f = out / f"{vc.case_id}.json"
        if _is_current(f, cn.evidence_fp(vc.case_id), cn.conditions(vc.case_id)):
            continue
        rec = _canonical_evidence(cn, vc, cn.conditions(vc.case_id))
        _write_json(f, rec)
        print(f"[{i}/{len(sel)}] {vc.case_id}: {list(rec['conditions'])}")
    if any(m != "none" for m in cfg.get("retrieval", ["none"])) and cn.split_dir:
        from .legacy_view import visible_case
        st = cn.store_incidents()
        for k, inc in enumerate(st, 1):
            f = out / "store" / f"{inc['incident_uid']}.json"
            if not _is_current(f, cn.evidence_fp(inc["incident_uid"]), ["full"]):
                _write_json(f, _canonical_evidence(cn, visible_case(inc), ["full"]))
        print(f"store: {len(st)} train-role incidents")
    log = Path(cfg["out"]).parent / "ablation_log.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "w", encoding="utf-8", newline="\n") as fh:
        for r in ablation_log(cn, [vc.case_id for vc, _ in sel], out):
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- bước 1
def prepare(cfg):
    if is_canonical(cfg):
        return prepare_canonical(cfg)
    out = evidence_dir(cfg)
    cases = select_cases(cfg)
    print(f"{len(cases)} cases")
    fp = evidence.fingerprint()
    for i, c in enumerate(cases, 1):
        f = out / f"{c.case_id}.json"
        if _is_current(f, fp):
            continue
        tel = load_case(c)
        vc = c.visible()
        rec = {"case": {**asdict(c), "path": str(c.path)}, "evidence_fp": fp, "candidates": evidence.shuffled_candidates(vc),
               "conditions": {}}
        for cond in cfg["conditions"]:
            if not ablate.applicable(cond, tel):
                continue
            ev = evidence.build(vc, ablate.apply(tel, cond, c.root_service))
            rec["conditions"][cond] = ev
        _write_json(f, rec)
        print(f"[{i}/{len(cases)}] {c.case_id}: {list(rec['conditions'])}")


def load_evidence(cfg) -> list[dict]:
    """Mỗi bản ghi có `vc` (VisibleCase, cho mô hình) và `truth` (Truth, chỉ để chấm điểm)."""
    recs = []
    cn = Canon(cfg) if is_canonical(cfg) else None
    for f in sorted(evidence_dir(cfg).glob("*.json")):
        with open(f, encoding="utf-8") as fh:
            r = json.load(fh)
        if r.get("schema") == EVIDENCE_SCHEMA:
            from .legacy_view import visible_case
            _check_current(r, cn.evidence_fp(r["incident_uid"]), f)
            r["vc"] = visible_case(cn.store.incident(r["incident_uid"]))
            r["truth"] = cn.truth(r["incident_uid"])
        else:
            _check_current(r, evidence.fingerprint(), f)
            c = Case(**{**r["case"], "path": Path(r["case"]["path"])})
            r["case_obj"], r["vc"], r["truth"] = c, c.visible(), c.truth()
        recs.append(r)
    return recs


def _store_entries(cfg, recs, cn: Canon | None) -> list[dict]:
    if cn is not None and cn.split_dir:
        entries = []
        for f in sorted((evidence_dir(cfg) / "store").glob("*.json")):
            with open(f, encoding="utf-8") as fh:
                r = json.load(fh)
            _check_current(r, cn.evidence_fp(r["incident_uid"]), f)
            t = cn.truth(r["incident_uid"])   # nhãn của ca TRAIN (bản post-mortem), không phải của ca hỏi
            entries.append({"case_id": r["incident_uid"], "system": r["system"], "root": t.root_service, "fault": t.fault,
                            "text": r["conditions"]["full"]["text"], "evidence_fp": r["evidence_fp"]})
        return entries
    return [{"case_id": r["vc"].case_id, "system": r["vc"].system, "root": r["truth"].root_service,
             "fault": r["truth"].fault, "text": r["conditions"]["full"]["text"], "evidence_fp": r["evidence_fp"]}
            for r in recs if "full" in r["conditions"]]


def exclusions(store: CaseStore, vc: VisibleCase, truth: Truth, mode: str, group_members: frozenset) -> frozenset:
    """`precedent`: cùng nhóm trong manifest (không nhãn). `no_precedent` (oracle): thêm cùng (gốc, lỗi) từ Truth."""
    ex = frozenset(group_members) - {vc.case_id}
    if mode == "no_precedent":
        ex |= store.oracle_exclusions(truth.root_service, truth.fault)
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


def write_manifest(cfg, cn: Canon | None, server_fps: dict, started: float) -> dict:
    """`manifest.json` next to the results: code, data, split, config and model identity of this run."""
    from . import jev
    bundle = {}
    if cn is not None:
        root = cn.data_home.parent
        if (root / "bundle.json").is_file():
            with open(root / "bundle.json", encoding="utf-8") as f:
                bundle["bundle_id"] = json.load(f).get("bundle_id")
        if (root / "MANIFEST.sha256").is_file():
            bundle["manifest_sha256"] = hashlib.sha256((root / "MANIFEST.sha256").read_bytes()).hexdigest()
    man = {"git_commit": _git("rev-parse", "HEAD"), "git_dirty": bool(_git("status", "--porcelain", "--", ".")),
           **bundle, "split_id": cn.split_id if cn is not None else None,
           "split_roles": cn.split_roles() if cn is not None else None, "config_hash": cfg["_hash"],
           "models": [{"name": m["name"], "role": m.get("role", "primary"), "revision": m.get("revision"),
                       "quantization": m.get("quantization"), "backend": m.get("backend", "vllm"),
                       "vllm_version": m.get("vllm_version"), "server_fp": server_fps.get(m["name"])}
                      for m in cfg["models"]],
           "gpu": _gpu_name(), "prompt_version": PROMPT_VERSION, "jev_question_version": jev.JEV_QUESTION_VERSION,
           "jev_pinned_model": jev.PINNED_MODEL, "seed": cfg.get("seed", 0),
           "sampling": {"n": cfg["n_samples"], "temperature": cfg["temperature"]},
           "started": int(started), "finished": int(time.time())}
    path = Path(cfg["out"]).parent / "manifest.json"
    _write_json(path, man)
    return man


def _check_roles(models):
    for m in models:
        if m.get("role", "primary") not in MODEL_ROLES:
            raise ValueError(f"model {m['name']}: role must be one of {MODEL_ROLES}")


# ---------------------------------------------------------------- bước 2
def run(cfg):
    cn = Canon(cfg) if is_canonical(cfg) else None
    recs = load_evidence(cfg)
    if cn is not None:
        wanted = {vc.case_id for vc, _ in cn.selected()}
    else:
        wanted = {c.case_id for c in select_cases(cfg)} if Path(cfg["data_root"]).exists() else None
    if wanted:
        recs = [r for r in recs if r["vc"].case_id in wanted]
    print(f"{len(recs)} cases with evidence")

    _check_roles(cfg["models"])
    started = time.time()
    store, store_fp = None, "-"
    if any(m != "none" for m in cfg["retrieval"]):
        entries = _store_entries(cfg, recs, cn)
        emb_name = cfg.get("embedder", "BAAI/bge-small-en-v1.5")
        store = CaseStore(entries, Embedder(emb_name))
        if emb_name != "tfidf" and store.emb.kind != "st":
            raise RuntimeError(f"embedder {emb_name!r} is unavailable (fell back to {store.emb.kind}); "
                               "install sentence-transformers or set `embedder: tfidf` explicitly")
        blob = "\n".join([f"embedder:{store.emb.kind}:{emb_name}"] + sorted(f"{e['case_id']}:{e['evidence_fp']}" for e in entries))
        store_fp = hashlib.sha256(blob.encode()).hexdigest()[:16]
        print(f"case store: {len(entries)} entries, embedder={store.emb.kind}")
    members: dict[str, set] = {}
    if cn is not None:
        for u, g in cn.group.items():
            members.setdefault(g, set()).add(u)

    out_path = Path(cfg["out"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out_path.exists():
        with open(out_path, encoding="utf-8") as fh:
            done = {json.loads(l)["key"] for l in fh if l.strip()}
    cache = Cache(cfg.get("cache", "results/llm_cache.sqlite"))
    server_fps = {}

    with open(out_path, "a", encoding="utf-8", newline="\n") as fout:
        for m in cfg["models"]:
            llm = LLM(m["name"], m.get("base_url", "http://localhost:8000/v1"), m.get("backend", "vllm"),
                      n=cfg["n_samples"], temperature=cfg["temperature"], seed=cfg.get("seed", 0), cache=cache,
                      max_tokens=m.get("max_tokens", 400), revision=m.get("revision"),
                      chat_template_kwargs=m.get("chat_template_kwargs"), logprobs=m.get("logprobs", False))
            server_fps[m["name"]] = llm.server_fingerprint(m.get("launch_args"), m.get("quantization"))
            role, rev = m.get("role", "primary"), m.get("revision")
            for r in recs:
                vc, tr, cands = r["vc"], r["truth"], r["candidates"]
                grp = frozenset(members.get(cn.group.get(vc.case_id), ())) if cn is not None else frozenset()
                for cond, ev in r["conditions"].items():
                    cells = [("none", "-")] + [(meth, mode) for meth in cfg["retrieval"] if meth != "none"
                                               for mode in cfg["store_modes"]]
                    for meth, mode in cells:
                        if meth == "none" and "none" not in cfg["retrieval"]:
                            continue
                        # the evidence (and store) fingerprints are part of the key: rows produced from
                        # stale evidence are not counted as done
                        key = (f"{m['name']}|{rev}|{PROMPT_VERSION}|{vc.case_id}|{cond}|{meth}|{mode}|{r['evidence_fp']}|"
                               f"{store_fp if meth != 'none' else '-'}")
                        if key in done:
                            continue
                        hits = (store.search(ev["text"], vc, meth, mode, cfg["top_k"], exclude_ids=exclusions(store, vc, tr, mode, grp))
                                if meth != "none" else [])
                        msgs = build_messages(vc, cands, ev["text"], format_hits(hits))
                        res = llm.ask(msgs, cands)
                        agg = aggregate(res["samples"])
                        sc = score.correctness(agg["ranking"], tr, len(cands))
                        row = {
                            "key": key, "cfg": cfg["_hash"], "model": m["name"], "model_role": role, "model_revision": rev,
                            "prompt_version": PROMPT_VERSION, "server_fp": llm.server_fp, "backend": llm.backend,
                            "sampling": {"n": llm.n, "temperature": llm.temperature, "seed": llm.seed},
                            "case_id": vc.case_id,
                            "system": vc.system, "dataset": vc.dataset, "fault": tr.fault, "truth": tr.root_service,
                            "truth_ids": list(score.truth_ids(tr)), "label_granularity": tr.granularity,
                            "n_candidates": len(cands), "condition": cond, "retrieval": meth, "store_mode": mode,
                            "rank": sc["rank"], "correct": sc["correct_at_1"], "correct_at_3": sc["correct_at_3"],
                            "parse_failed": sc["parse_failed"], "set_scored": sc["set_scored"], **agg,
                            "features": ev["features"],
                            "hits": [{"case_id": h["case_id"], "root": h["root"], "dense_sim": h["dense_sim"]} for h in hits],
                            "hit_has_truth": any(h["root"] in score.truth_ids(tr) for h in hits),
                            "prompt_tokens": res["prompt_tokens"], "completion_tokens": res["completion_tokens"],
                            "latency_s": res["latency_s"], "cached": res["cached"], "ts": int(time.time()),
                            "incident_uid": vc.case_id if cn is not None else None, "pair_id": vc.case_id,
                            "split_id": cn.split_id if cn is not None else None,
                            "split_role": cn.roles.get(vc.case_id) if cn is not None else None,
                            "oracle_store": mode == "no_precedent",
                            "evidence_fp": r["evidence_fp"], "store_fp": store_fp if meth != "none" else None,
                        }
                        fout.write(json.dumps(row) + "\n")
                        fout.flush()
                        done.add(key)
            print(f"model {m['name']} done")
    write_manifest(cfg, cn, server_fps, started)


if __name__ == "__main__":
    step, path = sys.argv[1], sys.argv[2]
    {"prepare": prepare, "run": run}[step](load_cfg(path))
