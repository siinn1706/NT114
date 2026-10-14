"""Archive extraction rejects unsafe members before writing anything, and resumes."""
from __future__ import annotations

import io
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
