"""Safe extraction of archives that cannot be streamed (tar.gz with random access needs).

Each member is checked before anything is written: absolute paths, drive letters, `..`, links,
devices, Windows-reserved names and characters, path length, member size and the cumulative
decompression ratio. Members matching skip patterns (macOS AppleDouble, .DS_Store) are counted
and skipped. Files are written to `<dest>.part` and moved into place; a receipt
`.extract.json` records size and sha256 per member so a rerun skips verified members.
"""
from __future__ import annotations

import fnmatch
import hashlib
import os
import re
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

from .store import read_json, write_json_atomic

WIN_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
WIN_BAD_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')
MAX_PATH = 240


class UnsafeArchive(Exception):
    """Raised when a member violates a rule; the command exits with code 4."""


def check_name(name: str, dest: Path) -> PurePosixPath:
    if not name or name.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", name):
        raise UnsafeArchive(f"absolute path: {name!r}")
    p = PurePosixPath(name.replace("\\", "/"))
    if any(part == ".." for part in p.parts):
        raise UnsafeArchive(f"parent reference: {name!r}")
    for part in p.parts:
        if WIN_BAD_CHARS.search(part):
            raise UnsafeArchive(f"invalid character: {name!r}")
        if part.split(".")[0].upper() in WIN_RESERVED:
            raise UnsafeArchive(f"reserved name: {name!r}")
        if part.endswith((" ", ".")) and part not in (".",):
            raise UnsafeArchive(f"trailing dot/space: {name!r}")
    if len(str(dest / p)) > MAX_PATH:
        raise UnsafeArchive(f"path too long ({len(str(dest / p))}): {name!r}")
    return p


def _skipped(name: str, patterns) -> bool:
    return any(fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(PurePosixPath(name).name, pat) for pat in patterns)


def _copy(src, dst: Path) -> tuple[int, str]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".part")
    h, n = hashlib.sha256(), 0
    with open(tmp, "wb") as f:
        while b := src.read(1 << 20):
            h.update(b)
            n += len(b)
            f.write(b)
    os.replace(tmp, dst)
    return n, h.hexdigest()


def extract(archive: Path, dest: Path, cfg: dict | None = None) -> dict:
    """Extract `archive` (tar, tar.gz or zip) into `dest`. Returns the receipt."""
    cfg = cfg or {}
    max_member = int(cfg.get("max_member_bytes", 20_000_000_000))
    max_ratio = float(cfg.get("max_total_ratio", 200))
    skip = cfg.get("skip_patterns", ["__MACOSX/*", "*/._*", "._*", "*.DS_Store"])
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    rpath = dest / ".extract.json"
    receipt = read_json(rpath) if rpath.exists() else {"archive": archive.name, "members": {}, "skipped": []}
    compressed = archive.stat().st_size
    total = 0
    skipped: set[str] = set(receipt.get("skipped", []))

    def accept(name: str, size: int):
        nonlocal total
        p = check_name(name, dest)
        if size > max_member:
            raise UnsafeArchive(f"member too large ({size}): {name!r}")
        total += size
        if total / max(compressed, 1) > max_ratio:
            raise UnsafeArchive(f"decompression ratio above {max_ratio}: {name!r}")
        return p

    def done(rel: str, size: int) -> bool:
        e = receipt["members"].get(rel)
        return bool(e and e["size"] == size and (dest / rel).is_file() and (dest / rel).stat().st_size == size)

    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                if _skipped(info.filename, skip):
                    skipped.add(info.filename)
                    continue
                mode = (info.external_attr >> 16) & 0o170000
                if mode in (0o120000,):
                    raise UnsafeArchive(f"symlink: {info.filename!r}")
                if info.is_dir():
                    check_name(info.filename.rstrip("/"), dest)
                    continue
                p = accept(info.filename, info.file_size)
                rel = p.as_posix()
                if done(rel, info.file_size):
                    continue
                with z.open(info) as src:
                    n, sha = _copy(src, dest / p)
                receipt["members"][rel] = {"size": n, "sha256": sha}
                write_json_atomic(rpath, {**receipt, "skipped": sorted(skipped)})
    else:
        with tarfile.open(archive, mode="r:*") as t:
            for m in t:
                if _skipped(m.name, skip):
                    skipped.add(m.name)
                    continue
                if m.issym() or m.islnk():
                    raise UnsafeArchive(f"link: {m.name!r}")
                if m.ischr() or m.isblk() or m.isfifo() or m.isdev():
                    raise UnsafeArchive(f"device or fifo: {m.name!r}")
                if m.isdir():
                    check_name(m.name.rstrip("/"), dest)
                    continue
                if not m.isfile():
                    raise UnsafeArchive(f"unsupported member type: {m.name!r}")
                p = accept(m.name, m.size)
                filtered = tarfile.data_filter(m, str(dest))  # stdlib "data" filter as a second check
                if filtered is None:
                    raise UnsafeArchive(f"rejected by data filter: {m.name!r}")
                rel = p.as_posix()
                if done(rel, m.size):
                    continue
                src = t.extractfile(m)
                n, sha = _copy(src, dest / p)
                receipt["members"][rel] = {"size": n, "sha256": sha}
                write_json_atomic(rpath, {**receipt, "skipped": sorted(skipped)})
    receipt["skipped"] = sorted(skipped)
    receipt["complete"] = True
    write_json_atomic(rpath, receipt)
    return receipt
