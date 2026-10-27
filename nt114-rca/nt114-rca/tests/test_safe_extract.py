"""Archive extraction rejects unsafe members before writing anything, and resumes."""
from __future__ import annotations

import hashlib
import io
import json
import tarfile
import zipfile

import pytest

from rca.safe_extract import UnsafeArchive, extract


def _tar(path, members):
    """members: [(name, bytes | None, type)]"""
    with tarfile.open(path, "w:gz") as t:
        for name, data, kind in members:
            ti = tarfile.TarInfo(name)
            if kind == "sym":
                ti.type, ti.linkname = tarfile.SYMTYPE, "/etc/passwd"
                t.addfile(ti)
            elif kind == "hard":
                ti.type, ti.linkname = tarfile.LNKTYPE, "a.txt"
                t.addfile(ti)
            elif kind == "fifo":
                ti.type = tarfile.FIFOTYPE
                t.addfile(ti)
            else:
                ti.size = len(data)
                t.addfile(ti, io.BytesIO(data))
    return path


def _zip(path, members):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in members:
            z.writestr(name, data)
    return path


def test_safe_tar_extracts_with_receipt_and_skips_appledouble(tmp_path):
    arc = _tar(tmp_path / "ok.tar.gz", [("d/a.txt", b"alpha", "file"), ("d/b.csv", b"x,y\n1,2\n", "file"),
                                         ("__MACOSX/d/._a.txt", b"junk", "file"), ("d/.DS_Store", b"junk", "file")])
    r = extract(arc, tmp_path / "out")
    assert (tmp_path / "out/d/a.txt").read_bytes() == b"alpha"
    assert set(r["members"]) == {"d/a.txt", "d/b.csv"}
    assert set(r["skipped"]) == {"__MACOSX/d/._a.txt", "d/.DS_Store"}
    assert r["complete"] and not list((tmp_path / "out").rglob("*.part"))


@pytest.mark.parametrize("name,kind", [
    ("../evil.txt", "file"), ("/abs.txt", "file"), ("C:/x.txt", "file"), ("d/../../x", "file"),
    ("d/CON.txt", "file"), ("d/a<b>.txt", "file"), ("d/trail. ", "file"),
    ("d/link", "sym"), ("d/hard", "hard"), ("d/pipe", "fifo"),
])
def test_unsafe_tar_member_rejected(tmp_path, name, kind):
    arc = _tar(tmp_path / "bad.tar.gz", [("a.txt", b"ok", "file"), (name, b"x", kind)])
    with pytest.raises(UnsafeArchive):
        extract(arc, tmp_path / "out")
    assert not (tmp_path / "evil.txt").exists()


@pytest.mark.parametrize("name", ["../evil.txt", "/abs.txt", "d/AUX", "d/x:y"])
def test_unsafe_zip_member_rejected(tmp_path, name):
    arc = _zip(tmp_path / "bad.zip", [("a.txt", b"ok"), (name, b"x")])
    with pytest.raises(UnsafeArchive):
        extract(arc, tmp_path / "out")
    assert not (tmp_path / "evil.txt").exists()


def test_path_too_long_rejected(tmp_path):
    arc = _zip(tmp_path / "long.zip", [("d/" + "a" * 250 + ".txt", b"x")])
    with pytest.raises(UnsafeArchive, match="too long"):
        extract(arc, tmp_path / "out")


def test_bomb_ratio_and_member_size_limits(tmp_path):
    arc = _zip(tmp_path / "bomb.zip", [("z.bin", b"\0" * 5_000_000)])
    with pytest.raises(UnsafeArchive, match="ratio"):
        extract(arc, tmp_path / "out", {"max_total_ratio": 10})
    with pytest.raises(UnsafeArchive, match="too large"):
        extract(arc, tmp_path / "out2", {"max_member_bytes": 1000})


def test_rerun_skips_verified_members_and_repairs_damaged(tmp_path):
    arc = _tar(tmp_path / "ok.tar.gz", [("a.txt", b"alpha", "file"), ("b.txt", b"beta", "file")])
    out = tmp_path / "out"
    extract(arc, out)
    m_a = (out / "a.txt").stat().st_mtime_ns
    (out / "b.txt").write_bytes(b"be")       # truncated, as after a crash
    r = extract(arc, out)
    assert (out / "a.txt").stat().st_mtime_ns == m_a
    assert (out / "b.txt").read_bytes() == b"beta"
    assert r["members"]["b.txt"]["size"] == 4


def test_receipt_records_archive_and_member_sha256(tmp_path):
    arc = _tar(tmp_path / "ok.tar.gz", [("a.txt", b"alpha", "file")])
    r = extract(arc, tmp_path / "out")
    assert r["archive_sha256"] == hashlib.sha256(arc.read_bytes()).hexdigest()
    assert r["members"]["a.txt"]["sha256"] == hashlib.sha256(b"alpha").hexdigest()


def test_rerun_repairs_member_damaged_without_size_change(tmp_path):
    arc = _tar(tmp_path / "ok.tar.gz", [("a.txt", b"alpha", "file")])
    out = tmp_path / "out"
    extract(arc, out)
    (out / "a.txt").write_bytes(b"alphX")
    extract(arc, out)
    assert (out / "a.txt").read_bytes() == b"alpha"


def test_receipt_without_sha_fields_is_not_trusted(tmp_path):
    arc = _tar(tmp_path / "ok.tar.gz", [("a.txt", b"alpha", "file")])
    out = tmp_path / "out"
    extract(arc, out)
    rp = out / ".extract.json"
    old = json.loads(rp.read_text(encoding="utf-8"))
    old.pop("archive_sha256", None)
    old["members"] = {k: {"size": v["size"]} for k, v in old["members"].items()}
    rp.write_text(json.dumps(old), encoding="utf-8")
    (out / "a.txt").write_bytes(b"alphX")
    r = extract(arc, out)
    assert (out / "a.txt").read_bytes() == b"alpha" and r["archive_sha256"] and r["members"]["a.txt"]["sha256"]


def test_receipt_of_another_archive_is_not_trusted(tmp_path):
    out = tmp_path / "out"
    extract(_tar(tmp_path / "v1.tar.gz", [("a.txt", b"alpha", "file")]), out)
    r = extract(_tar(tmp_path / "v2.tar.gz", [("a.txt", b"omega", "file")]), out)
    assert (out / "a.txt").read_bytes() == b"omega"
    assert r["members"]["a.txt"]["sha256"] == hashlib.sha256(b"omega").hexdigest()


@pytest.mark.parametrize("name", [".extract.json", "./.extract.json", ".EXTRACT.json"])
def test_member_named_like_the_receipt_rejected(tmp_path, name):
    arc = _tar(tmp_path / "bad.tar.gz", [("a.txt", b"ok", "file"), (name, b"{}", "file")])
    with pytest.raises(UnsafeArchive, match="receipt"):
        extract(arc, tmp_path / "out")


def test_case_insensitive_name_collision_rejected(tmp_path):
    arc = _tar(tmp_path / "bad.tar.gz", [("d/a.txt", b"one", "file"), ("D/A.txt", b"two", "file")])
    with pytest.raises(UnsafeArchive, match="collision"):
        extract(arc, tmp_path / "out")
    arc = _zip(tmp_path / "bad.zip", [("d/a.txt", b"one"), ("d/A.TXT", b"two")])
    with pytest.raises(UnsafeArchive, match="collision"):
        extract(arc, tmp_path / "out2")
