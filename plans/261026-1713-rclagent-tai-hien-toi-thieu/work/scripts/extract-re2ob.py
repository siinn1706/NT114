"""Extract the NT114 mirror of RCAEval RE2-OB.zip into a separate directory (the zip is only read).

usage: python -X utf8 extract-re2ob.py ZIP EXPECTED_SHA256 OUT_DIR

Fails before extracting when the zip hash differs from the NT114 manifest value. Prints the case layout
the author's preprocess expects: <service>_<fault>/<digit instance>/{inject_time.txt, traces.csv,
logs.csv, simple_metrics.csv}.
"""
import hashlib
import sys
import zipfile
from pathlib import Path

zp, want, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
h = hashlib.sha256()
with zp.open("rb") as f:
    for b in iter(lambda: f.read(1 << 22), b""):
        h.update(b)
if h.hexdigest() != want:
    sys.exit(f"sha256 mismatch: {h.hexdigest()}")
print("zip sha256 ok", want)
if out.exists():
    sys.exit(f"exists: {out}")
with zipfile.ZipFile(zp) as z:
    z.extractall(out)
root = out / "RE2-OB"
need = ("inject_time.txt", "traces.csv", "logs.csv", "simple_metrics.csv")
cases = [p for d in sorted(root.iterdir()) if d.is_dir() for p in sorted(d.iterdir()) if p.is_dir() and p.name.isdigit()]
other = [str(p.relative_to(root)) for d in root.iterdir() if d.is_dir() for p in d.iterdir() if p.is_dir() and not p.name.isdigit()]
missing = [(str(c.relative_to(root)), n) for c in cases for n in need if not (c / n).is_file()]
print("digit instances", len(cases), "service_fault dirs", len({c.parent.name for c in cases}))
print("non-digit instance dirs (skipped by the author's preprocess):", other)
print("missing required files:", missing)
