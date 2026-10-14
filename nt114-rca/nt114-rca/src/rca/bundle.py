"""Transfer bundle: export the validated data home parts and verify them after the move.

  python -m rca.prep export --bundle nt114-data-v1 [--parts visible,eval_only,splits,reports,manifests,provenance]
  python -m rca.prep verify-bundle <dir> [--deep]

`export/<name>-<YYYYMMDD>-<hash8>/parts/` mirrors the data-home layout (`canonical/v1/...`,
`splits/`, `reports/`, `manifests/`, `provenance/`), so every command runs unchanged with
`--data-home <bundle>/parts`. Files are hard-linked when possible, else copied; sources are never
modified. `configs/` holds copies of the repository's `configs/*.yaml` the data was built and is
read with (build config, aliases, evidence options, primary-evaluation exclusions). `MANIFEST.sha256` lists every file in GNU `sha256sum` format; `hash8` starts the sha256
of the parts manifest. `--deep` also recomputes every telemetry `content_sha256` and every
`blind_nonroot` target and compares them with `bundle.json`.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .schema import MODALITIES, SCHEMA_VERSION
from .store import CanonicalStore, read_json, sha256_file, table_content_sha256, write_json_atomic

EXIT_OK, EXIT_USAGE, EXIT_INTEGRITY, EXIT_PRECONDITION = 0, 2, 4, 5
RCA_ROOT = Path(__file__).resolve().parents[2]
PARTS = ("visible", "eval_only", "splits", "reports", "manifests", "provenance", "raw")
NONCOMMERCIAL = ("NC", "non-commercial", "noncommercial", "controlled", "request")


def _part_files(part: str, P: dict, data_home: Path) -> list[Path]:
    canon = P["canonical"]
    if part in ("visible", "eval_only"):
        out = []
        for ds in sorted(p for p in canon.iterdir() if (p / "_build.json").is_file()) if canon.is_dir() else []:
            if part == "visible":
                out.append(ds / "_build.json")
            out += sorted(p for p in (ds / part).rglob("*") if p.is_file() and not p.name.endswith(".part"))
        return out
    root = {"splits": P["splits"], "reports": P["reports"], "raw": P["raw"],
            "manifests": data_home / "manifests", "provenance": data_home / "provenance"}[part]
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob("*") if p.is_file() and not p.name.endswith(".part")
                  and not any(s.startswith(".") and s.endswith(".part") for s in p.relative_to(root).parts))


def _place(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def _git_commit() -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(RCA_ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=20)
        return r.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _git_dirty() -> bool | None:
    """True when RCA_ROOT has uncommitted or untracked (not ignored) files, so `git_commit` does not
    fully describe the code that exported the bundle."""
    try:
        r = subprocess.run(["git", "-C", str(RCA_ROOT), "status", "--porcelain", "--", "."],
                           capture_output=True, text=True, timeout=60)
        return bool(r.stdout.strip()) if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _git_tracked() -> bool:
    try:
        r = subprocess.run(["git", "-C", str(RCA_ROOT), "ls-files", "--error-unmatch", "src/rca/prep.py"],
                           capture_output=True, text=True, timeout=20)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _licences(data_home: Path, source_ids: set[str]) -> dict:
    cat = data_home / "manifests" / "dataset_catalog.json"
    out = {}
    if cat.is_file():
        for s in read_json(cat).get("sources", []):
            sid = s.get("id") or s.get("source_id")
            if sid in source_ids:
                lic = s.get("license") or "unknown"       # a string, or {subset: licence} (AgenticOpsEval)
                text = " ".join(map(str, lic.values())) if isinstance(lic, dict) else lic
                out[sid] = {"license": lic,
                            "note": "private transfer only" if any(k.lower() in text.lower() for k in NONCOMMERCIAL) or text == "unknown" else None}
    for sid in source_ids - set(out):
        out[sid] = {"license": "unknown", "note": "private transfer only"}
    return out


def fingerprints(data_home: Path) -> dict:
    """{dataset: {uid: {modality: content_sha256}}} and {dataset: {uid: blind_nonroot target}}, recomputed from files."""
    from .splits import condition_matrix
    store = CanonicalStore(data_home)
    hashes, targets = {}, {}
    for ds in store.datasets():
        hashes[ds] = {}
        for inc in store.incidents(ds, states=None):
            h = {}
            for m in MODALITIES:
                mi = inc["telemetry"][m]
                if mi["status"] == "present":
                    import pyarrow.parquet as pq
                    h[m] = table_content_sha256(pq.read_table(data_home / mi["path"]), m)
            hashes[ds][inc["incident_uid"]] = h
        if (store.root / ds / "eval_only" / "labels.jsonl").is_file():
            targets[ds] = {u: r["nonroot_target"] for u, r in condition_matrix(store, ds)["incidents"].items()}
    return {"content_sha256": hashes, "blind_nonroot_targets": targets}


def export_cmd(name: str, parts: list[str], include_raw: bool, cfg: dict, data_home: Path) -> int:
    from .prep import package_versions, paths
    P = paths(cfg, data_home)
    parts = [p for p in parts if p]
    if include_raw and "raw" not in parts:
        parts.append("raw")
    bad = [p for p in parts if p not in PARTS]
    if bad:
        print(f"unknown parts {bad}; choose from {PARTS}")
        return EXIT_USAGE
    store = CanonicalStore(data_home)
    if not store.datasets():
        print("no canonical builds")
        return EXIT_PRECONDITION
    files = {}
    for part in parts:
        for f in _part_files(part, P, data_home):
            rel = f.resolve().relative_to(data_home.resolve()).as_posix()
            files[f"parts/{rel}"] = f
    for f in sorted((RCA_ROOT / "configs").glob("*.yaml")):     # editable sources: copied, never hard-linked
        files[f"configs/{f.name}"] = f
    tmp = P["export"] / f".{name}.part"
    if tmp.exists():
        shutil.rmtree(tmp)
    lines = []
    for rel, src in sorted(files.items()):
        if rel.startswith("configs/"):
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, tmp / rel)
        else:
            _place(src, tmp / rel)
        lines.append(f"{sha256_file(tmp / rel)}  {rel}")
    parts_manifest = "".join(l + "\n" for l in lines)
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    bundle_id = f"{name}-{day}-{hashlib.sha256(parts_manifest.encode()).hexdigest()[:8]}"
    dest = P["export"] / bundle_id
    if dest.exists():
        shutil.rmtree(tmp)
        print(f"{bundle_id}: exists (same content); not rewritten")
        return EXIT_OK
    builds = {ds: store.build(ds) for ds in store.datasets()}
    sources = {b.get("source_id") for b in builds.values()} | {i["source_id"] for ds in builds for i in store.incidents(ds, states=None)}
    lock = RCA_ROOT / "requirements-lock.txt"
    split_root = P["splits"]
    meta = {
        "bundle_id": bundle_id, "name": name, "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema_version": SCHEMA_VERSION, "parts": parts, "files": len(lines),
        "bytes": sum(f.stat().st_size for f in files.values()),
        "datasets": {ds: {"build_id": b["build_id"], "dataset_digest": b["dataset_digest"], "adapter": b["adapter"],
                          "config_hash": b["config_hash"], "states": b["counts"]["states"]} for ds, b in builds.items()},
        "splits": sorted(p.name for p in split_root.iterdir() if (p / "split.json").is_file()) if split_root.is_dir() else [],
        "licences": _licences(data_home, {s for s in sources if s}),
        "code": {"git_commit": _git_commit(), "rca_root_tracked": _git_tracked(), "git_dirty": _git_dirty(),
                 "lock_sha256": sha256_file(lock) if lock.is_file() else None, "packages": package_versions()},
        **fingerprints(data_home),
    }
    write_json_atomic(tmp / "bundle.json", meta, indent=1)
    lines.append(f"{sha256_file(tmp / 'bundle.json')}  bundle.json")
    (tmp / "MANIFEST.sha256").write_bytes("".join(l + "\n" for l in sorted(lines, key=lambda l: l.split('  ', 1)[1])).encode())
    tmp.rename(dest)
    print(f"{bundle_id}: {len(lines)} files, {meta['bytes'] / 1e9:.2f} GB")
    return EXIT_OK


def verify_bundle(d: Path, deep: bool = False) -> list[str]:
    d = Path(d)
    man = d / "MANIFEST.sha256"
    if not man.is_file():
        return ["MANIFEST.sha256 missing"]
    errs, listed = [], set()
    for line in man.read_text(encoding="utf-8").splitlines():
        h, rel = line.split("  ", 1)
        listed.add(rel)
        p = d / rel
        if not p.is_file():
            errs.append(f"MISSING {rel}")
        elif sha256_file(p) != h:
            errs.append(f"MISMATCH {rel}")
    for p in d.rglob("*"):
        if p.is_file() and p.name != "MANIFEST.sha256":
            rel = p.relative_to(d).as_posix()
            if rel not in listed:
                errs.append(f"EXTRA {rel}")
    if deep and not errs:
        meta = read_json(d / "bundle.json")
        got = fingerprints(d / "parts")
        for key in ("content_sha256", "blind_nonroot_targets"):
            for ds, want in meta[key].items():
                have = got[key].get(ds, {})
                diff = [u for u in want if want[u] != have.get(u)]
                errs += [f"{key.upper()} {ds} {u}" for u in diff[:20]]
                if len(diff) > 20:
                    errs.append(f"{key.upper()} {ds}: {len(diff)} differences")
    return errs


def verify_cmd(d: Path, deep: bool = False) -> int:
    errs = verify_bundle(d, deep)
    for e in errs[:50]:
        print(e)
    print(f"{d.name}: {'OK' if not errs else f'{len(errs)} problems'}{' (deep)' if deep else ''}")
    return EXIT_INTEGRITY if errs else EXIT_OK
