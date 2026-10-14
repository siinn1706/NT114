"""Offline tests for scripts/datasets/acquire.py (stdlib unittest, local http.server only)."""

import hashlib
import http.server
import importlib.util
import io
import json
import os
import shutil
import tarfile
import tempfile
import threading
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "acquire", os.path.join(os.path.dirname(HERE), "scripts", "datasets", "acquire.py"))
acq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(acq)

PAYLOAD = os.urandom(300_000)


class RangeHandler(http.server.BaseHTTPRequestHandler):
    """Serves PAYLOAD at /data.bin with Range support; /drop.bin closes mid-body once."""
    dropped = set()

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path not in ("/data.bin", "/drop.bin"):
            self.send_error(404)
            return
        start, end = 0, len(PAYLOAD) - 1
        rng = self.headers.get("Range")
        if rng:
            a, _, b = rng.split("=")[1].partition("-")
            start, end = int(a), int(b) if b else end
        body = PAYLOAD[start:end + 1]
        self.send_response(206 if rng else 200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.path == "/drop.bin" and "drop" not in RangeHandler.dropped:
            RangeHandler.dropped.add("drop")
            self.wfile.write(body[:100_000])
            self.wfile.flush()
            self.connection.shutdown(2)
            return
        self.wfile.write(body)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), RangeHandler)
        cls.url = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.P = acq.paths(self.tmp)
        os.makedirs(os.path.dirname(self.P["registry"]))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def registry(self, files, anchor_ok=True, level="publisher-hash"):
        reg = {"defaults": {"budget_gb": 250, "reserve_gb": 0},
               "sources": [{"id": "t", "kind": "zenodo-record", "record": "1"}]}
        acq.write_json(self.P["registry"], reg)
        md5 = hashlib.md5(PAYLOAD).hexdigest() if anchor_ok else "0" * 32
        fl = [{"path": name, "size": len(PAYLOAD), "url": self.url + path, "integrity_level": level,
               "anchor": ({"algo": "md5", "value": md5, "source": "test"} if level == "publisher-hash"
                          else {"algo": "none", "value": None, "source": "test"})}
              for name, path in files]
        acq.write_json(acq.filelist_path(self.P, "t"), {"id": "t", "files": fl})
        return acq.load_registry(self.P)

    def manifest_lines(self):
        with open(self.P["download_log"], encoding="utf-8") as f:
            return [json.loads(x) for x in f]


class TestFetchVerify(Base):
    def test_resume_after_dropped_connection(self):
        reg = self.registry([("a.bin", "/drop.bin")])
        code, out = acq.cmd_fetch(self.P, reg, "t", 250, 0, retries=3, base_delay=0.01)
        self.assertEqual(code, 0, out)
        code, out = acq.cmd_verify(self.P, reg, "t")
        self.assertEqual((code, out["state"]), (0, "VERIFIED"))
        with open(os.path.join(acq.raw_dir(self.P, acq.get_source(reg, "t")), "a.bin"), "rb") as f:
            self.assertEqual(f.read(), PAYLOAD)

    def test_hash_mismatch_leaves_partial(self):
        reg = self.registry([("a.bin", "/data.bin")], anchor_ok=False)
        code, _ = acq.cmd_fetch(self.P, reg, "t", 250, 0, retries=1, base_delay=0.01)
        self.assertEqual(code, 1)
        self.assertEqual(acq.load_state(self.P, "t")["state"], "PARTIAL")
        code, _ = acq.cmd_verify(self.P, reg, "t")
        self.assertEqual(code, 1)
        self.assertEqual(acq.load_state(self.P, "t")["state"], "PARTIAL")
        self.assertEqual(self.manifest_lines()[-1]["result"], "integrity-mismatch")

    def test_budget_refusal_writes_nothing(self):
        reg = self.registry([("a.bin", "/data.bin")])
        code, out = acq.cmd_fetch(self.P, reg, "t", budget_gb=0.0001, reserve_gb=0)
        self.assertEqual(code, 4)
        st = acq.load_state(self.P, "t")
        self.assertEqual(st["state"], "PENDING:budget")
        self.assertIn("shortfall", st["reason"])
        self.assertGreater(out["budget"]["shortfall_bytes"], 0)
        self.assertFalse(os.path.exists(acq.raw_dir(self.P, acq.get_source(reg, "t"))))

    def test_reserve_refusal(self):
        reg = self.registry([("a.bin", "/data.bin")])
        code, out = acq.cmd_fetch(self.P, reg, "t", 250, reserve_gb=1, free_bytes=acq.GIB)
        self.assertEqual(code, 4)
        self.assertEqual(out["budget"]["shortfall_bytes"], len(PAYLOAD))

    def test_idempotent_rerun_transfers_zero(self):
        reg = self.registry([("a.bin", "/data.bin"), ("sub/b.bin", "/data.bin")])
        self.assertEqual(acq.cmd_fetch(self.P, reg, "t", 250, 0)[0], 0)
        n_lines = len(self.manifest_lines())
        code, out = acq.cmd_fetch(self.P, reg, "t", 250, 0)
        self.assertEqual((code, out["transferred"]), (0, 0))
        self.assertEqual(len(self.manifest_lines()), n_lines)

    def test_segmented_download_resumes_existing_part(self):
        dest = os.path.join(self.tmp, "seg", "a.bin")
        os.makedirs(os.path.dirname(dest))
        with open(dest + ".part", "wb") as f:
            f.write(PAYLOAD[:50_000])  # earlier single-stream progress
        n = acq.download_segmented(self.url + "/data.bin", dest, len(PAYLOAD), 4, retries=2, base_delay=0.01)
        with open(dest + ".part", "rb") as f:
            self.assertEqual(f.read(), PAYLOAD)
        self.assertEqual(n, len(PAYLOAD) - 50_000)
        self.assertEqual(os.listdir(os.path.dirname(dest)), ["a.bin.part"])

    def test_local_only_never_verified(self):
        reg = self.registry([("a.bin", "/data.bin")], level="local-only")
        self.assertEqual(acq.cmd_fetch(self.P, reg, "t", 250, 0)[0], 0)
        code, out = acq.cmd_verify(self.P, reg, "t")
        self.assertEqual((code, out["state"]), (0, "VERIFIED-LOCAL-ONLY"))

    def test_lfs_pointer_detected(self):
        reg = self.registry([("a.bin", "/data.bin")])
        dest = acq.raw_dir(self.P, acq.get_source(reg, "t"))
        os.makedirs(dest)
        with open(os.path.join(dest, "a.bin"), "wb") as f:
            f.write(acq.LFS_PREFIX + b"\noid sha256:" + b"0" * 64 + b"\nsize 300000\n")
        code, out = acq.cmd_verify(self.P, reg, "t")
        self.assertEqual(code, 1)
        self.assertEqual(out["lfs_pointers"], 1)

    def test_drive_quota_is_pending_not_partial(self):
        acq.write_json(self.P["registry"], {"sources": [{"id": "d", "kind": "google-drive-files",
                                                         "drive_folder": "f", "retrieved_tag": "x"}]})
        acq.write_json(acq.filelist_path(self.P, "d"), {"id": "d", "files": [
            {"path": "a.zip", "drive_id": "1", "size": None, "size_hint": "1.0G", "integrity_level": "local-only",
             "anchor": {"algo": "none", "value": None, "source": "test"}}]})
        reg = acq.load_registry(self.P)
        msg = "Too many users have viewed or downloaded this file recently. If you still can't access a file after 24 hours"
        real = acq.subprocess.run
        acq.subprocess.run = lambda *a, **k: acq.subprocess.CompletedProcess(a[0], 1, "", msg)
        try:
            code, out = acq.cmd_fetch(self.P, reg, "d", 250, 0, retries=2, base_delay=0.0001, gdown="gdown")
        finally:
            acq.subprocess.run = real
        self.assertEqual(code, 5)
        self.assertEqual(acq.load_state(self.P, "d")["state"], "PENDING:drive-quota")

    def test_unpinned_registry_rejected(self):
        acq.write_json(self.P["registry"], {"sources": [{"id": "x", "kind": "huggingface-dataset",
                                                         "repo": "a/b", "revision": "main"}]})
        with self.assertRaises(SystemExit):
            acq.load_registry(self.P)
        acq.write_json(self.P["registry"], {"sources": [{"id": "x", "kind": "ftp"}]})
        with self.assertRaises(SystemExit):
            acq.load_registry(self.P)

    def test_unsafe_relative_path_rejected(self):
        for bad in ("../x", "/abs", "C:/x", "a/../b", "a//b"):
            with self.assertRaises(ValueError):
                acq.safe_join(self.tmp, bad)


class TestArchiveAudit(Base):
    def test_unsafe_zip_and_tar_flagged_without_extraction(self):
        reg = self.registry([])
        dest = acq.raw_dir(self.P, acq.get_source(reg, "t"))
        os.makedirs(dest)
        with zipfile.ZipFile(os.path.join(dest, "z.zip"), "w") as z:
            z.writestr("ok.txt", "fine")
            z.writestr("../evil.txt", "x")
        with tarfile.open(os.path.join(dest, "t.tar.gz"), "w:gz") as t:
            info = tarfile.TarInfo("link")
            info.type, info.linkname = tarfile.SYMTYPE, "/etc/passwd"
            t.addfile(info)
            data = b"abc"
            info = tarfile.TarInfo("/abs.txt")
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
        before = sorted(os.listdir(dest))
        code, out = acq.cmd_audit_archives(self.P, reg, "t")
        self.assertEqual(code, 1)
        self.assertEqual(out["unsafe_or_corrupt"], 3)
        self.assertEqual(sorted(os.listdir(dest)), before)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "data", "raw", "t", "evil.txt")))

    def test_clean_zip_passes(self):
        reg = self.registry([])
        dest = acq.raw_dir(self.P, acq.get_source(reg, "t"))
        os.makedirs(dest)
        with zipfile.ZipFile(os.path.join(dest, "z.zip"), "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("dir/ok.txt", "fine" * 100)
        self.assertEqual(acq.cmd_audit_archives(self.P, reg, "t"), (0, {
            "archives": 1, "unsafe_or_corrupt": 0, "errors": 0, "encrypted_members": 0}))


class TestHelpers(unittest.TestCase):
    def test_git_blob_sha1(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello\n")
        try:
            # `git hash-object` of "hello\n"
            self.assertEqual(acq.file_hashes(f.name, ["git-sha1"])["git-sha1"],
                             "ce013625030ba8dba906f756967f9e9ca394464a")
        finally:
            os.remove(f.name)

    def test_parse_lfs_pointer(self):
        ptr = acq.LFS_PREFIX + b"\noid sha256:" + b"a" * 64 + b"\nsize 42\n"
        self.assertEqual(acq.parse_lfs_pointer(ptr), {"sha256": "a" * 64, "size": 42})
        self.assertIsNone(acq.parse_lfs_pointer(b"plain"))

    def test_drive_hint_rounds_up(self):
        self.assertEqual(acq.hint_bytes("2.6G (Drive-rounded)"), 3 * acq.GIB)


if __name__ == "__main__":
    unittest.main()
