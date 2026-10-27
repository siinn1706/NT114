"""Phase 08: re-check the static evidence behind two gate corrections, without running any paper code.

usage: python -X utf8 -I check-gate-evidence.py ARCHIVE PY7ZR_DIR OUT_JSON
ARCHIVE: CHASE.7z kept outside the NT114 repo; it is hashed and its entry names are listed (nothing extracted).
PY7ZR_DIR: directory holding py7zr (installed outside the NT114 environment).
Also fetches the public Zenodo API record 19176851 (AIOps 2022) and records title, licence and file names.
"""
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone

archive, lib, out = sys.argv[1:4]
sys.path.insert(0, lib)
import py7zr  # noqa: E402

data = open(archive, "rb").read()
names = py7zr.SevenZipFile(archive).getnames()
top = [n for n in names if n.count("/") == 1]
result = {"checked_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
          "archive": {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "entries": len(names),
                      "top_level": top, "py7zr": py7zr.__version__,
                      "license_like": [n for n in names if "licen" in n.lower()],
                      "readme_like": [n for n in names if "readme" in n.lower()]}}
with urllib.request.urlopen("https://zenodo.org/api/records/19176851", timeout=60) as response:
    record = json.load(response)
    result["zenodo"] = {"http": response.status, "title": record["metadata"]["title"],
                        "license": record["metadata"].get("license", {}).get("id"),
                        "files": [f["key"] for f in record.get("files", [])]}
open(out, "w", encoding="utf-8").write(json.dumps(result, indent=1))
print(json.dumps(result))
