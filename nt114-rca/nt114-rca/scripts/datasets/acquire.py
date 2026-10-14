"""Raw dataset acquisition and verification for nt114-rca.

Stdlib only, single file (``python -I`` drops the script directory from sys.path).
Never imports, extracts or executes downloaded content.

Layout (relative to the project root, two levels above this file):
  scripts/datasets/sources.json          registry (pinned revisions)
  data/manifests/filelists/<id>.json     pinned per-file list with publisher anchors
  data/manifests/download_manifest.jsonl one line per artefact attempt
  data/raw/<id>/<version>/...            raw files (git-ignored)
  data/.state/<id>.json                  per-source state (git-ignored)
  data/provenance/<id>.json              provenance records
"""

import argparse
import concurrent.futures
import datetime
import hashlib
import http.client
import json
import os
import random
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UA = "nt114-rca-acquire/1 (research dataset mirror; contact via project owner)"
KINDS = {"zenodo-record", "huggingface-dataset", "github-git", "gitlab-raw", "google-drive-files"}
LEVELS = ("publisher-hash", "publisher-size", "host-reported", "local-only")
LFS_PREFIX = b"version https://git-lfs.github.com/spec/v1"
CHUNK = 1 << 20
GIB = 1 << 30


class DriftError(Exception):
    pass


# ---------------------------------------------------------------- paths/io

def paths(root=None):
    root = root or ROOT
    d = os.path.join(root, "data")
    return {
        "root": root,
        "registry": os.path.join(root, "scripts", "datasets", "sources.json"),
        "raw": os.path.join(d, "raw"),
        "state": os.path.join(d, ".state"),
        "manifests": os.path.join(d, "manifests"),
        "filelists": os.path.join(d, "manifests", "filelists"),
        "provenance": os.path.join(d, "provenance"),
        "download_log": os.path.join(d, "manifests", "download_manifest.jsonl"),
    }


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


_log_lock = threading.Lock()


def log_attempt(P, rec):
    os.makedirs(os.path.dirname(P["download_log"]), exist_ok=True)
    rec = dict(rec, at=now())
    line = json.dumps(rec, ensure_ascii=False, sort_keys=True)
    with _log_lock, open(P["download_log"], "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")


def safe_join(base, rel):
    """Join a registry-relative path under base; reject absolute and parent paths."""
    rel = rel.replace("\\", "/")
    parts = rel.split("/")
    if rel.startswith("/") or ":" in parts[0] or any(p in ("", ".", "..") for p in parts):
        raise ValueError("unsafe relative path: %r" % rel)
    return os.path.join(base, *parts)


# ---------------------------------------------------------------- registry

def load_registry(P):
    reg = read_json(P["registry"])
    if not reg or "sources" not in reg:
        raise SystemExit("registry missing: %s" % P["registry"])
    seen = set()
    for s in reg["sources"]:
        sid = s.get("id")
        if not sid or sid in seen:
            raise SystemExit("registry: missing or duplicate id %r" % sid)
        seen.add(sid)
        if s.get("kind") not in KINDS:
            raise SystemExit("registry: %s has unknown kind %r" % (sid, s.get("kind")))
        pin = {"zenodo-record": "record", "huggingface-dataset": "revision", "github-git": "revision",
               "gitlab-raw": "revision", "google-drive-files": "drive_folder"}[s["kind"]]
        if not s.get(pin):
            raise SystemExit("registry: %s is not pinned (%s missing)" % (sid, pin))
        if s["kind"] in ("huggingface-dataset", "github-git", "gitlab-raw") and len(s[pin]) != 40:
            raise SystemExit("registry: %s revision must be a full 40-hex commit" % sid)
    return reg


def get_source(reg, sid):
    for s in reg["sources"]:
        if s["id"] == sid:
            return s
    raise SystemExit("unknown source %r" % sid)


def version_dir(s):
    k = s["kind"]
    if k == "zenodo-record":
        return "zenodo-%s" % s["record"]
    if k == "huggingface-dataset":
        return "hf-%s" % s["revision"][:12]
    if k == "github-git":
        return "git-%s" % s["revision"][:12]
    if k == "gitlab-raw":
        return "gitlab-%s" % s["revision"][:12]
    return "drive-%s" % s["retrieved_tag"]


def raw_dir(P, s):
    return os.path.join(P["raw"], s["id"], version_dir(s))


def state_path(P, sid):
    return os.path.join(P["state"], sid + ".json")


def load_state(P, sid):
    return read_json(state_path(P, sid), {"id": sid, "state": "PENDING:not-started", "history": []})


def save_state(P, sid, st, state=None, reason=None, next_action=None):
    if state:
        st["history"] = (st.get("history") or []) + [{"at": now(), "state": state, "reason": reason}]
        st["state"], st["reason"], st["next_action"] = state, reason, next_action
    write_json(state_path(P, sid), st)


# ---------------------------------------------------------------- http

def http_get(url, headers=None, timeout=60, data=None):
    req = urllib.request.Request(url, headers=dict({"User-Agent": UA}, **(headers or {})), data=data)
    return urllib.request.urlopen(req, timeout=timeout)


def http_json(url, retries=6, base_delay=2.0):
    return json.loads(http_bytes(url, retries=retries, base_delay=base_delay).decode("utf-8"))


def http_bytes(url, retries=6, base_delay=2.0, limit=None):
    err = None
    for attempt in range(retries):
        try:
            with http_get(url) as r:
                return r.read(limit) if limit else r.read()
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (400, 401, 403, 404, 410):
                raise
            backoff(attempt, base_delay, e)
        except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
            err = e
            backoff(attempt, base_delay, None)
    raise err


def backoff(attempt, base, http_err, cap=300.0):
    delay = min(cap, base * (2 ** attempt)) + random.uniform(0, 1)
    if http_err is not None and http_err.headers.get("Retry-After", "").isdigit():
        delay = max(delay, float(http_err.headers["Retry-After"]))
    time.sleep(delay)


def download(url, dest, expected_size=None, retries=6, base_delay=2.0, timeout=60, part=None, offset=None):
    """Resumable download into dest + '.part'. Returns bytes transferred in this call.

    The .part file is left in place on failure so the next call resumes. The caller
    renames it only after its own integrity check passes. With ``offset`` the call
    fetches the byte range [offset, offset + expected_size) into ``part``.
    """
    part = part or dest + ".part"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    transferred = 0
    err = None
    for attempt in range(retries):
        have = os.path.getsize(part) if os.path.exists(part) else 0
        if expected_size is not None and have == expected_size:
            return transferred
        if expected_size is not None and have > expected_size:
            os.remove(part)
            have = 0
        if offset is not None:
            headers = {"Range": "bytes=%d-%d" % (offset + have, offset + expected_size - 1)}
        else:
            headers = {"Range": "bytes=%d-" % have} if have else {}
        try:
            with http_get(url, headers=headers, timeout=timeout) as r:
                if offset is not None and r.status != 206:
                    raise IOError("server ignored a segment Range request")
                if have and r.status != 206:
                    have = 0  # server ignored Range: restart
                left = expected_size - have if expected_size is not None else None
                with open(part, "ab" if have else "wb") as f:
                    while left is None or left > 0:
                        b = r.read(CHUNK if left is None else min(CHUNK, left))
                        if not b:
                            break
                        if left is not None:
                            left -= len(b)
                        f.write(b)
                        transferred += len(b)
            size = os.path.getsize(part)
            if expected_size is None or size == expected_size:
                return transferred
            err = IOError("short read: %d of %d bytes" % (size, expected_size))
            backoff(attempt, base_delay, None)
        except urllib.error.HTTPError as e:
            err = e
            if e.code == 416 and expected_size is not None and os.path.getsize(part) == expected_size:
                return transferred
            if e.code in (400, 401, 403, 404, 410):
                raise
            backoff(attempt, base_delay, e)
        except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
            err = e
            backoff(attempt, base_delay, None)
    raise err


def download_segmented(url, dest, size, segments, retries=6, base_delay=2.0):
    """Fetch one large file as parallel byte ranges, then join them into dest + '.part'.

    Each range resumes from its own ``.part.segNN`` file. An existing single-stream
    ``.part`` becomes segment 0 so earlier progress is kept.
    """
    part = dest + ".part"
    if os.path.exists(part) and os.path.getsize(part) == size:
        return 0
    step = -(-size // segments)
    ranges = [(i, i * step, min(step, size - i * step)) for i in range(segments) if i * step < size]
    seg0 = "%s.seg%02d" % (part, 0)
    if os.path.exists(part) and not os.path.exists(seg0):
        with open(part, "r+b") as f:
            f.truncate(min(os.path.getsize(part), ranges[0][2]))
        os.replace(part, seg0)

    def one(r):
        i, off, length = r
        return download(url, dest, length, retries=retries, base_delay=base_delay,
                        part="%s.seg%02d" % (part, i), offset=off)

    with concurrent.futures.ThreadPoolExecutor(len(ranges)) as ex:
        transferred = sum(ex.map(one, ranges))
    with open(part + ".join", "wb") as out:
        for i, _, _ in ranges:
            with open("%s.seg%02d" % (part, i), "rb") as f:
                shutil.copyfileobj(f, out, CHUNK)
    os.replace(part + ".join", part)
    for i, _, _ in ranges:
        os.remove("%s.seg%02d" % (part, i))
    return transferred


# ---------------------------------------------------------------- hashing

def file_hashes(path, algos=("sha256",)):
    hs = {a: (hashlib.sha1() if a == "git-sha1" else hashlib.new(a)) for a in algos}
    if "git-sha1" in hs:
        hs["git-sha1"].update(b"blob %d\0" % os.path.getsize(path))
    with open(path, "rb") as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            for h in hs.values():
                h.update(b)
    return {a: h.hexdigest() for a, h in hs.items()}


def is_lfs_pointer(path):
    if os.path.getsize(path) > 1024:
        return False
    with open(path, "rb") as f:
        return f.read(len(LFS_PREFIX)) == LFS_PREFIX


def parse_lfs_pointer(blob):
    if not blob.startswith(LFS_PREFIX):
        return None
    out = {}
    for line in blob.decode("ascii", "replace").splitlines():
        k, _, v = line.partition(" ")
        if k == "oid" and v.startswith("sha256:"):
            out["sha256"] = v[7:]
        elif k == "size":
            out["size"] = int(v)
    return out if "sha256" in out and "size" in out else None


# ---------------------------------------------------------------- resolvers (host metadata -> file list)

def resolve_zenodo(s):
    rec = http_json("https://zenodo.org/api/records/%s" % s["record"])
    files = []
    for f in rec.get("files", []):
        algo, _, val = f["checksum"].partition(":")
        files.append({"path": f["key"], "size": f["size"],
                      "url": "https://zenodo.org/api/records/%s/files/%s/content"
                             % (s["record"], urllib.parse.quote(f["key"])),
                      "anchor": {"algo": algo, "value": val, "source": "zenodo record checksum"},
                      "integrity_level": "publisher-hash"})
    meta = {"license": (rec.get("metadata", {}).get("license") or {}).get("id"),
            "doi": rec.get("doi"), "version": rec.get("metadata", {}).get("version"),
            "updated": rec.get("updated"), "title": rec.get("metadata", {}).get("title")}
    return files, meta


def resolve_hf(s):
    d = http_json("https://huggingface.co/api/datasets/%s/revision/%s?blobs=true" % (s["repo"], s["revision"]))
    if d.get("sha") != s["revision"]:
        raise DriftError("HF returned sha %s for pinned %s" % (d.get("sha"), s["revision"]))
    files = []
    for x in d["siblings"]:
        url = "https://huggingface.co/datasets/%s/resolve/%s/%s" % (
            s["repo"], s["revision"], urllib.parse.quote(x["rfilename"]))
        if x.get("lfs"):
            anchor = {"algo": "sha256", "value": x["lfs"]["sha256"], "source": "HF LFS oid"}
        else:
            anchor = {"algo": "git-sha1", "value": x["blobId"], "source": "HF git blob id"}
        files.append({"path": x["rfilename"], "size": x["size"], "url": url, "anchor": anchor,
                      "integrity_level": "publisher-hash"})
    meta = {"license": (d.get("cardData") or {}).get("license"), "last_modified": d.get("lastModified")}
    return files, meta


def gitlab_tree(api, rev):
    out, page = [], 1
    while True:
        q = "%s/repository/tree?ref=%s&recursive=true&per_page=100&page=%d" % (api, rev, page)
        batch = http_json(q)
        out.extend(x for x in batch if x["type"] == "blob")
        if len(batch) < 100:
            return out
        page += 1


def resolve_gitlab(s):
    api = "%s/api/v4/projects/%s" % (s["host"], s["project_id"])
    base = "%s/%s/-/raw/%s/" % (s["host"], s["project_path"], s["revision"])
    include = s.get("include")
    files = []
    tree = [b for b in gitlab_tree(api, s["revision"])
            if not include or any(b["path"] == p or b["path"].startswith(p.rstrip("/") + "/") for p in include)]

    def one(b):
        blob = http_bytes("%s/repository/blobs/%s/raw" % (api, b["id"]), limit=2048)
        ptr = parse_lfs_pointer(blob)
        url = base + urllib.parse.quote(b["path"])
        if ptr:
            return {"path": b["path"], "size": ptr["size"], "url": url, "git_blob": b["id"],
                    "anchor": {"algo": "sha256", "value": ptr["sha256"], "source": "LFS pointer committed at revision"},
                    "integrity_level": "publisher-hash"}
        # Non-LFS blob: the git blob id is the content hash; size comes from the download.
        return {"path": b["path"], "size": None, "url": url, "git_blob": b["id"],
                "anchor": {"algo": "git-sha1", "value": b["id"], "source": "git blob id at revision"},
                "integrity_level": "publisher-hash"}

    with concurrent.futures.ThreadPoolExecutor(4) as ex:
        files = list(ex.map(one, tree))
    files.sort(key=lambda f: f["path"])
    return files, {"tree_blobs": len(tree)}


def resolve_github(s):
    t = http_json("https://api.github.com/repos/%s/git/trees/%s?recursive=1" % (s["repo"], s["revision"]))
    if t.get("truncated"):
        raise DriftError("GitHub tree listing truncated for %s" % s["repo"])
    files = [{"path": x["path"], "size": x["size"], "url": None,
              "anchor": {"algo": "git-sha1", "value": x["sha"], "source": "git blob id at revision"},
              "integrity_level": "publisher-hash"}
             for x in t["tree"] if x["type"] == "blob"]
    return files, {"tree_entries": len(t["tree"]), "submodules": sum(1 for x in t["tree"] if x["type"] == "commit")}


def resolve_drive(s):
    files = []
    for name, fid, size in s["files"]:
        files.append({"path": name, "drive_id": fid, "size": size if isinstance(size, int) else None,
                      "size_hint": None if isinstance(size, int) else size,
                      "url": None, "anchor": {"algo": "none", "value": None, "source": "no publisher checksum"},
                      "integrity_level": "local-only"})
    return files, {}


RESOLVERS = {"zenodo-record": resolve_zenodo, "huggingface-dataset": resolve_hf, "gitlab-raw": resolve_gitlab,
             "github-git": resolve_github, "google-drive-files": resolve_drive}


def filelist_path(P, sid):
    return os.path.join(P["filelists"], sid + ".json")


def comparable(files):
    return sorted((f["path"], f.get("size"), f["anchor"]["algo"], f["anchor"]["value"]) for f in files)


def cmd_check_metadata(P, reg, sid, pin_if_missing=True):
    s = get_source(reg, sid)
    files, meta = RESOLVERS[s["kind"]](s)
    fl = read_json(filelist_path(P, sid))
    if fl is None:
        if not pin_if_missing:
            return 3, {"status": "unpinned"}
        write_json(filelist_path(P, sid), {"id": sid, "pinned_at": now(), "kind": s["kind"],
                                           "host_meta": meta, "files": files})
        return 0, {"status": "pinned", "files": len(files), "bytes": sum(f["size"] or 0 for f in files)}
    old, new = comparable(fl["files"]), comparable(files)
    if old != new:
        a, b = set(old), set(new)
        return 3, {"status": "drift", "only_pinned": sorted(a - b)[:20], "only_host": sorted(b - a)[:20]}
    return 0, {"status": "match", "files": len(files), "host_meta": meta}


# ---------------------------------------------------------------- budget

def dir_bytes(path):
    total = 0
    for dp, _, fns in os.walk(path):
        for fn in fns:
            try:
                total += os.path.getsize(os.path.join(dp, fn))
            except OSError:
                pass
    return total


def budget_check(P, need, budget_gb, reserve_gb, free_bytes=None):
    used = dir_bytes(P["raw"]) if os.path.isdir(P["raw"]) else 0
    if free_bytes is None:
        os.makedirs(P["root"], exist_ok=True)
        free_bytes = shutil.disk_usage(P["root"]).free
    budget, reserve = int(budget_gb * GIB), int(reserve_gb * GIB)
    over_budget = used + need - budget
    over_reserve = reserve - (free_bytes - need)
    shortfall = max(over_budget, over_reserve, 0)
    return {"need": need, "used": used, "budget": budget, "free": free_bytes, "reserve": reserve,
            "ok": shortfall == 0, "shortfall_bytes": shortfall}


def need_bytes(files, dest):
    need = 0
    for f in files:
        size = f.get("size")
        if size is None and f.get("size_hint"):
            size = hint_bytes(f["size_hint"])
        if size is None:
            continue
        p = safe_join(dest, f["path"])
        have = os.path.getsize(p) if os.path.exists(p) else (
            os.path.getsize(p + ".part") if os.path.exists(p + ".part") else 0)
        need += max(size - have, 0)
    return need


def hint_bytes(hint):
    """Round a Drive-style size such as '2.6G (Drive-rounded)' up to whole GiB."""
    num = hint.split("G")[0]
    return int((float(num) + 1) // 1 * GIB) if num.replace(".", "").isdigit() else None


# ---------------------------------------------------------------- fetch

def check_file(path, f):
    """Return (ok, record) comparing a local file with its pinned anchor."""
    algo = f["anchor"]["algo"]
    algos = ["sha256"] + ([algo] if algo in ("md5", "git-sha1") else [])
    h = file_hashes(path, algos)
    size = os.path.getsize(path)
    ok_size = f.get("size") is None or size == f["size"]
    ok_hash = algo in ("none", None) or h.get(algo) == f["anchor"]["value"]
    return ok_size and ok_hash, {"path": f["path"], "size": size, "sha256": h["sha256"],
                                 "anchor": f["anchor"], "integrity_level": f["integrity_level"],
                                 "size_ok": ok_size, "anchor_ok": ok_hash if algo not in ("none", None) else None}


SEGMENT_MIN = 256 * CHUNK


def fetch_http_file(P, sid, dest, f, retries, base_delay, segments=1):
    target = safe_join(dest, f["path"])
    if os.path.exists(target):
        return 0, None  # verified at rename time; verify recomputes
    t0 = time.time()
    try:
        if segments > 1 and (f.get("size") or 0) >= SEGMENT_MIN:
            n = download_segmented(f["url"], target, f["size"], segments, retries=retries, base_delay=base_delay)
        else:
            n = download(f["url"], target, f.get("size"), retries=retries, base_delay=base_delay)
    except Exception as e:  # noqa: BLE001 - every failure is logged and keeps the .part
        log_attempt(P, {"source": sid, "path": f["path"], "url": f["url"], "result": "error", "error": repr(e)[:300]})
        return 0, "download error: %s" % repr(e)[:200]
    ok, rec = check_file(target + ".part", f)
    log_attempt(P, {"source": sid, "path": f["path"], "url": f["url"], "bytes": n, "seconds": round(time.time() - t0, 1),
                    "result": "ok" if ok else "integrity-mismatch", "sha256": rec["sha256"], "size": rec["size"]})
    if not ok:
        bad = target + ".mismatch"
        os.replace(target + ".part", bad)
        return n, "integrity mismatch (kept as %s)" % os.path.basename(bad)
    os.replace(target + ".part", target)
    return n, None


def git(args, cwd, env=None):
    e = dict(os.environ, GIT_LFS_SKIP_SMUDGE="1", GIT_TERMINAL_PROMPT="0")
    e.update(env or {})
    return subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "core.longpaths=true",
                           "-c", "core.symlinks=false"] + args,
                          cwd=cwd, env=e, capture_output=True, text=True, encoding="utf-8", errors="replace")


def fetch_git(P, s, dest):
    os.makedirs(dest, exist_ok=True)
    if os.path.isdir(os.path.join(dest, ".git")):
        head = git(["rev-parse", "HEAD"], dest)
        if head.returncode == 0 and head.stdout.strip() == s["revision"]:
            return 0, None
    else:
        r = git(["init", "-q"], dest)
        if r.returncode:
            return 0, "git init failed: " + r.stderr[-300:]
        git(["remote", "add", "origin", "https://github.com/%s.git" % s["repo"]], dest)
    t0 = time.time()
    before = dir_bytes(os.path.join(dest, ".git"))
    for attempt in range(6):
        r = git(["fetch", "--depth", "1", "origin", s["revision"]], dest)
        if r.returncode == 0:
            break
        log_attempt(P, {"source": s["id"], "result": "error", "error": r.stderr[-300:]})
        backoff(attempt, 5.0, None)
    else:
        return 0, "git fetch failed"
    r = git(["checkout", "-q", "--detach", s["revision"]], dest)
    n = dir_bytes(os.path.join(dest, ".git")) - before
    log_attempt(P, {"source": s["id"], "url": "https://github.com/%s" % s["repo"], "revision": s["revision"],
                    "bytes": n, "seconds": round(time.time() - t0, 1),
                    "result": "ok" if r.returncode == 0 else "checkout-error", "error": r.stderr[-300:] or None})
    return n, (None if r.returncode == 0 else "git checkout failed: " + r.stderr[-300:])


DRIVE_QUOTA_MARK = "drive quota"


def fetch_drive(P, s, dest, f, gdown, attempts=6, base_delay=60.0):
    target = safe_join(dest, f["path"])
    if os.path.exists(target):
        return 0, None
    incoming = os.path.join(dest, "incoming")
    os.makedirs(incoming, exist_ok=True)
    part = os.path.join(incoming, f["path"])
    before = os.path.getsize(part) if os.path.exists(part) else 0
    t0 = time.time()
    quota = False
    for attempt in range(attempts):
        r = subprocess.run([gdown, "--no-cookies", "--continue", f["drive_id"], "-O", part], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=incoming)
        if r.returncode == 0 and os.path.exists(part):
            break
        log_attempt(P, {"source": s["id"], "path": f["path"], "drive_id": f["drive_id"], "result": "error",
                        "error": (r.stderr or r.stdout)[-300:]})
        # gdown prints this when Drive refuses an anonymous download (quota exceeded or access interstitial).
        quota = "24 hours" in (r.stderr or "") + (r.stdout or "")
        if attempt + 1 < attempts:
            backoff(attempt, base_delay, None, cap=3600)
    else:
        kind = DRIVE_QUOTA_MARK if quota else "drive download failed"
        return 0, "%s after %d attempts; partial kept in incoming/" % (kind, attempts)
    n = os.path.getsize(part) - before
    ok, rec = check_file(part, f)
    if ok and f.get("size_hint"):
        hinted = float(f["size_hint"].split("G")[0])
        # Drive rounds to one decimal; accept either decimal or binary gigabytes.
        ok = any(abs(rec["size"] / unit - hinted) <= 0.05 for unit in (1e9, GIB))
        rec["size_ok"] = ok
    log_attempt(P, {"source": s["id"], "path": f["path"], "drive_id": f["drive_id"], "bytes": n,
                    "seconds": round(time.time() - t0, 1), "result": "ok" if ok else "size-mismatch",
                    "sha256": rec["sha256"], "size": rec["size"]})
    if not ok:
        return n, "size mismatch against Drive listing"
    os.replace(part, target)
    return n, None


def cmd_fetch(P, reg, sid, budget_gb, reserve_gb, workers=4, retries=6, base_delay=2.0,
              allow_unknown_size=False, gdown=None, free_bytes=None, segments=1):
    s = get_source(reg, sid)
    st = load_state(P, sid)
    fl = read_json(filelist_path(P, sid))
    if fl is None:
        save_state(P, sid, st, "BLOCKED:unpinned-filelist", "no pinned file list", "run check-metadata")
        return 2, {"error": "no pinned file list; run check-metadata first"}
    files = fl["files"]
    dest = raw_dir(P, s)
    if s["kind"] == "github-git":
        need = max(sum(f["size"] for f in files) - (dir_bytes(dest) if os.path.isdir(dest) else 0), 0)
    else:
        need = need_bytes(files, dest)
        unknown = [f["path"] for f in files if f.get("size") is None and not f.get("size_hint")]
        if unknown and not allow_unknown_size and len(unknown) == len(files):
            save_state(P, sid, st, "PENDING:budget", "all file sizes unknown", "rerun with --allow-unknown-size")
            return 4, {"error": "unknown sizes", "files": unknown[:5]}
    b = budget_check(P, need, budget_gb, reserve_gb, free_bytes=free_bytes)
    if not b["ok"]:
        save_state(P, sid, st, "PENDING:budget",
                   "needs %d B; shortfall %d B (budget %d B, reserve %d B, free %d B)"
                   % (need, b["shortfall_bytes"], b["budget"], b["reserve"], b["free"]),
                   "rerun with --budget-gb >= %.1f or free space" % ((b["used"] + need) / GIB + 0.1))
        return 4, {"budget": b}
    st["budget_check"] = b
    save_state(P, sid, st, "PARTIAL", "fetch in progress", "rerun fetch")
    total, errors = 0, []
    if s["kind"] == "github-git":
        n, err = fetch_git(P, s, dest)
        total += n
        errors += [err] if err else []
    elif s["kind"] == "google-drive-files":
        if not gdown:
            save_state(P, sid, st, "BLOCKED:tool", "gdown path not provided", "pass --gdown")
            return 2, {"error": "--gdown required"}
        for f in files:
            n, err = fetch_drive(P, s, dest, f, gdown, attempts=retries, base_delay=base_delay * 30)
            total += n
            errors += ["%s: %s" % (f["path"], err)] if err else []
    else:
        with concurrent.futures.ThreadPoolExecutor(workers) as ex:
            futs = {ex.submit(fetch_http_file, P, sid, dest, f, retries, base_delay, segments): f for f in files}
            for fut in concurrent.futures.as_completed(futs):
                n, err = fut.result()
                total += n
                if err:
                    errors.append("%s: %s" % (futs[fut]["path"], err))
    st["last_fetch"] = {"at": now(), "transferred_bytes": total, "errors": errors[:50], "error_count": len(errors)}
    if errors and all(DRIVE_QUOTA_MARK in e for e in errors):
        save_state(P, sid, st, "PENDING:drive-quota", "Drive refused all %d downloads (quota/interstitial)" % len(errors),
                   "rerun fetch after the Drive quota window (~24 h); never with cookies")
        return 5, {"transferred": total, "errors": errors[:10], "error_count": len(errors)}
    if errors:
        save_state(P, sid, st, "PARTIAL", "%d artefacts failed" % len(errors), "rerun fetch (resumes)")
        return 1, {"transferred": total, "errors": errors[:10], "error_count": len(errors)}
    save_state(P, sid, st, "PENDING:verify", "fetched; not yet verified", "run verify")
    return 0, {"transferred": total}


# ---------------------------------------------------------------- verify

def walk_files(base, skip_git=True):
    out = []
    for dp, dns, fns in os.walk(base):
        if skip_git and ".git" in dns:
            dns.remove(".git")
        dns.sort()
        for fn in sorted(fns):
            out.append(os.path.relpath(os.path.join(dp, fn), base).replace("\\", "/"))
    return out


def cmd_verify(P, reg, sid):
    s = get_source(reg, sid)
    st = load_state(P, sid)
    fl = read_json(filelist_path(P, sid))
    dest = raw_dir(P, s)
    if fl is None or not os.path.isdir(dest):
        save_state(P, sid, st, st.get("state") or "PENDING:not-started", "nothing to verify", "run fetch")
        return 2, {"error": "nothing fetched"}
    files = fl["files"]
    expected = {f["path"]: f for f in files}
    present = set(walk_files(dest))
    extras = sorted(p for p in present - set(expected) if not p.startswith("incoming/"))
    recs, missing, bad, pointers = [], [], [], []
    for path in sorted(expected):
        f = expected[path]
        p = safe_join(dest, path)
        if not os.path.exists(p):
            missing.append(path)
            continue
        ok, rec = check_file(p, f)
        if is_lfs_pointer(p) and f["anchor"]["algo"] != "git-sha1":
            pointers.append(path)
            ok = False
        if s["kind"] == "github-git" and is_lfs_pointer(p):
            pointers.append(path)
        recs.append(rec)
        if not ok:
            bad.append(path)
    git_check = None
    if s["kind"] == "github-git":
        head = git(["rev-parse", "HEAD"], dest).stdout.strip()
        fsck = git(["fsck", "--full", "--no-progress"], dest)
        status = git(["status", "--porcelain", "--untracked-files=all"], dest).stdout.strip()
        git_check = {"head": head, "head_ok": head == s["revision"], "fsck_exit": fsck.returncode,
                     "fsck_stderr": fsck.stderr[-500:], "worktree_clean": status == ""}
    exp = s.get("expected", {})
    counts = {"expected_files": len(expected), "present_files": len(recs), "missing": len(missing),
              "anchor_mismatch": len(bad), "lfs_pointers": len(set(pointers)), "extra_files": len(extras),
              "bytes": sum(r["size"] for r in recs),
              "expected_bytes": sum(f["size"] for f in files if f.get("size") is not None)}
    levels = sorted({r["integrity_level"] for r in recs})
    st.update(files=recs, counts=counts, missing=missing[:200], mismatched=bad[:200], extras=extras[:200],
              lfs_pointers=sorted(set(pointers))[:200], git_check=git_check, verified_at=now(),
              integrity_levels=levels, registry_expected=exp)
    st["files_verified"] = False
    problems = missing or bad or pointers or (git_check and not (git_check["head_ok"] and git_check["fsck_exit"] == 0
                                                                 and git_check["worktree_clean"]))
    if problems:
        save_state(P, sid, st, "PARTIAL",
                   "missing %d, mismatched %d, lfs pointers %d%s" % (len(missing), len(bad), len(set(pointers)),
                                                                  "" if not git_check else ", git %s" % git_check),
                   "rerun fetch, then verify")
        return 1, counts
    st["files_verified"] = True
    state = "VERIFIED" if levels == ["publisher-hash"] else "VERIFIED-LOCAL-ONLY"
    reason = "all files match publisher anchors" if state == "VERIFIED" else \
        "complete; integrity levels %s (no publisher hash for some files)" % ",".join(levels)
    if s.get("state_target") == "metadata-only":
        state = "PENDING:metadata-only"
        reason = "allowed small files verified (%s); archives not acquired (owner decision D4)" % ",".join(levels)
        save_state(P, sid, st, state, reason, "archives need a separate owner request")
        return 0, dict(counts, state=state)
    save_state(P, sid, st, state, reason, None)
    return 0, dict(counts, state=state)


# ---------------------------------------------------------------- archive audit (headers only)

def audit_zip(path):
    out = {"members": 0, "unsafe": [], "encrypted": 0, "crc_bad": [], "crc_skipped_encrypted": 0,
           "uncompressed": 0, "compressed": 0}
    with zipfile.ZipFile(path) as z:
        for i in z.infolist():
            out["members"] += 1
            out["uncompressed"] += i.file_size
            out["compressed"] += i.compress_size
            n = i.filename.replace("\\", "/")
            mode = (i.external_attr >> 16) & 0o170000
            if n.startswith("/") or (len(n) > 1 and n[1] == ":") or ".." in n.split("/"):
                out["unsafe"].append(n + " [path]")
            if mode == 0o120000:
                out["unsafe"].append(n + " [symlink]")
            if i.compress_size and i.file_size / i.compress_size > 100 and i.file_size > 100 * CHUNK:
                out["unsafe"].append(n + " [ratio>100]")
            if i.flag_bits & 0x1:
                out["encrypted"] += 1
                out["crc_skipped_encrypted"] += 1
                continue
            try:
                with z.open(i) as m:
                    while m.read(CHUNK):
                        pass
            except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError) as e:
                out["crc_bad"].append("%s: %s" % (n, e))
    return out


def audit_tar(path):
    out = {"members": 0, "unsafe": [], "uncompressed": 0, "compressed": os.path.getsize(path)}
    with tarfile.open(path, "r:*") as t:
        for m in t:
            out["members"] += 1
            out["uncompressed"] += m.size
            n = m.name.replace("\\", "/")
            if n.startswith("/") or (len(n) > 1 and n[1] == ":") or ".." in n.split("/"):
                out["unsafe"].append(n + " [path]")
            if m.issym() or m.islnk():
                out["unsafe"].append("%s [link -> %s]" % (n, m.linkname))
            if m.isdev() or m.isfifo():
                out["unsafe"].append(n + " [device]")
    if out["compressed"] and out["uncompressed"] / out["compressed"] > 100:
        out["unsafe"].append("[archive ratio>100]")
    return out


def cmd_audit_archives(P, reg, sid):
    s = get_source(reg, sid)
    st = load_state(P, sid)
    dest = raw_dir(P, s)
    results, unsafe, errors = {}, 0, []
    for rel in walk_files(dest):
        p = safe_join(dest, rel)
        low = rel.lower()
        try:
            if low.endswith(".zip"):
                results[rel] = audit_zip(p)
            elif low.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")):
                results[rel] = audit_tar(p)
            else:
                continue
        except Exception as e:  # noqa: BLE001
            errors.append("%s: %r" % (rel, e))
            continue
        unsafe += len(results[rel]["unsafe"]) + len(results[rel].get("crc_bad", []))
    st["archive_audit"] = {"at": now(), "archives": len(results), "unsafe_or_corrupt": unsafe,
                           "errors": errors, "detail": results}
    save_state(P, sid, st)
    summary = {"archives": len(results), "unsafe_or_corrupt": unsafe, "errors": len(errors),
               "encrypted_members": sum(r.get("encrypted", 0) for r in results.values())}
    return (0 if unsafe == 0 and not errors else 1), summary


# ---------------------------------------------------------------- catalog / status

NOT_ACQUIRED_STATES = ("PENDING", "BLOCKED", "PARTIAL", "DEFERRED", "NOT-ACQUIRED")


def cmd_catalog(P, reg):
    catalog, sums, levels, not_acq = [], [], [], []
    for s in reg["sources"]:
        st = load_state(P, s["id"])
        state = st.get("state")
        if s.get("decision_state") and state.startswith("PENDING:not-started"):
            state, st["reason"], st["next_action"] = s["decision_state"], s.get("reason"), s.get("next_action")
        entry = {k: s.get(k) for k in ("id", "kind", "category", "lineage_group", "copy_of", "license",
                                       "repo", "record", "revision", "doi")}
        entry.update(state=state, reason=st.get("reason"), next_action=st.get("next_action"),
                     version_dir=None if s["kind"] == "google-drive-files" and "retrieved_tag" not in s
                     else version_dir(s),
                     counts=st.get("counts"), integrity_levels=st.get("integrity_levels"),
                     archive_audit={k: v for k, v in (st.get("archive_audit") or {}).items() if k != "detail"} or None,
                     provenance="data/provenance/%s.json" % s["id"])
        catalog.append(entry)
        if st.get("files_verified") and state != "PARTIAL":
            base = "data/raw/%s/%s/" % (s["id"], version_dir(s))
            for r in st.get("files", []):
                sums.append("%s  %s%s" % (r["sha256"], base, r["path"]))
                anchor = r["anchor"]
                levels.append("%s%s\t%s\t%s:%s" % (base, r["path"], r["integrity_level"],
                                                   anchor["algo"], anchor["value"] or "-"))
        if state is None or state.split(":")[0] in NOT_ACQUIRED_STATES:
            not_acq.append({"id": s["id"], "state": state, "reason": st.get("reason") or s.get("reason"),
                            "next_action": st.get("next_action") or s.get("next_action"),
                            "expected": s.get("expected")})
    write_json(os.path.join(P["manifests"], "dataset_catalog.json"),
               {"generated_at": now(), "registry": "scripts/datasets/sources.json", "sources": catalog})
    write_json(os.path.join(P["manifests"], "not-acquired.json"), {"generated_at": now(), "sources": not_acq})
    with open(os.path.join(P["manifests"], "checksums.sha256"), "w", encoding="utf-8", newline="\n") as f:
        f.writelines(line + "\n" for line in sorted(sums, key=lambda x: x[66:]))
    with open(os.path.join(P["manifests"], "checksums-levels.tsv"), "w", encoding="utf-8", newline="\n") as f:
        f.write("path\tintegrity_level\tanchor\n")
        f.writelines(line + "\n" for line in sorted(levels))
    return 0, {"sources": len(catalog), "checksummed_files": len(sums), "not_acquired": len(not_acq)}


def cmd_status(P, reg):
    rows = []
    for s in reg["sources"]:
        st = load_state(P, s["id"])
        state = st.get("state")
        if s.get("decision_state") and state.startswith("PENDING:not-started"):
            state = s["decision_state"]
        rows.append((s["id"], state, ",".join(st.get("integrity_levels") or []) or "-",
                     (st.get("reason") or s.get("reason") or "")[:70], st.get("next_action") or s.get("next_action") or ""))
    w = [max(len(str(r[i])) for r in rows) for i in range(3)]
    for r in rows:
        print("%-*s  %-*s  %-*s  %s | %s" % (w[0], r[0], w[1], r[1], w[2], r[2], r[3], r[4]))
    return 0, None


def cmd_plan(P, reg, sid, budget_gb, reserve_gb):
    s = get_source(reg, sid)
    fl = read_json(filelist_path(P, sid))
    if fl is None:
        return 2, {"error": "no pinned file list; run check-metadata"}
    files = fl["files"]
    dest = raw_dir(P, s)
    need = need_bytes(files, dest) if s["kind"] != "github-git" else sum(f["size"] for f in files)
    out = {"source": sid, "kind": s["kind"], "dest": os.path.relpath(dest, P["root"]).replace("\\", "/"),
           "files": len(files), "expected_bytes": sum(f["size"] or 0 for f in files),
           "unknown_size_files": sum(1 for f in files if f.get("size") is None),
           "integrity_levels": sorted({f["integrity_level"] for f in files}),
           "budget": budget_check(P, need, budget_gb, reserve_gb),
           "urls_sha256": hashlib.sha256("\n".join(
               "%s %s %s" % (f["path"], f.get("url") or f.get("drive_id") or "git", f["anchor"]["value"])
               for f in sorted(files, key=lambda x: x["path"])).encode("utf-8")).hexdigest()}
    return 0, out


# ---------------------------------------------------------------- cli

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=ROOT, help="project root (default: two levels above this script)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check-metadata", "plan", "fetch", "verify", "audit-archives"):
        p = sub.add_parser(name)
        p.add_argument("--source", required=True)
        if name in ("plan", "fetch"):
            p.add_argument("--budget-gb", type=float, default=None)
            p.add_argument("--reserve-gb", type=float, default=None)
        if name == "fetch":
            p.add_argument("--workers", type=int, default=4)
            p.add_argument("--allow-unknown-size", action="store_true")
            p.add_argument("--retries", type=int, default=6, help="attempts per artefact (Drive: per file)")
            p.add_argument("--gdown", default=None, help="path to gdown inside the isolated venv")
            p.add_argument("--segments", type=int, default=1,
                           help="parallel byte ranges per file of 256 MiB or more (hosts that throttle per connection)")
        if name == "check-metadata":
            p.add_argument("--no-pin", action="store_true", help="never write a missing file list")
    sub.add_parser("catalog")
    sub.add_parser("status")
    a = ap.parse_args(argv)
    P = paths(a.root)
    reg = load_registry(P)
    d = reg.get("defaults", {})
    bg = getattr(a, "budget_gb", None) or d.get("budget_gb", 250)
    rg = getattr(a, "reserve_gb", None)
    rg = d.get("reserve_gb", 100) if rg is None else rg
    try:
        if a.cmd == "check-metadata":
            code, out = cmd_check_metadata(P, reg, a.source, pin_if_missing=not a.no_pin)
        elif a.cmd == "plan":
            code, out = cmd_plan(P, reg, a.source, bg, rg)
        elif a.cmd == "fetch":
            code, out = cmd_fetch(P, reg, a.source, bg, rg, workers=a.workers, retries=a.retries,
                                  allow_unknown_size=a.allow_unknown_size, gdown=a.gdown, segments=a.segments)
        elif a.cmd == "verify":
            code, out = cmd_verify(P, reg, a.source)
        elif a.cmd == "audit-archives":
            code, out = cmd_audit_archives(P, reg, a.source)
        elif a.cmd == "catalog":
            code, out = cmd_catalog(P, reg)
        else:
            code, out = cmd_status(P, reg)
    except DriftError as e:
        code, out = 3, {"drift": str(e)}
    if out is not None:
        print(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
